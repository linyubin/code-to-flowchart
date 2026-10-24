# Token telemetry & optimization contract

## Measurement definitions (do not mix)

- **exact**: `usage` returned by a model provider or an agent runner for a real request. Captures input/output/cache/reasoning subtotals when available. `reasoning_tokens` is within `output_tokens`, not additional. In Anthropic usage payloads, `cache_read_input_tokens` and `cache_creation_input_tokens` are added to `input_tokens` for a normalized total.
- **estimate**: approximate tokens from UTF-8 text files using fixed code-point heuristic (`CJK * 1.25 + other_chars / 3.1`). Not a tokenizer. This is for relative comparisons, not billing/cost claims. No token precision guarantee across model families.
- **local**: deterministic Python/Graphviz render or validation, no direct model invocation, therefore zero model tokens for that stage.
- **cache_hit**: unchanged deterministic stage skipped. Do not infer that the entire user conversation used zero tokens.

## Standard stage names

`load_skill`, `read_source`, `reason_logic`, `write_ir`, `render`, `validate`.

Do not estimate hidden reasoning consumption from text lengths. Only record `reason_logic` tokens when a runner provides its actual usage. Metadata hashes must not contain proprietary code or prompt text.

## API usage recording

Save the provider response usage object to a local file (do not store secrets):

```
python3 scripts/token_usage.py record --log reports/usage.jsonl --stage write_ir \
  --provider openai --usage-file my-api-usage.json --run-id trial-01
python3 scripts/token_usage.py report --log reports/usage.jsonl --out reports/usage-summary.json
```

Text estimate fallback:

```
python3 scripts/token_usage.py record --log reports/usage.jsonl --stage write_ir \
  --prompt-file prompt.txt --response-file output.json --run-id trial-01
```

A stage with no LLM requests should use `--local`. Record repeated prompts *again* when they were really submitted to the model. Do not assume context-cache hits without provider evidence.

## Optimizations without sacrificing correctness

1. Load lean `SKILL.md` by default; only load relevant reference modules.
2. Slice source to entry and reachable core callees, retaining exact line numbers. `source_slice.py` follows direct, same-file Python calls only; report unresolved imported/dynamic dispatch. Do not use shallow-only excerpts while claiming full Level-2 coverage.
3. Author compact IR for long model responses. Convert to canonical JSON before running existing validators and renderers. Repeated parameter objects are interned; semantic fields are retained. Never compare pretty JSON with compact and attribute all savings to semantic optimization; also compare with minified JSON.
4. Re-render valid, unchanged IR using `incremental_pipeline.py`; invalidation must include input source hashes, pinned commit and renderer implementation. If source changes but IR has not been updated, fail closed and require reanalysis.
5. Preserve final visual quality. Rendering a 250 KB HTML offline costs zero model *output* tokens if generated locally, although reviewing the output via a vision-capable model may consume tokens separately.

## Known limits

The Skill is an agent instruction file, **not** a source-analysis model. AST slicing does not guarantee complete call graphs. The graph IR is still authored/reviewed by an agent. Current telemetry CLI cannot auto-intercept an agent's API requests. Integrate `token_usage.py` at the model-call boundary for actual provider counters. Baseline tests using saved IR exercise rendering and compare saved representations, not a fresh inference-run token bill.
