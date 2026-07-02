from __future__ import annotations
from pathlib import Path

def project_root() -> Path:
    # symon_tools lives directly under the project root in source installs.
    return Path(__file__).resolve().parents[1]
