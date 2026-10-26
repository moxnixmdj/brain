"""Run a pipe of argvs as one governed operation.

Why this module exists
----------------------
Real work on a computer is almost never one program. "How many different
lines are in this file" is ``sort --unique | wc --lines``: no single
program answers it, and a machine that can only run one thing at a time
cannot answer it at all.

The obvious way to get composition is to hand a shell a string. That is
what a vendored agent harness does, and it is why such a harness cannot be
put behind this brain's gates: **a shell string cannot be allowlisted,
cannot be promised, and cannot be postcondition-checked.** ``"sort f | wc
-l"`` and ``"sort f; rm -rf ~"`` differ by two characters and by nothing
else that a validator can see.

An argv list is the opposite. Every program in it can be checked against
an allowlist, every element is a string a validator can read, and the
whole chain's effect on disk is computable from the parts. So composition
here is *N argvs piped together*, never a string handed to a shell — and
the pipe is built with ``Popen(stdin=previous.stdout)``, which needs no
shell to exist.

Fail closed
-----------
A malformed chain returns ``(None, b"")`` rather than running part of it.
"Which lines did you run?" must never have the answer "the first two of
the four you gave me".
"""

from __future__ import annotations

import subprocess
import threading
from typing import Any, Sequence

# A chain longer than this is not a measurement, it is a program. The bound
# keeps a runaway composition from outliving the question that asked for it.
MAX_STAGES = 8
DEFAULT_MAX_BYTES = 1 << 16


def reap(proc: subprocess.Popen, worker: Any,
         also: Sequence[subprocess.Popen] = ()) -> int:
    """The exit status of a command that has been read on a deadline.

    Poll() answers None both for "still running" and for "finished but not
    yet reaped", and those are opposite things: one must be killed, the
    other must be believed. Conflating them threw away perfectly good
    answers -- the same command scored 0 on one run and None on the next,
    so a correct measurement was skipped depending on nothing but timing.

    So it is waited for briefly. A command that has already finished is
    simply reaped and its true status returned; only one that is genuinely
    still running, or still talking, is killed.
    """
    code = proc.poll()
    if code is None:
        try:
            code = proc.wait(timeout=0.25)
        except Exception:  # noqa: BLE001 - still running
            code = None
    if code is None or worker.is_alive():
        for target in tuple(also) + (proc,):
            try:
                target.kill()
            except Exception:  # noqa: BLE001
                pass
        for target in tuple(also) + (proc,):
            try:
                target.wait(timeout=2)
            except Exception:  # noqa: BLE001
                pass
        return -9
    return int(code)


def _normalise(argvs: Sequence[Sequence[Any]]) -> list[list[str]] | None:
    """Every stage a non-empty list of elements, or None if the chain is bad.

    Accepted elements are strings and integers, and integers are returned as
    strings. That is not leniency for its own sake -- it is what the callers
    here actually build.  Measured: the learner\'s own probe shapes include
    ``["head", "-n", 7, "probe.txt"]``, and an earlier version of this
    function applied the bound capability layer\'s strings-only rule, refused
    that shape, and turned two passing pipeline tests into
    ``OPEN__NOTHING_MEASURED_IT``.  The capability layer governs what a
    SENTENCE may ask for; this governs what may be EXECUTED, and the two are
    not the same list.  Normalising to str here means everything downstream
    still sees a chain of strings, which is the property governance needs.

    Rejected: an empty chain, an empty stage, a stage count over MAX_STAGES,
    None, and anything else that is not a string or an int.

    An empty STRING is accepted, and that is measured rather than assumed.
    The learner builds shapes like ``["sort", "-d", "", "probe.txt"]`` -- a
    flag that takes an argument, given an empty one because the sentence
    stated no pattern.  Refusing those turned fourteen of the probe shapes
    from ``(0, b"0\\n")`` into ``(None, b"")`` and two passing pipeline tests
    into ``OPEN__NOTHING_MEASURED_IT``.  Whether an empty argument produces
    a USEFUL measurement is the learner's question to answer by comparing
    the output against a file built to hold 7 of the thing; it is not this
    function's to pre-judge.  What this function guarantees is narrower and
    still worth having: nothing that is not a readable string reaches exec.
    """
    if not argvs or len(argvs) > MAX_STAGES:
        return None
    out: list[list[str]] = []
    for argv in argvs:
        if not argv:
            return None
        stage: list[str] = []
        for part in argv:
            if isinstance(part, str):
                stage.append(part)
            elif isinstance(part, int) and not isinstance(part, bool):
                stage.append(str(part))
            else:
                return None
        out.append(stage)
    return out


def run_stages(argvs: Sequence[Sequence[str]], cwd: str,
               timeout: float = 5.0,
               max_bytes: int = DEFAULT_MAX_BYTES
               ) -> tuple[int | None, bytes]:
    """Run N commands, each fed by the one before it.

    Returns the exit status of the LAST stage and at most ``max_bytes`` of
    what it printed. Bounded for the same reason a single command is: a
    program in the middle of a pipe that never stops talking takes the
    caller down just as surely as one on its own, and it does it silently,
    with no exception and no traceback.
    """
    stages = _normalise(argvs)
    if stages is None:
        return None, b""
    procs: list[subprocess.Popen] = []
    previous: subprocess.Popen | None = None
    try:
        for argv in stages:
            proc = subprocess.Popen(
                argv, cwd=str(cwd),
                # The first stage reads nothing: a pipe's head must not hang
                # waiting on a terminal that does not exist.
                stdin=(previous.stdout if previous is not None
                       else subprocess.DEVNULL),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if previous is not None:
                try:
                    # Only the next reader may hold this open, or the writer
                    # is never told its reader has gone and never sees EOF.
                    previous.stdout.close()
                except Exception:  # noqa: BLE001
                    pass
            procs.append(proc)
            previous = proc
    except Exception:  # noqa: BLE001 - a stage that will not start
        for target in procs:
            try:
                target.kill()
            except Exception:  # noqa: BLE001
                pass
        return None, b""

    final = procs[-1]
    buf = bytearray()

    def drain() -> None:
        try:
            while len(buf) < max_bytes:
                chunk = final.stdout.read(4096)
                if not chunk:
                    break
                buf.extend(chunk)
        except Exception:  # noqa: BLE001
            pass

    worker = threading.Thread(target=drain, daemon=True)
    worker.start()
    worker.join(timeout)
    code = reap(final, worker, also=tuple(procs[:-1]))
    try:
        final.stdout.close()
    except Exception:  # noqa: BLE001
        pass
    return code, bytes(buf[:max_bytes])
