from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_BOUND_CLAIM_GUARD_V1"
_ALLOWED_STATUSES = {"SUPPORTED", "CONFLICTED", "UNSUPPORTED", "INSUFFICIENT"}


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
    }


def compile_guard(public: Mapping[str, Any]) -> dict[str, Any]:
    task = public.get("task")
    if not isinstance(task, Mapping):
        return _fail("TASK_INVALID")

    claims = task.get("claims")
    evidence = task.get("evidence")
    bindings = task.get("support_bindings")
    if not isinstance(claims, list) or not isinstance(evidence, list) or not isinstance(bindings, list):
        return _fail("NORMALIZED_LISTS_REQUIRED")

    claim_by_id: dict[str, Mapping[str, Any]] = {}
    required: set[str] = set()
    for row in claims:
        if not isinstance(row, Mapping):
            return _fail("CLAIM_ROW_INVALID")
        cid = row.get("claim_id")
        req = row.get("required")
        if not isinstance(cid, str) or not cid or cid in claim_by_id or type(req) is not bool:
            return _fail("CLAIM_ID_OR_REQUIRED_INVALID")
        claim_by_id[cid] = row
        if req:
            required.add(cid)

    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for row in evidence:
        if not isinstance(row, Mapping):
            return _fail("EVIDENCE_ROW_INVALID")
        eid = row.get("evidence_id")
        provenance = row.get("provenance")
        if (
            not isinstance(eid, str)
            or not eid
            or eid in evidence_by_id
            or not isinstance(provenance, list)
            or not provenance
            or any(not isinstance(x, str) or not x for x in provenance)
        ):
            return _fail("EVIDENCE_ID_OR_PROVENANCE_INVALID")
        evidence_by_id[eid] = row

    binding_by_claim: dict[str, dict[str, Any]] = {}
    for row in bindings:
        if not isinstance(row, Mapping):
            return _fail("SUPPORT_BINDING_ROW_INVALID")
        cid = row.get("claim_id")
        status = row.get("status")
        eids = row.get("evidence_ids")
        if not isinstance(cid, str) or cid not in claim_by_id or cid in binding_by_claim:
            return _fail("SUPPORT_BINDING_CLAIM_INVALID")
        if status not in _ALLOWED_STATUSES:
            return _fail("SUPPORT_BINDING_STATUS_INVALID")
        if (
            not isinstance(eids, list)
            or any(not isinstance(x, str) or not x for x in eids)
            or len(set(eids)) != len(eids)
            or any(x not in evidence_by_id for x in eids)
        ):
            return _fail("SUPPORT_BINDING_EVIDENCE_INVALID")
        if status in {"SUPPORTED", "CONFLICTED"} and not eids:
            return _fail("POSITIVE_SUPPORT_REQUIRES_EVIDENCE")
        binding_by_claim[cid] = {
            "status": status,
            "evidence_ids": list(eids),
        }

    claim_to_evidence: dict[str, list[str]] = {}
    claim_to_provenance: dict[str, list[str]] = {}
    uncertainty_claims: list[str] = []
    insufficient_required_claims: list[str] = []
    supported_claims: list[str] = []

    for cid in claim_by_id:
        binding = binding_by_claim.get(cid)
        status = binding["status"] if binding else "INSUFFICIENT"
        eids = binding["evidence_ids"] if binding else []

        if cid in required and status not in {"SUPPORTED", "CONFLICTED"}:
            insufficient_required_claims.append(cid)

        if status in {"SUPPORTED", "CONFLICTED"}:
            supported_claims.append(cid)
            claim_to_evidence[cid] = list(eids)
            provenance: list[str] = []
            seen: set[str] = set()
            for eid in eids:
                for source in evidence_by_id[eid]["provenance"]:
                    if source not in seen:
                        seen.add(source)
                        provenance.append(source)
            if not provenance:
                return _fail("SUPPORTED_CLAIM_PROVENANCE_EMPTY")
            claim_to_provenance[cid] = provenance
            if status == "CONFLICTED":
                uncertainty_claims.append(cid)

    ready = not insufficient_required_claims
    return {
        "schema": SCHEMA,
        "status": "READY_FOR_SYNTHESIS" if ready else "FAIL_CLOSED_INSUFFICIENT_REQUIRED_SUPPORT",
        "reason": "ALL_REQUIRED_CLAIMS_HAVE_BOUND_SUPPORT" if ready else "REQUIRED_SUPPORT_MISSING_OR_INSUFFICIENT",
        "supported_claims": supported_claims,
        "insufficient_required_claims": insufficient_required_claims,
        "uncertainty_claims": uncertainty_claims,
        "claim_to_evidence": claim_to_evidence,
        "claim_to_provenance": claim_to_provenance,
        "terminal_authority": False,
    }


def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    return compile_guard(public)
