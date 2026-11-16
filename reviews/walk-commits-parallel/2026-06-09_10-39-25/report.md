# Code Review Report

**Branch:** walk-commits-parallel
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:walk_commits
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

**Structure is sound.** The two-phase refactor (build topics, then batch-process) mirrors the existing `explore` command pattern (lines 770-780) and correctly reuses `_explore_topics_concurrent` and `_finalize_topic`. The batch slicing, progress display, and fallback to sequential `_run_file_topic` for `parallel=1` or last-batch-of-one are all correct.

**Error handling asymmetry (lines 1369-1377).** In parallel mode, exceptions are logged and skipped (`click.echo(f" Error: {r}")`) — the run continues. In sequential mode, `_run_file_topic` (line 1022) calls `sys.exit(1)` on the first error. This means identical inputs produce different failure behavior depending on `--parallel`. A file that triggers an LLM error will abort the entire walk in sequential mode but be silently skipped in parallel mode. This is the same pattern used in `explore`, so it may be intentional, but it's worth noting.

**Dead data in `topics_with_commits`.** The `commit` half of each `(topic, commit)` tuple is never referenced after topic construction — the commit SHA and subject are already baked into `topic.title` and `topic.source`. Minor; no functional impact.

**No tests.** `walk_commits_tests` shows zero test files. This is a non-trivial control flow change (batching, async/sync branching) with no coverage at all.

### Self-Review
**Limitations:** Could not verify that `ctx.obj["parallel"]` is set by the CLI group — the group definition was not in the diff or observations. Assumed it exists based on the same pattern working in the `explore` command. Could not run the code to verify batch boundary behavior with real data.

### Feature Requests
- Include the CLI group/parent command definition when child commands reference `ctx.obj` keys not defined in their own options — this is critical for verifying integration of group-level flags.
- Show the test directory structure or test manifest so reviewers can assess whether the absence of tests is a gap vs. a known state.

## gemini [CONCERN]

### ftl_code_expert/cli.py:walk_commits
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The implementation correctly transitions `walk_commits` from sequential to parallel file exploration. It uses a batching strategy synchronized with the `parallel` configuration and leverages the existing `_explore_topics_concurrent` helper. The logic for pre-filtering deleted files (lines 1344-1350) and handling concurrent results/exceptions (lines 1373-1380) is sound. However, the change is marked as CONCERN because this significant shift in execution flow is entirely UNTESTED in the provided context, and there is no verification that `ctx.obj` correctly contains the `parallel` and `timeout` keys (though their usage is consistent with typical Click patterns in this project).

### Self-Review
**Limitations:** I could not verify the CLI definition to ensure `--parallel` and `--timeout` options are correctly registered and passed into the context. The absence of test files in the diff or observations prevents me from confirming that this new concurrent execution path is actually exercised or that it doesn't break existing sequential expectations.

### Feature Requests
- Include the CLI command group definition (the `@click.group` or `@cli.command` decorators for the parent command) to verify how `ctx.obj` is populated.
- Provide existing test files for the modified functions to help identify regressions or missing coverage.
