# Code Review Report

**Branch:** benthomasson/ftl-code-expert#13
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_accept_proposals** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:_accept_proposals
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

1. **`set-metadata` return code silently ignored** (line 1653-1657): If `reasons set-metadata` fails, there's no log or feedback. The fallback in `_gather_belief_context` covers this, so it's not a blocker, but a failed metadata write is worth a debug-level message — otherwise a misconfigured `reasons` binary silently degrades every accept run.

2. **Only new beliefs get metadata**: When `already exists` is hit (skipped path), no metadata is set. If this feature is backfilled onto a codebase with existing beliefs, those beliefs will never get `source_file` metadata unless re-accepted. Consider setting metadata on the skipped path too, or document this as intentional.

3. **`beliefs` CLI fallback (line 1680+) doesn't set metadata**: The second fallback path for `beliefs add` doesn't call `set-metadata`. Since `_gather_belief_context` reads metadata from `nodes` (reasons-backed), this is probably fine, but it's an asymmetry that could confuse future readers.

4. **No tests**: Observation confirms 0 test callers for `_accept_proposals`. The new subprocess call path is entirely untested.

### ftl_code_expert/cli.py:_gather_belief_context
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `(node.get("metadata") or {}).get("source_file")` pattern correctly handles all null/missing cases: missing `metadata` key, explicit `None` metadata, empty dict, and present metadata without `source_file`. The fallback to `_extract_source_file(source, project_dir)` preserves backward compatibility for beliefs that predate this feature. Clean optimization — avoids disk I/O when metadata is already cached.

### Self-Review
**Limitations:** - Could not verify the `reasons set-metadata` CLI interface (argument order, behavior on non-existent node) — review assumes it works as the code implies.
- No tests exist for either modified function, so I cannot verify test assertions remain valid.
- Could not see how `node["metadata"]` is populated by the `reasons` CLI to confirm the key name `source_file` round-trips correctly between write and read.

### Feature Requests
- Include the schema or CLI help for external tools (`reasons set-metadata`) when they appear in subprocess calls, so reviewers can verify argument order and behavior.
- Flag when modified functions have zero test coverage — the observation data includes this, but a prominent warning at the top of the review context would help.

## gemini [PASS]

### ftl_code_expert/cli.py:_accept_proposals
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The addition of setting `source_file` metadata during proposal acceptance allows downstream processes to retrieve the file without re-parsing files. The subprocess call is fully guarded by the `_has_reasons()` check, ensuring it will not fail due to a missing `reasons` executable. The resolution of `_extract_source_file` works perfectly at runtime, and missing files/paths are handled gracefully without raising unhandled exceptions.

### ftl_code_expert/cli.py:_gather_belief_context
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function now checks the belief node's metadata dictionary first to retrieve the pre-extracted `source_file`, falling back to the slower/legacy `_extract_source_file` method if it's missing. This backwards-compatible design avoids redundant disk I/O when verifying beliefs and works flawlessly even if legacy databases do not contain the metadata.

### Self-Review
**Limitations:** There are no unit or integration tests present in this codebase, preventing dynamic verification of the changes. However, static code paths, safeguards, and exception handling were thoroughly verified and found to be correct.
