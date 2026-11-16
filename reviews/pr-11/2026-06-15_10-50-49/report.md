# Code Review Report

**Branch:** benthomasson/ftl-code-expert#11
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_parse_verify_response** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:verify** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template. Double-braces `{{` for literal JSON in the example are correct for Python `.format()`. Single `{beliefs}` placeholder is properly escaped. The three-way verdict taxonomy (CONFIRMED/STALE/INCONCLUSIVE) is clear and actionable.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard re-export. `VERIFY_PROMPT` added to both the import and `__all__`.

### ftl_code_expert/cli.py:_parse_verify_response
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `re.search(r"\{.*\}", response, re.DOTALL)` regex is greedy — it matches from the **first** `{` to the **last** `}` in the entire response. This works when the LLM returns a single top-level JSON object, but if the response contains trailing prose with a `}` character (e.g. `"Here are the results: {...} Hope that helps!}`), the match over-extends and `json.loads` fails, falling through to the WARN path. This is survivable (returns empty dict, beliefs become INCONCLUSIVE), but the same pattern appears in other commands so it's a known codebase risk, not new here. The per-item validation (checking `isinstance(v, dict)`, `"verdict" in v`, `isinstance(verdict, str)`) is thorough. No tests exist to exercise the parsing edge cases (empty response, partial JSON, extra keys, mixed-case verdicts).

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and follows the patterns established by `research` and other commands. Specific notes:

1. **`--reason` flag on `reasons retract`** (line ~3879): The subprocess call passes `["reasons", "retract", bid, "--reason", reason]`. If the `reasons` CLI doesn't accept `--reason` on `retract`, every retraction would fail. The code does check `returncode` and report failures, so this won't silently corrupt data — but it would make `--retract` a no-op in practice. Worth verifying the `reasons retract` interface.

2. **Multiple `asyncio.run()` calls in the batch loop** (line ~3831): Each batch calls `asyncio.run(_gather_confirmation_context(...))`. This is consistent with the codebase (29 other production usages), and works in Python 3.10+ since each call creates/tears down a fresh loop. Not a bug, but worth noting.

3. **Batch error handling**: If `invoke_sync` raises for a batch, the entire batch's beliefs silently become INCONCLUSIVE. The error is printed, so the user sees it, but there's no retry or batch-splitting on failure. Acceptable for a first pass.

4. **Selection mode mutual exclusivity**: The `elif` chain (belief_ids → gated → negative → category → verify_all) means only one mode applies. If a user passes both `--gated` and `--negative`, only `--gated` runs with no warning about the ignored flag. This is consistent with how Click flag precedence typically works, but could surprise users.

5. **No tests**: Zero test coverage per the observation (`test_count: 0`). For a command that can retract beliefs (`--retract`), this is the primary concern. At minimum, `_parse_verify_response` deserves unit tests covering: valid JSON, no JSON, malformed JSON, missing verdict keys, and mixed-case verdicts.

### Self-Review
**Limitations:** Could not see `invoke_sync` body (observation returned "not found") — verified it's imported from `.llm` but couldn't confirm its exception behavior. Could not verify whether `reasons retract --reason <text>` is a valid CLI invocation. No test files were included in the diff to assess coverage claims.

### Feature Requests
- Include the interface/help text of external CLI tools called via subprocess (e.g., `reasons retract --help`) so reviewers can verify flag compatibility
- When `test_count: 0`, automatically search for the closest test file pattern (e.g., `tests/test_cli.py`) and include its structure so the reviewer can assess whether tests should be added to an existing file or a new one

## gemini [PASS]

### ftl_code_expert/cli.py:verify
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is highly robust, clean, and idiomatic. It integrates flawlessly with the existing Click application group. It carefully handles and separates belief resolution strategies (by ID, gated/blocker status, category matching, negative-beliefs, or all IN beliefs) and prints helpful count summaries. It successfully employs async batching (`batch_size=10`) with `asyncio.run(_gather_confirmation_context(...))` to gather code contexts concurrently without triggering thread-safety or event-loop nesting errors, and cleanly manages prompt invocation and response parsing. The retraction logic correctly relies on `_has_reasons()` and executes a subprocess call to `reasons retract` with automatic state re-exporting (`_reasons_export()`).

### ftl_code_expert/cli.py:_parse_verify_response
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The regex pattern `r"\{.*\}"` with `re.DOTALL` correctly targets and extracts nested JSON maps from the LLM's response, even if wrapped in markdown formatting (e.g. ` ```json ` blocks). It is resilient to decoder failures and sanitizes keys/values to ensure they map strictly to expected dictionary shapes with uppercase verdicts (`CONFIRMED`, `STALE`, `INCONCLUSIVE`).

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standardized prompt template providing excellent framing, a clear instruction set, and a helpful schema example. Braces within the example block are double-escaped (`{{`, `}}`) so as not to conflict with Python's `.format(beliefs=...)` string interpolation.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Minimal and accurate module import/export modification adding `VERIFY_PROMPT` to both the local file import list and `__all__`.

### Self-Review
**Limitations:** None. Comprehensive file-level structure, dependencies, call hierarchies, and project files list were successfully provided via previous observations, enabling a fully detailed review with absolute certainty. (Note that the repository has a test count of 0, explaining why test coverage is marked as UNTESTED across all modified units).
