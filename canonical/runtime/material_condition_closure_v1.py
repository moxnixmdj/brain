"""Dynamic material-condition closure compiler for Project Brain.

This is deliberately orthogonal to the family acceptance predicate registry.
A family can be accepted on its frozen family protocol while a material
cross-cutting/domain condition remains unproved. Conversely, adding a new
condition never requires changing a magic denominator in this code.

Terminal condition finality requires:
1) every registered material condition has an explicit PROVED + scope_complete
   evidence binding, and
2) the bounded source universe itself is independently sealed.

The compiler is projection-only: it creates no evidence or credit.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MATERIAL_CONDITION_CLOSURE_VERDICT_V1"
PROVED = "PROVED"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "condition_count": 0,
        "proved_condition_count": 0,
        "open_condition_count": 0,
        "proved_conditions": [],
        "open_conditions": [],
        "source_universe_sealed": False,
        "terminal_condition_gate_pass": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def compile_material_condition_closure(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    envelope: Mapping[str, Any],
,
    verified_source_universe_receipt_sha: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    families = {
        row.get("id")
        for row in envelope.get("families", [])
        if isinstance(row, Mapping) and isinstance(row.get("id"), str) and row.get("id")
    }
    if not families:
        errors.append("TARGET_ENVELOPE_EMPTY_OR_INVALID")

    rows = registry.get("conditions")
    claims = evidence.get("claims")
    if not isinstance(rows, list):
        return _fail("CONDITIONS_NOT_LIST")
    if not isinstance(claims, list):
        return _fail("CLAIMS_NOT_LIST")

    condition_by_id: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"CONDITION_{i}_INVALID")
            continue
        cid = row.get("id")
        kind = row.get("kind")
        cfamilies = row.get("families")
        if not isinstance(cid, str) or not cid:
            errors.append(f"CONDITION_{i}_ID_INVALID")
            continue
        if cid in condition_by_id:
            errors.append(f"DUPLICATE_CONDITION:{cid}")
            continue
        if not isinstance(kind, str) or not kind:
            errors.append(f"CONDITION_KIND_INVALID:{cid}")
        if not isinstance(cfamilies, list) or not cfamilies:
            errors.append(f"CONDITION_FAMILIES_INVALID:{cid}")
        elif any(not isinstance(f, str) or f not in families for f in cfamilies):
            errors.append(f"CONDITION_FAMILY_OUTSIDE_TARGET_ENVELOPE:{cid}")
        condition_by_id[cid] = row

    claim_by_id: dict[str, Mapping[str, Any]] = {}
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_{i}_INVALID")
            continue
        cid = claim.get("condition_id")
        if not isinstance(cid, str) or cid not in condition_by_id:
            errors.append(f"CLAIM_UNKNOWN_CONDITION:{cid}")
            continue
        if cid in claim_by_id:
            errors.append(f"DUPLICATE_CLAIM:{cid}")
            continue
        claim_by_id[cid] = claim

    source_universe = registry.get("source_universe")
    if not isinstance(source_universe, Mapping):
        errors.append("SOURCE_UNIVERSE_MISSING")
        source_sealed = False
    else:
        source_sealed = source_universe.get("sealed") is True
        if source_sealed:
            receipt = source_universe.get("independent_seal_receipt")
            if not isinstance(receipt, Mapping):
                errors.append("SOURCE_UNIVERSE_SEALED_WITHOUT_STRUCTURED_INDEPENDENT_RECEIPT")
            else:
                path = receipt.get("path")
                declared_sha = receipt.get("git_blob_sha")
                state = receipt.get("state")
                if not isinstance(path, str) or not path:
                    errors.append("SOURCE_UNIVERSE_SEAL_RECEIPT_PATH_INVALID")
                if (
                    not isinstance(declared_sha, str)
                    or len(declared_sha) != 40
                    or any(ch not in "0123456789abcdef" for ch in declared_sha.lower())
                ):
                    errors.append("SOURCE_UNIVERSE_SEAL_RECEIPT_SHA_INVALID")
                if state != "INDEPENDENT_PASS":
                    errors.append("SOURCE_UNIVERSE_SEAL_RECEIPT_NOT_INDEPENDENT_PASS")
                if verified_source_universe_receipt_sha != declared_sha:
                    errors.append("SOURCE_UNIVERSE_SEAL_RECEIPT_BLOB_NOT_VERIFIED")

    if errors:
        return _fail(*errors)

    proved: set[str] = set()
    for cid in condition_by_id:
        claim = claim_by_id.get(cid)
        if (
            isinstance(claim, Mapping)
            and claim.get("state") == PROVED
            and claim.get("scope_complete") is True
        ):
            proved.add(cid)

    all_ids = set(condition_by_id)
    opened = all_ids - proved
    gate = not opened and source_sealed

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "condition_count": len(all_ids),
        "proved_condition_count": len(proved),
        "open_condition_count": len(opened),
        "proved_conditions": sorted(proved),
        "open_conditions": sorted(opened),
        "source_universe_sealed": source_sealed,
        "terminal_condition_gate_pass": gate,
        "legacy_atomic_predicate_denominator_sufficient_for_terminal_finality": False,
        "rule": (
            "TERMINAL_CONDITION_FINALITY_REQUIRES_ALL_REGISTERED_CONDITIONS_"
            "PROVED_SCOPE_COMPLETE_AND_SOURCE_UNIVERSE_INDEPENDENTLY_SEALED"
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
