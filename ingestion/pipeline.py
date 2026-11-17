"""M2 local ingestion. Content-addressed raw versions, checkpoint after successful run."""
import argparse
import csv
import hashlib
import io
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg import sql

TABLES = {'customers': 'customer_id', 'products': 'product_id', 'orders': 'order_id',
          'order_items': 'order_item_id', 'payments': 'payment_id'}
BUCKET = os.environ['RAW_BUCKET']
S3 = boto3.client('s3', endpoint_url='http://minio:9000', region_name='us-east-1')
STATE_KEY = '_metadata/m2/checkpoint.json'
EPOCH = '1970-01-01T00:00:00+00:00'
LOOKBACK = timedelta(minutes=5)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def read_json(key, default=None):
    try:
        return json.loads(S3.get_object(Bucket=BUCKET, Key=key)['Body'].read())
    except ClientError as exc:
        if exc.response['Error']['Code'] in ('NoSuchKey', '404'):
            return default
        raise


def put_json(key, value):
    S3.put_object(Bucket=BUCKET, Key=key, Body=encode(value), ContentType='application/json')


def lower_bound(watermark):
    return (datetime.fromisoformat(watermark) - LOOKBACK).isoformat()


def api_rows(since):
    page, seen = 1, set()
    while page is not None:
        if page in seen:
            raise RuntimeError('API pagination loop')
        seen.add(page)
        query = urlencode({'page': page, 'updated_since': since})
        with urlopen('http://source-api:8080/events?' + query, timeout=15) as response:
            payload = json.load(response)
        yield from payload['items']
        page = payload['next_page']


def store_rows(source, rows, pk, report):
    high = None
    summary = {'rows_read': 0, 'objects_created': 0, 'objects_reused': 0, 'object_keys': []}
    report['sources'][source] = summary
    for row in rows:
        summary['rows_read'] += 1
        updated = datetime.fromisoformat(row['updated_at'])
        if updated.tzinfo is None:
            raise ValueError('updated_at must contain a timezone')
        high = max(high, updated) if high else updated
        body = encode(row)
        digest = hashlib.sha256(body).hexdigest()
        # Each ID/content revision has exactly one immutable destination key.
        record_id = int(row[pk])
        key = f'raw/{source}/date={updated.date()}/id={record_id}/{digest}.json'
        try:
            S3.head_object(Bucket=BUCKET, Key=key)
            summary['objects_reused'] += 1
        except ClientError as exc:
            if exc.response['Error']['Code'] not in ('404', 'NoSuchKey', 'NotFound'):
                raise
            S3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType='application/json')
            summary['objects_created'] += 1
        summary['object_keys'].append(key)
    summary['upper_watermark'] = high.isoformat() if high else None
    return summary['upper_watermark']


def ingest(fail_after=None):
    run_id = str(uuid.uuid4())
    report = {'run_id': run_id, 'started_at': datetime.now(timezone.utc).isoformat(),
              'status': 'running', 'sources': {}}
    manifest_key = f'_metadata/m2/runs/{run_id}.json'
    with psycopg.connect('', autocommit=True) as conn:
        # One writer for checkpoint.json. Session lock released even on a crash.
        if not conn.execute('SELECT pg_try_advisory_lock(2027, 2)').fetchone()[0]:
            raise RuntimeError('Another M2 ingestion is running')
        state = read_json(STATE_KEY, {'watermarks': {}, 'files': {}})
        state = json.loads(json.dumps(state))
        try:
            S3.head_bucket(Bucket=BUCKET)
            put_json(manifest_key, report)
            with conn.transaction():
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                for table, pk in TABLES.items():
                    source = f'postgres/{table}'
                    previous = state['watermarks'].get(source, EPOCH)
                    since = lower_bound(previous)
                    records = conn.execute(sql.SQL('''SELECT to_jsonb(t) FROM shop.{} t
                        WHERE updated_at >= %s ORDER BY updated_at, {}''').format(
                            sql.Identifier(table), sql.Identifier(pk)), (since,)).fetchall()
                    high = store_rows(source, (r[0] for r in records), pk, report)
                    if high:
                        state['watermarks'][source] = max(datetime.fromisoformat(previous), datetime.fromisoformat(high)).isoformat()
                    report['sources'][source]['lower_bound'] = since
                    if fail_after == table:
                        raise RuntimeError(f'Injected failure after {table}')
            source = 'api/events'
            previous = state['watermarks'].get(source, EPOCH)
            since = lower_bound(previous)
            high = store_rows(source, api_rows(since), 'event_id', report)
            if high:
                state['watermarks'][source] = max(datetime.fromisoformat(previous), datetime.fromisoformat(high)).isoformat()
            report['sources'][source]['lower_bound'] = since
            path = Path('/app/fixtures/shipping.csv')
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if state['files'].get(path.name) == digest:
                report['sources']['file/shipping'] = {'file_unchanged': True, 'objects_created': 0}
            else:
                with io.StringIO(content.decode('utf-8'), newline='') as stream:
                    store_rows('file/shipping', csv.DictReader(stream), 'shipping_id', report)
                # Keep original file bytes as well as queryable JSON records.
                key = f'raw/file/original/{digest}/shipping.csv'
                S3.put_object(Bucket=BUCKET, Key=key, Body=content, ContentType='text/csv')
                state['files'][path.name] = digest
                report['sources']['file/shipping']['file_sha256'] = digest
                report['sources']['file/shipping']['original_key'] = key
            report.update(status='success', finished_at=datetime.now(timezone.utc).isoformat())
            state['last_run_id'] = run_id
            put_json(manifest_key, report)
            # Commit last: failed extraction/upload never advances a watermark.
            put_json(STATE_KEY, state)
        except Exception as exc:
            report.update(status='failed', error=type(exc).__name__, finished_at=datetime.now(timezone.utc).isoformat())
            put_json(manifest_key, report)
            raise
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fail-after', choices=list(TABLES))
    args = parser.parse_args()
    ingest(args.fail_after)


if __name__ == '__main__':
    main()
