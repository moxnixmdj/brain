"""Verify the content-addressed FIBO Q2 2026 production-TBox scope manifest.

This verifier is deliberately local and authority-minimal.  It verifies the
committed manifest's internal completeness contract and exact frozen source
identities.  The independent connector receipt separately proves those source
identities were recomputed against the upstream Git repository.

It does not map task text to FIBO concepts and does not infer ontology truth.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FIBO_PROD_TBOX_SCOPE_VERIFY_V1"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/evidence/FIBO_Q2_2026_PROD_TBOX_SCOPE_MANIFEST_V1.json"
EXPECTED_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
EXPECTED_TREE = "82d3273e1e93a98152b730538761b9e3264a37ea"
EXPECTED_LOADER_SHA = "69b9b10debbd5ad37e62a302d04e37ecbc063cc0"
EXPECTED_CATALOG_SHA = "40dfc76ba525503852a58757fb93992ff89b28b3"
EXPECTED_COUNT = 106
EXPECTED_BYTES = 3452615
EXPECTED_DOMAINS = {"BE":16,"CAE":1,"DER":15,"FBC":15,"FND":31,"IND":5,"LOAN":7,"SEC":16}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "convention_scope_authenticated": False,
        "task_mapping_authority": False,
        "semantic_truth_authority": False,
        "terminal_authority": False,
        **extra,
    }


def evaluate(manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    try:
        if manifest is None:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(manifest, Mapping):
            return _fail("MANIFEST_NOT_OBJECT")
        if manifest.get("schema") != "PROJECT_BRAIN_FIBO_Q2_2026_PROD_TBOX_SCOPE_MANIFEST_V1":
            return _fail("MANIFEST_SCHEMA_INVALID")
        source = manifest.get("source")
        scope = manifest.get("scope")
        rows = manifest.get("ontology_files")
        authority = manifest.get("authority_boundary")
        if not all(isinstance(x, Mapping) for x in (source, scope, authority)):
            return _fail("MANIFEST_CONTROL_BLOCK_INVALID")
        if not isinstance(rows, list):
            return _fail("ONTOLOGY_FILE_LIST_INVALID")
        expected = {
            "commit_sha": EXPECTED_COMMIT,
            "commit_tree_sha": EXPECTED_TREE,
            "loader_git_blob_sha": EXPECTED_LOADER_SHA,
            "catalog_git_blob_sha": EXPECTED_CATALOG_SHA,
        }
        for field, value in expected.items():
            if source.get(field) != value:
                return _fail("SOURCE_IDENTITY_DRIFT:" + field)
        if source.get("tag") != "master_2026Q2":
            return _fail("RELEASE_TAG_DRIFT")
        if source.get("tag_object_sha") != EXPECTED_COMMIT:
            return _fail("TAG_COMMIT_BINDING_INVALID")
        if source.get("tag_object_type") != "commit":
            return _fail("TAG_OBJECT_TYPE_INVALID")
        if source.get("commit_signature_verified") is not True:
            return _fail("UPSTREAM_COMMIT_SIGNATURE_NOT_VERIFIED")
        if len(rows) != EXPECTED_COUNT:
            return _fail("ONTOLOGY_FILE_COUNT_DRIFT")
        iris, paths, shas = set(), set(), set()
        domains: dict[str, int] = {}
        total = 0
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                return _fail("ONTOLOGY_ROW_NOT_OBJECT", row_index=index)
            iri = row.get("ontology_iri")
            path = row.get("path")
            sha = row.get("git_blob_sha")
            size = row.get("size_bytes")
            domain = row.get("domain")
            if not all(isinstance(x, str) and x for x in (iri, path, sha, domain)):
                return _fail("ONTOLOGY_ROW_IDENTITY_INVALID", row_index=index)
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                return _fail("ONTOLOGY_ROW_SIZE_INVALID", row_index=index)
            if not path.endswith(".rdf"):
                return _fail("NON_RDF_FILE_IN_PRODUCTION_TBOX_SCOPE", path=path)
            name = Path(path).name
            if path.startswith("EXMP/") or name.startswith("Metadata") or name.startswith("All"):
                return _fail("UPSTREAM_EXCLUDED_FILE_CLASS_PRESENT", path=path)
            if iri in iris or path in paths:
                return _fail("DUPLICATE_ONTOLOGY_IDENTITY", path=path)
            iris.add(iri); paths.add(path); shas.add(sha)
            domains[domain] = domains.get(domain, 0) + 1
            total += size
        if total != EXPECTED_BYTES:
            return _fail("TOTAL_SOURCE_BYTES_DRIFT")
        if domains != EXPECTED_DOMAINS:
            return _fail("DOMAIN_COUNTS_DRIFT", observed=domains)
        if scope.get("loader_import_count") != EXPECTED_COUNT:
            return _fail("LOADER_IMPORT_COUNT_DRIFT")
        if scope.get("unique_loader_import_count") != EXPECTED_COUNT:
            return _fail("LOADER_IMPORT_UNIQUENESS_NOT_PROVED")
        if scope.get("resolved_blob_count") != EXPECTED_COUNT or scope.get("unresolved_import_count") != 0:
            return _fail("LOADER_IMPORT_RESOLUTION_INCOMPLETE")
        for field in (
            "production_tbox_only",
            "explicit_source_declarations_authoritative_within_bound_release",
        ):
            if scope.get(field) is not True:
                return _fail("SCOPE_PREMISE_FALSE:" + field)
        for field in (
            "reference_data_in_scope",
            "examples_in_scope",
            "metadata_files_in_scope",
            "other_load_files_in_scope",
            "external_dependency_closure_in_scope",
            "inferred_semantics_requiring_unbound_external_dependencies_authoritative",
        ):
            if scope.get(field) is not False:
                return _fail("SCOPE_BOUNDARY_ESCALATION:" + field)
        if authority.get("release_relative_finance_convention_scope_authority") is not True:
            return _fail("CONVENTION_SCOPE_AUTHORITY_MISSING")
        for field in (
            "task_context_to_fibo_concept_mapping_authority",
            "open_world_ontology_completeness_authority",
            "factual_world_truth_authority",
            "regulatory_policy_truth_authority",
            "semantic_relation_inference_authority",
            "policy_adequacy_authority",
            "execution_authority",
            "acceptance_authority",
            "terminal_authority",
        ):
            if authority.get(field) is not False:
                return _fail("AUTHORITY_ESCALATION:" + field)
        return {
            "schema": SCHEMA,
            "status": "PASS__FIBO_Q2_2026_PRODUCTION_TBOX_CONVENTION_SCOPE_MANIFEST",
            "pass": True,
            "source_commit": EXPECTED_COMMIT,
            "source_tree": EXPECTED_TREE,
            "ontology_file_count": EXPECTED_COUNT,
            "total_source_bytes": EXPECTED_BYTES,
            "domain_counts": deepcopy(EXPECTED_DOMAINS),
            "convention_scope_authenticated": True,
            "task_mapping_authority": False,
            "semantic_truth_authority": False,
            "open_world_ontology_completeness": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
