from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_leaf_binder_v3 as binder

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ProfessionalQualityLeafBinderV3Tests(unittest.TestCase):
    def test_current_registry_preserves_exactly_twelve_execution_leaves(self):
        out = binder.evaluate()
        self.assertEqual(out["structural_errors"], [], out)
        self.assertTrue(out["existing_evidence_current"], out)
        self.assertEqual(len(out["verified_execution_leaf_ids"]), 12, out)
        self.assertEqual(out["verified_semantic_leaf_ids"], [], out)
        self.assertEqual(out["verified_leaf_count"], 12, out)
        self.assertEqual(out["open_leaf_count"], 12, out)
        self.assertFalse(out["promotion_ready"], out)

    def test_arbitrary_content_addressed_basis_cannot_self_certify_semantic_leaf(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            basis = root / "canonical/evidence/basis.json"
            receipt_path = root / "canonical/verification/leaf.json"
            basis.parent.mkdir(parents=True)
            receipt_path.parent.mkdir(parents=True)
            basis.write_text('{"result":"PASS"}\n', encoding="utf-8")

            leaf_id = "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
            receipt = {
                "schema": binder.RECEIPT_SCHEMA,
                "leaf_id": leaf_id,
                "root_id": "R1_TARGET_SPECIFICATION",
                "leaf_kind": "SEMANTIC",
                "verdict": "PASS",
                "closure_scope": "EXACT_LEAF",
                "acceptance_sha256": binder.v2.semantic_sha("DOMAIN ACCEPTANCE"),
                "root_contract_sha256": binder.v2.semantic_sha("ROOT CONTRACT"),
                "manifest_git_blob_sha": "manifest-sha",
                "leaf_semantic_satisfied": True,
                "verification_basis": [{
                    "path": "canonical/evidence/basis.json",
                    "git_blob_sha": binder.v2.git_blob_sha(basis),
                }],
                "terminal_authority": False,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            out = binder._receipt_result(
                repo_root=root,
                entry={
                    "path": "canonical/verification/leaf.json",
                    "git_blob_sha": binder.v2.git_blob_sha(receipt_path),
                },
                leaf_id=leaf_id,
                root_id="R1_TARGET_SPECIFICATION",
                kind="SEMANTIC",
                acceptance="DOMAIN ACCEPTANCE",
                contract="ROOT CONTRACT",
                manifest_blob_sha="manifest-sha",
            )
        self.assertFalse(out["admitted"], out)
        self.assertTrue(
            any("SEMANTIC_TOTALITY" in e or "SEMANTIC_COVERAGE" in e for e in out["errors"]),
            out,
        )

    def _valid_structural_snapshot(self):
        pack = load(binder.CLAIM_PACK_PATH)
        row = next(x for x in pack["claims"] if x["leaf_id"] == "PQ::R10_ANALYSIS_DECISION::SEMANTIC")
        claim = deepcopy(row["frozen_claim"])
        registry = load(ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json")
        registry["active_claim"] = deepcopy(claim)
        registry["currently_proved_root_certificates"] = 3
        registry["currently_open_root_certificates"] = 0
        registry["r4_proof_closure"] = True
        for slot in registry["certificate_slots"]:
            slot["status"] = "PROVED_CURRENT"
            slot["certificate"]["claim_binding"] = deepcopy(claim)
            slot["independent_verification"]["claim_id"] = claim["claim_id"]
        mission = load(binder.MISSION_POINTER_PATH)
        authority_path = ROOT / mission["authoritative_source"]["path"]
        return claim, registry, mission, binder.v2.git_blob_sha(authority_path), binder.v2.git_blob_sha(binder.MISSION_POINTER_PATH)

    def test_claim_identical_three_roots_and_r4_is_structurally_admissible(self):
        claim, registry, mission, auth_sha, mission_sha = self._valid_structural_snapshot()
        out = binder.validate_semantic_totality_documents(
            leaf_id="PQ::R10_ANALYSIS_DECISION::SEMANTIC",
            frozen_claim=claim,
            registry_snapshot=registry,
            current_mission_pointer=mission,
            current_mission_authority_blob_sha=auth_sha,
            current_mission_pointer_blob_sha=mission_sha,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["r4_proof_closure"], out)
        self.assertEqual(set(out["proved_root_ids"]), set(binder.root_guard.CERTIFICATE_ROOT_IDS))

    def test_cross_claim_root_snapshot_is_rejected(self):
        claim, registry, mission, auth_sha, mission_sha = self._valid_structural_snapshot()
        wrong = deepcopy(claim)
        wrong["scope_sha256"] = "0" * 64
        out = binder.validate_semantic_totality_documents(
            leaf_id="PQ::R10_ANALYSIS_DECISION::SEMANTIC",
            frozen_claim=wrong,
            registry_snapshot=registry,
            current_mission_pointer=mission,
            current_mission_authority_blob_sha=auth_sha,
            current_mission_pointer_blob_sha=mission_sha,
        )
        self.assertFalse(out["pass"], out)
        self.assertIn("SEMANTIC_COVERAGE_ACTIVE_CLAIM_MISMATCH", out["errors"], out)

    def test_open_root_prevents_semantic_admission(self):
        claim, registry, mission, auth_sha, mission_sha = self._valid_structural_snapshot()
        registry["certificate_slots"][2]["status"] = "OPEN_NO_GLOBAL_CERTIFICATE_BOUND"
        registry["certificate_slots"][2]["certificate"] = None
        registry["certificate_slots"][2]["semantic_verifier"] = None
        registry["certificate_slots"][2]["independent_verification"] = None
        registry["currently_proved_root_certificates"] = 2
        registry["currently_open_root_certificates"] = 1
        registry["r4_proof_closure"] = False
        out = binder.validate_semantic_totality_documents(
            leaf_id="PQ::R10_ANALYSIS_DECISION::SEMANTIC",
            frozen_claim=claim,
            registry_snapshot=registry,
            current_mission_pointer=mission,
            current_mission_authority_blob_sha=auth_sha,
            current_mission_pointer_blob_sha=mission_sha,
        )
        self.assertFalse(out["pass"], out)
        self.assertIn("SEMANTIC_COVERAGE_R4_PROOF_CLOSURE_REQUIRED", out["errors"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
