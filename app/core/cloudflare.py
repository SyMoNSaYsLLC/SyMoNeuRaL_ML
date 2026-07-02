from __future__ import annotations

import os
from pathlib import Path


def tunnel_config(hostname: str | None = None, service_url: str = "http://localhost:8000") -> str:
    hostname = hostname or os.getenv("SYMON_PUBLIC_HOSTNAME", "symoneural.example.com")
    return f"""tunnel: symoneural-local-ml
credentials-file: /etc/cloudflared/symoneural-local-ml.json

ingress:
  - hostname: {hostname}
    service: {service_url}
  - service: http_status:404
"""


def write_tunnel_config(path: str | Path, hostname: str | None = None) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = tunnel_config(hostname=hostname)
    p.write_text(text, encoding="utf-8")
    return {"path": str(p), "hostname": hostname or os.getenv("SYMON_PUBLIC_HOSTNAME", "symoneural.example.com")}
