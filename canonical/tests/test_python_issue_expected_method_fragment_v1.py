from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest

BASE=pathlib.Path("canonical/runtime/bound_capabilities")

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,BASE/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

v10=_load("v10_issue_fragment","python_issue_expected_method_fragment_v1.py")
v9=_load("v9_behavior_compiler","python_software_request_semantic_acceptance_v1.py")

REQUESTS_7594="""## Summary
The issue lies in: `src/requests/cookies.py`

`MockResponse.getheaders()` does not return the result of `self._headers.getheaders(name)`, causing it to always return `None`.

It should be:
```python
def getheaders(self, name: str) -> Any:
    return self._headers.getheaders(name)
```
"""


class PythonIssueExpectedMethodFragmentV1Tests(unittest.TestCase):
    def candidate(self,source):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        p=root/"src/requests/cookies.py"
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(source,encoding="utf-8")
        return td,root

    def test_real_requests_issue_falsifies_frozen_v9_but_yields_v10_fragment(self):
        prior=v9.compile_request(REQUESTS_7594)
        self.assertFalse(prior["coverage_complete"],prior)
        self.assertEqual(len(prior["compiled_obligation_ids"]),0)
        self.assertGreater(len(prior["residual_obligation_ids"]),0)

        out=v10.compile_fragment(REQUESTS_7594)
        self.assertTrue(out["fragment_compiled"],out)
        self.assertGreater(len(out["fragment_covered_obligation_ids"]),0)
        self.assertGreater(len(out["residual_obligation_ids"]),0)
        self.assertFalse(out["full_task_coverage_complete"])
        self.assertFalse(out["acceptance_stop_authorized"])
        self.assertEqual(out["fragment"]["path"],"src/requests/cookies.py")
        self.assertEqual(out["fragment"]["class_name"],"MockResponse")
        self.assertEqual(out["fragment"]["method_name"],"getheaders")

    def test_expected_method_ast_fragment_passes_without_mutating_candidate(self):
        td,root=self.candidate(
            "from typing import Any\n"
            "class MockResponse:\n"
            "    def getheaders(self, name: str) -> Any:\n"
            "        return self._headers.getheaders(name)\n"
        )
        with td:
            p=root/"src/requests/cookies.py"
            before=p.read_bytes()
            compiled=v10.compile_fragment(REQUESTS_7594)
            out=v10.evaluate_fragment(compiled,root)
            self.assertTrue(out["fragment_pass"],out)
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertEqual(p.read_bytes(),before)
            self.assertFalse(out["source_mutated"])

    def test_wrong_method_body_fails_fragment(self):
        td,root=self.candidate(
            "from typing import Any\n"
            "class MockResponse:\n"
            "    def getheaders(self, name: str) -> Any:\n"
            "        self._headers.getheaders(name)\n"
        )
        with td:
            out=v10.evaluate_fragment(v10.compile_fragment(REQUESTS_7594),root)
            self.assertFalse(out["fragment_pass"],out)
            self.assertEqual(out["reason"],"EXPECTED_METHOD_AST_MISMATCH")

    def test_same_method_in_wrong_class_does_not_pass(self):
        td,root=self.candidate(
            "from typing import Any\n"
            "class Other:\n"
            "    def getheaders(self, name: str) -> Any:\n"
            "        return self._headers.getheaders(name)\n"
        )
        with td:
            out=v10.evaluate_fragment(v10.compile_fragment(REQUESTS_7594),root)
            self.assertFalse(out["fragment_pass"],out)
            self.assertEqual(out["reason"],"TARGET_CLASS_METHOD_NOT_UNIQUE")

    def test_ambiguous_multiple_paths_fail_closed(self):
        task=REQUESTS_7594.replace(
            "The issue lies in: `src/requests/cookies.py`",
            "The issue lies in: `src/requests/cookies.py`\n"
            "The issue lies in: `src/requests/other.py`",
        )
        out=v10.compile_fragment(task)
        self.assertFalse(out["fragment_compiled"],out)
        self.assertIn("EXPECTED_EXACTLY_ONE_ISSUE_PATH",out["errors"])

    def test_ambiguous_multiple_expected_markers_fail_closed(self):
        task=REQUESTS_7594+"\nIt should be:\n```python\ndef x(): pass\n```\n"
        out=v10.compile_fragment(task)
        self.assertFalse(out["fragment_compiled"],out)
        self.assertIn("EXPECTED_EXACTLY_ONE_IT_SHOULD_BE_MARKER",out["errors"])

    def test_unsafe_path_fails_closed(self):
        task=REQUESTS_7594.replace(
            "src/requests/cookies.py","../src/requests/cookies.py"
        )
        out=v10.compile_fragment(task)
        self.assertFalse(out["fragment_compiled"],out)
        self.assertIn("ISSUE_PATH_INVALID",out["errors"])

    def test_expected_method_name_must_match_named_subject(self):
        task=REQUESTS_7594.replace(
            "def getheaders(self, name: str) -> Any:",
            "def other(self, name: str) -> Any:",
        )
        out=v10.compile_fragment(task)
        self.assertFalse(out["fragment_compiled"],out)
        self.assertIn("EXPECTED_METHOD_NAME_MISMATCH",out["errors"])

    def test_deterministic_and_zero_external_cognition(self):
        a=v10.compile_fragment(REQUESTS_7594)
        b=v10.compile_fragment(REQUESTS_7594)
        self.assertEqual(a,b)
        self.assertEqual(a["model_dependency_count"],0)
        self.assertEqual(a["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertEqual(a["incremental_spend_usd"],0)

    def test_bound_run_writes_verified_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            out=v10.run(
                {"task_text":REQUESTS_7594,"output_path":"fragment.json"},root
            )
            self.assertTrue(out["output_verified"],out)
            self.assertTrue((root/"fragment.json").is_file())
            self.assertTrue(out["output_sha256"])


if __name__=="__main__":
    unittest.main(verbosity=2)
