#!/usr/bin/env python3
"""Blind ranking server (standard library only, 127.0.0.1 only).

Usage: python3 rank_server.py <screens folder> <out folder> [--port 8765]

The screens folder holds one subfolder per screen with a screen.json:
  {"id": "s01", "task": "page", "brief_title": "...",
   "items": [{"label": "A", "kind": "html"|"text", "path": "...", "strip": "..."}]}
Paths are relative to the screen's own folder (absolute paths also work). For kind html, `path` is the
run's index.html; its folder is served read-only. For kind text, `path` is a markdown file shown as plain text.
Each save writes <out>/<screen id>.json.
"""
import argparse
import datetime
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
LABEL_RE = re.compile(r"^[A-Z]$")


class Store:
    def __init__(self, screens_dir, out_dir):
        self.screens_dir = os.path.realpath(screens_dir)
        self.out_dir = os.path.abspath(out_dir)
        os.makedirs(self.out_dir, exist_ok=True)
        self.screens = {}
        for name in sorted(os.listdir(self.screens_dir)):
            p = os.path.join(self.screens_dir, name, "screen.json")
            if not os.path.isfile(p):
                continue
            s = json.load(open(p, encoding="utf-8"))
            sid = str(s["id"])
            if not ID_RE.match(sid):
                raise SystemExit(f"bad screen id {sid!r}")
            base = os.path.join(self.screens_dir, name)
            items = {}
            for it in s["items"]:
                if not LABEL_RE.match(it["label"]):
                    raise SystemExit(f"bad label in {sid}")
                items[it["label"]] = {
                    "kind": it["kind"],
                    "path": os.path.realpath(os.path.join(base, it["path"])),
                    "strip": os.path.realpath(os.path.join(base, it["strip"])) if it.get("strip") else None,
                }
            self.screens[sid] = {"id": sid, "task": s.get("task", ""), "brief_title": s.get("brief_title", ""), "items": items}

    def saved(self, sid):
        p = os.path.join(self.out_dir, f"{sid}.json")
        if os.path.isfile(p):
            return json.load(open(p, encoding="utf-8"))
        return None

    def listing(self):
        return [{"id": s["id"], "task": s["task"], "brief_title": s["brief_title"], "done": self.saved(s["id"]) is not None}
                for s in self.screens.values()]

    def detail(self, sid):
        s = self.screens[sid]
        items = []
        for label in sorted(s["items"]):
            it = s["items"][label]
            d = {"label": label, "kind": it["kind"]}
            if it["strip"]:
                d["strip_url"] = f"/strip/{sid}/{label}"
            if it["kind"] == "html":
                d["open_url"] = f"/run/{sid}/{label}/" + os.path.basename(it["path"])
            else:
                with open(it["path"], encoding="utf-8", errors="replace") as f:
                    d["text"] = f.read()
            items.append(d)
        return {"id": sid, "task": s["task"], "brief_title": s["brief_title"], "items": items, "saved": self.saved(sid)}

    def save(self, sid, body):
        s = self.screens[sid]
        ranks = body.get("ranks")
        if not isinstance(ranks, dict) or set(ranks) != set(s["items"]):
            raise ValueError("ranks must have exactly the labels " + ",".join(sorted(s["items"])))
        clean = {}
        for k, v in ranks.items():
            if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5:
                raise ValueError("each rank must be an integer 1 to 5")
            clean[k] = v
        notes = body.get("notes", {})
        if not isinstance(notes, dict):
            raise ValueError("notes must be an object")
        clean_notes = {k: str(v)[:500] for k, v in notes.items() if k in s["items"] and str(v).strip()}
        use = body.get("use", {})
        if not isinstance(use, dict) or any(v not in ("yes", "fix", "no") for v in use.values()):
            raise ValueError("use must map labels to yes, fix or no")
        rec = {"id": sid, "ranks": dict(sorted(clean.items())), "notes": clean_notes,
               "use": {k: v for k, v in sorted(use.items()) if k in s["items"]},
               "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        tmp = os.path.join(self.out_dir, f".{sid}.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
        os.replace(tmp, os.path.join(self.out_dir, f"{sid}.json"))
        return rec


def make_handler(store, port):
    page = open(os.path.join(HERE, "rank.html"), "rb").read()
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        server_version = "rank"

        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def host_ok(self):
            if self.headers.get("Host", "") not in allowed_hosts:
                self.send(403, {"error": "bad host"})
                return False
            return True

        def send_file(self, path, root):
            real = os.path.realpath(path)
            if not (real == root or real.startswith(root + os.sep)) or not os.path.isfile(real):
                return self.send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(real)[0] or "application/octet-stream"
            if real.endswith((".js", ".mjs")):
                ctype = "text/javascript"
            with open(real, "rb") as f:
                data = f.read()
            self.send(200, data, ctype)

        def do_GET(self):
            if not self.host_ok():
                return
            path = unquote(urlparse(self.path).path)
            parts = [p for p in path.split("/") if p]
            try:
                if path == "/":
                    return self.send(200, page, "text/html; charset=utf-8")
                if path == "/api/screens":
                    return self.send(200, store.listing())
                if len(parts) == 3 and parts[:2] == ["api", "screen"] and parts[2] in store.screens:
                    return self.send(200, store.detail(parts[2]))
                if len(parts) == 3 and parts[0] == "strip" and parts[1] in store.screens:
                    it = store.screens[parts[1]]["items"].get(parts[2])
                    if it and it["strip"]:
                        return self.send_file(it["strip"], os.path.dirname(it["strip"]))
                if len(parts) >= 4 and parts[0] == "run" and parts[1] in store.screens:
                    it = store.screens[parts[1]]["items"].get(parts[2])
                    if it and it["kind"] == "html":
                        root = os.path.dirname(it["path"])
                        return self.send_file(os.path.join(root, *parts[3:]), root)
            except Exception as e:  # keep the server alive
                return self.send(500, {"error": str(e)})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.host_ok():
                return
            parts = [p for p in unquote(urlparse(self.path).path).split("/") if p]
            if len(parts) == 3 and parts[:2] == ["api", "save"] and parts[2] in store.screens:
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    if n > 100000:
                        raise ValueError("body too large")
                    body = json.loads(self.rfile.read(n) or b"{}")
                    return self.send(200, store.save(parts[2], body))
                except (ValueError, json.JSONDecodeError) as e:
                    return self.send(400, {"error": str(e)})
            self.send(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screens")
    ap.add_argument("out")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    store = Store(a.screens, a.out)
    if not store.screens:
        sys.exit("no screens found (need <screens>/<name>/screen.json)")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(store, a.port))
    print(f"{len(store.screens)} screens. Open http://127.0.0.1:{a.port}/  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
