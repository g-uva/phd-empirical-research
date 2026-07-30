from typing import Callable
import pandas as pd
import numpy as np
import os
from tqdm import tqdm


def get_timestamp(event: str):
    if "ts" in event:
        return get_value_by_key(event, "ts")
    else:
        return float("inf")


def get_value_by_key(line: str, key: str, data_type: Callable = int):
    assert key in line, f"{key} is not in the line {line}"
    return data_type(line.split(f"{key}:")[1].split(",")[0].strip())


def create_perf_df_from_trace(trace_file: str) -> pd.DataFrame:
    csv_path = ""
    if trace_file.endswith(".txt"):
        csv_path = f"{trace_file.split('.txt')[0]}.csv"
    elif trace_file.endswith(".csv"):
        csv_path = trace_file
    if os.path.exists(csv_path):
        # print("Read from csv file instead.")
        df = pd.read_csv(csv_path, index_col=0)
        if "count_decode" in df.columns:
            return df
        else:
            # print("Generate decode counts")
            df_sorted = df.sort_values("ts")
            df_sorted.reset_index(drop=True, inplace=True)
            # decode_indices = df_sorted[
            #     (df_sorted["func"] == "llama_decode") & (df_sorted["pos"] == "start")
            # ].index
            decode_indices = df_sorted[df_sorted["type"] == 10].index.to_numpy()
            decode_indices = np.append(decode_indices, len(df_sorted))
            df_sorted["count_decode"] = pd.cut(
                df_sorted.index,
                bins=decode_indices,
                labels=range(0, len(decode_indices) - 1),
                right=False,
            )
            return df_sorted

    print(f"Starting parsing the file {trace_file}")
    with open(trace_file, "r") as f_trace:
        lines = f_trace.readlines()
    lines.sort(key=get_timestamp)
    res = {}
    count_llama_decode = 0
    for i, line in enumerate(tqdm(lines)):
        if not line.startswith("ts"):
            continue
        if (
            get_value_by_key(line, "func", str) == "llama_decode"
            and get_value_by_key(line, "pos", str) == "start"
        ):
            count_llama_decode += 1
            # print(f"Found {count_llama_decode} llama decode")
        if count_llama_decode > 1:
            res[i] = {}
            res[i]["ts"] = get_value_by_key(line, "ts")
            res[i]["func"] = get_value_by_key(line, "func", str)
            res[i]["pos"] = get_value_by_key(line, "pos", str)
            res[i]["pid"] = get_value_by_key(line, "pid", str)
            res[i]["pmc"] = get_value_by_key(line, "pmc")
            res[i]["count_decode"] = count_llama_decode
            if "op" in line and "parm_addr" in line:
                res[i]["op"] = get_value_by_key(line, "op")
                res[i]["parm_addr"] = get_value_by_key(line, "parm_addr")
            if "ne0" in line:
                for j in range(4):
                    res[i][f"ne{j}"] = get_value_by_key(line, f"ne{j}")
                    res[i][f"src1_ne{j}"] = get_value_by_key(line, f"src1_ne{j}")
                    res[i][f"src2_ne{j}"] = get_value_by_key(line, f"src2_ne{j}")

    return pd.DataFrame.from_dict(res, orient="index")


def parse_ops_one_iter(
    df: pd.DataFrame,
    is_prefill: bool = False,
    n_iter: int = 3,
):
    if is_prefill:
        n_iter = 2
    df_iter = df[df["count_decode"] == n_iter].reset_index(drop=True)
    assert (
        20 in df_iter["type"].values
    ), f"There is no operator data in {n_iter}th iteration."
    dfs_iter_pid_start = dict(tuple(df_iter[df_iter["type"] == 20].groupby("pid")))
    dfs_iter_pid_end = dict(tuple(df_iter[df_iter["type"] == 25].groupby("pid")))
    if "parm_addr" in df.columns:
        num_nodes = len(
            list(set(df_iter[df_iter["type"] == 20]["parm_addr"].to_list()))
        )
        assert all(len(d) == num_nodes for d in dfs_iter_pid_start.values()) and all(
            len(d) == num_nodes for d in dfs_iter_pid_end.values()
        ), f"There are some nodes missing in the {n_iter}th iteration, please choose another decoding iteration."
    else:
        assert (df_iter["type"] == 20).sum() == (
            df_iter["type"] == 25
        ).sum(), f"There are some nodes missing in the {n_iter}th iteration, please choose another decoding iteration."

    start_ts = np.min(
        np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_start.values()], axis=1),
        axis=1,
    )
    end_ts = np.max(
        np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_end.values()], axis=1),
        axis=1,
    )
    if "pmc_0" in df.columns:
        pmc_0 = np.sum(
            np.stack(
                [
                    dfs_iter_pid_end[pid]["pmc_0"].to_numpy() - d["pmc_0"].to_numpy()
                    for pid, d in dfs_iter_pid_start.items()
                ],
                axis=1,
            ),
            axis=1,
        )
        pmc_1 = np.sum(
            np.stack(
                [
                    dfs_iter_pid_end[pid]["pmc_1"].to_numpy() - d["pmc_1"].to_numpy()
                    for pid, d in dfs_iter_pid_start.items()
                ],
                axis=1,
            ),
            axis=1,
        )
    elapsed_time = (end_ts - start_ts) / 1e6
    # TODO: Include PMU counters
    df_iter_pid_start = list(dfs_iter_pid_start.values())[0]
    df_iter_pid_start.reset_index(drop=True, inplace=True)
    df_iter_pid_start["elapsed_time"] = elapsed_time
    if "pmc_0" in df.columns:
        df_iter_pid_start["pmc_0"] = pmc_0
        df_iter_pid_start["pmc_1"] = pmc_1
    return df_iter_pid_start.drop(columns=["ts", "pid", "cpu", "type"])


def parse_ops_all_iters(df: pd.DataFrame, is_prefill: bool = False) -> pd.DataFrame:
    """
    Parse all iterations with count_decode >= 2 and compute elapsed_time for each.

    Args:
        df (pd.DataFrame): Input DataFrame containing 'ts', 'type', 'pid', 'count_decode', etc.
        is_prefill (bool): If True, skips prefill iteration handling (optional).

    Returns:
        pd.DataFrame: Combined DataFrame with columns:
                      ['pmc', 'pmc_hw', 'guid', 'op', 'name', 'count_decode', 'elapsed_time']
    """
    # Filter to only relevant iterations
    df = df[df["count_decode"] >= 2].reset_index(drop=True)

    # Collect all results here
    results = []

    # Loop through each unique count_decode value
    for n_iter in sorted(df["count_decode"].unique()):
        df_iter = df[df["count_decode"] == n_iter].reset_index(drop=True)

        if 20 not in df_iter["type"].values:
            print(f"⚠️ Skipping iteration {n_iter}: no operator data (type 20).")
            continue

        dfs_iter_pid_start = dict(tuple(df_iter[df_iter["type"] == 20].groupby("pid")))
        dfs_iter_pid_end = dict(tuple(df_iter[df_iter["type"] == 25].groupby("pid")))

        # Check that both start and end types are present
        if not dfs_iter_pid_start or not dfs_iter_pid_end:
            print(f"⚠️ Skipping iteration {n_iter}: missing type 20 or 25.")
            continue

        if "parm_addr" in df.columns:
            num_nodes = len(set(df_iter[df_iter["type"] == 20]["parm_addr"].to_list()))
            if not all(
                len(d) == num_nodes for d in dfs_iter_pid_start.values()
            ) or not all(len(d) == num_nodes for d in dfs_iter_pid_end.values()):
                print(f"⚠️ Skipping iteration {n_iter}: incomplete node data.")
                continue
        else:
            if (df_iter["type"] == 20).sum() != (df_iter["type"] == 25).sum():
                print(f"⚠️ Skipping iteration {n_iter}: mismatch in start/end counts.")
                continue

        # Compute elapsed time between type 20 and 25 per pid
        start_ts = np.min(
            np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_start.values()], axis=1),
            axis=1,
        )
        end_ts = np.max(
            np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_end.values()], axis=1),
            axis=1,
        )
        elapsed_time = (end_ts - start_ts) / 1e6  # ns → ms

        df_iter_pid_start = list(dfs_iter_pid_start.values())[0]
        df_iter_pid_start.reset_index(drop=True, inplace=True)
        df_iter_pid_start["elapsed_time"] = elapsed_time

        # Append results
        results.append(df_iter_pid_start.drop(columns=["ts", "pid", "cpu", "type"]))

    # Combine all iteration results
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        print("⚠️ No valid iterations found with count_decode >= 2.")
        return pd.DataFrame()


def compute_sum_elapsed_by_name(df: pd.DataFrame, name_prefix: str) -> pd.DataFrame:
    """
    Compute total (summed) elapsed_time for names starting with a given prefix per count_decode.
    If a sum is 0, replace it with the previous non-zero sum value.

    Args:
        df (pd.DataFrame): DataFrame with columns ['name', 'count_decode', 'elapsed_time'].
        name_prefix (str): Prefix to filter names (e.g., 'kq-', 'kqv-', etc.)

    Returns:
        pd.DataFrame: DataFrame with ['count_decode', 'sum_elapsed_time_ms'].
    """
    required = {"name", "count_decode", "elapsed_time"}
    if not required.issubset(df.columns):
        raise ValueError(f"Input DataFrame must contain columns: {required}")

    import re

    pattern = f"^{re.escape(name_prefix)}\\d+$"

    # Filter rows matching the name pattern
    df_filtered = df[df["name"].str.match(pattern, case=False, na=False)].copy()

    if df_filtered.empty:
        print(f"⚠️ No entries found with names starting with '{name_prefix}'")
        return pd.DataFrame()

    # Group by count_decode and compute the sum of elapsed_time
    sum_df = (
        df_filtered.groupby("count_decode", as_index=False)["elapsed_time"]
        .sum()
        .rename(columns={"elapsed_time": "sum_elapsed_time_ms"})
        .sort_values("count_decode")
        .reset_index(drop=True)
    )

    # Replace zeros with previous non-zero values
    previous_value = None
    for i, value in enumerate(sum_df["sum_elapsed_time_ms"]):
        if value == 0 and previous_value is not None:
            sum_df.at[i, "sum_elapsed_time_ms"] = previous_value
        else:
            previous_value = value

    return sum_df


def compute_type10_15_diff(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute time difference between rows of type == 10 and the next immediate type == 15,
    only when type 10 count_decode >= 2.

    If (current raw_time_diff - previous raw_time_diff) > 10_000_000,
    replace current raw_time_diff with previous raw_time_diff.

    Returns:
        pd.DataFrame with columns:
        ['ts_type_10', 'ts_type_15', 'pid_type_10', 'pid_type_15',
         'count_decode', 'raw_time_diff', 'time_diff']
    """
    df = df.sort_values(by="ts").reset_index(drop=True)

    results = []
    prev_raw_diff = None  # store previous raw_time_diff

    for i, row in df[df["type"] == 10].iterrows():
        # Only consider type 10 with count_decode >= 2
        if row["count_decode"] < 2:
            continue

        ts_10 = row["ts"]
        pid_10 = row["pid"]
        count_decode_10 = row["count_decode"]

        # Find next type 15 after this index
        next_15 = df[(df.index > i) & (df["type"] == 15)]
        if next_15.empty:
            continue

        ts_15 = next_15.iloc[0]["ts"]
        pid_15 = next_15.iloc[0]["pid"]

        # Calculate raw diff
        raw_time_diff = ts_15 - ts_10

        # Replace if large jump from previous raw diff
        if prev_raw_diff is not None and (raw_time_diff - prev_raw_diff) > 1_000_000:
            time_diff = prev_raw_diff
        else:
            time_diff = raw_time_diff

        # Update previous raw diff for next iteration
        prev_raw_diff = raw_time_diff

        results.append(
            {
                "ts_type_10": ts_10,
                "ts_type_15": ts_15,
                "pid_type_10": pid_10,
                "pid_type_15": pid_15,
                "count_decode": count_decode_10,
                "raw_time_diff": raw_time_diff,
                "time_diff": time_diff,
            }
        )

    return pd.DataFrame(results)
