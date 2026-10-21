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
        # Negative control. This goal ties on two capabilities that are both
        # wrong and neither wider text nor executability can separate them;
        # absorbing or guessing here would be a fabricated selection.
        with self.assertRaises(gc.GoalCompilationFailure) as ctx:
            gc.compile_goal(
                "Run the unittest corpus and produce a pass rate report.",
                self.reg,self.root,
            )
        self.assertEqual(ctx.exception.code,"GOAL_COMPILATION_AMBIGUOUS")

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
        # Negative control end to end.
        with self.assertRaises(gc.GoalCompilationFailure):
            gc.compile_goal(
                "Extract evidence from a source, then rank it, then bind it to a claim.",
                self.reg,self.root,
            )


if __name__=="__main__":
    unittest.main()
