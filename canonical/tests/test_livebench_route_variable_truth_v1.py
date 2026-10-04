import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/LIVEBENCH_2026_06_25_IFBENCH58_SCORER_ROUTE_RECONCILIATION_20261005_V1.json"
DISPATCH = ROOT / "canonical/verification/LIVEBENCH_FROZEN_POPULATION_DISPATCH_METADATA_VERIFICATION_20261004_V1.json"
SCOPE = ROOT / "canonical/verification/LIVEBENCH_FROZEN_SCORER_SCOPE_COLLAPSE_INDEPENDENT_VERIFICATION_20261004_V1.json"
REVOCATION = ROOT / "canonical/verification/LIVEBENCH_IFBENCH58_ROUTE_VARIABLE_SUBSTITUTION_REVOCATION_20261005_V1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_route_uses_per_question_release_not_selected_release():
    candidate = load(CANDIDATE)
    dispatch = load(DISPATCH)
    scope = load(SCOPE)
    revocation = load(REVOCATION)

    assert candidate["status"].startswith("REVOKED__VARIABLE_SUBSTITUTION_ERROR")
    assert candidate["current_authority"] is False

    subject = dispatch["verified_subject"]
    assert subject["frozen_release"] == "2026-06-25"
    assert subject["selected_release_histogram"] == {"2024-11-25": 200}
    assert subject["dispatch_boundary"] == "2025-11-25"
    assert subject["legacy_ifeval_rows"] == 200
    assert subject["modern_ifbench_rows"] == 0

    assert scope["pinned_inputs"]["observed_max_release_date"] == "2024-11-25"
    assert scope["pinned_inputs"]["dispatch_boundary"] == "2025-11-25"
    assert scope["verifier"]["conclusion"] == "success"

    assert "m.question.get('livebench_release_date'" in revocation["proof"]["router_selector"]
    assert revocation["proof"]["selected_legacy_rows"] == 200
    assert revocation["proof"]["selected_modern_rows"] == 0


def test_date_relation_that_controls_dispatch():
    # ISO YYYY-MM-DD strings preserve chronological ordering.
    assert "2024-11-25" < "2025-11-25"
    assert "2026-06-25" >= "2025-11-25"
    # The second fact is irrelevant to dispatch because it is not the variable
    # used by old_instruction_following_matches.
