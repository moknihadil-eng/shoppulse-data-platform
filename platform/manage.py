import argparse
import json
import sys
from datetime import date, timedelta

from dagster import DagsterInstance
import definitions


def execute(job, partition=None):
    with DagsterInstance.get() as instance:
        result = job.execute_in_process(instance=instance, partition_key=partition, raise_on_error=False)
        print(json.dumps({'job': job.name, 'run_id': result.run_id, 'success': result.success}))
        return result.success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run','backfill','retry-demo','quality-demo','verify','metabase','demo-order'])
    parser.add_argument('--start')
    parser.add_argument('--end')
    args = parser.parse_args()
    if args.command == 'run':
        if not execute(definitions.shoppulse_pipeline):
            sys.exit(1)
    elif args.command == 'backfill':
        start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        if end < start or start.isoformat() not in definitions.DATES or end.isoformat() not in definitions.DATES:
            parser.error('Select an inclusive range within January 2027')
        while start <= end:
            if not execute(definitions.backfill_sales, start.isoformat()):
                sys.exit(1)
            start += timedelta(days=1)
    elif args.command == 'retry-demo':
        if not execute(definitions.retry_demo):
            sys.exit(1)
    elif args.command == 'quality-demo':
        # Expected nonzero status, visible as FAILURE in Dagster.
        sys.exit(0 if execute(definitions.quality_failure_demo) else 1)
    elif args.command == 'verify':
        import verify
        verify.main()
    elif args.command == 'metabase':
        import metabase_setup
        metabase_setup.main()
    elif args.command == 'demo-order':
        import pipeline
        with pipeline.psycopg.connect('') as source:
            source.execute("""INSERT INTO shop.orders VALUES
                (9001,1,'paid','EUR','2027-01-03T12:00:00Z','2027-01-03T12:00:00Z')
                ON CONFLICT(order_id) DO NOTHING""")
            source.execute("""INSERT INTO shop.order_items VALUES
                (9001,9001,1,2,10,'2027-01-03T12:00:00Z','2027-01-03T12:00:00Z')
                ON CONFLICT(order_item_id) DO NOTHING""")
            source.execute("""INSERT INTO shop.payments VALUES
                (9001,9001,20,'succeeded','2027-01-03T12:00:00Z','2027-01-03T12:00:00Z')
                ON CONFLICT(payment_id) DO NOTHING""")
        if not execute(definitions.shoppulse_pipeline):
            sys.exit(1)
        import warehouse
        with warehouse.connect() as conn:
            if conn.execute('SELECT order_total FROM marts.fact_orders WHERE order_id=9001').fetchone() != (20,):
                raise RuntimeError('New order not propagated to warehouse')
        print('Demo order 9001 propagated; safe to rerun without adding a second order.')


if __name__ == '__main__':
    main()
