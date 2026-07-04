#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .vscode

SERVER="$PWD/bin/matlab-mcp-server"
if [ ! -x "$SERVER" ]; then
  echo "Missing executable: $SERVER" >&2
  echo "Build it first: ./scripts/build_matlab_mcp_server.sh" >&2
  exit 1
fi

cat > .vscode/mcp.json <<CONFIG
{
  "servers": {
    "matlab": {
      "type": "stdio",
      "command": "$SERVER",
      "args": [
        "--initial-working-folder=$PWD",
        "--matlab-display-mode=nodesktop"
      ]
    }
  }
}
CONFIG

echo "Wrote .vscode/mcp.json"
