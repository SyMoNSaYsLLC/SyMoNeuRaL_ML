#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
SRC="matlab/vendor/mathworks-matlab-mcp-server"
OUT="bin/matlab-mcp-server"

if [ ! -d "$SRC" ]; then
  echo "Missing $SRC. Run the MATLAB MCP/prompts migration update first." >&2
  exit 1
fi

if ! command -v go >/dev/null 2>&1; then
  echo "Go is required to build MATLAB MCP Server." >&2
  echo "Install Go, then rerun: ./scripts/build_matlab_mcp_server.sh" >&2
  exit 2
fi

mkdir -p bin
(
  cd "$SRC"
  go build -o "../../../../$OUT" ./cmd/matlab-mcp-server
)
chmod +x "$OUT"

echo "Built: $OUT"
"$OUT" --help | sed -n '1,40p' || true
