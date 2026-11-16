# Code Review Report

**Branch:** benthomasson/ftl-code-expert#28
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/language.py (GO profile addition)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The Go language profile is correctly structured and properly wired into both `LANGUAGE_REGISTRY` and `_CONFIG_TO_LANGUAGE` (the `"go.mod": "go"` entry already existed). The `detect_language` function will correctly detect Go repos via `go.mod`. Two concerns:

1. **Catch-all pattern overbroad** (line 121): `r"^{symbol}\s*[=\s]"` will match any line where the symbol appears at the start (after lstrip) followed by whitespace or `=`. Since `_extract_symbol_brace` uses `stripped = line.lstrip()` before pattern matching, this can match indented lines inside function bodies or grouped declarations, leading to false-positive definition matches and incorrect scope extraction. The other language profiles (Python, C++, Rust) don't have an equivalently broad catch-all. Consider removing this pattern or constraining it to only match assignment with `=` (i.e., `r"^{symbol}\s*="`).

2. **import_line_prefixes only catches `import` keyword** (line 124): Go's grouped import syntax means individual import lines (`"fmt"`, `"os"`) inside `import (...)` blocks won't be identified as imports. This is a minor limitation — the `import` keyword line itself is caught, which is likely sufficient for the tool's purposes.

3. **No test coverage**: The project has no test files at all, so this is consistent with the existing codebase, but the definition patterns (especially the complex generic-receiver regex) would benefit from unit tests.

The integration is complete — `GO` is in `LANGUAGE_REGISTRY`, `go.mod` maps to `"go"` in `_CONFIG_TO_LANGUAGE`, scope extraction uses `"brace"` style which correctly handles Go's `{}` blocks.

### Self-Review
**Limitations:** Could not execute Python to verify regex patterns against real Go constructs (permission denied). Analysis of pattern correctness is based on manual regex tracing. Could not verify whether the `module_name_from_path` output is meaningful for Go's package system (Go packages are directory-based, not file-based). No test files exist in the project to check for regressions.

### Feature Requests
- Include the full `LanguageProfile` dataclass definition in observations when reviewing a new profile addition, so field semantics can be verified without reading the whole file
- Run regex patterns against sample inputs as part of the observation phase to verify correctness empirically
- Flag when a project has zero test coverage so the reviewer can weight the UNTESTED verdict appropriately (known gap vs. regression)

## gemini [CONCERN]

### ftl_code_expert/language.py
**Verdict:** CONCERN
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** PARTIAL

- The `GO` `LanguageProfile` definition is syntactically and structurally correct. The `definition_patterns` are robust, including support for Go method receivers, generics, packages, and typical top-level declarations.
- However, integration is incomplete: `_CONFIG_TO_LANGUAGE` in `ftl_code_expert/language.py` was not updated to map `"go.mod": "go"`. As a result, automatic configuration-based language detection will fail for Go repositories.
- The changes are completely untested. There are no tests verifying the Go profile, its config file registration, or its regex-based definition pattern matching.

### Self-Review
**Limitations:** - Could not execute pytest or view other source files via shell commands due to environment-level tool execution policy restrictions.
- Verified usages and test coverage relying on the provided observation results.

### Feature Requests
- Ensure full file context and test execution reports are automatically included in observations when shell execution commands are restricted by environment policies.
