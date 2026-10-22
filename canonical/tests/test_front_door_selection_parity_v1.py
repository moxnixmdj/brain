"""The front door's selection is measured, and the two compilers now agree.

WHY THIS FILE EXISTS

``goal_compilation_benchmark_v1`` reports a correct-selection rate.  It measures
``goal_compiler.compile_goal`` over ``live_integrated_brain_v1.load_verified_registry()``.
The live front door does not make that call: ``run_raw_goal`` goes through
``compile_against_live_registry``, which selects with
``goal_front_compiler_v1.compile_goal`` over the platform-admissible projection.
Two call sites, one reported number -- so the rate in the benchmark describes a
configuration the shipping path does not use, and nothing measured the one that runs.

WHAT WAS MEASURED, AND WHAT WAS WRONG THE FIRST TIME

The first version of this file reported front-door selection as 15 of 19 and blamed a
disagreement between the two compiler MODULES.  Both claims were wrong and both are
corrected here rather than left standing:

  * 15 of 19 came from reading only ``plan["selected_capability"]``.  The benchmark's
    own rule reads ``compiled_parts`` first and falls back to the top-level pick, so a
    compound plan scored as "no selection".  Measured with the benchmark's own rule the
    number was 20 of 23, not 15 of 19.
  * The two compiler modules do not disagree.  Given the same registry and the same
    root, ``goal_compiler.compile_goal`` and ``goal_front_compiler_v1.compile_goal``
    return the same capability for all 23 goals.  The difference was the REGISTRY VIEW:
    the front compiler ranks over ``routable_registry(admissible)``, which deletes the
    capabilities that take no input, and the benchmark ranks over the full verified
    registry.

THE ACTUAL DEFECT, MEASURED

Deleting a zero-input capability from the RANKING does more than refuse it -- it
changes what the pinned compiler can bind at all.  For
"Fetch a JSON document and assess its internal consistency.":

  * over the routable projection the grounded pass returns NOTHING, so
    ``_compile_single_goal`` falls through to WORLD binding and returns
    ``docx.document.create_from_json_record`` at score 25 with ``json_path`` inferred
    to canonical/CANONICAL_POINTER.json -- a file the sentence never mentioned.  That
    plan then fails at execution with JSON_DOCX_SPEC_UNRESOLVED, because the spec that
    producer needs was never stated.
  * with ``terminal.kstar.root.assess.stdlib`` present the grounded pass is non-empty,
    the world fallback never runs, and the chained pass's ``knowledge.consistency.assess``
    (score 8, every slot bound from the sentence) wins.  Removing that one entry from
    the registry flipped the answer, and adding it back flipped it again -- which is
    what made the mechanism load-bearing rather than a story.

That last fragility has since been removed rather than merely pinned.  A second fix,
in ``goal_compiler.compile_goal``, makes a plan that filled a slot by scanning the
filesystem lose to a plan whose slots the sentence accounted for.  Measured over all
three registry views the answer is now the same and is grounded, so the selection no
longer depends on a weak competitor staying in the ranking.  Both fixes are kept: the
widened ranking separates "may compete" from "may decide", and the preference makes
the right answer independent of what competes.

The fix therefore keeps the full admissible view as the thing that is RANKED and bound
against, while the routable projection remains the only pool a DECISION may come from.
``_is_catch_all``'s own docstring already states the principle -- "it can never be the
DECISION" -- and F17 still displaces a catch-all the pinned scorer returned, so nothing
F4 was protecting became selectable.

MEASURED RESULT

  canonical (benchmark path)  22 of 23   was 21
  front door (shipping path)  22 of 23   was 20
  divergences between them    0          was 1

The one remaining miss is shared by both paths and is pinned with its wrong answer,
so a fix that moves it has to say so.

Every number here is a measurement, not an assertion: each test compiles the real goals
through the real entry points.  Perturbing any pin turns it red -- that was verified by
changing the pinned rate and the pinned mechanism and watching both fail.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import (  # noqa: E402
    goal_compiler,
    goal_compilation_benchmark_v1 as benchmark,
    goal_front_compiler_v1 as front,
    live_integrated_brain_v1 as live,
)

GOALS = benchmark.BENCHMARK_GOALS + benchmark.EXTENDED_BENCHMARK_GOALS

# The goal whose selection this file exists to keep correct.
FIXED_GOAL = "BENCH_JSON_FETCH_CONSISTENCY"
EXPECTED_FOR_FIXED = "knowledge.consistency.assess"
THE_WRONG_PICK = "docx.document.create_from_json_record"

# The zero-input capability whose presence in the RANKING keeps the grounded pass
# non-empty.  It is never the decision; it is only ever a competitor.
LOAD_BEARING_COMPETITOR = "terminal.kstar.root.assess.stdlib"

# Measured, with the benchmark's own selection rule (parts first, else the top pick).
KNOWN_FRONT_DOOR_CORRECT = 22
KNOWN_CANONICAL_CORRECT = 22
KNOWN_DIVERGENCES: set = set()
KNOWN_SHARED_MISSES = {
    "EXT_JQ_TABLE": "document.convert.markdown_pdf.pandoc_weasyprint",
}


def selected(plan) -> list:
    """The benchmark's own selection rule, copied rather than re-invented.

    A compound plan has no top-level ``selected_capability``; its parts are the
    selection.  Reading only the top level scored every compound plan as "no
    selection", which is how this file's first version produced 15 of 19.
    """
    if not isinstance(plan, dict):
        return []
    parts = [str((p or {}).get("selected_capability"))
             for p in (plan.get("compiled_parts") or [])
             if isinstance(p, dict) and (p or {}).get("selected_capability")]
    if parts:
        return parts
    if plan.get("selected_capability"):
        return [str(plan["selected_capability"])]
    return []


class RegistryViews(unittest.TestCase):
    """Both registry views the two call sites actually use, built once."""

    @classmethod
    def setUpClass(cls):
        cls.verified = dict(live.load_verified_registry(include_extended=True))
        cls.admissible = goal_compiler._platform_admissible_registry(dict(cls.verified))
        cls.routable = front.routable_registry(cls.admissible)

    def test_the_benchmark_covers_every_goal_it_claims_to(self):
        self.assertEqual(len(GOALS), 23, "the benchmark's goal list moved; re-measure")

    def test_the_routable_projection_really_does_delete_zero_input_tools(self):
        self.assertLess(len(self.routable), len(self.admissible),
                        "if the projection no longer deletes anything, the F4 rule and "
                        "this file's premise have both changed")
        self.assertNotIn(LOAD_BEARING_COMPETITOR, self.routable)
        self.assertIn(LOAD_BEARING_COMPETITOR, self.admissible)

    def test_both_candidates_exist_in_both_views(self):
        """The defect was never a missing capability."""
        for view in (self.routable, self.admissible, self.verified):
            for cid in (EXPECTED_FOR_FIXED, THE_WRONG_PICK):
                self.assertIn(cid, view)


class FrontDoorAndCanonicalNowAgreeTests(RegistryViews):
    """The two shipping paths are measured against each other, goal by goal."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = {}
        for g in GOALS:
            want = g["expected"][0]
            try:
                canon = selected(goal_compiler.compile_goal(g["goal"], cls.verified, str(REPO_ROOT)))
            except Exception:
                canon = []
            try:
                door = selected(front.compile_goal(g["goal"], cls.admissible, REPO_ROOT))
            except Exception:
                door = []
            cls.rows[g["id"]] = (want, canon, door)

    def test_the_front_door_selection_rate_is_pinned(self):
        got = sum(1 for want, _, door in self.rows.values() if want in door)
        self.assertEqual(
            got, KNOWN_FRONT_DOOR_CORRECT,
            "front-door selection moved -- update KNOWN_FRONT_DOOR_CORRECT and say "
            "which way it moved and why",
        )

    def test_the_canonical_selection_rate_is_pinned(self):
        got = sum(1 for want, canon, _ in self.rows.values() if want in canon)
        self.assertEqual(got, KNOWN_CANONICAL_CORRECT)

    def test_the_two_paths_agree_on_every_goal(self):
        """Zero divergence. This is the claim the first version of this file got wrong."""
        divergent = {gid for gid, (_, c, d) in self.rows.items() if c != d}
        self.assertEqual(
            divergent, KNOWN_DIVERGENCES,
            "the two shipping paths disagree again -- a compiled artifact and the path "
            "that runs it must not select differently",
        )

    def test_the_goal_this_file_exists_for_is_selected_correctly(self):
        want, canon, door = self.rows[FIXED_GOAL]
        self.assertEqual(want, EXPECTED_FOR_FIXED)
        self.assertIn(EXPECTED_FOR_FIXED, canon)
        self.assertIn(EXPECTED_FOR_FIXED, door,
                      "the front door is back on the docx writer")
        self.assertNotIn(THE_WRONG_PICK, door)

    def test_every_remaining_miss_is_pinned_with_its_wrong_answer(self):
        misses = {gid: (door[0] if door else None)
                  for gid, (want, _, door) in self.rows.items() if want not in door}
        self.assertEqual(
            misses, KNOWN_SHARED_MISSES,
            "the miss set changed -- update KNOWN_SHARED_MISSES with the new wrong "
            "answers, or the new correct ones",
        )

    def test_the_remaining_misses_are_missed_by_both_paths(self):
        """So they are a real gap in the compiler, not a front-door artefact."""
        for gid in KNOWN_SHARED_MISSES:
            want, canon, door = self.rows[gid]
            self.assertNotIn(want, canon, gid)
            self.assertNotIn(want, door, gid)


class TheMechanismIsLoadBearingTests(RegistryViews):
    """Pin WHY the answer holds, so the fix cannot be undone by accident.

    This class used to pin a FRAGILITY: the correct answer depended on one weak
    zero-input capability staying in the ranking, and deleting
    `terminal.kstar.root.assess.stdlib` flipped the selection to the docx writer.
    That was a real measurement and it drove the fix that widened the ranking.

    It no longer holds, and the reason is a better fix rather than a lost one.
    The unjustified-world-slot preference in `goal_compiler.compile_goal` now
    catches the same case one level down: the docx writer's `json_path` is filled
    by picking a file off the filesystem, so it loses to a plan every one of
    whose slots the sentence accounted for -- whatever the ranking contains.
    Measured over all three registry views, the answer is now the same and is
    grounded, so the selection no longer depends on a weak competitor being
    present. That is pinned here in place of the old fragility.
    """

    GOAL = next(g["goal"] for g in GOALS if g["id"] == FIXED_GOAL)

    def _pinned_over(self, registry):
        try:
            return selected(goal_compiler.compile_goal(self.GOAL, registry, REPO_ROOT))
        except Exception:
            return []

    def test_the_answer_holds_over_every_registry_view(self):
        """Stronger than the pin this replaces: no view, no competitor, same answer."""
        without = {k: v for k, v in self.admissible.items() if k != LOAD_BEARING_COMPETITOR}
        for label, view in (("routable", self.routable),
                            ("admissible", self.admissible),
                            ("admissible-minus-competitor", without)):
            self.assertIn(EXPECTED_FOR_FIXED, self._pinned_over(view), label)
            self.assertNotIn(THE_WRONG_PICK, self._pinned_over(view), label)

    def test_the_answer_is_grounded_over_every_registry_view(self):
        """Not merely correct -- bound from the sentence, never from the filesystem."""
        without = {k: v for k, v in self.admissible.items() if k != LOAD_BEARING_COMPETITOR}
        for label, view in (("routable", self.routable),
                            ("admissible", self.admissible),
                            ("admissible-minus-competitor", without)):
            plan = goal_compiler.compile_goal(self.GOAL, view, REPO_ROOT)
            self.assertEqual(plan["binding_source"], "GOAL_STATEMENT", label)
            self.assertFalse(
                goal_compiler._plan_has_unjustified_world_slots(plan),
                f"{label}: a slot was filled off the filesystem again",
            )

    def test_the_wrong_pick_would_need_a_file_the_sentence_never_stated(self):
        """Why the old wrong answer was wrong, kept as a measurement of the slot.

        The docx writer is still in the registry and still scores 25 on this
        sentence -- higher than the correct capability's 8.  What changed is that
        its `json_path` can now only be filled by picking a file the sentence
        never named, and a plan built on that guess no longer wins.
        """
        score, _spec, evidence = goal_compiler._score(self.GOAL, THE_WRONG_PICK,
                                                      self.admissible[THE_WRONG_PICK])
        self.assertGreater(score, 0, "the wrong pick is no longer even a candidate")
        self.assertTrue(evidence["matched_identity"], "it still matches the sentence's nouns")
        self.assertIn("json_path", goal_compiler._placeholders(
            (self.admissible[THE_WRONG_PICK].get("action_template") or {})))

    def test_the_right_pick_is_bound_from_the_sentence_not_the_world(self):
        plan = goal_compiler.compile_goal(self.GOAL, self.admissible, REPO_ROOT)
        self.assertEqual(plan["selected_capability"], EXPECTED_FOR_FIXED)
        self.assertEqual(plan["binding_source"], "GOAL_STATEMENT")


class AZeroInputToolCanNeverBeTheDecisionTests(RegistryViews):
    """The safety property F4 exists for, re-asserted against the widened ranking.

    The predicate is ``blocked_zero_input_capabilities`` -- the exact set
    ``routable_registry`` deletes -- and deliberately NOT ``_is_catch_all``.  Those
    two are not the same thing, and measuring the difference matters: ``_is_catch_all``
    also rejects capabilities whose only inputs are the whole request or an output
    path, and three of the benchmark's OWN correct answers
    (``plain_goal.bound_capability.grounding.stdlib``,
    ``source.candidates.enumerate.stdlib``,
    ``structured.decision_evidence.locate.stdlib``) are catch-alls in that broader
    sense.  Asserting the broad predicate here failed on a clean tree, which is what
    pinned the narrow one instead of an assumption about it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.blocked = set(front.blocked_zero_input_capabilities(cls.admissible))
        cls.selections = {}
        for g in GOALS:
            try:
                cls.selections[g["id"]] = selected(front.compile_goal(g["goal"], cls.admissible, REPO_ROOT))
            except Exception:
                cls.selections[g["id"]] = []

    def test_the_blocked_set_is_the_one_the_projection_deletes(self):
        self.assertTrue(self.blocked)
        self.assertEqual(set(self.admissible) - self.blocked, set(self.routable))

    def test_no_front_door_selection_is_a_capability_the_projection_deleted(self):
        caught = sorted((gid, cid) for gid, cids in self.selections.items()
                        for cid in cids if cid in self.blocked)
        self.assertEqual(
            caught, [],
            "a zero-input tool became a decision -- the widened ranking leaked into "
            "the decision pool, which is the one thing F4 exists to prevent",
        )

    def test_the_competitor_still_cannot_be_selected_by_the_front_door(self):
        """It may compete; it may never decide. Both halves are pinned."""
        self.assertIn(LOAD_BEARING_COMPETITOR, self.admissible)
        for g in GOALS:
            try:
                plan = front.compile_goal(g["goal"], self.admissible, REPO_ROOT)
            except Exception:
                continue
            self.assertNotIn(LOAD_BEARING_COMPETITOR, selected(plan),
                             f"{g['id']} selected a zero-input tool")


if __name__ == "__main__":
    unittest.main()
