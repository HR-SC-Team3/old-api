"""
Serve api-doc.yml as a browsable Swagger UI page, with live reload.

Usage:
    python scripts/serve_docs.py [--port 3001]

The page polls the server for the file's last-modified time and reloads
itself automatically whenever api-doc.yml changes on disk, so you can
edit the spec and see the rendered docs update without restarting
anything. Swagger UI itself is loaded from a CDN; no extra Python
dependencies are required beyond the standard library.
"""

import argparse
import http.server
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(ROOT_DIR, "api-doc.yml")

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>CargoHUB API docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>body { margin: 0; }</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/api-doc.yml",
      dom_id: "#swagger-ui",
    });

    (function pollForChanges() {
      var lastModified = null;
      setInterval(function () {
        fetch("/__last-modified")
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (lastModified === null) {
              lastModified = data.mtime;
            } else if (data.mtime !== lastModified) {
              location.reload();
            }
          })
          .catch(function () {});
      }, 1000);
    })();
  </script>
</body>
</html>
"""


class DocsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send(200, "text/html; charset=utf-8", INDEX_HTML.encode("utf-8"))
        elif self.path == "/api-doc.yml":
            with open(SPEC_PATH, "rb") as f:
                body = f.read()
            self._send(200, "application/yaml; charset=utf-8", body)
        elif self.path == "/__last-modified":
            mtime = os.path.getmtime(SPEC_PATH)
            self._send(
                200, "application/json", json.dumps({"mtime": mtime}).encode("utf-8")
            )
        else:
            self.send_error(404)

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()

    server = http.server.ThreadingHTTPServer(("localhost", args.port), DocsHandler)
    print(f"Serving api-doc.yml docs at http://localhost:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
