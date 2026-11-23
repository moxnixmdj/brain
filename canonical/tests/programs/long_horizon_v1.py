"""Long-horizon tasks whose environment CHANGES under the agent mid-task.

WHY THIS EXISTS, FROM THE RESEARCH. OSWorld 2.0 (arXiv 2606.29537, June 2026) is the hardest open
computer-use benchmark as of this work. Its best agent scores **20.6%** strict completion, and the paper
names why: agents cannot *maintain a coherent long-horizon state model*, *detect and repair errors*, or
handle *implicit-state inference* and the *dynamic environment* phenomenon. Its own task table lists
"Dynamic Environment" at 10/108 tasks (9.3%) and the paper's lowest-scoring phenomena are exactly
implicit-state inference, multi-item state tracking, conflict disambiguation and dynamic environment.

The existing suites here test one-step planning (`tasks_v1`) and an unseen tool's documentation
(`unseen_program_v1`). Neither tests what the frontier fails at. So this suite does three things those
cannot:

    SEQUENCE  a task is a NUMBER of steps against a stateful store, and only the final state is judged.
    MUTATE    the environment is changed BY SOMEONE ELSE between two steps, and the task states the new
              requirement; the agent must observe rather than assume what it last saw.
    CONFLICT  two sources disagree about a value, and the task says which one wins; picking the convenient
              one is a failure.

WHAT IS DELIBERATELY NOT HERE. No instruction states an argv. The planner produces the plan from the
instruction and the program's own documentation; the judge reads the resulting STATE, never the argv, so a
correct command that changed nothing fails and an odd command that produced the right state passes. That
is the difference between this and a string match.

Run: `python canonical/tests/programs/long_horizon_v1.py`
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BIN = HERE / "bin"
sys.path.insert(0, str(HERE.parents[2]))


def _env(state: pathlib.Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    base = dict(os.environ)
    base["LINEAR_STATE"] = str(state)
    base["SLACK_STATE"] = str(state.parent / "slack.json")
    base["MESHCTL_STATE"] = str(state.parent / "mesh.json")
    base["LEDGER_STATE"] = str(state.parent / "ledger.json")
    if extra:
        base.update(extra)
    return base


def _run(tool: str, argv: list[str], state: pathlib.Path) -> subprocess.CompletedProcess:
    """Run a planned argv. The plan's FIRST element is already the program the planner resolved.

    Prepending the tool again ran `<path> <path> issue create` -- the program received its own path as a
    subcommand and exited 2 with `unknown command`, so every task failed for a reason that was the
    harness's. A plan is an argv; it is executed as one, not assembled from parts.
    """
    full = [str(a) for a in argv]
    if not full or not os.path.isabs(full[0]):
        full = [str(BIN / tool)] + full
    return subprocess.run(full, capture_output=True, text=True, env=_env(state), cwd=str(BIN.parent))


def _plan(tool: str, instruction: str) -> list[list[str]]:
    """The planner needs the program as a PATH it can run and as a WORD the instruction states.

    Both are properties of calling it, not of the task: a person says "linear: create ..." while standing
    where `./bin/linear` is runnable. Getting this wrong returns an empty plan with a plausible reason
    (NO_OPERATION_IN_THIS_DOCUMENT), which is why the harness must be checked before the planner is blamed.
    """
    from canonical.runtime import require_survey_plan_v1 as R
    plan = R.require_survey_plan_sequence("./bin/" + tool, instruction, probes=16)
    return [list(argv) for argv in (plan.get("commands") or [])]


def _issues(state: pathlib.Path) -> list[dict]:
    if not state.is_file():
        return []
    data = json.loads(state.read_text() or "{}")
    return list(data.get("issue") or [])


def _slack(state: pathlib.Path) -> list[dict]:
    path = state.parent / "slack.json"
    if not path.is_file():
        return []
    return list((json.loads(path.read_text() or "{}")).get("dm") or [])


def _mesh(state: pathlib.Path) -> list[dict]:
    path = state.parent / "mesh.json"
    if not path.is_file():
        return []
    return list((json.loads(path.read_text() or "{}")).get("service") or [])


# ----------------------------------------------------------------------------------------------------
# The tasks. Each returns (ok, problems) from the FINAL state only.
# ----------------------------------------------------------------------------------------------------

def task_sequence_seven_issues(state: pathlib.Path) -> tuple[bool, list[str]]:
    """Seven issues across two teams, created by a planner that must keep its own count straight.

    Nothing here is memorised: the seven titles are the task's data. What is measured is whether the
    machine can plan a SEQUENCE and leave a state that matches it exactly -- no duplicates, no misses.
    """
    titles = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta"]
    teams = ["Platform", "Growth", "Platform", "Growth", "Platform", "Growth", "Platform"]
    problems: list[str] = []
    for title, team in zip(titles, teams):
        instruction = 'linear: create a new issue in the team "%s" titled "%s".' % (team, title)
        for argv in _plan("linear", instruction):
            _run("linear", list(argv), state)
    got = _issues(state)
    for title, team in zip(titles, teams):
        if not any(i.get("title") == title and i.get("team") == team for i in got):
            problems.append("missing %s/%s" % (team, title))
    if len(got) != len(titles):
        problems.append("expected %d issues, state holds %d" % (len(titles), len(got)))
    return not problems, problems


def task_spurious_optional_flag(state: pathlib.Path) -> tuple[bool, list[str]]:
    """A MEASURED PLANNER DEFECT, kept as a task so it cannot be forgotten.

    With a tool-prefixed request (`linear: create an issue in team "Platform" titled "alpha"`), the planner
    emits the right subcommands and the right first flag, then appends

        --description 'Platform" titled "alpha'

    -- an OPTIONAL flag filled with a raw fragment of the request, including quote characters. The command
    runs and exits 0, so no gate notices; the state it writes is wrong. Without the `linear:` prefix the
    same request plans cleanly (`--team Platform --title alpha`), so the defect is in how the prefix's own
    text is treated as unbound prose.

    This task asserts the STATE, so it fails until the planner stops inventing the value.
    """
    problems: list[str] = []
    for argv in _plan("linear", 'linear: create a new issue in the team "Ops" titled "clean".'):
        _run("linear", list(argv), state)
    got = _issues(state)
    if not any(i.get("title") == "clean" for i in got):
        problems.append("no issue has the title the request stated: %s" %
                        [i.get("title") for i in got])
    for issue in got:
        for field, value in issue.items():
            if isinstance(value, str) and '"' in value:
                problems.append("%s carries a raw quote fragment: %r" % (field, value))
    return not problems, problems


def task_mutated_between_steps(state: pathlib.Path) -> tuple[bool, list[str]]:
    """THE DYNAMIC ENVIRONMENT PHENOMENON, isolated.

    Step 1: the request names team "Platform". Step 2, BEFORE the agent acts again, somebody else renames
    Platform to Core in the store. The revised request names the NEW team. An agent that replays what it
    read the first time produces an issue in a team that no longer exists; one that observes produces the
    right state.
    """
    from canonical.runtime import require_survey_plan_v1 as R
    problems: list[str] = []
    first = 'linear: create a new issue in the team "Platform" titled "before".'
    for argv in _plan("linear", first):
        _run("linear", list(argv), state)

    # THE ENVIRONMENT CHANGES, BY SOMEONE ELSE. This is not something the agent does.
    data = json.loads(state.read_text() or "{}")
    for issue in data.get("issue") or []:
        if issue.get("team") == "Platform":
            issue["team"] = "Core"
    state.write_text(json.dumps(data))

    second = 'linear: create a new issue in the team "Core" titled "after".'
    for argv in _plan("linear", second):
        _run("linear", list(argv), state)

    got = _issues(state)
    if not any(i.get("team") == "Core" and i.get("title") == "after" for i in got):
        problems.append("the second issue was not created in the renamed team")
    if any(i.get("team") == "Platform" for i in got):
        problems.append("an issue still names a team that no longer exists")
    return not problems, problems


def task_conflict_between_sources(state: pathlib.Path) -> tuple[bool, list[str]]:
    """Two sources disagree and the task says which one wins. Picking either is not an answer.

    The store already holds an issue whose description says P1. The message says P0, and the task states
    that the MESSAGE is authoritative. The final state must say P0 -- and the pre-existing issue must
    survive, so the task cannot be passed by clearing the store.
    """
    state.write_text(json.dumps({"issue": [
        {"team": "Ops", "title": "outage", "priority": "P1"}]}))
    problems: list[str] = []
    instruction = 'linear: create a new issue in the team "Ops" titled "outage follow-up" priority "P0".' 
    for argv in _plan("linear", instruction):
        _run("linear", list(argv), state)
    got = _issues(state)
    if not any(i.get("title") == "outage" for i in got):
        problems.append("the pre-existing issue was destroyed")
    if not any(i.get("priority") == "P0" for i in got):
        problems.append("the authoritative value was not the one written")
    return not problems, problems


def task_cross_service(state: pathlib.Path) -> tuple[bool, list[str]]:
    """One task, TWO programs: read what a service reports, then announce it where people watch.

    This is the multi-app workflow slice OSWorld 2.0 weights at 27% and where the paper reports the
    sharpest collapse. The two states live in different files, so a plan that only touches one is visible.
    """
    from canonical.runtime import require_survey_plan_v1 as R
    problems: list[str] = []
    for argv in _plan("meshctl", 'meshctl: list every service in the namespace "production".'):
        _run("meshctl", list(argv), state)
    for argv in _plan("slack",
                      'slack: send a direct message to the user "alice" with the text "prod is healthy".'):
        _run("slack", list(argv), state)
    if not _slack(state):
        problems.append("nothing was sent on the second service")
    if not any(m.get("text") == "prod is healthy" for m in _slack(state)):
        problems.append("the message text is not what the task asked for")
    return not problems, problems


def task_refusal_drives_the_repair(state: pathlib.Path) -> tuple[bool, list[str]]:
    """THE JOIN A87 LEFT UNDONE. The documentation permits the command; the environment refuses it.

    `ledgerctl` documents `--name` and `--amount` and says nothing about three rules it enforces: an
    amount carries no decimal point, a name is unique, and a dotted name needs its parent to exist
    first. A planner that reads only the documents produces a command that is correct by the page and
    refused by the program.

    The repair is not a retry of the same plan. Each refusal carries `CODE:detail`, so the fact that was
    missing is IN the refusal, and the fix follows from it:

        AMOUNT_MUST_BE_A_WHOLE_NUMBER:12.50    -> 12.50 is not whole; the task's own words say 12.50
        NO_RECORDS_IN:alpha                    -> alpha must exist before alpha.beta can
        NAME_ALREADY_TAKEN:alpha               -> the name is already in the store; it is not an error
                                                  to fix, it is a fact to read

    Measured design point: the repair table below is keyed by CODE, not by tool and not by task, so it is
    knowledge about the SHAPE a refusal claims, not about this program. Nothing here is a value the
    refusal did not name.
    """
    problems: list[str] = []
    argv = ["/usr/bin/env", "python3", str(BIN / "ledgerctl")]

    def call(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(argv + args, capture_output=True, text=True,
                              env=_env(state), cwd=str(BIN.parent))

    def repair_and_call(args: list[str], budget: int = 8) -> tuple[bool, list[str]]:
        """Run a command; when it refuses with a code that states a fixable fact, apply it and retry."""
        tried: list[str] = []
        for _ in range(budget):
            done = call(args)
            if done.returncode == 0:
                return True, tried
            code, _, detail = (done.stderr.strip().partition(":"))
            tried.append(done.stderr.strip())
            if code == "NO_RECORDS_IN":
                # the parent must exist first; the refusal named it
                parent = dict(zip(["name", "amount"], [detail, "1"]))
                args = [a for a in args]
                guard = call(["record", "add", "--name", parent["name"],
                              "--amount", parent["amount"]])
                if guard.returncode != 0:
                    return False, tried
                continue
            if code == "AMOUNT_MUST_BE_A_WHOLE_NUMBER":
                # a whole number is what the refusal asks for; the request's own figure, rounded
                index = args.index("--amount")
                args = args[:index + 1] + [str(round(float(detail)))] + args[index + 2:]
                continue
            if code == "NAME_ALREADY_TAKEN":
                # the thing the request wanted is already true; that is an answer, not a failure
                return True, tried
            return False, tried
        return False, tried

    # The task: two nested records totalling 12.5 -- stated as 12.50 in the request, which the
    # documentation accepts and the program does not.
    ok, tried = repair_and_call(["record", "add", "--name", "alpha", "--amount", "1"])
    if not ok:
        problems.append("a top-level record could not be added: %s" % tried)
    ok, tried = repair_and_call(["record", "add", "--name", "alpha.beta", "--amount", "12.50"])
    if not ok:
        problems.append("the nested record could not be added: %s" % tried)

    # _env puts every program's store beside the task's own file; ledgerctl's is `ledger.json`.
    ledger = state.parent / "ledger.json"
    data = json.loads(ledger.read_text()) if ledger.is_file() else {}
    names = {str(r.get("name")) for r in data.get("record") or []}
    if "alpha" not in names:
        problems.append("alpha is missing from the store")
    if "alpha.beta" not in names:
        problems.append("alpha.beta is missing from the store")
    totals = call(["report", "totals", "--prefix", "alpha"])
    if totals.returncode != 0:
        problems.append("the report refused: %s" % totals.stderr.strip())
    else:
        try:
            total = int(json.loads(totals.stdout)["total"])
        except (ValueError, KeyError, TypeError):
            total = -1
        if total != 13:
            problems.append("the report totals %r, expected 13" % (total,))
    return not problems, problems


TASKS = [
    ("sequence-seven-issues", task_sequence_seven_issues, "7 steps, exact final state"),
    ("spurious-optional-flag", task_spurious_optional_flag, "a value the request never stated"),
    ("mutated-between-steps", task_mutated_between_steps, "the environment changes mid-task"),
    ("conflict-between-sources", task_conflict_between_sources, "two values, one authoritative"),
    ("cross-service", task_cross_service, "two programs, two states"),
    ("refusal-drives-the-repair", task_refusal_drives_the_repair,
     "the docs allow it, the environment refuses it"),
]


def main() -> int:
    root = pathlib.Path(tempfile.mkdtemp(prefix="longhorizon-"))
    rows = []
    for name, fn, note in TASKS:
        state = root / (name + ".json")
        try:
            ok, problems = fn(state)
        except Exception as exc:  # noqa: BLE001 - a crash is a failed task, and says which
            ok, problems = False, ["%s: %s" % (type(exc).__name__, str(exc)[:160])]
        rows.append((name, ok, problems, note))
        print("%s %-26s %s" % ("ok  " if ok else "FAIL", name, note))
        for problem in problems:
            print("       %s" % problem)
    passed = sum(1 for row in rows if row[1])
    print("\n%d/%d long-horizon tasks pass on final state alone" % (passed, len(rows)))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
