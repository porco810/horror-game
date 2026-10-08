"""Serve the preview and pinned Three.js locally, without a browser CDN dependency."""
import http.server
import os
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
THREE=ROOT/'node_modules/three'
PORT=int(os.environ.get('KUCHI_PREVIEW_PORT','8765'))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(WEB),**kwargs)
    def translate_path(self,path):
        path=unquote(urlsplit(path).path)
        if path.startswith('/vendor/three/'):
            target=(THREE/path[len('/vendor/three/'):]).resolve()
            return str(target) if target.is_relative_to(THREE.resolve()) else str(WEB/'__not_found__')
        return super().translate_path(path)
    def end_headers(self):
        self.send_header('Cache-Control','no-store');super().end_headers()

if __name__=='__main__':
    if not (THREE/'build/three.module.js').is_file():
        raise SystemExit('Three.js is missing. Run npm ci in the repository first.')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    print(f'[KUCHI PREVIEW] pid={os.getpid()} port={PORT}; local Three.js; root={WEB}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('[KUCHI PREVIEW] stopped',flush=True)
    finally:
        server.server_close()
