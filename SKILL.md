---
name: code-to-flowchart
description: Trace actual code and generate function-scoped Mermaid workflows with parameter-to-variable causality, verifiable source lines, layered interactive diagrams, and measurable token usage. Use when asked to explain algorithms, visualize function business logic, or trace parameters through multiple functions.
---

# Code to Flowchart

Analyze **actual source**, not names or docstrings. Default to **Level 2: expand core helper algorithms**. Output a business overview and linked function-level diagrams rather than one huge diagram. Preserve original code-to-flowchart behavior: explicit branches, errors, return paths and semantic step names.

## Required accuracy

- Record exact repository, commit, entry function, and consulted ranges. Detect source changes before reusing prior analysis. Never guess a call edge or a default.
- Give each expanded function a labeled scope (`subgraph` for Mermaid, function view in interactive HTML).
- Every process/decision node: `P:` parameters actually read/forwarded or `—`; `Δ:` the exact controlled variable, branch, mask, threshold, or output; include source line evidence in the ledger.
- Distinguish argument forwarding, defaulting, overriding, omitted parameters, and fallback behavior. Separate call-site paths if the same helper is invoked differently.
- No implicit loss of important failures/early returns. When a core helper is collapsed in the overview, link to its expanded detail view.

## Minimal workflow

1. **Scope:** Pin the repo commit and trace entry + core callees. For Python, optionally index local calls with `scripts/source_slice.py`, but treat dynamic/imported calls as unresolved. Read only relevant file/ranges; load `references/parameter-provenance.md` for complex parameters.
2. **Model:** Build function-scoped JSON IR (schema by example in `examples/sample_flow.json`) with exact evidence. For long outputs, author **compact IR** using `scripts/compact_ir.py` format (details in `references/compact-ir-schema.md` and `references/token-optimization.md`); unpack before validation. Do not discard causality to save tokens.
3. **Verify:** `python3 scripts/flowchart_ir.py IR.json --check`. Verify claims against code, especially numeric inequalities, early return precedence, and call-site parameter omissions.
4. **Render locally:** `python3 scripts/incremental_pipeline.py IR.json --out-dir docs/diagrams --request "<task>" --usage-log docs/diagrams/usage.jsonl`. Optional `--viewer-spec VIEWS.json` renders a standalone HTML (Graphviz `dot` required). Re-render without involving an LLM on a valid, unchanged IR.
5. **Measure:** Use `scripts/token_usage.py record --stage ... --usage-file <provider-usage.json> --provider openai|anthropic` for **exact model tokens**, if available. Without a provider usage response, pass prompt/response files and mark **estimate**. Never call estimated values actual billed tokens. Write `token_usage.py report --log ...`.
6. **Deliver:** `.mmd`, `.md` parameter ledger and (if requested) `.html`; include which checks actually ran and known algorithm/dynamic-call limits. When source changed, regenerate/review the IR before regenerating diagrams.

**Security:** The tooling stores SHA-256/metadata in measurement logs, never source/prompt contents. Keep private-code-derived IR and HTML out of public skill repositories.

Full standards: `references/parameter-provenance.md` (causality), `references/token-optimization.md` (metering/cache), `references/compact-ir-schema.md` (IR transport), and `references/full-procedure-v2.md` (detailed tracing contract). Tools use Python standard library; offline HTML generation additionally needs Graphviz at build time. The Skill does not itself call an LLM or guarantee access to model usage API metrics.
