"""Synthetic source API: pagination and updated_since filter; standard library only."""
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/health':
            payload = {'status': 'ok'}
        elif parsed.path == '/events':
            args = parse_qs(parsed.query)
            try:
                page = int(args.get('page', ['1'])[0])
                since = datetime.fromisoformat(args.get('updated_since', ['1970-01-01T00:00:00+00:00'])[0])
                if page < 1 or since.tzinfo is None:
                    raise ValueError('Invalid query')
            except ValueError:
                self.send_error(400)
                return
            rows = json.loads(Path('/app/fixtures/events.json').read_text())
            rows = [r for r in rows if datetime.fromisoformat(r['updated_at']) >= since]
            rows.sort(key=lambda r: (r['updated_at'], r['event_id']))
            start = (page - 1) * 2
            payload = {'items': rows[start:start + 2], 'next_page': page + 1 if start + 2 < len(rows) else None}
        else:
            self.send_error(404)
            return
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
