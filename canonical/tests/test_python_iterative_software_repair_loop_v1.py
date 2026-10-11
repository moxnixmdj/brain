import importlib.util,pathlib,sys,tempfile,textwrap,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/python_iterative_software_repair_loop_v1.py"
SPEC=importlib.util.spec_from_file_location("repair_loop_v1",PATH)
repair=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repair)

class IterativeSoftwareRepairLoopV1Tests(unittest.TestCase):
    def fixture(self,files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(body))
        return td,root

    def invoke(self,root,**extra):
        args={
            "source_root":".",
            "test_paths":["test_all.py"],
            "test_argv":[sys.executable,"test_all.py"],
            "output_path":"result.json",
            "timeout_s":5,
            "max_rounds":6,
            "max_files":4,
            "max_candidates_per_file":20,
            "max_total_candidates":120,
        }
        args.update(extra)
        return repair.run(args,root)

    def test_two_file_two_round_repair_and_restore(self):
        td,root=self.fixture({
            "a.py":"def f(x):\n    return x < 3\n",
            "b.py":"def g(x):\n    return x + 1\n",
            "test_all.py":"""
                import unittest
                from a import f
                from b import g
                class X(unittest.TestCase):
                    def test_a(self): self.assertTrue(f(3))
                    def test_b(self): self.assertEqual(g(1),3)
                if __name__=="__main__": unittest.main()
            """,
        })
        before={name:(root/name).read_bytes() for name in ("a.py","b.py")}
        out=self.invoke(root)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["accepted_edit_count"],2)
        self.assertEqual([x["score_after"] for x in out["accepted_edits"]],[1,0])
        self.assertEqual(len(out["patches"]),2)
        self.assertEqual([x["failure_score"] for x in out["final_verification_replays"]],[0,0])
        self.assertTrue(out["source_restored"])
        for name,data in before.items(): self.assertEqual((root/name).read_bytes(),data)
        td.cleanup()

    def test_single_file_boundary_repair(self):
        td,root=self.fixture({
            "m.py":"def f(x):\n    return x < 3\n",
            "test_all.py":"""
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_a(self): self.assertTrue(f(3))
                if __name__=="__main__": unittest.main()
            """,
        })
        out=self.invoke(root)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["accepted_edit_count"],1)
        self.assertIn("Lt->LtE",str(out["accepted_edits"][0]["mutation"]))
        td.cleanup()

    def test_no_solution_fails_closed_and_restores(self):
        td,root=self.fixture({
            "m.py":"def f(x):\n    return x\n",
            "test_all.py":"""
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_a(self): self.assertEqual(f(2),5)
                if __name__=="__main__": unittest.main()
            """,
        })
        before=(root/"m.py").read_bytes()
        out=self.invoke(root)
        self.assertFalse(out["pass"])
        self.assertTrue(out["source_restored"])
        self.assertEqual((root/"m.py").read_bytes(),before)
        td.cleanup()

    def test_one_round_cannot_finish_two_edit_problem(self):
        td,root=self.fixture({
            "a.py":"def f(x):\n    return x < 3\n",
            "b.py":"def g(x):\n    return x + 1\n",
            "test_all.py":"""
                import unittest
                from a import f
                from b import g
                class X(unittest.TestCase):
                    def test_a(self): self.assertTrue(f(3))
                    def test_b(self): self.assertEqual(g(1),3)
                if __name__=="__main__": unittest.main()
            """,
        })
        out=self.invoke(root,max_rounds=1)
        self.assertFalse(out["pass"])
        self.assertEqual(out["accepted_edit_count"],1)
        self.assertTrue(out["source_restored"])
        td.cleanup()

    def test_already_passing_baseline_rejected(self):
        td,root=self.fixture({
            "m.py":"def f(x): return x\n",
            "test_all.py":"""
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_a(self): self.assertEqual(f(2),2)
                if __name__=="__main__": unittest.main()
            """,
        })
        with self.assertRaisesRegex(repair.RepairLoopError,"BASELINE_ALREADY_PASSES"):
            self.invoke(root)
        td.cleanup()

    def test_path_escape_rejected(self):
        td,root=self.fixture({
            "m.py":"def f(x): return x\n",
            "test_all.py":"raise AssertionError()\n",
        })
        with self.assertRaisesRegex(repair.RepairLoopError,"PATH_OUTSIDE_REPOSITORY"):
            self.invoke(root,source_root="../")
        td.cleanup()

if __name__=="__main__":
    unittest.main()
