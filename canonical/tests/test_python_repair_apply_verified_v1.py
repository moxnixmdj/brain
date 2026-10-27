from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

BASE=pathlib.Path("canonical/runtime/bound_capabilities")
SPEC=importlib.util.spec_from_file_location("applyv1",BASE/"python_repair_apply_verified_v1.py")
applyv1=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(applyv1)

SRC="def f(x):\n    return x < 3\n"
TEST="from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n"


class RepairApplyVerifiedTests(unittest.TestCase):
    def fixture(self,src=SRC,test=TEST):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        (root/"m.py").write_text(textwrap.dedent(src),encoding="utf-8")
        (root/"test_all.py").write_text(textwrap.dedent(test),encoding="utf-8")
        return td,root

    def go(self,root,**extra):
        args={
            "source_root":".",
            "test_paths":["test_all.py"],
            "test_argv":[sys.executable,"test_all.py"],
            "output_path":"report.json",
            "timeout_s":120,
        }
        args.update(extra)
        return applyv1.run(args,root)

    # ---- the thing this capability exists to do ----

    def test_a_verified_repair_is_applied_and_the_stated_test_passes_in_place(self):
        td,root=self.fixture()
        before=(root/"m.py").read_bytes()
        with td:
            out=self.go(root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["status"],"PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE")
            self.assertTrue(out["applied"],out)
            self.assertEqual(out["files_written"],["m.py"])
            self.assertEqual(out["pre_apply_test_returncode"],1)
            self.assertEqual(out["post_apply_test_returncode"],0)
            self.assertFalse(out["source_restored"])
            # The claim is about bytes on disk, not about the report.
            after=(root/"m.py").read_bytes()
            self.assertNotEqual(after,before)
            self.assertEqual(after,textwrap.dedent("def f(x):\n    return x <= 3\n").encode("utf-8"))
            self.assertTrue(out["unified_diffs"])
            self.assertIn("-    return x < 3",out["unified_diffs"][0])
            self.assertIn("+    return x <= 3",out["unified_diffs"][0])

    def test_the_fixed_file_really_satisfies_the_stated_test_run_afresh(self):
        # Independent of the capability's own report: run the stated test again
        # in a fresh interpreter against the file it left behind.
        import subprocess
        td,root=self.fixture()
        with td:
            out=self.go(root)
            self.assertTrue(out["pass"],out)
            proc=subprocess.run([sys.executable,"test_all.py"],cwd=str(root),
                                capture_output=True,check=False)
            self.assertEqual(proc.returncode,0,proc.stderr.decode("utf-8","replace"))

    # ---- the gates that must refuse ----

    def test_a_stated_test_that_already_passes_is_refused_and_nothing_is_written(self):
        td,root=self.fixture(src="def f(x):\n    return x <= 3\n")
        original=(root/"m.py").read_bytes()
        with td:
            out=self.go(root)
            self.assertFalse(out["pass"],out)
            self.assertEqual(out["status"],"REFUSED__STATED_TEST_ALREADY_PASSES")
            self.assertFalse(out["applied"])
            self.assertEqual(out["pre_apply_test_returncode"],0)
            self.assertEqual((root/"m.py").read_bytes(),original)

    def test_no_bounded_repair_means_no_write(self):
        td,root=self.fixture(src="def f(x):\n    return x\n",test="from m import f\nassert f(2)==99999\n")
        original=(root/"m.py").read_bytes()
        with td:
            out=self.go(root,max_pair_candidates=10,mutations_per_file=4)
            self.assertFalse(out["pass"],out)
            self.assertEqual(out["status"],"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH")
            self.assertFalse(out["applied"])
            self.assertEqual(out["files_written"],[])
            self.assertEqual((root/"m.py").read_bytes(),original)

    def test_a_patch_that_fails_in_place_is_rolled_back_byte_for_byte(self):
        # The nearest world in which the accepting test above must fail: the same
        # verified patch, but the stated test does not pass in place afterwards.
        td,root=self.fixture()
        original=(root/"m.py").read_bytes()
        real=applyv1._run_test
        calls={"n":0}
        def fake(argv,cwd,timeout):
            calls["n"]+=1
            return (1,b"") if calls["n"]==1 else (1,b"STILL_BROKEN")
        applyv1._run_test=fake
        try:
            with td:
                out=self.go(root)
                self.assertFalse(out["pass"],out)
                self.assertEqual(out["status"],"FAIL_CLOSED__IN_PLACE_VERIFICATION_FAILED_AFTER_APPLY")
                self.assertFalse(out["applied"])
                self.assertTrue(out["source_restored"])
                self.assertEqual(out["files_written"],[])
                self.assertEqual((root/"m.py").read_bytes(),original)
        finally:
            applyv1._run_test=real

    def test_a_patch_whose_bytes_do_not_match_its_own_hash_never_reaches_the_disk(self):
        td,root=self.fixture()
        original=(root/"m.py").read_bytes()
        real=applyv1._REPAIR.run
        def fake(args,repo):
            row=dict((real(args,repo).get("patches") or [{}])[0])
            row["candidate_sha256"]="0"*64
            return {"status":"PATCHES","patches":[row]}
        applyv1._REPAIR.run=fake
        try:
            with td:
                with self.assertRaisesRegex(applyv1.RepairApplyError,"PATCH_CANDIDATE_SHA_MISMATCH"):
                    self.go(root)
                self.assertEqual((root/"m.py").read_bytes(),original)
        finally:
            applyv1._REPAIR.run=real

    def test_a_patch_claiming_different_original_bytes_never_reaches_the_disk(self):
        td,root=self.fixture()
        original=(root/"m.py").read_bytes()
        real=applyv1._REPAIR.run
        def fake(args,repo):
            row=dict((real(args,repo).get("patches") or [{}])[0])
            row["original_sha256"]="1"*64
            return {"status":"PATCHES","patches":[row]}
        applyv1._REPAIR.run=fake
        try:
            with td:
                with self.assertRaisesRegex(applyv1.RepairApplyError,"PATCH_ORIGINAL_SHA_MISMATCH"):
                    self.go(root)
                self.assertEqual((root/"m.py").read_bytes(),original)
        finally:
            applyv1._REPAIR.run=real

    def test_no_temporary_sibling_is_left_beside_the_file_it_wrote(self):
        td,root=self.fixture()
        with td:
            self.go(root)
            leftovers=[p.name for p in root.iterdir() if "brain_apply_tmp" in p.name]
            self.assertEqual(leftovers,[])

    # ---- the standing constraints ----

    def test_zero_external_model_cognition_and_zero_spend(self):
        td,root=self.fixture()
        with td:
            out=self.go(root)
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

    def test_the_report_is_written_and_states_what_happened(self):
        td,root=self.fixture()
        with td:
            out=self.go(root)
            report=json.loads((root/"report.json").read_text())
            self.assertEqual(report["status"],out["status"])
            self.assertTrue(report["output_verified"])
            self.assertEqual(report["files_written"],["m.py"])

    def test_a_refusal_is_also_written_to_the_report(self):
        td,root=self.fixture(src="def f(x):\n    return x <= 3\n")
        with td:
            self.go(root)
            report=json.loads((root/"report.json").read_text())
            self.assertEqual(report["status"],"REFUSED__STATED_TEST_ALREADY_PASSES")
            self.assertFalse(report["pass"])

    def test_the_same_request_twice_gives_the_same_verdict(self):
        verdicts=[]
        for _ in range(2):
            td,root=self.fixture()
            with td:
                out=self.go(root)
                verdicts.append((out["status"],tuple(out["files_written"]),
                                 out["pre_apply_test_returncode"],out["post_apply_test_returncode"]))
        self.assertEqual(verdicts[0],verdicts[1])

    def test_missing_test_paths_is_refused_rather_than_guessed(self):
        td,root=self.fixture()
        with td:
            with self.assertRaisesRegex(applyv1.RepairApplyError,"TEST_PATHS_REQUIRED"):
                applyv1.run({"source_root":".","output_path":"r.json"},root)


if __name__=="__main__":
    unittest.main(verbosity=2)
