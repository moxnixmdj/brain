from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime import astra_runtime
from canonical.runtime import bound_capability_isolated_runner_v1 as runner


class _Proc:
    returncode=0
    stdout=""
    stderr=""


class NativeRiskIsolationTests(unittest.TestCase):
    def test_exact_isolation_allowlist(self):
        self.assertEqual(
            runner.ALLOWED_ADAPTERS,
            {
                "python_library_codec",
                "docx_report_from_json",
                "python_document_builder",
                "xlsx_verify_openpyxl",
            },
        )
        self.assertEqual(
            astra_runtime._NATIVE_RISK_ISOLATED_ADAPTERS,
            runner.ALLOWED_ADAPTERS,
        )

    def test_parent_helper_uses_child_result_without_parent_adapter_import(self):
        calls=[]
        def fake_run(argv,**kwargs):
            calls.append((argv,kwargs))
            pathlib.Path(argv[-1]).write_text('{"ok":true}',encoding="utf-8")
            return _Proc()
        with mock.patch.object(astra_runtime.subprocess,"run",side_effect=fake_run):
            out=astra_runtime._invoke_isolated_bound_adapter(
                "python_library_codec","run",{"x":1}
            )
        self.assertTrue(out["ok"])
        self.assertEqual(calls[0][0][0],astra_runtime.sys.executable)
        self.assertIn("bound_capability_isolated_runner_v1.py",calls[0][0][1])
        self.assertEqual(calls[0][0][2:4],["python_library_codec","run"])
        self.assertEqual(json.loads(calls[0][1]["input"]),{"args":{"x":1}})

    def test_nonallowlisted_isolation_fails_before_process_spawn(self):
        with mock.patch.object(astra_runtime.subprocess,"run") as proc:
            with self.assertRaisesRegex(
                astra_runtime.Blocker,"ISOLATED_BOUND_ADAPTER_NOT_ALLOWLISTED"
            ):
                astra_runtime._invoke_isolated_bound_adapter(
                    "pdf_pypdf","run",{}
                )
        proc.assert_not_called()

    def test_runner_rejects_nonallowlisted_adapter(self):
        with tempfile.TemporaryDirectory(prefix="project-brain-isolated-cap-") as td:
            p=pathlib.Path(td)/"result.json"
            with self.assertRaisesRegex(runner.IsolatedAdapterError,"MODULE_NOT_ALLOWLISTED"):
                runner.execute("pdf_pypdf","run",b'{"args":{}}',p)

    def test_runner_result_path_must_be_dedicated_temp_dir(self):
        with self.assertRaisesRegex(
            runner.IsolatedAdapterError,"RESULT_PATH_OUTSIDE_DEDICATED_TEMP_DIR"
        ):
            runner._result_path(str(pathlib.Path(tempfile.gettempdir())/"result.json"))


if __name__=="__main__":
    unittest.main(verbosity=2)
