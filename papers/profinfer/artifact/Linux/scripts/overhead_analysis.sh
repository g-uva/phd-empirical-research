#!/bin/bash

TARGET_DIR=data/overhead_anl_cfg_gen

cd ..
for file in $(ls "$TARGET_DIR"/*.json | sort -V); do
    for i in $(seq 5); do
        echo "Start tracing with $file for $i iteration"
        python3 run_llama.py --config $file
        sleep 5
    done
done
