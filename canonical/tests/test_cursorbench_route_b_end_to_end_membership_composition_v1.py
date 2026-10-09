from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.independent_acceptance_model import generated_obligations
from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    model_sha256,
)
from canonical.runtime.cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    RECEIPT_SCHEMA as INFO_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as INFO_VERIFY_SCHEMA,
)
from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    RECEIPT_SCHEMA as DEP_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as DEP_VERIFY_SCHEMA,
    projection_sha256 as dep_projection_sha256,
)
from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as SOURCE_VERIFY_SCHEMA,
    projection_sha256 as source_projection_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_ID = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
FIVE_ATOMS = {
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
}
POLICY_FILES = (
    "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_BINDING_20261009_V1.json",
    "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V2.json",
    "canonical/verification/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_P3_NORMALIZATION_20261009_V1.json",
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def canon_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def write_json(root: Path, rel: str, value) -> dict[str, str]:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return {"path": rel, "git_blob_sha": git_blob_sha(path)}


def copy_policy_evidence(root: Path) -> None:
    for rel in POLICY_FILES:
        source = ROOT / rel
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert source.read_bytes() == target.read_bytes()


def typed_model():
    return {
        "requirements": [
            {
                "id": "R1",
                "critical": True,
                "transform_kinds": ["artifact"],
                "must_detect_failure_modes": ["task_specific_failure"],
                "builder_dependencies": ["raw:task", "builder:parser"],
            }
        ],
        "checks": [
            {
                "id": "C1",
                "covers": ["R1"],
                "detects": [
                    "task_specific_failure",
                    "existence",
                    "schema",
                    "roundtrip_or_parse",
                ],
                "dependencies": ["raw:task", "checker:independent-parser"],
                "provenance": "independent_runtime_oracle",
                "derived_from_builder_output": False,
            }
        ],
    }


def source_contract():
    out = compile_contract(
        "Create an artifact and ensure the artifact can be parsed correctly.",
        source_id="synthetic:cursorbench-route-b-composition",
        routing_target_effects=["DONE"],
    )
    assert out["pass"] is True, out
    return out


def source_coverage_binding(root: Path, model, source):
    source_ref = write_json(
        root,
        "canonical/governance/synthetic-route-b-source-contract.json",
        source,
    )
    model_digest = model_sha256(model)
    projection_digest = source_projection_sha256(model, source)
    obligation_ids = source["acceptance_contract"]["required_obligation_ids"]
    modes = sorted(generated_obligations(model["requirements"][0]))

    receipt = {
        "schema": SOURCE_RECEIPT_SCHEMA,
        "audit_id": "audit:route-b-source-coverage",
        "producer_id": "synthetic-producer",
        "subject_model_sha256": model_digest,
        "source_contract_git_blob_sha": source_ref["git_blob_sha"],
        "source_contract_sha256": canon_sha(source),
        "source_model_projection_sha256": projection_digest,
        "source_obligation_mappings": [
            {
                "source_obligation_id": oid,
                "model_requirement_ids": ["R1"],
            }
            for oid in obligation_ids
        ],
        "failure_mode_coverage": [
            {
                "requirement_id": "R1",
                "complete_failure_modes": modes,
            }
        ],
        "semantic_mapping_complete": True,
        "all_material_terminal_acceptance_semantics_bound": True,
        "failure_mode_universe_complete": True,
        "all_material_independently_knowable_failure_modes_represented": True,
        "source_authority_complete": True,
    }
    receipt_ref = write_json(
        root,
        "canonical/governance/synthetic-route-b-source-coverage.json",
        receipt,
    )
    verification = {
        "schema": SOURCE_VERIFY_SCHEMA,
        "subject_git_blob_sha": receipt_ref["git_blob_sha"],
        "subject_model_sha256": model_digest,
        "source_contract_git_blob_sha": source_ref["git_blob_sha"],
        "source_contract_sha256": canon_sha(source),
        "source_model_projection_sha256": projection_digest,
        "audit_id": "audit:route-b-source-coverage",
        "producer_id": "synthetic-producer",
        "independent_verifier_id": "synthetic-independent-verifier",
        "verification_method": "INDEPENDENT_AUDIT",
        "pass": True,
        "independent_verified": True,
        "source_contract_integrity_verified": True,
        "source_obligation_mapping_semantics_verified": True,
        "source_obligation_coverage_complete_verified": True,
        "model_requirement_review_completeness_verified": True,
        "all_material_terminal_acceptance_semantics_bound_verified": True,
        "failure_mode_universe_completeness_verified": True,
        "all_material_independently_knowable_failure_modes_represented_verified": True,
        "source_authority_completeness_verified": True,
    }
    verify_ref = write_json(
        root,
        "canonical/verification/synthetic-route-b-source-coverage.verify.json",
        verification,
    )
    return {
        "source_contract": source_ref,
        "receipt": receipt_ref,
        "verification": verify_ref,
    }


def dependency_binding(root: Path, model):
    projection_digest = dep_projection_sha256(model)
    model_digest = model_sha256(model)
    receipt = {
        "schema": DEP_RECEIPT_SCHEMA,
        "audit_id": "audit:route-b-dependency-provenance",
        "producer_id": "synthetic-producer",
        "subject_model_sha256": model_digest,
        "dependency_provenance_projection_sha256": projection_digest,
        "dependency_labels_source_verified": True,
        "provenance_labels_authorized": True,
        "independence_relevant_edges_complete": True,
        "no_undeclared_nonraw_dependencies": True,
        "builder_output_derivation_labels_truthful": True,
        "source_authority_complete": True,
    }
    receipt_ref = write_json(
        root,
        "canonical/governance/synthetic-route-b-dependency-provenance.json",
        receipt,
    )
    verification = {
        "schema": DEP_VERIFY_SCHEMA,
        "subject_git_blob_sha": receipt_ref["git_blob_sha"],
        "subject_model_sha256": model_digest,
        "dependency_provenance_projection_sha256": projection_digest,
        "audit_id": "audit:route-b-dependency-provenance",
        "producer_id": "synthetic-producer",
        "independent_verifier_id": "synthetic-independent-verifier",
        "verification_method": "INDEPENDENT_AUDIT",
        "pass": True,
        "independent_verified": True,
        "dependency_labels_source_verified": True,
        "provenance_labels_authorized": True,
        "independence_relevant_edges_complete": True,
        "no_undeclared_nonraw_dependencies": True,
        "builder_output_derivation_labels_truthful": True,
        "source_authority_completeness_verified": True,
    }
    verify_ref = write_json(
        root,
        "canonical/verification/synthetic-route-b-dependency-provenance.verify.json",
        verification,
    )
    return {"receipt": receipt_ref, "verification": verify_ref}


def information_boundary_binding(root: Path, model, source):
    model_digest = model_sha256(model)
    visible_inputs = [source["task_sha256"], model_digest]
    receipt = {
        "schema": INFO_RECEIPT_SCHEMA,
        "boundary_id": "boundary:route-b-preverifier",
        "producer_id": "synthetic-producer",
        "subject_model_sha256": model_digest,
        "declared_visible_input_sha256": visible_inputs,
        "preterminal_information_sources_complete": True,
        "model_derived_only_from_declared_visible_inputs": True,
        "hidden_verifier_access_before_terminal_authorization": False,
        "task_specific_solution_access_before_terminal_authorization": False,
        "boundary_frozen_before_terminal_authorization": True,
    }
    receipt_ref = write_json(
        root,
        "canonical/governance/synthetic-route-b-information-boundary.json",
        receipt,
    )
    verification = {
        "schema": INFO_VERIFY_SCHEMA,
        "subject_git_blob_sha": receipt_ref["git_blob_sha"],
        "subject_model_sha256": model_digest,
        "boundary_id": "boundary:route-b-preverifier",
        "producer_id": "synthetic-producer",
        "independent_verifier_id": "synthetic-independent-verifier",
        "verification_method": "INDEPENDENT_AUDIT",
        "declared_visible_input_sha256": visible_inputs,
        "pass": True,
        "independent_verified": True,
        "declared_visible_inputs_verified": True,
        "preterminal_information_source_completeness_verified": True,
        "model_derivation_boundary_verified": True,
        "hidden_verifier_access_absence_verified": True,
        "task_specific_solution_access_absence_verified": True,
        "boundary_ordering_verified": True,
    }
    verify_ref = write_json(
        root,
        "canonical/verification/synthetic-route-b-information-boundary.verify.json",
        verification,
    )
    return {"receipt": receipt_ref, "verification": verify_ref}


def complete_problem(root: Path):
    copy_policy_evidence(root)
    model = typed_model()
    source = source_contract()
    return {
        "decision_basis": ["seed"],
        "typed_acceptance_model": model,
        "typed_acceptance_source_coverage_binding": source_coverage_binding(
            root, model, source
        ),
        "typed_acceptance_dependency_provenance_binding": dependency_binding(
            root, model
        ),
        "typed_acceptance_information_boundary_binding": information_boundary_binding(
            root, model, source
        ),
    }


class RouteBEndToEndCompositionTests(unittest.TestCase):
    def test_all_five_proved_atoms_select_existing_specialist_through_real_p3_front_door(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = p3.run(complete_problem(root), root=root)

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
        )
        self.assertEqual(out["selected_policy_id"], POLICY_ID)
        self.assertTrue(out["common_policy_certified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])

        reg = out["conditioned_policy_adequacy_registry"]
        self.assertIn(POLICY_ID, reg["injected_policy_ids"])
        self.assertEqual(set(reg["proved_condition_atom_ids"]), FIVE_ATOMS)
        self.assertFalse(reg["membership_self_certified"])
        self.assertFalse(reg["registry_authority"])

    def test_missing_real_evidence_bundle_does_not_select_specialist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            problem = complete_problem(root)
            del problem["typed_acceptance_information_boundary_binding"]
            out = p3.run(problem, root=root)

        self.assertFalse(out["pass"])
        self.assertNotEqual(out.get("selected_policy_id"), POLICY_ID)
        reg = out.get("conditioned_policy_adequacy_registry") or {}
        typed_rows = [
            row
            for row in reg.get("skipped_registered_policies", [])
            if row.get("policy_id") == POLICY_ID
        ]
        self.assertEqual(len(typed_rows), 1)
        self.assertIn(
            "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
            typed_rows[0]["missing_atoms"],
        )

    def test_corrupted_evidence_bundle_fails_closed_before_policy_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            problem = complete_problem(root)
            receipt_path = (
                root
                / problem["typed_acceptance_dependency_provenance_binding"]["receipt"]["path"]
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["provenance_labels_authorized"] = False
            receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
            problem["typed_acceptance_dependency_provenance_binding"]["receipt"][
                "git_blob_sha"
            ] = git_blob_sha(receipt_path)
            out = p3.run(problem, root=root)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CONDITIONED_POLICY_ADEQUACY_REGISTRY_FAIL_CLOSED",
        )
        self.assertNotEqual(out.get("selected_policy_id"), POLICY_ID)


if __name__ == "__main__":
    unittest.main(verbosity=2)
