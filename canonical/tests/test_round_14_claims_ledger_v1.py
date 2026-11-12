"""A claim is stated with the thing that decides it.

`round_14_claims_ledger_20261112` puts each claim about how this tree learns beside the evidence that
decides it, and re-runs that evidence. Pinned here:

* every tree claim still holds, and each one names the measurement it rests on — not a summary of it;
* the registry really carries **no parametric channel** (0 of 145 capabilities update weights), and
  the detector that says so has teeth: it catches a planted record;
* a claim with neither an executable predicate nor a complete citation is **rejected**, so the
  ledger cannot silently hold an opinion;
* the report says what it cannot do — linkage is not truth, and the tree predicates check the tree,
  not the world.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import round_14_claims_ledger_20261112 as ledger  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = ledger.building_blocks()
    return _CACHE["r"]


def test_every_tree_claim_holds_and_names_its_measurement():
    report = _report()
    failing = [name for name, row in report["tree"].items() if not row["holds"]]
    assert failing == [], f"claims that no longer hold: {failing}"
    assert report["summary"]["tree_claims_holding"] == report["summary"]["tree_claims"] == 7
    for name, row in report["tree"].items():
        assert row["evidence"], f"{name} holds but names no evidence"


def test_the_registry_has_no_parametric_channel():
    count, total, hits = ledger._weight_capabilities()
    assert count == 0, f"capabilities that would train weights: {hits}"
    registry = ledger.json.loads(ledger.REGISTRY.read_text(encoding="utf-8"))
    assert total == len(registry["capabilities"]) == 145


def test_the_weight_detector_catches_a_planted_record():
    planted = {"capability_id": "x", "entrypoint": "canonical/runtime/lora_adapter_training_v1.py",
               "action_template": "fine-tune an adapter on the receipt stream"}
    assert ledger.WEIGHT_WORDS.search(ledger.json.dumps(planted)), "the detector must read the record"
    assert ledger.WEIGHT_WORDS.search("fast weights are updated during inference")


def test_a_claim_without_evidence_is_rejected():
    assert ledger.refuse_unsupported([{"claim": "the model is sentient"}]) == ["the model is sentient"]
    assert ledger.refuse_unsupported([{"claim": "checked", "predicate": lambda: (True, "ok")}]) == []
    assert ledger.refuse_unsupported([{"claim": "cited", "arxiv": "2611.14505",
                                       "url": "https://arxiv.org/html/2611.14505",
                                       "says": "No harness-based method gains on unseen tasks."}]) == []


def test_every_external_claim_is_complete_and_cites_a_paper():
    external = _report()["external"]
    assert len(external) == 6
    for cid, row in external.items():
        assert row["linked"] is True, cid
        assert row["arxiv"] and "." in row["arxiv"], cid
        assert row["url"].startswith("https://"), cid
        assert len(row["says"]) > 40, f"{cid} must quote the finding, not gesture at it"
        assert row["claim"], cid


def test_the_ledger_says_what_it_cannot_do():
    limits = _report()["what_this_cannot_do"]
    assert any("LINKAGE_IS_NOT_TRUTH" in item for item in limits)
    assert any("NOT_THE_WORLD" in item for item in limits)


def test_the_run_summarises_both_kinds_of_evidence():
    s = _report()["summary"]
    assert s['all_tree_claims_hold'] is True
    assert s["all_external_claims_linked"] is True
    assert s["external_claims_linked"] == s["external_claims"] == 6
    assert _report()["model_dependency_count"] == 0
    assert _report()["incremental_spend_usd"] == 0
