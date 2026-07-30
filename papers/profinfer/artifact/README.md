# ProfInfer reproducibility artifact

This repository contains the ProfInfer implementations for Linux and OpenHarmony. The implementation layout is preserved from the original checkout; catalogue metadata and experiment provenance are additive.

## Version and provenance

- Artifact package version: `0.1.0` (from `Linux/pyproject.toml`)
- Preserved Git revision: `a311e7c24687b878ec560d77ea7bfd04e9036e04`
- Canonical ProfInfer source: [oh-llama.cpp/profinfer](https://gitcode.com/openharmony-robot/oh-llama.cpp/tree/main/profinfer)
- Pinned upstream revision: `210890a1f06cc837179d83e96fa0ea5327f9bf9d`
- Preserved source ZIP and checksum: [`../original/README.md`](../original/README.md)
- Paper: [`../paper/profinfer-mlsys-2026.pdf`](../paper/profinfer-mlsys-2026.pdf)
- Required `llama.cpp`: [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) at `d04e7163c85a847bc61d58c22f2c503596db7aa8`
- Documented accelerator fork: [oh-llama.cpp](https://gitcode.com/openharmony-robot/oh-llama.cpp) (revision not recorded)

The artifact files are tracked directly by the catalogue repository; upstream
Git history is not embedded. The pre-existing clone URL was verified to contain
the canonical `profinfer/` directory. No covering upstream licence was found,
so redistribution terms still require author confirmation.

## Layout

- `Linux/`: Python, eBPF/BCC tracing, analysis scripts, and configuration
- `OpenHarmony/`: C/eBPF implementation and Makefile
- `experiments/`: stable experiment IDs and provenance metadata
- `REPRODUCING.md`: verified local Linux CPU reproduction procedure

## Install and run

The supported local layout keeps heavyweight inputs at the catalogue root:

```text
<catalogue-root>/
├── llama.cpp/                 # external checkout; ignored
├── models/                    # GGUF weights; ignored
└── papers/profinfer/artifact/ # this repository
```

Install/build the system dependencies and pinned `llama.cpp` revision as described in [`REPRODUCING.md`](REPRODUCING.md). From this artifact root, a single Linux trace is launched with:

```bash
cd Linux
sudo /usr/bin/python3 run_llama.py --config jsons/config.json
```

Multi-model local traces use:

```bash
cd Linux
./run_cpu_models.sh
```

OpenHarmony exposes a Makefile but its complete toolchain and target setup are not documented:

```bash
make -C OpenHarmony
```

## Known limitations

- Setup is not automated or containerised, and no automated test suite is present.
- BCC must be available to system Python and execution generally needs elevated privileges.
- Hardware, kernel, BCC, and OpenHarmony versions are incompletely recorded.
- Linux experiment results under `Linux/experiments/` are generated data and remain ignored; only their provenance metadata is versioned.
- No artifact licence or citation file is present.
