# Code Review Report

**Branch:** benthomasson/ftl-code-expert#24
**Models:** claude, gemini
**Gate:** [BLOCK] BLOCK

## claude [BLOCK]

### ERROR
**Verdict:** BLOCK

Model invocation failed: Model claude timed out after 300s

## gemini [CONCERN]

### ftl_code_expert/language.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- This new module introduces `LanguageProfile`, predefined profiles for Python, C++, and Rust, and language detection/symbol-extraction routines.
- `detect_language` utilizes file system heuristics (e.g. `Cargo.toml`, `pyproject.toml`) and falls back on extension counting, which is robust and correct.
- `_extract_symbol_brace` handles C-style comments, string literals, and brace depths carefully to extract symbols cleanly.
- Minor: The `in_line_comment` local variable is defined but unused.

### ftl_code_expert/cli.py
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Integrates language profiles into CLI subcommands (`scan`, `explain_file`, `explain_function`, `explain_repo`, `generate_spec`, and `_verify_belief_with_observations`).
- Passing `lang` into `_prepare_diff_topic` prevents runtime `TypeError` issues when invoking parallel exploration topics.
- Concerns:
  1. `_repo_path_to_entry_pattern` (line 1205) is called inside `_retract_beliefs_for_deleted_files` without passing `lang`. It defaults to Python (stripping `.py` instead of the project's actual extension like `.cpp` or `.rs`). For non-Python projects, deleted files' entry-name patterns will be computed incorrectly, causing retraction to fail.
  2. `_find_entry_points` splits on `=` under `[[bin]]` for Rust. In `Cargo.toml`, the binary entry looks like:
     ```toml
     [[bin]]
     name = "my-bin"
     path = "src/main.rs"
     ```
     This parser will append keys like `"name"` and `"path"` to the `entry_points` list because of `line.split("=")[0].strip()`. It should instead extract the actual path values.

### ftl_code_expert/git_utils.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Correctly updates `get_imports`, `extract_symbol`, and `find_related_tests` to support language-specific profiles.
- Correctly delegates `extract_symbol` to `extract_symbol_with_profile`.
- Incorporates a `seen` set in `find_related_tests` to prevent duplicate test files from being returned.

### ftl_code_expert/observations.py
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Updates observation commands (`grep`, `find_symbol`, `find_usages`, `file_imports`) to support language-specific patterns and globs.
- Supporting list-based `glob` in `grep` by mapping them to multiple `--include` flags is correct and well-integrated.
- Fallback line-by-line prefix matching in `file_imports` works well for C++ and Rust.
- Concern: In `find_symbol` (line 151), `patterns` are built with `p.format(symbol=symbol)` without escaping the symbol (unlike `_extract_symbol_indent` and `_extract_symbol_brace` which use `re.escape`). If a symbol contains regex-active special characters (such as C++ `operator+` or `operator[]`), passing it unescaped to `grep -Ern` will cause grep syntax errors or incorrect matches. It should use `re.escape(symbol)`.

### ftl_code_expert/prompts/function.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Adds `language` parameter to `build_function_prompt` to allow dynamic syntax highlighting in markdown code blocks.
- Backward compatible as it defaults to `"python"`.

### ftl_code_expert/prompts/observe.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Correctly updates `build_observe_prompt` to support the default glob parameter, defaulting to `"*.py"`.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

- Correctly replaces `*.py` with `{default_glob}` in the `VERIFY_OBSERVE_PROMPT` string template.
- Enables dynamic customization of the default glob description inside the prompt based on the repository's primary language.

### Self-Review
**Limitations:** - Shell commands were restricted in this environment, which prevented running existing tests or validating runtime behavior dynamically.
- The full body of `_retract_beliefs_for_deleted_files` was not visible in the diff or the observation results, but the caller context of `_repo_path_to_entry_pattern` was sufficient to trace the parameter mismatch.

### Feature Requests
- Include options to automatically run the project's test suite to verify whether modifications break existing unit/integration tests.
- Show full function definitions for every caller returned in the observation results to facilitate verification of parameter signatures and type correctness.
- Automatically check for dead code or unused imports inside the modified or newly added files.
