"""Read what a command would do BEFORE doing it.

env_monster2 made the cost of acting first unrecoverable: running the task
named "report" poisoned the environment so the correct task could never
succeed. Everything needed to choose correctly was sitting in the directory
as plain text -- the oracle said what a valid report contains, and each
script said what it would write. None of it was read.

A command is not opaque. It names files that are sitting right there.

This does three things, in order:

    required_by()   read the environment's own check, and take the content
                    it demands -- the string literals it compares against
    produces()      read the scripts a command names, and take the literals
                    they would write
    choose()        prefer commands whose literals satisfy what the check
                    demands; demote the rest

Cheap, read-only, and no model. It is what a careful person does before
running something unfamiliar in a directory they have never seen: open the
file and read it.

Returns None rather than guessing when the sources say nothing usable.
"""
from __future__ import annotations

import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_LOOK_BEFORE_V1"

_SCRIPT = re.compile(r"[\w./-]+\.(?:py|sh|js|rb|pl)$")

# Literals that are noise in a check: filenames, modes, flags.
_NOISE = {"r", "w", "a", "rb", "wb", "utf-8", "utf8", "replace"}


def literals(path):
    """String literals in a file, longest first.

    Double- and single-quoted strings are scanned SEPARATELY, in code
    rather than with one regex.

    A single character class of both quote kinds let a double-quoted string
    be closed by a single-quote nested inside it. In right.py,
        print("produces: out/report.txt containing 'report rows=3'")
    matched up to the INNER quote, mangled the literal, and resumed
    scanning after it -- so the one string that mattered, "report rows=3",
    was never extracted, and the correct task was demoted alongside the
    wrong one. A closing quote has to match the opening quote.
    """
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    found = []
    for quote in ('"', "'"):
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch != quote:
                i += 1
                continue
            j = text.find(quote, i + 1)
            if j == -1:
                break
            piece = text[i + 1:j]
            if len(piece) >= 3 and "\n" not in piece:
                found.append(piece)
            i = j + 1
    return sorted({m for m in found if m.strip() and m not in _NOISE},
                  key=len, reverse=True)


def scripts_named(command: list[str], root: Path) -> list[Path]:
    """Local files a command refers to, that can be read before it runs."""
    found = []
    for tok in command:
        # A command arrives as ["sh","-c","python3 wrong.py"] -- the whole
        # command is ONE token, so the script name has to be pulled out of
        # it. Matching the token as a whole never finds anything.
        for word in str(tok).split():
            if _SCRIPT.search(word):
                p = (root / word)
                if p.is_file():
                    found.append(p)
    return found


def required_by(validator_sources: list[Path]) -> list[str]:
    """What the environment's own checks demand, read from their source.

    Prefers literals that look like required CONTENT rather than paths:
    longer, and not shaped like a file.
    """
    reqs: list[str] = []
    for src in validator_sources:
        for lit in literals(src):
            if "/" in lit or lit.endswith((".txt", ".json", ".log")):
                continue          # a path, not a content requirement
            reqs.append(lit)
    return sorted(set(reqs), key=len, reverse=True)[:12]


def produces(command: list[str], root: str) -> list[str]:
    """Literals the scripts a command names would write."""
    rootp = Path(root)
    out: list[str] = []
    for src in scripts_named(command, rootp):
        out.extend(literals(src))
    return sorted(set(out), key=len, reverse=True)


def satisfies(command: list[str], root: str, requirements: list[str]) -> bool:
    """Does this command's own source contain what the check demands?"""
    if not requirements:
        return False
    produced = produces(command, root)
    if not produced:
        return False
    joined = " ".join(produced)
    return any(r in joined for r in requirements)


def choose(commands: list[list[str]], root: str,
           validator_sources: list[Path]) -> dict:
    """Order commands by whether their source satisfies the oracle.

    Commands we could not read are left in place -- unread is not the same
    as wrong, and dropping them would blind the system to anything it
    cannot open.
    """
    reqs = required_by(validator_sources)
    if not reqs:
        return {"schema": SCHEMA, "requirements": [], "preferred": [],
                "demoted": [], "unread": [c for c in commands]}
    preferred, demoted, unread = [], [], []
    for cmd in commands:
        if not scripts_named(cmd, Path(root)):
            unread.append(cmd)
        elif satisfies(cmd, root, reqs):
            preferred.append(cmd)
        else:
            demoted.append(cmd)
    return {"schema": SCHEMA, "requirements": reqs,
            "preferred": preferred, "demoted": demoted, "unread": unread}
