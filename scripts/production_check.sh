#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Syntax check =="
python3 -m py_compile main.py app/main.py app/routers/api_v1.py app/services/*.py app/core/*.py app/workers/*.py

if command -v node >/dev/null 2>&1; then
  node --check frontend/js/app.js
else
  echo "node not installed; skipping JS syntax check"
fi

echo "== Config smoke =="
python3 - <<'CHECKPY'
from app.core.config import get_settings
s = get_settings()
print('host', s.host, 'port', s.port)
print('engines', sorted(s.engines))
assert 'writer' in s.engines and 'code' in s.engines and 'image' in s.engines
CHECKPY

echo "== API route import =="
python3 - <<'ROUTEPY'
from app.main import app
routes = sorted(r.path for r in app.routes)
for target in ['/api/v1/catalog','/api/v1/health','/api/v1/manager/submit','/api/v1/manager/jobs']:
    assert target in routes, target
print('route count', len(routes))
ROUTEPY

echo "Production check complete."
