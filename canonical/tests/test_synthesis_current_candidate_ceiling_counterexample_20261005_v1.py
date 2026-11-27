from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.p3_information_safe_candidate_v3 import solve
from canonical.runtime.synthesis_matched_quality_metric_v1 import aggregate

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "canonical/runtime/p3_information_safe_candidate_v3.py": "54bfc7e5ee205aa328863a5ea1ca6f47f864d85a",
    "canonical/governance/SYNTHESIS_P3_TYPED_INPUT_DOMAIN_COUNTERMODEL_PARTITION_20261005_V1.json": "4150a16f4c20bf0bfcaa23d31b0b03af69417b2b",
    "canonical/runtime/synthesis_matched_quality_metric_v1.py": "116b7394f4b0a6845056c798e966f4cc26f294bf",
    "canonical/governance/SYNTHESIS_HIDDEN_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_V1.json": "ac12d96b7d060ba996f1f2672d66f05da628dd93",
}


def blob(rel: str) -> str:
    b = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_current_p3_v3_cannot_have_global_matched_quality_one():
    for rel, expected in FILES.items():
        assert blob(rel) == expected, (rel, blob(rel), expected)

    partition = load(
        "canonical/governance/SYNTHESIS_P3_TYPED_INPUT_DOMAIN_COUNTERMODEL_PARTITION_20261005_V1.json"
    )
    r6 = next(
        x
        for x in partition["constructive_uncovered_classes"]
        if x["id"] == "SYNTHESIS_SCOPE_R6_PROVENANCE_AND_UNIT_SENSITIVE_SUPPORT"
    )
    assert "source authority" in r6["witness"]
    assert partition["source_bound_facts"]["provenance_consumed_by_candidate"] is False
    assert partition["source_bound_facts"]["evidence_unit_consumed_by_candidate"] is False

    public = {
        "contract": "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "task": {
            "audience": "executive",
            "required_claims": ["C"],
            "max_claims": 1,
            "claims": [
                {
                    "claim_id": "C",
                    "metric": "M",
                    "relation": "at_least",
                    "threshold": 50,
                    "kind": "risk",
                }
            ],
            "evidence": [
                {
                    "metric": "M",
                    "value": 60,
                    "unit": "index_point",
                    "provenance": ["SRC_A"],
                },
                {
                    "metric": "M",
                    "value": 40,
                    "unit": "index_point",
                    "provenance": ["SRC_B"],
                },
            ],
        },
    }

    result = solve(public)
    assert result["selected_claims"] == ["C"]

    # Admissible R6 authority world: only SRC_B is admissible.
    # Its value 40 falsifies C: M >= 50, so selecting C is an unsupported
    # material claim in this world.
    src_b_value = public["task"]["evidence"][1]["value"]
    assert src_b_value < public["task"]["claims"][0]["threshold"]

    perfect_other_dimensions = {
        "claim_to_source_fidelity": 1.0,
        "uncertainty_and_disagreement_preservation": 1.0,
        "audience_adaptation": 1.0,
        "format_and_style_constraints": 1.0,
        "compression_without_decision_relevant_loss": 1.0,
    }
    scored = aggregate(perfect_other_dimensions, unsupported_material_claims=1)
    assert scored["matched_quality"] == 0.0
    assert scored["reason"] == "UNSUPPORTED_MATERIAL_CLAIM_HARD_ZERO"

    cert = load(
        "canonical/governance/SYNTHESIS_CURRENT_CANDIDATE_CEILING_COUNTEREXAMPLE_20261005_V1.json"
    )
    assert cert["theorem"]["result"] == "CURRENT_CANDIDATE_UNIVERSAL_CEILING_1_ROUTE_FALSIFIED"
    assert cert["fresh_reality_authority"] is False
    assert cert["acceptance_credit_delta"] == 0
