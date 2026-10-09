"""Pinned FIBO Q2 2026 bounded finance semantic authority.

This module authenticates one finite source pack extracted from seven exact
FIBO RDF files at release tag master_2026Q2 / commit
f59157fe156e3d91b1c045222d0a7dc06b7d78a2.

Authority is deliberately narrow:
- exact FIBO class IRIs and source-declared labels are authenticated only as
  ontology vocabulary metadata;
- direct rdfs:subClassOf edges whose endpoints are both declared/labeled in the
  bound pack may issue ENTAILS receipts;
- transitive entailment is delegated to the existing scoped DAG proof kernel;
- labels are candidate-discovery surfaces only and never establish contextual
  semantic identity;
- missing paths are UNKNOWN, not NOT_ENTAILS;
- no complete FIBO import closure or open-world finance ontology is claimed.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import semantic_relation_entailment_dag_v1 as entailment_dag

SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_BOUNDED_FINANCE_AUTHORITY_V1"
PACK_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_CORE_FINANCE_BOUNDED_SOURCE_V1"
EDGE_REQUEST_SCHEMA = "PROJECT_BRAIN_FIBO_Q2_2026_EDGE_REQUEST_V1"
EDGE_RECEIPT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_RECEIPT_V1"
PACK_PATH = "canonical/evidence/FIBO_Q2_2026_CORE_FINANCE_BOUNDED_SOURCE_V1.json"
PACK_GIT_BLOB_SHA = "5849e1fdd68b5883deaa0fbd6146f2b9aea9729a"
UPSTREAM_REPOSITORY = "edmcouncil/fibo"
UPSTREAM_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
UPSTREAM_RELEASE_TAG = "master_2026Q2"
SCOPE_ID = "FIBO_Q2_2026_CORE7_LABELED_CLASSES_AND_INTERNAL_DIRECT_SUBCLASS_EDGES"
EXPECTED_CLASS_COUNT = 253
EXPECTED_EDGE_COUNT = 177
SOURCE_MANIFEST = (
    ("FBC/FinancialInstruments/FinancialInstruments.rdf", "5456f5cb395f30d4636f8d2b1e5f0463466b764e", 56770),
    ("FBC/DebtAndEquities/Debt.rdf", "a5eb752f32d6af7bfa09331e93472caabb9c2369", 103624),
    ("FBC/ProductsAndServices/FinancialProductsAndServices.rdf", "9c07773a5f78ae872e297517004b9a3d47a2d6ab", 90893),
    ("FBC/FunctionalEntities/FinancialServicesEntities.rdf", "1e9a14a20cf56f651853d3afb8bec60654f1a226", 82365),
    ("FND/Accounting/AccountingEquity.rdf", "85c2ca077946d14dda74c52338a7523a1b44c1e3", 11047),
    ("FND/Accounting/CurrencyAmount.rdf", "f06b766f11fe040a0f4d2d511c8a7a856045a05c", 36093),
    ("FND/Agreements/Contracts.rdf", "90e96983bfb78e300875cdff01ef4dff3a4a2d3b", 73907),
)


class FiboAuthorityError(ValueError):
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
        raise FiboAuthorityError("PACK_FILE_INVALID")
    raw = target.read_bytes()
    observed_blob = _git_blob_sha(raw)
    if observed_blob != PACK_GIT_BLOB_SHA:
        raise FiboAuthorityError("PACK_GIT_BLOB_DRIFT:" + observed_blob)
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != PACK_SCHEMA:
        raise FiboAuthorityError("PACK_SCHEMA_INVALID")

    upstream = doc.get("upstream")
    if not isinstance(upstream, Mapping):
        raise FiboAuthorityError("UPSTREAM_BINDING_MISSING")
    expected_upstream = {
        "repository": UPSTREAM_REPOSITORY,
        "release_tag": UPSTREAM_RELEASE_TAG,
        "commit_sha": UPSTREAM_COMMIT,
        "license": "MIT",
    }
    for key, value in expected_upstream.items():
        if upstream.get(key) != value:
            raise FiboAuthorityError("UPSTREAM_BINDING_MISMATCH:" + key)

    expected_manifest = [
        {"path": path, "git_blob_sha": blob, "byte_count": size}
        for path, blob, size in SOURCE_MANIFEST
    ]
    if doc.get("source_files") != expected_manifest:
        raise FiboAuthorityError("SOURCE_MANIFEST_MISMATCH")

    scope = doc.get("scope")
    if not isinstance(scope, Mapping) or scope.get("scope_id") != SCOPE_ID:
        raise FiboAuthorityError("SCOPE_BINDING_INVALID")
    if scope.get("source_file_manifest_complete") is not True:
        raise FiboAuthorityError("SOURCE_MANIFEST_COMPLETENESS_UNPROVED")
    if scope.get("class_count") != EXPECTED_CLASS_COUNT:
        raise FiboAuthorityError("CLASS_COUNT_MISMATCH")
    if scope.get("direct_entailment_edge_count") != EXPECTED_EDGE_COUNT:
        raise FiboAuthorityError("EDGE_COUNT_MISMATCH")
    if scope.get("open_world_finance_ontology_complete") is not False:
        raise FiboAuthorityError("OPEN_WORLD_COMPLETENESS_BOUNDARY_INVALID")
    if scope.get("imported_ontology_closure_complete") is not False:
        raise FiboAuthorityError("IMPORT_CLOSURE_BOUNDARY_INVALID")

    raw_concepts = doc.get("concepts")
    raw_edges = doc.get("entailment_edges")
    if not isinstance(raw_concepts, list) or len(raw_concepts) != EXPECTED_CLASS_COUNT:
        raise FiboAuthorityError("CONCEPTS_INVALID")
    if not isinstance(raw_edges, list) or len(raw_edges) != EXPECTED_EDGE_COUNT:
        raise FiboAuthorityError("EDGES_INVALID")

    manifest_by_path = {path: blob for path, blob, _ in SOURCE_MANIFEST}
    concepts: dict[str, dict[str, Any]] = {}
    label_index: dict[str, list[str]] = {}
    for index, raw_concept in enumerate(raw_concepts):
        if not isinstance(raw_concept, Mapping):
            raise FiboAuthorityError("CONCEPT_NOT_OBJECT:" + str(index))
        cid = str(raw_concept.get("concept_id") or "").strip()
        surfaces = raw_concept.get("surfaces")
        source_path = str(raw_concept.get("source_path") or "")
        source_blob = str(raw_concept.get("source_blob_sha") or "")
        definition = str(raw_concept.get("definition") or "").strip()
        if not cid or cid in concepts:
            raise FiboAuthorityError("CONCEPT_ID_INVALID_OR_DUPLICATE:" + str(index))
        if not isinstance(surfaces, list) or not surfaces:
            raise FiboAuthorityError("CONCEPT_SURFACES_REQUIRED:" + cid)
        normalized_surfaces = sorted({
            " ".join(str(x or "").strip().split()) for x in surfaces if str(x or "").strip()
        })
        if not normalized_surfaces or not definition:
            raise FiboAuthorityError("CONCEPT_SEMANTICS_INCOMPLETE:" + cid)
        if manifest_by_path.get(source_path) != source_blob:
            raise FiboAuthorityError("CONCEPT_SOURCE_BINDING_INVALID:" + cid)
        row = {
            "concept_id": cid,
            "surfaces": normalized_surfaces,
            "definition": definition,
            "source_path": source_path,
            "source_blob_sha": source_blob,
        }
        concepts[cid] = row
        for surface in normalized_surfaces:
            label_index.setdefault(_norm_surface(surface), []).append(cid)

    edges: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            raise FiboAuthorityError("EDGE_NOT_OBJECT:" + str(index))
        source = str(raw_edge.get("source_id") or "").strip()
        target_id = str(raw_edge.get("target_id") or "").strip()
        source_path = str(raw_edge.get("source_path") or "")
        source_blob = str(raw_edge.get("source_blob_sha") or "")
        key = (source, target_id)
        if not source or not target_id or source == target_id or key in edges:
            raise FiboAuthorityError("EDGE_IDENTITY_INVALID_OR_DUPLICATE:" + str(index))
        if source not in concepts or target_id not in concepts:
            raise FiboAuthorityError("EDGE_ENDPOINT_OUTSIDE_BOUND_CONCEPT_SET:" + str(index))
        if concepts[source]["source_path"] != source_path:
            raise FiboAuthorityError("EDGE_SOURCE_PATH_MISMATCH:" + source)
        if manifest_by_path.get(source_path) != source_blob:
            raise FiboAuthorityError("EDGE_SOURCE_BLOB_MISMATCH:" + source)
        edges[key] = {
            "source_id": source,
            "target_id": target_id,
            "source_path": source_path,
            "source_blob_sha": source_blob,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_FIBO_BOUNDED_SOURCE_PACK_AUTHENTICATED",
        "pass": True,
        "pack_path": PACK_PATH,
        "pack_git_blob_sha": observed_blob,
        "upstream_commit": UPSTREAM_COMMIT,
        "scope_id": SCOPE_ID,
        "concept_count": len(concepts),
        "edge_count": len(edges),
        "concepts": concepts,
        "edges": edges,
        "label_index": {k: sorted(v) for k, v in label_index.items()},
        "open_world_finance_ontology_complete": False,
        "semantic_truth_authority": False,
        "source_authority": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def exact_label_candidates(surface: str, *, repo_root: str | Path) -> dict[str, Any]:
    """Return source-backed candidates only; exact labels do not prove contextual identity."""
    try:
        pack = load_pack(repo_root=repo_root)
        key = _norm_surface(surface)
        ids = list(pack["label_index"].get(key, []))
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
        raise FiboAuthorityError("DIRECT_EDGE_NOT_IN_BOUND_PACK")
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
    """Authenticate one direct FIBO subclass edge as a scoped ENTAILS receipt."""
    try:
        if not isinstance(raw, Mapping) or raw.get("schema") != EDGE_REQUEST_SCHEMA:
            return _fail("EDGE_REQUEST_SCHEMA_INVALID")
        if raw.get("scope_id") != SCOPE_ID or raw.get("relation") != "ENTAILS":
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
            "upstream_commit": UPSTREAM_COMMIT,
            "scope_id": SCOPE_ID,
            "relation": "ENTAILS",
            **deepcopy(dict(edge)),
        }
        core = {
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
            **core,
            "receipt_sha256": _sha(core),
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


def _shortest_path(
    edges: Mapping[tuple[str, str], Mapping[str, Any]],
    source: str,
    target: str,
) -> list[str] | None:
    adjacency: dict[str, set[str]] = {}
    for left, right in edges:
        adjacency.setdefault(left, set()).add(right)
    queue = deque([source])
    prior: dict[str, str | None] = {source: None}
    while queue:
        current = queue.popleft()
        for nxt in sorted(adjacency.get(current, set())):
            if nxt in prior:
                continue
            prior[nxt] = current
            if nxt == target:
                out = [target]
                cursor = target
                while prior[cursor] is not None:
                    cursor = str(prior[cursor])
                    out.append(cursor)
                return list(reversed(out))
            queue.append(nxt)
    return None


def build_entailment_evidence(
    left_id: str,
    right_id: str,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Build only a positive proof path. No path never becomes NOT_ENTAILS."""
    try:
        pack = load_pack(repo_root=repo_root)
        left = str(left_id or "").strip()
        right = str(right_id or "").strip()
        if not left or not right or left == right:
            return _fail("DISTINCT_BOUND_CONCEPT_IDS_REQUIRED")
        if left not in pack["concepts"] or right not in pack["concepts"]:
            return _fail("CONCEPT_OUTSIDE_BOUND_FIBO_SCOPE")
        path = _shortest_path(pack["edges"], left, right)
        if path is None:
            return _fail(
                "UNKNOWN__NO_POSITIVE_ENTAILMENT_PATH_IN_BOUND_SCOPE",
                non_entailment_proved=False,
            )
        receipts = [
            make_edge_request(path[i], path[i + 1], repo_root=repo_root)
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
            "status": "PASS__FIBO_SCOPED_ENTAILMENT_EVIDENCE_READY",
            "pass": True,
            "path": path,
            "evidence": evidence,
            "evidence_sha256": entailment_dag.evidence_sha256(evidence),
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
    built = build_entailment_evidence(left_id, right_id, repo_root=repo_root)
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
