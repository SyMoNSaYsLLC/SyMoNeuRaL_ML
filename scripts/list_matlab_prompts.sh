#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PROMPTS="matlab/vendor/mathworks-ai-coding-prompts/prompts"
if [ ! -d "$PROMPTS" ]; then
  echo "Missing $PROMPTS" >&2
  exit 1
fi

find "$PROMPTS" -mindepth 2 -maxdepth 2 -type f -name '*.md' \
  | sort \
  | sed "s#^$PROMPTS/##" \
  | sed 's#/#  ->  #' \
  | sed 's#\.md$##'
