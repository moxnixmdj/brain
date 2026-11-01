"""A definition is not a file, and moving one is not moving the other.

Measured 2026-11-01 on main ``e304434033``, with ``big.py`` holding ``a``, ``b`` and ``c``:

    "Move b from <b>/big.py into <b>/out.py."
        -> shell.command.run argv ['mv', '<b>/big.py', '<b>/out.py']
        -> big.py DELETED, pass=True,
           PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED

The sentence names ``b``, which lives inside ``big.py``; it does not name a file to move.
Without the word "function" in front of it, the rule that refuses a file command for a
named definition had nothing to match, and ``mv`` overwrote the destination with the
source's bytes and removed the source -- the whole file, for a request about one
definition in it.  "Copy b from A into B" was the same mistake without the deletion: it
copied the whole file and certified it.

The row that answers the move already existed.  With the shell reading out of the way the
typed plan compiles ``python.refactor.move_symbol.v1``, which moves ``b`` out of
``big.py``, leaves ``a`` and ``c`` where they were, and PASSes.

So the discriminator is the sentence's grammar, not another noun list: in
"move|copy <OBJECT> from <SOURCE> ... <DESTINATION>", the OBJECT is what is being moved,
and a file command moves its operands -- it can only be the answer when that object is a
file.  A real file move ("Move <path> to <path>", "Move the file X from A to B") keeps
exactly the reading it had.
"""
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

# Neutral directory name on purpose: a stated PATH is a name, not evidence, and this
# repository does not yet mask the words inside one when it ranks capabilities --
# measured 2026-11-01, the same sentence routed to a different row when the directory
# was called `definition_is_not_a_file_v1` than when it was called `workspace_v1`.
WORK = ROOT / "canonical/astra_runtime/tmp/workspace_v1"
SOURCE = ('"""Maths."""\n\n\ndef a():\n    return 1\n\n\ndef b():\n    return 2\n\n\n'
          'def c():\n    return 3\n')


def definitions(text):
    return [name for name in ("a", "b", "c") if ("def %s(" % name) in text]


class ADefinitionIsNotAFileToMove(unittest.TestCase):

    def setUp(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "big.py").write_text(SOURCE, encoding="utf-8")
        self.relative = str(WORK.relative_to(ROOT))

    def tearDown(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)

    def test_moving_a_definition_moves_the_definition_and_not_the_file(self) -> None:
        result = door.solve({"task_id": "MOVE_A_DEFINITION",
                             "goal": f"Move b from {self.relative}/big.py into {self.relative}/out.py."})
        self.assertTrue(result.get("pass"), (result.get("status"), result.get("reason")))
        self.assertTrue((WORK / "big.py").exists(), "the file the definition lived in was removed")
        self.assertEqual(definitions((WORK / "big.py").read_text(encoding="utf-8")), ["a", "c"],
                         "the definitions that were not moved were not kept")
        self.assertEqual(definitions((WORK / "out.py").read_text(encoding="utf-8")), ["b"])

    def test_the_sentence_is_answered_by_the_row_that_moves_a_symbol(self) -> None:
        result = door.solve({"task_id": "MOVE_A_DEFINITION_ROW",
                             "goal": f"Move b from {self.relative}/big.py into {self.relative}/out.py."})
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.refactor.move_symbol.v1", result.get("status"))
        executed = [step.get("capability_id")
                    for step in ((result.get("composer_execution") or {}).get("steps") or [])]
        self.assertNotIn("shell.command.run", executed,
                         "a file command was handed a definition to move")

    def test_copying_a_definition_changes_nothing_and_says_so(self) -> None:
        result = door.solve({"task_id": "COPY_A_DEFINITION",
                             "goal": f"Copy b from {self.relative}/big.py into {self.relative}/out.py."})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertFalse((WORK / "out.py").exists(),
                         "the whole file was copied for a request about one definition in it")
        self.assertEqual((WORK / "big.py").read_text(encoding="utf-8"), SOURCE)

    def test_a_path_named_as_the_object_is_still_moved(self) -> None:
        result = door.solve({"task_id": "MOVE_A_PATH",
                             "goal": f"Move {self.relative}/big.py to {self.relative}/moved.py."})
        self.assertTrue(result.get("pass"), (result.get("status"), result.get("reason")))
        self.assertTrue((WORK / "moved.py").exists())
        self.assertFalse((WORK / "big.py").exists(), "a sentence that named a path did not move it")

    def test_the_rule_is_the_grammar_and_not_another_noun_list(self) -> None:
        # The sentence with its stated paths masked, exactly as the reader sees it.
        self.assertFalse(composer._states_a_file_as_the_object("move b  from  into "))
        self.assertTrue(composer._states_a_file_as_the_object("move the file  from  to "))
        self.assertTrue(composer._states_a_file_as_the_object("move the module  to "))
        self.assertTrue(composer._states_a_file_as_the_object("move  to "),
                        "a sentence with no object keeps the file reading it had")


if __name__ == "__main__":
    unittest.main()
