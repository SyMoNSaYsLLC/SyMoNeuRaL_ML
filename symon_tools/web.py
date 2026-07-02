from __future__ import annotations
import os, subprocess, webbrowser

def main() -> int:
    url = os.getenv("SYMON_WEB_URL", "http://127.0.0.1:8000")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(url)
    return 0
