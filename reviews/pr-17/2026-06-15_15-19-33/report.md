# Code Review Report

**Branch:** benthomasson/ftl-code-expert#17
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:verify** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

**Private API usage.** The stamping logic imports `_with_network` from `reasons_lib.api` — the underscore prefix marks it as internal. This couples the verify command to an implementation detail that could change without notice. The stale-retraction code 10 lines below shells out to `reasons retract` via subprocess, which is the more stable pattern. If `reasons_lib` exposes (or could expose) a public `stamp` or `update_node` API, that would be preferable; if not, at minimum the import path should be treated as fragile and documented.

**Direct attribute assignment.** `net.nodes[bid].verified_at = now` assumes the Node object supports arbitrary attribute setting. If Node is later tightened (e.g., `__slots__`, frozen dataclass), this silently fails inside the broad `except Exception`. The broad catch is reasonable for a non-critical side-effect, but it also masks bugs during development — consider logging the exception type at debug level.

**Approach inconsistency.** Retraction uses `subprocess.run(["reasons", "retract", ...])` while stamping uses the Python API directly. Pick one approach — if the Python API is preferred for performance, the retraction could use it too; if the CLI is preferred for stability, stamping should shell out to something like `reasons stamp`.

**No tests.** The stamping path has no test coverage in this diff. A test that verifies `verified_at` is set after a CONFIRMED verdict (and not set after STALE/INCONCLUSIVE) would catch regressions if the `_with_network` API changes.

### Self-Review
**Limitations:** Could not inspect `reasons_lib.api._with_network` to verify the Node object supports `verified_at` attribute assignment. Could not see test files to confirm there is truly no coverage. Could not verify whether `_has_reasons()` reliably gates the `reasons_lib` import in all code paths (e.g., if `_has_reasons()` returns True but `reasons_lib` is not installed).

### Feature Requests
- Include the source of imported private APIs (`_with_network`) so reviewers can verify the contract
- Show test files that cover the modified function, or explicitly note "no test files found"
- Flag when a dependency is imported at runtime but declared as dev-only

## gemini [PASS]

### ftl_code_expert/cli.py:verify
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- **Correctness/Safety Guards**: The addition of the guard check `if confirmed and _has_reasons() and Path("reasons.db").exists():` is highly robust. It prevents unnecessary LLM/CLI operations and avoids creating an empty or unwanted `reasons.db` file in the current directory if it does not already exist.
- **Robust Exception Handling**: Wrapping the db-stamping import and context-manager usage in a generic `try...except Exception as e:` block ensures that if `reasons_lib` is not available, fails to import, or if the database schema is locked/incompatible, the application does not crash and instead outputs a clean, user-friendly error message before continuing.
- **Minor Concern (Private API Coupling)**: The code imports and uses `_with_network` from `reasons_lib.api`. The leading underscore strongly suggests it is an internal/private function within the `reasons` codebase, making this integration highly fragile to upstream changes in `ftl-reasons`. However, given the wrapper safety, it degrades gracefully and represents an acceptable tradeoff if no stable public API is available.
- **Metadata vs Field Location**: Modifying the `.verified_at` attribute on the node class object matches how data is persisted by the dataclass field, but it is worth noting that some stale-check functions in the `reasons` package might use a nested dictionary structure (e.g., `metadata["verified_at"]`). Double-checking that consumers read from the dataclass attribute is recommended.
- **Hardcoded DB path**: Assumes `"reasons.db"` is in the CWD, which matches the existing retract logic conventions in `cli.py`.
- **Test Coverage**: The logic is untested due to the lack of unit tests for the `verify` command in the `ftl_code_expert` codebase.

### Self-Review
**Limitations:** - Could not check if `check_stale.py` (or other stale-check logic in the external `reasons` package) reads `node.verified_at` or `node.metadata["verified_at"]` downstream to confirm complete consistency of the stamp's target location.
- Verified that there are no test files in `ftl_code_expert` to update or verify coverage on.

### Feature Requests
- Include public API signatures or documentation of external dependencies (`ftl-reasons` in this case) to verify if a public alternative to private functions (`_with_network`) exists.
- Automatically check and report whether the specified python package name (`reasons_lib`) aligns with the imported path when relative tool paths are used.
