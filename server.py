#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo-track — 自托管定位后端（OwnTracks 兼容） / self-hosted location backend
手机(OwnTracks HTTP 模式)把位置上报到你自己的服务器；数据只存本地文件，
后端不向任何第三方发一个请求。

- 只绑 127.0.0.1，公网入口交给隧道/反代（Cloudflare Tunnel / Caddy / nginx）
- 鉴权双通道：URL ?token= 或 Basic-Auth 密码，任一命中即放行（常量时间比较）
- 首次启动自动生成钥匙 data/token.txt (0600)
"""
import os, json, time, hmac, base64, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TOKEN_FILE = os.path.join(DATA, "token.txt")
LATEST = os.path.join(DATA, "latest.json")
HISTORY = os.path.join(DATA, "history.jsonl")
HOST, PORT = "127.0.0.1", 8098

os.makedirs(DATA, exist_ok=True)


def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            t = f.read().strip()
            if t:
                return t
    t = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
    with open(TOKEN_FILE, "w") as f:
        f.write(t + "\n")
    os.chmod(TOKEN_FILE, 0o600)
    return t


TOKEN = load_token()
_lock = threading.Lock()


def ok_token(cand):
    return bool(cand) and hmac.compare_digest(str(cand), TOKEN)


def extract_tokens(handler):
    """收集所有 token 候选：Basic-Auth 密码 + ?token=，任一命中即放行。"""
    out = []
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            raw = base64.b64decode(auth[6:]).decode("utf-8", "replace")
            if ":" in raw:
                out.append(raw.split(":", 1)[1].strip())
        except Exception:
            pass
    q = parse_qs(urlparse(handler.path).query)
    if "token" in q:
        out.append(q["token"][0].strip())
    return out


def any_ok(cands):
    return any(ok_token(c) for c in cands)


class H(BaseHTTPRequestHandler):
    server_version = "geo-track/1.0"

    def log_message(self, *a):
        pass  # 不把 token/坐标写进 stderr 日志

    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/pub", "/"):
            return self._send(404, b'{"error":"not found"}')
        if not any_ok(extract_tokens(self)):
            return self._send(401, b'{"error":"unauthorized"}')
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 262144:  # 256KB 封顶，定位包只有几百字节
                return self._send(413, b'{"error":"too large"}')
            raw = self.rfile.read(n) if n else b""
            payload = json.loads(raw.decode("utf-8", "replace")) if raw else {}
        except Exception:
            return self._send(400, b'{"error":"bad json"}')

        rec = payload if isinstance(payload, dict) else {}
        rec.setdefault("_recv", int(time.time()))
        with _lock:
            with open(HISTORY, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec.get("_type") == "location" and "lat" in rec and "lon" in rec:
                with open(LATEST, "w") as f:
                    json.dump(rec, f, ensure_ascii=False)
        # OwnTracks 期待返回一个数组（friends/cards）；空数组即可
        return self._send(200, b"[]")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, b'{"ok":true}')
        if path == "/latest":
            if not any_ok(extract_tokens(self)):
                return self._send(401, b'{"error":"unauthorized"}')
            if os.path.exists(LATEST):
                with open(LATEST, "rb") as f:
                    return self._send(200, f.read())
            return self._send(404, b'{"error":"no fix yet"}')
        return self._send(404, b'{"error":"not found"}')


if __name__ == "__main__":
    print(f"geo-track on http://{HOST}:{PORT}  (token in {TOKEN_FILE})")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
