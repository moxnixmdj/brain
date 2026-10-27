"""A refactoring sentence names a SYMBOL; the binder only ever read paths.

Measured on main 34648e4f, before this slice:

    "Rename the function add to plus in the python module <root>/pkg/calc.py
     and save the report to <root>/ren.json."

scored ``python.refactor.rename_symbol.v1`` at 22 -- the highest prose score of
any candidate -- and then dropped it with
``GOAL_INPUT_BINDING_REQUIRED module``, because ``_bind_inputs`` produced only
``text``/``goal``/``url``/``*_path``/``*_argv``/``*_root``/``*_dir`` values and
``module`` is none of those.  ``qualname``, ``old_param``, ``new_param``,
``old_symbol`` and ``new_symbol`` were unreachable the same way, so all three
rename capabilities were present, correct and **unbindable from language**.
The goal then fell through to an artifact writer whose only relation to the
request was that it can write the report file.

These tests pin the binding, not the score: every value below is read out of a
phrase in the sentence, and a sentence that names no symbol binds nothing.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_the_sentence_names_the_symbol"
REL = "canonical/astra_runtime/tmp/test_the_sentence_names_the_symbol"

MODULE = (
    "class Calc:\n"
    "    def scale(self, a, b):\n"
    "        return a * b\n"
    "\n"
    "def add(a, b):\n"
    "    return a + b\n"
)

SUITE = (
    "import pathlib\n"
    "import sys\n"
    "import unittest\n"
    "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
    "import calc\n"
    "\n"
    "class T(unittest.TestCase):\n"
    "    def test_add(self): self.assertEqual(calc.add(2, 3), 5)\n"
)


@pytest.fixture()
def world():
    shutil.rmtree(WORK, ignore_errors=True)
    (WORK / "pkg").mkdir(parents=True)
    (WORK / "pkg/calc.py").write_text(MODULE, encoding="utf-8")
    (WORK / "pkg/test_calc.py").write_text(SUITE, encoding="utf-8")
    yield WORK / "pkg"
    shutil.rmtree(WORK, ignore_errors=True)


def _registry():
    return live.load_verified_registry()


def _entry(capability_id):
    return _registry()[capability_id]


def test_a_symbol_sentence_binds_the_symbol_slots(world):
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["qualname"] == "add"
    assert inputs["new_symbol"] == "plus"
    assert inputs["output_path"] == REL + "/ren.json"


def test_the_module_and_the_root_are_one_binding(world):
    """The adapter resolves ``module`` RELATIVE TO ``source_root``.

    Binding the repo-relative path and the module's own directory as the root
    made the adapter look for ``pkg/<root>/pkg/calc.py`` and refuse
    PATH_MISSING, so the pair has to be decided together.
    """
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["source_root"] == REL + "/pkg"
    assert (ROOT / inputs["source_root"] / inputs["module"]).is_file()
    assert inputs["module"] == "calc.py"


def test_a_parameter_sentence_binds_the_parameter_slots(world):
    goal = (f"Rename the parameter a to x in the function add in the python module "
            f"{REL}/pkg/calc.py and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_parameter.v1"))
    assert inputs["old_param"] == "a"
    assert inputs["new_param"] == "x"
    assert inputs["qualname"] == "add"


def test_a_dotted_address_keeps_its_scope(world):
    """``Calc.scale to Calc.multiply`` is one address, not two identifiers."""
    goal = (f"Rename the method Calc.scale to Calc.multiply in the python module "
            f"{REL}/pkg/calc.py and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["qualname"] == "Calc.scale"
    assert inputs["new_symbol"] == "multiply"


def test_a_quoted_identifier_is_still_an_identifier(world):
    goal = (f"Rename `add` to `plus` in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["qualname"] == "add"
    assert inputs["new_symbol"] == "plus"


def test_the_verification_suite_is_the_one_beside_the_module(world):
    """A blind edit is not a rename, so the referee suite is discovered.

    The adapter's own law is that with no suite it returns PASS_BLIND --
    verified false -- and the registry's ``gate == PASS`` expectation refuses
    the run.  The suite is therefore not an invented input: it is the test
    module that already sits beside the module the sentence named.
    """
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["run_tests"] == ["test_calc.py"]
    assert (ROOT / inputs["source_root"] / inputs["run_tests"][0]).is_file()


def test_no_suite_beside_the_module_means_no_suite_is_bound(world):
    (world / "test_calc.py").unlink()
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert "run_tests" not in inputs


def test_a_sentence_that_names_no_symbol_binds_nothing(world):
    assert gc._identifier_slots(
        f"Write a summary of the python module {REL}/pkg/calc.py and save it to {REL}/s.json.",
        ROOT,
    ) == {}


def test_a_symbol_with_no_module_is_not_bound(world):
    """Without a module the rename address is ambiguous, so the slot stays open."""
    inputs = gc._identifier_slots("Rename the function add to plus.", ROOT)
    assert inputs["qualname"] == "add"
    assert inputs["new_symbol"] == "plus"
    assert "module" not in inputs


def test_execution_knobs_are_defaulted_not_invented(world):
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert "timeout_s" not in inputs
    assert "python_executable" not in inputs
    # ... and rendering the template must not turn that into a failure.
    rendered = gc._render_template(
        _entry("python.refactor.rename_symbol.v1")["action_template"], inputs)
    assert "python_executable" not in rendered["args"]
    assert "timeout_s" not in rendered["args"]


def test_a_stated_knob_is_bound(world):
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"with timeout_s 30 and save the report to {REL}/ren.json.")
    inputs = gc._bind_inputs(goal, ROOT, _entry("python.refactor.rename_symbol.v1"))
    assert inputs["timeout_s"] == 30


def test_the_route_reaches_the_rename_verb_and_not_a_converter(world):
    """The measured defect: the sentence was answered by a markdown-to-PDF writer.

    ``document.convert.markdown_pdf.pandoc_weasyprint`` bound ``markdown_path``
    to the ``.py`` file the sentence named and reported success for work nobody
    asked for.  The symbol slots now bind, so the capability the sentence
    describes is the one that is selected.
    """
    goal = (f"Rename the function add to plus in the python module {REL}/pkg/calc.py "
            f"and save the report to {REL}/ren.json.")
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "python.refactor.rename_symbol.v1"
    assert compiled["inputs"]["qualname"] == "add"
    assert compiled["inputs"]["new_symbol"] == "plus"
