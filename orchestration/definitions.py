import contextlib
import io
import json
from datetime import date, timedelta

from dagster import (Backoff, DefaultScheduleStatus, Definitions, Failure, RetryPolicy,
    ScheduleDefinition, StaticPartitionsDefinition, in_process_executor, job, op, resource)
import pipeline
import tasks
import warehouse

RETRY = RetryPolicy(max_retries=2, delay=3, backoff=Backoff.EXPONENTIAL)


@resource
def warehouse_lock(_):
    # Shared by every step for the life of an in-process job, including manual runs.
    with warehouse.connect() as conn:
        conn.execute("SET statement_timeout = '300s'")
        conn.execute('SELECT pg_advisory_lock(2027,3)')
        yield conn


@op(retry_policy=RETRY, required_resource_keys={'warehouse_lock'})
def ingest_sources(context):
    with contextlib.redirect_stdout(io.StringIO()):
        report = pipeline.ingest()
    context.log.info(f"Ingestion {report['run_id']}: success")
    return report['run_id']


@op(retry_policy=RETRY, required_resource_keys={'warehouse_lock'})
def load_raw(context, ingestion_run):
    result = warehouse.load_bronze()
    context.log.info(json.dumps(result))
    return ingestion_run


@op(retry_policy=RETRY, required_resource_keys={'warehouse_lock'})
def freshness_gate(context, run_id):
    tasks.dbt('source', 'freshness', report_name='freshness')
    return run_id


@op(retry_policy=RETRY, required_resource_keys={'warehouse_lock'})
def transform_and_test(context, run_id):
    tasks.dbt('build', report_name='build')
    return run_id


@op(required_resource_keys={'warehouse_lock'})
def publish(context, run_id):
    report = tasks.quality_report()
    warehouse.grant_readonly()
    tasks.dbt('docs', 'generate', report_name='docs')
    with warehouse.connect() as conn:
        with conn.cursor().copy('COPY (SELECT * FROM marts.customer_features ORDER BY customer_id) TO STDOUT CSV HEADER') as export:
            with (tasks.REPORTS/'customer_features.csv').open('wb') as stream:
                for chunk in export:
                    stream.write(chunk)
    pipeline.put_json(f'_metadata/platform/quality/{context.run_id}.json', report)
    warehouse.record_run(context.run_id, 'success', {'ingestion_run_id': run_id, 'quality': report})
    context.log.info(json.dumps(report))


@job(executor_def=in_process_executor, resource_defs={'warehouse_lock':warehouse_lock})
def shoppulse_pipeline():
    publish(transform_and_test(freshness_gate(load_raw(ingest_sources()))))


DATES = [(date(2027,1,1)+timedelta(days=n)).isoformat() for n in range(31)]


@op(retry_policy=RETRY, required_resource_keys={'warehouse_lock'})
def replay_day(context):
    warehouse.load_bronze()
    tasks.dbt('run', '--select', 'daily_sales', '--vars', json.dumps({'backfill_date': context.partition_key}),
        report_name=f'backfill-{context.partition_key}')
    tasks.dbt('test', '--select', 'daily_sales')


@job(partitions_def=StaticPartitionsDefinition(DATES), executor_def=in_process_executor,
     resource_defs={'warehouse_lock':warehouse_lock})
def backfill_sales():
    replay_day()


@op(retry_policy=RetryPolicy(max_retries=1, delay=1))
def transient_failure(context):
    if context.retry_number == 0:
        raise RuntimeError('Intentional transient error for retry demonstration')
    context.log.info('Retry recovered successfully')


@job
def retry_demo():
    transient_failure()


@op(required_resource_keys={'warehouse_lock'})
def reject_bad_record(context):
    from psycopg.types.json import Jsonb
    key = '_quality_demo/negative_payment'
    with warehouse.connect() as conn:
        conn.execute('''INSERT INTO bronze.raw_records(object_key,source_name,payload,source_updated_at)
            VALUES(%s,'postgres/payments',%s,'2027-01-04T00:00:00Z') ON CONFLICT DO NOTHING''',
            (key, Jsonb({'payment_id':9999,'order_id':9999,'amount':-5,'status':'succeeded',
                'created_at':'2027-01-04T00:00:00Z','updated_at':'2027-01-04T00:00:00Z'})))
    try:
        tasks.dbt('build', '--select', 'stg_payments', report_name='quality-rejected', expect_failure=True)
        result = json.loads((tasks.REPORTS/'quality-rejected-run_results.json').read_text())
        if not any(r['status']=='fail' and 'positive_payments' in r['unique_id'] for r in result['results']):
            raise RuntimeError('Expected positive_payments test did not fail')
    finally:
        with warehouse.connect() as conn:
            conn.execute('DELETE FROM bronze.raw_records WHERE object_key=%s', (key,))
    # Staging is a view, so cleanup immediately restores the healthy data view.
    raise Failure('Expected demo failure: negative payment rejected; bad bronze row removed')


@job(executor_def=in_process_executor, resource_defs={'warehouse_lock':warehouse_lock})
def quality_failure_demo():
    reject_bad_record()


hourly = ScheduleDefinition(job=shoppulse_pipeline, cron_schedule='0 * * * *', execution_timezone='UTC',
    default_status=DefaultScheduleStatus.RUNNING)
defs = Definitions(jobs=[shoppulse_pipeline, backfill_sales, retry_demo, quality_failure_demo], schedules=[hourly])
