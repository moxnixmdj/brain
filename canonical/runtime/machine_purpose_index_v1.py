"""THE MACHINE AS A KNOWLEDGE SOURCE THAT CANNOT BE WRONG, BECAUSE IT IS ASKED.

This module answers exactly one question: a sentence states a GOAL and no COMMAND -- which command
does THIS machine actually run for it?

It used to also build an index of every program's stated purpose and documented flags, and to read a
flag out of a program's manual by matching the sentence's words against the gloss. That was measured
2026-11-22 and it invented a command three times in one round:

    "audit python source structure ..."       -> python -I   (gloss: "isolate ... environment")
    "check the python version and write ..."  -> python -B   (gloss: "don't write .pyc files")
    "check the python version"                -> python -q   (gloss: "don't print version ...")

It also took 24.5 s to index 856 programs and got the stated purpose wrong for `dpkg`, `python3`,
`git` and `pip3`. None of it was on the path that works, so all of it is gone.

What remains needs no prediction, and that is the whole point. `--version` and `--help` are queries
every program answers the same way, so the machine can be ASKED rather than modelled, and an answer
that came back is not a guess:

  * WHAT IS A PROGRAM: only `shutil.which` decides, on this machine, at this moment.
  * WHAT TO ASK IT: the sentence's own words, plus the closed English idioms for asking for
    instructions ("how to use tar" asks for tar's help though no word says "help").
  * WHETHER THAT WORKED: the argv is RUN before it is returned, so `ok` is evidence, not belief.

A wrong guess does not survive that last step, because a wrong guess does not answer. A refusal is
visible; an invention is not -- which is why this module refuses far more often than it answers.
"""

import re
import shutil
import subprocess
from typing import Any

SCHEMA = "MACHINE_ANSWERS_WHEN_ASKED_V1"

# A QUERY EVERY PROGRAM ANSWERS THE SAME WAY.
#
# These are not flags read off one program's manual -- that is what invented `python -I` and
# `python -q`. They are the two questions a Unix program is expected to answer about itself, and the
# machine either answers or it does not, which is checked by running it.
_UNIVERSAL_QUERIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("--version", ("version", "versions", "release", "build")),
    ("--help", ("help", "usage", "options", "flags", "syntax", "manual", "documentation", "docs")),
)

# PHRASES ARE NOT WORDS. "how to use tar" asks for tar's help, and the sentence contains no word
# that says "help" -- matching whole words alone refused it, while `tar --help` answers it exactly
# ("Usage: tar [OPTION...] [FILE]..." then what tar does). These are closed English idioms for
# asking for instructions, so they belong to the grammar of the question, not to any subject matter.
_PHRASE_QUERIES: tuple[tuple[str, str], ...] = (
    ("how to use", "--help"),
    ("how do i use", "--help"),
    ("how do you use", "--help"),
    ("how can i use", "--help"),
    ("how to run", "--help"),
    ("how do i run", "--help"),
    ("instructions for", "--help"),
    ("documentation for", "--help"),
    ("docs for", "--help"),
    ("manual for", "--help"),
)

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_.+-]{1,}")


def _program_named_in(sentence: str) -> str | None:
    """The first word of the sentence that is a program ON THIS MACHINE. Never a stored name.

    `shutil.which` is the only authority. A word that looks like a program but is not installed
    here is not a program here, and nothing is assumed to be present because it usually is.
    """
    for word in _WORD.findall(str(sentence or "")):
        low = word.lower()
        for candidate in (low, (low + "3") if low in ("python", "pip") else low):
            if shutil.which(candidate):
                return candidate
    return None


def _universal_query_for(sentence: str) -> str | None:
    """Which universal query the sentence asks for, decided by its own words and idioms."""
    lowered = " ".join(str(sentence or "").lower().split())
    for phrase, query in _PHRASE_QUERIES:
        if phrase in lowered:
            return query
    words = {w.lower() for w in _WORD.findall(str(sentence or ""))}
    for query, triggers in _UNIVERSAL_QUERIES:
        if words & set(triggers):
            return query
    return None


def derive_argv(sentence: str) -> dict[str, Any]:
    """The command this machine ANSWERS for the request, or the reason there is none.

    The returned argv has been run: `ok` is true only because it exited 0 and printed something on
    this machine, at this moment. Nothing is predicted, so nothing can be predicted wrongly. The
    first line of what the program printed comes back as `answer` -- it is the machine's own words,
    not a stored fact.
    """
    program = _program_named_in(sentence)
    if program is None:
        return {"schema": SCHEMA, "ok": False, "reason": "NO_PROGRAM_NAMED_IN_THE_SENTENCE",
                "authority": "shutil.which"}
    query = _universal_query_for(sentence)
    if query is None:
        return {"schema": SCHEMA, "ok": False, "reason": "NO_UNIVERSAL_QUERY_ANSWERS_THE_WORDS",
                "program": program, "authority": "THE_SENTENCE_ITSELF"}
    argv = [program, query]
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=20)
    except Exception as exc:  # noqa: BLE001 - a program that cannot be asked has no answer
        return {"schema": SCHEMA, "ok": False,
                "reason": "THE_PROGRAM_DID_NOT_RUN:" + type(exc).__name__,
                "program": program, "argv": argv}
    out = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace").strip()
    if proc.returncode != 0 or not out:
        return {"schema": SCHEMA, "ok": False, "reason": "THE_PROGRAM_DID_NOT_ANSWER",
                "program": program, "argv": argv, "exit_code": proc.returncode}
    return {"schema": SCHEMA, "ok": True, "argv": argv, "program": program, "query": query,
            "answer": out.splitlines()[0][:200],
            "authority": "THE_PROGRAM_ON_THIS_MACHINE_ANSWERED_WHEN_ASKED",
            "verified_by_running": True, "stored_world_facts": 0, "network_used": False}
