# Research papers and reproducibility artifacts

This repository is a versioned catalogue for research papers, their software artifacts, and the scientific lineage of experiments. Manuscripts and publication metadata live under `paper/` and `metadata/`; executable code, installation guidance, and experiment provenance live under `artifact/`.

## Current research direction

As of **2026-07-30**, the research direction is building a reproducible
taxonomy around **observability, profiling, characterisation, and telemetry**
for GPU-accelerated AI workloads. The current catalogue-development phase
focuses on **profiling**. See
[`docs/research-direction.md`](docs/research-direction.md) for the living scope
statement and definitions.

## Repository instance and cluster execution

This catalogue instance is hosted on the DAS-6 cluster and has access to
GPU-equipped compute nodes. Reproduction procedures imported from upstream
repositories may assume an interactive workstation and are not automatically
safe or suitable for cluster execution.

Artifacts should therefore gain SLURM-compatible launch wrappers where
possible. A wrapper should preserve the original scientific command while
handling scheduler resource requests, GPU allocation, environment modules or
virtual environments, input staging, working/scratch directories, time limits,
logs, exit status, and environment capture. CPU/GPU-intensive work must run in
an allocated job rather than on a login node.

SLURM adaptation is generally possible for batch-oriented CPU and GPU
experiments, including Neutrino's static analysis and non-interactive dynamic
GPU collection. Interactive notebooks can run inside an interactive allocation
or be converted to parameterised, non-interactive execution. Hardware probing,
privileged tracing, kernel features, network downloads, and access to
performance counters may still be restricted by DAS-6 policy and must be
validated rather than assumed.

Cluster-specific partitions, GPU resource syntax, modules, storage paths, and
time limits must remain configurable and be documented per artifact. The
original upstream command should remain visible alongside its SLURM wrapper so
that scheduler adaptation does not silently alter the experiment.

## Repository catalogue

| Research work | Paper version | Artifact status | Artifact version | Paper | Artifact and installation | Metadata | Experiments |
|---|---:|---|---:|---|---|---|---|
| ProfInfer | MLSys 2026 manuscript | Working; Linux CPU subset reproduced locally | `0.1.0` / upstream `210890a1` | [PDF](papers/profinfer/paper/2026-profinfer-eurosys.pdf) | [README](papers/profinfer/artifact/README.md) | [Paper](papers/profinfer/metadata/paper.json) · [Artifact](papers/profinfer/metadata/artifact.json) | [Index](papers/profinfer/artifact/experiments/index.json) |
| Neutrino | OSDI 2025 | Available; not yet executed locally | `0.1.0` / main `4a82cd22` / AE `43182f30` | [PDF](papers/neutrino/paper/2025-neutrino-osdi.pdf) | [README](papers/neutrino/artifact/README.md) · [Reproducing](papers/neutrino/artifact/REPRODUCING.md) | [Paper](papers/neutrino/metadata/paper.json) · [Artifact](papers/neutrino/metadata/artifact.json) | [Index](papers/neutrino/artifact/experiments/index.json) |
| XProf | MLSys 2026 | Available; not yet built or evaluated locally | Upstream `713b05f0` | [PDF](papers/xprof/paper/2026-xprof-mlsys.pdf) | [README](papers/xprof/artifact/README.md) · [Reproducing](papers/xprof/artifact/REPRODUCING.md) | [Paper](papers/xprof/metadata/paper.json) · [Artifact](papers/xprof/metadata/artifact.json) | [Index](papers/xprof/artifact/experiments/index.json) |
| eGPU | HCDS 2025 | Original paper artifact available; not yet built or evaluated locally | Upstream `166c175b` | [PDF](papers/egpu/paper/2025-egpu-hcds.pdf) | [README](papers/egpu/artifact/README.md) · [Reproducing](papers/egpu/artifact/REPRODUCING.md) | [Paper](papers/egpu/metadata/paper.json) · [Artifact](papers/egpu/metadata/artifact.json) | [Index](papers/egpu/artifact/experiments/index.json) |
| eInfer | eBPF 2025 | Public artifact unavailable; review due 2026-09-08 | Not available | [PDF](papers/einfer/paper/2025-einfer.pdf) | [Status](papers/einfer/artifact/README.md) · [Reminder](papers/einfer/REMINDER.md) | [Paper](papers/einfer/metadata/paper.json) · [Artifact](papers/einfer/metadata/artifact.json) | [Empty index](papers/einfer/artifact/experiments/index.json) |

External repositories used by the current artifact are pinned or marked unknown explicitly:

| Repository | Role | Status | Current/pinned version | Original link |
|---|---|---|---|---|
| ProfInfer artifact | Research implementation; tracked directly in this catalogue | Pinned snapshot preserved | Upstream `210890a1f06c`; catalogue import `a311e7c` | [Canonical ProfInfer directory](https://gitcode.com/openharmony-robot/oh-llama.cpp/tree/main/profinfer) · [snapshot details](papers/profinfer/original/README.md) |
| llama.cpp | Local inference dependency; excluded from Git | Present locally | `d04e7163` | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| oh-llama.cpp | Upstream containing ProfInfer and optional accelerator-capable code | ProfInfer snapshot pinned; accelerator build not validated | `210890a1f06c` for preserved ProfInfer source | [OpenHarmony fork](https://gitcode.com/openharmony-robot/oh-llama.cpp) |
| Neutrino | GPU kernel profiler and OSDI artifact | Main and artifact-evaluation snapshots pinned; not run locally | Main `4a82cd22f474`; artifact `43182f3082f5` | [open-neutrino/neutrino](https://github.com/open-neutrino/neutrino) |
| XProf | Modern ML profiling system | Snapshot pinned; not run locally | `713b05f09e30` | [openxla/xprof](https://github.com/openxla/xprof) |
| eGPU | GPU eBPF runtime and original paper artifact | Snapshot pinned; not run locally | `166c175bdc6c` | [eunomia-bpf/eGPU](https://github.com/eunomia-bpf/eGPU) |
| eInfer | Distributed LLM tracing artifact | Unavailable; reminder open | Unknown | No verified source; review on 2026-09-08 |

The machine-readable entry point is [`catalog.json`](catalog.json). Its metadata
model is documented in [`docs/metadata-model.md`](docs/metadata-model.md). The
repeatable contributor and Agent/LLM workflow is documented in
[`AGENTS.md`](AGENTS.md) and
[`docs/adding-research-work.md`](docs/adding-research-work.md).

### Reproducibility completeness checklist

| Item | ProfInfer | Evidence or remaining work |
|---|:---:|---|
| Paper PDF | ✅ | [`papers/profinfer/paper/`](papers/profinfer/paper/) |
| Artifact source tracked | ✅ | [`papers/profinfer/artifact/`](papers/profinfer/artifact/) |
| Canonical upstream URL | ✅ | [Upstream `profinfer/`](https://gitcode.com/openharmony-robot/oh-llama.cpp/tree/main/profinfer) |
| Pinned upstream revision | ✅ | `210890a1f06cc837179d83e96fa0ea5327f9bf9d` |
| Original source snapshot and SHA-256 | ✅ | [`papers/profinfer/original/README.md`](papers/profinfer/original/README.md) |
| Installation and reproduction instructions | ✅ | [`REPRODUCING.md`](papers/profinfer/artifact/REPRODUCING.md) |
| Experiment IDs, lineage, and content hashes | ✅ | [`experiments/index.json`](papers/profinfer/artifact/experiments/index.json) |
| Linux CPU subset reproduced | ✅ | Local traces and registered provenance |
| ARM/accelerator/OpenHarmony paths reproduced | ❌ | Procedures defined; hardware/vendor inputs remain missing |
| Paper-identical results reproduced | ❌ | Exact hardware and full experiment mapping remain missing |
| Automated metadata/hash validation | ✅ | Local Git hooks and GitHub Actions |
| Artifact licence and citation | ❌ | No covering upstream licence or citation file found |

### Neutrino

| Item | Status | Evidence or remaining work |
|---|:---:|---|
| Paper PDF | ✅ | [`papers/neutrino/paper/`](papers/neutrino/paper/) |
| Artifact source tracked directly | ✅ | [`papers/neutrino/artifact/`](papers/neutrino/artifact/) |
| Canonical upstream URL | ✅ | [open-neutrino/neutrino](https://github.com/open-neutrino/neutrino) |
| Main and artifact revisions pinned | ✅ | `4a82cd22…` and `43182f30…` |
| Original source snapshots and SHA-256 | ✅ | [`papers/neutrino/original/README.md`](papers/neutrino/original/README.md) |
| Installation and reproduction instructions | ✅ | [`REPRODUCING.md`](papers/neutrino/artifact/REPRODUCING.md) |
| Experiment IDs, lineage, and content hashes | ✅ | [`experiments/index.json`](papers/neutrino/artifact/experiments/index.json) |
| Static trace evaluation reproduced locally | ❌ | Official notebook preserved; not run in this workspace |
| Dynamic GPU evaluation reproduced locally | ❌ | Requires a validated CUDA/PTX environment and GPU |
| Paper-identical A100 results reproduced | ❌ | No local A100 execution; some original upstream traces were deleted |
| Artifact licence resolved | ❌ | Upstream statements conflict and licence texts are absent |
| Citation available | ✅ | Upstream README supplies the OSDI 2025 BibTeX |

### XProf

| Item | Status | Evidence or remaining work |
|---|:---:|---|
| Paper PDF | ✅ | [`papers/xprof/paper/`](papers/xprof/paper/) |
| Artifact source tracked directly | ✅ | [`papers/xprof/artifact/`](papers/xprof/artifact/) |
| Canonical upstream URL | ✅ | [openxla/xprof](https://github.com/openxla/xprof) |
| Pinned upstream revision | ✅ | `713b05f09e30…` |
| Original source snapshot and SHA-256 | ✅ | [`papers/xprof/original/README.md`](papers/xprof/original/README.md) |
| Installation and SLURM-aware reproduction guide | ✅ | [`REPRODUCING.md`](papers/xprof/artifact/REPRODUCING.md) |
| Experiment IDs, lineage, and content hashes | ✅ | [`experiments/index.json`](papers/xprof/artifact/experiments/index.json) |
| Local build/demo-profile processing | ❌ | Not yet executed |
| Paper-scale distributed/scalability results | ❌ | Raw profiles and exact evaluation matrix not identified |
| Artifact licence | ✅ | Apache-2.0; see [`artifact/LICENSE`](papers/xprof/artifact/LICENSE) |
| Citation available | ✅ | Citation guidance is preserved in the upstream README |

### eGPU

| Item | Status | Evidence or remaining work |
|---|:---:|---|
| Paper PDF | ✅ | [`papers/egpu/paper/`](papers/egpu/paper/) |
| Artifact source tracked directly | ✅ | [`papers/egpu/artifact/`](papers/egpu/artifact/) |
| Canonical upstream URL | ✅ | [eunomia-bpf/eGPU](https://github.com/eunomia-bpf/eGPU) |
| Pinned upstream revision | ✅ | `166c175bdc6c…` |
| Original source snapshot and SHA-256 | ✅ | [`papers/egpu/original/README.md`](papers/egpu/original/README.md) |
| Installation and SLURM-aware reproduction guide | ✅ | [`REPRODUCING.md`](papers/egpu/artifact/REPRODUCING.md) |
| Experiment IDs, lineage, and content hashes | ✅ | [`experiments/index.json`](papers/egpu/artifact/experiments/index.json) |
| CUDA/eBPF build and smoke test | ❌ | Privileged/container requirements remain unvalidated on DAS-6 |
| Paper-identical results | ❌ | Plot summaries exist, but raw measurement provenance is missing |
| Artifact licence | ✅ | MIT; see [`artifact/LICENSE`](papers/egpu/artifact/LICENSE) |
| Citation available | ✅ | [`artifact/CITATION.cff`](papers/egpu/artifact/CITATION.cff) |

### eInfer

| Item | Status | Evidence or remaining work |
|---|:---:|---|
| Paper PDF | ✅ | [`papers/einfer/paper/`](papers/einfer/paper/) |
| Paper and DOI metadata | ✅ | [`metadata/paper.json`](papers/einfer/metadata/paper.json) |
| Canonical upstream URL | ❌ | No verified official source currently available |
| Pinned upstream revision | ❌ | Blocked until an official artifact is released |
| Original source snapshot and SHA-256 | ❌ | No source is available to archive |
| Official public artifact | ❌ | No verified source currently available |
| Installation and reproduction instructions | ❌ | Cannot be completed without the artifact |
| Experiment IDs, lineage, and content hashes | ✅ | [Empty index](papers/einfer/artifact/experiments/index.json), by design |
| Local or paper-identical results reproduced | ❌ | No executable artifact exists |
| Artifact licence and citation | ❌ | Blocked until an official release |
| Availability reminder | ⏰ | Review on **2026-09-08**; see [`docs/reminders.md`](docs/reminders.md) |

## Interactive graph

Generate an interactive, black-outlined Cytoscape.js visualisation of the entities, provenance records, and relationships:

```bash
python3 scripts/generate_graph.py
```

Open [`docs/research-graph.html`](docs/research-graph.html) in a browser. The default tree view starts from the paper, artifact, and software roots; click nodes to expand relationships, or use the project and legend-type checkboxes to control visibility. Project choices are generated from `catalog.json`, so future research entries are added to the selector automatically. The graph data is embedded in the HTML; loading Cytoscape.js itself requires an internet connection.

![Interactive ProfInfer metadata graph](assets/screenshot.png)

## Local-only dependencies and data

Model weights and external source checkouts are deliberately not versioned. The root `.gitignore` excludes `models/`, `llama.cpp/`, and the common misspelling `llama.cp/`. Each artifact documents the exact external revision and expected local layout needed for reproduction.

## Adding another paper

Follow the complete layout, provenance, metadata, snapshot, experiment, and
checklist workflow in [`AGENTS.md`](AGENTS.md). In particular, imported
artifacts must be ordinary files in the root repository—not nested Git
repositories. After registering the work in `catalog.json`, run:

```bash
python3 scripts/experiment_versions.py check
python3 scripts/validate_metadata.py
```

Enable the repository-managed commit and push checks once per clone:

```bash
git config core.hooksPath .githooks
```

When experiment metadata changes, refresh its content hash and create
a Git-diff-based change record before committing:

```bash
python3 scripts/experiment_versions.py update --paper profinfer exp-0014 \
  --reason "Describe why this experiment metadata changed"
```

## Committing changes

Enable the managed hooks once per clone:

```bash
git config core.hooksPath .githooks
```

For ordinary changes that do not modify experiment metadata:

```bash
git status
git add .
git status
git commit -m "Describe the change"
git push
```

When creating or modifying an experiment, update its content hash and generate
the machine-readable change record before staging:

```bash
python3 scripts/experiment_versions.py update --paper profinfer exp-0014 \
  --reason "Describe the scientific or metadata change"
git add .
python3 scripts/experiment_versions.py check --staged
git commit -m "Describe the experiment change"
git push
```

The pre-commit hook validates the staged experiment hashes and catalogue
metadata. The pre-push hook repeats validation against the working tree, and
GitHub Actions performs the same checks after pushing or in a pull request.
Hash validation never changes files automatically: an intentional experiment
change must use the explicit `update --reason` command.

Always review the second `git status` before committing. `git add .` stages all
modified, deleted, and untracked files below the current directory, including
work unrelated to the intended commit.

The catalogue and its schema are experimental and will evolve as new papers and experiment families are added.
