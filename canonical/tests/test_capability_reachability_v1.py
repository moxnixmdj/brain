"""Tests for the reachability census and the declaration resolver.

The whole point of these two modules is that a capability which cannot be reached
cannot be used. So the tests are built to catch the three ways that claim could rot:

  1. the census could count a module as reachable because a TEST imports it. A test
     proves a capability; it does not deliver one. If counting tests as reach were
     allowed, every orphan would look alive and the census would be worthless.
  2. the resolver could resolve a capability whose verifier does not exist. Then a
     registry entry would be a wish, not a binding. It must fail closed.
  3. the resolver could resolve a capability whose entry point does not exist, or is
     not callable. Same failure mode, later in the pipeline, harder to see.

Each of those is a synthetic tree built here, so the test measures the rule and not
the author's optimism. The final test runs against the real repository and asserts that
the four capabilities we actually declared are resolvable end to end.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import textwrap
import unittest

from canonical.runtime.capability_declaration_resolver_v1 import (
    CapabilityError,
    Resolver,
    resolve_all,
    usable,
)
from canonical.tools.capability_reachability_census_v1 import (
    ReachabilityError,
    census_reachability,
    load_declared,
)

REPO = pathlib.Path(__file__).resolve().parents[2]


def _write(root: pathlib.Path, rel: str, body: str) -> pathlib.Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def _tree(tmp: pathlib.Path, *, test_imports_orphan: bool = True) -> pathlib.Path:
    """A miniature repository with one reachable and one orphaned module."""
    _write(tmp, "canonical/runtime/brain_unified_model_v1.py", """
        from canonical.runtime import fabric_stub_v1
    """)
    _write(tmp, "canonical/runtime/fabric_stub_v1.py", """
        def run(x=None):
            return {"pass": True}
    """)
    # reachable transitively through the fabric
    _write(tmp, "canonical/runtime/used_v1.py", """
        def entry(utterance):
            return ["used"]
    """)
    # make used_v1 reachable: fabric_stub_v1 imports it
    _write(tmp, "canonical/runtime/fabric_stub_v1.py", """
        from canonical.runtime.used_v1 import entry

        def run(x=None):
            return {"pass": True}
    """)
    # orphaned: nothing imports it
    _write(tmp, "canonical/runtime/orphan_v1.py", """
        def entry(utterance):
            return ["orphan"]
    """)
    if test_imports_orphan:
        _write(tmp, "canonical/tests/test_orphan_v1.py", """
            from canonical.runtime.orphan_v1 import entry
        """)
    return tmp


class TestCensusDoesNotCountTestsAsReach(unittest.TestCase):
    def test_orphan_stays_orphaned_even_when_a_test_imports_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = _tree(pathlib.Path(d))
            out = census_reachability(root, front_doors=("canonical/runtime/brain_unified_model_v1.py",),
                                      registry=None)
            self.assertIn("canonical/runtime/orphan_v1.py", out["orphaned_runtime_modules"])
            self.assertNotIn("canonical/runtime/used_v1.py", out["orphaned_runtime_modules"])

    def test_reachable_fraction_is_a_fraction_of_the_population(self):
        with tempfile.TemporaryDirectory() as d:
            root = _tree(pathlib.Path(d))
            out = census_reachability(root, front_doors=("canonical/runtime/brain_unified_model_v1.py",),
                                      registry=None)
            self.assertEqual(out["runtime_modules_total"], 4)  # brain_unified, fabric_stub, used, orphan
            self.assertEqual(out["reachable_runtime_modules"] + out["orphaned_runtime_modules_count"], 4)

    def test_missing_front_door_is_an_error_not_an_empty_success(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ReachabilityError):
                census_reachability(pathlib.Path(d), front_doors=("canonical/runtime/nope.py",))


class TestDeclarationMakesReachable(unittest.TestCase):
    def test_declaring_an_orphan_moves_it_out_of_the_orphan_set(self):
        with tempfile.TemporaryDirectory() as d:
            root = _tree(pathlib.Path(d))
            _write(root, "canonical/tests/test_orphan_v1.py", "")
            reg = {
                "capabilities": {
                    "orphan.thing": {
                        "module": "canonical/runtime/orphan_v1.py",
                        "verifier": "canonical/tests/test_orphan_v1.py",
                        "entry": "entry",
                    }
                }
            }
            (root / "canonical/runtime/REG.json").write_text(json.dumps(reg), encoding="utf-8")
            out = census_reachability(
                root,
                front_doors=("canonical/runtime/brain_unified_model_v1.py",),
                registry="canonical/runtime/REG.json",
            )
            self.assertNotIn("canonical/runtime/orphan_v1.py", out["orphaned_runtime_modules"])
            self.assertEqual(out["declared_and_usable"], 1)

    def test_a_declaration_with_no_verifier_is_reported_defective_and_grants_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root = _tree(pathlib.Path(d))
            reg = {
                "capabilities": {
                    "orphan.thing": {
                        "module": "canonical/runtime/orphan_v1.py",
                        "verifier": "canonical/tests/DOES_NOT_EXIST.py",
                        "entry": "entry",
                    }
                }
            }
            (root / "canonical/runtime/REG.json").write_text(json.dumps(reg), encoding="utf-8")
            out = census_reachability(
                root,
                front_doors=("canonical/runtime/brain_unified_model_v1.py",),
                registry="canonical/runtime/REG.json",
            )
            self.assertIn("orphan.thing", out["declared_but_defective"])
            self.assertEqual(out["declared_and_usable"], 0)
            self.assertIn("canonical/runtime/orphan_v1.py", out["orphaned_runtime_modules"])


class TestResolverFailsClosed(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _tree(pathlib.Path(self._tmp.name))
        reg = {
            "capabilities": {
                "good": {
                    "module": "canonical/runtime/orphan_v1.py",
                    "verifier": "canonical/tests/test_orphan_v1.py",
                    "entry": "entry",
                },
                "no_verifier": {
                    "module": "canonical/runtime/orphan_v1.py",
                    "verifier": "canonical/tests/missing.py",
                    "entry": "entry",
                },
                "no_entry": {
                    "module": "canonical/runtime/orphan_v1.py",
                    "verifier": "canonical/tests/test_orphan_v1.py",
                    "entry": "not_a_function_in_the_module",
                },
                "no_module": {
                    "module": "canonical/runtime/ghost_v1.py",
                    "verifier": "canonical/tests/test_orphan_v1.py",
                    "entry": "entry",
                },
            }
        }
        (self.root / "canonical/runtime/REG.json").write_text(json.dumps(reg), encoding="utf-8")
        self.reg = "canonical/runtime/REG.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_good_one_resolves_and_runs(self):
        r = Resolver(self.root, self.reg)
        self.assertEqual(r.invoke("good", "an utterance"), ["orphan"])

    def test_each_defect_raises_with_its_own_name(self):
        r = Resolver(self.root, self.reg)
        with self.assertRaisesRegex(CapabilityError, "VERIFIER_MISSING"):
            r.resolve("no_verifier")
        with self.assertRaisesRegex(CapabilityError, "ENTRY_MISSING"):
            r.resolve("no_entry")
        with self.assertRaisesRegex(CapabilityError, "MODULE_MISSING"):
            r.resolve("no_module")

    def test_undeclared_capability_is_refused_rather_than_improvised(self):
        r = Resolver(self.root, self.reg)
        with self.assertRaisesRegex(CapabilityError, "NOT_DECLARED"):
            r.resolve("not.in.the.registry")

    def test_usable_returns_only_what_actually_resolves(self):
        caps = usable(self.root, self.reg)
        self.assertEqual(sorted(caps), ["good"])

    def test_resolve_all_reports_every_entry_and_hides_nothing(self):
        rows = resolve_all(self.root, self.reg)
        self.assertEqual(sorted(rows), ["good", "no_entry", "no_module", "no_verifier"])
        self.assertFalse(rows["no_verifier"]["entry_exists"] and rows["no_verifier"]["verifier_exists"])


class TestRealRepositoryDeclarations(unittest.TestCase):
    """The four capabilities declared in this change resolve against the real tree."""

    def test_declared_capabilities_are_all_resolvable(self):
        rows = resolve_all(REPO)
        self.assertGreaterEqual(len(rows), 4, "registry is missing its declared capabilities")
        for cap_id, row in rows.items():
            with self.subTest(capability=cap_id):
                self.assertTrue(row["module_exists"], f"{cap_id}: module missing")
                self.assertTrue(row["verifier_exists"], f"{cap_id}: verifier missing")
                self.assertTrue(row["entry_exists"], f"{cap_id}: entry point missing")

    def test_the_task_state_ledger_really_runs_and_refuses_ambiguity(self):
        r = Resolver(REPO)
        fn = r.resolve("osworld.task_state_ledger")
        reqs, errs = fn("Write the summary to /home/user/reports/q3.txt")
        self.assertTrue(reqs, "a literal path should compile to a requirement")
        self.assertEqual(errs, [])
        vague, vague_errs = fn("Create a file named budget.csv in the Desktop folder")
        self.assertEqual(vague, [], "an unanchored instruction must not invent a path")
        self.assertIn("NO_EXPLICIT_STATE_PATH", vague_errs)

    def test_the_census_on_the_real_tree_is_not_trivially_empty(self):
        out = census_reachability(REPO)
        self.assertGreater(out["runtime_modules_total"], 1000)
        self.assertGreater(out["reachable_runtime_modules"], 100)
        self.assertGreater(out["orphaned_runtime_modules_count"], 0)
        self.assertLess(out["reachable_fraction"], 1.0)


if __name__ == "__main__":
    unittest.main()
