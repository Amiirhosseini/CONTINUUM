import json

from continuum.adapters import AdapterAction, AdapterResult, GenericAgentAdapter, run_action
from continuum.models import Run
from continuum.storage import SQLiteStorage


def _adapter() -> GenericAgentAdapter:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="adapter_action"))
    return GenericAgentAdapter(storage)


def test_adapter_action_serializes() -> None:
    action = AdapterAction(name="pkg.install", params={"ver": 1}, dep_scope="numpy")
    payload = json.loads(json.dumps(action.to_json()))
    assert payload == {"name": "pkg.install", "params": {"ver": 1}, "dep_scope": "numpy", "action_id": None}
    restored = AdapterAction(**payload)
    assert restored == action


def test_adapter_emits_action() -> None:
    adapter = _adapter()
    result = run_action(adapter, "run_1", AdapterAction(name="pkg.install", params={"x": 1}, dep_scope="numpy"), lambda: 7)
    assert isinstance(result, AdapterResult)
    assert result.status == "completed"
    assert result.output == 7


def test_adapter_action_failure_is_captured() -> None:
    adapter = _adapter()
    result = run_action(
        adapter, "run_1", AdapterAction(name="boom", params={}), lambda: (_ for _ in ()).throw(RuntimeError("nope"))
    )
    assert result.status == "failed"
    assert "RuntimeError" in result.error
