# Code Review Report

**Branch:** file-issues-negative-confirm
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_extract_source_file** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:_confirm_beliefs** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:_get_negative_beliefs** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:_build_negative_issue_body
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean parallel to `_build_issue_body` for negative beliefs. Correctly references the belief ID in the retract command. Simpler body is appropriate since negative beliefs don't have gated dependents. Integrated via `file_issues` command.

### ftl_code_expert/cli.py:_extract_source_file
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function reads the first 5 lines of an entry file looking for `# File: `. Two concerns: (1) No path traversal guard — if `entry_path` (from `node.get("source")`) contains `../` segments, `Path(base) / entry_path` could escape the project directory. The data is internal but defense-in-depth would check `resolve()` stays within `base`. (2) If the header format ever changes (e.g. `## File:` or `# Source:`), this silently returns None and grep fallback kicks in — acceptable degradation.

### ftl_code_expert/cli.py:_gather_confirmation_context
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Three concerns: (1) `read_file` is called with `max_lines=300` but the function signature defaults to 200 — this is fine since it accepts the parameter, just noting the override. (2) The grep term extraction `terms = [t for t in bid.replace("-", " ").split() if len(t) > 3][:3]` derives search terms from belief IDs, which are slugified identifiers. This will produce useful terms for IDs like `sql-injection-user-input` but poor ones for IDs like `issue-1234-fix`. No fallback uses the belief *text* for grep, which would often be more informative. (3) The `grep` call doesn't pass a `glob` parameter, so it defaults to `"*.py"` — this silently excludes non-Python files (JS, TS, Go, etc.) that may be relevant in polyglot repos.

### ftl_code_expert/cli.py:_parse_confirmation
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Regex `r"\{[^{}]*\}"` correctly extracts a flat JSON object (no nesting needed for `{id: bool}` map). Returns empty dict on failure, and callers treat missing keys as `True` (default to filing), so parse failures fail open. Sound approach.

### ftl_code_expert/cli.py:_confirm_beliefs
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

(1) `asyncio.run()` is called inside a synchronous Click command. This works for CLI invocation but will raise `RuntimeError` if the code is ever called from within an existing event loop (e.g., Jupyter, or if the CLI is embedded in an async framework). The rest of the codebase likely has the same pattern so this is consistent. (2) The fail-open design (on LLM error, include all beliefs) is the right choice — avoids silently dropping legitimate issues. (3) Batch size of 10 is hardcoded; not configurable via CLI but reasonable default. (4) The prompt format is well-structured and unambiguous, with a clear expected output format.

### ftl_code_expert/cli.py:_get_negative_beliefs
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The regex `r"\s*\[-\]\s+([\w-]+):\s+(.+)"` parses `reasons list-negative` output. Two concerns: (1) This creates a tight coupling to the CLI output format of `reasons list-negative`. If that format changes, the parsing silently fails and falls back to keyword detection — acceptable degradation but could cause confusion if the `reasons` tool is installed but the regex no longer matches (user sees keyword-based results instead of LLM-classified ones with no warning). (2) The `-m model` flag is passed to `reasons list-negative` — this requires the reasons CLI to support that flag. If it doesn't, `returncode != 0` triggers the fallback, which is fine.

### ftl_code_expert/cli.py:file_issues (command)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The refactored command correctly unifies gated blockers and negative beliefs into a single candidate pipeline. Key concerns: (1) **Dry-run still runs LLM confirmation** — confirmation is gated on `not skip_confirm and remaining and check_model_available(model)` but NOT on `not dry_run`. This means `--dry-run` incurs LLM costs and latency. This may be intentional (to show accurate preview) but should be documented or reconsidered since dry-run typically implies no external calls. (2) **`_find_existing_issues` parameter names are misleading** — the parameters are named `blocker_ids` and `blocker_texts` in the function signature, but now they receive all candidate IDs (including negatives). The function still works correctly since it's just doing string matching, but the parameter names are now inaccurate. (3) The summary line `len(candidates) - len(remaining) - len(existing)` for "filtered" count is correct mathematically only when `existing` was already subtracted from `remaining`. Since `remaining = [c for c in candidates if c["id"] not in existing]`, the filtered count = `len(candidates) - len(remaining)` already includes existing, so `- len(existing)` double-counts. Wait — let me re-check: `candidates` = all, `remaining` = candidates minus existing minus LLM-rejected. So `len(candidates) - len(remaining)` = existing + LLM-rejected. Then `- len(existing)` = just LLM-rejected. That's what "filtered" means here. The math is correct.

### Self-Review
**Limitations:** Could not verify whether `reasons list-negative -m model` is an actual supported invocation of the reasons CLI. Could not see the full `_find_existing_issues` implementation to verify it handles the expanded input correctly. No test files were available to check for regressions. Could not verify the `CONFIRM_PROMPT` template's effectiveness empirically.

### Feature Requests
- Include the full body of modified functions (not just diff hunks) so reviewers can see surrounding logic like error handling paths and early returns
- Show the import block to verify all new imports are present
- Include test files alongside implementation changes, or flag when tests are absent for the modified module

## gemini [CONCERN]

### ftl_code_expert/cli.py:_build_negative_issue_body
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** MEETS
**Test Coverage:** UNTESTED
**Integration:** WIRED

Simple and correct template for formatting negative belief issues.

### ftl_code_expert/cli.py:_extract_source_file
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly extracts the source file path from entry headers using a standard project heuristic (first 5 lines).

### ftl_code_expert/cli.py:_gather_confirmation_context
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function is `async` but performs I/O operations (read_file, grep) sequentially within loops. This is a missed opportunity for parallelism which could significantly slow down the confirmation process for larger batches. Additionally, `grep` defaults to `*.py` in `observations.py`, which might miss context for beliefs associated with non-Python files.

### ftl_code_expert/cli.py:_confirm_beliefs
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Implements a sound batching and confirmation strategy. The error handling is conservative, including all issues in a batch if the LLM invocation fails, ensuring no potential issues are lost due to transient failures.

### ftl_code_expert/cli.py:file_issues
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** MEETS
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command logic is well-structured to handle both gated blockers and negative beliefs. The integration of the confirmation step and the new flags (`--skip-confirm`, `--no-negative`) is correct. It properly deduplicates against existing issues before filing.

### ftl_code_expert/cli.py:_get_negative_beliefs
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Good fallback strategy: prefers the specialized `reasons list-negative` command if available, falling back to a keyword-based search on IN beliefs.

### Self-Review
**Limitations:** No test files were included in the codebase, so I could not verify if existing tests would break or create new ones. I had to rely on static analysis of the provided diff and surrounding context. I also assumed the output format of the `reasons` CLI matches the regex used in `_get_negative_beliefs`.

### Feature Requests
- Include a sample output or contract for the `reasons` CLI to verify regex patterns in `cli.py`.
- Provide existing test files to ensure new CLI flags and async logic don't introduce regressions.
- Parallelize I/O operations in `_gather_confirmation_context` using `asyncio.gather`.
- Allow the `grep` glob in `_gather_confirmation_context` to be configurable or more inclusive (e.g., including `.md`, `.json`, `.yml`).
