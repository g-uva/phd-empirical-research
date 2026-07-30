import multiprocessing
from collections import defaultdict, deque
import os
import struct
import signal
import ctypes
import pandas as pd
import uuid
import numpy as np
from bcc import BPF, PerfType, PerfHWConfig
from utils.json import read_from_json
# import tracemalloc
# import resource

# from utils.cpufreq import lock_cpu_freq, restore_state

MAX_NUM_OPS = 128
MUL_MAT_ID_OP_ID = 27  # For RKNN it is 28
NUM_EXPERTS = 4

# TODO: Optimize the method of storing the tracing results.


def timeout_handler(signum, frame):
    raise TimeoutError("Function call timeout")


def convert_to_uuid(raw_data):
    return uuid.UUID(bytes=bytes(raw_data))


import numpy as np
import pandas as pd
import uuid


def store_to_dataframe_flatten(
    arr: np.ndarray,
    *,
    guid_field: str = "guid",
    decode_bytes: bool = True,
) -> pd.DataFrame:
    """
    - SXX decoded to UTF-8 string, and strip trailing \x00
    - normal multi-dimensional data to field_0..field_k
    - guid(u1[16]) to uuid.UUID or str(uuid.UUID) (if all zero, set to pd.NA)
    """
    if arr.dtype.names is None:
        raise TypeError("arr must be a structured array")

    out = {}

    names = arr.dtype.names
    for name in names:
        col = arr[name]

        # --- guid：u8[16] -> UUID ---
        if name == guid_field:
            if col.ndim != 2 or col.shape[1] != 16 or col.dtype != np.uint8:
                raise TypeError(
                    f"{guid_field} must be uint8[16], got shape={col.shape}, dtype={col.dtype}"
                )

            is_zero = (col == 0).all(axis=1)

            b16 = col.view("S16").reshape(-1)  # dtype='|S16', shape=(N,)

            vals = [
                (pd.NA if z else (uuid.UUID(bytes=bytes(x))))
                for x, z in zip(b16, is_zero)
            ]
            out[name] = vals
            continue

        # --- 1D field ---
        if col.ndim == 1:
            if decode_bytes and col.dtype.kind == "S":
                s = np.char.decode(col, "utf-8", errors="replace")
                s = np.char.rstrip(s, "\x00")
                out[name] = s
            else:
                out[name] = col
            continue

        # --- other multi-dimensional fields ---
        flat = col.reshape(col.shape[0], -1)
        for j in range(flat.shape[1]):
            out[f"{name}_{j}"] = flat[:, j]

    return pd.DataFrame(out)


class op_map_128(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint64), ("hi", ctypes.c_uint64)]


class LLMTracer:
    def __init__(self, config: dict):
        self.config = config
        self._parse_config(config)
        self.perf_events = read_from_json(self.config["perf_events_path"])
        self.type_to_func = defaultdict(str)

        # TODO: Optimize this part
        self.type_to_func[10] = "llama_decode_start"
        self.type_to_func[15] = "llama_decode_end"
        self.type_to_func[20] = "ggml_compute_forward_start"
        self.type_to_func[25] = "ggml_compute_forward_end"
        self.type_to_func[30] = "ggml_backend_graph_compute_async_start"
        self.type_to_func[35] = "ggml_backend_graph_compute_async_end"
        self.type_to_func[40] = "ggml_acc_compute_forward_start"
        self.type_to_func[45] = "ggml_acc_compute_forward_end"

        if self.flag_open_perf:
            # Config is from /bcc/__init__.py or uapi/linux/perf_event.h
            self.perf_fd = []
            self.perf_types = []
            self.perf_configs = []
            self.perf_types_ = [self.config["perf_type_1"], self.config["perf_type_2"]]
            for i, perf_type in enumerate(self.perf_types_):
                if perf_type == "raw":
                    self.perf_types.append(PerfType.RAW)
                    self.perf_configs.append(
                        int(
                            self.perf_events["perf_raw_config"][
                                self.config[f"perf_config_{i+1}"]
                            ],
                            16,
                        )
                    )
                elif perf_type == "hardware":
                    self.perf_types.append(PerfType.HARDWARE)
                    self.perf_configs.append(
                        self.perf_events["perf_hw_id"][
                            self.config[f"perf_config_{i+1}"]
                        ]
                    )
                elif perf_type == "software":
                    self.perf_types.append(PerfType.SOFTWARE)
                    self.perf_configs.append(
                        self.perf_events["perf_sw_id"][
                            self.config[f"perf_config_{i+1}"]
                        ]
                    )
                elif perf_type == "dsu":
                    self.perf_types.append(self._perf_pmu_type("arm_dsu_0"))
                    self.perf_configs.append(
                        int(
                            self.perf_events["perf_raw_config"][
                                self.config[f"perf_config_{i+1}"]
                            ],
                            16,
                        )
                    )
                else:
                    print("Unidentified perf type")
                    raise ValueError
        self._bpf_init()

        ## Store the tracing results
        self.outputs = []
        self.result_lines = []
        # The older way to save result
        self.result_dict = defaultdict(lambda: deque(maxlen=1000000))
        trace_types = [
            ("ts", np.uint64),
            ("type", np.uint16),
            ("pid", np.uint32),
            ("cpu", np.uint16),
            ("name", "S16"),
            ("op", np.uint16),
            ("guid", np.uint8, (16,)),
        ]
        if self.flag_open_perf:
            for i in range(len(self.perf_types_)):
                trace_types.append((f"pmc_{i}", np.uint64))
        if self.flag_structrual:
            trace_types += [
                ("parm_addr", np.uint64),
                ("first_src_addr", np.uint64),
                ("second_src_addr", np.uint64),
                ("ne", np.int64, (4,)),
                ("src0_ne", np.int64, (4,)),
                ("src1_ne", np.int64, (4,)),
            ]
        if self.flag_trace_moe:
            trace_types += [
                ("third_src_addr", np.uint64),
                ("src2_ne", np.int64, (4,)),
                ("id_experts", np.uint16, (NUM_EXPERTS,)),
            ]
        self.n_trace_fields = len(trace_types)
        self.trace_dtype = np.dtype(trace_types)
        self.n_decode_iter = 0
        if self.flag_trace_moe:
            self.activated_experts = defaultdict(list)
        self.result_deque = deque(maxlen=1000000)

    def _parse_config(self, config: dict):
        """
        Parse the tracing config
        """
        # Flags
        self.flag_open_perf: bool = config["open_perf"]
        self.flag_structrual: bool = config["structrual_info"]
        self.flag_trace_moe: bool = config["trace_moe"]

        # TODO: Others

    def _perf_pmu_type(self, name: str):
        with open(f"/sys/bus/event_source/devices/{name}/type", "r") as f_type:
            type_raw = f_type.read()
        return int(type_raw)

    def _bpf_init(self):
        cflags = ["-Wno-macro-redefined"]
        cflags += [f"-DMAX_NUM_OPS={MAX_NUM_OPS}"]
        if self.flag_open_perf:
            # FIXME: It needs not to be across all the cpus, if it's binded to some.
            cflags += ["-DNUM_CPUS=%d" % multiprocessing.cpu_count(), "-DOPEN_PERF=1"]
        if self.flag_structrual:
            cflags += ["-DDIMS=1"]
        if self.flag_trace_moe:
            cflags += ["-DTRACE_MOE=1"]
        if self.config["target_iter"] >= 0:
            cflags += [f"-DTARGET_N_ITER={self.config['target_iter']}"]
        if self.config["ring_buffer"]:
            cflags += ["-DRING_BUFFER=1"]
        self.bpf = BPF(src_file="trace_llm.c", cflags=cflags)
        ## Attach uprobe and uretprobe
        lib_func_pair = [
            (self.config["lib_llama_dyn"], self.config["activated_funcs_llama"]),
            (
                self.config["lib_ggml_dyn_base"],
                self.config["activated_funcs_ggml_base"],
            ),
            (
                self.config["lib_ggml_dyn_cpu"],
                self.config["activated_funcs_ggml_cpu"],
            ),
            # (
            #     self.config["lib_ggml_dyn_acc"],
            #     self.config["activated_funcs_ggml_acc"],
            # ),
        ]

        if self.config["dynamic_link"]:
            for lib, funcs in lib_func_pair:
                for func_name in funcs:
                    self.bpf.attach_uprobe(
                        name=lib, sym=func_name, fn_name=func_name + "_start"
                    )
                    self.bpf.attach_uretprobe(
                        name=lib, sym=func_name, fn_name=func_name + "_end"
                    )
                    print(f"Attach func {func_name} successfully.")
            # attach acc func
            lib_acc = self.config["lib_ggml_dyn_acc"]
            for func_name in self.config["activated_funcs_ggml_acc"]:
                if "compute_forward" in func_name:
                    self.bpf.attach_uprobe(
                        name=lib_acc,
                        sym=func_name,
                        fn_name="ggml_compute_forward_acc_start",
                    )
                    self.bpf.attach_uretprobe(
                        name=lib_acc,
                        sym=func_name,
                        fn_name="ggml_compute_forward_acc_end",
                    )
                    print(f"Attach acc op func {func_name} successfully.")
                else:
                    self.bpf.attach_uprobe(
                        name=lib_acc,
                        sym=func_name,
                        fn_name=func_name + "_start",
                    )
                    self.bpf.attach_uretprobe(
                        name=lib_acc, sym=func_name, fn_name=func_name + "_end"
                    )
                    print(f"Attach acc other func {func_name} successfully.")
        # Deprecated
        else:
            for _, funcs in lib_func_pair:
                for func_name in funcs:
                    self.bpf.attach_uprobe(
                        name=self.config["lib_llama"],
                        sym=func_name,
                        fn_name=func_name + "_start",
                    )
                    self.bpf.attach_uretprobe(
                        name=self.config["lib_llama"],
                        sym=func_name,
                        fn_name=func_name + "_end",
                    )
                    print(f"Attach func {func_name} successfully.")
        # Open perf event
        if self.flag_open_perf:
            for i, perf_type_ in enumerate(self.perf_types_):
                if perf_type_ != "dsu":
                    self.bpf[f"cnt{i}".encode("utf-8")].open_perf_event(
                        self.perf_types[i], self.perf_configs[i]
                    )
                    print(self.perf_types[i], self.perf_configs[i])
                    self.perf_fd.append(0)
                else:
                    cnt = self.bpf[f"cnt{i}".encode("utf-8")]
                    cnt._open_perf_event(0, self.perf_types[i], self.perf_configs[i])
                    self.perf_fd.append(cnt._open_key_fds[0])

        # Define the target number of iteration, or trace all the iterations when it is -1
        if self.config["target_iter"] >= 0:
            self.bpf["num_iter_array"][ctypes.c_int32(0)] = ctypes.c_uint16(0)
        # Define the activated operators, if there is no activated ops or need to trace the whole structure, activate all the ops
        activated_ops_map = self.bpf.get_table("activated_ops")
        val = op_map_128()
        key = ctypes.c_uint(0)
        if len(self.config["activated_ops"]) == 0 or self.config["structrual_info"]:
            activated_ops = list(range(MAX_NUM_OPS))
        else:
            activated_ops = self.config["activated_ops"]
        for op_id in activated_ops:
            if op_id < 64:
                val.lo |= 1 << op_id
            else:
                val.hi |= 1 << (op_id - 64)
        activated_ops_map[key] = val

    def _handel_event(self, cpu, data, size):
        output = self.bpf["eventsRun"].event(data)
        self._post_process(output)
        # self.result_deque.append(output)
    def _handel_event_graph(self, cpu, data, size):
        output = self.bpf["eventsRunG"].event(data)
        self._post_process(output)
        # self.result_deque.append(output)

    def _handel_event_op(self, cpu, data, size):
        output = self.bpf["eventsRunO"].event(data)
        self._post_process(output)
        # self.result_deque.append(output)

    
    
    def _post_process(self, output):
        if output.type == 50:
            print(output.other)
        # for output in self.outputs:
        self.result_dict["ts"].append(output.TS)
        # self.result_dict["func"].append(func_name_and_pos[0])
        # self.result_dict["pos"].append(func_name_and_pos[1])
        self.result_dict["type"].append(output.type)
        self.result_dict["pid"].append(output.pid)
        self.result_dict["cpu"].append(output.cpu)
        if self.flag_open_perf:
            pmcs = [output.pmc_0, output.pmc_1]
            for i, perf_type_ in enumerate(self.perf_types_):
                if perf_type_ != "dsu":
                    self.result_dict[f"pmc_{i}"].append(pmcs[i])
                else:
                    counter = os.read(self.perf_fd[i], 8)
                    pmc = struct.unpack("Q", counter)[0]
                    # result_line += f",pmc:{pmc}"
                    self.result_dict[f"pmc_{i}"].append(pmc)
        if output.type == 15:
            # print(f"Finish {self.n_decode_iter}th iteration.")
            # if self.n_decode_iter == self.config["target_iter"] - 1:
            #     self.bpf["target_iter"][0] = ctypes.c_uint8(1)
            # elif self.config["target_iter"] != -1:
            #     self.bpf["target_iter"][0] = ctypes.c_uint8(0)
            self.n_decode_iter += 1
        if output.type == 30:
            # self.result_dict["guid"].append(uuid.UUID(bytes=bytes(output.guid)))
            self.result_dict["guid"].append(output.guid)
        else:
            self.result_dict["guid"].append(0)
        if output.type == 20 or output.type == 40:
            self.result_dict["name"].append(output.name.decode("UTF-8"))
            self.result_dict["op"].append(output.op)
            if (
                self.flag_trace_moe and output.op == MUL_MAT_ID_OP_ID
            ):  # FIXME: 27 is hardcoded now.
                # TODO: It is better to read it from the output of view/argsort, but to match the name of the operator is not realized inside eBPF
                self.activated_experts[self.n_decode_iter].append(
                    [output.id_experts[id] for id in range(NUM_EXPERTS)]
                )

            if self.flag_structrual:
                self.result_dict["ne0"].append(output.ne0)
                self.result_dict["ne1"].append(output.ne1)
                self.result_dict["ne2"].append(output.ne2)
                self.result_dict["ne3"].append(output.ne3)
                self.result_dict["src0_ne0"].append(output.src0_ne[0])
                self.result_dict["src0_ne1"].append(output.src0_ne[1])
                self.result_dict["src0_ne2"].append(output.src0_ne[2])
                self.result_dict["src0_ne3"].append(output.src0_ne[3])
                self.result_dict["src1_ne0"].append(output.src1_ne[0])
                self.result_dict["src1_ne1"].append(output.src1_ne[1])
                self.result_dict["src1_ne2"].append(output.src1_ne[2])
                self.result_dict["src1_ne3"].append(output.src1_ne[3])
                self.result_dict["first_src_addr"].append(output.first_src_addr)
                self.result_dict["second_src_addr"].append(output.second_src_addr)
                self.result_dict["parm_addr"].append(output.tensor_address)
                if self.flag_trace_moe:
                    self.result_dict["third_src_addr"].append(output.third_src_addr)
                    self.result_dict["src2_ne0"].append(output.src2_ne[0])
                    self.result_dict["src2_ne1"].append(output.src2_ne[1])
                    self.result_dict["src2_ne2"].append(output.src2_ne[2])
                    self.result_dict["src2_ne3"].append(output.src2_ne[3])

        else:
            self.result_dict["op"].append(0)
            self.result_dict["name"].append("")
            if self.flag_structrual:
                self.result_dict["parm_addr"].append(0)
                self.result_dict["first_src_addr"].append(0)
                self.result_dict["second_src_addr"].append(0)
                if self.flag_trace_moe:
                    self.result_dict["third_src_addr"].append(0)
                for i in range(4):
                    self.result_dict[f"ne{i}"].append(0)
                    self.result_dict[f"src0_ne{i}"].append(0)
                    self.result_dict[f"src1_ne{i}"].append(0)
                    if self.flag_trace_moe:
                        self.result_dict[f"src2_ne{i}"].append(0)

    def start_trace(
        self, event=None, lock=None, output_csv: str = None, output_txt: str = None
    ):
        # tracemalloc.start()
        print("Start tracing......")
        # lock_cpu_freq(self.config["cpu_ids"], [2352000, 2352000], cache_state=True, set_userspace=True)
        if event is not None:
            print("With event communication")
        if self.config["ring_buffer"]:
            self.bpf["eventsRun"].open_ring_buffer(self._handel_event)
            self.bpf["eventsRunG"].open_ring_buffer(self._handel_event_graph)
            self.bpf["eventsRunO"].open_ring_buffer(self._handel_event_op)
        else:
            self.bpf["eventsRun"].open_perf_buffer(self._handel_event, page_cnt=256)
            self.bpf["eventsRunG"].open_perf_buffer(self._handel_event_graph, page_cnt=256)
            self.bpf["eventsRunO"].open_perf_buffer(self._handel_event_op, page_cnt=256)
        signal.signal(signal.SIGALRM, timeout_handler)
        # if event is None:
        while 1:
            signal.alarm(self.config["timeout"])
            if event is not None and lock is not None:
                with lock:
                    print(f"enter lock, {event.value}")
                    if event.value == 1:
                        print("event triggered")
                        break
            try:
                if self.config["ring_buffer"]:
                    self.bpf.ring_buffer_poll()
                else:
                    self.bpf.perf_buffer_poll()
            except KeyboardInterrupt:
                print("\n".join(self.result_lines))
                exit()
            except TimeoutError:
                for output in self.result_deque:
                    self._post_process(output)
                # result_df = store_to_dataframe_flatten(self.store.view())
                result_df = pd.DataFrame(self.result_dict)
                # # result_df = store_to_dataframe_flatten(self.store.view())
                # if self.config["trace_moe"]:
                #     activated_experts = np.array(
                #         [self.activated_experts[i] for i in range(self.n_decode_iter)]
                #     )
                #     np.save(output_csv.split(".csv")[0] + "_moe.npy", activated_experts)
                #     # print(self.activated_experts)
                #     # moe_df = pd.DataFrame(self.activated_experts)
                #     # moe_df.to_csv(output_csv.split(".csv")[0] + "_moe.csv")
                # if output_txt is not None:
                #     result_lines = []
                #     for i, row in result_df.iterrows():
                #         pos = "start" if row["type"] % 10 == 0 else "end"
                #         result_line = f"ts:{row['ts']},func:{self.type_to_func[row['type']].rsplit('_', 1)[0]},pos:{pos},pid:{row['pid']},op:{row['op']},cpu:{row['cpu']},"
                #         result_line += f"name:{row['name']},"
                #         # result_line += f"python-ts:{row['python-ts']},"
                #         if self.config["structrual_info"]:
                #             result_line += f"parm_addr:{row['parm_addr']},first_src_addr:{row['first_src_addr']},second_src_addr:{row['second_src_addr']},"
                #             for i_dim in range(4):
                #                 result_line += f"ne{i_dim}:{row[f'ne{i_dim}']},"
                #                 result_line += (
                #                     f"src1_ne{i_dim}:{row[f'src0_ne{i_dim}']},"
                #                 )
                #                 result_line += (
                #                     f"src2_ne{i_dim}:{row[f'src1_ne{i_dim}']},"
                #                 )
                #         if row["type"] == 30:
                #             result_line += (
                #                 f"guid:{uuid.UUID(bytes=bytes(row['guid']))},"
                #             )
                #         result_lines.append(result_line)
                #     with open(output_txt, "w") as f:
                #         f.write("\n".join(result_lines))
                if output_csv is not None:
                    try:
                        result_df.loc[result_df["guid"] != 0, "guid"] = result_df.loc[
                            result_df["guid"] != 0, "guid"
                        ].apply(convert_to_uuid)
                    except:
                        print(result_df.head())
                    result_df.to_csv(output_csv)
                print("Timeout for tracing")
                # current, peak = tracemalloc.get_traced_memory()
                # print(
                #    f"tracemalloc current={current/1024/1024:.1f}MB, peak={peak/1024/1024:.1f}MB"
                #)
                # rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                # print("Peak RSS:", rss_kb, "KB")
                # restore_state()
                exit()


def main():
    config_file = "jsons/config.json"
    config = read_from_json(config_file, cat="trace")
    tracer = LLMTracer(config=config)
    tracer.start_trace(output_csv="test.csv")


if __name__ == "__main__":
    main()
