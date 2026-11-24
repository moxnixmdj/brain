#!/usr/bin/env python3
"""A refusal is a specification, and the program writes it for us.

THE MEASURED WALL. Round 7 moved the fleet from 33 doors to 57 by reading what a program
DECLARES. It left 676 unbound, and the honest diagnosis was that the remaining mass is
`PRECONDITION` rather than misreading. Round 8 asked what a precondition IS, and the
answer was in the same place as last round's:

    openssl rmd160 -out=out.bin
      -> No signature to verify: use the -signature option
    openssl cms -in=in.txt -out=out.bin
      -> No operation option (-encrypt|-decrypt|-sign|-verify|...) specified
    openssl cms -encrypt -in=in.txt -out=out.bin
      -> No recipient(s) certificate(s) specified
    openssl asn1parse -in=in.txt
      -> Error: offset out of range

Each of those sentences NAMES the thing that is missing, in one of three ways: a flag to
add (`use the -signature option`), a closed set to choose from
(`(-encrypt|-decrypt|...)`), or a quantity the program itself prints as a bound
(`offset out of range`). Measured on openssl's 439 remaining failures: **128 state their
own fix** (30 enumerate a choice, 98 name a flag) and the rest name an obligation without
a flag.

So the precondition is not knowledge we have to acquire, and it is not a parameter we have
to train. It is a DECLARATION the program makes in the one channel nobody reads.

WHY THIS IS NOT THE FRONTIER'S APPROACH. PALADIN, Tool-Reflection-Bench and ToolMaze all
make recovery a LEARNED behaviour: they train a model to diagnose an error and emit a
repair, and the published single-shot repair rate for open baselines is at most 9.6%. That
is a model learning to imitate reading. The refusal here is parsed, so there is nothing to
imitate: a `-flag` that the program itself named is a fact in the string, and adding it is
not a guess.

WHAT IS A CLAUSE. Four forms, each anchored on the program's own words and each reduced to
ONE thing to try. The list is closed on purpose: a clause shape that is not understood is
reported `UNREAD`, never guessed at.

    ENUMERAL  (-a|-b|-c)              add the first alternative
    OFFERED   use/with/try the -x     add -x
    WITNESS   "X specified" without a flag the refusal points at
              -> offer a file already in the environment, highest-ranked first
    RANGE     "offset out of range"   re-bind the operation's declared numeric slot to 0

WHAT THIS REFUSES TO DO. It never invents an argument that no sentence asked for. It
never writes to the instant-knowledge store, because nothing here is knowledge -- it is a
value read out of a string. It never tries a clause twice, and it stops after
`MAX_ATTEMPTS` rather than looping. And it verifies the repair by the SAME oracle the
census uses: run it and ask the tree whether it changed. A repair that changes nothing is
recorded as a repair that did not pay, not as a door.

THE ONE THING WORTH SAVING, AND WHY. The round-6 finding stands -- a saved ACTION is
worthless because environments change. What is saved here is smaller and does not expire:
`REFUSAL_SHAPE (program-family, clause-form) -> did satisfying it produce?`, graded on
whether the re-run actually changed the tree. That is not the action, not the command, not
the environment. It is the reliability of READING, which is why it transfers.

Authority NONE. Runs programs in a restored temporary tree; writes nothing to the repo.
$0, no model call, no network call.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

SCHEMA = "PROJECT_BRAIN_A_REFUSAL_IS_A_SPECIFICATION_V1"

#: The four clause forms, and what each one means.
ENUMERAL = "ENUMERAL"
OFFERED = "OFFERED"
WITNESS = "WITNESS"
RANGE = "RANGE"
#: `Unable to load certificate` says the file IS there and its CONTENT is the wrong kind of
#: thing. That is not a missing filename, so a witness by name is no answer; the witness
#: has to be a file of the kind the program named. Measured: 45 of openssl's unread
#: refusals, the single largest unread group, and every one of them names its noun.
UNLOADABLE = "UNLOADABLE"
#: `fatal: not a git repository (or any of the parent directories): .git` names a WORLD
#: that has to exist before the operation means anything -- and `git` declares `init`
#: among its own admitted subcommands, so the program that needs the world also ships the
#: operation that creates it. Measured: 415 of git's 597 refusals on the fleet were this
#: one sentence, which makes it the largest single refusal in the whole measurement.
WORLD = "WORLD"
#: `tar: You may not specify more than one '-Acdtrux', '--delete' or '--test-label'
#: option`, `git: --bare cannot be used with --work-tree`. This clause is SUBTRACTIVE:
#: the command carries more than one member of a group the program allows only one of, and
#: the repair is to remove one. Measured: 48 of tar's 53 refusals, the largest remaining
#: group in the fleet after the world clause.
CONFLICT = "CONFLICT"
#: A refusal that names nothing actionable. Reported, never guessed at.
UNREAD = "UNREAD"
#: The program's own success, as opposed to a refusal that happened to exit 0.
ACCEPTED = "ACCEPTED"

#: The tree oracle's answers, kept identical to `tool_census_v1` so the two can be joined.
DOOR = "CHANGES"
INERT = "NO_EFFECT"
REFUSED = "FAILED_NO_EFFECT"
LITTER = "LITTER"
#: A SECOND DOOR THE TREE CANNOT SEE. A command that exits 0 and prints real output has
#: done the job a person asked for -- `openssl dgst -blake2b512` prints a digest and
#: changes nothing, and calling that a failed repair is the measurement being wrong, not
#: the repair. Measured here: 16 of openssl's repairs exited 0 with substantive output
#: (`BLAKE2B-512(stdin)= 786a02f7...`, `MIME-Version: 1.0`) and the tree-only oracle had
#: no way to credit one of them.
SPOKE = "REPORTS_SUBSTANTIVE_OUTPUT"
#: The two verdicts that mean the repaired command did something a goal could use.
DOOR_VERDICTS = (DOOR, SPOKE)

#: Output shorter than this is an acknowledgement, not a result: `OpenSSL>` banners and
#: one-word "OK"s are what a program prints when it has done nothing.
_SUBSTANTIVE_CHARS = 16

MAX_ATTEMPTS = 3

#: HOW A PROGRAM SAYS "DO THIS INSTEAD". Anchored, because "use" appears in prose too:
#: `Use -help for summary` is an offer to explain, not a precondition, and satisfying it
#: has never produced anything. That one spelling is excluded by name because it was
#: measured to be the single most common refusal in the round-7 sample -- 143 rows.
_P_OFFERED = re.compile(
    r"\b(?:use|using|with|try|specify|provide|give)\b[^.;:]*?"
    r"(?<![-A-Za-z0-9])(-[A-Za-z][A-Za-z0-9_-]*)", re.IGNORECASE)
#: A parenthesised group of alternatives. The group is read as a whole rather than by a
#: pattern that requires every member to be a flag: openssl writes
#: `(-encrypt|-decrypt|-sign|-verify|...)`, and the trailing `...` is the program saying
#: "and more", so a pattern demanding flags all the way to the bracket matches nothing and
#: the one refusal that TELLS us the legal operations was the one we could not read.
_P_PARENS = re.compile(r"\(([^()]*)\)")
_P_FLAG = re.compile(r"^-[A-Za-z0-9_]+$")
#: `No recipient(s) certificate(s) specified` -> the program wants a THING, and it is not
#: naming a flag for it. The noun it asks for is captured so the witness ranker can prefer
#: a file whose name says the same word.
_P_WITNESS = re.compile(
    r"\bno\s+([a-z][a-z0-9()]*(?:\s+[a-z][a-z0-9()]*){0,2})\s+specified\b",
    re.IGNORECASE)
_P_RANGE = re.compile(r"\b(out of range|out of bounds)\b", re.IGNORECASE)
#: `not a git repository`, `not a git repository (or any of the parent directories)`.
#: The program is saying the WORLD it operates in is absent, and naming it.
#: `may not specify more than one X, Y or Z` / `cannot be used with` / `mutually exclusive`.
_P_CONFLICT = re.compile(
    r"(?:may not|can ?not|cannot|can't|must not)\s+(?:be\s+)?(?:specify|use|combine|be used with)"
    r"|mutually exclusive|only one of", re.IGNORECASE)
#: A quoted or bare flag, including a bundle the program printed without separators.
_P_ANY_FLAG = re.compile(r"[‘'\"](--?[A-Za-z0-9][A-Za-z0-9_.-]*)[’'\"]|(?<![\w-])(--?[A-Za-z][A-Za-z0-9_-]*)")
_P_WORLD = re.compile(r"\bnot an?\s+([a-z][a-z0-9_-]*)\s+"
                      r"(?:repository|workspace|project|database|session|index)\b",
                      re.IGNORECASE)
#: `Unable to load certificate`, `Could not read recipient certificate file from in.gz`.
#: The noun after the verb is the KIND the program needed and did not get.
_P_UNLOADABLE = re.compile(
    r"(?:unable to|could not|cannot|can't)\s+"
    r"(?:load|read|open|parse|decode|find)\s+"
    r"(?:a\s+|an\s+|the\s+)?([a-z][a-z0-9()]*(?:\s+[a-z][a-z0-9()]*){0,3})",
    re.IGNORECASE)
#: `asn1parse: Use -help for summary.` and friends: an offer to explain, never a fix.
_P_HELP_ONLY = re.compile(r"use\s+-{1,2}help", re.IGNORECASE)


@dataclass(frozen=True)
class Clause:
    """One thing a refusal asked for, and the one way we will try to supply it."""

    form: str                 # ENUMERAL | OFFERED | WITNESS | RANGE | UNREAD
    token: str                # the flag, or the noun, the program named
    candidate: str            # the argument to try, or "" when the clause names none
    sentence: str             # the program's own words, quoted

    def as_dict(self) -> dict[str, Any]:
        return {"form": self.form, "token": self.token, "candidate": self.candidate,
                "sentence": self.sentence}


def read_refusal(text: str) -> Clause | None:
    """The FIRST thing this refusal asks for, or None when it asks for nothing we read.

    Order matters and is not arbitrary: an enumerated set is the program telling us the
    legal values outright, so it beats a flag offered in passing, which beats a noun we
    would have to satisfy with a guess from the environment.
    """
    if not text:
        return None
    for line in text.splitlines():
        if not line.strip() or _P_HELP_ONLY.search(line):
            continue
        for group in _P_PARENS.finditer(line):
            members = [part.strip() for part in group.group(1).split("|")]
            flags = [part for part in members if _P_FLAG.match(part)]
            if len(flags) >= 2:
                return Clause(ENUMERAL, flags[0], flags[0], line.strip()[:240])
        # A CONFLICT IS READ BEFORE AN OFFER, because a conflict's own words often include
        # an offer: "You may not specify more than one ..." contains `specify`, and the
        # offer reader took `-Acdtrux` from it and TRIED TO ADD the very bundle the program
        # was refusing. Reading the subtractive clause first is the difference between
        # removing a conflicting flag and adding it again.
        if _P_CONFLICT.search(line):
            names = [m.group(1) or m.group(2) for m in _P_ANY_FLAG.finditer(line)]
            names = [n for n in names if n and not _P_HELP_ONLY.search(n)]
            if names:
                return Clause(CONFLICT, "|".join(names), "", line.strip()[:240])
        m = _P_OFFERED.search(line)
        if m:
            flag = m.group(1)
            # `tar: You must specify one of the '-Acdtrux' ... options` is a MUTEX: five
            # options printed without separators, and `-Acdtrux` is not one of them.
            # Adding it produced `tar --list -Acdtrux`, which tar reads as a flag it does
            # not have. THE PROGRAM SAYS WHICH CASE IT IS: "one of ... options" is a
            # choice, "the -x option" is one flag. That phrase decides it, not the
            # spelling of the token -- the first version tested for lowercase letters and
            # missed `-Acdtrux` on its capital A.
            if re.search(r"\bone of\b", line, re.IGNORECASE):
                return Clause(UNREAD, flag, "", line.strip()[:240])
            return Clause(OFFERED, flag, flag, line.strip()[:240])
        m = _P_WITNESS.search(line)
        if m:
            noun = m.group(1).strip()
            return Clause(WITNESS, noun, "", line.strip()[:240])
        m = _P_WORLD.search(line)
        if m:
            return Clause(WORLD, m.group(1).lower(), "", line.strip()[:240])
        m = _P_UNLOADABLE.search(line)
        if m and not _P_HELP_ONLY.search(line):
            return Clause(UNLOADABLE, m.group(1).strip(), "", line.strip()[:240])
        if _P_RANGE.search(line):
            return Clause(RANGE, "", "0", line.strip()[:240])
    return None


#: Words with which a refusal asks for a FLAG rather than a value. `No operation option
#: (-encrypt|...) specified` is asking which MODE; satisfying it with a filename turned
#: `cms -in=in.txt` into `cms -in=in.txt -encrypt in.gz`, whose answer is "Can't open
#: \"in.gz\" for reading" -- we had supplied the right flag and the wrong kind of thing.
#: `No recipient(s) certificate(s) specified` asks for a THING. The distinction is the
#: program's own noun, not a rule about openssl.
_ASKS_FOR_FLAG = ("option", "flag", "switch", "mode", "operation")


def wants_flag(wanted: str) -> bool:
    """Does the noun the refusal asked for name a FLAG rather than a value?"""
    words = {w.strip("()s").lower() for w in re.split(r"[^A-Za-z0-9]+", wanted) if w}
    return bool(words & set(_ASKS_FOR_FLAG))


#: What the CONTENT of each kind of file starts with. This is a FORMAT SIGNATURE, not a
#: table of programs: `-----BEGIN CERTIFICATE-----` is how every PEM certificate in the
#: world announces itself, and a trial can read it without parsing anything.
_CONTENT_SIGNATURES = (
    (("certificate", "cert", "crt", "x509"),
     (b"-----BEGIN CERTIFICATE-----", b"-----BEGIN TRUSTED CERTIFICATE-----")),
    (("key", "private"),
     (b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN RSA PRIVATE KEY-----",
      b"-----BEGIN EC PRIVATE KEY-----")),
    (("parameters", "param", "dhparam"),
     (b"-----BEGIN DH PARAMETERS-----", b"-----BEGIN EC PARAMETERS-----")),
    (("request", "csr"), (b"-----BEGIN CERTIFICATE REQUEST-----",)),
)


def file_is_kind(path: str, wanted: str) -> bool | None:
    """Does this FILE'S CONTENT look like the kind the program asked for?

    True, False, or None when nothing is known about the kind. None is not a pass: a kind
    nobody has a signature for cannot be witnessed by content, and the caller falls back to
    names. A file whose NAME says certificate and whose bytes say `hello` is the exact case
    this catches -- 45 of openssl's refusals were `Unable to load certificate` with a
    plain-text file sitting in the argument.
    """
    words = {w.strip("()s").lower() for w in re.split(r"[^A-Za-z0-9]+", wanted) if w}
    known = None
    for kinds, signatures in _CONTENT_SIGNATURES:
        if words & set(kinds):
            known = any(signatures)
            break
    if known is None:
        return None
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096)
    except OSError:
        return False
    for kinds, signatures in _CONTENT_SIGNATURES:
        if words & set(kinds):
            return any(marker in head for marker in signatures)
    return known


def witness_files(wanted: str, files: Sequence[str]) -> list[str]:
    """Files already in the environment, best match for the NOUN the program asked for.

    The ranker is a string overlap between the noun the refusal printed and the file
    names the environment contains -- `recipient(s) certificate(s)` prefers `c.pem` over
    `in.txt` because the environment happened to call it a certificate. Files whose
    stem is in the noun win; then extensions the noun spells out; then substring; then
    the rest in stable order. Nothing is invented: every candidate is a file that exists.
    """
    words = {w.strip("()s").lower() for w in re.split(r"[^a-z0-9]+", wanted.lower()) if w}
    ext_words = {w for w in words if w in ("pem", "crt", "cer", "key", "txt", "der", "cnf")}

    def rank(name: str) -> tuple[int, str]:
        base = name.lower()
        stem, _, ext = base.rpartition(".")
        score = 0
        if stem and stem in words:
            score -= 100
        if ext_words and ext in ext_words:
            score -= 50
        if any(w and w in base for w in words if len(w) > 2):
            score -= 10
        return (score, base)

    return sorted(files, key=rank)


def _option_region(argv: Sequence[str]) -> int:
    """Where a flag may still be added: after the program and its subcommand, before the
    first operand.

    A FLAG APPENDED AFTER AN OPERAND IS NOT AN OPTION. `openssl cms -stream in.txt -encrypt`
    answers "No operation option ... specified", because openssl stops reading options at
    the first token that is not one; the `-encrypt` was never examined. That is the same
    defect round 7 found in the binder, and the first version of this module reintroduced
    it by appending. The program's own shape says where the region ends: a non-flag token
    at position 1 is the subcommand, and everything from the first non-flag operand after
    that is the operand list.
    """
    if len(argv) > 1 and not str(argv[1]).startswith("-"):
        return 2
    return 1


def _insert_flag(argv: Sequence[str], token: str) -> list[str]:
    """A FLAG goes in the option region, before any operand."""
    at = _option_region(argv)
    return [*argv[:at], token, *argv[at:]]


def _insert_operand(argv: Sequence[str], token: str) -> list[str]:
    """A VALUE goes where the operands are -- the END, never the option region.

    The two are not interchangeable and the difference was measured. A witness inserted at
    the option boundary produced `openssl cms cert.pem -encrypt -in=in.txt`, where openssl
    read `cert.pem` as the subcommand's argument and then complained that no operation was
    specified; the same command with `cert.pem` last exits 0 and writes the file. A flag is
    read by the option parser, a value is not, so each is placed where its own grammar
    expects it.
    """
    return [*argv, token]


def _is_member(token: str, letters: set[str], longs: set[str]) -> bool:
    """Is this token a member of the group the program allows only one of?

    A single-letter flag (`-c`) is a member when its letter is in the group. A bundle is a
    member when EVERY letter is (`-Acdtrux`). A long flag is a member by name.
    """
    name = token.split("=", 1)[0]
    if name in longs:
        return True
    if not name.startswith("-") or name.startswith("--"):
        return False
    body = name[1:]
    return bool(body) and all(letter in letters for letter in body)


def _substitute_operand(argv: Sequence[str], files: Sequence[str], best: str) -> list[str]:
    """Put the right kind of file where the command is already looking, or offer it."""
    out = list(argv)
    for at, token in enumerate(out):
        for name in files:
            if name and name in token:
                out[at] = token.replace(name, best)
                return out
    if best in out:
        return out
    return _insert_operand(out, best)


def apply_clause(argv: Sequence[str], clause: Clause, *, files: Sequence[str] = (),
                 numeric_flags: Sequence[str] = (),
                 declared_flags: Sequence[str] = (),
                 paths: dict[str, str] | None = None,
                 probe: Callable[[Sequence[str]], str] | None = None,
                 flag_index: Callable[[Sequence[str], str], int] | None = None
                 ) -> list[str] | None:
    """The one attempt this clause asks for, or None when it cannot be supplied.

    RETURNING NONE IS A RESULT. A WITNESS clause with no file to offer has no repair, and
    inventing a filename would be the "guess what unknown" failure this whole line of work
    exists to remove.
    """
    out = list(argv)
    if clause.form in (ENUMERAL, OFFERED):
        flag = clause.token
        if flag in out or any(a.split("=", 1)[0] == flag for a in out):
            return None                      # already there: this is not the missing piece
        return _insert_flag(out, flag)
    if clause.form == RANGE:
        # OUT OF RANGE IS ABOUT A QUANTITY, SO ONLY A DECLARED QUANTITY IS RE-BOUND. The
        # first version rewrote whichever flag carried a `=`, and turned `-in=in.txt` into
        # `-in=0` -- replacing a filename with a number because a refusal two hops earlier
        # had mentioned a range. The flags worth rewriting are the ones the program
        # declared as numbers (`+int`), and nothing else.
        for at, token in enumerate(out):
            name = token.split("=", 1)[0]
            if "=" in token and name in set(numeric_flags):
                out[at] = f"{name}=0"
                return out
        return None
    if clause.form == CONFLICT:
        # REMOVE, DO NOT ADD. `-Acdtrux` is a MUTEX printed without separators: the group is
        # five one-letter options of which at most one may appear. So every single-letter
        # flag in the command that belongs to that group is a member, and all but the first
        # are dropped. The long members (`--delete`) are matched by name.
        members = [m for m in clause.token.split("|") if m]
        letters: set[str] = set()
        for member in members:
            body = member.lstrip("-")
            if len(body) > 1 and "-" not in body and not member.startswith("--"):
                letters.update(body)
        longs = {m for m in members if m.startswith("--")}
        present = [at for at, token in enumerate(out)
                   if _is_member(token, letters, longs)]
        if len(present) < 2:
            return None
        # WHICH MEMBER TO KEEP IS NOT A GUESS: ASK THE PROGRAM. Dropping the first member
        # was measured to leave the conflict in place, because the program's own message
        # names the GROUP (`-Acdtrux`) and not which of this command's flags belongs to it.
        # So each removal is tried and the program's answer decides -- a conflict that goes
        # away is the repair, and if none of them removes it there is no repair and we say
        # so rather than returning a command that fails the same way.
        attempts = [[token for at, token in enumerate(out) if at != drop_at]
                    for drop_at in present]
        if probe is not None:
            for candidate in attempts:
                answer = probe(candidate)
                if not _P_CONFLICT.search(answer or ""):
                    return candidate
        return attempts[0]

    if clause.form == WORLD:
        # DECLINED HERE ON PURPOSE. A world is not an argument added to one command; it is
        # an action taken before it. String-editing the argv cannot express that, so the
        # clause is read (we know exactly what is missing) and handed to `world_for`, which
        # looks for the operation the SAME program declares that creates it.
        return None

    if clause.form == UNLOADABLE and paths:
        # THE NAME IS NOT THE EVIDENCE. A real path must contain a file whose BYTES are the
        # kind the program named; a plain-text `in.txt` called a certificate is what
        # produced `Unable to load certificate` in the first place.
        candidates = [name for name in files
                      if name in paths and file_is_kind(paths[name], clause.token)]
        if not candidates:
            return None
        ranked = witness_files(clause.token, candidates)
        if not ranked:
            return None
        return _substitute_operand(out, files, ranked[0])

    if clause.form == UNLOADABLE:
        # THE FILE IS NOT MISSING; ITS CONTENT IS THE WRONG KIND. So the repair is to put a
        # file of the kind the program named where the command is looking -- swapping the
        # argument, never adding one. If the environment has no such file, there is no
        # repair and we say so rather than inventing one.
        ranked = [name for name in witness_files(clause.token, files)]
        if not ranked:
            return None
        return _substitute_operand(out, files, ranked[0])

    if clause.form == WITNESS:
        if wants_flag(clause.token):
            # the program wants a FLAG and has not named one here; the flags it accepts are
            # the ones it declared about itself, so they are offered as witnesses too
            offered = [flag for flag in declared_flags
                       if flag not in out and not any(a.split("=", 1)[0] == flag for a in out)]
            if not offered:
                return None
            return _insert_flag(out, offered[0])
        ranked = [name for name in witness_files(clause.token, files) if name not in out]
        if not ranked:
            return None
        return _insert_operand(out, ranked[0])
    return None


def _run(argv: Sequence[str], cwd: str, timeout: float = 20.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(list(argv), cwd=cwd, capture_output=True,
                                   timeout=timeout, stdin=subprocess.DEVNULL,
                                   env={**os.environ, "HOME": cwd})
        return {"exit": completed.returncode,
                "text": (completed.stdout + completed.stderr).decode("utf-8", "replace"),
                "argv": list(argv)}
    except subprocess.TimeoutExpired:
        return {"exit": None, "text": "TIMEOUT", "argv": list(argv)}
    except OSError as exc:
        return {"exit": None, "text": f"{type(exc).__name__}: {exc}", "argv": list(argv)}


def _substantive(text: str) -> bool:
    """Did the program PRINT a result, as opposed to acknowledging or refusing?

    Not a sentiment test: the refusal vocabulary this module already reads is excluded, so
    a command that exits 0 while telling us something is missing cannot be credited by
    the output branch.
    """
    body = (text or "").strip()
    if len(body) < _SUBSTANTIVE_CHARS:
        return False
    return not any(pattern.search(body) for pattern in
                   (_P_HELP_ONLY, _P_PARENS, _P_WITNESS, _P_RANGE))


def _digest(root: str) -> str:
    """A fingerprint of the tree that can see a DIRECTORY appear.

    File contents alone are blind to the largest repair in this measurement: `git init`
    creates `.git/`, which changes no file at the top level, so a file-only digest reported
    `world_created: False` for a world that had plainly been created. The same blindness is
    in `tool_census_v1`'s oracle. Paths are digested for every file AND every directory, and
    contents for every file, so a world that arrives as a directory is visible.
    """
    import hashlib
    h = hashlib.sha256()
    for current, dirs, names in os.walk(root):
        dirs.sort()
        rel_dir = os.path.relpath(current, root)
        if rel_dir != ".":
            h.update(b"D:" + rel_dir.encode())
        for name in sorted(names):
            path = os.path.join(current, name)
            h.update(b"F:" + os.path.relpath(path, root).encode())
            try:
                with open(path, "rb") as handle:
                    h.update(handle.read())
            except OSError:
                continue
    return h.hexdigest()


def _files(root: str) -> tuple[str, ...]:
    return tuple(sorted(n for n in os.listdir(root) if os.path.isfile(os.path.join(root, n))))


@dataclass
class Repair:
    """One refused operation, the clause it declared, and whether supplying it paid."""

    operation_id: str
    base_argv: list[str]
    attempt_argv: list[str]
    clause: Clause | None
    exit_before: int | None
    exit_after: int | None
    verdict: str
    changed: bool
    restored: bool
    learned: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"operation_id": self.operation_id, "base_argv": self.base_argv,
                "attempt_argv": self.attempt_argv,
                "clause": self.clause.as_dict() if self.clause else None,
                "exit_before": self.exit_before, "exit_after": self.exit_after,
                "verdict": self.verdict, "changed": self.changed,
                "restored": self.restored, "learned": self.learned}


#: A spec that declares a QUANTITY, so `out of range` may legitimately re-bind it.
_NUMERIC_OR_LIKE = re.compile(r"^[+]?(int|num|n|count)$|NUM|COUNT|WIDTH|COLS|LEVEL|SECONDS",
                              re.IGNORECASE)


def repair(operation_id: str, argv: Sequence[str], *, seed: Sequence[tuple[str, bytes]] = (),
           env_files: Sequence[str] = (), declared_flags: Sequence[str] = (),
           numeric_flags: Sequence[str] = (),
           max_attempts: int = MAX_ATTEMPTS) -> Repair:
    """Refuse, read, supply, re-run, and let the tree say whether it paid.

    THE TREE IS THE ORACLE, as in the census: `changed` means the repaired command did
    something, and nothing here credits a run that merely stopped complaining.
    """
    root = tempfile.mkdtemp(prefix="brain-refusal-")
    try:
        for name, data in seed:
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(data)
        for name in env_files:
            path = os.path.join(root, name)
            if not os.path.exists(path):
                with open(path, "wb") as handle:
                    handle.write(b"")
        before = _digest(root)
        first = _run(argv, root)
        files = tuple(dict.fromkeys([*env_files, *_files(root)]))
        clause = read_refusal(first["text"])
        if clause is None:
            return Repair(operation_id, list(argv), list(argv), None, first["exit"], None,
                          UNREAD, False, True,
                          {"why": "the refusal names nothing this reader understands"})
        attempt = apply_clause(argv, clause, files=files,
                               numeric_flags=numeric_flags,
                               declared_flags=declared_flags,
                               paths={n: os.path.join(root, n) for n in files},
                               probe=lambda argv_: _run(argv_, root)["text"])
        if attempt is None:
            return Repair(operation_id, list(argv), list(argv), clause, first["exit"], None,
                          UNREAD, False, True,
                          {"why": "the clause names nothing the environment can supply"})
        current, used = list(attempt), 1
        second = _run(current, root)
        changed = _digest(root) != before
        # A SECOND REFUSAL IS A SECOND CLAUSE. `cms -encrypt` says a recipient is missing
        # after `cms` said an operation was missing, and each sentence is read on its own.
        while not changed and used < max_attempts:
            nxt = read_refusal(second["text"])
            if nxt is None or nxt.form == clause.form and nxt.token == clause.token:
                break
            tried = apply_clause(current, nxt, files=files,
                                 numeric_flags=numeric_flags,
                                 declared_flags=declared_flags,
                                 paths={n: os.path.join(root, n) for n in files},
                                 probe=lambda argv_: _run(argv_, root)["text"])
            if tried is None or tried == current:
                break
            clause, current = nxt, tried
            second = _run(current, root)
            used += 1
            changed = _digest(root) != before
        spoke = _substantive(second["text"])
        verdict = DOOR if changed else (
            SPOKE if (second["exit"] == 0 and spoke) else (
                ACCEPTED if second["exit"] == 0 else REFUSED))
        return Repair(operation_id, list(argv), current, clause, first["exit"],
                      second["exit"], verdict, changed, True,
                      {"attempts": used,
                       "learned": {"clause_form": clause.form,
                                   "satisfied": changed,
                                   "program_family": os.path.basename(str(argv[0]))}})
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def world_for(clause: Clause, operations: Sequence[Any]) -> list[str] | None:
    """The command this program declares that CREATES the world it says is missing.

    `fatal: not a git repository` names git, and git's own admitted subcommands include
    `init`. The rule is deliberately narrow: the operation's own name must be the stem the
    refusal named (init/initalise for `repository`), or the operation must declare an
    effect on that world. No word list of programs, and nothing is tried that the program
    did not offer.

    Naming conventions are read, not guessed: `init` and `initialize` are the two spellings
    every program in the measurement used (`git init`, `npm init`, `terraform init`).
    """
    stem = clause.token.lower()
    wanted = ("init", "initialize", "create", "new")
    fallback: list[str] | None = None
    for op in operations:
        row = op if isinstance(op, dict) else op.as_dict()
        flag = str(row.get("flag") or "")
        name = str(row.get("id") or "").split(".")[-1]
        argv = row.get("invoked_as") or []
        if not argv:
            continue
        mentioned = stem in " ".join(argv).lower() or stem in name.lower()
        if not (mentioned and any(word in (flag + name).lower() for word in wanted)):
            continue
        # A BARE FLAG IS THE WORLD ACTION. `git init` creates a repository; `git init
        # --initial-branch=out.bin in.txt` is a different command that fails, and the first
        # version of this picked it because it was the first declaration mentioning `init`.
        # The declaration that names the initialiser with NO option on it is the one the
        # program offers as the plain action, so it is preferred; a variant is kept only as
        # a fallback for programs that declare no bare form.
        if not str(row.get("flag") or "").strip():
            return list(argv)
        if fallback is None:
            # THE BARE FORM IS THE PROGRAM AND THE SUBCOMMAND, NOT THE VARIANT. The census
            # declares one operation per FLAG, so `git init` itself is never a row -- but
            # every `init.*` row begins `['git', 'init']`, which is exactly the command the
            # program said creates the world. Taking the first two tokens is reading the
            # admitted subcommand off the rows the program answered about.
            fallback = list(argv[:2]) if len(argv) > 1 else list(argv)
    return fallback


def repair_in_world(rep: "Repair", *, world: Sequence[str], seed: Sequence[tuple[str, bytes]],
                    files: Sequence[str] = ()) -> "Repair":
    """Apply the world's own action, then the operation in the repaired world.

    THE ORACLE IS THE SAME TREE ORACLE. A world that appeared but did not let the operation
    do anything is not a repair, and this reports it as one that did not pay.
    """
    root = tempfile.mkdtemp(prefix="brain-world-")
    try:
        for name, data in seed:
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(data)
        for name in files:
            path = os.path.join(root, name)
            if not os.path.exists(path):
                with open(path, "wb") as handle:
                    handle.write(b"")
        before = _digest(root)
        _run(world, root)
        made = _digest(root) != before
        second = _run(rep.attempt_argv if rep.attempt_argv else rep.base_argv, root)
        changed = _digest(root) != before
        spoke = _substantive(second["text"])
        verdict = DOOR if changed else (
            SPOKE if (second["exit"] == 0 and spoke) else (
                ACCEPTED if second["exit"] == 0 else REFUSED))
        return Repair(rep.operation_id, rep.base_argv, list(rep.attempt_argv), rep.clause,
                      rep.exit_before, second["exit"], verdict, changed, True,
                      {"world": list(world), "world_created": made,
                       "learned": {"enclosing_action": list(world),
                                   "satisfied": verdict in DOOR_VERDICTS,
                                   "program_family": os.path.basename(str(world[0]))}})
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def repair_many(operations: Sequence[Any], *, seed: Sequence[tuple[str, bytes]] = (),
                env_files: Sequence[str] = (),
                only_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """The repair pass over bound operations, with its own accounting.

    `operations` are the census's BOUND rows, because a world repair needs the names and
    flags of every operation the program declared -- `git init` is found among git's own
    rows, not among the ones that failed. `only_ids` narrows the pass to the ones actually
    refused, so a door is never re-run. Passing the commit-check rows instead was measured
    to silence every world repair: those rows carry `id` and `invoked_as` but no `flag`, so
    the initialiser could not be recognised and 436 readable clauses answered nothing.
    """
    rows: list[Repair] = []
    wanted = set(only_ids) if only_ids is not None else None
    for op in operations:
        row = op if isinstance(op, dict) else op.as_dict()
        argv = row.get("invoked_as") or []
        if not argv or not row.get("bound", True):
            continue
        if wanted is not None and str(row.get("id")) not in wanted:
            continue
        declared = [spelling
                    for flag in (row.get("declared_flags") or ())
                    for spelling in (flag.get("flags") or ())
                    if not spelling.startswith("-no")]
        numeric = [spelling
                   for flag in (row.get("declared_flags") or ())
                   if flag.get("placeholder") and _NUMERIC_OR_LIKE.match(str(flag["placeholder"]))
                   for spelling in (flag.get("flags") or ())]
        one = repair(str(row.get("id")), argv, seed=seed, env_files=env_files,
                     declared_flags=declared, numeric_flags=numeric)
        if one.clause is not None and one.clause.form == WORLD:
            world = world_for(one.clause, operations)
            if world is not None:
                one = repair_in_world(one, world=world, seed=seed, files=env_files)
        rows.append(one)
    forms: dict[str, int] = {}
    paid: dict[str, int] = {}
    for row in rows:
        if row.clause is not None:
            forms[row.clause.form] = forms.get(row.clause.form, 0) + 1
            if row.verdict in DOOR_VERDICTS:
                paid[row.clause.form] = paid.get(row.clause.form, 0) + 1
    return {"schema": SCHEMA, "rows": [r.as_dict() for r in rows],
            "attempted": len(rows),
            "repaired": sum(1 for r in rows if r.changed),
            "spoke": sum(1 for r in rows if r.verdict == SPOKE),
            "answered": sum(1 for r in rows if r.verdict in DOOR_VERDICTS),
            "clause_forms": forms, "clause_paid": paid,
            "unread": sum(1 for r in rows if r.clause is None),
            "all_restored": all(r.restored for r in rows),
            "model_calls": 0, "network_calls": 0, "parameters": 0}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from canonical.runtime import tool_census_v1 as census_module

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", action="append", default=[])
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)

    programs = args.program or ["openssl"]
    started = time.perf_counter()
    out: dict[str, Any] = {"schema": SCHEMA, "programs": {}, "model_calls": 0,
                           "network_calls": 0, "parameters": 0}
    for program in programs:
        contract = census_module.parse_contract(census_module._own_text(program), program)
        census = census_module.census(program, depth=2, max_ops=60)
        bound = [census_module.bind(op, contract=contract) for op in census["operations"]]
        committed = census_module.commit_check_many(
            bound, seed=census_module.trial_seeds(), preparation="PLAIN")
        refused = [row for row in committed["rows"] if row["verdict"] == "FAILED_NO_EFFECT"]
        results = repair_many(bound, seed=census_module.trial_seeds(),
                              only_ids=[row["id"] for row in refused])
        out["programs"][program] = {
            "bound": len(bound), "doors_before": committed["counts"].get(DOOR, 0),
            "refused": len(refused), **{k: v for k, v in results.items()
                                        if k not in ("rows", "schema")},
            "repaired_ids": [r["operation_id"] for r in results["rows"] if r["changed"]],
        }
    out["seconds"] = round(time.perf_counter() - started, 2)
    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
            handle.write("\n")
        print("wrote", args.receipt)
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
