#!/bin/bash

TARGET_DIR=data/prefill_anl_cfg

cd ..
for file in $(ls "$TARGET_DIR"/*.json | sort -V); do
    echo "Start tracing with $file"
    python3 run_llama.py --config $file
    sleep 10
done