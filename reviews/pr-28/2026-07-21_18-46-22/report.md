# Code Review Report

**Branch:** benthomasson/ftl-code-expert#28
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/language.py (GO profile)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The profile is structurally correct and integrates properly — it's in `LANGUAGE_REGISTRY` and `_CONFIG_TO_LANGUAGE` already maps `"go.mod": "go"` (pre-existing), so `detect_language()` will return the GO profile when it finds a `go.mod`. The `scope_style="brace"` choice is correct and will route to `_extract_symbol_brace`. Three issues worth noting:

1. **Backtick raw strings not handled by brace extractor** (pre-existing, but Go-specific risk). `_extract_symbol_brace` (line 279) handles `"` and `'` string literals but not Go's backtick-delimited raw strings. A function containing `` `SELECT * FROM {table}` `` or raw regex with braces would throw off the brace counter and truncate/overrun extraction. This affects Go more than the other brace languages since raw strings are idiomatic Go (SQL, templates, test fixtures). Not introduced by this diff, but this is the first language where it matters enough to flag.

2. **Grouped const/var declarations missed**. The patterns `^const\s+{symbol}\s+` and `^var\s+{symbol}\s+` only match standalone declarations (`const Foo = ...`). Go commonly uses grouped syntax:
   ```go
   const (
       MaxRetries = 3
       Timeout    = 30
   )
   ```
   Here `MaxRetries` doesn't start with `const` — it won't match. This is a coverage gap for a common Go idiom.

3. **Multi-line import blocks**. `import_line_prefixes=["import"]` will match `import "fmt"` and the opening `import (`, but individual package lines inside a grouped import block (`"fmt"`, `"os"`) won't match. This depends on how `matches_import` is consumed downstream — if callers assume every import line matches, they'll miss most imports in real Go files. (Go rarely uses single-line imports.)

4. **No tests exist** for any language profile (not just Go). The observation data confirms zero test files.

The func pattern is well-crafted — the optional receiver group `(\(\s*\w+\s+\*?\w+\s*\)\s+)?` handles both value and pointer receivers, and `[\[(]` captures generic functions. `module_name_from_path` falls through to `os.path.basename(name)` which is reasonable for Go.

### ftl_code_expert/language.py (LANGUAGE_REGISTRY addition)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `"go": GO` entry correctly wires the profile into the registry. `detect_language()` at line 160 already checks `LANGUAGE_REGISTRY` after finding `go.mod` via `_CONFIG_TO_LANGUAGE`, so this completes the integration path. `get_grep_include_args` and `extract_symbol_with_profile` will work correctly with the Go profile.

### Self-Review
**Limitations:** Could not execute the regex patterns to verify edge cases (permission denied for python3 execution). Reviewed them by reading only. No test files exist in the project to check for breakage. Could not verify how `matches_import` is consumed downstream to assess the real impact of the multi-line import gap.

### Feature Requests
- Include downstream callers of methods like `matches_import()` in observations so reviewers can assess whether a limitation matters in practice
- Run regex patterns against sample inputs automatically and include results in observations
- Flag when a new language profile introduces the first use of a pre-existing code path limitation (like the backtick raw string gap in `_extract_symbol_brace`)

## gemini [CONCERN]

### ftl_code_expert/language.py
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

The addition of the Go language profile is a great step, but there are multiple correctness, integration, and testing concerns:

1. **Integration Gap (`_CONFIG_TO_LANGUAGE`)**:
   The profile defines `config_files=["go.mod"]`, but `"go.mod": "go"` has not been added to `_CONFIG_TO_LANGUAGE` (which immediately follows `LANGUAGE_REGISTRY`). Any automatic language detection based on project configuration files will fail to recognize Go projects.

2. **Go Generics Support on Receivers**:
   The receiver pattern `r"(\(\s*\w+\s+\*?\w+\s*\)\s+)?"` in `func` fails to match methods defined on generic types (e.g., `func (r *MyStruct[T]) MyMethod()`) because `\*?\w+` does not match the type parameter bracket characters (`[` and `]`). Unnamed receivers (e.g., `func (*MyType) MyMethod()`) will also fail to match because the pattern expects both a receiver name and a receiver type separated by whitespace.

3. **Go Generics Support on Types**:
   The pattern `r"^type\s+{symbol}\s+"` will miss generic type definitions (e.g., `type MyContainer[T any] struct`) because there is typically no space between the type name and the generic bracket. Replacing the trailing `\s+` with `\b` or `(?:\s+|\[)` would solve this.

4. **Variables and Constants Spacing**:
   The patterns `r"^var\s+{symbol}\s+"` and `r"^const\s+{symbol}\s+"` require a trailing space, which will fail to match valid compact declarations like `var x=1` or `const C=2`. Using `\b` instead of the trailing `\s+` is much more robust.

5. **No Test Coverage**:
   The profile is entirely untested. Unit tests should be added to verify these regular expressions against standard, generic, and edge-case Go declarations.

### Self-Review
**Limitations:** - Could not view the full structure of `_CONFIG_TO_LANGUAGE` or how other language profiles (e.g., Rust/Python) are tested in the codebase due to the absence of the test files and complete helper definitions in the provided context.
- Was unable to run the workspace tests to verify compatibility or existing test patterns due to tool execution policy restrictions.

### Feature Requests
- Include the complete file content of modified modules (or at least larger class/variable context) to verify adjacent dictionaries and mappings.
- Provide the corresponding unit test files automatically alongside the implementation files to ease verification of test coverage.
