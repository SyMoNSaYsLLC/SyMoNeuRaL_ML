#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from app.core.cuda_model_tools import model_inventory
from pathlib import Path
import json
print(json.dumps(model_inventory(Path.cwd()), indent=2))
PY
