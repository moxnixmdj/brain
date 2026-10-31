"""A placeholder is not a statement: the sentence's own proof outranks a filled default.

Measured 2026-10-31, advanced census request 38:

    "Extract the loop in the function total in <pkg>/util.py into a helper."

The front binder settled the still-unbound ``start_line`` / ``end_line`` by writing the literal
``0`` -- before anything asked ``declared_input_derivation_v1``.  The adapter then refused
``REGION_INVALID`` on a request whose region the repository could prove: the host function was
named with a role phrase ("the function total"), the region was named by its kind ("the loop"),
and the adapter, called with ``qualname=total``, ``start_line=3``, ``end_line=4``, extracts that
loop with gate PASS and one edit.  Nothing was missing but the ORDER of the two answers.

These tests are the rule, in three places, each against an independent oracle:

  * the derivation reads a role-phrase host and a stated region kind (the AST is the oracle);
  * ``derive_declared_inputs`` writes the proven span, not ``0``, for the same sentence;
  * ``door.solve`` serves the request -- and the tree really contains the extracted function,
    which is the only oracle that cannot be satisfied by a report.

The last test breaks the mechanism on purpose: a test that cannot fail is not a test.
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_placeholder_is_not_a_statement"

SOURCE = '''def total(xs):
    out = 0
    for x in xs:
        out += x
    return out
'''

GOAL = "Extract the loop in the function total in {rel} into a helper."


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    pkg = base / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "util.py").write_text(SOURCE, encoding="utf-8")
    return base


def _entry() -> dict:
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    return load_verified_registry()["python.refactor.extract_function.v1"]


class TheSentenceNamesTheHostByItsRole(unittest.TestCase):
    def test_role_phrase_finds_the_host_and_the_stated_loop_is_the_span(self) -> None:
        _fresh("role")
        rel = "canonical/astra_runtime/tmp/test_placeholder_is_not_a_statement/role/pkg/util.py"
        got = derivation.derive(GOAL.format(rel=rel), _entry(), ROOT)
        self.assertEqual(got["qualname"]["value"], "total", got.get("qualname"))
        self.assertEqual(got["qualname"]["rule"], "QUALNAME_PROVED_FROM_STATED_SOURCE_AST",
                         got["qualname"])
        # The oracle is the file's own AST: the single loop node of `total`.
        tree = ast.parse(SOURCE)
        loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)]
        self.assertEqual(len(loops), 1)
        self.assertEqual(got["start_line"]["value"], loops[0].lineno)
        self.assertEqual(got["end_line"]["value"], loops[0].end_lineno)
        self.assertEqual(got["start_line"]["rule"], "SPAN_IS_THE_STATED_REGION_KIND")

    def test_a_stated_loop_span_never_widens_to_its_neighbours(self) -> None:
        """The self-contained-block search alone returns 2-4; the stated kind returns 3-4.

        Widening is not a cosmetic difference: the adapter refuses a span that begins before the
        loop (REGION_NOT_STATEMENT_ALIGNED), so the wider answer is a refusal.
        """
        _fresh("wide")
        rel = "canonical/astra_runtime/tmp/test_placeholder_is_not_a_statement/wide/pkg/util.py"
        got = derivation.derive(GOAL.format(rel=rel), _entry(), ROOT)
        self.assertNotEqual(got["start_line"]["value"], 2)
        self.assertEqual(got["start_line"]["value"], 3)


class ThePlaceholderNeverOutranksTheProof(unittest.TestCase):
    def test_front_binder_writes_the_proven_span_instead_of_zero(self) -> None:
        base = _fresh("front")
        rel = str((base / "pkg/util.py").relative_to(ROOT))
        goal = GOAL.format(rel=rel)
        inputs: dict = {}
        # Exactly the two keys the front binder used to stuff with 0, and nothing else.
        still = front.derive_declared_inputs(
            goal, [("start_line", KeyError("start_line")),
                   ("end_line", KeyError("end_line"))],
            ROOT, _entry(), inputs)
        self.assertEqual(still, [], "a region the sentence states must not stay unbound")
        self.assertEqual((inputs["start_line"], inputs["end_line"]), (3, 4), inputs)

    def test_without_a_stated_region_the_placeholder_is_still_written(self) -> None:
        """The rule must not become a licence to invent a region.

        With no host to hang the span on, the derivation proves nothing, the placeholder stands,
        and the adapter's own contract still fails closed -- exactly as before.
        """
        _fresh("nostated")
        rel = "canonical/astra_runtime/tmp/test_placeholder_is_not_a_statement/nostated/pkg/util.py"
        goal = "Extract the region in %s into a helper." % rel
        self.assertEqual(derivation.derive(goal, _entry(), ROOT).get("start_line"), None)
        inputs: dict = {}
        front.derive_declared_inputs(
            goal, [("start_line", KeyError("start_line")),
                   ("end_line", KeyError("end_line"))],
            ROOT, _entry(), inputs)
        self.assertEqual((inputs["start_line"], inputs["end_line"]), (0, 0), inputs)


class TheDoorServesItAndTheTreeProvesIt(unittest.TestCase):
    def test_extract_request_is_served_and_the_function_exists(self) -> None:
        from canonical.runtime import live_brain_route_admission_v1 as door
        base = _fresh("door")
        rel = str((base / "pkg/util.py").relative_to(ROOT))
        result = door.solve({"task_id": "PLACEHOLDER_38", "goal": GOAL.format(rel=rel)}) or {}
        self.assertTrue(result.get("pass"), result.get("status"))
        # The oracle is the file: a report may not stand in for the edit.
        after = (base / "pkg/util.py").read_text(encoding="utf-8")
        names = [n.name for n in ast.parse(after).body if isinstance(n, ast.FunctionDef)]
        self.assertGreaterEqual(len(names), 2, after)
        self.assertIn("total", names)

    def test_the_mechanism_can_fail(self) -> None:
        """Break the role phrase and the proof disappears -- so the tests above can fail."""
        _fresh("broken")
        rel = "canonical/astra_runtime/tmp/test_placeholder_is_not_a_statement/broken/pkg/util.py"
        without_role = "Extract the loop in %s into a helper." % rel
        got = derivation.derive(without_role, _entry(), ROOT)
        self.assertNotIn("start_line", got)


if __name__ == "__main__":
    unittest.main()
