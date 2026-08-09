from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from continuum.models import Goal, StateStatus
from continuum.security.hashing import canonical, hash_content, make_id, stable_hash, to_json


def test_key_order_does_not_change_hash() -> None:
    a = {"b": 1, "a": {"z": [1, 2], "y": "x"}}
    b = {"a": {"y": "x", "z": [1, 2]}, "b": 1}
    assert stable_hash(a) == stable_hash(b)


def test_list_order_does_change_hash() -> None:
    assert stable_hash([1, 2]) != stable_hash([2, 1])


def test_naive_and_aware_datetimes_normalize_to_utc() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    other_zone = datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert stable_hash(naive) == stable_hash(aware) == stable_hash(other_zone)


def test_bytes_are_hashable_and_distinct_from_their_text() -> None:
    assert stable_hash(b"abc") != stable_hash("abc")


def test_non_finite_floats_are_rejected() -> None:
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            stable_hash({"x": bad})


def test_unhashable_types_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        stable_hash({"fn": lambda: None})


def test_sets_are_rejected_because_they_have_no_stable_order() -> None:
    with pytest.raises(TypeError, match="no stable order"):
        stable_hash({"tags": {"a", "b"}})


def test_enums_hash_by_value_not_by_identity() -> None:
    assert stable_hash(StateStatus.STALE) == stable_hash("stale")
    assert stable_hash({"status": StateStatus.VALID}) == stable_hash({"status": "valid"})


def test_ambiguous_mapping_keys_are_rejected() -> None:
    with pytest.raises(ValueError, match="ambiguous mapping key"):
        stable_hash({1: "a", "1": "b"})


def test_tuples_and_lists_are_equivalent_after_json_round_trip() -> None:
    assert stable_hash({"xs": (1, 2)}) == stable_hash({"xs": [1, 2]})


def test_pydantic_models_are_hashed_through_json_dump() -> None:
    goal = Goal(description="Analyze 10,000 documents", version=3)
    assert stable_hash(goal) == stable_hash(goal.model_dump(mode="json"))


def test_canonical_sorts_nested_keys() -> None:
    assert to_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert canonical({"b": {"d": 1, "c": 2}}) == {"b": {"c": 2, "d": 1}}


def test_hash_content_is_sha256_hex() -> None:
    digest = hash_content(b"")
    assert len(digest) == 64
    assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_make_id_is_prefixed_and_unique() -> None:
    ids = {make_id("run") for _ in range(200)}
    assert len(ids) == 200
    assert all(i.startswith("run_") for i in ids)


@given(st.dictionaries(st.text(), st.integers() | st.text() | st.booleans() | st.none()))
def test_hash_is_deterministic_for_arbitrary_json_dicts(payload: dict[str, object]) -> None:
    assert stable_hash(payload) == stable_hash(dict(reversed(list(payload.items()))))
