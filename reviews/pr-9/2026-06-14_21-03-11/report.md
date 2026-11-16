# Code Review Report

**Branch:** benthomasson/ftl-code-expert#9
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_parse_inferred_files** [LOW]: claude: PASS, gemini: CONCERN

## claude [CONCERN]

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean prompt template. Properly instructs the LLM to output a JSON array with clear constraints (1-5 files, relative paths, exclude already-explored). Format placeholders match usage in the research command.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard re-export addition. Added to both the import and `__all__`.

### ftl_code_expert/cli.py:_get_explored_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Scans first 5 lines of each entry for `# File:` header — matches the entry format used by `_create_entry`. OSError is caught per-file so one unreadable entry won't crash the scan. Returns a set for O(1) lookup.

### ftl_code_expert/cli.py:_parse_review_candidates
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function itself is fine, but callers access `c['id']` and `c['comment']` without checking those keys exist. If a review result lacks `id` or `comment`, the command crashes with a KeyError. Low risk since the input is from `review-beliefs` output which should always have those fields, but a `.get()` with a fallback or early validation would be more defensive at this system boundary (reading external JSON).

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Regex `\[.*?\]` with `re.DOTALL` correctly handles multiline JSON arrays. Non-greedy match grabs the first array, which is the right behavior given the prompt asks for exactly one. Type-checks both the parsed result and individual elements. Edge case: nested arrays would be mis-parsed, but the prompt constrains output to a flat string array.

### ftl_code_expert/cli.py:research
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and follows established patterns (concurrent exploration, `_finalize_topic`, `ctx.invoke(propose_beliefs)`). Two concerns:

1. **No tests.** This is a 130-line command with multiple stages (parse, infer, explore, propose). The helper functions `_parse_review_candidates`, `_parse_inferred_files`, and `_get_explored_files` are all easily unit-testable but have zero coverage.

2. **Sequential path calls `sys.exit(1)` on error.** When `parallel <= 1`, the code calls `_run_file_topic` which exits on any LLM error (observed at line 1024). This means the first file failure kills the entire research run, losing any results from previously explored files. The concurrent path handles this gracefully via `return_exceptions=True`. Consider wrapping the sequential call in a try/except to match the concurrent path's resilience.

Minor: `ctx.invoke(propose_beliefs, auto_accept=True)` is a correct use of Click's invoke mechanism — the `SystemExit` catch is appropriate since `propose_beliefs` calls `sys.exit()` on some error paths.

### Self-Review
**Limitations:** Could not verify the `Topic` dataclass/namedtuple fields — the observation showed no `__init__` signature, so I cannot confirm the constructor accepts `title`, `kind`, `target`, `source` kwargs (though usage is consistent with `_explore_topics_concurrent` which accesses `.kind` and `.target`). Could not see `invoke_concurrent_sync` implementation to verify it handles the prompts list and returns results in the same order. Could not see the review-beliefs output format to confirm `id` and `comment` fields are always present.

### Feature Requests
- Include dataclass/namedtuple field definitions when a class observation returns no `__init__` signature
- When `invoke_concurrent_sync` is imported from another module but not found in the target file, auto-search the source module
- Include the JSON schema or sample output of upstream commands (like `review-beliefs`) when the code under review parses their output

## gemini [CONCERN]

### ftl_code_expert/cli.py:_parse_inferred_files
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The function extracts a JSON array from the model's response using the regex `re.search(r"\[.*?\]", response, re.DOTALL)`. This is highly fragile. If the LLM includes any conversational text that contains square brackets prior to the actual JSON array (e.g., `"I have reviewed belief [belief-123] and suggest..."`), the regex will match `[belief-123]`. `json.loads` will then fail with a `JSONDecodeError`, and the entire extraction will return an empty list `[]`, ignoring the actual file list array. 

**Recommendation:**
Instead of using `re.search`, iterate through all matches using `re.finditer` and try to parse each bracketed expression as a list of strings until one succeeds:
```python
def _parse_inferred_files(response: str) -> list[str]:
    """Extract JSON array of file paths from LLM response."""
    for m in re.finditer(r"\[.*?\]", response, re.DOTALL):
        try:
            files = json.loads(m.group(0))
            if isinstance(files, list) and all(isinstance(f, str) for f in files):
                return files
        except json.JSONDecodeError:
            continue
    return []
```

### ftl_code_expert/cli.py:research
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The command is well-structured and maps the entire evidence-driven exploration pipeline correctly. However, there is an inconsistency in how errors are handled during topic explanation:
1. **Parallel execution:** If a topic explanation fails, `_explore_topics_concurrent` catches the exception via `asyncio.gather(return_exceptions=True)`. The command logs the error and proceeds to process the remaining topics.
2. **Sequential execution:** If a topic explanation fails, `_run_file_topic` intercepts the exception and immediately invokes `sys.exit(1)`, terminating the entire research execution prematurely and skipping the rest of the topics.

Additionally, `open` is called in `_parse_review_candidates` without specifying `encoding="utf-8"`, which could cause decoding errors on platforms where the system default encoding is not UTF-8.

**Recommendation:**
Harmonize the sequential execution to log errors and continue (similar to the parallel execution) rather than aborting immediately with `sys.exit(1)`. Always specify `encoding="utf-8"` on `open()`.

### ftl_code_expert/prompts/research.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The prompt template is clear, structured, and properly leverages relevant context (the belief claim, review comments, repository tree, and already explored files). It explicitly asks the LLM to output ONLY the JSON array to minimize formatting variation.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The prompt module correctly imports and exports `RESEARCH_INFER_FILES_PROMPT` in `__all__`, making it available for clean usage in `cli.py`.

### Self-Review
**Limitations:** No existing unit tests or test frameworks are configured in the repository (as verified by the absence of test files in `ftl_code_expert` or root and empty optional dependencies), so the execution and coverage of the command could not be verified programmatically in this project's ecosystem.

### Feature Requests
- Implement a basic unit testing framework (e.g., `pytest` or Python's native `unittest` library) with mock responses for the LLM component to allow robust test verification of the parsing and command flows.
- Show code callers of functions imported/exported from `git_utils.py` and `llm.py` to make architectural dependencies even clearer during review.
