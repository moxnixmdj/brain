"""Source-aligned semantic proof checker v3.

V3 preserves v2 source proofs and adds one narrow primitive for exact values from a
content-addressed typed context. The typed context does not authenticate itself:
the caller must supply an expected SHA-256 that is bound by a separate authority.
This module checks exact equality only and never infers domain meaning from field
names. It has no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof as verify_v2

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V3"
_TYPES = {"BOOL", "INT", "STRING", "DECIMAL_STRING"}
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def typed_context_sha256(context: Mapping[str, Any]) -> str:
    return sha256(_canon(context).encode("utf-8")).hexdigest()


def _type_ok(kind: str, value: Any) -> bool:
    if kind == "BOOL":
        return isinstance(value, bool)
    if kind == "INT":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "STRING":
        return isinstance(value, str)
    if kind == "DECIMAL_STRING":
        return isinstance(value, str) and _DECIMAL.fullmatch(value) is not None
    return False


def _value_digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _field_atom(schema_id: str, field_name: str, field_type: str, value: Any) -> str:
    return (
        f"TYPED_FIELD::{schema_id}::{field_name}::{field_type}::"
        f"{_value_digest(value)}"
    )


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    base_claims = []
    typed_claims = []
    seen: set[str] = set()
    errors: list[str] = []
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}")
            continue
        seen.add(cid)
        if claim.get("kind") == "TYPED_FIELD_VALUE":
            typed_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v2(source_text, source_id=source_id, claims=base_claims)
    if base.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["V2_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    context_digest = None
    schema_id = None
    fields: Mapping[str, Any] = {}

    if typed_claims:
        if not isinstance(typed_context, Mapping):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["TYPED_CONTEXT_REQUIRED_FOR_TYPED_FIELD_CLAIMS"],
                "base_proof": base,
                "terminal_authority": False,
            }
        if not isinstance(expected_typed_context_sha256, str) or len(expected_typed_context_sha256) != 64:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["EXPECTED_TYPED_CONTEXT_SHA256_REQUIRED"],
                "base_proof": base,
                "terminal_authority": False,
            }
        context_digest = typed_context_sha256(typed_context)
        if context_digest != expected_typed_context_sha256:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH"],
                "typed_context_sha256": context_digest,
                "terminal_authority": False,
            }
        schema_id = typed_context.get("schema_id")
        fields = typed_context.get("fields")
        if not isinstance(schema_id, str) or not schema_id.strip():
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["TYPED_CONTEXT_SCHEMA_ID_INVALID"],
                "terminal_authority": False,
            }
        if not isinstance(fields, Mapping):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "errors": ["TYPED_CONTEXT_FIELDS_INVALID"],
                "terminal_authority": False,
            }

    for claim in typed_claims:
        cid = str(claim["claim_id"])
        claimed_schema = claim.get("schema_id")
        field_name = claim.get("field_name")
        field_type = claim.get("field_type")
        claimed_value = claim.get("value")

        if claimed_schema != schema_id:
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_SCHEMA_MISMATCH"})
            continue
        if not isinstance(field_name, str) or not field_name:
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_NAME_INVALID"})
            continue
        if field_type not in _TYPES:
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_TYPE_UNSUPPORTED"})
            continue

        row = fields.get(field_name)
        if not isinstance(row, Mapping):
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_NOT_PRESENT"})
            continue
        actual_type = row.get("type")
        actual_value = row.get("value")
        if actual_type != field_type:
            rejected.append({
                "claim_id": cid,
                "reason": "TYPED_FIELD_DECLARED_TYPE_MISMATCH",
                "actual_type": actual_type,
                "claimed_type": field_type,
            })
            continue
        if not _type_ok(str(actual_type), actual_value):
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_CONTEXT_VALUE_INVALID"})
            continue
        if not _type_ok(str(field_type), claimed_value):
            rejected.append({"claim_id": cid, "reason": "TYPED_FIELD_CLAIM_VALUE_INVALID"})
            continue
        if claimed_value != actual_value:
            rejected.append({
                "claim_id": cid,
                "reason": "TYPED_FIELD_VALUE_MISMATCH",
                "actual_value_sha256": _value_digest(actual_value),
                "claimed_value_sha256": _value_digest(claimed_value),
            })
            continue

        atom = _field_atom(str(schema_id), field_name, str(field_type), actual_value)
        constraint = {"op": "ATOM", "id": atom}
        accepted.append({
            "claim_id": cid,
            "kind": "TYPED_FIELD_VALUE",
            "schema_id": schema_id,
            "field_name": field_name,
            "field_type": field_type,
            "value": actual_value,
            "typed_context_sha256": context_digest,
            "constraint": constraint,
        })
        proved.append(constraint)

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "proved_constraint_ids": [c["id"] for c in proved],
        "typed_context_sha256": context_digest,
        "terminal_authority": False,
        "soundness_boundary": (
            "V3_CERTIFIES_ONLY_V2_SOURCE_PRIMITIVES_PLUS_EXACT_VALUES_FROM_A_CONTENT_ADDRESSED_TYPED_CONTEXT;"
            "AUTHORITY_OF_THE_EXPECTED_TYPED_CONTEXT_DIGEST_DOMAIN_MEANING_REFERENCE_RESOLUTION_AND_POLICY_ADEQUACY_REQUIRE_SEPARATE_SOUND_BINDINGS"
        ),
    }
