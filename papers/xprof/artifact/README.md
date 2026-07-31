# XProf reproducibility artifact

This directory contains XProf from
[`openxla/xprof`](https://github.com/openxla/xprof) at
`713b05f09e30bce895af985cf4846f3274a1e558`. It is tracked directly by
the catalogue repository.

- Upstream documentation: [`UPSTREAM_README.md`](UPSTREAM_README.md)
- Reproduction procedure: [`REPRODUCING.md`](REPRODUCING.md)
- Licence: [`LICENSE`](LICENSE), Apache-2.0
- Experiment catalogue: [`experiments/index.json`](experiments/index.json)

Status: the stable XProf package has processed the two official demo profiles
successfully (`exp-0001`). A build of the pinned source, distributed processing,
new profile collection, and paper-identical scalability results have not been
reproduced in this workspace.

Large checked-in `.xplane.pb` test/demo inputs are omitted from the flattened
artifact to avoid duplicating them in Git. They remain preserved in the
checksummed source ZIP under `../original/` and can be extracted locally.
