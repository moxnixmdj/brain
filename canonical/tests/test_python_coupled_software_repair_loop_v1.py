import importlib.util, pathlib, tempfile, textwrap, unittest, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/python_coupled_software_repair_loop_v1.py"
SPEC=importlib.util.spec_from_file_location("coupled",PATH)
repair=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repair)
class CoupledSoftwareRepairLoopV1Tests(unittest.TestCase):
    def fixture(self,files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(body))
        return td,root
    def invoke(self,root,**extra):
        args={"source_root":".","test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","timeout_s":5,"max_rounds":5,"max_files":6,"max_variants_per_file":12,"max_single_candidates":3,"max_pair_candidates":4}
        args.update(extra); return repair.run(args,root)
    def test_neutral_intermediate_pair_can_solve(self):
        td,root=self.fixture({"a.py":"def a():\n    return 1\n","b.py":"def b():\n    return 1\n","test_all.py":"""
            import unittest
            from a import a
            from b import b
            class X(unittest.TestCase):
                def test_sum(self): self.assertEqual(a()+b(),4)
            if __name__=='__main__': unittest.main()
        """})
        with td:
            before={n:(root/n).read_bytes() for n in ("a.py","b.py")}; out=self.invoke(root)
            self.assertTrue(out["pass"],out); self.assertGreaterEqual(out["coupled_pair_event_count"],1); self.assertEqual([x["failure_score"] for x in out["final_verification_replays"]],[0,0]); self.assertTrue(out["source_restored"])
            for n,b in before.items(): self.assertEqual((root/n).read_bytes(),b)
    def test_strict_single_improvement_still_supported(self):
        td,root=self.fixture({"m.py":"def f():\n    return False\n","test_all.py":"""
            import unittest
            from m import f
            class X(unittest.TestCase):
                def test_f(self): self.assertTrue(f())
            if __name__=='__main__': unittest.main()
        """})
        with td:
            out=self.invoke(root); self.assertTrue(out["pass"],out); self.assertEqual(out["accepted_edit_sets"][0]["edit_kind"],"single")
    def test_localization_ranks_imported_symbol_files(self):
        td,root=self.fixture({"a.py":"def a():\n    return 1\n","b.py":"def b():\n    return 1\n","noise.py":"def z():\n    return 99\n","test_all.py":"""
            import unittest
            from a import a
            from b import b
            class X(unittest.TestCase):
                def test_sum(self): self.assertEqual(a()+b(),4)
            if __name__=='__main__': unittest.main()
        """})
        with td:
            out=self.invoke(root); top={r["source_path"] for r in out["localization"][:2]}; self.assertEqual(top,{"a.py","b.py"}); self.assertTrue(any("TEST_REFERENCED_SYMBOL" in r["reasons"] for r in out["localization"][:2]))
    def test_no_solution_fails_closed_and_restores(self):
        td,root=self.fixture({"m.py":"def f(x):\n    return x\n","test_all.py":"""
            import unittest
            from m import f
            class X(unittest.TestCase):
                def test_f(self): self.assertEqual(f(2),99)
            if __name__=='__main__': unittest.main()
        """})
        with td:
            before=(root/"m.py").read_bytes(); out=self.invoke(root,max_single_candidates=10,max_pair_candidates=10); self.assertFalse(out["pass"]); self.assertTrue(out["source_restored"]); self.assertEqual((root/"m.py").read_bytes(),before)
    def test_path_escape_rejected(self):
        td,root=self.fixture({"m.py":"def f():\n    return False\n","test_all.py":"raise AssertionError()\n"})
        with td:
            with self.assertRaisesRegex(repair.RepairLoopError,"PATH_OUTSIDE_REPOSITORY"): self.invoke(root,source_root="../")
    def test_deterministic_replay_and_zero_model(self):
        files={"a.py":"def a():\n    return 1\n","b.py":"def b():\n    return 1\n","test_all.py":"""
            import unittest
            from a import a
            from b import b
            class X(unittest.TestCase):
                def test_sum(self): self.assertEqual(a()+b(),4)
            if __name__=='__main__': unittest.main()
        """}
        td,root=self.fixture(files)
        with td:
            x=self.invoke(root); y=self.invoke(root); self.assertEqual(x["accepted_edit_sets"],y["accepted_edit_sets"]); self.assertEqual(x["patches"],y["patches"]); self.assertEqual(x["model_dependency_count"],0); self.assertEqual(x["external_capability_provider_count"],0); self.assertEqual(x["incremental_spend_usd"],0)
if __name__=='__main__': unittest.main(verbosity=2)
