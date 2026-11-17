"""Integration demo: replays, one real source update, partial failure and recovery."""
import contextlib
import io
import json

import psycopg
import pipeline as p


def run(fail_after=None):
    with contextlib.redirect_stdout(io.StringIO()):
        return p.ingest(fail_after)


def raw_keys():
    pages = p.S3.get_paginator('list_objects_v2').paginate(Bucket=p.BUCKET, Prefix='raw/')
    return {item['Key'] for page in pages for item in page.get('Contents', [])}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def mutate(customer_id):
    with psycopg.connect('') as conn:
        row = conn.execute('''UPDATE shop.customers
            SET country_code = CASE WHEN country_code='FR' THEN 'BE' ELSE 'FR' END
            WHERE customer_id=%s RETURNING updated_at''', (customer_id,)).fetchone()
        require(row is not None, 'Demo customer missing')


def main():
    initial = run()
    for table, count in {'customers': 10, 'products': 5, 'orders': 20, 'order_items': 40, 'payments': 20}.items():
        # Raw contains history, so verify source cardinality separately.
        with psycopg.connect('') as conn:
            from psycopg import sql
            actual = conn.execute(sql.SQL('SELECT count(*) FROM shop.{}').format(sql.Identifier(table))).fetchone()[0]
        require(actual >= count, f'Missing seed rows: {table}')
    require(initial['sources']['api/events']['rows_read'] >= 2, 'API pagination/filter returned too few events')
    before = raw_keys()
    replay = run()
    require(raw_keys() == before, 'Replay created duplicate raw objects')
    require(sum(s['objects_created'] for s in replay['sources'].values()) == 0, 'Replay created new row versions')
    require(replay['sources']['file/shipping'].get('file_unchanged'), 'Unchanged CSV was not skipped')
    mutate(1)
    changed = run()
    require(changed['sources']['postgres/customers']['objects_created'] == 1, 'Customer change not ingested once')
    require(len(raw_keys() - before) == 1, 'Expected exactly one new raw revision')
    require(sum(s['objects_created'] for s in changed['sources'].values()) == 1, 'Unchanged sources created revisions')
    state_before_failure = p.read_json(p.STATE_KEY)
    mutate(2)
    try:
        run('orders')
        raise RuntimeError('Injected failure did not happen')
    except RuntimeError as exc:
        require(str(exc) == 'Injected failure after orders', 'Unexpected failure')
    require(p.read_json(p.STATE_KEY) == state_before_failure, 'Failed run advanced checkpoints')
    after_partial_failure = raw_keys()
    recovery = run()
    require(raw_keys() == after_partial_failure, 'Recovery duplicated partially uploaded data')
    require(recovery['sources']['postgres/customers']['objects_reused'] >= 1, 'Recovery did not reuse objects')
    require(p.read_json(p.STATE_KEY)['last_run_id'] == recovery['run_id'], 'Recovery checkpoint not committed')
    require(p.read_json(f"_metadata/m2/runs/{recovery['run_id']}.json")['status'] == 'success', 'Manifest missing')
    print(json.dumps({'result': 'PASS', 'raw_objects': len(raw_keys()),
        'replay_created': 0, 'single_customer_update_created': 1,
        'failure_checkpoint_unchanged': True, 'recovery_duplicates': 0,
        'last_successful_run': recovery['run_id']}, indent=2))


if __name__ == '__main__':
    main()
