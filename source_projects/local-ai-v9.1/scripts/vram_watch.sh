#!/usr/bin/env bash
set -euo pipefail
watch -n 0.5 'nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits; echo; nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu --format=csv'
