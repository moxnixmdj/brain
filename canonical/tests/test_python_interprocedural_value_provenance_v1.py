import importlib.util
import pathlib
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "canonical/runtime/bound_capabilities/python_interprocedural_value_provenance_v1.py"
SPEC = importlib.util.spec_from_file_location("prov", PATH)
prov = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prov)


class InterproceduralValueProvenanceV1Tests(unittest.TestCase):
    def fixture(self, files):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        for name, body in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(body), encoding="utf-8")
        return td, root

    def runp(self, root, tests, **extra):
        args = {
            "source_root": ".",
            "test_paths": tests,
            "output_path": "provenance.json",
            "timeout_s": 5,
            "max_trace_events": 50000,
        }
        args.update(extra)
        return prov.run(args, root)

    def test_argument_and_return_binding_cross_function(self):
        td, root = self.fixture(
            {
                "m.py": """
                    def inner(x):
                        y = x + 1
                        return y

                    def outer(x):
                        z = inner(x)
                        return z * 2
                """,
                "test_fail.py": "from m import outer\nassert outer(2) == 8\n",
            }
        )
        with td:
            out = self.runp(root, ["test_fail.py"])
            kinds = {row["kind"] for row in out["value_provenance_edges"]}
            self.assertIn("ARGUMENT", kinds)
            self.assertIn("RETURN_BINDING", kinds)
            ret = [
                row
                for row in out["value_provenance_edges"]
                if row["kind"] == "RETURN_BINDING"
            ][0]
            self.assertEqual(ret["from"]["function"], "inner")
            self.assertEqual(ret["to"]["function"], "outer")
            self.assertEqual(ret["to"]["name"], "z")

    def test_return_to_return_edge(self):
        td, root = self.fixture(
            {
                "m.py": """
                    def inner(x):
                        return x + 1

                    def outer(x):
                        return inner(x)
                """,
                "test_fail.py": "from m import outer\nassert outer(2) == 4\n",
            }
        )
        with td:
            out = self.runp(root, ["test_fail.py"])
            rows = [
                row
                for row in out["value_provenance_edges"]
                if row["kind"] == "RETURN_TO_RETURN"
            ]
            self.assertTrue(rows)
            self.assertEqual(rows[0]["from"]["function"], "inner")
            self.assertEqual(rows[0]["to"]["function"], "outer")

    def test_multiple_calls_on_one_line_are_left_unresolved(self):
        td, root = self.fixture(
            {
                "m.py": """
                    def inner(x):
                        return x + 1

                    def outer(x):
                        return inner(x) + inner(x)
                """,
                "test_fail.py": "from m import outer\nassert outer(2) == 7\n",
            }
        )
        with td:
            out = self.runp(root, ["test_fail.py"])
            inner_edges = [
                row
                for row in out["value_provenance_edges"]
                if row["from"].get("function") == "inner"
            ]
            self.assertEqual(inner_edges, [])

    def test_trace_bound_marks_truncation(self):
        td, root = self.fixture(
            {
                "m.py": """
                    def f():
                        total = 0
                        for i in range(200):
                            total += i
                        return total
                """,
                "test_fail.py": "from m import f\nassert f() == -1\n",
            }
        )
        with td:
            out = self.runp(root, ["test_fail.py"], max_trace_events=50)
            self.assertTrue(out["trace_truncated"])

    def test_path_escape_rejected(self):
        td, root = self.fixture(
            {
                "m.py": "def f(): return 1\n",
                "test_fail.py": "assert False\n",
            }
        )
        with td:
            with self.assertRaisesRegex(
                prov.ValueProvenanceError, "PATH_OUTSIDE_REPOSITORY"
            ):
                self.runp(root, ["test_fail.py"], source_root="../")

    def test_deterministic_and_zero_external_cognition(self):
        files = {
            "m.py": """
                def inner(x):
                    return x + 1

                def outer(x):
                    y = inner(x)
                    return y
            """,
            "test_fail.py": "from m import outer\nassert outer(2) == 4\n",
        }
        td, root = self.fixture(files)
        with td:
            a = self.runp(root, ["test_fail.py"])
            b = self.runp(root, ["test_fail.py"])
            self.assertEqual(a["value_provenance_edges"], b["value_provenance_edges"])
            self.assertEqual(a["model_dependency_count"], 0)
            self.assertEqual(a["external_capability_provider_count"], 0)
            self.assertEqual(a["incremental_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
