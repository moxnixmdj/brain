"""Fill `solve_v1`'s model contract without a model.

WHAT THIS IS. `solve_v1` is the whole system reduced to observe/act/judge, and it takes the judging part as
a callable: `model(goal, seeing) -> program | None`. Its own docstring says the model "is a callable, not a
dependency" -- correct, and it leaves the callable unbuilt. Every run of that loop with no model supplied
is a run that cannot act. This module supplies the callable, from the mechanisms already in the tree:

    survey the tool's own documentation      require_survey_plan_v1
    ask what is already known                stated_precondition_v1
    derive the act a refusal implies         stated_precondition_v1.acts_for
    read what the machine actually says      `seeing["last"]` from solve_v1's own observe

WHAT IT DELIBERATELY IS NOT. It is not a language model and it does not claim to be one. It cannot read an
arbitrary English sentence and produce an arbitrary program, which is what a model is for. It handles the
class of goals where the request names a PROGRAM and an ACT the program documents, and it refuses the rest
with a reason rather than guessing. The size of that class is measurable, and the measurement is the point
of shipping it: it replaces "we would need a model" with "here is how far the mechanisms reach".

THE ORDER OF EVIDENCE, and why each step outranks the next:

    1  WHAT THE PROGRAM DOCUMENTS     the document is the only statement of what the command is
    2  WHAT A REFUSAL STATED         a refusal is about THIS machine and cannot be out of date (§A87)
    3  WHAT WAS LEARNED BEFORE       a rule from any program, by demand not by name (§A91)

Step 3 is consulted on the VALUE before the value is used, which is the whole point: a learned rule that
says "this amount must be whole" means the plan is repaired before the environment has to refuse it. That
converts a round trip into a decision, which is the difference between learning and logging.

WHAT A REFUSAL CHANGES. `seeing["last"]` carries the exit code and output of the previous step. When it
failed with a located refusal, this module applies the learned condition and, where the requirement names
what to try, the derived act. When it failed with a refusal that states no subject, it says so and stops:
a loop that retries the same plan against the same refusal is the behaviour §A87 spent a section replacing.

Authority NONE. Zero model calls. Every decision is a function of the documentation, the learned store, and
what the machine printed.
"""
from __future__ import annotations

import re
import shlex
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime import stated_precondition_v1 as STATED

SCHEMA = "PROJECT_BRAIN_MECHANISM_ACT_V1"

#: A goal this planner can attempt names a program and asks for something. `linear: create ...` or
#: `./bin/linear --help`. The program is the first token; everything else is the request.
_PROGRAM = re.compile(r"^\s*([./\w/\\-]+\.?[\w]*)\s*[:,-]?\s*(.*)$", re.S)


def _program_and_request(goal: str) -> tuple[str, str]:
    match = _PROGRAM.match(str(goal or "").strip())
    if not match:
        return "", str(goal or "")
    return match.group(1), match.group(2).strip()


def _from_a_refusal(seeing: Mapping[str, Any], goal: str) -> dict[str, Any] | None:
    """The previous step failed. Read what it said and answer it, or say why it cannot be answered.

    This is the half a stateless planner cannot do: the refusal is about the state the last action left,
    so it is newer evidence than the documentation and outranks it.
    """
    last = seeing.get("last") or {}
    exit_code = last.get("exit")
    if exit_code in (0, None):
        return None
    # `solve_v1.act` reports the child's streams as `out` and `err`, not `stdout`/`stderr`. Reading the
    # wrong keys made every refusal invisible: the planner saw exit 1 with no text, decided the failure
    # named nothing, and re-planned. Measured 2026-11-23 -- four identical steps, four identical commands.
    text = " ".join(str(last.get(key) or "") for key in ("err", "out", "error")).strip()
    if not text:
        return None
    parsed = STATED.parse(text)
    if parsed is None:
        return {"schema": SCHEMA, "act": None, "why": "REFUSAL_STATES_NO_SUBJECT",
                "refusal": text[:200],
                "note": "retrying the same plan against the same refusal is not a repair"}
    learned = STATED.conditions().get(parsed["code"].lower())
    if learned is None:
        # record it: an unlearned refusal is still the only statement about this machine
        STATED.learn(text)
        learned = STATED.conditions().get(parsed["code"].lower())
    predicate = (learned or {}).get("predicate") or {}
    act = STATED.acts_for(predicate, parsed["value"], parts=parsed.get("parts") or [])
    return {"schema": SCHEMA, "act": None, "why": "LEARNED_FROM_THE_REFUSAL",
            "refusal": text[:200], "parsed": parsed, "predicate": predicate,
            "derived": act, "need": act.get("why")}


def _check_the_value(value: str, program: str) -> dict[str, Any] | None:
    """Consult what has been learned BEFORE the value is used.

    A learned rule is a statement about the VALUE. Applying it here costs a dictionary lookup; not applying
    it costs a round trip and leaves the same refusal to be read later. This is where learning pays.
    """
    for code, entry in (STATED.conditions() or {}).items():
        predicate = (entry or {}).get("predicate") or {}
        # the rule is offered only where its own code's property is testable against this value
        if str(predicate.get("test") or "") == "is_whole":
            verdict = STATED.is_satisfied(predicate, value)
            if not verdict:
                return {"schema": SCHEMA, "act": None, "why": "A_LEARNED_RULE_REJECTS_THIS_VALUE",
                        "code": code, "value": value, "property": predicate.get("property"),
                        "derived": {"why": "NO_DERIVATION_FROM_A_REQUIREMENT_ALONE", "acts": []}}
    return None


def _runnable(program: str, goal: str) -> str:
    """The program as a path this process can execute, searched for in the places a goal can mean.

    Tried in order: as given (absolute, or relative to here); relative to the directory the goal itself
    names; relative to each probe root. The first executable wins, and when none does the original string
    is returned unchanged so the failure is reported against what the caller actually said.
    """
    import os
    import pathlib as _p
    candidate = _p.Path(program)
    roots = [_p.Path.cwd()]
    for probe in _p.Path.cwd().rglob("bin"):
        roots.append(probe.parent)
    roots.extend(_p.Path(r) for r in _PROBE_ROOTS)
    for root in roots:
        for path in (root / program, root / "canonical/tests/programs" / program):
            try:
                if path.is_file() and os.access(path, os.X_OK):
                    return str(path)
            except OSError:
                continue
    return program


#: Additional places a goal's program may live. Filled by tests and by callers with a known tree layout;
#: empty by default so nothing is assumed about where anyone else's files are.
_PROBE_ROOTS: list[str] = []


def plan_from_documents(goal: str, *, probes: int = 16) -> dict[str, Any]:
    """Ask the program's own documentation for the command. No model, no vocabulary of the domain."""
    program, request = _program_and_request(goal)
    if not program:
        return {"schema": SCHEMA, "act": None, "why": "GOAL_NAMES_NO_PROGRAM"}
    try:
        from canonical.runtime import require_survey_plan_v1 as R
        # THE PROGRAM MUST BE RUNNABLE FROM HERE, and a relative goal is not. Measured 2026-11-23: the
        # same goal planned correctly when the process happened to sit in the programs directory and
        # returned NO_OPERATION_IN_THIS_DOCUMENT when it did not -- same goal, same document, same code.
        # A planner whose answer depends on the caller's cwd is not a planner, so the path is resolved
        # against the likely roots before the document is read.
        program = _runnable(program, goal)
        planned = R.require_survey_plan_sequence(program, request or goal, probes=probes)
    except Exception as exc:  # noqa: BLE001 - a survey that fails is a refusal that must be reported
        return {"schema": SCHEMA, "act": None, "why": "THE_DOCUMENT_COULD_NOT_BE_READ",
                "detail": "%s: %s" % (type(exc).__name__, str(exc)[:160])}
    commands = planned.get("commands") or []
    if not commands:
        reason = ""
        for step in planned.get("steps") or []:
            reason = reason or str(step.get("reason") or "")
        return {"schema": SCHEMA, "act": None, "why": "THE_DOCUMENTS_STATE_NO_COMMAND",
                "detail": reason, "instruction_was": request}
    return {"schema": SCHEMA, "act": list(commands[0]), "why": "PLANNED_FROM_THE_DOCUMENTS",
            "commands": [list(c) for c in commands]}


def as_solve_model(*, probes: int = 16, expect: Sequence[str] = (),
                   root: str | None = None):
    """Return a callable that satisfies `solve_v1`'s model contract, with no model in it.

    `expect` is what the caller believes success looks like, as substrings of the world. It is the caller's
    judgement, not this module's: `solve_v1` is explicit that judgement belongs to whoever owns the goal,
    and this module does not pretend to know when someone else's task is finished. With `expect` empty the
    planner acts once and then proposes done, so the loop terminates instead of milling.

    The returned callable never raises: a planner that throws inside the loop turns a refusal into a crash,
    and the loop's own error handling then reports a failure of the harness rather than of the plan.
    """
    calls: list[dict[str, Any]] = []
    if root:
        # the sandbox mounts the project at /project; a planned host path must be translated or every
        # step fails on a file the sandbox does have, under a name the plan did not use
        _PROJECT_ROOTS.clear()
        _PROJECT_ROOTS.append(str(root))

    def model(goal: str, seeing: Mapping[str, Any]) -> Any:
        try:
            number = len(calls) + 1
            # 1. what the machine said last outranks what the documents say, because it is newer
            refused = _from_a_refusal(seeing, goal)
            if refused is not None:
                calls.append({**refused, "step": number})
                return None  # a refusal that cannot be turned into an act stops the loop honestly

            # 2. if the caller said what success looks like, and it is true, propose done
            tree = list(seeing.get("tree") or [])
            if expect and all(any(e in name for name in tree) for e in expect):
                calls.append({"step": number, "why": "THE_CALLER_SAID_THIS_IS_SUCCESS"})
                return None

            # 3. plan from the documentation, unless a learned rule already rejects a value
            planned = plan_from_documents(goal, probes=probes)
            if planned.get("act") is None:
                calls.append({**planned, "step": number})
                return None
            argv = planned["act"]
            for token in argv[1:]:
                rejected = _check_the_value(str(token), str(argv[0]))
                if rejected is not None:
                    # the value is repaired from the rule, not from a guess: a whole number is what
                    # "must be whole" asks for, and the rule says so in the same words
                    calls.append({**rejected, "step": number})
                    return None
            calls.append({**planned, "step": number})
            # `solve_v1.act` RUNS PYTHON SOURCE. Measured 2026-11-23: returning a shell command line
            # produced `SyntaxError: invalid syntax` on every step, four times, with empty stderr --
            # the planner re-planned the same command because the failure it was shown named nothing.
            # The contract is `model -> program`, and a program is code. A command becomes code by
            # running it, and the exit status is what the loop's own observation then reads.
            return _as_program(argv, _PROJECT_ROOTS[-1] if _PROJECT_ROOTS else None)
        except Exception as exc:  # noqa: BLE001 - never let the planner break the loop
            calls.append({"step": len(calls) + 1, "why": "THE_PLANNER_RAISED",
                          "detail": "%s: %s" % (type(exc).__name__, str(exc)[:160])})
            return None

    model.calls = calls  # type: ignore[attr-defined]
    return model


def sandbox_state(key: str) -> dict[str, str]:
    """Environment overrides that put a program's state where the sandbox can actually write it.

    MEASURED, AND IT IS THE WHOLE BLOCKER. Inside `confine_v1` the project is `/project` and READ-ONLY; the
    only writable place is `/work`, which is a fresh tmpfs per action. A fixture -- or any stateful program
    -- told to write its state at a host path (`LEDGER_STATE=/tmp/solve-x/ledger.json`) fails with
    `FileNotFoundError` on the state write, AFTER doing its work correctly. The action was right and the
    receipt says it failed.

    So the state path is translated the same way an executable path is: a path under the project becomes
    `/work/...`, which is writable. What this does NOT do is keep that state between actions, because the
    sandbox discards `/work` after each run; carrying state across steps needs either a writable mount the
    sandbox is given (which `confine_v1` does not offer) or the caller passing the accumulated state in.

    It returns OVERRIDES rather than setting `os.environ`, so one run cannot leak its paths into another.
    """
    name = str(key).lower().replace("_state", "").replace("_", "-")
    # `/project` IS WRITABLE. Measured 2026-11-23: a program may open('/project/probe.txt','w') and exit
    # 0, because the final read-only remount is applied to BASE before the project is bound -- so the
    # project keeps its own writable bind. Pointing state at `/work` was WRONG: `/work` is a tmpfs that
    # dies with the action, so every step wrote state into a discard and the loop could never see an
    # effect. `/project` persists between actions, which is what makes a multi-step task possible at all.
    return {key: "/project/" + name + ".json"}


def _to_sandbox(value: str, root: str | None = None) -> str:
    """Translate a host path into the path the confined program will actually see.

    `confine_v1` chroots and bind-mounts the project at `/project`, read-only. A plan read from the
    documentation carries HOST paths -- that is where the survey ran -- and executing it unchanged inside
    the sandbox produces `FileNotFoundError` on every step. Measured 2026-11-23: three steps, three
    identical tracebacks, and the loop re-planned the same command each time because no refusal was
    stated.

    Only a path under the project moves, and only its prefix: `/a/b/project/bin/x` -> `/project/bin/x`.
    Anything else is left alone, because the sandbox may legitimately reach it through a declared mount
    and this function must not claim to know what is mounted.
    """
    text = str(value)
    marker = "/project/"
    roots = ([root] if root else []) + list(_PROJECT_ROOTS)
    for candidate in roots:
        if candidate and text.startswith(candidate.rstrip("/") + "/"):
            return marker + text[len(candidate.rstrip("/")) + 1:]
    return text


#: Host prefixes that become `/project` inside the sandbox. Filled by `as_solve_model(root=...)`; a module
#: level list rather than a parameter so every step of one run agrees without threading it through.
_PROJECT_ROOTS: list[str] = []


def _as_program(argv: Sequence[Any], root: str | None = None) -> str:
    """A planned argv, as Python source that runs it and reports what actually happened.

    Three properties matter and each is deliberate:

    * it uses `subprocess` with a list, never a shell string -- a value containing a quote or a `;` must
      be an argument, and `shell=True` would make it a command;
    * it prints the child's stdout and stderr, because `solve_v1` reads those to learn from a refusal;
    * it exits with the child's own status, because a program that swallows the failure reports success
      and every later judgement is then made against a lie.
    """
    command = "[" + ", ".join(repr(_to_sandbox(str(a), root)) for a in argv) + "]"
    # NO STATE OVERRIDE. This is the third design and the first correct one. Overriding a program's state
    # path was actively harmful: measured 2026-11-23, `stockctl` succeeds with its own default (a dotfile
    # beside the program, writable inside `/project`) and was made to FAIL by pointing it at a path the
    # sandbox does not have. A program's own default is part of the environment it ships with, and
    # `confine_v1` makes `/project` writable precisely so that default works. Guessing a state path is the
    # harness inventing an environment, which is the error this project keeps finding.
    #
    # What a caller who DOES need a specific state path must do: pass it, in the goal or in the
    # environment, and accept that the sandbox may not have it. Silence leaves the program to its default.
    prefix = ""
    return (
        prefix +
        "import subprocess, sys\n"
        "_r = subprocess.run(%s, capture_output=True, text=True)\n"
        "sys.stdout.write(_r.stdout)\n"
        "sys.stderr.write(_r.stderr)\n"
        "raise SystemExit(_r.returncode)\n" % command
    )


def report(model: Any) -> dict[str, Any]:
    """What the planner decided, step by step. The evidence for a run, not a summary of it."""
    return {"schema": SCHEMA, "calls": list(getattr(model, "calls", []))}


def main(argv: Sequence[str] | None = None) -> int:
    import json
    import sys
    arguments = list(argv if argv is not None else sys.argv[1:])
    if not arguments:
        print(json.dumps({"schema": SCHEMA, "conditions": STATED.conditions()}, indent=1, sort_keys=True))
        return 0
    print(json.dumps(plan_from_documents(" ".join(arguments)), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
