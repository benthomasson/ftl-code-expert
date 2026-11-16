# Code Review Report

**Branch:** benthomasson/ftl-code-expert#22
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/cli.py:analyze
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

**Correctness issues:**

1. **`project_dir` computed twice** (lines 4323 and 4433): Minor redundancy — `project_dir` is assigned at line 4323 for the explore limit calculation and then reassigned the same value at line 4433 for the checkpoint. Not a bug, just dead code.

2. **`pending_count` called before `scan` completes when `limit=0`** (line 4325): When `limit=0`, `explore_limit` is computed as `pending_count(project_dir)` *before* explore runs. This is computed after scan (step 2), so the queue is populated. This is correct.

3. **`SystemExit` handling is inconsistent**: Steps 1–7 print a `WARN:` message on `SystemExit`, but step 8 (`generate-summary`) and step 9 (`file-issues`) silently swallow `SystemExit` failures — they append to `errors` but don't echo a warning. This inconsistency means a user won't see visual feedback if the summary or issue-filing step fails.

4. **`explore` with `loop_max=0`**: If `pending_count` returns 0 (empty queue when `limit=0`), `ctx.invoke(explore, ..., loop_max=0)` enters `_explore_loop` with `max_topics=0`. The `while explored < max_topics` loop exits immediately without error, which is fine — but the step banner says "Explore (up to 0 topics)" which is confusing.

5. **Error accumulation is fire-and-forget**: Every step wraps in try/except and continues on error. If `init` fails (e.g., missing `git`/`entry` tools), subsequent steps like `scan` will also fail because config isn't written. The cascade of failures produces a noisy list of errors that obscures the root cause. Consider short-circuiting on `init` failure since it's a prerequisite for everything else.

6. **`_load_network()` called from CWD**: The snapshot logic at lines 4335–4338 calls `_load_network()` which looks for `network.json` in CWD or runs `reasons export`. This is consistent with how other commands work, so it's correct within the existing design.

**Testing**: Zero tests for this command. The `analyze` command orchestrates 8+ subcommands — even a basic smoke test verifying the happy path wiring or error handling would be valuable.

**Integration**: The command is properly wired as a Click subcommand, correctly sets `ctx.obj["repo"]`, and chains subcommands via `ctx.invoke` with correct parameter signatures. The checkpoint JSON output is a nice touch for debugging long runs.

### Self-Review
**Limitations:** Could not verify whether `ctx.invoke` correctly shares the Click context's `obj` dict with subcommands that use `@click.pass_context` (like `scan`, `explore`, `derive`) — this is a Click framework behavior I'm inferring from the pattern used in the existing `update` command (which presumably works the same way). Also could not see the `update` command implementation to compare patterns, though it's referenced in the diff context as being just above `analyze`. Could not run the code to verify end-to-end behavior.

### Feature Requests
- Include the sibling/analogous function (`update` command in this case) in observations when a new function follows the same pattern — enables diff-against-pattern review.
- Show import statements at the top of the file to verify all referenced names are imported.

## gemini [CONCERN]

### ftl_code_expert/cli.py:analyze
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The new `analyze` command is a convenient pipeline wrapper that automates the entire bootstrap, exploration, belief extraction, derivation, and summary generation flow from scratch. It is clean and well-structured, mirroring the existing `update` command's robust error-handling style and sequential step execution. However, several correctness and integration concerns exist:

1. **Path Resolution & Directory Mismatch**:
   - The command sets `ctx.obj["repo"] = os.path.abspath(repo_path)` and resolves `project_dir` using `_get_project_dir(ctx)`, which points to `{repo_path}/.code-expert`.
   - However, the `init` command bootstraps the project directory and `config.json` relative to `Path.cwd()` (i.e., `./.code-expert`), and `propose_beliefs` searches for `Path("entries")` relative to `Path.cwd()`.
   - If `code-expert analyze ~/git/my-project` is run from any directory other than `~/git/my-project`, the metadata will be fragmented: `config.json` and the `entries/` directory will be created in the current working directory, whereas `topics.json` will be saved under the target repository's `.code-expert` directory. This will cause subsequent steps to look in the wrong folders or fail to find expected inputs.

2. **Exploration Limit Calculation (`--limit 0`)**:
   - The command calculates `explore_limit = limit if limit > 0 else pending_count(project_dir)`.
   - When `--limit 0` ("no cap") is passed, this snapshots the pending topics queue count right after `scan`. However, during file exploration in Step 3, the model can dynamically discover and enqueue new sub-topics (e.g., functions, nested files). Since `explore_limit` is passed as a static number to `explore` (`loop_max=explore_limit`), the command will stop exploring once the initial queue is exhausted, rather than truly exploring "without cap" until the queue is fully depleted.

3. **Untested Execution**:
   - There are no automated unit or integration tests for the `analyze` command, and there is no active test framework/suite currently configured in the workspace to cover CLI integration flows.

### Self-Review
**Limitations:** - Could not run or verify the CLI command directly as no mock repository or test harness was available in the workspace to perform end-to-end testing.
- The external commands/CLIs (`entry`, `reasons`, and `beliefs`) are assumed to behave as described, but their implementation details or path expectations (such as how they handle relative versus absolute paths) were not fully visible.

### Feature Requests
- Include mock git repository setups or a standard test workspace to allow running and dry-running end-to-end integration tests of CLI commands.
- Provide a tool to inspect the behavior of external CLI tools (like `entry` or `reasons`) to verify directory/file-handling consistency across boundaries.
