#!/usr/bin/env python3
"""Validate the research catalogue without requiring a project framework."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9][a-z0-9.-]*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

VOCABULARY = {
    "research_functions": {
        "measurement-telemetry", "workload-characterisation", "performance-modelling",
        "prediction-inference", "optimisation", "scheduling-resource-management",
        "runtime-systems", "benchmarking-evaluation", "reproducibility", "methodology",
        "survey", "vision",
    },
    "technical_categories": {
        "measurement-and-telemetry", "workload-characterisation", "ai-serving-and-inference",
        "ai-training", "gpu-and-accelerator-systems", "cluster-scheduling", "energy-and-carbon",
        "scientific-workflows", "reproducibility-and-artifacts", "virtualisation-and-cloud-native",
        "distributed-and-federated-systems", "performance-modelling", "benchmarking",
    },
    "system_layers": {
        "application", "model", "framework", "runtime", "operator", "library",
        "accelerator-kernel", "accelerator", "device-driver", "os-kernel", "process-thread",
        "container", "virtual-machine", "node", "cluster", "data-centre", "federation",
        "cloud-edge-continuum",
    },
    "resource_types": {"cpu", "gpu", "accelerator", "memory", "storage", "network", "io", "energy", "power", "carbon", "time", "cost"},
    "workload_types": {"ai-training", "ai-inference", "llm-serving", "batch", "interactive", "scientific-workflow", "data-processing", "microservice", "benchmark", "synthetic"},
    "infrastructure_contexts": {"bare-metal", "containerised", "virtualised", "cloud", "edge", "hpc", "data-centre", "distributed", "federated", "multi-tenant", "heterogeneous"},
    "telemetry_sources": {"hardware-counter", "software-instrumentation", "application-log", "system-call", "ebpf", "cupti", "dcgm", "nvml", "perf", "prometheus", "rapl", "scaphandre", "custom-profiler"},
    "methodologies": {"controlled-experiment", "benchmark", "trace-driven", "simulation", "testbed", "production-deployment", "case-study", "ablation", "sensitivity-analysis", "comparative-evaluation", "statistical-analysis"},
    "sustainability_dimensions": {"energy-efficiency", "power-efficiency", "carbon-efficiency", "resource-efficiency", "hardware-utilisation", "environmental-impact"},
}
EXPERIMENT_STATUSES = {"draft", "working", "validated", "archived", "published"}


def load(path: Path, errors: list[str]) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load {path.relative_to(ROOT)}: {exc}")
        return None


def check_path(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing path referenced by {label}: {path}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    catalogue_path = ROOT / "catalog.json"
    schema_path = ROOT / "schemas/research-catalogue.schema.json"
    catalogue = load(catalogue_path, errors)
    schema = load(schema_path, errors)
    if catalogue is None or schema is None:
        return report(errors, warnings)

    try:
        import jsonschema
    except ImportError:
        warnings.append("jsonschema is unavailable; using built-in root structural checks")
        required = {"$schema", "catalogue_version", "project", "papers", "artifacts"}
        missing = required - set(catalogue)
        if missing:
            errors.append(f"catalog.json lacks required fields: {sorted(missing)}")
        if not SEMVER_RE.fullmatch(str(catalogue.get("catalogue_version", ""))):
            errors.append("catalogue_version is not semantic x.y.z form")
    else:
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.validate(catalogue, schema)
        except jsonschema.exceptions.SchemaError as exc:
            errors.append(f"invalid JSON Schema: {exc.message}")
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(f"catalog.json schema failure at {list(exc.path)}: {exc.message}")

    references = catalogue.get("papers", []) + catalogue.get("artifacts", [])
    reference_ids = [ref.get("id") for ref in references]
    for value, count in Counter(reference_ids).items():
        if count > 1:
            errors.append(f"duplicate root catalogue ID: {value}")

    documents: dict[str, Any] = {}
    document_paths: dict[str, Path] = {}
    for ref in references:
        ref_id, relpath = ref.get("id"), ref.get("path")
        if not ID_RE.fullmatch(str(ref_id)):
            errors.append(f"invalid namespaced ID: {ref_id}")
        path = ROOT / str(relpath)
        check_path(path, f"catalogue entry {ref_id}", errors)
        doc = load(path, errors) if path.exists() else None
        if doc is not None:
            documents[ref_id] = doc
            document_paths[ref_id] = path
            if doc.get("id") != ref_id:
                errors.append(f"{relpath} ID does not match catalogue reference {ref_id}")

    work_slugs = {
        Path(str(ref.get("path"))).parts[1]
        for ref in references
        if len(Path(str(ref.get("path"))).parts) >= 3
        and Path(str(ref.get("path"))).parts[0] == "papers"
    }
    required_work_paths = (
        "README.md",
        "paper",
        "artifact/README.md",
        "artifact/REPRODUCING.md",
        "artifact/experiments/README.md",
        "artifact/experiments/index.json",
        "metadata/paper.json",
        "metadata/artifact.json",
        "metadata/entities.json",
        "metadata/provenance.json",
        "metadata/relationships.json",
        "original/README.md",
    )
    for slug in sorted(work_slugs):
        work_root = ROOT / "papers" / slug
        for relative in required_work_paths:
            check_path(work_root / relative, f"required {slug} catalogue layout", errors)
        if not list((work_root / "original").glob("*.zip")):
            errors.append(f"no original source ZIP is preserved for {slug}")
        nested_git = list(work_root.rglob(".git"))
        if nested_git:
            errors.append(
                f"nested Git metadata is forbidden for {slug}: "
                f"{[str(path.relative_to(ROOT)) for path in nested_git]}"
            )

    metadata_sets: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    entity_records: list[dict[str, Any]] = []
    for metadata_dir in sorted((ROOT / "papers").glob("*/metadata")):
        entities_path = metadata_dir / "entities.json"
        provenance_path = metadata_dir / "provenance.json"
        entities = load(entities_path, errors) or {}
        provenance = load(provenance_path, errors) or {}
        metadata_sets.append((metadata_dir, entities, provenance))
        for collection in (
            "people", "organisations", "software", "datasets", "experiments",
            "venues", "funding_projects",
        ):
            entity_records.extend(entities.get(collection, []))
        for collection in ("configurations", "results"):
            entity_records.extend(provenance.get(collection, []))

    definition_ids = list(documents) + [record.get("id") for record in entity_records]
    for value, count in Counter(definition_ids).items():
        if count > 1:
            errors.append(f"duplicate defined entity ID: {value}")
        if not ID_RE.fullmatch(str(value)):
            errors.append(f"invalid defined entity ID: {value}")

    for metadata_dir, entities, provenance in metadata_sets:
        for record in entities.get("experiments", []):
            relpath = record.get("metadata_path")
            if relpath:
                check_path(
                    (metadata_dir / relpath).resolve(),
                    f"experiment {record.get('id')}",
                    errors,
                )

        for record in provenance.get("configurations", []):
            digest = record.get("sha256")
            if not SHA256_RE.fullmatch(str(digest)):
                errors.append(
                    f"invalid configuration SHA-256 for {record.get('id')}: {digest}"
                )
            path = (metadata_dir / str(record.get("path"))).resolve()
            if path.exists():
                observed = hashlib.sha256(path.read_bytes()).hexdigest()
                if observed != digest:
                    errors.append(
                        f"configuration checksum mismatch for {record.get('id')}"
                    )
            else:
                warnings.append(
                    f"local-only configuration is absent: {record.get('id')}"
                )

        for record in provenance.get("results", []):
            digest = record.get("manifest_sha256")
            if not SHA256_RE.fullmatch(str(digest)):
                errors.append(
                    f"invalid result manifest SHA-256 for {record.get('id')}: {digest}"
                )
            directory = (metadata_dir / str(record.get("path"))).resolve()
            if directory.exists():
                manifest = b""
                for name in sorted(record.get("files", [])):
                    path = directory / name
                    if not path.exists():
                        errors.append(
                            f"missing generated file for {record.get('id')}: {name}"
                        )
                        continue
                    file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    manifest += f"{file_digest}  {name}\n".encode("utf-8")
                observed = hashlib.sha256(manifest).hexdigest()
                if observed != digest:
                    errors.append(
                        f"result manifest checksum mismatch for {record.get('id')}"
                    )
            else:
                warnings.append(
                    f"local-only result bundle is absent: {record.get('id')}"
                )

    for paper_id, paper in documents.items():
        if not paper_id.startswith("paper:"):
            continue
        for axis, allowed in VOCABULARY.items():
            values = paper.get("classification", {}).get(axis, [])
            invalid = sorted(set(values) - allowed)
            if invalid:
                errors.append(
                    f"invalid classification values for {paper_id}.{axis}: {invalid}"
                )

    for doc_id, doc in documents.items():
        base = document_paths[doc_id].parent
        source_path = doc.get("source_path")
        if source_path:
            check_path((base / source_path).resolve(), f"{doc_id}.source_path", errors)
        for component in doc.get("components", []):
            if component.get("path"):
                check_path((base / component["path"]).resolve(), f"component {component.get('name')}", errors)

    for index_path in sorted((ROOT / "papers").glob("*/artifact/experiments/index.json")):
        index = load(index_path, errors) or {}
        experiment_ids = [entry.get("id") for entry in index.get("experiments", [])]
        experiment_uids = [entry.get("uid") for entry in index.get("experiments", [])]
        for value, count in Counter(experiment_ids).items():
            if count > 1:
                errors.append(f"duplicate experiment ID in {index_path}: {value}")
        for value, count in Counter(experiment_uids).items():
            if count > 1:
                errors.append(f"duplicate experiment UID in {index_path}: {value}")
        issued_numbers: list[int] = []
        for entry in index.get("experiments", []):
            match = re.fullmatch(r"exp-([0-9]{4})", str(entry.get("id")))
            if not match:
                errors.append(f"invalid experiment ID: {entry.get('id')}")
                continue
            issued_numbers.append(int(match.group(1)))
            uid = entry.get("uid")
            if not re.fullmatch(r"[0-9a-f]{8}", str(uid)):
                errors.append(f"invalid experiment UID for {entry.get('id')}: {uid}")
            expected_uid = hashlib.sha256(
                f"{index.get('artifact')}/{entry.get('id')}".encode("utf-8")
            ).hexdigest()[:8]
            if uid != expected_uid:
                errors.append(
                    f"incorrect derived UID for {entry.get('id')}: "
                    f"expected {expected_uid}, got {uid}"
                )
            metadata_path = index_path.parent / str(entry.get("path"))
            check_path(
                metadata_path, f"experiment index entry {entry.get('id')}", errors
            )
            metadata = load(metadata_path, errors) if metadata_path.exists() else None
            if metadata:
                if metadata.get("id") != entry.get("id"):
                    errors.append(
                        f"experiment metadata ID mismatch in {metadata_path}"
                    )
                if metadata.get("uid") != uid:
                    errors.append(
                        f"experiment metadata UID mismatch in {metadata_path}"
                    )
                if metadata.get("status") not in EXPERIMENT_STATUSES:
                    errors.append(
                        f"invalid status for {entry.get('id')}: "
                        f"{metadata.get('status')}"
                    )
                content_hash = metadata.get("content_hash")
                if not SHA256_RE.fullmatch(str(content_hash)):
                    errors.append(
                        f"invalid content hash for {entry.get('id')}: {content_hash}"
                    )
                if entry.get("content_hash") != content_hash:
                    errors.append(
                        f"experiment index content hash mismatch for {entry.get('id')}"
                    )
                parent = metadata.get("parent")
                if parent is not None and parent not in experiment_ids:
                    errors.append(
                        f"unresolved parent for {entry.get('id')}: {parent}"
                    )
        next_number = index.get("next_experiment_number")
        if issued_numbers and (
            not isinstance(next_number, int) or next_number <= max(issued_numbers)
        ):
            errors.append(
                f"next_experiment_number must exceed every issued number in {index_path}"
            )

    for artifact_id, artifact in documents.items():
        if not artifact_id.startswith("artifact:"):
            continue
        snapshots = artifact.get("original_source_snapshots")
        if snapshots is None:
            singular = artifact.get("original_source_snapshot")
            snapshots = [singular] if singular else []
        if not snapshots:
            errors.append(f"{artifact_id} has no original source snapshot metadata")
        for snapshot in snapshots:
            snapshot_path = ROOT / str(snapshot.get("path", ""))
            snapshot_digest = snapshot.get("sha256")
            if not SHA256_RE.fullmatch(str(snapshot_digest)):
                errors.append(
                    f"invalid original source snapshot SHA-256 for {artifact_id}: "
                    f"{snapshot_digest}"
                )
            elif snapshot_path.is_file():
                observed = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
                if observed != snapshot_digest:
                    errors.append(
                        f"original source snapshot checksum mismatch for {artifact_id}"
                    )
            else:
                errors.append(f"missing original source snapshot: {snapshot_path}")

    known_ids = set(definition_ids)
    allowed_predicates = {
        "has-artifact", "supports-paper", "authored-by", "affiliated-with", "uses-software",
        "uses-dataset", "produces-dataset", "defines-experiment", "evaluates-with",
        "implements-method", "extends-paper", "compares-against", "funded-by", "published-at",
        "addresses-research-question", "classified-as", "produces-result", "implements-software",
        "uses-configuration", "derived-from",
    }
    for metadata_dir, _, _ in metadata_sets:
        relationships = load(metadata_dir / "relationships.json", errors) or {}
        for rel in relationships.get("relationships", []):
            if rel.get("predicate") not in allowed_predicates:
                errors.append(f"unsupported predicate: {rel.get('predicate')}")
            for endpoint in ("source", "target"):
                if rel.get(endpoint) not in known_ids:
                    errors.append(
                        f"unresolved relationship {endpoint}: {rel.get(endpoint)}"
                    )

    return report(errors, warnings)


def report(errors: list[str], warnings: list[str]) -> int:
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"metadata validation failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("metadata validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
