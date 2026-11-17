"""Incremental raw-version loader; warehouse is separate from the shop database."""
import json
import os
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

import pipeline


def connect():
    return psycopg.connect(host='warehouse', dbname=os.environ.get('WAREHOUSE_DB', 'shoppulse_warehouse'),
        user=os.environ['PGUSER'], password=os.environ['PGPASSWORD'])


def bootstrap():
    with connect() as conn:
        conn.execute('CREATE SCHEMA IF NOT EXISTS bronze')
        conn.execute('CREATE SCHEMA IF NOT EXISTS platform')
        conn.execute('''CREATE TABLE IF NOT EXISTS bronze.raw_records (
            object_key text PRIMARY KEY, source_name text NOT NULL, payload jsonb NOT NULL,
            source_updated_at timestamptz NOT NULL, loaded_at timestamptz NOT NULL DEFAULT now())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bronze.ingestion_clock (
            source_name text PRIMARY KEY, checked_at timestamptz NOT NULL, run_id text NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS platform.pipeline_runs (
            run_id text PRIMARY KEY, finished_at timestamptz NOT NULL DEFAULT now(),
            status text NOT NULL, details jsonb NOT NULL)''')


def load_bronze():
    bootstrap()
    manifests = []
    pages = pipeline.S3.get_paginator('list_objects_v2').paginate(
        Bucket=pipeline.BUCKET, Prefix='_metadata/m2/runs/')
    for page in pages:
        for item in page.get('Contents', []):
            manifest = pipeline.read_json(item['Key'])
            if manifest['status'] == 'success':
                manifests.append(manifest)
    if not manifests:
        raise RuntimeError('No successful ingestion manifest; run M2 first')
    manifests.sort(key=lambda m: m['finished_at'])
    imported = 0
    with connect() as conn:
        known = {r[0] for r in conn.execute('SELECT object_key FROM bronze.raw_records')}
        for manifest in manifests:
            for source, data in manifest['sources'].items():
                for key in data.get('object_keys', []):
                    if key in known:
                        continue
                    row = pipeline.read_json(key)
                    conn.execute('''INSERT INTO bronze.raw_records
                        (object_key, source_name, payload, source_updated_at) VALUES (%s,%s,%s,%s)
                        ON CONFLICT (object_key) DO NOTHING''', (key, source, Jsonb(row), row['updated_at']))
                    known.add(key)
                    imported += 1
        latest = manifests[-1]
        for source in latest['sources']:
            conn.execute('''INSERT INTO bronze.ingestion_clock VALUES (%s,%s,%s)
                ON CONFLICT(source_name) DO UPDATE SET checked_at=excluded.checked_at, run_id=excluded.run_id''',
                (source, latest['finished_at'], latest['run_id']))
    return {'raw_versions_imported': imported, 'manifest_run_id': manifests[-1]['run_id']}


def grant_readonly():
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='metabase_reader'").fetchone():
            conn.execute('CREATE ROLE metabase_reader LOGIN')
        conn.execute(sql.SQL('ALTER ROLE metabase_reader PASSWORD {}').format(sql.Literal(os.environ['METABASE_READ_PASSWORD'])))
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO metabase_reader').format(
            sql.Identifier(os.environ.get('WAREHOUSE_DB', 'shoppulse_warehouse'))))
        conn.execute('GRANT USAGE ON SCHEMA marts TO metabase_reader')
        conn.execute('GRANT SELECT ON ALL TABLES IN SCHEMA marts TO metabase_reader')
        conn.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO metabase_reader')


def record_run(run_id, status, details):
    with connect() as conn:
        conn.execute('''INSERT INTO platform.pipeline_runs(run_id,status,details) VALUES(%s,%s,%s)
            ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, details=excluded.details, finished_at=now()''',
            (run_id, status, Jsonb(details)))
