#!/usr/bin/env python3
"""Pins for the sentences this machine could not hear even though it had bound them.

Measured on 9ebfa2a, asking every capability its own way -- by naming it, then stating its
declared inputs in a caller's words -- 39 of them were refused with
`named_but_inputs_not_stated:<slot>` or `contract_not_stated:inputs`.  Two of those refusals
were not about the sentence at all:

  * A LIST WAS NOT A STATEMENT.  Every "was it stated?" test in the front compiler was
    `isinstance(value, str)`.  `shell.command.run` bound `argv` to exactly the quoted command
    the caller wrote -- "cat README.md" -> ["cat", "README.md"] -- and was then refused
    `named_but_inputs_not_stated:argv`, because a list is not a string.  `queries`,
    `test_argv`, `test_paths`, `source_paths`, `changed_paths` and `edits` were refused the
    same way, which is the single largest cause of the residue.

  * A DELIMITED RUN IS A LIST.  "resolve the symbols add, sub" bound `queries` to ["add"] and
    the caller's second question was silently dropped: the artifact then honestly reported one
    query, and a truthful answer to a narrower question is not the answer to the question.

And one refusal lied about its own cause: when no declared input was missing, it reported the
word "inputs" as though one were, so a request that had stated everything was told to state
inputs it had already stated.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "canonical" / "astra_runtime" / "tmp" / "pins_stated_list_v1"


@pytest.fixture(scope="module")
def registry():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


@pytest.fixture(scope="module")
def work():
    work = WORK
    work.mkdir(parents=True, exist_ok=True)
    (work / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (work / "test_mod.py").write_text("from mod import add\n", encoding="utf-8")
    (work / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (WORK / "pkg").mkdir(exist_ok=True)
    (WORK / "pkg" / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (WORK / "src_dir").mkdir(exist_ok=True)
    return work


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


# ------------------------------------------------------------------ the law: a list is a value

def test_a_bound_list_the_sentence_states_is_a_stated_value():
    text = 'Run the shell command "cat README.md"'
    assert front._stated_in(text, ["cat", "README.md"]) is True


def test_a_list_with_one_unstated_member_is_not_stated():
    # The binder's job is to bind what the sentence says; the check's job is to notice when it
    # bound something the sentence did not say.  Half a list is exactly that.
    text = 'Run the shell command "cat README.md"'
    assert front._stated_in(text, ["cat", "secrets.txt"]) is False


def test_a_string_that_is_not_in_the_sentence_is_not_stated():
    assert front._stated_in("Run the shell command", ["cat"]) is False
    assert front._stated_in("Run the shell command", ["cat", "README.md"]) is False


def test_an_empty_list_is_not_a_statement():
    assert front._stated_in("Run anything at all", []) is False


def test_the_regression_that_named_a_statement_as_a_gap():
    """The exact refusal this unit exists for: argv bound, and still called unstated."""
    inputs = {"output_path": rel(WORK / "out.json"), "argv": ["cat", "README.md"]}
    unstated = front._inputs_not_stated_by('Run the shell command "cat README.md" and save the '
                                           'output to ' + rel(WORK / "out.json"), inputs)
    assert "argv" not in unstated


# --------------------------------------------------- the law: a delimited run is a list of names

def test_a_delimited_run_binds_every_name():
    assert gc._identifiers_after_role("resolve the symbols add, sub in the tree",
                                      ["symbols", "queries"]) == ["add", "sub"]


def test_a_single_name_stays_a_single_name():
    assert gc._identifiers_after_role("resolve the symbol add in the tree",
                                      ["symbol", "symbols"]) == ["add"]


def test_the_run_stops_where_the_prose_resumes():
    # "and" is a delimiter, "in the source root" is not a name.  A stopword in the run ends it
    # rather than being appended to the artifact as an unresolved identifier.
    assert gc._identifiers_after_role("resolve the symbols add and in the tree",
                                      ["symbols"]) == ["add"]


# ----------------------------------------------- the whole requests, through the front door

def test_a_quoted_command_is_the_command(registry, work):
    goal = ('Run the shell command "cat README.md" and save the output to '
            + rel(work / "out.json"))
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "shell.command.run"
    assert compiled["inputs"]["argv"] == ["cat", "README.md"]


def test_two_named_symbols_are_two_questions(registry, work):
    goal = ("Resolve the symbols add, sub in the source root " + rel(work / "src_dir")
            + " and save the index to " + rel(work / "out.json"))
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "python.source.symbols.resolve.v1"
    assert compiled["inputs"]["queries"] == ["add", "sub"]


def test_a_tree_slot_takes_a_tree_and_a_file_slot_takes_a_file(registry, work):
    goal = ("Run a git blame of the file " + rel(work / "calc.py") + " in the worktree "
            + rel(work / "src_dir") + " and save it to " + rel(work / "out.json"))
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "vcs.git.blame.v1"
    assert compiled["inputs"]["path"] == rel(work / "calc.py")
    assert compiled["inputs"]["worktree_path"] == rel(work / "src_dir")


def test_a_capability_the_sentence_names_is_the_capability(registry):
    """A NAME in the request outranks keyword overlap, and this is the measured case.

    "Run the python perf benchmark ... " states the capability's whole name, and the pinned
    scorer ranked it BEHIND `code.multilanguage.parse.tree_sitter.v1`, which merely shared the
    word "tree" from "source tree".  The scorer weighs a name word like any other evidence; a
    sentence that spells the name out is not offering evidence, it is identifying the tool.
    Eight capabilities were unaskable by their own names for exactly this reason
    (`python.quality.*`, `python.perf.benchmark.v1`, `python.packaging.build_package.v1`, ...).
    """
    goal = ("Run the python perf benchmark on source tree " + rel(WORK / "src_dir")
            + " and save it to " + rel(WORK / "out.json"))
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "python.perf.benchmark.v1"


def test_the_whole_name_has_to_be_stated(registry):
    """The complement, so the law cannot widen into "a name word decides".

    `python.quality.coverage.v1` and `python.quality.flake_detect.v1` share "python quality";
    a sentence that states only those two words has named neither of them, and the scorer must
    still be free to choose on the strength of the rest of the sentence.
    """
    assert front._named_by_its_own_name(gc._tokens("python quality"), "python.quality.coverage.v1") is False
    assert front._named_by_its_own_name(
        gc._tokens("run the python quality coverage"), "python.quality.coverage.v1") is True


def test_a_refusal_with_nothing_missing_says_so_instead_of_naming_inputs(registry):
    """A refusal must name the thing to fix; it may not invent one.

    `text.file.write` is routed away from by the body's own walk even though the sentence names
    it, so the named guard fires.  Its diagnosis used to say `contract_not_stated:inputs` -- a
    slot the capability does not declare -- which sends the caller to fix something that is not
    wrong.
    """
    goal = 'Run the text file write. text "hello world" and save it to ' + rel(WORK / "out.json")
    with pytest.raises(gc.GoalCompilationFailure) as raised:
        front.compile_goal(goal, registry, ROOT)
    detail = str(raised.value.detail)
    assert detail.endswith("contract_not_stated:no_declared_input_missing"), detail


def test_the_refusal_still_names_the_inputs_that_are_missing(registry, work):
    """The complementary case: a real gap keeps the old, useful diagnosis."""
    goal = "Rename the symbol add to plus and save the report to " + rel(work / "out.json")
    with pytest.raises(gc.GoalCompilationFailure) as raised:
        front.compile_goal(goal, registry, ROOT)
    detail = str(raised.value.detail)
    # The diagnosis names the slot that is genuinely missing, in the caller's own terms.
    assert "module" in detail, detail
    assert "no_declared_input_missing" not in detail


# ------------------------------------------- the fallbacks that must run BEFORE a refusal

def test_a_rename_states_its_new_symbol(registry, work):
    """The pinned binder has no rule for an identifier introduced by "to"; the typed one does.

    Measured: every refactor verb was refused `contract_not_stated:module,new_symbol,...` for a
    sentence that stated all of them, because the pinned binder failed the slot and the typed
    grammar was never asked.
    """
    goal = ("Rename the symbol add to plus in the python module " + rel(work / "mod.py")
            + " and save the report to " + rel(work / "reports" / "rename.json"))
    (work / "reports").mkdir(exist_ok=True)
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "python.refactor.rename_symbol.v1"
    assert compiled["inputs"]["new_symbol"] == "plus"
    assert compiled["inputs"]["qualname"] == "add"


def test_an_identifier_slot_does_not_take_a_path():
    """The anti-fabrication check cannot catch this one, because the file name IS in the sentence.

    "new_symbol" is an identifier slot; `out.json` is not an identifier.  Without this law the
    sentence "... and save the report to out.json" offered its own destination as the symbol name.
    """
    assert front._parse_typed_value("new_symbol", " out.json") is None
    assert front._parse_typed_value("new_symbol", " plus") == "plus"
    assert front._parse_typed_value("qualname", " pkg/mod.py") is None


def test_an_output_path_the_pinned_binder_cannot_decide_is_bound_not_dropped(registry, work):
    """An output that vanishes from the request makes the capability write wherever it likes.

    Measured: the pypi provenance audit states `report_path` in plain words and the row only
    passed because the missing artifact path was never noticed -- the handler meant to bind it sat
    after an unconditional `continue`.
    """
    (work / "selection.json").write_text("{}", encoding="utf-8")
    (work / "metadata.json").write_text("{}", encoding="utf-8")
    entry = dict(registry["pypi.provenance.audit_live_artifact"])
    goal = ("Audit the provenance of " + rel(work / "metadata.json") + " against the selection "
            + rel(work / "selection.json") + " and save the report to "
            + rel(work / "reports" / "provenance.json"))
    bound = front.bind_all_inputs(goal, entry, ROOT, cycle=0, spool=set())
    assert "report_path" in bound, bound
    assert bound["report_path"].endswith(".json"), bound
