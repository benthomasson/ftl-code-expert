# Code Review Report

**Branch:** benthomasson/ftl-code-expert#21
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/git_utils.py:list_source_files
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Logic is sound for the happy path. The BFS sort `(p.count(os.sep), p)` correctly orders by depth. However, `git ls-files` always emits forward-slash separators, while the sort key uses `os.sep`. On macOS (current platform) this works because `os.sep == '/'`, but it's a latent cross-platform bug — on Windows, `os.sep` is `\\` so every file would get `count=0` and the depth sort would be flat. Minor: no upper bound on returned files — a large monorepo could queue thousands of topics in one shot. No tests exist for this function.

### ftl_code_expert/git_utils.py:BINARY_EXTENSIONS
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Reasonable blocklist. Extension-less files (Makefile, Dockerfile, LICENSE) correctly pass through since empty string is not in the set. `frozenset` is the right choice for a module-level constant used in membership tests. Could be more exhaustive (`.wasm`, `.parquet`, `.arrow`) but covers the common cases well.

### ftl_code_expert/cli.py:scan
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The ordering is intentional — file topics are queued before LLM-suggested topics so that BFS file exploration has priority. `add_topics` deduplicates by `target`, so if the LLM later suggests a file that was already queued, it's correctly skipped. The `project_dir` extraction was hoisted above both calls, avoiding a redundant `_get_project_dir` call — good. One concern: for a repo with 5,000 tracked source files, `add_topics` loads the queue JSON, builds a set of all existing targets, iterates all 5,000 topics, then serializes back — all synchronous and in-memory. No test coverage for the scan command at all.

### ftl_code_expert/cli.py (import cleanup)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

`Topic` moved from two inline `from .topics import Topic` statements (in `walk_commits` at line 1337 and `research` at line 3788) to the top-level import block. The observation confirms no stale references remain. Clean improvement that reduces redundancy.

### Self-Review
**Limitations:** No test files exist for either `git_utils.py` or the `scan` CLI command, so there's nothing to check for broken assertions. Could not verify the `Topic` dataclass fields directly (observation returned "No function found at 'Topic'" since it's a class, not a function) — relied on usage patterns to confirm the constructor call is correct. Could not assess how `explore` processes `kind="file"` topics downstream, which would confirm end-to-end correctness of the new file topic flow.

### Feature Requests
- Include dataclass/class definitions in observations, not just functions — the `Topic` class observation failed because the observer only looks for functions
- Show downstream consumers of queued topics (e.g., what processes `kind="file"` topics) to verify end-to-end integration
- Flag when test_count is 0 for modified files more prominently in the observation summary

## gemini [CONCERN]

### `ftl_code_expert/git_utils.py:list_source_files`
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** MEETS
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. **Windows OS Compatibility Issue**: The sorting line `files.sort(key=lambda p: (p.count(os.sep), p))` attempts to sort files by depth first (BFS). However, Git (`git ls-files`) consistently outputs forward-slash path separators (`/`) across all operating systems, including Windows. Since `os.sep` is `'\\'` on Windows, `p.count(os.sep)` will evaluate to `0` for all paths on Windows platforms, falling back to a pure lexicographical/alphabetical sort. Changing this to count forward slashes (e.g., `p.count('/')`) or using `Path(p).parts` is necessary to ensure platform-independent BFS sorting.
2. **Missing Tests**: This utility handles shell command execution and filtering logic, but contains no unit or integration tests. A mock-based or temporary-directory-based test verifying file filtering and path depth sorting would guard against silent regressions.

### `ftl_code_expert/cli.py:scan`
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. The implementation cleanly extracts the project directory path once and feeds all tracked source files into the topic queue as `kind="file"` topics. By adding these before parsing LLM-suggested topics, it satisfies the "breadth before depth" ordering.
2. **Scalability/Performance Concern**: Since the topic queue is scanned with $O(N)$ complexity on each pop, enqueuing every single tracked file in a large repository (e.g., >1,000 files) without a depth limit or maximum count could degrade queue operation performance downstream.

### `ftl_code_expert/cli.py` (Topic Import Cleanup)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Since the `Topic` dataclass is now imported at the module level (line 48) to support the `scan` command, deleting the redundant local imports in `walk_commits` and `research` commands is correct, clean, and avoids import shadowing.

### Self-Review
**Limitations:** - There are no existing automated tests in the repository for `scan` or `git_utils` commands, making it impossible to check for preexisting test assertions.
- Did not have access to an active Windows environment to empirically measure the exact behavior of `subprocess` with `git ls-files` under the Windows terminal/environment, but the forward-slash separator output is well-known standard behavior for Git commands.

### Feature Requests
- **Automatic Test Runner & Verification**: Enhance the review platform to automatically identify and run local test files (if they exist) upon code modification or review, so we can verify if test coverage metric claims are correct.
- **Cross-Platform Virtualization/Mocking**: Provide a way to run checks or simulated executions of system/shell utility functions on different target OSs (e.g., Windows vs. Linux) to catch OS-specific bugs like path separator mismatches automatically.
