# eGPU reproducibility artifact

This is the original eGPU paper artifact from
[`eunomia-bpf/eGPU`](https://github.com/eunomia-bpf/eGPU), pinned at
`166c175bdc6c654fe115a261b0aa00c3aaf092f9` and tracked directly by this
catalogue.

- Upstream documentation: [`UPSTREAM_README.md`](UPSTREAM_README.md)
- Reproduction procedure: [`REPRODUCING.md`](REPRODUCING.md)
- Licence: [`LICENSE`](LICENSE), MIT
- Citation: [`CITATION.cff`](CITATION.cff)
- Paper-result plotting material: [`artifact/`](artifact/)

Status: source, plotting scripts, and reported plots are present; the Docker
build, CUDA instrumentation, benchmarks, and paper-identical results have not
been reproduced locally.

The bundled MNIST input directory is omitted from the flattened artifact to
avoid duplicating large data in Git. It remains preserved in the checksummed
source ZIP under `../original/`.
