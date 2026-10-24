# Function-scoped source evidence and parameter causality

## Use a five-column mental model

| Parameter origin | Value read | Intermediate/operation | Controlled variable/branch | Observable effect |
|---|---|---|---|---|
| `min_score` function arg | caller supplied | `item.score >= min_score` | `valid` filtered list | rows below threshold are dropped |
| `config.max_items` | config value | `max_items > 0` | `result[:max_items]` | limit number of returned rows |
| `force_mode` option | override flag | `if force_mode` | `mode = "fast"` | requested slower branch is skipped |

Do not mislabel database/config metadata as function arguments; name the parameter origin. Distinguish caller-supplied value, effective normalized config and inline `get(..., fallback)` defaults. Be precise that a fallback in one layer can differ from the final runtime value.

## Node contract

Each node includes:

- One short business-action title (preferred to raw Python function name).
- `P:` named influencing input/config variables; `—` if no direct input parameter is read.
- `Δ:` **short formula or concrete controlled variable**, preferably without vague verbs.
- Metadata `source_lines`, all originating from actual source at pinned commit.

If the node's direct inputs are derived intermediate values, list those too. If multiple parameters are coupled, explain combination in `params[].controls` and show the resulting intermediate in `Δ:`.

If too many parameter names exceed node width, split decision and calculation nodes; do **not** silently drop parameter influence. Use the Markdown ledger to elaborate formulas and data shape.

## Call-site binding traps

- `def helper(..., tuning=None)`: callers explicitly forwarding `tuning=tuning` versus omitting it cause different behavior. Annotate these call sites.
- A mode-override check before dispatch must connect only to reachable branches.
- A capped subset used **only when non-empty** is not an unconditional cap. Show the fallback edge.
- A function invocation does not guarantee useful data: distinguish return-empty from return-original fallback, and cases where an exception propagates.
- A repeated shared helper should not have diagram arrows falsely connecting the result of one call to another independent caller.

## Evidence requirements

For each node capture: `function`, `path`, 1-based source line(s), parameter origins, exact comparison/operator, and output variable/side effect. For each caller/callee capture which args are forwarded/omitted/defaulted; cross-check positional arguments and config normalization. Explain how uncertainty is handled rather than inventing a value.

Before delivery, compare source listing to diagrams and execute a targeted test where feasible. `scripts/flowchart_ir.py` checks structure, not algorithm semantics.
