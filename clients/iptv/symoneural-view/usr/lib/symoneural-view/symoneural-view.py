#!/usr/bin/env python3
"""SyMoNeuRaL-View launcher shim."""

import sys
from symon_view.app import main

if __name__ == "__main__":
    sys.exit(main() or 0)
