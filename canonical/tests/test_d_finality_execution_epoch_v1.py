import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d


class DFinalityExecutionEpochTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-d-finality-")
        self.root = Path(self.tmp.name)
        (self.root / "canonical/runtime").mkdir(parents=True)
        self.a = self.root / "canonical/runtime/a.py"
        self.b = self.root / "canonical/runtime/b.py"
        self.unrelated = self.root / "README.md"
        self.a.write_text("A = 1\n", encoding="utf-8")
        self.b.write_text("B = 2\n", encoding="utf-8")
        self.unrelated.write_text("unrelated\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def policy(self, *, revoked=(), semantic_version="1"):
        p = {
            "schema": d.POLICY_SCHEMA,
            "status": "ACTIVE_FAIL_CLOSED",
            "semantic_version": semantic_version,
            "rule": "NO_UNCERTIFIED_AUTHORITY_WIDENING",
            "revoked_certificate_sha256": list(revoked),
        }
        p["policy_sha256"] = d.policy_sha256(p)
        return p

    def certificate(self, policy, **overrides):
        materials = [
            {
                "path": "canonical/runtime/a.py",
                "git_blob_sha": d.git_blob_sha_file(self.a),
            },
            {
                "path": "canonical/runtime/b.py",
                "git_blob_sha": d.git_blob_sha_file(self.b),
            },
        ]
        c = {
            "schema": d.CERT_SCHEMA,
            "status": "VERIFIED_D_FINAL",
            "capability_id": "engine:A",
            "capability_contract_sha256": d.sha256_json({"contract": "A"}),
            "policy_sha256": d.policy_sha256(policy),
            "registry_snapshot_root": d.sha256_json({"registry": "frozen"}),
            "state_snapshot_root": d.sha256_json({"state": "frozen"}),
            "materials": materials,
            "material_closure_root": d.material_closure_root(materials),
            "allowed_capability_ids": ["engine:A", "bound:B"],
            "allowed_knowledge_channels": ["world:facts"],
            "allowed_effect_channels": ["artifact:write"],
            "donor_authority_zero": True,
            "fresh_replay_pass": True,
            "independent_replay_pass": True,
            "knowledge_capability_nonsmuggling_pass": True,
            "undeclared_dependency_count": 0,
        }
        c.update(overrides)
        c["certificate_sha256"] = d.certificate_sha256(c)
        return c

    def test_valid_epoch_and_child_authority_shrink(self):
        policy = self.policy()
        cert = self.certificate(policy)
        with d.activate(cert, policy=policy, repo_root=self.root) as epoch:
            self.assertEqual(epoch.root_capability_id, "engine:A")
            d.require_capability("engine:A")
            d.require_material("canonical/runtime/a.py", repo_root=self.root)
            d.require_knowledge_channel("world:facts")
            d.require_effect_channel("artifact:write")
            with d.child_scope(
                "bound:B",
                allowed_capability_ids=["bound:B"],
                allowed_knowledge_channels=[],
                allowed_effect_channels=[],
            ) as child:
                self.assertEqual(child.current_capability_id, "bound:B")
                d.require_capability("bound:B")
                with self.assertRaisesRegex(d.DFinalityError, "CAPABILITY_OUTSIDE_EPOCH"):
                    d.require_capability("engine:A")

    def test_child_authority_cannot_widen(self):
        policy = self.policy()
        cert = self.certificate(policy)
        with d.activate(cert, policy=policy, repo_root=self.root):
            with self.assertRaisesRegex(d.DFinalityError, "CHILD_CAPABILITY_AUTHORITY_WIDENING"):
                with d.child_scope(
                    "bound:B",
                    allowed_capability_ids=["engine:A", "bound:B", "skill:new"],
                ):
                    pass

    def test_same_epoch_new_capability_is_denied(self):
        policy = self.policy()
        cert = self.certificate(policy)
        with d.activate(cert, policy=policy, repo_root=self.root):
            with self.assertRaisesRegex(d.DFinalityError, "CAPABILITY_OUTSIDE_EPOCH"):
                d.require_capability("skill:newly-promoted-during-run")

    def test_material_drift_before_execution_fails(self):
        policy = self.policy()
        cert = self.certificate(policy)
        self.a.write_text("A = 99\n", encoding="utf-8")
        with self.assertRaisesRegex(d.DFinalityError, "MATERIAL_BLOB_DRIFT"):
            d.verify_certificate(cert, policy=policy, repo_root=self.root)

    def test_material_drift_during_epoch_fails_at_point_of_use(self):
        policy = self.policy()
        cert = self.certificate(policy)
        with d.activate(cert, policy=policy, repo_root=self.root):
            self.a.write_text("A = 99\n", encoding="utf-8")
            with self.assertRaisesRegex(d.DFinalityError, "MATERIAL_CHANGED_DURING_EPOCH"):
                d.require_material("canonical/runtime/a.py", repo_root=self.root)

    def test_unrelated_file_change_does_not_invalidate_closure_relative_certificate(self):
        policy = self.policy()
        cert = self.certificate(policy)
        self.unrelated.write_text("changed but not load-bearing\n", encoding="utf-8")
        epoch = d.verify_certificate(cert, policy=policy, repo_root=self.root)
        self.assertEqual(epoch.material_closure_root, cert["material_closure_root"])

    def test_targeted_revocation_does_not_change_policy_semantics(self):
        policy = self.policy()
        cert = self.certificate(policy)
        revoked_policy = self.policy(revoked=[cert["certificate_sha256"]])
        self.assertEqual(d.policy_sha256(policy), d.policy_sha256(revoked_policy))
        with self.assertRaisesRegex(d.DFinalityError, "CERTIFICATE_REVOKED"):
            d.verify_certificate(cert, policy=revoked_policy, repo_root=self.root)

    def test_semantic_policy_change_invalidates_certificate(self):
        policy = self.policy(semantic_version="1")
        cert = self.certificate(policy)
        changed = self.policy(semantic_version="2")
        with self.assertRaisesRegex(d.DFinalityError, "CERTIFICATE_POLICY_DRIFT"):
            d.verify_certificate(cert, policy=changed, repo_root=self.root)

    def test_false_donor_or_replay_claims_fail_closed(self):
        policy = self.policy()
        for field, reason in (
            ("donor_authority_zero", "DONOR_AUTHORITY_NOT_ZERO"),
            ("fresh_replay_pass", "FRESH_REPLAY_NOT_PASS"),
            ("independent_replay_pass", "INDEPENDENT_REPLAY_NOT_PASS"),
            ("knowledge_capability_nonsmuggling_pass", "NONSMUGGLING_NOT_PASS"),
        ):
            with self.subTest(field=field):
                cert = self.certificate(policy, **{field: False})
                with self.assertRaisesRegex(d.DFinalityError, reason):
                    d.verify_certificate(cert, policy=policy, repo_root=self.root)

    def test_no_active_epoch_has_zero_d_final_authority(self):
        with self.assertRaisesRegex(d.DFinalityError, "NO_ACTIVE_D_FINALITY_EPOCH"):
            d.require_capability("engine:A")


if __name__ == "__main__":
    unittest.main(verbosity=2)
