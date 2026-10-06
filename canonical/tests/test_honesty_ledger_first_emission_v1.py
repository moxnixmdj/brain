from __future__ import annotations

import copy
import hashlib

from canonical.runtime.honesty_ledger_first_emission_v1 import (
    INPUT_SCHEMA,
    compile_emission,
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def base():
    return {
        "schema": INPUT_SCHEMA,
        "sequence": 0,
        "emission_id": "e0",
        "task_id": "T1",
        "obligations": [
            {"id": "o1", "state": "VERIFIED", "receipts": [h("o1")]},
        ],
        "declared_inputs": [
            {"input_id": "source", "sha256": h("source"), "material": True},
        ],
        "content_items": [
            {
                "claim_id": "c1",
                "text": "The verified result is 42.",
                "stance": "SUPPORTED",
                "evidence_receipts": [h("evidence")],
            }
        ],
        "belief_assertions": [],
    }


def test_valid_ledger_first_emission_passes():
    out = compile_emission(base())
    assert out["status"] == "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION"
    assert out["ledger_complete_by_construction_for_rendered_dynamic_content"] is True
    assert out["payload"]["rendered_text"] == "The verified result is 42."
    assert out["payload"]["completion_state"] == "COMPLETE"
    assert out["honesty_record"]["completion_claim"] == "COMPLETE"
    assert out["arbitrary_dynamic_payload_field_permitted"] is False


def test_arbitrary_payload_field_is_rejected():
    x = base()
    x["payload"] = {"hidden": "The experiment succeeded."}
    out = compile_emission(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "UNDECLARED_TOP_LEVEL_FIELD:payload" in out["errors"][0]


def test_caller_cannot_supply_completion_claim():
    x = base()
    x["completion_claim"] = "COMPLETE"
    out = compile_emission(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "UNDECLARED_TOP_LEVEL_FIELD:completion_claim" in out["errors"][0]


def test_open_obligation_forces_partial_completion():
    x = base()
    x["obligations"][0] = {"id": "o1", "state": "OPEN", "receipts": []}
    out = compile_emission(x)
    assert out["status"] == "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION"
    assert out["payload"]["completion_state"] == "PARTIAL"
    assert out["honesty_record"]["completion_claim"] == "PARTIAL"


def test_supported_content_requires_evidence():
    x = base()
    x["content_items"][0]["evidence_receipts"] = []
    out = compile_emission(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "RECEIPTS_EMPTY" in out["errors"][0]


def test_uncertain_content_may_render_without_evidence_but_is_marked_uncertain():
    x = base()
    x["content_items"][0]["stance"] = "UNCERTAIN"
    x["content_items"][0]["evidence_receipts"] = []
    out = compile_emission(x)
    assert out["status"] == "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION"
    claim = out["honesty_record"]["material_claims"][0]
    assert claim["supported"] is False
    assert claim["explicit_uncertainty"] is True


def test_material_declared_input_becomes_disclosed_provenance():
    out = compile_emission(base())
    event = out["honesty_record"]["provenance_events"][0]
    assert event["event_id"] == "input::source"
    assert event["material"] is True
    assert event["disclosed"] is True
    assert event["receipts"] == [h("source")]


def test_dynamic_render_is_exactly_content_item_texts():
    x = base()
    x["content_items"].append({
        "claim_id": "c2",
        "text": "Second line.",
        "stance": "UNCERTAIN",
        "evidence_receipts": [],
    })
    out = compile_emission(x)
    assert out["status"] == "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION"
    texts = [r["text"] for r in out["payload"]["content_items"]]
    assert out["payload"]["rendered_text"] == "\n".join(texts)
    assert [r["claim_id"] for r in out["payload"]["content_items"]] == [
        r["claim_id"] for r in out["honesty_record"]["material_claims"]
    ]


def test_belief_change_without_evidence_fails_closed():
    x = base()
    x["belief_assertions"] = [{
        "assertion_id": "b1",
        "registered_state": "FALSE",
        "asserted_state": "TRUE",
        "evidence_update_receipts": [],
    }]
    out = compile_emission(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "HONESTY_ENVELOPE_DENIED" in out["errors"][0]


def test_belief_change_with_evidence_can_pass():
    x = base()
    x["belief_assertions"] = [{
        "assertion_id": "b1",
        "registered_state": "FALSE",
        "asserted_state": "TRUE",
        "evidence_update_receipts": [h("belief-update")],
    }]
    out = compile_emission(x)
    assert out["status"] == "PASS__LEDGER_FIRST_CONTENT_BOUND_EMISSION"


def test_unknown_content_field_cannot_smuggle_dynamic_text():
    x = base()
    x["content_items"][0]["hidden_text"] = "undocumented claim"
    out = compile_emission(x)
    # V1 must reject fields it does not semantically bind rather than silently
    # dropping them from the rendered/ledger relation.
    assert out["status"] == "FAIL_CLOSED"
