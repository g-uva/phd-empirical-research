from utils.json import read_from_json, write_to_json
import os
import itertools

output_dir = "data/kv_cache_anl_cfg"
template_json_file = "jsons/config.json"
model_paths = [
    "/mnt/playground/gguf_models/llama-3.2-1B-Instruct.gguf",
    "/mnt/playground/gguf_models/gemma-2-2b.gguf",
    "/mnt/playground/gguf_models/deepseek-r1-qwen-1.5b.gguf",
]
models = ["LLaMA3.2-1B", "Gemma2-2B", "Qwen2-1.5B"]
cpu_config = [6, 7]

# Trace config
ring_buffer = [True, False]
# target_iter = [3, -1]


def main():
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    config = read_from_json(template_json_file)
    config["exp"]["dir"] = "exp_kv_cache"
    config["llama-cli"]["n_tokens"] = 500
    cnt = 0
    config["llama-cli"]["cpu_ids"] = cpu_config
    config["llama-cli"]["n_threads"] = len(cpu_config)
    config["trace"]["trace_kernel"] = False
    for i, model in enumerate(models):
        config["llama-cli"]["model_path"] = model_paths[i]
        config["llama-cli"]["model"] = model
        config["exp"]["name"] = f"kv_cache_anl_{model}"
        config["trace"]["activated_ops"] = []
        config["trace"]["structrual_info"] = False
        config["trace"]["open_perf"] = True
        config["trace"]["target_iter"] = -1
        for ring_buf_flag in ring_buffer:
            config["trace"]["ring_buffer"] = ring_buf_flag
            write_to_json(config, f"{output_dir}/config_{cnt}.json")
            cnt += 1


if __name__ == "__main__":
    main()
