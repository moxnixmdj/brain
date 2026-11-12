"""The applicability learner is fed on the live path, with the state that preceded the plan.

Two defects are pinned here.

The first is reachability: `applicability_v1` and `macro_v1`'s `context` argument shipped and then
sat unused -- every live caller still passed no context, so the chain battery stored macros with
ZERO evidence rows. A learner nothing feeds is not a capability.

The second is the trap the wiring walks into. `chain_v1` starts `established` empty and fills it
from each verified step's `provides`, so at the end of a run it holds the plan's OWN OUTPUTS. A
learner fed that identifies a circular requirement and then refuses every cold start, because a
fresh state cannot contain effects the plan has not produced yet. That is executed below, not
asserted, so the reason for the pre-state snapshot stays a measurement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import chain_v1 as C  # noqa: E402
from canonical.runtime import macro_v1 as MC  # noqa: E402

from the_state_a_plan_is_judged_in_must_precede_it_probe_20261112 import (  # noqa: E402
    GOAL,
    run,
)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(MC, "STATE", tmp_path / "chain_macros_v1.json")
    return MC


def test_the_live_chain_records_the_state_it_started_in(store):
    result = C.run(GOAL, memory=True)
    assert result["ok"], result.get("failed_at")
    assert result["preconditions_observed"] is not None
    key = MC.signature(C.decompose(GOAL))
    entry = (MC._load()["macros"])[key]
    assert len(entry.get("evidence") or []) >= 1
    assert all(row["ok"] is True for row in entry["evidence"])


def test_the_recorded_state_is_not_the_plans_own_outputs(store):
    """The load-bearing distinction, read from the STORE and not from the reported field.

    Asserting on `preconditions_observed` alone would pass even if a different value were handed
    to `record` -- a mutation that did exactly that survived the first version of this test.
    """
    result = C.run(GOAL, memory=True)
    produced = set(result["established_effects"] or [])
    key = MC.signature(C.decompose(GOAL))
    entry = (MC._load()["macros"])[key]
    stored = {f for row in (entry.get("evidence") or []) for f in (row.get("facts") or [])}
    assert produced, "the fixture must actually produce effects, or this proves nothing"
    assert stored, "the fixture must have observable preconditions"
    assert stored & produced == set()
    assert stored == set(result["preconditions_observed"] or [])


def test_the_snapshot_is_the_same_object_for_success_and_failure(store):
    """One starting state describes both outcomes; it is not recomputed after the side effects."""
    first = C.run(GOAL, memory=True)
    second = C.run(GOAL, memory=True)
    assert first["preconditions_observed"] == second["preconditions_observed"]


def test_the_naive_post_state_wiring_would_fabricate_a_circular_boundary(store):
    """Executes the idea that was rejected, so the rejection stays falsifiable.

    A success establishes every effect; a run failing at the last step establishes only the
    prefix. That difference is how far the plan got, not a fact about the world -- yet it yields
    a boundary made of the plan's own outputs that refuses every fresh state.
    """
    result = C.run(GOAL, memory=False)
    produced = list(result["established_effects"] or [])
    assert len(produced) >= 2, "need at least two effects for a prefix to differ"
    fabricated = APP.learn([(frozenset(produced), True), (frozenset(produced[:-1]), False)])
    assert fabricated.survivor_count > 0
    assert set(fabricated.most_general) <= set(produced)
    assert APP.explains_failure(fabricated, frozenset()) is True


def test_the_real_snapshot_does_not_refuse_a_cold_start(store):
    """The same test the fabricated boundary fails: a fresh world must still be offered the plan."""
    C.run(GOAL, memory=True)
    key = MC.signature(C.decompose(GOAL))
    boundary = MC.applicability(key)
    # Success-only evidence determines nothing, so nothing may be withheld.
    assert boundary.status == APP.UNDETERMINED
    assert MC.applicable(key, frozenset()) is True


def test_an_out_of_scope_plan_is_withdrawn_and_the_chain_still_runs(store, monkeypatch):
    C.run(GOAL, memory=True)
    monkeypatch.setattr(MC, "applicable", lambda key, context: False)
    refused = C.run(GOAL, memory=True)
    assert refused["macro_withheld_out_of_scope"] is True
    assert refused["used_macro"] is False
    assert refused["ok"] is True


def test_an_in_scope_plan_is_not_withdrawn(store):
    C.run(GOAL, memory=True)
    again = C.run(GOAL, memory=True)
    assert again["macro_withheld_out_of_scope"] is False


def test_memory_off_does_not_compute_or_record_a_context(store):
    result = C.run(GOAL, memory=False)
    assert result["preconditions_observed"] is None
    assert store._load().get("macros") in (None, {})


def test_the_snapshot_fails_open_when_the_registry_cannot_load(monkeypatch):
    from canonical.runtime import grounded_action_v1 as GA

    def _boom():
        raise RuntimeError("REGISTRY_UNAVAILABLE")
    monkeypatch.setattr(GA, "load_registry", _boom)
    assert C.precondition_context(["a", "b"], ROOT, "a and b") is None


def test_an_undecidable_premise_is_absent_and_never_guessed_true(monkeypatch):
    from canonical.runtime import world_probe_v1 as WP

    monkeypatch.setattr(
        WP, "probe_effect",
        lambda *a, **k: {"true": False, "how": "UNDECIDABLE__NOT_ESTABLISHED", "evidence": None},
    )
    ctx = C.precondition_context(C.decompose(GOAL), ROOT, GOAL)
    assert ctx == frozenset()


def test_a_sensor_that_raises_for_one_fact_does_not_lose_the_others(monkeypatch):
    from canonical.runtime import world_probe_v1 as WP

    real = WP.probe_effect
    calls = {"n": 0}

    def _flaky(fact, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("ONE_SENSOR_FAILED")
        return real(fact, **kw)
    monkeypatch.setattr(WP, "probe_effect", _flaky)
    ctx = C.precondition_context(C.decompose(GOAL), ROOT, GOAL)
    assert ctx is not None
    assert calls["n"] > 1


def test_the_fact_universe_is_bounded(monkeypatch):
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import world_probe_v1 as WP

    seen = []
    monkeypatch.setattr(WP, "probe_effect", lambda fact, **k: seen.append(fact) or {"true": False})
    monkeypatch.setattr(C, "MAX_PRECONDITION_FACTS", 3)
    C.precondition_context(C.decompose(GOAL), ROOT, GOAL)
    assert len(seen) <= 3


def test_the_probe_holds_in_every_arm():
    summary = run()["summary"]
    assert summary["learner_is_fed_on_the_live_path"] is True
    assert summary["recorded_state_excludes_the_plans_own_outputs"] is True
    assert summary["naive_post_state_fabricates_a_circular_requirement"] is True
    assert summary["naive_post_state_would_destroy_cold_start_reuse"] is True
    assert summary["offer_is_withheld_when_out_of_scope"] is True
    assert summary["offer_is_kept_when_in_scope"] is True
    assert summary["undecidable_premises_are_never_guessed_true"] is True
    assert summary["snapshot_fails_open_when_the_registry_is_unavailable"] is True


def test_the_probe_restores_the_repositorys_macro_state():
    path = MC.STATE
    before = path.read_bytes() if path.is_file() else None
    run()
    assert MC.STATE == path
    assert (path.read_bytes() if path.is_file() else None) == before
