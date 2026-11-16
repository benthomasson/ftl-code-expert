# Code Review Report

**Branch:** benthomasson/ftl-code-expert#9
**Models:** claude, gemini
**Gate:** [BLOCK] BLOCK

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:research** [MEDIUM]: claude: CONCERN, gemini: BLOCK
- **ftl_code_expert/cli.py:_parse_review_candidates** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:_parse_inferred_files** [LOW]: claude: PASS, gemini: CONCERN

## claude [CONCERN]

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template with clear instructions and example output format. Placeholders (`belief_id`, `belief_text`, `comment`, `repo_tree`, `explored_files`) all match what the caller passes in `research()`. The "Output ONLY the JSON array" instruction pairs well with `_parse_inferred_files()` which defensively scans for the first valid JSON array.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard export wiring — import added and `__all__` updated. Alphabetical ordering maintained.

### ftl_code_expert/cli.py:_get_explored_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Scans first 5 lines of each entry for `# File:` headers, which matches the entry format produced by `_create_entry`. Handles missing `entries/` dir and per-file `OSError` gracefully. Returns a set for O(1) lookup.

### ftl_code_expert/cli.py:_parse_review_candidates
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

No error handling for malformed JSON — `json.load` will raise `JSONDecodeError` with a raw traceback rather than a user-friendly CLI error. Also, downstream code accesses `c['id']` and `c['comment']` without checking those keys exist. If a review entry lacks either key, you get a `KeyError`. Since this parses LLM-generated review output, defensive key access (`.get()` with a fallback or a filter) would be safer. Not a blocker since `click.Path(exists=True)` at least ensures the file exists, but a malformed review file gives a poor UX.

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Robust LLM output parser — iterates over all regex matches for `[...]` and validates each as a JSON list of strings before returning. Falls back to empty list. Handles markdown-wrapped responses where the array might not be the only content.

### ftl_code_expert/cli.py:research
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and follows existing patterns (`explore`, `propose-beliefs`, `_explore_topics_concurrent`). Integration is solid — it correctly uses `Topic(kind="file")`, `_explore_topics_concurrent`, `_finalize_topic`, `_run_file_topic`, and `ctx.invoke(propose_beliefs, auto_accept=True)`. Two concerns:

1. **No tests at all.** The observation confirms `test_count: 0`. The helper functions (`_parse_review_candidates`, `_parse_inferred_files`, `_get_explored_files`) are pure functions that are straightforward to unit test.

2. **`SystemExit` catch on `e.code`**: The check `if e.code and e.code != 0` will also suppress `SystemExit(None)` and `SystemExit(0)`, which is correct intent but worth noting that `_run_file_topic` calls `sys.exit(1)` on error, so the catch in the sequential path `except (SystemExit, Exception)` correctly prevents a single file failure from aborting the whole research run.

The overall pipeline logic — parse review → load network → infer files → filter explored → explore → propose+accept — is sound. The `--dry-run` escape hatch is a good design choice.

### Self-Review
**Limitations:** Could not verify the `Topic` dataclass/namedtuple field names — the observation shows no `__init__` signature, so I'm trusting that `title`, `kind`, `target`, `source` are valid fields based on existing usage patterns in the codebase. Could not see `invoke_concurrent_sync` signature to verify the `model`/`timeout`/`max_concurrent` kwargs. Could not see what `_create_entry` expects to verify the entry format matches what `_get_explored_files` parses.

### Feature Requests
- Include the dataclass/namedtuple definition for classes used in new code (e.g., `Topic` fields and types)
- Show the signature of utility functions called from new code (`invoke_concurrent_sync`, `get_repo_structure`, `check_model_available`) to verify argument compatibility
- Flag when `test_count: 0` prominently in the observation results header so it's immediately visible

## gemini [BLOCK]

### ftl_code_expert/cli.py:research
**Verdict:** BLOCK
**Correctness:** BROKEN
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

In Step 7, calling `ctx.invoke(propose_beliefs, auto_accept=True)` will raise a `TypeError` in Python. The function `propose_beliefs` has the signature `def propose_beliefs(ctx, batch_size, output, model, entry_paths, process_all, auto_accept, since)` where none of the arguments except `ctx` (automatically managed by Click) have Python default values. Since `ctx.invoke` is a direct function invocation wrapper, Python will fail to bind the other positional/keyword arguments. This will cause `TypeError: propose_beliefs() missing 6 required positional arguments: 'batch_size', 'output', 'model', 'entry_paths', 'process_all', and 'since'`. While the error is caught, it prints a warning and completely skips proposing and auto-accepting the new beliefs, breaking the core "explore → propose → accept" loop.
To fix this, the call should explicitly pass the default values/arguments:
```python
ctx.invoke(
    propose_beliefs,
    batch_size=5,
    output="proposed-beliefs.md",
    model=None,
    entry_paths=None,
    process_all=False,
    auto_accept=True,
    since=None
)
```

### ftl_code_expert/cli.py:_get_explored_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly scans the first 5 lines of each markdown file in `entries/` for the `# File: <path>` header to collect explored files. One minor concern is that `entry_path.read_text()` uses the system default encoding, which could theoretically raise `UnicodeDecodeError` or behave inconsistently depending on the platform's default encoding (e.g., on Windows), but since the project runs on Darwin/Unix and uses standard UTF-8 files, it is generally safe. Adding `encoding="utf-8"` would be more robust.

### ftl_code_expert/cli.py:_parse_review_candidates
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Parses the review JSON file and filters candidates where `sufficient` or `valid` are false. Similar to above, `open(review_file)` has no explicit encoding. Using `open(review_file, encoding="utf-8")` is recommended.

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The non-greedy regex `r"\[.*?\]"` works well for flat JSON arrays, but could fail or behave unexpectedly if the LLM output contains nested brackets (e.g. `[["file1.py"]]` would yield `[["file1.py"]` which fails JSON parsing, or if there is preceding bracketed text like reference markers `[1]`). 
Furthermore, the extracted relative file paths `f` are passed directly to `os.path.join(abs_repo, f)` and checked with `os.path.isfile(abs_path)`. There is no check to ensure `f` is a relative path that doesn't escape `abs_repo` (e.g., via directory traversal like `../../etc/passwd` or absolute path `/etc/passwd`). While the repository environment is trusted, it is a code safety concern when handling raw LLM outputs.

### ftl_code_expert/prompts/__init__.py
VERDICT: PASS
CORRECTNESS: VALID
SPEC_COMPLIANCE: N/A
ISSUE_COMPLIANCE: N/A
BELIEF_COMPLIANCE: N/A
TEST_COVERAGE: N/A
INTEGRATION: WIRED
REASONING: Correctly imports and re-exports `RESEARCH_INFER_FILES_PROMPT`.
---

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Well-structured prompt that provides clear instructions, context placeholders (`belief_id`, `belief_text`, `comment`, `repo_tree`, `explored_files`), and a concrete JSON example to guide the model.

### Self-Review
**Limitations:** Did not have full context of `ftl_code_expert/cli.py` or definition of `Topic` class, but the observation results for relevant functions and types were sufficient to verify integration points.

### Feature Requests
- Automatically run linting and signature-matching checks on internal `ctx.invoke` calls to catch argument binding mismatches.
- Show signatures of Click command callbacks directly when checking integration in observation results.
