# ProfInfer reproducibility artifact

This repository contains the ProfInfer implementations for Linux and OpenHarmony. The implementation layout is preserved from the original checkout; catalogue metadata and experiment provenance are additive.

## Version and provenance

- Artifact package version: `0.1.0` (from `Linux/pyproject.toml`)
- Preserved Git revision: `a311e7c24687b878ec560d77ea7bfd04e9036e04`
- Original ProfInfer repository URL: unknown; this checkout has no configured Git remote
- Paper: [`../paper/profinfer-mlsys-2026.pdf`](../paper/profinfer-mlsys-2026.pdf)
- Required `llama.cpp`: [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) at `d04e7163c85a847bc61d58c22f2c503596db7aa8`
- Documented accelerator fork: [oh-llama.cpp](https://gitcode.com/openharmony-robot/oh-llama.cpp) (revision not recorded)

The clone URL in the pre-existing `Linux/README.md` names `oh-llama.cpp`, not an independently verifiable ProfInfer origin. It is retained as documentation but is not represented as the artifact's original URL.

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
