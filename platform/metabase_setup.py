"""Idempotent local dashboard setup using the Metabase HTTP API."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

BASE = 'http://metabase:3000/api'
TOKEN = None


def request(method, path, payload=None):
    headers = {'Content-Type': 'application/json'}
    if TOKEN:
        headers['X-Metabase-Session'] = TOKEN
    req = Request(BASE + path, data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers, method=method)
    with urlopen(req, timeout=120) as response:
        body = response.read()
        return json.loads(body) if body else None


def main():
    global TOKEN
    properties = request('GET','/session/properties')
    email = os.environ['METABASE_ADMIN_EMAIL']
    password = os.environ['METABASE_ADMIN_PASSWORD']
    if properties.get('setup-token'):
        request('POST','/setup', {'token': properties['setup-token'],
            'user': {'first_name':'ShopPulse','last_name':'Demo','email':email,'password':password},
            'prefs': {'site_name':'ShopPulse Portfolio','allow_tracking':False}})
    TOKEN = request('POST','/session', {'username':email,'password':password})['id']
    try:
        dbs = request('GET','/database')['data']
        database = next((d for d in dbs if d['name']=='ShopPulse Warehouse'), None)
        if not database:
            database = request('POST','/database', {'name':'ShopPulse Warehouse','engine':'postgres',
                'details': {'host':'warehouse','port':5432,'dbname':os.environ['WAREHOUSE_DB'],
                    'user':'metabase_reader','password':os.environ['METABASE_READ_PASSWORD'], 'ssl':False}})
        found = request('GET','/dashboard')
        dashboards = found.get('data', []) if isinstance(found,dict) else found
        dashboard = next((d for d in dashboards if d['name']=='ShopPulse - Overview'),None)
        if not dashboard:
            dashboard = request('POST','/dashboard', {'name':'ShopPulse - Overview',
                'description':'Synthetic e-commerce: orders, paid revenue, products and customer features.'})
        existing = request('GET',f"/dashboard/{dashboard['id']}")
        if not existing.get('dashcards'):
            cards = []
            for n, definition in enumerate(json.loads(Path('/app/dashboards/cards.json').read_text())):
                card = request('POST','/card', {'name':definition['name'],'display':definition['display'],
                    'dataset_query': {'type':'native','database':database['id'],
                        'native': {'query':definition['sql'],'template-tags':{}}},
                    'visualization_settings':{}})
                cards.append({'id':-(n+1),'card_id':card['id'],'row':(n//2)*5,'col':(n%2)*12,
                    'size_x':12,'size_y':5,'parameter_mappings':[]})
            request('PUT',f"/dashboard/{dashboard['id']}", {'dashcards':cards})
        # Execute every dashboard question, not merely create its metadata.
        current = request('GET',f"/dashboard/{dashboard['id']}")
        checked = 0
        for dashcard in current.get('dashcards', []):
            card_id = dashcard.get('card_id')
            if card_id:
                result = request('POST',f'/card/{card_id}/query', {})
                if result.get('status') != 'completed':
                    raise RuntimeError(f'Dashboard card {card_id} did not complete')
                checked += 1
        if checked != 6:
            raise RuntimeError(f'Expected six cards, found {checked}')
        report = {'dashboard_id':dashboard['id'], 'cards_verified':checked,
            'url':f"http://localhost:{os.environ.get('METABASE_PORT','3001')}/dashboard/{dashboard['id']}"}
        Path('/reports/metabase.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
    finally:
        request('DELETE','/session', {'metabase-session-id':TOKEN})


if __name__ == '__main__':
    main()
