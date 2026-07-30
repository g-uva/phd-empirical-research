# Reproducing eGPU

## Requirements and safety

The upstream quick start uses a privileged, host-networked GPU Docker container.
On DAS-6 this may be disallowed and must not be attempted outside an allocated
GPU job or without cluster approval. Record GPU, driver, CUDA, kernel, Docker or
Apptainer version, compiler, container digest, source revision, and commands.

## Build and smoke test

The upstream command is:

```bash
docker run -dit --gpus all -v.:/root --privileged --network=host --ipc=host \
  --name egpu yangyw12345/egpu:latest
make release
```

Before using it, resolve the mutable image tag to a digest and review the image.
For DAS-6, adapt this to the supported container runtime and SLURM GPU
allocation. If privileged containers are unavailable, document the blocker and
test only unprivileged components.

The flattened artifact does not vendor Git submodule contents. For a local build,
clone the pinned eGPU revision into an ignored external working directory with
`--recurse-submodules`, verify every submodule revision against
`../original/README.md`, and build there. Do not introduce nested Git metadata
under `papers/`.

Validate incrementally:

1. Build the eBPF-to-PTX VM/compiler and CUDA attachment components.
2. Run a minimal PTX/eBPF example from `attach/nv_attach_impl/examples/`.
3. Confirm probe attachment, expected output, clean detachment, and unchanged
   workload correctness.
4. Capture instrumentation overhead against an uninstrumented control.

## Paper-result families

The repository contains plotting scripts and PDFs under `artifact/` for latency,
end-to-end scaling, profiler/instrumentation overhead, memory tracing, and
LRU/LFU scheduling. The scripts contain hard-coded summary values, not raw
measurement provenance. Regenerating those PDFs validates plotting only.

For scientific reproduction, recover the exact workloads, GPUs, CUDA/tool
versions, competitors, repetitions, raw measurements, and commands used for
each figure. Execute them through SLURM allocations, retain raw outputs outside
Git, and register their manifests and derived figures under new experiments.
