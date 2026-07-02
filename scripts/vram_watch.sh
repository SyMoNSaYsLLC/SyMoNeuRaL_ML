#!/usr/bin/env bash
watch -n 0.2 'nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu --format=csv && echo && nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv'
