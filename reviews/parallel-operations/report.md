# Code Review Report

**Branch:** parallel-operations
**Models:** claude, gemini
**Gate:** [CONCERN] CONCERN

## claude [CONCERN]

### ftl_code_expert/llm.py:invoke_concurrent
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean semaphore-bounded concurrency using `asyncio.gather` with `return_exceptions=True`. Return type `list[str | Exception]` is well-documented. Correctly delegates to existing `invoke()`. Both async and sync wrappers provided consistently with the existing pattern.

### ftl_code_expert/topics.py:pop_batch
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Simple and correct — iterates queue, marks up to `n` pending as done, saves once. Follows the same pattern as `pop_next`. Only concern would be if `n <= 0`, but the caller clamps `parallel` to `max(1, ...)` and `batch_size` is always `min(parallel, max_topics - explored)` where `explored < max_topics`, so `n` is always >= 1 at call sites.

### ftl_code_expert/cli.py:_prepare_file_topic
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

At line 882, `topic.kind` is mutated to `"repo"` before delegating to `_prepare_repo_topic`. This mutates the caller's Topic object. In the concurrent path (`_explore_topics_concurrent`), `_PREPARE_DISPATCH` dispatches based on `topic.kind` at call time, so the mutation happens during preparation (which is synchronous within the semaphore). Since `_prepare_file_topic` is called via the dispatch dict and the mutation happens before returning, the topic's kind is changed before the result tuple is constructed. The returned `source` from `_prepare_repo_topic` will be `"repo-overview"`, which is correct for that case. However, the mutation of the shared Topic object is a side effect that could surprise callers — the topic printed in progress output would show `kind=file` but the result would be a repo exploration. This existed in the original code too, so it's pre-existing.

### ftl_code_expert/cli.py:_prepare_function_topic, _prepare_repo_topic, _prepare_diff_topic
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean extraction of prompt preparation from the old `_run_*` functions. Each returns a consistent `(prompt, entry_name, entry_title, source)` tuple or `None`. Logic is preserved from the originals. The `_PREPARE_DISPATCH` dict at line 1004 correctly maps all non-general kinds.

### ftl_code_expert/cli.py:_finalize_topic
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Simple consolidation of post-processing (create entry, enqueue topics, report beliefs, emit). Eliminates duplication across all `_run_*` functions.

### ftl_code_expert/cli.py:_explore_topics_concurrent
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Two concerns:

1. **Double semaphore for general topics**: At line 1141, the entire `_do_topic` body runs under the semaphore. For general topics, `_run_general_topic_async` calls `invoke()` twice (observe + explain) plus `run_observations()`. This means one semaphore slot is held for the entire multi-step pipeline, which is correct for bounding subprocess count — but it means general topics hold a slot much longer than simple topics, potentially starving the pipeline. This is an acceptable trade-off but worth noting.

2. **`_prepare_*` functions do synchronous I/O** (file reads, `get_imports`, `get_repo_structure`, `extract_symbol`) inside the async semaphore. These are blocking calls that won't yield to the event loop. Since `invoke()` uses `asyncio.create_subprocess_exec` which does yield, the synchronous I/O between the sem acquire and the first `await` won't cause a deadlock, but it does mean the event loop is blocked during preparation. In practice this is likely fine since file I/O is fast, but it's not textbook async.

### ftl_code_expert/cli.py:_run_general_topic_async
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Faithful async conversion of the old `_run_general_topic`'s observe-then-explain pipeline. Drops the progress logging that the sync version had (observation counts, failure reporting), which is acceptable in the concurrent context where interleaved output would be confusing. Returns `(result, entry_name, entry_title, source)` consistent with the concurrent result protocol.

### ftl_code_expert/cli.py:explore (parallel path)
**Verdict:** CONCERN
**Correctness:** QUESTIONABLE
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

At line 770, the parallel path checks `parallel > 1 and len(topics_only) > 1`. When `--parallel 1` (or default with a single topic), it falls through to the sequential path. This is correct. However, the `check_model_available` call at line 762 is only in the explore command's pick path — the sequential `_run_*` functions no longer check model availability themselves (that check was removed). This is fine because `explore()` checks it upfront. But note that if `_run_file_topic` etc. are ever called from outside `explore()`, the model check would be missing. Currently they're only called from `explore` and `_explore_loop`, both of which check upfront, so this is safe.

### ftl_code_expert/cli.py:_explore_loop (batch path)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Correctly uses `pop_batch` to grab a batch sized to `min(parallel, remaining_budget)`. Progress counter `explored` is incremented by `len(batch)` after processing, so it correctly tracks total explored. The model availability check is done once upfront at line 822. The fallback to sequential processing when `parallel == 1` or `len(batch) == 1` is correct.

### ftl_code_expert/cli.py:propose_beliefs (parallel path)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Clean refactor — prompts are built in one loop, then `invoke_concurrent_sync` processes them all with bounded parallelism. Results are iterated with index tracking for error reporting. The `isinstance(result, Exception)` check correctly handles per-batch failures without aborting. The `continue` from the old `except` block is replaced by the `else` branch that appends to `all_proposals`, which is equivalent.

### ftl_code_expert/cli.py:review_proposals (parallel path)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Same pattern as propose_beliefs — prompts built in a loop, then concurrent invocation. Error handling matches. The `all_decisions.update(decisions)` in the success branch preserves the merge behavior from the original sequential loop.

### ftl_code_expert/cli.py:cli (global option)
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

`--parallel/-j` option with default 3, clamped to `max(1, parallel)` at line 238. Stored in `ctx.obj["parallel"]` and consumed by explore, propose_beliefs, and review_proposals. Clean integration.

### Self-Review
**Limitations:** Could not verify whether `run_observations` is already async-safe (it's called from `_run_general_topic_async` with `await`, suggesting it is). Could not see the full `propose_beliefs` and `review_proposals` commands to verify no other callers of the old sequential pattern were missed. No test files exist to check for breakage.

### Feature Requests
- Include the full function body for all modified functions, not just the diff hunks — the `explore()` function is large and context around the pick/skip logic was important to verify
- Show import graph: which functions call the modified functions, to verify all callers are updated
- Flag projects with zero test coverage upfront so the reviewer knows test verification is impossible

## gemini [PASS]

### README.md
VERDICT: PASS
CORRECTNESS: VALID
SPEC_COMPLIANCE: N/A
ISSUE_COMPLIANCE: N/A
BELIEF_COMPLIANCE: CONSISTENT
TEST_COVERAGE: N/A
INTEGRATION: WIRED
REASONING: The documentation correctly adds the new `--parallel` / `-j` flag and its default value (3) to the global options table.
---

### ftl_code_expert/llm.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

Implementation of `invoke_concurrent` and its synchronous wrapper uses `asyncio.Semaphore` to correctly bound parallelism. The use of `return_exceptions=True` in `asyncio.gather` is a good practice here, allowing the caller to handle individual failures without failing the entire batch.

### ftl_code_expert/topics.py:pop_batch
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

`pop_batch` correctly extends the existing queue management logic to handle multiple topics. It follows the existing pattern of marking topics as "done" in the queue before returning them.

### ftl_code_expert/cli.py
**Verdict:** PASS
**Correctness:** VALID
**Spec Compliance:** N/A
**Test Coverage:** UNTESTED
**Integration:** WIRED

The refactoring of topic execution into `_prepare`, `_run`, and `_finalize` stages is well-executed. This separation allows the same logic to be used for both serial and concurrent execution. The `explore` command and `_explore_loop` now correctly leverage `asyncio` for parallel processing when requested. The `propose-beliefs` and `review-proposals` commands also benefit from the new parallel `invoke` capabilities, which should significantly improve performance for large codebases.

One observation: Topics are marked as "done" in the queue as soon as they are popped. If the process crashes during a parallel run, all topics in that batch will be lost (marked done but not documented). This is consistent with the existing serial behavior but affects more topics at once when running in parallel.

### Self-Review
**Limitations:** I could not verify the thread-safety of `run_observations` as `ftl_code_expert/observations.py` was not provided. However, since observations are typically read-only operations on the filesystem, concurrent execution is likely safe. No test files were included in the diff, so I cannot verify if the new concurrency logic is covered by automated tests.
