# Checkpoint

**Saved:** 2026-04-10 00:15
**Project:** /Users/ben/git/code-expert (and related repos)

## Task

Building expert tool family: project-expert, product-expert, and next market-expert and business-expert. Running them against agents-python (GitLab) and ftl2 (GitHub) repos.

## Status

### project-expert (`/Users/ben/git/project-expert`)
- [x] Added `derive` command with DERIVE/GATE support
- [x] Added backtick-stripping fix to derive parser
- [x] Added closed issue scanning (`--state closed`) with state-aware prompts
- [x] Added state suffix to entry naming to avoid collisions
- [x] Installed editable: `uv pip install -e . --python .venv/bin/python`

### product-expert (`/Users/ben/git/product-expert`)
- [x] Added backtick-stripping fix to derive parser
- [x] Installed editable in its own venv

### agents-python-project-expert (`/Users/ben/git/agents-python-project-expert`)
- [x] 79 entries from 67 explored topics
- [x] 649 beliefs proposed and accepted (607 IN, 0 OUT before derive)
- [x] 6 derive rounds → 63 derived beliefs, max depth 4+
- [x] 12 OUT gated beliefs documented in `entries/2026/04/09/gated-beliefs-out-summary.md`
- [x] 5 critical IN beliefs documented in `entries/2026/04/09/critical-derived-beliefs-summary.md`
- [x] AIA-542 Jira finding documented in `entries/2026/04/09/aia-542-is-jira-ticket.md`
- [ ] 9 backtick-wrapped node IDs in reasons.db from derive round 4 (cosmetic bug)

### agents-python-product-expert (`/Users/ben/git/agents-python-product-expert`)
- [x] 5 derive rounds → 77 derived beliefs, max depth 5
- [x] 19 OUT gated beliefs documented in `entries/2026/04/09/gated-beliefs-out-summary.md`
- [x] PDF rendered and opened

### ftl2-project-expert (`/Users/ben/git/ftl2-project-expert`)
- [x] Initialized, scanned open (3 issues) and closed (29 issues)
- [x] 35 beliefs accepted, 3 derive rounds → 33 derived, 57 IN, 11 OUT
- [x] README.md, CLAUDE.md, history.md, roadmap.md written
- [x] Pushed to GitHub (private): benthomasson/ftl2-project-expert
- [x] reasons.db gitignored

### ftl2-product-expert (`/Users/ben/git/ftl2-product-expert`)
- [x] Initialized, ingested ftl2 PRD (2 docs)
- [x] 21 beliefs accepted, 3 derive rounds → 29 derived, 42 IN, 8 OUT
- [x] README.md, CLAUDE.md written
- [x] Pushed to GitHub (private): benthomasson/ftl2-product-expert

### Key Findings
- project-expert is NOT inherently pessimistic — agents-python looks bad because it IS bad, ftl2 looks healthy because it IS healthy
- Closed issue scanning was the key fix — without it, the tool only sees problems
- The tool family: code-expert → project-expert → product-expert → market-expert → business-expert

## Key Files

- `/Users/ben/git/project-expert/ftl_project_expert/cli.py` — full CLI with derive, closed issue scanning, state-aware entry naming
- `/Users/ben/git/project-expert/ftl_project_expert/prompts/scan.py` — state-aware scan prompts (open/closed/all)
- `/Users/ben/git/project-expert/ftl_project_expert/prompts/derive.py` — project-focused derive prompt
- `/Users/ben/git/product-expert/ftl_product_expert/cli.py` — full CLI with backtick fix
- `/Users/ben/git/product-expert/ftl_product_expert/prompts/derive.py` — product-focused derive prompt

## Commands

```bash
# Run project-expert from editable install
cd /Users/ben/git/agents-python-project-expert
/Users/ben/git/project-expert/.venv/bin/project-expert derive --auto
/Users/ben/git/project-expert/.venv/bin/project-expert scan --state closed --all-pages

# Run product-expert from editable install
cd /Users/ben/git/ftl2-product-expert
/Users/ben/git/product-expert/.venv/bin/product-expert derive --auto

# Reinstall after edits
cd /Users/ben/git/project-expert && uv pip install -e . --python .venv/bin/python
cd /Users/ben/git/product-expert && uv pip install -e . --python .venv/bin/python
```

## Next Step

Build **market-expert** at `/Users/ben/git/market-expert` following the same pattern as project-expert and product-expert. Then build **business-expert**. These complete the expert tool family:
- market-expert: competitive landscape, TAM, positioning, customer segments, market trends
- business-expert: revenue model, pricing, unit economics, GTM, partnerships

Start by creating the repo structure, adapting prompts for market analysis, and adding an `ingest` command for competitive docs, analyst reports, and market data.

## Context

- User prefers `pip install -e .` / `uv pip install -e .` over `uv tool install` for development
- User bumps **minor** versions, not patch
- Shell resets to /Users/ben/git/code-expert after every command — must cd in same command
- Bus-factor-1 concerns are intentional — AI agents are being built to scale, not human hires
- The backtick bug in derive round 4 of agents-python-project-expert left 9 nodes with backtick-wrapped IDs in reasons.db — the parser fix prevents future occurrences but doesn't repair existing ones
- project-expert and product-expert repos have uncommitted changes (derive command, closed scanning, backtick fix) — should commit before building new tools
- AIA-542 is a Jira ticket at redhat.atlassian.net (restricted access) — the compliance authority lives in Jira while engineering work is in GitLab
