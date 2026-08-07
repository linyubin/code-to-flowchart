---
name: code-to-flowchart
description: Convert a function, method, or service's control flow — in any programming language — into a Mermaid flowchart diagram. Use when the user wants to visualize code logic, map a control flow, turn a method into a diagram, or understand a complex/branchy function visually.
---

# Code to Flowchart

Turns a function's real branching logic into a Mermaid `flowchart TD` that a reader can follow without reading the source. Language-agnostic — the steps below talk about decisions, side effects, and error-handling boundaries as concepts, not any one language's syntax.

## Steps

1. **Identify the target function(s).** If the project has codebase-memory indexed, use `trace_path`/`get_code_snippet` to pull the exact source. Otherwise `Read`/`Grep` the file directly. Confirm with the user which function/entry point is in scope if it isn't obvious from context.

2. **Trace the control flow top to bottom.** Walk the function and record, in order:
   - every decision point (`if`/`else`, `switch`/`match`, loop condition, early return)
   - every distinct action or side effect (DB call, network/IO call, external API/hardware call, state mutation)
   - every error-handling boundary (`try`/`catch`, `except`, an `err != nil`/`Result` check, `panic`/`recover`, etc.) and what happens on failure
   Skip pure logging statements and no-op lines — they add nodes without adding understanding.

3. **Group into named steps.** Don't emit one node per source line. Collapse a straight-line run of statements that serves one purpose (e.g. "parse input", "look up record by key") into a single labeled node named for *what* it accomplishes, not *how*. This is the step that keeps the diagram legible for any reader, not just someone who already knows the code — a 500-line function should produce ~15-30 nodes, not 500.

4. **Render as Mermaid.** Use `flowchart TD`:
   - process steps: `A[Do the thing]`
   - decisions: `B{Condition?}` with labeled edges — `B -->|Yes| C`, `B -->|No| D`
   - terminal/exit states: distinct shape, e.g. `Z([Done])`
   - error/failure paths: route through a visually distinct branch (e.g. prefix label `Error:` or a dedicated `classDef error` style) rather than interleaving them invisibly with the happy path
   For a very large or high-complexity function, produce a high-level diagram of named steps first; only add a second, more detailed diagram for a specific branch if the user asks for it.

5. **Write the output to a file**, not an Artifact, as a `.md` with a fenced ```mermaid block. Default path: `docs/diagrams/<function-or-service-name>-flowchart.md` in the target project (create the folder if missing) — unless the user names a different location. Add one sentence above the fence naming the source file/function the diagram was traced from, so it doesn't go stale silently.

## Completion criterion

Every decision point and named step identified in step 2 appears as a node; every branch out of a decision node has a labeled edge; every error/catch path is visible, not merged into the happy path. Sanity-check the Mermaid syntax (balanced `[]`/`{}`/`()`, every edge references a declared node) before writing the file.
