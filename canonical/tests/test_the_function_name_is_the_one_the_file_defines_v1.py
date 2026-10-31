"""The function a sentence names is the one the file defines, not the word beside it.

Measured 2026-10-31, advanced sentence 35:

    Rename the public function total in <pkg>/util.py to sum_all across the repository.

``python.refactor.rename_symbol.v1`` exists, does exactly that, and serves the same
sentence about one file on the capability matrix.  The sentence was refused
``ROUTE_ADMISSION_REJECTED:R3_WEAK_EVIDENCE`` because the derivation of ``qualname``
read the word in front of "function" as the function's name.  The grammar knew
``<name> function`` ("the total function") and nothing else, so "the public function
total" produced ``public``, the file defines no ``public``, the match set was empty,
and the only proven reading -- ``total``, the single function the file defines among
the names the sentence states -- was never tried.

The fix is a proof instead of a vocabulary: both word orders are read as candidates
and the file's own AST keeps the one it defines.  An adjective is not excluded by
being on a list; it is excluded because the file does not define it.  The negative
control below is the load-bearing case: a sentence that names a function the file
does NOT define must still derive nothing, because otherwise the rule would be
"whichever name appears next to the word function", which is what failed.

Independent oracle: the file on disk and its AST.  Every test builds a fresh tree.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_function_name_is_defined"

RENAME_SYMBOL_CONTRACT = {
    "capability_id": "python.refactor.rename_symbol.v1",
    "module": "${input.module}",
    "qualname": "${input.qualname}",
    "new_symbol": "${input.new_symbol}",
    "source_root": "${input.source_root}",
    "output_path": "${input.output_path}",
}


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/util.py").write_text(
        "def total(values):\n    return sum(values)\n\n"
        "def helper(x):\n    return x\n", encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _contract() -> dict:
    return {"action_template": {"args": dict(RENAME_SYMBOL_CONTRACT)}}


class TheNameTheSentenceStatesTests(unittest.TestCase):
    def test_the_adjective_before_the_noun_is_not_the_function_name(self):
        base = _fresh("adjective")
        goal = (f"Rename the public function total in {_rel(base / 'pkg/util.py')} "
                "to sum_all across the repository.")
        derived = derivation.derive(goal, _contract(), ROOT)
        self.assertIn("qualname", derived)
        self.assertEqual(derived["qualname"]["value"], "total")
        self.assertEqual(derived["qualname"]["rule"], "QUALNAME_PROVED_FROM_STATED_SOURCE_AST")

    def test_the_other_word_order_is_read_the_same_way(self):
        base = _fresh("reverse_order")
        goal = (f"Rename the total function in {_rel(base / 'pkg/util.py')} "
                "to sum_all across the repository.")
        derived = derivation.derive(goal, _contract(), ROOT)
        self.assertEqual(derived["qualname"]["value"], "total")

    def test_a_name_the_file_does_not_define_derives_nothing(self):
        """The negative control: proof, not position, decides."""
        base = _fresh("undefined")
        goal = (f"Rename the public function multiply in {_rel(base / 'pkg/util.py')} "
                "to sum_all across the repository.")
        derived = derivation.derive(goal, _contract(), ROOT)
        self.assertNotIn("qualname", derived)

    def test_two_defined_functions_named_in_the_sentence_are_ambiguous(self):
        base = _fresh("ambiguous_names")
        goal = (f"Rename the public function total and the function helper in "
                f"{_rel(base / 'pkg/util.py')} to sum_all.")
        derived = derivation.derive(goal, _contract(), ROOT)
        self.assertNotIn("qualname", derived)

    def test_the_door_renames_the_function_the_sentence_names(self):
        """End to end: the row that exists is reached and the edit is real."""
        base = _fresh("door")
        source = base / "pkg/util.py"
        goal = (f"Rename the public function total in {_rel(source)} "
                "to sum_all across the repository.")
        result = door.solve({"task_id": "THE_FUNCTION_NAME_IS_DEFINED", "goal": goal}) or {}
        self.assertTrue(result.get("pass"), result.get("status"))
        text = source.read_text(encoding="utf-8")
        self.assertIn("def sum_all(", text)
        self.assertNotIn("def total(", text)


if __name__ == "__main__":
    unittest.main()
