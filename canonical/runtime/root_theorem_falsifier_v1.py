#!/usr/bin/env python3
"""Fail-closed four-root coverage-completeness classifier.

This module grants no terminal, acceptance, family, capability, or ownership credit.
R1: B_real subseteq B_plus
R2: G_minus subseteq G_real
R3: B_plus subseteq G_minus
R4: proof/realization chain establishing R1-R3 is trustworthy.
"""

from __future__ import annotations

import argparse
import itertools
import json
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

ROOTS = ("R1", "R2", "R3", "R4")

from canonical.runtime.coverage_root_certificate_registry_guard_v1 import validate as validate_root_registry
from canonical.runtime.coverage_root_semantic_receipt_v1 import validate_semantic_root_slot
from canonical.runtime.coverage_root_semantic_receipt_v1 import validate_semantic_root_slot

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_REGISTRY_PATH = REPO_ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
MISSION_PATH = REPO_ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
CANONICAL_POINTER_PATH = REPO_ROOT / "canonical/CANONICAL_POINTER.json"

BINDING_FIELDS = (
    "claim_id", "scope_sha256", "semantics_sha256", "carrier_schema_id",
    "mission_id", "epoch_id", "canonical_generation",
)
HASH_FIELDS = ("claim_id", "scope_sha256", "semantics_sha256")


def _binding_key(value: Any) -> Optional[tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return None
    if any(not isinstance(value.get(k), str) or not value.get(k) for k in BINDING_FIELDS):
        return None
    if any(
        len(value[k]) != 64 or any(c not in "0123456789abcdef" for c in value[k])
        for k in HASH_FIELDS
    ):
        return None
    return tuple(value[k] for k in BINDING_FIELDS)


def evaluate_binding_coherence(data: Mapping[str, Any]) -> Dict[str, Any]:
    expected = _binding_key(data.get("expected_binding"))
    proofs = data.get("root_proofs")
    if expected is None or not isinstance(proofs, Mapping):
        return {"status": "UNKNOWN_FAIL_CLOSED", "coherent": None, "terminal_credit": 0}
    keys = []
    for root in ("R1", "R2", "R3"):
        proof = proofs.get(root)
        if not isinstance(proof, Mapping):
            return {"status": "UNKNOWN_FAIL_CLOSED", "coherent": None, "terminal_credit": 0}
        status = proof.get("status", "UNKNOWN")
        if status == "FALSIFIED":
            return {"status": "R4_ROOT_PROOF_NOT_PROVED", "coherent": False, "terminal_credit": 0}
        if status != "PROVED":
            return {"status": "UNKNOWN_FAIL_CLOSED", "coherent": None, "terminal_credit": 0}
        key = _binding_key(proof.get("binding"))
        if key is None:
            return {"status": "R4_BINDING_INVALID", "coherent": False, "terminal_credit": 0}
        keys.append(key)
    if len(set(keys)) != 1:
        return {"status": "R4_BINDING_MISMATCH", "coherent": False, "terminal_credit": 0}
    if keys[0] != expected:
        return {"status": "R4_STALE_OR_FOREIGN_BINDING", "coherent": False, "terminal_credit": 0}
    return {"status": "PASS_EXACT_BINDING_COHERENCE", "coherent": True, "terminal_credit": 0}


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return sha1(header + payload).hexdigest()


def execute_semantic_root_verifiers(registry: Mapping[str, Any]) -> Dict[str, Any]:
    proved_slots = [
        slot for slot in registry.get("certificate_slots", [])
        if isinstance(slot, Mapping) and slot.get("status") == "PROVED_CURRENT"
    ]
    if not proved_slots:
        return {
            "status": "PASS_NO_PROVED_ROOTS_TO_SEMANTICALLY_VERIFY",
            "pass": True,
            "results": [],
            "terminal_credit": 0,
        }

    active_claim = registry.get("active_claim")
    if not isinstance(active_claim, Mapping):
        return {
            "status": "R4_SEMANTIC_ACTIVE_CLAIM_MISSING",
            "pass": False,
            "results": [],
            "terminal_credit": 0,
        }

    results = []
    for slot in proved_slots:
        checked = validate_semantic_root_slot(REPO_ROOT, slot, active_claim)
        results.append({
            "root_id": slot.get("root_id"),
            "pass": checked.get("pass") is True,
            "status": checked.get("status"),
            "errors": checked.get("errors", []),
        })

    failed = [row for row in results if row["pass"] is not True]
    if failed:
        return {
            "status": "R4_SEMANTIC_ROOT_VERIFICATION_FAILED",
            "pass": False,
            "results": results,
            "terminal_credit": 0,
        }

    if len(results) != len(proved_slots):
        return {
            "status": "R4_SEMANTIC_ROOT_VERIFICATION_INCOMPLETE",
            "pass": False,
            "results": results,
            "terminal_credit": 0,
        }

    return {
        "status": "PASS_EXECUTABLE_SEMANTIC_ROOT_VERIFICATION",
        "pass": True,
        "results": results,
        "terminal_credit": 0,
    }


def evaluate_canonical_registry_authority() -> Dict[str, Any]:
    try:
        registry = json.loads(ROOT_REGISTRY_PATH.read_text(encoding="utf-8"))
        mission_pointer = json.loads(MISSION_PATH.read_text(encoding="utf-8"))
        canonical_pointer = json.loads(CANONICAL_POINTER_PATH.read_text(encoding="utf-8"))
        mission_pointer_sha = _git_blob_sha(MISSION_PATH)
        current_generation = canonical_pointer.get("canonical_generation")
        if not isinstance(current_generation, str) or not current_generation:
            raise ValueError("CANONICAL_GENERATION_MISSING")
        authority_rel = (mission_pointer.get("authoritative_source") or {}).get("path")
        if not isinstance(authority_rel, str) or not authority_rel:
            raise ValueError("MISSION_AUTHORITY_PATH_MISSING")
        authority_path = REPO_ROOT / authority_rel
        mission_authority_sha = _git_blob_sha(authority_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "UNKNOWN_FAIL_CLOSED",
            "authorized": None,
            "error": type(exc).__name__,
            "terminal_credit": 0,
        }

    checked = validate_root_registry(
        registry,
        current_mission_pointer=mission_pointer,
        current_mission_authority_blob_sha=mission_authority_sha,
        current_mission_pointer_blob_sha=mission_pointer_sha,
    )
    if checked["pass"]:
        for slot in registry.get("certificate_slots", []):
            if slot.get("status") != "PROVED_CURRENT":
                continue
            for field in ("certificate", "semantic_verifier", "independent_verification"):
                ref = slot.get(field) or {}
                rel = ref.get("path")
                claimed_sha = ref.get("git_blob_sha")
                if (
                    not isinstance(rel, str)
                    or rel.startswith("/")
                    or ".." in Path(rel).parts
                    or not isinstance(claimed_sha, str)
                ):
                    checked["errors"].append(
                        f"PROVED_SLOT_{field.upper()}_PATH_OR_SHA_INVALID:{slot.get('root_id')}"
                    )
                    continue
                target = REPO_ROOT / rel
                try:
                    actual_sha = _git_blob_sha(target)
                except OSError:
                    checked["errors"].append(
                        f"PROVED_SLOT_{field.upper()}_FILE_MISSING:{slot.get('root_id')}"
                    )
                    continue
                if actual_sha != claimed_sha:
                    checked["errors"].append(
                        f"PROVED_SLOT_{field.upper()}_CONTENT_ADDRESS_MISMATCH:{slot.get('root_id')}"
                    )

            semantic = validate_semantic_root_slot(
                REPO_ROOT,
                slot,
                registry.get("active_claim") or {},
            )
            if semantic.get("pass") is not True:
                checked["errors"].append(
                    f"PROVED_SLOT_SEMANTIC_RECEIPT_INVALID:{slot.get('root_id')}:{semantic.get('status')}"
                )
        if checked["errors"]:
            checked["pass"] = False
            checked["status"] = "FAIL_CLOSED"
            checked["r4_proof_closure"] = False
    if not checked["pass"]:
        return {
            "status": "R4_CANONICAL_REGISTRY_INVALID",
            "authorized": False,
            "registry": checked,
            "active_claim": registry.get("active_claim"),
            "canonical_generation": current_generation,
            "mission_pointer_blob_sha": mission_pointer_sha,
            "terminal_credit": 0,
        }

    semantic = execute_semantic_root_verifiers(registry)
    if semantic["pass"] is not True:
        return {
            "status": semantic["status"],
            "authorized": False,
            "registry": checked,
            "semantic_verification": semantic,
            "active_claim": registry.get("active_claim"),
            "canonical_generation": current_generation,
            "mission_pointer_blob_sha": mission_pointer_sha,
            "terminal_credit": 0,
        }

    if not checked["r4_proof_closure"]:
        return {
            "status": "R4_CANONICAL_ROOT_CERTIFICATES_OPEN",
            "authorized": False,
            "registry": checked,
            "active_claim": registry.get("active_claim"),
            "canonical_generation": current_generation,
            "mission_pointer_blob_sha": mission_pointer_sha,
            "terminal_credit": 0,
        }
    return {
        "status": "PASS_CANONICAL_ROOT_CERTIFICATE_AUTHORITY",
        "authorized": True,
        "registry": checked,
        "active_claim": registry.get("active_claim"),
        "canonical_generation": current_generation,
        "mission_pointer_blob_sha": mission_pointer_sha,
        "terminal_credit": 0,
    }


def evaluate_registry_claim_alignment(
    data: Mapping[str, Any],
    registry_authority: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    authority = registry_authority or evaluate_canonical_registry_authority()
    authorized = authority.get("authorized")
    if authorized is None:
        return {"status": "UNKNOWN_FAIL_CLOSED", "aligned": None, "terminal_credit": 0}
    if authorized is False:
        return {"status": "R4_CANONICAL_REGISTRY_NOT_AUTHORIZED", "aligned": False, "terminal_credit": 0}

    active = authority.get("active_claim")
    expected = data.get("expected_binding")
    if not isinstance(active, Mapping) or _binding_key(expected) is None:
        return {"status": "R4_REGISTRY_CLAIM_BINDING_MISSING", "aligned": False, "terminal_credit": 0}

    mismatches = []
    for local_field, claim_field in (
        ("claim_id", "claim_id"),
        ("scope_sha256", "scope_sha256"),
        ("semantics_sha256", "semantics_sha256"),
        ("epoch_id", "epoch"),
    ):
        if expected.get(local_field) != active.get(claim_field):
            mismatches.append(f"{local_field}:{claim_field}")

    if expected.get("canonical_generation") != authority.get("canonical_generation"):
        mismatches.append("canonical_generation")

    if mismatches:
        return {
            "status": "R4_REGISTRY_CLAIM_MISMATCH",
            "aligned": False,
            "mismatches": mismatches,
            "terminal_credit": 0,
        }
    return {
        "status": "PASS_REGISTRY_CLAIM_ALIGNMENT",
        "aligned": True,
        "terminal_credit": 0,
    }


def _effective_r4(value: Any, data: Mapping[str, Any]) -> Optional[bool]:
    trust = _tri(value)
    coherent = evaluate_binding_coherence(data)["coherent"]
    registry_authority = evaluate_canonical_registry_authority()
    registry = registry_authority["authorized"]
    aligned = evaluate_registry_claim_alignment(data, registry_authority)["aligned"]
    if trust is False or coherent is False or registry is False or aligned is False:
        return False
    if trust is None or coherent is None or registry is None or aligned is None:
        return None
    return True



def _tri(value: Any) -> Optional[bool]:
    if value is True or value is False:
        return value
    if value is None or value == "UNKNOWN":
        return None
    raise ValueError(f"expected true/false/UNKNOWN, got {value!r}")


def _root_statuses(data: Mapping[str, Any]) -> Dict[str, Optional[bool]]:
    r = _tri(data.get("real_behavior", "UNKNOWN"))
    p = _tri(data.get("in_behavior_upper", "UNKNOWN"))
    g = _tri(data.get("in_good_lower", "UNKNOWN"))
    a = _tri(data.get("real_good", "UNKNOWN"))
    t = _tri(data.get("proof_chain_trustworthy", "UNKNOWN"))

    def impl(x: Optional[bool], y: Optional[bool]) -> Optional[bool]:
        if x is False:
            return True
        if x is True and y is not None:
            return y
        if y is True:
            return True
        return None

    return {"R1": impl(r, p), "R2": impl(g, a), "R3": impl(p, g), "R4": _effective_r4(t, data)}


def classify_false_success(data: Mapping[str, Any]) -> Dict[str, Any]:
    success = _tri(data.get("terminal_success_claimed", "UNKNOWN"))
    real_behavior = _tri(data.get("real_behavior", "UNKNOWN"))
    real_good = _tri(data.get("real_good", "UNKNOWN"))
    statuses = _root_statuses(data)

    if None in (success, real_behavior, real_good):
        return {
            "status": "UNKNOWN_FAIL_CLOSED",
            "roots": statuses,
            "terminal_credit": 0,
            "action": "REFINE_OR_OBTAIN_MISSING_PROOF__DO_NOT_PROMOTE",
        }

    false_success = bool(success and real_behavior and not real_good)
    if not false_success:
        return {"status": "NOT_A_FALSE_SUCCESS_WITNESS", "roots": statuses, "terminal_credit": 0}

    failed = [root for root, value in statuses.items() if value is False]
    unknown = [root for root, value in statuses.items() if value is None]

    if failed:
        return {
            "status": "ROOT_FAILURE_WITNESS",
            "failed_roots": failed,
            "unknown_roots": unknown,
            "roots": statuses,
            "terminal_credit": 0,
            "action": "REOPEN_ONLY_AFFECTED_ROOT_DEPENDENCIES",
        }

    if unknown:
        return {
            "status": "UNKNOWN_FAIL_CLOSED",
            "failed_roots": [],
            "unknown_roots": unknown,
            "roots": statuses,
            "terminal_credit": 0,
            "action": "REFINE_OR_OBTAIN_MISSING_PROOF__DO_NOT_PROMOTE",
        }

    return {
        "status": "THEOREM_BINDING_INCONSISTENCY",
        "failed_roots": [],
        "unknown_roots": [],
        "roots": statuses,
        "terminal_credit": 0,
        "action": "REOPEN_R4_AND_SEMANTIC_BINDINGS__DO_NOT_CREATE_NEW_ROOT_BY_DEFAULT",
    }


def evaluate_root_closure(data: Mapping[str, Any]) -> Dict[str, Any]:
    statuses = {root: _tri(data.get(root, "UNKNOWN")) for root in ("R1", "R2", "R3")}
    statuses["R4"] = _effective_r4(data.get("R4", "UNKNOWN"), data)
    failed = [r for r, v in statuses.items() if v is False]
    unknown = [r for r, v in statuses.items() if v is None]
    if failed:
        state = "ROOT_NOT_CLOSED"
    elif unknown:
        state = "REFINE"
    else:
        state = "FOUR_ROOT_PRECONDITIONS_CLOSED"
    return {
        "status": state,
        "roots": statuses,
        "failed_roots": failed,
        "unknown_roots": unknown,
        "terminal_credit": 0,
        "nonclaim": "THIS_CLASSIFIER_DOES_NOT_PROVE_CURRENT_MISSION_ROOTS_OR_TERMINAL_COMPLETION",
    }


def assess_mechanism_admission(data: Mapping[str, Any]) -> Dict[str, Any]:
    closes_gap = bool(data.get("closes_demonstrated_root_gap", False))
    proof_cost_reduction = data.get("proof_cost_reduction", 0)
    tcb_delta = data.get("trusted_core_delta", 0)
    dominance_proved = bool(data.get("tcb_growth_dominance_proved", False))

    if closes_gap:
        return {
            "status": "ADMIT_ROOT_REPAIR_CANDIDATE",
            "terminal_credit": 0,
            "required_next": "VERIFY_ROOT_REPAIR_AND_REGRESSION",
        }

    if proof_cost_reduction and proof_cost_reduction > 0:
        if tcb_delta and tcb_delta > 0 and not dominance_proved:
            return {"status": "REJECT_PENDING_TCB_DOMINANCE_PROOF", "terminal_credit": 0}
        return {"status": "ADMIT_DERIVED_OPTIMIZATION", "terminal_credit": 0}

    return {"status": "REJECT_REDUNDANT_META_MECHANISM", "terminal_credit": 0}


def exhaustive_boolean_theorem_check() -> Dict[str, Any]:
    counterexamples = []
    omission_counterexamples = {"R1": None, "R2": None, "R3": None}

    for r, p, g, a in itertools.product((False, True), repeat=4):
        r1 = (not r) or p
        r2 = (not g) or a
        r3 = (not p) or g
        conclusion = (not r) or a
        valuation = {"r": r, "p": p, "g": g, "a": a}

        if r1 and r2 and r3 and not conclusion:
            counterexamples.append(valuation)

        root_values = {"R1": r1, "R2": r2, "R3": r3}
        for omitted in omission_counterexamples:
            if omission_counterexamples[omitted] is not None:
                continue
            remaining = [v for k, v in root_values.items() if k != omitted]
            if all(remaining) and not conclusion:
                omission_counterexamples[omitted] = valuation

    return {
        "valuations_checked": 16,
        "counterexamples_with_R1_R2_R3": counterexamples,
        "theorem_holds": not counterexamples,
        "omission_counterexamples": omission_counterexamples,
        "each_set_root_load_bearing": all(v is not None for v in omission_counterexamples.values()),
        "note": "R4 is meta-level trust/realization and is outside this pure Boolean implication.",
    }


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("classify-witness", "root-closure", "mechanism-admission"):
        p = sub.add_parser(command)
        p.add_argument("json_path")
    sub.add_parser("self-check")
    args = parser.parse_args(argv)

    if args.command == "classify-witness":
        result = classify_false_success(_load_json(args.json_path))
    elif args.command == "root-closure":
        result = evaluate_root_closure(_load_json(args.json_path))
    elif args.command == "mechanism-admission":
        result = assess_mechanism_admission(_load_json(args.json_path))
    else:
        result = exhaustive_boolean_theorem_check()

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
