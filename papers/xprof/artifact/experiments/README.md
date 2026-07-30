# XProf experiments

`exp-0001` pre-registers the local installation and demo-profile smoke test.
Create a new sequential experiment for every real run or paper-result family.

```bash
python3 scripts/experiment_versions.py update --paper xprof exp-0001 \
  --reason "Register or update the XProf smoke test"
```

IDs and UIDs are immutable; the content hash versions metadata. Large profiles
remain outside Git and are represented by checksummed manifests.
