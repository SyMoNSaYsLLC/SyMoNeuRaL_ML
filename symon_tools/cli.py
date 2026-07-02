from __future__ import annotations
import argparse
import json
import sys
import urllib.request
import urllib.error
from .paths import project_root

DEFAULT_BASE = "http://127.0.0.1:8000"

def request(method: str, path: str, data=None, base: str = DEFAULT_BASE):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode()
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            return json.loads(raw)
        return raw

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="symon-cli")
    p.add_argument("--base", default=DEFAULT_BASE)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    sub.add_parser("catalog")
    sub.add_parser("vram")
    ask = sub.add_parser("ask")
    ask.add_argument("prompt", nargs="+")
    ask.add_argument("--route", choices=["writer","code","image"], default=None)
    jobs = sub.add_parser("jobs")
    jobs.add_argument("--kind", choices=["manager","coder"], default="manager")
    ns = p.parse_args(argv)
    try:
        if ns.cmd == "health":
            print(json.dumps(request("GET","/api/v1/health", base=ns.base), indent=2)); return 0
        if ns.cmd == "catalog":
            print(json.dumps(request("GET","/api/v1/catalog", base=ns.base), indent=2)); return 0
        if ns.cmd == "vram":
            print(json.dumps(request("GET","/api/v1/tools/vram", base=ns.base), indent=2)); return 0
        if ns.cmd == "jobs":
            path = "/api/v1/manager/jobs" if ns.kind == "manager" else "/api/v1/coder/jobs"
            print(json.dumps(request("GET", path, base=ns.base), indent=2)); return 0
        if ns.cmd == "ask":
            payload = {"prompt": " ".join(ns.prompt)}
            if ns.route:
                payload["route"] = ns.route
            print(json.dumps(request("POST","/api/v1/manager/submit", data=payload, base=ns.base), indent=2)); return 0
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr); return 1
    except Exception as e:
        print(repr(e), file=sys.stderr); return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
