# Code Review Report

**Branch:** benthomasson/ftl-code-expert#9
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_get_explored_files** [LOW]: claude: PASS, gemini: CONCERN
- **ftl_code_expert/cli.py:_parse_inferred_files** [LOW]: claude: PASS, gemini: CONCERN

## claude [CONCERN]

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template. Format placeholders (`{belief_id}`, `{belief_text}`, `{comment}`, `{repo_tree}`, `{explored_files}`) match the `.format()` call in the research command. Properly exported through `prompts/__init__.py` and `__all__`.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard re-export plumbing. Import and `__all__` entry both added.

### ftl_code_expert/cli.py:_get_explored_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Scans first 5 lines of entry files for `# File:` headers — matches the format used by `_create_entry` elsewhere. `OSError` catch on per-file reads is appropriate. Returns an empty set gracefully when `entries/` doesn't exist.

### ftl_code_expert/cli.py:_parse_review_candidates
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Uses bare `json.load` with no error handling — a malformed review JSON will produce an unhandled exception with no user-friendly message. More importantly, callers later access `c['id']` and `c['comment']` with direct dict indexing (not `.get()`). If the review JSON has entries missing these keys, a `KeyError` propagates with no context. Since this reads LLM-generated review output, defensive access would be prudent.

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `\[.*?\]` regex with `re.DOTALL` is non-greedy and will match the first complete bracket pair. For simple string arrays (which the prompt requests), this is reliable. Type validation (`isinstance` checks) is good. Falls back to empty list on parse failure.

### ftl_code_expert/cli.py:research
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and follows existing patterns in the codebase (same explore/propose pipeline, same concurrency approach). Path traversal protection on LLM-inferred paths is present and correct (`os.path.isabs` + `..` check + `os.path.isfile`). Two concerns:

1. **No tests at all.** The observation confirms `test_count: 0`. The helper functions (`_get_explored_files`, `_parse_review_candidates`, `_parse_inferred_files`) are pure and easily testable — they should have unit tests.

2. **`ctx.invoke(propose_beliefs, auto_accept=True)`** in step 7 relies on Click parameter defaults for `batch_size`, `output`, `model`, `entry_paths`, `process_all`, `since`. This works today but is brittle — if `propose_beliefs` adds a required parameter or changes a default, this call silently changes behavior. Consider passing key parameters explicitly.

The integration is solid: the command reuses `_explore_topics_concurrent`, `_finalize_topic`, `_run_file_topic`, `_load_network`, `invoke_concurrent_sync`, `get_repo_structure`, and `Topic` — all existing infrastructure. The CLI registration via `@cli.command("research")` wires it into the group automatically.

### Self-Review
**Limitations:** Could not see the `invoke_concurrent_sync`, `get_repo_structure`, or `check_model_available` implementations (imported from `.llm` and `.git_utils`). Could not verify the review JSON schema that `_parse_review_candidates` expects. Could not see the `Topic` dataclass/namedtuple definition to confirm field names match.

### Feature Requests
- Include the schema or sample output of upstream commands (e.g. `review-beliefs` JSON format) when the diff parses their output — lets reviewers verify field access is correct.
- Show the `Topic` class definition when it's constructed in new code — field name mismatches are a common source of bugs.

## gemini [CONCERN]

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Well-crafted prompt template that sets clear expectations, provides a concrete output format, and supplies the LLM with relevant context (belief metadata, repository tree, and already-explored files) to successfully infer target files.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly imports and re-exports `RESEARCH_INFER_FILES_PROMPT` in `__init__.py` and maintains clean alphabetical exports in `__all__`.

### ftl_code_expert/cli.py:_get_explored_files
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function correctly extracts paths from files with `# File: ` headers in the first 5 lines. However, calling `read_text()` on the entire file before splitting lines is memory-inefficient if any entry files are large (e.g., from massive log dumps or automated system reports). Reading line-by-line using a `with open(...)` file handler and `f.readline()` in a 5-iteration loop is much more token-efficient and performance-friendly.

### ftl_code_expert/cli.py:_parse_review_candidates
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. No fallback or error handling is provided for `json.load(f)`. If a review file is malformed or corrupted, it will raise a raw `JSONDecodeError` rather than a user-friendly CLI warning.
2. The caller directly accesses `c["id"]` and `c["comment"]` without verifying that these keys exist in the parsed JSON objects. If a result object is missing either of these fields, the CLI will crash with a `KeyError`. Using `.get("id")` and `.get("comment", "")` is highly recommended at this system boundary.

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The extraction logic via `re.finditer(r"\[.*?\]", response, re.DOTALL)` is elegant because it correctly validates elements as strings, but has a cross-platform path validation vulnerability in its usage.
Specifically, `f.split(os.sep)` is used in the caller to check for directory traversal (`".."`). If the tool runs on Windows (where `os.sep` is `\`) but the LLM returns standard POSIX paths (e.g. `["src/auth/../../etc/passwd"]`), `split(os.sep)` splits on `\`, resulting in `["src/auth/../../etc/passwd"]`. Since `".."` is not exactly in that list, the traversal check is bypassed. Using `Path(f).parts` is platform-agnostic and robust as it splits on both slashes correctly.

### ftl_code_expert/cli.py:research
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

1. **No Tests**: There is no test coverage for the new `research` command or its pure utility functions (e.g., parsing, path validation).
2. **Robust Click Defaults**: Calling `ctx.invoke(propose_beliefs, auto_accept=True)` is fully correct. Click's `Context.invoke()` dynamically populates all missing options with their decorator-defined defaults when calling a `click.Command` object, so this will not raise a `TypeError`.
3. **Asymmetric/Questionable Error Handling**: `_run_file_topic` calls `sys.exit(1)` directly on error. This is a questionable practice for batch/loop helpers and forces `research` to wrap the call in a `try/except (SystemExit, Exception)` block to avoid process termination on a single file failure.

### Self-Review
**Limitations:** - There is no unit/integration testing framework in the current workspace (test files list is empty and test count is 0), so verification of test-suite integration was limited to structural analysis of signatures and callbacks.

### Feature Requests
- Provide sample output/schema files of upstream tool outputs (like `reasons export` or `review-beliefs`) to aid in reviewing external parser boundaries.
- Automatically flag cross-platform file path traversal concerns (`os.sep` splits) when analyzing raw string manipulation of file paths.
