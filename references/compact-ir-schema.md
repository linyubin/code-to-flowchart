# Compact IR transport schema (v1)

Use ONLY after collecting actual code evidence. The compact format is an
alternative **model transport representation**, not a substitute for semantics.
Run `python3 scripts/compact_ir.py unpack model-output.json --out reviewed.json`
then use `flowchart_ir.py reviewed.json --check`.

```
{
  "format": "flowchart-compact-v1",
  "title": "...",
  "source": {"repository":"owner/repo", "revision":"full-pinned-revision", "entry":"source/function"},
  "parameters": [{"name":"min_score","controls":"min_score is compared with score"}],
  "f": [
    ["F1","function_name","responsibility","source.py", [
      ["N1","action","Filter valid records",[0],"valid = points meeting min_score",[13,14]],
      ["N2","terminal","Return results",[],"return valid",[16]]
    ]]
  ],
  "e": [["N1","N2","continue"]]
}
```

- `parameters` is a shared dictionary of `{name,controls}` pairs.
- Each `f` entry is `[id, name, purpose, file, nodes]`; an optional sixth item is an object of extra function fields.
- Each node tuple is `[id, kind, title, parameter_indices, impact, source_line_numbers]`; optional seventh item carries extra node fields.
- Each edge is `[from, to, label]`; optional fourth item carries extra edge fields (`kind: fallback`, etc.).
- Optional root `extra` object carries additional top-level metadata.
- Function scope ownership and all causal controls are preserved. Avoid one-node-per-code-line outputs; no invented names or line evidence.

Unpack and validate every model-produced compact object before rendering.
The tuple schema saves repeated keys and interning saves repeated parameter
objects; do not use abbreviations in titles/causal descriptions that impair clarity.
