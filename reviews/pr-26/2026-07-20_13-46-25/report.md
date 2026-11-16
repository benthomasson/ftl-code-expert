# Code Review Report

**Branch:** benthomasson/ftl-code-expert#26
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:_ensure_labels
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Two issues:

1. **GitLab label parsing is broken.** The GitHub path correctly uses `--json name -q ".[].name"` to get one label name per line, but the GitLab path uses bare `glab label list` which outputs a formatted table (columns with Name, Description, Color, etc.). Splitting on newlines will produce table headers and formatted rows, not clean label names. The `required - existing` set difference will never match, so every label will be "missing" and `glab label create` will be called unnecessarily. Creates for already-existing labels fail silently so this doesn't crash, but the dedup logic is dead code on GitLab. Fix: use `glab label list --output json` and parse JSON, or use a jq-style filter equivalent.

2. **`gh label list` pagination.** Default limit is 30 labels. Repos with many labels may not return all existing labels, causing redundant create attempts. Minor since creation failures are swallowed, but adding `-L 1000` would make the check reliable.

Neither issue causes data loss or crashes — label creation is idempotent (fails silently for duplicates) — so this is a CONCERN, not a BLOCK.

### ftl_code_expert/cli.py:file_issues (integration point)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The integration at lines 3527-3529 is correctly placed: after dedup and confirmation, before filing. The guard conditions (`not dry_run and remaining`) are appropriate. The required label set `{"reasons-gate", "reasons-negative"} | set(labels)` correctly covers both hardcoded labels (matching the `f"reasons-{ctype}"` pattern in the filing loop where ctype is "gate" or "negative") and user-supplied `--label` values. No issues with the wiring itself.

### Self-Review
**Limitations:** No test files exist for cli.py (confirmed by observations), so I cannot verify whether any test infrastructure exists that should have been extended. Could not verify the exact output format of `glab label list` at runtime — my concern about table-formatted output is based on known glab CLI behavior but not confirmed against the specific version in use. Could not see the full `_detect_platform` or `_find_existing_issues` functions to verify they handle the same platform strings consistently.

### Feature Requests
- Include the output format of external CLI tools (`gh`, `glab`) when subprocess calls parse their stdout — a quick runtime sample or man-page excerpt would help verify parsing logic
- Flag functions with zero test coverage automatically in the observation results, with a note about whether sibling functions have tests (to distinguish "no tests exist for this module" from "this function was skipped")

## gemini [CONCERN]

### ftl_code_expert/cli.py:_ensure_labels
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The GitHub implementation (`gh label list --repo repo_slug --json name -q .[].name`) correctly retrieves a clean list of label names. However, the GitLab implementation (`glab label list --repo repo_slug`) returns human-readable tables/headers containing metadata (e.g. `Showing X of Y labels` and colors/descriptions on each line). Thus, checking exact match via `required - existing` on line-by-line output will fail, causing the command to attempt to recreate existing labels on every invocation of `file_issues`. Also, subprocess exceptions and failure codes for label creation are swallowed silently.

### ftl_code_expert/cli.py:file_issues
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The label check and creation integration is correctly positioned after verifying remaining candidates and before executing the main loop. It correctly guards label auto-creation to only execute when `--dry-run` is omitted and there are active issues to file, which avoids redundant CLI overhead. However, the functionality is ultimately dependent on the flawed `_ensure_labels` for GitLab.

### Self-Review
**Limitations:** - Did not have a local environment with `glab` or `gh` CLI installed to execute the raw commands and verify exact output formats dynamically.
- No automated test files were provided or exist in the workspace directory structure, making it impossible to check for regression tests or run verification suites.

### Feature Requests
- Include CLI mock fixtures or sandbox integrations for tool dependencies (e.g. `gh` and `glab`) to allow validation of subprocess commands in unit tests.
- Show related tests or a basic testing suite outline in the workspace context to facilitate writing and reviewing test coverage.
