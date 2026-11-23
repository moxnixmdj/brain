"""`solve_v1`'s model contract filled without a model, and the loop driven to a real state change.

WHY THIS IS THE FILE THAT MATTERS. `solve_v1` is the whole system reduced to observe/act/judge, and it
takes the judging part as a callable: `model(goal, seeing) -> program | None`. Its docstring says the model
"is a callable, not a dependency" -- true, and it left the callable unbuilt. Every run of that loop with
nothing supplied is a run that cannot act, which is why the mission's question "what stops us now" had the
answer "the part that decides what to do".

This supplies that part from mechanisms already in the tree, and measures how far they reach. What it
replaces is not a claim of model-equivalence; it is the sentence "we would need a model" with a number.

    documentation -> a command            require_survey_plan_v1
    a refusal     -> a condition          stated_precondition_v1
    a condition   -> an act               stated_precondition_v1.acts_for

The loop is `solve_v1`'s own, unmodified. The confinement is `confine_v1`'s own, unmodified. Nothing here
is a special case for the fixtures.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BIN = _ROOT / "canonical/tests/programs/bin"
sys.path.insert(0, str(_ROOT))

from canonical.runtime import mechanism_act_v1 as M  # noqa: E402
from canonical.runtime import solve_v1 as S  # noqa: E402


def _sandbox(tmp_path: pathlib.Path, program: str) -> tuple[pathlib.Path, str]:
    """A world whose program is reachable at `/project/bin/...` inside confinement, as a real one is."""
    world = tmp_path / "world"
    (world / "bin").mkdir(parents=True)
    shutil.copy(_BIN / program, world / "bin" / program)
    (world / "bin" / program).chmod(0o755)
    return world, str(world / "bin" / program)


def test_the_loop_reaches_a_real_state_with_no_model(tmp_path: pathlib.Path) -> None:
    """THE CLAIM, END TO END. `solve_v1` runs a goal to `DONE` with a callable that contains no model.

    The judgement -- "is this task finished" -- is the CALLER's, per `solve_v1`'s own design, and it is
    supplied as a list of substrings the caller expects the world to contain. What is not supplied is any
    decided action: the command is read from the program's documentation, run confined, and the world it
    leaves behind is checked on disk, not taken from the receipt.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    goal = program + ': add a record named "top" with amount "5"'
    # the program's OWN state file beside itself: `confine_v1` makes `/project` writable so a program's
    # shipped default works, and overriding that default made a working program fail (measured).
    model = M.as_solve_model(root=str(world), expect=[".ledgerctl-state.json"])

    out = S.solve(goal, str(world), model=model, steps=4, learn=False)

    assert out.get("verdict") == S.DONE, out
    assert out.get("steps") == 1, "the loop took more than one step: %r" % (out.get("trace"),)

    # the world, read from disk -- not from the run's own account of itself
    written = [p for p in world.rglob("*") if p.is_file() and ".ledgerctl-state" in p.name]
    assert written, "the run reported DONE and wrote no state"
    state = written[0].read_text()
    assert "top" in state and "5" in state, state


def test_the_command_is_read_from_the_documentation(tmp_path: pathlib.Path) -> None:
    """No vocabulary of the fixtures anywhere: the same function plans three unrelated programs."""
    for program, goal_text, expected in (
        ("linear", 'create an issue in the team "Platform" titled "alpha"',
         ["issue", "create", "--team", "Platform", "--title", "alpha"]),
        ("ledgerctl", 'add a record named "top" with amount "5"',
         ["record", "add", "--name", "top", "--amount", "5"]),
        ("stockctl", 'set the qty for sku "A1"',
         ["item", "set", "--sku", "A1"]),
    ):
        plan = M.plan_from_documents("./bin/%s: %s" % (program, goal_text))
        assert plan["act"] is not None, (program, plan)
        assert [str(a) for a in plan["act"][1:]] == expected, (program, plan["act"])


def test_it_refuses_a_goal_it_cannot_read_rather_than_guessing() -> None:
    """The honest half. A goal naming no program, or a program whose documents state no command, gets a
    named refusal -- not an invented action. This is the difference between a planner and a guess."""
    assert M.plan_from_documents("")["why"] == "GOAL_NAMES_NO_PROGRAM"

    missing = M.plan_from_documents("no_such_program_anywhere: do the thing")
    assert missing["act"] is None
    assert missing["why"] in ("THE_DOCUMENT_COULD_NOT_BE_READ", "THE_DOCUMENTS_STATE_NO_COMMAND")


def test_a_refusal_that_states_no_subject_stops_the_loop_and_says_why(tmp_path: pathlib.Path) -> None:
    """A loop that retries the same plan against the same refusal is the behaviour §A87 replaced.

    When the last step failed and the failure names nothing, the planner returns None with
    `REFUSAL_STATES_NO_SUBJECT` rather than planning again.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    seeing = {"tree": [], "last": {"exit": 1, "err": "SOMETHING_WENT_WRONG"}}
    model = M.as_solve_model(root=str(world))
    assert model("ledgerctl: do it", seeing) is None
    reasons = [call.get("why") for call in M.report(model)["calls"]]
    assert "REFUSAL_STATES_NO_SUBJECT" in reasons, reasons


def test_the_sandbox_path_translation_is_a_prefix_move_only() -> None:
    """A planned path carries a HOST prefix; confinement mounts it at `/project`.

    Without the translation every step fails on a file the sandbox does have under a name the plan did not
    use -- measured as three identical tracebacks that named nothing, so the loop re-planned each time.
    Only a path under the project moves; nothing else is touched, because the sandbox may reach it through
    a declared mount and this function must not claim to know what is mounted.
    """
    root = "/home/someone/world"
    assert M._to_sandbox(root + "/bin/tool", root) == "/project/bin/tool"
    assert M._to_sandbox("/usr/bin/python3", root) == "/usr/bin/python3"
    assert M._to_sandbox("plain_argument", root) == "plain_argument"


def test_state_is_pointed_at_the_persistent_mount_not_the_tmpfs() -> None:
    """A measured defect, kept as a test. `/work` is a tmpfs discarded after every action, so a stateful
    program that writes there does its work correctly and the loop can never see an effect -- three
    successful steps, a real state change, and `GAVE_UP` in the same run. `/project` persists.

    This is why a multi-step task is possible at all, and it is a property of `confine_v1` that was
    verified by writing into `/project` from inside the sandbox and reading it back from the host.
    """
    overrides = M.sandbox_state("LEDGER_STATE")
    assert overrides["LEDGER_STATE"].startswith("/project/")
    assert "/work/" not in overrides["LEDGER_STATE"]


def test_a_relative_goal_plans_the_same_from_any_directory() -> None:
    """A planner whose answer depends on the caller's cwd is not a planner.

    Measured 2026-11-23: `./bin/linear: create ...` planned correctly when the process happened to sit in
    the programs directory and returned `NO_OPERATION_IN_THIS_DOCUMENT` when it did not -- same goal, same
    document, same code, different answer. The program path is now resolved before the document is read.
    """
    M._PROBE_ROOTS.clear()
    M._PROBE_ROOTS.append(str(_ROOT / "canonical/tests/programs"))
    try:
        plan = M.plan_from_documents('./bin/linear: create an issue in the team "Platform" titled "alpha"')
        assert plan["act"] is not None, plan
        assert [str(a) for a in plan["act"][1:]] == ["issue", "create", "--team", "Platform",
                                                     "--title", "alpha"]
    finally:
        M._PROBE_ROOTS.clear()


# ----------------------------------------------------------------------------------------------------
# How far the no-model loop actually reaches, measured on three unrelated programs.
# ----------------------------------------------------------------------------------------------------

def test_three_unrelated_programs_reach_a_correct_state_in_one_step(tmp_path: pathlib.Path) -> None:
    """THE HONEST REACH. Not "it works": three programs with three different state conventions, each
    driven to `DONE` in one step, each judged by reading the state file from disk.

    What is filled by the mechanism: the command (documentation), the confinement (confine_v1), the path
    translation (sandbox). What the caller supplies: the goal, and the judgement of success. The last one
    is deliberate -- `solve_v1` says judgement belongs to whoever owns the goal, and a harness that
    invented it would be deciding when someone else's task is finished.
    """
    for program, goal_text, state_name, must_contain in (
        ("ledgerctl", 'add a record named "alpha" with amount "4"', ".ledgerctl-state.json", "alpha"),
        ("stockctl", 'set qty "8" for sku "B2"', ".stockctl-state.json", "B2"),
        ("linear", 'create an issue in the team "Ops" titled "fix"', ".linear-state.json", "Ops"),
    ):
        world = tmp_path / program
        (world / "bin").mkdir(parents=True)
        shutil.copy(_BIN / program, world / "bin" / program)
        (world / "bin" / program).chmod(0o755)

        goal = "%s: %s" % (world / "bin" / program, goal_text)
        model = M.as_solve_model(root=str(world), expect=[state_name])
        out = S.solve(goal, str(world), model=model, steps=3, learn=False)

        assert out.get("verdict") == S.DONE, (program, out.get("trace"))
        assert out.get("steps") == 1, (program, out.get("trace"))

        written = [p for p in world.rglob("*") if p.is_file() and state_name in p.name]
        assert written, "%s wrote no state at %s" % (program, state_name)
        assert must_contain in written[0].read_text(), written[0].read_text()


def test_a_goal_that_states_no_value_does_not_invent_one(tmp_path: pathlib.Path) -> None:
    """`set the qty for sku "B2"` states no quantity, and the plan has no `--qty`.

    The program then writes its own default (0). That is the honest outcome: the mechanism does not
    manufacture a value the request never gave. Keeping this as a test stops a future change from
    "helpfully" filling the gap with a guess.
    """
    plan = M.plan_from_documents('./bin/stockctl: set the qty for sku "B2"')
    assert plan["act"] is not None, plan
    assert "--qty" not in [str(a) for a in plan["act"]], plan["act"]


# ----------------------------------------------------------------------------------------------------
# The judge the caller does not have to supply.
# ----------------------------------------------------------------------------------------------------

def test_the_environment_confirms_its_own_effect(tmp_path: pathlib.Path) -> None:
    """§A94 left one burden: "is it done". It is avoidable, because a program that writes can nearly
    always say what it wrote. `judge()` plans the program's own read and asks.

    The same command is judged twice, before and after it runs, and the two answers differ only because
    the world differs. That is what makes it a judge rather than a belief.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    plan = M.plan_from_documents(program + ': add a record named "ghost" with amount "99"')
    assert plan["act"] is not None, plan

    def run(command: str) -> dict:
        argv = [M._to_sandbox(part, str(world)) for part in command.split()]
        source = ("import subprocess, sys\n"
                  "_r = subprocess.run(%r, capture_output=True, text=True)\n"
                  "sys.stdout.write(_r.stdout)\nsys.stderr.write(_r.stderr)\n"
                  "raise SystemExit(_r.returncode)\n" % (argv,))
        result = S.act(str(world), source)
        return {"exit": result.get("exit"), "out": result.get("out") or "",
                "err": result.get("err") or ""}

    before = M.judge(program, plan["act"], "", run=run)
    assert before["verdict"] == "EFFECT_ABSENT", before
    assert before["read"][1:] == ["record", "list"], before["read"]

    run(" ".join(str(a) for a in plan["act"]))

    after = M.judge(program, plan["act"], "", run=run)
    assert after["verdict"] == "EFFECT_CONFIRMED", after
    assert "ghost" in after["found_in"] and "99" in after["found_in"]


def test_a_failed_read_never_confirms_anything(tmp_path: pathlib.Path) -> None:
    """THE WORST BUG THIS MODULE HAD, kept as a test.

    A read that crashed produced a traceback that did not contain the value, an empty `missing` list was
    read as success, and the verdict came back `EFFECT_CONFIRMED` on a program that never ran. Confirming
    on a crash is worse than no judge: everything downstream believes a thing that never happened.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    plan = M.plan_from_documents(program + ': add a record named "alpha" with amount "4"')

    def failing_read(command: str) -> dict:
        return {"exit": 1, "out": "Traceback (most recent call last): boom", "err": "boom"}

    answer = M.judge(program, plan["act"], "", run=failing_read)
    assert answer["judged"] is False, answer
    assert answer["why"] == "THE_READ_FAILED"
    assert "verdict" not in answer


def test_the_caller_can_omit_the_judgement_entirely(tmp_path: pathlib.Path) -> None:
    """`solve_v1` to `DONE` with NO `expect`: the loop asks the environment instead of the caller.

    With `expect` the caller states success in the world's terms, which §A94 noted is a burden for anyone
    who cannot. With `self_judge` the same run finishes on the environment's own answer.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    goal = program + ': add a record named "zed" with amount "6"'
    model = M.as_solve_model(root=str(world), self_judge=True)  # no expect=

    out = S.solve(goal, str(world), model=model, steps=3, learn=False)

    assert out.get("verdict") == S.DONE, out
    reasons = [call.get("why") for call in M.report(model)["calls"]]
    assert "ASKED_THE_ENVIRONMENT" in reasons, reasons
    written = [p for p in world.rglob("*") if p.is_file() and ".ledgerctl-state" in p.name]
    assert written and "zed" in written[0].read_text()


# ----------------------------------------------------------------------------------------------------
# Multi-step: the hole flagged twice and closed once.
# ----------------------------------------------------------------------------------------------------

def test_a_two_act_request_completes_BOTH_acts(tmp_path: pathlib.Path) -> None:
    """THE DEFECT THAT LOOKED LIKE SUCCESS. A request for two records planned two commands, the first
    ran, the judge confirmed it, and the loop reported DONE with the second record never created.

    Three separate bugs had to be fixed to see this, and the first hid the other two:
      1. `and` was not a step boundary, so the request was read as ONE step and planned one command with
         the second record's values as stray operands.
      2. the planner returned the first command forever instead of advancing through the request's order.
      3. the self-judge confirmed ONE act and called the GOAL complete.

    Every one of them was invisible, because the half that ran had succeeded.
    """
    world, program = _sandbox(tmp_path, "ledgerctl")
    goal = (program + ': add a record named "alpha" with amount "3"'
            ' and add a record named "alpha.beta" with amount "5"')
    model = M.as_solve_model(root=str(world), self_judge=True)

    out = S.solve(goal, str(world), model=model, steps=6, learn=False)

    assert out.get("verdict") == S.DONE, out.get("trace")
    # BOTH records, read from disk
    written = [p for p in world.rglob("*") if p.is_file() and ".ledgerctl-state" in p.name]
    assert written, "no state was written"
    state = written[0].read_text()
    assert "alpha.beta" in state, state
    assert '"amount": 5' in state, state


def test_and_splits_two_acts_but_not_two_fields_of_one_act() -> None:
    """The guard, not the connective, is what makes splitting on `and` safe.

    The guard is `_leads_with_an_act`, and it is a closed class of verbs. `add` and `set` are both in it,
    so BOTH of these split -- that is the pre-existing behaviour, confirmed unchanged at pristine HEAD
    before `and` was added, and this test records it rather than wishing it different. A half that leads
    with no act at all is what gets re-joined, and that is the case asserted here.
    """
    from canonical.runtime import require_survey_plan_v1 as R

    two = R.sentences_of('add a record named "a" with amount "1" and add a record named "b" with amount "2"')
    assert len(two) == 2, two

    # a second half that names no act continues the step -- `with the owner set to "y"` is a field
    # of the create, and splitting it would cut a field off the command it belongs to
    one = R.sentences_of('create a workflow named "x" and with the owner set to "y"')
    assert len(one) == 1, one
