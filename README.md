# code-to-flowchart

An AI coding agent skill that traces a function's control flow (branches, decisions, error paths) and turns it into a Mermaid flowchart. Language-agnostic: works the same on a 500-line, high-complexity method in C#, Python, Go, Java, Rust, JS, or anything else with branches and error handling. Built to explain that kind of method to a team without making everyone read it line by line.

Unlike asking a model to "just draw a diagram of this code," the skill enforces a fixed process:
- trace every decision point and side effect, in order
- collapse straight-line logic into named steps instead of one node per line (~15-30 nodes for a 500-line function, not 500)
- keep error/failure paths visible instead of merging them into the happy path
- write a plain Markdown file with a fenced `mermaid` block. Renders natively on GitHub, GitLab, and most editors, no extra tooling needed

## Install

`SKILL.md` follows the [Agent Skills standard](https://github.com/anthropics/skills), so the same file works unmodified across every tool that supports it:

**Claude Code, Codex, Vibe, Amp, GitHub Copilot CLI**

```bash
mkdir -p ~/.claude/skills/code-to-flowchart   # or ~/.codex/skills/... , ~/.vibe/skills/...
cp SKILL.md ~/.claude/skills/code-to-flowchart/SKILL.md
```

It's a model-invoked skill (no `disable-model-invocation` flag), so the agent picks it up when you ask to visualize code, map a control flow, or explain a branchy function. No slash command needed. You can also invoke it explicitly.

**Cursor**

Cursor doesn't read `SKILL.md`. It uses its own project-scoped rules format. Use [`cursor/code-to-flowchart.mdc`](cursor/code-to-flowchart.mdc) instead:

```bash
mkdir -p .cursor/rules
cp cursor/code-to-flowchart.mdc .cursor/rules/code-to-flowchart.mdc
```

Same steps and completion criterion, translated to Cursor's rule frontmatter.

## Example

```
> convert the OrderProcessor.Process method into a flowchart
```

produces `docs/diagrams/Process-flowchart.md` with a Mermaid diagram tracing every `if`/`else`, DB/IO call, and catch block in that method, grouped into named steps.

### Before / after

[`examples/before/OrderImportWorker.cs`](examples/before/OrderImportWorker.cs) is a representative "god method": a polling timer handler with a device-connectivity check, a presence check, and a duplicated old-format/new-format branch. Same shape you'll find in most legacy polling services, regardless of language.

[`examples/after/OrderImportWorker-flowchart.md`](examples/after/OrderImportWorker-flowchart.md) is what the skill produces from it: a ~30-node Mermaid flowchart that makes the branch duplication and every error/no-action path visible at a glance, instead of something you have to trace through 200+ lines to understand.

## License

MIT. See [LICENSE](LICENSE).
