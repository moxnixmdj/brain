#!/usr/bin/env python3
"""A written artifact is not a verified result.

Measured on `251b2bc` (2026-10-28): **36 of 147 adapters** returned
`output_verified: True` as a literal constant, and the registry uses
`output_verified == true` as the success predicate for 87 of its 128 rows. The door
therefore could not fail those rows once the adapter returned at all.

The concrete failure that made this a defect rather than a style question: asked to repair
a bug outside its five-rewrite vocabulary (a helper called with its arguments swapped), the
repair loop returned `status: OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP`, `pass: false`,
`edits_applied: 0` -- and `output_verified: true`. The door reported PASS, three runs out of
three, on work that never happened.

This file holds the two things that keep that from coming back:

  * `test_a_no_op_repair_may_not_be_reported_as_verified` runs the real adapter through the
    real door and asserts the refusal;
  * `test_no_adapter_hardcodes_the_predicate_it_also_computes` is the fleet invariant: an
    adapter that computes a verdict may not simultaneously hardcode the flag the door judges.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTERS = REPO_ROOT / "canonical" / "runtime" / "bound_capabilities"
REGISTRY = REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"


def _constant(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _dict_pairs(node: ast.Dict):
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            yield key.value, value


def _hardcoded_predicate(tree: ast.AST) -> bool:
    """`{"output_verified": True}` written as a literal, in any dict in the module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in _dict_pairs(node):
                if key == "output_verified" and _constant(value):
                    return True
        if isinstance(node, ast.Assign) and _constant(node.value):
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "output_verified"):
                    return True
    return False


def _computed_pass(tree: ast.AST) -> bool:
    """A `"pass"` entry whose value is an expression, i.e. a verdict that was actually decided."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in _dict_pairs(node):
                if key == "pass" and not isinstance(value, ast.Constant):
                    return True
    return False


class PredicateHonestyTest(unittest.TestCase):
    def test_no_adapter_hardcodes_the_predicate_it_also_computes(self):
        """An adapter that decides a verdict must not also write the door's flag by hand.

        This is the invariant, not a count: it does not stop a *pure writer* from reporting
        that it wrote its artifact, and it cannot be satisfied by editing a number.
        """
        offenders = []
        for path in sorted(ADAPTERS.glob("*.py")):
            if path.name == "__init__.py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # an unparseable adapter is a different defect, reported elsewhere
                continue
            if _hardcoded_predicate(tree) and _computed_pass(tree):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            "these adapters compute a `pass` verdict and then write output_verified=True by "
            "hand, so the door can never fail them: %s" % offenders,
        )

    def test_the_registry_predicate_is_readable_for_every_row(self):
        """Every row's success predicate must be a field the adapter actually returns."""
        caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
        silent = []
        for cid, row in caps.items():
            expect = ((row.get("action_template") or {}).get("expect") or {})
            field = str(expect.get("field") or "")
            if not field:
                silent.append((cid, "no expect field"))
                continue
            declared = set(row.get("result_fields") or [])
            # result_fields is optional in 36 older rows; only judge rows that declare them.
            if declared and field not in declared:
                silent.append((cid, "expects %r, does not declare it" % field))
        self.assertEqual(silent, [], "rows whose success predicate they never declare: %s" % silent)


@unittest.skipUnless(shutil.which("python3"), "python3 is required")
class NoOpRepairIsNotVerifiedTest(unittest.TestCase):
    """The measured failure, end to end through the door."""

    def setUp(self):
        # The adapter resolves its paths against the caller's root, which the door sets to the
        # repository, so the fixture lives in the repository's gitignored scratch directory.
        self._tmp = tempfile.mkdtemp(prefix="brain_predicate_",
                                     dir=str(REPO_ROOT / "canonical" / "astra_runtime" / "tmp"))
        self.root = pathlib.Path(self._tmp).resolve()
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
        self.row = registry["python.software.repair.loop.test_guided.ast.v1"]

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _invoke(self, source: str, test: str):
        (self.root / "m.py").write_text(source, encoding="utf-8")
        (self.root / "test_m.py").write_text(test, encoding="utf-8")
        from canonical.runtime import live_brain_route_admission_v1 as admission

        cid = "python.software.repair.loop.test_guided.ast.v1"
        entry = {"capability_id": cid, "adapter_module": self.row["adapter_module"],
                 "entrypoint": self.row["entrypoint"], "source": self.row["source"],
                 "incremental_spend_usd": 0}
        out = self.root / "out.json"
        action = {"type": "invoke_capability",
                  "args": {"capability_id": cid,
                           "source_paths": [str(self.root / "m.py")],
                           "test_paths": [str(self.root / "test_m.py")],
                           "output_path": str(out)},
                  "expect": self.row["action_template"]["expect"]}
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                return "PASS", admission.run_adapter_locally(entry, action)
            except BaseException as exc:  # the door's refusal is the expected shape here
                return "REFUSED", str(exc)

    # A bug the candidate basis cannot reach: the body must produce a string, and no swap or
    # constant substitution over `None` can write one. The loop therefore finds no edit, and
    # the adapter used to report that as `output_verified: true`.
    #
    # This fixture used to be a swapped call argument, on the grounds that the basis could not
    # express one. `CALL_ARG_SWAP` now exists, the loop repairs that shape in one edit, and the
    # door is right to admit it -- so the no-op case needs a bug that is still outside the basis.
    UNSOLVABLE = ("def describe(x):\n"
                  "    return None\n")

    TEST_UNSOLVABLE = ("import unittest\n"
                       "from m import describe\n\n\n"
                       "class T(unittest.TestCase):\n"
                       "    def test_describe(self):\n"
                       "        self.assertEqual(describe(3), \"odd\")\n")

    # The same predicate on a bug the basis can express, so the adapter must succeed.
    SOLVABLE = ("def area(w, h):\n"
                "    return w - h\n")

    TEST_SOLVABLE = ("import unittest\n"
                     "from m import area\n\n\n"
                     "class T(unittest.TestCase):\n"
                     "    def test_area(self):\n"
                     "        self.assertEqual(area(2, 3), 5)\n")

    def test_a_no_op_repair_may_not_be_reported_as_verified(self):
        verdict, detail = self._invoke(self.UNSOLVABLE, self.TEST_UNSOLVABLE)
        self.assertEqual(verdict, "REFUSED",
                         "the door credited a repair that changed nothing: %s" % (detail,))
        self.assertIn("output_verified", str(detail))
        self.assertEqual((self.root / "m.py").read_text(encoding="utf-8"), self.UNSOLVABLE,
                         "a refused repair must leave the source untouched")

    def test_a_real_repair_still_passes_the_same_predicate(self):
        verdict, detail = self._invoke(self.SOLVABLE, self.TEST_SOLVABLE)
        self.assertEqual(verdict, "PASS", "a real fix must still be credited: %s" % (detail,))
        self.assertTrue(detail.get("output_verified"))


if __name__ == "__main__":
    unittest.main()
