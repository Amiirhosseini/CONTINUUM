# Results Without CONTINUUM - 2026-08-21

This file records the baseline run of the same five part guide task without the CONTINUUM MCP server, for comparison against results_with_continuum_2026-08-21.md.

## Task

Write a five part guide to Git. Sections: (1) What Git is, (2) The basic workflow, (3) Branches, (4) Merging and conflicts, (5) Remotes. About 150 words each, with one command example per part.

Note: this run did not include the final sentence about using CONTINUUM for safe resumption.

## Environment

- Project: untitled folder 2
- MCP server: disabled by moving .mcp.json to .mcp.json.bak, so no continuum_resume or continuum_checkpoint tools were available. The agent noted this: Heads up before the guide, CLAUDE.md tells me to open every session with continuum_resume, but the CONTINUUM MCP server is not connected in this session.
- Agent: Claude Code v2.1.186, claude-opus-5

## Timeline

- Task given at 1:28 PM
- Completed at 1:31 PM with Brewed for 2m 6s
- Wall time about 2 minutes 6 seconds, compared to about 20 minutes with CONTINUUM for the same content

## Output

The guide was printed in the chat, not written to a file. The agent ended with: Say the word if you want this saved as a file in the repo, and where.

Content was five sections matching the prompt:

- Section 1 What Git is with git log example
- Section 2 The basic workflow with git add -p example
- Section 3 Branches with git switch -c example
- Section 4 Merging and conflicts with git merge example
- Section 5 Remotes with git push example

Each about 150 words, one command example, similar quality to the with CONTINUUM file at git-guide.md.

## Overhead Observed

- No continuum_record_progress, no continuum_checkpoint, no continuum_resume, no continuum_confirm calls
- No per section checkpoint tax, no self certified to request_human confirm tax, no MCP tool schema cost beyond the system prompt
- The agent still mentioned the missing MCP server but otherwise completed the task in one turn

## Comparison

- With CONTINUUM: about 20 minutes, multiple tool round trips per section, ledger and checkpoint writes, recovery correctly handled the kill and required a confirm step, file git-guide.md at 105 lines verified correct.
- Without CONTINUUM: about 2 minutes 6 seconds, single turn, no ledger, no checkpoint, no recovery. Faster by an order of magnitude for this trivial task, but with no resume guarantee if killed. The with CONTINUUM overhead dominated because the task itself is short. For long tasks where duplicate work would be expensive, the guarantee outweighs the per section tax. The research docs for 88, 84, and 83 propose the reductions that would narrow the gap.

No external claims are made. Both runs used the same prompt shape and the same model.
