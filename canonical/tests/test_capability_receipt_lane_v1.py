#!/usr/bin/env python3
"""Capability execution receipts: prove the mechanism by running it.

These tests execute real inventory modules.  They assert the *mechanism*, not
that any particular capability is correct — a receipt records what was observed,
nothing more.
"""
from __future__ import annotations

import importlib.util
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


class CliKindTests(unittest.TestCase):
    """CLI-shaped capabilities run through the repository's own cli_command adapter."""

    def _cli_module(self, tmp, body):
        root = pathlib.Path(tmp)
        target = root / "canonical/experiments/probe_cli_v1.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return root, "canonical/experiments/probe_cli_v1.py"

    def test_cli_shape_detects_main_and_dunder_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rel = self._cli_module(tmp, "def main():\n    print('{}')\n")
            self.assertTrue(lane_module.cli_shape(root / rel))
            root2, rel2 = self._cli_module(tmp, "def helper():\n    return 1\n")
            self.assertFalse(lane_module.cli_shape(root2 / rel2))

    def test_argv_is_portable_not_an_absolute_interpreter(self):
        argv = lane_module.cli_argv_for("canonical/experiments/x.py")
        self.assertEqual(argv, ["python3", "canonical/experiments/x.py"])
        self.assertNotIn(sys.executable, argv)

    def test_cli_module_printing_json_yields_a_cli_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rel = self._cli_module(
                tmp, "import json\nprint(json.dumps({'status': 'CLI_OK', 'pass': True}))\n")
            receipt = lane_module.execute_and_receipt("cli.v1", rel, "run", str(root), "me", "cli")
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["kind"], "cli")
            self.assertEqual(receipt["entrypoint"], "run")
            self.assertEqual(receipt["invoked_args"]["argv"], ["python3", rel])
            self.assertEqual(receipt["observed"], {"returncode": 0, "status": "CLI_OK", "pass": True})
            self.assertIsNone(receipt["independent_verifier"])

    def test_cli_module_requiring_arguments_yields_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rel = self._cli_module(
                tmp, "import sys\nsys.exit('Usage: needs <input>')\n")
            self.assertIsNone(lane_module.execute_and_receipt("cli.v1", rel, "run", str(root), "me", "cli"))

    def test_cli_module_printing_prose_yields_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, rel = self._cli_module(tmp, "print('hello, not structured')\n")
            self.assertIsNone(lane_module.execute_and_receipt("cli.v1", rel, "run", str(root), "me", "cli"))

    def test_cli_projection_drives_the_repository_adapter(self):
        receipt = {"capability_id": "canonical/x.py.auto.v1", "kind": "cli",
                   "module_path": "canonical/x.py", "module_sha256": "a" * 64,
                   "entrypoint": "run", "invoked_args": {"argv": ["python3", "canonical/x.py"]},
                   "observed": {"returncode": 0}, "result_sha256": "b" * 64,
                   "model_dependency_count": 0, "independent_verifier": None,
                   "receipt_path": "canonical/astra_runtime/evidence/r.json"}
        entry = lane_module.projection_entry(receipt)
        self.assertEqual(entry["adapter_module"], "cli_command")
        self.assertEqual(entry["source"]["adapter_path"], lane_module.CLI_ADAPTER)
        self.assertEqual(entry["action_template"]["args"]["argv"], ["python3", "canonical/x.py"])
        self.assertEqual(entry["action_template"]["expect"],
                         {"type": "field_equals", "field": "returncode", "value": 0})

    def test_contract_projection_still_uses_the_module_directly(self):
        receipt = {"capability_id": "canonical/y.py.auto.v1", "kind": "contract",
                   "module_path": "canonical/y.py", "module_sha256": "a" * 64,
                   "entrypoint": "run", "invoked_args": {}, "observed": {"status": "OK"},
                   "result_sha256": "b" * 64, "model_dependency_count": 0,
                   "independent_verifier": None, "receipt_path": "r.json"}
        entry = lane_module.projection_entry(receipt)
        self.assertEqual(entry["adapter_module"], "y")
        self.assertEqual(entry["source"]["adapter_path"], "canonical/y.py")


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


class IndependenceProvenanceTests(unittest.TestCase):
    """Only a GitHub-signed reference may WRITE a verification record."""

    def test_a_local_reference_is_not_attestable(self):
        self.assertFalse(lane_module.run_reference_is_attested({"github_run_id": 1}))
        self.assertFalse(lane_module.run_reference_is_attested({"local_replay": True}))
        self.assertFalse(lane_module.run_reference_is_attested(
            {"github_run_id": 1, "oidc_claims": {"iss": "https://evil.example", "repository": "x"}}))
        self.assertFalse(lane_module.run_reference_is_attested(
            {"oidc_claims": {"iss": lane_module.GITHUB_OIDC_ISSUER}}))
        self.assertTrue(lane_module.run_reference_is_attested(
            {"github_run_id": 1, "oidc_claims": {"iss": lane_module.GITHUB_OIDC_ISSUER,
                                                 "repository": "o/r", "run_id": "1"}}))

    def _producer_root(self, tmp, name):
        root = pathlib.Path(tmp)
        (root / "canonical/runtime/bound_capabilities").mkdir(parents=True, exist_ok=True)
        (root / lane_module.RECEIPT_DIR).mkdir(parents=True, exist_ok=True)
        module = root / "canonical/runtime/bound_capabilities" / name
        module.write_text("def run(args, root):\n    return {'status': 'S'}\n", encoding="utf-8")
        rel = f"canonical/runtime/bound_capabilities/{name}"
        receipt = lane_module.execute_and_receipt(f"{name}.v1", rel, "run", str(root), "producer")
        receipt["receipt_path"] = lane_module.receipt_path_for(f"{name}.v1")
        (root / receipt["receipt_path"]).write_text(json.dumps(receipt), encoding="utf-8")
        return root, receipt

    def test_local_identity_confirms_reproduction_but_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, receipt = self._producer_root(tmp, "prod_v1.py")
            report = lane_module.verify_producer_receipts(
                str(root), "local-replay", {"local_replay": True})
            self.assertEqual(report["reproduced"], 1)
            self.assertIs(report["run_reference_attested"], False)
            self.assertEqual(report["records_written"], 0)
            self.assertFalse((root / lane_module.verification_path_for(receipt["receipt_path"])).exists())

    def test_attested_identity_writes_the_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, receipt = self._producer_root(tmp, "prod2_v1.py")
            ref = {"github_run_id": 7, "oidc_claims": {"iss": lane_module.GITHUB_OIDC_ISSUER,
                                                      "repository": "o/r", "run_id": "7"}}
            report = lane_module.verify_producer_receipts(str(root), "github-actions:o/r", ref)
            self.assertEqual(report["records_written"], 1)
            written = root / lane_module.verification_path_for(receipt["receipt_path"])
            self.assertTrue(written.is_file())
            self.assertEqual(json.loads(written.read_text())["independent_verifier"], "github-actions:o/r")

    def test_the_producer_cannot_verify_its_own_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = self._producer_root(tmp, "prod3_v1.py")
            ref = {"github_run_id": 7, "oidc_claims": {"iss": lane_module.GITHUB_OIDC_ISSUER,
                                                      "repository": "o/r", "run_id": "7"}}
            report = lane_module.verify_producer_receipts(str(root), "producer", ref)
            self.assertEqual(report["records_written"], 0)


class TreeRestorationTests(unittest.TestCase):
    """Probing executes real modules; it must never leave the project mutated."""

    def test_restores_modified_tracked_files_and_removes_new_ones(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for cmd in (["git", "init", "-q", "."], ["git", "config", "user.email", "t@t"],
                        ["git", "config", "user.name", "t"]):
                sp.run(cmd, cwd=root, check=True)
            (root / "tracked.txt").write_text("original", encoding="utf-8")
            sp.run(["git", "add", "-A"], cwd=root, check=True)
            sp.run(["git", "commit", "-qm", "init"], cwd=root, check=True)

            before = lane_module._changed_paths(str(root))
            (root / "tracked.txt").write_text("TAMPERED", encoding="utf-8")
            (root / "litter.json").write_text("{}", encoding="utf-8")
            (root / "--help").write_text("{}", encoding="utf-8")

            reverted = lane_module.restore_tree(str(root), before, ("CAPABILITY__",))
            self.assertIn("tracked.txt", reverted)
            self.assertIn("litter.json", reverted)
            self.assertIn("--help", reverted)
            self.assertEqual((root / "tracked.txt").read_text(encoding="utf-8"), "original")
            self.assertFalse((root / "litter.json").exists())
            self.assertFalse((root / "--help").exists())

    def test_pre_existing_dirt_is_left_alone(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for cmd in (["git", "init", "-q", "."], ["git", "config", "user.email", "t@t"],
                        ["git", "config", "user.name", "t"]):
                sp.run(cmd, cwd=root, check=True)
            (root / "tracked.txt").write_text("original", encoding="utf-8")
            sp.run(["git", "add", "-A"], cwd=root, check=True)
            sp.run(["git", "commit", "-qm", "init"], cwd=root, check=True)
            (root / "tracked.txt").write_text("MINE, pre-existing", encoding="utf-8")
            before = lane_module._changed_paths(str(root))
            (root / "litter.json").write_text("{}", encoding="utf-8")
            reverted = lane_module.restore_tree(str(root), before, ("CAPABILITY__",))
            self.assertEqual(reverted, ["litter.json"])
            self.assertEqual((root / "tracked.txt").read_text(encoding="utf-8"), "MINE, pre-existing")


class DeclaredExpectationTests(unittest.TestCase):
    """The projection may not advertise an expectation the receipt never observed."""

    def test_cli_always_supports_returncode_zero(self):
        self.assertEqual(lane_module._declared_expectation(True, {}),
                         {"type": "field_equals", "field": "returncode", "value": 0})

    def test_contract_asserts_only_what_the_receipt_observed(self):
        self.assertEqual(lane_module._declared_expectation(False, {"status": "OK"}),
                         {"type": "field_nonempty", "field": "status"})
        self.assertEqual(lane_module._declared_expectation(False, {"pass": True}),
                         {"type": "field_equals", "field": "pass", "value": True})
        self.assertEqual(lane_module._declared_expectation(False, {"output_verified": True}),
                         {"type": "field_equals", "field": "output_verified", "value": True})
        # observed nothing -> assert nothing. This is the defect that was found by executing
        # the projection: 7 capabilities recorded `observed: {}` and were still advertised as
        # `field_nonempty status`, so they failed their own declared template.
        self.assertIsNone(lane_module._declared_expectation(False, {}))
        # a field recorded as False is NOT evidence for asserting it True
        self.assertIsNone(lane_module._declared_expectation(False, {"pass": False}))

    def test_projection_entry_never_overclaims(self):
        for observed in ({}, {"status": "OK"}, {"pass": True}, {"output_verified": True}):
            receipt = {"capability_id": "x.v1", "module_path": "m.py", "entrypoint": "run",
                       "kind": "contract", "observed": observed, "receipt_path": "r.json",
                       "module_sha256": "0" * 64, "independent_verifier": None}
            exp = lane_module.projection_entry(receipt)["action_template"]["expect"]
            if observed:
                self.assertIsNotNone(exp)
            else:
                self.assertIsNone(exp)


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
        for cid, _path, kind, _entrypoint in candidates:
            # A bound capability may appear, but only if the bound adapter would still
            # refuse it: "already live" is not "already independently verified".
            self.assertTrue(
                cid not in bound or not lane_module._has_independence_claim(bound[cid]),
                f"{cid} is bound and already carries an independence claim; re-receipting it proves nothing",
            )
            self.assertIn(kind, ("contract", "cli"))

    def test_every_discovered_bound_candidate_is_one_the_gate_refuses(self):
        """The bound population added to discovery is exactly the unattested remainder."""
        candidates = lane_module.discover(str(ROOT))
        bound = json.loads((ROOT / lane_module.BOUND).read_text(encoding="utf-8"))["capabilities"]
        discovered_bound = {cid for cid, *_ in candidates if cid in bound}
        self.assertGreater(len(discovered_bound), 0, "no bound capability was left unattested?")
        unattested = {
            cid for cid, entry in bound.items()
            if isinstance(entry, dict) and not lane_module._has_independence_claim(entry)
        }
        self.assertTrue(discovered_bound <= unattested)
        self.assertIn("source.candidates.enumerate.stdlib", discovered_bound)

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


class DeclaredProbeArgsTests(unittest.TestCase):
    """The probe called every contract adapter with `{}` and swallowed the failure.

    `result = fn({}, root)` inside `except BaseException: return None` meant an
    adapter that reads an argument was never executed at all, and the lane reported
    that as "no evidence available" rather than "the probe never ran it".
    """

    def _fake_root(self, tmp, capabilities):
        root = pathlib.Path(tmp)
        for rel in (lane_module.EXTENDED, lane_module.BOUND):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"capabilities": capabilities}), encoding="utf-8")
        return str(root)

    def test_empty_probe_is_still_tried_first(self):
        """Monotonicity: an adapter the empty call already exercises is unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / "m.py"
            mod.write_text("def run(args, root):\n    return {'status': 'OK', 'n': len(args)}\n", encoding="utf-8")
            spec = importlib.util.spec_from_file_location("mono_probe", mod)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result, used = lane_module._probe_invoke(module.run, tmp, "some.capability", "a" * 64)
            self.assertEqual(used, {})
            self.assertEqual(result["n"], 0)

    def test_declared_args_are_used_only_when_the_empty_probe_fails(self):
        entry = {
            "needs.args.v1": {
                "adapter_module": "needs_args",
                "action_template": {
                    "type": "invoke_capability",
                    "args": {
                        "capability_id": "needs.args.v1",
                        "objective": "${input.goal}",
                        "output_path": "${input.output_path}",
                    }
                },
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fake_root(tmp, entry)
            lane_module._DECLARED_ARG_CACHE.pop(root, None)
            mod = pathlib.Path(tmp) / "canonical/runtime/bound_capabilities/needs_args.py"
            mod.parent.mkdir(parents=True, exist_ok=True)
            mod.write_text(
                "def run(args, root):\n"
                "    args = dict(args or {})\n"
                "    if not args.get('output_path'):\n"
                "        raise RuntimeError('JSON_OUTPUT_REQUIRED')\n"
                "    return {'status': 'S', 'objective': args['objective'],\n"
                "            'sink': args['output_path']}\n",
                encoding="utf-8",
            )
            receipt = lane_module.execute_and_receipt(
                "needs.args.v1",
                "canonical/runtime/bound_capabilities/needs_args.py",
                "run",
                root,
                "me",
            )
            self.assertIsNotNone(receipt, "the declared-args fallback must produce a receipt")
            self.assertEqual(receipt["outcome"], "EXECUTED")
            self.assertEqual(receipt["observed"]["status"], "S")
            # the receipt must record what was actually passed, or --verify cannot replay it
            self.assertEqual(receipt["invoked_args"]["objective"], "needs.args.v1")
            self.assertTrue(receipt["invoked_args"]["output_path"].endswith(".json"))
            self.assertNotIn("capability_id", receipt["invoked_args"])

    def test_declared_args_are_deterministic_so_verify_can_replay_them(self):
        entry = {
            "det.v1": {
                "action_template": {"args": {"goal": "${input.goal}", "out": "${input.output_path}"}}
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fake_root(tmp, entry)
            lane_module._DECLARED_ARG_CACHE.pop(root, None)
            first = lane_module.declared_probe_args(root, "det.v1", "b" * 64)
            second = lane_module.declared_probe_args(root, "det.v1", "b" * 64)
            self.assertEqual(first, second)
            self.assertIn("receipt_probe", first["out"])


class BoundDiscoveryTests(unittest.TestCase):
    """Bound capabilities were skipped because "already live" was read as "already verified"."""

    def _root(self, tmp, bound_entry):
        root = pathlib.Path(tmp)
        for rel, caps in ((lane_module.EXTENDED, {}), (lane_module.BOUND, bound_entry)):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"capabilities": caps}), encoding="utf-8")
        mod = root / "canonical/runtime/bound_capabilities/unattested.py"
        mod.parent.mkdir(parents=True, exist_ok=True)
        mod.write_text("def run(args, root):\n    return {'status': 'S'}\n", encoding="utf-8")
        return str(root)

    def test_unattested_bound_capability_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {
                "unattested.v1": {
                    "adapter_module": "unattested",
                    "verification": {"status": "LOCAL_EXECUTION_AND_TEST_VERIFIED",
                                     "independent_public_cross_domain_qualification": False},
                }
            })
            found = {cid for cid, *_ in lane_module.discover(root)}
            self.assertIn("unattested.v1", found)

    def test_independently_verified_bound_capability_is_not_re_receipted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, {
                "unattested.v1": {
                    "adapter_module": "unattested",
                    "verification": {"independently_verified_by": "github-actions:moxnixmdj/brain"},
                }
            })
            found = {cid for cid, *_ in lane_module.discover(root)}
            self.assertNotIn("unattested.v1", found)


class CommittedReceiptReproducesTests(unittest.TestCase):
    """The receipt this change adds must survive the verifier's re-execution."""

    CAPABILITY = "source.candidates.enumerate.stdlib"

    def test_committed_receipt_reproduces_exactly(self):
        path = (
            ROOT / "canonical/astra_runtime/evidence"
            / f"CAPABILITY__{self.CAPABILITY}__EXECUTION_RECEIPT.json"
        )
        self.assertTrue(path.exists(), "the producer receipt must be committed")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["outcome"], "EXECUTED")
        self.assertEqual(receipt["capability_id"], self.CAPABILITY)
        module_path = ROOT / receipt["module_path"]
        spec = importlib.util.spec_from_file_location("replay_enumerate", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        again = getattr(module, receipt["entrypoint"])(
            dict(receipt.get("invoked_args") or {}), str(ROOT)
        )
        self.assertEqual(
            lane_module.sha256_canonical(again),
            receipt["result_sha256"],
            "a receipt the independent verifier cannot reproduce is not evidence",
        )


if __name__ == "__main__":
    unittest.main()
