"""
Analyze the trace file and generate a DAG for the model
"""

from utils.args import get_args
from utils.json import read_from_json
from utils.parse import get_timestamp, get_value_by_key, create_perf_df_from_trace
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np

node_markers = {
    "GGML_OP_MUL_MAT": "o",
    "GGML_OP_MUL_MAT_ID": "v",
    "GGML_OP_TRANSPOSE": "^",
    "GGML_OP_GET_ROWS": "<",
    "GGML_OP_ADD": ">",
    "GGML_OP_MUL": "8",
    "GGML_OP_SOFT_MAX": "s",
    "GGML_OP_ROPE": "p",
    "GGML_OP_UNARY": "h",
    "GGML_OP_RMS_NORM": "H",
    "GGML_OP_CPY": "D",
    "GGML_OP_CONT": "d",
    "GGML_OP_RESHAPE": "P",
    "GGML_OP_VIEW": "X",
    "GGML_OP_PERMUTE": "*",
}

MAX_NE_DIM = 3


def get_ops_list(ops_dict: dict, lines: list) -> tuple:
    ops_all = [
        int(line.split("op:")[1].split(",")[0]) for line in lines if "op" in line
    ]
    ops_all = list(set(ops_all))
    ops_list = [ops_dict["names"][i] for i in ops_all]
    return ops_all, ops_list


def get_ops_list_from_df(ops_dict: dict, df: pd.DataFrame) -> tuple:
    ops_all = list(set(df["op"].to_list()))
    ops_list = [ops_dict["names"][i] for i in ops_all]
    return ops_all, ops_list


def get_nodes(
    lines: list, ops_list: list, node_ids: list, is_prefill: bool = False
) -> tuple:
    nodes = defaultdict(dict)
    node_addrs = []
    node_order_id = 0
    decode_cnt = 0
    target_decode_cnt = 2 if is_prefill else 3
    for i, line in enumerate(lines):
        func_name = get_value_by_key(line, "func", str)
        pos = get_value_by_key(line, "pos", str)
        if func_name == "llama_decode" and pos == "start":
            decode_cnt += 1
            continue
        if func_name == "llama_decode" and pos == "end":
            continue
        if func_name == "ggml_compute_forward" and pos == "end":
            continue

        if decode_cnt != target_decode_cnt:
            continue
        if "op:" not in line:
            continue
        op = get_value_by_key(line, "op")
        cur_addr = get_value_by_key(line, "parm_addr")
        first_src_addr = get_value_by_key(line, "first_src_addr")
        second_src_addr = get_value_by_key(line, "second_src_addr")
        ne = [get_value_by_key(line, f"ne{i}") for i in range(MAX_NE_DIM)]
        src1_ne = [get_value_by_key(line, f"src1_ne{i}") for i in range(MAX_NE_DIM)]
        src2_ne = [get_value_by_key(line, f"src2_ne{i}") for i in range(MAX_NE_DIM)]
        assert (
            "ggml_compute_forward" in line
        ), f"Line {line} is not for ggml_compute_forward_start"
        pid = get_value_by_key(line, "pid")
        ts_start = get_value_by_key(line, "ts")
        ## FIXME: This will only work for 2 threads
        for sub_line in lines[(i + 1) :]:
            if "ggml_compute_forward" in sub_line and "pos:end" in sub_line:
                pid_2 = get_value_by_key(sub_line, "pid")
                ts_end = get_value_by_key(sub_line, "ts")
                if pid_2 == pid:
                    nodes[cur_addr]["runtime_ms"] = (ts_end - ts_start) / 1e6
                    break
        nodes[cur_addr]["op"] = ops_list[op].split("GGML_OP_")[1]
        nodes[cur_addr]["first_src"] = first_src_addr
        nodes[cur_addr]["second_src"] = second_src_addr
        nodes[cur_addr]["output_size"] = ne
        nodes[cur_addr]["src1_size"] = src1_ne
        nodes[cur_addr]["src2_size"] = src2_ne
        if cur_addr not in node_addrs:
            node_addrs.append(cur_addr)
            nodes[cur_addr]["order_id"] = node_order_id
            node_order_id += 1
    print(f"There are {len(node_addrs)} nodes in total")
    selected_node_addrs = [node_addrs[id] for id in node_ids]
    print(f"length of selected nodes {len(selected_node_addrs)}")
    sub_nodes = {addr: nodes[addr] for addr in selected_node_addrs}
    return nodes, sub_nodes


def get_nodes_from_df(
    df: pd.DataFrame,
    ops_list: list,
    node_ids: list,
    is_prefill: bool = False,
    n_iter: int = 4,
):
    """
    Get the nodes from a dataframe.
    Args:
        df:
    """
    nodes = defaultdict(dict)
    if is_prefill:
        n_iter = 2
    df_iter = df[df["count_decode"] == n_iter].reset_index(drop=True)
    assert (
        20 in df_iter["type"].values
    ), f"There is no operator data in {n_iter}th iteration."
    num_nodes = len(list(set(df_iter[df_iter["type"] == 20]["parm_addr"].to_list())))
    dfs_iter_pid_start = dict(tuple(df_iter[df_iter["type"] == 20].groupby("pid")))
    dfs_iter_pid_end = dict(tuple(df_iter[df_iter["type"] == 25].groupby("pid")))
    assert all(len(d) == num_nodes for d in dfs_iter_pid_start.values()) and all(
        len(d) == num_nodes for d in dfs_iter_pid_end.values()
    ), f"There are some nodes missing in the {n_iter}th iteration, please choose another decoding iteration."
    start_ts = np.min(
        np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_start.values()], axis=1),
        axis=1,
    )
    end_ts = np.min(
        np.stack([d["ts"].to_numpy() for d in dfs_iter_pid_end.values()], axis=1),
        axis=1,
    )
    elapsed_time_ms = (end_ts - start_ts) / 1e6

    df_iter_pid_start = list(dfs_iter_pid_start.values())[0]
    df_iter_pid_start.reset_index(drop=True, inplace=True)
    # PMC
    if "pmc_0" in df_iter_pid_start.columns:
        pmcs_0 = np.sum(
            [
                dfs_iter_pid_end[pid]["pmc_0"].to_numpy() - df["pmc_0"].to_numpy()
                for pid, df in dfs_iter_pid_start.items()
            ],
            axis=0,
        )
        pmcs_ps_0 = np.sum(
            [
                (dfs_iter_pid_end[pid]["pmc_0"].to_numpy() - df["pmc_0"].to_numpy())
                * 1e9
                / (dfs_iter_pid_end[pid]["ts"].to_numpy() - df["ts"].to_numpy())
                for pid, df in dfs_iter_pid_start.items()
            ],
            axis=0,
        )
    if "pmc_1" in df_iter_pid_start.columns:
        pmcs_1 = np.sum(
            [
                dfs_iter_pid_end[pid]["pmc_1"].to_numpy() - df["pmc_1"].to_numpy()
                for pid, df in dfs_iter_pid_start.items()
            ],
            axis=0,
        )
        pmcs_ps_1 = np.sum(
            [
                (dfs_iter_pid_end[pid]["pmc_1"].to_numpy() - df["pmc_1"].to_numpy())
                * 1e9
                / (dfs_iter_pid_end[pid]["ts"].to_numpy() - df["ts"].to_numpy())
                for pid, df in dfs_iter_pid_start.items()
            ],
            axis=0,
        )
    for i, row in df_iter_pid_start.iterrows():
        key = int(row["parm_addr"])
        nodes[key]["runtime_ms"] = elapsed_time_ms[i]
        nodes[key]["op"] = ops_list[row["op"]].split("GGML_OP_")[1]
        nodes[key]["name"] = row["name"]
        nodes[key]["first_src"] = row["first_src_addr"]
        nodes[key]["second_src"] = row["second_src_addr"]
        nodes[key]["output_size"] = [row[f"ne{i}"] for i in range(MAX_NE_DIM)]
        nodes[key]["src1_size"] = [row[f"src0_ne{i}"] for i in range(MAX_NE_DIM)]
        nodes[key]["src2_size"] = [row[f"src1_ne{i}"] for i in range(MAX_NE_DIM)]
        nodes[key]["order_id"] = i
        if "pmc_0" in df_iter_pid_start.columns:
            nodes[key]["pmc_diff_0"] = (
                pmcs_0[i] * 16 / 1024 / 1024
            )  # MB with 64B for each cacheline
            nodes[key]["pmc_diff_ps_0"] = (
                pmcs_0[i] * 16 / 1024 / 1024 / (elapsed_time_ms[i] / 1000)
            )
        if "pmc_1" in df_iter_pid_start.columns:
            nodes[key]["pmc_diff_1"] = pmcs_1[i] * 64 / 1024 / 1024
            nodes[key]["pmc_diff_ps_1"] = (
                pmcs_1[i] * 64 / 1024 / 1024 / (elapsed_time_ms[i] / 1000)
            )
        if (
            "pmc_0" in df_iter_pid_start.columns
            and "pmc_1" in df_iter_pid_start.columns
        ):
            nodes[key]["pmc_diff_all"] = (
                pmcs_0[i] * 16 / 1024 / 1024 + pmcs_1[i] * 64 / 1024 / 1024
            )
            nodes[key]["pmc_diff_ps_all"] = nodes[key]["pmc_diff_all"] / (
                elapsed_time_ms[i] / 1000
            )
            nodes[key]["pmc_mean_ps_all"] = (
                pmcs_ps_0[i] * 16 / 1024 / 1024 + pmcs_ps_1[i] * 64 / 1024 / 1024
            )
        if nodes[key]["op"] == "MUL_MAT_ID":
            print("MoE!!")
            nodes[key]["third_src"] = row["third_src_addr"]
            nodes[key]["src3_size"] = [row[f"src2_ne{i}"] for i in range(MAX_NE_DIM)]
    node_addrs = df_iter_pid_start["parm_addr"].to_list()
    node_addrs.append(0)  # Add a virtual output node
    selected_node_addrs = [node_addrs[id] for id in node_ids]
    sub_nodes = {addr: nodes[addr] for addr in selected_node_addrs}
    return nodes, sub_nodes
    # min_ts = pd.concat([d["ts"] for d in groups_by_pid.values()], axis=1).min(axis=1)
    # print(min_ts)
    # for pid, df_iter_pid in df_iter.groupby("pid"):


def build_graph_from_nodes(nodes: dict) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node, value in nodes.items():
        if node == 0:
            continue
        graph.add_edge(value["first_src"], node)
        # if value["first_src"] in nodes:
        #     graph.edges[(value["first_src"], node)]["dim"] = nodes[value["first_src"]][
        #         "output_size"
        #     ]
        graph.edges[(value["first_src"], node)]["dim"] = value["src1_size"]
        if (
            value["second_src"] != 0
        ):  # FIXME: This is not robust, as it could be some garbage value
            graph.add_edge(value["second_src"], node)
            # if value["second_src"] in nodes:
            #     graph.edges[(value["second_src"], node)]["dim"] = nodes[
            #         value["second_src"]
            #     ]["output_size"]
            graph.edges[(value["second_src"], node)]["dim"] = value["src2_size"]
        if "third_src" in value.keys():
            print(value["third_src"])
            graph.add_edge(value["third_src"], node)
            graph.edges[(value["third_src"], node)]["dim"] = value["src3_size"]
    # Add a virtual output node
    if 0 in nodes.keys():
        last_node = list(nx.topological_sort(graph))[-1]
        graph.add_edge(last_node, 0)
        graph.edges[(last_node, 0)]["dim"] = nodes[last_node]["output_size"]
        nodes[0]["order_id"] = "Out"
        nodes[0]["runtime_ms"] = 0
        nodes[0]["op"] = "Output"
    print(f"Number of nodes is {int(graph.number_of_nodes())}")
    return graph


def get_nodes_with_input(graph: nx.DiGraph, non_op_tensors_addr: list):
    # Make sure that the graph is with data tensor
    nodes_with_input = []
    nodes_without_input = []
    for node in graph.nodes():
        if node in non_op_tensors_addr:
            continue
        predecessors = list(graph.predecessors(node))
        if any([n in non_op_tensors_addr for n in predecessors]):
            nodes_with_input.append(node)
        else:
            nodes_without_input.append(node)
    return nodes_with_input, nodes_without_input


def main():
    args = get_args()
    config_file = args.config
    config = read_from_json(config_file, cat="ops")
    start_node_id = config["start_node_id"]
    end_node_id = config["end_node_id"]
    ops_dict = read_from_json(config["ops_file"])
    trace_file: str = config["trace_file"]
    target_iter = config["target_iter"]
    figsize = config["figsize"]
    cmap = config["cmap"]
    assert len(figsize) == 2, "Length of figsize must be 2."
    if trace_file.endswith("txt"):
        with open(trace_file, "r") as tfile:
            lines = tfile.readlines()
        ops_all, ops_list = get_ops_list(ops_dict, lines)
        print("The types of operations inside the model are: ", ", ".join(ops_list))
        lines.sort(key=get_timestamp)
        allnodes, nodes = get_nodes(
            lines,
            ops_dict["names"],
            list(range(start_node_id, end_node_id + 1)),
            config["is_prefill"],
        )
    elif trace_file.endswith("csv"):
        df = create_perf_df_from_trace(trace_file)
        # df.to_csv("test.csv")
        ops_all, ops_list = get_ops_list_from_df(ops_dict, df)
        allnodes, nodes = get_nodes_from_df(
            df,
            ops_dict["names"],
            list(range(start_node_id, end_node_id + 1)),
            config["is_prefill"],
            n_iter=target_iter,
        )
    llama_graph = build_graph_from_nodes(nodes)
    result_dag = (
        "Graph is a DAG"
        if nx.is_directed_acyclic_graph(llama_graph)
        else "Graph is not a DAG"
    )
    print(result_dag)
    fig, ax = plt.subplots(figsize=(figsize[0], figsize[1]))
    print(f"Number of op tensors: {len(nodes)}")

    non_op_tensors_addr = [addr for addr in llama_graph.nodes() if addr not in nodes]
    output_path = (
        config["output_dir"]
        + f"/{config['model_name']}_with_non_op_nodes_"
        + f"{start_node_id}-{end_node_id}"
    )
    nodes_with_input, nodes_without_input = get_nodes_with_input(
        llama_graph, non_op_tensors_addr
    )
    if not config["with_data_tensor"]:
        for addr in non_op_tensors_addr:
            llama_graph.remove_node(addr)
            output_path = (
                config["output_dir"]
                + f"/{config['model_name']}_without_non_op_nodes_"
                + f"{start_node_id}-{end_node_id}"
            )
    if config["with_order"]:
        output_path += "_with_order"
    if config["is_prefill"]:
        output_path += "_prefill"
    metric_key = config["metric"]
    output_path += config["fig_format"]
    color_with_input = []
    color_without_input = []
    labels_with_input = defaultdict(int)
    labels_without_input = defaultdict(int)
    labels = defaultdict(int)
    metric = [n[metric_key] for n in nodes.values()]
    # norm = Normalize(vmin=min(metric), vmax=max(metric))
    # norm = LogNorm(vmin=0.003, vmax=1)
    norm = LogNorm(vmin=min(metric), vmax=max(metric))
    # colormap = plt.get_cmap("coolwarm")
    colormap = plt.get_cmap(cmap)
    all_markers = list(plt.Line2D.markers.keys())
    rest_markers = [
        m
        for m in all_markers
        if m not in node_markers.values() and m != "none" and m != "None"
    ]
    for node in llama_graph.nodes():
        if node not in nodes:
            labels[node] = -1
        else:
            labels[node] = f"{nodes[node]['order_id']}"
    # total_time = sum(runtimes)
    # print(f"Total time is {total_time:.4f} ms.")
    for node in llama_graph.nodes():
        # print(
        #     f"Node_{nodes[node]['order_id']}: {nodes[node]['runtime_ms'] * 100 /total_time:.4f}"
        # )
        if node in nodes_with_input:
            if node not in nodes:
                labels_with_input[node] = -1
                color_with_input.append((0, 0, 0, 1))
            elif config["with_order"]:
                labels_with_input[node] = (
                    f"{nodes[node]['name']}-{nodes[node]['order_id']}"
                )
                color_with_input.append(colormap(norm(nodes[node][metric_key])))
            else:
                labels_with_input[node] = nodes[node]["name"]
                color_with_input.append(colormap(norm(nodes[node][metric_key])))
        else:
            if node not in nodes:
                labels_without_input[node] = -1
                color_without_input.append((0, 0, 0, 1))
            elif config["with_order"]:
                labels_without_input[node] = (
                    f"{nodes[node]['name']}-{nodes[node]['order_id']}"
                )
                color_without_input.append(colormap(norm(nodes[node][metric_key])))
            else:
                labels_without_input[node] = nodes[node]["name"]
                color_without_input.append(colormap(norm(nodes[node][metric_key])))
    position = nx.nx_agraph.graphviz_layout(
        llama_graph,
        prog="dot",
        args="-Gminlen=3000 -Grankdir='LR' -Gnodesep=1.5",
    )
    nx_node_labels = nx.draw_networkx_labels(
        llama_graph, pos=position, ax=ax, labels=labels, font_size=8, font_color="k"
    )
    # for _, text in nx_node_labels.items():
    #     text.set_rotation(45)
    legend_elements = []
    for op in ops_list:
        if op in node_markers.keys():
            op_marker = node_markers[op]
        else:
            op_marker = rest_markers[0]
            del rest_markers[0]
            node_markers[op] = op_marker
        nodelist = [
            key for key, values in nodes.items() if f"GGML_OP_{values['op']}" == op
        ]
        if len(nodelist) > 0:
            # color = [colormap(norm(nodes[n]["runtime_ms"])) for n in nodelist]
            nx.draw(
                llama_graph,
                pos=position,
                ax=ax,
                nodelist=[n for n in nodelist if n in nodes_with_input],
                node_size=200,
                node_shape=op_marker,
                node_color=[
                    colormap(norm(nodes[n][metric_key]))
                    for n in nodelist
                    if n in nodes_with_input
                ],
                edgelist=[],
                edgecolors="black",
            )
            nx.draw(
                llama_graph,
                pos=position,
                ax=ax,
                nodelist=[n for n in nodelist if n in nodes_without_input],
                node_size=200,
                node_shape=op_marker,
                node_color=[
                    colormap(norm(nodes[n][metric_key]))
                    for n in nodelist
                    if n in nodes_without_input
                ],
                edgelist=[],
            )
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    marker=op_marker,
                    color="w",
                    markerfacecolor="lightblue",
                    markeredgecolor="k",
                    markersize=10,
                    label=op.split("GGML_OP_")[1],
                )
            )
    legend_elements.append(Line2D([0], [0], color="w"))
    legend_elements.append(
        Line2D(
            [0],
            [0],
            marker="o",
            markeredgecolor="k",
            markerfacecolor="lightpink",
            markersize=10,
            label="With constant data input",
        )
    )
    legend_elements.append(
        Line2D(
            [0],
            [0],
            marker="o",
            markeredgecolor="w",
            markerfacecolor="lightpink",
            markersize=10,
            label="Without constant data input",
        )
    )
    ax.legend(
        handles=legend_elements,
        loc="lower center",
        fontsize=8,
        ncol=4,
        markerscale=0.8,
        bbox_to_anchor=(0.5, -0.3),
    )
    if config["with_edge_attr"]:
        edge_attr = nx.get_edge_attributes(llama_graph, "dim")
        nx.draw_networkx_edge_labels(
            llama_graph,
            pos=position,
            edge_labels=edge_attr,
            font_size=5.5,
            rotate=True,
            verticalalignment="bottom",
            clip_on=False,
            # label_pos=0.5,
            # bbox=dict(boxstyle="round", facecolor="yellow", edgecolor="red", pad=0.3),
        )
    nx.draw_networkx_edges(llama_graph, pos=position, ax=ax, arrowsize=5)
    print(
        "The length of each topo generation is ",
        [len(n) for n in nx.topological_generations(llama_graph)],
    )
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    # sm = plt.cm.ScalarMappable(cmap="RdYlGn_r", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(
        sm,
        ax=ax,
        orientation="vertical",
        pad=-0.05,
        location="left",
        aspect=20,
    )
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label(label=config["metric_name"], fontsize=8)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)

    # print(nodes)


if __name__ == "__main__":
    main()
