# code-to-flowchart v3 — Function Scopes & Token Telemetry

This extension keeps the upstream MIT license and source-to-Mermaid method. It adds:

- **Explicit function ownership:** each expanded helper is a Mermaid `subgraph` and a separately navigable HTML view.
- **Causal annotations:** every node records `P:` influencing parameters and `Δ:` exact affected masks, variables, decisions or return values, with source-line evidence.
- **Progressive disclosure:** business overview → focused function internals → parameter lineage. Core helper algorithms must not collapse into opaque function-name boxes.
- **Usage metering:** `scripts/token_usage.py` can record exact OpenAI/Anthropic response usage when provided, or label text-based estimates as estimates.
- **Token reduction:** shared-parameter compact IR and source-slice indexing for direct Python calls. Cached renders do not require another model request when the reviewed IR remains valid.
- **Offline UI:** `scripts/interactive_explorer.py` builds single-file HTML via local Graphviz; the generated file has no CDN dependency.

## Setup and smoke test

Python 3.10+ is required. Install Graphviz `dot` for the HTML viewer.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/flowchart_ir.py examples/sample_flow.json --check
python3 scripts/flowchart_ir.py examples/sample_flow.json --out /tmp/sample.mmd --markdown /tmp/sample.md
python3 scripts/interactive_explorer.py examples/sample_explorer_spec.json --out /tmp/sample.html
bash scripts/install_skill.sh ~/.codex/skills/code-to-flowchart
```

Use `~/.claude/skills/code-to-flowchart` instead for Claude Code; use `cursor/code-to-flowchart.mdc` for Cursor.

## Token measurement

```bash
python3 scripts/token_usage.py record --log usage.jsonl --run-id R1 --stage write_ir --provider openai --usage-file model-response-usage.json
python3 scripts/token_usage.py report --log usage.jsonl --out usage-report.json
```

The usage file must originate from the model API/agent runtime. This repository cannot intercept hidden model calls. Without actual usage fields, a fixed character heuristic is available but is **not exact billing**.

## Provenance and privacy

- Anchor analysis to a commit SHA and actual file/line evidence.
- The Mermaid renderer checks **IR structure**, not the code's runtime behavior.
- AST source slicing is conservative: dynamic dispatch/imported calls require further inspection.
- Keep source-derived examples from private repositories outside this public fork.
- Original author and MIT terms remain in the upstream `LICENSE`.

See `SKILL.md`, `references/full-procedure-v2.md`, `references/parameter-provenance.md` and `references/token-optimization.md`.
