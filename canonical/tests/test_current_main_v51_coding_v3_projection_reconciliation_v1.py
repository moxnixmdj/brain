from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ONE = ROOT / "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"
REC = ROOT / "canonical/governance/CURRENT_MAIN_V51_CODING_V3_PROJECTION_RECONCILIATION_20261009_V1.json"
V51 = ROOT / "canonical/verification/R2_V51_SOURCE_EXPLICIT_AUTOFILL_VERIFY_20261009_V1.json"
CODING = ROOT / "canonical/governance/CODING_SHARED_SPECIFICATION_COVERAGE_ONLY_SUCCESSOR_20261009_V3.json"
CODING_VERIFY = ROOT / "canonical/verification/CODING_SHARED_SPECIFICATION_COVERAGE_ONLY_SUCCESSOR_V3_INDEPENDENT_VERIFICATION_20261009_V1.json"


def blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_projection_binds_exact_verified_frontier_without_overclaim():
    r2 = load(R2)
    term = load(TERM)
    one = load(ONE)
    rec = load(REC)
    v51 = load(V51)
    coding = load(CODING)
    coding_verify = load(CODING_VERIFY)

    assert blob(R2) == "8aa893d4eaa8435933571fb1453e0028dd79f754"
    assert blob(TERM) == "da6b485de7e57330b0dcbd313c8570cfc6f2810f"
    assert blob(ONE) == "9db5dd1f2f44871251a61199d755ddc91489ef7d"
    assert blob(REC) == "a98d91ba889a4b5bba95d0838174299b57d21970"
    assert blob(V51) == "7e4ea72a141c92b70867e133c55a85b01a66e999"
    assert blob(CODING) == "8c6db7aa24e9e535fd3502234975250ef4bfb9cb"
    assert blob(CODING_VERIFY) == "718b2e77dd2549cba0f95f79a33d8dc3255c4952"

    assert "__V51__" in r2["status"]
    assert r2["scheduler_cut"]["path"].endswith("V50.json")
    assert r2["r2_v51_source_explicit_semantic_autofill_reconciliation"]["primary_internal_unsolved_count"] == 1
    assert r2["r2_v51_source_explicit_semantic_autofill_reconciliation"]["primary_internal_cell"] == "FINANCE_SEMANTIC_ADEQUACY_TAIL"
    assert r2["fixed_point_information_policy"]["source_explicit_parser_explicit_omissions_auto_filled"] is True
    assert r2["fixed_point_information_policy"]["source_explicit_autofill_replaces_caller_claims"] is False
    assert r2["fixed_point_information_policy"]["unrecognized_prose_remains_semantic_top"] is True
    assert r2["condition_bound_adequacy_reuse"]["registered_policy_count"] == 2
    assert r2["condition_bound_adequacy_reuse"]["registered_coding_specialist_policy_count"] == 1

    live = term["live_truth"]
    assert term["pointer_revision"] == 78
    assert live["current_r2_pointer_git_blob_sha"] == blob(R2)
    assert live["r2_primary_internal_unsolved_count"] == 1
    assert live["r2_primary_internal_unsolved_cell"] == "FINANCE_SEMANTIC_ADEQUACY_TAIL"
    assert live["coding_specification_registered_conditioned_policy_count"] == 2
    assert live["coding_specification_registered_coding_policy_count"] == 1
    assert live["coding_specification_registered_coding_specialist_policy_count"] == 1
    assert live["coding_specification_specialist_membership_self_certified"] is False
    assert live["cursorbench_next_proof_object"] == "CODING_V5_AUTHENTICATED_POSITIVE_ADEQUACY_CERTIFICATE_V1"
    assert live["cursorbench_global_selector_work_authorized_now"] is False
    assert live["terminal"] is False

    auth = one["authority"]
    assert auth["current_r2_pointer_git_blob_sha"] == blob(R2)
    assert auth["current_terminal_authority_git_blob_sha"] == blob(TERM)
    assert auth["current_terminal_authority_pointer_revision"] == 78
    assert auth["current_r2_internal_unsolved_count"] == 1
    assert auth["coding_registered_conditioned_policy_count"] == 2
    assert auth["coding_registered_coding_specialist_policy_count"] == 1
    assert auth["coding_v5_common_policy_certificate_ready"] is False
    assert auth["coding_whole_specification_cover_closed"] is False
    assert auth["current_r3_internal_unsolved"] is False
    assert any("CODING_V5_AUTHENTICATED_POSITIVE_ADEQUACY_CERTIFICATE_V1" in x for x in one["next_load_bearing_roots"])
    assert any("REUSE_V51_SOURCE_EXPLICIT_AUTOFILL" in x for x in one["next_load_bearing_roots"])

    assert v51["boundary"]["fills_omissions_only"] is True
    assert v51["boundary"]["replaces_existing_same_slot_claim"] is False
    assert v51["boundary"]["unrecognized_prose_remains_open"] is True
    assert v51["boundary"]["terminal_authority"] is False

    assert coding["current_registry_fact"]["registered_conditioned_policy_count"] == 2
    assert coding["current_registry_fact"]["registered_coding_specialist_policy_count"] == 1
    assert coding["current_registry_fact"]["v5_common_policy_certificate_registered"] is False
    assert coding["reduction"]["global_selector_work_ready"] is False
    assert coding_verify["result"]["whole_specification_residual_closed"] is False
    assert coding_verify["result"]["whole_cursorbench_positive_cover_closed"] is False

    assert rec["current_truth"]["r2_primary_internal_unsolved_count"] == 1
    assert rec["current_truth"]["coding_registered_conditioned_policy_count"] == 2
    assert rec["current_truth"]["coding_registered_coding_specialist_policy_count"] == 1
    assert rec["current_truth"]["terminal"] is False
    assert rec["accounting"]["terminal_credit_delta"] == 0
