#!/usr/bin/env python3
"""Render and validate function-scoped, parameter-annotated Mermaid from JSON.

No third-party dependencies. The JSON is a reviewed analysis record, NOT an
automatic AST-to-business-meaning inference engine.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

VALID_KINDS = {"action", "decision", "terminal", "start", "call", "error"}
VALID_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

class DiagramError(ValueError):
    pass


def load_ir(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_ir(data: dict) -> list[str]:
    errors = []
    ids = set()
    fn_ids = set()
    kinds = {}
    for field in ("title", "source", "functions", "edges"):
        if field not in data:
            errors.append(f"missing top-level key: {field}")
    for fn in data.get("functions", []):
        fid = fn.get("id", "")
        if not VALID_ID.fullmatch(fid) or fid in fn_ids:
            errors.append(f"invalid or duplicate function id: {fid!r}")
        fn_ids.add(fid)
        if not all(fn.get(k) for k in ("name", "purpose", "file", "nodes")):
            errors.append(f"function {fid}: name/purpose/file/nodes required")
        for n in fn.get("nodes", []):
            nid = n.get("id", "")
            if not VALID_ID.fullmatch(nid) or nid in ids:
                errors.append(f"invalid or duplicate node id: {nid!r}")
            ids.add(nid)
            kind = n.get("kind")
            kinds[nid] = kind
            if kind not in VALID_KINDS:
                errors.append(f"{nid}: invalid kind {kind!r}")
            for k in ("title", "impact", "source_lines"):
                if not n.get(k):
                    errors.append(f"{nid}: missing {k}")
            line = n.get("source_lines", [])
            if not isinstance(line, list) or not all(isinstance(x, int) and x > 0 for x in line):
                errors.append(f"{nid}: source_lines must be positive line numbers")
            params = n.get("params")
            if not isinstance(params, list):
                errors.append(f"{nid}: params must be list (empty list if none)")
            else:
                for p in params:
                    if not isinstance(p, dict) or not all(isinstance(p.get(k), str) and p[k].strip() for k in ("name", "controls")):
                        errors.append(f"{nid}: each parameter requires name and controls causal effect")
                    if isinstance(p, dict) and p.get("controls", "").lower() in {"affects output", "varies", "influences", "used", "unknown"}:
                        errors.append(f"{nid}: parameter effect too vague")
    degrees = defaultdict(list)
    for e in data.get("edges", []):
        a, b = e.get("from"), e.get("to")
        if a not in ids or b not in ids:
            errors.append(f"edge refers to unknown node: {a} -> {b}")
        if not e.get("label"):
            errors.append(f"edge {a} -> {b}: explicit label required")
        degrees[a].append(e.get("label", ""))
    for nid, k in kinds.items():
        if k == "decision" and len(degrees[nid]) < 2:
            errors.append(f"decision node {nid} must have at least two outgoing labeled edges")
    if not data.get("source", {}).get("revision"):
        errors.append("source.revision is required for reproducibility")
    return errors


def label_text(s: str) -> str:
    return html.escape(s, quote=True).replace("\n", " ").replace("|", "∣")


def render_mermaid(data: dict) -> str:
    errors = validate_ir(data)
    if errors:
        raise DiagramError("\n".join(errors))
    lines = ["flowchart TD", "  %% Auto-rendered from reviewed JSON IR; keep human verification of source semantics."]
    for fn in data["functions"]:
        desc = f"ƒ {fn['name']} — {fn['purpose']}"
        lines.append(f'  subgraph scope_{fn["id"]}["{label_text(desc)}"]')
        lines.append("    direction TB")
        for n in fn["nodes"]:
            pnames = ", ".join(p["name"] for p in n["params"]) or "—"
            description = f"{label_text(n['title'])}<br/>P: {label_text(pnames)}<br/>Δ: {label_text(n['impact'])}"
            if n["kind"] == "decision":
                rendered = f'{n["id"]}{{"{description}"}}'
            elif n["kind"] in {"start", "terminal", "error"}:
                rendered = f'{n["id"]}(["{description}"])'
            elif n["kind"] == "call":
                rendered = f'{n["id"]}[["{description}"]]'
            else:
                rendered = f'{n["id"]}["{description}"]'
            lines.append("    " + rendered)
        lines.append("  end")
    lines.append("")
    for edge in data["edges"]:
        tag = label_text(edge["label"])
        style = "-.->" if edge.get("kind") in {"fallback", "parameter"} else "-->"
        lines.append(f'  {edge["from"]} {style}|"{tag}"| {edge["to"]}')
    error_ids = [n["id"] for fn in data["functions"] for n in fn["nodes"] if n["kind"] == "error"]
    if error_ids:
        lines.append("  classDef error fill:#fff0f0,stroke:#c44,color:#7a1717")
        lines.append("  class " + ",".join(error_ids) + " error")
    lines.append("  %% Node labels display P (parameters read here) and Δ (the controlled output/variable effect).")
    return "\n".join(lines) + "\n"


def render_report(data: dict, mmd: str) -> str:
    src = data["source"]
    lines = [f"# {data['title']}", "", f"Source: `{src.get('repository', '')}` @ `{src['revision']}`. Analysis input: `{src.get('entry', '')}`.", "", "## Diagram", "", "```mermaid", mmd.rstrip(), "```", "", "## Node-by-node parameter influence and source evidence", "", "P = directly read parameter/config; Δ = effect on variable, branch, mask, or output. `—` means no direct parameter read. Parameters forwarded but not read are stated explicitly in the ledger.", ""]
    for fn in data["functions"]:
        lines.extend([f"### `{fn['name']}` — {fn['purpose']}", "", f"File: `{fn['file']}`", "", "| Node | Parameter and its controlled effect | Variable/output change | Source lines |", "|---|---|---|---|"])
        for n in fn["nodes"]:
            p = "<br>".join(f"`{k['name']}` → {k['controls']}" for k in n["params"]) or "—"
            sr = ", ".join(str(v) for v in n["source_lines"])
            lines.append(f"| `{n['id']}` {n['title']} | {p} | {n['impact']} | `{sr}` |")
        lines.append("")
    lines.extend(["## Scope and limitations", "", "- Diagrams are static source-tracing results, not proof that each runtime branch is executable on representative point clouds.", "- Source line numbers are evidence hints and must be reverified whenever the commit changes.", "- A function box denotes the owning implementation; call edges crossing boxes are not Python stack-frame lifetime diagrams.", "- Never infer a parameter's use from its name: distinguish forwarded, overwritten, omitted, and actually read parameters.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate function scope/parameter influence IR and generate Mermaid")
    parser.add_argument("ir", type=Path)
    parser.add_argument("--out", type=Path, help="Output .mmd; default: IR stem .mmd")
    parser.add_argument("--markdown", type=Path, help="Output evidence ledger Markdown")
    parser.add_argument("--check", action="store_true", help="Validate only")
    args = parser.parse_args()
    try:
        data = load_ir(args.ir)
        output = render_mermaid(data)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if args.check:
        print(f"PASS {args.ir}: {sum(len(f['nodes']) for f in data['functions'])} annotated nodes; {len(data['functions'])} function scopes; {len(data['edges'])} labeled edges")
        return 0
    out = args.out or args.ir.with_suffix(".mmd")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_report(data, output), encoding="utf-8")
    print(f"Generated {out} ({sum(len(f['nodes']) for f in data['functions'])} nodes, {len(data['functions'])} scopes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
