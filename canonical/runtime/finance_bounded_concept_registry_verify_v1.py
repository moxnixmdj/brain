"""Independent verifier for bounded Finance explicit-definition concept identity.

This module intentionally does not import the registry producer. It reparses the
source bytes independently and recomputes the complete bounded registry.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_IDENTITY_VERIFY_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_REGISTRY_V1"
CLAIM_SCHEMA = "PROJECT_BRAIN_FINANCE_BOUNDED_CONCEPT_IDENTITY_CLAIM_V1"
AUTHORITY_RECEIPT_SCHEMA = "PROJECT_BRAIN_SHARED_CONCEPT_IDENTITY_AUTHORITY_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = "canonical/runtime/r2_finance_normalized_source_universe_direct_adequacy_v1.py"
EXPECTED_AUTHORITY_GIT_BLOB_SHA = "7530b3717eda4429a7903bf5d317384d727b8de7"

ROLES = (
    "RULE",
    "EXCEPTION",
    "ESCALATION",
    "DISCLOSURE",
    "FACT",
    "CROSS_REFERENCE",
    "CONTRADICTION",
    "RECONCILIATION",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_DEF = re.compile(
    r"""^\s*(?:for purposes of this [^,]+,\s*)?["']?"""
    r"""(?P<term>[A-Za-z][A-Za-z0-9 _-]{0,80}?)["']?\s+"""
    r"""(?:means|refers\s+to|is\s+defined\s+as)\s+"""
    r"""(?P<definition>.+?)\s*$""",
    re.I,
)


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canon(value).encode("utf-8")
    return sha256(raw).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _independent_registry(
    source_id: str,
    source_text: str,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    authority_path = (repo_root / AUTHORITY_PATH).resolve(strict=True)
    authority_path.relative_to(repo_root)
    authority_blob = _git_blob(authority_path)
    if authority_blob != EXPECTED_AUTHORITY_GIT_BLOB_SHA:
        raise ValueError("FINANCE_ROLE_AUTHORITY_BLOB_DRIFT:" + authority_blob)

    sentences = [
        x.strip()
        for x in _SENTENCE_SPLIT.split(source_text)
        if x.strip()
    ]
    definitions: dict[str, dict[str, Any]] = {}
    for index, sentence in enumerate(sentences):
        match = _DEF.fullmatch(sentence.rstrip("."))
        if match is None:
            continue
        term = _norm(match.group("term"))
        definition = _norm(match.group("definition"))
        key = term.casefold()
        prior = definitions.get(key)
        if prior is not None and prior["definition"].casefold() != definition.casefold():
            raise ValueError("CONFLICTING_DEFINITION:" + term)
        definitions[key] = {
            "term": term,
            "definition": definition,
            "sentence_index": index,
        }
    if not definitions:
        raise ValueError("AT_LEAST_ONE_EXPLICIT_DEFINITION_REQUIRED")

    role_lookup = {x.casefold(): x for x in ROLES}
    resolving: set[str] = set()
    resolved: dict[str, str] = {}

    def resolve(key: str) -> str:
        if key in resolved:
            return resolved[key]
        if key in resolving:
            raise ValueError("DEFINITION_CYCLE:" + key)
        resolving.add(key)
        row = definitions[key]
        target = row["definition"].casefold()
        if target in role_lookup:
            role = role_lookup[target]
        elif target in definitions:
            role = resolve(target)
        else:
            raise ValueError(
                "DEFINITION_OUTSIDE_VERIFIED_FINANCE_ROLE_UNIVERSE:"
                + row["term"]
                + "=>"
                + row["definition"]
            )
        resolving.remove(key)
        resolved[key] = role
        return role

    bindings = []
    for key in sorted(definitions):
        row = definitions[key]
        role = resolve(key)
        binding = {
            "term": row["term"],
            "term_casefold": key,
            "definition": row["definition"],
            "definition_sha256": _sha(row["definition"]),
            "sentence_index": row["sentence_index"],
            "concept_id": "FINANCE_ROLE::" + role,
            "concept_semantics": role,
        }
        binding["binding_sha256"] = _sha(binding)
        bindings.append(binding)

    core = {
        "schema": REGISTRY_SCHEMA,
        "scope_id": "finance:explicit-definitions:" + _sha(
            {
                "source_id": source_id,
                "source_text_sha256": _sha(source_text),
            }
        )[:24],
        "source_id": source_id,
        "source_text_sha256": _sha(source_text),
        "authority": {
            "path": AUTHORITY_PATH,
            "git_blob_sha": authority_blob,
        },
        "canonical_role_universe": list(ROLES),
        "explicit_definition_count": len(bindings),
        "bindings": bindings,
        "scope_completeness": {
            "complete_for": "ALL_EXPLICIT_DEFINITION_STATEMENTS_IN_EXACT_SOURCE",
            "all_explicit_definitions_resolve_to_verified_role_universe": True,
            "open_world_finance_ontology_complete": False,
        },
        "semantic_boundary": (
            "EXACT_EXPLICIT_DEFINITION_CHAIN_TO_VERIFIED_V32_FINANCE_ROLE_ONLY"
        ),
        "model_dependency_count": 0,
        "terminal_authority": False,
    }
    registry = dict(core)
    registry["registry_sha256"] = _sha(core)
    return registry


def verify_claim(
    claim: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        if not isinstance(claim, Mapping) or claim.get("schema") != CLAIM_SCHEMA:
            return _fail("CLAIM_SCHEMA_INVALID")
        source_id = _norm(claim.get("source_id"))
        source_text = claim.get("source_text")
        registry = claim.get("registry")
        left_id = _norm(claim.get("left_id"))
        right_id = _norm(claim.get("right_id"))
        if not source_id or not isinstance(source_text, str) or not source_text.strip():
            return _fail("SOURCE_ID_OR_TEXT_INVALID")
        if not isinstance(registry, Mapping):
            return _fail("REGISTRY_REQUIRED")
        if not left_id or not right_id:
            return _fail("LEFT_AND_RIGHT_ID_REQUIRED")

        recomputed = _independent_registry(
            source_id,
            source_text,
            repo_root=root,
        )
        if dict(registry) != recomputed:
            return _fail(
                "REGISTRY_RECOMPUTATION_MISMATCH",
                expected_registry_sha256=recomputed.get("registry_sha256"),
                supplied_registry_sha256=registry.get("registry_sha256"),
            )

        if claim.get("scope_id") != recomputed.get("scope_id"):
            return _fail("SCOPE_ID_MISMATCH")
        if claim.get("source_text_sha256") != recomputed.get("source_text_sha256"):
            return _fail("SOURCE_TEXT_SHA256_MISMATCH")
        if claim.get("registry_sha256") != recomputed.get("registry_sha256"):
            return _fail("REGISTRY_SHA256_MISMATCH")
        if claim.get("authority_git_blob_sha") != EXPECTED_AUTHORITY_GIT_BLOB_SHA:
            return _fail("AUTHORITY_BLOB_MISMATCH")

        claim_core = {
            "schema": CLAIM_SCHEMA,
            "scope_id": claim.get("scope_id"),
            "left_id": left_id,
            "right_id": right_id,
            "shared_concept_id": claim.get("shared_concept_id"),
            "source_id": source_id,
            "source_text_sha256": claim.get("source_text_sha256"),
            "registry_sha256": claim.get("registry_sha256"),
            "left_binding_sha256": claim.get("left_binding_sha256"),
            "right_binding_sha256": claim.get("right_binding_sha256"),
            "authority_git_blob_sha": claim.get("authority_git_blob_sha"),
            "source_text": source_text,
            "registry": dict(registry),
        }
        if claim.get("claim_sha256") != _sha(claim_core):
            return _fail("CLAIM_SHA256_MISMATCH")

        by_term = {
            str(row.get("term_casefold") or ""): row
            for row in recomputed.get("bindings") or []
            if isinstance(row, Mapping)
        }
        left = by_term.get(left_id.casefold())
        right = by_term.get(right_id.casefold())
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            return _fail("TERM_NOT_BOUND_IN_RECOMPUTED_REGISTRY")
        if claim.get("left_binding_sha256") != left.get("binding_sha256"):
            return _fail("LEFT_BINDING_SHA256_MISMATCH")
        if claim.get("right_binding_sha256") != right.get("binding_sha256"):
            return _fail("RIGHT_BINDING_SHA256_MISMATCH")
        if left.get("concept_id") != right.get("concept_id"):
            return _fail("TERMS_DO_NOT_SHARE_CONCEPT")
        if claim.get("shared_concept_id") != left.get("concept_id"):
            return _fail("SHARED_CONCEPT_ID_MISMATCH")

        receipt_core = {
            "pass": True,
            "schema": AUTHORITY_RECEIPT_SCHEMA,
            "scope_id": recomputed["scope_id"],
            "left_id": left_id,
            "right_id": right_id,
            "shared_concept_id": left["concept_id"],
            "left_binding_authenticated": True,
            "right_binding_authenticated": True,
            "concept_semantics_authenticated": True,
            "left_binding_sha256": left["binding_sha256"],
            "right_binding_sha256": right["binding_sha256"],
            "registry_sha256": recomputed["registry_sha256"],
            "verification_authority_mutated": False,
            "bounded_registry_scope_complete": True,
            "open_world_ontology_complete": False,
            "source_text_sha256": recomputed["source_text_sha256"],
            "authority_git_blob_sha": EXPECTED_AUTHORITY_GIT_BLOB_SHA,
        }
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = _sha(receipt_core)
        return receipt
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
