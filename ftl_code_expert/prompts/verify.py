"""Prompt template for verifying belief staleness against current source code."""

VERIFY_PROMPT = """\
You are verifying whether beliefs about a codebase still hold by examining the current source code.

For each belief below, I provide the belief text and relevant code context gathered from \
the current state of the repository.

Determine whether each belief is:
- **CONFIRMED** — the current code still supports this claim
- **STALE** — the code has changed and the belief no longer holds (explain what changed)
- **INCONCLUSIVE** — the provided code context is insufficient to determine either way

Return ONLY a JSON object mapping each belief ID to an object with "verdict" and "reason":

Example:
```json
{{"belief-1": {{"verdict": "CONFIRMED", "reason": "The handler still enforces zero-arg construction"}}, \
"belief-2": {{"verdict": "STALE", "reason": "LoginAttemptAuditHandler now covers failed logins with WARNING severity"}}, \
"belief-3": {{"verdict": "INCONCLUSIVE", "reason": "The relevant middleware file was not in the provided context"}}}}
```

## Beliefs to Verify

{beliefs}"""
