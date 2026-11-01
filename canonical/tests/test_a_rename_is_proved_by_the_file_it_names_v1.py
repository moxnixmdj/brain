"""A rename names its two objects by position; the file proves which object it is.

``python.refactor.rename_symbol.v1`` and ``python.refactor.rename_parameter.v1``
declare the same verb and tie on the sentence's lexical evidence, so the only thing
that can separate them is WHAT THE FILE DEFINES.  The noun does that job when the
sentence states one ("Rename the function old_name to ..."), and measured on main
``c64af36c`` that was the only shape that worked:

    "Rename old_name to new_name in <f>."              -> FAIL__RAW_GOAL_COMPILATION_GAP
                                                          rename_parameter:old_param:not_stated
    "Rename the function old_name to new_name in <f>." -> PASS, function renamed

The noun is not a fact about the file.  ``old_name`` is a ``def`` the stated file
contains, and the same sentence without the noun was refused for stating nothing.

Worse, the mirror shape was answered by the wrong object, and reported PASS:

    "Rename text to value in <f>."   (text is a PARAMETER of norm)
      -> python.refactor.rename_symbol.v1 -> "def value(text, scale=1)"

The function's public name changed and the parameter kept its own -- the exact
wrong-object edit the role rule exists to stop, reached through the one shape where
no noun states the role.  ``declared_input_derivation_v1`` now proves both readings
against the stated file's AST (``QUALNAME_PROVED_FROM_STATED_SOURCE_AST`` and
``PARAM_PROVED_FROM_STATED_SOURCE_AST``), and only when the name is unambiguous:
a parameter is not a definition, a definition is not a parameter, and a name the
file does not contain proves nothing at all.
"""
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as registry_module  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/rename_object_proof_v1"
FUNCTION_FILE = "def old_name(x):\n    return x\n\n\ndef use():\n    return old_name(1)\n"
PARAMETER_FILE = "def norm(text, scale=1):\n    return (text + 0) * scale\n"
UNRELATED_FILE = "def norm(text, scale=1):\n    return (text + 0) * scale\n"


def _entry(cid: str):
    return registry_module.load_verified_registry(include_extended=True)[cid]


def _admissible():
    registry = registry_module.load_verified_registry(include_extended=True)
    routable = {cid: entry for cid, entry in registry.items()
                if registry_module.is_verified_entry(entry)}
    return goal_compiler._platform_admissible_registry(routable)


class ARenameIsProvedByTheFileItNames(unittest.TestCase):

    def setUp(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "lib.py").write_text(FUNCTION_FILE, encoding="utf-8")
        (WORK / "models.py").write_text(PARAMETER_FILE, encoding="utf-8")
        self.lib = str((WORK / "lib.py").relative_to(ROOT))
        self.models = str((WORK / "models.py").relative_to(ROOT))

    def tearDown(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)

    # ---- the proof itself -------------------------------------------------

    def test_the_file_proves_a_def_is_the_old_symbol_without_the_noun(self) -> None:
        proved = derivation.derive(f"Rename old_name to new_name in {self.lib}.",
                                   _entry("python.refactor.rename_symbol.v1"), ROOT)
        self.assertEqual(proved["qualname"]["value"], "old_name")
        self.assertEqual(proved["qualname"]["rule"], "QUALNAME_PROVED_FROM_STATED_SOURCE_AST")
        self.assertEqual(proved["new_symbol"]["value"], "new_name")

    def test_the_file_proves_a_parameter_without_the_noun(self) -> None:
        proved = derivation.derive(f"Rename text to value in {self.models}.",
                                   _entry("python.refactor.rename_parameter.v1"), ROOT)
        self.assertEqual(proved["old_param"]["value"], "text")
        self.assertEqual(proved["old_param"]["rule"], "PARAM_PROVED_FROM_STATED_SOURCE_AST")
        self.assertEqual(proved["qualname"]["value"], "norm")

    def test_a_parameter_is_not_a_definition_and_a_definition_is_not_a_parameter(self) -> None:
        symbol_row = derivation.derive(f"Rename text to value in {self.models}.",
                                       _entry("python.refactor.rename_symbol.v1"), ROOT)
        self.assertNotIn("qualname", symbol_row, "a parameter was read as a definition")
        parameter_row = derivation.derive(f"Rename old_name to new_name in {self.lib}.",
                                          _entry("python.refactor.rename_parameter.v1"), ROOT)
        self.assertNotIn("old_param", parameter_row, "a definition was read as a parameter")

    def test_a_name_the_file_does_not_define_proves_nothing(self) -> None:
        (WORK / "other.py").write_text(UNRELATED_FILE, encoding="utf-8")
        other = str((WORK / "other.py").relative_to(ROOT))
        proved = derivation.derive(f"Rename nothing_here to something in {other}.",
                                   _entry("python.refactor.rename_symbol.v1"), ROOT)
        self.assertNotIn("qualname", proved)

    # ---- the sentence, end to end -----------------------------------------

    def test_a_symbol_rename_without_a_noun_reaches_the_symbol_rename(self) -> None:
        compiled = front.compile_goal(f"Rename old_name to new_name in {self.lib}.",
                                      _admissible(), ROOT)
        self.assertEqual(compiled.get("selected_capability"), "python.refactor.rename_symbol.v1")
        self.assertEqual(str((compiled.get("inputs") or {}).get("qualname")), "old_name")

    def test_the_rename_is_applied_to_the_file_and_to_every_caller(self) -> None:
        result = door.solve({"task_id": "RENAME_NOUNLESS",
                             "goal": f"Rename old_name to new_name in {self.lib}."})
        self.assertTrue(result.get("pass"), str(result.get("status")))
        body = (WORK / "lib.py").read_text(encoding="utf-8")
        self.assertIn("def new_name(", body)
        self.assertNotIn("old_name", body)

    def test_a_parameter_rename_without_a_noun_is_not_answered_by_the_symbol_rename(self) -> None:
        result = door.solve({"task_id": "PARAM_NOUNLESS",
                             "goal": f"Rename text to value in {self.models}."})
        self.assertTrue(result.get("pass"), str(result.get("status")))
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.refactor.rename_parameter.v1",
                         "the function's public name was changed instead of the parameter")
        body = (WORK / "models.py").read_text(encoding="utf-8")
        self.assertIn("def norm(value, scale=1)", body)


if __name__ == "__main__":
    unittest.main()
