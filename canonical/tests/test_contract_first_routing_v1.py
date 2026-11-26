"""Tests for Play 1: route by contract, and the recipe that killed it.

The measurement itself is a committed artifact; these tests pin the behaviour that makes the
artifact readable (a verb gate that refuses topic overlap, deterministic ranking, agreement
numbers that can be audited) and pin the finding so it cannot drift silently.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import contract_first_routing_v1 as R  # noqa: E402

ARTIFACT = ROOT / "canonical/verification/PLAY_1_ROUTE_BY_CONTRACT_20261126_V1.json"


def _index() -> dict:
    contracts = {
        "canonical/runtime/expire_rule_v1.py": {
            "path": "canonical/runtime/expire_rule_v1.py",
            "stem": "expire_rule_v1",
            "verbs": {"expire": 2, "retain": 1},
            "objects": {"rule": 2, "store": 1},
            "topic": ["drift", "store", "current"],
            "guards": ["RULE_SCOPE_NO_LONGER_HOLDS"],
            "public_callables": ["expire_rule", "retain_rule"],
            "executable": True,
        },
        "canonical/runtime/memory_notes_v1.py": {
            "path": "canonical/runtime/memory_notes_v1.py",
            "stem": "memory_notes_v1",
            "verbs": {"note": 1},
            "objects": {"memory": 3},
            "topic": ["memory", "store", "current", "drift"],
            "guards": [],
            "public_callables": ["note_memory"],
            "executable": False,
        },
    }
    return {
        "contracts": contracts,
        "domain_of": {rel: ["continual_learning"] for rel in contracts},
        "stems": {rel: row["stem"] for rel, row in contracts.items()},
        "idf_verb": {"expire": 1.0, "retain": 1.0, "note": 1.0},
        "idf_object": {"rule": 1.0, "store": 1.0, "memory": 1.0},
        "verb_vocabulary": {"expire", "retain", "note"},
    }


def test_a_verb_is_what_admits_a_module() -> None:
    result = R.route_by_contract(_index(), "expire the rule when the store drifts")
    assert result["candidates"], result
    top = result["candidates"][0]
    assert top["stem"] == "expire_rule_v1"
    assert top["agreement"]["verbs"] == ["expire"]
    assert "rule" in top["agreement"]["objects"]
    assert top["agreement"]["guards"] == ["RULE_SCOPE_NO_LONGER_HOLDS"]


def test_topic_overlap_alone_is_refused_not_ranked_low() -> None:
    # Every word here is in memory_notes_v1's topic list, and none of its verbs or objects.
    result = R.route_by_contract(_index(), "drift store current drift")
    assert result["candidates"] == []
    assert result["reason"] == "NO_CONTRACT_AGREEMENT__NOT_A_TOPIC_MATCH"


def test_the_ablation_is_the_falsifier_and_it_is_wired() -> None:
    index = _index()
    query = "drift store current drift"
    strict = R.route_by_contract(index, query)
    loose = R.route_by_contract(index, query, require_contract=False, use_verbs=False)
    assert strict["candidates"] == []
    assert loose["candidates"], "the ablation must see what the gate refuses, or it tests nothing"


def test_ranking_is_deterministic() -> None:
    index = _index()
    first = R.route_by_contract(index, "expire the rule and retain the store")
    second = R.route_by_contract(index, "expire the rule and retain the store")
    assert first == second


def test_the_committed_measurement_still_says_what_it_said() -> None:
    report = json.loads(ARTIFACT.read_text())
    assert report["schema"] == R.SCHEMA
    assert report["queries"] == 42
    assert report["pool"] <= 1260, "the pool must not grow past the atlas to win"
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    # The finding: the label saturates, so domain recall cannot separate routers.
    assert report["chance_topic_at_5"] > 0.80
    assert report["ablation_topic_only_recall_at_5"] >= report["contract_recall_at_5"]
    assert report["verdict"] == "KILLED"
