#!/usr/bin/env python3
"""Three gates that were deciding on the wrong evidence, and the proofs they now read.

Measured 2026-10-31 on `96e97b0` (the advanced SWE census, 49 sentences):

1. WHICH SENTENCES MAY DERIVE THEIR INPUTS FROM THE TREE WAS DECIDED BY A WORD LIST.
   `capability_selection_retrieval_v1.admit` gated the derivation on
   `is_swe_request(goal)` -- forty curated verbs.  "Optimise the function total in
   <f>; it is too slow on large inputs", "Add a thread pool to <f> that totals the
   list in parallel" and "Make the function total in <f> release the GIL while
   summing" name an existing source file and state a real effect, contain none of
   those words, and were refused at admission on the `source_root` slot that the
   derivation had already proved against that file.  The row's own id is the
   structural fact; the vocabulary was a second, weaker gate on the same decision.

2. A BINDING REFUSAL WAS REPORTED AS WEAK EVIDENCE.  The binder says exactly which
   declared input it cannot bind (`BINDING_REFUSED:source_root`); the route then fell
   through to the lexical floor and reported `R3_WEAK_EVIDENCE` -- "your sentence is
   thin" -- and three inventories read that as the cause.  Same refusal, named cause.

3. AN EFFECT MUST LAND IN THE FILE THE SENTENCE NAMED.  The cross-file choreographer
   was handed `pkg/` (the tree holding the named file), ran the one pass it found a
   use for -- dead-code pruning -- rewrote `pkg/mod.py` and `pkg/service.py`, and left
   `pkg/util.py` byte-identical.  The door certified
   `PASS__..._EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` for "Optimise the function total in
   <pkg>/util.py".  `output_verified: True` with the stated effect untouched is the
   worst defect class this repository names, and it was reachable because the effect
   was checked against the row's DECLARATION and never against what moved.
"""

from __future__ import annotations

import pathlib
import shutil
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

CHOREOGRAPH = "software.repair.choreograph.crossfile.v1"


def _fixture(name: str) -> tuple[pathlib.Path, dict[str, pathlib.Path]]:
    base = ROOT / "canonical" / "astra_runtime" / "tmp" / ("test_effect_lands_" + name)
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "tests").mkdir()
    files = {
        "util": base / "pkg" / "util.py",
        "calc": base / "pkg" / "calc.py",
        "test": base / "tests" / "test_calc.py",
    }
    files["util"].write_text("def total(xs):\n    out = 0\n    for x in xs:\n        out += x\n"
                             "    return out\n", encoding="utf-8")
    files["calc"].write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    files["test"].write_text("import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
                             "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n",
                             encoding="utf-8")
    return base, files


class TheStatedEffectLandsWhereTheSentencePutIt(unittest.TestCase):
    """(3) A run that edits something else has not performed the stated effect."""

    def setUp(self) -> None:
        self.base, self.files = _fixture("scope")

    def tearDown(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)

    def _rel(self, path: pathlib.Path) -> str:
        return path.relative_to(ROOT).as_posix()

    def test_a_file_the_sentence_named_must_be_the_one_that_moves(self) -> None:
        goal = ("Optimise the function total in %s; it is too slow on large inputs."
                % self._rel(self.files["util"]))
        # The run rewrote two unrelated modules in the same package.
        refusal = door._effect_landed_outside_the_named_subject(
            goal, [self._rel(self.files["calc"]), self._rel(self.files["test"].parent / "test_x.py")])
        self.assertTrue(refusal.startswith("EDITS_LANDED_OUTSIDE_THE_NAMED_SUBJECT:"), refusal)
        self.assertIn("calc.py", refusal)

    def test_the_named_file_moving_is_the_effect(self) -> None:
        goal = ("Optimise the function total in %s; it is too slow on large inputs."
                % self._rel(self.files["util"]))
        self.assertEqual(door._effect_landed_outside_the_named_subject(
            goal, [self._rel(self.files["util"])]), "")

    def test_a_named_test_is_a_witness_not_the_subject_of_a_source_edit(self) -> None:
        # "the test in <T> is failing, make the suite pass" -- the repair belongs in the
        # source the test exercises.  Refusing it would deny work the machine can do.
        goal = ("the test in %s is failing, make the suite pass" % self._rel(self.files["test"]))
        self.assertEqual(door._effect_landed_outside_the_named_subject(
            goal, [self._rel(self.files["calc"])]), "")

    def test_a_sentence_that_names_no_file_is_untouched(self) -> None:
        self.assertEqual(door._effect_landed_outside_the_named_subject(
            "Add a retry to the HTTP client.", [self._rel(self.files["calc"])]), "")


class TheRowDecidesWhetherItsInputsMayBeDerived(unittest.TestCase):
    """(1) The row's own id is the gate; the sentence's vocabulary is not."""

    def setUp(self) -> None:
        self.base, self.files = _fixture("derive")

    def tearDown(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)

    def _rel(self, path: pathlib.Path) -> str:
        return path.relative_to(ROOT).as_posix()

    def test_a_swe_row_binds_its_source_root_from_the_named_file_without_a_magic_verb(self) -> None:
        goal = ("Optimise the function total in %s; it is too slow on large inputs."
                % self._rel(self.files["util"]))
        # The verb list does NOT contain "optimise", so this is the case that was refused.
        self.assertFalse(derivation.is_swe_request(goal))
        entry = door.load_verified_registry()[CHOREOGRAPH]
        view, values, _report = derivation.binding_view(goal, entry, ROOT)
        self.assertEqual(values.get("source_root"), self._rel(self.files["util"].parent))
        from canonical.runtime import capability_selection_retrieval_v1 as selection
        verdict = selection.admit(goal, CHOREOGRAPH, entry, ROOT)
        self.assertFalse(str(verdict.get("reason") or "").startswith("BINDING_REFUSED:source_root"),
                         verdict)


class ARefusedBindingIsNamedAsSuch(unittest.TestCase):
    """(2) `R3_WEAK_EVIDENCE` must not stand in for a named binding refusal."""

    def test_a_declared_input_that_cannot_bind_is_named(self) -> None:
        from canonical.runtime import capability_selection_retrieval_v1 as selection
        entry = door.load_verified_registry()[CHOREOGRAPH]
        goal = ("Pin the dependency versions in %s."
                % (ROOT / "pyproject.toml").relative_to(ROOT).as_posix())
        typed = selection.admit(goal, CHOREOGRAPH, entry, ROOT)
        if not str(typed.get("reason") or "").startswith("BINDING_REFUSED:"):
            self.skipTest("the fixture's pyproject.toml is bindable on this tree")
        verdict = door.route_admission(goal, {"selected_capability": CHOREOGRAPH,
                                              "compiler_mode": "front"}, door.load_verified_registry())
        self.assertFalse(verdict.get("admitted"))
        if verdict.get("rule") == "R3_WEAK_EVIDENCE":
            # Only acceptable when the route was about to be admitted (the rule is a last
            # resort, placed exactly where the lexical floor refused before it).
            self.fail("a known binding refusal was reported as weak evidence: %r" % (verdict,))


if __name__ == "__main__":
    unittest.main()
