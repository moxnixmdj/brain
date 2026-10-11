import importlib.util,pathlib,sys,tempfile,textwrap,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/python_pair_lookahead_repair_v1.py"
SPEC=importlib.util.spec_from_file_location("pair_repair_v1",PATH)
repair=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repair)

class PairLookaheadRepairV1Tests(unittest.TestCase):
    def fixture(self,files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(body))
        return td,root
    def invoke(self,root,**extra):
        args={"source_root":".","test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","timeout_s":4,"max_files":4,"max_first_candidates":8,"max_second_candidates":8,"max_total_pairs":80}
        args.update(extra); return repair.run(args,root)
    def test_neutral_two_file_pair(self):
        td,root=self.fixture({
            "a.py":"def a():\n    return False\n",
            "b.py":"def b():\n    return False\n",
            "test_all.py":"""
                import unittest
                from a import a
                from b import b
                class X(unittest.TestCase):
                    def test_pair(self): self.assertTrue(a() and b())
                if __name__=="__main__": unittest.main()
            """,
        })
        before={n:(root/n).read_bytes() for n in ("a.py","b.py")}
        out=self.invoke(root)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["baseline_failure_score"],1)
        self.assertEqual(out["pair"]["intermediate_failure_score"],1)
        self.assertEqual([x["failure_score"] for x in out["final_verification_replays"]],[0,0])
        self.assertEqual({x["source_path"] for x in out["patches"]},{"a.py","b.py"})
        self.assertTrue(out["source_restored"])
        for n,v in before.items(): self.assertEqual((root/n).read_bytes(),v)
        td.cleanup()
    def test_one_file_only_rejected(self):
        td,root=self.fixture({
            "a.py":"def a():\n    return False\n",
            "test_all.py":"""
                import unittest
                from a import a
                class X(unittest.TestCase):
                    def test_a(self): self.assertTrue(a())
                if __name__=="__main__": unittest.main()
            """,
        })
        with self.assertRaisesRegex(repair.PairLookaheadError,"PAIR_SEARCH_REQUIRES_TWO_LOCALIZED_FILES"):
            self.invoke(root)
        td.cleanup()
    def test_no_pair_fails_closed(self):
        td,root=self.fixture({
            "a.py":"def a():\n    return 0\n",
            "b.py":"def b():\n    return 0\n",
            "test_all.py":"""
                import unittest
                from a import a
                from b import b
                class X(unittest.TestCase):
                    def test_pair(self): self.assertEqual(a()+b(),99)
                if __name__=="__main__": unittest.main()
            """,
        })
        before={n:(root/n).read_bytes() for n in ("a.py","b.py")}
        out=self.invoke(root,max_first_candidates=4,max_second_candidates=4,max_total_pairs=16)
        self.assertFalse(out["pass"]); self.assertTrue(out["source_restored"])
        for n,v in before.items(): self.assertEqual((root/n).read_bytes(),v)
        td.cleanup()
    def test_baseline_pass_rejected(self):
        td,root=self.fixture({
            "a.py":"def a():\n    return True\n",
            "b.py":"def b():\n    return True\n",
            "test_all.py":"""
                import unittest
                from a import a
                from b import b
                class X(unittest.TestCase):
                    def test_pair(self): self.assertTrue(a() and b())
                if __name__=="__main__": unittest.main()
            """,
        })
        with self.assertRaisesRegex(repair.PairLookaheadError,"BASELINE_ALREADY_PASSES"):
            self.invoke(root)
        td.cleanup()
    def test_path_escape_rejected(self):
        td,root=self.fixture({"a.py":"def a(): return False\n","b.py":"def b(): return False\n","test_all.py":"raise AssertionError()\n"})
        with self.assertRaisesRegex(repair.PairLookaheadError,"PATH_OUTSIDE_REPOSITORY"):
            self.invoke(root,source_root="../")
        td.cleanup()

if __name__=="__main__": unittest.main()
