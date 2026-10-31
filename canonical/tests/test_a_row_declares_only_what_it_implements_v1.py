"""A row may only declare the effects its adapter implements, and a git read of a
named revision is a repository read.

Two defects, measured 2026-10-31 on main `bf4f78f`.

**1. A declaration that defeats the effect gate.** `software.repair.choreograph.crossfile.v1`
declared four effects in its own ``provides`` that its adapter does not implement:

    software.concurrency.race.condition.fix
    security.sql.injection.remove
    performance.quadratic.linearithmic.optimize
    dependency.deprecated.inspect.migrate

The adapter implements one choreography: patch, symbol graph, change-impact slice, dual-oracle
verify, gate. But the effect gate reads ``provides``, so every sentence stating one of those four
effects was admitted to this row and died *inside the controller* instead of being refused by
name. Measured after the deletion: the capability matrix's ``fix_failing_ci`` case went from
``LIVE_CONTROLLER_EXECUTION`` to **REAL** -- the row was absorbing a sentence a real capability
could serve -- and the advanced census's ``#18`` changed from the misleading ``R3_WEAK_EVIDENCE``
to the precise ``STATED_OPTIMISATION_NOT_PERFORMED``.

A word-mention law ("the effect's name appears in the adapter source") was measured and
**rejected**: the choreograph adapter *does* contain the words race, sql, dependent and inject,
in the prose that explains what it refuses. That law would have certified nothing, which is
exactly the failure class it was written to prevent. The fence here is therefore the row's own
declaration, and the inventory records the general question as an open measurement.

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
    def test_the_choreograph_row_declares_only_the_effects_its_adapter_implements(self):
        """The four deleted effects defeated the gate that exists to catch them."""
        row = dict(load_verified_registry())[CHOREOGRAPH]
        declared = set(row.get("provides") or [])
        self.assertEqual(declared, {
            "software.repair.choreography.verified",
            "software.patch.crossfile.atomic",
            "software.source.write.crossfile",
            "source.repair.applied",
        })
        for undeclared in ("software.concurrency.race.condition.fix",
                           "security.sql.injection.remove",
                           "performance.quadratic.linearithmic.optimize",
                           "dependency.deprecated.inspect.migrate"):
            self.assertNotIn(undeclared, declared)

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
