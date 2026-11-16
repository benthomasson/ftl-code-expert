# Code Review Report

**Branch:** benthomasson/ftl-code-expert#26
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_ensure_labels** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:_ensure_labels
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Logic is sound for both GitHub and GitLab paths. GitHub uses `--json name -q ".[].name"` which correctly produces one label per line. GitLab JSON parsing is defensive with proper type checks and exception handling. If label listing fails (returncode != 0), `existing` falls back to an empty set, causing all labels to be attempted for creation — if they already exist, the create command fails and the error is logged, which is acceptable best-effort behavior. Two minor observations: (1) `required_labels` always includes both `reasons-gate` and `reasons-negative` even when `--no-negative` is passed, so an unused label type may be created — harmless but slightly wasteful. (2) If `_ensure_labels` fails to create a label (e.g., permissions), execution continues but the downstream `_create_issue` call will also fail for that label since `gh issue create --label X` requires the label to exist. Both failures are logged, so the user gets visibility. No tests exist for this function.

### ftl_code_expert/cli.py:file_issues (integration of _ensure_labels)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The call site at line 3543-3545 is correctly placed — after dedup and LLM confirmation but before issue filing. The `not dry_run and remaining` guard is correct: labels shouldn't be created during dry-run (no side effects), and there's no point creating labels when there are no issues to file. The `required_labels` union of hardcoded labels and user-provided labels covers all labels that will be referenced by `_create_issue`.

### Self-Review
**Limitations:** Could not verify `glab label list` accepts `--repo` and `-F json` flags — relying on consistency with existing `glab` usage in `_create_issue`. No test files were available to check whether existing test assertions still hold after these changes. Could not verify whether `gh label create` without `--color` behaves as expected across `gh` CLI versions.

### Feature Requests
- Include the test file(s) for the parent command (`file_issues`) if they exist, even when no tests directly cover the new function — callers' tests may exercise the new code path indirectly
- Flag when a new function with subprocess calls has zero test coverage, since these are integration-sensitive and hard to verify statically

## gemini [PASS]

### ftl_code_expert/cli.py:_ensure_labels
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `_ensure_labels` function is correctly implemented with robust checks and defensive JSON parsing for GitLab CLI (`glab`) output. Error scenarios (non-zero exit codes, malformed JSON, and empty list outputs) are handled gracefully to prevent command crashes. Standard output for status messages is correctly written to stderr (`err=True`).

### ftl_code_expert/cli.py:file_issues
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Integrating `_ensure_labels` into `file_issues` right before issue creation is safe, logically placed, and guarded with `not dry_run and remaining`. It verifies platform and repo credentials prior to calling label check/creation commands, preventing redundant executions or unhandled crashes.

### Self-Review
**Limitations:** - Could not list the directory structure or locate unit test files because shell command execution was restricted by security policy.
- Test coverage is marked as UNTESTED as there is no evidence of existing test files covering `file_issues` or `_ensure_labels` in the repository metadata or changes.
