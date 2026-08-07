# code-to-flowchart

A [Claude Code](https://claude.com/claude-code) skill that traces a function's real control flow — branches, decisions, error paths — and turns it into a Mermaid flowchart. Built to explain a 500-line, cyclomatic-complexity-85 C# method to engineers who shouldn't have to read it line by line to understand what it does.

Unlike asking a model to "just draw a diagram of this code," the skill enforces a fixed process:
- trace every decision point and side effect, in order
- collapse straight-line logic into named steps instead of one node per line (~15-30 nodes for a 500-line method, not 500)
- keep error/exception paths visible instead of merging them into the happy path
- write a plain Markdown file with a fenced `mermaid` block — renders natively on GitHub, GitLab, and in most editors, no extra tooling needed

## Install

Copy `SKILL.md` into a `code-to-flowchart/` folder under your Claude Code personal skills directory:

```bash
mkdir -p ~/.claude/skills/code-to-flowchart
cp SKILL.md ~/.claude/skills/code-to-flowchart/SKILL.md
```

It's a model-invoked skill (no `disable-model-invocation` flag), so Claude Code will pick it up automatically when you ask to visualize code, map a control flow, or explain a branchy function — no slash command needed. You can also invoke it explicitly.

## Example

```
> convert the OrderProcessor.Process method into a flowchart
```

produces `docs/diagrams/Process-flowchart.md` with a Mermaid diagram tracing every `if`/`else`, DB/IO call, and catch block in that method, grouped into named steps.

## License

MIT — see [LICENSE](LICENSE).
