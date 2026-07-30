import json
from utils.args import get_args
from utils.json import read_from_json
from utils.parse import get_value_by_key


##
def main():
    guid_map = read_from_json("jsons/ggml_guids.json")
    args = get_args()
    config_file = args.config
    config = read_from_json(config_file, "trace_event")
    op_list = read_from_json(config["ops_file"], "names")

    # kernelfile = "trace_results/trace_llama-cpp_kernel_t_4.txt"
    # funcfile = "trace_results/trace_llama-cpp_func_t_4.txt"
    kernel_file = config["kernel_file"]
    func_file = config["func_file"]
    output_dir = config["output_dir"]
    pid_file = config["pid_file"]
    with open(pid_file, "r") as f_pid:
        pid = int(f_pid.read())

    # outfile = kernelfile.split(".")[0] + ".json"
    # outfile = "trace_results/trace_llama-cpp_func_t_4.json"
    file_name = f"{output_dir}/{func_file.split('/')[1].split('.')[0]}"
    if func_file == "":
        outfile = file_name + ".json"
    else:
        outfile = file_name + "_func" + ".json"

    metadata = []
    event_entries = []
    count = 0

    def add_metadata_event(pid, tid):
        entry = {}
        entry["name"] = "thread_name"
        entry["ph"] = "M"
        entry["pid"] = pid
        entry["tid"] = f"{tid}-t"
        entry["args"] = {"name": "thread-" + str(pid)}
        metadata.append(entry)

    def get_threads(pid, tids):
        threadList = {}
        for tid in tids:
            # threadList[str(tid)] = {}
            threadList[tid] = {}
            # nodeList["name"] = "thread-" + str(pid)
            add_metadata_event(pid, tid)
        return threadList

    def add_sched_event(tid, thread_info, timestamp, pid, cpu):
        if thread_info.get("last_timestamp") != None:
            if thread_info["last_timestamp"] + 1 >= timestamp:
                print(tid)
                print(thread_info)
            else:
                # if thread_info["last_state"] == "running":
                entry_begin = {}
                entry_begin["name"] = thread_info["last_state"] + f"-cpu-{cpu}"
                entry_begin["cat"] = "main thread state"
                entry_begin["ph"] = "B"
                entry_begin["ts"] = thread_info["last_timestamp"] + 1
                entry_begin["pid"] = pid
                entry_begin["tid"] = f"{tid}-t"
                event_entries.append(entry_begin)

                entry_end = {}
                entry_end["cat"] = "main thread state"
                entry_end["ph"] = "E"
                entry_end["ts"] = timestamp
                entry_end["pid"] = pid
                entry_end["tid"] = f"{tid}-t"
                event_entries.append(entry_end)

    def use_timestamp(event):
        if "ts" in event:
            return get_value_by_key(event, "ts")
        else:
            return int(event.split()[0])

    def process_scheduler_traces(kernelfile, threadList, pid):
        with open(kernelfile) as fkernel:
            kernelevents = fkernel.readlines()
        fkernel.close()

        kernelevents = [evt for evt in kernelevents[1:] if len(evt.split()) > 3]
        kernelevents.sort(key=use_timestamp)

        for evt in kernelevents:
            cpu = int(evt.split("[")[1].split("]")[0])
            if "sched_wakeup" in evt:
                tid = int(evt.split()[3])
                if threadList.get(tid) != None:
                    timestamp = int(evt.split()[0]) / 1e3
                    add_sched_event(tid, threadList[tid], timestamp, pid, cpu)
                    threadList[tid]["last_timestamp"] = timestamp
                    threadList[tid]["last_state"] = "runnable"
            elif "sched_switch" in evt:
                timestamp = int(evt.split()[0]) / 1e3
                prev_tid = int(evt.split("sched_switch: [")[1].split()[1])
                if threadList.get(prev_tid) != None:
                    add_sched_event(prev_tid, threadList[prev_tid], timestamp, pid, cpu)
                    state = int(evt.split("[")[2].split("]")[0].split()[3])
                    threadList[prev_tid]["last_timestamp"] = timestamp
                    if state == 0:
                        threadList[prev_tid]["last_state"] = "runnable"
                    else:
                        threadList[prev_tid]["last_state"] = "idle"

                next_tid = int(evt.split("=> [")[1].split()[1])
                if threadList.get(next_tid) != None:
                    add_sched_event(next_tid, threadList[next_tid], timestamp, pid, cpu)
                    threadList[next_tid]["last_timestamp"] = timestamp
                    threadList[next_tid]["last_state"] = "running"

    def get_children_tids(kernelfile: str):
        with open(kernelfile, "r") as fkernel:
            lines = fkernel.readlines()
        pids = []
        for line in lines:
            if line.startswith("Children PIDs are"):
                pids_str = line.split(":", 1)[1].strip()
                pids = [int(pid) for pid in pids_str.split(",")]
        if not pids:
            print("Not found children pids.")
        return pids

    def add_func_event_op(
        pid: int,
        tid: int,
        ts_us: float,
        func_name: str,
        pos: str,
        op_id: int,
        op_name: str,
        clblast: bool = False,
    ) -> None:
        entry = {}
        entry["pid"] = pid
        entry["tid"] = tid
        entry["ts"] = ts_us
        if clblast:
            entry["name"] = f"clblast"
        else:
            # entry["name"] = f"{func_name}_{op_list[op_id]}_{op_name}_running"
            assert op_id < len(
                op_list
            ), f"{op_id} is out of range, there are {len(op_list)} in total"
            entry["name"] = f"{op_list[op_id].split('GGML_OP_')[1]}-{op_name}"
        entry["cat"] = func_name
        # if func_info.endswith("start"):
        if pos == "start":
            entry["ph"] = "B"
        else:
            entry["ph"] = "E"
        event_entries.append(entry)

    def add_func_event(
        pid: int, tid: int, ts_us: float, func_name: str, pos: str
    ) -> None:
        entry = {}
        entry["pid"] = pid
        entry["tid"] = tid
        entry["ts"] = ts_us
        entry["name"] = func_name
        entry["cat"] = func_name
        if pos == "start":
            entry["ph"] = "B"
        else:
            entry["ph"] = "E"
        event_entries.append(entry)

    def add_func_event_graph(
        pid: int, tid: int, ts_us: float, func_name: str, pos: str, guid: str
    ) -> None:
        entry = {}
        # func_name = "_".join(
        #     func_info.split("_")[:-1]
        # )  # Supposing "_" is the delimiter of function and type

        entry["pid"] = pid
        entry["tid"] = tid
        entry["ts"] = ts_us
        entry["name"] = f"graph_comp_{guid_map[guid]}"
        entry["cat"] = func_name
        # if func_info.endswith("start"):
        if pos == "start":
            entry["ph"] = "B"
        else:
            entry["ph"] = "E"
        event_entries.append(entry)

    def find_partner_evt(
        cur_evt_id: int,
        cur_pid: int,
        func_events: list,
        func_name: str,
        pos: str = "end",
    ):
        if pos == "end":
            for evt in func_events[cur_evt_id - 1 :: -1]:
                if (
                    get_value_by_key(evt, "pid") == cur_pid
                    and get_value_by_key(evt, "pos", str) == "start"
                    and get_value_by_key(evt, "func", str) == func_name
                ):
                    return evt
            print(f"Start partner evt of {func_events[cur_evt_id]} is not found.")
            raise ValueError
        else:
            for evt in func_events[cur_evt_id + 1 :]:
                if (
                    get_value_by_key(evt, "pid") == cur_pid
                    and get_value_by_key(evt, "pos", str) == "end"
                    and get_value_by_key(evt, "func", str) == func_name
                ):
                    return evt
            print(f"End partner evt of {func_events[cur_evt_id]} is not found.")
            raise ValueError

    def process_function_traces(funcfile: str, pid: int) -> None:
        with open(funcfile, "r") as ffunc:
            func_events = ffunc.readlines()
        # func_events = [
        #     evt.split(",")[0] for evt in func_events if evt.startswith("func:")
        # ]
        func_events.sort(key=use_timestamp)
        for id, evt in enumerate(func_events):
            tid = get_value_by_key(evt, "pid")
            ts_us = get_value_by_key(evt, "ts") / 1e3
            func_name = get_value_by_key(evt, "func", str)
            pos = get_value_by_key(evt, "pos", str)
            # cpu_id = get_value_by_key(evt, "cpu")
            if (
                func_name == "ggml_compute_forward"
                or func_name == "ggml_acc_compute_forward"
            ):

                if pos == "start":
                    op_id = get_value_by_key(evt, "op")
                    name = get_value_by_key(evt, "name", str)
                else:
                    op_id = get_value_by_key(
                        find_partner_evt(id, tid, func_events, func_name), "op"
                    )
                    name = get_value_by_key(
                        find_partner_evt(id, tid, func_events, func_name), "name", str
                    )
                # func_name += f"-cpu-{cpu_id}"
                clblast = (
                    True
                    if config["clblast"] and func_name == "ggml_acc_compute_forward"
                    else False
                )
                add_func_event_op(pid, tid, ts_us, func_name, pos, op_id, name, clblast)
            elif func_name == "ggml_backend_graph_compute_async":

                if pos == "start":
                    guid = get_value_by_key(evt, "guid", str)
                else:
                    guid = get_value_by_key(
                        find_partner_evt(id, tid, func_events, func_name), "guid", str
                    )
                # func_name += f"-cpu-{cpu_id}"
                add_func_event_graph(pid, tid, ts_us, func_name, pos, guid)
            else:
                # func_name += f"-cpu-{cpu_id}"
                add_func_event(pid, tid, ts_us, func_name, pos)
                continue

    ofile = open(outfile, "w")
    print("Start generating......")
    if config["output_sched_switch"]:
        tids = get_children_tids(kernel_file)
        threadList = get_threads(pid, tids)
        print("output sched info")
        process_scheduler_traces(kernel_file, threadList, pid)
    if func_file != "":
        process_function_traces(func_file, pid)

    json_data = {}
    json_data["traceEvents"] = metadata + event_entries
    json_data["displayTimeUnit"] = "ns"

    json.dump(json_data, ofile, indent=4)


if __name__ == "__main__":
    main()
