"""Pinned full FIBO Q2 2026 bounded source authority.

This module reuses the existing FIBO path and scoped entailment proof machinery
over a wider, independently re-extracted source pack: every .rdf file in the
exact upstream repository tree at master_2026Q2 / commit
f59157fe156e3d91b1c045222d0a7dc06b7d78a2.

Authority remains deliberately bounded:
- source labels are candidate-discovery surfaces, never contextual identity;
- source definitions authenticate only what the pinned source says;
- direct rdfs:subClassOf edges provide positive ENTAILS evidence;
- transitive entailment reuses the existing scoped DAG verifier;
- missing paths are UNKNOWN, never NOT_ENTAILS;
- external imports, open-world finance completeness, policy adequacy, and
  terminal acceptance are not claimed.
"""
from __future__ import annotations

from copy import deepcopy
import gzip
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import fibo_q2_2026_bounded_finance_authority_v1 as core
from canonical.runtime import semantic_relation_entailment_dag_v1 as entailment_dag

SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_FULL_RELEASE_AUTHORITY_V1"
PACK_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_FULL_RELEASE_BOUNDED_SOURCE_V1"
EDGE_REQUEST_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_FULL_RELEASE_EDGE_REQUEST_V1"
EDGE_RECEIPT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_RECEIPT_V1"

PACK_PATH = (
    "canonical/evidence/"
    "FIBO_Q2_2026_FULL_RELEASE_BOUNDED_SOURCE_V1.json.gz"
)
PACK_GIT_BLOB_SHA = "e77fcf1232c0422c0af9bcbda6d85026dfd09092"
PACK_SHA256 = "651402fe984a965b456a92dcf92cf49ab43d309acbdd3643313c114cb1c1eae3"
UPSTREAM_REPOSITORY = "edmcouncil/fibo"
UPSTREAM_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
UPSTREAM_RELEASE_TAG = "master_2026Q2"
SCOPE_ID = (
    "FIBO_Q2_2026_FULL_RDF_TREE_LABELED_DEFINED_CLASSES_"
    "AND_INTERNAL_DIRECT_SUBCLASS_EDGES"
)
EXPECTED_SOURCE_FILE_COUNT = 295
EXPECTED_CLASS_COUNT = 2671
EXPECTED_EDGE_COUNT = 3443
EXPECTED_AMBIGUOUS_EXACT_LABEL_COUNT = 5

_HEX40 = set("0123456789abcdef")


class FiboFullReleaseAuthorityError(ValueError):
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
    return sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _norm_surface(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _valid_git_sha(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 40 and all(ch in _HEX40 for ch in text)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "semantic_truth_authority": False,
        "source_authority": False,
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
        raise FiboFullReleaseAuthorityError("PACK_FILE_INVALID")
    raw = target.read_bytes()
    if _git_blob_sha(raw) != PACK_GIT_BLOB_SHA:
        raise FiboFullReleaseAuthorityError("PACK_GIT_BLOB_DRIFT")
    if sha256(raw).hexdigest() != PACK_SHA256:
        raise FiboFullReleaseAuthorityError("PACK_SHA256_DRIFT")
    try:
        doc = json.loads(gzip.decompress(raw).decode("utf-8"))
    except Exception as exc:
        raise FiboFullReleaseAuthorityError(
            "PACK_DECODE_FAILED:" + type(exc).__name__
        ) from exc
    if not isinstance(doc, Mapping) or doc.get("schema") != PACK_SCHEMA:
        raise FiboFullReleaseAuthorityError("PACK_SCHEMA_INVALID")

    upstream = doc.get("upstream")
    expected_upstream = {
        "repository": UPSTREAM_REPOSITORY,
        "release_tag": UPSTREAM_RELEASE_TAG,
        "commit_sha": UPSTREAM_COMMIT,
        "license": "MIT",
    }
    if not isinstance(upstream, Mapping):
        raise FiboFullReleaseAuthorityError("UPSTREAM_BINDING_MISSING")
    for key, value in expected_upstream.items():
        if upstream.get(key) != value:
            raise FiboFullReleaseAuthorityError(
                "UPSTREAM_BINDING_MISMATCH:" + key
            )

    scope = doc.get("scope")
    if not isinstance(scope, Mapping) or scope.get("scope_id") != SCOPE_ID:
        raise FiboFullReleaseAuthorityError("SCOPE_BINDING_INVALID")
    required_scope = {
        "source_file_manifest_complete": True,
        "source_file_count": EXPECTED_SOURCE_FILE_COUNT,
        "class_count": EXPECTED_CLASS_COUNT,
        "direct_entailment_edge_count": EXPECTED_EDGE_COUNT,
        "ambiguous_exact_label_surface_count": (
            EXPECTED_AMBIGUOUS_EXACT_LABEL_COUNT
        ),
        "upstream_rdf_tree_complete": True,
        "imported_external_ontology_closure_complete": False,
        "open_world_finance_ontology_complete": False,
        "unrestricted_synonymy_proved": False,
        "arbitrary_context_to_concept_mapping_proved": False,
        "missing_path_is_non_entailment": False,
    }
    for key, value in required_scope.items():
        if scope.get(key) != value:
            raise FiboFullReleaseAuthorityError(
                "SCOPE_FIELD_MISMATCH:" + key
            )

    source_files = doc.get("source_files")
    if (
        not isinstance(source_files, list)
        or len(source_files) != EXPECTED_SOURCE_FILE_COUNT
    ):
        raise FiboFullReleaseAuthorityError("SOURCE_MANIFEST_INVALID")
    manifest: dict[str, str] = {}
    for index, row in enumerate(source_files):
        if not isinstance(row, Mapping):
            raise FiboFullReleaseAuthorityError(
                "SOURCE_MANIFEST_ROW_INVALID:" + str(index)
            )
        path = str(row.get("path") or "")
        blob = str(row.get("git_blob_sha") or "").lower()
        size = row.get("byte_count")
        if (
            not path
            or path in manifest
            or not path.endswith(".rdf")
            or not _valid_git_sha(blob)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        ):
            raise FiboFullReleaseAuthorityError(
                "SOURCE_MANIFEST_ROW_INVALID:" + str(index)
            )
        manifest[path] = blob

    raw_concepts = doc.get("concepts")
    if (
        not isinstance(raw_concepts, list)
        or len(raw_concepts) != EXPECTED_CLASS_COUNT
    ):
        raise FiboFullReleaseAuthorityError("CONCEPTS_INVALID")
    concepts: dict[str, dict[str, Any]] = {}
    label_index: dict[str, list[str]] = {}
    for index, raw_concept in enumerate(raw_concepts):
        if not isinstance(raw_concept, Mapping):
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_NOT_OBJECT:" + str(index)
            )
        cid = str(raw_concept.get("concept_id") or "").strip()
        surfaces = raw_concept.get("surfaces")
        definitions = raw_concept.get("definitions")
        source_path = str(raw_concept.get("source_path") or "")
        source_blob = str(raw_concept.get("source_blob_sha") or "").lower()
        if not cid or cid in concepts:
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_ID_INVALID_OR_DUPLICATE:" + str(index)
            )
        if not isinstance(surfaces, list) or not surfaces:
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_SURFACES_REQUIRED:" + cid
            )
        if not isinstance(definitions, list) or not definitions:
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_DEFINITIONS_REQUIRED:" + cid
            )
        normalized_surfaces = sorted({
            " ".join(str(x or "").strip().split())
            for x in surfaces
            if str(x or "").strip()
        })
        normalized_definitions = sorted({
            " ".join(str(x or "").strip().split())
            for x in definitions
            if str(x or "").strip()
        })
        if not normalized_surfaces or not normalized_definitions:
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_SEMANTICS_INCOMPLETE:" + cid
            )
        if manifest.get(source_path) != source_blob:
            raise FiboFullReleaseAuthorityError(
                "CONCEPT_SOURCE_BINDING_INVALID:" + cid
            )
        row = {
            "concept_id": cid,
            "surfaces": normalized_surfaces,
            "definitions": normalized_definitions,
            "source_path": source_path,
            "source_blob_sha": source_blob,
        }
        concepts[cid] = row
        for surface in normalized_surfaces:
            label_index.setdefault(_norm_surface(surface), []).append(cid)

    ambiguous = {
        k: sorted(v)
        for k, v in label_index.items()
        if len(v) > 1
    }
    if len(ambiguous) != EXPECTED_AMBIGUOUS_EXACT_LABEL_COUNT:
        raise FiboFullReleaseAuthorityError(
            "AMBIGUOUS_EXACT_LABEL_COUNT_MISMATCH"
        )

    raw_edges = doc.get("entailment_edges")
    if (
        not isinstance(raw_edges, list)
        or len(raw_edges) != EXPECTED_EDGE_COUNT
    ):
        raise FiboFullReleaseAuthorityError("EDGES_INVALID")
    edges: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            raise FiboFullReleaseAuthorityError(
                "EDGE_NOT_OBJECT:" + str(index)
            )
        source = str(raw_edge.get("source_id") or "").strip()
        target_id = str(raw_edge.get("target_id") or "").strip()
        refs = raw_edge.get("source_refs")
        key = (source, target_id)
        if (
            not source
            or not target_id
            or source == target_id
            or key in edges
            or source not in concepts
            or target_id not in concepts
            or not isinstance(refs, list)
            or not refs
        ):
            raise FiboFullReleaseAuthorityError(
                "EDGE_IDENTITY_INVALID:" + str(index)
            )
        normalized_refs = []
        seen_paths = set()
        for ref in refs:
            if not isinstance(ref, Mapping):
                raise FiboFullReleaseAuthorityError(
                    "EDGE_SOURCE_REF_INVALID:" + str(index)
                )
            path = str(ref.get("path") or "")
            blob = str(ref.get("git_blob_sha") or "").lower()
            if (
                not path
                or path in seen_paths
                or manifest.get(path) != blob
            ):
                raise FiboFullReleaseAuthorityError(
                    "EDGE_SOURCE_REF_INVALID:" + str(index)
                )
            seen_paths.add(path)
            normalized_refs.append({
                "path": path,
                "git_blob_sha": blob,
            })
        edges[key] = {
            "source_id": source,
            "target_id": target_id,
            "source_refs": sorted(
                normalized_refs,
                key=lambda x: x["path"],
            ),
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_FIBO_FULL_RELEASE_SOURCE_PACK_AUTHENTICATED",
        "pass": True,
        "pack_path": PACK_PATH,
        "pack_git_blob_sha": PACK_GIT_BLOB_SHA,
        "pack_sha256": PACK_SHA256,
        "upstream_commit": UPSTREAM_COMMIT,
        "scope_id": SCOPE_ID,
        "source_file_count": len(manifest),
        "concept_count": len(concepts),
        "edge_count": len(edges),
        "ambiguous_exact_label_surface_count": len(ambiguous),
        "concepts": concepts,
        "edges": edges,
        "label_index": {k: sorted(v) for k, v in label_index.items()},
        "open_world_finance_ontology_complete": False,
        "imported_external_ontology_closure_complete": False,
        "semantic_truth_authority": False,
        "source_authority": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def exact_label_candidates(
    surface: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        pack = load_pack(repo_root=repo_root)
        ids = list(
            pack["label_index"].get(_norm_surface(surface), [])
        )
        return {
            "schema": SCHEMA,
            "status": "PASS__EXACT_SOURCE_LABEL_CANDIDATES",
            "pass": True,
            "surface": str(surface),
            "candidate_concept_ids": ids,
            "candidate_set_complete_relative_to_exact_label_index": True,
            "contextual_semantic_identity_proved": False,
            "candidate_generation_authority": True,
            "semantic_truth_authority": False,
            "source_authority": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def make_edge_request(
    source_id: str,
    target_id: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    pack = load_pack(repo_root=repo_root)
    key = (str(source_id).strip(), str(target_id).strip())
    if key not in pack["edges"]:
        raise FiboFullReleaseAuthorityError(
            "DIRECT_EDGE_NOT_IN_BOUND_PACK"
        )
    return {
        "schema": EDGE_REQUEST_SCHEMA,
        "scope_id": SCOPE_ID,
        "relation": "ENTAILS",
        "source_id": key[0],
        "target_id": key[1],
        "pack_git_blob_sha": PACK_GIT_BLOB_SHA,
        "upstream_commit": UPSTREAM_COMMIT,
    }


def verify_edge_receipt(
    raw: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if (
            not isinstance(raw, Mapping)
            or raw.get("schema") != EDGE_REQUEST_SCHEMA
        ):
            return _fail("EDGE_REQUEST_SCHEMA_INVALID")
        if (
            raw.get("scope_id") != SCOPE_ID
            or raw.get("relation") != "ENTAILS"
        ):
            return _fail("EDGE_REQUEST_SCOPE_OR_RELATION_INVALID")
        if raw.get("pack_git_blob_sha") != PACK_GIT_BLOB_SHA:
            return _fail("EDGE_REQUEST_PACK_BINDING_INVALID")
        if raw.get("upstream_commit") != UPSTREAM_COMMIT:
            return _fail("EDGE_REQUEST_UPSTREAM_BINDING_INVALID")

        pack = load_pack(repo_root=repo_root)
        source = str(raw.get("source_id") or "").strip()
        target_id = str(raw.get("target_id") or "").strip()
        edge = pack["edges"].get((source, target_id))
        if not isinstance(edge, Mapping):
            return _fail("EDGE_NOT_DECLARED_IN_PINNED_FIBO_SCOPE")

        evidence = {
            "pack_git_blob_sha": PACK_GIT_BLOB_SHA,
            "pack_sha256": PACK_SHA256,
            "upstream_commit": UPSTREAM_COMMIT,
            "scope_id": SCOPE_ID,
            "relation": "ENTAILS",
            **deepcopy(dict(edge)),
        }
        core_receipt = {
            "schema": EDGE_RECEIPT_SCHEMA,
            "pass": True,
            "scope_id": SCOPE_ID,
            "relation": "ENTAILS",
            "source_id": source,
            "target_id": target_id,
            "source_semantics_authenticated": True,
            "target_semantics_authenticated": True,
            "relation_semantics_authenticated": True,
            "evidence_sha256": _sha(evidence),
            "verification_authority_mutated": False,
        }
        return {
            **core_receipt,
            "receipt_sha256": _sha(core_receipt),
            "source_authority": True,
            "semantic_truth_authority": True,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def build_entailment_evidence(
    left_id: str,
    right_id: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        pack = load_pack(repo_root=repo_root)
        left = str(left_id or "").strip()
        right = str(right_id or "").strip()
        if not left or not right or left == right:
            return _fail("DISTINCT_BOUND_CONCEPT_IDS_REQUIRED")
        if left not in pack["concepts"] or right not in pack["concepts"]:
            return _fail("CONCEPT_OUTSIDE_BOUND_FIBO_SCOPE")
        path = core._shortest_path(pack["edges"], left, right)
        if path is None:
            return _fail(
                "UNKNOWN__NO_POSITIVE_ENTAILMENT_PATH_IN_BOUND_SCOPE",
                non_entailment_proved=False,
            )
        receipts = [
            make_edge_request(
                path[i],
                path[i + 1],
                repo_root=repo_root,
            )
            for i in range(len(path) - 1)
        ]
        evidence = {
            "schema": entailment_dag.EVIDENCE_SCHEMA,
            "scope_id": SCOPE_ID,
            "left_id": left,
            "right_id": right,
            "entailment_receipts": receipts,
            "counterexample_receipts": [],
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__FIBO_FULL_RELEASE_SCOPED_ENTAILMENT_EVIDENCE_READY",
            "pass": True,
            "path": path,
            "evidence": evidence,
            "evidence_sha256": entailment_dag.evidence_sha256(
                evidence
            ),
            "semantic_truth_authority": False,
            "source_authority": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def prove_entailment(
    left_id: str,
    right_id: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    built = build_entailment_evidence(
        left_id,
        right_id,
        repo_root=repo_root,
    )
    if built.get("pass") is not True:
        return built
    return entailment_dag.prove(
        built["evidence"],
        expected_evidence_sha256=built["evidence_sha256"],
        relation_verifier=lambda receipt: verify_edge_receipt(
            receipt,
            repo_root=repo_root,
        ),
    )
