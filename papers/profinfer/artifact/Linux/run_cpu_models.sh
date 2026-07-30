#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../../../.." && pwd)
CFG=jsons/config.json

run_one () {
  local name="$1"
  local model="$2"

  if [[ -z "$model" || ! -f "$model" ]]; then
    echo "Missing model for $name: $model" >&2
    return 1
  fi

  /usr/bin/python3 - "$CFG" "$name" "$model" "$ROOT" <<'PY'
import json, sys
cfg_path, name, model_path, root = sys.argv[1:]
with open(cfg_path) as f:
    cfg = json.load(f)

cfg["exp"]["name"] = f"trace_{name}"
cfg["llama-cli"]["model"] = name
cfg["llama-cli"]["model_path"] = model_path
cfg["llama-cli"]["work_dir"] = f"{root}/llama.cpp/build/bin"
cfg["llama-cli"]["cpu_ids"] = [0, 1]
cfg["llama-cli"]["n_threads"] = 2
cfg["llama-cli"]["n_tokens"] = 100

cfg["trace"]["lib_llama_dyn"] = f"{root}/llama.cpp/build/bin/libllama.so"
cfg["trace"]["lib_ggml_dyn_base"] = f"{root}/llama.cpp/build/bin/libggml-base.so"
cfg["trace"]["lib_ggml_dyn_cpu"] = f"{root}/llama.cpp/build/bin/libggml-cpu.so"
cfg["trace"]["open_perf"] = False
cfg["trace"]["dynamic_link"] = True
cfg["trace"]["trace_kernel"] = False
cfg["trace"]["target_iter"] = 3
cfg["trace"]["timeout"] = 120

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=4)
PY

  echo "Running $name"
  sudo /usr/bin/python3 run_llama.py --config "$CFG"
}

run_one qwen2.5-0.5B "$ROOT/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
run_one llama3.2-1B "$ROOT/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
run_one deepseek-r1-qwen-1.5B "$ROOT/models/DeepSeek-R1-Distill-Qwen-1.5B.Q4_K_M.gguf"

GEMMA=$(find "$ROOT/models" -name '*Q4_K_M*.gguf' | grep -i gemma | head -1)
run_one gemma2-2B "$GEMMA"
