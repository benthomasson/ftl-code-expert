# Code Review Report

**Branch:** benthomasson/ftl-code-expert#23
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/prompts/verify.py — VERIFY_INFER_FILE_PROMPT
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template. Asks for a JSON array with exactly one path — matches what `_parse_inferred_files` parses. Properly exported via `__init__.py`. No issues.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Straightforward re-export of `VERIFY_INFER_FILE_PROMPT` — added to both the import and `__all__`. Correctly wired.

### ftl_code_expert/cli.py:_verify_belief_with_observations (inline inference block)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The inline inference fallback in `_verify_belief_with_observations` works but has two issues:

1. **`get_repo_structure` moved up, `max_depth` changed from 2 to 3.** The `tree` variable is now computed unconditionally (line 3150) before the inference block, and its `max_depth` changed from 2 to 3. This is a subtle behavioral change for all verify calls — the observe prompt now gets a deeper tree even when no inference is needed. This is likely intentional (the observe prompt also benefits from more context) but is a silent change bundled into a feature commit. Worth noting.

2. **Bare `except Exception: pass` (lines 3178-3179).** The outer try/except swallows all errors silently, including unexpected ones like `TypeError` from a broken `_parse_inferred_files` or `set_metadata` signature change. At minimum, a debug log would help diagnosability. The inner `except Exception: pass` around `set_metadata` (line 3176) is similarly opaque — if metadata stamping fails, the user sees the "Inferred source file" message but the metadata is silently not persisted. The verify still proceeds with the inferred file in memory, so the result is correct for this run, but the metadata won't be there next time.

3. **Deferred import of `read_file` inside hot path** (line 3170). Minor, but this import runs on every verify where inference triggers. It would be cleaner at module level or alongside the other observation imports.

### ftl_code_expert/cli.py:infer_sources (new CLI command)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and follows existing patterns in the codebase (similar to other batch commands using `invoke_concurrent_sync`). Path traversal protection is present. However:

1. **`_reasons_export()` called at start but `_load_network()` reads from a file (`network.json`).** If `_reasons_export` writes `network.json` and this is the expected flow, it works — but there's no error handling if `_reasons_export` fails silently and leaves stale/missing `network.json`. The `try/except` around `_load_network` catches this, but the error message won't hint that the export step was the actual failure.

2. **`set_metadata` imported unconditionally outside the loop (line 4241) even though `_has_reasons()` was already checked.** This is fine because the guard at line 4185 already exits if reasons.db is missing — but contrast this with the inline verify version which imports conditionally. The inconsistency is cosmetic but could confuse readers.

3. **`--all` flag filters on `truth_value == "IN"` and tries `_extract_source_file` as a secondary check** (lines 4206-4213). The `_extract_source_file` reads an entry file looking for a `# File:` header. If the entry file doesn't exist or has no such header, it returns None, and the belief becomes a candidate. This is correct — it catches beliefs that have a source file derivable from their entry but not yet stamped as metadata.

4. **No `--force` flag to re-infer for beliefs that already have `source_file`.** If an inference was wrong, there's no way to re-run it without manually clearing metadata first. Not a bug, but a usability gap.

5. **No test coverage.** The project has zero test files. This is the biggest concern — a batch command that writes metadata to a database with no tests at all.

### Self-Review
**Limitations:** Could not see `_auto_gather_verify_observations` to verify what it returns when `src_file` is `None` and whether the new inference block correctly covers all cases. Could not see `_load_network` or `_reasons_export` implementations to verify the export-then-load pattern. No test files exist in the project to verify against. Could not see `invoke_concurrent_sync` to confirm error return type (the code checks `isinstance(result, Exception)` which depends on the implementation).

### Feature Requests
- Include the implementation of functions called by new code (e.g., `_auto_gather_verify_observations`, `_load_network`, `_reasons_export`) as observations so reviewers can verify the contract between caller and callee
- Flag when a project has zero test files — this is a stronger signal than just "UNTESTED" on individual changes

## gemini [CONCERN]

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The integration of source-file inference logic inside `_verify_belief_with_observations` is clean and elegant. It consolidates the repository tree generation into a single call to `get_repo_structure` with `max_depth=3`, which is reused for both inference and observation prompt generation. It includes safe relative path verification (reversing path traversals and absolute paths) and actual existence checks via `os.path.isfile` before adding the inferred file to the observations context. However, this fallback flow remains completely untested.

### ftl_code_expert/cli.py:infer_sources
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The new `infer-sources` command is well-structured and fully integrated with click. It safely validates inferred paths against directory traversal and checks for local file existence before modifying metadata via `set_metadata`. The concurrent invocation is wrapped to handle individual failures gracefully without aborting the entire command. If updates succeed, it triggers `_reasons_export()` to ensure persistence. The main concern is the complete lack of automated test coverage for this new subcommand.

### Self-Review
**Limitations:** - Shell commands and test execution tools were restricted by environment policies, preventing empirical verification of the new CLI command's execution and behavior.

### Feature Requests
- Include mock tools or dry-run integrations in the observation results to facilitate verification of shell/CLI commands.
- Provide a summary of the reasons schema or metadata expectations when reviewing integrations with external state databases (like `reasons.db`).
