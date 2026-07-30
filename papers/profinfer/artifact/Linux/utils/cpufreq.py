from __future__ import annotations
from pathlib import Path
import argparse
import sys
import json

CPU_PATH = Path("/sys/devices/system/cpu")
STATE_FILE = Path("/tmp/.cpufreq_lock_state.json")  # for saving the previous 

def each_cpu_cpufreq():
    """yield Path objects like cpu0/cpufreq"""
    for p in CPU_PATH.glob("cpu[0-9]*"):
        cpufreq = p / "cpufreq"
        if cpufreq.is_dir():
            yield cpufreq

def read_text(path: Path) -> str:
    try:
        return path.read_text().strip()
    except Exception as e:
        sys.exit(f"Unable to read {path}: {e}")

def write_text(path: Path, value: str):
    try:
        path.write_text(value)
    except PermissionError:
        sys.exit(f"Permission denied with {path}, please use sudo")
    except Exception as e:
        sys.exit(f"Writing into {path} failed: {e}")

def save_state():
    """Backup governor/min/max to STATE_FILE"""
    state = {}
    for cpufreq in each_cpu_cpufreq():
        cpu = cpufreq.parent.name
        state[cpu] = {
            "governor": read_text(cpufreq / "scaling_governor"),
            "min":      read_text(cpufreq / "scaling_min_freq"),
            "max":      read_text(cpufreq / "scaling_max_freq"),
        }
    STATE_FILE.write_text(json.dumps(state))

def restore_state():
    if not STATE_FILE.exists():
        sys.exit("Cannot find the backup config")
    state = json.loads(STATE_FILE.read_text())
    for cpufreq in each_cpu_cpufreq():
        cpu = cpufreq.parent.name
        if cpu not in state:
            continue
        write_text(cpufreq / "scaling_governor", state[cpu]["governor"])
        write_text(cpufreq / "scaling_min_freq", state[cpu]["min"])
        write_text(cpufreq / "scaling_max_freq", state[cpu]["max"])
    STATE_FILE.unlink()
    print("Reset CPU freqs and governors")

def lock_freq(freq_khz: str, governor: str):
    save_state()
    for cpufreq in each_cpu_cpufreq():
        write_text(cpufreq / "scaling_governor", governor)
        write_text(cpufreq / "scaling_min_freq", freq_khz)
        write_text(cpufreq / "scaling_max_freq", freq_khz)
    print(f"Lock all CPUs to {freq_khz} kHz, governor={governor}")

def lock_cpu_freq(cpu_list: list, freq_list: list, cache_state: bool=False, set_userspace: bool=False):
    # TODO: Check if the freq to be set is available or not
    if cache_state:
        save_state()
    for i, cpu in enumerate(cpu_list):
        cpufreq_dir = CPU_PATH / f"cpu{cpu}" / "cpufreq" 
        if set_userspace:
            write_text(cpufreq_dir / "scaling_governor", "userspace")
        write_text(cpufreq_dir / "scaling_min_freq", str(freq_list[i]))
        write_text(cpufreq_dir / "scaling_max_freq", str(freq_list[i]))
    # print("Lock all CPUs' frequencies.")