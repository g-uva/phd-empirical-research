#!/usr/bin/env python3
"""Generate an expandable Cytoscape.js view of the research metadata graph."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/research-graph.html"

COLLECTION_KINDS = {
    "people": "person",
    "organisations": "organisation",
    "software": "software",
    "datasets": "dataset",
    "experiments": "experiment",
    "venues": "venue",
    "funding_projects": "funding-project",
    "configurations": "configuration",
    "results": "result",
}


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def display_label(record: dict[str, Any]) -> str:
    return str(
        record.get("short_name")
        or record.get("name")
        or record.get("title")
        or record["id"]
    )


def add_node(
    nodes: dict[str, dict[str, Any]],
    record: dict[str, Any],
    kind: str,
    project: str,
) -> None:
    identifier = record["id"]
    if identifier in nodes:
        projects = nodes[identifier]["data"]["projects"]
        if project not in projects:
            projects.append(project)
        return
    nodes[identifier] = {
        "data": {
            "id": identifier,
            "label": display_label(record),
            "kind": kind,
            "projects": [project],
            "root": 0,
            "metadata": json.dumps(record, indent=2, ensure_ascii=False),
        }
    }


def build_elements() -> tuple[list[dict[str, Any]], list[str], list[dict[str, str]]]:
    catalogue = load(ROOT / "catalog.json")
    nodes: dict[str, dict[str, Any]] = {}
    metadata_projects: dict[Path, str] = {}
    projects: dict[str, dict[str, str]] = {}

    for reference in catalogue["papers"]:
        path = ROOT / reference["path"]
        record = load(path)
        project = record["id"].split(":", 1)[1]
        projects[project] = {"id": project, "label": display_label(record)}
        metadata_projects[path.parent] = project
        add_node(nodes, record, "paper", project)

    for reference in catalogue["artifacts"]:
        record = load(ROOT / reference["path"])
        supported_paper = str(record.get("supports_paper", ""))
        project = supported_paper.split(":", 1)[-1] or record["id"].split(":", 1)[1]
        projects.setdefault(project, {"id": project, "label": display_label(record)})
        add_node(nodes, record, "artifact", project)

    edge_records: list[tuple[str, dict[str, Any]]] = []
    for metadata_root, project in metadata_projects.items():
        for filename in ("entities.json", "provenance.json"):
            path = metadata_root / filename
            if not path.exists():
                continue
            document = load(path)
            for collection, kind in COLLECTION_KINDS.items():
                for record in document.get(collection, []):
                    add_node(nodes, record, kind, project)

        relationships_path = metadata_root / "relationships.json"
        if relationships_path.exists():
            for relationship in load(relationships_path).get("relationships", []):
                edge_records.append((project, relationship))

    label_counts = Counter(
        node["data"]["label"].casefold() for node in nodes.values()
    )
    for node in nodes.values():
        data = node["data"]
        if label_counts[data["label"].casefold()] > 1:
            data["label"] = f'{data["label"]} ({data["kind"]})'
        for project in data["projects"]:
            project_label = projects[project]["label"].casefold()
            original_label = display_label(json.loads(data["metadata"])).casefold()
            if (
                data["kind"] in {"paper", "artifact", "software"}
                and original_label == project_label
            ):
                data["root"] = 1

    edges: list[dict[str, Any]] = []
    for number, (project, relationship) in enumerate(edge_records, start=1):
        source = relationship["source"]
        target = relationship["target"]
        if source not in nodes or target not in nodes:
            raise ValueError(
                f"relationship endpoint is undefined: {source} -> {target}"
            )
        edges.append(
            {
                "data": {
                    "id": f"edge-{number:04d}",
                    "source": source,
                    "target": target,
                    "label": relationship["predicate"],
                    "kind": "relationship",
                    "projects": [project],
                    "metadata": json.dumps(
                        relationship, indent=2, ensure_ascii=False
                    ),
                }
            }
        )

    kinds = sorted({node["data"]["kind"] for node in nodes.values()})
    return [*nodes.values(), *edges], kinds, list(projects.values())


def render(
    elements: list[dict[str, Any]],
    kinds: list[str],
    projects: list[dict[str, str]],
) -> str:
    graph_json = json.dumps(elements, ensure_ascii=False).replace("</", "<\\/")
    kinds_json = json.dumps(kinds, ensure_ascii=False)
    projects_json = json.dumps(projects, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research metadata graph</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4f4f1; color: #111; }}
    header {{ height: 58px; display: flex; align-items: center; gap: 16px; padding: 0 18px; border-bottom: 2px solid #000; background: #fff; }}
    header h1 {{ margin: 0; font-size: 18px; }}
    header span {{ color: #555; font-size: 13px; }}
    main {{ height: calc(100vh - 58px); display: grid; grid-template-columns: 270px minmax(420px, 1fr) 330px; }}
    aside {{ background: #fff; padding: 16px; overflow: auto; }}
    #controls {{ border-right: 2px solid #000; }}
    #details {{ border-left: 2px solid #000; }}
    #cy {{ width: 100%; height: 100%; background: #fafaf8; }}
    .control-title {{ display: block; margin: 2px 0 8px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }}
    input[type="search"], button {{ width: 100%; min-height: 36px; margin: 0 0 12px; padding: 7px 9px; color: #111; background: #fff; border: 2px solid #000; border-radius: 5px; font: inherit; }}
    button {{ cursor: pointer; font-weight: 700; }}
    button:hover {{ background: #111; color: #fff; }}
    .button-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .stats {{ margin: 4px 0 16px; padding: 9px; border: 2px solid #000; border-radius: 5px; font-size: 12px; background: #f4f4f1; }}
    .toggle-list {{ display: grid; gap: 5px; margin: 0 0 16px; padding: 9px; border: 2px solid #000; border-radius: 5px; }}
    .toggle-row {{ display: grid; grid-template-columns: 18px 18px 1fr; align-items: center; gap: 7px; min-height: 24px; font-size: 12px; cursor: pointer; }}
    .toggle-row.project {{ grid-template-columns: 18px 1fr; font-weight: 700; }}
    .toggle-row input {{ width: 16px; height: 16px; margin: 0; accent-color: #000; }}
    .swatch {{ width: 18px; height: 18px; border: 2px solid #000; border-radius: 50%; }}
    #details h2 {{ margin: 0 0 4px; font-size: 16px; overflow-wrap: anywhere; }}
    #details .kind {{ margin: 0 0 14px; color: #555; font-size: 12px; text-transform: uppercase; }}
    #metadata {{ margin: 0; padding: 12px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; border: 2px solid #000; border-radius: 5px; background: #f4f4f1; font: 11px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .hint {{ color: #555; font-size: 13px; line-height: 1.5; }}
    @media (max-width: 1000px) {{
      main {{ grid-template-columns: 220px 1fr; }}
      #details {{ position: fixed; right: 0; bottom: 0; width: min(360px, 90vw); max-height: 45vh; border-top: 2px solid #000; box-shadow: -4px -4px 0 rgba(0,0,0,.12); }}
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js"></script>
</head>
<body>
  <header><h1>Research metadata graph</h1><span>Click a circle to expand · drag nodes · scroll to zoom</span></header>
  <main>
    <aside id="controls">
      <span class="control-title">Research projects</span>
      <div id="project-list" class="toggle-list" role="group" aria-label="Visible research projects"></div>
      <label class="control-title" for="search">Search</label>
      <input id="search" type="search" placeholder="ID, name, predicate…">
      <span class="control-title">Legend / node types</span>
      <div id="type-list" class="toggle-list" role="group" aria-label="Visible node types"></div>
      <div class="button-row"><button id="fit">Fit</button><button id="layout">Relayout</button></div>
      <div class="button-row"><button id="expand-all">Expand all</button><button id="collapse">Collapse</button></div>
      <button id="reset">Reset view</button>
      <div id="stats" class="stats"></div>
    </aside>
    <section id="cy" aria-label="Interactive research metadata graph"></section>
    <aside id="details">
      <h2 id="detail-title">Select a node or edge</h2>
      <p id="detail-kind" class="kind">Details</p>
      <p id="detail-hint" class="hint">Paper, artifact, and matching software identities are roots. Click a node to expand or collapse its immediate relationships and inspect its metadata.</p>
      <pre id="metadata">No selection</pre>
    </aside>
  </main>
  <script>
    const elements = {graph_json};
    const kinds = {kinds_json};
    const projects = {projects_json};
    const colours = {{
      paper: '#ffcf56', artifact: '#ff8f70', person: '#9dd9f3', software: '#b8e986',
      dataset: '#d8b4fe', experiment: '#f9a8d4', configuration: '#fef08a', result: '#93c5fd',
      venue: '#cbd5e1', organisation: '#fdba74', 'funding-project': '#a7f3d0'
    }};

    if (typeof cytoscape === 'undefined') {{
      document.getElementById('cy').innerHTML = '<p style="padding:20px">Cytoscape.js could not load. Connect to the internet and reload this file.</p>';
      throw new Error('Cytoscape.js did not load');
    }}

    const cy = cytoscape({{
      container: document.getElementById('cy'), elements, wheelSensitivity: 0.18,
      minZoom: 0.08, maxZoom: 3, layout: {{ name: 'grid' }},
      style: [
        {{ selector: 'node', style: {{
          'background-color': ele => colours[ele.data('kind')] || '#fff',
          'border-color': '#000', 'border-width': 2.5, 'width': 42, 'height': 42,
          'label': 'data(label)', 'font-size': 9, 'font-weight': 700, 'color': '#000',
          'text-wrap': 'wrap', 'text-max-width': 115, 'text-valign': 'bottom',
          'text-margin-y': 8, 'text-background-color': '#fff', 'text-background-opacity': 0.9,
          'text-background-padding': 2
        }} }},
        {{ selector: 'node[root = 1]', style: {{ 'width': 58, 'height': 58, 'border-width': 4, 'font-size': 11 }} }},
        {{ selector: 'edge', style: {{
          'width': 1.7, 'line-color': '#000', 'target-arrow-color': '#000',
          'target-arrow-shape': 'triangle', 'curve-style': 'bezier',
          'label': 'data(label)', 'font-size': 7, 'color': '#111',
          'text-background-color': '#fff', 'text-background-opacity': 0.92,
          'text-background-padding': 2, 'text-rotation': 'autorotate'
        }} }},
        {{ selector: ':selected', style: {{ 'border-width': 6, 'border-color': '#000', 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'z-index': 999 }} }},
        {{ selector: '.expanded', style: {{ 'border-style': 'double', 'border-width': 6 }} }},
        {{ selector: '.matched', style: {{ 'border-width': 7, 'background-color': '#fff' }} }},
        {{ selector: '.hidden', style: {{ 'display': 'none' }} }}
      ]
    }});

    const enabledKinds = new Set(kinds);
    const enabledProjects = new Set(projects.map(project => project.id));
    const expanded = new Set();
    const search = document.getElementById('search');
    const stats = document.getElementById('stats');
    const title = document.getElementById('detail-title');
    const detailKind = document.getElementById('detail-kind');
    const metadata = document.getElementById('metadata');
    const hint = document.getElementById('detail-hint');

    function intersects(values, selected) {{ return values.some(value => selected.has(value)); }}
    function eligibleNode(node) {{ return enabledKinds.has(node.data('kind')) && intersects(node.data('projects'), enabledProjects); }}
    function eligibleEdge(edge) {{ return intersects(edge.data('projects'), enabledProjects); }}

    function visibleGraph() {{
      const query = search.value.trim().toLowerCase();
      let visibleNodes = cy.collection();
      cy.nodes().forEach(node => {{ if (eligibleNode(node) && node.data('root') === 1) visibleNodes = visibleNodes.union(node); }});
      expanded.forEach(id => {{
        const node = cy.getElementById(id);
        if (!node.nonempty() || !eligibleNode(node)) return;
        visibleNodes = visibleNodes.union(node);
        node.connectedEdges().forEach(edge => {{
          if (!eligibleEdge(edge)) return;
          const neighbour = edge.source().id() === id ? edge.target() : edge.source();
          if (eligibleNode(neighbour)) visibleNodes = visibleNodes.union(neighbour);
        }});
      }});
      if (query) {{
        cy.nodes().forEach(node => {{
          const haystack = `${{node.data('id')}} ${{node.data('label')}} ${{node.data('metadata')}}`.toLowerCase();
          if (eligibleNode(node) && haystack.includes(query)) visibleNodes = visibleNodes.union(node);
        }});
      }}
      let visibleEdges = cy.edges().filter(edge => eligibleEdge(edge) && visibleNodes.contains(edge.source()) && visibleNodes.contains(edge.target()));
      return {{ nodes: visibleNodes, edges: visibleEdges, all: visibleNodes.union(visibleEdges) }};
    }}

    function runTreeLayout(animate = true, fit = true) {{
      const graph = visibleGraph();
      let roots = graph.nodes.filter(node => node.data('root') === 1);
      if (roots.empty() && graph.nodes.nonempty()) roots = graph.nodes.first();
      graph.all.layout({{
        name: 'breadthfirst', directed: true, roots, circle: false, grid: true,
        spacingFactor: 1.25, avoidOverlap: true, maximal: true,
        animate, animationDuration: 300, fit, padding: 45
      }}).run();
    }}

    function applyView(relayout = false) {{
      const graph = visibleGraph();
      cy.elements().addClass('hidden').removeClass('matched expanded');
      graph.all.removeClass('hidden');
      expanded.forEach(id => cy.getElementById(id).addClass('expanded'));
      const query = search.value.trim().toLowerCase();
      if (query) graph.nodes.forEach(node => {{
        if (`${{node.data('id')}} ${{node.data('label')}} ${{node.data('metadata')}}`.toLowerCase().includes(query)) node.addClass('matched');
      }});
      stats.textContent = `${{graph.nodes.length}} / ${{cy.nodes().length}} nodes · ${{graph.edges.length}} / ${{cy.edges().length}} edges`;
      if (relayout) runTreeLayout(true, true);
    }}

    function addToggle(container, value, text, colour, selectedSet, extraClass = '') {{
      const label = document.createElement('label'); label.className = `toggle-row ${{extraClass}}`;
      const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.checked = true; checkbox.value = value;
      checkbox.addEventListener('change', () => {{ checkbox.checked ? selectedSet.add(value) : selectedSet.delete(value); applyView(true); }});
      label.append(checkbox);
      if (colour) {{ const swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.background = colour; label.append(swatch); }}
      const caption = document.createElement('span'); caption.textContent = text; label.append(caption);
      container.append(label);
    }}

    const projectList = document.getElementById('project-list');
    projects.forEach(project => addToggle(projectList, project.id, project.label, null, enabledProjects, 'project'));
    const typeList = document.getElementById('type-list');
    kinds.forEach(kind => addToggle(typeList, kind, kind, colours[kind] || '#fff', enabledKinds));

    search.addEventListener('input', () => applyView(false));
    document.getElementById('fit').addEventListener('click', () => cy.fit(visibleGraph().all, 40));
    document.getElementById('layout').addEventListener('click', () => runTreeLayout(true, true));
    document.getElementById('expand-all').addEventListener('click', () => {{ cy.nodes().filter(eligibleNode).forEach(node => expanded.add(node.id())); applyView(true); }});
    document.getElementById('collapse').addEventListener('click', () => {{ expanded.clear(); applyView(true); }});
    document.getElementById('reset').addEventListener('click', () => {{
      search.value = ''; expanded.clear(); enabledKinds.clear(); kinds.forEach(kind => enabledKinds.add(kind));
      enabledProjects.clear(); projects.forEach(project => enabledProjects.add(project.id));
      document.querySelectorAll('#controls input[type="checkbox"]').forEach(box => box.checked = true);
      applyView(true);
    }});

    cy.on('tap', 'node', event => {{
      const node = event.target;
      expanded.has(node.id()) ? expanded.delete(node.id()) : expanded.add(node.id());
      title.textContent = node.data('label'); detailKind.textContent = `${{node.data('kind')}} · ${{node.data('id')}}`;
      metadata.textContent = node.data('metadata'); hint.hidden = true; applyView(true);
    }});
    cy.on('tap', 'edge', event => {{
      const edge = event.target;
      title.textContent = edge.data('label'); detailKind.textContent = `${{edge.data('source')}} → ${{edge.data('target')}}`;
      metadata.textContent = edge.data('metadata'); hint.hidden = true;
    }});
    cy.on('tap', event => {{ if (event.target === cy) cy.$(':selected').unselect(); }});
    cy.on('mouseover', 'node, edge', () => document.body.style.cursor = 'pointer');
    cy.on('mouseout', 'node, edge', () => document.body.style.cursor = 'default');

    applyView(false);
    runTreeLayout(false, true);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output HTML path (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    elements, kinds, projects = build_elements()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(elements, kinds, projects), encoding="utf-8")
    node_count = sum("source" not in element["data"] for element in elements)
    edge_count = len(elements) - node_count
    print(
        f"wrote {output} ({node_count} nodes, {edge_count} edges, "
        f"{len(projects)} projects)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
