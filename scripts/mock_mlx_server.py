#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


TOPIC_RESPONSE = "1. Why emotional distance feels addictive"
HOOK_RESPONSE = "1. The subtle shift that makes them pull away"


class Handler(BaseHTTPRequestHandler):
    server_version = "MockMLX/1.0"

    def _write(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write(200, {"ok": True})
            return
        self._write(404, {"ok": False})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._write(404, {"ok": False})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        system_text = " ".join(
            str(message.get("content", ""))
            for message in payload.get("messages", [])
            if message.get("role") == "system"
        ).lower()
        if "content strategist" in system_text:
            content = TOPIC_RESPONSE
        elif "short-form hooks" in system_text:
            content = HOOK_RESPONSE
        else:
            content = ""
        self._write(
            200,
            {
                "id": "mock-chatcmpl",
                "object": "chat.completion",
                "created": 0,
                "model": payload.get("model", "mock"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content,
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Mock MLX listening on http://127.0.0.1:8000", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
