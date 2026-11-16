# Code Review Report

**Branch:** benthomasson/ftl-code-expert#11
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template. Properly uses double-brace escaping for the JSON example inside the f-string format placeholder. The prompt clearly instructs the LLM to return JSON with the expected schema. Well-structured.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard import/re-export wiring. `VERIFY_PROMPT` is added to both the import and `__all__` list, consistent with how `REVIEW_PROMPT`, `RESEARCH_INFER_FILES_PROMPT`, etc. are handled.

### ftl_code_expert/cli.py:_parse_verify_response
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The regex `re.search(r"\{.*\}", response, re.DOTALL)` is greedy and matches from the **first** `{` to the **last** `}` in the entire response. If the LLM wraps the JSON in markdown fences with other commentary containing braces, this will still work *by accident* (greedy match captures everything between outermost braces). However, if the response contains a stray `}` after the JSON block (e.g., in trailing commentary), the match extends past the JSON and `json.loads` will fail, falling through to the empty-dict return. This is a known fragile pattern but is consistent with how LLM JSON extraction works elsewhere in this codebase. The silent empty-dict return on parse failure means all beliefs in that batch become INCONCLUSIVE with no indication that parsing failed — the user sees "INCONCLUSIVE (no LLM response)" which is misleading since the LLM did respond, the parse just failed. A log message on parse failure would help debugging.

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Several issues of varying severity:

1. **`ctx` shadowed by Click's `@click.pass_context`**: The parameter is named `ctx`, which shadows the outer `ctx` from `@click.pass_context`. This is fine for Click commands (standard pattern), but note that on line `_gather_confirmation_context(batch, nodes, abs_repo, project_dir)`, the variable `project_dir` comes from `_get_project_dir(ctx)` — this works correctly since `ctx` here is the Click context.

2. **`--retract` calls `reasons retract` with `--reason` flag**: The subprocess call on the retract path uses `["reasons", "retract", bid, "--reason", reason]`. I confirmed this flag exists in other parts of the codebase (lines 2897, 2917 use the same pattern in string form). Consistent usage.

3. **`asyncio.run()` called potentially inside an existing event loop**: If `verify` is ever called from an async context, `asyncio.run()` will raise. This is the same pattern used in `research` (line 3661), so it's consistent with the codebase but worth noting.

4. **`--gated` finds blockers of OUT beliefs, but verifies blocker IN beliefs**: This is semantically correct — the goal is to check whether the blocker beliefs (which are keeping downstream beliefs OUT) are still valid. If they're STALE, retracting them unblocks the downstream chain. The intent is clear and the logic matches.

5. **Missing `project_dir` for non-batch paths**: `project_dir = _get_project_dir(ctx)` is called unconditionally, which is correct.

6. **No test coverage at all**: The `_parse_verify_response` function has zero test usages per the observations. For a function that parses LLM output (inherently variable), unit tests on expected/edge-case inputs would be valuable.

### Overall Assessment
**Verdict:** CONCERN

The implementation is well-structured, follows existing patterns in the codebase (matches `research` command structure closely), and the integration is complete (prompt, import wiring, CLI registration). The two concerns are: (1) no tests for `_parse_verify_response`, which handles inherently unpredictable LLM output and silently returns empty dict on failure, and (2) the "INCONCLUSIVE (no LLM response)" message is misleading when the LLM responded but the JSON couldn't be parsed. Neither is a blocker, but adding a parse-failure log line and unit tests for the parser would meaningfully improve reliability.

### Self-Review
**Limitations:** Could not verify whether `reasons retract --reason` is an actual CLI flag (the `reasons --help` command was blocked). Relied on other usage in the same codebase as evidence it works. Could not see the full `invoke_sync` implementation to verify error behavior. No test files exist to check for coverage.

### Feature Requests
- Include the `reasons retract --help` output or CLI schema when the diff calls external CLI tools, so reviewers can verify flag correctness
- Auto-detect untested parser/formatter functions and flag them with higher severity, since these handle external/LLM input

## gemini [CONCERN]

### ftl_code_expert/cli.py:_parse_verify_response
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The parsing logic is correct and uses a robust `re.search(..., re.DOTALL)` pattern to extract JSON blocks. However, the outer `try-except` block surrounds the entire dictionary iteration. If the LLM returns an unexpected non-string type for a single belief's verdict, calling `.upper()` will raise an `AttributeError`, causing the entire parsed results dictionary to be discarded and returning `{}`. This marks the entire batch as `INCONCLUSIVE` due to a single malformed item. A safer, more granular type validation of individual items within the loop is recommended.

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The verification command is well-implemented and fully integrated with the `reasons` CLI. It properly supports diverse selection options (`--category`, `--gated`, `--negative`, `--all`), gathers asynchronous code context in batches, handles LLM invocation with fallbacks, and automates retraction of stale beliefs. The verdict is set to CONCERN solely because the repository lacks any automated tests or test runner configurations, leaving the command entirely untested.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The prompt template contains clear, unambiguous instructions, a structured JSON format contract, and a helpful multi-verdict example. It correctly utilizes double curly braces (`{{` and `}}`) to escape the JSON payload structure from Python's `.format()` interpreter.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

`VERIFY_PROMPT` is correctly imported and registered under the package-level `__all__` exports, making it seamlessly available to `cli.py`.

### Self-Review
**Limitations:** A complete codebase search was performed, confirming that there is no active test directory or testing configurations (such as pytest or unittest) in this repository. Consequently, no existing tests could be executed or verified for coverage.
