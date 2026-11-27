from __future__ import annotations

from typing import Any, Mapping

ACTIVE_POINTER_PATH = "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
MODES = {"ACTIVE_INTERFACE", "DORMANT_WAKE", "CONTROL_PLANE_PREREQUISITE"}
GOVERNANCE_ACTIONS = {"GOVERNANCE_GUARD", "USER_AUTHORIZED_GOVERNANCE_STRATEGY_PROMOTION"}
WORK_CLASSES = {"PROGRESS_CANDIDATE", "FALSIFICATION_PROBE", "TRUTH_REPAIR", "CONTROL_PLANE"}
PROGRESS_EFFECT_KINDS = {
    "TRUTH_CLOSURE",
    "INTERFACE_CONTRACTION",
    "DEPTH_CONTRACTION",
    "PREREQUISITE_CONTRACTION",
    "PROOF_NODE_CONTRACTION",
}

CURRENTNESS_FIELDS = (
    "accepted_families",
    "open_families",
    "proved_atomic",
    "unresolved_atomic",
    "root1_positive_gap_count",
    "root2_touching_count",
    "root3_touching_count",
    "meta_envelope_open_count",
    "total_open_truth_obligations",
    "terminal",
)

def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _sha1(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)

def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty(x) for x in value)

def admission_errors(
    admission: Any,
    pointer: Mapping[str, Any],
    *,
    pointer_blob_sha: str,
    action_kind: str,
    receipt_blobs: Mapping[str, str] | None = None,
) -> list[str]:
    errors: list[str] = []
    receipt_blobs = dict(receipt_blobs or {})
    if not isinstance(admission, Mapping):
        return ["V22_ADMISSION_MISSING"]
    if admission.get("active_pointer_path") != ACTIVE_POINTER_PATH:
        errors.append("V22_ACTIVE_POINTER_PATH_MISMATCH")
    if admission.get("active_pointer_git_blob_sha") != pointer_blob_sha:
        errors.append("V22_ACTIVE_POINTER_BLOB_STALE_OR_MISMATCH")
    exact = pointer.get("exact_state")
    if not isinstance(exact, Mapping):
        return errors + ["V22_POINTER_EXACT_STATE_MISSING"]
    currentness = admission.get("currentness")
    if not isinstance(currentness, Mapping):
        errors.append("V22_CURRENTNESS_BINDING_MISSING")
    else:
        for field in CURRENTNESS_FIELDS:
            if currentness.get(field) != exact.get(field):
                errors.append("V22_CURRENTNESS_MISMATCH:" + field)
    active = pointer.get("current_shared_causal_interfaces")
    if not _nonempty_list(active):
        errors.append("V22_ACTIVE_INTERFACE_SET_INVALID")
        active_set: set[str] = set()
    else:
        active_set = set(active)
    mode = str(admission.get("mode") or "")
    if mode not in MODES:
        errors.append("V22_ADMISSION_MODE_INVALID")
    if not _nonempty_list(admission.get("target_truth_obligations")):
        errors.append("V22_TARGET_TRUTH_OBLIGATIONS_MISSING")
    if not _nonempty(admission.get("proof_state_reachability")):
        errors.append("V22_PROOF_STATE_REACHABILITY_MISSING")
    if admission.get("fresh_reality_authority") is not False:
        errors.append("V22_FRESH_REALITY_AUTHORITY_NOT_FALSE")
    if admission.get("terminal_credit_delta") != 0:
        errors.append("V22_TERMINAL_CREDIT_NONZERO")
    work_class=str(admission.get("work_class") or "")
    if work_class not in WORK_CLASSES:
        errors.append("V22_WORK_CLASS_INVALID")
    if admission.get("claimed_progress_credit") not in (None, 0):
        errors.append("V22_PREWRITE_PROGRESS_CREDIT_NONZERO")
    if mode=="CONTROL_PLANE_PREREQUISITE":
        if work_class!="CONTROL_PLANE":
            errors.append("V22_CONTROL_PLANE_WORK_CLASS_REQUIRED")
    elif work_class=="CONTROL_PLANE":
        errors.append("V22_CONTROL_PLANE_WORK_CLASS_OUTSIDE_CONTROL_PLANE_MODE")
    if work_class=="PROGRESS_CANDIDATE":
        expected=admission.get("expected_progress")
        if not isinstance(expected,Mapping):
            errors.append("V22_EXPECTED_PROGRESS_MISSING")
        else:
            if expected.get("effect_kind") not in PROGRESS_EFFECT_KINDS:
                errors.append("V22_EXPECTED_PROGRESS_EFFECT_INVALID")
            expected_targets=expected.get("target_truth_obligations")
            actual_targets=admission.get("target_truth_obligations")
            if not isinstance(expected_targets,list) or set(expected_targets)!=set(actual_targets or []):
                errors.append("V22_EXPECTED_PROGRESS_TARGET_MISMATCH")
            if not _nonempty(expected.get("success_condition")):
                errors.append("V22_EXPECTED_PROGRESS_SUCCESS_CONDITION_MISSING")
        if admission.get("postchange_evidence_required") is not True:
            errors.append("V22_PROGRESS_POSTCHANGE_EVIDENCE_NOT_REQUIRED")
    elif work_class=="TRUTH_REPAIR":
        if admission.get("postchange_evidence_required") is not True:
            errors.append("V22_TRUTH_REPAIR_POSTCHANGE_EVIDENCE_NOT_REQUIRED")
    elif work_class=="FALSIFICATION_PROBE":
        if admission.get("claimed_progress_credit") not in (None,0):
            errors.append("V22_FALSIFICATION_PROBE_CANNOT_CLAIM_PROGRESS")
    if mode == "ACTIVE_INTERFACE":
        if str(admission.get("interface") or "") not in active_set:
            errors.append("V22_INTERFACE_NOT_CURRENTLY_ACTIVE")
    elif mode == "DORMANT_WAKE":
        dormant = set(pointer.get("dormant_wake_only") or [])
        dormant.update(pointer.get("meta_dormant_wake_only") or [])
        if str(admission.get("dormant_work_id") or "") not in dormant:
            errors.append("V22_DORMANT_WORK_NOT_IN_CURRENT_WAKE_ONLY_SET")
        path = admission.get("wake_receipt_path")
        sha = admission.get("wake_receipt_git_blob_sha")
        if not _nonempty(path) or not _sha1(sha):
            errors.append("V22_WAKE_RECEIPT_BINDING_INVALID")
        elif receipt_blobs.get(str(path)) != sha:
            errors.append("V22_WAKE_RECEIPT_BLOB_STALE_OR_MISMATCH")
    elif mode == "CONTROL_PLANE_PREREQUISITE":
        if action_kind not in GOVERNANCE_ACTIONS:
            errors.append("V22_CONTROL_PLANE_MODE_REQUIRES_GOVERNANCE_ACTION")
        if admission.get("control_plane_gap") != "V22_SCHEDULER_ENFORCEMENT_GAP":
            errors.append("V22_CONTROL_PLANE_GAP_MISMATCH")
        prereq = admission.get("minimum_prerequisite_for")
        if not isinstance(prereq, list) or set(prereq) != active_set:
            errors.append("V22_CONTROL_PLANE_PREREQUISITE_SCOPE_MISMATCH")
    tournament = admission.get("tournament")
    if not isinstance(tournament, Mapping):
        errors.append("V22_TOURNAMENT_BINDING_MISSING")
    else:
        for field in ("proposal_id", "falsifier_id", "decisive_question"):
            if not _nonempty(tournament.get(field)):
                errors.append("V22_TOURNAMENT_FIELD_MISSING:" + field)
        if tournament.get("known_counterexamples_checked") is not True:
            errors.append("V22_KNOWN_COUNTEREXAMPLES_NOT_CHECKED")
        receipts = tournament.get("counterexample_receipts")
        if not isinstance(receipts, list):
            errors.append("V22_COUNTEREXAMPLE_RECEIPTS_NOT_LIST")
        elif not receipts and not _nonempty(tournament.get("no_known_counterexample_reason")):
            errors.append("V22_COUNTEREXAMPLE_EVIDENCE_OR_REASON_REQUIRED")
        else:
            if work_class=="TRUTH_REPAIR" and not receipts:
                errors.append("V22_TRUTH_REPAIR_COUNTERMODEL_RECEIPT_REQUIRED")
            for i, row in enumerate(receipts):
                if not isinstance(row, Mapping):
                    errors.append(f"V22_COUNTEREXAMPLE_RECEIPT_INVALID:{i}")
                    continue
                path = row.get("path")
                sha = row.get("git_blob_sha")
                if not _nonempty(path) or not _sha1(sha):
                    errors.append(f"V22_COUNTEREXAMPLE_RECEIPT_BINDING_INVALID:{i}")
                elif receipt_blobs.get(str(path)) != sha:
                    errors.append(f"V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:{i}")
    return sorted(set(errors))
