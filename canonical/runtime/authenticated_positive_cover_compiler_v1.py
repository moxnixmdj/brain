from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.proof_carrying_semantic_refinement_v6 import (
    resolve_from_source_proof,
)

SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_POSITIVE_COVER_COMPILER_V1"


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "covered_context_count": 0,
        "uncovered_context_ids": [],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def compile_positive_cover(
    manifest: Mapping[str, Any],
    *,
    resolver: Callable[..., Mapping[str, Any]] = resolve_from_source_proof,
) -> dict[str, Any]:
    """Compile a sound positive-policy cover over an already-bound finite manifest.

    This compiler deliberately does *not* prove that the manifest is the whole target
    universe. It proves the narrower statement that every declared context in the
    manifest resolves, through the proof-carrying semantic runtime, to at least one
    independently authenticated Brain-owned adequate policy.

    Global ABC/U-empty credit therefore still requires a separate scope-completeness
    certificate binding this exact manifest digest to the current terminal authority.
    """

    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_MAPPING_REQUIRED")

    scope_id = manifest.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id.strip():
        return _fail("SCOPE_ID_INVALID")

    contexts = manifest.get("contexts")
    if (
        not isinstance(contexts, Sequence)
        or isinstance(contexts, (str, bytes))
        or not contexts
    ):
        return _fail("CONTEXTS_REQUIRED")

    seen: set[str] = set()
    normalized_manifest_rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    uncovered: list[str] = []

    for index, row in enumerate(contexts):
        if not isinstance(row, Mapping):
            return _fail("CONTEXT_ROW_INVALID", details={"index": index})

        context_id = row.get("context_id")
        if (
            not isinstance(context_id, str)
            or not context_id.strip()
            or context_id in seen
        ):
            return _fail(
                "CONTEXT_ID_INVALID_OR_DUPLICATE",
                details={"index": index, "context_id": context_id},
            )
        seen.add(context_id)

        required = {
            "source_text": row.get("source_text"),
            "source_id": row.get("source_id"),
            "claims": row.get("claims"),
            "decision_basis": row.get("decision_basis"),
            "policy_conditions": row.get("policy_conditions"),
        }
        if not isinstance(required["source_text"], str):
            return _fail("SOURCE_TEXT_INVALID", details={"context_id": context_id})
        if not isinstance(required["source_id"], str) or not required["source_id"]:
            return _fail("SOURCE_ID_INVALID", details={"context_id": context_id})
        if (
            not isinstance(required["claims"], Sequence)
            or isinstance(required["claims"], (str, bytes))
        ):
            return _fail("CLAIMS_INVALID", details={"context_id": context_id})
        if (
            not isinstance(required["decision_basis"], Sequence)
            or isinstance(required["decision_basis"], (str, bytes))
            or any(not isinstance(x, str) or not x for x in required["decision_basis"])
        ):
            return _fail("DECISION_BASIS_INVALID", details={"context_id": context_id})
        if not isinstance(required["policy_conditions"], Mapping):
            return _fail("POLICY_CONDITIONS_INVALID", details={"context_id": context_id})

        kwargs = {
            "source_id": required["source_id"],
            "claims": required["claims"],
            "decision_basis": required["decision_basis"],
            "policy_conditions": required["policy_conditions"],
            "typed_context": row.get("typed_context"),
            "expected_typed_context_sha256": row.get(
                "expected_typed_context_sha256"
            ),
            "fact_source": row.get("fact_source"),
            "fact_source_id": row.get("fact_source_id"),
            "policy_adequacy_bindings": row.get("policy_adequacy_bindings"),
        }

        try:
            resolved = resolver(required["source_text"], **kwargs)
        except Exception as exc:
            return _fail(
                "RESOLVER_EXCEPTION",
                details={
                    "context_id": context_id,
                    "error": type(exc).__name__ + ":" + str(exc),
                },
            )

        if not isinstance(resolved, Mapping):
            return _fail(
                "RESOLVER_RESULT_INVALID",
                details={"context_id": context_id},
            )

        certified = resolved.get("certified_common_policies")
        if not isinstance(certified, list):
            certified = []

        covered = (
            resolved.get("status") == "COMMON_POLICY_CERTIFIED"
            and bool(certified)
            and all(isinstance(x, str) and x for x in certified)
        )
        if not covered:
            uncovered.append(context_id)

        fact_source = row.get("fact_source")
        if isinstance(fact_source, str):
            fact_source_bytes = fact_source.encode("utf-8")
        elif isinstance(fact_source, bytes):
            fact_source_bytes = fact_source
        elif fact_source is None:
            fact_source_bytes = b""
        else:
            return _fail("FACT_SOURCE_INVALID", details={"context_id": context_id})

        row_digest_payload = {
            "context_id": context_id,
            "source_id": required["source_id"],
            "source_text_sha256": hashlib.sha256(
                required["source_text"].encode("utf-8")
            ).hexdigest(),
            "claims": required["claims"],
            "decision_basis": required["decision_basis"],
            "policy_conditions": required["policy_conditions"],
            "typed_context": row.get("typed_context"),
            "expected_typed_context_sha256": row.get(
                "expected_typed_context_sha256"
            ),
            "fact_source_id": row.get("fact_source_id"),
            "fact_source_sha256": hashlib.sha256(fact_source_bytes).hexdigest(),
            "policy_adequacy_bindings": row.get("policy_adequacy_bindings"),
        }
        normalized_manifest_rows.append(row_digest_payload)
        results.append(
            {
                "context_id": context_id,
                "covered": covered,
                "resolver_status": str(resolved.get("status") or ""),
                "certified_common_policies": sorted(
                    x for x in certified if isinstance(x, str) and x
                ),
                "authenticated_policy_adequacy": resolved.get(
                    "authenticated_policy_adequacy", []
                ),
                "rejected_policy_adequacy_bindings": resolved.get(
                    "rejected_policy_adequacy_bindings", []
                ),
            }
        )

    try:
        manifest_digest = _sha256(
            {
                "scope_id": scope_id,
                "contexts": normalized_manifest_rows,
            }
        )
    except (TypeError, ValueError) as exc:
        return _fail(
            "MANIFEST_NOT_CANONICAL_JSON",
            details={"error": type(exc).__name__ + ":" + str(exc)},
        )

    if uncovered:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "PARTIAL_COVER__FAIL_CLOSED",
            "scope_id": scope_id,
            "manifest_sha256": manifest_digest,
            "declared_context_count": len(contexts),
            "covered_context_count": len(contexts) - len(uncovered),
            "uncovered_context_ids": sorted(uncovered),
            "contexts": results,
            "scope_complete_proved": False,
            "abc_credit_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__AUTHENTICATED_POSITIVE_COVER_FOR_DECLARED_MANIFEST",
        "scope_id": scope_id,
        "manifest_sha256": manifest_digest,
        "declared_context_count": len(contexts),
        "covered_context_count": len(contexts),
        "uncovered_context_ids": [],
        "contexts": results,
        "scope_complete_proved": False,
        "abc_credit_authorized": False,
        "next_required_binding": (
            "BIND_THIS_EXACT_MANIFEST_SHA256_TO_A_SEPARATE_SOUND_SCOPE_COMPLETE_"
            "CERTIFICATE_BEFORE_U_EMPTY_OR_ABC_CREDIT"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
