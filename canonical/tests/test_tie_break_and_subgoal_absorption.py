"""Two refusal sites that refused goals the machine could in fact carry out.

Both were measured, not theorised:

1. ``Read a PDF and extract its text.`` split into ``Read a PDF`` / ``extract
   its text``. The first clause tied ``pdf.extract.text.pypdf`` against
   ``pdf.extract.ocr.tesseract`` at score 10 and the compiler refused. The
   words that decide between them -- "extract its **text**" -- were in the part
   of the sentence the split carved away; scored against the whole sentence the
   two separate at 24 and 17.

2. Having resolved that, the goal then refused on clause 2, ``extract its
   text``, which matches no capability at all -- because one action had been
   described twice and the prefix already compiled it.

These tests pin both, and pin that neither widens into guessing.
"""

import pathlib
import unittest

REPO_ROOT=pathlib.Path(__file__).resolve().parents[2]

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402


def _registry():
    import json
    path=REPO_ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
    return json.loads(path.read_text(encoding="utf-8"))["capabilities"]


def _ambiguous_pair_registry():
    """Two capabilities no evidence can tell apart -- the honest refusal case.

    Deliberately symmetric: same keywords, same single placeholder, no
    ``verification`` record and no declared discovery mechanism, so neither
    the goal, the world, a receipt, nor a platform default can separate them.
    Built synthetically rather than borrowed from a live goal so the negative
    control cannot be quietly invalidated by a future registry change.
    """
    def entry(cid):
        return {
            "status":"VERIFIED_BOUND_CAPABILITY",
            "action_template":{
                "type":"invoke_capability",
                "args":{"capability_id":cid,"output_path":"${input.output_path}"},
                "expect":{"type":"field_equals","field":"output_verified","value":True},
            },
            "provides":["zebrafish.metric"],
            "requires":[],
            "keywords":["zebrafish","metric"],
            "platforms":["linux","windows","darwin"],
            "source":{"type":"stdlib"},
            "adapter_module":"python_stub",
        }
    return {
        "zebrafish.metric.alpha":entry("zebrafish.metric.alpha"),
        "zebrafish.metric.beta":entry("zebrafish.metric.beta"),
    }


class TieBrokenByTheSentenceTheClauseCameFrom(unittest.TestCase):
    def setUp(self):
        type(self).reg=staticmethod(_registry())
        type(self).root=staticmethod(str(REPO_ROOT))

    def test_read_a_pdf_selects_the_text_extractor_not_the_ocr_engine(self):
        plan=gc.compile_goal("Read a PDF and extract its text.",self.reg,self.root)
        parts=plan.get("compiled_parts") or [plan]
        self.assertEqual(parts[0]["selected_capability"],"pdf.extract.text.pypdf")

    def test_the_clause_alone_really_does_tie(self):
        # Without the tiebreaker's wider text the two are indistinguishable, so
        # this pins the premise the fix rests on rather than assuming it.
        tied=[]
        for cid in ("pdf.extract.text.pypdf","pdf.extract.ocr.tesseract"):
            score,specificity,_=gc._score("Read a PDF",cid,self.reg[cid])
            tied.append((score,specificity))
        self.assertEqual(tied[0],tied[1])
        separated=[gc._score("Read a PDF and extract its text.",c,self.reg[c])[:2]
                   for c in ("pdf.extract.text.pypdf","pdf.extract.ocr.tesseract")]
        self.assertNotEqual(separated[0],separated[1])

    def test_a_genuine_ambiguity_still_refuses(self):
        """Negative control, on a pair that genuinely is indistinguishable.

        This used to use ``Run the unittest corpus and produce a pass rate
        report.`` That goal was never genuinely ambiguous -- the next test
        measures why -- so it is replaced here by a synthetic pair built to
        tie: identical keywords, identical placeholders, no receipt and no
        declared discovery mechanism to separate them. A tie with no basis to
        break it must still refuse rather than guess.
        """
        reg=_ambiguous_pair_registry()
        with self.assertRaises(gc.GoalCompilationFailure) as ctx:
            gc.compile_goal(
                "Compute the zebrafish metric and store it.",
                reg,self.root,
            )
        self.assertEqual(ctx.exception.code,"GOAL_COMPILATION_AMBIGUOUS")

    def test_the_unittest_corpus_goal_was_never_ambiguous(self):
        """The premise the old negative control rested on, measured and false.

        ``Run the unittest corpus and produce a pass rate report.`` scored
        ``python.tests.audit.unittest`` at 6 while both competitors scored 4.
        There was never a tie involving the owner: the owner was DROPPED,
        because ``pattern`` had no binder at all and world binding filled
        ``source_root`` with ``.`` -- a root under which ``test*.py`` matches
        nothing. The refusal was therefore not the compiler declining to
        guess between two rivals; it was the compiler failing to see the one
        capability that owned the goal, then tying two that did not.

        Once the capability's own verification record supplies both slots, the
        owner wins outright on score and the ambiguity disappears. Pinning the
        scores, not just the outcome, is what keeps this honest: if the owner
        ever stops outranking its rivals the compile is guessing again.
        """
        owner="python.tests.audit.unittest"
        goal="Run the unittest corpus and produce a pass rate report."
        rivals=("source.candidates.enumerate.stdlib",
                "document.convert.markdown_pdf.pandoc_weasyprint")
        owner_score=gc._score(goal,owner,self.reg[owner])[0]
        rival_scores=[gc._score(goal,c,self.reg[c])[0] for c in rivals]
        self.assertGreater(owner_score,max(rival_scores))
        plan=gc.compile_goal(goal,self.reg,self.root)
        parts=plan.get("compiled_parts") or [plan]
        self.assertEqual(parts[0]["selected_capability"],owner)
        inputs=plan.get("inputs") or {}
        # Both come from the capability's recorded, receipt-pinned run -- not
        # from a heuristic, and not authored here.
        self.assertEqual(inputs.get("pattern"),"test_*.py")
        self.assertEqual(inputs.get("source_root"),"canonical/tests")
        # And the plan says so. A value supplied by a receipt must never be
        # reported as though the sentence had stated it.
        prov=plan.get("binding_provenance") or {}
        self.assertEqual(
            prov.get("filled_from_demonstrated_case"),
            {"pattern":"test_*.py","source_root":"canonical/tests"},
        )
        self.assertEqual(plan.get("binding_source"),"GOAL_STATEMENT+WORLD_BINDING")

    def test_the_tiebreaker_never_admits_a_candidate_the_sentence_rejected(self):
        # Negative control on the invariant the ranking documents: an inferred
        # candidate must not outrank a grounded one. Whatever the resolver
        # returns has to be one of the candidates the grounded pass tied on --
        # it may reorder them, never replace them.
        tied=[
            (10,1,"pdf.extract.ocr.tesseract",self.reg["pdf.extract.ocr.tesseract"],
             {"input_path":"x"},[],None),
            (10,1,"pdf.extract.text.pypdf",self.reg["pdf.extract.text.pypdf"],
             {"input_path":"x"},[],None),
        ]
        resolved=gc._resolve_tie_by_executability(
            "Read a PDF",self.reg,self.root,tied,future_clauses=["extract its text"],
        )
        self.assertIsNotNone(resolved)
        self.assertIn(resolved[2],{"pdf.extract.text.pypdf","pdf.extract.ocr.tesseract"})
        self.assertEqual(resolved[2],"pdf.extract.text.pypdf")

    def test_the_resolver_refuses_when_it_cannot_separate(self):
        # Negative control. Two candidates that stay tied even on the wider
        # text must come back as None so the caller refuses as before.
        tied=[
            (5,1,"pdf.extract.ocr.tesseract",self.reg["pdf.extract.ocr.tesseract"],
             {},[],None),
            (5,1,"pdf.extract.text.pypdf",self.reg["pdf.extract.text.pypdf"],
             {},[],None),
        ]
        self.assertIsNone(gc._resolve_tie_by_executability(
            "zzz qqq",self.reg,self.root,tied,future_clauses=[],
        ))


class SubgoalAbsorbedByTheCompiledPrefix(unittest.TestCase):
    def setUp(self):
        type(self).reg=staticmethod(_registry())
        type(self).root=staticmethod(str(REPO_ROOT))

    def test_one_action_described_twice_compiles_once(self):
        plan=gc.compile_goal("Read a PDF and extract its text.",self.reg,self.root)
        parts=plan.get("compiled_parts") or []
        self.assertTrue(parts)
        self.assertEqual(
            parts[-1].get("mode"),"SUBGOAL_ABSORBED_BY_COMPILED_PREFIX",
        )
        self.assertEqual(parts[-1]["selected_capability"],"pdf.extract.text.pypdf")

    def test_a_clause_whose_words_are_not_in_the_prefix_is_not_absorbed(self):
        # Negative control. "bind it to a claim" shares no identity with the
        # capability the prefix selected, so this must still refuse.
        self.assertFalse(gc._subgoal_absorbed_by_prefix(
            "bind it to a claim",
            [{"selected_capability":"pdf.extract.text.pypdf"}],
            self.reg,
        ))

    def test_absorption_needs_real_content_words(self):
        # Negative control. A clause of pure stopwords must not be waved
        # through just because it has nothing to check.
        self.assertFalse(gc._subgoal_absorbed_by_prefix(
            "and then the",
            [{"selected_capability":"pdf.extract.text.pypdf"}],
            self.reg,
        ))

    def test_absorption_needs_a_prefix(self):
        self.assertFalse(gc._subgoal_absorbed_by_prefix(
            "extract its text",[],self.reg,
        ))

    def test_a_goal_with_no_capability_at_all_still_refuses(self):
        # Negative control end to end, on BOTH shapes the compiler can take.
        #
        # This used to pin "Extract evidence from a source, then rank it, then
        # bind it to a claim." as uncompilable. That premise is now false and
        # was measured false: the sentence resolves to a four-step producer
        # chain -- enumerate 400 candidates, rank them, extract objective-
        # grounded evidence, then attempt the claim binding -- and runs to
        # completion. Pinning it as impossible would have pinned a capability
        # the machine demonstrably has.
        #
        # The invariant this control actually protects is unchanged: a goal no
        # capability can serve must still refuse, on the single-clause path and
        # on the multi-clause path alike. The multi-clause case is the one that
        # matters now, because the chained fallback only fires where the clause
        # split has already failed -- so a compound nonsense goal is what proves
        # that fallback refuses instead of fabricating a selection.
        with self.assertRaises(gc.GoalCompilationFailure) as single:
            gc.compile_goal("Teleport the moon into next Tuesday.",
                            self.reg, self.root)
        self.assertEqual(
            single.exception.code,
            "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH",
        )
        with self.assertRaises(gc.GoalCompilationFailure) as compound:
            gc.compile_goal(
                "Fold the alphabet into a paper crane, then whisper to it.",
                self.reg, self.root,
            )
        self.assertEqual(
            compound.exception.code,
            "GOAL_COMPILATION_SUBGOAL_UNRESOLVED",
            "a compound goal no capability can serve must still refuse",
        )


class ChainedPlanClauseCoverageTests(unittest.TestCase):
    """A chained plan may cover a sentence only by accounting for every clause.

    The clause split compiles one capability per clause, so its parts line up
    1:1 with the clauses. A chained plan resolves the sentence's own dependency
    order instead, which can need MORE steps than the sentence has clauses --
    extracting objective-grounded evidence requires ranked candidates first, so
    "extract, then rank, then bind" needs enumerate -> rank -> extract -> bind,
    four steps for three clauses.

    The clause ledger is about the sentence being accounted for, not about how
    many steps execution takes. So each clause must win a DISTINCT step, and a
    step that answers no clause stays in the execution chain without being
    claimed as coverage.
    """

    def setUp(self):
        self.reg = _registry()
        self.root = str(REPO_ROOT)
        self.goal = ("Extract evidence from a source, then rank it, "
                     "then bind it to a claim.")

    def test_every_clause_wins_a_distinct_capability(self):
        compiled = gc.compile_goal(self.goal, self.reg, self.root)
        self.assertTrue(compiled.get("clause_coverage_verified"))
        parts = compiled.get("compiled_parts") or []
        self.assertEqual([p["index"] for p in parts], [0, 1, 2])
        selected = [p["selected_capability"] for p in parts]
        self.assertEqual(len(set(selected)), 3, "two clauses collapsed onto one step")
        self.assertEqual(selected, [
            "source.evidence.extract.objective_grounded.stdlib",
            "source.objective_relevance.rank.bm25",
            "evidence.claim_spec.bind.explicit_comparison.stdlib",
        ])

    def test_a_prerequisite_step_is_not_claimed_as_clause_coverage(self):
        """NEGATIVE CONTROL on the ledger itself.

        ``source.candidates.enumerate.stdlib`` is a prerequisite the dependency
        order forced -- no clause asked to enumerate candidates. It must remain
        in the execution chain, and must NOT appear as a clause's capability.
        If it did, the ledger would be claiming the sentence asked for something
        it did not.
        """
        compiled = gc.compile_goal(self.goal, self.reg, self.root)
        claimed = {p["selected_capability"] for p in compiled["compiled_parts"]}
        self.assertNotIn("source.candidates.enumerate.stdlib", claimed)
        self.assertIn(
            "source.candidates.enumerate.stdlib",
            compiled.get("effect_producer_chain_steps") or [],
            "the prerequisite must still be in the execution chain",
        )
        self.assertEqual(len(compiled["effect_producer_chain_steps"]), 4)

    def test_attribution_refuses_when_a_clause_wins_no_step(self):
        """NEGATIVE CONTROL: the attribution must be able to say no.

        A clause no step answers means the sentence is not accounted for. The
        helper must return None so the caller re-raises the split's original
        reason rather than reporting coverage it does not have.
        """
        parts = [
            {"selected_capability": "pdf.extract.text.pypdf", "inputs": {}},
        ]
        self.assertIsNone(gc._attribute_chained_parts_to_clauses(
            ["read the pdf", "then summarise it"], parts, self.reg,
        ))

    def test_attribution_refuses_when_two_clauses_want_the_same_step(self):
        """NEGATIVE CONTROL: one step cannot cover two clauses."""
        parts = [
            {"selected_capability": "pdf.extract.text.pypdf", "inputs": {}},
        ]
        self.assertIsNone(gc._attribute_chained_parts_to_clauses(
            ["read the pdf", "extract the pdf text"], parts, self.reg,
        ))

    def test_attribution_refuses_an_unknown_capability(self):
        parts = [{"selected_capability": "no.such.capability", "inputs": {}}]
        self.assertIsNone(gc._attribute_chained_parts_to_clauses(
            ["do something"], parts, self.reg,
        ))


if __name__=="__main__":
    unittest.main()
