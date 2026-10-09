import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d
from canonical.runtime import d_finality_fabric_guard_v1 as guard


class DFinalityFabricGuardTests(unittest.TestCase):
    def _policy_cert(self, root: Path, allowed):
        material = root / "material.txt"
        material.write_text("sealed\n", encoding="utf-8")
        materials = [{
            "path": "material.txt",
            "git_blob_sha": d.git_blob_sha_file(material),
        }]
        policy = {
            "schema": d.POLICY_SCHEMA,
            "status": "ACTIVE_FAIL_CLOSED",
            "semantic_version": "fabric-guard-test-v1",
            "rule": "NO_FRONT_DOOR_AUTHORITY_WIDENING",
            "revoked_certificate_sha256": [],
        }
        policy["policy_sha256"] = d.policy_sha256(policy)
        cert = {
            "schema": d.CERT_SCHEMA,
            "status": "VERIFIED_D_FINAL",
            "capability_id": allowed[0],
            "capability_contract_sha256": d.sha256_json({"scope": "fabric-guard"}),
            "substrate_contract": {"kind": "TEST_CPYTHON", "version": "test"},
            "substrate_contract_sha256": d.sha256_json({"kind": "TEST_CPYTHON", "version": "test"}),
            "policy_sha256": policy["policy_sha256"],
            "registry_snapshot_root": d.sha256_json({"registry": "test"}),
            "state_snapshot_root": d.sha256_json({"state": "test"}),
            "materials": materials,
            "material_closure_root": d.material_closure_root(materials),
            "allowed_capability_ids": list(allowed),
            "allowed_knowledge_channels": [],
            "allowed_effect_channels": [],
            "donor_authority_zero": True,
            "fresh_replay_pass": True,
            "independent_replay_pass": True,
            "knowledge_capability_nonsmuggling_pass": True,
            "undeclared_dependency_count": 0,
        }
        cert["certificate_sha256"] = d.certificate_sha256(cert)
        return policy, cert

    def test_outside_epoch_is_noop(self):
        self.assertFalse(guard.active())
        self.assertFalse(guard.authorize_requested_mode("CATALOG")["active"])
        self.assertFalse(guard.authorize_dispatch("H100_INFERENCE", {})["active"])
        self.assertTrue(guard.implicit_learning_allowed())

    def test_direct_engine_identity_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy, cert = self._policy_cert(root, ["engine:P3"])
            with d.activate(cert, policy=policy, repo_root=root):
                out = guard.authorize_dispatch("P3", {})
                self.assertEqual(out["checked_identity"], "engine:P3")
                with self.assertRaisesRegex(d.DFinalityError, "CAPABILITY_OUTSIDE_EPOCH"):
                    guard.authorize_dispatch("RAW_GOAL", {})

    def test_bound_carrier_checks_member_identity_not_generic_carrier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy, cert = self._policy_cert(root, ["bound:cap.a"])
            with d.activate(cert, policy=policy, repo_root=root):
                out = guard.authorize_dispatch(
                    "BOUND_CAPABILITY",
                    {"capability_id": "cap.a", "inputs": {}},
                )
                self.assertEqual(out["checked_identity"], "bound:cap.a")
                with self.assertRaisesRegex(d.DFinalityError, "CAPABILITY_OUTSIDE_EPOCH"):
                    guard.authorize_dispatch(
                        "BOUND_CAPABILITY",
                        {"capability_id": "cap.b", "inputs": {}},
                    )

    def test_live_capability_checks_exact_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy, cert = self._policy_cert(root, ["h100:CAP_X"])
            with d.activate(cert, policy=policy, repo_root=root):
                out = guard.authorize_dispatch(
                    "LIVE_CAPABILITY",
                    {"capability_id": "h100:CAP_X", "capability_payload": {}},
                )
                self.assertEqual(out["checked_identity"], "h100:CAP_X")

    def test_identity_bypass_carriers_are_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy, cert = self._policy_cert(root, ["engine:H100_INFERENCE"])
            with d.activate(cert, policy=policy, repo_root=root):
                for mode in ("H100_INFERENCE", "CERTIFIED_ROUTE"):
                    with self.subTest(mode=mode):
                        with self.assertRaisesRegex(
                            guard.DFinalityFabricGuardError,
                            "IDENTITY_BYPASS_CARRIER",
                        ):
                            guard.authorize_dispatch(mode, {})

    def test_mutable_meta_and_mutating_modes_are_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy, cert = self._policy_cert(root, ["engine:P3"])
            with d.activate(cert, policy=policy, repo_root=root):
                for mode in ("CATALOG", "ONE_SHOT_REALITY_CLOSURE", "OWNERSHIP_CATALOG"):
                    with self.subTest(mode=mode):
                        with self.assertRaisesRegex(
                            guard.DFinalityFabricGuardError,
                            "NOT_SNAPSHOT_BOUND",
                        ):
                            guard.authorize_requested_mode(mode)
                for mode in ("LEARNING_EPISODE", "IMPROVEMENT_CYCLE"):
                    with self.subTest(mode=mode):
                        with self.assertRaisesRegex(
                            guard.DFinalityFabricGuardError,
                            "NOT_STATE_EFFECT_BOUND",
                        ):
                            guard.authorize_dispatch(mode, {})
                self.assertFalse(guard.implicit_learning_allowed())


if __name__ == "__main__":
    unittest.main(verbosity=2)
