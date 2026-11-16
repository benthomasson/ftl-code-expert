# Code Review Report

**Branch:** benthomasson/ftl-code-expert#17
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:verify (verified_at stamping block)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

**1. Private API coupling.** `_with_network` is a private (underscore-prefixed) function in `reasons_lib.api`. This is the only usage from outside `reasons_lib` — every other call site is internal to the library. If `reasons_lib` refactors this function, this code silently breaks (caught by the `except`). Consider either promoting `_with_network` to a public API in `reasons_lib`, or adding a dedicated public function like `stamp_verified(db_path, node_ids, timestamp)`.

**2. Dual `verified_at` storage location.** The cli.py code sets `node.verified_at` (the dataclass field at `reasons_lib/__init__.py:45`), which is what `storage.py:138` persists. But `check_stale.py` sets `node.metadata["verified_at"]` (lines 119, 154, 350, 415, 463) — a different dict. Code that reads `metadata["verified_at"]` (e.g., staleness checks) won't see the value this code writes, and vice versa. Verify which location downstream consumers actually read; if both are read, one of the two write sites is wrong.

**3. `reasons_lib` is dev-only.** `ftl-reasons` is in `[dependency-groups] dev`, not in `[project] dependencies`. The `try/except` gracefully degrades, but users running a non-dev install get silent no-ops on every confirmed verification — no error, just no stamp. Consider either promoting it to an optional dependency with a clear user-facing message, or gating the import attempt on `_has_reasons()` to make the skip explicit.

**4. No tests.** The verify function has zero test coverage (observation confirms `test_count: 0`). The new stamping logic has multiple branches (confirmed non-empty, bid in net.nodes check, stamped count, exception path) that are all untested.

**5. Minor — hardcoded `"reasons.db"` path.** Consistent with the rest of the file, but the path is relative to CWD, not to the project directory. If the user runs the command from a subdirectory, this opens the wrong (or nonexistent) database. The existing retract block uses `_has_reasons()` as a guard; the stamp block doesn't.

### Self-Review
**Limitations:** - Could not verify `check_stale.py`'s full staleness-check logic to confirm whether it reads `node.verified_at` or `node.metadata["verified_at"]` downstream — the dual-location concern may or may not be a real bug depending on which is authoritative.
- Could not see the full `Storage.save()` method to confirm which `verified_at` field it persists.
- No test files exist for the verify function, so I could not check for test breakage.

### Feature Requests
- Include the full `Storage.save()` and `Storage.load()` methods as observations when the diff touches persistence logic, to verify round-trip correctness.
- When a diff imports from a library, auto-observe the imported function's signature and docstring to catch private API usage and parameter mismatches.

## gemini [CONCERN]

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. **Private/Internal API Usage:** The code imports `_with_network` from `reasons_lib.api`. In Python, leading underscores denote private APIs. Directly accessing internal functions makes the integration fragile to upstream refactoring in the `ftl-reasons` package. If a public CLI or stable API exists (e.g., `reasons set-metadata`), it would be much more robust.
2. **Missing Guard Check:** The logic runs unconditionally whenever `confirmed` is not empty. In other parts of `cli.py`, database access is guarded by checking if `_has_reasons() and Path("reasons.db").exists()`. Without this guard, if `reasons_lib` is installed in the environment but `reasons.db` doesn't exist, calling `_with_network("reasons.db", write=True)` may create an empty/unwanted `reasons.db` file in the directory.
3. **Redundant Imports:** `datetime` is already imported at the module level in `cli.py` (line 10), so re-importing it locally is redundant.
4. **Untested:** The codebase lacks any automated unit tests to verify database stamping, error handling, or command integration.

### Self-Review
**Limitations:** - Could not directly read `.venv/lib/python3.14/site-packages/reasons_lib/api.py` in the main session due to Gitignore constraints, though a subagent was delegated to verify its internal auto-persistence and API attributes.
- No functional spec or issue description was provided, restricting the review strictly to integration safety and correctness.
