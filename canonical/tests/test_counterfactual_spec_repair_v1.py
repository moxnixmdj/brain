import importlib.util
import pathlib
import sys
import tempfile
import textwrap
import unittest

SPEC = importlib.util.spec_from_file_location(
    "cf", "canonical/runtime/bound_capabilities/python_counterfactual_spec_repair_v1.py")
cf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cf)


class T(unittest.TestCase):
    def fixture(self, source, test):
        td = tempfile.TemporaryDirectory()
        r = pathlib.Path(td.name)
        (r / "m.py").write_text(textwrap.dedent(source))
        (r / "test_m.py").write_text(textwrap.dedent(test))
        return td, r

    def run_cf(self, r, **extra):
        a = {
            "source_path": "m.py",
            "test_paths": ["test_m.py"],
            "test_argv": [sys.executable, "-m", "pytest", "test_m.py",
                          "-q", "-p", "no:cacheprovider"],
            "output_path": "result.json",
            "timeout_s": 5,
            "wall_budget_s": 45.0,
            "max_sites": 12,
            "max_terms": 50,
        }
        a.update(extra)
        return cf.run(a, root=r)

    # ---- site collection -------------------------------------------------
    def test_collect_sites_finds_cond_and_ret(self):
        src = "def f(x):\n    if x < 3:\n        return 0\n    return 1\n"
        sites = cf.collect_sites(src, "m.py")
        kinds = {s.kind for s in sites}
        self.assertIn("cond", kinds)
        self.assertIn("ret", kinds)
        self.assertTrue(any(s.kind == "expr" for s in sites) or len(sites) >= 2)

    # ---- term generation -------------------------------------------------
    def test_generate_terms_includes_names_and_consts(self):
        src = "def f(a, b):\n    return a\n"
        sites = cf.collect_sites(src, "m.py")
        ret = next(s for s in sites if s.kind == "ret")
        terms = cf.generate_terms(ret, ["a", "b"], [7, True], {}, cf._DEFAULT_OPS,
                                  max_terms=80)
        self.assertIn("a", terms)
        self.assertIn("b", terms)
        self.assertIn("7", terms)
        # names survive truncation and precede composite binaries
        self.assertIn("(a + b)", terms)
        self.assertLess(terms.index("a"), terms.index("(a + b)"))

    def test_generate_terms_slice_and_max(self):
        src = "def f(arr, k, longest, length):\n    return length + 1\n"
        sites = cf.collect_sites(src, "m.py")
        ret = next(s for s in sites if s.kind == "ret")
        terms = cf.generate_terms(ret, ["arr", "k", "longest", "length"],
                                  [0], {}, cf._DEFAULT_OPS, max_terms=80)
        self.assertTrue(any("[" in t and ":" in t for t in terms), terms[:40])
        self.assertTrue(any(t.startswith("max(") for t in terms), terms[:40])

    # ---- end-to-end on tiny fixtures ------------------------------------
    def test_return_constant(self):
        td, r = self.fixture(
            "def f():\n    return 4\n",
            """import unittest
from m import f
class X(unittest.TestCase):
    def test_v(self): self.assertEqual(f(), 7)
if __name__ == '__main__': unittest.main()
""")
        with td:
            o = self.run_cf(r)
            self.assertTrue(o["pass"], o.get("status"))
            self.assertIn("return 7", o["unified_diff"])
            self.assertEqual(o["model_dependency_count"], 0)
            self.assertTrue(o["source_restored"])

    def test_condition_swap(self):
        # Two separate test methods so BOTH observations (x=4 and x=3) are
        # logged; a single method stops at the first failed assert.
        # x < 3 fails these; x > 3 (or x >= 3, x == 3, ...) passes.
        td, r = self.fixture(
            "def f(x):\n    return x < 3\n",
            """import unittest
from m import f
class X(unittest.TestCase):
    def test_hi(self): self.assertTrue(f(4))
    def test_lo(self): self.assertFalse(f(3))
if __name__ == '__main__': unittest.main()
""")
        with td:
            o = self.run_cf(r)
            self.assertTrue(o["pass"], o.get("status"))
            diff = o["unified_diff"] or ""
            self.assertTrue(
                any(s in diff for s in ("x > 3", "x >= 3", "x == 3", "x != 3",
                                        "x >= 4", "x > 2", "3 < x", "3 <= x",
                                        "not (x < 3)")),
                diff,
            )

    def test_no_solution_restores_source(self):
        # Same input, two different required outputs: no single expression
        # can satisfy both -- must return OPEN and restore the source.
        s = "def f(x):\n    return x\n"
        td, r = self.fixture(
            s,
            """import unittest
from m import f
class X(unittest.TestCase):
    def test_a(self): self.assertEqual(f(1), 2)
    def test_b(self): self.assertEqual(f(1), 3)
if __name__ == '__main__': unittest.main()
""")
        with td:
            o = self.run_cf(r)
            self.assertFalse(o["pass"], o)
            self.assertTrue(o["source_restored"])
            self.assertEqual((r / "m.py").read_text(), textwrap.dedent(s))

    def test_baseline_already_passes_rejected(self):
        td, r = self.fixture(
            "def f():\n    return 1\n",
            """import unittest
from m import f
class X(unittest.TestCase):
    def test_v(self): self.assertEqual(f(), 1)
if __name__ == '__main__': unittest.main()
""")
        with td:
            with self.assertRaisesRegex(cf.CounterfactualSpecError,
                                        "BASELINE_ALREADY_PASSES"):
                self.run_cf(r)

    def test_swap_arguments_via_name_term(self):
        # gcd-shaped: recursive call args swapped; force arg0 to name b.
        td, r = self.fixture(
            """def gcd(a, b):
    if b == 0:
        return a
    return gcd(a % b, b)
""",
            """import unittest
from m import gcd
class X(unittest.TestCase):
    def test_v(self):
        self.assertEqual(gcd(35, 21), 7)
        self.assertEqual(gcd(13, 13), 13)
if __name__ == '__main__': unittest.main()
""")
        with td:
            o = self.run_cf(r)
            self.assertTrue(o["pass"], o.get("status"))
            # The winning term should replace a % b with b (or equivalent).
            self.assertTrue(
                "gcd(b, b)" in o["unified_diff"]
                or "gcd(b, a % b)" in o["unified_diff"]
                or "b" in (o.get("winning_term") or ""),
                o,
            )

    def test_deterministic(self):
        src = "def f(x):\n    return x < 3\n"
        test = """import unittest
from m import f
class X(unittest.TestCase):
    def test_v(self):
        self.assertTrue(f(3))
        self.assertFalse(f(4))
if __name__ == '__main__': unittest.main()
"""
        td1, r1 = self.fixture(src, test)
        td2, r2 = self.fixture(src, test)
        with td1, td2:
            a = self.run_cf(r1)
            b = self.run_cf(r2)
            self.assertEqual(a.get("candidate_source_sha256"),
                             b.get("candidate_source_sha256"))
            self.assertEqual(a.get("unified_diff"), b.get("unified_diff"))

    def test_zero_network_and_spend_fields(self):
        td, r = self.fixture(
            "def f():\n    return 4\n",
            """import unittest
from m import f
class X(unittest.TestCase):
    def test_v(self): self.assertEqual(f(), 7)
if __name__ == '__main__': unittest.main()
""")
        with td:
            o = self.run_cf(r)
            self.assertEqual(o["model_dependency_count"], 0)
            self.assertEqual(o["incremental_spend_usd"], 0)
            self.assertEqual(o["external_capability_provider_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
