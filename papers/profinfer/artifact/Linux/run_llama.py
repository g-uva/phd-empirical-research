import pandas as pd
import numpy as np
import signal
import time
from multiprocessing import Process, Event, Value, Lock
import subprocess

from utils.llama_cpp import LlamaCPPRunner
from utils.json import read_from_json, write_to_json
from utils.args import get_args
from utils.dirs import create_dirs
from trace_llama import LLMTracer
from trace_kernel import KTracer
from utils.cpufreq import lock_cpu_freq, restore_state


def get_prompt_db(prompt_csv: str) -> pd.DataFrame:
    return pd.read_csv(prompt_csv, index_col="n_tokens")


def get_prompt_by_length(n_prompt: int, prompt_df: pd.DataFrame) -> str:
    if n_prompt not in prompt_df.index:
        print("No such length prompt")
        return ""
    return prompt_df.loc[n_prompt]


def timeout_handler(signum, frame):
    raise TimeoutError("Function call timeout")


def check_and_wait_cpu_freq(cpu_ids: list, freq_threshold: int):
    if len(cpu_ids) == 0:
        return
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(600)
    try:
        cpu_freqs = np.zeros_like(np.array(cpu_ids))
        while True:
            for i, cpu_id in enumerate(cpu_ids):
                with open(
                    f"/sys/devices/system/cpu/cpu{cpu_id}/cpufreq/cpuinfo_cur_freq", "r"
                ) as f_cpufreq:
                    cur_freq = int(f_cpufreq.read())
                    cpu_freqs[i] = cur_freq
                    print(cur_freq)
            if np.all(cpu_freqs > freq_threshold):
                break
            else:
                print("CPU Throttling!")
                time.sleep(10)

    except TimeoutError:
        print("The sleep time exceeded the pre-set timeout.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        signal.alarm(0)


def main():
    args = get_args()
    config_path: str = args.config
    config = read_from_json(config_path, create_dir=True)
    run_config = config["llama-cli"]
    trace_config = config["trace"]
    # exp_config = read_from_json("jsons/config.json", cat="exp")
    # exp_dir = f"{exp_config['dir']}"
    # if trace_config["open_perf"]:
    #     if trace_config["perf_type"] == "hardware":
    #         output_dir = f"{config['exp_dir']}/{trace_config['perf_config_hw']}"
    #     else:
    #         output_dir = f"{config['exp_dir']}/{trace_config['perf_config_raw']}"
    #     create_dirs([output_dir])
    # else:
    output_dir = config["exp_dir"]
    # Initializations
    runner_pid = Value("i", 0)
    runner = LlamaCPPRunner(config=run_config, shared_pid=runner_pid)
    tracer = LLMTracer(config=trace_config)
    if trace_config["trace_kernel"]:
        ktracer = KTracer()

    # Iterate prompts
    # df_prompt_db = get_prompt_db("prompt_db.csv")
    # for i_row, row in df_prompt_db.iterrows():
    # prompt = row["prompts"]
    # print(f"Running llm with {i_row} prompt size.")
    # prompt = "'Once upon a time.'"  # 5 tokens in llama
    prompt = run_config["prompt"]
    i_row = run_config["n_prompt"]
    # Preparation of prompts
    # check_and_wait_cpu_freq(run_config["cpu_ids"], 2300000)
    # lock_cpu_freq(run_config["cpu_ids"], [2352000, 2256000])
    runner_process = Process(
        target=runner.run_llama_cli,
        args=(prompt,),
        kwargs={
            "n_tokens": run_config["n_tokens"],
            "display_answer": False,
            "metrics_path": f"{output_dir}/metrics.json",
        },
    )

    tracer_process = Process(
        target=tracer.start_trace,
        kwargs={
            "output_csv": f"{output_dir}/trace_{run_config['model']}_f16_t{run_config['n_threads']}_p{i_row}.csv",
            # "output_txt": f"{output_dir}/trace_{run_config['model']}_f16_t{run_config['n_threads']}_p{i_row}.txt",
        },
    )
    tracer_process.start()
    time.sleep(2)  # Wait the verification of BPF TODO: needs to be improved
    runner_process.start()
    time.sleep(0.5)
    print(f"The PID of the runner process is {runner.get_process_pid()}")
    with open(f"{output_dir}/process.pid", "w") as f:
        f.write(str(runner.get_process_pid()))

    # kprobe tracing in the main process
    if trace_config["trace_kernel"]:
        ktracer.start_trace(
            runner_pid,
            n_threads=run_config["n_threads"],
            output_txt=f"{output_dir}/ktrace_{run_config['model']}_f16_t{run_config['n_threads']}_p{i_row}.txt",
        )

    runner_process.join()
    tracer_process.join()
    res_bpftool_prog = subprocess.run(
        "bpftool -j prog show", shell=True, capture_output=True, text=True
    )
    with open(f"{output_dir}/bpftool_prog.json", "w") as f:
        f.write(res_bpftool_prog.stdout)
    res_bpftool_map = subprocess.run(
        "bpftool -j map show", shell=True, capture_output=True, text=True
    )
    with open(f"{output_dir}/bpftool_map.json", "w") as f:
        f.write(res_bpftool_map.stdout)

    # restore_state()

    # # Experiments


if __name__ == "__main__":
    main()
