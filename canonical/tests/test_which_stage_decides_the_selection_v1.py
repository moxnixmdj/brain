#!/usr/bin/env python3
"""Which stage actually decides the selection, and what it is allowed to overturn.

WHY THIS FILE EXISTS

The benchmark reported 18 of 23 goals selected correctly.  Reading the ranker said
the ranker was right: on every miss the correct capability was ranked FIRST by
``_score`` -- ``xlsx.table.create_from_json_records`` 43 against 36,
``sqlite.table.verify_against_json_records`` 54 against 36,
``python.source.audit.ast`` 42 against 33.  The answer was being replaced after the
ranking, by two stages that had never been asked what they were allowed to overturn:

  * ``_bm25_rerank`` sorted by BM25 relevance FIRST and the pinned score second.  On
    "Audit the python source tree with an AST." that loses
    ``python.source.audit.ast`` (42, ``matched_head_verb: audit``) to
    ``code.multilanguage.parse.tree_sitter.v1`` (30) because "parse" and "tree" are
    the rarer words in the corpus.  Corpus statistics may order candidates; they
    must not overturn the one the pinned scorer recorded as DECLARING the goal's
    verb.
  * ``compile_goal`` compared the grounded plan with the producer-chained plan
    without asking whether the chained one could run at all.  On "Create an xlsx
    table from JSON records." the chained pass returned ``auto.pypi.msgpack`` at
    score 7 -- a serialization library -- still carrying a ``$effect_result`` that
    no capability could satisfy.  An unexecutable plan has no slot filled off the
    filesystem, so the guess-loses-to-the-sentence rule preferred it to the
    world-bound plan scoring 43.

Measured after both: 22 of 23 on the benchmark path, 21 of 23 through the front
door (it refuses the two it cannot bind), 33 -> 25 failures and 155 -> 176 passes
across the seven door/compiler suites with no new failure against the baseline.

The discriminator that keeps the second fix from becoming a new wrong-answer machine
is NOT a score margin.  ``match_evidence["matched_identity"]`` already records
whether a capability's own name contains a word of the sentence, and it separates the
two cases exactly: ``auto.pypi.msgpack`` matches no identity token at all on the xlsx
goal, while ``knowledge.consistency.assess`` matches ``assess`` and ``consistency`` on
the consistency goal and is the best answer available there.  These tests pin that
distinction, because it is the whole reason the fix is safe.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import (  # noqa: E402
    goal_compilation_benchmark_v1 as benchmark,
    goal_compiler,
    live_integrated_brain_v1 as live,
)

GOALS = {g["id"]: g for g in benchmark.BENCHMARK_GOALS + benchmark.EXTENDED_BENCHMARK_GOALS}


def selected(plan):
    """The benchmark's own rule: parts first, else the top-level pick."""
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


class TheRerankCannotOverturnTheActTests(unittest.TestCase):
    """BM25 orders candidates. It does not get to disagree with the act word."""

    @classmethod
    def setUpClass(cls):
        cls.verified = dict(live.load_verified_registry(include_extended=True))
        cls.admissible = goal_compiler._platform_admissible_registry(dict(cls.verified))

    def test_the_capability_that_declares_the_verb_is_first_after_the_rerank(self):
        goal = GOALS["EXT_AST_AUDIT"]["goal"]
        ranked = goal_compiler._rank_bindable_candidates(
            goal, self.admissible, REPO_ROOT, allow_world_binding=True)
        self.assertEqual(ranked[0][2], "python.source.audit.ast",
                         "a candidate whose own name does not contain the goal's verb "
                         "was promoted over the one that declares it")
        self.assertEqual((ranked[0][5] or {}).get("matched_head_verb"), "audit")

    def test_that_capability_does_not_win_on_the_pinned_score_alone(self):
        """Negative control: the rerank is still doing work, not just deferring.

        ``code.multilanguage.parse.tree_sitter.v1`` scores 30 against 42, yet it is
        the only one of the two that BM25 prefers -- so if the ordering came out
        right by accident the score comparison would have to explain it, and it
        cannot.
        """
        goal = GOALS["EXT_AST_AUDIT"]["goal"]
        ranked = goal_compiler._rank_bindable_candidates(
            goal, self.admissible, REPO_ROOT, allow_world_binding=True)
        scores = {item[2]: item[0] for item in ranked}
        module = goal_compiler._bm25_module()
        docs = [goal_compiler._capability_document(item[2], item[3]) for item in ranked]
        relevance = {item[2]: rel for item, (rel, _c) in
                     zip(ranked, module._bm25_scores(goal_compiler._bm25_terms(goal), docs))}
        self.assertGreater(scores["python.source.audit.ast"],
                           scores["code.multilanguage.parse.tree_sitter.v1"])
        self.assertGreater(relevance["code.multilanguage.parse.tree_sitter.v1"],
                           relevance["python.source.audit.ast"],
                           "BM25 no longer prefers the parser, so this pin is measuring "
                           "nothing and should be re-derived")

    def test_bm25_still_decides_where_no_candidate_declares_the_verb(self):
        """The reason the rerank is kept: the barcode case is unchanged.

        ``image.code.decode.zbarimg`` out-scores ``image.qr.generate.qrencode`` 22 to
        21 on "Generate a QR code image..." and declares no head verb there, so
        relevance still has to be what separates them.
        """
        plan = goal_compiler.compile_goal(
            GOALS["EXT_QR_GENERATE"]["goal"], self.verified, str(REPO_ROOT))
        self.assertEqual(selected(plan), ["image.qr.generate.qrencode"])


class AnUnexecutablePlanIsNotAnAnswerTests(unittest.TestCase):
    """A dangling producer reference is a plan's missing half, not a plan."""

    @classmethod
    def setUpClass(cls):
        cls.verified = dict(live.load_verified_registry(include_extended=True))
        cls.admissible = goal_compiler._platform_admissible_registry(dict(cls.verified))
        cls.binder = goal_compiler._load_sibling_runtime_module(
            "capability_proposal_generators.py",
            "project_brain_direct_compiler_proposal_binder")
        cls.providers = goal_compiler._effect_providers(dict(cls.verified))

    def _chained(self, goal):
        return goal_compiler._compile_single_goal(
            goal, self.verified, str(REPO_ROOT),
            proposal_binder=self.binder,
            effect_providers=self.providers,
            attach_producer_steps=True,
        )

    def test_a_chain_nothing_can_produce_is_left_with_a_dangling_reference(self):
        """The precondition the fix reads. Attaching refuses rather than pretends."""
        plan = self._chained(GOALS["EXT_XLSX_CREATE"]["goal"])
        self.assertTrue(goal_compiler._plan_has_dangling_effect_refs(plan))
        self.assertEqual(goal_compiler._collect_effect_result_refs(plan.get("inputs"))[0]["effect"],
                         "json.file.available")

    def test_a_nameless_security_plan_does_not_beat_the_capability_the_sentence_names(self):
        plan = goal_compiler.compile_goal(
            GOALS["EXT_XLSX_CREATE"]["goal"], self.verified, str(REPO_ROOT))
        self.assertEqual(selected(plan), ["xlsx.table.create_from_json_records"],
                         "a serialization library answered a spreadsheet question again")

    def test_the_same_shape_on_a_database_question_is_answered_by_the_database(self):
        plan = goal_compiler.compile_goal(
            GOALS["EXT_SQLITE_VERIFY"]["goal"], self.verified, str(REPO_ROOT))
        self.assertEqual(selected(plan), ["sqlite.table.verify_against_json_records"])

    def test_a_named_capability_keeps_the_incomplete_plan_that_names_it(self):
        """The other half of the rule, measured on the goal it protects.

        ``knowledge.consistency.assess`` is also one producer step short, but its own
        name carries the sentence's verb and object, so replacing it with a
        filesystem-guessed docx writer solves nothing and answers the wrong question.
        """
        goal = GOALS["BENCH_JSON_FETCH_CONSISTENCY"]["goal"]
        chained = self._chained(goal)
        self.assertTrue(goal_compiler._plan_has_dangling_effect_refs(chained))
        self.assertTrue(goal_compiler._plan_terminal_names_the_sentence(chained))
        self.assertEqual(selected(goal_compiler.compile_goal(goal, self.verified, str(REPO_ROOT))),
                         ["knowledge.consistency.assess"])

    def test_the_predicate_reads_recorded_evidence_and_invents_nothing(self):
        self.assertFalse(goal_compiler._plan_terminal_names_the_sentence({}))
        self.assertFalse(goal_compiler._plan_terminal_names_the_sentence(
            {"match_evidence": {}}))
        self.assertTrue(goal_compiler._plan_terminal_names_the_sentence(
            {"match_evidence": {"matched_identity": ["audit"]}}))
        self.assertFalse(goal_compiler._plan_has_dangling_effect_refs(
            {"inputs": {"json_path": "a/real/file.json"}}))


class TheMeasuredRateTests(unittest.TestCase):
    """The two numbers a change has to move deliberately, measured not asserted."""

    def test_the_benchmark_path_selects_the_expected_capability_for_22_of_23(self):
        registry = dict(live.load_verified_registry(include_extended=True))
        correct = 0
        missed = []
        for gid, spec in GOALS.items():
            try:
                got = selected(goal_compiler.compile_goal(spec["goal"], registry, str(REPO_ROOT)))
            except Exception:
                got = []
            if spec["expected"][0] in got:
                correct += 1
            else:
                missed.append(gid)
        self.assertEqual(correct, 22, f"missed:{sorted(missed)}")
        self.assertEqual(sorted(missed), ["EXT_JQ_TABLE"],
                         "the only goal left is the one whose sentence states no jq_filter")


if __name__ == "__main__":
    unittest.main()
