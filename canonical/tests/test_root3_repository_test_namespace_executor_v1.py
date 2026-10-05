from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from canonical.runtime import root3_repository_test_namespace_executor_v1 as rte
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as ro
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED
from canonical.runtime.bound_capabilities import python_test_audit


def context(repo: pathlib.Path, test_file: pathlib.Path, *, site=None, timeout=60):
    module_path, lineno, api = site or (
        "canonical/runtime/bound_capabilities/python_test_audit.py",
        50,
        "subprocess.run",
    )
    return {
        "effect_class": "BOUND_CHILD_CODE_EXECUTION",
        "callsite": {
            "module_path": module_path,
            "lineno": lineno,
            "process_api": api,
        },
        "api": "subprocess.run",
        "args": ([os.sys.executable, str(test_file)],),
        "kwargs": {
            "cwd": repo,
            "text": True,
            "capture_output": True,
            "timeout": timeout,
        },
    }


class RepositoryTestNamespaceExecutorTests(unittest.TestCase):
    def tearDown(self):
        try:
            mediator.uninstall()
        except Exception:
            subprocess.run = mediator._ORIGINAL_RUN
            subprocess.Popen = mediator._ORIGINAL_POPEN
            mediator._AUTHORIZER = None
            mediator._AUTHORITY_ID = None
            mediator._CLASS_EXECUTORS = {}
            mediator._INSTALLED = False

    def allow(self, request):
        return {"allowed": True, "authorization_sha256": "a" * 64}

    def test_supported_is_exact_two_site_subset_of_current_bound_child_class(self):
        current = {k for k, v in EXPECTED.items() if v == "BOUND_CHILD_CODE_EXECUTION"}
        self.assertEqual(len(current), 5)
        self.assertEqual(len(rte.SUPPORTED), 2)
        self.assertTrue(set(rte.SUPPORTED).issubset(current))
        self.assertEqual(
            set(rte.SUPPORTED),
            {
                ("canonical/runtime/astra_runtime.py", 1215, "subprocess.run"),
                ("canonical/runtime/bound_capabilities/python_test_audit.py", 50, "subprocess.run"),
            },
        )

    def test_prepare_binds_exact_test_bytes_into_namespace_policy(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            test_file = repo / "canonical/tests/test_x.py"
            test_file.parent.mkdir(parents=True)
            raw = b"print('x')\n"
            test_file.write_bytes(raw)
            prepared = rte._prepare(context(repo, test_file))
            self.assertEqual(prepared["test_sha256"], hashlib.sha256(raw).hexdigest())
            encoded = prepared["policy"]["argv"][-1]
            spec = json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))
            self.assertEqual(spec["test_sha256"], prepared["test_sha256"])
            self.assertEqual(spec["source_path"], "/input/canonical/tests/test_x.py")
            self.assertEqual(spec["logical_path"], "/input/canonical/tests/test_x.py")
            self.assertEqual(spec["cwd"], "/input")

    def test_program_byte_drift_after_prepare_fails_before_test_execution(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            test_file = repo / "test_x.py"
            test_file.write_text("print('before')\n", encoding="utf-8")
            prepared = rte._prepare(context(repo, test_file))
            test_file.write_text("print('after')\n", encoding="utf-8")
            result = ro._run_confined_with_popen(
                prepared["policy"], mediator._ORIGINAL_POPEN
            )
            with self.assertRaisesRegex(
                rte.RepositoryTestDenied, "TEST_PROGRAM_SHA256_MISMATCH"
            ):
                rte._decode_result(result, prepared)

    def test_real_namespace_test_cannot_write_repo_or_inherit_broker(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            test_file = repo / "test_boundary.py"
            test_file.write_text(
                "import os,pathlib,unittest\n"
                "class T(unittest.TestCase):\n"
                "  def test_boundary(self):\n"
                "    self.assertNotIn('PROJECT_BRAIN_BROKER_FD',os.environ)\n"
                "    with self.assertRaises(OSError): pathlib.Path('forbidden.txt').write_text('x')\n"
                "if __name__=='__main__': unittest.main()\n",
                encoding="utf-8",
            )
            ex = rte.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
            cp = ex(context(repo, test_file))
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn("Ran 1 test", cp.stderr)
            self.assertFalse((repo / "forbidden.txt").exists())
            receipt = cp.project_brain_execution_receipt
            self.assertEqual(receipt["test_sha256"], hashlib.sha256(test_file.read_bytes()).hexdigest())
            self.assertEqual(receipt["material_effects_committed"], 0)
            self.assertTrue(receipt["repository_read_only"])
            self.assertFalse(receipt["test_child_broker_fd_inherited"])

    def test_unsupported_bound_child_site_denies_before_spawn(self):
        calls = []
        ex = rte.make_executor(popen_impl=lambda *a, **k: calls.append((a, k)))
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            test_file = repo / "test_x.py"
            test_file.write_text("print('x')\n", encoding="utf-8")
            ctx = context(
                repo,
                test_file,
                site=(
                    "canonical/runtime/auto_python_source_codec_acquisition.py",
                    217,
                    "subprocess.run",
                ),
            )
            with self.assertRaisesRegex(
                rte.RepositoryTestDenied, "REPOSITORY_TEST_CALLSITE_NOT_SUPPORTED"
            ):
                ex(ctx)
        self.assertEqual(calls, [])

    def test_test_program_outside_repository_denies(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as od:
            repo = pathlib.Path(td)
            test_file = pathlib.Path(od) / "test_x.py"
            test_file.write_text("print('x')\n", encoding="utf-8")
            with self.assertRaisesRegex(
                rte.RepositoryTestDenied, "TEST_PROGRAM_OUTSIDE_REPOSITORY"
            ):
                rte._prepare(context(repo, test_file))

    def test_real_python_test_audit_routes_through_mediator_and_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            tests_dir = repo / "canonical/tests"
            tests_dir.mkdir(parents=True)
            test_file = tests_dir / "test_sample.py"
            test_file.write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "  def test_ok(self): self.assertEqual(2+2,4)\n"
                "if __name__=='__main__': unittest.main()\n",
                encoding="utf-8",
            )
            ex = rte.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
            mediator.install(
                self.allow,
                authority_id="TEST",
                class_executors={"BOUND_CHILD_CODE_EXECUTION": ex},
            )
            out = python_test_audit.run(
                {
                    "source_root": "canonical/tests",
                    "pattern": "test_*.py",
                    "timeout_s": 60,
                    "output_path": "audit.json",
                },
                repo,
            )
            self.assertEqual(out["file_count"], 1)
            self.assertEqual(out["failed_count"], 0)
            self.assertEqual(out["error_count"], 0)
            self.assertTrue(out["output_verified"])
            audit = json.loads((repo / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["totals"]["files"], 1)
            self.assertEqual(audit["totals"]["failed"], 0)
            self.assertEqual(audit["totals"]["errors"], 0)

    def test_wrong_effect_class_and_popen_are_denied(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            test_file = repo / "test_x.py"
            test_file.write_text("print('x')\n", encoding="utf-8")
            ctx = context(repo, test_file)
            ctx["effect_class"] = "READ_ONLY_DECLARED_QUERY"
            with self.assertRaisesRegex(rte.RepositoryTestDenied, "EFFECT_CLASS_MISMATCH"):
                rte._prepare(ctx)
            ctx = context(repo, test_file)
            ctx["api"] = "subprocess.Popen"
            with self.assertRaisesRegex(rte.RepositoryTestDenied, "PROCESS_API_NOT_SUPPORTED"):
                rte._prepare(ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
