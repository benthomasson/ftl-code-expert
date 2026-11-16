# Code Review Report

**Branch:** benthomasson/ftl-code-expert#24
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

## gemini [PASS]

### ftl_code_expert/language.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- This is a new module defining language profiles (`LanguageProfile`) for Python, C++, and Rust, and implementing language-specific tokenizers and scope extractors.
- The brace-matching parser (`_extract_symbol_brace`) is exceptionally robust. It correctly tracks block comments (`/* ... */`), single-line comments (`// ...`), and quoted strings (including backslash-escaped characters), preventing false-positive brace matches inside comments or literals.
- Semicolon-terminated declaration statements vs. brace-based scope definition blocks are correctly distinguished.
- No automated test files are visible in the workspace, so coverage is rated `UNTESTED`.

### ftl_code_expert/git_utils.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- `get_imports` was successfully refactored to use the active language profile's rules instead of hardcoded Python behavior.
- `extract_symbol` delegates extraction logic to the language profile, ensuring correct parsing for Python (indent-based) and C++/Rust (brace-based).
- `find_related_tests` was updated to iterate through test file globs specific to each language profile (e.g. `*_test.rs` and `test_*.rs` for Rust) and uses a `seen` set to avoid duplicate entries when a test file matches multiple glob patterns.
- All modifications preserve complete backward compatibility when `lang` is omitted (defaults to Python).

### ftl_code_expert/observations.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- `grep` was modified to support the `glob` parameter as a `list[str]` of multiple glob patterns, correctly formatting multiple `--include` arguments for the underlying `grep` process.
- `find_symbol`, `find_usages`, and `file_imports` were successfully updated to utilize language profiles (`definition_patterns`, `import_line_prefixes`, `source_globs`, etc.).
- The Python-specific AST parse in `file_imports` is safely isolated to `lang.name == "python"`, with a generic line-by-line prefix matcher as a fallback for other languages, preventing AST errors on non-Python code.

### ftl_code_expert/prompts/function.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Adds the `language` argument (default `"python"`) to `build_function_prompt` and uses it to dynamically format the markdown code block fence language. This ensures correct syntax highlighting in generated reports for C++ and Rust.

### ftl_code_expert/prompts/observe.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Updates `build_observe_prompt` to accept `default_glob` (defaulting to `"*.py"`) and interpolates it into the user prompt guidelines to provide accurate context to the model based on the repo's actual language.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Modifies the prompt template's grep instructions to utilize a dynamic `{default_glob}` placeholder instead of a hardcoded `"*.py"`. This matches the updated call signature in `cli.py` during belief verification.

### ftl_code_expert/cli.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Integrates language-specific features throughout the entire command-line lifecycle (scanning, explaining files/functions/repositories, belief verification, and spec generation).
- Lazily detects and caches language in click context via `_get_lang(ctx)`.
- `_find_entry_points` was refactored to parse entries based on language profile candidates and configuration markers. It includes a smart parser for key-value entry lines (such as cargo `[[bin]]` entries with `path` keys) while retaining full compatibility with python project scripts.
- Updates belief retraction/gathering to reconstruct non-Python file extensions and format code blocks using proper markdown syntax fences.
- Updates concurrency orchestrators (`_explore_topics_concurrent`) to pass down the detected language, preventing mixed language profiles during concurrent execution.

### Self-Review
**Limitations:** - Shell command execution was denied by environment policy, preventing me from running `pytest` to verify runtime correctness and test suite status, or executing linters (e.g., `flake8` or `black`) to ensure zero formatting issues exist.

### Feature Requests
- Provide policy clearance or a restricted shell mode for running benign, non-modifying commands (such as `pytest` and code linters) to confirm test-suite success.
- Explicitly identify and append directories containing test code in the workspace context, even when they do not reside directly at the repository root.
