# Code Review Report

**Branch:** benthomasson/ftl-code-expert#16
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## Disagreements

The following changes have different verdicts across models:

- **ftl_code_expert/cli.py:_auto_gather_verify_observations** [LOW]: claude: CONCERN, gemini: PASS
- **ftl_code_expert/cli.py:verify** [LOW]: claude: CONCERN, gemini: PASS

## claude [CONCERN]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Bug fix — `reasons export` writes `network.json` directly, so the old `network_path.write_text(result.stdout)` was writing a status message into the file. Removing it is correct. The comment accurately documents the behavior, confirmed by the observation at `reasons_export_behavior`.

### ftl_code_expert/cli.py:_auto_gather_verify_observations
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Two issues: (1) `find_symbol` is imported at line 3075 but never used in this function — dead import. (2) The symbol extraction heuristic (`term[0].isupper() or "_" in term`) applied to belief ID segments is fragile. Belief IDs like `login-audit-always-success-info` yield terms like `login`, `audit`, `always` — none of which pass the uppercase/underscore filter, so `symbols` will be empty and the fallback grep on `terms[0]` fires. This is probably the common case, making the `find_usages` path rarely exercised. Not a bug per se, but the symbol extraction logic may be dead weight for most belief IDs.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean two-stage observe pattern: auto-gather seed context, then ask LLM what else it needs. Content truncation at 4000 chars is reasonable. The `display_obs` filtering to exclude `source_key` from the JSON dump avoids duplication in the prompt. `timeout` is correctly threaded through to `invoke()`.

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Mirrors the existing `_gather_confirmation_context` pattern. Error handling per-belief with stderr output is consistent with project conventions.

### ftl_code_expert/cli.py:verify
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The `--no-observe` flag and conditional branching are clean. Two concerns: (1) `_reasons_export()` is called unconditionally before network load, even on `--dry-run` — this is a side effect (writing files) on what the user expects to be a read-only operation. The dry-run check happens ~40 lines later. (2) The re-export adds latency to every `verify` invocation even when the network is already fresh. Consider gating the re-export behind a staleness check or skipping it on `--dry-run`.

### ftl_code_expert/prompts/verify.py:VERIFY_OBSERVE_PROMPT
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Prompt is well-structured with clear tool table, output format, and guidelines. The "3-8 observations" guidance is reasonable. The instruction "Do NOT verify the belief yet" is important to prevent the LLM from short-circuiting the observe step. Consistent with the existing `build_observe_prompt` pattern in `prompts/observe.py`.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Standard export addition. `VERIFY_OBSERVE_PROMPT` added to both import and `__all__`.

### Self-Review
**Limitations:** Could not verify `parse_observation_requests` handles the VERIFY_OBSERVE_PROMPT output format correctly (function body not in observations). Could not verify `_load_network` reads from the file that `_reasons_export` writes. The "related tests" in observations were all sympy false positives — no actual project tests were available to review.

### Feature Requests
- Filter out `.venv/` paths from related test discovery — all four "related tests" were sympy internals, providing zero signal and adding noise
- Include the body of functions that are called by new code but not in the diff (e.g., `parse_observation_requests`, `_load_network`) when they're key to correctness
- Flag unused imports automatically as part of observation gathering

## gemini [PASS]

### ftl_code_expert/cli.py:_reasons_export
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

This fixes a critical bug where `reasons export`'s stdout status message was written to `network.json`, thereby corrupting it. Since the `reasons export` command automatically writes its JSON payload directly to `network.json`, discarding stdout on success is correct and prevents corruption.

### ftl_code_expert/cli.py:_auto_gather_verify_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

This function efficiently pre-gathers local code context in parallel before any LLM involvement. The heuristics for symbol extraction from the belief ID (splitting on hyphens, filtering length > 3, identifying snake_case or PascalCase terms for `find_usages`, and falling back to `grep`) are well-designed, extremely safe against empty inputs, and run concurrently using `asyncio.gather(return_exceptions=True)`. Note that `find_symbol` is imported but not used inside the function, which is a minor cleanliness issue but does not affect correctness.

### ftl_code_expert/cli.py:_verify_belief_with_observations
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Implements a clean two-stage "observe" pattern. First, it uses `_auto_gather_verify_observations` to get basic file contents and symbol usages. Then, it queries the LLM using `VERIFY_OBSERVE_PROMPT` to find out what other observations are needed, executes those in parallel via `run_observations`, and builds a clean context block. It intelligently truncates the main source file to 4000 characters and filters out the main source file from the duplicate JSON block in `display_obs`. Crucially, it uses `json.dumps` with `default=str` to prevent crashes when encountering non-serializable objects (such as exception messages or Path objects).

### ftl_code_expert/cli.py:_gather_verify_contexts
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly coordinates parallel execution of `_verify_belief_with_observations` across a batch of beliefs using `asyncio.gather` with `return_exceptions=True`. It handles errors robustly by logging them to Click's stderr and falling back to a placeholder context string rather than failing the whole verification batch.

### ftl_code_expert/cli.py:verify
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Integrates the new observation-based context gathering loop into the existing click subcommand seamlessly. By default, it runs the advanced `_gather_verify_contexts` loop, while preserving the old simple behavior if `--no-observe` is supplied. Click option names with hyphens are automatically converted to snake_case parameters in Python (e.g. `no_observe`), and the signatures match perfectly. It also proactively runs `_reasons_export` to keep metadata in `network.json` fresh before verification.

### ftl_code_expert/prompts/verify.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Introduces `VERIFY_OBSERVE_PROMPT` which outlines clear tasks, available observation tools, guidelines, and an expected JSON output format for the LLM. It properly uses double curly braces (`{{` and `}}`) to escape the literal JSON format block, ensuring that calling `.format()` on the template string in Python will not raise a `KeyError`.

### ftl_code_expert/prompts/__init__.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Properly imports and registers `VERIFY_OBSERVE_PROMPT` in `__all__`, making it available cleanly to the rest of the package.

### Self-Review
**Limitations:** The codebase completely lacks any unit or integration tests for `ftl-code-expert` itself (the `*test*.py` files shown in the workspace are from external site-packages inside `.venv`), which prevented us from verifying any test coverage claims or running suite assertions.

### Feature Requests
- Flag when modified files have zero test coverage in the workspace to highlight testing risks earlier.
- Perform static analysis or simple linter checks (like pyright/flake8) on the code changes prior to presenting them for review to catch minor unused imports.
