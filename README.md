# Research papers and reproducibility artifacts

This repository is a versioned catalogue for research papers, their software artifacts, and the scientific lineage of experiments. Manuscripts and publication metadata live under `paper/` and `metadata/`; executable code, installation guidance, and experiment provenance live under `artifact/`.

## Current research direction

As of **2026-07-13**, the research direction is focused on **GPU telemetry, observability, and probing approaches for characterising AI workloads**. See [`docs/research-direction.md`](docs/research-direction.md) for the living scope statement.

## Repository catalogue

| Research work | Paper version | Artifact status | Artifact version | Paper | Artifact and installation | Metadata | Experiments |
|---|---:|---|---:|---|---|---|---|
| ProfInfer | MLSys 2026 manuscript | Working; Linux CPU subset reproduced locally | `0.1.0` / `a311e7c` | [PDF](papers/profinfer/paper/profinfer-mlsys-2026.pdf) | [README](papers/profinfer/artifact/README.md) | [Paper](papers/profinfer/metadata/paper.json) · [Artifact](papers/profinfer/metadata/artifact.json) | [Index](papers/profinfer/artifact/experiments/index.json) |

External repositories used by the current artifact are pinned or marked unknown explicitly:

| Repository | Role | Status | Current/pinned version | Original link |
|---|---|---|---|---|
| ProfInfer artifact | Research implementation; tracked directly in this catalogue | Pinned snapshot preserved | Upstream `210890a1f06c`; catalogue import `a311e7c` | [Canonical ProfInfer directory](https://gitcode.com/openharmony-robot/oh-llama.cpp/tree/main/profinfer) · [snapshot details](papers/profinfer/original/README.md) |
| llama.cpp | Local inference dependency; excluded from Git | Present locally | `d04e7163` | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| oh-llama.cpp | Upstream containing ProfInfer and optional accelerator-capable code | ProfInfer snapshot pinned; accelerator build not validated | `210890a1f06c` for preserved ProfInfer source | [OpenHarmony fork](https://gitcode.com/openharmony-robot/oh-llama.cpp) |

The machine-readable entry point is [`catalog.json`](catalog.json). Its metadata model is documented in [`docs/metadata-model.md`](docs/metadata-model.md).

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

Create `papers/<slug>/paper`, `artifact`, and `metadata` directories; place installation and execution guidance at that artifact's root; assign stable namespaced entity IDs; add references to `catalog.json`; and run:

```bash
python3 scripts/experiment_versions.py check
python3 scripts/validate_metadata.py
```

Enable the repository-managed commit and push checks once per clone:

```bash
git config core.hooksPath .githooks
```

When experiment metadata changes, explicitly refresh its content hash and create
a Git-diff-based change record before committing:

```bash
python3 scripts/experiment_versions.py update exp-0014 \
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
python3 scripts/experiment_versions.py update exp-0014 \
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
