"""End-to-end integration checks; uses synthetic customers only."""
import json
from datetime import timedelta
from decimal import Decimal

from dagster import DagsterInstance
import definitions
import pipeline
import tasks
import warehouse


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(job, partition=None, expected=True):
    with DagsterInstance.get() as instance:
        result = job.execute_in_process(instance=instance, partition_key=partition, raise_on_error=False)
        require(result.success == expected, f'Unexpected status: {job.name}')
        retry_events = sum(bool(e.dagster_event and e.dagster_event.event_type_value=='STEP_UP_FOR_RETRY')
            for e in instance.all_logs(result.run_id))
        return {'job':job.name, 'run_id':result.run_id, 'success':result.success,'retry_events':retry_events}


def sales():
    with warehouse.connect() as conn:
        return conn.execute('SELECT to_jsonb(t) FROM marts.daily_sales t ORDER BY sales_date').fetchall()


def main():
    outcomes = []
    with warehouse.connect() as conn:
        counts = {table: conn.execute(f'SELECT count(*) FROM marts.{table}').fetchone()[0]
            for table in ('fact_orders','fact_payments','fact_order_items','customer_features','dim_customer')}
        current = conn.execute('SELECT count(*) FROM marts.dim_customer WHERE is_current').fetchone()[0]
        revenue = conn.execute("SELECT sum(amount) FROM marts.fact_payments WHERE status='succeeded'").fetchone()[0]
        before_scd = conn.execute('SELECT count(*) FROM marts.dim_customer WHERE customer_id=1').fetchone()[0]
    with pipeline.psycopg.connect('') as source:
        expected_revenue = source.execute("SELECT sum(amount) FROM shop.payments WHERE status='succeeded'").fetchone()[0]
        expected_orders = source.execute('SELECT count(*) FROM shop.orders').fetchone()[0]
        expected_payments = source.execute('SELECT count(*) FROM shop.payments').fetchone()[0]
        expected_items = source.execute('SELECT count(*) FROM shop.order_items').fetchone()[0]
        expected_customers = source.execute('SELECT count(*) FROM shop.customers').fetchone()[0]
    require(counts['fact_orders']==expected_orders and counts['fact_payments']==expected_payments and
        counts['fact_order_items']==expected_items and counts['customer_features']==expected_customers,
        'Source/warehouse cardinalities differ')
    require(current==expected_customers and counts['dim_customer']>current, 'SCD history/current versions missing')
    require(revenue==expected_revenue, 'Source/warehouse paid revenue mismatch')
    initial_sales = sales()
    outcomes.append(run(definitions.shoppulse_pipeline))
    require(sales()==initial_sales, 'Replay changed daily sales')
    with pipeline.psycopg.connect('') as source:
        source.execute("UPDATE shop.customers SET country_code=CASE WHEN country_code='FR' THEN 'BE' ELSE 'FR' END WHERE customer_id=1")
    outcomes.append(run(definitions.shoppulse_pipeline))
    with warehouse.connect() as conn:
        after_scd = conn.execute('SELECT count(*) FROM marts.dim_customer WHERE customer_id=1').fetchone()[0]
        require(after_scd==before_scd+1, 'SCD2 did not append exactly one customer revision')
    for day in ('2027-01-02','2027-01-03'):
        outcomes.append(run(definitions.backfill_sales, day))
    require(sales()==initial_sales, 'Backfill changed already correct aggregates')
    retry = run(definitions.retry_demo)
    require(retry['retry_events']==1, 'Transient failure was not retried exactly once')
    outcomes.append(retry)
    outcomes.append(run(definitions.quality_failure_demo, expected=False))
    with warehouse.connect() as conn:
        require(conn.execute("SELECT count(*) FROM bronze.raw_records WHERE object_key LIKE '_quality_demo/%'").fetchone()[0]==0,
            'Invalid demo row was not cleaned')
        clocks = conn.execute('SELECT source_name,checked_at FROM bronze.ingestion_clock').fetchall()
        conn.execute("UPDATE bronze.ingestion_clock SET checked_at=now()-interval '48 hours'")
    try:
        tasks.dbt('source','freshness', report_name='stale-rejected', expect_failure=True)
        stale = json.loads((tasks.REPORTS/'stale-rejected-sources.json').read_text())
        require(any(r['status']=='error' for r in stale['results']), 'Stale source not detected')
    finally:
        with warehouse.connect() as conn:
            for source, checked in clocks:
                conn.execute('UPDATE bronze.ingestion_clock SET checked_at=%s WHERE source_name=%s',(checked,source))
    outcomes.append(run(definitions.shoppulse_pipeline))
    with warehouse.connect() as conn:
        counts['dim_customer'] = conn.execute('SELECT count(*) FROM marts.dim_customer').fetchone()[0]
    import os
    with pipeline.psycopg.connect(host='warehouse',dbname=os.environ['WAREHOUSE_DB'],user='metabase_reader',
            password=os.environ['METABASE_READ_PASSWORD']) as reader:
        require(reader.execute('SELECT count(*) FROM marts.fact_orders').fetchone()[0]==expected_orders, 'Reader cannot query marts')
        writable = reader.execute("SELECT has_table_privilege(current_user,'marts.fact_orders','INSERT')").fetchone()[0]
        require(not writable, 'BI role has write permission')
    report = {'status':'PASS','counts':counts,'paid_revenue_eur':str(revenue),
        'scd2_new_version':1,'replay_identical':True,'backfill_identical':True,
        'invalid_record_rejected':True,'stale_source_rejected':True,'bi_readonly':True,'runs':outcomes}
    (tasks.REPORTS/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
