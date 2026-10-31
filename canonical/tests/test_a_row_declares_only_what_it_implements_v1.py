"""A row declares what its adapter implements, and a git read of a named revision is
a repository read.

Measured 2026-10-31 on main `bf4f78f`.

**1. A ROW WAS ACCUSED OF LYING AND THE ACCUSATION WAS WRONG.**

Three inventories (V16..V3) recorded `software.repair.choreograph.crossfile.v1` as declaring
four effects it does not implement. It implements all four, and the evidence was inside the
adapter the whole time:

    Pass C  deprecated stdlib/API codemod      -> dependency.deprecated.inspect.migrate
    Pass D  DB-API 2.0 parameterization (CWE-89)-> security.sql.injection.remove
    Pass E  shared-state concurrency RLock     -> software.concurrency.race.condition.fix
    Pass F  O(n^2) -> O(n) strength reduction  -> performance.quadratic.linearithmic.optimize

Deleting the declarations to "make the row honest" cost the surface census a REAL case:
`fix_race` (ten real runs, all passing, plus a real `Lock(` construct in the source) went
28/28 -> 27/28 immediately, and no matrix case was gained that survived re-measurement. The
declaration was the truth and the accusation was the defect. The fence below therefore pins
the row's declaration to exactly the passes its adapter names, so the next hand that deletes
one has to delete a pass first.

The same measurement killed a candidate law: "an effect's name must appear in its adapter"
passes on a row that lies, and fails on a row that is honest, because the vocabulary of an
adapter is prose as well as code. It is not shipped.

**2. A read of a named revision never reached the repository row.** ``Show me the diff of
<pkg>/calc.py against HEAD~1`` states the operation (``diff``), the object (the file) and the
revision -- and the row's ``OPS`` tuple already contained ``diff``. It compiled to nothing,
because the read-detection required the sentence to end at the object: paths are values and are
removed before the family check, leaving "show me the diff of against HEAD~1" and a failed
fullmatch. It was outscored by six ``diff_*_gate`` rows that only share the noun, and the
front door reported ``RAW_GOAL_COMPILATION_GAP``.

Independent oracle for both: the git binary itself (a repository with one commit and one
uncommitted change), and the row's own ``OPS``/``provides`` declarations.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_GUARD = ROOT / "execution_guard"
if str(_GUARD) not in sys.path:
    sys.path.insert(0, str(_GUARD))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import swe_typed_plan_v1 as typed_plan  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402
from swe_git_fixture_v1 import seed_repository  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_row_declares_what_it_implements"

CHOREOGRAPH = "software.repair.choreograph.crossfile.v1"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (base / "tests").mkdir()
    (base / "tests/test_calc.py").write_text(
        "import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n", encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


class ARowDeclaresOnlyWhatItImplementsTests(unittest.TestCase):
    # The adapter's own pass list, one entry per declared effect.  A declaration may be
    # deleted only together with the pass that implements it.
    PASSES = {
        "software.concurrency.race.condition.fix": "_try_concurrency_lock_synthesis",
        "security.sql.injection.remove": "_try_sql_parameterization",
        "performance.quadratic.linearithmic.optimize": "_try_quadratic_to_linear",
        "dependency.deprecated.inspect.migrate": "_try_deprecated_stdlib_codemod",
    }

    def test_every_declared_effect_names_the_pass_that_implements_it(self):
        """The four effects three inventories called false are implemented, by name."""
        row = dict(load_verified_registry())[CHOREOGRAPH]
        declared = set(row.get("provides") or [])
        source = (ROOT / "canonical/runtime/bound_capabilities/"
                        "software_repair_crossfile_choreograph_v1.py").read_text(encoding="utf-8")
        for effect, entry_point in self.PASSES.items():
            self.assertIn(effect, declared,
                          "a pass without its declaration is a capability nobody can reach")
            self.assertIn(entry_point, source,
                          "a declaration without its pass is the defect this pins")

    def test_the_race_fix_still_reaches_a_row_that_can_perform_it(self):
        """Deleting a true declaration cost the surface census a real case (28 -> 27)."""
        row = dict(load_verified_registry())[CHOREOGRAPH]
        self.assertIn("software.concurrency.race.condition.fix", set(row.get("provides") or []))

    def test_the_gate_refuses_the_race_question_by_name_rather_than_running_it(self):
        """A read-only race question is refused BY NAME, not run inside a writer.

        The row can still be the shortlisted candidate -- selection is a different layer -- but
        the answer gate must name the mismatch ("a read-only question answered by a writer")
        instead of letting the choreography run and fail with one opaque controller string.
        """
        base = _fresh("race")
        result = door.solve({"task_id": "RACE_BY_NAME",
                             "goal": f"Find the race condition in {_rel(base / 'pkg/calc.py')}."}) or {}
        self.assertFalse(result.get("pass"))
        self.assertNotIn("LIVE_CONTROLLER_EXECUTION",
                         str(result.get("failure_class") or ""))
        self.assertIn("STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER",
                      str(result.get("failure_class") or ""))


class AReadOfANamedRevisionIsARepositoryReadTests(unittest.TestCase):
    def test_the_family_fires_for_a_stated_revision(self):
        goal = "Show me the diff of pkg/calc.py against HEAD~1."
        self.assertEqual(typed_plan._family_terms(goal)[1], "git")

    def test_a_benchmark_is_not_a_repository_read(self):
        """The read opener is a closed list; a benchmark states no read of a revision.

        The sentence must contain no git TRIGGER word either, or the existing trigger list
        claims it first -- that is a separate, pre-existing rule and not what this pins.
        """
        family = typed_plan._family_terms("Benchmark pkg/calc.py against HEAD~1.")
        self.assertIsNotNone(family)
        self.assertEqual(family[1], "perf")

    def test_a_review_of_a_diff_stays_a_review(self):
        goal = "Review the diff of pkg/calc.py for security issues."
        self.assertIsNone(typed_plan._family_terms(goal))

    def test_the_door_shows_the_diff_against_the_revision(self):
        base = _fresh("diff")
        self.assertTrue(seed_repository(base))
        result = door.solve({"task_id": "SHOW_THE_DIFF",
                             "goal": f"Show me the diff of {_rel(base / 'pkg/calc.py')} against HEAD~1."}) or {}
        self.assertTrue(result.get("pass"), result.get("status"))
        self.assertEqual(str(result.get("compiled_capability_id") or ""), "git.repository.operate.v1")


if __name__ == "__main__":
    unittest.main()
