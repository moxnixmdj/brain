"""Regressions for the EIG question wire and the external one-experience store.

These are mechanism tests, not benchmark results. The real hard-case transfer instrument is
`canonical/tools/one_experience_cross_family_transfer_v1.py` and its persistent receipt.
"""

from __future__ import annotations

import json

from canonical.runtime import active_question_v1 as aq
from canonical.runtime import settlement_v1 as sv
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.tools import one_experience_cross_family_transfer_v1 as tr


def _two_regime_space() -> sv.VersionSpace:
    def predicts(probe: tuple[object, ...], winner: str) -> str:
        if winner == "TRANSFER" and len(probe) > 1 and probe[1] == "bind/correct":
            return "MATCH"
        return "MISMATCH"

    return sv.VersionSpace([
        sv.Hypothesis(key="TRANSFER", predict=lambda p: predicts(tuple(p), "TRANSFER")),
        sv.Hypothesis(key="NON_TRANSFER", predict=lambda p: predicts(tuple(p), "NON_TRANSFER")),
    ])


def test_eig_policy_selects_positive_gain_and_preserves_caller_order() -> None:
    space = _two_regime_space()
    first = ("target", "bind/correct", "first")
    second = ("target", "bind/correct", "second")
    wrong = ("target", "bind/wrong", "wrong")
    decision = aq.policy(space, [first, second, wrong], budget=3)
    assert decision["policy"] == "EIG"
    assert decision["probes"] == [first, second]
    assert decision["gains"][aq.key_of(first)] == 1.0
    assert decision["gains"][aq.key_of(wrong)] == 0.0


def test_eig_refuses_open_space_and_a_blind_instrument() -> None:
    many = sv.VersionSpace([
        sv.Hypothesis(key=f"h{i}", predict=lambda p: "MATCH") for i in range(25)
    ])
    open_decision = aq.policy(many, [("target", "bind/correct", "p")])
    assert open_decision["policy"] == "FALLBACK__ARRIVAL_ORDER"
    assert "open" in open_decision["reason"]

    identical = sv.VersionSpace([
        sv.Hypothesis(key="a", predict=lambda p: "MATCH"),
        sv.Hypothesis(key="b", predict=lambda p: "MATCH"),
    ])
    blind = aq.policy(identical, [("target", "bind/correct", "p")])
    assert blind["policy"] == "REFUSED__INSTRUMENT_BLIND"


def test_ask_executes_the_question_and_uses_the_observation() -> None:
    space = _two_regime_space()
    correct = ("target", "bind/correct", "p")
    wrong = ("target", "bind/wrong", "q")
    asked: list[str] = []

    def oracle(probe: tuple[object, ...]) -> str:
        asked.append(aq.key_of(probe))
        return "MATCH" if probe[1] == "bind/correct" else "MISMATCH"

    result = aq.ask(space, [correct, wrong], oracle=oracle,
                    domain=[correct, wrong], budget=2)
    assert asked == [aq.key_of(correct)]
    assert result["settled"] is True
    assert result["winner"] == "TRANSFER"
    assert result["posterior"]["TRANSFER"] > 0.99
    assert result["settlement"]["status"] == "SETTLED"
    assert result["settlement"]["information_bits"] == 1.0


def test_perfect_algorithm_right_question_executes_and_uses_eig() -> None:
    space = _two_regime_space()
    correct = ("target", "bind/correct", "p")
    wrong = ("target", "bind/wrong", "q")
    asked: list[str] = []

    def oracle(probe: tuple[object, ...]) -> str:
        asked.append(aq.key_of(probe))
        return "MATCH" if probe[1] == "bind/correct" else "MISMATCH"

    class Env:
        pass

    scan = {"learned": {"model": {}, "transition_count": 0},
            "root": "root", "observations": {"root": "root"}}
    row = pa.right_question(Env(), scan, ["novelty_only"],
                            question_space=space,
                            probe_keys=[correct, wrong],
                            probe_oracle=oracle,
                            probe_budget=2)
    assert asked == [aq.key_of(correct)]
    assert row["eig"]["policy"] == "EIG"
    assert row["eig"]["answered"] is True
    assert row["eig"]["gain_of_the_question_bits"] == 1.0
    assert row["best"] == aq.key_of(correct)
    assert row["eig"]["posterior"]["TRANSFER"] > 0.99
    assert row["honest_note"] == "EIG-selected probe, executed and observed"


def test_external_store_rule_is_editable_and_does_not_hold_an_exact_action(tmp_path) -> None:
    source = {
        "question": "x",
        "job_digest": "job",
        "binding_digest": "binding",
        "resolution": {"status": "RESOLVED__GUIDE_OUTPUT_REPRODUCED"},
    }
    evidence = {
        "probes": [{"key": ("source", "bind/correct", "x"), "outcome": "MATCH"}],
        "exact": {"source|bind/correct|x": "MATCH"},
        "classes": {"bind/correct": "MATCH"},
        "source_outcomes_digest": "digest",
    }
    store = tr._store_document(source, evidence)
    path = tmp_path / "store.json"
    path.write_text(json.dumps(store, sort_keys=True), encoding="utf-8")
    assert tr._verify_store(path)["ok"] is True
    assert tr._load_abstract_rule(path) is not None
    assert tr.LEARNED_ABSTRACTION["parameters_written"] is False
    assert store["source_provenance"]["exact_source_binding_stored"] is False
    assert "exact source action replay" in tr.LEARNED_ABSTRACTION["what_not_to_save"]

    removed = dict(store)
    removed.pop("learned_abstraction")
    removed_path = tmp_path / "removed.json"
    removed_path.write_text(json.dumps(removed, sort_keys=True), encoding="utf-8")
    assert tr._load_abstract_rule(removed_path) is None
    assert tr._load_abstract_rule(path) is not None
