# Reproducing Neutrino

The upstream artifact provides a CPU-only static evaluation over collected
traces and a dynamic evaluation that collects new traces on an NVIDIA GPU.
Neither path has yet been run in this workspace.

## 1. Record the source and environment

Use main revision `4a82cd22f474c31ac2fecfa174d381a19bb3f469` for the
preserved implementation and artifact revision
`43182f3082f5617d8bc85cd8902af4f6fbaeeb24` for the evaluation notebooks.
Before running, record OS/kernel, Python, GNU toolchain, CUDA driver/toolkit,
GPU model/firmware, PyTorch, Triton, CUTLASS, model/workload revisions, exact
commands, and checksums of downloaded traces.

## 2. Static evaluation

The static path requires Python and approximately 3 GB for the upstream
collected traces; it does not require a GPU or an installed Neutrino package.

1. Create an isolated Python environment.
2. Open `evaluation/static.ipynb`.
3. Inspect every download URL and record the checksum before executing it. The
   notebook currently references an upstream `trace.zip` object; no checksum is
   supplied by the authors.
4. Run the notebook sections for `block_sched`, `dmat`, `kernel_overhead`,
   `max_mem`, `exposed_latency`, and `warp_sched`.
5. Save the executed notebook, generated tables/figures, trace manifest, Python
   package versions, and console output under new registered experiment runs.
6. Compare outputs with Sec. 4.5, Figs. 1 and 10--13, and Table 2.

The artifact authors state that original traces for some Table 2 and Sec. 4.5
values were deleted, so those exact values cannot be reproduced from the
provided static traces.

## 3. Dynamic evaluation

The upstream instructions require an NVIDIA GPU (A100 for paper-identical
hardware), at least 10 GB free space, CUDA tools (`cuobjdump`, `ptxas`), GNU
tools, Python, a PTX-included PyTorch 2.5.0 build, Triton, and CUTLASS 3.5.0.

1. Review `evaluation/prepare_env.py` before running it. It downloads executable
   code and a third-party PyTorch wheel without recorded checksums.
2. Prefer a disposable environment and pin/checksum every downloaded input.
3. Install the package from this directory and confirm the CLI:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install .
   neutrino --help
   ```

4. Verify `nvidia-smi`, `cuobjdump`, `ptxas`, `gcc`, `file`, `git`, and `nm`;
   confirm the workload contains PTX and no competing GPU workload is active.
5. Open `evaluation/dynamic.ipynb`, run one `block_sched` smoke test, and verify
   that a trace is produced and parsed.
6. Run each remaining evaluation section independently. Preserve probe files,
   workload commits, commands, raw traces, executed notebooks, and generated
   figures/tables.
7. Repeat timing experiments, report variance and failures, and compare against
   the paper. Results from non-A100 GPUs should be labelled similar rather than
   paper-identical.

## 4. Catalogue the evidence

The six evaluation families are pre-registered as draft experiments under
`experiments/`. After each real run, create a new experiment rather than
overwriting a draft description, register configuration/result checksums in
`../metadata/provenance.json`, and update the content hash:

```bash
python3 scripts/experiment_versions.py update --paper neutrino exp-0001 \
  --reason "Record the Neutrino block-scheduling reproduction"
```
