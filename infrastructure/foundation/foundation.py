"""M1 bootstrap and integration checks. Never ingest business data into raw here."""
import hashlib
import json
import os
import sys
from pathlib import Path

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg import sql

TABLES = {'customers': 10, 'products': 5, 'orders': 20, 'order_items': 40, 'payments': 20}
BUCKET = os.environ['RAW_BUCKET']
S3 = boto3.client('s3', endpoint_url='http://minio:9000', region_name='us-east-1')
REPORT = Path('/reports/m1-before.json')
KEY = '_m1/persistence.txt'
BODY = b'ShopPulse M1 persistence probe v1\n'


def seed(conn):
    conn.execute(Path('/sql/01-foundation.sql').read_text(encoding='utf-8'))


def snapshot(conn):
    result = {}
    for table, expected in TABLES.items():
        rows = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM shop.{} t ORDER BY 1').format(sql.Identifier(table))).fetchall()
        if len(rows) < expected:
            raise RuntimeError(f'{table}: expected at least the {expected} seed rows, got {len(rows)}')
        result[table] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(r[0] for r in rows).encode()).hexdigest()}
    mismatch = conn.execute('''SELECT count(*) FROM shop.payments p JOIN
        (SELECT order_id, sum(quantity*unit_price) total FROM shop.order_items GROUP BY order_id) i
        USING(order_id) WHERE p.amount <> i.total''').fetchone()[0]
    if mismatch:
        raise RuntimeError('Payment amounts differ from order totals')
    S3.head_bucket(Bucket=BUCKET)
    return result


def main():
    mode = sys.argv[1]
    with psycopg.connect('', autocommit=True) as conn:
        if mode == 'init':
            seed(conn)
            try:
                S3.head_bucket(Bucket=BUCKET)
            except ClientError as exc:
                if exc.response['Error']['Code'] not in ('404', 'NoSuchBucket', 'NotFound'):
                    raise
                S3.create_bucket(Bucket=BUCKET)
            print(f'Bootstrap OK; bucket {BUCKET} exists')
        elif mode == 'before':
            before = snapshot(conn)
            seed(conn)
            seed(conn)
            if snapshot(conn) != before:
                raise RuntimeError('Seed replay changed data')
            S3.put_object(Bucket=BUCKET, Key=KEY, Body=BODY)
            REPORT.write_text(json.dumps(before, indent=2), encoding='utf-8')
            print(json.dumps(before, indent=2))
            print('Seed replay twice: identical data; persistence probe written')
        elif mode == 'after':
            after = snapshot(conn)
            if after != json.loads(REPORT.read_text(encoding='utf-8')):
                raise RuntimeError('Data changed after container recreation')
            if S3.get_object(Bucket=BUCKET, Key=KEY)['Body'].read() != BODY:
                raise RuntimeError('MinIO probe changed')
            print(f"PASS: orders={after['orders']['count']}; bucket={BUCKET}; all five tables identical; MinIO object retained")
        elif mode == 'check':
            print(json.dumps(snapshot(conn), indent=2))
            print(f'Bucket {BUCKET}: accessible')
        else:
            raise ValueError(f'Unknown mode: {mode}')


if __name__ == '__main__':
    main()
