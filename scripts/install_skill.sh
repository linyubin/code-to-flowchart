#!/usr/bin/env bash
# Install this directory as a conventional Agent Skill without exposing private fixtures.
set -euo pipefail
TARGET="${1:-$HOME/.codex/skills/code-to-flowchart}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
  echo "ERROR: target directory exists and is nonempty: $TARGET. Back up or choose a different target." >&2
  exit 1
fi
mkdir -p "$TARGET"/{scripts,references,examples,templates}
cp "$HERE/SKILL.md" "$HERE/LICENSE" "$TARGET/"
cp "$HERE/scripts/"{flowchart_ir.py,graphviz_preview.py,interactive_explorer.py,token_usage.py,compact_ir.py,source_slice.py,incremental_pipeline.py} "$TARGET/scripts/"
cp "$HERE/references/"{parameter-provenance.md,token-optimization.md,compact-ir-schema.md,full-procedure-v2.md} "$TARGET/references/"
cp "$HERE/examples/"{sample_code.py,sample_flow.json,sample_explorer_spec.json} "$TARGET/examples/"
cp "$HERE/templates/explorer.html" "$TARGET/templates/"
# No private LiDAR artifacts are installed.
echo "Installed code-to-flowchart at $TARGET"
