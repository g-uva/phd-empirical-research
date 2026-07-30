from bcc import BPF
from ctypes import *
from utils.find_pid import get_pids_from_name, get_children_pids
import signal


def timeout_handler(signum, frame):
    raise TimeoutError("Function call timeout")


class KTracer:
    def __init__(self):
        self._bpf_init()
        self.result = []

    def _bpf_init(self):
        self.bpf = BPF(src_file="trace_kernel.c")
        self.bpf.attach_tracepoint(
            tp="sched:sched_wakeup", fn_name="get_sched_wakeup_events"
        )
        self.bpf.attach_tracepoint(
            tp="sched:sched_switch", fn_name="get_sched_switch_tp_events"
        )
        self.bpf["eventsKernel"].open_perf_buffer(self._handle_event)

    def _handle_event(self, cpu, data, size):
        output = self.bpf["eventsKernel"].event(data)
        if output.type == 0:
            self.result.append(
                {
                    "type": 0,
                    "value": (
                        output.timestamp,
                        cpu,
                        output.next_pid,
                        output.prev_comm.decode("UTF-8"),
                    ),
                }
            )
        elif output.type == 1:
            self.result.append(
                {
                    "type": 1,
                    "value": (
                        output.timestamp,
                        cpu,
                        output.prev_comm.decode("UTF-8"),
                        output.prev_pid,
                        output.prev_ppid,
                        output.prev_prio,
                        output.prev_state,
                        output.next_comm.decode("UTF-8"),
                        output.next_pid,
                        output.next_ppid,
                        output.next_prio,
                    ),
                }
            )
        elif output.type == 2:
            self.result.append(
                {
                    "type": 2,
                    "value": (
                        output.timestamp,
                        cpu,
                        output.prev_comm.decode("UTF-8"),
                        output.prev_pid,
                        output.prev_prio,
                        output.prev_state,
                        output.next_comm.decode("UTF-8"),
                        output.next_pid,
                        output.next_prio,
                    ),
                }
            )

    def start_trace(
        self,
        workload_pid,
        n_threads: int = 0,
        timeout: int = 10,
        output_txt: str = None,
    ):
        signal.signal(signal.SIGALRM, timeout_handler)
        self.pids = get_children_pids(workload_pid.value)
        while len(self.pids) < n_threads + 1:
            self.pids = get_children_pids(workload_pid.value)
        for pid in self.pids:
            self.bpf["pid_store"][c_int(pid)] = c_int(pid)
        while 1:
            signal.alarm(timeout)
            try:
                self.bpf.perf_buffer_poll()
                # if (
                #     n_threads > 0 and len(self.pids) < n_threads + 1
                # ):  ## FIXME: will this be too late?
                #     self.pids = get_children_pids(workload_pid.value)
                #     for pid in self.pids:
                #         self.bpf["pid_store"][c_int(pid)] = c_int(pid)
            except KeyboardInterrupt:
                print("User interrupt...")
                exit()
            except TimeoutError:
                if output_txt is not None:
                    result_lines = []
                    result_lines.append(
                        f"Children PIDs are: {','.join(map(str, self.pids))}"
                    )
                    for res in self.result:
                        if res["type"] == 0:
                            result_lines.append(
                                "%d [%d] sched_wakeup: %d %s" % res["value"]
                            )
                        elif res["type"] == 1:
                            result_lines.append(
                                "%d [%d] sched_switch: [%s %d %d %d %d] => [%s %d %d %d]"
                                % res["value"]
                            )
                        elif res["type"] == 2:
                            result_lines.append(
                                "%d [%d] sched_switch: [%s %d %d %d] => [%s %d %d]"
                                % res["value"]
                            )
                    with open(output_txt, "w") as f:
                        f.write("\n".join(result_lines))
                    break
                # exit()
