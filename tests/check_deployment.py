"""Exercise the real queued Dagster launcher, not execute_in_process in the CLI."""
import json
import time
from pathlib import Path
from urllib.request import urlopen

from dagster_graphql import DagsterGraphQLClient

client = DagsterGraphQLClient('dagster', port_number=3000, timeout=30)
run_id = client.submit_job_execution('shoppulse_pipeline', run_config={})
print(f'Queued run: {run_id}', flush=True)
deadline = time.monotonic() + 300
observed = []
while time.monotonic() < deadline:
    status = client.get_run_status(run_id).value
    if not observed or observed[-1] != status:
        observed.append(status)
        print(status, flush=True)
    if status == 'SUCCESS':
        break
    if status in ('FAILURE', 'CANCELED'):
        raise RuntimeError(f'Queued Dagster run {run_id}: {status}')
    time.sleep(2)
else:
    raise TimeoutError(f'Queued Dagster run {run_id} exceeded five minutes')
for endpoint in ('http://metabase:3000/api/health', 'http://minio:9000/minio/health/ready',
                 'http://dbt-docs:8080/index.html'):
    with urlopen(endpoint, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f'Endpoint unhealthy: {endpoint}')
        response.read(1024)
report = {'status':'PASS', 'queued_run_id':run_id, 'observed_states':observed,
          'interfaces_checked':['metabase','minio','dbt-docs']}
Path('/reports/deployment.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
