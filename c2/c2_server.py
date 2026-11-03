#!/usr/bin/env python3
"""Stand-in for the attacker's exfil endpoint. Logs whatever the backdoored
agent sends it. Only used to prove reachability -- real attacker C2 is out of
scope and irrelevant to the containment demo."""
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="replace")
        print(f"[c2] received exfil payload: {body!r}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
