# Code Review Report

**Branch:** benthomasson/ftl-code-expert#13
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_gather_belief_context** [LOW]: claude: PASS, gemini: CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:_accept_proposals
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The write-side change is correct. After successfully adding a belief, it extracts the source file path and stores it as metadata via `reasons set-metadata`. The `set-metadata` return code is intentionally ignored — since the belief was already added, this is best-effort metadata enrichment, and `_gather_belief_context` falls back gracefully if the metadata is absent. The only concern is the call `_extract_source_file(source.strip())` with no `project_dir`, which defaults to resolving relative to CWD (`.`). This is fine for the CLI invocation context but worth noting — if `_accept_proposals` is ever called from a different working directory, the file lookup will break silently (returns `None`). No tests exist for `_accept_proposals` at all (0 test files per observations).

### ftl_code_expert/cli.py:_gather_belief_context
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The read-side change is clean. It checks `node.get("metadata", {}).get("source_file")` first, avoiding a disk read of the source entry file when metadata is already populated. Falls back to `_extract_source_file(source, project_dir)` when metadata is absent, preserving full backwards compatibility with beliefs created before this change. The `.get("metadata", {})` chain handles missing keys safely. Integration is complete — the write side in `_accept_proposals` populates the metadata, and this read side consumes it.

### Overall Assessment
**Verdict:** CONCERN

The change is logically sound and well-integrated — write side stores metadata at accept time, read side prefers it over disk-based extraction, with a clean fallback. The two concerns are: (1) **zero test coverage** for both `_accept_proposals` and `_extract_source_file` (no test files found in observations), and (2) the silent failure on `set-metadata` — while acceptable for resilience, a `logging.debug` or similar would help diagnose cases where metadata is consistently not being stored.

### Self-Review
**Limitations:** Could not verify whether `reasons set-metadata` is an established subcommand (the observation for `set_metadata_raises` returned "Function not found," meaning I couldn't confirm the CLI contract). Could not verify the shape of `node` dict returned by `reasons` to confirm that `node.get("metadata", {}).get("source_file")` matches the actual data structure. No test files were available to assess whether this change breaks any existing assertions.

### Feature Requests
- Include the CLI subcommand interface (e.g., `reasons set-metadata --help` output) when the diff shells out to external tools, so reviewers can verify argument order and existence
- Flag when test coverage is 0 for both the modified function AND all its callers — this is a stronger signal than just "no tests for this function"

## gemini [CONCERN]

### ftl_code_expert/cli.py:_accept_proposals
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function correctly extracts the source file path from the proposal's source entry using `_extract_source_file` when a belief is successfully added to `reasons.db`. It then issues a `reasons set-metadata` command via `subprocess.run` to store the path as `source_file` in the belief's metadata. The command is invoked safely without `shell=True` to prevent command injection. A CONCERN is raised solely because the codebase completely lacks automated tests or test configurations to verify this CLI integration path.

### ftl_code_expert/cli.py:_gather_belief_context
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The change successfully prioritizes reading `source_file` from the node's metadata, falling back to parsing the file with `_extract_source_file` only if not found. This elegantly avoids legacy issues where `_extract_source_file` failed when `project_dir` pointed to `.code-expert`. However, the dictionary retrieval `node.get("metadata", {}).get("source_file")` is questionable: if `"metadata"` exists in the exported JSON but is explicitly `null` (e.g. `{"metadata": null}`), `.get("metadata", {})` returns `None` instead of `{}`, which raises an `AttributeError` on the subsequent `.get("source_file")` call. Using `(node.get("metadata") or {}).get("source_file")` is a much more robust pythonic pattern.

### Self-Review
**Limitations:** - Could not execute the `reasons` CLI tool directly to verify the exact behavior of `reasons set-metadata` under all conditions because the shell command execution tool was not available in this environment.
- No test suite, test files, or mock structures were present in the repository to run integration checks.

### Feature Requests
- Provide CLI execution tools (e.g., shell command runner) to allow reviewers to dynamically verify external CLI tool integrations (such as `ftl-reasons` behavior and help schemas).
- Include sample JSON schema files or mock/fixture outputs for external databases (`reasons.db` / `network.json`) to verify key structures statically.
