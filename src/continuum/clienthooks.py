"""Host-side observation hooks for coding CLIs (issue #207).

CONTINUUM's recovery guarantees depend on the agent voluntarily calling
``continuum_record_progress`` / ``continuum_checkpoint``, which leaves an
unbounded window in which real work exists on disk but the event log knows
nothing about it. A kill inside that window hands the next session a contract
that understates what actually happened (observed live on 2026-08-22: a Claude
Code session wrote ``tic-tac-toe.html`` and was killed before any recording
call, so resume reported progress 0/1 with zero checkpoints).

The durable-execution literature (Temporal, Restate, LangGraph checkpointers,
the Crab sandbox paper) closes this by making recording mandatory at the
runtime layer rather than voluntary at the model layer. CONTINUUM cannot wrap
an external CLI's agent loop, but Claude Code exposes something nearly as
good: PostToolUse hooks fire after every Write/Edit completion, outside the
model's control. This module turns those hook events into durable evidence.

Two pieces live here:

- :func:`observe_event_payload` extracts the durable facts (tool, path, byte
  count, content digest) from one hook payload.
- :func:`install_claude_code_hook` / :func:`remove_claude_code_hook` manage the
  entry in ``.claude/settings.json`` that wires file-mutating tool completions
  to ``continuum observe``.

Provenance note: an observation is recorded ``Origin.EXTERNAL_AGENT``
deliberately. The fact it captures ("this tool call completed") is asserted by
the client harness, not verified by CONTINUUM, so it must never launder
self-reported state into trusted state. What it buys is independent *evidence*
a resumed session can weigh against the log.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_MATCHER",
    "observe_event_payload",
    "observe_command",
    "install_claude_code_hook",
    "remove_claude_code_hook",
]

#: Tool names whose completions carry a file path worth observing. Kept as one
#: matcher expression so the installed settings stay a single entry.
DEFAULT_MATCHER = "Write|Edit|MultiEdit|NotebookEdit"

#: Keys of ``tool_input`` that hold the primary file path, in priority order.
_PATH_KEYS = ("file_path", "notebook_path")


def observe_event_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the durable facts from one PostToolUse payload.

    Returns a JSON-native dict suitable for a ``TOOL_COMPLETED`` event:
    ``{"tool": ..., "path": ..., "bytes": ..., "sha256": ...}``. The path keys
    are read from the hook's own report; size and digest come from reading the
    file *now*, because the observation is only useful to recovery if it
    describes what is actually on disk. A missing or unreadable file records
    the path without size or digest: the absence is itself evidence, and
    guessing values would poison it.
    """
    tool = str(raw.get("tool_name") or "unknown")
    payload: dict[str, Any] = {"tool": tool}

    tool_input = raw.get("tool_input")
    path: str | None = None
    if isinstance(tool_input, Mapping):
        for key in _PATH_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                path = value
                break
    if path is None:
        return payload

    payload["path"] = path
    # Read in bounded chunks rather than whole: the hook runs after every
    # file-mutating tool call, and a multi-gigabyte artifact must not be held
    # in memory just to hash it. Size and digest are only recorded after the
    # read completes, so a mid-read failure records neither.
    digest = hashlib.sha256()
    size = 0
    try:
        with Path(path).open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
    except OSError:
        return payload
    payload["bytes"] = size
    payload["sha256"] = digest.hexdigest()
    return payload


def observe_command(*, db: str | None = None) -> str:
    """Build the shell command the hook will run.

    The absolute path of the ``continuum`` executable is resolved at install
    time and baked into the settings: hook processes may not inherit the PATH
    that found the binary originally. When no executable is on PATH (editable
    installs inside environments that expose only the interpreter), the
    interpreter-plus-module form is used instead. An explicit ``db`` is baked
    in too, since the default resolves relative to the working directory and
    hook processes run with the project root as cwd.
    """
    executable = shutil.which("continuum")
    parts = [executable] if executable else [sys.executable, "-m", "continuum.cli"]
    if db:
        parts += ["--db", db]
    parts.append("observe")
    return " ".join(shlex.quote(part) for part in parts)


def _is_observe_hook(hook: Mapping[str, Any]) -> bool:
    """True when a hook entry is one this module would have installed.

    Deliberately narrow: a command that merely ends in ``observe`` could
    belong to an unrelated tool, and treating it as ours would let install
    repoint or remove delete someone else's configuration. Two shapes are
    recognised, matching :func:`observe_command` exactly: a resolved
    ``continuum`` executable path (its stem is ``continuum``), and the
    interpreter fallback form ``<python> -m continuum.cli ... observe``.
    """
    command = hook.get("command")
    if not isinstance(command, str):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) < 2 or tokens[-1] != "observe":
        return False
    if Path(tokens[0]).stem == "continuum":
        return True
    return tokens[1] == "-m" and len(tokens) >= 4 and tokens[2] == "continuum.cli"


def install_claude_code_hook(
    settings_path: Path,
    command: str,
    *,
    matcher: str = DEFAULT_MATCHER,
) -> str:
    """Add the observe hook to a Claude Code settings file.

    Existing settings are preserved; only the ``hooks.PostToolUse`` list gains
    (or updates) our single entry. Returns ``"installed"`` when the entry was
    added, ``"updated"`` when an existing observe entry pointed somewhere else
    (a moved virtualenv, say) and was repointed, ``"present"`` when nothing
    needed to change.

    A settings file that exists but is unreadable raises rather than being
    overwritten: a file someone edited by hand is a statement of intent, and
    silently replacing it would destroy work to save a typo.
    """
    if settings_path.exists():
        try:
            settings: dict[str, Any] = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{settings_path} is not valid JSON ({exc}); refusing to edit it"
            ) from exc
        if not isinstance(settings, dict):
            raise ValueError(f"{settings_path} does not contain a JSON object")
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{settings_path}: 'hooks' is not an object")

    post_tool_use: list[Any] = hooks.setdefault("PostToolUse", [])
    if not isinstance(post_tool_use, list):
        raise ValueError(f"{settings_path}: 'hooks.PostToolUse' is not a list")

    status = "installed"
    entry_found = False
    for group in post_tool_use:
        if not isinstance(group, dict) or group.get("matcher") != matcher:
            continue
        entries = group.get("hooks")
        if not isinstance(entries, list):
            continue
        for hook in entries:
            if isinstance(hook, dict) and _is_observe_hook(hook):
                entry_found = True
                if hook.get("command") != command:
                    hook["command"] = command
                    status = "updated"
                else:
                    status = "present"

    if not entry_found:
        post_tool_use.append(
            {
                "matcher": matcher,
                "hooks": [{"type": "command", "command": command}],
            }
        )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return status


def remove_claude_code_hook(settings_path: Path, *, matcher: str = DEFAULT_MATCHER) -> bool:
    """Remove the observe hook. Returns True when anything was removed.

    Only entries this module's shape recognises are touched: a hand-written
    PostToolUse entry pointing elsewhere survives untouched, as does every
    other key in the file.
    """
    if not settings_path.exists():
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{settings_path} is not valid JSON ({exc}); refusing to edit it") from exc
    if not isinstance(settings, dict):
        return False

    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    post_tool_use = hooks.get("PostToolUse")
    if not isinstance(post_tool_use, list):
        return False

    removed = False
    kept_groups: list[Any] = []
    for group in post_tool_use:
        if not (
            isinstance(group, dict)
            and group.get("matcher") == matcher
            and isinstance(group.get("hooks"), list)
        ):
            kept_groups.append(group)
            continue
        # Drop only the hook entries this module recognises as its own. A
        # matcher group can hold unrelated user hooks alongside ours; removing
        # the whole group would delete configuration this command never
        # installed.
        kept_hooks = [
            h
            for h in group["hooks"]
            if not (isinstance(h, dict) and _is_observe_hook(h))
        ]
        if len(kept_hooks) != len(group["hooks"]):
            removed = True
        if not kept_hooks:
            continue
        group["hooks"] = kept_hooks
        kept_groups.append(group)

    if not removed:
        return False

    if kept_groups:
        hooks["PostToolUse"] = kept_groups
    else:
        del hooks["PostToolUse"]
        if not hooks:
            del settings["hooks"]

    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return True
