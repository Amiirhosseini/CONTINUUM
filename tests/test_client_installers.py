"""Client installers beyond Claude Code (issue #209).

Gemini CLI and Codex CLI expose hook surfaces with the same stdin contract
(tool_name + tool_input JSON) but different settings layouts, event names
and matchers. Wiring is data-driven from CLIENT_PROFILES; these tests pin
each profile's installed shape, idempotency, removal, and the Codex feature
flag hint.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from continuum.cli import ExitCode, main
from continuum.clienthooks import CLIENT_PROFILES


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


import io  # noqa: E402


@pytest.mark.parametrize("client", ("claude-code", "gemini", "codex"))
def test_install_writes_the_profiled_shape(tmp_path: Path, client: str) -> None:
    profile = CLIENT_PROFILES[client]
    settings = tmp_path / "settings.json"

    code, out, err = run("--json", "hooks", "install", client, "--settings", str(settings))
    assert code == ExitCode.OK, err

    data = json.loads(settings.read_text())
    hooks_obj = data["hooks"]
    post = hooks_obj[profile["post_event"]]
    assert len(post) == 1
    assert post[0]["matcher"] == profile["write_matcher"]
    command = post[0]["hooks"][0]["command"]
    assert command.split()[-1] == "observe"

    payload = json.loads(out)
    assert payload["hooks"][0]["event"] == profile["post_event"]
    assert payload["settings"] == str(settings)


@pytest.mark.parametrize("client", ("claude-code", "gemini", "codex"))
def test_install_is_idempotent_per_client(tmp_path: Path, client: str) -> None:
    settings = tmp_path / "settings.json"
    for _ in range(2):
        code, _, err = run("--json", "hooks", "install", client, "--settings", str(settings))
        assert code == ExitCode.OK, err
    data = json.loads(settings.read_text())
    event = CLIENT_PROFILES[client]["post_event"]
    assert len(data["hooks"][event]) == 1


def test_gemini_gate_uses_before_tool(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    code, out, _ = run(
        "--json", "hooks", "install", "gemini", "--with-gate", "--settings", str(settings)
    )
    assert code == ExitCode.OK
    data = json.loads(settings.read_text())
    assert data["hooks"]["AfterTool"][0]["matcher"] == "write_file|replace"
    before = data["hooks"]["BeforeTool"]
    assert before[0]["matcher"] == ".*"
    assert before[0]["hooks"][0]["command"].split()[-1] == "gate"


def test_remove_cleans_each_client(tmp_path: Path) -> None:
    for client in ("claude-code", "gemini", "codex"):
        settings = tmp_path / f"{client}.json"
        run("--json", "hooks", "install", client, "--with-gate", "--settings", str(settings))
        code, out, _ = run("--json", "hooks", "remove", client, "--settings", str(settings))
        assert code == ExitCode.OK
        assert json.loads(out)["removed"] is True
        data = json.loads(settings.read_text())
        # No continuum entries survive; unrelated content would.
        assert "hooks" not in data or all(
            not group.get("hooks") for group in data.get("hooks", {}).values()
        )


def test_codex_install_hints_when_feature_flag_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    settings = tmp_path / "settings.json"
    code, out, _ = run("--json", "hooks", "install", "codex", "--settings", str(settings))
    assert code == ExitCode.OK
    payload = json.loads(out)
    assert "codex_hooks" in payload["feature_flag_hint"]


def test_codex_install_stays_silent_when_flag_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    codex_dir = fake_home / ".codex"
    codex_dir.mkdir(parents=True)
    (codex_dir / "config.toml").write_text("[features]\ncodex_hooks = true\n")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    settings = tmp_path / "settings.json"
    code, out, _ = run("--json", "hooks", "install", "codex", "--settings", str(settings))
    assert code == ExitCode.OK
    assert "feature_flag_hint" not in json.loads(out)


def test_gemini_payload_shape_matches_the_observation_contract() -> None:
    """Gemini AfterTool payloads carry the same tool_name/tool_input fields;
    prove `continuum observe` accepts one verbatim through the real CLI."""
    import tempfile

    project = Path(tempfile.mkdtemp())
    subprocess.run(["python", "-m", "continuum.cli", "init"], cwd=project, capture_output=True)
    subprocess.run(
        ["python", "-m", "continuum.cli", "start", "g", "--goal", "gemini"],
        cwd=project,
        capture_output=True,
    )
    artifact = project / "out.txt"
    artifact.write_text("written by gemini")
    gemini_payload = json.dumps(
        {
            "hook_event_name": "AfterTool",
            "tool_name": "write_file",
            "tool_input": {"file_path": str(artifact), "content": "x"},
        }
    )
    result = subprocess.run(
        ["python", "-m", "continuum.cli", "--db", str(project / "continuum.db"), "observe"],
        input=gemini_payload,
        capture_output=True,
        text=True,
        cwd=project,
    )
    assert result.returncode == ExitCode.OK, result.stderr


@pytest.mark.parametrize("client", ("claude-code", "gemini", "codex"))
def test_default_settings_path_comes_from_the_profile(
    tmp_path: Path, client: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caught live: an explicit --settings was tested everywhere, so a
    hardcoded CLI default silently sent every client's hooks to Claude
    Code's settings file. The default must come from the profile."""
    monkeypatch.chdir(tmp_path)
    code, _, err = run("--json", "hooks", "install", client)
    assert code == ExitCode.OK, err
    expected = CLIENT_PROFILES[client]["settings"]
    assert (tmp_path / expected).exists(), expected
