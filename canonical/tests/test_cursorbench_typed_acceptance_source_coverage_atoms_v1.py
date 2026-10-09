from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    FAILURE_COMPLETENESS_ATOM_ID,
    RECEIPT_SCHEMA,
    TYPED_SEMANTICS_ATOM_ID,
    VERIFY_SCHEMA,
    model_sha256,
    projection_sha256,
    verify,
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def source_contract():
    obligations = [
        {"obligation_id": "RAWREQ:one"},
        {"obligation_id": "RAWREQ:two"},
    ]
    return {
        "schema": "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1",
        "pass": True,
        "task_sha256": "a" * 64,
        "nonwhitespace_source_coverage_complete": True,
        "acceptance_contract": {
            "obligations": obligations,
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


def failure_modes(m):
    from canonical.runtime.independent_acceptance_model import generated_obligations
    return {
        row["id"]: sorted(generated_obligations(row))
        for row in m["requirements"]
    }


def write_binding(root: Path, m, s, *, receipt_mut=None, verify_mut=None):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)

    sp = gov / "source-contract.json"
    sp.write_text(json.dumps(s, sort_keys=True), encoding="utf-8")
    source_blob = git_blob_sha(sp)
    source_digest = hashlib.sha256(
        json.dumps(
            s, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()

    modes = failure_modes(m)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "audit_id": "audit:source-cover-1",
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
            {"requirement_id": rid, "complete_failure_modes": vals}
            for rid, vals in sorted(modes.items())
        ],
        "semantic_mapping_complete": True,
        "all_material_terminal_acceptance_semantics_bound": True,
        "failure_mode_universe_complete": True,
        "all_material_independently_knowable_failure_modes_represented": True,
        "source_authority_complete": True,
    }
    if receipt_mut:
        receipt_mut(receipt)
    rp = gov / "source-cover.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(rp),
        "subject_model_sha256": model_sha256(m),
        "source_contract_git_blob_sha": source_blob,
        "source_contract_sha256": source_digest,
        "source_model_projection_sha256": projection_sha256(m, s),
        "audit_id": "audit:source-cover-1",
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
    if verify_mut:
        verify_mut(verification)
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


class SourceCoverageAtomsTests(unittest.TestCase):
    def test_missing_binding_is_open(self):
        out = verify(model(), None)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__SOURCE_COVERAGE_BINDING_REQUIRED")
        self.assertEqual(out["proved_atom_ids"], [])

    def test_complete_independent_source_cover_proves_exact_two_atoms(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            out = verify(m, write_binding(root, m, s), repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["proved_atom_ids"]),
            {TYPED_SEMANTICS_ATOM_ID, FAILURE_COMPLETENESS_ATOM_ID},
        )
        self.assertEqual(len(out["proved_constraints"]), 2)
        self.assertEqual(out["other_condition_atoms_proved"], [])
        self.assertFalse(out["whole_policy_condition_proved"])
        self.assertFalse(out["whole_cursorbench_adequate"])

    def test_missing_source_obligation_mapping_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            binding = write_binding(
                root, m, s,
                receipt_mut=lambda r: r["source_obligation_mappings"].pop(),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_OBLIGATION_COVERAGE_INCOMPLETE", out["errors"][0])

    def test_unreviewed_model_requirement_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            def mutate(r):
                r["source_obligation_mappings"][1]["model_requirement_ids"] = ["R1"]
            out = verify(m, write_binding(root, m, s, receipt_mut=mutate), repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("MODEL_REQUIREMENT_REVIEW_COVERAGE_INCOMPLETE", out["errors"][0])

    def test_failure_mode_set_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            def mutate(r):
                r["failure_mode_coverage"][0]["complete_failure_modes"].append("invented")
            out = verify(m, write_binding(root, m, s, receipt_mut=mutate), repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("FAILURE_MODE_SET_MISMATCH:R1", out["errors"][0])

    def test_source_contract_must_be_lossless_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            s["nonwhitespace_source_coverage_complete"] = False
            binding = write_binding(root, m, s)
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_CONTRACT_NONWHITESPACE_COVERAGE_INCOMPLETE", out["errors"][0])

    def test_receipt_cannot_self_assert_semantic_completeness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            binding = write_binding(
                root, m, s,
                receipt_mut=lambda r: r.__setitem__(
                    "all_material_terminal_acceptance_semantics_bound", False
                ),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn(
            "RECEIPT_PREMISE_UNPROVED:all_material_terminal_acceptance_semantics_bound",
            out["errors"][0],
        )

    def test_independent_verifier_must_verify_failure_completeness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            binding = write_binding(
                root, m, s,
                verify_mut=lambda v: v.__setitem__(
                    "failure_mode_universe_completeness_verified", False
                ),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn(
            "VERIFICATION_PREMISE_UNPROVED:failure_mode_universe_completeness_verified",
            out["errors"][0],
        )

    def test_verifier_must_be_producer_independent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m, s = model(), source_contract()
            binding = write_binding(
                root, m, s,
                verify_mut=lambda v: v.__setitem__(
                    "independent_verifier_id", "producer"
                ),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_NOT_PRODUCER_INDEPENDENT", out["errors"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
