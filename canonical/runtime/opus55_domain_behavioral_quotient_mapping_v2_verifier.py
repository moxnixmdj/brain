from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V2.json"
COUNTER = ROOT / "canonical/verification/TERMINAL_FALSIFICATION_TOURNAMENT_UNMAPPED_TRANSFORM_SEARCH_20261005_V1.json"
ENVELOPE = ROOT / "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"

VISION = "VISION_AND_DENSE_DOCUMENT_UNDERSTANDING"
BIOLOGY = "BIOLOGY_RESEARCH_AND_DEVELOPMENT"
VISUAL_TRANSFORM = "biomedical_image_perception_segmentation_detection_measurement_classification_registration_reconstruction_and_tracking"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify():
    mapping = load(V2)
    counter = load(COUNTER)
    envelope = load(ENVELOPE)

    families = {row["id"] for row in envelope["families"]}
    rows = {row["surface"]: row for row in mapping["mappings"]}

    assert set(rows) == {
        "CYBERSECURITY",
        "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
        "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
        "HEALTHCARE",
        "MATHEMATICAL_REASONING_ARXIVMATH",
    }
    assert counter["status"].startswith("COUNTEREXAMPLE_FOUND__BIOLOGY_V1_MAPPING_OMITS")
    assert counter["verdict"]["new_primitive_family_required"] is False

    biology = rows[BIOLOGY]
    assert VISION in biology["existing_family_union"]
    assert VISUAL_TRANSFORM in biology["behavioral_decomposition"]
    assert set(biology["existing_family_union"]) <= families
    assert all(set(row["existing_family_union"]) <= families for row in rows.values())
    assert all(row["new_family_required"] is False for row in rows.values())

    result = mapping["mapping_result"]
    assert result["known_v1_constructive_counterexample_repaired"] is True
    assert result["known_v1_unmapped_transform_now_mapped_to_existing_family"] is True
    assert result["new_family_added"] is False
    assert result["terminal_acceptance_credit_delta"] == 0

    joined = " ".join(mapping["hard_nonclaims"])
    assert "NO_CLAIM_ALL_BIOLOGY_BEHAVIORS_ARE_NOW_ENUMERATED" in joined
    assert mapping["accounting"]["acceptance_credit_delta"] == 0
    assert mapping["accounting"]["family_credit_delta"] == 0
    assert mapping["accounting"]["capability_credit_delta"] == 0
    assert mapping["accounting"]["ownership_credit_delta"] == 0

    return {
        "status": "PASS__BIOLOGY_V1_COUNTEREXAMPLE_MINIMALLY_REPAIRED_WITH_EXISTING_FAMILY",
        "surface_count": len(rows),
        "biology_vision_family_present": True,
        "biology_visual_transform_present": True,
        "new_family_added": False,
        "semantic_losslessness_proved": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
