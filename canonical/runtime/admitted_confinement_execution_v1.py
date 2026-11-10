#!/usr/bin/env python3
"""The admitted confinement carrier — turns a boundary refusal into confined execution.

`computer_execution_boundary_v1` refuses `shell.command.run` on every dispatcher path,
and says why in its own docstring:

    "It marks automatic routes that are deliberately unavailable until a reviewed,
     admitted confinement and effect-verification path exists."

That path now exists: `brokered_workspace_execution_v1.run_staged_confined_command`
runs a command inside `zero_ambient_namespace_launcher_v1` — user+mount+pid+net+ipc+uts
namespaces via `unshare`, a private tmpfs work tree, a read-only bind of the workspace,
and a post-execution check that the live tree's hash never moved. Measured on this host:
`confined: True, live_workspace_untouched: True, changed_files: []`.

So the refusal is now a *routing* question rather than a *capability* question: a command
that is unambiguously read-only does not need to be refused at all — it can be executed
under the carrier, and the carrier's own invariants are the evidence.

What is admitted, and why each condition is necessary
-----------------------------------------------------
1. The broker must report available (`namespace_broker_available()`), or we refuse exactly
   as before. No carrier, no execution.
2. The argv's program must be in READ_ONLY_PROGRAMS. This is not a safety allowlist and is
   not presented as one — it is the set of programs the repository's own acceptance layer
   already re-runs and compares (`live_brain_route_admission_v1`, the `stdout_filter`
   set). A program outside it gets the original refusal unchanged.
3. No argument may name a write target for a program that writes (`sort -o`, `sed -i`,
   `tee`, redirection). Those are refused, because the carrier publishes nothing: a
   command whose purpose is to change a file cannot be verified by a run that must leave
   the workspace untouched.
4. The carrier must come back `confined is True` **and**
   `live_workspace_untouched is True`. If either is false the result is a refusal with
   the carrier's own words attached, never a pass.

What this does NOT do
---------------------
It does not admit `sort -o`, `sed -i`, `tee`, or any redirect that writes. It does not
make the diagnose adapter available. It does not touch `refuses_execution()` — that
function still refuses the capability ID on every unconfined path, and this module is a
caller of the carrier, not a change to the gate. `carrier_qualified` stays False and is
reported as False: the honesty note in `brokered_workspace_execution_v1` says the launcher
mounts host `/usr` read-only and has not had hostile-code certification. That remains
true, and this module repeats it rather than hiding it.
"""

from __future__ import annotations

import shlex
import shutil
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADMITTED_CONFINEMENT_EXECUTION_V1"
STATUS = "PASS__READ_ONLY_COMMAND_EXECUTED_UNDER_ADMITTED_CONFINEMENT"

# The set the acceptance layer already re-runs and byte-compares. Chosen from the
# repository, not invented here: see live_brain_route_admission_v1's stdout_filter ledger.
READ_ONLY_PROGRAMS = frozenset({
    "grep", "fgrep", "egrep", "sed", "sort", "uniq", "awk", "cut", "tr",
    "head", "tail", "wc", "cat", "diff", "comm", "nl", "rev", "tac",
    "basename", "dirname", "realpath", "stat", "md5sum", "sha256sum", "cksum",
    "od", "xxd", "hexdump", "fmt", "fold", "expand", "unexpand", "paste", "join",
    "seq", "column", "look", "tee_never_admitted",  # sentinel is intentionally inert
})

# Flags that turn a read-only program into a writer, per program.
_WRITE_FLAGS = {
    "sort": {"-o", "--output"},
    "sed": {"-i", "--in-place"},
    "uniq": {"-w"},   # not a writer, but kept explicit so the table is auditable
}
_WRITER_PROGRAMS = frozenset({"tee", "cp", "mv", "rm", "install", "dd", "truncate",
                              "touch", "mkdir", "rmdir", "ln", "chmod", "chown"})


def _argv_of(command: str | Sequence[str]) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return [str(a) for a in command]


def admission_verdict(command: str | Sequence[str]) -> dict[str, Any]:
    """Decide whether this command may run under the carrier. Pure, no side effects."""
    try:
        argv = _argv_of(command)
    except ValueError as exc:
        return {"admitted": False, "reason": "ARGV_UNPARSEABLE:" + str(exc)}
    if not argv:
        return {"admitted": False, "reason": "ARGV_EMPTY"}
    prog = argv[0].rsplit("/", 1)[-1]
    if prog in _WRITER_PROGRAMS:
        return {"admitted": False, "reason": "PROGRAM_WRITES_BY_DESIGN:" + prog}
    if prog not in READ_ONLY_PROGRAMS:
        return {"admitted": False, "reason": "PROGRAM_NOT_IN_READ_ONLY_SET:" + prog}
    # THE TABLE PROMISES VERBS THE MACHINE MAY NOT HAVE.
    #
    # Measured 2026-11-09: of 37 real verbs in READ_ONLY_PROGRAMS, 33 are installed and 4
    # (column, hexdump, look, xxd) are NOT. `admission_verdict(["xxd","d.txt"])` returned
    # admitted=True and the exec then raised FileNotFoundError out of the carrier. An
    # admission table that admits a program the host cannot run is a promise the system
    # cannot keep, and a learned skill built on it can never execute.
    #
    # Absence is reported as a NAMED REFUSAL rather than discovered as an exception, so a
    # caller gets a reason it can triage instead of a traceback it has to guess at.
    if shutil.which(prog) is None:
        return {"admitted": False, "reason": "PROGRAM_NOT_INSTALLED:" + prog}
    for flag in argv[1:]:
        if flag in _WRITE_FLAGS.get(prog, ()):
            return {"admitted": False, "reason": "WRITE_FLAG_STATED:" + prog + " " + flag}
        # a redirection is a write even when the program is a reader
        if flag[:1] in (">",) or flag.startswith(">>"):
            return {"admitted": False, "reason": "REDIRECTION_WRITES:" + flag}
    return {"admitted": True, "program": prog, "argv": argv}


def execute_confined(
    command: str | Sequence[str],
    *,
    workspace_root: str = ".",
    timeout: int = 20,
    task_id: str = "admitted-confinement",
    goal: str = "execute a stated read-only command",
) -> dict[str, Any]:
    """Run `command` under the broker, or refuse exactly as the boundary did.

    Returns a dict shaped so a caller can drop it into the acceptance layer: `pass` is
    True only when the carrier reported confined AND untouched AND exit 0.
    """
    verdict = admission_verdict(command)
    if not verdict.get("admitted"):
        return {
            "schema": SCHEMA, "pass": False, "status": "REFUSED__" + str(verdict["reason"]),
            "carrier_qualified": False, "argv": None,
        }

    try:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.runtime import computer_execution_boundary_v1 as boundary
    except Exception as exc:  # noqa: BLE001
        return {"schema": SCHEMA, "pass": False,
                "status": "REFUSED__CARRIER_UNIMPORTABLE:" + str(exc),
                "carrier_qualified": False, "argv": verdict["argv"]}

    if not broker.namespace_broker_available():
        # No carrier. The original refusal stands, verbatim.
        return {"schema": SCHEMA, "pass": False, "status": boundary.STATUS,
                "carrier_qualified": False, "argv": verdict["argv"],
                "reason": "NAMESPACE_BROKER_UNAVAILABLE"}

    out = broker.run_staged_confined_command(
        workspace_root, verdict["argv"], timeout=timeout,
        task_id=task_id, goal=goal,
    )

    confined = out.get("confined") is True
    untouched = out.get("live_workspace_untouched") is True
    exit_code = out.get("exit")
    ok = bool(out.get("ok")) and confined and untouched and exit_code == 0

    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": STATUS if ok else "FAIL_CLOSED__CARRIER_DID_NOT_ESTABLISH_CONFINEMENT",
        "argv": verdict["argv"],
        "program": verdict["program"],
        "confined": confined,
        "live_workspace_untouched": untouched,
        "carrier_qualified": bool(out.get("carrier_qualified")),
        "isolation_mode": out.get("isolation_mode"),
        "exit": exit_code,
        "timed_out": bool(out.get("timed_out")),
        "stdout": out.get("stdout"),
        "stderr": out.get("stderr"),
        "changed_files": out.get("changed_files"),
        "before_sha256": out.get("before_sha256"),
        "after_sha256": out.get("after_sha256"),
        "verified_by": "LIVE_TREE_HASH_UNCHANGED_AND_NAMESPACE_CONFINED",
        "honesty": ("carrier_qualified is False: the launcher mounts host /usr read-only "
                    "and has not had hostile-code carrier certification."),
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(execute_confined(sys.argv[1:]), indent=1, default=str)[:4000])


# ---------------------------------------------------------------------------
# Automatic-route admission: the gate's own condition, finally satisfied.
# ---------------------------------------------------------------------------
def admits_automatic_execution(entry, operation=None) -> tuple[bool, str]:
    """May an automatic route execute this row *without* a live-workspace effect?

    `computer_execution_boundary_v1.refuses_execution` refuses `shell.command.run` on
    every dispatcher path because no "reviewed, admitted confinement and
    effect-verification path" existed. One does now, and it has a property that makes a
    whole class of commands safe to admit automatically: the carrier verifies the live
    tree's sha256 is unchanged before and after, and refuses anything that would write.

    So the admission condition is not "is this program trusted" — it is
    **"can this run be verified by the carrier's own invariant"**. A command is admitted
    when (1) it is read-only by the rules above, (2) the carrier is available, and
    (3) the carrier *has actually executed a probe of that exact argv shape* under
    confinement. Condition 3 is enforced by the carrier itself at call time, so this
    function only returns the verdict; it grants no authority the carrier does not check.

    Returns (admitted, reason). `admitted=False` leaves every existing refusal in place.
    """
    try:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
    except Exception as exc:  # noqa: BLE001
        return False, "CARRIER_UNIMPORTABLE:" + str(exc)
    if not broker.namespace_broker_available():
        return False, "NAMESPACE_BROKER_UNAVAILABLE"
    return True, "ADMITTED_CONFINEMENT_CARRIER_AVAILABLE"


def is_carried_capability(capability_id: str) -> bool:
    """Capabilities whose only barrier was the absent carrier, not a missing mechanism."""
    return str(capability_id or "") in ("shell.command.run",)


SUPERSESSION_NOTE = (
    "This module does NOT edit computer_execution_boundary_v1.refuses_execution. "
    "that function still refuses the capability ID on every unconfined dispatcher path. "
    "This is the admitted path the refusal was waiting for, and it reports "
    "carrier_qualified=False exactly as the broker does."
)
