"""The benchmark must measure the compiler the product actually runs.

`goal_compilation_benchmark_v1` scores selection with `goal_compiler.compile_goal`.
The live front door does not use that function: `live_integrated_brain_v1.run_raw_goal`
calls `compile_against_live_registry`, which selects through
`goal_front_compiler_v1.compile_goal`. Two compilers, one reported number.

Measured on all 23 benchmark goals, the two disagree on exactly one:

    goal      "Fetch a JSON document and assess its internal consistency."
    expected  knowledge.consistency.assess
    canonical knowledge.consistency.assess                 (score 8)
    front     docx.document.create_from_json_record        (score 25)

The front-door pick wins on raw lexical score because it matches two INPUT nouns --
"json" and "document" -- while the capability the sentence actually asks for matches
the sentence's ACTION words, "assess" and "consistency". It then fails at execution
with `JSON_DOCX_SPEC_UNRESOLVED`, because the spec the docx producer needs was never
stated.

So the reported correct-selection rate describes a compiler the shipping path does not
use, and one goal's error is invisible in it.

Diagnosed and deliberately NOT papered over here:

  * The registry is not the cause. Both capabilities are present in the plain 72-entry
    registry and in the 365-entry extended/admissible one, and each compiler gives the
    same answer under either registry. The divergence is entirely in the compiler
    module.
  * The front compiler already owns a bind-first-then-rank reconciliation (rules F1,
    F22, F24) that is exactly the right shape of fix, but on this goal
    `rules_applied` is only `F2_SENTENCE_FINAL_PERIOD_REMOVED` and
    `F4_ZERO_INPUT_TOOLS_NOT_ROUTABLE` -- the reconciliation never fires.
  * Preferring the canonical pick would NOT fix it either. Measured: `bind_all_inputs`
    raises `GOAL_INPUT_BINDING_REQUIRED` for BOTH candidates
    (`json_path:0_type_compatible_existing_files_named` and
    `evidence_paths:no_matching_existing_files_named`), so neither survives a
    bindability filter and the walk falls through to the lexical winner regardless.
    The real repair has to make "the producer needs a spec the sentence never stated"
    count as unstated, which is a change to binding, not to ordering.

What this suite does instead is make the gap impossible to lose sight of. It measures
the FRONT-DOOR selection rate directly, pins it, and names the divergent goal. Anyone
who repairs the selection has to update the pinned set -- the ratchet only turns one
way, and it turns visibly.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import availability_v1  # noqa: E402
from canonical.runtime import goal_compilation_benchmark_v1 as benchmark  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

GOALS = benchmark.BENCHMARK_GOALS + benchmark.EXTENDED_BENCHMARK_GOALS

# Goals whose expected chain is a single capability, so a selection can be compared.
# Compound goals report selected_capability None on both compilers by design.
SINGLE_CAPABILITY_GOALS = {
    "BENCH_PDF_EXTRACT_TEXT",
    "BENCH_SOURCE_AUDIT_WRITE_JSON",
    "BENCH_JSON_FETCH_CONSISTENCY",
    "BENCH_UNITTEST_PASS_RATE",
    "BENCH_MARKDOWN_TO_DECISION",
    "EXT_QR_GENERATE",
    "EXT_BARCODE_DECODE",
    "EXT_OCR_SCANNED_IMAGE",
    "EXT_TAR_VERIFY",
    "EXT_XLSX_CREATE",
    "EXT_DOCX_VERIFY",
    "EXT_EVIDENCE_RANK",
    "EXT_CLAIM_BIND",
    "EXT_KNOWLEDGE_CONSISTENCY",
    "EXT_JQ_TABLE",
    "EXT_AST_AUDIT",
    "EXT_SQLITE_VERIFY",
    "EXT_DECISION_VERIFY",
    "EXT_MD_TO_PDF",
}

# The measured divergence set. Repairing the selection must shrink this, and the test
# fails if it silently grows or if an entry changes without the docstring being updated.
KNOWN_FRONT_DOOR_DIVERGENCE = {"BENCH_JSON_FETCH_CONSISTENCY"}

# The measured front-door selection rate over the single-capability goals.
# Measured: 15 of the 19 single-capability goals select correctly through the front
# door. The four that do not, and why each is different:
#   BENCH_JSON_FETCH_CONSISTENCY  the divergence -- canonical is right, front is wrong
#   BENCH_MARKDOWN_TO_DECISION    BOTH compilers pick the pandoc converter
#   EXT_JQ_TABLE                  BOTH compilers pick the pandoc converter
#   BENCH_PDF_EXTRACT_TEXT        front returns None: it plans a DAG, not one capability
KNOWN_FRONT_DOOR_CORRECT = 15

# Every goal the front door gets wrong, pinned with its wrong answer, so a repair has
# to be explicit about which one it fixed.
KNOWN_FRONT_DOOR_WRONG = {
    "BENCH_JSON_FETCH_CONSISTENCY": "docx.document.create_from_json_record",
    "BENCH_MARKDOWN_TO_DECISION": "document.convert.markdown_pdf.pandoc_weasyprint",
    "EXT_JQ_TABLE": "document.convert.markdown_pdf.pandoc_weasyprint",
    "BENCH_PDF_EXTRACT_TEXT": None,
}


class FrontDoorSelectionIsMeasuredTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = availability_v1.load_registry()
        cls.rows = {}
        for goal in GOALS:
            gid = goal["id"]
            expected = (goal.get("expected") or [None])[0]
            try:
                canonical = goal_compiler.compile_goal(
                    goal["goal"], cls.registry, str(REPO_ROOT)
                ).get("selected_capability")
            except Exception as exc:  # a compile failure is data, not a crash
                canonical = "EXCEPTION:" + type(exc).__name__
            try:
                _reg, _adm, compiled = live.compile_against_live_registry(goal["goal"])
                frontdoor = compiled.get("selected_capability")
            except Exception as exc:
                frontdoor = "EXCEPTION:" + type(exc).__name__
            cls.rows[gid] = {
                "goal": goal["goal"],
                "expected": expected,
                "canonical": canonical,
                "front_door": frontdoor,
            }

    def test_the_benchmark_covers_every_goal_it_claims_to(self):
        self.assertEqual(len(GOALS), 23)

    def test_the_two_compilers_agree_on_every_goal_except_the_pinned_one(self):
        divergent = {
            gid for gid, row in self.rows.items()
            if row["canonical"] != row["front_door"]
        }
        self.assertEqual(
            divergent, KNOWN_FRONT_DOOR_DIVERGENCE,
            "the divergence set changed -- update the docstring and the pinned rate, "
            "and say which way it moved",
        )

    def test_the_divergent_goal_is_the_one_the_docstring_names(self):
        row = self.rows["BENCH_JSON_FETCH_CONSISTENCY"]
        self.assertEqual(row["expected"], "knowledge.consistency.assess")
        self.assertEqual(row["canonical"], "knowledge.consistency.assess")
        self.assertEqual(row["front_door"], "docx.document.create_from_json_record")

    def test_the_front_door_selection_rate_is_pinned(self):
        """The number that describes the shipping path, measured not asserted."""
        correct = sum(
            1 for gid in SINGLE_CAPABILITY_GOALS
            if self.rows[gid]["front_door"] == self.rows[gid]["expected"]
        )
        self.assertEqual(
            correct, KNOWN_FRONT_DOOR_CORRECT,
            f"front-door selection moved to {correct}/"
            f"{len(SINGLE_CAPABILITY_GOALS)} -- update the pin and say which way",
        )

    def test_every_front_door_miss_is_pinned_with_its_wrong_answer(self):
        wrong = {
            gid: self.rows[gid]["front_door"]
            for gid in SINGLE_CAPABILITY_GOALS
            if self.rows[gid]["front_door"] != self.rows[gid]["expected"]
        }
        self.assertEqual(
            wrong, KNOWN_FRONT_DOOR_WRONG,
            "the front-door miss set changed -- update the pin and say which way it moved",
        )

    def test_only_one_miss_is_a_divergence_the_others_are_shared(self):
        """Three of the four misses are not this suite's subject: both compilers agree
        on them. Only the divergent one is a front-door-specific defect."""
        shared = {
            gid for gid in KNOWN_FRONT_DOOR_WRONG
            if self.rows[gid]["canonical"] == self.rows[gid]["front_door"]
        }
        self.assertEqual(
            shared,
            set(KNOWN_FRONT_DOOR_WRONG) - KNOWN_FRONT_DOOR_DIVERGENCE,
        )

    def test_the_canonical_compiler_is_not_the_one_that_is_wrong(self):
        """Guard the direction of the repair: the canonical pick is the correct one."""
        row = self.rows["BENCH_JSON_FETCH_CONSISTENCY"]
        self.assertEqual(row["canonical"], row["expected"])
        self.assertNotEqual(row["front_door"], row["expected"])


class DivergenceIsNotTheRegistryTests(unittest.TestCase):
    """The cause is the compiler module, and that must stay measured."""

    GOAL = "Fetch a JSON document and assess its internal consistency."

    def test_both_candidates_exist_in_both_registries(self):
        plain = availability_v1.load_registry()
        extended = live.load_verified_registry(include_extended=True)
        for cid in ("knowledge.consistency.assess",
                    "docx.document.create_from_json_record"):
            self.assertIn(cid, plain)
            self.assertIn(cid, extended)

    def test_the_canonical_compiler_gives_the_same_answer_under_either_registry(self):
        plain = availability_v1.load_registry()
        extended = live.load_verified_registry(include_extended=True)
        admissible = goal_compiler._platform_admissible_registry(dict(extended))
        for label, reg in (("plain", plain), ("admissible-extended", admissible)):
            with self.subTest(registry=label):
                self.assertEqual(
                    goal_compiler.compile_goal(
                        self.GOAL, reg, str(REPO_ROOT)
                    ).get("selected_capability"),
                    "knowledge.consistency.assess",
                )

    def test_the_front_compiler_gives_the_same_wrong_answer_under_either_registry(self):
        plain = availability_v1.load_registry()
        extended = live.load_verified_registry(include_extended=True)
        admissible = goal_compiler._platform_admissible_registry(dict(extended))
        for label, reg in (("plain", plain), ("admissible-extended", admissible)):
            with self.subTest(registry=label):
                self.assertEqual(
                    front.compile_goal(self.GOAL, reg, REPO_ROOT).get(
                        "selected_capability"),
                    "docx.document.create_from_json_record",
                )


class NeitherCandidateBindsSoOrderingAloneCannotFixItTests(unittest.TestCase):
    """Pins why the obvious one-line repair does not work.

    If this ever starts passing, bind-first-then-rank becomes a live fix and the
    docstring's diagnosis is stale -- which is exactly when someone should look again.
    """

    GOAL = "Fetch a JSON document and assess its internal consistency."

    def _binds(self, cid):
        registry = front.routable_registry(
            goal_compiler._platform_admissible_registry(
                dict(live.load_verified_registry(include_extended=True))
            )
        )
        try:
            front.bind_all_inputs(
                self.GOAL, registry[cid], REPO_ROOT, cycle=0, spool=set()
            )
            return True
        except Exception:
            return False

    def test_neither_candidate_survives_a_bindability_filter(self):
        self.assertFalse(self._binds("knowledge.consistency.assess"))
        self.assertFalse(self._binds("docx.document.create_from_json_record"))


class TheLoserFailsAtExecutionNotAtCompileTests(unittest.TestCase):
    """The wrong pick is not harmless: it fails later, with a cause nobody could see
    before the reason survived to the blocker."""

    def test_the_front_door_pick_is_the_one_that_fails_at_runtime(self):
        import uuid
        result = live.run_raw_goal({
            "task_id": f"DIVERGE_{uuid.uuid4().hex[:8]}",
            "goal": "Fetch a JSON document and assess its internal consistency.",
        })
        self.assertFalse(result.get("pass"))
        self.assertEqual(
            result.get("compiled_capability_id"),
            "docx.document.create_from_json_record",
        )
        self.assertIn("JSON_DOCX_SPEC_UNRESOLVED", str(result.get("reason") or ""))


if __name__ == "__main__":
    unittest.main()
