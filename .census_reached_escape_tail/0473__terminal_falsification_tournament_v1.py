from __future__ import annotations

import json
import math
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_TERMINAL_FALSIFICATION_TOURNAMENT_V1"
ACTIVE_INTERFACES = {
    "EXTERNAL_RESULT_OR_ACCESS",
    "UNIVERSAL_SCOPE_AND_COMPOSITION",
    "BEHAVIORAL_QUOTIENT_AND_TRANSFER",
}
DORMANT_INTERFACES = {"TARGET_TUPLE_BINDING"}

VALID_QUANTIFIERS = {"UNIVERSAL", "EXISTENTIAL", "POINTWISE", "STRUCTURAL", "EXTERNAL_FACT"}
VALID_FALSIFIER_STATUS = {
    "PENDING",
    "PASS_NO_COUNTEREXAMPLE",
    "COUNTEREXAMPLE_FOUND",
    "INAPPLICABLE",
}
VALID_FALSIFIER_KINDS = {
    "CONSTRUCTIVE_COUNTEREXAMPLE",
    "NEGATIVE_CANARY",
    "BYPASS_SEARCH",
    "SCOPE_COUNTERMODEL",
    "STRONGER_PROOF_SUBSTITUTION",
    "PUBLIC_EQUIVALENCE",
    "DECOMPOSITION_ENTAILMENT",
    "UNMAPPED_TRANSFORM_SEARCH",
    "NECESSITY_COUNTERMODEL",
    "SUFFICIENCY_COUNTERMODEL",
    "EXHAUSTIVE_FINITE_SEARCH",
    "FORMAL_CONTRADICTION",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")

INTERFACE_REQUIRED_ATTACKS = {
    "EXTERNAL_RESULT_OR_ACCESS": {
        "STRONGER_PROOF_SUBSTITUTION",
        "PUBLIC_EQUIVALENCE",
        "DECOMPOSITION_ENTAILMENT",
    },
    "UNIVERSAL_SCOPE_AND_COMPOSITION": {
        "BYPASS_SEARCH",
        "SCOPE_COUNTERMODEL",
        "CONSTRUCTIVE_COUNTEREXAMPLE",
        "NEGATIVE_CANARY",
    },
    "BEHAVIORAL_QUOTIENT_AND_TRANSFER": {
        "UNMAPPED_TRANSFORM_SEARCH",
        "CONSTRUCTIVE_COUNTEREXAMPLE",
        "SCOPE_COUNTERMODEL",
    },
}


def _nonempty_str(v: Any, name: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return v.strip()


def _unique_strs(v: Any, name: str) -> list[str]:
    if not isinstance(v, list) or not v:
        raise ValueError(f"{name} must be a non-empty list")
    out = [_nonempty_str(x, name) for x in v]
    if len(out) != len(set(out)):
        raise ValueError(f"{name} contains duplicates")
    return out


def _finite_nonnegative(v: Any, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{name} must be a finite non-negative number")
    x = float(v)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return x


def _positive_cost(v: Any, name: str) -> float:
    x = _finite_nonnegative(v, name)
    if x <= 0:
        raise ValueError(f"{name} must be > 0")
    return x


def _wake_receipt_valid(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    try:
        path = _nonempty_str(receipt.get("path"), "wake_receipt.path")
        sha = _nonempty_str(receipt.get("git_blob_sha"), "wake_receipt.git_blob_sha")
        trigger = _nonempty_str(receipt.get("trigger"), "wake_receipt.trigger")
    except ValueError:
        return False
    return path.startswith("canonical/") and bool(SHA40.fullmatch(sha)) and len(trigger) >= 3


def _parse_falsifier(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"falsifiers[{idx}] must be an object")
    fid = _nonempty_str(raw.get("id"), f"falsifiers[{idx}].id")
    kind = _nonempty_str(raw.get("kind"), f"falsifiers[{idx}].kind")
    if kind not in VALID_FALSIFIER_KINDS:
        raise ValueError(f"falsifiers[{idx}].kind invalid")
    cost = _positive_cost(raw.get("cost_units"), f"falsifiers[{idx}].cost_units")
    status = _nonempty_str(raw.get("status"), f"falsifiers[{idx}].status")
    if status not in VALID_FALSIFIER_STATUS:
        raise ValueError(f"falsifiers[{idx}].status invalid")
    decisive = raw.get("decisive")
    if decisive is not True:
        raise ValueError(f"falsifiers[{idx}].decisive must be true")
    receipt = raw.get("receipt")
    if status in {"PASS_NO_COUNTEREXAMPLE", "COUNTEREXAMPLE_FOUND"}:
        if not isinstance(receipt, dict):
            raise ValueError(f"falsifiers[{idx}].receipt required for completed falsifier")
        sha = receipt.get("git_blob_sha")
        path = receipt.get("path")
        if not isinstance(path, str) or not path.startswith("canonical/"):
            raise ValueError(f"falsifiers[{idx}].receipt.path invalid")
        if not isinstance(sha, str) or not SHA40.fullmatch(sha):
            raise ValueError(f"falsifiers[{idx}].receipt.git_blob_sha invalid")
    if status == "INAPPLICABLE":
        _nonempty_str(raw.get("reason"), f"falsifiers[{idx}].reason")
    return {
        "id": fid,
        "kind": kind,
        "cost_units": cost,
        "status": status,
        "receipt": receipt,
    }


def _proposal(raw: Any, idx: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"proposals[{idx}] must be an object")
    pid = _nonempty_str(raw.get("id"), f"proposals[{idx}].id")
    interface = _nonempty_str(raw.get("interface"), f"proposals[{idx}].interface")
    targets = _unique_strs(raw.get("target_obligations"), f"proposals[{idx}].target_obligations")
    claim = raw.get("claim")
    if not isinstance(claim, dict):
        raise ValueError(f"proposals[{idx}].claim must be an object")
    claim_id = _nonempty_str(claim.get("id"), f"proposals[{idx}].claim.id")
    statement = _nonempty_str(claim.get("statement"), f"proposals[{idx}].claim.statement")
    quantifier = _nonempty_str(claim.get("quantifier"), f"proposals[{idx}].claim.quantifier")
    if quantifier not in VALID_QUANTIFIERS:
        raise ValueError(f"proposals[{idx}].claim.quantifier invalid")
    falsifiers_raw = raw.get("falsifiers")
    if not isinstance(falsifiers_raw, list) or not falsifiers_raw:
        raise ValueError(f"proposals[{idx}].falsifiers must be a non-empty list")
    falsifiers = [_parse_falsifier(x, j) for j, x in enumerate(falsifiers_raw)]
    if len({f["id"] for f in falsifiers}) != len(falsifiers):
        raise ValueError(f"proposals[{idx}].falsifiers contain duplicate ids")
    action_cost = _positive_cost(raw.get("action_cost_units"), f"proposals[{idx}].action_cost_units")
    expected = raw.get("expected_closure_count")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        raise ValueError(f"proposals[{idx}].expected_closure_count must be a non-negative integer")
    requires_fresh = raw.get("requires_fresh_reality", False)
    if not isinstance(requires_fresh, bool):
        raise ValueError(f"proposals[{idx}].requires_fresh_reality must be boolean")
    fresh_authority = raw.get("fresh_reality_authority", False)
    if not isinstance(fresh_authority, bool):
        raise ValueError(f"proposals[{idx}].fresh_reality_authority must be boolean")

    route_state = "ACTIVE"
    if interface not in ACTIVE_INTERFACES:
        if _wake_receipt_valid(raw.get("wake_receipt")):
            route_state = "WOKEN_BY_CONTENT_ADDRESSED_RECEIPT"
        else:
            route_state = "OFF_FRONTIER_DENY"

    return {
        "id": pid,
        "interface": interface,
        "target_obligations": targets,
        "claim": {"id": claim_id, "statement": statement, "quantifier": quantifier},
        "falsifiers": falsifiers,
        "action_cost_units": action_cost,
        "expected_closure_count": expected,
        "requires_fresh_reality": requires_fresh,
        "fresh_reality_authority": fresh_authority,
        "route_state": route_state,
        "wake_receipt": raw.get("wake_receipt"),
    }


def _evaluate_one(p: dict[str, Any]) -> dict[str, Any]:
    base = {
        "id": p["id"],
        "interface": p["interface"],
        "target_obligations": p["target_obligations"],
        "proof_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    if p["route_state"] == "OFF_FRONTIER_DENY":
        return {**base, "status": "DENY_OFF_FRONTIER_NO_WAKE_RECEIPT", "admitted_action": None}

    kinds = {f["kind"] for f in p["falsifiers"]}
    required = INTERFACE_REQUIRED_ATTACKS.get(p["interface"])
    if required is not None and not (kinds & required):
        return {
            **base,
            "status": "DENY_MISSING_INTERFACE_SPECIFIC_ATTACK",
            "required_attack_one_of": sorted(required),
            "admitted_action": None,
        }

    counterexamples = [f for f in p["falsifiers"] if f["status"] == "COUNTEREXAMPLE_FOUND"]
    if counterexamples:
        return {
            **base,
            "status": "KILLED_BY_VERIFIED_COUNTEREXAMPLE",
            "killer_falsifiers": [f["id"] for f in counterexamples],
            "admitted_action": None,
        }

    pending = [f for f in p["falsifiers"] if f["status"] == "PENDING"]
    if pending:
        chosen = min(pending, key=lambda f: (f["cost_units"], f["id"]))
        leverage = len(p["target_obligations"]) / chosen["cost_units"]
        return {
            **base,
            "status": "MUST_FALSIFY_FIRST",
            "survival_is_proof": False,
            "admitted_action": {
                "kind": "RUN_FALSIFIER",
                "falsifier_id": chosen["id"],
                "cost_units": chosen["cost_units"],
                "leverage": leverage,
            },
        }

    if p["requires_fresh_reality"] and not p["fresh_reality_authority"]:
        return {
            **base,
            "status": "SURVIVED_FALSIFICATION__BLOCKED_ON_FRESH_REALITY_AUTHORITY",
            "survival_is_proof": False,
            "admitted_action": None,
        }

    leverage = max(p["expected_closure_count"], 1) / p["action_cost_units"]
    return {
        **base,
        "status": "SURVIVES_FALSIFICATION__ELIGIBLE_FOR_EXECUTION",
        "survival_is_proof": False,
        "admitted_action": {
            "kind": "EXECUTE_SURVIVOR",
            "cost_units": p["action_cost_units"],
            "expected_closure_count": p["expected_closure_count"],
            "leverage": leverage,
        },
    }


def evaluate_tournament(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["INPUT_NOT_OBJECT"], "terminal_credit_delta": 0}
    try:
        tournament_id = _nonempty_str(data.get("tournament_id"), "tournament_id")
        terminal_state_sha = _nonempty_str(data.get("terminal_state_git_blob_sha"), "terminal_state_git_blob_sha")
        if not SHA40.fullmatch(terminal_state_sha):
            raise ValueError("terminal_state_git_blob_sha must be 40 lowercase hex")
        raw = data.get("proposals")
        if not isinstance(raw, list) or not raw:
            raise ValueError("proposals must be a non-empty list")
        proposals = [_proposal(p, i) for i, p in enumerate(raw)]
        ids = [p["id"] for p in proposals]
        if len(ids) != len(set(ids)):
            raise ValueError("proposal ids must be unique")
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "terminal_credit_delta": 0,
            "fresh_terminal_evidence_consumed": 0,
        }

    results = [_evaluate_one(p) for p in proposals]
    actionable = [r for r in results if r["admitted_action"] is not None]
    actionable.sort(
        key=lambda r: (
            0 if r["admitted_action"]["kind"] == "RUN_FALSIFIER" else 1,
            -r["admitted_action"]["leverage"],
            r["admitted_action"]["cost_units"],
            r["id"],
        )
    )
    selected = actionable[0] if actionable else None
    return {
        "schema": SCHEMA,
        "tournament_id": tournament_id,
        "status": "PASS__TOURNAMENT_COMPILED_FAIL_CLOSED",
        "terminal_state_git_blob_sha": terminal_state_sha,
        "proposal_results": results,
        "selected_next_action": None if selected is None else {
            "proposal_id": selected["id"],
            **selected["admitted_action"],
        },
        "rules": [
            "COUNTEREXAMPLE_KILLS_CLAIM",
            "SURVIVAL_IS_NOT_PROOF",
            "CHEAPEST_DECISIVE_FALSIFIER_PRECEDES_MAIN_EXECUTION",
            "OFF_FRONTIER_WORK_REQUIRES_CONTENT_ADDRESSED_WAKE_RECEIPT",
            "FRESH_REALITY_REQUIRES_EXPLICIT_AUTHORITY",
            "NO_TOURNAMENT_RESULT_GRANTS_TERMINAL_ACCEPTANCE_FAMILY_OR_OWNERSHIP_CREDIT",
        ],
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "fresh_terminal_evidence_consumed": 0,
    }


def main() -> int:
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ns = ap.parse_args()
    out = evaluate_tournament(json.loads(ns.input.read_text(encoding="utf-8")))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
