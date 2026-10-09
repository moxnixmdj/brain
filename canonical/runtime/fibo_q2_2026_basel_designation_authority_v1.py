"""Pinned FIBO Q2 2026 Basel III designation authority.

Authenticates one exact source fragment from
SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions.rdf at the pinned
FIBO Q2 2026 commit.

The bounded authority is deliberately narrow:
- the BaselIIIDesignation class definition is source-bound;
- the four NamedIndividuals explicitly typed as BaselIIIDesignation in the
  bound source are complete relative to that one source file;
- exact labels and abbreviations are candidate-discovery surfaces only;
- INSTANCE_OF receipts authenticate only the explicit rdf:type assertions;
- no contextual word sense, synonymy, policy adequacy, imported ontology
  closure, or open-world finance completeness is claimed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_BASEL_DESIGNATION_AUTHORITY_V1"
PACK_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_BASEL_DESIGNATION_SOURCE_V1"
TYPE_REQUEST_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_BASEL_TYPE_MEMBERSHIP_REQUEST_V1"
TYPE_RECEIPT_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_BASEL_TYPE_MEMBERSHIP_RECEIPT_V1"

PACK_PATH = "canonical/evidence/FIBO_Q2_2026_BASEL_DESIGNATIONS_V1.json"
PACK_GIT_BLOB_SHA = "ae11a0ddca613b25b7df37b1a3f99ade0836f6ee"

UPSTREAM_REPOSITORY = "edmcouncil/fibo"
UPSTREAM_RELEASE_TAG = "master_2026Q2"
UPSTREAM_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
SOURCE_PATH = "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions.rdf"
SOURCE_GIT_BLOB_SHA = "c17e0d79fc90c7469910d053b9dc942bd1043323"
SOURCE_BYTE_COUNT = 17750
SCOPE_ID = "FIBO_Q2_2026_EU_SECURITIES_RESTRICTIONS_BASEL_III_DESIGNATIONS"

BASE = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/"
)
DESIGNATION_CLASS_ID = BASE + "BaselIIIDesignation"
EXPECTED_MEMBER_IDS = frozenset({
    BASE + "AdditionalTier1Capital",
    BASE + "CommonEquityTier1",
    BASE + "Tier1Capital",
    BASE + "Tier2Capital",
})


class BaselDesignationAuthorityError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _norm_surface(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "semantic_truth_authority": False,
        "source_authority": False,
        "candidate_generation_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def load_pack(*, repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    target = (root / PACK_PATH).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise BaselDesignationAuthorityError("PACK_FILE_INVALID")

    raw = target.read_bytes()
    observed_blob = _git_blob_sha(raw)
    if observed_blob != PACK_GIT_BLOB_SHA:
        raise BaselDesignationAuthorityError("PACK_GIT_BLOB_DRIFT:" + observed_blob)

    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != PACK_SCHEMA:
        raise BaselDesignationAuthorityError("PACK_SCHEMA_INVALID")

    upstream = doc.get("upstream")
    if not isinstance(upstream, Mapping):
        raise BaselDesignationAuthorityError("UPSTREAM_BINDING_MISSING")
    expected_upstream = {
        "repository": UPSTREAM_REPOSITORY,
        "release_tag": UPSTREAM_RELEASE_TAG,
        "commit_sha": UPSTREAM_COMMIT,
        "license": "MIT",
        "source_path": SOURCE_PATH,
        "source_git_blob_sha": SOURCE_GIT_BLOB_SHA,
        "source_byte_count": SOURCE_BYTE_COUNT,
    }
    for key, value in expected_upstream.items():
        if upstream.get(key) != value:
            raise BaselDesignationAuthorityError("UPSTREAM_BINDING_MISMATCH:" + key)

    scope = doc.get("scope")
    if not isinstance(scope, Mapping) or scope.get("scope_id") != SCOPE_ID:
        raise BaselDesignationAuthorityError("SCOPE_BINDING_INVALID")
    required_scope_flags = {
        "source_file_manifest_complete": True,
        "basel_designation_class_bound": True,
        "basel_designation_members_complete_relative_to_bound_source": True,
        "member_count": 4,
        "imported_ontology_closure_complete": False,
        "open_world_finance_ontology_complete": False,
        "contextual_semantic_identity_from_label_or_abbreviation": False,
    }
    for key, value in required_scope_flags.items():
        if scope.get(key) != value:
            raise BaselDesignationAuthorityError("SCOPE_PREMISE_INVALID:" + key)

    raw_class = doc.get("designation_class")
    if not isinstance(raw_class, Mapping):
        raise BaselDesignationAuthorityError("DESIGNATION_CLASS_REQUIRED")
    if raw_class.get("concept_id") != DESIGNATION_CLASS_ID:
        raise BaselDesignationAuthorityError("DESIGNATION_CLASS_ID_INVALID")
    if raw_class.get("source_path") != SOURCE_PATH:
        raise BaselDesignationAuthorityError("DESIGNATION_CLASS_SOURCE_PATH_INVALID")
    if raw_class.get("source_blob_sha") != SOURCE_GIT_BLOB_SHA:
        raise BaselDesignationAuthorityError("DESIGNATION_CLASS_SOURCE_BLOB_INVALID")
    class_surfaces = raw_class.get("surfaces")
    class_definition = str(raw_class.get("definition") or "").strip()
    if (
        not isinstance(class_surfaces, list)
        or not class_surfaces
        or not class_definition
    ):
        raise BaselDesignationAuthorityError("DESIGNATION_CLASS_SEMANTICS_INCOMPLETE")

    raw_members = doc.get("members")
    if not isinstance(raw_members, list) or len(raw_members) != 4:
        raise BaselDesignationAuthorityError("MEMBERS_INVALID")

    members: dict[str, dict[str, Any]] = {}
    label_index: dict[str, list[str]] = {}
    for index, raw_member in enumerate(raw_members):
        if not isinstance(raw_member, Mapping):
            raise BaselDesignationAuthorityError("MEMBER_NOT_OBJECT:" + str(index))
        cid = str(raw_member.get("concept_id") or "").strip()
        if not cid or cid in members:
            raise BaselDesignationAuthorityError(
                "MEMBER_ID_INVALID_OR_DUPLICATE:" + str(index)
            )
        if raw_member.get("type_concept_id") != DESIGNATION_CLASS_ID:
            raise BaselDesignationAuthorityError("MEMBER_TYPE_INVALID:" + cid)
        if raw_member.get("source_path") != SOURCE_PATH:
            raise BaselDesignationAuthorityError("MEMBER_SOURCE_PATH_INVALID:" + cid)
        if raw_member.get("source_blob_sha") != SOURCE_GIT_BLOB_SHA:
            raise BaselDesignationAuthorityError("MEMBER_SOURCE_BLOB_INVALID:" + cid)

        surfaces = raw_member.get("surfaces")
        label = str(raw_member.get("label") or "").strip()
        definition = str(raw_member.get("definition") or "").strip()
        abbreviation = raw_member.get("abbreviation")
        if abbreviation is not None:
            abbreviation = str(abbreviation).strip() or None
        if (
            not isinstance(surfaces, list)
            or not surfaces
            or not label
            or not definition
        ):
            raise BaselDesignationAuthorityError("MEMBER_SEMANTICS_INCOMPLETE:" + cid)

        normalized_surfaces = sorted({
            " ".join(str(x or "").strip().split())
            for x in surfaces
            if str(x or "").strip()
        })
        if not normalized_surfaces:
            raise BaselDesignationAuthorityError("MEMBER_SURFACES_EMPTY:" + cid)
        if _norm_surface(label) not in {_norm_surface(x) for x in normalized_surfaces}:
            raise BaselDesignationAuthorityError("MEMBER_LABEL_NOT_IN_SURFACES:" + cid)
        if abbreviation is not None and _norm_surface(abbreviation) not in {
            _norm_surface(x) for x in normalized_surfaces
        }:
            raise BaselDesignationAuthorityError(
                "MEMBER_ABBREVIATION_NOT_IN_SURFACES:" + cid
            )

        row = {
            "concept_id": cid,
            "surfaces": normalized_surfaces,
            "label": label,
            "abbreviation": abbreviation,
            "definition": definition,
            "type_concept_id": DESIGNATION_CLASS_ID,
            "source_path": SOURCE_PATH,
            "source_blob_sha": SOURCE_GIT_BLOB_SHA,
        }
        members[cid] = row
        for surface in normalized_surfaces:
            label_index.setdefault(_norm_surface(surface), []).append(cid)

    if set(members) != EXPECTED_MEMBER_IDS:
        raise BaselDesignationAuthorityError("MEMBER_SET_MISMATCH")

    designation_class = {
        "concept_id": DESIGNATION_CLASS_ID,
        "surfaces": sorted({
            " ".join(str(x or "").strip().split())
            for x in class_surfaces
            if str(x or "").strip()
        }),
        "definition": class_definition,
        "source_path": SOURCE_PATH,
        "source_blob_sha": SOURCE_GIT_BLOB_SHA,
    }

    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_FIBO_BASEL_DESIGNATION_SOURCE_AUTHENTICATED",
        "pass": True,
        "pack_path": PACK_PATH,
        "pack_git_blob_sha": observed_blob,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_release_tag": UPSTREAM_RELEASE_TAG,
        "upstream_commit": UPSTREAM_COMMIT,
        "source_path": SOURCE_PATH,
        "source_git_blob_sha": SOURCE_GIT_BLOB_SHA,
        "source_byte_count": SOURCE_BYTE_COUNT,
        "scope_id": SCOPE_ID,
        "designation_class_id": DESIGNATION_CLASS_ID,
        "designation_class": designation_class,
        "member_ids": sorted(members),
        "members": members,
        "member_set_complete_relative_to_bound_source": True,
        "label_index": {k: sorted(v) for k, v in label_index.items()},
        "imported_ontology_closure_complete": False,
        "open_world_finance_ontology_complete": False,
        "semantic_truth_authority": False,
        "source_authority": True,
        "candidate_generation_authority": True,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def exact_surface_candidates(
    surface: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Return exact source-label/abbreviation candidates only.

    Exact surface equality is candidate-generation evidence. It is never
    contextual semantic identity.
    """
    try:
        pack = load_pack(repo_root=repo_root)
        key = _norm_surface(surface)
        ids = list(pack["label_index"].get(key, []))
        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_BASEL_DESIGNATION_SURFACE_CANDIDATES",
            "pass": True,
            "surface": str(surface),
            "candidate_concept_ids": ids,
            "candidate_set_complete_relative_to_exact_surface_index": True,
            "contextual_semantic_identity_proved": False,
            "candidate_generation_authority": True,
            "semantic_truth_authority": False,
            "source_authority": True,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def make_type_membership_request(
    source_id: str,
    target_id: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    pack = load_pack(repo_root=repo_root)
    source = str(source_id or "").strip()
    target = str(target_id or "").strip()
    member = pack["members"].get(source)
    if not isinstance(member, Mapping):
        raise BaselDesignationAuthorityError("MEMBER_OUTSIDE_BOUND_SCOPE")
    if target != DESIGNATION_CLASS_ID:
        raise BaselDesignationAuthorityError("TARGET_NOT_BASEL_III_DESIGNATION")
    if member.get("type_concept_id") != target:
        raise BaselDesignationAuthorityError("TYPE_MEMBERSHIP_NOT_DECLARED")
    return {
        "schema": TYPE_REQUEST_SCHEMA,
        "scope_id": SCOPE_ID,
        "relation": "INSTANCE_OF",
        "source_id": source,
        "target_id": target,
        "pack_git_blob_sha": PACK_GIT_BLOB_SHA,
        "upstream_commit": UPSTREAM_COMMIT,
        "source_git_blob_sha": SOURCE_GIT_BLOB_SHA,
    }


def verify_type_membership_receipt(
    raw: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Authenticate one explicit rdf:type assertion from the pinned source."""
    try:
        if not isinstance(raw, Mapping) or raw.get("schema") != TYPE_REQUEST_SCHEMA:
            return _fail("TYPE_REQUEST_SCHEMA_INVALID")
        if raw.get("scope_id") != SCOPE_ID:
            return _fail("TYPE_REQUEST_SCOPE_INVALID")
        if raw.get("relation") != "INSTANCE_OF":
            return _fail("TYPE_REQUEST_RELATION_INVALID")
        if raw.get("pack_git_blob_sha") != PACK_GIT_BLOB_SHA:
            return _fail("TYPE_REQUEST_PACK_BINDING_INVALID")
        if raw.get("upstream_commit") != UPSTREAM_COMMIT:
            return _fail("TYPE_REQUEST_UPSTREAM_BINDING_INVALID")
        if raw.get("source_git_blob_sha") != SOURCE_GIT_BLOB_SHA:
            return _fail("TYPE_REQUEST_SOURCE_BLOB_BINDING_INVALID")

        pack = load_pack(repo_root=repo_root)
        source = str(raw.get("source_id") or "").strip()
        target = str(raw.get("target_id") or "").strip()
        member = pack["members"].get(source)
        if not isinstance(member, Mapping):
            return _fail("MEMBER_NOT_DECLARED_IN_PINNED_BASEL_SCOPE")
        if target != DESIGNATION_CLASS_ID:
            return _fail("TARGET_NOT_DECLARED_BASEL_DESIGNATION_CLASS")
        if member.get("type_concept_id") != target:
            return _fail("TYPE_MEMBERSHIP_NOT_DECLARED")

        evidence = {
            "pack_git_blob_sha": PACK_GIT_BLOB_SHA,
            "upstream_commit": UPSTREAM_COMMIT,
            "source_git_blob_sha": SOURCE_GIT_BLOB_SHA,
            "scope_id": SCOPE_ID,
            "relation": "INSTANCE_OF",
            "source_id": source,
            "target_id": target,
            "source_path": SOURCE_PATH,
            "member_definition": member["definition"],
            "target_definition": pack["designation_class"]["definition"],
        }
        core = {
            "schema": TYPE_RECEIPT_SCHEMA,
            "pass": True,
            "scope_id": SCOPE_ID,
            "relation": "INSTANCE_OF",
            "source_id": source,
            "target_id": target,
            "source_semantics_authenticated": True,
            "target_semantics_authenticated": True,
            "relation_semantics_authenticated": True,
            "evidence_sha256": _sha(evidence),
            "verification_authority_mutated": False,
        }
        return {
            **core,
            "status": "PASS__PINNED_FIBO_BASEL_TYPE_MEMBERSHIP_AUTHENTICATED",
            "receipt_sha256": _sha(core),
            "source_authority": True,
            "semantic_truth_authority": True,
            "candidate_generation_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "EXACT_PINNED_RDF_TYPE_MEMBERSHIP_ONLY__LABEL_OR_ABBREVIATION_DOES_NOT_"
                "PROVE_CONTEXTUAL_IDENTITY__NO_IMPORTED_CLOSURE_OR_OPEN_WORLD_FINANCE_CREDIT"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
