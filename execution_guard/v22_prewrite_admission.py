from __future__ import annotations

from typing import Any, Mapping

ACTIVE_POINTER_PATH = "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
MODES = {"ACTIVE_INTERFACE", "DORMANT_WAKE", "CONTROL_PLANE_PREREQUISITE"}
GOVERNANCE_ACTIONS = {"GOVERNANCE_GUARD", "USER_AUTHORIZED_GOVERNANCE_STRATEGY_PROMOTION"}

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

BENCHMARK_INFORMATION_EQUIVALENCE_LAW_PATH = "canonical/laws/BENCHMARK_OUTPUT_INFORMATION_EQUIVALENCE_LAW_V1.md"
BENCHMARK_WITNESS_SYNTHESIS_PATH = "canonical/governance/BENCHMARK_WITNESS_ELIMINATION_SYNTHESIS_20261006_V1.json"
BENCHMARK_WITNESS_PREDICATES = {
    "CODING_TB4_GE_66_4",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "HLE_TOOLS_GE_67_7",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_AGENT_V2_GE_58_59",
    "CODING_FRONTIERCODE_GE_54_4",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "MYSTERYMECHANISM_GE_49_55",
}
INTERNAL_CERTIFICATE_SEARCH_STATES = {
    "NONZERO_INFORMATION_GAIN",
    "EXHAUSTED_OR_FALSIFIED",
}


def _bound_receipt_errors(
    prefix: str,
    binding: Any,
    receipt_blobs: Mapping[str, str],
) -> list[str]:
    if not isinstance(binding, Mapping):
        return [prefix + "_RECEIPT_MISSING"]
    path = binding.get("path")
    sha = binding.get("git_blob_sha")
    if not _nonempty(path) or not _sha1(sha):
        return [prefix + "_RECEIPT_BINDING_INVALID"]
    if receipt_blobs.get(str(path)) != sha:
        return [prefix + "_RECEIPT_BLOB_STALE_OR_MISMATCH"]
    return []


def _benchmark_external_route_errors(
    admission: Mapping[str, Any],
    receipt_blobs: Mapping[str, str],
) -> list[str]:
    if admission.get("mode") != "ACTIVE_INTERFACE":
        return []
    if admission.get("interface") != "EXTERNAL_RESULT_OR_ACCESS":
        return []

    raw_targets = admission.get("target_truth_obligations")
    if not isinstance(raw_targets, list):
        return []
    benchmark_targets = sorted(
        {str(x) for x in raw_targets if str(x) in BENCHMARK_WITNESS_PREDICATES}
    )
    if not benchmark_targets:
        return []

    errors: list[str] = []
    info = admission.get("benchmark_information_equivalence")
    if not isinstance(info, Mapping):
        return ["V22_BENCHMARK_INFORMATION_EQUIVALENCE_MISSING"]

    if info.get("law_path") != BENCHMARK_INFORMATION_EQUIVALENCE_LAW_PATH:
        errors.append("V22_BENCHMARK_INFORMATION_EQUIVALENCE_LAW_MISMATCH")
    if info.get("witness_synthesis_path") != BENCHMARK_WITNESS_SYNTHESIS_PATH:
        errors.append("V22_BENCHMARK_WITNESS_SYNTHESIS_PATH_MISMATCH")

    declared = info.get("target_predicates")
    if (
        not isinstance(declared, list)
        or sorted(set(str(x) for x in declared)) != benchmark_targets
    ):
        errors.append("V22_BENCHMARK_TARGET_PREDICATE_BINDING_MISMATCH")

    if info.get("current_minimum_information_cut_member") is not True:
        errors.append("V22_BENCHMARK_ROUTE_NOT_PROVED_IN_CURRENT_MINIMUM_INFORMATION_CUT")
    if info.get("route_nondominated_proved") is not True:
        errors.append("V22_BENCHMARK_ROUTE_NONDOMINANCE_UNPROVED")

    search_state = info.get("internal_certificate_search_state")
    if search_state not in INTERNAL_CERTIFICATE_SEARCH_STATES:
        errors.append("V22_BENCHMARK_INTERNAL_CERTIFICATE_SEARCH_STATE_INVALID")
    elif search_state == "NONZERO_INFORMATION_GAIN":
        if info.get("external_wait_on_critical_path") is not False:
            errors.append("V22_PROVIDER_WAIT_FORBIDDEN_WHILE_INTERNAL_CERTIFICATE_HAS_INFORMATION_GAIN")
    else:
        errors.extend(
            _bound_receipt_errors(
                "V22_BENCHMARK_CERTIFICATE_EXHAUSTION",
                info.get("certificate_exhaustion_receipt"),
                receipt_blobs,
            )
        )

    if info.get("self_service_access_claimed") is True:
        provisioned = info.get("self_service_provisioning_verified") is True
        authorized = info.get("existing_authorized_credential_verified") is True
        if not (provisioned or authorized):
            errors.append("V22_PROVIDER_UI_IS_NOT_SELF_SERVICE_PROVISIONING_EVIDENCE")
        if provisioned:
            errors.extend(
                _bound_receipt_errors(
                    "V22_PROVIDER_SELF_SERVICE_PROVISIONING",
                    info.get("self_service_provisioning_receipt"),
                    receipt_blobs,
                )
            )
        if authorized:
            errors.extend(
                _bound_receipt_errors(
                    "V22_PROVIDER_AUTHORIZED_CREDENTIAL",
                    info.get("existing_authorized_credential_receipt"),
                    receipt_blobs,
                )
            )

    return errors


def referenced_receipt_paths(admission: Any) -> list[str]:
    if not isinstance(admission, Mapping):
        return []
    refs: list[str] = []

    wake = admission.get("wake_receipt_path")
    if _nonempty(wake):
        refs.append(str(wake))

    tournament = admission.get("tournament")
    if isinstance(tournament, Mapping):
        for row in tournament.get("counterexample_receipts") or []:
            if isinstance(row, Mapping) and _nonempty(row.get("path")):
                refs.append(str(row["path"]))

    info = admission.get("benchmark_information_equivalence")
    if isinstance(info, Mapping):
        for field in (
            "certificate_exhaustion_receipt",
            "self_service_provisioning_receipt",
            "existing_authorized_credential_receipt",
        ):
            row = info.get(field)
            if isinstance(row, Mapping) and _nonempty(row.get("path")):
                refs.append(str(row["path"]))

    return sorted(set(refs))


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
    errors.extend(_benchmark_external_route_errors(admission, receipt_blobs))
    return sorted(set(errors))
