# ProfInfer

This is the project about how to use ProfInfer to trace llama.cpp during LLM inference.

## Prerequisites

 -  <details open>
    <summary> Build llama.cpp </summary>

    1. Building details: Please refer to the official website of [llama.cpp-github](https://github.com/ggml-org/llama.cpp)
    
    2. Please checkout the current supported version (b4743). It will support the latest version.
    ```bash
    git checkout d04e7163c85a847bc61d58c22f2c503596db7aa8
    ```
    3. Try to run an example of `llama-cli`. Before that you might need to download a model in `gguf` format
    ```bash
    ./build/bin/llama-cli -m llama-3.2-1B-Instruct.gguf -n 10 -t 4 -p "Once upon a time" -no-cnv
    ```
    
    4. If you want to run `llama-cli` with more backends (e.g. RKNPU or OPENCL with GPU), you need to compile it with specific versions and flags.
    
    Repo of llama.cpp with RKNPU: [oh-llama.cpp](https://gitcode.com/openharmony-robot/oh-llama.cpp)
    
    - TODO: Add repos and compilation details of different backends that supported on Orangepi 5 Pro/Ultra with RKNPU/OpenCL(Arm Mali GPU), as well as on Rubik Pi3 with OpenCL
    </details>

-   <details>
    <summary> Build BCC </summary>
    0. Please refer to [install-guide-ubuntu](https://github.com/iovisor/bcc/blob/master/INSTALL.md#ubuntu---binary) for detailed information.

    1. Install the linux header

    2. Install bcc
    ```
    sudo apt install bpfcc-tools
    ```

    **IMPORTANT**: Please do not use any userspace python environment to install BCC, as it needs root permission.

    </details>

## Obtain the artifact and dependencies

Installation and repository provenance are documented at the artifact root in
[`../README.md`](../README.md). The accelerator-capable `oh-llama.cpp` fork is
available at <https://gitcode.com/openharmony-robot/oh-llama.cpp>; it is a
dependency/fork option, not a verified origin URL for this ProfInfer checkout.

## Run a simple tracing for llama.cpp

### Edit the config file
Before launching the workload and tracing framework, please modify the config file in `jsons/config.json`

1. A wrapper of workload for `llama-cli` is defined as a class `LlamaCPPRunner` to run `llama-cli` inside python, instead of running it in command line. In this part, you need to specify the some arguments for the workload, as well as some runtime configurations .

```json
"llama-cli":{
    "model_path": "qwen1.5-moe-a2.7b-q4_k.gguf",
    "sched_fifo": false,
    "model": "qwen1.5-moe-a2.7b-q4_k",
    "n_threads": 2,
    "work_dir": "../../../../llama.cpp/build/bin",
    "cpu_ids": [6, 7]
}
```

Runtime configurations: `cpu_ids`, `n_threads`, `sched_fifo`.

`work_dir` is the path where `llama-cli` is located.

2. Class `LLMTracer` is defined to configure and run the tracing part. You need to specify some options for tracing, as shown in the following.

```json
"trace": {
    "lib_llama": "../build/bin/llama-cli",
    "lib_llama_dyn": "../build/bin/libllama.so",
    "lib_ggml_dyn_base": "../build/bin/libggml-base.so",
    "lib_ggml_dyn_cpu": "../build/bin/libggml-cpu.so",
    "lib_c": "/lib/aarch64-linux-gnu/libc.so.6",
    "activated_funcs_llama": ["llama_decode"],
    "activated_funcs_ggml_base": ["ggml_backend_graph_compute_async"],
    "activated_funcs_ggml_cpu": ["ggml_compute_forward"],
    "dynamic_link": true,

    "activated_ops": [26, 27],
    "target_iter": -1,
    "cmd_name": "llama-cli",

    "structrual_info": true,
    "trace_moe": true,
    "open_perf": false,
    "ring_buffer": false,

    "perf_type": "raw",
    "perf_config_hw": "PERF_COUNT_HW_STALLED_CYCLES_BACKEND",
    "perf_config_raw": "l3d_cache_refill",
    
    "perf_events_path": "jsons/perf_events.json",
    "timeout": 15
}
```

`"lib_llama"`: works only if llama.cpp is statically built. Then you need to add probe to this executable binary only. Specify "dynamic_link" as "true".

`"lib_llama_dyn"`, `"lib_ggml_dyn_base"`, `"lib_ggml_dyn_cpu"`: works only if llama.cpp is dynamically built. Path of "libllama.so", "libggml-base.so", "libggml-cpu.so".

`"activated_funcs_llama"`, `"activated_funcs_ggml_base"`, `"activated_funcs_ggml_cpu"`: the functions to be probed in each of the aforementioned libraries correspondingly. If statically linked, these should be in the binary only.

`"dynamic_link"`: whether llama.cpp is dynamically built.

`"activated_ops"`: activated operator types (e.g. 26 for mul_mat, 27 for mul_mat_id), that will only be profiled. If it is empty, then it will profile all the operator types.

`"target_iter"`: activated number of iteration that the tracing framework will only trace. If it is -1, then trace all the decoding iteration.

`"cmd_name"`: not used yet. For getting the PID of the process.

`"structrual_info"`: whether to get the information of tensor address and dimensions. Disabling it could reduce the overhead.

`"trace_moe"`: only works for MoE models to get the activated expert IDs.

`"open_perf"`: whether to open perf event to read PMU counters.

`"ring_buffer"`: whether to use ring buffer to reduce the overhead, but enabling it could cause some events missing.

`"perf_type"`: "raw" or "dsu", defines the customized PMU counter should be a raw counter of a ARM DSU counter.

`"perf_config_hw"`: name of predefined hardware perf event.

`"perf_config_raw"`: name of the raw PMU counters.

`"timeout"`: timeout of tracing if there is no `llama-cli` running.

### Run a simple example
```bash
sudo python3 run_llama.py --config jsons/config.json
```

Then you will see the results in the folder `experiments`.

### A full list of experiments
Overhead analysis: Turn of the bpf stats counters
```bash
sudo sysctl -w kernel.bpf_stats_enabled=1
```

### Parse the result

#### Draw the metrics of one operator of matrix multiplication
```bash
```
- [ ] TODO: copy the python parsing scripts.

## How to add a new uprobe?

1. Locate the target function inside llama.cpp source code.

2. Find where the signature is located. E.g. use `nm` command to read the symbols of a binary, and use `ldd` or `readelf -d` to find the dynamic linked libraries.

3. Write the probe handler inside `trace_llm.c`.

4. Attach the new probes inside `trace_llama.py` and probably update the handling methods.
