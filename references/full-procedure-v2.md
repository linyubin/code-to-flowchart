---
name: code-to-flowchart
description: Convert real code and its transitive core helpers into a Mermaid control-flow chart with explicit per-function scope boxes, parameter-to-variable effects at every node, and source-line evidence. Use for understanding algorithms, function internals, config-dependent behavior, return paths, and parameter propagation.
---

# Code to Flowchart — Function Scopes & Parameter Effects

This skill extends [AjinkyaDeshmukh1990/code-to-flowchart](https://github.com/AjinkyaDeshmukh1990/code-to-flowchart) (MIT). Retain its priorities: **accurate control flow**, readable semantic step names, explicit error/return branches, Mermaid in version-controlled Markdown. Added capabilities: **function ownership** and **parameter causality**.

## Layout standard: progressive disclosure (v2)

For functions with multiple helpers, produce **three presentation layers** without losing
source evidence:

- **L1 — business overview**: one compact, three-stage flow (inputs & checks →
  branching/algorithm → result), with business action labels and explicit early exits.
- **L2 — function-focused diagrams**: one separate, *bounded* diagram per expanded
  core function. A call to another function is a **clickable proxy**, not a giant
  cross-function wire. Its return must connect to the **verified call site**;
  if return semantics are uncertain, annotate them rather than inventing a path.
- **L3 — parameter lineage**: expose a curated cross-function sequence of
  `parameter -> intermediate -> condition/variable -> output` with per-step
  code evidence. Include omission, override, defaults and source location.

**Default layout behavior:** do not fit a long (> roughly 2× viewport aspect) diagram
into an unreadable postage stamp. Show its start at readable width, enable vertical
wheel navigation and pan, and provide an explicit *full graph* button. Keep `P:`
and `Δ:` visible inside nodes and the full wording in a separate detail panel.

When delivering an HTML artifact, prefer a **self-contained file** embedding SVG,
styles, node data, and viewer script. No CDN dependencies. Include static SVG/PNG
or a ZIP fallback for preview-limited environments. Ensure keyboard activation
for clickable nodes and meaningful titles/labels.

The generic viewer builder consumes a human-reviewed multi-view specification:

```bash
python3 scripts/interactive_explorer.py examples/sample_explorer_spec.json \
  --out examples/sample_explorer.html
```

`--out` HTML works offline; **Graphviz dot is needed during generation**, not by the
viewer. The builder validates references/structure but does **not** understand
source code automatically. Build the multi-view JSON from verified control-flow
IR and manually reviewed call/return bridges. The public example is safe to share;
private source-backed demos must remain outside a public fork.

## Mandatory outputs

1. A Mermaid diagram with **each expanded function enclosed in a `subgraph` labeled with exact function name + brief responsibility**. No unnamed function boxes. Every action and decision belongs to precisely one function boundary.
2. **Every node** must display `P:` (the inputs/config parameters read at that step, or `—`) and `Δ:` (the precise variable, mask, threshold, decision, or output modified/selected there). Examples: `P: min_score` / `Δ: valid = records with score >= min_score`, `P: max_items` / `Δ: valid = valid[:max_items]`. Include no vague `affects output` effects.
3. A node-level **parameter provenance table** listing each parameter's origin, values/defaults *when known*, intermediate variables, condition or threshold controlled, and target DataFrame/output, linked to `path:line` at a pinned commit.
4. A top-level chart plus one or more algorithm-detail charts when multiple core helper functions would make the top-level graph illegible. **Do not silently collapse a core helper to a function-name-only box**. When collapsed for readability, label it `see detail diagram` and provide the detail diagram.
5. A Markdown file with a fenced Mermaid diagram, associated parameter ledger, source repository and full pinned commit SHA. Keep the working JSON IR (see below), `.mmd`, and `.md`. If user wants a rendered image, optionally render SVG/PNG; no image is evidence of correctness.

## Analysis procedure

### 1. Find and pin the exact implementation

Find the user-facing entry point and source commit, inspect actual source rather than its docstring alone. Follow direct and indirect calls which **change filtering, business decisions, data shape, output or failure handling**. Stop at library/IO boundaries, or summarize dependency logic as an external operation. Do not infer functionality from the helper name.

Read configuration normalization/defaults, model-specific drivers when they affect math, and caller bindings (positional/keyword/defaults). For every function, record **name, responsibility, code location, inputs, outputs, failure/return behavior, and caller/callee**.

### 2. Trace parameter effects, not just references

For every meaningful node, capture `parameter/source -> expression/intermediate variable -> conditional/mask/value controlled -> observable output`. Distinguish:

- Argument `expected_value` versus config key `processing.offset`; distinguish read defaults (`dict.get(..., 2.0)`) from runtime normalized config values.
- **Read**: actually consulted in this node; **forwarded**: passed to callee; **overridden**: replaced by another parameter/mode; **omitted**: caller doesn't forward it so callee default applies; **unused**: present in signature but not used on this path.
- Actual comparisons (`<` vs `<=`, non-empty fallback) and earliest returns must be shown exactly, as written.
- Dynamic values: show formula and units instead of making up numeric output.

Detailed conventions and a cautionary review checklist: [`references/parameter-provenance.md`](references/parameter-provenance.md).

### 3. Choose expansion depth deliberately

Default to **Level 2 (business algorithm)**; avoid either one box per source line or one box per called function.

- **L1 — API/main business path**: input validation, prefilters, method selection, output/early returns.
- **L2 — core helper internals (default)**: include conditions, thresholds, transformed intermediate variables, fallback branches, and integration of outputs. Every core helper must have its own clearly named function box, either here or on a companion chart.
- **L3 — expression/implementation**: math formulas, exact filter predicates, data structure details and rare exception paths on request.

If a helper is both shared and invoked with different argument bindings, either draw separate **call-site instances** with the same source function name plus invocation context or give it a separate detail graph and annotate callers' distinct bindings. Never make both call sites look as though they return to the same caller unconditionally.

### 4. Build verified diagram intermediate representation

Use `examples/sample_flow.json` as a public schema-by-example. Real-code examples may remain private and should not be published without approval. JSON fields:

- Root: `title`, `source:{repository,revision,entry}`, `functions`, `edges`.
- Function: `id`, `name`, `purpose`, `file`, `nodes`.
- Node: `id`, `kind` (`start/action/call/decision/terminal/error`), `title` (what it accomplishes), `params:[{name,controls}]` (`[]` if no direct parameter), `impact` (single concise variable/result effect), `source_lines` (actual 1-based line numbers).
- Edge: `from`, `to`, `label` (always explicit), optional `kind:"fallback"` for a dashed fallback edge.

`params[].controls` must describe a concrete causal link. The `impact` summarizes the net data or control effect. Group expanded nodes by **owning function** in distinct IR function objects. Cross-function arrows indicate calls/results, not individual stack frames. Preserve call-site semantics when visualizing shared callees.

### 5. Generate, test, and review

With Python 3 (no third-party dependencies):

```bash
python3 scripts/flowchart_ir.py examples/sample_flow.json \
  --out docs/diagrams/sample_flow.mmd \
  --markdown docs/diagrams/sample_flow.md
python3 -m unittest discover -s tests -v
```

The generator emits Mermaid `subgraph` function boundaries, `P:` and `Δ:` annotations on **every node**, labeled branches, error styling, and a source-line parameter ledger. It rejects missing ownership/impact, unknown edges, unnamed decision branches, and vague parameter effects. **It is a consistency validator and renderer, not an automatic code parser.** The agent remains responsible for verified source tracing.

If Mermaid CLI is available, use it to render actual `.mmd`; otherwise report `static IR validation only` and never claim a browser/render test. Check readability, scope boundaries, decision semantics, arrows crossing boxes, and sources against code. Do not claim behavior tests passed if no point-cloud data was executed.

## Completion gates

- [ ] Every expanded function clearly bounded; no step assigned to two functions.
- [ ] Every node has `P:` and `Δ:`; every control parameter's influence is causal, not a list of argument names.
- [ ] All important early returns, error paths, and conditions are accurate; include caller omission/default and override rules.
- [ ] Function calls/returns and parameter propagation do not imply an execution path that the code cannot take.
- [ ] Source commit and `path:lines` attached to a parameter ledger and checked against actual code.
- [ ] Top-level and detail diagram together expose the *mechanism* of each core helper, not only its name.
- [ ] State exactly which checks were run (IR validation, Python tests, Mermaid render, algorithm runtime tests).
