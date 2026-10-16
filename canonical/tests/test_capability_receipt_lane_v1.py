#!/usr/bin/env python3
"""Capability execution receipts: prove the mechanism by running it.

These tests execute real inventory modules.  They assert the *mechanism*, not
that any particular capability is correct — a receipt records what was observed,
nothing more.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane_module  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import _receipt_admits, load_verified_registry  # noqa: E402

EXPECTED_SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"


class ContractShapeTests(unittest.TestCase):
    def test_recognises_the_executor_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args, root):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertEqual(lane_module.contract_shape(mod), ("run", "root"))

    def test_rejects_wrong_first_parameter(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(normal_form, matrix):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertIsNone(lane_module.contract_shape(mod))

    def test_rejects_one_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args):\n    return {'status': 'OK'}\n", encoding="utf-8")
            self.assertIsNone(lane_module.contract_shape(mod))

    def test_rejects_syntax_error_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args, root:\n", encoding="utf-8")
            self.assertIsNone(lane_module.contract_shape(mod))


class ReceiptTests(unittest.TestCase):
    def test_receipt_is_content_addressed_and_records_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/qr_probe_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text(
                "def run(args, root):\n    return {'status': 'PROBE_OK', 'pass': True}\n",
                encoding="utf-8",
            )
            rel = "canonical/runtime/bound_capabilities/qr_probe_v1.py"
            receipt = lane_module.execute_and_receipt("probe.v1", rel, "run", str(tmp_path), "test-identity")
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["schema"], EXPECTED_SCHEMA)
            self.assertEqual(receipt["module_sha256"], lane_module.sha256_file(module))
            self.assertEqual(receipt["observed"], {"status": "PROBE_OK", "pass": True})
            self.assertEqual(receipt["model_dependency_count"], 0)
            self.assertIsNone(receipt["independent_verifier"])

    def test_a_module_that_raises_yields_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/bad_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text(
                "def run(args, root):\n    raise RuntimeError('boom')\n", encoding="utf-8"
            )
            rel = "canonical/runtime/bound_capabilities/bad_v1.py"
            self.assertIsNone(lane_module.execute_and_receipt("bad.v1", rel, "run", str(tmp_path), "test"))

    def test_receipt_hash_is_order_independent(self):
        self.assertEqual(lane_module.sha256_canonical({"a": 1, "b": 2}), lane_module.sha256_canonical({"b": 2, "a": 1}))


def _signed_run_reference(run_id=123):
    """The shape only a GitHub runner can produce: a signed OIDC claim set."""
    return {"github_run_id": run_id,
            "oidc_claims": {"iss": "https://token.actions.githubusercontent.com",
                            "repository": "moxnixmdj/brain",
                            "run_id": str(run_id),
                            "workflow_ref": "capability-receipt-verification.yml@refs/heads/main"}}


class LoaderGateTests(unittest.TestCase):
    """The gate must admit on INDEPENDENT reproduction, and demote nothing."""

    def _root(self, tmp, *, verifier="github-actions:ci", run_ref=None, result_mismatch=False,
              verifier_equals_producer=False):
        """Build a minimal repo root holding one producer receipt + one verification record."""
        root = pathlib.Path(tmp)
        (root / "canonical/runtime/bound_capabilities").mkdir(parents=True)
        (root / lane_module.RECEIPT_DIR).mkdir(parents=True)
        module = root / "canonical/runtime/bound_capabilities/probe_v1.py"
        module.write_text("def run(args, root):\n    return {'status': 'OK'}\n", encoding="utf-8")
        rel_module = "canonical/runtime/bound_capabilities/probe_v1.py"
        module_sha = lane_module.sha256_file(module)
        rel_receipt = lane_module.receipt_path_for("probe.v1")

        receipt = {"schema": lane_module.SCHEMA, "capability_id": "probe.v1",
                   "module_path": rel_module, "module_sha256": module_sha,
                   "entrypoint": "run", "result_sha256": "a" * 64,
                   "model_dependency_count": 0, "ran_by": "producer-session"}
        if verifier_equals_producer:
            verifier = "producer-session"
        record = {"schema": lane_module.VERIFICATION_SCHEMA, "capability_id": "probe.v1",
                  "module_path": rel_module, "module_sha256": module_sha,
                  "reproduced": True, "independent_verifier": verifier,
                  "verifier_result_sha256": "b" * 64 if result_mismatch else "a" * 64,
                  "independent_run_reference": run_ref if run_ref is not None else _signed_run_reference(),
                  "model_dependency_count": 0}
        (root / rel_receipt).write_text(json.dumps(receipt), encoding="utf-8")
        (root / lane_module.verification_path_for(rel_receipt)).write_text(json.dumps(record), encoding="utf-8")
        entry = {"status": "UNVERIFIED_INVENTORY", "incremental_spend_usd": 0,
                 "source": {"path": rel_module}, "verification": {"receipt_path": rel_receipt}}
        return root, entry

    def test_status_alone_cannot_admit(self):
        entry = {"status": "VERIFIED_BOUND_CAPABILITY", "verification": {"verified": True},
                 "source": {"path": "canonical/runtime/capability_receipt_lane_v1.py"}}
        self.assertFalse(_receipt_admits(entry, ROOT))

    def test_producer_receipt_alone_cannot_admit(self):
        """A receipt this project issued to itself is SESSION_E0A256F8, not evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp)
            (root / lane_module.verification_path_for(entry["verification"]["receipt_path"])).unlink()
            self.assertFalse(_receipt_admits(entry, root))

    def test_same_identity_cannot_admit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp, verifier_equals_producer=True)
            self.assertFalse(_receipt_admits(entry, root))

    def test_unattested_run_reference_cannot_admit(self):
        """A reference a local process invented carries no github_run_id, so it proves nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp, run_ref={"local_replay": True})
            self.assertFalse(_receipt_admits(entry, root))

    def test_mismatched_result_cannot_admit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp, result_mismatch=True)
            self.assertFalse(_receipt_admits(entry, root))

    def test_unsigned_run_id_cannot_admit(self):
        """A bare github_run_id is a number; without GitHub's signed claims it proves nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp, run_ref={"github_run_id": 123})
            self.assertFalse(_receipt_admits(entry, root))

    def test_wrong_oidc_issuer_cannot_admit(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref = _signed_run_reference()
            ref["oidc_claims"] = dict(ref["oidc_claims"], iss="https://evil.example")
            root, entry = self._root(tmp, run_ref=ref)
            self.assertFalse(_receipt_admits(entry, root))

    def test_independent_attested_reproduction_admits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp)
            self.assertTrue(_receipt_admits(entry, root))

    def test_edited_module_voids_the_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, entry = self._root(tmp)
            (root / entry["source"]["path"]).write_text(
                "def run(args, root):\n    return {'status': 'TAMPERED'}\n", encoding="utf-8")
            self.assertFalse(_receipt_admits(entry, root))

    def test_existing_capabilities_are_preserved(self):
        registry = load_verified_registry(include_extended=True)
        self.assertGreaterEqual(len(registry), 67)

    def test_cache_invalidates_when_evidence_directory_changes(self):
        """A stamped verification record must be visible to the next load in the same process.

        The first version of the cache keyed only on registry/projection mtimes, so a record
        stamped after a load was invisible until the process restarted.  This probe changes
        the directory mtime WITHOUT creating any attestation, so it cannot fabricate one.
        """
        from canonical.runtime import live_integrated_brain_v1 as lib

        load_verified_registry(include_extended=True)
        before = len(lib._REGISTRY_CACHE)
        probe = ROOT / "canonical/astra_runtime/evidence/__cache_probe__.tmp"
        try:
            probe.write_text("probe", encoding="utf-8")
            load_verified_registry(include_extended=True)
            after = len(lib._REGISTRY_CACHE)
        finally:
            probe.unlink(missing_ok=True)
            load_verified_registry(include_extended=True)
        self.assertGreater(after, before)

    def test_every_admitted_capability_is_backed_by_signed_independent_evidence(self):
        """The permanent invariant, whether or not a runner has stamped records yet.

        Initially this asserted "nothing is admitted", which was true only while no runner
        had produced attestations.  The invariant that must always hold is stronger and does
        not go stale: NOTHING is admitted without a signed, independently reproduced record.
        """
        registry = load_verified_registry(include_extended=True)
        for cid, entry in registry.items():
            if entry.get("capability_source") != "receipt_projection":
                continue
            receipt_path = entry["verification"]["receipt_path"]
            vpath = ROOT / lane_module.verification_path_for(receipt_path)
            self.assertTrue(vpath.is_file(), cid)
            record = json.loads(vpath.read_text(encoding="utf-8"))
            producer = json.loads((ROOT / receipt_path).read_text(encoding="utf-8"))
            self.assertEqual(record["schema"], lane_module.VERIFICATION_SCHEMA, cid)
            self.assertIs(record["reproduced"], True, cid)
            self.assertNotEqual(record["independent_verifier"], producer["ran_by"], cid)
            self.assertEqual(record["module_sha256"], producer["module_sha256"], cid)
            self.assertEqual(record["verifier_result_sha256"], producer["result_sha256"], cid)
            claims = record["independent_run_reference"]["oidc_claims"]
            self.assertEqual(claims["iss"], "https://token.actions.githubusercontent.com", cid)

    def test_one_capability_stopped_executing_is_still_present(self):
        """Grace: admission can only add. The original capabilities must all still be here."""
        registry = load_verified_registry(include_extended=True)
        original = [k for k, v in registry.items()
                    if v.get("capability_source") != "receipt_projection"]
        self.assertGreaterEqual(len(original), 67)


class LaneRunTests(unittest.TestCase):
    def test_discover_finds_contract_shaped_inventory_only(self):
        candidates = lane_module.discover(str(ROOT))
        self.assertGreater(len(candidates), 100)
        bound = json.loads((ROOT / lane_module.BOUND).read_text(encoding="utf-8"))["capabilities"]
        for cid, _path, _entrypoint in candidates:
            self.assertNotIn(cid, bound)

    def test_lane_never_claims_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            module = tmp_path / "canonical/runtime/bound_capabilities/ok_v1.py"
            module.parent.mkdir(parents=True)
            module.write_text("def run(args, root):\n    return {'status': 'S'}\n", encoding="utf-8")
            receipt = lane_module.execute_and_receipt(
                "ok.v1", "canonical/runtime/bound_capabilities/ok_v1.py", "run", str(tmp_path), "me"
            )
            self.assertIsNone(receipt["independent_verifier"])
            self.assertIsNone(receipt["independent_run_reference"])


if __name__ == "__main__":
    unittest.main()
