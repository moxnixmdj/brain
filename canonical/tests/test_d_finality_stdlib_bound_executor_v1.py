import json
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d
from canonical.runtime import d_finality_stdlib_bound_executor_v1 as ex


class DStdlibBoundExecutorTests(unittest.TestCase):
    def _write_repo(self, root: Path, *, source_type="python_stdlib"):
        adapter_dir = root / "canonical/runtime/bound_capabilities"
        adapter_dir.mkdir(parents=True)
        adapter = adapter_dir / "synthetic_stdlib.py"
        adapter.write_text(
            "def run(args, root):\n"
            "    return {'output_verified': args.get('value') == 'ok', 'echo': args.get('value')}\n",
            encoding="utf-8",
        )
        registry = {
            "schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
            "capabilities": {
                "synthetic.stdlib": {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "incremental_spend_usd": 0,
                    "verification": {"independent_verified": True},
                    "source": (
                        {"type": "python_stdlib", "module": "json"}
                        if source_type == "python_stdlib"
                        else {"type": source_type, "executable": "python3"}
                    ),
                    "adapter_module": "synthetic_stdlib",
                    "entrypoint": "run",
                    "action_template": {
                        "type": "invoke_capability",
                        "args": {
                            "capability_id": "synthetic.stdlib",
                            "value": "${input.value}",
                        },
                        "expect": {
                            "type": "field_equals",
                            "field": "output_verified",
                            "value": True,
                        },
                    },
                }
            },
        }
        reg = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps(registry, sort_keys=True), encoding="utf-8")
        return reg, adapter

    def _policy_cert(self, root: Path, reg: Path, adapter: Path, *, version=None):
        version = version or sys.version.split()[0]
        materials = [
            {"path": reg.relative_to(root).as_posix(), "git_blob_sha": d.git_blob_sha_file(reg)},
            {"path": adapter.relative_to(root).as_posix(), "git_blob_sha": d.git_blob_sha_file(adapter)},
        ]
        substrate = {
            "kind": "CPYTHON_STDLIB",
            "implementation": sys.implementation.name,
            "python_version": version,
            "sys_platform": sys.platform,
            "stdlib_modules": ["json"],
        }
        policy = {
            "schema": d.POLICY_SCHEMA,
            "status": "ACTIVE_FAIL_CLOSED",
            "semantic_version": "stdlib-executor-test-v1",
            "rule": "NO_UNDECLARED_D_AUTHORITY",
            "revoked_certificate_sha256": [],
        }
        policy["policy_sha256"] = d.policy_sha256(policy)
        cert = {
            "schema": d.CERT_SCHEMA,
            "status": "VERIFIED_D_FINAL",
            "capability_id": "bound:synthetic.stdlib",
            "capability_contract_sha256": d.sha256_json({"capability": "synthetic.stdlib"}),
            "substrate_contract": substrate,
            "substrate_contract_sha256": d.sha256_json(substrate),
            "policy_sha256": policy["policy_sha256"],
            "registry_snapshot_root": d.sha256_json({"registry": d.git_blob_sha_file(reg)}),
            "state_snapshot_root": d.sha256_json({"state": "none"}),
            "materials": materials,
            "material_closure_root": d.material_closure_root(materials),
            "allowed_capability_ids": ["bound:synthetic.stdlib"],
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

    def test_requires_active_d_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_repo(root)
            out = ex.execute("synthetic.stdlib", inputs={"value": "ok"}, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertIn("ACTIVE_D_EPOCH_REQUIRED", out["errors"][0])

    def test_executes_exact_promoted_stdlib_row_under_d_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, adapter = self._write_repo(root)
            policy, cert = self._policy_cert(root, reg, adapter)
            with d.activate(cert, policy=policy, repo_root=root):
                out = ex.execute(
                    "synthetic.stdlib",
                    inputs={"value": "ok"},
                    repo_root=root,
                )
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["result"]["echo"], "ok")
            self.assertEqual(out["substrate_observation"]["stdlib_modules"], ["json"])
            self.assertEqual(out["donor_capability_calls"], 0)

    def test_action_expectation_failure_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, adapter = self._write_repo(root)
            policy, cert = self._policy_cert(root, reg, adapter)
            with d.activate(cert, policy=policy, repo_root=root):
                out = ex.execute(
                    "synthetic.stdlib",
                    inputs={"value": "bad"},
                    repo_root=root,
                )
            self.assertFalse(out["pass"])
            self.assertIn("ACTION_EXPECTATION_FAILED", out["errors"][0])

    def test_non_stdlib_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, adapter = self._write_repo(root, source_type="system_tool")
            policy, cert = self._policy_cert(root, reg, adapter)
            with d.activate(cert, policy=policy, repo_root=root):
                out = ex.execute(
                    "synthetic.stdlib",
                    inputs={"value": "ok"},
                    repo_root=root,
                )
            self.assertFalse(out["pass"])
            self.assertIn("D_STDLIB_EXECUTOR_SOURCE_TYPE_FORBIDDEN", out["errors"][0])

    def test_substrate_version_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, adapter = self._write_repo(root)
            policy, cert = self._policy_cert(root, reg, adapter, version="0.0.invalid")
            with d.activate(cert, policy=policy, repo_root=root):
                out = ex.execute(
                    "synthetic.stdlib",
                    inputs={"value": "ok"},
                    repo_root=root,
                )
            self.assertFalse(out["pass"])
            self.assertIn("D_SUBSTRATE_PYTHON_VERSION_MISMATCH", out["errors"][0])

    def test_prepare_binds_registry_entry_adapter_and_rendered_action(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, adapter = self._write_repo(root)
            policy, cert = self._policy_cert(root, reg, adapter)
            with d.activate(cert, policy=policy, repo_root=root):
                out = ex.prepare(
                    "synthetic.stdlib",
                    inputs={"value": "ok"},
                    repo_root=root,
                )
            self.assertEqual(out["status"], "PREPARED__D_STDLIB_BOUND_CAPABILITY")
            self.assertEqual(out["adapter_git_blob_sha"], d.git_blob_sha_file(adapter))
            self.assertEqual(out["rendered_action"]["args"]["value"], "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)
