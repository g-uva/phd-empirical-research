# Current research direction

**As of 2026-07-30**, the research direction is focused on building a
reproducible taxonomy of methods for understanding GPU-accelerated AI
workloads. The current catalogue-development phase concentrates on
**profiling**.

## Main taxonomy

The taxonomy is organised around four related, but distinct, elements:

1. **Observability** — the overall ability to infer and explain system or
   workload state from externally available signals.
2. **Profiling** — targeted measurement and analysis of workload execution,
   including time, resource use, operators, kernels, memory behaviour, and
   bottlenecks. This is the current focus.
3. **Characterisation** — the systematic description and comparison of
   workload behaviour across models, frameworks, configurations, hardware, and
   experimental conditions.
4. **Telemetry** — the mechanisms and data streams used to collect and export
   runtime or hardware measurements, continuously or during defined
   experiments.

These elements can overlap: telemetry supplies signals; profiling turns
selected measurements into execution-level analyses; characterisation
organises repeatable findings across workloads and configurations; and
observability is the broader capability enabled by these methods.

The research includes investigating how runtime and hardware signals are
collected, related, and interpreted across models, frameworks, operators,
kernels, and accelerator execution. The emphasis is on reproducible
measurement methods and on connecting telemetry sources, profiling or probing
mechanisms, experimental configurations, and observed results through explicit
provenance.

This is a living research-direction statement rather than a claim about the
scope or conclusions of every catalogued paper. Papers may cover one or more
taxonomy elements, and their classification must be supported by evidence. The
statement should be updated and re-dated when the direction materially changes.
