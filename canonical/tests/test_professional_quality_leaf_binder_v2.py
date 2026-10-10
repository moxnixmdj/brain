from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_leaf_binder_v2 as binder


class ProfessionalQualityLeafBinderV2Tests(unittest.TestCase):
    def test_current_manifest_remains_24_open_without_leaf_receipts(self):
        out = binder.evaluate()
        self.assertEqual(out["structural_errors"], [], out)
        self.assertEqual(out["verified_leaf_count"], 0, out)
        self.assertEqual(out["open_leaf_count"], 24, out)
        self.assertFalse(out["promotion_ready"], out)
        self.assertFalse(out["manifest_status_has_promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_verified_string_cannot_self_promote_leaf(self):
        manifest = json.loads(binder.MANIFEST.read_text())
        registry = json.loads(binder.REGISTRY.read_text())
        manifest["roots"][0]["semantic_leaf"]["status"] = "VERIFIED"

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            manifest_path = td_path / "manifest.json"
            registry_path = td_path / "registry.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            registry["manifest"]["git_blob_sha"] = binder.git_blob_sha(manifest_path)
            registry_path.write_text(json.dumps(registry, indent=2) + "\n")

            out = binder.evaluate(
                manifest_path=manifest_path,
                graph_path=binder.GRAPH,
                registry_path=registry_path,
                repo_root=binder.ROOT,
            )

        leaf_id = manifest["roots"][0]["semantic_leaf"]["id"]
        self.assertIn(leaf_id, out["declared_verified_without_receipt"], out)
        self.assertIn(leaf_id, out["open_semantic_leaf_ids"], out)
        self.assertNotIn(leaf_id, out["verified_semantic_leaf_ids"], out)
        self.assertFalse(out["promotion_ready"], out)

    def test_scope_matched_content_addressed_receipt_is_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            basis_path = root / "canonical/evidence/basis.json"
            receipt_path = root / "canonical/verification/leaf.json"
            basis_path.parent.mkdir(parents=True)
            receipt_path.parent.mkdir(parents=True)
            basis_path.write_text('{"result":"PASS"}\n')

            leaf_id = "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
            root_id = "R1_TARGET_SPECIFICATION"
            acceptance = "DOMAIN ACCEPTANCE"
            contract = "ROOT CONTRACT"
            manifest_sha = "manifest-sha"
            receipt = {
                "schema": binder.RECEIPT_SCHEMA,
                "leaf_id": leaf_id,
                "root_id": root_id,
                "leaf_kind": "SEMANTIC",
                "verdict": "PASS",
                "closure_scope": "EXACT_LEAF",
                "acceptance_sha256": binder.semantic_sha(acceptance),
                "root_contract_sha256": binder.semantic_sha(contract),
                "manifest_git_blob_sha": manifest_sha,
                "leaf_semantic_satisfied": True,
                "verification_basis": [{
                    "path": "canonical/evidence/basis.json",
                    "git_blob_sha": binder.git_blob_sha(basis_path),
                }],
                "terminal_authority": False,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            entry = {
                "path": "canonical/verification/leaf.json",
                "git_blob_sha": binder.git_blob_sha(receipt_path),
            }
            out = binder._receipt_result(
                repo_root=root,
                entry=entry,
                leaf_id=leaf_id,
                root_id=root_id,
                kind="SEMANTIC",
                acceptance=acceptance,
                contract=contract,
                manifest_blob_sha=manifest_sha,
            )

        self.assertTrue(out["admitted"], out)
        self.assertEqual(out["errors"], [], out)

    def test_receipt_for_wrong_acceptance_cannot_close_leaf(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            basis_path = root / "canonical/evidence/basis.json"
            receipt_path = root / "canonical/verification/leaf.json"
            basis_path.parent.mkdir(parents=True)
            receipt_path.parent.mkdir(parents=True)
            basis_path.write_text('{"result":"PASS"}\n')

            receipt = {
                "schema": binder.RECEIPT_SCHEMA,
                "leaf_id": "leaf",
                "root_id": "root",
                "leaf_kind": "EXECUTION",
                "verdict": "PASS",
                "closure_scope": "EXACT_LEAF",
                "acceptance_sha256": binder.semantic_sha("WRONG"),
                "root_contract_sha256": binder.semantic_sha("CONTRACT"),
                "manifest_git_blob_sha": "manifest-sha",
                "leaf_execution_satisfied": True,
                "verification_basis": [{
                    "path": "canonical/evidence/basis.json",
                    "git_blob_sha": binder.git_blob_sha(basis_path),
                }],
                "terminal_authority": False,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            out = binder._receipt_result(
                repo_root=root,
                entry={
                    "path": "canonical/verification/leaf.json",
                    "git_blob_sha": binder.git_blob_sha(receipt_path),
                },
                leaf_id="leaf",
                root_id="root",
                kind="EXECUTION",
                acceptance="RIGHT",
                contract="CONTRACT",
                manifest_blob_sha="manifest-sha",
            )

        self.assertFalse(out["admitted"], out)
        self.assertIn("ACCEPTANCE_BINDING_MISMATCH", out["errors"], out)

    def test_unknown_registry_leaf_id_fails_structure(self):
        registry = json.loads(binder.REGISTRY.read_text())
        registry["leaf_receipts"]["PQ::UNKNOWN::SEMANTIC"] = []

        with tempfile.TemporaryDirectory() as td:
            registry_path = Path(td) / "registry.json"
            registry_path.write_text(json.dumps(registry, indent=2) + "\n")
            out = binder.evaluate(registry_path=registry_path)

        self.assertIn("REGISTRY_UNKNOWN_LEAF_IDS", out["structural_errors"], out)
        self.assertFalse(out["promotion_ready"], out)


if __name__ == "__main__":
    unittest.main()
