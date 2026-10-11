from __future__ import annotations
import pathlib
import sys
import tempfile
import textwrap
import unittest

from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as coupled
from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as strict


class CoupledSoftwareRepairLoopV1Tests(unittest.TestCase):
    def fixture(self, files):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        for name, body in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(body))
        return td, root

    def args(self):
        return {
            "source_root": ".",
            "test_paths": ["test_all.py"],
            "test_argv": [sys.executable, "test_all.py"],
            "output_path": "result.json",
            "timeout_s": 5,
            "max_rounds": 4,
            "max_files": 4,
            "max_candidates_per_file": 30,
            "max_pair_first_candidates": 80,
            "max_pair_second_candidates": 80,
            "max_total_candidates": 1200,
        }

    def neutral_pair_fixture(self):
        return {
            "a.py": """
                def inc(x):
                    return x + 1
            """,
            "b.py": """
                from a import inc
                def f(x):
                    return inc(x) * 2
            """,
            "test_all.py": """
                import unittest
                from b import f
                class X(unittest.TestCase):
                    def test_value(self):
                        self.assertEqual(f(2), 12)
                if __name__ == "__main__":
                    unittest.main()
            """,
        }

    def test_crosses_neutral_intermediate_pair_that_strict_loop_cannot(self):
        td, root = self.fixture(self.neutral_pair_fixture())
        with td:
            before = {p.name: p.read_bytes() for p in (root/"a.py", root/"b.py")}
            strict_out = strict.run({
                "source_root": ".",
                "test_paths": ["test_all.py"],
                "test_argv": [sys.executable, "test_all.py"],
                "output_path": "strict.json",
                "timeout_s": 5,
                "max_rounds": 4,
                "max_files": 4,
                "max_candidates_per_file": 30,
                "max_total_candidates": 300,
            }, root)
            self.assertFalse(strict_out["pass"], strict_out)
            out = coupled.run(self.args(), root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["baseline_failure_score"], 1)
            self.assertEqual(out["final_failure_score"], 0)
            self.assertGreaterEqual(out["coupled_pair_count"], 1)
            pair = next(x for x in out["accepted_actions"] if x["kind"] == "NEUTRAL_INTERMEDIATE_COUPLED_PAIR")
            self.assertEqual(len({e["source_path"] for e in pair["edits"]}), 2)
            self.assertEqual({p["source_path"] for p in out["patches"]}, {"a.py", "b.py"})
            self.assertEqual([x["failure_score"] for x in out["final_verification_replays"]], [0, 0])
            self.assertTrue(out["source_restored"])
            for p in (root/"a.py", root/"b.py"):
                self.assertEqual(p.read_bytes(), before[p.name])

    def test_strict_single_still_works_without_pair(self):
        td, root = self.fixture({
            "m.py": "def f(x):\n    return x < 3\n",
            "test_all.py": """
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_boundary(self):
                        self.assertTrue(f(3))
                if __name__ == "__main__":
                    unittest.main()
            """,
        })
        with td:
            out = coupled.run(self.args(), root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["coupled_pair_count"], 0)
            self.assertEqual(out["accepted_actions"][0]["kind"], "STRICT_SINGLE")

    def test_localization_prefers_imported_source_and_records_evidence(self):
        td, root = self.fixture(self.neutral_pair_fixture() | {"z_unrelated.py": "def noise(): return 99\n"})
        with td:
            baseline = coupled._run(root, [sys.executable, "test_all.py"], 5)
            rows = coupled.localize_sources(root, root, [root/"test_all.py"], baseline, max_files=4)
            by = {x["source_path"]: x for x in rows}
            self.assertIn("b.py", by)
            self.assertTrue(by["b.py"]["test_import_hit"])
            self.assertGreater(by["b.py"]["localization_score"], by["z_unrelated.py"]["localization_score"])

    def test_no_solution_fails_closed_and_restores(self):
        td, root = self.fixture({
            "m.py": "def f(x):\n    return x\n",
            "test_all.py": """
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_v(self):
                        self.assertEqual(f(2), 5)
                if __name__ == "__main__":
                    unittest.main()
            """,
        })
        with td:
            before = (root/"m.py").read_bytes()
            a = self.args()
            a.update({"max_candidates_per_file": 5, "max_pair_first_candidates": 5, "max_pair_second_candidates": 5, "max_total_candidates": 40})
            out = coupled.run(a, root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["source_restored"])
            self.assertEqual((root/"m.py").read_bytes(), before)

    def test_zero_model_zero_spend(self):
        td, root = self.fixture({
            "m.py": "def f(x):\n    return x < 3\n",
            "test_all.py": """
                import unittest
                from m import f
                class X(unittest.TestCase):
                    def test_boundary(self):
                        self.assertTrue(f(3))
                if __name__ == "__main__":
                    unittest.main()
            """,
        })
        with td:
            out = coupled.run(self.args(), root)
            self.assertTrue(out["pass"])
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"], 0)
            self.assertEqual(out["external_capability_provider_count"], 0)
            self.assertEqual(out["incremental_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
