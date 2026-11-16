# Code Review Report

**Branch:** benthomasson/ftl-code-expert#16
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_reasons_export** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:_auto_gather_verify_observations** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The line `network_path.write_text(result.stdout)` was removed with a comment claiming `reasons export` writes `network.json` directly. However, the CLAUDE.md documents `reasons export -o beliefs.json` (with a `-o` flag for output), and the command here is invoked without `-o`. The previous behavior captured stdout and wrote it to the file — the same pattern used for `export-markdown` one block above. If `reasons export` without `-o` writes to stdout (a common CLI convention), this change silently breaks network.json updates. The comment should be verified against the actual `reasons` CLI behavior. The `click.echo(f"Updated {network_path}")` message would also be misleading if the file isn't actually written.

### ftl_code_expert/cli.py:_auto_gather_verify_observations
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The symbol extraction heuristic (lines ~3087-3093) splits the belief ID on hyphens and filters for terms >3 chars that start uppercase or contain underscores. This is fragile — many belief IDs will contain only lowercase words (e.g., `login-audit-always-success-info`), yielding zero symbols and falling through to a grep on the first term (`login`), which is likely too broad. Conversely, IDs like `http-handler-returns-json` would match nothing since none start uppercase or have underscores. The fallback grep with a single short term could return noise. Not a bug, but the heuristic quality directly affects context quality, which affects verification accuracy. Consider also checking for camelCase patterns or common code identifiers.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The observe-then-verify pipeline is well-structured: auto-gather seed context, ask LLM for targeted observations, execute them, combine. Content truncation at 4000 chars for the seed context is reasonable. The `source_key` handling correctly guards against `src_file` being None. One note: `get_repo_structure` is called but its import isn't visible in the diff — the observation system couldn't find it in cli.py either, suggesting it's imported from `git_utils`. Since it's used in existing code, this is likely fine. The function makes one LLM call per belief just for observation planning, which doubles the LLM cost of verify — acceptable given the `--no-observe` escape hatch.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Straightforward parallel wrapper consistent with the existing `_gather_confirmation_context` pattern. Error handling (printing to stderr, returning placeholder text) matches the established convention. No issues.

### ftl_code_expert/cli.py:verify (command)
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `--no-observe` flag and conditional context gathering are cleanly integrated. The new `_reasons_export()` call before loading the network (line 3907) ensures fresh metadata — a good fix. However, this adds two subprocess calls (`reasons export-markdown` + `reasons export`) to every non-dry-run verify invocation, even when the user is verifying a single belief. For large belief databases this may be slow. Consider caching or making the re-export conditional on database mtime. The default behavior changed from simple context to observation-based context, which is a significant behavioral change — the old behavior is now behind `--no-observe`. This is the right default but should be noted in any release notes.

### ftl_code_expert/prompts/verify.py:VERIFY_OBSERVE_PROMPT
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Well-structured prompt with clear instructions, a table of available tools, explicit output format, and sensible guidelines (3-8 observations, targeted not exhaustive). The `{{` double-brace escaping for JSON examples in the f-string template is correct. Properly exported through `prompts/__init__.py`.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean addition of `VERIFY_OBSERVE_PROMPT` to both the import and `__all__` list. Alphabetical ordering maintained.

### Overall test coverage
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

None of the new functions (`_auto_gather_verify_observations`, `_verify_belief_with_observations`, `_gather_verify_contexts`) have tests. The "related tests" in observations are all from sympy in `.venv/` and are unrelated — they merely contain the word `verify`. The symbol extraction heuristic, context assembly, and error handling paths would particularly benefit from unit tests. At minimum, `_auto_gather_verify_observations` should have tests covering: no source file, no symbols found, symbols found, and exception handling.

### Self-Review
**Limitations:** Could not verify `get_repo_structure` import — the function is called in new code but wasn't found in cli.py by the observation system; it's likely imported from git_utils but I cannot confirm. Could not verify the `reasons export` CLI behavior to confirm whether removing `network_path.write_text(result.stdout)` is correct or a regression. No actual test files for this project were available to assess existing test patterns.

### Feature Requests
- Include the full import block of modified files, not just the diff context around changed imports — this would catch missing imports
- When observing "related tests", filter out `.venv/` paths which are third-party dependencies, not project tests
- Include the actual project test directory listing so reviewers can assess whether tests exist elsewhere
- For CLI tools invoked via subprocess (like `reasons`), include a `--help` capture or docstring so behavioral assumptions can be verified

## gemini [PASS]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Prevents a critical data-corruption bug. Previously, calling `network_path.write_text(result.stdout)` overrode the `network.json` file (which `reasons export` already writes directly) with a simple CLI status message. Removing this line preserves the actual exported JSON file correctly.

### ftl_code_expert/cli.py:_auto_gather_verify_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function is robust and defensive. It safely falls back to extracting the source file path via `_extract_source_file` if metadata is missing, replaces and splits token terms cleanly, and uses parallel `asyncio.gather` with `return_exceptions=True` to prevent a single lookup failure from crashing the entire process.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Executes the multi-step context collection flow seamlessly. It formats `VERIFY_OBSERVE_PROMPT` correctly, handles empty initial context cleanly, and runs any requested observations in parallel. Crucially, it serializes any non-standard observations safely with `json.dumps(..., default=str)` to prevent serialization type errors.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Collects observation contexts for multiple beliefs in a single parallel batch. Any task-level exception is caught individually with `is_instance(result, Exception)` and gracefully printed via `click.echo(..., err=True)` rather than aborting execution for other beliefs in the batch.

### ftl_code_expert/cli.py:verify
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The CLI changes perfectly integrate the new observation loop. The addition of `_reasons_export()` before loading the network prevents stale `network.json` metadata during verification. The `--no-observe` flag correctly falls back to the simpler context gatherer, ensuring flexibility and token optimization.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean and standard packaging; `VERIFY_OBSERVE_PROMPT` is correctly imported and listed in `__all__`.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The newly introduced `VERIFY_OBSERVE_PROMPT` is highly descriptive and provides excellent guidelines to the model on how and when to request observations. The output format instructions use doubled braces (`{{` and `}}`) correctly, which are required for standard Python string formatting interpolation.

### Self-Review
**Limitations:** There are no unit or integration tests for `cli.py` or `prompts` present in the repository, making exact test coverage assessment impossible. All logic was reviewed purely via static analysis, code paths, and exception handling patterns.
