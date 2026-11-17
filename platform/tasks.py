import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPORTS = Path('/reports')
PROJECT = Path('/app/dbt')


def dbt(*args, report_name=None, expect_failure=False):
    REPORTS.mkdir(exist_ok=True, parents=True)
    command = ['dbt', '--no-use-colors', *args, '--project-dir', str(PROJECT), '--profiles-dir', str(PROJECT)]
    result = subprocess.run(command, text=True, capture_output=True, timeout=600)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if report_name:
        for filename in ('run_results.json', 'sources.json', 'manifest.json', 'catalog.json'):
            source = PROJECT / 'target' / filename
            if source.exists():
                shutil.copyfile(source, REPORTS / f'{report_name}-{filename}')
        (REPORTS / f'{report_name}.log').write_text(result.stdout + result.stderr)
    if args[:2] == ('docs', 'generate') and result.returncode == 0:
        destination = REPORTS/'dbt-docs'
        destination.mkdir(exist_ok=True)
        for filename in ('index.html','manifest.json','catalog.json'):
            shutil.copyfile(PROJECT/'target'/filename, destination/filename)
    if expect_failure:
        if result.returncode == 0:
            raise RuntimeError('Bad record was not rejected')
    elif result.returncode != 0:
        raise RuntimeError(f'dbt {args[0]} failed with exit code {result.returncode}; see /reports')
    return result


def quality_report():
    results = json.loads((PROJECT / 'target/run_results.json').read_text())
    sources = json.loads((PROJECT / 'target/sources.json').read_text())
    tests = [r for r in results['results'] if r['unique_id'].startswith('test.')]
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
        'tests_total': len(tests), 'tests_passed': sum(r['status']=='pass' for r in tests),
        'test_failures': [r['unique_id'] for r in tests if r['status'] != 'pass'],
        'freshness': [{'source': r['unique_id'], 'status': r['status']} for r in sources['results']]}
    report['status'] = 'success' if not report['test_failures'] and all(
        r['status']=='pass' for r in report['freshness']) else 'failed'
    (REPORTS/'quality-report.json').write_text(json.dumps(report, indent=2))
    if report['status'] != 'success':
        raise RuntimeError('Quality gate failed')
    return report
