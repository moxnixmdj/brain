"""Self-extension of the computer surface from the machine's own documentation.

A creature that can only use the binaries someone pre-approved cannot do
anything on the computer; it can only do the approved things.  This module is
how the vocabulary grows at runtime without a model, a network call or a
hand-written table of commands:

1. **The machine documents itself.**  Every executable on ``PATH`` answers
   ``--help`` with a usage line and a one-sentence definition.  That text is a
   real, local, authoritative description of what the computer can do, written
   by the tool's authors, not by this file.
2. **A goal is a specification, not a template lookup.**  ``readings()`` turns
   a goal sentence into the exact expected output using only its words: which
   verb, which unit of text it applies to, and whether it applies per unit
   ("each line") or to the sequence ("the lines").  Where the goal does not say,
   both readings are proposed and the computer decides by experiment.
3. **Nothing is believed because it matched a keyword.**  A candidate command is
   admitted only when the real shell reproduces the expected bytes exactly,
   twice, on a real file.  A tool whose documentation claims the right thing and
   whose behaviour is wrong is rejected -- that case is a test, not a hope.
4. **Ambiguity is not resolved by guessing.**  If two readings are both
   satisfiable by real commands, the goal is genuinely ambiguous and the
   creature says so instead of silently choosing one.

The design is specification mining (as in MAPO/SWIM-style API mining, but from
the tools' own help text) plus exact differential verification, with the
conservative rule that only decidable claims are admitted.
"""
from __future__ import annotations

import json
import math
import os
import re
import select
import shutil
import tempfile
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVING_DISCOVERY_V1"

# Bumped whenever help parsing changes: a cache is only valid for the
# parser that produced it, or stale documentation outlives its reader.
PARSER_VERSION = 4

SYSTEM_DIRS = ("/usr/local/bin", "/usr/bin", "/bin")

# Utilities that change state or reach the network are never discoverable: the
# creature extends its *reading* vocabulary, not its authority.
_DENY = frozenset(
    {
        "apt", "apt-get", "bash", "chmod", "chown", "chroot", "cp", "curl", "dd",
        "docker", "dpkg", "git", "gzip", "gunzip", "kill", "killall", "ln", "login",
        "mkdir", "mkfifo", "mknod", "mktemp", "mount", "mv", "nc", "netcat", "nice",
        "nohup", "npm", "perl", "php", "pip", "pip3", "python", "python3", "reboot",
        "rm", "rmdir", "ruby", "scp", "sh", "shutdown", "ssh", "sudo", "su", "systemctl",
        "tar", "tee", "telnet", "touch", "umount", "unzip", "vi", "vim", "wget", "xargs",
        "zip", "zsh",
    }
)

DENY = _DENY

_STOP = {
    "the", "a", "an", "in", "of", "for", "to", "and", "with", "from", "into", "file",
    "please", "me", "it", "this", "that", "on", "at", "each", "every", "per", "all",
    "its", "their", "my", "content", "contents", "text", "order", "sequence",
}


class DiscoveryError(RuntimeError):
    """A goal could not be understood or no real command was verified for it."""


# --------------------------------------------------------------------------- #
# the machine's own description of itself                                      #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Option:
    """One option a tool documents for itself, with what it takes.

    Read from the tool's own ``--help``: the flag spellings, whether the option
    wants a value, and the sentence the authors wrote about it.  Nothing here
    is a table of known flags -- a tool the creature has never seen contributes
    its own options the same way.
    """

    short: str
    long: str
    argument: str
    description: str

    def spellings(self) -> list[str]:
        return [spelling for spelling in (self.short, self.long) if spelling]

    def to_dict(self) -> dict[str, str]:
        return {
            "short": self.short,
            "long": self.long,
            "argument": self.argument,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Option":
        return cls(
            short=str(payload.get("short", "")),
            long=str(payload.get("long", "")),
            argument=str(payload.get("argument", "")),
            description=str(payload.get("description", "")),
        )


_OPTION_LINE = re.compile(
    r"^\s{2,8}(?:(-[A-Za-z0-9])(?:,\s*)?)?(--[A-Za-z0-9][A-Za-z0-9_-]*)?"
    r"(?:=\[?-?\]?([A-Za-z][A-Za-z0-9_-]*))?(?:\s{2,}(.*))?$"
)


def parse_options(text: str) -> tuple[Option, ...]:
    """Every option line in a help text, in the order the tool lists them.

    Coreutils, BSD and hand-written help all put options two-to-eight columns in
    and describe them two or more spaces later, which is the only structure
    relied on.  A line that does not start with a flag is not an option.
    """
    options: list[Option] = []
    for raw in text.replace("\r", "").split("\n"):
        if "-" not in raw or len(raw) > 240:
            continue
        match = _OPTION_LINE.match(raw)
        if not match:
            continue
        short, long, argument, description = match.groups()
        if not short and not long:
            continue
        if long and not argument and "=" in raw.split(long, 1)[1][:1]:
            continue
        description = re.sub(r"\s+", " ", description or "").strip()
        options.append(
            Option(
                short=short or "",
                long=long or "",
                argument=(argument or "").upper(),
                description=description,
            )
        )
    return tuple(options)


_ENUM_HEADER = re.compile(r"^([A-Z][A-Z0-9_-]*)\s+(?:is|are)\s+one of:?\s*$")
_ENUM_ITEM = re.compile(r"^ {1,4}(\S+)\s{2,}(\S.*)$")


def parse_enumerations(text: str) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """Option values a tool lists for itself ("STYLE is one of: a t n ...").

    Some arguments are not quantities but a small closed vocabulary whose
    meaning the tool defines in its own help.  ``nl -b a`` is the standard
    example: "a" means "number all lines", and nothing else on the machine
    says so.  Reading the enumeration is how an argument like that can be
    bound from evidence instead of guessed.
    """
    lines = text.replace("\r", "").split("\n")
    found: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    index = 0
    while index < len(lines):
        header = _ENUM_HEADER.match(lines[index].strip())
        if not header:
            index += 1
            continue
        name = header.group(1)
        values: list[tuple[str, str]] = []
        cursor = index + 1
        while cursor < len(lines):
            line = lines[cursor]
            if not line.strip():
                if values:
                    break
                cursor += 1
                continue
            item = _ENUM_ITEM.match(line)
            if not item:
                break
            value, description = item.groups()
            values.append((value, re.sub(r"\s+", " ", description).strip()))
            cursor += 1
        if values:
            found.append((name, tuple(values)))
        index = cursor
    return tuple(found)


@dataclass(frozen=True)
class ToolDoc:
    """What one executable says about itself, plus where that text came from."""

    name: str
    path: str
    usage: str
    summary: str
    words: frozenset[str]
    seconds: float = 0.0
    options: tuple[Option, ...] = ()
    enumerations: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "usage": self.usage,
            "summary": self.summary,
            "words": sorted(self.words),
            "options": [option.to_dict() for option in self.options],
            "enumerations": [[name, [list(pair) for pair in values]] for name, values in self.enumerations],
        }

    @property
    def takes_a_file(self) -> bool:
        """Does the synopsis say this tool reads a file argument?

        ``tr [OPTION]... STRING1 [STRING2]`` does not: every operand it has is
        a string to translate, and handing it a path is a different command.
        ``grep [OPTION]... PATTERNS [FILE]...`` does.  Read from the tool's own
        usage line, because that is the tool's statement about its own shape --
        a path can be appended only where the synopsis has a place for it.
        """
        for match in re.finditer(r"\[?\b([A-Z][A-Z0-9_]{0,15})\b\]?(?:\.\.\.)?", self.usage):
            name = match.group(1)
            if name in {"OPTION", "OPTIONS", "USAGE", "ARG", "ARGS"}:
                continue
            if re.fullmatch(r"(?:[A-Z]+_)?(?:FILE|FILES|PATH|INPUT|OUTPUT|DIR|DIRECTORY|SOURCE|TARGET|NAME)S?\d?", name):
                return True
        return False

    @property
    def operands(self) -> tuple[str, ...]:
        """Placeholders the synopsis says this tool consumes, in order.

        ``tr [OPTION]... STRING1 [STRING2]`` takes two positional strings that
        no option describes -- the tool translates STRING1 into STRING2 and says
        so nowhere else.  The usage line is the tool's own statement about the
        values it consumes, so it is read rather than assumed.  Brackets around
        a placeholder mean optional; the position still counts, because
        ``tr ','`` reads differently from ``tr ',' ';'``.
        """
        if not self.usage:
            return ()
        names: list[str] = []
        for match in re.finditer(r"\[?\b([A-Z][A-Z0-9_]{0,15})\b\]?(?:\.\.\.)?", self.usage):
            name = match.group(1)
            if name in {"OPTION", "OPTIONS", "USAGE", "ARG", "ARGS"}:
                continue
            if name not in names:
                names.append(name)
        return tuple(names)

    def values_for(self, argument: str) -> tuple[tuple[str, str], ...]:
        """The tool's own list of values for this argument, if it gave one."""
        wanted = argument.strip("[]").upper()
        for name, values in self.enumerations:
            if name == wanted:
                return values
        return ()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ToolDoc":
        return cls(
            name=str(payload["name"]),
            path=str(payload.get("path", "")),
            usage=str(payload.get("usage", "")),
            summary=str(payload.get("summary", "")),
            words=frozenset(str(w) for w in payload.get("words", ())),
            options=tuple(Option.from_dict(row) for row in payload.get("options", ())),
            enumerations=tuple(
                (str(name), tuple((str(value), str(text)) for value, text in values))
                for name, values in payload.get("enumerations", ())
            ),
        )


def _run_capped(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 1.0,
    limit: int = 262_144,
    stdin_text: str | None = None,
) -> tuple[int, bytes]:
    """Run a command and read at most ``limit`` bytes before stopping it.

    A machine contains tools like ``yes`` that will happily write forever.
    Reading their output with an unbounded pipe turns a learning step into a
    memory bomb, so the reader stops at the limit and kills the child.

    Two distinctions matter and both were learned the hard way:

    * **EOF is not exit.**  A tool closes its stdout and then exits; killing it
      the instant the pipe drains races that exit and reports ``-9`` for a tool
      that was answering perfectly.  After EOF the child gets the rest of its
      budget to finish, and only a child that outlives its budget is killed.
    * **Truncation is not an answer.**  A run stopped by the byte limit or the
      deadline returns 137 with the bytes seen so far, so no caller can mistake
      a flood for a result.
    """
    started = time.perf_counter()
    # A pipeline stage is fed through a temporary file rather than a pipe: a
    # writer thread to keep a pipe from filling would cost more than the fork,
    # and a temp file can never deadlock against the capped reader.
    handle = None
    try:
        if stdin_text is None:
            source: Any = subprocess.DEVNULL
        else:
            handle = tempfile.TemporaryFile()
            handle.write(stdin_text.encode("utf-8"))
            handle.seek(0)
            source = handle
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, ValueError):
        if handle is not None:
            handle.close()
        return 127, b""
    buffer = bytearray()
    deadline = started + timeout
    stopped_early = False
    try:
        assert process.stdout is not None
        fd = process.stdout.fileno()
        while True:
            if len(buffer) >= limit:
                stopped_early = True
                break
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                stopped_early = True
                break
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(fd, min(65_536, limit - len(buffer)))
            if not chunk:
                break
            buffer.extend(chunk)
    except (OSError, ValueError):
        stopped_early = True
    finally:
        if stopped_early:
            try:
                process.kill()
            except OSError:
                pass
        else:
            # EOF: let the tool finish on its own clock, but not forever.
            try:
                process.wait(timeout=max(0.05, deadline - time.perf_counter()))
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
    code = 137 if stopped_early else (process.returncode if process.returncode is not None else 137)
    return code, bytes(buffer)


def _decode(raw: bytes | None) -> str:
    """Bytes a tool printed, decoded leniently: help and output are evidence,
    not a protocol, and one binary blob is not a reason to stop learning."""
    return (raw or b"").decode("utf-8", "replace")


def _stem(word: str) -> str:
    """Crude, deterministic plural folding: ``lines`` and ``line`` are the same
    word for retrieval purposes, and nothing else is conflated."""
    lowered = word.lower()
    if len(lowered) > 3 and lowered.endswith("s") and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


def _words(text: str) -> frozenset[str]:
    return frozenset(
        token for token in re.findall(r"[a-z][a-z0-9_]{1,}", text.lower()) if token not in _STOP
    )


def parse_help(name: str, text: str, *, path: str = "", seconds: float = 0.0) -> ToolDoc | None:
    """Read a usage line and a definition out of a tool's own help output.

    Coreutils-style help puts ``Usage: ...`` first and the definition on the
    next non-empty line; BSD-style help puts ``usage: ...`` first and the
    definition above it.  Both are handled by taking the first line that is
    neither a usage line, an option, nor a section header.
    """
    lines = [line.strip() for line in text.replace("\r", "").split("\n")]
    usage = ""
    definition = ""
    for index, line in enumerate(lines):
        if not line:
            continue
        if not usage and re.match(r"^(usage|Usage|USAGE)\s*:", line):
            usage = line
            for following in lines[index + 1 :]:
                if not following or following.startswith("-"):
                    continue
                if re.match(r"^(or|and|options|Options|OPTIONS|flags|Examples?)\s*:", following):
                    # "  or:  wc [OPTION]... --files0-from=F" is another usage
                    # form, not the definition of the tool.
                    if re.match(r"^(or|and)\s*:", following):
                        continue
                    break
                definition = following
                break
            break
    if not definition:
        for line in lines:
            if not line or line.startswith("-"):
                continue
            if re.match(r"^(usage|Usage|USAGE|options|Options|OPTIONS)\s*:", line):
                continue
            definition = line
            break
    if not usage and not definition:
        return None
    definition = re.sub(r"\s+", " ", definition).strip().rstrip(".")
    return ToolDoc(
        name=name,
        path=path,
        usage=re.sub(r"\s+", " ", usage).strip(),
        summary=definition,
        words=_words(name.replace("_", " ").replace("-", " ") + " " + definition),
        seconds=seconds,
        options=parse_options(text),
        enumerations=parse_enumerations(text),
    )


def _plausible_name(name: str) -> bool:
    """Whether an executable name could plausibly denote a text tool.

    Toolchains, versioned interpreters and library shims outnumber real
    filters by three to one, and every one of them costs a process to ask.
    This is a heuristic about how machines name their programs, not about
    tasks: it decides only what to read *first*, and the differential sweep
    still covers everything it skips.
    """
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,24}", name):
        return False
    if any(character.isdigit() for character in name):
        return False
    if name.count("-") > 1 or len(name) > 12:
        return False
    return name not in _DENY


class MachineVocabulary:
    """The set of executables the machine offers, with their own definitions.

    Answers are cached on disk, keyed by executable name, size and mtime, so a
    second session reads the machine's vocabulary in milliseconds instead of
    running hundreds of ``--help`` calls again.  The cache is a *cache*: if a
    binary changes, its entry stops matching and is re-read.
    """

    def __init__(
        self,
        dirs: Sequence[str | Path] = SYSTEM_DIRS,
        *,
        cache_path: str | Path | None = None,
        limit: int = 1200,
        help_timeout: float = 0.6,
        workers: int = 16,
    ) -> None:
        self.dirs = tuple(str(Path(d)) for d in dirs)
        self.cache_path = Path(cache_path) if cache_path is not None else None
        self.limit = int(limit)
        self.help_timeout = float(help_timeout)
        self.workers = max(1, int(workers))
        self._docs: dict[str, ToolDoc | None] = {}
        self._inventory: list[tuple[str, str]] | None = None
        self._stamps: dict[str, str] = {}
        self.help_reads = 0
        self.seconds = 0.0
        self._load_cache()

    # -- inventory --------------------------------------------------------
    def executables(self) -> list[tuple[str, str]]:
        """Executables worth asking, deduplicated by the binary itself.

        The inventory is a fact about the machine that does not change while a
        goal is being solved, and every tier of every search asks for it, so it
        is computed once per vocabulary.

        ``zcat``, ``gzcat`` and ``zless`` can be the same program; one probe per
        distinct binary is enough to learn what it does, and the alias that is
        asked is the shortest name (the one a person would type).
        """
        if self._inventory is not None:
            return list(self._inventory)
        found: dict[str, str] = {}
        seen_inodes: dict[int, str] = {}
        candidates: list[tuple[str, str, int]] = []
        for directory in self.dirs:
            base = Path(directory)
            if not base.is_dir():
                continue
            for entry in sorted(base.iterdir()):
                name = entry.name
                if name in found or name in _DENY:
                    continue
                if not _plausible_name(name):
                    continue
                if "-" in name:
                    # Hyphenated names are package subcommands (apt-cache,
                    # dpkg-query, gcc-ar), not text filters.  The sweep still
                    # reaches anything this skips if a goal truly needs it.
                    continue
                try:
                    if not entry.is_file():
                        continue
                    stat = entry.stat()
                    if not stat.st_mode & 0o111:
                        continue
                except OSError:
                    continue
                inode = stat.st_ino
                if inode in seen_inodes:
                    continue
                seen_inodes[inode] = name
                found[name] = str(entry)
                candidates.append((name, str(entry), inode))
                if len(found) >= self.limit:
                    break
        self._inventory = sorted((name, path) for name, path, _inode in candidates)
        return list(self._inventory)

    # -- documentation ----------------------------------------------------
    def doc(self, name: str) -> ToolDoc | None:
        if name in self._docs:
            return self._docs[name]
        return None

    def read(self, entries: Sequence[tuple[str, str]] | None = None) -> list[ToolDoc]:
        """Read ``--help`` for entries whose documentation is not cached yet."""
        started = time.perf_counter()
        pending: list[tuple[str, str, str]] = []
        for name, path in entries if entries is not None else self.executables():
            stamp = self._stamp(name, path)
            if self._stamps.get(name) == stamp and name in self._docs:
                continue
            pending.append((name, path, stamp))
        if pending:
            # Asking a stranger about itself runs code.  Some tools write next
            # to their working directory even for `--help` (a real scan left
            # `gz*` files in the repository root), so the whole scan runs in
            # one throwaway directory that is removed afterwards.
            scratch = tempfile.mkdtemp(prefix="brain-help-")
            try:
                with ThreadPoolExecutor(max_workers=self.workers) as pool:
                    results = list(
                        pool.map(lambda item: self._read_one(item[0], item[1], scratch), pending)
                    )
            finally:
                shutil.rmtree(scratch, ignore_errors=True)
            for (name, _path, stamp), doc in zip(pending, results):
                self._docs[name] = doc
                self._stamps[name] = stamp
            self._save_cache()
        self.seconds = time.perf_counter() - started
        return [doc for doc in self._docs.values() if doc is not None]

    def _read_one(self, name: str, path: str, scratch: str) -> ToolDoc | None:
        self.help_reads += 1
        started = time.perf_counter()
        _code, raw = _run_capped(
            [path, "--help"],
            cwd=scratch,
            env={"PATH": ":".join(self.dirs), "LC_ALL": "C", "HOME": scratch},
            timeout=self.help_timeout,
            limit=131_072,
        )
        text = _decode(raw)
        return parse_help(name, text, path=path, seconds=time.perf_counter() - started)

    @staticmethod
    def _stamp(name: str, path: str) -> str:
        try:
            stat = Path(path).stat()
            return f"{stat.st_size}:{int(stat.st_mtime)}"
        except OSError:
            return "missing"

    def _load_cache(self) -> None:
        if self.cache_path is None or not self.cache_path.is_file():
            return
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if payload.get("schema") != SCHEMA + "_VOCABULARY":
            return
        if int(payload.get("parser", 0)) != PARSER_VERSION:
            return
        for name, record in payload.get("tools", {}).items():
            try:
                # A tool that answered with nothing worth parsing is a fact
                # too: caching only the successes meant re-asking a third of
                # the machine every session.
                doc = record.get("doc")
                self._docs[name] = ToolDoc.from_dict(doc) if doc else None
                self._stamps[name] = str(record["stamp"])
            except (KeyError, TypeError, ValueError):
                continue

    def _save_cache(self) -> None:
        if self.cache_path is None:
            return
        payload = {
            "schema": SCHEMA + "_VOCABULARY",
            "parser": PARSER_VERSION,
            "tools": {
                name: {
                    "stamp": self._stamps.get(name, ""),
                    "doc": doc.to_dict() if doc is not None else None,
                }
                for name, doc in self._docs.items()
            },
        }
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            temporary.replace(self.cache_path)
        except OSError:
            pass

    # -- trial ------------------------------------------------------------
    def trial(
        self,
        name: str,
        relative: str | None = None,
        *,
        cwd: str | None = None,
        payload: str | None = None,
        timeout: float = 1.0,
    ) -> str | None:
        """Run one tool on one file with no shell, and return its stdout.

        This is how the creature *tries* a tool it has not admitted: exact argv,
        no shell interpretation, no arguments beyond one file name, a hard
        timeout and an empty stdin.  Nothing is believed from this run; it only
        decides which tools deserve a real, verified check.

        The run is hermetic.  A tool is arbitrary code: it may write files next
        to its input, delete its input, or scribble in ``$HOME``.  So the trial
        gets a throwaway directory holding a private copy of the input, and the
        directory is destroyed afterwards.  Nothing a stranger tool does can
        reach the creature's tree -- probing a candidate must never cost the
        creature its own files.
        """
        located = next(
            (str(Path(directory) / name) for directory in self.dirs if (Path(directory) / name).is_file()),
            None,
        )
        if located is None:
            return None
        if (relative is None) == (payload is None):
            raise ValueError("trial needs exactly one of relative= or payload=")
        with tempfile.TemporaryDirectory(prefix="brain-trial-") as scratch:
            target = Path(scratch) / Path(relative).name if relative is not None else Path(scratch) / "trial.txt"
            if payload is None:
                try:
                    shutil.copyfile(Path(cwd or ".") / str(relative), target)
                except OSError:
                    return None
            else:
                target.write_text(payload, encoding="utf-8")
            code, raw = _run_capped(
                [located, target.name],
                cwd=scratch,
                env={"PATH": ":".join(self.dirs), "LC_ALL": "C", "HOME": scratch},
                timeout=timeout,
                limit=1_048_576,
            )
        if code != 0:
            return None
        return _decode(raw)

    def sweep(
        self,
        payload: str,
        expected: str,
        *,
        names: Sequence[str] | None = None,
        workers: int | None = None,
        timeout: float = 0.6,
    ) -> list[str]:
        """Every tool on the machine that reproduces ``expected`` on one file.

        The vocabulary does not need documentation for this: one file, no
        arguments, exact bytes.  It is the differential experiment that says
        *which* tools are even candidates; documentation is then used to order
        them and to record why the winner was believed.

        The whole sweep shares one throwaway directory and gives every trial its
        own copy, so a tool that rewrites or removes its input -- ``shred`` will
        happily eat a file -- cannot blind the trials after it, and per-trial
        directory churn is not paid 300 times.
        """
        wanted = list(names) if names is not None else [name for name, _ in self.executables()]
        located = {name: str(Path(directory) / name) for directory in reversed(self.dirs)
                   for name in wanted if (Path(directory) / name).is_file()}
        scratch = tempfile.mkdtemp(prefix="brain-sweep-")
        try:
            def attempt(item: tuple[int, str]) -> str | None:
                index, name = item
                binary = located.get(name)
                if binary is None:
                    return None
                relative = f"case-{index}.txt"
                try:
                    (Path(scratch) / relative).write_text(payload, encoding="utf-8")
                except OSError:
                    return None
                code, raw = _run_capped(
                    [binary, relative],
                    cwd=scratch,
                    env={"PATH": ":".join(self.dirs), "LC_ALL": "C", "HOME": scratch},
                    timeout=timeout,
                    limit=1_048_576,
                )
                return name if code == 0 and _decode(raw) == expected else None

            with ThreadPoolExecutor(max_workers=workers or self.workers) as pool:
                matched = [name for name in pool.map(attempt, list(enumerate(wanted))) if name]
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        return sorted(matched)

    def name_candidates(self, words: Iterable[str], *, limit: int = 4) -> list[str]:
        """Executables whose *name* is one of the goal's words, at no cost.

        ``rev`` for "reverse", ``sort`` for "sorted", ``uniq`` for "unique":
        machines often name a filter after the verb it performs, and reading a
        name costs nothing.  These are still only candidates -- each one is
        verified by exact bytes before it is believed.
        """
        wanted = [word for word in dict.fromkeys(words) if len(word) >= 3]
        scored: list[tuple[int, str]] = []
        for name, _path in self.executables():
            best = 0
            for token in re.split(r"[-_]", name):
                if len(token) < 3:
                    continue
                for word in wanted:
                    if token == word:
                        best = max(best, 3)
                    elif word.startswith(token) or token.startswith(word):
                        best = max(best, 2)
            if best:
                scored.append((best, name))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [name for _score, name in scored[:limit]]

    def mentioning(self, words: Iterable[str], *, limit: int = 48) -> list[str]:
        """Tools whose own description uses any of these words.

        This is the recall step, not the decision: "last line first" mentions a
        line, so ``tac`` is worth a real trial for "reverse the lines", while a
        tool that never mentions lines is not.  Narrowing the differential
        experiment this way keeps first contact with a new machine fast.
        """
        wanted = {_stem(word) for word in words if len(word) >= 3}
        if not wanted:
            return []
        shortlist: list[tuple[int, str]] = []
        for name, doc in self._docs.items():
            if doc is None:
                continue
            vocabulary = {_stem(word) for word in doc.words}
            overlap = len(wanted & vocabulary)
            if overlap:
                shortlist.append((overlap, name))
        shortlist.sort(key=lambda item: (-item[0], item[1]))
        return [name for _overlap, name in shortlist[:limit]]

    # -- ranking ----------------------------------------------------------
    def ranked(self, words: Iterable[str], *, limit: int = 8) -> list[ToolDoc]:
        """Tools ordered by how strongly their own text matches the goal words.

        Name matches outrank definition matches, and a word that appears in
        almost every tool's help ("input", "output") is worth less than a rare
        one ("reverse").  This only decides *what to try first*: the shell
        decides what is true.
        """
        wanted = [word for word in dict.fromkeys(words) if word]
        if not wanted:
            return []
        docs = [doc for doc in self._docs.values() if doc is not None]
        if not docs:
            return []
        document_frequency = {
            word: sum(1 for doc in docs if word in doc.words) for word in wanted
        }
        total = len(docs)
        scored: list[tuple[float, str, ToolDoc]] = []
        for doc in docs:
            name_tokens = [t for t in re.split(r"[-_]", doc.name) if t]
            score = 0.0
            doc_stems = {_stem(word) for word in doc.words}
            for word in wanted:
                if _stem(word) in doc_stems:
                    score += math.log(1.0 + total / (1.0 + document_frequency[word]))
                if any(len(t) >= 3 and (word.startswith(t) or t.startswith(word)) for t in name_tokens):
                    score += 2.5
            if score > 0:
                scored.append((score, doc.name, doc))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [doc for _score, _name, doc in scored[:limit]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_VOCABULARY",
            "tools": {
                name: {"stamp": self._stamps.get(name, ""), "doc": doc.to_dict()}
                for name, doc in self._docs.items()
                if doc is not None
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MachineVocabulary":
        vocabulary = cls(dirs=())
        for name, record in (payload or {}).get("tools", {}).items():
            try:
                vocabulary._docs[name] = ToolDoc.from_dict(record["doc"])
                vocabulary._stamps[name] = str(record["stamp"])
            except (KeyError, TypeError, ValueError):
                continue
        return vocabulary


# --------------------------------------------------------------------------- #
# what a goal sentence means                                                   #
# --------------------------------------------------------------------------- #

_UNITS: dict[str, str] = {}
for _word in ("character", "characters", "char", "chars", "letter", "letters"):
    _UNITS[_word] = "character"
for _word in ("word", "words", "token", "tokens"):
    _UNITS[_word] = "word"
for _word in ("line", "lines", "row", "rows", "record", "records"):
    _UNITS[_word] = "line"
for _word in ("byte", "bytes"):
    _UNITS[_word] = "byte"

_VERBS = {
    "reverse": {"reverse", "reversed", "flip", "flipped", "backward", "backwards", "invert", "inverted"},
    "sort": {"sort", "sorted", "order", "ordered", "arrange", "arranged", "alphabetical", "alphabetically"},
    # "number the lines" asks for line numbers; "the number of lines" asks for
    # a count.  The two are told apart by the partitive "of", not by a guess.
    "count": {"count", "counted", "tally", "total"},
    "number": {"number", "numbered", "numbering"},
    "unique": {"unique", "distinct", "deduplicate", "deduplicated", "dedupe"},
    "upper": {"upper", "uppercase", "capital", "capitalized", "shout"},
    "lower": {"lower", "lowercase", "downcase"},
    "squeeze": {"squeeze", "squeezed", "collapse", "collapsed", "compress", "compressed", "shrink", "shrunk", "normalize", "normalized"},
    "head": {"first", "head", "top"},
    "tail": {"last", "tail", "bottom"},
}

_SCOPE_PER = {"each", "every", "per", "within"}


@dataclass(frozen=True)
class Reading:
    """One way to read a goal, with the exact output that reading implies.

    ``scope`` is ``"per"`` when the verb applies inside each unit ("reverse each
    line") and ``"sequence"`` when it applies to the units themselves ("reverse
    the lines").  Different scopes imply different answers, so they are
    different readings -- never one guess.
    """

    verb: str
    unit: str
    scope: str
    count: int | None = None
    words: tuple[str, ...] = ()

    def key(self) -> str:
        return f"{self.verb}:{self.unit}:{self.scope}" + (f":{self.count}" if self.count else "")

    def describe(self) -> str:
        scope = "each " if self.scope == "per" else ""
        return f"{self.verb} {scope}{self.unit}" + (f" {self.count}" if self.count else "")

    def expected(self, source: str) -> str | None:
        """The exact bytes this reading demands, or ``None`` if not decidable."""
        lines = source.split("\n")
        trailing_newline = source.endswith("\n") or source == ""
        if source and not trailing_newline:
            # Every line-shaped tool ends its output with a newline.  A file
            # without one is still a legitimate input; the reading stays exact.
            trailing_newline = True
        body = lines[:-1] if source.endswith("\n") else lines
        if self.verb == "reverse":
            if self.unit == "character" and self.scope == "per":
                return "\n".join(line[::-1] for line in body) + ("\n" if body else "")
            if self.unit == "line" and self.scope == "sequence":
                return "\n".join(reversed(body)) + ("\n" if body else "")
            if self.unit == "word" and self.scope == "per":
                return "\n".join(" ".join(reversed(line.split(" "))) for line in body) + ("\n" if body else "")
            return None
        if self.verb == "sort":
            if self.unit in ("line",):
                return "\n".join(sorted(body, key=lambda line: line.encode())) + ("\n" if body else "")
            if self.unit == "word":
                return "\n".join(sorted(source.split(), key=lambda word: word.encode())) + ("\n" if source.split() else "")
            return None
        if self.verb == "unique":
            if self.unit == "line":
                seen: set[str] = set()
                kept = [line for line in body if not (line in seen or seen.add(line))]
                return "\n".join(kept) + ("\n" if kept else "")
            if self.unit == "word":
                seen = set()
                kept = [word for word in source.split() if not (word in seen or seen.add(word))]
                return "\n".join(kept) + ("\n" if kept else "")
            return None
        if self.verb == "number":
            # Every line gets a number, right-aligned in six columns and
            # separated by a tab -- the layout `nl` produces.  The reading says
            # what the goal means; whether this machine can produce it is a
            # separate question, answered by running something.
            if self.unit != "line":
                return None
            numbered = [f"{index:>6}\t{line}" for index, line in enumerate(body, start=1)]
            return "\n".join(numbered) + ("\n" if numbered else "")
        if self.verb == "count":
            if self.unit == "line":
                return f"{len(body)}\n"
            if self.unit == "word":
                return f"{len(source.split())}\n"
            if self.unit == "character":
                return f"{len(source)}\n"
            if self.unit == "byte":
                return f"{len(source.encode('utf-8'))}\n"
            return None
        if self.verb == "upper":
            return source.upper()
        if self.verb == "lower":
            return source.lower()
        if self.verb == "squeeze":
            if self.unit in ("character", "byte"):
                return re.sub(r"\s+", " ", source)
            return None
        if self.verb in ("head", "tail") and self.count:
            chosen = body[: self.count] if self.verb == "head" else body[-self.count :]
            return "\n".join(chosen) + ("\n" if chosen else "")
        return None


def _goal_tokens(goal: str, path: str | None = None) -> list[str]:
    """The words of a goal, with the file it names removed.

    The name is removed as a *word*, not as a substring.  Comparing by
    substring turned the file `n.txt` into the rule "delete every letter n",
    which silently mangled the goal ("lines" became "lies") and made a
    perfectly clear request ambiguous.
    """
    text = goal.lower()
    if path:
        fragments = {path, Path(path).name, Path(path).stem, Path(path).suffix.lstrip(".")}
        for fragment in sorted((f for f in fragments if len(f) >= 3), key=len, reverse=True):
            text = re.sub(
                r"(?<![a-z0-9_])" + re.escape(fragment.lower()) + r"(?![a-z0-9_])", " ", text
            )
    return re.findall(r"[a-z][a-z0-9_]*|\d+", text)


def readings(goal: str, *, path: str | None = None) -> list[Reading]:
    """Every reading of a goal that this creature can decide exactly.

    Returns an empty list when no verb in the sentence is understood -- an
    honest "I do not know what this asks for" rather than a guess.
    """
    tokens = _goal_tokens(goal, path)
    if not tokens:
        return []
    token_set = set(tokens)
    pairs = set(zip(tokens, tokens[1:]))
    verbs = [verb for verb, words in _VERBS.items() if token_set & words]
    if ("number", "of") in pairs:
        # "the number of lines" is a quantity, not an enumeration.
        verbs = [verb for verb in verbs if verb != "number"]
        if "count" not in verbs:
            verbs.append("count")
    if not verbs:
        return []
    unit = next((_UNITS[t] for t in tokens if t in _UNITS), None)
    per_scope = bool(token_set & _SCOPE_PER)
    count = next((int(t) for t in tokens if t.isdigit()), None)
    words = tuple(
        t for t in tokens if not t.isdigit() and (t not in _STOP or t in _UNITS)
    )
    # Every content word of the sentence must be part of what a reading
    # explains.  Otherwise the goal says something the creature would silently
    # drop -- "number the lines in roman numerals" is not answered by Arabic
    # numerals, and "sort in descending order" is not answered by ascending
    # order.  Refusing is honest; answering a different question is not.
    explained: set[str] = set(_STOP)
    for synonyms in _VERBS.values():
        explained |= synonyms
    explained |= set(_UNITS) | _SCOPE_PER
    uncovered = [
        token for token in tokens if token not in explained and not token.isdigit()
    ]
    if uncovered:
        return []

    found: list[Reading] = []
    for verb in verbs:
        if verb in ("head", "tail"):
            if count:
                found.append(Reading(verb, unit or "line", "sequence", count=count, words=words))
            continue
        if verb in ("upper", "lower"):
            found.append(Reading(verb, unit or "character", "sequence", words=words))
            continue
        if verb in ("count", "sort", "unique", "number"):
            found.append(Reading(verb, unit or "line", "sequence", words=words))
            continue
        if verb == "squeeze":
            found.append(Reading(verb, unit or "character", "sequence", words=words))
            continue
        # reverse: scope changes *what* is reversed, not just how.
        #   "reverse each line"  -> the characters inside every line
        #   "reverse the lines"  -> the order of the lines themselves
        # "each"/"every"/"per" is what distinguishes them; without it the
        # sentence is genuinely ambiguous and both readings stay live.
        if unit == "character":
            if per_scope:
                found.append(Reading(verb, "character", "per", words=words))
            continue
        if unit == "word":
            found.append(Reading(verb, "word", "per" if per_scope else "sequence", words=words))
            continue
        if unit == "line":
            if per_scope:
                found.append(Reading(verb, "character", "per", words=words))
            else:
                found.append(Reading(verb, "line", "sequence", words=words))
            continue
        # No unit named: both readings are live, and the computer decides.
        found.append(Reading("reverse", "line", "sequence", words=words))
        found.append(Reading("reverse", "character", "per", words=words))
    return [reading for reading in found if reading.expected("a\nb\n") is not None]


# --------------------------------------------------------------------------- #
# a discovered tool as a pipeline stage                                        #
# --------------------------------------------------------------------------- #


def tool_stage(tool: str, run: Callable[[str], str]) -> Any:
    """A ``Stage`` whose model of the tool is the tool itself.

    The synthesiser's other stages are hand-modelled interpreters, which is safe
    only because the real shell re-checks the winner.  A discovered tool has no
    model, so its model *is* a real execution, memoised per input: the search
    orders hypotheses with the truth, and never pretends to know more.
    """
    from canonical.runtime.shell_synthesis_v1 import LINES, Stage

    memo: dict[str, str] = {}

    def apply(text: str) -> str:
        if text not in memo:
            memo[text] = run(text)
        return memo[text]

    return Stage(tool, LINES, LINES, apply)


__all__ = [
    "SCHEMA",
    "SYSTEM_DIRS",
    "DENY",
    "DiscoveryError",
    "ToolDoc",
    "MachineVocabulary",
    "Reading",
    "parse_help",
    "readings",
    "tool_stage",
]
