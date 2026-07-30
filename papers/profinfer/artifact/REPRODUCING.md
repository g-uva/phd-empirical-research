# ProfInfer Linux CPU reproduction

These instructions reproduce the Linux CPU/x86 subset observed in this workspace.
The later sections define the work required to reproduce OpenHarmony, ARM raw PMU
counters, RKNPU/RKNN, Mali/OpenCL, and paper-identical hardware results. Those
sections are checklists, not claims that the corresponding paths have been
validated.

Set the catalogue root once for the commands below:

```bash
export CATALOG_ROOT=/path/to/this/catalogue
```

## 1. External source and model layout

Clone the required `llama.cpp` revision into the ignored root dependency directory:

```bash
cd "$CATALOG_ROOT"
git clone https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp checkout d04e7163c85a847bc61d58c22f2c503596db7aa8
```

Install the observed Ubuntu dependencies:

```bash
sudo apt update
sudo apt install build-essential cmake ccache
sudo apt install bpfcc-tools python3-bpfcc linux-headers-$(uname -r) bpftool
sudo apt install python3-pandas python3-numpy python3-matplotlib python3-scipy python3-tqdm
sudo apt install python3.12-dev graphviz graphviz-dev pkg-config
/usr/bin/python3 -c "from bcc import BPF; print('bcc ok')"
```

BCC must use system Python rather than a virtual environment because it needs the system installation and elevated tracing permissions.

Build dynamic libraries and `llama-cli`:

```bash
cmake -S "$CATALOG_ROOT/llama.cpp" -B "$CATALOG_ROOT/llama.cpp/build" -DBUILD_SHARED_LIBS=ON
cmake --build "$CATALOG_ROOT/llama.cpp/build" --target llama-cli -j
```

The expected files are `build/bin/llama-cli`, `libllama.so`, `libggml-base.so`, and `libggml-cpu.so`.

## 2. Download local-only GGUF inputs

Model weights are inputs, not repository content, and `models/` is ignored:

```bash
mkdir -p "$CATALOG_ROOT/models"

hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
  qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir "$CATALOG_ROOT/models"

hf download bartowski/Llama-3.2-1B-Instruct-GGUF \
  Llama-3.2-1B-Instruct-Q4_K_M.gguf --local-dir "$CATALOG_ROOT/models"

hf download lm-kit/gemma-2-2b-gguf --include '*Q4_K_M*.gguf' \
  --local-dir "$CATALOG_ROOT/models"

hf download QuantFactory/DeepSeek-R1-Distill-Qwen-1.5B-GGUF \
  DeepSeek-R1-Distill-Qwen-1.5B.Q4_K_M.gguf --local-dir "$CATALOG_ROOT/models"
```

## 3. Configure and smoke-test

The checked-in `Linux/jsons/config.json` uses paths relative to `Linux/`. Select the model name/path and online CPU IDs for the target host. On the observed x86 host, `[0, 1]` worked; ARM-oriented raw PMU events did not, so `open_perf` was disabled.

Test the external runtime independently:

```bash
"$CATALOG_ROOT/llama.cpp/build/bin/llama-cli" \
  -m "$CATALOG_ROOT/models/qwen2.5-0.5b-instruct-q4_k_m.gguf" \
  -t 2 -p "Once upon a time" --ignore-eos -no-cnv -n 10
```

## 4. Run ProfInfer

```bash
cd "$CATALOG_ROOT/papers/profinfer/artifact/Linux"
sudo /usr/bin/python3 run_llama.py --config jsons/config.json
```

A successful run attaches `llama_decode`, `ggml_backend_graph_compute_async`, and `ggml_compute_forward`, then writes a timestamped directory under `Linux/experiments/`. `Timeout for tracing` is the script's normal stop condition.

Expected generated outputs include `metrics.json`, a `trace_*.csv`, `bpftool_prog.json`, `bpftool_map.json`, `process.pid`, and a configuration snapshot. These outputs remain ignored.

For all four documented models:

```bash
cd "$CATALOG_ROOT/papers/profinfer/artifact/Linux"
./run_cpu_models.sh
```

The helper derives `CATALOG_ROOT` from its own location, updates the selected model in `jsons/config.json`, and executes each trace with system Python and `sudo`.

## 5. Capture the environment for every new reproduction

Before running a missing platform, save enough information to identify the
machine and software stack:

```bash
mkdir -p "$CATALOG_ROOT/reproduction-environment"
uname -a > "$CATALOG_ROOT/reproduction-environment/uname.txt"
lscpu > "$CATALOG_ROOT/reproduction-environment/lscpu.txt"
cat /etc/os-release > "$CATALOG_ROOT/reproduction-environment/os-release.txt"
/usr/bin/python3 --version > "$CATALOG_ROOT/reproduction-environment/python.txt" 2>&1
/usr/bin/python3 -c "import bcc; print(getattr(bcc, '__version__', 'version unavailable'))" \
  > "$CATALOG_ROOT/reproduction-environment/bcc.txt" 2>&1
bpftool version > "$CATALOG_ROOT/reproduction-environment/bpftool.txt" 2>&1
git -C "$CATALOG_ROOT/llama.cpp" rev-parse HEAD \
  > "$CATALOG_ROOT/reproduction-environment/llama-cpp-commit.txt"
```

Also record the board name and revision, SoC, RAM, storage, kernel configuration,
firmware, governor, online CPU set, accelerator driver/firmware version, compiler
version, model checksum, exact command, and ambient/power conditions when relevant.
Add the captured configuration and output manifest to `metadata/provenance.json`
as described in `experiments/README.md`. The environment directory is evidence to
archive with a published experiment; it is not currently ignored automatically.

## 6. ARM raw PMU counters (not yet validated)

The raw event numbers in `Linux/jsons/perf_events.json` are
microarchitecture-specific. Do not use them on a new SoC until they have been
checked against that SoC's technical reference manual or `perf list`.

1. Boot an ARM64 Linux kernel with BPF, uprobes, perf events, and access to the
   target PMU enabled. Install the dependencies from section 1.
2. Capture the environment from section 5 and identify the exact CPU
   microarchitecture for every CPU ID used.
3. Check PMU availability and permissions:

   ```bash
   perf list
   ls /sys/bus/event_source/devices
   cat /proc/sys/kernel/perf_event_paranoid
   sudo perf stat -e cycles,instructions -- sleep 1
   ```

4. Validate each desired event independently with `perf stat`. Obtain the raw
   encoding from the processor documentation or the named event exposed by the
   kernel; then update `Linux/jsons/perf_events.json` for this machine. Do not
   infer an event encoding from a different ARM core.
5. In a copy of `Linux/jsons/config.json`, set the correct ARM CPU IDs,
   `"open_perf": true`, the two `perf_type_*` values (`"raw"`, `"hardware"`, or
   `"dsu"`), and matching `perf_config_*` names. For DSU events, first confirm
   that `/sys/bus/event_source/devices/arm_dsu_0/type` exists.
6. Run a short trace, then repeat with PMU collection disabled as a control:

   ```bash
   cd "$CATALOG_ROOT/papers/profinfer/artifact/Linux"
   sudo /usr/bin/python3 run_llama.py --config /path/to/arm-config.json
   ```

7. Confirm that the trace contains non-zero, plausible counter deltas, that the
   process remained on the selected CPUs, and that event-loss messages were not
   produced. Repeat the run at least three times with a fixed model, prompt,
   thread count, token count, CPU affinity, and frequency governor.
8. Preserve both the PMU-enabled and control configurations, output manifests,
   and summary statistics under a new experiment ID.

This section is complete only when the event encodings and their meanings have
been documented for a named board/SoC and the resulting counters have been
cross-checked against `perf stat`.

## 7. RKNPU/RKNN backend (blocked on vendor build details)

The artifact points to `https://gitcode.com/openharmony-robot/oh-llama.cpp`, but
does not record a revision, RKNN toolkit/runtime versions, model conversion
procedure, or build flags. Those inputs must be recovered from the authors or a
known-good target before this path can be reproduced.

1. Record the exact board and SoC, Linux image/kernel, NPU driver and firmware,
   RKNN Toolkit/runtime versions, vendor `oh-llama.cpp` commit, and model
   conversion settings.
2. Follow that pinned fork's instructions to build shared `llama-cli`,
   `libllama.so`, `libggml-base.so`, and its RKNN backend library. Record the
   complete configure and build commands; do not substitute the CPU-only
   `llama.cpp` revision from section 1.
3. Run the vendor runtime without ProfInfer and verify that the model is actually
   offloaded to the NPU.
4. Copy `Linux/jsons/config.json` to a platform-specific configuration. Set
   `work_dir`, model path, `ngl`/offload settings, `lib_llama_dyn`,
   `lib_ggml_dyn_base`, and `lib_ggml_dyn_acc` to the built files. Set
   `activated_funcs_ggml_acc` to exported symbols verified with `nm -D`; use
   `Linux/jsons/ggml_ops_rknn.json` only after confirming that its operator IDs
   match the pinned fork.
5. Smoke-test uprobe attachment, run the fixed experiment matrix, and compare a
   CPU-only control against NPU offload. Save accelerator utilization evidence
   from the board's supported monitoring interface.
6. Validate trace event counts, offloaded operators, latency, throughput,
   counter/event loss, and output correctness; then register the configuration
   and result bundle in experiment provenance.

## 8. Mali/OpenCL backend (blocked on vendor build details)

The precise OpenCL implementation, driver version, fork revision, and build
flags used by the paper are not recorded.

1. Record the board/SoC and GPU, OS/kernel, Mali driver and firmware, OpenCL
   implementation/version, pinned source revision, and model checksum.
2. Verify the device independently:

   ```bash
   clinfo
   ```

3. Build the pinned `llama.cpp` fork with its documented OpenCL backend and
   shared libraries. Record the exact configure/build flags and retain the build
   cache or log.
4. Run `llama-cli` without ProfInfer and confirm from runtime output or vendor
   tooling that operators execute on the Mali GPU.
5. Create a platform-specific ProfInfer configuration as in section 7, pointing
   `lib_ggml_dyn_acc` at the OpenCL backend and listing only symbols confirmed
   by `nm -D`. Check the operator mapping against the exact fork; the repository
   contains `ggml_ops_clblast.json` and `ggml_ops_rubik.json`, but neither is
   validated here as a generic Mali mapping.
6. Run matched CPU-only and OpenCL trials, monitor GPU utilization/frequency,
   check event loss and output correctness, and archive the raw traces,
   configuration, build metadata, and summaries under a new experiment ID.

## 9. OpenHarmony implementation (blocked on SDK and target details)

`OpenHarmony/` contains a libbpf skeleton-based tracer, but its Makefile expects
source trees that are absent: `libbpf/`, `bpftool/`, `blazesym/`, and
architecture-specific `vmlinux.h` files. The tracer also hard-codes
`/system/lib64/libllama.so`, `/system/lib64/libggml-cpu.so`, and
`/system/lib64/libggml-base.so`.

1. Recover and record the OpenHarmony release/SDK, device and kernel build,
   compiler/sysroot, deployment method, root/debug permissions, BPF kernel
   configuration, the matching `vmlinux`/BTF source, dependency revisions, and
   ProfInfer build instructions.
2. Populate the dependency directories at pinned revisions and provide
   `OpenHarmony/vmlinux.h/include/<arch>/vmlinux.h` generated from the target's
   exact kernel BTF. Record whether the build is native or cross-compiled.
3. Verify the three hard-coded libraries exist on the target and export
   `llama_decode`, `ggml_compute_forward`, and
   `ggml_backend_graph_compute_async`. If paths differ, change and document
   them before building.
4. Build only the relevant target first:

   ```bash
   cd "$CATALOG_ROOT/papers/profinfer/artifact/OpenHarmony"
   make trace_llm
   ```

   A cross-build additionally requires the author-confirmed `ARCH`,
   `CROSS_COMPILE`, `CC`, and linker/sysroot settings; they are not known yet.

5. Deploy `trace_llm` to the device, start the matching inference workload, and
   run the tracer with the privileges required to load BPF and attach uprobes.
   Stop it with `SIGINT` and retain the generated `event_log_*.csv`.
6. Confirm that all three start/end probe pairs appear, timestamps are ordered,
   GUID and tensor fields decode correctly, and no perf-buffer loss is reported.
   Repeat a fixed workload at least three times and register the environment,
   configuration, executable checksum, and outputs in experiment provenance.

## 10. Reproduce paper tables and figures

1. Extract from the paper a manifest of every claimed table/figure: hardware,
   model and quantization, backend, prompt/token counts, threads, PMU events,
   repetitions, warm-up, and reported statistic.
2. Map every row or curve to an immutable experiment ID. Any paper parameter
   that cannot be recovered must be marked unknown and requested from the
   authors; it must not be silently guessed.
3. Run the full matrix on the named hardware using the fixed configurations
   above. Keep raw outputs and environment/build manifests.
4. Use the scripts under `Linux/scripts/` and `Linux/utils/` only after replacing
   their embedded example paths with the registered experiment paths. Record
   the exact script and command used for each derived table or figure.
5. Compare reproduced and reported values with an explicitly chosen tolerance,
   reporting absolute/relative error, variance, failed runs, and event loss.
   Store machine-readable summaries alongside regenerated figures.

## 11. Automation still required

After one manual run succeeds on each platform, capture it in a pinned container
or machine-readable provisioning script where the platform permits. Add smoke
tests for configuration parsing, symbol discovery, BPF load/attachment, trace
schema, non-empty metrics, and result parsing. Hardware tests should be clearly
marked and must report a skip—not a pass—when the required board or privileges
are unavailable.

## Reproduction status

Reproduced locally: Linux CPU tracing, dynamic-library uprobe attachment, GGUF inference, operator trace CSV generation, and basic load/prefill/decode/sampling metrics.

Defined but not yet validated: ARM raw PMU analysis, OpenHarmony, RKNPU/RKNN,
Mali/OpenCL, and paper-exact result comparison. Sections 6--10 state the
required procedure and the information still missing. No automated test suite
or container definition is present.
