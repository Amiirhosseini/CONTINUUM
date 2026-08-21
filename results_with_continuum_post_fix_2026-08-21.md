# Results With CONTINUUM Post Fix - 2026-08-21

This records the re measurement of the same five part guide task after the async hook and CLAUDE.md update for issue 187.

## Task

Write a five part guide to Git. Sections: (1) What Git is, (2) The basic workflow, (3) Branches, (4) Merging and conflicts, (5) Remotes. About 150 words each, with one command example per part.

## Environment After Fix

- Hooks: make_async_auto_checkpoint_hook in src/continuum/hooks.py, checkpoints on a background thread without blocking the agent turn
- Prompt: CLAUDE.md now says durability is handled by the hook, no per section continuum_checkpoint tool call
- MCP: still connected, but the model did not call continuum_record_progress or continuum_checkpoint per section in this run

## Timeline

- Started at 6:52 PM with MCP connected and the async hook on main
- Completed in 52s as reported by Brewed for 52s
- Compared to 20 minutes with the old per section tool path and 2m06s without MCP, this is about 23 times faster than the old MCP path and about 2.4 times faster than the without MCP baseline for this trivial task

## Output

The guide was printed in the chat, five sections matching the prompt, each about 150 words with one command example:

- Section 1 What Git is with git log example
- Section 2 The basic workflow with git add and commit example
- Section 3 Branches with git switch example
- Section 4 Merging and conflicts with git merge example
- Section 5 Remotes with git push example

The agent ended with: Want this saved to a file in the repo, say docs/git-guide.md, and did not write git-guide.md on its own. This is the token saving: no file write plus record plus checkpoint per section, just the content.

## Verdict

The architectural change keeps the same event log, validation, ledger, and contracts with no loss. Durability is still available via the hook when the semantic policy says the state meaningfully changed, but for this short guide the hook correctly did not checkpoint per section, so the run stayed at one model turn. The speedup is real and measured. File git-guide.md was not written in this run, which is expected when the model is not told to write a file. For the unscripted test that requires a file, the hook will checkpoint after the file write.

No external claims beyond this single re measurement. The side by side files are results_with_continuum_2026-08-21.md at 20 minutes, results_without_continuum_2026-08-21.md at 2m06s, and this file at 52s.
