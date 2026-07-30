import subprocess
import re
import os
import sys
import random
import string
from multiprocessing import Event
from utils.json import write_to_json


class LlamaCPPRunner:
    def __init__(self, config, shared_pid=None):
        self.config = config
        self.model_path = config["model_path"]
        self.n_threads = config["n_threads"]
        self.work_dir = config["work_dir"]
        self.cpus = config["cpu_ids"]
        self.no_cnv = config["no-cnv"]
        self.ngl = config["ngl"]
        self.runtime_info = config["runtime_info"]
        self.shared_pid = shared_pid
        self.metrics = None

    def run_llama_cli(
        self,
        prompt: str,
        n_tokens: int = 0,
        display_answer=True,
        event=None,
        lock=None,
        metrics_path=None,
    ):
        assert (
            n_tokens > 1 or n_tokens == 0
        ), "The number of generated tokens should not be negative or 1."
        # cmd = [self.work_dir + "llama-cli"]
        cmd = [os.path.join(self.work_dir, "llama-cli")]
        cmd += ["-m", self.model_path]
        cmd += ["-t", str(self.n_threads)]
        cmd += ["-p", f"{prompt}"]
        cmd += ["--ignore-eos"]
        # cmd += ["--no-mmap"]
        if self.ngl > 0:
            cmd += ["-ngl", str(self.ngl)]
        if self.no_cnv:
            cmd += ["-no-cnv"]  # For the newer version to get rid of interactive mode
        if n_tokens != 0:
            cmd += ["-n", str(n_tokens)]
        if self.config["sched_fifo"]:
            cmd = ["chrt", "-f", "90"] + cmd
        if len(self.cpus) > 0:
            cmd = [
                "taskset",
                "-c",
                ",".join(map(str, self.cpus)),
            ] + cmd
            # cmd += ["-C", "0xC0"]

        if display_answer:
            # res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
            res = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        else:
            # res = subprocess.run(
            #     cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            # )
            res = subprocess.Popen(
                cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            )
        if self.shared_pid != None:
            self.shared_pid.value = res.pid
        stdout, stderr = res.communicate()
         
        if res.returncode != 0:
            print("Running failed.")
            print(" ".join(cmd))
            # self.output = stdout.split(prompt)[1]
        self.runinfo = stderr.splitlines()
        if self.runtime_info:
            self._parse_runinfo()
            if metrics_path is not None:
                write_to_json(self.metrics, metrics_path)
        if event is not None and lock is not None:
            with lock:
                event.value = 1
                print("event is set")

    def profile_with_prompt_size(self, n_prompt: list):
        """
        It is just a parse of the output information from llama.cpp.
        The fine-grained profile is done within eBPF-enabled tracing tool
        """
        pass

    # def _generate_random_prompt(length: int, chars=string.ascii_letters + string.digits):
    #     return "".join
    def update_cpu(self, cpu_ids: list):
        self.cpus = cpu_ids

    def update_n_threads(self, n_threads: int):
        self.n_threads = n_threads

    def get_process_pid(self):
        if self.shared_pid is None:
            raise ValueError("The PID of the subprocess is still not obtained.")
        return self.shared_pid.value

    def get_metrics(self):
        if self.metrics is None:
            raise ValueError("The metrics are not obtained yet")
        return self.metrics

    def _parse_runinfo(self):
        ## Parsing time information
        timing_patterns = {
            "load_time": r"load time =\s*(\d+\.\d+)\s*ms",
            "sampling_time": r"sampling time =\s*(\d+\.\d+)\s*ms.*?(\d+)\s*runs.*?(\d+\.\d+)\s*ms per token.*?(\d+\.\d+)\s*tokens per second",
            "prompt_eval_time": r"prompt eval time =\s*(\d+\.\d+)\s*ms.*?(\d+)\s*tokens.*?(\d+\.\d+)\s*ms per token.*?(\d+\.\d+)\s*tokens per second",
            "eval_time": r"eval time =\s*(\d+\.\d+)\s*ms.*?(\d+)\s*runs.*?(\d+\.\d+)\s*ms per token.*?(\d+\.\d+)\s*tokens per second",
            "total_time": r"total time =\s*(\d+\.\d+)\s*ms.*?(\d+)\s*tokens",
        }
        timing_info = [
            line
            for line in self.runinfo
            if "llama_perf_context_print:" in line or "llama_perf_sampler_print" in line
        ]
        timing_data = {}
        for timing_line in timing_info:
            for key, pattern in timing_patterns.items():
                match = re.search(pattern, timing_line)
                if match:
                    timing_data[key] = match.groups()
                    break
        ## Check the matching result
        for key in timing_patterns.keys():
            # assert key in timing_data.keys(), f"{key} was not successfully parsed."
            if key not in timing_data.keys():
                print(
                    f"{key} was not successfully parsed, replaced by 0.",
                    file=sys.stderr,
                )
                timing_data[key] = 0
        self.load_time = float(timing_data["load_time"][0])
        self.sampling_speed = float(timing_data["sampling_time"][-1])
        self.prefill_speed = float(timing_data["prompt_eval_time"][-1])
        self.decode_speed = float(timing_data["eval_time"][-1])
        self.n_output_tokens = (
            int(timing_data["eval_time"][1]) + 1
        )  # The first token is not counted
        self.n_input_tokens = int(timing_data["prompt_eval_time"][1])
        self.metrics = {
            "load_time": self.load_time,
            "sampling_speed": self.sampling_speed,
            "prefill_speed": self.prefill_speed,
            "decode_speed": self.decode_speed,
            "n_output_tokens": self.n_output_tokens,
            "n_input_tokens": self.n_input_tokens,
        }

        print(f"\nThe decoding speed is {self.decode_speed} tokens / s")
        ## TODO: Parse other information. For now, only timing info is obtained
