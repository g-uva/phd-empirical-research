#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from collections import defaultdict


# ========= Part 1: parse log =========
START_RE = re.compile(
    r"^Start tracing with\s+(?P<file>\S+)\s+for\s+(?P<iter>\d+)\s+iteration\s*$"
)
LOST_RE = re.compile(r"^Possibly lost\s+(?P<n>\d+)\s+samples\s*$")


def parse_log_lost_stats(log_path: Path) -> Dict[str, Tuple[int, int]]:
    """
    Return:
      { config_<i>.json : (lost_total_sum_across_blocks, block_count) }

    A block = lines between two 'Start tracing with ...' markers (or EOF).
    For each block, we sum all 'Possibly lost X samples' as lost_sum.
    For each config, we accumulate (lost_total, blocks_count).
    """
    stats: Dict[str, Tuple[int, int]] = {}

    current_key: Optional[str] = None
    current_lost: int = 0

    def flush():
        nonlocal current_key, current_lost
        if current_key is None:
            return
        total, cnt = stats.get(current_key, (0, 0))
        stats[current_key] = (total + current_lost, cnt + 1)
        current_key = None
        current_lost = 0

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")

            m = START_RE.match(line)
            if m:
                flush()
                current_key = Path(m.group("file")).name  # basename: config_<i>.json
                continue

            if current_key is not None:
                m2 = LOST_RE.match(line)
                if m2:
                    current_lost += int(m2.group("n"))

    flush()
    return stats


# ========= Part 2: read exp_overhead_old =========
def read_run_cnt_sum(bpftool_path: Path) -> int:
    """bpftool_prog.json is a list of dict; sum item['run_cnt'] if present and numeric."""
    with bpftool_path.open("r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    total = 0
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "run_cnt" in item:
                try:
                    total += int(item["run_cnt"])
                except Exception:
                    pass
    return total


def find_single_config_file(config_dir: Path) -> Path:
    """config_dir contains exactly one config_*.json."""
    configs = list(config_dir.glob("config_*.json"))
    if len(configs) != 1:
        raise RuntimeError(
            f"{config_dir} should contain exactly one config_*.json (found {len(configs)})"
        )
    return configs[0]


def read_trace_flags(config_path: Path) -> Tuple[bool, bool]:
    """
    Read config json dict, fetch:
      cfg['trace']['structrual_info'] : bool
      cfg['trace']['open_perf']       : bool
    """
    with config_path.open("r", encoding="utf-8", errors="replace") as f:
        cfg = json.load(f)

    if not isinstance(cfg, dict):
        raise ValueError(f"{config_path} is not a JSON object")

    trace = cfg.get("trace")
    if not isinstance(trace, dict):
        raise KeyError(f"{config_path}: missing or invalid 'trace'")

    s = trace["structrual_info"]
    o = trace["open_perf"]

    if not isinstance(s, bool):
        raise TypeError(f"{config_path}: trace['structrual_info'] is not bool")
    if not isinstance(o, bool):
        raise TypeError(f"{config_path}: trace['open_perf'] is not bool")

    return s, o


def collect_config_meta(base_dir: Path) -> Dict[str, Tuple[int, bool, bool]]:
    """
    Walk exp_overhead_old/*/
    Each subfolder has:
      - bpftool_prog.json
      - config/config_<i>.json (exactly one)
    Return:
      { config_<i>.json : (run_cnt_sum, structrual_info, open_perf) }
    """
    meta: Dict[str, Tuple[int, bool, bool]] = {}

    for sub in sorted([p for p in base_dir.iterdir() if p.is_dir()]):
        bpftool = sub / "bpftool_prog.json"
        config_dir = sub / "config"

        if not bpftool.exists() or not config_dir.exists():
            continue

        try:
            cfg_path = find_single_config_file(config_dir)
            run_cnt = read_run_cnt_sum(bpftool)
            s, o = read_trace_flags(cfg_path)
        except Exception as e:
            print(f"[WARN] Skip {sub}: {e}")
            continue

        meta[cfg_path.name] = (run_cnt, s, o)

    return meta


# ========= Helpers =========
def sort_key_config(name: str):
    """Sort by the numeric i in config_<i>.json if possible."""
    try:
        return int(Path(name).stem.split("_")[-1])
    except Exception:
        return name


def fmt_num(x: float) -> str:
    """Pretty print: integer -> no decimals; else compact."""
    if abs(x - round(x)) < 1e-12:
        return str(int(round(x)))
    return f"{x:.6g}"


# ========= Main =========
def main():
    ap = argparse.ArgumentParser(
        description=(
            "Parse log to compute average lost samples per config (averaged over blocks), "
            "join with run_cnt and trace flags from exp_overhead_old, print per-config results, "
            "then print grouped averages by (structrual_info, open_perf) considering only configs with lost_avg > 0."
        )
    )
    ap.add_argument("logfile", help="Path to the log file")
    ap.add_argument(
        "--base-dir",
        default="exp_overhead_old",
        help="Base directory (default: exp_overhead_old)",
    )
    ap.add_argument(
        "--show-zero-lost-rows",
        action="store_true",
        help="Also print per-config rows where lost_avg == 0 (default: hide them)",
    )
    args = ap.parse_args()

    log_path = Path(args.logfile)
    base_dir = Path(args.base_dir)

    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return
    if not base_dir.exists():
        print(f"Base dir not found: {base_dir}")
        return

    lost_stats = parse_log_lost_stats(log_path)  # {cfg: (lost_total, blocks)}
    meta = collect_config_meta(base_dir)  # {cfg: (run_cnt, s, o)}

    # Build per-config rows
    rows: List[dict] = []

    # Per-config table
    header = (
        f"{'config':<16} {'structrual_info':>16} {'open_perf':>10} "
        f"{'lost_avg':>10} {'blocks':>8} {'run_cnt':>10} {'total':>10} {'lost/run':>10}"
    )
    print(header)
    print("-" * len(header))

    for cfg in sorted(lost_stats.keys(), key=sort_key_config):
        if cfg not in meta:
            print(f"[WARN] In log but not found in exp_overhead_old: {cfg}")
            continue

        lost_total, blocks = lost_stats[cfg]
        lost_avg = (lost_total / blocks) if blocks > 0 else 0.0

        run_cnt, s, o = meta[cfg]
        total = lost_avg + run_cnt
        ratio = None if run_cnt == 0 else (lost_avg / run_cnt)

        rows.append(
            {
                "config": cfg,
                "structrual_info": s,
                "open_perf": o,
                "lost_avg": lost_avg,
                "blocks": blocks,
                "run_cnt": run_cnt,
                "total": total,
                "ratio": ratio,
            }
        )

        if (not args.show_zero_lost_rows) and lost_avg == 0:
            continue

        ratio_str = "NA" if ratio is None else fmt_num(ratio)
        print(
            f"{cfg:<16} {str(s):>16} {str(o):>10} "
            f"{fmt_num(lost_avg):>10} {blocks:>8} {run_cnt:>10} {fmt_num(total):>10} {ratio_str:>10}"
        )

    # ========= Summary by (structrual_info, open_perf), only consider lost_avg > 0 =========
    print("\n=== Summary (averages over configs with lost_avg > 0 only) ===")

    groups = defaultdict(list)
    for r in rows:
        if r["lost_avg"] > 0:
            groups[(r["structrual_info"], r["open_perf"])].append(r)

    if not groups:
        print("No groups with lost_avg > 0.")
        return

    sum_header = (
        f"{'structrual_info':>16} {'open_perf':>10} {'N':>6} "
        f"{'lost_avg_mean':>14} {'blocks_mean':>14} {'run_cnt_mean':>14} {'total_mean':>14} {'ratio_mean':>14}"
    )
    print(sum_header)
    print("-" * len(sum_header))

    for (s, o), items in sorted(groups.items()):
        n = len(items)
        lost_avg_mean = sum(r["lost_avg"] for r in items) / n
        blocks_mean = sum(r["blocks"] for r in items) / n
        run_cnt_mean = sum(r["run_cnt"] for r in items) / n
        total_mean = sum(r["total"] for r in items) / n

        ratios = [r["ratio"] for r in items if r["ratio"] is not None]
        ratio_mean = (sum(ratios) / len(ratios)) if ratios else None

        print(
            f"{str(s):>16} {str(o):>10} {n:>6} "
            f"{fmt_num(lost_avg_mean):>14} {fmt_num(blocks_mean):>14} {fmt_num(run_cnt_mean):>14} "
            f"{fmt_num(total_mean):>14} {('NA' if ratio_mean is None else fmt_num(ratio_mean)):>14}"
        )


if __name__ == "__main__":
    main()
