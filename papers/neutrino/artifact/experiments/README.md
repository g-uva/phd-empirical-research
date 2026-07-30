# Neutrino experiment catalogue

Each evaluation family starts as a draft experiment. A real execution must get
a new immutable `exp-####` ID and derived UID; do not overwrite a draft with
results from multiple machines or runs.

Create metadata, add it to `index.json`, increment `next_experiment_number`,
register configuration/result checksums in `../../metadata/provenance.json`,
then run:

```bash
python3 scripts/experiment_versions.py update --paper neutrino exp-0007 \
  --reason "Register the new Neutrino experiment"
python3 scripts/experiment_versions.py check
python3 scripts/validate_metadata.py
```

The permanent ID/UID identifies the experiment. The full `content_hash` versions
its metadata and changes when the record changes. Generated traces remain
outside Git; their manifests and checksums belong in provenance metadata.
