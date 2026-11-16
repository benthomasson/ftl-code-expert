# Code Review Report

**Branch:** benthomasson/ftl-code-expert#16
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The removed line `network_path.write_text(result.stdout)` is a behavioral change. The comment claims `reasons export` writes `network.json` directly, but the sibling command `export-markdown` outputs to stdout and gets written via `beliefs_path.write_text(result.stdout)`. This asymmetry between the two export commands is not self-evident — if the assumption about `reasons export` writing the file directly is wrong, `network.json` will stop being updated. The `click.echo(f"Updated {network_path}")` still runs on success, which would be misleading if the file wasn't actually written. Should verify the actual behavior of `reasons export`.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function logic is sound overall, but has a fragile pattern: comparing `seed_context != "(no initial source file)"` against a magic string to decide inclusion in `context_parts`. If the sentinel string ever changes in one place but not the other, it silently drops or includes wrong context. A boolean flag (`has_seed = True/False`) would be more robust. The lazy import of `read_file` inside the function body is fine but atypical for this codebase. No exception handling around the `invoke()` call for the observation prompt — if the LLM call fails, the exception propagates up to `_gather_verify_contexts` which catches it via `return_exceptions=True`, so the system won't crash, but the error message (`"Error gathering context for {bid}: {result}"`) will show a raw exception rather than a user-friendly message.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Structurally mirrors `_gather_confirmation_context` with the addition of `model` and `timeout` parameters and slightly better error reporting (printing to stderr). The pattern is consistent with existing code. Errors are caught via `return_exceptions=True` on `asyncio.gather` and reported gracefully.

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Two notable changes: (1) Re-exporting via `_reasons_export()` before loading the network ensures fresh metadata — good defensive move but adds latency to every verify invocation. (2) The default behavior flips from simple file-read context to observation-based context (the new path requires an additional LLM call per belief for the observation prompt). This is a significant cost/latency increase for users who don't pass `--no-observe`. The flag naming `--no-observe` with `is_flag=True, default=False` means observations are ON by default — this is a breaking change in cost characteristics that should be noted in documentation or changelog. The integration between the flag and the two code paths is clean.

### ftl_code_expert/prompts/verify.py:VERIFY_OBSERVE_PROMPT
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Well-structured prompt. Clearly instructs the LLM to request observations without verifying the belief itself. The tool table and output format are consistent with the observation system used elsewhere. Guidelines asking for 3-8 targeted observations are reasonable. Format uses proper `{{` escaping for f-string compatibility.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean addition of `VERIFY_OBSERVE_PROMPT` to imports and `__all__`. Alphabetical ordering maintained.

### Self-Review
**Limitations:** The "related test" observations were all false positives from sympy's vendored tests (matching on the word "verify" generically) — there appear to be no actual project tests for the verify command or the new observation functions, so I cannot assess whether existing tests break. I could not verify the actual behavior of `reasons export` (whether it writes to stdout or directly to file), which is critical to assessing the `_reasons_export()` change. I also couldn't see the full `_extract_source_file` or `_gather_belief_context` functions to compare patterns.

### Feature Requests
- Filter out test files from `.venv/` or other vendored directories when finding related tests — all 5 "related test" observations were false positives from sympy
- Include the actual project test files (e.g. `tests/test_cli.py`) if they exist, to verify coverage claims
- Show the implementation of functions called by new code (e.g. `_extract_source_file`, `parse_observation_requests`, `run_observations`) to verify correct usage of their APIs

## gemini [PASS]

### ftl_code_expert/cli.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. **`_reasons_export` Fix**: Corrects a bug where `network.json` was overwritten by stdout (a mere status message). Removing `network_path.write_text(result.stdout)` allows the `reasons` tool to write directly to `network.json` as designed.
2. **Fresh Metadata Auto-Sync**: Calling `_reasons_export()` at the start of `verify()` ensures that `network.json` is always fresh before being loaded into `nodes`.
3. **LLM-Driven Observation Loop**: `_verify_belief_with_observations` and `_gather_verify_contexts` correctly implement the observation pattern. They dynamically compile initial context (`src_file` content truncated safely to 4000 characters), query the model via `VERIFY_OBSERVE_PROMPT` for additional observation steps, run them concurrently, and assemble the resulting dataset.
4. **Robust Error Handling**: Using `asyncio.gather(*tasks, return_exceptions=True)` in context-gathering pipelines prevents failures of individual observation queries from aborting or crashing batch verification.
5. **CLI Integration**: Seamless addition of the `--no-observe` flag lets users optionally bypass the multi-step observation loop and fall back to simple file/grep reads.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Properly exposes `VERIFY_OBSERVE_PROMPT` in the package's public interface (`__all__`), facilitating clean imports in `cli.py`.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The new `VERIFY_OBSERVE_PROMPT` is well-structured and clearly defines the expected JSON response schema. It correctly uses doubled-braces (`{{` and `}}`) for JSON format literals, preventing any format syntax errors when interpolating single-braced parameters `{belief_id}`, `{belief_text}`, `{seed_context}`, and `{tree}` at runtime.

### Self-Review
**Limitations:** No unit tests or integration tests exist in the workspace root or codebase itself (the scanned `.venv` test files are standard dependency test suites and unrelated). Behavior was verified through static analysis of functions and import safety.
