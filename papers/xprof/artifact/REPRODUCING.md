# Reproducing XProf

The validated use case serves the two official TPU training profiles preserved
in the pinned source ZIP. It requires no accelerator because it processes an
existing trace. On 31 July 2026 it passed with Linux x86-64, Python 3.12.3 and
`xprof==2.22.3`; see `experiments/exp-0001/result.json`.

## Quick reproduction

Requirements are Python 3.10--3.13, `venv`, `pip`, `unzip`, Internet access for
package installation, and a browser. From this directory run:

```bash
experiments/exp-0001/run_demo.sh
```

The script verifies that the checksummed catalogue snapshot exists, extracts
only `xprof/demo/` to a temporary directory, creates an isolated environment,
installs the tested XProf version, and starts the server on port 8791. Override
the port or retained working directory when needed:

```bash
XPROF_PORT=6006 XPROF_WORKDIR=/tmp/xprof-demo \
  experiments/exp-0001/run_demo.sh
```

Open `http://127.0.0.1:8791/`. The run selector should contain
`v6e-4-training` and `tpu-training`. For each run, XProf should offer Overview,
Trace Viewer, Graph Viewer, Op Profile, Input Pipeline, Memory Profile/Viewer,
Roofline Model, Framework Op Stats, and HLO Stats. Stop it with Ctrl-C.

This is the experiment: XProf reads and processes two pre-recorded
`.xplane.pb` profiles and presents their analysis in the browser. It does not
rerun the original TPU training computation. To validate the run manually:

1. Confirm that the header reports XProf `v2.22.3`.
2. Open the session selector and confirm both `v6e-4-training` and
   `tpu-training` are present.
3. Select each session and open at least one analysis tool. Graph Viewer has
   been manually confirmed to render HLO modules and operation graphs.
4. Confirm that **Capture Profile** opens its recording dialog. This only
   confirms the capture interface is available; capturing requires a separate
   compatible JAX/TensorFlow profiling service and is not part of `exp-0001`.

XProf loads Google Charts from the Internet, so some charts and tables may be
missing behind a firewall. The first request can log a missing
`.cached_tools.json`; XProf then derives and writes this cache in the temporary
demo directory. This is expected, not a failed run.

## Manual equivalent

```bash
workdir=$(mktemp -d /tmp/xprof-demo.XXXXXX)
unzip ../original/xprof-713b05f09e30.zip 'xprof/demo/*' -d "$workdir"
python3 -m venv "$workdir/venv"
"$workdir/venv/bin/pip" install --upgrade pip
"$workdir/venv/bin/pip" install 'setuptools<70' 'xprof==2.22.3'
"$workdir/venv/bin/xprof" --logdir="$workdir/xprof/demo" --port=8791
```

The source snapshot is pinned at revision
`713b05f09e30bce895af985cf4846f3274a1e558`. Building that exact source instead
of using the tested release package remains an unvalidated alternative; follow
the Bazel procedure in `UPSTREAM_README.md` if source equivalence is required.

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
