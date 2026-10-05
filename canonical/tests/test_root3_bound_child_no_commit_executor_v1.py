from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import root3_bound_child_no_commit_executor_v1 as ex
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED


ROOT = pathlib.Path(__file__).resolve().parents[2]


class BoundChildNoCommitExecutorTests(unittest.TestCase):
    def _ctx(self, module, line, argv, *, cwd=ROOT, timeout=30, env=None):
        kwargs = {
            "cwd": cwd,
            "text": True,
            "capture_output": True,
            "timeout": timeout,
        }
        if env is not None:
            kwargs["env"] = env
        return {
            "effect_class": "BOUND_CHILD_CODE_EXECUTION",
            "callsite": {
                "module_path": module,
                "lineno": line,
                "process_api": "subprocess.run",
            },
            "args": (argv,),
            "kwargs": kwargs,
        }

    def test_supported_is_exact_three_site_subset_of_current_bound_child_class(self):
        current = {k for k, v in EXPECTED.items() if v == "BOUND_CHILD_CODE_EXECUTION"}
        self.assertEqual(len(current), 5)
        self.assertEqual(len(ex.SUPPORTED), 3)
        self.assertTrue(set(ex.SUPPORTED).issubset(current))
        self.assertEqual(
            current - set(ex.SUPPORTED),
            {
                ("canonical/runtime/astra_runtime.py", 5777, "subprocess.run"),
                ("canonical/runtime/bound_capabilities/node_library_codec.py", 16, "subprocess.run"),
            },
        )

    def test_repo_python_verification_maps_repo_read_only(self):
        target = ROOT / "canonical/runtime/python_codec_probe.py"
        prepared = ex._prepare(
            self._ctx(
                "canonical/runtime/astra_runtime.py",
                1215,
                [sys.executable, str(target)],
                timeout=180,
            )
        )
        self.assertEqual(pathlib.Path(prepared["input_dir"]), ROOT)
        self.assertEqual(prepared["inner"][1], "/input/canonical/runtime/python_codec_probe.py")
        self.assertEqual(prepared["policy"]["input_dir"], str(ROOT.resolve()))
        self.assertEqual(prepared["policy"]["argv"][0:3], ["/usr/bin/python3", "-I", "-c"])

    def test_python_test_audit_profile_is_supported(self):
        target = ROOT / "canonical/runtime/python_codec_probe.py"
        prepared = ex._prepare(
            self._ctx(
                "canonical/runtime/bound_capabilities/python_test_audit.py",
                50,
                [sys.executable, str(target)],
                timeout=60,
            )
        )
        self.assertEqual(prepared["profile"], "REPO_PYTHON_TEST_AUDIT")

    def test_node_codec_site_remains_fail_closed(self):
        with self.assertRaisesRegex(ex.BoundChildDenied, "NOT_SUPPORTED"):
            ex._prepare(
                self._ctx(
                    "canonical/runtime/bound_capabilities/node_library_codec.py",
                    16,
                    ["node", str(ROOT / "canonical/runtime/node_codec_runner.js")],
                    timeout=60,
                )
            )

    def test_nested_astra_mission_site_remains_fail_closed(self):
        with self.assertRaisesRegex(ex.BoundChildDenied, "NOT_SUPPORTED"):
            ex._prepare(
                self._ctx(
                    "canonical/runtime/astra_runtime.py",
                    5777,
                    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), "x.json"],
                    timeout=600,
                )
            )

    def test_wrong_python_executable_denied(self):
        target = ROOT / "canonical/runtime/python_codec_probe.py"
        with self.assertRaisesRegex(ex.BoundChildDenied, "PYTHON_EXECUTABLE"):
            ex._prepare(
                self._ctx(
                    "canonical/runtime/astra_runtime.py",
                    1215,
                    ["/bin/false", str(target)],
                    timeout=30,
                )
            )

    def test_repo_target_outside_declared_root_denied(self):
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "x.py"
            target.write_text("print('x')\n", encoding="utf-8")
            with self.assertRaisesRegex(ex.BoundChildDenied, "PATH_OUTSIDE_DECLARED_ROOT"):
                ex._prepare(
                    self._ctx(
                        "canonical/runtime/astra_runtime.py",
                        1215,
                        [sys.executable, str(target)],
                        timeout=30,
                    )
                )

    def test_custom_environment_denied_for_no_commit_profiles(self):
        target = ROOT / "canonical/runtime/python_codec_probe.py"
        with self.assertRaisesRegex(ex.BoundChildDenied, "CUSTOM_ENV_FORBIDDEN"):
            ex._prepare(
                self._ctx(
                    "canonical/runtime/bound_capabilities/python_test_audit.py",
                    50,
                    [sys.executable, str(target)],
                    timeout=30,
                    env={"PATH": "/tmp"},
                )
            )

    def test_codec_probe_stages_only_regular_bounded_source_tree(self):
        helper = ROOT / "canonical/runtime/python_codec_probe.py"
        with tempfile.TemporaryDirectory() as td:
            site = pathlib.Path(td) / "site"
            pkg = site / "pkg"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text(
                "def encode(x, **kw): return json.dumps(x).encode()\n"
                "def decode(x, **kw): return json.loads(x.decode())\n"
                "import json\n",
                encoding="utf-8",
            )
            prepared = ex._prepare(
                self._ctx(
                    "canonical/runtime/auto_python_source_codec_acquisition.py",
                    217,
                    [sys.executable, str(helper), str(site), json.dumps(["pkg"])],
                    timeout=90,
                )
            )
            try:
                staged = pathlib.Path(prepared["input_dir"])
                self.assertTrue((staged / "python_codec_probe.py").is_file())
                self.assertTrue((staged / "site/pkg/__init__.py").is_file())
                self.assertEqual(prepared["inner"][1:3], ["/input/python_codec_probe.py", "/input/site"])
            finally:
                import shutil
                shutil.rmtree(prepared["cleanup_dir"], ignore_errors=True)

    def test_codec_probe_rejects_module_list_expansion(self):
        helper = ROOT / "canonical/runtime/python_codec_probe.py"
        with tempfile.TemporaryDirectory() as td:
            site = pathlib.Path(td) / "site"
            site.mkdir()
            (site / "x.py").write_text("x=1\n", encoding="utf-8")
            with self.assertRaisesRegex(ex.BoundChildDenied, "MODULE_LIST_INVALID"):
                ex._prepare(
                    self._ctx(
                        "canonical/runtime/auto_python_source_codec_acquisition.py",
                        217,
                        [sys.executable, str(helper), str(site), json.dumps(["a", "b"])],
                        timeout=90,
                    )
                )

    def test_completed_process_preserves_caller_shape(self):
        target = ROOT / "canonical/runtime/python_codec_probe.py"
        prepared = ex._prepare(
            self._ctx(
                "canonical/runtime/astra_runtime.py",
                1215,
                [sys.executable, str(target)],
                timeout=30,
            )
        )
        import base64
        result = {
            "timed_out": False,
            "returncode": 7,
            "stdout_b64": base64.b64encode(b"out").decode(),
            "stderr_b64": base64.b64encode(b"err").decode(),
        }
        got = ex._completed(prepared, result)
        self.assertEqual(got.returncode, 7)
        self.assertEqual(got.stdout, "out")
        self.assertEqual(got.stderr, "err")


if __name__ == "__main__":
    unittest.main(verbosity=2)
