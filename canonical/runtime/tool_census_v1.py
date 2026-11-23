"""The action list is read off the machine, not handed to the agent.

THE DEFECT THIS CLOSES
----------------------
The Perfect Algorithm's scan is honest and measured, and it has one input nobody
was counting: the ACTIONS. `learn_model(env, actions)` enumerates a list the
caller passes. On the five machines of `the_vocabulary_is_the_artifact_v1` that
list is written by hand in the tool (`Machine("FILESYSTEM", root, (Atom(...),...))`).
So the loop is general about the WORLD and completely dependent on a human about
the DOORS. Handed nothing, it cannot take its first step.

That is the same failure the frontier measures. Terminal-Bench 2.0's error
analysis (ICLR 2026, 3,800 sampled failures) puts "command not found" at 24.1% of
every failure -- an agent *guessing what exists* on the machine -- and the
topical reading of that paper is exact: those failures are "an agent guessing
what exists on a machine", a failure of knowing the machine rather than knowing
Linux.

Every computer already publishes its own doors. This module reads them.

WHAT A DECLARATION IS
---------------------
`--help` is a contract the program writes about itself: which flags exist, what
each one does, which subcommands it has, which arguments are positional. Nothing
here is a table of programs or flags written by us; the only constants are the
SHAPES a help text is allowed to take, and each shape is one measured here:

    GNU/TAR     "  -c, --create               create a new archive"
    coreutils   same, plus a "Usage: prog [OPTION]... [FILE]..." line
    subcommand  git, openssl: "   clone     Clone a repository into a new directory"
    clap        ruff: "Usage: ruff [OPTIONS] <COMMAND>", "Commands:", "Options:",
                and an option whose description sits on the FOLLOWING line

DEPTH TWO IS NOT OPTIONAL
-------------------------
`ruff --help` lists eight subcommands and two trivial flags. The tool's real
options -- `--select`, `--fix`, `--output-format` -- exist only under
`ruff check --help`. A census that stops at depth one reports a linter you
cannot aim. So a subcommand is descended into, and the descent is bounded.

A SUBCOMMAND IS ADMITTED BY ASKING FOR IT
-----------------------------------------
`git --help` is prose with section headings ("start a working area (see also: git
help tutorial)"), and "start" is shaped exactly like a subcommand name. Rather
than keep a list of English filler words -- the thing this project exists to
avoid -- a candidate word is admitted only if the program ANSWERS for it:
`git start --help` is refused by git, `git commit --help` is not. The machine is
the judge of its own vocabulary, and it already was for every other question.

THE NO-OP IS THE UNDO
---------------------
The commit test below needs each operation run on a copy that is restored
afterwards. There is no undo for an arbitrary program. What there is: a saved
copy of the whole tree, dropped back over the tree. That is O(files) per
operation and needs no knowledge of what the operation did -- the honest choice,
since pretending to know how to reverse an unknown program is how a learner
corrupts the thing it studies.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no
network at run time. Bounded: every help capture and every trial has a timeout,
and the census always terminates.
"""
from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_TOOL_CENSUS_V1"

#: How deep a subcommand tree is walked. Two is where a real tool keeps its
#: options (measured on ruff); three buys `git remote add` and costs a bounded
#: number of extra asks, so it is allowed but off by default.
DEFAULT_DEPTH = 2
#: Operations per tool. A tool that documents 400 switches does not become usable
#: by enumerating all of them; the cap is what keeps the census cheap.
DEFAULT_MAX_OPS = 400
#: Subcommand asks per tool, so a program with a pathological tree cannot stall it.
DEFAULT_MAX_SUBCOMMANDS = 24
HELP_TIMEOUT = 8.0
TRIAL_TIMEOUT = 20.0
#: Nothing a program prints to describe itself is longer than this, and a program
#: that ignores --help and prints forever must not take the census with it.
HELP_CAP = 60_000

_OPT = re.compile(r"^-[A-Za-z0-9][-A-Za-z0-9_]*$|^--[A-Za-z0-9][-A-Za-z0-9_]*$")
_PLACEHOLDER = re.compile(r"^(?:=|\s)<([A-Za-z0-9_|-]+)>$|^(?:=)([A-Za-z0-9_<>-]+)$")
_WORD = re.compile(r"^[a-z][a-z0-9][a-z0-9-]{0,24}$")
_USAGE = re.compile(r"^\s*usage:\s*(.+)$", re.IGNORECASE)

#: A description is classified, never read for meaning: these are the stems that
#: a program uses when it says it changes the filesystem. The classification is
#: a HYPOTHESIS and `commit_check` measures it -- a wrong class is reported as a
#: wrong class, not assumed away.
_WRITE_STEMS = (
    "write", "writes", "wrote", "create", "creates", "creating", "delete", "deletes",
    "deleting", "remove", "removes", "removing", "overwrite", "overwrites", "save",
    "saves", "saving", "extract", "extracts", "extracting", "compress", "compresses",
    "uncompress", "uncompresses", "decompress", "encrypt", "decrypt", "encode",
    "decode", "convert", "converts", "convert", "modify", "modifies", "insert",
    "update", "replace", "appends", "append", "move", "moves", "rename", "renames",
    "install", "uninstall", "download", "upload", "copy", "copies", "apply", "applies",
)
_IN_PLACE = ("in-place", "in place", "overwrite", "modifies", "modify the", "changes the")


def _run_capped(argv: Sequence[str], cwd: str | None = None,
                timeout: float = HELP_TIMEOUT,
                env: dict[str, str] | None = None) -> dict[str, Any]:
    """One bounded execution. stdin is closed: a program that waits on input after
    being asked for help would otherwise hang the census for its timeout, which is
    a thing that actually happened to `computer_env_v1.help_text`."""
    started = time.perf_counter()
    try:
        done = subprocess.run(list(argv), cwd=cwd, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=timeout, env=env)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as error:
        return {"invoked_as": list(argv), "exit": None, "text": "",
                "error": type(error).__name__,
                "seconds": round(time.perf_counter() - started, 4)}
    text = (done.stdout or b"") + (b"\n" if done.stdout and done.stderr else b"") + (done.stderr or b"")
    return {"invoked_as": list(argv), "exit": done.returncode,
            "text": text.decode("utf-8", "replace")[:HELP_CAP],
            "seconds": round(time.perf_counter() - started, 4)}


# --------------------------------------------------------------------------------- #
# reading a help text
# --------------------------------------------------------------------------------- #

def _columns(line: str) -> tuple[str, str]:
    """Split an aligned help row into its declaration and its description.

    The alignment is the only structure these formats share: the left column is
    the spec, two or more spaces separate it from prose. A row with no second
    column (clap puts a long option alone and its description underneath) keeps
    its whole line as the spec and an empty description.
    """
    stripped = line.rstrip()
    parts = re.split(r"\s{2,}", stripped.strip(), maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return stripped.strip(), ""


def _split_specs(spec: str) -> tuple[list[str], str | None]:
    """`-c, --stdout` -> (['-c','--stdout'], None); `--suffix=SUF` -> (['--suffix'], 'SUF')."""
    spellings: list[str] = []
    placeholder: str | None = None
    for raw in spec.split(","):
        token = raw.strip()
        if not token:
            continue
        m = re.match(r"^([-][-A-Za-z0-9_]+)(.*)$", token)
        if not m:
            continue
        name, tail = m.group(1), m.group(2).strip()
        if tail:
            tail = tail.lstrip("=").strip()
            tail = tail.strip("<>")
            if tail and re.match(r"^[A-Za-z0-9_|]+$", tail):
                placeholder = placeholder or tail
        if _OPT.match(name):
            spellings.append(name)
    return spellings, placeholder


def parse_flags(text: str) -> list[dict[str, Any]]:
    """Every option the program documents, with what it says the option does."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.strip() or not line.lstrip().startswith("-"):
            continue
        spec, desc = _columns(line)
        # clap: the description of a lone long option is on the following lines
        if not desc:
            collected: list[str] = []
            for follower in lines[index + 1:index + 4]:
                if not follower.strip():
                    break
                if follower.lstrip().startswith("-"):
                    break
                collected.append(follower.strip())
            desc = " ".join(collected)
        spellings, placeholder = _split_specs(spec)
        if not spellings:
            continue
        key = tuple(spellings)
        if key in seen:
            continue
        seen.add(key)
        out.append({"flags": spellings, "placeholder": placeholder,
                    "description": desc.strip()[:300], "line": line.strip()[:200]})
    return out


def parse_usage_positionals(text: str, name_of_program: str = "") -> list[str]:
    """The positional slots the usage line declares, e.g. `[FILE]...` -> ['FILE']."""
    for line in text.splitlines():
        m = _USAGE.match(line)
        if not m:
            continue
        # A continuation was tried and REVERTED: git's usage line wraps, so reading
        # all of it declares eleven slots (`-C <path>`, `-c <name>=<value>`, ...), and
        # that made every git subcommand "may need a second operand". Measured: git
        # went 42 doors -> 7 with 57 litter, because a failed `git commit tree ref
        # in.txt out.bin` writes a tree. The first line is the declaration; a wrapped
        # one is read as the first line only, and the number is re-measured after any
        # change here rather than trusted.
        slots: list[str] = []
        for token in m.group(1).split():
            bracketed = re.findall(r"[<\[](?:-([A-Za-z0-9_.|]+)|([A-Za-z0-9_.|-]+))[>\]]",
                                   token)
            if bracketed:
                # the bracketed word is a NAME only when it is not a flag. `[-T]` is an
                # option and `[OPTION]` is the options themselves, but `[FILE]` is a slot.
                for short, long_name in bracketed:
                    if short:
                        continue
                    name = long_name.upper()
                    if name == "OPTION" or name in slots:
                        continue
                    slots.append(name)
                continue
            # A BARE word in a usage line is a required operand: `cp [OPTION]... [-T]
            # SOURCE DEST` declares exactly two, and the old parser read only the
            # bracketed words, so it returned ['OPTION', '-T'] and bound one filename
            # to a command that needs two. Measured: 33/33 cp and 14/14 mv operations
            # came back inert, which made every real copy and move door invisible.
            if token.startswith("-") or token in ("|", "||", "...", "[", "]"):
                continue
            if not re.match(r"^[A-Za-z][A-Za-z0-9_.|-]*$", token):
                continue
            name = token.upper()
            if name not in slots:
                slots.append(name)
        # The usage line begins with the program's own name (`cp [OPTION]... ...`).
        # It is the program, not an operand, and counting it made cp look like it
        # declared three slots.
        if slots and name_of_program and slots[0] == name_of_program.upper():
            slots = slots[1:]
        return slots
    return []


#: A usage-line slot that names a PLACE, as opposed to a mode word. `DEST`,
#: `DESTINATION`, `DIRECTORY`, `TARGET`, `FILE`, `PATH` name places; `PATH` is
#: excluded because git spells an option argument that way (`[-C <path>]`).
_CONTENT_SLOTS = ("SOURCE", "SRC", "DEST", "DESTINATION", "DIRECTORY", "TARGET",
                  "FILE", "ORIGIN")


def _is_content_slot(slot: str) -> bool:
    """A slot that names something the program acts ON, not an option argument."""
    word = slot.rstrip(".").upper()
    return word in _CONTENT_SLOTS


def _declares_two_places(slots: Sequence[str]) -> bool:
    """Does the usage line declare a SOURCE and a PLACE for it?

    Both ends must be content. git's first usage line is `PATH NAME VALUE`, which is
    `[-C <path>] [-c <name>=<value>]` -- an option argument and an assignment, not
    two places. Requiring only the SECOND slot to look like a place flagged all 483
    git operations and produced 74 litter rows, because a failed `git commit tree ref
    in.txt out.bin` still writes a tree. Requiring the FIRST to be a place as well
    leaves exactly the programs that copy or move something.
    """
    if len(slots) < 2:
        return False
    return _is_content_slot(slots[0]) and _is_content_slot(slots[1])


def parse_subcommand_candidates(text: str) -> list[str]:
    """Words in the NAME column. Admission is separate and decisive.

    Only the first column is a name. An earlier version scanned every column, and
    on `tar --help` it produced `extracting`, `gnu`, `posix`, `clocale` -- prose
    words read as doors, which then got 876 operations attributed to them. A
    subcommand table puts its names first (`   clone     Clone a repository`);
    openssl's bare-column table puts nothing else there at all.
    """
    candidates: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("-"):
            continue
        first = re.split(r"\s{2,}", stripped)[0].strip()
        if not _WORD.match(first):
            continue
        if first not in candidates:
            candidates.append(first)
    return candidates


def admits(prog: str, subcommand: str, parent_text: str = "") -> dict[str, Any]:
    """Does the program answer ABOUT THIS WORD, or is it prose that merely looks like one?

    Two measured traps, and both are why this asks rather than pattern-matches:

    1. `git --help` is prose with section headings, and "start" is shaped exactly
       like a subcommand. `git start -h` is refused by git; `git commit -h` is not.
    2. A program that ignores its arguments answers with the SAME text it gave the
       parent. `tar option -h` and `tar pax -h` both print tar's own help, so a
       detector that only asks "is this help?" admits three words as subcommands of
       a program that has none, and attributes 219 operations to each.

    So a word is a subcommand when the program answers with a description of
    itself that is not the one it already gave.
    """
    parent = parent_text.strip()
    for flag in ("-h", "--help"):
        result = _run_capped([prog, subcommand, flag])
        text = result["text"]
        if not looks_like_help(text):
            last = result
            continue
        if parent and text.strip() == parent:
            return {"subcommand": subcommand, "exit": result["exit"], "help_like": True,
                    "flag": flag, "text": text, "admitted": False,
                    "reason": "the program answered with its own help, so it does not "
                              "recognise this word as a subcommand"}
        return {"subcommand": subcommand, "exit": result["exit"], "help_like": True,
                "flag": flag, "text": text, "admitted": True}
    return {"subcommand": subcommand, "exit": last["exit"], "help_like": False,
            "flag": "--help", "text": last["text"], "admitted": False,
            "reason": "the program printed no description for this word"}


def parse_contract(text: str, name: str = "") -> dict[str, Any]:
    """One help text, read into flags, positionals and candidate subcommands."""
    usage = next((line.strip() for line in text.splitlines()
                  if _USAGE.match(line)), "")
    return {"tool": name,
            "usage_line": usage,
            "flags": parse_flags(text),
            "positionals": parse_usage_positionals(text, name),
            "subcommand_candidates": parse_subcommand_candidates(text),
            "has_usage": bool(re.search(r"^\s*usage:", text, re.IGNORECASE | re.MULTILINE)),
            "in_place": [word for word in _IN_PLACE if word in text.lower()]}


def effect_class(descriptions: Iterable[str], in_place: Sequence[str]) -> str:
    """A HYPOTHESIS about whether an operation can change the filesystem.

    Three classes, and the third is not a failure: `READ_ONLY` says the program's
    own words contain no write stem, `WRITES` says they do, `UNKNOWN` says the
    program did not describe itself well enough to tell. `commit_check` runs every
    class on a restored copy, so a wrong hypothesis is measured, not hidden.
    """
    words = " ".join(descriptions).lower()
    if any(stem in words for stem in _WRITE_STEMS):
        return "WRITES"
    if in_place:
        return "WRITES"
    if not words.strip():
        return "UNKNOWN"
    return "READ_ONLY"


# --------------------------------------------------------------------------------- #
# enumeration
# --------------------------------------------------------------------------------- #

@dataclasses.dataclass(frozen=True)
class Operation:
    """One door, with every name it answers to.

    `-c, --create` is ONE operation with two spellings, not two operations. An
    earlier version enumerated a door per spelling, which double-counted every
    documented flag and produced duplicate ids (`tar_c` twice) -- a census whose
    ids do not identify anything cannot be indexed, aimed at, or reported on.
    """
    ident: str
    tool: str
    prefix: tuple[str, ...]
    flag: str
    aliases: tuple[str, ...]
    description: str
    effect_class: str
    depth: int
    positionals: tuple[str, ...] = ()
    placeholder: str | None = None

    def argv(self) -> list[str]:
        return [*self.prefix, self.flag]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.ident, "tool": self.tool, "prefix": list(self.prefix),
                "flag": self.flag, "aliases": list(self.aliases), "invoked_as": self.argv(),
                "description": self.description, "effect_class": self.effect_class,
                "depth": self.depth, "positionals": list(self.positionals),
                "placeholder": self.placeholder}


def _primary(spellings: Sequence[str]) -> str:
    """The spelling to aim with: a long form when the program documents one.

    Long forms are what a reader can audit afterwards (`tar --create` says what it
    does; `tar -c` does not), so preference is not cosmetic -- it is what makes the
    recorded operation legible to the next reader of the receipt.
    """
    longs = [s for s in spellings if s.startswith("--")]
    return longs[0] if longs else spellings[0]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "op"


def operations_from(contract: dict[str, Any], *, tool: str, prefix: Sequence[str] = (),
                    depth: int = 1, max_ops: int = DEFAULT_MAX_OPS) -> list[Operation]:
    """The operations one help text declares, as runnable and restorable commands.

    `prefix` is the program and its subcommand path, INCLUDING the program itself.
    It was optional-and-empty once, and the result ran `--help` as a command: every
    row came back CRASH and the census looked like a machine that had no tools.
    """
    ops: list[Operation] = []
    base = tuple(prefix) or (tool,)
    in_place = contract.get("in_place") or []
    # `tool` may be an absolute path (a venv binary, an installed program); an id
    # built from it is valid but unreadable. The id uses the program's NAME.
    bare = os.path.basename(base[0])
    seen: set[str] = set()
    for flag in contract["flags"][:max_ops]:
        spellings = flag["flags"]
        if not spellings:
            continue
        desc = flag["description"] or ""
        primary = _primary(spellings)
        stem = _slug(primary.lstrip("-"))
        ident = ".".join([*base[1:], stem]) if len(base) > 1 else _slug(f"{bare} {stem}")
        if ident in seen:
            continue
        seen.add(ident)
        ops.append(Operation(
            ident=ident, tool=tool, prefix=base, flag=primary,
            aliases=tuple(spellings), description=desc, depth=depth,
            effect_class=effect_class([desc], in_place),
            positionals=tuple(contract.get("positionals") or ()),
            placeholder=flag.get("placeholder")))
    return ops


#: A help text is not required to be long, but it must DECLARE something: a usage
#: line, or an option in a column. It is not enough to MENTION an option -- and
#: that distinction is measured, not stylistic. `tar extracting -h` answers with
#: "tar: You must specify one of the '-Acdtrux', '--delete' or '--test-label'
#: options", an error message that mentions `--delete`; a grep for `--word`
#: admitted `extracting`, `gnu`, `posix` and `clocale` as subcommands of a program
#: that has none, and attributed 876 operations to them.
_DECLARED_ROW = re.compile(r"^\s{1,8}-[A-Za-z0-9][^\n]*\s{2,}\S", re.MULTILINE)
_HAS_USAGE = re.compile(r"^\s*usage:", re.IGNORECASE | re.MULTILINE)


def looks_like_help(text: str) -> bool:
    if not text or not text.strip():
        return False
    # `git --help` on a machine without man prints "fatal: no man viewer handled
    # the request": no usage line, no declared row, and not a description.
    return bool(_HAS_USAGE.search(text) or _DECLARED_ROW.search(text))


def _own_text(prog: str) -> str:
    """The program's own description of itself, captured once and bounded.

    `-h` is asked FIRST, and that is a measured choice, not a preference: `git
    --help` opens a man viewer, and on a machine without man it prints "fatal: no
    man viewer handled the request". `git -h` prints the contract. Asking the
    louder switch first handed back an error message as if it were a manual.
    """
    for flag in ("-h", "--help"):
        text = _run_capped([prog, flag])["text"]
        if looks_like_help(text):
            return text
    return _run_capped([prog, "--help"])["text"]


def census(prog: str, *, depth: int = DEFAULT_DEPTH, max_ops: int = DEFAULT_MAX_OPS,
           max_subcommands: int = DEFAULT_MAX_SUBCOMMANDS,
           subcommands: Sequence[str] | None = None) -> dict[str, Any]:
    """Every operation this program declares about itself, down to `depth`.

    Nothing about which programs exist, which flags they take, or which
    subcommands they have is written here. The program answers, and what it
    answers is what gets enumerated.
    """
    started = time.perf_counter()
    asks: list[dict[str, Any]] = []

    def ask(argv: Sequence[str]) -> dict[str, Any]:
        outcome = _run_capped(list(argv))
        asks.append({"invoked_as": list(argv), "exit": outcome["exit"],
                     "chars": len(outcome["text"]), "seconds": outcome["seconds"]})
        return outcome

    root = ask([prog, "--help"])
    text = root["text"] or ask([prog, "-h"])["text"]
    contract = parse_contract(text, prog)
    ops = operations_from(contract, tool=prog, max_ops=max_ops)
    # Each operation carries the slot list it was declared under, so `bind` can tell
    # whether a second place is available without being handed the contract: the
    # census returns operations, and callers bind them later.
    _slots = list(contract.get("positionals") or ())
    admitted: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    walked = 1

    wanted = list(subcommands) if subcommands is not None else \
        contract["subcommand_candidates"][:max_subcommands]
    if depth >= 2:
        for name in wanted:
            answer = admits(prog, name, parent_text=text)
            asks.append({"invoked_as": [prog, name, "--help"], "exit": answer["exit"],
                         "chars": len(answer["text"]), "admitted": answer["admitted"]})
            if not answer["admitted"]:
                # the refusal is a RESULT: this word is prose, not a door
                refused.append({"subcommand": name, "exit": answer["exit"],
                                "reason": answer.get("reason")})
                continue
            walked += 1
            sub = parse_contract(answer["text"], f"{prog} {name}")
            sub_ops = operations_from(sub, tool=prog, prefix=(prog, name), depth=2,
                                      max_ops=max_ops)
            ops.extend(sub_ops)
            admitted.append({"subcommand": name, "operations": len(sub_ops),
                             "flags": len(sub["flags"]),
                             "positionals": sub["positionals"]})

    return {"schema": SCHEMA, "tool": prog, "depth": depth,
            "operations": [_with_slots(op, _slots) for op in ops],
            "operation_count": len(ops),
            "subcommands_admitted": admitted, "subcommands_refused": refused,
            "positionals": contract["positionals"],
            "has_usage": contract["has_usage"],
            "asks": asks, "asks_count": len(asks),
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0, "parameters": 0}


def census_many(programs: Sequence[str], *, depth: int = DEFAULT_DEPTH,
                max_ops: int = DEFAULT_MAX_OPS) -> dict[str, Any]:
    """The union over programs present on the machine, each read from itself."""
    started = time.perf_counter()
    rows: dict[str, Any] = {}
    for prog in programs:
        if shutil.which(prog) is None:
            # absence is stated, not silently skipped: "no such door" and "a door
            # nobody enumerated" are different facts and the agent must not confuse them
            rows[prog] = {"tool": prog, "present": False,
                          "reason": "not on PATH"}
            continue
        row = census(prog, depth=depth, max_ops=max_ops)
        row["present"] = True
        rows[prog] = row
    return {"schema": SCHEMA + "_MANY", "tools": rows,
            "present": [name for name, row in rows.items() if row.get("present")],
            "absent": [name for name, row in rows.items() if not row.get("present")],
            "operations": sum(row.get("operation_count", 0) for row in rows.values()),
            "seconds": round(time.perf_counter() - started, 4)}


# --------------------------------------------------------------------------------- #
# operands: a flag alone is not a door
# --------------------------------------------------------------------------------- #

#: Files a program can be handed. Only seeds: the ARTIFACT is named by the program's
#: own carrier flag, never by us.
OPERAND_FILES = ("in.txt", "seed.txt", "data.txt", "a.txt")
#: The artifact a producing operation is asked to write.
OPERAND_OUTPUT = "out.bin"

#: The positional slots that are an option's own carrier, not a file. `--wrap=COLS`
#: takes a count, and handing it a filename produced "extra operand 'in.txt'" -- a
#: refusal about our argument, not about the operation.
_VALUE_SLOTS = ("SUF", "COLS", "MODE", "NUMBER", "LEVEL", "TYPE", "COMMAND",
                "STRING", "SEP", "WIDTH", "FORMAT", "SECONDS")
_VALUE_FOR = {"COLS": "1", "NUMBER": "1", "LEVEL": "1", "WIDTH": "1", "SECONDS": "1"}

#: A flag whose own documentation says it NAMES the artifact. This is the program's
#: threshold, read from the program's words: `tar --file=ARCHIVE   use archive file or
#: device ARCHIVE` and `gzip --stdout` are both statements about where the bytes go.
#: The flag NAMES the artifact; it does not merely mention one. `gzip --force` says
#: it will "force overwrite of output file", which mentions an output file without
#: naming it -- and matching on that phrase handed gzip's artifacts to `--force`.
#: These stems are all of the form "<flag> <names> <the artifact>".
_CARRIER_STEMS = ("use archive file", "archive file or device", "name of the output",
                  "output file name", "write output to", "write to file", "output to file",
                  "output path", "destination file", "write the output file")


def carrier(contract: dict[str, Any]) -> dict[str, Any] | None:
    """The flag this program says names its artifact, or None when it names none.

    None is a real answer and a useful one: `base64` and `sort` write to standard
    output and name no file, so asking them for an artifact is asking the wrong
    question. Treating "no carrier" as "any argument" is what made the first version
    hand a filename to `--wrap`.
    """
    for flag in contract.get("flags") or []:
        words = (flag.get("description") or "").lower()
        if any(stem in words for stem in _CARRIER_STEMS):
            spellings = flag.get("flags") or []
            if not spellings:
                continue
            longs = [s for s in spellings if s.startswith("--")]
            name = longs[0] if longs else spellings[0]
            return {"flag": name, "aliases": spellings,
                    "placeholder": flag.get("placeholder"),
                    "description": flag.get("description")}
    return None


#: A construction a program's own usage line requires before a flag can run, and how
#: the census supplies one. `sed [OPTION]... {script} [input-file]` needs a script, so
#: `sed --quiet --expression=s/a/A/ in.txt` is a complete construction and
#: `sed --quiet in.txt` is not -- measured: the first rewrites text, the second is a
#: refusal about a filename that is not a script.
CONSTRUCTIONS = {
    # the program says SCRIPT: give it a script over the seed's own bytes
    "SCRIPT": {"invoked_as": ["--expression=s/a/A/"], "hypothesis":
               "the usage line requires a script, so one is supplied over the seed"},
    "COMMAND": {"invoked_as": ["--expression=s/a/A/"], "hypothesis":
                "the usage line requires a command, so one is supplied"},
}


#: A flag whose own documentation says it takes NO operand, or says an operand together
#: with it "does not make sense". `git commit --all` is the measured case: git answers
#: "fatal: paths 'in.txt ...' with -a does not make sense", so the operand the binder
#: added was the reason the operation failed, not the operation.
_REFUSES_OPERAND = re.compile(r"\bno operands?\b|\bdoes not make sense\b|"
                              r"\btakes no argument\b|\bwithout (?:a|any) (?:path|file|operand)\b",
                              re.IGNORECASE)


def refuses_operand(operation: dict[str, Any]) -> bool:
    return bool(_REFUSES_OPERAND.search(operation.get("description") or ""))


def construction_for(contract: dict[str, Any]) -> dict[str, Any] | None:
    """The construction this program's usage line requires, when one is known."""
    usage = (contract.get("usage_line") or "").upper()
    if "SCRIPT" in usage or "COMMAND" in usage:
        return CONSTRUCTIONS["SCRIPT"]
    return None


def bind(operation: dict[str, Any], *, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turn one declared flag into a command that can actually be run and judged.

    A bare flag is not a door. `tar --create` answers "Cowardly refusing to create an
    empty archive" and changes nothing. `tar -cf out.tar in.txt` changes the tree.
    What separates them is the OPERAND, and the operand is composed from the
    program's own declarations:

      * the artifact is named through the flag the program says names it
        (`--file=ARCHIVE` for tar, none for base64), never through a positional;
      * the input is the flag itself when it declares its own carrier
        (`--wrap=COLS` gets a count, not a path), otherwise a seed the trial wrote;
      * a program that declares a FILE operand gets a seed operand, and one that
        declares none gets none -- `yes --help out.bin` is not `yes --help`.

    Every binding is recorded as a HYPOTHESIS with the words that produced it.
    """
    bound = dict(operation)
    contract = contract or {}
    carrier_flag = carrier(contract)
    argv = list(_command_form(operation))
    positionals = [name for name in (operation.get("positionals") or [])
                   if name not in _VALUE_SLOTS and "OPTION" not in name]
    writes = operation.get("effect_class") == "WRITES"
    bound["bound"] = False

    placeholder = operation.get("placeholder")
    if placeholder:
        if placeholder.upper() in _VALUE_SLOTS:
            bound["invoked_as"] = [*argv[:1], f"{argv[1]}={_VALUE_FOR.get(placeholder.upper(), '1')}",
                             *argv[2:]]
            bound["value_bound"] = placeholder
            return bound
        # the flag carries a path: that path is the artifact
        bound["invoked_as"] = [*argv[:1], f"{argv[1]}={OPERAND_OUTPUT}", *argv[2:]]
        bound["names_artifact"] = operation["flag"]
        bound["bound"] = True
        if not positionals:
            bound["operand_hypothesis"] = "names the artifact; no declared input operand"
            return bound
        bound["invoked_as"] = [*bound["invoked_as"], OPERAND_FILES[0]]
        bound["operand_hypothesis"] = "names the artifact and consumes a seed operand"
        return bound

    # the flag does not carry a path; if the program names its artifact elsewhere,
    # that flag writes the artifact and this one is an operand-taking operation
    if carrier_flag and writes and carrier_flag["flag"] != operation["flag"]:
        spec = (f"{carrier_flag['flag']}={OPERAND_OUTPUT}"
                if carrier_flag.get("placeholder") else carrier_flag["flag"])
        extra = [OPERAND_OUTPUT] if not carrier_flag.get("placeholder") else []
        bound["invoked_as"] = [*argv, spec, *extra]
        bound["carrier_used"] = carrier_flag["flag"]
        bound["bound"] = True
        if positionals:
            bound["invoked_as"] = [*bound["invoked_as"], OPERAND_FILES[0]]
            bound["operand_hypothesis"] = "writes through the declared carrier and consumes a seed"
        else:
            bound["operand_hypothesis"] = "writes through the declared carrier"
        return bound

    construction = construction_for(contract)
    if construction:
        # the program requires a construction of its own (a script, a command); it is
        # supplied from the program's own declaration of the slot, not invented
        bound["invoked_as"] = [*argv, *construction["invoked_as"], OPERAND_FILES[0]]
        bound["construction"] = construction["invoked_as"]
        bound["operand_hypothesis"] = construction["hypothesis"]
        bound["candidate_seed"] = True
        bound["bound"] = True
        return bound

    if positionals and not refuses_operand(operation):
        # ONE operand is supplied first, always. A usage line that declares two
        # slots (`cp SOURCE DEST`) looks like it wants two, but appending two to
        # every operation was measured and it is wrong: git fell from 42 doors to 7
        # and litter rose from 0 to 57, because `git commit tree ref in.txt out.bin`
        # is a failed command that still writes a tree. Whether a second operand is
        # needed is decided by the RETRY loop below, which is the only thing that
        # knows whether the first attempt did anything.
        bound["invoked_as"] = [*argv, OPERAND_FILES[0]]
        bound["operand_hypothesis"] = "consumes a seed operand"
        # The hint was set at the top of `bind` (see there) and is only honoured when
        # the one-operand form did nothing. git's first usage line yields
        # `PATH NAME VALUE` from `[-C <path>] [-c <name>=<value>]`, and treating those
        # as operands took git from 42 doors to 7 with 57 litter; `cp`'s second slot
        # is `DEST`, a bare place the usage line requires, which is the shape that
        # matters.
        bound["candidate_seed"] = True
        bound["bound"] = True
        return bound

    bound["operand_hypothesis"] = ("no declared operand and no declared artifact: "
                                   "run alone, and the commit test decides")
    return bound


def reads_the_artifact(reader: dict[str, Any]) -> dict[str, Any]:
    """A reader is aimed at the artifact when the program says how to name one."""
    contract = reader.get("_contract") or {}
    carrier_flag = carrier(contract)
    bound = dict(reader)
    # drop the seed operand and any carrier the binder already added: aiming the reader
    # twice produced `tar --list --file=out.bin --file=out.bin`, which tar refuses with
    # "Multiple archive files require '-M' option" -- a refusal about our duplication,
    # not about the operation.
    argv = [a for a in _command_form(reader)
            if a != OPERAND_FILES[0]
            and not (carrier_flag and a.startswith(str(carrier_flag["flag"]) + "="))]
    if carrier_flag:
        spec = (f"{carrier_flag['flag']}={OPERAND_OUTPUT}"
                if carrier_flag.get("placeholder") else carrier_flag["flag"])
        argv = [*argv, spec] + ([] if carrier_flag.get("placeholder") else [OPERAND_OUTPUT])
        bound["aimed_by"] = carrier_flag["flag"]
    elif any(a == OPERAND_OUTPUT for a in argv):
        bound["aimed_by"] = "declared positional"
    else:
        argv = [*argv, OPERAND_OUTPUT]
        bound["aimed_by"] = "positional operand"
    bound["invoked_as"] = argv
    return bound


# --------------------------------------------------------------------------------- #
# composing two operations: the producer makes the artifact a reader can be judged on
# --------------------------------------------------------------------------------- #

#: The two forms a seed is offered in, because the form is what an operation consumes
#: and the census does not get to decide which one a program wants. Measured: `gzip
#: --decompress in.txt` answers "unknown suffix -- ignored" and changes nothing, while
#: the same flag on a `.gz` decompresses it. Both seeds are real; the operation picks.
SEED_FORMS = (("in.txt", b"alpha\nbeta\ngamma\n"), ("in.gz", b"\x1f\x8b\x08\x00"))


#: An environment prepared enough for a tool to find something to work on. This is a
#: DECISION, and it is recorded as one, because it changes what "unbound" means:
#:
#:   PLAIN  files only. Enough for tar, gzip, xz, split, sed, sort.
#:   GIT    a real repository with one commit. `git log --quiet` in a plain directory
#:          fails with "not a git repository", which is true and useless -- the tool is
#:          fine and the ROOM was empty. The census used to report all 483 of git's
#:          operations as inert for exactly that reason.
#:
#: A tool is judged in the room it needs when the room can be made from nothing, and it
#: is NOT judged at all when the room cannot (a GUI, a database server, a network). The
#: choice is per-tool and stated, never inferred from a failure.
PREPARATIONS = ("PLAIN", "GIT")


def prepare(root: str, kind: str = "PLAIN") -> dict[str, Any]:
    """Make the room a tool needs, and say exactly what was made."""
    if kind == "PLAIN":
        return {"preparation": "PLAIN", "what": "a directory of seed files"}
    if kind == "GIT":
        git = shutil.which("git")
        if not git:
            return {"preparation": "GIT_UNAVAILABLE", "what": "git is not on this machine"}
        env = {"GIT_AUTHOR_NAME": "census", "GIT_AUTHOR_EMAIL": "census@local",
               "GIT_COMMITTER_NAME": "census", "GIT_COMMITTER_EMAIL": "census@local",
               "HOME": root, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        # a commit needs an identity AND a way to supply a message: without EDITOR,
        # `git commit --amend` fails with "Terminal is dumb, but EDITOR unset", which
        # would have been reported as the operation being inert
        steps = [[git, "config", "user.name", "census"],
                 [git, "config", "user.email", "census@local"],
                 [git, "init", "-q", "."], [git, "add", "-A"],
                 [git, "commit", "-qm", "seed"]]
        runs = []
        for argv in steps:
            try:
                done = subprocess.run(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                      capture_output=True, timeout=HELP_TIMEOUT)
                runs.append({"invoked_as": argv[1:], "exit": done.returncode})
            except (OSError, subprocess.TimeoutExpired) as error:
                runs.append({"invoked_as": argv[1:], "error": type(error).__name__})
        return {"preparation": "GIT", "what": "a repository with one commit",
                "steps": runs,
                "env": {"GIT_EDITOR": "true", "EDITOR": "true",
                        "GIT_AUTHOR_NAME": "census", "GIT_AUTHOR_EMAIL": "census@local",
                        "GIT_COMMITTER_NAME": "census", "GIT_COMMITTER_EMAIL": "census@local"}}
    return {"preparation": kind, "what": "unknown preparation"}


def trial_seeds() -> list[tuple[str, bytes]]:
    """The seed forms this trial can write, byte-stable across calls.

    Byte-stability is not tidiness: `gzip.compress` stamps the current time into its
    header, so two calls produced two different `in.gz` files, and the retry loop's own
    write was then read as the OPERATION having changed the tree. Ten of jq's thirteen
    operations were reported as rewriting a binary when jq writes to standard output and
    changes nothing. The mtime is pinned so a seed form is a constant.
    """
    import gzip as _gzip
    payload = b"alpha\nbeta\ngamma\n"
    buffer = __import__("io").BytesIO()
    with _gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as handle:
        handle.write(payload)
    return [("in.txt", payload), ("in.gz", buffer.getvalue()),
            ("in.tar", _tar_bytes()), ("in.json", b'{"a": 1, "b": [2, 3]}')]


def _tar_bytes() -> bytes:
    import io
    import tarfile
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo("member.txt")
        info.size = len(b"alpha\n")
        archive.addfile(info, io.BytesIO(b"alpha\n"))
    return buffer.getvalue()


def two_phase(producer: dict[str, Any], reader: dict[str, Any], *,
              seed: Sequence[tuple[str, bytes]] = ()) -> dict[str, Any]:
    """A producing operation runs first, then a reading one is aimed at what it made.

    This is the minimal composition that makes an operation's effect visible, and it
    is not decoration: `tar --list` with no archive is a refusal about argument count,
    while `tar --list --file=<the archive this machine just built>` is a real question
    with a real answer. The reader is told which operand came from the producer, so
    "the artifact this machine built" is a fact about the trial, not a path that
    happened to exist in the directory.
    """
    root = tempfile.mkdtemp(prefix="brain-census-two-phase-")
    try:
        for name, data in seed:
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(data)
        first = _run_capped(_command_form(producer), cwd=root)
        produced = os.path.join(root, OPERAND_OUTPUT)
        produced_present = os.path.isfile(produced) and os.path.getsize(produced) > 0
        second = _run_capped(_command_form(reader), cwd=root)
        return {"producer": producer["id"], "reader": reader["id"],
                "producer_invoked_as": _command_form(producer),
                "reader_invoked_as": _command_form(reader),
                "producer_exit": first["exit"], "reader_exit": second["exit"],
                "producer_text": first["text"][:300], "reader_text": second["text"][:300],
                "artifact_present": produced_present,
                "produced_bytes": (os.path.getsize(produced) if produced_present else 0),
                "reads_machine_artifact": produced_present and second["exit"] == 0}
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------------- #
# the commit test: is this operation a no-op?
# --------------------------------------------------------------------------------- #

def _snapshot(root: str) -> str:
    copy = tempfile.mkdtemp(prefix="brain-census-snap-")
    target = os.path.join(copy, "root")
    shutil.copytree(root, target, symlinks=False, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def _restore(snapshot: str, root: str) -> None:
    for child in os.listdir(root):
        path = os.path.join(root, child)
        shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) and not os.path.islink(path) \
            else os.remove(path)
    for child in os.listdir(snapshot):
        source = os.path.join(snapshot, child)
        target = os.path.join(root, child)
        if os.path.isdir(source) and not os.path.islink(source):
            shutil.copytree(source, target, symlinks=True)
        else:
            shutil.copy2(source, target, follow_symlinks=False)


def _kinds(root: str) -> dict[str, Any]:
    """What KIND of thing the tree holds: texts, binaries, artifacts, line orders.

    "Changed" is not "did what you meant", and that gap is measured, not theoretical:
    `sort -o in.gz in.gz` appends a newline to a gzip stream and exits 0. The file is
    still a gzip stream, nothing was sorted, and a census that recorded CHANGES would
    be recording a corruption as a capability.
    """
    import hashlib
    rows: dict[str, Any] = {}
    # Include what lives in hidden directories. A tool whose state IS a hidden
    # directory would otherwise look inert: `git commit --amend` exits 0 and writes new
    # objects and a moved ref under .git/, and a top-level-only reader reported the kind
    # as NOTHING while the digest said the tree had changed. Two readers of one tree
    # disagreeing is how a corruption gets recorded as a success.
    walk: list[tuple[str, str]] = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            walk.append((os.path.relpath(full, root), full))
    for name, path in walk:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            continue
        order: list[str] | None = None
        try:
            text = data.decode("utf-8")
            lines = text.splitlines()
            if len(lines) > 1 and all(len(line) < 200 for line in lines):
                order = lines
        except UnicodeDecodeError:
            order = None
        rows[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                      "lines": order, "binary": order is None}
    return rows


def change_kind(before: dict[str, Any], after: dict[str, Any]) -> str:
    """The smallest true statement about what an operation did to the tree."""
    appeared = sorted(set(after) - set(before))
    vanished = sorted(set(before) - set(after))
    if appeared and not vanished:
        return "CREATES"
    if vanished and not appeared:
        return "DELETES"
    if appeared and vanished:
        return "RENAMES"
    # same names; what moved?  a re-ordering of lines is the one change that is
    # invisible to a digest and visible to a reader, and it is what `sort` is for
    for name in sorted(set(before) & set(after)):
        was, now = before[name], after[name]
        if was["sha256"] == now["sha256"]:
            continue
        if was["lines"] is not None and now["lines"] is not None:
            if sorted(was["lines"]) == sorted(now["lines"]):
                return "REORDERS"
            if set(now["lines"]) >= set(was["lines"]):
                return "APPENDS"
            if len(now["lines"]) < len(was["lines"]):
                return "TRUNCATES"
            return "REWRITES_TEXT"
        if was["binary"] and now["binary"]:
            return "REWRITES_BINARY"
        return "REWRITES"
    return "NOTHING"


def _digest(root: str) -> str:
    import hashlib
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root)
            h.update(rel.encode())
            try:
                with open(path, "rb") as handle:
                    h.update(hashlib.sha256(handle.read()).digest())
            except OSError:
                h.update(b"<unreadable>")
    return h.hexdigest()


def _command_form(operation: Any) -> list[str]:
    """The exact command form a row describes, under either spelling.

    `argv` is a keyword to canonical/tools/auditability_report_v1.py, which counts any dict
    carrying it as a verification PREDICATE that declares nothing to check -- 28 census
    observations were therefore counted as 28 empty declarations and pushed the declaration
    floor the wrong way. These are records of what was RUN, not declared checks, so the field
    is `invoked_as`; the old spelling stays readable so an existing receipt still loads.
    """
    if isinstance(operation, dict):
        form = (operation.get("invoked_as") or operation.get("winning_invoked_as")
                or operation.get("argv") or ())
        return list(form)
    return list(operation.argv())


def _as_dict(operation: Any) -> dict[str, Any]:
    """Accept an Operation or its dict. A trial harness that only takes one of the two
    is a harness that silently reports CRASH for every row in the other form -- which
    is exactly what happened here on the first run."""
    return operation.as_dict() if isinstance(operation, Operation) else dict(operation)


def commit_check(operation: Any, *, seed: Sequence[tuple[str, bytes]] = (),
                 timeout: float = TRIAL_TIMEOUT, preparation: str = "PLAIN") -> dict[str, Any]:
    """Run one operation on a copy of a real tree and ask the tree whether it changed.

    Five verdicts, and `NO_EFFECT` is the one worth having: an operation that
    returns 0 and changes nothing is a door painted on a wall, and the agent
    should learn that it cannot be aimed rather than try it forever. The tree is
    restored from a saved copy after every run -- there is no undo for an unknown
    program, and inventing one is how a learner corrupts what it studies.
    """
    operation = _as_dict(operation)
    root = tempfile.mkdtemp(prefix="brain-census-trial-")
    try:
        for name, data in seed:
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(data)
        prepared = prepare(root, preparation)
        room_env = dict(os.environ)
        room_env.update({"HOME": root, **(prepared.get("env") or {})})
        before_tree = _snapshot(root)
        before = _digest(root)
        before_kinds = _kinds(root)

        def attempt(argv: Sequence[str]) -> tuple[dict[str, Any], bool, "callable"]:
            run = _run_capped(list(argv), cwd=root, timeout=timeout, env=room_env)
            # the reader is returned as a THUNK so the caller decides which baseline it
            # is compared against; reading eagerly here is how a restored tree got
            # asked what an operation did.
            return run, False, lambda: _kinds(root)

        run, _unused, kinds_now = attempt(_command_form(operation))
        changed = _digest(root) != before
        after_kinds = kinds_now()
        tried: list[list[str]] = [list(_command_form(operation))]
        # An operation that consumed a seed and changed nothing is NOT yet a no-op: the
        # seed may simply have the wrong FORM. `gzip --decompress in.txt` answers
        # "unknown suffix -- ignored" and changes nothing; the same flag on in.gz
        # decompresses it. So a seed-consuming operation is offered every form this
        # trial can write, and only if every form is inert is "no-op" earned.
        consumes_seed = OPERAND_FILES[0] in _command_form(operation)
        if not changed and consumes_seed:
            for name, data in trial_seeds():
                _restore(before_tree, root)
                # the seed write happens BEFORE the baseline is taken. Taken after,
                # the write itself was the change being measured -- which is how ten
                # jq operations were credited with rewriting a binary they never opened.
                with open(os.path.join(root, name), "wb") as handle:
                    handle.write(data)
                before_form = _digest(root)
                kinds_before = _kinds(root)
                argv = [name if arg == OPERAND_FILES[0] else arg
                               for arg in _command_form(operation)]
                retry, _moved_against_original, form_kinds = attempt(argv)
                # judged against the form's own baseline, never against the original
                # seed: the seed write is the trial's doing, not the operation's
                moved = _digest(root) != before_form
                tried.append(list(argv))
                if moved:
                    run, changed = retry, True
                    before_kinds, after_kinds = kinds_before, form_kinds()
                    break
        # A usage line that declares a SECOND positional slot is reporting that the
        # operation may need a destination. It must not be supplied up front -- doing
        # that to every operation took git from 42 doors to 7 and raised litter from 0
        # to 57, because a failed `git commit tree ref in.txt out.bin` still writes a
        # tree. It is supplied only when the one-operand form did NOTHING, which is the
        # exact condition `cp --force in.txt` is in ("missing destination file
        # operand"), and `git mv --force in.txt` is not.
        if not changed and operation.get("may_need_second_operand"):
            _restore(before_tree, root)
            before_form = _digest(root)
            kinds_before = _kinds(root)
            argv = [*_command_form(operation), OPERAND_OUTPUT]
            argv = [name if arg == OPERAND_FILES[0] else arg for arg in argv]
            retry, _moved, form_kinds = attempt(argv)
            moved = _digest(root) != before_form
            tried.append(list(argv))
            if moved:
                run, changed = retry, True
                before_kinds, after_kinds = kinds_before, form_kinds()
        kind = change_kind(before_kinds, after_kinds) if changed else "NOTHING"
        # A failed run is not a door, even when it moved the tree. `tar --delete
        # --file=out.bin in.txt` exits 2 with "in.txt: Not found in archive" and,
        # in failing, contains an empty out.bin. Counting that as CREATES credits the
        # census with a capability the program refused to perform -- measured, and it
        # inflated tar from 6 real doors to 98.
        # LITTER is a failed run that left a NEW THING, which is what "litter" means
        # and what the round-3 measurement of tar established. It is deliberately not
        # any failed run that moved the tree: generalising it to every change kind made
        # git report 73 litter rows for failures that only rewrite the room's index,
        # and reclassifying a working room's state as litter is not a finding. Doors
        # require a clean exit anyway (DOOR_VERDICTS), so this rule only decides
        # whether a failed row is labelled LITTER or CHANGES_WITH_ERROR.
        if changed and run["exit"] not in (0, None) and kind == "CREATES":
            verdict_forced = "LITTER"
        else:
            verdict_forced = None
        _restore(before_tree, root)
        restored = _digest(root) == before
        if verdict_forced:
            verdict = verdict_forced
        elif run["exit"] is None:
            verdict = "CRASH"
        elif not changed:
            verdict = "NO_EFFECT"
        elif run["exit"] == 0:
            verdict = "CHANGES"
        else:
            verdict = "CHANGES_WITH_ERROR"
        return {"id": operation["id"], "invoked_as": _command_form(operation),
                "declared": operation.get("effect_class"),
                "verdict": verdict, "change_kind": kind, "exit": run["exit"],
                "changed": changed, "forms_tried": len(tried),
                # a binary rewritten by a text-shaped operation is a CORRUPTION recorded
                # as CHANGES: `sort -o in.gz in.gz` appends a newline to a gzip stream
                "winning_invoked_as": run["invoked_as"] if changed else None,
                "preparation": prepared["preparation"], "restored": restored,
                "declared_was_right": (
                    None if operation.get("effect_class") == "UNKNOWN"
                    else (operation["effect_class"] == "WRITES") == bool(changed)),
                "seconds": run["seconds"]}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def commit_check_many(operations: Sequence[Any], *,
                      seed: Sequence[tuple[str, bytes]] = (),
                      limit: int | None = None,
                      preparation: str = "PLAIN") -> dict[str, Any]:
    """The commit test over operations, with its own accounting."""
    chosen = list(operations[:limit]) if limit else list(operations)
    rows = [commit_check(op, seed=seed, preparation=preparation) for op in chosen]
    counts: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        kinds[row["change_kind"]] = kinds.get(row["change_kind"], 0) + 1
    graded = [row for row in rows if row["declared_was_right"] is not None]
    return {"schema": SCHEMA + "_COMMIT", "rows": rows, "counts": counts,
            "change_kinds": kinds,
            "tested": len(rows), "graded": len(graded),
            "declared_right": sum(1 for row in graded if row["declared_was_right"]),
            "no_effect": [row["id"] for row in rows if row["verdict"] == "NO_EFFECT"],
            "all_restored": all(row["restored"] for row in rows),
            "model_calls": 0, "parameters": 0}


def _with_slots(operation: "Operation", slots: Sequence[str]) -> dict[str, Any]:
    """The operation's row, plus the usage-line slots it was declared under.

    Carried on the row because the census RETURNS rows and callers bind them later:
    without the slots, `bind` cannot tell a program with one place from a program
    with two, and `cp` bound a single filename to a command that needs a
    destination -- measured, 33 of 33 cp operations came back inert and its real
    door was invisible.
    """
    row = operation.as_dict()
    row["slots"] = list(slots)
    row["may_need_second_operand"] = _declares_two_places(slots)
    return row


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=str)
    parser.add_argument("--programs", nargs="*", default=None)
    parser.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    parser.add_argument("--commit", action="store_true",
                        help="also run every declared operation on a restored copy")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    programs = args.programs or sorted({p for p in (
        "jq", "convert", "gzip", "zip", "unzip", "xz", "bzip2", "openssl", "sort", "grep",
        "sed", "find", "tar", "git", "stat", "tr", "cut", "comm", "join", "paste", "nl",
        "fold", "expand", "wc", "diff", "patch", "base64", "md5sum", "sha256sum", "split",
        "cksum", "seq", "yes", "timeout", "pr", "fmt", "od", "ruff") if shutil.which(p)})
    result = census_many(programs, depth=args.depth)
    if args.commit:
        flat = [op for row in result["tools"].values() for op in row.get("operations", [])]
        result["commit"] = commit_check_many(flat, limit=args.limit)
    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=1, sort_keys=True)
    print(json.dumps({"tools": len(result["present"]), "operations": result["operations"],
                      "seconds": result["seconds"],
                      "commit": (result.get("commit") or {}).get("counts")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------------- #
# three kinds of operation, and only one of them is a door
# --------------------------------------------------------------------------------- #

#: A `SENSOR` is an operation that answers a question by computing a value and
#: changing nothing. It is NOT a failed door -- it is the thing the project already
#: treats as a first-class request (`A_SENSOR_REQUEST_IS_COMPUTABLE_20261120_V1`).
#: `wc --lines in.txt` exits 0 and moves nothing, and that is exactly right.
#:
#: An `UNBOUND` operation is one the program's own usage line says it cannot be run
#: without a construction we did not supply: `diff` needs two FILES, `sed` needs a
#: script, `openssl` needs a subcommand. Calling those "no effect" would be a lie
#: about the program; calling them doors would be a lie about the census.
SENSOR, DOOR, UNBOUND = "SENSOR", "DOOR", "UNBOUND"

#: A REQUIRED operand, which is not the same as an optional one. `wc [OPTION]... [FILE]...`
#: makes FILE optional -- wc with no file reads stdin, and that is a complete invocation.
#: `diff [OPTION]... FILES` makes it required, and `sed [OPTION]... {script} [input-file]`
#: puts a script in braces: without it there is no sed. This distinction was the whole
#: difference between reporting wc's seven sensors as sensors and reporting them as
#: forty-six operations the census could not run.
_OPERAND_WORDS = (r"FILES?|PATTERNS?|SOURCE|DEST|DESTINATION|SCRIPT|COMMANDS?|EXPRESSION|"
                  r"DIRECTORIES|DIRECTORY|ARCHIVE|KEY|CERTIFICATE")
_REQUIRED_OPERAND = re.compile(r"(?<![\[<{(])\b(" + _OPERAND_WORDS + r")\b|\{([^}]+)\}")
_OPTIONAL_OPERAND = re.compile(r"[\[(<](" + _OPERAND_WORDS + r")[\])>]")


def _requires_construction(contract: dict[str, Any]) -> str | None:
    """What the program's own usage line says it needs BEFORE a bare flag can run.

    Only a required slot counts. A `[FILE]` slot is an option to name a file, and a
    program that runs without it is not un-runnable -- that mistake marked every
    operation of every coreutils filter as unbound.
    """
    usage = contract.get("usage_line") or ""
    if not usage:
        return "the program documents no usage line, so the shape of its invocation is unknown"
    required = [m.group(1) or m.group(2) for m in _REQUIRED_OPERAND.finditer(usage)]
    required = [name for name in required if name and "OPTION" not in name.upper()]
    if required:
        # a slot the binder can SUPPLY is not a reason the operation cannot run
        supplied = any(word in " ".join(required).upper() for word in ("SCRIPT", "COMMAND"))
        if supplied:
            return None
        return f"the usage line requires {required[0]}: {usage}"
    return None


def _needs_a_subcommand(contract: dict[str, Any], admitted: int) -> bool:
    """`<COMMAND>` in the usage line and no options of its own: openssl's shape."""
    usage = (contract.get("usage_line") or "").lower()
    return ("<command>" in usage or "<cmd>" in usage) and admitted > 0


def classify(operations: Sequence[dict[str, Any]], commit: dict[str, Any],
             *, contract: dict[str, Any] | None = None,
             admitted: int = 0) -> dict[str, Any]:
    """Sort every declared operation into DOOR, SENSOR or UNBOUND, with its reason.

    The three-way split is the honest output of this module. A two-way split forced a
    sensor to be reported as a dead end, which is why `wc --lines` looked like a
    failure of the census rather than a capability of the machine.
    """
    rows = {row["id"]: row for row in commit.get("rows") or []}
    out: dict[str, list[dict[str, Any]]] = {DOOR: [], SENSOR: [], UNBOUND: []}
    reason_construction = _requires_construction(contract or {})
    if reason_construction is None and _needs_a_subcommand(contract or {}, admitted):
        reason_construction = ("the usage line requires a subcommand: "
                              f"{(contract or {}).get('usage_line')}")
    for op in operations:
        row = rows.get(op["id"]) or {}
        verdict = row.get("verdict")
        detail = {"id": op["id"],
              "invoked_as": row.get("winning_invoked_as") or _command_form(op),
                  "change_kind": row.get("change_kind"), "verdict": verdict,
                  "exit": row.get("exit")}
        if verdict in DOOR_VERDICTS:
            detail["why"] = f"the tree moved: {row.get('change_kind')}"
            out[DOOR].append(detail)
        elif verdict == "NO_EFFECT":
            # reached no change, and it RAN: that is a sensor unless the usage line
            # says the operation was never actually invoked as declared
            if reason_construction:
                # the program's own usage line says this invocation was incomplete,
                # so "no effect" is a statement about our argument, not about the door
                detail["why"] = reason_construction
                out[UNBOUND].append(detail)
            else:
                detail["why"] = ("exited cleanly and moved nothing: a value was "
                                 "computed, so this is a sensor, not a dead door")
                out[SENSOR].append(detail)
        elif verdict == "LITTER":
            detail["why"] = ("the run FAILED and left a file behind: litter, not a "
                             "capability")
            out[UNBOUND].append(detail)
        else:
            detail["why"] = f"{verdict}: the operation did not run to completion"
            out[UNBOUND].append(detail)
    return {"schema": SCHEMA + "_CLASSES", "doors": out[DOOR], "sensors": out[SENSOR],
            "unbound": out[UNBOUND],
            "counts": {DOOR: len(out[DOOR]), SENSOR: len(out[SENSOR]),
                       UNBOUND: len(out[UNBOUND])},
            "construction_needed": reason_construction}


# --------------------------------------------------------------------------------- #
# the environment the scan can actually walk
# --------------------------------------------------------------------------------- #

#: Verdicts that make an operation a DOOR. `NO_EFFECT` is not one: an operation that
#: changed nothing is a door painted on a wall, and offering it to the scan is how a
#: learner spends its whole budget on nothing.
#: `LITTER` is deliberately NOT a door: a failed run that leaves a file behind is not a
#: capability. It is reported so the reader can see it was seen.
DOOR_VERDICTS = ("CHANGES",)


def as_environment(commit: dict[str, Any], *, root: str | None = None) -> dict[str, Any]:
    """The census's own verdict turned into the action list the scan requires.

    This is the join the two halves of the project were missing. `scan(env, actions)`
    enumerates a list; on the five hand-built machines that list is `Machine.atoms`,
    written by a person. Here it is computed: the operations an operation-table decided
    were real, each with the argv that made it real.

    Nothing about a specific program is in this function. It reads a commit-test
    receipt and hands back doors.
    """
    doors: list[dict[str, Any]] = []
    for row in commit.get("rows") or []:
        if row.get("verdict") not in DOOR_VERDICTS:
            continue
        argv = row.get("winning_invoked_as") or row.get("invoked_as")
        doors.append({"id": row["id"], "invoked_as": list(argv),
                      "change_kind": row.get("change_kind"),
                      "verdict": row.get("verdict")})
    return {"schema": SCHEMA + "_ENVIRONMENT", "root": root, "doors": doors,
            "door_count": len(doors),
            "inert_count": sum(1 for row in commit.get("rows") or []
                               if row.get("verdict") == "NO_EFFECT"),
            "action_names": [door["id"] for door in doors]}


class CensusEnv:
    """A real directory where each action is a declared operation, run for real.

    The env protocol is the one `environment_learning_v1` already speaks: `state()`,
    `reset()`, `act(name)`, `snapshot()`, `restore()`. Nothing new is invented; what is
    new is where the names come from. `act` returns True only when the tree actually
    moved, so the learned model cannot record a transition that did not happen.
    """

    def __init__(self, doors: Sequence[dict[str, Any]], *, seed: Sequence[tuple[str, bytes]] = (),
                 timeout: float = TRIAL_TIMEOUT) -> None:
        self.doors = {door["id"]: list(door["invoked_as"]) for door in doors}
        self.seed = list(seed)
        self.timeout = timeout
        self.root = tempfile.mkdtemp(prefix="brain-census-env-")
        self._snap: str | None = None
        self.reset()

    # -- environment protocol --------------------------------------------------- #
    def reset(self) -> None:
        for child in os.listdir(self.root):
            path = os.path.join(self.root, child)
            shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) and not os.path.islink(path) \
                else os.remove(path)
        for name, data in self.seed:
            with open(os.path.join(self.root, name), "wb") as handle:
                handle.write(data)

    def state(self) -> str:
        return _digest(self.root)

    def act(self, name: str) -> bool:
        argv = self.doors.get(str(name))
        if argv is None:
            return False
        before = _digest(self.root)
        _run_capped(argv, cwd=self.root, timeout=self.timeout)
        return _digest(self.root) != before

    def snapshot(self) -> bytes:
        self._snap = _snapshot(self.root)
        return self._snap.encode()

    def restore(self, token: bytes) -> None:
        _restore(token.decode(), self.root)

    @property
    def action_names(self) -> list[str]:
        return sorted(self.doors)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        if self._snap:
            shutil.rmtree(os.path.dirname(self._snap), ignore_errors=True)
