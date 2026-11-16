# Code Review Report

**Branch:** benthomasson/ftl-code-expert#22
**Models:** claude, gemini
**Gate:** [BLOCK] BLOCK

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:analyze** [MEDIUM]: claude: CONCERN, gemini: BLOCK

## claude [CONCERN]

### ftl_code_expert/cli.py:analyze
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

**1. `ctx.obj["repo"]` not set — broken when run from outside the target repo.**
The `analyze` command takes `repo_path` as an argument, but never sets `ctx.obj["repo"]` to match. At CLI group level (line 251-255), `ctx.obj["repo"]` resolves to cwd when no `--repo` flag is passed and no config exists yet (which is the case for a fresh `analyze` run). All subsequent `ctx.invoke` calls to `scan`, `explore`, etc. use `_get_repo(ctx)` (line 81-83) which reads `ctx.obj["repo"]`, so they'll operate on cwd instead of the target repo.

Typical use case (`cd repo && code-expert analyze .`) works because cwd == repo_path. But the documented example `code-expert analyze ~/git/my-project` from a different directory will silently use the wrong paths for scanning, exploration, queue reads, etc.

Fix: add `ctx.obj["repo"] = os.path.abspath(repo_path)` near the top of `analyze`, before any `ctx.invoke` calls. The `update` command doesn't need this because it doesn't take a `repo_path` argument and relies on pre-existing config.

**2. `limit=0` ("unlimited") caps at point-in-time queue size.**
Line `explore_limit = limit if limit > 0 else pending_count(project_dir)` snapshots the queue count after `scan`. But `explore` itself can enqueue new sub-topics during exploration (via `_finalize_topic` → `_enqueue_topics`). So "unlimited" actually means "up to however many topics existed when we started exploring", which is smaller than the true exhaustive count. This is minor and may be intentional, but the docstring says `--limit 0  # no cap` which overpromises.

**3. Duplicate `project_dir` resolution.**
`project_dir = _get_project_dir(ctx)` appears at line 4322 (for `explore_limit`) and the variable is reused at line 4420 (checkpoint save). The first call assigns `project_dir`, but if the bug from item 1 is fixed, the value will be consistent. Not a bug, just noting it.

**4. No test coverage.**
The observation confirms `test_count: 0`. A pipeline command that orchestrates 8+ steps is high-value for at least a smoke test (e.g., mocking the sub-commands and verifying invocation order and error-continue behavior).

**5. Good patterns carried over from `update`.**
The error-collection-and-continue pattern, `SystemExit` handling, pre/post belief snapshot, checkpoint persistence, and final report are all consistent with the existing `update` command (lines 4099-4259). The structure is clearly modeled on it, which is the right approach.

**6. Minor: `generate_summary` step 8 missing WARN echo.**
At step 8 (line 4393-4398), when `generate-summary` fails with `SystemExit`, the error is appended but no `click.echo(f"WARN: ...")` is printed. This mirrors `update`'s pattern at line 4211-4212, so it's intentionally silent there, but inconsistent with steps 1-7 which all echo warnings.

### Self-Review
**Limitations:** Could not inspect `_explore_loop` to verify behavior when `loop_max=0`. Could not verify where `topics.json` / queue files are written relative to `project_dir` to fully confirm the cwd-vs-repo_path impact. No test files to cross-reference against.

### Feature Requests
- Include the full body of helper functions referenced in the diff (like `_explore_loop`) to verify edge-case behavior in orchestration commands
- Show the `update` command body alongside `analyze` when both exist in the same file, since `analyze` is clearly modeled on it — makes it easy to spot intentional vs accidental divergence

## gemini [BLOCK]

### ftl_code_expert/cli.py:analyze
**Verdict:** BLOCK
**Correctness:** BROKEN
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

1. **Critical Target Repository Bug (Broken Integration)**: When the CLI runs, `cli()` initializes `ctx.obj["repo"]` to `os.getcwd()` if no global `--repo` option is passed and no config exists. The new `analyze` command accepts a required `repo_path` argument, but it never updates `ctx.obj["repo"]` to this path. Consequently, while `init` writes the correct `repo_path` to config, all subsequent invoked commands (`scan`, `explore`, etc.) retrieve the repository path via `_get_repo(ctx)`, which still returns `ctx.obj["repo"]` (the original current working directory). This means if `code-expert analyze ~/git/some-project` is run from outside the target repository, the tool will scan and explore the current directory instead of the target repository.
   * **Fix**: Add `ctx.obj["repo"] = os.path.abspath(repo_path)` at the start of the `analyze` function body to properly override and align the execution context.
2. **Fragile Error Handling/Cascade Failures**: If critical steps like `init` or `scan` fail and exit via `sys.exit(1)`, they raise `SystemExit(1)` which is caught and logged. However, the command prints a warning and proceeds to execute the rest of the pipeline anyway. For instance, if `scan` fails (leaving the queue empty), the command will still trigger `explore`, `propose_beliefs`, etc., which leads to redundant API calls and cascade errors.
3. **Missing File Encoding**: Writing the checkpoint file `last-analyze.json` lacks an explicit `encoding="utf-8"` parameter (line 4426), which can cause failures or corruptions on Windows platforms or systems with non-UTF-8 default locale settings.

### Self-Review
**Limitations:** - There are no automated tests (unit or integration) in this repository, making it impossible to run automated regressions or verify Click command context propagation through standard test suites.

### Feature Requests
- Implement a standard testing framework (such as `pytest` with Click's `CliRunner`) to facilitate automated testing of subcommand workflows and context interaction.
- Introduce mock configurations for LLM invocation components (`ftl_code_expert/llm.py`) so end-to-end integration tests can be run safely in CI.
