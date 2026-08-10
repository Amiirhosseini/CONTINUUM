from __future__ import annotations

from collections.abc import Iterator

import pytest

from continuum.actions import (
    ActionLedger,
    LedgerError,
    arguments_hash,
    idempotency_key,
)
from continuum.events import EventType
from continuum.models import ActionStatus, Run, UnknownSideEffect
from continuum.storage import SQLiteStorage


@pytest.fixture
def store() -> Iterator[SQLiteStorage]:
    storage = SQLiteStorage(":memory:")
    storage.create_run(Run(run_id="run_1", goal="g"))
    storage.append_event("run_1", EventType.RUN_STARTED, {"goal": "g"})
    yield storage
    storage.close()


@pytest.fixture
def ledger(store: SQLiteStorage) -> ActionLedger:
    return ActionLedger(store, "run_1")


ISSUE = {"title": "Bug report", "body": "It broke"}


# --- idempotency keys ------------------------------------------------------ #


def test_argument_order_does_not_change_the_key() -> None:
    a = idempotency_key("github.create_issue", {"title": "x", "body": "y"})
    b = idempotency_key("github.create_issue", {"body": "y", "title": "x"})
    assert a == b


def test_different_arguments_produce_different_keys() -> None:
    a = idempotency_key("github.create_issue", {"title": "x"})
    b = idempotency_key("github.create_issue", {"title": "y"})
    assert a != b


def test_different_action_types_produce_different_keys() -> None:
    assert idempotency_key("a.do", {"x": 1}) != idempotency_key("b.do", {"x": 1})


def test_scope_separates_runs() -> None:
    a = idempotency_key("send_email", {"to": "x"}, scope="run_1")
    b = idempotency_key("send_email", {"to": "x"}, scope="run_2")
    assert a != b
    assert idempotency_key("send_email", {"to": "x"}) != a


def test_volatile_fields_are_excluded_so_retries_deduplicate() -> None:
    """A retry counter must not make a retry look like a new action."""
    first = idempotency_key("call", {"payload": "p", "attempt": 1}, volatile=["attempt"])
    second = idempotency_key("call", {"payload": "p", "attempt": 2}, volatile=["attempt"])
    assert first == second

    without = idempotency_key("call", {"payload": "p", "attempt": 1})
    with_retry = idempotency_key("call", {"payload": "p", "attempt": 2})
    assert without != with_retry  # not excluded by default


def test_an_empty_action_type_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        idempotency_key("", {})


def test_unhashable_arguments_fail_loudly() -> None:
    """A key that varies between runs would silently disable deduplication."""
    with pytest.raises(TypeError):
        arguments_hash({"bad": {1, 2}})


# --- the basic protocol ---------------------------------------------------- #


def test_a_first_claim_is_fresh_and_recorded_as_started(ledger: ActionLedger) -> None:
    outcome = ledger.claim("github.create_issue", ISSUE)
    assert outcome.fresh
    assert outcome.action.status is ActionStatus.STARTED
    assert outcome.action.arguments_hash is not None


def test_completing_stores_the_external_id_and_result(ledger: ActionLedger) -> None:
    outcome = ledger.claim("github.create_issue", ISSUE)
    action = ledger.complete(outcome.key, external_id="481", result={"url": "/issues/481"})

    assert action.status is ActionStatus.COMPLETED
    assert action.external_id == "481"
    assert action.result_hash is not None
    assert action.completed_at is not None


def test_a_repeat_claim_returns_the_previous_result_instead_of_redoing_it(
    ledger: ActionLedger,
) -> None:
    """The headline behaviour: no duplicate GitHub issue."""
    first = ledger.claim("github.create_issue", ISSUE)
    ledger.complete(first.key, external_id="481", result={"url": "/issues/481"})

    second = ledger.claim("github.create_issue", ISSUE)
    assert not second.fresh
    assert second.already_completed
    assert second.external_id == "481"
    assert second.result == {"url": "/issues/481"}


def test_a_different_action_is_not_deduplicated(ledger: ActionLedger) -> None:
    first = ledger.claim("github.create_issue", ISSUE)
    ledger.complete(first.key, external_id="481")
    second = ledger.claim("github.create_issue", {"title": "Different", "body": "x"})
    assert second.fresh


def test_a_failed_action_may_be_retried(ledger: ActionLedger) -> None:
    first = ledger.claim("api.call", {"x": 1})
    ledger.fail(first.key, "500 from upstream")

    retry = ledger.claim("api.call", {"x": 1})
    assert retry.fresh
    assert retry.action.status is ActionStatus.STARTED


def test_a_compensated_action_may_be_performed_again(ledger: ActionLedger) -> None:
    first = ledger.claim("github.create_issue", ISSUE)
    ledger.complete(first.key, external_id="481")
    ledger.compensate(first.key, note="issue closed as duplicate", by="close_issue")

    again = ledger.claim("github.create_issue", ISSUE)
    assert again.fresh
    assert again.action.external_id is None  # the old effect is not reused


def test_completing_an_unknown_key_is_refused(ledger: ActionLedger) -> None:
    with pytest.raises(LedgerError, match="no action recorded"):
        ledger.complete("nonexistent", external_id="1")


# --- the crash gap: the reason this module exists -------------------------- #


def test_an_interrupted_action_refuses_to_silently_retry(ledger: ActionLedger) -> None:
    """Crash between claim and complete: the effect may or may not have landed."""
    ledger.claim("github.create_issue", ISSUE)  # never completed — process died

    with pytest.raises(UnknownSideEffect, match="may or may not have occurred"):
        ledger.claim("github.create_issue", ISSUE)


def test_an_interrupted_action_is_marked_uncertain_for_later(
    ledger: ActionLedger,
) -> None:
    ledger.claim("github.create_issue", ISSUE)
    with pytest.raises(UnknownSideEffect):
        ledger.claim("github.create_issue", ISSUE)

    uncertain = ledger.pending()
    assert len(uncertain) == 1
    assert uncertain[0].status is ActionStatus.UNKNOWN
    assert uncertain[0].side_effect_uncertain


def test_a_timeout_is_not_evidence_of_absence(ledger: ActionLedger) -> None:
    """A request that timed out may still have been processed."""
    outcome = ledger.claim("payment.charge", {"amount": 100})
    action = ledger.fail(outcome.key, "timeout after 30s", certain=False)

    assert action.status is ActionStatus.UNKNOWN
    assert action.side_effect_uncertain
    assert ledger.pending()

    with pytest.raises(UnknownSideEffect):
        ledger.claim("payment.charge", {"amount": 100})


def test_a_definite_failure_is_distinguished_from_a_timeout(
    ledger: ActionLedger,
) -> None:
    outcome = ledger.claim("payment.charge", {"amount": 100})
    action = ledger.fail(outcome.key, "400 invalid card", certain=True)

    assert action.status is ActionStatus.FAILED
    assert not action.side_effect_uncertain
    assert ledger.pending() == []


def test_an_inline_resolver_can_rescue_an_interrupted_action(
    ledger: ActionLedger,
) -> None:
    from continuum.actions.ledger import ActionOutcome

    ledger.claim("github.create_issue", ISSUE)

    def found_it(action: object) -> ActionOutcome:
        key = idempotency_key("github.create_issue", ISSUE, scope="run_1")
        recovered = ledger.reconcile(key, occurred=True, external_id="481")
        return ActionOutcome(key=key, action=recovered, fresh=False)

    outcome = ledger.claim("github.create_issue", ISSUE, on_unknown=found_it)
    assert not outcome.fresh
    assert outcome.external_id == "481"


# --- reconciliation -------------------------------------------------------- #


def test_reconciling_as_occurred_prevents_any_repeat(ledger: ActionLedger) -> None:
    outcome = ledger.claim("github.create_issue", ISSUE)
    ledger.fail(outcome.key, "connection lost", certain=False)

    ledger.reconcile(outcome.key, occurred=True, external_id="481", note="found via search")

    repeat = ledger.claim("github.create_issue", ISSUE)
    assert not repeat.fresh
    assert repeat.external_id == "481"
    assert ledger.pending() == []


def test_reconciling_as_not_occurred_permits_a_retry(ledger: ActionLedger) -> None:
    outcome = ledger.claim("github.create_issue", ISSUE)
    ledger.fail(outcome.key, "connection lost", certain=False)

    ledger.reconcile(outcome.key, occurred=False, note="no matching issue found")

    retry = ledger.claim("github.create_issue", ISSUE)
    assert retry.fresh


def test_reconciliation_is_recorded_as_its_own_event(
    ledger: ActionLedger, store: SQLiteStorage
) -> None:
    outcome = ledger.claim("api.call", {})
    ledger.reconcile(outcome.key, occurred=True, external_id="x")

    kinds = [e.type for e in store.read_events("run_1")]
    assert EventType.ACTION_RECONCILED in kinds


def test_flagging_for_review_escalates(ledger: ActionLedger) -> None:
    outcome = ledger.claim("payment.charge", {"amount": 100})
    action = ledger.flag_for_review(outcome.key, "cannot verify with provider")
    assert action.status is ActionStatus.REQUIRES_REVIEW


# --- durability ------------------------------------------------------------ #


def test_the_ledger_is_rebuilt_from_events(store: SQLiteStorage) -> None:
    outcome = ActionLedger(store, "run_1").claim("github.create_issue", ISSUE)
    ActionLedger(store, "run_1").complete(outcome.key, external_id="481")

    rebuilt = ActionLedger(store, "run_1")
    assert rebuilt.get(outcome.key).external_id == "481"  # type: ignore[union-attr]


def test_the_ledger_survives_a_process_restart(tmp_path: object) -> None:
    from pathlib import Path

    db = Path(str(tmp_path)) / "agent.db"
    with SQLiteStorage(db) as store:
        store.create_run(Run(run_id="run_1", goal="g"))
        outcome = ActionLedger(store, "run_1").claim("github.create_issue", ISSUE)
        ActionLedger(store, "run_1").complete(outcome.key, external_id="481")

    with SQLiteStorage(db) as store:
        repeat = ActionLedger(store, "run_1").claim("github.create_issue", ISSUE)
        assert not repeat.fresh
        assert repeat.external_id == "481"


def test_ledgers_for_different_runs_are_isolated(store: SQLiteStorage) -> None:
    store.create_run(Run(run_id="run_2", goal="g"))
    first = ActionLedger(store, "run_1")
    second = ActionLedger(store, "run_2")

    outcome = first.claim("github.create_issue", ISSUE)
    first.complete(outcome.key, external_id="481")

    assert second.claim("github.create_issue", ISSUE).fresh


def test_a_globally_scoped_action_deduplicates_across_runs(
    store: SQLiteStorage,
) -> None:
    """Some effects must happen once ever, not once per run."""
    key_a = idempotency_key("send_welcome_email", {"to": "x@y.z"})
    key_b = idempotency_key("send_welcome_email", {"to": "x@y.z"})
    assert key_a == key_b

    ledger = ActionLedger(store, "run_1")
    outcome = ledger.claim("send_welcome_email", {"to": "x@y.z"}, scoped_to_run=False)
    ledger.complete(outcome.key, external_id="msg_1")
    assert not ledger.claim("send_welcome_email", {"to": "x@y.z"}, scoped_to_run=False).fresh


def test_a_resolver_that_declines_falls_back_to_refusing(
    ledger: ActionLedger,
) -> None:
    """A resolver returning None must not be read as 'safe to proceed'."""
    ledger.claim("github.create_issue", ISSUE)

    with pytest.raises(UnknownSideEffect):
        ledger.claim("github.create_issue", ISSUE, on_unknown=lambda action: None)


def test_a_malformed_action_event_is_skipped_not_fatal(
    ledger: ActionLedger, store: SQLiteStorage
) -> None:
    """A foreign writer's action event must not make the ledger unreadable."""
    store.append_event("run_1", EventType.ACTION_RECORDED, {"note": "no key here"})
    outcome = ledger.claim("github.create_issue", ISSUE)
    ledger.complete(outcome.key, external_id="481")

    assert len(ledger.all()) == 1
    assert not ledger.claim("github.create_issue", ISSUE).fresh


def test_all_and_pending_report_the_ledger_contents(ledger: ActionLedger) -> None:
    done = ledger.claim("a.do", {"n": 1})
    ledger.complete(done.key)
    ledger.claim("b.do", {"n": 2})  # left in flight

    assert len(ledger.all()) == 2
    assert [a.action_type for a in ledger.pending()] == ["b.do"]


def test_an_explicit_key_lets_a_repeat_be_a_genuine_second_action(
    ledger: ActionLedger,
) -> None:
    """Argument hashing cannot express "this repeat is intentional".

    Two identical reminders are two sends, not one. Without an explicit key the
    second is silently deduplicated away — failing closed, but still wrong.
    """
    args = {"to": "x@y.z", "body": "Standup in 5"}

    first = ledger.claim("send_reminder", args, key="reminder-monday")
    ledger.complete(first.key, external_id="msg_1")

    second = ledger.claim("send_reminder", args, key="reminder-tuesday")
    assert second.fresh, "a distinct key must not collide with an earlier send"

    repeat = ledger.claim("send_reminder", args, key="reminder-monday")
    assert not repeat.fresh
    assert repeat.external_id == "msg_1"


def test_an_explicit_key_ignores_argument_drift(ledger: ActionLedger) -> None:
    """The caller's key is the identity; incidental argument changes are not."""
    first = ledger.claim("charge", {"amount": 100, "attempt": 1}, key="order-42")
    ledger.complete(first.key, external_id="ch_1")

    retry = ledger.claim("charge", {"amount": 100, "attempt": 2}, key="order-42")
    assert not retry.fresh
    assert retry.external_id == "ch_1"


def test_an_empty_explicit_key_is_refused(ledger: ActionLedger) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        ledger.claim("send_reminder", {"to": "x"}, key="")
