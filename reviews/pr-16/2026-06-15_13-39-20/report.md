# Code Review Report

**Branch:** benthomasson/ftl-code-expert#16
**Models:** claude, gemini
**Gate:** [BLOCK] BLOCK

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:verify** [LOW]: claude: CONCERN, gemini: PASS

## claude [BLOCK]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** BLOCK
**Correctness:** BROKEN
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** MISSING

The line `network_path.write_text(result.stdout)` was deleted but the `click.echo(f"Updated {network_path}")` message was kept. This means `_reasons_export()` no longer writes `network.json` to disk, yet prints a lie saying it did. The verify command adds a call to `_reasons_export()` specifically to "ensure fresh metadata (fixes stale network.json)" — but the export no longer writes that file. `_load_network()` reads from `network.json` on disk, so verify will read stale data. This is a clear regression that undermines the stated purpose of the re-export.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Logic is mostly sound — seeds with source file, asks LLM for observations, runs them, returns combined context. Two issues: (1) `timeout` parameter is accepted but never used (dead parameter carried from the caller signature). (2) The function calls `invoke(observe_prompt, model)` without any timeout or error handling around the LLM call itself — if the model returns malformed JSON, `parse_observation_requests` returns `[]` which is handled gracefully, but a network error would propagate as an unhandled exception (caught only by `asyncio.gather(return_exceptions=True)` in the parent). This is acceptable but worth noting.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Mirrors the existing `_gather_confirmation_context` pattern correctly. Exceptions are caught via `asyncio.gather(return_exceptions=True)` and logged to stderr with `click.echo(..., err=True)` — an improvement over the original which silently swallowed errors. The `timeout` parameter is threaded through but ultimately unused in the callee (see above).

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `--no-observe` flag and branching logic are clean. The default behavior change (observation-based is now default, simple read is opt-in) is a significant UX change — each belief now costs an extra LLM call for observation planning, roughly doubling cost. The re-export call at line 3850 is good in intent but broken in practice due to the `_reasons_export` bug above. The `_load_network()` fallback (reading from `reasons export` stdout directly if `network.json` doesn't exist) partially masks the bug — if `network.json` was previously deleted, `_load_network` would call `reasons export` directly. But if `network.json` exists and is stale, the stale version is used.

### ftl_code_expert/prompts/verify.py:VERIFY_OBSERVE_PROMPT
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Well-structured prompt. Provides clear instructions, available tools table, output format, and practical guidelines (3-8 observations). The format placeholders (`belief_id`, `belief_text`, `seed_context`, `tree`) match the `.format()` call in `_verify_belief_with_observations`. The double-brace escaping for JSON template is correct.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean addition of `VERIFY_OBSERVE_PROMPT` to imports and `__all__`. Alphabetical ordering maintained.

### Self-Review
**Limitations:** Could not see the full `_gather_belief_context` function to compare behavior with the new `_verify_belief_with_observations`. Could not verify whether other callers of `_reasons_export` depend on `network.json` being written. Could not see the test directory structure to confirm whether tests truly don't exist or were just not found by the observation tool.

### Feature Requests
- Filter out test files from `.venv/` or other dependency directories — false-positive "related tests" from sympy wasted observation budget and added noise
- Show the project's actual test directory structure and any test files matching the modified module names
- Include a "callers of modified functions" observation to verify integration impact (e.g., all callers of `_reasons_export`)

## gemini [BLOCK]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** BLOCK
**Correctness:** BROKEN
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The line `network_path.write_text(result.stdout)` has been removed. However, the command prints `Updated network.json` on success. This creates a silent bug where `reasons export` runs and its output is captured, but never written to `network.json`, while falsely claiming the file was updated. This will cause stale belief network data to be loaded from the cache.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The implementation is clean and handles seeding/truncation correctly. However, the `timeout` parameter is defined in the function signature but is completely unused inside the body (not passed down to `invoke` or other async calls). Furthermore, there is no test coverage for this function.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The logic is sound and robust. It uses `return_exceptions=True` under `asyncio.gather` and handles individual failures gracefully, outputting errors using `click.echo(..., err=True)` and returning a safe fallback context. No local tests exist for this code.

### ftl_code_expert/cli.py:verify
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The CLI command integration is correct. Positional arguments map cleanly to click options and decorators. The command properly respects the new `--no-observe` flag and falls back to simple context gathering when enabled.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly imports and exports the new `VERIFY_OBSERVE_PROMPT` in `__all__`.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The prompt template `VERIFY_OBSERVE_PROMPT` is well-written and correctly escapes double curly braces for formatting. However, there are no tests verifying prompt assembly or response parsing.

### Self-Review
**Limitations:** The test runner mapped several virtualenv SymPy tests (e.g., `test_arit.py`, `test_expand.py`) as "related tests" because of a simple name matching collision on the word "verify" or "verify.py". There are actually no local unit or integration tests for the observation-based verification features implemented in this PR.
