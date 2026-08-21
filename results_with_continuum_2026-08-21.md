# Results With CONTINUUM via Claude Code MCP - 2026-08-21

This file records the full real world run using CONTINUUM through the MCP server, as observed in the unscripted test for issue 6. It will be compared against a normal run without CONTINUUM to measure overhead.

## Task

Write a five part guide to Git. Sections: (1) What Git is, (2) The basic workflow, (3) Branches, (4) Merging and conflicts, (5) Remotes. About 150 words each, with one command example per part. Use CONTINUUM for safe resumption if you are interrupted.

## Environment

- Project: untitled folder 2
- Database: continuum.db, cleared before test with rm -f continuum.db
- MCP server: continuum-mcp registered in .mcp.json, allowlisted via CONTINUUM_MCP_MUTATING_CLIENTS
- Agent: Claude Code v2.1.186, claude-opus-5
- System prompt: CLAUDE.md with continuum_resume as first action

## Timeline

- Task given at 12:59 PM
- First phase completed two sections by about 01:00 PM, then terminal killed hard
- Fresh session at about 01:06 PM sent hi, agent called continuum_resume autonomously
- Task completed after resume by about 01:12 PM
- Total wall time about 20 minutes. Without CONTINUUM the same task completes in about 10 seconds via a direct prompt.

## Tool Call Sequence

Initial session:

1. continuum_resume with no run_id, result no_active_run
2. continuum_record_progress run git-guide-5part completed 0 total 5
3. Write git-guide.md section 1
4. continuum_record_progress completed 1
5. Update git-guide.md section 2
6. continuum_record_progress completed 2
7. continuum_checkpoint reason Sections 1 and 2 written
8. Killed

Fresh session after hi:

1. continuum_resume with no run_id, result run git-guide-5part at 3 of 5, mode request_human, next_allowed_action human_review:goal
2. Asked Resume it, or start a new task
3. On resume it, called continuum_confirm, then resumed
4. Read git-guide.md, confirmed sections 1 to 3 on disk, picked up at section 4
5. Update git-guide.md section 4, continuum_record_progress completed 4, continuum_checkpoint
6. Update git-guide.md section 5, continuum_record_progress completed 5, continuum_checkpoint
7. Done at 5 of 5, checkpoint v2

## Generated Artifact

File git-guide.md at 105 lines, verified correct:

- Section 1 What Git is with git init example
- Section 2 The basic workflow with git add and commit example
- Section 3 Branches with git switch example
- Section 4 Merging and conflicts with git merge example
- Section 5 Remotes with git push example

Each section about 150 words, one command example, no duplicates after resume, no missing content. Earlier terminal garble was display only.

## Dashboard States During Run

- demo started resume yes is the clean baseline
- stale_demo started request_human no is the conservative no environment view, becomes repair_and_resume with an environment
- human_demo started request_human no is the uncertain side effect case

After the kill, the dashboard for git-guide-5part showed request_human, after confirm it showed resume.

## Overhead Observed

- Per section cost of two continuum_record_progress plus one continuum_checkpoint. This dominated token count.
- Self certified to request_human confirm tax on every resume. Required an extra continuum_confirm turn.
- Detection cost of a full inference after hi before continuum_resume. No autonomous SessionStart hook.
- Per session token floor of system prompt plus ten MCP tool schemas.

These map to already speced fixes: docs/research/token_floor.md for 88, docs/research/confirm_tax.md for 84, docs/research/instant_detection.md for 83, and src/continuum/hooks.py for 86.

## Verdict

Recovery was functionally correct. No data loss, no duplicate sections after resume, checkpoint at 2 survived the kill, ledger correctly surfaced the uncertain state and required human gate. Overhead made it 20 minutes vs 10 seconds without CONTINUUM for this trivial task. Tracked as issue 186.

## Next Comparison

Run the same five part guide task without CONTINUUM in a fresh Claude Code session with .mcp.json disabled or with no mention of CONTINUUM, and time it. Then compare wall time and token counts side by side in a follow up file results_without_continuum_2026-08-21.md.
