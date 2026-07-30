from utils.parse import create_perf_df_from_trace, parse_ops_one_iter
from utils.args import get_args
from utils.json import read_from_json
import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Ellipse

colors = ["lightsalmon", "lightgreen", "lightblue"]
markers = ["o", "s", "^"]
scale_x = [0.5, 1.1, 1.2]
scale_y = [0.8, 1.1, 1]


def draw_ellipse_log_s_ops(ax: Axes):
    log_x0 = np.log10(2e7)
    log_y0 = np.log10(1.3e0)

    a = 2.5
    b = 0.3
    theta_deg = 46
    theta = np.deg2rad(theta_deg)

    t = np.linspace(0, 2 * np.pi, 300)
    x_log = log_x0 + a * np.cos(t) * np.cos(theta) - b * np.sin(t) * np.sin(theta)
    y_log = log_y0 + a * np.cos(t) * np.sin(theta) + b * np.sin(t) * np.cos(theta)

    x = 10**x_log
    y = 10**y_log
    ax.text(
        1e7,
        5,
        "Static Operators",
        rotation=46,
        fontsize=7,
        color="blue",
        ha="center",
        va="center",
    )
    ax.plot(x, y, color="blue", lw=0.5, linestyle="--")


def draw_ellipse_log_d_ops(ax: Axes):
    log_x0 = np.log10(6.5e4)
    log_y0 = np.log10(1e-1)

    a = 0.2
    b = 0.5
    theta_deg = -10
    theta = np.deg2rad(theta_deg)

    t = np.linspace(0, 2 * np.pi, 300)
    x_log = log_x0 + a * np.cos(t) * np.cos(theta) - b * np.sin(t) * np.sin(theta)
    y_log = log_y0 + a * np.cos(t) * np.sin(theta) + b * np.sin(t) * np.cos(theta)

    x = 10**x_log
    y = 10**y_log
    ax.text(
        1.2e5,
        0.5,
        "Dynamic Operators",
        fontsize=7,
        color="red",
        ha="center",
        va="baseline",
    )
    ax.plot(x, y, color="red", lw=0.5, linestyle="--")


def main():
    args = get_args()
    config_path: str = args.config
    config = read_from_json(config_path, cat="op_mat_mul")
    m_configs = config["models"]
    output_path = config["output_path"]
    fig, ax = plt.subplots(figsize=(4.2, 2.4))
    cnt_m = 0
    for model, m_config in m_configs.items():
        print(f"Start model {model}")
        csv_path = m_config["csv_path"]
        arch_csv_path = m_config["arch_csv_path"]
        n_iter = m_config["n_iter"]
        op_names = m_config["ops"]
        df = create_perf_df_from_trace(csv_path)
        df_arch = create_perf_df_from_trace(arch_csv_path)
        df_op = parse_ops_one_iter(df, n_iter=n_iter)
        df_arch = parse_ops_one_iter(df_arch, n_iter=n_iter)
        df_arch = df_arch[df_arch["op"] == 26]
        df_arch.reset_index(drop=True, inplace=True)
        df_arch = df_arch.drop(columns=["op", "name", "count_decode", "elapsed_time"])
        assert len(df_op) == len(df_arch), f"{len(df_op)}, {len(df_arch)}"
        df_merged = pd.concat([df_op, df_arch], axis=1)
        df_merged["complexity"] = (
            df_merged["src0_ne0"]
            * df_merged["ne0"]
            * df_merged["ne1"]
            * df_merged["ne2"]
        )
        x_data = []
        y_data = []
        for op_name in op_names:
            sub_df = df_merged[df_merged["name"].str.startswith(op_name)]
            mean_time = np.mean(sub_df["elapsed_time"].to_numpy())
            compl = sub_df["complexity"].to_list()[0]
            x_data.append(compl)
            y_data.append(mean_time)
            if op_name == "Kcur":
                op_label = "K/V"
            elif op_name == "Qcur":
                op_label = "Q/KQV-out"
            elif op_name == "ffn_gate":
                op_label = "FFN Gate/Up/Out"
                mean_time *= 0.8
            elif op_name == "ffn_out":
                op_label = "FFN Out"
            elif op_name == "result_output" or op_name == "node_1046":
                op_label = "LM Head"
            elif op_name == "kq":
                op_label = "KQ"
            elif op_name == "kqv":
                op_label = "KQV"
            else:
                raise KeyError(f"{op_name} is not known.")
            mean_time *= scale_y[cnt_m]
            compl *= scale_x[cnt_m]
            ax.text(compl, mean_time, op_label, fontsize=6, color=colors[cnt_m])
        ax.scatter(
            x_data, y_data, color=colors[cnt_m], marker=markers[cnt_m], label=model, s=5
        )
        cnt_m += 1
    ax.grid(linestyle="--", alpha=0.7)
    ax.legend(fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim([1e4, 1e9])
    ax.set_ylim([1e-2, 1e2])
    for label in ax.get_yticklabels():
        label.set_rotation(90)
    ax.set_xlabel("Computation complexity", fontsize=8)
    ax.set_ylabel("Elapsed time (ms)", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    # Draw two regions
    draw_ellipse_log_s_ops(ax)
    draw_ellipse_log_d_ops(ax)
    fig.savefig(output_path, bbox_inches="tight")


if __name__ == "__main__":
    main()
