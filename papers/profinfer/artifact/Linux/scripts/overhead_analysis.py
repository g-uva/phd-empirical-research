from glob import glob
from utils.json import read_from_json, write_to_json
from collections import defaultdict
import numpy as np
from scipy import stats

probe_funcs = [
    "llama_decode_start",
    "llama_decode_end",
    "ggml_backend_graph_compute_async_start",
    "ggml_backend_graph_compute_async_end",
    "ggml_compute_forward_start",
    "ggml_compute_forward_end",
    # "get_sched_wakeup_events",
    # "get_sched_switch_tp_events",
]

baseline_p = {
    "LLaMA3.2-1B": [10.32, 18.97, 26.2, 30.78],
    "Gemma2-2B": [4.69, 8.48, 11.74, 13.7],
    "Qwen2-1.5B": [7.97, 15.46, 22.12, 27.14],
}

baseline_d = {
    "LLaMA3.2-1B": [6.21, 8.58, 9.68, 9.78],
    "Gemma2-2B": [2.7, 3.78, 4.36, 4.43],
    "Qwen2-1.5B": [5.85, 10.42, 13.01, 13.69],
}


def parse_bpfprog(bpf_metric: list) -> tuple:
    runtime_ns = 0
    cnt = 0
    for metric in bpf_metric:
        if "name" not in metric.keys() or metric["name"] not in probe_funcs:
            continue
        elif "run_time_ns" not in metric.keys() or "run_cnt" not in metric.keys():
            runtime_ns += 0
        else:
            runtime_ns += metric["run_time_ns"]
            cnt += metric["run_cnt"]
    if cnt == 0:
        cnt = 1
    return runtime_ns, cnt


target_dir = "exp_overhead"
res_org = defaultdict(dict)  # [p_speed, d_speed, probe_time, probe_cnt]
res_overhead = defaultdict(dict)  # [p_dec, d_dec, ratio_probe]
res_overhead_all = defaultdict(list)  # Statistics
res_overhead_model = defaultdict(dict)  # Statistics for each model
res = defaultdict(np.ndarray)
for file in glob(f"{target_dir}/*"):
    # for cfg_json in [
    #     sorted(glob(f"{file}/config/*.json"))[-1]
    # ]:  # There is a bug of date
    cfg_json = sorted(glob(f"{file}/config/*.json"))[-1]
    cfg = read_from_json(cfg_json)
    # if cfg["trace"]["open_perf"]:
    #     metric = read_from_json(
    #         f"{file}/{cfg['trace']['perf_config_raw']}/metrics.json"
    #     )
    #     bpf_prog = read_from_json(
    #         f"{file}/{cfg['trace']['perf_config_raw']}/bpftool_prog.json"
    #     )
    # else:
    metric = read_from_json(f"{file}/metrics.json")
    bpf_prog = read_from_json(f"{file}/bpftool_prog.json")
    bpf_metrics = parse_bpfprog(bpf_prog)
    model = cfg["llama-cli"]["model"]
    n_threads = cfg["llama-cli"]["n_threads"]

    struct_flag = cfg["trace"]["structrual_info"]
    perf_flag = cfg["trace"]["open_perf"]
    perfbuf_flag = not cfg["trace"]["ring_buffer"]
    op_flag = True if len(cfg["trace"]["activated_ops"]) == 0 else False

    if (
        str((model, n_threads))
        not in res_org[str((struct_flag, perf_flag, op_flag, perfbuf_flag))].keys()
    ):
        res_org[str((struct_flag, perf_flag, op_flag, perfbuf_flag))][
            str((model, n_threads))
        ] = []
    res_org[str((struct_flag, perf_flag, op_flag, perfbuf_flag))][
        str((model, n_threads))
    ].append(
        [
            metric["prefill_speed"],
            metric["decode_speed"],
            bpf_metrics[0],
            bpf_metrics[1],
        ]
    )

    p_dec = baseline_p[model][n_threads - 1] - metric["prefill_speed"]
    d_dec = baseline_d[model][n_threads - 1] - metric["decode_speed"]

    p_dec_rel = (
        baseline_p[model][n_threads - 1] - metric["prefill_speed"]
    ) / baseline_p[model][n_threads - 1]
    p_dec_rel = 0 if p_dec_rel < 0 else p_dec_rel
    d_dec_rel = (
        baseline_d[model][n_threads - 1] - metric["decode_speed"]
    ) / baseline_d[model][n_threads - 1]
    d_dec_rel = 0 if d_dec_rel < 0 else d_dec_rel
    ratio = (
        bpf_metrics[0]
        / 1e9
        / (
            (
                metric["n_input_tokens"] / metric["prefill_speed"]
                + metric["n_output_tokens"] / metric["decode_speed"]
            )
            * n_threads
        )
    )

    res_overhead[str((struct_flag, perf_flag, op_flag, perfbuf_flag))][
        str((model, n_threads))
    ] = np.array([p_dec_rel, d_dec_rel, ratio])

    # For each model
    if (
        model
        not in res_overhead_model[
            str((struct_flag, perf_flag, op_flag, perfbuf_flag))
        ].keys()
    ):
        res_overhead_model[str((struct_flag, perf_flag, op_flag, perfbuf_flag))][
            model
        ] = []
    res_overhead_model[str((struct_flag, perf_flag, op_flag, perfbuf_flag))][
        model
    ].append(np.array([p_dec, d_dec, ratio]))

    # For all
    res_overhead_all[str((struct_flag, perf_flag, op_flag, perfbuf_flag))].append(
        np.array([p_dec_rel, d_dec_rel, ratio])
    )

# Analyze the statistics
for key, value in res_overhead_all.items():
    np_value = np.array(value)
    mean = np.mean(np_value, axis=0)
    std = np.std(np_value, axis=0, ddof=1)
    # t_stat, p_value = stats.ttest_1samp(np_value, popmean=0, axis=0)
    t_stat, p_value = stats.wilcoxon(np_value, axis=0)
    print(f"{key}, mean: {mean[1]}, std: {std[1]}, p-value: {p_value[1]}")

for key, value in res_overhead_model.items():
    for m_key, m_value in value.items():
        np_value = np.array(m_value)
        mean = np.mean(np_value, axis=0)
        std = np.std(np_value, axis=0, ddof=1)
        t_stat, p_value = stats.wilcoxon(np_value, axis=0)
        print(f"{key} - {m_key}, mean: {mean[1]}, std: {std[1]}, p-value: {p_value[1]}")

for key, value in res_overhead.items():
    # res[key] = np.mean(list(value.values()), axis=0).tolist()
    arr = [
        sub_v
        for sub_k, sub_v in value.items()
        if sub_k.startswith("('LLaMA3.2-1B'") or sub_k.startswith("('G")
    ]
    # arr = [sub_v for sub_k, sub_v in value.items()]
    res[key] = np.mean(arr, axis=0).tolist()
    # arr = np.stack(list(value.values()))  # shape: (N, 3)

    # # 对每一列（维度）去掉最大值和最小值
    # result = []
    # for i in range(arr.shape[1]):  # 遍历每一列（维度）
    #     col = arr[:, i]
    #     if len(col) > 2:
    #         trimmed = np.delete(col, [np.argmax(col), np.argmin(col)])
    #     else:
    #         trimmed = col  # 不足3个元素，跳过剔除
    #     result.append(np.mean(trimmed))

    # res[key] = result
    for sub_key, sub_value in value.items():
        res_overhead[key][sub_key] = sub_value.tolist()

# write_to_json(res_overhead, "results/overhead_raw_gen.json")
# write_to_json(res, "results/overhead_new_gen.json")
