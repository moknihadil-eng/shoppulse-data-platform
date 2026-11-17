"""Small read-only M2 summary for PowerShell and interviews."""
import json
from collections import Counter

import pipeline as p

counts = Counter()
for page in p.S3.get_paginator('list_objects_v2').paginate(Bucket=p.BUCKET, Prefix='raw/'):
    for item in page.get('Contents', []):
        counts['/'.join(item['Key'].split('/')[:3])] += 1
state = p.read_json(p.STATE_KEY, {})
last_run = state.get('last_run_id')
manifest = p.read_json(f'_metadata/m2/runs/{last_run}.json', {}) if last_run else {}
print(json.dumps({'bucket': p.BUCKET, 'raw_objects_by_source': dict(counts),
    'last_run_id': last_run, 'status': manifest.get('status'),
    'watermarks': state.get('watermarks', {}),
    'last_run_objects_created': sum(s['objects_created'] for s in manifest.get('sources', {}).values())}, indent=2))
