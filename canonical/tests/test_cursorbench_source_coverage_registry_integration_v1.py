from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    FAILURE_COMPLETENESS_ATOM_ID,
    RECEIPT_SCHEMA,
    TYPED_SEMANTICS_ATOM_ID,
    VERIFY_SCHEMA,
    model_sha256,
    projection_sha256,
)
from canonical.runtime.independent_acceptance_model import generated_obligations


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def source_contract():
    return {
        "schema": "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1",
        "pass": True,
        "task_sha256": "a" * 64,
        "nonwhitespace_source_coverage_complete": True,
        "acceptance_contract": {
            "obligations": [
                {"obligation_id": "RAWREQ:one"},
                {"obligation_id": "RAWREQ:two"},
            ],
            "required_obligation_ids": ["RAWREQ:one", "RAWREQ:two"],
            "raw_source_is_final_semantic_reference": True,
            "unverified_obligation_may_be_silently_dropped": False,
        },
    }


def model():
    return {
        "requirements": [
            {
                "id": "R1",
                "critical": True,
                "transform_kinds": ["artifact"],
                "must_detect_failure_modes": ["bad_output"],
            },
            {
                "id": "R2",
                "critical": True,
                "transform_kinds": ["numeric_formula"],
                "must_detect_failure_modes": [],
            },
        ],
        "checks": [],
    }


def write_binding(root: Path, m, s, *, bad=False):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)

    sp = gov / "source-contract.json"
    sp.write_text(json.dumps(s, sort_keys=True), encoding="utf-8")
    source_blob = git_blob_sha(sp)
    source_digest = hashlib.sha256(
        json.dumps(s, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "audit_id": "audit:source-cover-registry",
        "producer_id": "producer",
        "subject_model_sha256": model_sha256(m),
        "source_contract_git_blob_sha": source_blob,
        "source_contract_sha256": source_digest,
        "source_model_projection_sha256": projection_sha256(m, s),
        "source_obligation_mappings": [
            {"source_obligation_id": "RAWREQ:one", "model_requirement_ids": ["R1"]},
            {"source_obligation_id": "RAWREQ:two", "model_requirement_ids": ["R2"]},
        ],
        "failure_mode_coverage": [
            {
                "requirement_id": row["id"],
                "complete_failure_modes": sorted(generated_obligations(row)),
            }
            for row in m["requirements"]
        ],
        "semantic_mapping_complete": not bad,
        "all_material_terminal_acceptance_semantics_bound": True,
        "failure_mode_universe_complete": True,
        "all_material_independently_knowable_failure_modes_represented": True,
        "source_authority_complete": True,
    }
    rp = gov / "source-cover.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(rp),
        "subject_model_sha256": model_sha256(m),
        "source_contract_git_blob_sha": source_blob,
        "source_contract_sha256": source_digest,
        "source_model_projection_sha256": projection_sha256(m, s),
        "audit_id": "audit:source-cover-registry",
        "producer_id": "producer",
        "independent_verifier_id": "verifier",
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
    vp = ver / "source-cover.verify.json"
    vp.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")

    return {
        "source_contract": {
            "path": "canonical/governance/source-contract.json",
            "git_blob_sha": source_blob,
        },
        "receipt": {
            "path": "canonical/governance/source-cover.json",
            "git_blob_sha": git_blob_sha(rp),
        },
        "verification": {
            "path": "canonical/verification/source-cover.verify.json",
            "git_blob_sha": git_blob_sha(vp),
        },
    }


class SourceCoverageRegistryIntegrationTests(unittest.TestCase):
    def test_valid_source_cover_adds_two_atoms_but_not_whole_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            out = registry.augment_problem(
                {
                    "decision_basis": ["seed"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_source_coverage_binding": write_binding(root, m, s),
                },
                repo_root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["source_coverage_proved_atom_ids"]),
            {TYPED_SEMANTICS_ATOM_ID, FAILURE_COMPLETENESS_ATOM_ID},
        )
        self.assertIn(TYPED_SEMANTICS_ATOM_ID, out["problem"]["decision_basis"])
        self.assertIn(FAILURE_COMPLETENESS_ATOM_ID, out["problem"]["decision_basis"])
        self.assertIn(
            "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
            out["problem"]["decision_basis"],
        )
        typed = [
            row for row in out["skipped_registered_policies"]
            if row["policy_id"] == "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
        ]
        self.assertEqual(len(typed), 1)
        self.assertEqual(
            set(typed[0]["missing_atoms"]),
            {
                "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
                "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
            },
        )
        self.assertFalse(out["membership_self_certified"])
        self.assertFalse(out["terminal_authority"])

    def test_bad_source_coverage_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            out = registry.augment_problem(
                {
                    "decision_basis": ["seed"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_source_coverage_binding": write_binding(root, m, s, bad=True),
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SOURCE_COVERAGE_ATOMS_BINDING_INVALID")

    def test_source_coverage_binding_without_model_fails_closed(self):
        out = registry.augment_problem(
            {
                "decision_basis": ["seed"],
                "typed_acceptance_source_coverage_binding": {},
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SOURCE_COVERAGE_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
