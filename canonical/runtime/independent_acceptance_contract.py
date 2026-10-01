"""Fail-closed acceptance-contract validation for fresh benchmark sessions.

The controller uses this before any builder command. The contract describes
observable behavior and independent acceptance consequences. It does not solve
semantic rule extraction; it makes omissions and builder-derived self-checks
explicit and machine-rejectable.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA = "BRAIN_FAST_BURST_ACCEPTANCE_MODEL_V1"
REQUIRED_BEHAVIOR_FIELDS = (
    "behavior_id",
    "inputs",
    "environment_state",
    "allowed_information",
    "required_output_or_action",
    "success_condition",
    "failure_condition",
    "terminal_consequence",
    "verification_route",
    "dependency_boundary",
    "scope",
)
ALLOWED_CHECK_KINDS = {
    "EXACT_ORACLE",
    "INVARIANT",
    "METAMORPHIC",
    "BOUNDARY",
    "ALTERNATIVE_INTERPRETATION",
    "EXTERNAL_AUTHORITY",
    "DIMENSIONAL_OR_TYPE",
    "LINEAGE_COVERAGE",
}
FORBIDDEN_INDEPENDENCE = {"BUILDER_RECOMPUTE", "BUILDER_DERIVED_EXPECTATION"}


LEASE_SCHEMA = "BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1"

def validate_lease_authorization(payload: Any, session_id: str, task: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["LEASE_PAYLOAD_NOT_OBJECT"]
    if payload.get("schema") != LEASE_SCHEMA:
        errors.append("LEASE_SCHEMA_INVALID")
    if payload.get("session_id") != session_id:
        errors.append("LEASE_SESSION_MISMATCH")
    if payload.get("task") != task:
        errors.append("LEASE_TASK_MISMATCH")
    if payload.get("authorization") is not True:
        errors.append("LEASE_AUTHORIZATION_FALSE")
    if payload.get("lease_merged_to_main") is not True:
        errors.append("LEASE_NOT_CONFIRMED_MERGED_TO_MAIN")
    commit = payload.get("canonical_brain_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        errors.append("CANONICAL_BRAIN_COMMIT_INVALID")
    path = payload.get("canonical_lease_path")
    if not isinstance(path, str) or not path.startswith("canonical/governance/") or not path.endswith(".json"):
        errors.append("CANONICAL_LEASE_PATH_INVALID")
    rank = payload.get("sample_rank")
    if not isinstance(rank, int) or rank < 1:
        errors.append("SAMPLE_RANK_INVALID")
    return errors

def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def canonical_payload_hash(payload: Mapping[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("acceptance_contract_sha256", None)
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def validate_acceptance_payload(payload: Any, session_id: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["PAYLOAD_NOT_OBJECT"]
    if payload.get("schema") != SCHEMA:
        errors.append("SCHEMA_INVALID")
    if payload.get("session_id") != session_id:
        errors.append("SESSION_MISMATCH")
    if payload.get("frozen_before_builder") is not True:
        errors.append("NOT_FROZEN_BEFORE_BUILDER")
    if payload.get("solution_tests_verifier_exposed") is not False:
        errors.append("HIDDEN_AUTHORITY_BOUNDARY_NOT_CLEAN")

    behavior = payload.get("behavioral_contract")
    if not isinstance(behavior, dict):
        errors.append("BEHAVIORAL_CONTRACT_MISSING")
    else:
        for field in REQUIRED_BEHAVIOR_FIELDS:
            if not _nonempty_text(behavior.get(field)):
                errors.append(f"BEHAVIOR_FIELD_MISSING:{field}")

    reqs = payload.get("requirements")
    requirement_ids: list[str] = []
    if not isinstance(reqs, list) or not reqs:
        errors.append("REQUIREMENTS_MISSING")
    else:
        seen: set[str] = set()
        for i, req in enumerate(reqs):
            if not isinstance(req, dict):
                errors.append(f"REQUIREMENT_INVALID:{i}")
                continue
            rid = req.get("id")
            if not _nonempty_text(rid):
                errors.append(f"REQUIREMENT_ID_MISSING:{i}")
                continue
            if rid in seen:
                errors.append(f"REQUIREMENT_ID_DUPLICATE:{rid}")
            seen.add(rid)
            if req.get("applicable", True) is not True:
                justification = req.get("exclusion_justification")
                if not _nonempty_text(justification):
                    errors.append(f"EXCLUDED_REQUIREMENT_UNJUSTIFIED:{rid}")
                continue
            requirement_ids.append(rid)
            if not _nonempty_text(req.get("statement")):
                errors.append(f"REQUIREMENT_STATEMENT_MISSING:{rid}")
            if not _nonempty_text(req.get("source_basis")):
                errors.append(f"REQUIREMENT_SOURCE_BASIS_MISSING:{rid}")

    checks = payload.get("acceptance_checks")
    covered: set[str] = set()
    if not isinstance(checks, list) or not checks:
        errors.append("ACCEPTANCE_CHECKS_MISSING")
    else:
        seen_checks: set[str] = set()
        for i, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"ACCEPTANCE_CHECK_INVALID:{i}")
                continue
            cid = check.get("id")
            if not _nonempty_text(cid):
                errors.append(f"ACCEPTANCE_CHECK_ID_MISSING:{i}")
                continue
            if cid in seen_checks:
                errors.append(f"ACCEPTANCE_CHECK_ID_DUPLICATE:{cid}")
            seen_checks.add(cid)
            kind = check.get("kind")
            if kind not in ALLOWED_CHECK_KINDS:
                errors.append(f"ACCEPTANCE_CHECK_KIND_INVALID:{cid}")
            if not _nonempty_text(check.get("predicted_consequence")):
                errors.append(f"PREDICTED_CONSEQUENCE_MISSING:{cid}")
            if not _nonempty_text(check.get("evidence_basis")):
                errors.append(f"EVIDENCE_BASIS_MISSING:{cid}")
            independence = check.get("independence_class")
            if not _nonempty_text(independence):
                errors.append(f"INDEPENDENCE_CLASS_MISSING:{cid}")
            elif independence in FORBIDDEN_INDEPENDENCE:
                errors.append(f"CHECK_NOT_INDEPENDENT:{cid}")
            covers = check.get("covers_requirements")
            if not isinstance(covers, list) or not covers:
                errors.append(f"CHECK_REQUIREMENT_COVERAGE_MISSING:{cid}")
            else:
                for rid in covers:
                    if _nonempty_text(rid):
                        covered.add(rid)

    for rid in requirement_ids:
        if rid not in covered:
            errors.append(f"REQUIREMENT_NOT_COVERED:{rid}")
    return errors

def required_check_ids(payload: Mapping[str, Any]) -> set[str]:
    checks = payload.get("acceptance_checks") or []
    return {
        str(c["id"])
        for c in checks
        if isinstance(c, dict) and _nonempty_text(c.get("id"))
    }

def terminal_acceptance_errors(
    terminal_payload: Mapping[str, Any],
    acceptance_payload: Mapping[str, Any],
    acceptance_hash: str,
) -> list[str]:
    errors: list[str] = []
    if terminal_payload.get("acceptance_contract_sha256") != acceptance_hash:
        errors.append("ACCEPTANCE_CONTRACT_HASH_MISMATCH")
    required = required_check_ids(acceptance_payload)
    criteria = terminal_payload.get("acceptance_criteria")
    if not isinstance(criteria, list):
        return errors + ["ACCEPTANCE_CRITERIA_EVIDENCE_MISSING"]
    by_id = {
        c.get("id"): c
        for c in criteria
        if isinstance(c, dict) and _nonempty_text(c.get("id"))
    }
    for cid in sorted(required):
        item = by_id.get(cid)
        if item is None:
            errors.append(f"FROZEN_ACCEPTANCE_CHECK_MISSING:{cid}")
        elif item.get("status") != "PASS" or not item.get("evidence"):
            errors.append(f"FROZEN_ACCEPTANCE_CHECK_NOT_PASS:{cid}")
    return errors

def audit_required_graph(
    required_nodes: Iterable[str],
    required_edges: Iterable[tuple[str, str]],
    candidate_nodes: Iterable[str],
    candidate_edges: Iterable[tuple[str, str]],
    *,
    inputs: Iterable[str] = (),
    outputs: Iterable[str] = (),
) -> dict[str, Any]:
    """Deterministic coverage audit after semantic requirements are structured."""
    rn=set(required_nodes); re=set(tuple(e) for e in required_edges)
    cn=set(candidate_nodes); ce=set(tuple(e) for e in candidate_edges)
    missing_nodes=sorted(rn-cn)
    missing_edges=sorted(re-ce)
    adj: dict[str,set[str]]={}
    for a,b in ce:
        adj.setdefault(a,set()).add(b)

    def reachable(a: str,b: str)->bool:
        if a==b:
            return True
        todo=[a]; seen={a}
        while todo:
            cur=todo.pop()
            for nxt in adj.get(cur,()):
                if nxt==b:
                    return True
                if nxt not in seen:
                    seen.add(nxt); todo.append(nxt)
        return False

    unreachable=[]
    for i in inputs:
        for o in outputs:
            if i in rn and o in rn and not reachable(i,o):
                unreachable.append((i,o))
    return {
        "pass": not missing_nodes and not missing_edges and not unreachable,
        "missing_nodes":missing_nodes,
        "missing_edges":missing_edges,
        "unreachable_input_output_pairs":sorted(unreachable),
    }
