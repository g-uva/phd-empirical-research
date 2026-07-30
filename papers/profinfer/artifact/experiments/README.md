# Experiment provenance

This directory records scientific experiment identity and intent. It does not replace Git and it does not store model weights or generated trace data.

## Creating an experiment

1. Read `next_experiment_number` in `index.json` and assign that number as an immutable zero-padded ID such as `exp-0015`.
2. Generate the experiment's immutable `uid` as the first eight lowercase hexadecimal characters of SHA-256 over `<artifact-id>/<experiment-id>`. For example:

   ```bash
   printf '%s' 'artifact:profinfer/exp-0015' | sha256sum | cut -c1-8
   ```

3. Create `exp-0015/metadata.json` from an existing metadata file and record both `"id": "exp-0015"` and the generated `uid`, leaving unknown scientific values `null` or empty.
4. Record the objective, exact command, configurations, datasets/model artifacts, expected outputs, and the Git commit before execution.
5. Set `parent` only when the new run is a scientific continuation of a prior experiment. Parent references use the readable `exp-####` ID.
6. Add the `id`, `uid`, metadata path, and status to `index.json`, then increment `next_experiment_number`. Never reuse either identifier.
7. Run `python3 scripts/validate_metadata.py` from the catalogue root. It rejects malformed, duplicate, mismatched, or incorrectly derived UIDs.
8. Generate the experiment `content_hash` and its change record:

   ```bash
   python3 scripts/experiment_versions.py update exp-0015 \
     --reason "Register exp-0015"
   ```

9. Change status through `draft`, `working`, `validated`, `archived`, or `published` as evidence warrants. Tags or releases are only appropriate for published experiments and are never created automatically by this workflow.

## Identity, versions, and change checks

`id` and `uid` are permanent identities and never change. `content_hash` is a
SHA-256 version fingerprint of the canonical experiment metadata and changes
when that metadata changes. The hash is stored both in `metadata.json` and the
index. It incorporates referenced configuration/result checksums through their
metadata values; local generated files remain outside Git.

Run `python3 scripts/experiment_versions.py check` before committing. For an
intentional edit, use `update --reason ...`; this refreshes the hash and writes
a timestamped, machine-readable record under `changes/` with old/new hashes and
the current Git working-tree change list. Repository hooks and CI reject stale
or missing hashes.

The sequential `exp-####` value remains the primary human-readable identity and directory name. The eight-character `uid` is a compact artifact-scoped alias; it is not a cryptographic security token or a globally collision-proof identifier. Both values are immutable once issued.

Git captures how files changed. Experiment metadata captures why a run exists and which inputs produced which outputs. Generated files remain under `Linux/experiments/` and are ignored; `actual_outputs` may point to those local paths. Future metadata may add hardware, containers, seeds, runtime parameters, metrics, figures, RO-Crate, Zenodo DOI, or evaluation badges when evidence is available.

## Configuration and output provenance

When an experiment acquires real files, add them to `../../metadata/provenance.json` rather than committing generated data:

- Identify its captured configuration as `configuration:<artifact>-<experiment>`, record its path and SHA-256, and add an experiment `uses-configuration` relationship.
- Identify its generated files as one bundle named `result:<artifact>-<experiment>-outputs`, record the directory, file manifest and manifest SHA-256, and add an experiment `produces-result` relationship.
- Connect the result bundle to the configuration with `derived-from`.
- Express the experiment's software and dataset inputs with `uses-software` and `uses-dataset` relationships.

The configuration and result IDs remain stable even when the corresponding local-only files are unavailable. A changed configuration or output bundle must receive new provenance rather than silently replacing the checksum associated with an existing identity.
