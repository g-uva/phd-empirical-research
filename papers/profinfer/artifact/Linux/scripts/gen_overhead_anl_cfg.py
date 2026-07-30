from utils.json import read_from_json, write_to_json
import os
import itertools

output_dir = "data/overhead_anl_cfg_gen"
template_json_file = "jsons/config.json"
model_paths = [
    "/mnt/playground/gguf_models/llama-3.2-1B-Instruct.gguf",
    "/mnt/playground/gguf_models/gemma-2-2b.gguf",
    "/mnt/playground/gguf_models/deepseek-r1-qwen-1.5b.gguf",
]
# models = ["LLaMA3.2-1B", "Gemma2-2B", "Qwen2-1.5B"]
models = ["LLaMA3.2-1B"]
cpu_configs = [[6, 7]]

# Trace config
activated_ops = [[]]
structrual_info = [True, False]
open_perf = [True, False]
ring_buffer = [True, False]
n_tokens = [10, 50, 100, 200, 400]
# target_iter = [3, -1]


def main():
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    config = read_from_json(template_json_file)
    config["exp"]["dir"] = "exp_overhead_gen"
    # config["llama-cli"]["n_tokens"] = 10
    trace_lists = [activated_ops, structrual_info, open_perf, ring_buffer, n_tokens]
    trace_configs = [
        (a, b, c, d, e)
        for (a, b, c, d, e) in itertools.product(*trace_lists)
        if not (a == [26] and b == True)
    ]
    cnt = 0
    for cpu_config in cpu_configs:
        config["llama-cli"]["cpu_ids"] = cpu_config
        config["llama-cli"]["n_threads"] = len(cpu_config)
        for i, model in enumerate(models):
            config["llama-cli"]["model_path"] = model_paths[i]
            config["llama-cli"]["model"] = model
            config["exp"]["name"] = f"ovh_{model}_t{len(cpu_config)}"
            for a, b, c, d, e in trace_configs:
                config["trace"]["activated_ops"] = a
                config["trace"]["structrual_info"] = b
                config["trace"]["open_perf"] = c
                config["trace"]["ring_buffer"] = d
                config["llama-cli"]["n_tokens"] = e
                write_to_json(config, f"{output_dir}/config_{cnt}.json")
                cnt += 1


if __name__ == "__main__":
    main()
