from utils.parse import create_perf_df_from_trace, parse_ops_one_iter
from utils.args import get_args
from utils.json import read_from_json
import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Ellipse

colors = ["lightsalmon", "lightgreen", "lightblue", "lightpink"]
markers = ["o", "s", "^", "v"]
scale_x = [0.6, 1.1, 1.4, 1.5]
scale_y = [1, 1.1, 1, 1.3]


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
    config = read_from_json(config_path, cat="op_mat_mul_id_pmc")
    m_configs = config["models"]
    output_path = config["output_path"]
    fig, ax = plt.subplots(figsize=(2.9, 2.3))
    cnt_m = 0
    scatters = []
    models = []
    x_data = []
    y1_data = []
    y2_data = []
    for model, m_config in m_configs.items():
        print(f"Start model {model}")
        csv_path = m_config["csv_path"]
        # arch_csv_path = m_config["arch_csv_path"]
        # n_iter = m_config["n_iter"]
        op_names = m_config["ops"]
        df = create_perf_df_from_trace(csv_path)
        # df_arch = create_perf_df_from_trace(arch_csv_path)
        # df_op = parse_ops_one_iter(df, n_iter=n_iter)
        for n_iter in range(200):
            df_op = parse_ops_one_iter(df, n_iter=n_iter)
            df_op = df_op[df_op["op"] == 27]
            df_op.reset_index(drop=True, inplace=True)
            # df_arch = parse_ops_one_iter(df_arch, n_iter=n_iter)
            # df_arch = df_arch[df_arch["op"] == 27]
            # df_arch.reset_index(drop=True, inplace=True)

            # df_arch = df_arch.drop(columns=["op", "name", "count_decode"])
            # assert len(df_op) == len(df_arch), f"{len(df_op)}, {len(df_arch)}"
            # df_merged = pd.concat([df_op, df_arch], axis=1)
            # df_merged["complexity"] = (
            #     df_merged["src0_ne0"]
            #     * df_merged["ne0"]
            #     * df_merged["ne1"]
            #     * df_merged["ne2"]
            # )

            # print(df_op["name"])
            for op_name in op_names:
                sub_df = df_op[df_op["name"] == op_name]

                # mean_pmc = (
                #     np.mean(
                #         sub_df["pmc_0"].to_numpy() * 16 + sub_df["pmc_1"].to_numpy()
                #     )
                #     * 64
                #     / 1024
                #     / 1024
                # )
                # print(sub_df["pmc_0"])
                mean_mem = sub_df["pmc_1"].iloc[0] * 64 / 1024 / 1024
                mean_page_fault = sub_df["pmc_0"].iloc[0]
                # print(mean_pmc)
                mean_time = sub_df["elapsed_time"].iloc[0]
                # compl = sub_df["complexity"].to_list()[0]
                x_data.append(mean_time)
                y1_data.append(mean_mem)
                y2_data.append(mean_page_fault)
                # if op_name == "Kcur":
                #     op_label = "K/V"
                # elif op_name == "Qcur":
                #     op_label = "Q/attn-out"
                # elif op_name == "ffn_gate":
                #     op_label = "FFN"
                #     mean_time *= 0.8
                # elif op_name == "ffn_out":
                #     op_label = "FFN Out"
                # elif op_name == "result_output" or op_name == "node_1046":
                #     op_label = "LM Head"
                # elif op_name == "kq":
                #     op_label = "KQ"
                # elif op_name == "kqv":
                #     op_label = "KQV"
                # else:
                #     raise KeyError(f"{op_name} is not known.")
                # mean_time *= scale_y[cnt_m]
                # mean_pmc *= scale_x[cnt_m]
                # if cnt_m == 0:
                #     ax.text(mean_pmc, mean_time, op_name, fontsize=6, color="grey")

    ax.scatter(
        x_data,
        y1_data,
        color="red",
        marker="o",
        label=model,
        s=5,
    )
    ax2 = ax.twinx()
    ax2.scatter(
        x_data,
        y2_data,
        color="blue",
        marker="o",
        label=model,
        s=5,
    )

    # scatters.append(scatter)
    # models.append(model)
    # cnt_m += 1
    ax.grid(linestyle="--", alpha=0.7)
    # ax.legend(fontsize=8)
    # fig_legend = plt.figure(figsize=(3, 1))
    # fig_legend.legend(
    #     handles=scatters, labels=models, loc="center", ncols=len(models), fontsize=7
    # )
    # fig_legend.savefig("figures/pmc_legend.pdf", bbox_inches="tight", transparent=True)
    # plt.close(fig_legend)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for label in ax.get_yticklabels():
        label.set_rotation(90)
    # ax.set_xlim([1e4, 1e9])
    # ax.set_ylim([1e-2, 1e2])
    ax.set_xlabel("Elapsed time (ms)", fontsize=8)
    ax.set_ylabel("Page faults", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    # Draw two regions
    # draw_ellipse_log_s_ops(ax)
    # draw_ellipse_log_d_ops(ax)
    # fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


if __name__ == "__main__":
    main()
