"""A quantity is not a name, and the door may not credit one as if it were.

The measured defect
-------------------
On base ``ce92836``, through the public entry
``canonical.runtime.live_brain_route_admission_v1.solve``::

    goal   "Show the last three git commits."
    route  canonical/runtime/cursorbench_three_region_complement_nonidentifiability_v1.py.auto.v1
    basis  DECISIVE_LEXICAL_MARGIN, runner-up python.repo.diff_apply_full_testgate.v1
    status PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
    pass   True, semantic_acceptance_complete True, obligations accepted 1/1

The request was about git history.  The capability executed is a CursorBench
three-region complement verifier that reads no git and answers nothing about
git.  It earned the route on the single shared token ``three`` -- because
``_tokens`` drops one-character digits but keeps numerals spelled out -- and it
earned the *credit* because the acceptance layer asks whether the capability's
own declared effect happened, which it did.  A false credit of this shape is
worse than a refusal: every number this repository reports is measured as a
pass, so a pass that nothing caused is a defect in the instrument itself.

What the fix is, and what it deliberately is not
------------------------------------------------
Numerals, ordinals and frequency words are declared generic vocabulary in
``goal_compiler.GENERIC_MATCH_TOKENS``.  Generic tokens may still *refine* a
match that a distinctive token created; they may never *create* one.  So:

  * the numeral can no longer be the whole basis of a route (defect closed);
  * a capability that is genuinely about two regions still routes through
    "two"/"region"/"complement", and is still reached when a sentence names it
    (controls below);
  * nothing is deleted, no capability is unregistered, no threshold moves.

Measured on the live 419-entry registry: 8 numerals are in use (zero 11, one 3,
two 3, five 3, four 1, seven 1, second 1, three 1); 0 capabilities lose their
last distinctive token and 0 are named only by a numeral.
``test_no_capability_loses_its_last_distinctive_token`` is the guard that keeps
that true when someone adds the next word to the list.

Zero external model.  Zero spend.  Deterministic: every assertion below is about
tokens and admissions, not about timing or environment.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import goal_compiler as compiler
from canonical.runtime import live_integrated_brain_v1 as live_brain
from canonical.runtime import live_brain_route_admission_v1 as admission

# The capability the measured sentence reached, and the sentence itself.
NUMERAL_CAPABILITY = (
    "canonical/runtime/"
    "cursorbench_three_region_complement_nonidentifiability_v1.py.auto.v1"
)
GIT_QUESTION = "Show the last three git commits."

# The words the fix declares generic.  Kept as a literal so a change to the
# vocabulary is visible here rather than inferred from the compiler.
QUANTITY_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million",
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
    "eighth", "ninth", "tenth", "once", "twice", "thrice",
)


class QuantityIsNotIdentity(unittest.TestCase):
    """The defect, the fix, and the two controls that keep it from over-reaching."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = live_brain.load_verified_registry()

    def test_the_vocabulary_is_actually_declared_generic(self) -> None:
        """The rule lives in the shared vocabulary, not in one call site.

        Both readers consult ``GENERIC_MATCH_TOKENS``: the compiler's scoring
        (a generic token can refine, never create, a match) and the selector's
        name/request words.  Declaring it once is the whole reason a numeral
        stops counting as evidence in both places at once.
        """
        missing = sorted(w for w in QUANTITY_WORDS
                         if w not in compiler.GENERIC_MATCH_TOKENS)
        self.assertEqual([], missing)

    def test_a_numeral_cannot_name_the_capability_by_itself(self) -> None:
        """The measured route.  Before the fix this returned True."""
        self.assertFalse(
            selection.request_names_capability(GIT_QUESTION, NUMERAL_CAPABILITY)
        )
        # And the reason is the numeral, not a missing route: the capability's
        # own distinctive name words are intact.
        self.assertEqual(
            {"complement", "cursorbench", "nonidentifiability", "region"},
            set(selection._name_words(NUMERAL_CAPABILITY)),
        )

    def test_the_door_does_not_credit_a_git_question(self) -> None:
        """The false credit itself, through the public entry point.

        A refusal is the correct answer here: no bound capability in this
        registry reads git history.  What must never come back is a pass.
        """
        result = admission.solve({"task_id": "QUANTITY_NOT_IDENTITY", "goal": GIT_QUESTION})
        self.assertIs(False, result.get("pass"))
        self.assertIsNone(result.get("compiled_capability_id"))
        self.assertNotIn(
            NUMERAL_CAPABILITY, str(result.get("status") or "")
        )
        self.assertIn("FAIL", str(result.get("status") or ""))

    def test_the_capability_is_still_reached_when_a_sentence_names_it(self) -> None:
        """Control 1: the fix removes evidence, not a route.

        If this ever fails, the vocabulary change has deleted a reachable
        capability, which is a capability regression rather than a
        truthfulness gain.
        """
        for goal in (
            "Run the cursorbench three region complement nonidentifiability verifier.",
            "Check the three region complement nonidentifiability with cursorbench.",
        ):
            with self.subTest(goal=goal):
                decision = selection.select(goal, self.registry, ROOT)
                self.assertEqual("SELECTED", decision.get("status"))
                self.assertEqual(NUMERAL_CAPABILITY,
                                 decision.get("selected_capability"))

    def test_no_capability_loses_its_last_distinctive_token(self) -> None:
        """Control 2: the vocabulary can only remove matches that never had a basis.

        For every capability in the live registry, at least one token of its
        name, keywords or provided effects must survive the generic vocabulary.
        Measured before the fix: 0 of 419 fail this; it is asserted so the next
        word added to the list cannot silently unmatch a capability.
        """
        generic = set(compiler.GENERIC_MATCH_TOKENS)
        unmatchable = []
        for cid, entry in self.registry.items():
            if not isinstance(entry, dict):
                continue
            tokens = (compiler._tokens(str(cid).split("/")[-1])
                      | compiler._tokens(" ".join(map(str, entry.get("keywords") or [])))
                      | compiler._tokens(" ".join(map(str, entry.get("provides") or []))))
            if not (tokens - generic):
                unmatchable.append(cid)
        self.assertEqual([], sorted(unmatchable))


if __name__ == "__main__":
    unittest.main()
