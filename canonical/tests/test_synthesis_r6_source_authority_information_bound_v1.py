from canonical.runtime.synthesis_r6_source_authority_information_bound_v1 import (
    gate_evidence,
    threshold_polarity,
)

CLAIM = {
    "claim_id": "C",
    "metric": "M",
    "relation": "at_least",
    "threshold": 50,
    "unit": "index_point",
}
EVIDENCE = [
    {
        "evidence_id": "E_HIGH",
        "metric": "M",
        "value": 60,
        "unit": "index_point",
        "provenance": ["SRC_A"],
    },
    {
        "evidence_id": "E_LOW",
        "metric": "M",
        "value": 40,
        "unit": "index_point",
        "provenance": ["SRC_B"],
    },
]


def _facts(high_state: str, low_state: str):
    return [
        {
            "evidence_id": "E_HIGH",
            "provenance": ["SRC_A"],
            "state": high_state,
            "basis": "verified-authority-relation-A",
        },
        {
            "evidence_id": "E_LOW",
            "provenance": ["SRC_B"],
            "state": low_state,
            "basis": "verified-authority-relation-B",
        },
    ]


def test_identical_public_payload_requires_opposite_polarity_in_two_authority_worlds():
    public_a = {"claim": CLAIM, "evidence": EVIDENCE}
    public_b = {"claim": CLAIM, "evidence": EVIDENCE}
    assert public_a == public_b

    world_a = gate_evidence(EVIDENCE, _facts("ADMISSIBLE", "INADMISSIBLE"))
    world_b = gate_evidence(EVIDENCE, _facts("INADMISSIBLE", "ADMISSIBLE"))

    assert threshold_polarity(CLAIM, world_a) == "SUPPORTED"
    assert threshold_polarity(CLAIM, world_b) == "UNSUPPORTED"


def test_no_authority_information_never_commits_support_polarity():
    gated = gate_evidence(EVIDENCE, [])
    assert len(gated["unresolved"]) == 2
    assert threshold_polarity(CLAIM, gated) == "UNRESOLVED_SOURCE_AUTHORITY"


def test_provenance_name_does_not_confer_authority():
    renamed = [dict(x) for x in EVIDENCE]
    renamed[0]["provenance"] = ["OFFICIAL_LOOKING_NAME"]
    renamed[1]["provenance"] = ["UNOFFICIAL_LOOKING_NAME"]
    gated = gate_evidence(renamed, [])
    assert threshold_polarity(CLAIM, gated) == "UNRESOLVED_SOURCE_AUTHORITY"


def test_authority_fact_must_bind_exact_provenance():
    facts = _facts("ADMISSIBLE", "INADMISSIBLE")
    facts[0] = dict(facts[0])
    facts[0]["provenance"] = ["DIFFERENT_SOURCE"]
    gated = gate_evidence(EVIDENCE, facts)
    reasons = {x["evidence_id"]: x["reason"] for x in gated["unresolved"]}
    assert reasons["E_HIGH"] == "AUTHORITY_PROVENANCE_BINDING_MISMATCH"
    assert threshold_polarity(CLAIM, gated) == "UNRESOLVED_SOURCE_AUTHORITY"


def test_contradictory_authority_facts_fail_closed():
    facts = _facts("ADMISSIBLE", "INADMISSIBLE")
    facts.append(
        {
            "evidence_id": "E_HIGH",
            "provenance": ["SRC_A"],
            "state": "INADMISSIBLE",
            "basis": "conflicting-verified-claim",
        }
    )
    gated = gate_evidence(EVIDENCE, facts)
    reasons = {x["evidence_id"]: x["reason"] for x in gated["unresolved"]}
    assert reasons["E_HIGH"] == "CONTRADICTORY_AUTHORITY_FACTS"
    assert threshold_polarity(CLAIM, gated) == "UNRESOLVED_SOURCE_AUTHORITY"


def test_admitted_receipt_preserves_original_evidence_fields():
    gated = gate_evidence(EVIDENCE, _facts("ADMISSIBLE", "INADMISSIBLE"))
    assert gated["admissible"][0]["evidence"] == EVIDENCE[0]
    assert gated["inadmissible"][0]["evidence"] == EVIDENCE[1]
    assert gated["terminal_authority"] is False


def test_unknown_general_relation_is_not_silently_interpreted():
    claim = dict(CLAIM)
    claim["relation"] = "causes"
    gated = gate_evidence(EVIDENCE, _facts("ADMISSIBLE", "INADMISSIBLE"))
    assert threshold_polarity(claim, gated) == "UNRESOLVED_GENERAL_SUPPORT_SEMANTICS"
