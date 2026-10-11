from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime.bound_capabilities.python_software_acceptance_spec_v1 import (
    compile_request,
    verify_acceptance,
)


class SoftwareAcceptanceSpecV1Tests(unittest.TestCase):
    def repo(self):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        (root/"pkg").mkdir()
        (root/"tests").mkdir()
        (root/"pkg/app.py").write_text("def answer():\n    return 42\n",encoding="utf-8")
        (root/"README.md").write_text("hello\n",encoding="utf-8")
        (root/"tests/test_app.py").write_text(
            "import unittest\n"
            "from pkg.app import answer\n"
            "class T(unittest.TestCase):\n"
            "    def test_answer(self): self.assertEqual(answer(),42)\n"
            "if __name__=='__main__': unittest.main()\n",
            encoding="utf-8",
        )
        return td,root

    def test_explicit_file_compile_and_test_requirements_pass(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        req=(
            "pkg/app.py must compile; "
            "tests/test_app.py tests must pass; "
            "README.md must contain \"hello\""
        )
        plan=compile_request(req,root)
        out=verify_acceptance(plan,root)
        self.assertTrue(plan["all_critical_bound"])
        self.assertTrue(out["pass"])
        self.assertFalse(out["merge_or_promotion_authority"])

    def test_passing_test_does_not_override_unbound_semantics(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        req="tests/test_app.py tests must pass; function answer should satisfy the unspecified business rule"
        plan=compile_request(req,root)
        out=verify_acceptance(plan,root)
        self.assertEqual(plan["unbound_predicate_count"],1)
        self.assertFalse(out["pass"])
        self.assertTrue(out["existing_test_pass_does_not_override_unbound_semantics"])

    def test_do_not_modify_binds_baseline_and_detects_change(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("do not modify README.md",root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"README.md").write_text("changed\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_only_modify_scope_detects_out_of_scope_change(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("only modify pkg/app.py",root)
        (root/"pkg/app.py").write_text("def answer():\n    return 43\n",encoding="utf-8")
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"README.md").write_text("changed\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_create_and_absent_file_predicates(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        (root/"new.py").write_text("x=1\n",encoding="utf-8")
        plan=compile_request("create file new.py; remove file old.py",root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])

    def test_text_absent(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request('README.md must not contain "secret"',root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"README.md").write_text("secret\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_python_compile_failure(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("pkg/app.py must compile",root)
        (root/"pkg/app.py").write_text("def broken(:\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_test_failure_is_detected(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("tests/test_app.py tests must pass",root)
        (root/"pkg/app.py").write_text("def answer():\n    return 0\n",encoding="utf-8")
        out=verify_acceptance(plan,root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_results"][0]["verifier_kind"],"PYTHON_TEST_FILE_PASS")

    def test_unsafe_path_is_never_bound(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("create file ../escape.py",root)
        self.assertFalse(plan["all_critical_bound"])
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_model_dependency_and_score_nonclaims(self):
        td,root=self.repo()
        self.addCleanup(td.cleanup)
        plan=compile_request("pkg/app.py must compile",root)
        out=verify_acceptance(plan,root)
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertIn("NO_FRONTIERCODE_SCORE_CREDIT",out["hard_nonclaims"])


if __name__=="__main__":
    unittest.main(verbosity=2)
