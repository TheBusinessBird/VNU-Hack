"""python serve_site.py [port]  ->  site static pe http://127.0.0.1:8080 (doar biblioteca standard Python, fără Node)."""
import http.server, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")        # modificările apar imediat, fără cache vechi în browser
        super().end_headers()

    def log_message(self, *args):
        pass

    def guess_type(self, path):
        t = super().guess_type(path)
        return t + "; charset=utf-8" if t.startswith(("text/", "application/javascript")) and "charset" not in t else t


if __name__ == "__main__":
    print(f"Site pe http://127.0.0.1:{PORT}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
