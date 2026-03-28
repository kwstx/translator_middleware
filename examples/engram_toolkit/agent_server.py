from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class AgentHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/tools/echo":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        self._send_json(200, {"echo": data})


def main() -> None:
    server = HTTPServer(("0.0.0.0", 8080), AgentHandler)
    print("Agent health server running on http://localhost:8080")
    print("Health endpoint: http://localhost:8080/health")
    server.serve_forever()


if __name__ == "__main__":
    main()

