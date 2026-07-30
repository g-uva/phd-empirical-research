# Agent/LLM guideline for catalogue work

This repository uses one root Git history. Never retain or create nested `.git`
directories, submodules, or Gitlinks under `papers/`. Upstream history is
represented by canonical URLs, pinned revisions, and checksummed snapshots.

## Adding a paper and artifact

For every `papers/<slug>/`, create and complete:

```text
papers/<slug>/
├── README.md
├── paper/
├── artifact/
│   ├── README.md
│   ├── REPRODUCING.md
│   └── experiments/
│       ├── README.md
│       ├── index.json
│       ├── changes/
│       └── exp-####/metadata.json
├── metadata/
│   ├── paper.json
│   ├── artifact.json
│   ├── entities.json
│   ├── provenance.json
│   └── relationships.json
└── original/
    ├── README.md
    └── <pinned-source-snapshot>.zip
```

Use evidence from the paper, upstream repository, artifact instructions, Git
metadata, or observed runs. Never turn a plausible value into a fact. Record
unknown or conflicting information in `metadata_gaps`.

## Required provenance

1. Resolve and record the canonical upstream repository/directory URL.
2. Pin the exact revision used. Do not archive a moving branch name alone.
3. Preserve a deterministic ZIP with `git archive` when redistribution is
   appropriate, recording SHA-256, scope, revision, and creation notes.
4. Inspect licence and citation files. If licence text is absent or statements
   conflict, mark licence status unresolved.
5. Flatten imported code into `artifact/`; move a nested `.git` directory to a
   temporary backup before removing the parent Gitlink from the index.
6. Keep large models, trace bundles, generated outputs, and external checkouts
   out of Git unless explicitly preserved. Register URLs, revisions, checksums,
   and manifests in metadata.

## Required documentation and metadata

- Root catalogue table and per-work reproducibility checklist.
- Paper title, version, venue/year, authors, source path, classification, and
  evidence.
- Artifact source/revisions, snapshots, components, entry points, dependencies,
  reproducibility status, licence/citation status, and evidence gaps.
- Namespaced people, organisations, software, datasets, experiments, venues,
  configurations, and result bundles.
- Evidence-backed relationships whose endpoints resolve.
- Detailed static and dynamic reproduction procedures, expected outputs,
  hardware/software requirements, and honest “not reproduced” statements.

## Experiment identity and versioning

- `exp-####` is immutable and sequential within one artifact.
- `uid` is immutable and derived from the first eight SHA-256 characters of
  `<artifact-id>/<experiment-id>`.
- `content_hash` is a mutable SHA-256 version fingerprint of canonical metadata.
- Never reuse an ID or silently rewrite an existing run as a different run.
- Prefer a new experiment with `parent` lineage for a new scientific execution.
- Register tracked configurations and local result manifests in
  `metadata/provenance.json`.

After creating or changing experiment metadata:

```bash
python3 scripts/experiment_versions.py update --paper <slug> exp-#### \
  --reason "Explain the scientific or metadata change"
python3 scripts/experiment_versions.py check
python3 scripts/validate_metadata.py
```

The update command must generate the JSON change record. Validators must never
silently rewrite hashes.

## Completion checklist

- [ ] Paper stored under `paper/`
- [ ] Artifact source flattened and tracked
- [ ] No nested `.git` directory or Gitlink
- [ ] Canonical upstream URL and pinned revision recorded
- [ ] Original ZIP(s) and SHA-256 recorded
- [ ] Licence and citation status verified or marked unresolved
- [ ] Artifact installation and reproduction instructions written
- [ ] Paper and artifact registered in `catalog.json`
- [ ] Entities, provenance, and relationships validate
- [ ] Experiment index, UIDs, content hashes, and change records validate
- [ ] Root README catalogue and checklist updated
- [ ] Static/dynamic/paper-identical reproduction status stated truthfully
- [ ] `git diff --check`, hash validation, and metadata validation pass

Before committing, inspect both `git status` outputs:

```bash
git status
git add .
git status
python3 scripts/experiment_versions.py check --staged
git commit -m "Describe the catalogue change"
git push
```
