"""Certified evidence-role binding for a narrow supervisory-finance UNLESS fragment.

The existing finance controller requires rule_evidence_ids and exception_evidence_ids
to contribute to the selected decision, but those role labels are caller supplied.
This gate derives a narrow structural role from exact source spans instead:

    ORDINARY_BRANCH unless EXCEPTION_BRANCH

Evidence spans wholly contained in the left branch are ordinary-branch evidence;
spans wholly contained in the right branch are exception-branch evidence.

This does NOT prove domain-level finance correctness, rule applicability, or whether
the exception is satisfied by case facts. It only prevents arbitrary evidence IDs
from self-declaring a structural rule/exception role for this certified fragment.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "BRAIN_FINANCE_CERTIFIED_UNLESS_EVIDENCE_ROLE_GATE_V1"


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def derive_roles(
    source_text: str,
    *,
    source_id: str,
    evidence_bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"]}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["SOURCE_ID_MISSING"]}
    if not isinstance(evidence_bindings, Sequence) or isinstance(evidence_bindings, (str, bytes)):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["EVIDENCE_BINDINGS_INVALID"]}

    scoped = parse_scope(source_text, source=source_id)
    if scoped.get("status") != "PARSED" or scoped.get("parse", {}).get("relation") != "UNLESS":
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_NOT_IN_CERTIFIED_SINGLE_UNLESS_FRAGMENT"],
            "scope_parse": scoped,
        }

    p = scoped["parse"]
    left_start, left_end = p["left_span"]
    right_start, right_end = p["right_span"]

    errors: list[str] = []
    roles: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for i, row in enumerate(evidence_bindings):
        if not isinstance(row, Mapping):
            errors.append(f"EVIDENCE_BINDING_NOT_OBJECT:{i}")
            continue
        eid = row.get("evidence_id")
        start = row.get("start")
        end = row.get("end")
        digest = row.get("text_sha256")
        if not isinstance(eid, str) or not eid.strip() or eid in seen:
            errors.append(f"EVIDENCE_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        seen.add(eid)
        if (
            not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or start < 0 or end <= start or end > len(source_text)
        ):
            errors.append(f"EVIDENCE_SPAN_INVALID:{eid}")
            continue
        actual = source_text[start:end]
        if not isinstance(digest, str) or digest != _sha(actual):
            errors.append(f"EVIDENCE_SPAN_HASH_MISMATCH:{eid}")
            continue

        if left_start <= start and end <= left_end:
            role = "ORDINARY_BRANCH_EVIDENCE"
        elif right_start <= start and end <= right_end:
            role = "EXCEPTION_BRANCH_EVIDENCE"
        else:
            errors.append(f"EVIDENCE_SPAN_NOT_CONTAINED_IN_ONE_CERTIFIED_BRANCH:{eid}")
            continue

        roles[eid] = role
        normalized.append({
            "evidence_id": eid,
            "start": start,
            "end": end,
            "text_sha256": digest,
            "derived_role": role,
        })

    if errors:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "scope_parse": scoped,
            "derived_roles": roles,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CERTIFIED_UNLESS_STRUCTURAL_EVIDENCE_ROLES",
        "scope_parse": scoped,
        "evidence_bindings": normalized,
        "derived_roles": roles,
        "ordinary_branch_evidence_ids": sorted(eid for eid, role in roles.items() if role == "ORDINARY_BRANCH_EVIDENCE"),
        "exception_branch_evidence_ids": sorted(eid for eid, role in roles.items() if role == "EXCEPTION_BRANCH_EVIDENCE"),
        "terminal_authority": False,
        "soundness_boundary": (
            "PROVES_ONLY_SOURCE_SPAN_MEMBERSHIP_IN_THE_CERTIFIED_UNLESS_BRANCHES;"
            "DOES_NOT_PROVE_RULE_APPLICABILITY_EXCEPTION_SATISFACTION_OR_DOMAIN_TRUTH"
        ),
    }


def validate_supervisory_proposal_roles(
    proposal: Mapping[str, Any],
    role_result: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if role_result.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["ROLE_DERIVATION_NOT_PROVED"],
            "terminal_authority": False,
        }
    if not isinstance(proposal, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["PROPOSAL_NOT_OBJECT"],
            "terminal_authority": False,
        }

    rule_ids = proposal.get("rule_evidence_ids")
    exception_ids = proposal.get("exception_evidence_ids")
    if not isinstance(rule_ids, list) or not rule_ids or any(not isinstance(x, str) or not x for x in rule_ids):
        errors.append("RULE_EVIDENCE_IDS_INVALID")
        rule_ids = []
    if not isinstance(exception_ids, list) or not exception_ids or any(not isinstance(x, str) or not x for x in exception_ids):
        errors.append("EXCEPTION_EVIDENCE_IDS_INVALID")
        exception_ids = []

    ordinary = set(role_result.get("ordinary_branch_evidence_ids") or [])
    exceptions = set(role_result.get("exception_branch_evidence_ids") or [])

    for eid in rule_ids:
        if eid not in ordinary:
            errors.append(f"RULE_EVIDENCE_NOT_DERIVED_FROM_ORDINARY_BRANCH:{eid}")
    for eid in exception_ids:
        if eid not in exceptions:
            errors.append(f"EXCEPTION_EVIDENCE_NOT_DERIVED_FROM_EXCEPTION_BRANCH:{eid}")
    overlap = sorted(set(rule_ids) & set(exception_ids))
    errors.extend(f"EVIDENCE_ID_USED_AS_BOTH_RULE_AND_EXCEPTION:{eid}" for eid in overlap)

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": "PASS__SUPERVISORY_EVIDENCE_ROLES_BOUND_TO_SOURCE_BRANCHES" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "terminal_authority": False,
    }


def configured_finance_supervisory_terminal_decision_v2(
    proposal: Any,
    proof_bundle: Any,
) -> dict[str, Any]:
    if not isinstance(proof_bundle, Mapping):
        return {
            "schema": SCHEMA,
            "accepted": False,
            "status": "TERMINAL_BLOCKED",
            "errors": ["PROOF_BUNDLE_NOT_OBJECT"],
        }
    if not isinstance(proposal, Mapping):
        proposal = {}

    source_text = proof_bundle.get("source_text")
    source_id = proof_bundle.get("source_id")
    bindings = proof_bundle.get("finance_evidence_role_bindings", [])
    role_result = derive_roles(
        source_text if isinstance(source_text, str) else "",
        source_id=source_id if isinstance(source_id, str) else "",
        evidence_bindings=bindings,
    )
    proposal_roles = validate_supervisory_proposal_roles(proposal, role_result)
    if proposal_roles.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "accepted": False,
            "status": "TERMINAL_BLOCKED",
            "errors": ["FINANCE_CERTIFIED_EVIDENCE_ROLE_GATE_FAIL_CLOSED", *(proposal_roles.get("errors") or [])],
            "evidence_role_gate": role_result,
            "proposal_role_validation": proposal_roles,
        }

    from canonical.runtime.finance_proof_carrying_source_gate_v1 import configured_finance_terminal_decision
    downstream = configured_finance_terminal_decision(proposal, proof_bundle)
    out = dict(downstream)
    out["finance_role_gate_schema"] = SCHEMA
    out["evidence_role_gate"] = role_result
    out["proposal_role_validation"] = proposal_roles
    return out
