# Reproducing XProf

No paper-specific end-to-end reproduction script or raw fleet-scale evaluation
dataset was identified in the repository. The steps below validate the released
system and establish the work needed for paper-level reproduction.

## Local smoke test

1. Use Python 3.10--3.13 and create an isolated environment.
2. Install the pinned source with Bazel/Bazelisk as described in
   `UPSTREAM_README.md`, or install the released `xprof` package while recording
   its exact version. A source build is preferred for matching this snapshot.
3. Use the checked-in demo profile or capture a JAX/TensorFlow/PyTorch-XLA
   `.xplane.pb` profile following `docs/`.
4. Start XProf:

   ```bash
   xprof --logdir=/path/to/profile-data --port=6006
   ```

5. Verify the overview, trace viewer, memory profile, graph viewer, and relevant
   analysis tools. Record logs, source/package versions, profile checksum, and
   generated screenshots or exported data.

XProf loads Google Charts from the Internet, so browser access and cluster
network policy affect the UI.

## DAS-6 and SLURM

Profile collection should run in a GPU allocation using `sbatch`/`srun`.
The XProf server can run in the allocation or on an approved service/login
node, subject to DAS-6 policy, with access through SSH port forwarding. Keep
profile collection and UI serving as separate commands. Distributed XProf
workers require allocated nodes, distinct HTTP/gRPC ports, and connectivity
between jobs; do not assume arbitrary inbound ports are available.

## Paper-level reproduction still required

Recover from the authors or supplementary materials the exact hardware,
framework versions, workload/profile inputs, worker counts, trace sizes,
baselines, metrics, repetitions, and commands behind each MLSys 2026 result.
Register each real execution as a new experiment and preserve profile manifests
rather than committing large `.xplane.pb` files.
