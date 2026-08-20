"""Uniform action representation across adapters.

Different environment adapters (shell, in-process python, container, browser,
k8s, filesystem) ultimately do the same thing: perform a named operation with
some parameters, possibly scoped to a dependency. To recover any
agent-environment interaction uniformly, the recovery pipeline works with
:class:`AdapterAction` and :class:`AdapterResult` rather than each adapter's
native call shape. Adapters translate their own requests into an
``AdapterAction`` and return an ``AdapterResult``; nothing about the existing
adapter interfaces changes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from continuum.adapters.base import AgentAdapter


@dataclass(frozen=True)
class AdapterAction:
    """A single, dependency-aware operation an adapter can perform."""

    name: str
    params: Mapping[str, Any] = field(default_factory=dict)
    dep_scope: str | None = None
    action_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "params": dict(self.params),
            "dep_scope": self.dep_scope,
            "action_id": self.action_id,
        }


@dataclass
class AdapterResult:
    """The outcome of running an :class:`AdapterAction`."""

    status: str
    output: Any = None
    error: str | None = None


def run_action(
    adapter: AgentAdapter,
    run_id: str,
    action: AdapterAction,
    fn: Callable[[], Any],
) -> AdapterResult:
    """Execute ``action`` through ``adapter`` and return an ``AdapterResult``.

    Thin, uniform facade over :meth:`AgentAdapter.intercept_action`: the adapter
    still owns idempotency and side-effect safety; this only normalizes the
    request/response shape so the recovery pipeline treats every adapter the
    same. Failures are captured into ``AdapterResult`` instead of raised.
    """
    try:
        output = adapter.intercept_action(
            run_id,
            action.name,
            fn,
            arguments=dict(action.params),
            dep_scope=action.dep_scope,
        )
    except Exception as exc:  # adapter already recorded the attempt uncertain
        return AdapterResult(status="failed", error=f"{type(exc).__name__}: {exc}")
    return AdapterResult(status="completed", output=output)
