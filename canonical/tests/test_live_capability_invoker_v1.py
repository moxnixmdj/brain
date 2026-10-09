from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d_finality
from canonical.runtime import live_capability_invoker_v1 as invoker
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run


class LiveCapabilityInvokerV1Tests(unittest.TestCase):

    def _d_policy_and_certificate(self, root: Path, allowed):
        material = root / "material.txt"
        material.write_text("sealed\n", encoding="utf-8")
        materials = [{
            "path": "material.txt",
            "git_blob_sha": d_finality.git_blob_sha_file(material),
        }]
        policy = {
            "schema": d_finality.POLICY_SCHEMA,
            "status": "ACTIVE_FAIL_CLOSED",
            "semantic_version": "invoker-test-v1",
            "rule": "NO_UNCERTIFIED_AUTHORITY_WIDENING",
            "revoked_certificate_sha256": [],
        }
        policy["policy_sha256"] = d_finality.policy_sha256(policy)
        cert = {
            "schema": d_finality.CERT_SCHEMA,
            "status": "VERIFIED_D_FINAL",
            "capability_id": allowed[0],
            "capability_contract_sha256": d_finality.sha256_json({"scope": "invoker-test"}),
            "policy_sha256": policy["policy_sha256"],
            "registry_snapshot_root": d_finality.sha256_json({"registry": "test"}),
            "state_snapshot_root": d_finality.sha256_json({"state": "test"}),
            "materials": materials,
            "material_closure_root": d_finality.material_closure_root(materials),
            "allowed_capability_ids": list(allowed),
            "allowed_knowledge_channels": [],
            "allowed_effect_channels": [],
            "donor_authority_zero": True,
            "fresh_replay_pass": True,
            "independent_replay_pass": True,
            "knowledge_capability_nonsmuggling_pass": True,
            "undeclared_dependency_count": 0,
        }
        cert["certificate_sha256"] = d_finality.certificate_sha256(cert)
        return policy, cert

    def test_no_epoch_preserves_direct_invoker_behavior(self):
        calls = []
        def engine_runner(mode, payload, options):
            calls.append((mode, dict(payload), dict(options)))
            return {"pass": True, "status": "OK"}
        out = invoker.invoke(
            "engine:TEST_ENGINE",
            {"x": 1},
            engine_runner=engine_runner,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(calls[0][0], "TEST_ENGINE")

    def test_active_epoch_allows_member_and_denies_nonmember_before_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="brain-d-invoker-") as td:
            root = Path(td)
            policy, cert = self._d_policy_and_certificate(
                root,
                ["engine:TEST_ENGINE"],
            )
            calls = []
            def engine_runner(mode, payload, options):
                calls.append(mode)
                return {"pass": True, "status": "OK"}

            with d_finality.activate(cert, policy=policy, repo_root=root):
                allowed = invoker.invoke(
                    "engine:TEST_ENGINE",
                    {},
                    engine_runner=engine_runner,
                )
                self.assertTrue(allowed["pass"], allowed)
                with self.assertRaisesRegex(
                    d_finality.DFinalityError,
                    "CAPABILITY_OUTSIDE_EPOCH",
                ):
                    invoker.invoke(
                        "engine:OTHER_ENGINE",
                        {},
                        engine_runner=engine_runner,
                    )
            self.assertEqual(calls, ["TEST_ENGINE"])

    def test_classifier_covers_every_ownership_kind(self):
        rows = {
            "engine:RAW_GOAL": "ENGINE",
            "bound:archive.tar_gz.create_from_manifest": "BOUND_CAPABILITY",
            "h100:CAP_X": "H100_VERIFIED_CAPABILITY",
            "h100:CAP_X@ROUTE_A": "H100_VERIFIED_CAPABILITY",
            "skill:abc": "ACTIVE_VERIFIED_LEARNED_SKILL",
            "certified_route:ROUTE_A": "CERTIFIED_ROUTE",
        }
        for cid, kind in rows.items():
            self.assertEqual(invoker.classify(cid)["kind"], kind)

    def test_catalog_proves_universal_invocation_contract_coverage(self):
        c = catalog()
        coverage = c["live_capability_invocation_coverage"]
        self.assertTrue(coverage["pass"], coverage)
        self.assertEqual(
            coverage["capability_count"],
            c["live_owned_capability_count"],
        )
        self.assertEqual(coverage["missing_capability_count"], 0)
        self.assertTrue(c["all_live_owned_capabilities_universally_invocable"])
        self.assertTrue(c["r1_structural_closure"], c)
        self.assertEqual(c["known_r1_residuals"], [])

    def test_one_front_door_can_invoke_an_owned_engine_by_ownership_id(self):
        out = run({
            "payload": {
                "capability_id": "engine:OWNERSHIP_CATALOG",
                "capability_payload": {},
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["mode"], "LIVE_CAPABILITY")
        self.assertTrue(out["auto_routed"])
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "PASS__EXACT_ENGINE_CAPABILITY_DISPATCHED",
        )
        nested = out["result"]["result"]
        self.assertEqual(nested["mode"], "OWNERSHIP_CATALOG")
        self.assertTrue(nested["inner_pass"], nested)
        self.assertTrue(nested["result"]["live_owned_equals_fabric_reachable"])

    def test_unknown_ownership_identity_fails_closed(self):
        out = run({
            "mode": "LIVE_CAPABILITY",
            "payload": {
                "capability_id": "unknown:nope",
                "capability_payload": {},
            },
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OWNED_CAPABILITY_ID_KIND_UNKNOWN", out["reason"])


    def test_active_d_epoch_never_uses_legacy_bound_executor(self):
        with mock.patch.object(invoker, "_active_d_epoch_or_none", return_value=object()), \
             mock.patch.object(invoker, "_invoke_bound_under_d_epoch", return_value={"pass": True, "status": "D"}), \
             mock.patch.object(invoker, "execute_bound", side_effect=AssertionError("legacy executor must not run")):
            out = invoker.invoke(
                "bound:archive.tar_gz.create_from_manifest",
                {"manifest_path": "m.json", "output_path": "o.tar.gz"},
                engine_runner=lambda *_: {},
            )
        self.assertTrue(out["pass"])
        self.assertEqual(out["result"]["status"], "D")

    def test_no_d_epoch_preserves_legacy_bound_executor(self):
        with mock.patch.object(invoker, "_active_d_epoch_or_none", return_value=None), \
             mock.patch.object(invoker, "execute_bound", return_value={"pass": True, "status": "LEGACY"}) as legacy, \
             mock.patch.object(invoker, "_invoke_bound_under_d_epoch", side_effect=AssertionError("D path must not run")):
            out = invoker.invoke(
                "bound:archive.tar_gz.create_from_manifest",
                {"manifest_path": "m.json", "output_path": "o.tar.gz"},
                engine_runner=lambda *_: {},
            )
        self.assertTrue(out["pass"])
        self.assertEqual(out["result"]["status"], "LEGACY")
        legacy.assert_called_once()

    def test_d_epoch_contract_hash_must_match_registry_entry(self):
        epoch = SimpleNamespace(
            capability_contract_sha256="a" * 64,
            material_bindings=tuple(),
        )
        with mock.patch.object(invoker.d_epoch, "require_capability", return_value=epoch), \
             mock.patch.object(invoker.d_epoch, "require_material", return_value=None), \
             mock.patch.object(
                 invoker.d_stdlib_provider,
                 "inspect",
                 return_value={
                     "registry_entry_sha256": "b" * 64,
                     "entry": {
                         "source": {"adapter_path": "canonical/runtime/bound_capabilities/archive_tarfile.py"},
                         "adapter_module": "archive_tarfile",
                     },
                 },
             ):
            with self.assertRaisesRegex(
                invoker.LiveCapabilityInvocationError,
                "D_EPOCH_CAPABILITY_CONTRACT_MISMATCH",
            ):
                invoker._invoke_bound_under_d_epoch(
                    "bound:archive.tar_gz.create_from_manifest",
                    "archive.tar_gz.create_from_manifest",
                    {},
                )

    def test_d_epoch_requires_adapter_blob_in_material_closure(self):
        contract = "a" * 64
        epoch = SimpleNamespace(
            capability_contract_sha256=contract,
            material_bindings=tuple(),
        )
        with mock.patch.object(invoker.d_epoch, "require_capability", return_value=epoch), \
             mock.patch.object(invoker.d_epoch, "require_material", return_value=None), \
             mock.patch.object(
                 invoker.d_stdlib_provider,
                 "inspect",
                 return_value={
                     "registry_entry_sha256": contract,
                     "entry": {
                         "source": {"adapter_path": "canonical/runtime/bound_capabilities/archive_tarfile.py"},
                         "adapter_module": "archive_tarfile",
                     },
                 },
             ):
            with self.assertRaisesRegex(
                invoker.LiveCapabilityInvocationError,
                "D_EPOCH_ADAPTER_NOT_BOUND",
            ):
                invoker._invoke_bound_under_d_epoch(
                    "bound:archive.tar_gz.create_from_manifest",
                    "archive.tar_gz.create_from_manifest",
                    {},
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
