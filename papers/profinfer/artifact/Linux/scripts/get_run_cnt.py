#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path


BASE_DIR = Path("exp_overhead_old")


def read_run_cnt_sum(bpftool_path: Path) -> int:
    """bpftool_prog.json is a list of dict; sum item['run_cnt'] if present."""
    with bpftool_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{bpftool_path} is not a JSON list")

    total = 0
    for item in data:
        if isinstance(item, dict) and "run_cnt" in item:
            # tolerate run_cnt being str/int/float-like
            try:
                total += int(item["run_cnt"])
            except Exception:
                # ignore non-numeric run_cnt
                pass
    return total


def find_single_config_file(config_dir: Path) -> Path:
    """config_dir should contain exactly one config_*.json."""
    configs = sorted(config_dir.glob("config_*.json"))
    if len(configs) == 0:
        raise FileNotFoundError(f"No config_*.json found in {config_dir}")
    if len(configs) > 1:
        raise RuntimeError(
            f"More than one config_*.json found in {config_dir}: {[p.name for p in configs]}"
        )
    return configs[0]


def main():
    if not BASE_DIR.exists():
        print(f"Directory not found: {BASE_DIR}")
        return

    results = {}

    for sub_dir in sorted([p for p in BASE_DIR.iterdir() if p.is_dir()]):
        bpftool_path = sub_dir / "bpftool_prog.json"
        config_dir = sub_dir / "config"

        if not bpftool_path.exists() or not config_dir.exists():
            continue

        try:
            config_file = find_single_config_file(config_dir)
            run_cnt_sum = read_run_cnt_sum(bpftool_path)
        except Exception as e:
            print(f"[WARN] Skip {sub_dir}: {e}")
            continue

        results[config_file.name] = run_cnt_sum

    if not results:
        print("No valid results found.")
        return

    def sort_key(name: str):
        try:
            stem = Path(name).stem  # "config_17"
            idx = int(stem.split("_")[-1])
            return (0, idx)
        except Exception:
            return (1, name)

    for k in sorted(results.keys(), key=sort_key):
        print(f"{k}: {results[k]}")


if __name__ == "__main__":
    main()
