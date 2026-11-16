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

The function is sound for the common case, but two things stand out:

1. **The "BFS" claim is inaccurate.** The comment in `cli.py:371` says "BFS: breadth before depth," but `files.sort()` produces lexicographic order on full paths, which interleaves depths (`a/b/c.py` sorts before `a/d.py` sorts before `b.py`). True breadth-first would sort by `path.count(os.sep)` first, then alphabetically within each level. If BFS ordering matters for the exploration queue, this is a bug; if not, the comment is misleading and should be removed or corrected.

2. **No tests.** `list_source_files` has zero test callers. A unit test with a temp git repo (or mocked subprocess) covering the happy path, a failed `git ls-files`, and binary-extension filtering would be valuable — especially since this feeds directly into the topic queue and a subtle regression (e.g., including binaries, or returning empty on a valid repo) would be silent.

Minor: `.svg` is listed as binary but is text/XML. Reasonable to exclude from code analysis, but worth a brief inline note if someone later wonders why SVGs are "binary."

### ftl_code_expert/git_utils.py:BINARY_EXTENSIONS
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The frozenset is a sensible blocklist of non-source extensions. Coverage is broad enough for typical repos. Missing some arguable entries (`.lock`, `.min.js`, `.map`, `.wasm`) but those are judgment calls, not bugs.

### ftl_code_expert/cli.py:scan
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The scan command now enumerates all tracked source files as file topics before appending LLM-suggested topics. Integration with `add_topics` is correct — deduplication by `target` prevents double-queuing if the LLM also suggests a file path.

Two concerns:

1. **Scale.** For a large repo (10k+ files), this creates 10k+ Topic objects, serializes them all through `add_topics` (which loads the full queue JSON, builds a set of existing targets, appends, and re-serializes). No cap, no warning. This will work but could be slow and produce a very large queue file. Worth at least a `log` or `click.echo` if `len(source_files)` exceeds some threshold, or documenting the expected scale.

2. **BFS ordering mismatch** (same as above). The file topics are sorted lexicographically, not by directory depth. Since these are inserted before LLM topics, the "breadth before depth" intent is only partially realized — files within directories are breadth-ordered relative to LLM topics, but not relative to each other.

No tests exist for the `scan` command at all (`scan_tests` shows 0 test files).

### ftl_code_expert/cli.py (import cleanup)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Moving `Topic` from inline imports in `walk_commits` (line 1348) and `research` (line 3798) to the top-level import block is a clean consolidation. The `topic_import_migration` observation confirms no stale references remain. No behavioral change.

### Self-Review
**Limitations:** Could not see the full `Topic` dataclass definition (observation errored). Could not verify what fields are required or whether `kind="file"` is a recognized value downstream. Could not see how topics are consumed (the `explore` command or equivalent) to verify that `kind="file"` topics are handled correctly end-to-end.

### Feature Requests
- Include dataclass/NamedTuple definitions when they're constructed in the diff — the `Topic` class definition was missing from observations
- Show downstream consumers of new data (e.g., what reads `kind="file"` topics from the queue) to verify full end-to-end integration
- Flag when test coverage is zero for both the function AND its callers — that's a stronger signal than either alone

## gemini [CONCERN]

### ftl_code_expert/git_utils.py:list_source_files
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function executes `git ls-files` and sorts the resulting list of files using `files.sort()`. This is a standard alphabetical (lexicographical) sort. However, the caller in `cli.py` explicitly states that the enumeration should follow BFS order (`BFS: breadth before depth`). Alphabetical sorting places deeper files (such as `a/b/c.py`) before shallower files (such as `g.py`) if they are alphabetically earlier, violating BFS ordering. To achieve true BFS ordering, the list should be sorted by depth (e.g. `files.sort(key=lambda p: (p.count(os.sep), p))`).
Additionally, there are no unit tests in the repository to verify this utility or its filtering of binary extensions.

### ftl_code_expert/cli.py:scan
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The integration logic in the `scan` command is correct. It successfully resolves the repository path, retrieves tracked non-binary source files, maps them to `Topic` objects, and bulk-appends them to the queue via `add_topics` prior to enqueuing LLM-suggested topics. No issues were found in parameter mapping or type conversions. However, like the rest of the codebase, there is no automated test coverage to assert correctness.

### ftl_code_expert/cli.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The changes clean up inline imports of `Topic` from functions `walk_commits` and `research`, moving them to a single top-level import from `.topics`. This is idiomatic and clean. It does not introduce circular dependencies as `topics.py` does not import `cli.py` or depend on any of its exports.

### Self-Review
**Limitations:** No specification (`SPEC.md`) or issue description was provided, so compliance with specific feature requests could not be evaluated.
