from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.terminal_closure_reducer import evaluate_manifest

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MANIFEST = ROOT / "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"

MANDATORY_ROOT = "CLOSE_AGGREGATE_FROZEN_PROTOCOL_AND_OWNERSHIP_PREDICATE"
MANDATORY_SEMANTICS = "FROZEN_19_FAMILY_ACCEPTANCE_AND_OWNERSHIP_FINALITY"


def _verify_file_exists(path: Any) -> bool:
    """Verify a path exists and is a file."""
    if not path:
        return False
    if isinstance(path, str):
        full_path = ROOT / path
        return full_path.exists() and full_path.is_file()
    if isinstance(path, Path):
        return path.exists() and path.is_file()
    return False


def _verify_manifest_integrity(manifest: dict) -> tuple[bool, list[str]]:
    """
    Verify that the manifest's claimed states match actual reality.
    For any family claiming PASS, the proof_bundle must actually exist.
    """
    failures = []
    families = manifest.get("families", [])
    
    for family in families:
        if not isinstance(family, dict):
            continue
        
        family_id = family.get("id", "UNKNOWN")
        is_pass = (
            family.get("closure_state") == "PASS" or
            family.get("opus55_acceptance_state") == "PASS"
        )
        
        if is_pass:
            proof_bundle = family.get("proof_bundle")
            if not proof_bundle:
                failures.append(f"FAMILY_{family_id}_PASS_WITHOUT_PROOF_BUNDLE")
                continue
            
            if isinstance(proof_bundle, str):
                if not _verify_file_exists(proof_bundle):
                    failures.append(f"FAMILY_{family_id}_PROOF_BUNDLE_NOT_FOUND:{proof_bundle}")
            elif isinstance(proof_bundle, list):
                for bundle_path in proof_bundle:
                    if isinstance(bundle_path, str):
                        if not _verify_file_exists(bundle_path):
                            failures.append(f"FAMILY_{family_id}_PROOF_BUNDLE_NOT_FOUND:{bundle_path}")
    
    return (len(failures) == 0, failures)


def _verify_authority_integrity(authority: dict) -> tuple[bool, list[str]]:
    """
    Verify that the authority's claimed states are consistent.
    If terminal is claimed, all required predicates must be true.
    """
    failures = []
    live = authority.get("live_truth", {})
    
    if live.get("terminal") is True:
        required_truths = [
            ("final_donor_deletion_cleanroom_pass", "Donor deletion cleanroom must pass"),
            ("donor_independence_closed", "Donor independence must be closed"),
            ("current_U_empty_proved", "U-empty must be proved"),
            ("selected_cover_complete", "Selected cover must be complete"),
            ("complete_selected_context_ABC_closed", "ABC must be closed"),
        ]
        
        for field, description in required_truths:
            if live.get(field) is not True:
                failures.append(f"TERMINAL_CLAIMED_BUT_{field.upper()}_FALSE:{description}")
    
    return (len(failures) == 0, failures)


def _accepted_family_count(manifest: dict) -> int:
    families = manifest.get("families")
    if not isinstance(families, list):
        return 0
    return sum(
        1
        for family in families
        if isinstance(family, dict)
        and family.get("opus55_acceptance_state") == "PASS"
        and family.get("opus55_acceptance_calibrated") is True
    )


def evaluate(pointer: dict, manifest: dict) -> dict:
    live = pointer.get("live_truth", {}) if isinstance(pointer, dict) else {}
    semantic_failures: list[str] = []
    warnings: list[str] = []
    integrity_failures: list[str] = []

    # =========================================================================
    # INTEGRITY CHECKS - Prevent JSON tampering and gaming
    # =========================================================================
    
    manifest_integrity_ok, manifest_failures = _verify_manifest_integrity(manifest)
    if not manifest_integrity_ok:
        integrity_failures.extend(manifest_failures)
    
    authority_integrity_ok, authority_failures = _verify_authority_integrity(pointer)
    if not authority_integrity_ok:
        integrity_failures.extend(authority_failures)
    
    # =========================================================================
    # SEMANTIC CHECKS - Original gate logic
    # =========================================================================
    
    if live.get("terminal_root_semantics") != MANDATORY_SEMANTICS:
        semantic_failures.append("MANDATORY_TERMINAL_ROOT_SEMANTICS_DRIFT")
    if live.get("universal_trace_not_x_required_for_terminal") is not False:
        semantic_failures.append("OPTIONAL_UNIVERSAL_TRACE_ROUTE_REPROMOTED_TO_MANDATORY")
    if live.get("primary_terminal_scheduler_object") != MANDATORY_ROOT:
        semantic_failures.append("PRIMARY_TERMINAL_SCHEDULER_ROOT_DRIFT")

    closure = evaluate_manifest(manifest if isinstance(manifest, dict) else {}, ROOT)
    closure_achieved = closure.get("achieved") is True
    
    # Terminal is only real if all checks pass
    has_integrity_failures = len(integrity_failures) > 0
    has_semantic_failures = len(semantic_failures) > 0
    terminal_real = not has_semantic_failures and not has_integrity_failures and closure_achieved

    declared_terminal = live.get("terminal") is True
    if declared_terminal and not terminal_real:
        semantic_failures.append(
            "DECLARED_TERMINAL_INCONSISTENT_WITH_FROZEN_PROTOCOL_AND_OWNERSHIP_GATE"
        )
        terminal_real = False
    elif terminal_real and not declared_terminal:
        warnings.append(
            "DECLARED_TERMINAL_FALSE_BUT_FROZEN_PROTOCOL_AND_OWNERSHIP_GATE_TRUE__METADATA_OUT_OF_SYNC"
        )

    blockers = list(dict.fromkeys(semantic_failures + integrity_failures))
    if not closure_achieved:
        blockers.append(MANDATORY_ROOT)

    accepted = _accepted_family_count(manifest)
    owned = int(closure.get("closed_family_count") or 0)
    manifest_family_count = int(closure.get("family_count") or 0)

    pointer_acceptance = live.get("frozen_terminal_family_pass_count")
    pointer_open = live.get("frozen_terminal_family_open_count")
    if type(pointer_acceptance) is int and pointer_acceptance != accepted:
        warnings.append(
            f"POINTER_ACCEPTANCE_COUNT_STALE:{pointer_acceptance}:{accepted}"
        )
    manifest_open = max(manifest_family_count - accepted, 0)
    if type(pointer_open) is int and pointer_open != manifest_open:
        warnings.append(f"POINTER_OPEN_COUNT_STALE:{pointer_open}:{manifest_open}")

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_REALITY_GATE_V3_HARDENED",
        "terminal_real": terminal_real,
        "declared_terminal": declared_terminal,
        "phase": "TERMINAL" if terminal_real else "FROZEN_PROTOCOL_ACCEPTANCE_AND_OWNERSHIP",
        "blockers": blockers,
        "live_research_blockers": [] if terminal_real else [MANDATORY_ROOT],
        "mandatory_terminal_root": MANDATORY_ROOT,
        "mandatory_terminal_semantics": MANDATORY_SEMANTICS,
        "frozen_family_count": manifest_family_count,
        "accepted_family_count": accepted,
        "verified_owned_family_count": owned,
        "open_acceptance_family_count": max(manifest_family_count - accepted, 0),
        "open_ownership_or_acceptance_family_count": max(manifest_family_count - owned, 0),
        "closure_failed_predicates": closure.get("failed_predicates", []),
        "declaration_warnings": warnings,
        "integrity_failures": integrity_failures,
        "optional_stronger_trace_route": {
            "required_for_terminal": False,
            "current_U_empty_proved": live.get("current_U_empty_proved"),
            "selected_cover_complete": live.get("router_registry_real_selected_cover_complete"),
            "abc_closed": live.get("complete_selected_context_ABC_closed"),
            "d_finality_field": live.get("D_finality_closed"),
        },
        "anti_bureaucracy": {
            "universal_trace_not_x_is_optional_stronger_route": True,
            "generator_completeness_is_not_a_mandatory_terminal_prerequisite": True,
            "global_rank_and_resource_potential_are_not_mandatory_terminal_prerequisites": True,
            "residual_complement_unsat_is_not_the_only_terminal_root": True,
            "official_gate_reads_the_frozen_19_family_manifest": True,
        },
        "hardening": {
            "manifest_integrity_verified": manifest_integrity_ok,
            "authority_integrity_verified": authority_integrity_ok,
            "proof_bundle_existence_required": True,
            "tamper_detection_enabled": True,
        },
    }


def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = evaluate(pointer, manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["terminal_real"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
