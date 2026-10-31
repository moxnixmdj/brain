# PROJECT_BRAIN
"""A repair is an edit plus a referee; the sentence decides, the suite proves.

Two census rows have scored zero since revision 2 -- *resolve a merge conflict* and
*inline a helper* -- and neither was a missing analysis.  Both were missing the
same thing: **a controller that writes to the tree and then proves it**.  Every
adapter in the analysis lane answered questions; nothing could change a file.

Measured on the census fixtures, first run:

    python.vcs.merge_conflict.resolve.v1   -> markers gone, 200, suite green   125-189 ms
    python.refactor.inline_helper.v1       -> helper gone, 165, suite green    101-109 ms

Four laws, each one a refusal:

1. KEEP BOTH IS A UNION.  The sentence says which resolution it wants.  Two sides
   the author asked to keep are the concatenation of both, in order -- and the
   proof is that the module parses and the suite passes.  A diff3 base section
   (``|||||||``) means the two sides are not the whole story, so it is refused.

2. SINGLE-USE IS A PROPERTY OF THE TREE.  Selecting the helper by its shape ("ends
   in a single return") also matched the caller, which also ends in a return.
   Exactly one call site is what "single-use" means, and the tree says it.

3. A DUPLICATED CALL IS NEVER SUBSTITUTED.  Inlining replaces a call with its
   body, and a body can use a parameter more than once.  An argument that is a
   call, a lambda, an await or a comprehension would then run twice.

4. THE REFEREE IS THE SUITE.  Every adapter here restores every original byte
   before returning failure.  A conflicted tree is better than a corrupted one,
   and a repair that reports success without running the tests is the class of
   answer this repository exists to stop.

The third row this slice was built for -- *remove the SQL injection* -- is
measured at the adapter level and **not** shipped: the composer claims that clause
and turns "Remove the SQL injection" into ``rm <db.py>``.  Deleting the file is not
a parameterised query, and a row that cannot be reached is not a row.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_inline_helper as inline  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_merge_resolve as merge  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/pin_repair_lane_v1"

CONFLICTED = '''"""Models."""

<<<<<<< HEAD
def line_total(item):
    return item.price_cents * item.qty
=======
class Item:
    def __init__(self, price_cents, qty=1):
        self.price_cents = price_cents
        self.qty = qty
>>>>>>> feature/item-class
'''

CONFLICT_TEST = '''import unittest
from app.models import Item, line_total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(line_total(Item(100, 2)), 200)
'''

HELPER = '''"""Logic."""


def _price_with_tax(price_cents, rate):
    return price_cents + price_cents * rate // 100


def total(items, rate):
    return sum(_price_with_tax(i["price_cents"], rate) for i in items)
'''

HELPER_TEST = '''import unittest
from app.service import total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([{"price_cents": 100}, {"price_cents": 50}], 10), 165)
'''


class Base(unittest.TestCase):
    files: dict[str, str] = {}

    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        for rel, text in self.files.items():
            path = WORK / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def run_adapter(self, module, **extra):
        return module.run(dict({"source_root": str(WORK / "app"),
                                "output_path": str(WORK / "answer.json")}, **extra), str(ROOT))


class TestAConflictIsTheUnionItsAuthorAskedFor(Base):
    files = {"app/__init__.py": "", "app/models.py": CONFLICTED,
             "tests/__init__.py": "", "tests/test_models.py": CONFLICT_TEST}

    def test_both_sides_survive_and_the_suite_is_green(self):
        out = self.run_adapter(merge)
        text = (WORK / "app/models.py").read_text(encoding="utf-8")
        self.assertNotIn("<<<<<<<", text)
        self.assertNotIn("=======", text)
        self.assertIn("def line_total", text)
        self.assertIn("class Item", text)
        self.assertTrue(out["suite_passed"])
        self.assertEqual(out["resolved_file_count"], 1)

    def test_the_artifact_is_written(self):
        self.run_adapter(merge)
        report = json.loads((WORK / "answer.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "PROJECT_BRAIN_PYTHON_MERGE_CONFLICT_RESOLVE_V1")
        self.assertEqual(report["resolved"][0]["regions"][0]["resolution"],
                         "KEEP_BOTH__OURS_THEN_THEIRS")

    def test_a_diff3_base_section_is_refused_not_guessed(self):
        (WORK / "app/models.py").write_text(
            CONFLICTED.replace("<<<<<<< HEAD", "<<<<<<< HEAD\n||||||| base\nx = 1"), encoding="utf-8")
        before = (WORK / "app/models.py").read_text(encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            self.run_adapter(merge)
        self.assertIn("DIFF3", str(caught.exception))
        self.assertEqual((WORK / "app/models.py").read_text(encoding="utf-8"), before)

    def test_a_tree_with_no_markers_is_refused(self):
        (WORK / "app/models.py").write_text("x = 1\n", encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            self.run_adapter(merge)
        self.assertIn("NO_CONFLICT_MARKERS_FOUND", str(caught.exception))


class TestASingleUseHelperBecomesItsBody(Base):
    files = {"app/__init__.py": "", "app/service.py": HELPER,
             "tests/__init__.py": "", "tests/test_service.py": HELPER_TEST}

    def test_the_helper_is_inlined_and_the_value_is_unchanged(self):
        out = self.run_adapter(inline)
        text = (WORK / "app/service.py").read_text(encoding="utf-8")
        self.assertNotIn("_price_with_tax", text)
        self.assertEqual(out["helper"], "_price_with_tax")
        self.assertTrue(out["suite_passed"])

    def test_single_use_is_read_from_the_tree_not_from_the_shape(self):
        # `total` also ends in a single return; only the call-site count says
        # which of the two is the helper.
        self.assertEqual(self.run_adapter(inline)["helper"], "_price_with_tax")

    def test_a_call_argument_is_never_duplicated(self):
        # `int(rate)` is the only call site's argument, and `int` is not a helper,
        # so the selection is unambiguous and the ARGUMENT is what must be
        # refused: substituting it twice would call it twice.
        (WORK / "app/service.py").write_text(
            HELPER.replace('i["price_cents"]', 'int(rate)'), encoding="utf-8")
        before = (WORK / "app/service.py").read_text(encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            self.run_adapter(inline)
        self.assertIn("NOT_RE_EVALUABLE", str(caught.exception))
        self.assertEqual((WORK / "app/service.py").read_text(encoding="utf-8"), before)

    def test_an_ambiguous_tree_is_refused(self):
        (WORK / "app/service.py").write_text(
            HELPER + '''

def _other(price_cents, rate):
    return price_cents * rate


def second(items, rate):
    return sum(_other(i["price_cents"], rate) for i in items)
''', encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            self.run_adapter(inline)
        self.assertIn("AMBIGUOUS", str(caught.exception))


class TestTheSentenceReachesTheRepair(Base):
    files = {"app/__init__.py": "", "app/models.py": CONFLICTED,
             "tests/__init__.py": "", "tests/test_models.py": CONFLICT_TEST}

    def test_the_repair_sentences_are_software_engineering_requests(self):
        for goal in (
            "Resolve the merge conflict in <b>/app/models.py keeping both changes.",
            "Inline the single-use helper _price_with_tax in <b>/app/service.py into its only caller.",
        ):
            self.assertTrue(derivation.is_swe_request(goal), goal)

    def test_a_subject_file_states_its_directory(self):
        # The derivation is a GATE plus evidence, never a guess: one stated .py
        # file yields source_root = its directory, and nothing else.
        goal = f"Inline the single-use helper f in {WORK.relative_to(ROOT)}/app/m.py into its caller."
        (WORK / "app/m.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
        entry = {"action_template": {"args": {"source_root": "${input.source_root}"}}}
        derived = derivation.derive(goal, entry, ROOT)
        self.assertEqual(derived["source_root"]["rule"], "PATH_DIR_FROM_STATED_FILE_PARENT")

    def test_the_two_rows_are_registered_and_routable(self):
        from canonical.runtime import live_integrated_brain_v1 as live
        from canonical.runtime import goal_front_compiler_v1 as front
        registry = dict(live.load_verified_registry())
        routable = front.routable_registry(registry)
        for cid in ("python.vcs.merge_conflict.resolve.v1", "python.refactor.inline_helper.v1"):
            self.assertIn(cid, registry)
            self.assertIn(cid, routable)
            self.assertEqual(registry[cid]["status"], "VERIFIED_BOUND_CAPABILITY")

    def test_a_row_that_nothing_can_reach_is_not_shipped(self):
        # The SQL row was measured at the adapter level and withheld: the composer
        # claims the clause and turns "Remove the SQL injection" into `rm <db.py>`.
        from canonical.runtime import live_integrated_brain_v1 as live
        registry = dict(live.load_verified_registry())
        self.assertNotIn("python.repair.sql_injection.v1", registry)


if __name__ == "__main__":
    unittest.main()
