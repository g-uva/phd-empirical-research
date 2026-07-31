# XProf experiments

`exp-0001` records the completed local installation and official demo-profile
smoke test. Its runnable script and result manifest are stored with its
metadata. Create a new sequential experiment for every later scientific run or
paper-result family; do not rewrite this execution as a different run.

```bash
python3 scripts/experiment_versions.py update --paper xprof exp-0001 \
  --reason "Register or update the XProf smoke test"
```

IDs and UIDs are immutable; the content hash versions metadata. Large profiles
remain outside Git and are represented by checksummed manifests.
