"""The sentence a user actually says must claim the family its near-miss trigger misses.

Measured 2026-11-12, dual-layer census round (``TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY_
20261112_V1.md``): at the door ``refactor the function stated_family_token in
canonical/runtime/swe_typed_plan_v1.py to extract the constant`` reported
``FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED`` while the swe family already carried the
trigger ``extract constant`` -- one article away from the phrase the sentence states.
With the measured phrase added, the same sentence claims the family, ``_resolve_family``
admits ``python.swe.transform_and_synthesize.v1`` with ``operation=extract_constant``,
and ``build_plan`` is decisive. A metaphor and a question must not claim (the
governing-clause and analysis-only guards stay in force).
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import swe_typed_plan_v1 as tp  # noqa: E402

_REGISTRY = json.loads(
    (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
)["capabilities"]

_SENTENCE = ("refactor the function stated_family_token in "
             "canonical/runtime/swe_typed_plan_v1.py to extract the constant")


class TheMeasuredPhraseClaimsTheFamily(unittest.TestCase):

    def test_the_sentence_the_user_says_claims_the_swe_family(self) -> None:
        self.assertEqual(tp.stated_family_token(_SENTENCE), "swe.transform_and_synthesize")

    def test_the_family_resolves_to_the_transform_row_with_the_stated_operation(self) -> None:
        resolved = tp._resolve_family(_SENTENCE, ROOT, _REGISTRY, {})
        self.assertIsNotNone(resolved, "the claimed family found no bindable row")
        cid, inputs = resolved
        self.assertEqual(cid, "python.swe.transform_and_synthesize.v1")
        self.assertEqual(inputs.get("operation"), "extract_constant")

    def test_the_typed_plan_is_decisive_for_that_sentence(self) -> None:
        plan = tp.build_plan(_SENTENCE, ROOT)
        self.assertIsNotNone(plan, "a decisive family claim must produce a plan")
        self.assertEqual(plan[2].get("selected_capability"),
                         "python.swe.transform_and_synthesize.v1")

    def test_a_metaphor_and_a_question_do_not_claim(self) -> None:
        self.assertIsNone(tp.stated_family_token("Branch out the new feature for the report"))
        self.assertIsNone(
            tp.stated_family_token("what is the constant used for in the documentation"))


if __name__ == "__main__":
    unittest.main()
