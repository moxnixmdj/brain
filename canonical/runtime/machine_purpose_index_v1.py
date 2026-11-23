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


# A NONZERO EXIT IS NOT ALWAYS A FAILURE, AND THE PROGRAM SAYS WHICH IT IS.
#
# `grep -n TODO README.md` on a file with no TODO prints nothing and exits 1. That is grep
# reporting NO MATCH -- a true and useful answer -- and the receipt read it as a failed run:
# FAIL_CLOSED__CONFINED_RUN_NOT_VERIFIED for a command that had worked correctly. Measured
# 2026-11-22; `grep --help` states the rule itself:
#
#     Exit status is 0 if any line is selected, 1 otherwise;
#     if any error occurs and -q is not given, the exit status is 2.
#
# So the meaning of a nonzero exit is READ FROM THE PROGRAM, not assumed, exactly as `derive_argv`
# reads which query to ask. A program that documents no exit status anywhere in its help text has
# documented no exception, and a nonzero exit from it stays a failure. Nothing is hard-coded: `ls`
# documents "0 if OK" and `df`, `wc` and `find` document nothing, so only the programs that say so
# get the benefit of the doubt, and the check is per program, per machine.
_EXIT_STATUS_LINE = re.compile(r"exit\s+status", re.IGNORECASE)


def documents_a_nonzero_exit_as_a_result(program: str) -> bool:
    """True when the program's OWN help text says a nonzero exit can be a result, not an error."""
    import shutil as _shutil
    resolved = _shutil.which(str(program or ""))
    if not resolved:
        return False
    try:
        proc = subprocess.run([resolved, "--help"], capture_output=True, timeout=10)
    except Exception:  # noqa: BLE001 - a program that cannot be asked documents nothing
        return False
    text = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not _EXIT_STATUS_LINE.search(line):
            continue
        # The rule is stated on this line and the one or two that continue it.
        block = " ".join(lines[index:index + 3]).lower()
        # "1 otherwise", "nonzero", "non-zero", "1 if", ">0" -- the program saying a non-success
        # outcome is one of its normal answers.
        if re.search(r"(\b1\s+otherwise|nonzero|non-zero|\b1\s+if\b|\b2\s+if\b|>\s*0)", block):
            return True
    return False


_INSTRUMENT_MARKERS = (
    r"\busing\s+{p}\b",
    r"\bwith\s+{p}\b",
    r"\b(?:use|run)\s+{p}\s+to\b",
    r"\b(?:use|run)\s+{p}\s+(?:on|against|in|for)\b",
)


def _named_as_an_instrument(sentence: str, program: str) -> bool:
    """True when the sentence names the program as the thing to USE, not as the thing to DISCUSS.

    "use ls to list the files" -> True.  "what does ls do" -> False.  The distinction is carried by
    the marker; a bare mention is never enough, because answering a question about a program by
    running it is a different answer from the one that was asked for.
    """
    text = str(sentence or "")
    needle = re.escape(str(program or ""))
    if not needle:
        return False
    return any(re.search(pattern.format(p=needle), text, re.I) for pattern in _INSTRUMENT_MARKERS)


def _a_path_the_bare_command_would_ignore(sentence: str) -> bool:
    """True when the sentence names a file or directory that `[program]` could not be given.

    Read from the checkout this module is part of -- the same roots every other binder uses -- so a
    name is only "a path" when it actually is one here.
    """
    try:
        from pathlib import Path as _Path
        from canonical.runtime import goal_compiler as _gc
        root = _Path(__file__).resolve().parents[3]
        return bool(_gc._repo_paths(str(sentence or ""), root))
    except Exception:  # noqa: BLE001 - unreadable roots mean no evidence, so no derivation
        return True


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
        # SOME PROGRAMS ANSWER WITH NO ARGUMENT AT ALL, AND THE SENTENCE MAY HAVE ASKED FOR ONE.
        #
        # "list the files using ls" names `ls` as the INSTRUMENT, and bare `ls` is a complete command
        # on this machine -- it exits 0 and prints. Measured 2026-11-22. Refusing here for want of a
        # flag leaves a request the machine can plainly answer with no route.
        #
        # THIS IS THE DANGEROUS SHAPE, SO THE MARKER IS MEASURED, NOT GUESSED. 11 probes that name a
        # program were written down and classified by hand: 7 are sentences ABOUT the program
        # ("what does ls do", "explain how ls works", "is ls dangerous", "tell me about ls"), and
        # running the program to answer those is a regression -- it answers a question nobody asked.
        # All 7 carry no instrument marker and all 3 genuinely instrumental ones do, so the marker is
        # the whole guard: the program must be named as the thing to USE ("using X", "with X",
        # "use X to", "use X on"), never merely mentioned.
        # AND THE SENTENCE MUST NOT HAVE NAMED SOMETHING THE BARE COMMAND WOULD IGNORE.
        #
        # Measured minutes after the rule above was written, and it was a real defect: with nothing
        # in memory, "use wc on AGENTS.md" derived bare `['wc']`, which is a complete command --
        # it reads stdin and exits 0 -- so the request PASSED and answered "0 0 0". The sentence said
        # which file; the command could not see it. That is a pass whose answer is about something
        # else, which is worse than a refusal.
        #
        # A program run with no argument has no way to address a path the sentence named, so if the
        # sentence named one, this derivation does not apply and the refusal stands.
        if _named_as_an_instrument(sentence, program) and not _a_path_the_bare_command_would_ignore(sentence):
            bare = [program]
            try:
                proc = subprocess.run(bare, capture_output=True, timeout=20)
            except Exception as exc:  # noqa: BLE001 - a program that cannot be asked has no answer
                return {"schema": SCHEMA, "ok": False,
                        "reason": "THE_PROGRAM_DID_NOT_RUN:" + type(exc).__name__,
                        "program": program, "argv": bare}
            # The program's own behaviour decides whether it needed an argument: `git` bare exits 1,
            # `ls` bare exits 0 and prints. Nothing is predicted.
            if proc.returncode == 0 and proc.stdout.strip():
                # The program's own documentation travels with the result, for the same reason the
                # derivation above returns an `answer`: the words a program uses about itself are
                # evidence about what it did. "use date to tell the time" is explained by
                # `date --help`'s "Display date and time".
                try:
                    _h = subprocess.run([program, "--help"], capture_output=True, timeout=20)
                    _help = (_h.stdout or b"").decode("utf-8", "replace")[:20000]
                except Exception:  # noqa: BLE001 - a program that cannot be asked explains nothing
                    _help = ""
                return {"schema": SCHEMA, "ok": True, "program": program, "argv": bare,
                        "answer": proc.stdout.decode("utf-8", "replace").splitlines()[0][:400],
                        "documentation": _help,
                        "authority": "THE_PROGRAM_ANSWERED_WITH_NO_ARGUMENT",
                        "evidence": "ran " + " ".join(bare) + ": exit 0, "
                                    + str(len(proc.stdout)) + " bytes on stdout"}
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
