import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator


def plot_time_diff_vs_count_decode(
    df: pd.DataFrame, title: str = "Time vs Count Decode", save_path: str = None
):
    """
    Plot a line graph of time_diff (Y-axis) vs count_decode (X-axis)
    with x-axis tick interval = 10.
    """
    if "count_decode" not in df.columns or "time_diff" not in df.columns:
        raise ValueError(
            "DataFrame must contain 'count_decode' and 'time_diff' columns"
        )

    # Convert time_diff to milliseconds (if in ns)
    df["time_diff_ms"] = df["time_diff"] / 1e6

    # Sort by count_decode to ensure line continuity
    df = df.sort_values(by="count_decode")

    plt.figure(figsize=(7, 4.5), dpi=100)
    plt.plot(
        df["count_decode"], df["time_diff_ms"], color="blue", linewidth=0.5, marker=None
    )

    plt.title(title)
    plt.xlabel("Iterations")
    plt.ylabel("Time Difference (ms)")

    # Force x-axis tick every 10 units
    ax = plt.gca()
    ax.xaxis.set_major_locator(MultipleLocator(50))

    # Axis limits
    min_x, max_x = df["count_decode"].min(), df["count_decode"].max()
    plt.xlim(0, max_x + 10)

    # min_y, max_y = df["time_diff_ms"].min(), df["time_diff_ms"].max()
    # plt.ylim(0, max_y + (0.05 * max_y))

    if save_path:
        plt.savefig(save_path, dpi=500, bbox_inches="tight")
        print(f"✅ Plot saved to {save_path}")
    else:
        plt.show()


def plot_elapsed_vs_count(
    avg_df: pd.DataFrame,
    title: str = "Elapsed Time vs Count Decode",
    save_path: str = None,
):
    """
    Plot a graph of count_decode (x-axis) vs sum_elapsed_time_ms (y-axis) with x-axis step.

    Args:
        avg_df (pd.DataFrame): DataFrame with columns ['count_decode', 'sum_elapsed_time_ms'].
        title (str): Title of the plot.
        x_step (int): Step for x-axis ticks.
    """
    if avg_df.empty:
        print("⚠️ DataFrame is empty. Nothing to plot.")
        return

    plt.figure(figsize=(8, 5))
    plt.plot(
        avg_df["count_decode"],
        avg_df["sum_elapsed_time_ms"],
        color="blue",
        linewidth=0.5,
        marker=None,
    )
    plt.xlabel("Iterations")
    plt.ylabel("Average Elapsed Time (ms)")
    plt.title(title)

    # Force x-axis tick every 10 units
    ax = plt.gca()
    ax.xaxis.set_major_locator(MultipleLocator(50))

    # Axis limits
    min_x, max_x = avg_df["count_decode"].min(), avg_df["count_decode"].max()
    plt.xlim(0, max_x + 10)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=500, bbox_inches="tight")
        print(f"✅ Plot saved to {save_path}")
    else:
        plt.show()


def plot_combined_graph(df1, df2, df3, title="Combined Plot", save_path=None):
    """
    Plot all three graphs (from 3 DataFrames) on one combined figure.
    - df1: must contain ['count_decode', 'time_diff']  (in ns)
    - df2, df3: must contain ['count_decode', 'sum_elapsed_time_ms']
    """

    # --- Validation ---
    if not {"count_decode", "time_diff"}.issubset(df1.columns):
        raise ValueError("df1 must contain 'count_decode' and 'time_diff' columns")
    for i, df in enumerate([df2, df3], start=2):
        if not {"count_decode", "sum_elapsed_time_ms"}.issubset(df.columns):
            raise ValueError(
                f"df{i} must contain 'count_decode' and 'sum_elapsed_time_ms' columns"
            )

    # --- Preprocessing ---
    df1 = df1.sort_values("count_decode").copy()
    df2 = df2.sort_values("count_decode").copy()
    df3 = df3.sort_values("count_decode").copy()

    # Convert df1 time_diff from ns → ms
    df1["time_diff_ms"] = df1["time_diff"] / 1e6

    # --- Plot ---
    fig, ax1 = plt.subplots(figsize=(6, 2.8))

    # Plot 1: time_diff_ms (left Y-axis)
    (p1,) = ax1.plot(
        df1["count_decode"],
        df1["time_diff_ms"],
        color="royalblue",
        linewidth=0.8,
        label="Entire decoding iteration",
    )
    ax1.set_xlabel("Decoding iterations")
    ax1.set_ylabel("Elapsed time (ms)")
    ax1.tick_params(axis="y")
    ax1.xaxis.set_major_locator(MultipleLocator(50))
    ax1.set_xlim(0, df1["count_decode"].max() + 10)
    x = 5
    y_start = df1["time_diff_ms"].min()
    y_end = df1["time_diff_ms"].max()
    # ax1.axhline(y=y_end, linewidth=1, linestyle="--")
    ax1.hlines(
        y=y_end, xmin=0, xmax=430, linewidth=1, linestyle="--", colors="royalblue"
    )
    ax1.annotate(
        # f"{df1['time_diff_ms'].iloc[-1] - df1['time_diff_ms'].iloc[0]} ms",
        "",
        xy=(x, y_end),
        xytext=(x, y_start),
        arrowprops=dict(
            arrowstyle="<->", linewidth=0.8, mutation_scale=7, color="royalblue"
        ),
    )
    ax1.annotate(
        f"{y_end - y_start:.2f} ms",
        xy=(x, (y_start + y_end) / 2),
        xytext=(3, 0),
        textcoords="offset points",
        va="center",
        ha="left",
        rotation=90,
        color="royalblue",
    )
    ax1.grid(linewidth=0.5, linestyle="--")

    # Plot 2 & 3: sum_elapsed_time_ms (right Y-axis)
    ax2 = ax1.twinx()
    (p2,) = ax2.plot(
        df2["count_decode"],
        df2["sum_elapsed_time_ms"],
        color="springgreen",
        linewidth=0.8,
        label="Sum of KQ",
    )
    x = 400
    y_start = df2["sum_elapsed_time_ms"].min()
    y_end = df2["sum_elapsed_time_ms"].max()
    ax2.hlines(
        y=y_end, xmin=400, xmax=450, linewidth=1, linestyle="--", color="springgreen"
    )
    ax2.annotate(
        # f"{df1['time_diff_ms'].iloc[-1] - df1['time_diff_ms'].iloc[0]} ms",
        "",
        xy=(x, y_end),
        xytext=(x, y_start),
        arrowprops=dict(
            arrowstyle="<->", linewidth=0.8, mutation_scale=7, color="springgreen"
        ),
    )
    ax2.annotate(
        f"{y_end - y_start:.2f} ms",
        xy=(x, (y_start + y_end) / 2),
        xytext=(3, 0),
        textcoords="offset points",
        va="center",
        ha="left",
        rotation=90,
        color="springgreen",
    )
    (p3,) = ax2.plot(
        df3["count_decode"],
        df3["sum_elapsed_time_ms"],
        color="coral",
        linewidth=0.8,
        label="Sum of KQV",
    )
    x = 420
    y_start = df3["sum_elapsed_time_ms"].min()
    y_end = df3["sum_elapsed_time_ms"].max()
    ax2.hlines(y=y_end, xmin=420, xmax=450, linewidth=1, linestyle="--", color="coral")
    ax2.annotate(
        # f"{df1['time_diff_ms'].iloc[-1] - df1['time_diff_ms'].iloc[0]} ms",
        "",
        xy=(x, y_end),
        xytext=(x, y_start),
        arrowprops=dict(
            arrowstyle="<->", linewidth=0.8, mutation_scale=7, color="coral"
        ),
    )
    ax2.annotate(
        f"{y_end - y_start:.2f} ms",
        xy=(x, (y_start + y_end) / 2),
        xytext=(3, 0),
        textcoords="offset points",
        va="center",
        ha="left",
        rotation=90,
        color="coral",
    )
    ax2.set_ylabel("Sum of the OPs' time (ms)")
    ax2.tick_params(axis="y")

    ax1.set_ylim([118, 123])
    ax2.set_ylim([0, 5])
    # --- Combine legends ---
    lines = [p1, p2, p3]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)

    # plt.title(title)
    plt.tight_layout()

    # --- Save or Show ---
    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        print(f"✅ Combined plot saved to {save_path}")
    else:
        plt.show()


def plot_combined_logy(
    df1, df2, df3, title="Combined Plot (Log Scale)", save_path=None
):
    """
    Plot 3 datasets on a single graph (shared Y-axis, log scale).

    - df1: must contain ['count_decode', 'time_diff']  (in ns)
    - df2, df3: must contain ['count_decode', 'sum_elapsed_time_ms']
    """

    # --- Validation ---
    if not {"count_decode", "time_diff"}.issubset(df1.columns):
        raise ValueError("df1 must contain 'count_decode' and 'time_diff'")
    for i, df in enumerate([df2, df3], start=2):
        if not {"count_decode", "sum_elapsed_time_ms"}.issubset(df.columns):
            raise ValueError(
                f"df{i} must contain 'count_decode' and 'sum_elapsed_time_ms'"
            )

    # --- Preprocess ---
    df1 = df1.sort_values("count_decode").copy()
    df2 = df2.sort_values("count_decode").copy()
    df3 = df3.sort_values("count_decode").copy()

    df1["time_diff_ms"] = df1["time_diff"] / 1e6  # ns → ms

    # --- Plot ---
    plt.figure(figsize=(9, 5))
    plt.plot(
        df1["count_decode"],
        df1["time_diff_ms"],
        color="tab:royalblue",
        linewidth=0.8,
        label="Time Diff (ms)",
    )
    plt.plot(
        df2["count_decode"],
        df2["sum_elapsed_time_ms"],
        color="tab:orange",
        linewidth=0.8,
        label="Avg Elapsed 1 (ms)",
    )
    plt.plot(
        df3["count_decode"],
        df3["sum_elapsed_time_ms"],
        color="tab:green",
        linewidth=0.8,
        label="Avg Elapsed 2 (ms)",
    )

    plt.xlabel("Iterations")
    plt.ylabel("Time (ms)")
    plt.title(title)

    # --- Log scale on Y-axis ---
    plt.yscale("log")

    # --- X-axis settings ---
    ax = plt.gca()
    ax.xaxis.set_major_locator(MultipleLocator(50))
    min_x, max_x = df1["count_decode"].min(), df1["count_decode"].max()
    plt.xlim(0, max_x + 10)

    # --- Legend and layout ---
    plt.legend(loc="best")
    plt.grid(True, which="both", linestyle="--", linewidth=0.4, alpha=0.7)
    plt.tight_layout()

    # --- Save or Show ---
    if save_path:
        plt.savefig(save_path, dpi=500, bbox_inches="tight")
        print(f"✅ Combined log-scale plot saved to {save_path}")
    else:
        plt.show()


def plot_combined_broken_y(
    df1, df2, df3, title="Combined Broken-Y Plot", save_path=None
):
    """
    Plot 3 datasets with one X-axis and broken Y-axis, without extra horizontal lines or labels.
    """
    # --- Validation ---
    if not {"count_decode", "time_diff"}.issubset(df1.columns):
        raise ValueError("df1 must contain 'count_decode' and 'time_diff'")
    for i, df in enumerate([df2, df3], start=2):
        if not {"count_decode", "sum_elapsed_time_ms"}.issubset(df.columns):
            raise ValueError(
                f"df{i} must contain 'count_decode' and 'sum_elapsed_time_ms'"
            )

    # --- Preprocess ---
    df1 = df1.sort_values("count_decode").copy()
    df2 = df2.sort_values("count_decode").copy()
    df3 = df3.sort_values("count_decode").copy()
    df1["time_diff_ms"] = df1["time_diff"] / 1e6  # ns → ms

    # --- Create subplots for broken axis ---
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, sharex=True, figsize=(9, 6), gridspec_kw={"height_ratios": [1, 1]}
    )

    # --- Plot Top Axis (high values) ---
    ax_top.plot(
        df1["count_decode"],
        df1["time_diff_ms"],
        color="tab:blue",
        linewidth=0.8,
        label="Time Diff (ms)",
    )
    ax_top.plot(
        df2["count_decode"],
        df2["sum_elapsed_time_ms"],
        color="tab:orange",
        linewidth=0.8,
        label="Sum Elapsed time kq (ms)",
    )
    ax_top.plot(
        df3["count_decode"],
        df3["sum_elapsed_time_ms"],
        color="tab:green",
        linewidth=0.8,
        label="Sum Elapsed time kqv (ms)",
    )
    ax_top.set_ylim(110, 120)
    ax_top.spines["bottom"].set_visible(False)  # hide bottom spine
    ax_top.tick_params(bottom=False)  # hide bottom ticks
    ax_top.yaxis.set_major_locator(MultipleLocator(1))

    # --- Plot Bottom Axis (low values) ---
    ax_bottom.plot(
        df1["count_decode"], df1["time_diff_ms"], color="tab:blue", linewidth=0.8
    )
    ax_bottom.plot(
        df2["count_decode"],
        df2["sum_elapsed_time_ms"],
        color="tab:orange",
        linewidth=0.8,
    )
    ax_bottom.plot(
        df3["count_decode"],
        df3["sum_elapsed_time_ms"],
        color="tab:green",
        linewidth=0.8,
    )
    ax_bottom.set_ylim(0, 4)
    ax_bottom.spines["top"].set_visible(False)  # hide top spine
    ax_bottom.tick_params(top=False)  # hide top ticks
    ax_bottom.yaxis.set_major_locator(MultipleLocator(1))

    # --- X-axis ---
    ax_bottom.set_xlabel("Iterations")
    ax_top.set_ylabel("Time (ms)")
    ax_bottom.set_ylabel("Time (ms)")

    # X-axis tick every 50
    ax_bottom.xaxis.set_major_locator(MultipleLocator(50))
    max_x = max(
        df1["count_decode"].max(), df2["count_decode"].max(), df3["count_decode"].max()
    )
    ax_bottom.set_xlim(0, max_x + 10)

    # --- Add diagonal lines to indicate break ---
    d = 0.005  # size of diagonal lines
    kwargs = dict(transform=ax_top.transAxes, color="k", clip_on=False)
    ax_top.plot((-d, +d), (-d, +d), **kwargs)  # top-left
    ax_top.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # top-right

    kwargs.update(transform=ax_bottom.transAxes)  # switch to bottom axes
    ax_bottom.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # bottom-left
    ax_bottom.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)  # bottom-right

    # --- Legend ---
    ax_top.legend(loc="best")

    plt.suptitle(title)
    plt.tight_layout()

    # --- Save or Show ---
    if save_path:
        plt.savefig(save_path, dpi=500, bbox_inches="tight")
        print(f"✅ Broken-Y plot saved to {save_path}")
    else:
        plt.show()


def plot_throughput(
    results_df: pd.DataFrame,
    title: str = "Prompts_per_Time vs Prompts",
    save_path: str = None,
):
    """
    Plot n_prompt vs (n_prompt / time_difference) throughput graph
    with non-overlapping x-axis labels
    """
    if results_df.empty:
        print("DataFrame is empty")
        return

    # Check if required columns exist
    if (
        "n_prompt" not in results_df.columns
        or "time_difference_ms" not in results_df.columns
    ):
        print("Error: DataFrame must contain 'n_prompt' and 'time_difference' columns")
        return

    # Sort by n_prompt for better visualization
    df_sorted = results_df.sort_values("n_prompt")

    # Calculate throughput: n_prompt / time_difference
    throughput = df_sorted["n_prompt"] / df_sorted["time_difference_ms"]
    # print(f"  throughput: {throughput}")

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Plot scatter points and line
    plt.scatter(
        df_sorted["n_prompt"], throughput, s=60, color="blue", label="Data points"
    )
    plt.plot(
        df_sorted["n_prompt"], throughput, "b-", alpha=0.7, linewidth=1, label="Trend"
    )

    # Customize the plot
    plt.xlabel("n_prompt", fontsize=12)
    plt.ylabel("Throughput (n_prompt / time_ms)", fontsize=12)
    plt.title(title, fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Set x-axis ticks with step of 10 and prevent overlapping
    min_n_prompt = df_sorted["n_prompt"].min()
    max_n_prompt = df_sorted["n_prompt"].max()

    # Create x-axis ticks with step of 10
    start = (min_n_prompt // 10) * 10
    end = ((max_n_prompt // 10) + 1) * 10
    x_ticks = list(range(start, end + 1, 10))

    plt.xticks(x_ticks, rotation=45)  # Rotate labels to prevent overlapping

    # Adjust layout to make room for rotated labels
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=500, bbox_inches="tight")
        print(f"✅ Plot saved to {save_path}")
    else:
        plt.show()
