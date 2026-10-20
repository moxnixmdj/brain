"""Living agent V1: one creature that acts, learns, remembers and repairs.

The agent is deliberately not a pipeline of named task handlers.  It has:

- one computer surface (a confined POSIX shell + filesystem);
- one skill representation (a parameterized action template plus an executable
  postcondition), learned by chunking a demonstration;
- one memory (skills, episodes, facts) with *learned* salience;
- one loop: retrieve -> bind -> act -> check -> learn -> consolidate.

Novel behaviour worth naming:

- **One-shot chunking**: a single demonstrated success becomes a parameterized
  skill whose slots are inferred from the demonstration's bindings.  It is then
  replayed on fresh inputs before it is admitted.
- **Self-monitoring and drift repair**: every skill keeps a canary.  A silent
  environment change is detected by re-running the canary; the agent probes the
  changed tool and searches for an adapted command that restores the canary.
- **Word learning**: one demonstration binds a new verb to a skill; later goals
  using that verb resolve correctly, and before the demonstration the same goal
  fails closed.
- **Self-directed practice**: the agent chooses its own practice inputs
  (maximizing coverage of untested parameter regions) and updates calibrated
  confidence from the outcomes.

Boundaries: no model, no network, $0 spend, no claim of terminal capability.
A skill admitted here is a *sandbox* mechanism until an independent oracle has
verified it on untouched instances.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import living_discovery_v1 as discovery
from canonical.runtime import shell_synthesis_v1 as synthesis
from canonical.runtime.living_core_v1 import (
    SCHEMA as CORE_SCHEMA,
    DecisionList,
    LivingCoreError,
    Memory,
    expr_columns,
    induce_decisions,
    Table,
    apply_program,
    induce,
    program_to_json,
)

SCHEMA = "PROJECT_BRAIN_LIVING_AGENT_V1"

_STDOUT_CAP = 4_000_000
_STDERR_CAP = 200_000

_ALLOWED_BINARIES = {
    "awk", "basename", "cat", "cut", "dirname", "find", "grep", "head", "ls",
    "md5sum", "nl", "printf", "sed", "sha256sum", "sort", "tail", "tr", "uniq",
    "wc",
}


class AgentError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# computer surface                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str
    seconds: float
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.truncated


class Computer:
    """A real, confined POSIX computer surface.

    Commands are executed by ``/bin/sh`` inside one root directory with a
    scrubbed environment.  Only an explicit binary vocabulary is admitted, and
    network-capable or state-escaping utilities are absent.  Paths are confined
    to the root by resolving every word that looks like a path.
    """

    def __init__(
        self, root: str | Path, *, timeout: float = 6.0, bin_dir: str | Path | None = None
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.timeout = float(timeout)
        self.bin_dir = None
        if bin_dir is not None:
            self.bin_dir = self.path(str(bin_dir))
            self.bin_dir.mkdir(parents=True, exist_ok=True)
        # The starting vocabulary is a floor, not a ceiling: ``admit`` extends
        # it with a real binary found on this machine, recording the evidence.
        self._admitted: set[str] = set(_ALLOWED_BINARIES)
        self.admissions: dict[str, dict[str, Any]] = {}
        self._digests: dict[tuple[str, str], str] = {}

    def search_dirs(self) -> list[str]:
        """The directories this computer will look in, nearest first."""
        dirs = [str(self.bin_dir)] if self.bin_dir is not None else []
        return dirs + ["/usr/local/bin", "/usr/bin", "/bin"]

    def admit(self, binary: str, *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Admit one real, read-only binary discovered on this machine.

        Admission is an explicit, auditable act: the binary must exist in a
        directory this computer searches, must not be a state-changing or
        network tool, and the evidence that justified it (its own help text and
        the exact result it reproduced) is stored next to it.
        """
        name = str(binary)
        if name in self.admissions:
            return dict(self.admissions[name])
        if name in discovery.DENY:
            raise AgentError("BINARY_REFUSED_STATEFUL:" + name)
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,24}", name):
            raise AgentError("BINARY_NAME_INVALID:" + name)
        located = None
        for directory in self.search_dirs():
            candidate = Path(directory) / name
            try:
                if candidate.is_file() and candidate.stat().st_mode & 0o111:
                    located = candidate
                    break
            except OSError:
                continue
        if located is None:
            raise AgentError("BINARY_NOT_ON_THIS_MACHINE:" + name)
        # Hashing a binary is the expensive part of admission, and the same
        # few tools are admitted over and over while a hypothesis is searched.
        # The digest is keyed by the file's own identity and is recomputed if
        # the binary changes, so the cache can never outlive the evidence.
        try:
            stat = located.stat()
            stamp = f"{stat.st_size}:{int(stat.st_mtime)}:{stat.st_ino}"
        except OSError:
            stamp = "missing"
        cached = self._digests.get((str(located), stamp))
        if cached is not None:
            digest = cached
        else:
            digest = hashlib.sha256(located.read_bytes()).hexdigest()
            self._digests[(str(located), stamp)] = digest
        record = {
            "binary": name,
            "path": str(located),
            "sha256": digest,
            "evidence": dict(evidence or {}),
            "admitted_at": time.time(),
        }
        self._admitted.add(name)
        self.admissions[name] = record
        return dict(record)

    def revoke(self, binary: str) -> None:
        """Withdraw an admission that did not survive verification."""
        self.admissions.pop(str(binary), None)
        if str(binary) not in _ALLOWED_BINARIES:
            self._admitted.discard(str(binary))

    def admitted(self) -> tuple[str, ...]:
        return tuple(sorted(self._admitted))

    # -- files ------------------------------------------------------------
    def path(self, relative: str | Path) -> Path:
        candidate = (self.root / str(relative)).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise AgentError("PATH_ESCAPES_SANDBOX:" + str(relative))
        return candidate

    def write(self, relative: str, text: str) -> Path:
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read(self, relative: str) -> str:
        return self.path(relative).read_text(encoding="utf-8")

    def exists(self, relative: str) -> bool:
        return self.path(relative).exists()

    def listdir(self, relative: str = ".") -> list[str]:
        path = self.path(relative)
        return sorted(p.name for p in path.iterdir())

    # -- execution --------------------------------------------------------
    def _admit(self, command: str) -> None:
        if not isinstance(command, str) or not command.strip():
            raise AgentError("COMMAND_EMPTY")
        if "\x00" in command or "\n" in command:
            raise AgentError("COMMAND_CONTROL_CHARACTER")
        # The only substitution a command may contain is the literal TAB, which
        # has no direct spelling in a shell string and no other portable one.
        # Anything else -- $(...), backticks -- would run a program the
        # admission check never saw, so it is refused as an escape.
        if command.count(_TAB_SPELLING) != command.count("$("):
            raise AgentError("COMMAND_SUBSTITUTION_REFUSED")
        if "`" in command:
            raise AgentError("COMMAND_SUBSTITUTION_REFUSED")
        for segment in _segments(command):
            words = shlex.split(segment.strip()) if segment.strip() else []
            index = 0
            while index < len(words) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[index]):
                index += 1
            if index >= len(words):
                continue
            binary = words[index]
            if binary not in self._admitted:
                raise AgentError("BINARY_NOT_ADMITTED:" + binary)
        for operator in (">", "<"):
            if operator in command:
                for target in re.findall(re.escape(operator) + r"\s*([^\s|;&]+)", command):
                    if target.startswith("&"):
                        continue
                    self.path(target)
        for word in re.findall(r"[^\s|;&<>]+", command):
            if word.startswith("/") or ".." in word or word.startswith("~"):
                self.path(word)

    def run(self, command: str, *, cwd: str | None = None, stdin: str | None = None) -> CommandResult:
        self._admit(command)
        workdir = self.path(cwd or ".")
        workdir.mkdir(parents=True, exist_ok=True)
        search = "/usr/local/bin:/usr/bin:/bin"
        if self.bin_dir is not None:
            search = str(self.bin_dir) + ":" + search
        env = {
            "PATH": search,
            "HOME": str(self.root),
            "TMPDIR": str(self.root / ".tmp"),
            "LC_ALL": "C",
            "PYTHONHASHSEED": "0",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
        (self.root / ".tmp").mkdir(exist_ok=True)
        started = time.perf_counter()
        # A machine contains tools that write forever (`yes`, `seq inf`), and a
        # candidate is chosen by a keyword match long before anything is known
        # about it.  Reading its output with an unbounded pipe turns one bad
        # guess into a memory bomb -- this process was OOM-killed once by
        # exactly that.  The readers therefore *drain* without keeping more
        # than a cap, the child is killed at the deadline, and a truncated or
        # timed-out run is reported as a failure rather than as an answer.
        import threading

        handle = None
        try:
            if stdin is None:
                source: Any = subprocess.DEVNULL
            else:
                handle = tempfile.TemporaryFile()
                handle.write(stdin.encode("utf-8"))
                handle.seek(0)
                source = handle
            process = subprocess.Popen(
                ["/bin/sh", "-c", command],
                cwd=workdir,
                env=env,
                stdin=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            sink: dict[str, list[bytes]] = {"out": [], "err": []}
            overflow = {"out": False, "err": False}

            def drain(stream: Any, key: str, limit: int) -> None:
                kept = 0
                for block in iter(lambda: stream.read(65536), b""):
                    if kept < limit:
                        take = block[: limit - kept]
                        sink[key].append(take)
                        kept += len(take)
                        if kept >= limit:
                            # The output is already unusable, and a tool that
                            # filled the cap will fill it again: stop it now
                            # rather than waiting out the deadline.  `yes`
                            # reaches this in microseconds.
                            overflow[key] = True
                            process.kill()
                stream.close()

            readers = [
                threading.Thread(target=drain, args=(process.stdout, "out", _STDOUT_CAP), daemon=True),
                threading.Thread(target=drain, args=(process.stderr, "err", _STDERR_CAP), daemon=True),
            ]
            for reader in readers:
                reader.start()
            timed_out = False
            try:
                code = process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                timed_out = True
                code = 124
            for reader in readers:
                reader.join(timeout=1.0)
            out = b"".join(sink["out"]).decode("utf-8", "replace")
            err = b"".join(sink["err"]).decode("utf-8", "replace")
            if timed_out:
                return CommandResult(124, out[-20_000:], "TIMEOUT", time.perf_counter() - started, truncated=True)
            return CommandResult(
                code,
                out,
                err,
                time.perf_counter() - started,
                truncated=overflow["out"] or overflow["err"],
            )
        finally:
            if handle is not None:
                handle.close()


# --------------------------------------------------------------------------- #
# skills                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class ShellSkill:
    skill_id: str
    description: str
    template: str
    slots: dict[str, str]
    postcondition: str
    canary_input: dict[str, str]
    canary_expected: str
    keywords: list[str] = field(default_factory=list)
    properties: list[str] = field(default_factory=list)
    version: int = 1
    tries: int = 0
    successes: int = 0
    last_probe_seconds: float = 0.0
    repair_history: list[dict[str, Any]] = field(default_factory=list)

    def bind(self, bindings: Mapping[str, str]) -> str:
        missing = [slot for slot in self.slots if slot not in bindings]
        if missing:
            raise AgentError("SLOT_BINDING_MISSING:" + ",".join(missing))
        command = self.template
        for slot, value in bindings.items():
            command = command.replace("{" + slot + "}", shlex.quote(str(value)))
        return command

    def text(self) -> str:
        return " ".join([self.description, *self.keywords, *self.slots.keys()])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_SHELL_SKILL",
            "skill_id": self.skill_id,
            "description": self.description,
            "template": self.template,
            "slots": dict(self.slots),
            "postcondition": self.postcondition,
            "canary_input": dict(self.canary_input),
            "canary_expected": self.canary_expected,
            "keywords": list(self.keywords),
            "properties": list(self.properties),
            "version": self.version,
            "tries": self.tries,
            "successes": self.successes,
            "repair_history": list(self.repair_history),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ShellSkill":
        return cls(
            skill_id=str(payload["skill_id"]),
            description=str(payload["description"]),
            template=str(payload["template"]),
            slots={str(k): str(v) for k, v in payload["slots"].items()},
            postcondition=str(payload["postcondition"]),
            canary_input={str(k): str(v) for k, v in payload["canary_input"].items()},
            canary_expected=str(payload["canary_expected"]),
            keywords=[str(x) for x in payload.get("keywords", [])],
            properties=[str(x) for x in payload.get("properties", [])],
            version=int(payload.get("version", 1)),
            tries=int(payload.get("tries", 0)),
            successes=int(payload.get("successes", 0)),
            repair_history=list(payload.get("repair_history", [])),
        )


_SORT_WORDS = {"sort", "sorted", "order", "ordered", "alphabetical", "alphabetically"}
_UNIQUE_WORDS = {"unique", "distinct", "deduplicate", "dedupe", "dedup", "duplicate", "duplicates"}
_COUNT_WORDS = {"count", "tally", "total"}
_LOWER_WORDS = {"lower", "lowercase"}
_UPPER_WORDS = {"upper", "uppercase"}
_WORD_WORDS = {"word", "words", "vocabulary", "tokens"}


def _properties_from_goal(goal: str) -> list[str]:
    """Read the *checkable* intent out of a goal, and nothing more.

    A property is admitted only when its satisfaction can be decided from the
    produced text itself.  "Make it nice" has no property, so it fails closed
    instead of inventing an interpretation.
    """
    tokens = _tokens(goal)
    words = re.findall(r"[a-z]+", goal.lower())
    pairs = set(zip(words, words[1:]))
    properties: list[str] = []
    # "the number of lines" is a count; "number the lines" asks for line
    # numbers.  Sharing the word "number" between them is not a reason to
    # return a count for a request that never asked for one.
    if tokens & _COUNT_WORDS or ("how", "many") in pairs or ("number", "of") in pairs:
        properties.append("count")
    if tokens & _SORT_WORDS:
        properties.append("sorted")
    if tokens & _UNIQUE_WORDS:
        properties.append("unique")
    if tokens & _LOWER_WORDS:
        properties.append("lower")
    elif tokens & _UPPER_WORDS:
        properties.append("upper")
    if tokens & _WORD_WORDS:
        properties.append("words")
    return properties


def _segments(command: str) -> list[str]:
    """Split a command on shell operators, respecting quotes.

    A naive split on "|" corrupts ``cut -d'|' -f2`` -- there the pipe is data,
    not an operator -- and the admission check would reject or mis-parse a
    legitimate command.
    """
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            index += 1
            continue
        if char in ("|", ";", "&"):
            segments.append("".join(current))
            current = []
            index += 2 if command[index:index + 2] in ("||", "&&") else 1
            continue
        current.append(char)
        index += 1
    segments.append("".join(current))
    return segments


def _lines(text: str) -> list[str]:
    """Exactly the shell's notion of a line: the text split on \\n only.

    ``str.splitlines`` also splits on form feed, U+0085 and U+2028, which the
    shell does not; using it here would silently disagree with the tools.
    """
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _check_properties(properties: Sequence[str], output: str) -> bool:
    lines = _lines(output)
    for prop in properties:
        if prop == "sorted":
            if any(a > b for a, b in zip(lines, lines[1:])):
                return False
        elif prop == "unique":
            if len(set(lines)) != len(lines):
                return False
        elif prop == "count":
            if not re.fullmatch(r"-?\d+", output.strip()):
                return False
        elif prop == "lower":
            if output != output.lower():
                return False
        elif prop == "upper":
            if output != output.upper():
                return False
        elif prop == "words":
            continue  # a tokenization convention, not an assertion
        else:
            return False
    return True


def _conserves(properties: Sequence[str], source: str, output: str) -> bool:
    """A transformation may rearrange or select; it may not invent content.

    For sorted/unique goals over words, the multiset or set of words must be
    preserved.  That single check rejects pipelines that "succeed" by
    dropping data.
    """
    if "count" in properties:
        return True
    if "words" in properties:
        before = set(source.split())
        after = set(output.split())
    else:
        before = set(_lines(source))
        after = set(_lines(output))
    if "unique" in properties:
        return after == before
    if "sorted" in properties:
        return sorted(_lines(output)) == sorted(_lines(source)) if "words" not in properties else before == after
    return True


_LAST_WORDS = {"last", "later", "final", "second", "third", "tail"}


_DIRECTIVES = {
    "list", "show", "print", "display", "give", "keep", "only", "remove", "delete",
    "make", "get", "produce", "return", "turn", "change", "convert", "put", "want",
    # "ascending" is what sorting means here; "descending" is a different
    # mechanism and is not silently ignored.
    "ascending",
    # function words that carry no content of their own
    "how", "many", "are", "is", "there", "does", "do", "its", "into", "than",
    # generic words for "the thing being worked on"
    "text", "content", "contents", "data", "file", "files", "input", "output", "result",
}
_PROPERTY_WORDS = (
    _COUNT_WORDS | _SORT_WORDS | _UNIQUE_WORDS | _LOWER_WORDS | _UPPER_WORDS | _WORD_WORDS
)


def _unexplained_words(goal: str, properties: Sequence[str], path: str = "") -> list[str]:
    """Words the stated properties do not account for.

    A goal is only answered when what it *says* is what the answer *does*.
    "sort the lines in descending order" names the same property as "sort the
    lines" and asks for the opposite result; answering ascending order would be
    a right answer to a different question.
    """
    # Units ("lines", "words") and the partitive "number of" are content the
    # properties already account for.
    explained = (
        set(_STOP)
        | _DIRECTIVES
        | _PROPERTY_WORDS
        | set(discovery._UNITS)
        | set(discovery._SCOPE_PER)
        | {"number"}
    )
    text = goal
    if path:
        fragments = {path, Path(path).name, Path(path).stem, Path(path).suffix.lstrip(".")}
        for fragment in sorted((f for f in fragments if len(f) >= 3), key=len, reverse=True):
            text = re.sub(
                r"(?<![A-Za-z0-9_])" + re.escape(fragment) + r"(?![A-Za-z0-9_])", " ", text
            )
    return sorted({word for word in _tokens(text) if word not in explained})


_NUMBER_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}


_UNIT_NOUNS = (
    "line", "lines", "row", "rows", "column", "columns", "field", "fields",
    "word", "words", "byte", "bytes", "character", "characters", "char", "chars",
    "letter", "letters", "digit", "digits", "item", "items", "element", "elements",
)


# A request can name the character that separates its data.  Naming it is not
# the same as describing the data: "comma separated" says which character the
# answer must use, and a pipeline that never mentions a comma has not answered.
# A TAB cannot be written into a command: a literal one is a control character
# and a shell has no portable escape for it.  This one substitution is the
# portable spelling, and it is the only one the machine will execute.
_TAB_SPELLING = "\"$(printf '\\t')\""


def _shell_spelling(part: str) -> str:
    """How a bound argument is written for the shell.

    A TAB is spelled as the one substitution the admission check allows; every
    other argument is quoted so it stays data.  `-t |` is a pipe unless it is
    quoted, and then the file name becomes the next command.
    """
    if part == "\t":
        return _TAB_SPELLING
    return shlex.quote(part)


_SEPARATOR_WORDS = {
    "comma": ",", "commas": ",",
    "pipe": "|", "pipes": "|",
    "tab": "\t", "tabs": "\t",
    "semicolon": ";", "semicolons": ";",
    "colon": ":", "colons": ":",
    "space": " ", "spaces": " ", "blank": " ", "blanks": " ",
    # Punctuation has names too, and a request that says "with a star" names
    # `*` just as exactly as one that says "with a comma" names `,`.  Without
    # these, a class translation such as "replace every digit with a star" has
    # nothing to translate *into*.
    "star": "*", "stars": "*", "asterisk": "*", "asterisks": "*",
    "dot": ".", "dots": ".", "period": ".", "periods": ".",
    "dash": "-", "dashes": "-", "hyphen": "-", "hyphens": "-", "minus": "-",
    "underscore": "_", "underscores": "_",
    "slash": "/", "slashes": "/", "hash": "#", "pound": "#",
    "percent": "%", "tilde": "~", "caret": "^",
    "exclamation": "!",
    # Words that are also ordinary English are deliberately absent: "at" is a
    # preposition in "fold each line at 40 characters", and taking it for `@`
    # made every sentence containing it name a character it never mentioned.
    # A name earns its place here only if it cannot be read as anything else.
}


# What a request *asks for* that a stage can be checked against: a selection of
# the first or last N rows, a set of distinct values, a count.  Each entry is
# (the words the request used, how every way of doing it is written).  This is
# a reading of the sentence, not a task table: the pipeline may satisfy it in
# any of the spellings the machine offers.
_SELECTION = re.compile(
    r"\b(first|top|last|bottom)\s+(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b"
)


# Where in the pipeline a selection belongs is part of the sentence, not a
# preference: "keep the first two" happens to what the transformation left,
# while "take the first four rows" is what the transformation starts from.
# The verbs the sentence uses are the evidence for which it is.
_PREFIX_VERBS = {"take", "read", "use", "consider", "starting", "beginning", "from", "among"}
_SUFFIX_VERBS = {"keep", "leave", "retain", "show", "output", "print", "return", "give", "report"}
_SKIP_BEFORE = {"the", "only", "just", "and", "then", "a", "an", "of", "these", "those"}


_PER_LINE = re.compile(r"\b(each|every|per)\s+line\b")
_EDGE_CHARS = re.compile(
    r"\b(first|last|leading|trailing)\s+(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"\s+(?:characters|character|chars|bytes|letters)\b"
    r"|\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:characters|character|chars)"
    r"\s+from\s+the\s+(start|beginning|end)\b"
)
_CHARACTER_NOUNS = ("characters", "character", "chars", "letters", "bytes", "byte")

# Names of *sets* of characters, and the sets they name.  "Replace every digit
# with a star" names no character at all -- it names a class -- and `tr` takes
# exactly such a set.  This is vocabulary of the same kind as knowing that
# "comma" is `,`: a fixed, checkable meaning that the bytes still have to
# confirm.
_CHARACTER_CLASSES = {
    "digit": "0-9", "digits": "0-9", "number": "0-9", "numbers": "0-9",
    "letter": "a-zA-Z", "letters": "a-zA-Z",
    "lowercase": "a-z", "lowercaseletter": "a-z", "lowercaseletters": "a-z",
    "uppercase": "A-Z", "uppercaseletter": "A-Z", "uppercaseletters": "A-Z",
    "space": " ", "spaces": " ", "blank": " ", "blanks": " ", "whitespace": " ",
    "vowel": "aeiou", "vowels": "aeiou",
    "consonant": "bcdfghjklmnpqrstvwxyz", "consonants": "bcdfghjklmnpqrstvwxyz",
}
_REPLACE_CLASS = re.compile(
    r"\b(?:replace|change|turn|translate)\s+(?:every|each|all\s+(?:the\s+)?)?"
    r"\s*([a-z]+)\s+(?:with|by|into|to)\s+(?:a\s+|an\s+|the\s+)?([a-z]+)\b"
)
# What a request *counts*, when it says so: the noun is the meaning, and every
# spelling the machine can express that meaning with counts as a match.  A
# single `wc -l` was standing in for all counting; "the number of characters in
# each line" is a count of the same kind and had no spelling at all.
_COUNT_UNIT = re.compile(
    r"\b(?:count|counts|number\s+of|how\s+many)\b[^.\n]*?\b"
    r"(characters|character|chars|letters|bytes|byte|words|word|lines|line|values)\b"
)


def _expand_class(specification: str) -> list[str]:
    """The characters a `tr` set names: ranges, and literal characters.

    `tr` takes sets, not just literals -- `0-9`, `a-z`, and a bare `-` at the
    end.  The interpreter has to expand them the same way POSIX does or the two
    halves of the verification would disagree on exactly the interesting cases.
    """
    out: list[str] = []
    index = 0
    while index < len(specification):
        if index + 2 < len(specification) and specification[index + 1] == "-":
            low, high = specification[index], specification[index + 2]
            out.extend(chr(code) for code in range(ord(low), ord(high) + 1))
            index += 3
        else:
            out.append(specification[index])
            index += 1
    return out


def _translate_sets(text: str, source: str, target: str) -> str:
    """`tr SOURCE TARGET`, byte for byte, with the padding rule tr uses."""
    source_chars = _expand_class(source)
    target_chars = _expand_class(target)
    if not source_chars or not target_chars:
        return text
    mapping = {
        char: target_chars[index] if index < len(target_chars) else target_chars[-1]
        for index, char in enumerate(source_chars)
    }
    return "".join(mapping.get(char, char) for char in text)


def _requested_operations(goal: str) -> list[tuple[str, str, str]]:
    """Operations the sentence names: (label, stage spellings, where it belongs).

    "Keep the first two" fixes an operation no matter what the examples show,
    and it fixes *where* it happens: after the transformation.  On two rows,
    "keep the first two, sorted by the third column" is byte-identical to
    "sort those two by the third column" -- and on a third row it is not.
    The second element is every spelling of that *meaning* this machine offers,
    not one chosen command: a count of characters is `wc -m` for the whole text
    and `awk length` per line, and both are the operation the sentence named.
    Only readings the sentence states outright are listed; anything vaguer is
    left to the bytes.
    """
    text = goal.lower()
    per_line = bool(_PER_LINE.search(text))
    requested: list[tuple[str, str, str]] = []
    for match in _SELECTION.finditer(text):
        direction, amount = match.group(1), match.group(2)
        count = int(amount) if amount.isdigit() else _NUMBER_WORDS[amount]
        after = text[match.end(): match.end() + 24]
        if re.match(r"\s*(?:characters|character|chars|letters|bytes|byte)\b", after):
            # A slice, not a row selection: the sentence says how much of each
            # line survives, so the stage belongs wherever the text is a line.
            side = "first" if direction in {"first", "top"} else "last"
            # `cut -c 1-3` and `cut -c 3` both keep the first three characters;
            # `cut -c -3` is the last three, which is a different answer.
            spelled = (
                rf"\bcut\s+-c\s*(?:1-)?{count}\b|\bsubstr\s*\("
                if side == "first"
                else rf"\bcut\s+-c\s*-{count}\b|\bsubstr\s*\(|\bsed\b[^|]*\b{count}\b"
            )
            requested.append((f"{side} {count} characters", spelled, "any"))
            continue
        before = re.findall(r"[a-z]+", text[max(0, match.start() - 24): match.start()])
        verb = ""
        for word in reversed(before):
            if word in _SKIP_BEFORE:
                continue
            verb = word
            break
        role = "prefix" if verb in _PREFIX_VERBS else "suffix"
        if direction in {"first", "top"}:
            requested.append((f"first {count}", rf"\bhead\s+-n\s*\+?{count}\b", role))
        else:
            requested.append((f"last {count}", rf"\btail\s+-n\s*{count}\b", role))
    if re.search(r"\b(distinct|unique)\b", text):
        requested.append(("distinct values", r"\bsort\s+-u\b|\buniq\b", "any"))
    counted = _COUNT_UNIT.search(text)
    distinct_requested = re.search(r"\b(distinct|unique)\b", text) is not None
    if re.search(r"\b(count|counts|how many|number of)\b", text):
        # "How many distinct words" counts a *set*: once the stream has one
        # word per line and the duplicates are gone, counting lines *is*
        # counting words.  The unit noun belongs to the thing being made
        # distinct, not to the arithmetic, so the generic count is the right
        # reading -- requiring `wc -w` would refuse the correct pipeline.
        unit = (counted.group(1) if counted else "") if not distinct_requested else ""
        if unit in {"characters", "character", "chars", "letters", "bytes", "byte"}:
            if per_line:
                requested.append(("a count of the characters in each line",
                                  r"\bawk\b[^|]*\blength\s*\(", "any"))
            else:
                requested.append(("a count of characters", r"\bwc\s+-[mc]\b", "any"))
        elif unit in {"words", "word"}:
            if per_line:
                requested.append(("a count of the words in each line", r"\bawk\b[^|]*\bNF\b", "any"))
            else:
                requested.append(("a count of words", r"\bwc\s+-w\b", "any"))
        else:
            requested.append(("a count", r"\bwc\s+-l\b", "any"))
    return requested


def _ordinal_positions(goal: str) -> list[int]:
    """Positions the sentence names *of* something ("the second column").

    An ordinal next to a unit noun is a position; a bare ordinal is usually an
    enumeration ("the first two rows").  Only the first kind is evidence for a
    key or a field index.
    """
    words = re.findall(r"[a-z]+", goal.lower())
    found: list[int] = []
    for index, word in enumerate(words):
        value = _NUMBER_WORDS.get(word)
        if value is None or word not in {
            "first", "second", "third", "fourth", "fifth", "sixth",
            "seventh", "eighth", "ninth", "tenth",
        }:
            continue
        following = words[index + 1] if index + 1 < len(words) else ""
        if following in _UNIT_NOUNS:
            found.append(value)
    return found


def _target_for(properties: Sequence[str], text: str, goal: str = "") -> str | None:
    """The unique result the stated properties determine, when there is one."""
    word_mode = "words" in properties
    if word_mode:
        tokens = text.split()
        if "count" in properties:
            return ("%d\n" % len(set(tokens))) if "unique" in properties else ("%d\n" % len(tokens))
        if "unique" in properties:
            return "\n".join(sorted(set(tokens))) + "\n"
        return None
    lines = _lines(text)
    if "count" in properties:
        return "%d\n" % len(lines)
    if "unique" in properties and "sorted" in properties:
        return "\n".join(sorted(set(lines))) + "\n"
    if "unique" in properties:
        # "the unique lines" means: keep the first of each repeated line, in
        # the order the lines appear.  "the last occurrence" is a different
        # goal that shares the word "duplicate"; assuming it would be a wrong
        # answer to a right reading, so it is not assumed.
        if _tokens(goal) & _LAST_WORDS:
            return None
        seen: set[str] = set()
        kept: list[str] = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                kept.append(line)
        return "\n".join(kept) + "\n"
    if "sorted" in properties:
        return "\n".join(sorted(lines)) + "\n"
    if "lower" in properties:
        return text.lower()
    if "upper" in properties:
        return text.upper()
    return None


_STOP = {
    "the", "a", "an", "in", "of", "for", "to", "and", "with", "from", "into",
    "file", "please", "me", "it", "this", "that", "on", "at",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in _STOP and len(t) > 1}


# --------------------------------------------------------------------------- #
# the agent                                                                    #
# --------------------------------------------------------------------------- #


class LivingAgent:
    def __init__(self, root: str | Path, *, computer: Computer | None = None) -> None:
        self.computer = computer or Computer(root)
        self.memory = Memory()
        self.skills: dict[str, ShellSkill] = {}
        self.word_bindings: dict[str, str] = {}
        self.practice_log: list[dict[str, Any]] = []
        self.policies: dict[str, DecisionList] = {}
        self.policy_evidence: dict[str, dict[str, list[dict[str, str]]]] = {}
        # What the creature has learned about *this machine*: which real tools
        # answer which readings of a goal, and the stage models it built from
        # them.  None of this is a task table; every entry was verified by
        # exact bytes before it was recorded.
        self.capabilities: dict[str, dict[str, Any]] = {}
        self._stages: dict[str, Any] = {}
        self._vocabulary: discovery.MachineVocabulary | None = None
        # An audit trail of what was tried and what survived: a rejected tool
        # is evidence of a real experiment, not an absence of one.
        self.discovery_log: list[dict[str, Any]] = []
        # Pure-derivation caches: separators per text, a tool's whole
        # self-description per tool.  Both are recomputed from the machine and
        # the data, never learned, so caching them changes no answer.
        self._separator_cache: dict[str, list[str]] = {}
        self._described_cache: dict[str, set[str]] = {}
        # One invocation on one text is a pure function of the machine: the
        # same binary, the same arguments and the same input produce the same
        # bytes.  Probing it twice is waste, and the search probes the same
        # invocation from several directions (recall, hypotheses, verification).
        self._stage_memo: dict[tuple[tuple[str, ...], str], str] = {}
        # What answered this *kind* of request before: the reading of the
        # sentence (its content words, with the parameters removed) and the
        # mechanism that verified against real bytes.  A cache of experience,
        # never an authority: every reuse is re-verified on the new examples,
        # and a miss demotes the entry instead of trusting it.
        self.mechanisms: dict[str, dict[str, Any]] = {}
        # Stages the creature has *earned*: a documented invocation that was
        # verified on real bytes becomes a word in its grammar, so later goals
        # can be composed from it by pure search instead of being searched for
        # again.  The vocabulary grows from proof, not from configuration.
        self._learned: dict[str, dict[str, Any]] = {}
        self._learned_cache: dict[str, Any] = {}
        self._stage_dir: str | None = None
        # Real process executions, counted so a claim about cost is measured
        # rather than estimated.
        self._runs = 0

    # -- learning ---------------------------------------------------------
    def learn_shell_skill(
        self,
        goal_text: str,
        demonstration_command: str,
        bindings: Mapping[str, str],
        *,
        description: str | None = None,
        canary: tuple[Mapping[str, str], str],
        postcondition: str = r"^\s*\S+",
        keywords: Sequence[str] = (),
    ) -> ShellSkill:
        """Chunk one demonstrated success into a reusable, checked skill.

        The demonstration's literal binding values are replaced by slots; the
        template is then replayed by the caller before admission.  This is the
        SOAR-style impasse->chunk step, made explicit and auditable.
        """
        template = str(demonstration_command)
        inferred_slots: dict[str, str] = {}
        for name, value in sorted(bindings.items(), key=lambda kv: -len(str(kv[1]))):
            literal = str(value)
            quoted = shlex.quote(literal)
            if quoted in template:
                template = template.replace(quoted, "{" + name + "}", 1)
            elif literal in template:
                template = template.replace(literal, "{" + name + "}", 1)
            else:
                raise AgentError("BINDING_NOT_IN_DEMONSTRATION:" + name)
            inferred_slots[name] = literal
        if "{" not in template:
            raise AgentError("DEMONSTRATION_HAS_NO_GENERALIZABLE_ARGUMENT")

        canary_input, canary_expected = canary
        skill_id = "S-" + hashlib.sha256(
            json.dumps(
                {"goal": goal_text, "template": template, "slots": sorted(inferred_slots)},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=description or goal_text,
            template=template,
            slots=inferred_slots,
            postcondition=postcondition,
            canary_input={str(k): str(v) for k, v in canary_input.items()},
            canary_expected=str(canary_expected),
            keywords=sorted({*_tokens(goal_text), *map(str, keywords)}),
        )
        # Prove the skill on the canary *through the template*, not through the
        # raw demonstration, before admitting it.
        if not self._canary_ok(skill):
            raise AgentError("CHUNKED_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        self._resolve_impasse(goal_text)
        self.memory.add(
            "skill",
            " ".join([skill.description, *skill.keywords]),
            {"skill_id": skill_id, "kind": "shell", "template": skill.template},
            confidence=0.7,
            tags=("shell",),
        )
        self.memory.add(
            "episode",
            "learned " + goal_text,
            {"skill_id": skill_id, "outcome": "learned"},
            surprise=0.5,
            tags=("learn",),
        )
        return skill

    def learn_table_skill(
        self,
        goal_text: str,
        demonstrations: Sequence[tuple[Table, Table]],
        query: Callable[[Table], Table | None],
        *,
        seed: int = 0,
    ):
        """Induce a reusable data skill from few demonstrations."""
        result = induce(query, demonstrations, seed=seed)
        if not result.success or result.program is None:
            raise AgentError("TABLE_INDUCTION_FAILED:" + str(result.failure_reason))
        skill_id = "T-" + hashlib.sha256(
            json.dumps(program_to_json(result.program), sort_keys=True).encode()
        ).hexdigest()[:12]
        payload = {
            "skill_id": skill_id,
            "kind": "table",
            "program": program_to_json(result.program),
            "probes": result.probes,
        }
        self.memory.add(
            "skill",
            " ".join([goal_text, "data table csv transform"]),
            payload,
            confidence=0.8,
            tags=("table",),
        )
        return payload, result

    # -- acting -----------------------------------------------------------
    def _canary_bindings(self, skill: ShellSkill) -> dict[str, str]:
        files = sorted(skill.canary_input)
        path_slots = sorted(
            slot
            for slot in skill.slots
            if "path" in slot or "file" in slot or "dir" in slot or slot in ("input", "source")
        )
        if not files or len(files) < len([s for s in path_slots if "dir" not in s]):
            raise AgentError("CANARY_INPUT_MISSING")
        bindings = {slot: value for slot, value in skill.slots.items()}
        parents = [str(Path(name).parent) for name in files]
        common = str(Path(os.path.commonpath(parents))) if len(parents) > 1 else parents[0]
        file_iter = iter(files)
        for slot in path_slots:
            if "dir" in slot:
                bindings[slot] = common if common not in ("", ".") else "."
            else:
                try:
                    bindings[slot] = next(file_iter)
                except StopIteration:
                    raise AgentError("CANARY_INPUT_MISSING")
        return bindings

    def _canary_ok(self, skill: ShellSkill) -> bool:
        for name, content in skill.canary_input.items():
            self.computer.write(name, content)
        command = skill.bind(self._canary_bindings(skill))
        result = self.computer.run(command)
        if not result.ok:
            return False
        produced = result.stdout.strip()
        if not re.search(skill.postcondition, produced, flags=re.MULTILINE):
            return False
        return produced == skill.canary_expected.strip()

    def _open_questions(self) -> list[str]:
        questions = []
        for entry in self.memory.active():
            if entry.kind == "episode" and entry.payload.get("outcome") == "impasse":
                if not entry.payload.get("resolved"):
                    questions.append(str(entry.payload.get("goal", entry.text)))
        return questions

    def open_questions(self) -> list[str]:
        """What the creature knows it does not know, oldest first."""
        return self._open_questions()

    def _record_impasse(self, goal: str, detail: Mapping[str, Any] | None = None) -> None:
        """Put a gap on the record, with whatever is known about its shape.

        An impasse is not an error message: it is a memory.  It names the goal,
        what was understood about it, and what was missing, so the same gap is
        never re-derived from scratch and a single demonstration can close it.
        """
        if goal in self._open_questions():
            return
        payload: dict[str, Any] = {"outcome": "impasse", "goal": goal, "resolved": False}
        if detail:
            payload.update(dict(detail))
        self.memory.add(
            "episode",
            "do not know how to " + goal,
            payload,
            surprise=1.0,
            tags=("impasse",),
        )

    def _resolve_impasse(self, goal_text: str) -> None:
        wanted = _tokens(goal_text)
        for entry in self.memory.active():
            if entry.kind != "episode" or entry.payload.get("outcome") != "impasse":
                continue
            if entry.payload.get("resolved"):
                continue
            if wanted & _tokens(str(entry.payload.get("goal", ""))):
                entry.payload["resolved"] = True
                entry.payload["resolved_by"] = "demonstration"

    def _lookup(self, goal: str) -> tuple[ShellSkill, list[tuple[float, Any]]] | None:
        ranked = self.memory.retrieve(goal, kind="skill", k=6)
        wanted = _tokens(goal)
        overlapping = []
        for score, entry in ranked:
            skill_id = entry.payload.get("skill_id")
            if entry.payload.get("kind") != "shell" or skill_id not in self.skills:
                continue
            skill = self.skills[str(skill_id)]
            if wanted & _tokens(skill.text()):
                overlapping.append((score, entry))
        if not overlapping:
            return None
        return self.skills[str(overlapping[0][1].payload["skill_id"])], overlapping

    def _resolve(self, goal: str) -> tuple[ShellSkill, list[tuple[float, Any]]]:
        found = self._lookup(goal)
        if found is None:
            self._record_impasse(goal)
            raise AgentError("GOAL_UNKNOWN_FAIL_CLOSED")
        return found

    def _bind_from_goal(self, skill: ShellSkill, goal: str, provided: Mapping[str, str] | None) -> dict[str, str]:
        bindings = dict(provided or {})
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", goal)
        plain = [t for t in re.findall(r"[A-Za-z0-9_./\\-]+", goal) if "/" in t or "." in t]
        paths = [*quoted, *plain]
        path_slots = [
            slot
            for slot in skill.slots
            if "path" in slot or "file" in slot or "dir" in slot or slot in ("input", "source")
        ]
        unbound = [slot for slot in path_slots if slot not in bindings]
        if unbound:
            # The goal text must supply every path the caller did not supply.
            if not paths:
                raise AgentError("GOAL_PATH_BINDING_REQUIRED")
            for slot in unbound:
                bindings[slot] = paths[0]
        for slot in skill.slots:
            if slot not in bindings:
                bindings[slot] = skill.slots[slot]
        return bindings

    def _execute(
        self,
        skill: ShellSkill,
        goal: str,
        bindings: Mapping[str, str],
        *,
        ranked_entry_id: str | None = None,
    ) -> dict[str, Any]:
        bound = self._bind_from_goal(skill, goal, bindings)
        command = skill.bind(bound)
        result = self.computer.run(command)

        def passes(res: CommandResult, text: str) -> bool:
            return res.ok and re.search(skill.postcondition, text, flags=re.MULTILINE) is not None

        ok = passes(result, result.stdout)
        if ok and skill.properties:
            ok = _check_properties(skill.properties, result.stdout)
        repaired_now = False
        # The canary is the skill's own regression test.  Only a canary failure
        # means the *tool* changed; a goal-only failure is a bad input or a bad
        # binding and must stay failed instead of being papered over.
        if not self._canary_ok(skill):
            repaired = self._repair(skill)
            repaired_now = repaired
            if repaired:
                command = skill.bind(bound)
                result = self.computer.run(command)
                ok = passes(result, result.stdout) and (
                    _check_properties(skill.properties, result.stdout) if skill.properties else True
                )
        skill.tries += 1
        skill.successes += int(ok)
        if ranked_entry_id is not None:
            self.memory.record_retrieval(goal, ranked_entry_id, success=bool(ok))
        self.memory.add(
            "episode",
            goal,
            {"skill_id": skill.skill_id, "command": command, "success": bool(ok)},
            surprise=0.0 if ok else 1.0,
            cost_saved=1.0 if ok else 0.0,
            tags=("solve",),
        )
        return {
            "status": "PASS" if ok else "FAIL_CLOSED",
            "skill_id": skill.skill_id,
            "version": skill.version,
            "command": command,
            "stdout": result.stdout,
            "text": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.code,
            "repaired": repaired_now,
        }

    def solve(self, goal: str, *, bindings: Mapping[str, str] | None = None) -> dict[str, Any]:
        skill, ranked = self._resolve(goal)
        return self._execute(skill, goal, dict(bindings or {}), ranked_entry_id=ranked[0][1].entry_id)

    # -- drift repair -----------------------------------------------------
    def _repair(self, skill: ShellSkill) -> bool:
        """Detect a changed tool and adapt the command to the same effect."""
        # Observe the raw behaviour of the current tool on the canary.
        raw = self.computer.run(skill.bind(self._canary_bindings(skill)))
        original = skill.template
        wrappers = [
            " | awk '{print $1}'",
            " | grep -oE '[0-9]+([.][0-9]+)?' | head -n1",
            " | sed -E 's/[^0-9]*([0-9]+).*/\\1/'",
            " | tr -dc '0-9\\n' | head -n1",
            " | cut -d' ' -f1",
        ]
        for wrapper in wrappers:
            skill.template = original + wrapper
            try:
                if self._canary_ok(skill):
                    skill.repair_history.append(
                        {
                            "from": original,
                            "to": skill.template,
                            "observed_before": raw.stdout.strip()[:200],
                            "observed_after": self.computer.run(skill.bind(self._canary_bindings(skill))).stdout.strip()[:200],
                        }
                    )
                    skill.version += 1
                    return True
            except AgentError:
                pass
        skill.template = original
        return False

    def self_test(self) -> dict[str, Any]:
        reports = []
        for skill in self.skills.values():
            ok = self._canary_ok(skill)
            reports.append({"skill_id": skill.skill_id, "canary_ok": ok})
            if not ok:
                if self._repair(skill):
                    reports[-1]["repaired"] = True
                    reports[-1]["canary_ok"] = self._canary_ok(skill)
        return {"schema": SCHEMA + "_SELF_TEST", "skills": reports}

    # -- word learning ----------------------------------------------------
    def teach_word(self, word: str, goal_text: str) -> dict[str, Any]:
        word = word.strip().lower()
        if not word:
            raise AgentError("WORD_EMPTY")
        skill, _ = self._resolve(goal_text)
        self.word_bindings[word] = skill.skill_id
        if word not in skill.keywords:
            skill.keywords.append(word)
        self._resolve_impasse(word + " " + goal_text)
        self.memory.add(
            "fact",
            f"the word {word} means {skill.description}",
            {"skill_id": skill.skill_id, "word": word},
            surprise=0.3,
            confidence=0.9,
            tags=("language",),
        )
        return {"word": word, "skill_id": skill.skill_id, "taught_from": goal_text}

    # -- self-directed practice ------------------------------------------
    def practice(self, make_task: Callable[[int], tuple[str, dict[str, str]]], rounds: int = 6) -> dict[str, Any]:
        """Generate and run its own practice tasks.

        Selection maximizes coverage of untested integer parameter regions:
        every round takes the largest untested bucket.  Outcomes update the
        skill's empirical success rate; the caller can compare calibrated
        confidence with reality instead of trusting a self-report.
        """
        if not self.skills:
            raise AgentError("NO_SKILL_TO_PRACTICE")
        # Practise what is least calibrated, not whatever happens to be first.
        skill = min(self.skills.values(), key=lambda s: (s.tries, s.skill_id))
        tested: dict[int, bool] = {}
        for _ in range(rounds):
            candidates = [n for n in range(1, rounds + 4) if n not in tested]
            if not candidates:
                break
            choice = max(candidates, key=lambda n: (sum(1 for k in tested if abs(k - n) == 1), -n))
            goal, bindings = make_task(choice)
            outcome = self.solve(goal, bindings=bindings)
            tested[choice] = outcome["status"] == "PASS"
            self.practice_log.append({"n": choice, "outcome": outcome})
        tries = skill.tries
        successes = skill.successes
        return {
            "schema": SCHEMA + "_PRACTICE",
            "rounds": len(tested),
            "tested": sorted(tested),
            "observed_success_rate": (successes / tries) if tries else 0.0,
            "confidence": self.skills[skill.skill_id].successes / max(1, self.skills[skill.skill_id].tries),
            "log": self.practice_log,
        }

    # -- synthesis: learn a new skill from examples, not from a command ----
    def _skill_matches_examples(
        self, skill: ShellSkill, examples: Sequence[tuple[str, str]]
    ) -> bool:
        for path, expected in examples:
            try:
                command = skill.bind(self._example_bindings(skill, path))
                result = self.computer.run(command)
            except AgentError:
                return False
            if not result.ok or result.stdout != expected:
                return False
        return True

    def _example_bindings(self, skill: ShellSkill, path: str) -> dict[str, str]:
        bindings = {slot: value for slot, value in skill.slots.items()}
        path_slots = [
            slot
            for slot in skill.slots
            if "path" in slot or "file" in slot or slot in ("input", "source")
        ]
        for slot in path_slots:
            bindings[slot] = path
        return bindings

    def acquire(
        self,
        goal: str,
        examples: Sequence[tuple[str, str]],
        *,
        max_length: int = 3,
        time_budget_s: float = 2.0,
    ) -> dict[str, Any]:
        """Learn whatever is needed to make ``examples`` come true.

        ``examples`` are (input file, expected stdout) pairs.  Nothing here is
        a command demonstration: the creature sees only what the result should
        be, searches hypotheses, and admits a skill only when the real shell
        reproduces every example byte for byte on fresh files.

        Retrieval comes first.  An existing skill that already satisfies the
        examples is reused, even if the goal text shares no word with it, which
        is what makes memory worth having.
        """
        if not examples:
            raise AgentError("EXAMPLES_REQUIRED")
        if len(examples) < 2:
            # One observation cannot identify a function: many pipelines agree
            # on it and disagree everywhere else.  Refusing is the honest
            # answer; goals with checkable properties use ``fulfil`` instead,
            # which needs no example because the result is verified directly.
            raise AgentError("TOO_FEW_EXAMPLES")
        started = time.perf_counter()
        runs_before = self._runs
        # Two demonstrations of the same thing are one demonstration.  A
        # request taught twice on identical data constrains the answer exactly
        # as much as a single example does, and admitting a pipeline from it
        # would be claiming knowledge the evidence does not contain -- the
        # duplicate is a way of passing one observation past the guard below.
        distinct = {
            (self.computer.read(path), expected) for path, expected in examples
        }
        if len(distinct) < 2:
            raise AgentError("TOO_FEW_EXAMPLES")
        for path, expected in examples:
            if not self.computer.exists(path):
                raise AgentError("EXAMPLE_INPUT_MISSING:" + path)
            if not self.computer.read(path):
                raise AgentError("EXAMPLE_INPUT_EMPTY:" + path)

        # 1. behavioural retrieval: a known skill that already produces these
        # results is reused, even if the goal shares no word with its text.
        for skill in sorted(self.skills.values(), key=lambda s: (s.tries, s.skill_id)):
            if not self._skill_matches_examples(skill, examples):
                continue
            for token in _tokens(goal):
                if token not in skill.keywords:
                    skill.keywords.append(token)
            entry_id = None
            for _score, entry in self.memory.retrieve(goal, kind="skill", k=6):
                if entry.payload.get("skill_id") == skill.skill_id:
                    entry_id = entry.entry_id
                    break
            outcome = self._execute(
                skill,
                goal,
                {"path": examples[0][0]},
                ranked_entry_id=entry_id,
            )
            outcome["reused"] = True
            # Every outcome reports the same schema: what was learned, what ran,
            # and how long it took.  A memorised answer that skips the search
            # still ran a command, and saying so is what lets a caller compare
            # instant recall with first-time search on equal terms.
            outcome["learned"] = False
            outcome["source"] = "reused"
            outcome["commands_run"] = max(1, self._runs - runs_before)
            outcome["seconds"] = round(time.perf_counter() - started, 4)
            return outcome

        # 2b. A request that names every value a command consumes has nothing
        # left to search: try that command before spending the grammar search on
        # mechanisms that cannot express it at all.
        sources_now = [self.computer.read(path) for path, _ in examples]
        for doc in self._fully_named_mechanisms(goal, sources_now):
            found = self._find_documented_mechanism(goal, examples, docs=[doc], max_runs=4)
            if found is None:
                continue
            skill = self._admit_documented_skill(goal, found, examples)
            outcome = self.solve(goal, bindings={"path": examples[0][0]})
            outcome.update(
                {
                    "learned": True,
                    "stages": [found["stage"]],
                    "tool": found["tool"],
                    "argv": list(found["argv"]),
                    "source": "documentation-options",
                    "commands_run": max(int(found.get("runs") or 0), self._runs - runs_before),
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome

        # 3. synthesize from behaviour
        inputs = [(self.computer.read(path), expected) for path, expected in examples]
        # The fixed vocabulary is searched first, because it is small and its
        # ordering is sharp: a goal the creature already speaks costs two runs
        # and must not pay for grammar it never asked for.  Only when that
        # finds nothing exact and explainable is the same search repeated over
        # the *full* grammar -- the fixed table plus anything the sentence
        # states (a length filter, a character slice, a per-line length) and
        # everything already earned.  Searching the full grammar first made
        # every ordinary request pay for stages it never used, and made "the
        # number of characters in each line" answerable only by accident of
        # ordering.
        # A transformation the evidence states exactly is not searched for: it
        # is read off the examples and offered to the same search, which then
        # has to prove it against the real shell like anything else.  This is
        # what turns "reverse the lines" from a nineteen-process scan of the
        # machine's documentation into a two-process answer -- and it is the
        # evidence doing the work, not a word list.
        induced = self._induced_stages(inputs)
        induced_tools = (
            [stage.shell.split()[0] for stage in induced] if induced else []
        )
        before_admissions = set(self.computer.admitted())
        for tool in induced_tools:
            try:
                self.computer.admit(
                    tool,
                    evidence={
                        "induced_from": [path for path, _ in examples],
                        "relation": "the examples are the input's lines in a fixed order",
                    },
                )
            except AgentError:
                induced = ()
                break
        searched = [
            synthesis.search(
                inputs,
                max_length=max_length,
                time_budget_s=time_budget_s,
                stages=(tuple(synthesis.STAGES) + induced) if induced else None,
            )
        ]
        first_candidates, first_stats = searched[0]
        evaluated = 0
        # A grammar fit is evidence, not proof.  A pipeline can reproduce every
        # example and still ignore what the sentence says about them: on three
        # rows, "reverse the first two" matches a truncated sort by the third
        # column exactly.  Such a fit is kept on the record and the search moves
        # on; only a pipeline that answers both specifications is admitted here.
        contradicted: list[tuple[list[str], list[str]]] = []

        def consider(
            candidates: Sequence[Sequence[str]], stats: Mapping[str, Any]
        ) -> dict[str, Any] | None:
            nonlocal evaluated
            outcome, evaluated = self._consider_grammar_fits(
                candidates,
                stats,
                goal=goal,
                examples=examples,
                inputs=inputs,
                contradicted=contradicted,
                evaluated=evaluated,
                runs_before=runs_before,
                started=started,
            )
            return outcome

        outcome = consider(*searched[0])
        winner = ""
        if outcome is not None:
            # Only a tool the admitted pipeline actually uses keeps its
            # authority; an induced tool that lost to a known stage is revoked
            # like any other failed guess.
            for tool in induced_tools:
                if any(stage.split()[0] == tool for stage in outcome.get("stages", ())):
                    winner = tool
        self._settle_admissions(before_admissions, winner=winner)
        if outcome is not None:
            return outcome
        # The wider search is worth its processes only when the *sentence*
        # supplies a stage the fixed table does not have.  Stages the creature
        # has already earned are reachable through composition, which is where
        # a stranger mechanism is looked for anyway; re-running the whole
        # search over them made every ordinary request pay for its own memory.
        full = self._grammar(inputs, goal)
        if self._derived_stages(goal) and len(full) > len(synthesis.STAGES):
            extra_candidates, extra_stats = synthesis.search(
                inputs, max_length=max_length, time_budget_s=time_budget_s, stages=full
            )
            outcome = consider(extra_candidates, extra_stats)
            if outcome is not None:
                return outcome

        # Nothing the fixed vocabulary can build is both exact and an answer to
        # the request.  The machine's own documentation is the next place to
        # look: a tool that takes an argument may be exactly the mechanism the
        # request names, and its help text says which arguments it has.
        # Composition is the general case -- an unknown mechanism with grounded
        # arguments feeding stages the creature already knows; a single stage is
        # its degenerate case.
        composed = self._compose(
            goal, examples, max_length=max_length, time_budget_s=time_budget_s
        )
        if composed is not None:
            pipeline, detail = composed
            skill = self._admit_composed(goal, pipeline, examples)
            outcome = self.solve(goal, bindings={"path": examples[0][0]})
            outcome.update(
                {
                    "learned": True,
                    "stages": pipeline,
                    "documented": detail["documented"],
                    "grammar": detail["grammar"],
                    "prefix": detail.get("prefix", ""),
                    "remembered": bool(detail.get("remembered", False)),
                    "source": "composed",
                    "tool": detail["tool"],
                    "argv": list(detail["argv"]),
                    "commands_run": max(int(detail.get("tested") or 0), self._runs - runs_before),
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome
        # The shortlist is a keyword ranking, and a keyword ranking is a prior:
        # "reverse the lines" puts `rev` (which reverses *characters*) first and
        # `tac` (which reverses *lines*) nineteenth.  Only the bytes can settle
        # that, so when the top of the ranking has nothing, the search widens
        # to the whole documented surface instead of stopping at six.  It runs
        # only on the path where nothing else answered, and every attempt is
        # bounded by the run cap inside the search.
        found = self._find_documented_mechanism(goal, examples)
        if found is None:
            found = self._find_documented_mechanism(
                goal, examples, max_tools=24, max_runs=40, arguments=False
            )
        if found is not None:
            skill = self._admit_documented_skill(goal, found, examples)
            outcome = self.solve(goal, bindings={"path": examples[0][0]})
            outcome.update(
                {
                    "learned": True,
                    "stages": [found["stage"]],
                    "tool": found["tool"],
                    "argv": list(found["argv"]),
                    "source": "documentation-options",
                    "commands_run": max(int(found.get("runs") or 0), self._runs - runs_before),
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome
        if contradicted:
            # Something reproduced the bytes and contradicted the sentence.  The
            # examples and the request are two specifications, and the honest
            # report is that they disagree -- not the pipeline that fits one and
            # ignores the other.
            stages, unexplained = contradicted[0]
            self._record_impasse(
                goal,
                {
                    "reason": "evidence_conflict",
                    "unexplained": unexplained,
                    "contradicted_by": [" ".join(stages)],
                    "strategies": ["synthesis", "composition", "documentation"],
                    "examples": [path for path, _ in examples],
                    "tools_tried": sorted({row["tool"] for row in self.discovery_log}),
                },
            )
            raise AgentError("EXAMPLES_CONTRADICT_GOAL:" + ",".join(unexplained))
        # The vocabulary cannot express the examples and nothing on this machine
        # that documents itself reproduces them.  That is knowledge -- the goal,
        # the evidence and the tools that were tried -- and it belongs on the
        # record, not in a traceback nobody keeps.
        self._record_impasse(
            goal,
            {
                "reason": "no_verified_mechanism",
                "strategies": ["synthesis", "composition", "documentation"],
                "examples": [path for path, _ in examples],
                "tools_tried": sorted({row["tool"] for row in self.discovery_log}),
            },
        )
        raise AgentError("NO_PIPELINE_WITHIN_BUDGET")

    # -- arguments the machine documents -----------------------------------
    # ``F`` is a *file* placeholder in the coreutils convention (--files0-from=F), so
    # it is deliberately absent: binding it to a number would invent a filename.
    _INT_NAME = re.compile(r"^(?:N|NUM|NUMBER|COUNT|WIDTH|SIZE|LENGTH|LIST|KEYDEF|COLS|LINE|LINES)$")
    # A placeholder that names a file, a program or a directory cannot be bound
    # by a number or a character: inventing a filename is not evidence.
    _FILE_NAME = re.compile(r"^(?:F|FILE|FILES|PROG|PROGRAM|PATH|DIR|DIRECTORY|CMD|COMMAND)$")
    _CHAR_NAME = re.compile(r"^(?:DELIM|SEP|CHAR|CC|STRING|TEXT)$")
    _INT_WORDS = {"width", "column", "columns", "number", "numbers", "count", "line", "lines",
                  "byte", "bytes", "size", "length", "digit", "digits", "increment", "key"}
    _CHAR_WORDS = {"delimiter", "separator", "character", "char", "characters", "string"}
    # Words that mean "this option is about how the data is laid out" rather
    # than how a result is printed.
    _STRUCTURE_WORDS = {
        "field", "fields", "column", "columns", "value", "values", "key", "keys",
        "delimiter", "delimiters",
    }
    # A *position* in the data is a different kind of argument from an
    # *amount*: a key or a field takes an index the request can name, while a
    # width or a count is only meaningful if the request names the number.
    # A *position* is an index into the data: a field, a column, a key.  The
    # test is deliberately not "the option's prose contains a word that can
    # mean position" -- `--verify-key` is a cryptographic key, `--interval` is a
    # time, and `-w` is a width.  Binding the ordinal to any of those produces a
    # command that runs, fits two small files by luck, and means nothing.
    _POSITION_WORDS = {"field", "fields", "column", "columns", "position", "positions"}
    # Placeholders a tool uses when its value is an index into the data.  A
    # generic LIST or NUMBER is not enough (`expand -t LIST` is a tab width);
    # KEYDEF and FIELDS are.
    _POSITION_NAMES = {"KEYDEF", "FIELDS", "FIELD", "POS", "POSITION", "COLUMN", "COLUMNS"}
    # Words that place a value *in the data* rather than in a display or a clock.
    # A place in the data: a field, a column, a character, a byte.  Not a time
    # interval, a checksum key, or a width.
    _DATA_NOUNS = {
        "field", "fields", "column", "columns", "value", "values", "location",
        "character", "characters", "byte", "bytes",
    }
    # Positional operand names, read off a usage line.  A pattern is a value the
    # sentence supplies; a set is a translation of characters; the rest are
    # files or names the pipeline supplies for itself.
    _OPERAND_PATTERN = re.compile(r"^(?:PATTERN|PATTERNS|REGEXP|REGEXPS|EXPRESSION|EXPRESSIONS)$")
    _OPERAND_CHARS = re.compile(r"^(?:SET|STRING|ARRAY)\d?$|^(?:FROM|TO)$")
    _OPERAND_SKIP = re.compile(
        r"^(?:F|FILE|FILES|FILE\d|INPUT|OUTPUT|INPUT_FILE|NAME|SUFFIX|PROG|PROGRAM|PATH|DIR|DIRECTORY|CMD|COMMAND)$"
    )
    _AMOUNT_WORDS = {
        "number", "width", "line", "lines", "byte", "bytes", "size", "count",
        "length", "increment", "digit", "digits", "start", "first",
        "character", "characters",
    }

    @classmethod
    def _value_kind(cls, option: discovery.Option, doc: discovery.ToolDoc | None = None) -> str:
        """What kind of value an option's argument is, read from its own text.

        The name the authors gave the placeholder is the strongest evidence
        (``=WIDTH``), the sentence they wrote about it is the second.  If
        neither says, the option cannot be grounded and is not tried -- an
        invented value is not evidence.
        """
        name = option.argument.strip("[]").upper()
        if cls._FILE_NAME.match(name):
            return ""
        if doc is not None and doc.values_for(name):
            # The tool lists the values it accepts, so the argument is a small
            # closed vocabulary rather than a number or a character.
            return "enum"
        if cls._INT_NAME.match(name):
            return "int"
        if cls._CHAR_NAME.match(name):
            return "char"
        words = set(discovery._words(option.description))
        if words & cls._INT_WORDS:
            return "int"
        if words & cls._CHAR_WORDS:
            return "char"
        return ""

    @staticmethod
    def _named_characters(goal: str) -> list[str]:
        """Characters the sentence names, in the order it names them.

        ``"replace every comma with a semicolon"`` names two: ``,`` then ``;``.
        The order is the meaning -- the first is what is there, the second what
        it becomes -- so this is a list rather than a set.
        """
        out: list[str] = []
        for word in re.findall(r"[a-z]+", goal.lower()):
            character = _SEPARATOR_WORDS.get(word)
            if character is not None and character not in out:
                out.append(character)
        return out

    @classmethod
    def _position_of(cls, option: "discovery.Option", words: set[str], placeholder: str) -> bool:
        """Is this option's value an index into the data?

        Two independent signals, and either is enough: the tool names the value
        as a data position (KEYDEF, FIELDS), or the option says in words that it
        puts the value in the data (a field, a column, a location).  Both are
        about the data's shape.  ``--verify-key`` names a key and means a
        checksum; ``-w`` names a width; neither is a place in the text.
        """
        if placeholder in cls._POSITION_NAMES and words & cls._DATA_NOUNS:
            return True
        return bool(words & cls._DATA_NOUNS) and bool(words & {"select", "sort", "print", "output", "display"})


    def _separators(self, sources: Sequence[str]) -> list[str]:
        """Characters that actually separate parts of the data, most common first.

        Separators depend only on the data, and every option of every tool asks
        for them: counting characters thousands of times per goal is pure
        waste, so the answer is kept per text.
        """
        text = "\n".join(sources)
        cached = self._separator_cache.get(text)
        if cached is not None:
            return cached
        counts: dict[str, int] = {}
        for character in text:
            if character in ",:|; \t":
                counts[character] = counts.get(character, 0) + 1
        found = [character for character, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:3]
        self._separator_cache[text] = found
        return found

    def _argument_atoms(
        self, goal: str, doc: discovery.ToolDoc, sources: Sequence[str]
    ) -> list[tuple[int, list[str], str]]:
        """Option bindings something real can justify, with the strength of it.

        Three kinds of evidence are accepted and nothing else:

        * a *position* the sentence names of a unit ("the second column") bound
          to an option about positions -- a key, a field, a location;
        * a *quantity* the request names ("at 40 characters") bound to an
          option about amounts, when the option's own words appear in the goal;
        * a *separator* the data actually contains, bound to an option about
          delimiters.

        An option whose words share nothing with the request, or whose value
        nothing in the request or the data can supply, is unjustified.  An
        unjustified argument would be a guess wearing an experiment's clothes.
        """
        positions = _ordinal_positions(goal)
        # A written number is a *quantity* ("40 characters"); an ordinal is a
        # *position* ("the second column").  Binding a quantity to a key or a
        # position to a buffer size is how a guess disguises itself as a
        # deduction, so the two are kept apart.
        quantities = sorted({int(match) for match in re.findall(r"\b(\d{1,4})\b", goal)})
        separators = self._separators(sources)
        tokens = _tokens(goal)
        atoms: list[tuple[int, list[str], str]] = []
        for option in doc.options:
            spelling = option.short or option.long
            if not spelling:
                continue
            kind = self._value_kind(option, doc)
            # A tool names itself twice: in the flag and in the sentence.  The
            # long flag is often the clearer of the two ("--field-separator").
            labelled = option.long.lstrip("-").replace("-", " ")
            words = set(discovery._words(option.description)) | set(discovery._words(labelled))
            placeholder = option.argument.strip("[]").upper() or "SWITCH"
            if kind == "enum":
                for value, text in doc.values_for(option.argument):  # type: ignore[union-attr]
                    value_words = set(discovery._words(text))
                    if not value_words & tokens:
                        score = 2
                    elif value_words & {"no", "not", "none", "skip", "except", "ignore"}:
                        # A value that excludes things is a different operation
                        # from the one the request names, even when it shares
                        # every other word with it.
                        score = 3
                    else:
                        score = 4
                    atoms.append((score, [spelling, value], placeholder))
                continue
            if option.argument:
                if kind == "int":
                    if positions and self._position_of(option, words, placeholder):
                        # `-c` says "characters" and the sentence said
                        # "character"; `-b` says "bytes" and it did not.  Both
                        # would produce the same bytes on ASCII data, so the
                        # sentence's own word is what chooses between them.
                        bonus = 1 if self._shares_words(words, tokens) else 0
                        atoms.append((5 + bonus, [spelling, str(positions[0])], placeholder))
                    elif quantities and (
                        words & (self._POSITION_WORDS | self._AMOUNT_WORDS)
                        or placeholder in self._POSITION_NAMES
                    ):
                        atoms.append((4, [spelling, str(quantities[0])], placeholder))
                elif kind == "char":
                    # A character the sentence names is the best evidence there
                    # is: "comma separated" says exactly what `-d ,` needs.
                    named = self._named_characters(goal)
                    if named:
                        # The same evidence as a separator found in the data,
                        # but a better value: the sentence names this one.
                        atoms.append((4, [spelling, named[0]], placeholder))
                    elif separators and words & (self._CHAR_WORDS | {"field", "fields"}) and (
                        words & self._STRUCTURE_WORDS
                    ):
                        # Otherwise a separator the data contains is only this
                        # option's business if the option is about the *shape of
                        # the data* -- a delimiter, a field, a key.  grep's
                        # `--group-separator` also says "separator", but it
                        # formats output groups the request never mentioned, and
                        # binding the data's space to it would be a guess dressed
                        # as evidence.
                        atoms.append((4, [spelling, separators[0]], placeholder))
                continue
            if tokens & words:
                atoms.append((1, [spelling], placeholder))
        # Some tools take *positional* operands that no option describes:
        # `tr ',' ';'` translates the first string into the second, and says so
        # only in its usage line.  The sentence supplies the values -- the
        # characters it names, or the word whose lines it wants kept -- and the
        # examples decide whether the reading was right.
        if doc.operands:
            named_chars = self._named_characters(goal)
            literal = "\n".join(sources)
            kept = [w for w in sorted(tokens - _STOP) if w in literal and len(w) > 2]
            operand_place = 0
            for operand in doc.operands:
                name = operand.strip("[]").upper()
                if self._OPERAND_SKIP.match(name):
                    continue
                if self._OPERAND_PATTERN.match(name):
                    pattern = self._affix_pattern(goal)
                    if pattern:
                        # The sentence named the shape of the pattern, not just
                        # a word: "start with a" is anchored, and an unanchored
                        # `a` would select every line containing the letter.
                        atoms.append((5, [pattern], name))
                    elif kept:
                        atoms.append((5, [kept[0]], name))
                elif self._OPERAND_CHARS.match(name):
                    index = min(operand_place, len(named_chars) - 1)
                    if named_chars:
                        # The sentence named this exact character, which is the
                        # strongest evidence any argument can have.
                        atoms.append((6, [named_chars[index]], name))
                        operand_place += 1
                elif self._INT_NAME.match(name):
                    if positions:
                        atoms.append((5, [str(positions[0])], name))
                    elif quantities:
                        atoms.append((4, [str(quantities[0])], name))
        # Strongest evidence first, and otherwise the order the tool itself
        # declared.  Two named characters are *not* interchangeable: the first
        # is what the text has and the second is what it becomes, so sorting
        # them alphabetically would translate in the wrong direction -- `tr , :`
        # for a request that said "colon with a comma".
        atoms.sort(key=lambda row: -row[0])
        return atoms

    def _argument_forms(
        self,
        goal: str,
        doc: discovery.ToolDoc,
        sources: Sequence[str],
        manners: Sequence[str] = (),
    ) -> list[tuple[int, list[str]]]:
        """Candidate option bundles, strongest evidence and fewest arguments first.

        A tool's own option list is the space; the request and the data only
        *rank* and *bind* it.  Singles come before pairs, and a pair is only
        formed from two arguments of *different kinds* -- a style and a style,
        or a width and a width, usually compete for the same job rather than
        compose, while a delimiter and a field really do need each other.
        """
        def cls_flags(form: Sequence[str]) -> int:
            return sum(1 for part in form if part.startswith("-"))

        atoms = self._argument_atoms(goal, doc, sources)
        # A qualifier the sentence states ("numerically") and the tool itself
        # documents ("-n, --numeric-sort") is not a guess: it is the option
        # that implements a word of the request.  It joins the bundles below as
        # evidence, because a sort that ignores "numerically" answers a
        # different question.
        qualifiers: list[str] = []
        qualifier_words: list[str] = []
        stated = [word for word in sorted(set(re.findall(r"[a-z]+", goal.lower())))
                  if len(word) >= 6 and word.endswith("ly")]
        for word in [*stated, *manners]:
            flags = self._qualifier_flags(word, doc)
            if not flags or word in qualifier_words:
                continue
            qualifier_words.append(word)
            for flag in flags:
                if flag not in qualifiers:
                    qualifiers.append(flag)

        forms: list[tuple[int, list[str]]] = [(0, [])]
        for score, tokens, _placeholder in atoms:
            forms.append((score, list(tokens)))
        for first in range(len(atoms)):
            for second in range(first + 1, len(atoms)):
                if atoms[first][2] == atoms[second][2]:
                    continue
                if atoms[first][1][0] == atoms[second][1][0]:
                    continue
                # Only grounded evidence raises a bundle's rank.  A switch
                # that merely shares a word with the goal still composes (it
                # may be exactly right), but it must not make a two-argument
                # bundle look better evidenced than the one-argument bundle it
                # extends: `fold -w 40 -b` is not stronger than `fold -w 40`.
                forms.append(
                    (
                        # Only *grounded* evidence raises a bundle's rank:
                        # an enum value the sentence never mentions scores 2
                        # and must not make `nl -b a` look weaker than
                        # `nl -b a -n rn`, which fits the same bytes with an
                        # option nobody asked for.
                        sum(atom[0] for atom in (atoms[first], atoms[second]) if atom[0] >= 3),
                        list(atoms[first][1]) + list(atoms[second][1]),
                    )
                )
        if qualifier_words:
            # Every bundle this tool could offer is also offered with the
            # qualifiers attached.  It outranks the bare bundle by exactly the
            # weight of the words it implements.  The words are kept apart
            # rather than pooled, because each one has to contribute its own
            # flag: taking the first two flags on the whole list would let two
            # synonyms of "numeric" crowd out "reverse", and then a descending
            # request could never be spelled.
            expanded: list[tuple[int, list[str]]] = []
            for score, form in forms:
                expanded.append((score, form))
                per_word: list[str] = []
                for word in qualifier_words:
                    flag = next(
                        (candidate for candidate in self._qualifier_flags(word, doc)
                         if candidate not in form and candidate not in per_word),
                        "",
                    )
                    if flag:
                        per_word.append(flag)
                for flag in per_word:
                    expanded.append((score + 2, [*form, flag]))
                if len(per_word) > 1:
                    # Numeric *and* reversed is one request, not two: the
                    # options it needs belong in the same bundle.
                    expanded.append((score + 2 * len(per_word), [*form, *per_word]))
            forms = expanded
        unique: list[tuple[int, list[str]]] = []
        seen: set[tuple[str, ...]] = set()
        for score, form in forms:
            key = tuple(form)
            if key in seen:
                continue
            seen.add(key)
            unique.append((score, form))
        # Evidence first, then the fewest arguments: a single grounded argument
        # is the simplest explanation, and a pair is only worth a process if the
        # singles cannot do the job.  Keyword-only switches are kept to the last
        # two, because they are the most numerous and the least informative.
        # Among equally strong bundles, the shortest spelling wins: `-d ,` before
        # `--output-delimiter ,`, and `-k 2 -t ,` before `-k 2 --field-separator ,`
        # -- the same option, said the way a person would say it.
        # Evidence decides first, then parsimony.  A bundle that implements a
        # word of the request ("-n" for "numerically") carries more evidence
        # than a shorter one that does not, and ordering by argument count
        # first would bury it behind every one-flag form on the machine.
        unique.sort(
            key=lambda row: (
                -row[0],
                cls_flags(row[1]),
                len(" ".join(row[1])),
                row[1],
            )
        )
        strong = [row for row in unique if row[0] >= 2][:12]
        weak = [row for row in unique if row[0] < 2][:2]
        return strong + weak

    def _demonstrated_manners(
        self, goal: str, examples: Sequence[tuple[str, str]]
    ) -> tuple[str, ...]:
        """Orderings the examples themselves demonstrate.

        "Sort the rows by the second column" says nothing about how numbers
        compare, but the numbers in that column are 10, 2 and 1 and the answer
        is 1, 2, 10: the examples show a numeric ordering, and the tool
        documents the switch that computes one.  Reading that off the *answers*
        is different from assuming it -- the bytes the user produced are part
        of the request.  A descending answer is the same evidence for a reverse
        switch, so the two are returned as words the tool's own options must
        match, exactly like an adverb in the sentence.
        """
        position = self._orders_by_named_column(goal)
        if position is None:
            return ()
        path, expected = examples[0]
        text = self.computer.read(path)
        separators = self._separators([text])
        if not separators:
            return ()
        separator = separators[0]
        rows = [line.split(separator) for line in text.splitlines()]
        want = [line.split(separator) for line in expected.splitlines()]
        if not rows or not want:
            return ()
        if any(len(row) < position for row in rows) or any(len(row) < position for row in want):
            return ()
        values = [row[position - 1] for row in rows]
        ordered = [row[position - 1] for row in want]
        try:
            numeric = sorted(values, key=float)
        except ValueError:
            numeric = []
        words: list[str] = []
        if numeric and numeric != sorted(values) and ordered in (numeric, list(reversed(numeric))):
            words.append("numerically")
        plain = numeric if numeric else sorted(values)
        if ordered == list(reversed(plain)) and ordered != plain:
            words.append("reverse")
        return tuple(words)

    @staticmethod
    def _structure_words(sources: Sequence[str]) -> set[str]:
        """Words the *shape of the data* makes meaningful.

        This is not a task rule: it is what the inputs themselves show.  If the
        data is separated by commas, then "field", "column" and "delimiter" are
        the descriptions under which an operation on those parts can be
        documented; if a line is nothing but a number, "numeric" is.  The words
        are used to *order* documented mechanisms for trial, never to decide
        anything -- the bytes decide.
        """
        text = "\n".join(sources)
        words: set[str] = set()
        if re.search(r"[,;:|\t]", text):
            words |= {"field", "fields", "column", "columns", "delimiter", "separator", "list"}
        if re.search(r"(?m)^\s*-?\d+(?:\.\d+)?\s*$", text):
            words |= {"numeric", "number", "sort"}
        return words

    # -- what answered a request before ------------------------------------
    @staticmethod
    def _mechanism_id(doc_name: str, form: Sequence[str]) -> str:
        return " ".join([doc_name, *(_shell_spelling(part) for part in form)]).strip()

    def _remember_mechanism(self, goal: str, doc: discovery.ToolDoc, form: Sequence[str]) -> None:
        """Record a mechanism that verified, against the request it answered.

        The record is keyed by the *mechanism*, not by the sentence: two
        requests that need `sort -k 2 -t ,` can share almost no words ("sort
        the rows by the second column, comma separated" and "keep the last two
        rows of the table, sorted by the second column"), and a request that
        shares every word with an earlier one may still need different
        arguments.  What carries over is the tool and the kinds of argument it
        was given; the values are bound fresh every time.
        """
        key = self._mechanism_id(doc.name, form)
        previous = self.mechanisms.get(key) or {}
        self.mechanisms[key] = {
            "tool": doc.name,
            "argv": list(form),
            "documentation": doc.summary,
            "goal": goal,
            "hits": int(previous.get("hits", 0)) + 1,
            "misses": int(previous.get("misses", 0)),
        }

    def _recall_mechanism(
        self,
        goal: str,
        examples: Sequence[tuple[str, str]],
        grammar: Sequence[Any],
        scratch: str,
        *,
        max_length: int,
        time_budget_s: float,
    ) -> tuple[list[str], dict[str, Any]] | None:
        """Try the mechanisms that have worked before, most proven first.

        Each one is re-armed from *this* request and *this* data -- the
        position it names, the separator the data contains, the quantity the
        sentence writes -- and then verified on the new examples like anything
        else.  A mechanism that fails is demoted, so a memory that has gone
        wrong stops being consulted instead of being trusted.
        """
        if not self.mechanisms:
            return None
        sources = [self.computer.read(path) for path, _ in examples]
        expected = [text for _, text in examples]
        vocabulary = self.vocabulary
        vocabulary.read()
        located = dict(vocabulary.executables())
        grammar_list = list(grammar)
        prefixes = self._named_prefixes(goal, sources, grammar_list)
        ranked = sorted(
            self.mechanisms.items(),
            key=lambda item: (-int(item[1].get("hits", 0)), item[0]),
        )[:4]
        for _key, entry in ranked:
            if int(entry.get("misses", 0)) >= 2 + int(entry.get("hits", 0)):
                continue  # this memory has been wrong more often than right
            tool = str(entry.get("tool", ""))
            doc = vocabulary.doc(tool)
            if doc is None or tool not in located or tool in discovery.DENY:
                continue
            # The same tool, with arguments bound from the new sentence.  A
            # mechanism whose kinds of argument the request cannot supply is
            # skipped before it costs a process.
            scored = [
                (strength, list(form))
                for strength, form in self._argument_forms(goal, doc, sources)
                if form and strength >= 4
            ]
            scored.sort(key=lambda row: (-row[0], len(row[1])))
            forms: list[list[str]] = [form for _strength, form in scored[:2]]
            remembered = list(entry.get("argv") or [])
            if remembered and remembered not in forms:
                forms.append(remembered)
            for form in forms:
                stage = self._stage_for(doc, form, located[tool], cwd=scratch)
                for pipeline in self._hypotheses(
                    stage,
                    sources,
                    expected,
                    grammar_list,
                    goal,
                    max_length=max_length,
                    time_budget_s=time_budget_s,
                    prefixes=prefixes,
                ):
                    if not self._confirm(goal, pipeline, examples):
                        continue
                    entry["hits"] = int(entry.get("hits", 0)) + 1
                    self._remember_mechanism(goal, doc, form)
                    prefix_shell = pipeline[0] if pipeline[0] != stage.shell else ""
                    return pipeline, {
                        "documented": [stage.shell],
                        "grammar": pipeline[2:] if prefix_shell else pipeline[1:],
                        "prefix": prefix_shell,
                        "tool": tool,
                        "argv": list(form),
                        "remembered": True,
                    }
            entry["misses"] = int(entry.get("misses", 0)) + 1
        return None

    def _learn_stage(self, doc: discovery.ToolDoc, form: Sequence[str], binary: str) -> None:
        """Admit a verified invocation as a word of the grammar.

        A mechanism that produced the right bytes is a fact about this machine.
        Keeping it as a *skill* answers the one goal that taught it; keeping it
        as a *stage* lets every later search use it, so a related request is
        solved by pure search plus one verification instead of a fresh
        hunt.  Nothing is trusted: the stage runs the real binary every time.
        """
        if not form:
            return
        shell = " ".join([doc.name, *(_shell_spelling(part) for part in form)]).strip()
        self._learned[shell] = {"tool": doc.name, "argv": list(form)}
        self._learned_cache.pop(shell, None)

    def _earned_dir(self) -> str:
        """One throwaway directory for every earned stage, made on first use."""
        if self._stage_dir is None:
            self._stage_dir = tempfile.mkdtemp(prefix="brain-stages-")
        return self._stage_dir

    def _learned_stages(self) -> list[Any]:
        """The earned stages, rebuilt from the machine when first needed.

        A snapshot stores the invocation, not a live object: after a restart the
        stage is rebuilt by asking the machine for the same tool, so a binary
        that has changed is re-admitted rather than inherited on trust.
        """
        out: list[Any] = []
        for shell, record in self._learned.items():
            stage = self._learned_cache.get(shell)
            if stage is None:
                tool = str(record.get("tool", ""))
                doc = self.vocabulary.doc(tool)
                located = dict(self.vocabulary.executables()) if doc is not None else {}
                if doc is None or tool not in located:
                    continue
                stage = self._stage_for(doc, list(record.get("argv") or []), located[tool], cwd=self._earned_dir())
                self._learned_cache[shell] = stage
            out.append(stage)
        return out

    _LINE_LENGTH = re.compile(
        r"\bnumber\s+of\s+(?:characters|character|chars|bytes|letters)\b"
        r"|\bhow\s+many\s+(?:characters|character|chars|bytes|letters)\b"
    )
    _NUMBER_WORDS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    @classmethod
    def _small_number(cls, word: str) -> int:
        word = word.strip().lower()
        return int(word) if word.isdigit() else cls._NUMBER_WORDS.get(word, 0)

    @staticmethod
    def _induced_stages(inputs: Sequence[tuple[str, str]]) -> tuple[Any, ...]:
        """Transformations the *evidence* demonstrates as an exact permutation.

        Two examples can say something a sentence never will.  If every
        example's answer is its input's lines in a fixed order -- the last line
        first, or shifted by one -- then the transformation is that permutation
        and no search over the machine's tools can say more about it than the
        bytes already have.  Reading it off the evidence costs nothing; finding
        `tac` by scanning nineteen strangers costs nineteen processes.

        Induction from two examples is only honest when it is *unique*: at
        least one example must have three or more lines (otherwise "reverse"
        and "rotate by one" are the same function on the evidence), and no
        second rule may fit.  When two rules fit, this returns nothing and the
        creature goes on searching -- a guess between two readings is exactly
        what it must not do.
        """
        pairs: list[tuple[list[str], list[str]]] = []
        for source, expected in inputs:
            lines = source.splitlines()
            want = expected.splitlines()
            if sorted(lines) != sorted(want):
                return ()  # not a permutation of the lines: a different function
            pairs.append((lines, want))
        if len(pairs) < 2 or not any(len(lines) >= 3 for lines, _ in pairs):
            return ()

        def reverse(lines: list[str]) -> list[str]:
            return list(reversed(lines))

        def rotate(lines: list[str], k: int) -> list[str]:
            return lines[k:] + lines[:k]

        fits: list[Any] = []
        if all(want == reverse(lines) for lines, want in pairs) and any(
            reverse(lines) != lines for lines, _ in pairs
        ):
            fits.append(synthesis.Stage("tac", synthesis.LINES, synthesis.LINES, synthesis.as_text and (lambda text: synthesis.as_text(reverse(synthesis.as_lines(text))))))
        longest = max(len(lines) for lines, _ in pairs)
        for k in range(1, longest):
            if all(want == rotate(lines, k) for lines, want in pairs) and any(
                rotate(lines, k) != lines for lines, _ in pairs
            ):
                # A rotation cannot be spelled in `sed`: sed decides each
                # line on its own and cannot move it, so a two-address range
                # prints the file unchanged (the interpreter and the shell
                # disagreed, and the shell check refused the candidate -- which
                # is exactly what that check is for).  `awk` can buffer, so the
                # rotation is written as one indexed pass over the records.
                shell = (
                    "awk '{a[NR]=$0} END {for (i=1; i<=NR; i++) "
                    f"print a[(i+{k}-1)%NR+1]}}'"
                )
                fits.append(
                    synthesis.Stage(
                        shell,
                        synthesis.LINES,
                        synthesis.LINES,
                        lambda text, step=k: synthesis.as_text(rotate(synthesis.as_lines(text), step)),
                    )
                )
        return tuple(fits) if len(fits) == 1 else ()

    @classmethod
    def _derived_stages(cls, goal: str) -> tuple[Any, ...]:
        """Stages the request states outright, in the words it states them.

        Three requests of this shape are answerable with nothing but a reading:
        "the lines longer than 20 characters" filters on a length, "the number
        of characters in each line" *reports* that length, and "the first three
        characters of each line" keeps a slice of it.  Each stage is built from
        the sentence's own number and is checked like any other -- an
        interpreter function plus a real run -- so a misreading costs a probe
        rather than an answer.
        """
        lowered = goal.lower()
        stages: list[Any] = []

        counting = _COUNT_UNIT.search(lowered)
        if counting and counting.group(1) in {
            "characters", "character", "chars", "bytes", "byte"
        } and not (
            "each line" in lowered or "per line" in lowered
        ) and re.search(r"\b(count|counts|how many|number of)\b", lowered) and not re.search(
            r"\b(distinct|unique)\b", lowered
        ):
            # `wc -m` counts characters; `wc -c` counts bytes.  They agree on
            # ASCII and disagree everywhere else, so the noun in the sentence
            # chooses between them and neither is a stand-in for the other.
            units = "bytes" if counting.group(1) in {"bytes", "byte"} else "characters"
            shell = "wc -c" if units == "bytes" else "wc -m"
            stages.append(
                synthesis.Stage(
                    shell,
                    synthesis.LINES,
                    synthesis.COUNT,
                    (lambda text: str(len(text)) + "\n")
                    if shell == "wc -m"
                    else (lambda text: str(len(text.encode("utf-8"))) + "\n"),
                )
            )
        if counting and counting.group(1) in {"words", "word"} and not (
            "each line" in lowered or "per line" in lowered
        ) and re.search(r"\b(count|counts|how many|number of)\b", lowered) and not re.search(
            r"\b(distinct|unique)\b", lowered
        ):
            # "How many words" is `wc -w` on the whole text.  It stays out of
            # the fixed vocabulary because it is *not* interchangeable with
            # `wc -l` on a one-word-per-line stream: an empty line is a word
            # to `wc -l` and nothing to `wc -w`, and a grammar that offered
            # both would drown the right candidate with the near-miss.
            stages.append(
                synthesis.Stage(
                    "wc -w",
                    synthesis.LINES,
                    synthesis.COUNT,
                    lambda text: str(
                        sum(len(line.split()) for line in synthesis.as_lines(text))
                    ) + "\n",
                )
            )
        if counting and counting.group(1) in {"words", "word"} and (
            "each line" in lowered or "per line" in lowered
        ):
            stages.append(
                synthesis.Stage(
                    "awk '{print NF}'",
                    synthesis.LINES,
                    synthesis.LINES,
                    lambda text: synthesis.as_text(
                        [str(len(line.split())) for line in synthesis.as_lines(text)]
                    ),
                )
            )
        # A class of characters translated into another class or character:
        # `tr '0-9' '*'`.  Both sides are read from the sentence; the shell
        # decides whether the reading was right.
        if "replace" in lowered or "change" in lowered or "turn" in lowered:
            match = _REPLACE_CLASS.search(lowered)
            if match:
                source_set = _CHARACTER_CLASSES.get(match.group(1))
                target_words = cls._named_characters(match.group(2))
                target_set = _CHARACTER_CLASSES.get(match.group(2))
                if source_set and target_words:
                    replacement = target_words[0]
                    stages.append(
                        synthesis.Stage(
                            f"tr '{source_set}' '{replacement}'",
                            synthesis.TEXT,
                            synthesis.TEXT,
                            lambda text, a=source_set, b=replacement: _translate_sets(text, a, b),
                        )
                    )
                elif source_set and target_set:
                    stages.append(
                        synthesis.Stage(
                            f"tr '{source_set}' '{target_set}'",
                            synthesis.TEXT,
                            synthesis.TEXT,
                            lambda text, a=source_set, b=target_set: _translate_sets(text, a, b),
                        )
                    )

        length = cls._LINE_LENGTH.search(lowered)
        if length and ("each line" in lowered or "per line" in lowered):
            stages.append(
                synthesis.Stage(
                    "awk '{print length($0)}'",
                    synthesis.LINES,
                    synthesis.LINES,
                    lambda text: synthesis.as_text(
                        [str(len(line)) for line in synthesis.as_lines(text)]
                    ),
                )
            )

        edge = _EDGE_CHARS.search(lowered)
        if edge:
            if edge.group(1):
                side, amount = edge.group(1), cls._small_number(edge.group(2))
            else:
                side, amount = edge.group(4), cls._small_number(edge.group(3))
            if amount:
                leading = side in {"first", "leading", "start", "beginning"}
                if leading:
                    shell = f"cut -c 1-{amount}"
                    apply = lambda text, n=amount: synthesis.as_text(  # noqa: E731
                        [line[:n] for line in synthesis.as_lines(text)]
                    )
                else:
                    # `cut -c -2` is the *first* two characters (a range from
                    # 1), not the last two.  A stage whose interpreter says one
                    # thing and whose shell says another would be the worst kind
                    # of mistake -- the search would believe it and the shell
                    # would disagree -- so the last-N reading is spelled the way
                    # it is actually true: `sed` keeps the final N of each line
                    # and leaves a shorter line alone, exactly like the slice.
                    shell = "sed 's/.*\\(.\\{" + str(amount) + "\\}\\)$/\\1/'"
                    apply = lambda text, n=amount: synthesis.as_text(  # noqa: E731
                        [line[-n:] for line in synthesis.as_lines(text)]
                    )
                stages.append(synthesis.Stage(shell, synthesis.LINES, synthesis.LINES, apply))

        stated = cls._length_stage(goal)
        if stated is not None:
            stages.append(stated)
        return tuple(stages)

    @staticmethod
    def _length_stage(goal: str) -> Any:
        """A length filter, when the request states one as a comparison.

        "The lines longer than 20 characters" is `awk 'length($0) > 20'` and
        nothing else in the grammar does it.  The number is read from the
        sentence, so the stage is a reading of the request rather than a guess
        over a table of thresholds.
        """
        found = LivingAgent._LENGTH_FILTER.search(goal.lower())
        if not found:
            return None
        if found.group(1):
            relation, amount = found.group(1), int(found.group(2))
        else:
            relation, amount = found.group(3).replace(" ", ""), int(found.group(4))
        operator = {
            "longer": ">", "more": ">", "greater": ">", "bigger": ">",
            "shorter": "<", "fewer": "<", "less": "<", "smaller": "<",
            "atleast": ">=", "atmost": "<=",
        }[relation]

        def apply(text: str, op: str = operator, n: int = amount) -> str:
            keep = {
                ">": lambda size: size > n,
                "<": lambda size: size < n,
                ">=": lambda size: size >= n,
                "<=": lambda size: size <= n,
            }[op]
            return synthesis.as_text([line for line in synthesis.as_lines(text) if keep(len(line))])

        return synthesis.Stage(f"awk 'length($0) {operator} {amount}'", synthesis.LINES, synthesis.LINES, apply)

    def _base_grammar(self, inputs: Sequence[tuple[str, str]], goal: str = "") -> tuple[Any, ...]:
        """The grammar whose stages cost nothing to apply.

        Every stage here is pure computation, which is what a *search* needs:
        it applies stages to hundreds of intermediate texts, and an earned
        stage would turn each of those into a process.  Earned stages are
        tried deliberately, in their own loop, where each costs one run.
        """
        stages = synthesis.instantiate(inputs)
        if goal:
            own = {stage.shell for stage in stages}
            for stage in self._derived_stages(goal):
                if stage.shell not in own:
                    own.add(stage.shell)
                    stages = stages + (stage,)
        return stages + tuple(self._stages.values())

    def _grammar(self, inputs: Sequence[tuple[str, str]], goal: str = "") -> tuple[Any, ...]:
        """The fixed grammar plus everything this creature has earned."""
        base = self._base_grammar(inputs, goal)
        seen = {stage.shell for stage in base}
        return base + tuple(stage for stage in self._learned_stages() if stage.shell not in seen)

    def _candidate_stages(
        self,
        goal: str,
        sources: Sequence[str],
        manners: Sequence[str] = (),
        *,
        limit: int = 64,
    ) -> list[tuple[discovery.ToolDoc, list[str], str, int, int]]:
        # `manners` carries orderings the examples demonstrate ("numerically",
        # "reverse"); they join the sentence's own adverbs as option evidence.
        """Documented invocations worth *trying*, ordered by evidence strength.

        The request's words, plus the words the data itself makes meaningful,
        are matched against each tool's entire self-description -- summary and
        every option line -- because a tool's useful vocabulary often lives in
        its options ("select only these fields") rather than in its one-line
        summary.  Breadth comes before depth: the first form of every plausible
        tool is tried before any tool gets a second one, because a keyword score
        is a prior and a wrong prior about one tool must not crowd out the rest.

        This is recall, not decision: keywords decide what to *try*, and every
        candidate is executed before anything is believed.
        """
        vocabulary = self.vocabulary
        vocabulary.read()
        located = dict(vocabulary.executables())
        named = set(discovery._words(goal))
        wanted = named | self._structure_words(sources)
        scored: list[tuple[int, str, discovery.ToolDoc]] = []
        for doc in vocabulary.read():
            if doc.name in discovery.DENY or doc.name not in located:
                continue
            described = self._described_cache.get(doc.name)
            if described is None:
                described = set(doc.words)
                for option in doc.options:
                    described |= set(discovery._words(option.description))
                    described |= set(discovery._words(option.long.lstrip("-").replace("-", " ")))
                self._described_cache[doc.name] = described
            overlap = len(wanted & described)
            # A tool the request *names* is a candidate however little its own
            # documentation happens to share with the sentence: "fold each line
            # at 40 characters" says "fold", and fold's summary never says
            # "line".  Two shared words is the bar for everything else.
            # A tool whose own usage line consumes the very characters the
            # sentence names is relevant however little prose it shares: `tr`
            # never says "comma" or "replace", but `tr STRING1 [STRING2]` is
            # exactly the translation of two named sets, and no other tool on
            # this machine declares that shape.
            names_values = bool(self._named_characters(goal)) and any(
                self._OPERAND_CHARS.match(operand.strip("[]").upper())
                for operand in doc.operands
            )
            if overlap >= 2 or doc.name in named or names_values:
                scored.append((overlap, doc.name, doc))
        scored.sort(key=lambda row: (-row[0], row[1]))
        per_tool: list[list[tuple[discovery.ToolDoc, list[str], str, int, int]]] = []
        for overlap, _name, doc in scored:
            forms = [
                (doc, form, located[doc.name], overlap, strength)
                for strength, form in self._argument_forms(goal, doc, sources, manners)
                # A first-stage mechanism must be justified by evidence the
                # request or the data supply -- a number, a position, a
                # separator -- not by a keyword: switches that merely share a
                # word with the goal are the most numerous candidates and the
                # least likely to be the missing mechanism.
                if form and strength >= 4
            ][:4]
            if forms:
                per_tool.append(forms)
        out: list[tuple[discovery.ToolDoc, list[str], str, int, int]] = []
        for depth in range(4):
            for forms in per_tool:
                if depth < len(forms):
                    out.append(forms[depth])
                    if len(out) >= limit:
                        return out
        return out

    def _named_prefixes(
        self, goal: str, sources: Sequence[str], grammar: Sequence[Any]
    ) -> list[tuple[str, list[str]]]:
        """Stages the sentence puts before the mechanism, already applied.

        Applying a grammar stage is pure computation, so this costs nothing:
        the text the mechanism will really see is prepared once and shared by
        every candidate mechanism.
        """
        out: list[tuple[str, list[str]]] = []
        for prefix_shell in self._requested_prefixes(goal):
            prefix_stage = next((item for item in grammar if item.shell == prefix_shell), None)
            if prefix_stage is None:
                continue
            try:
                prefixed = [prefix_stage.apply(text) for text in sources]
            except ValueError:
                continue
            if prefixed != sources:
                out.append((prefix_shell, prefixed))
        return out

    def _hypotheses(
        self,
        stage: Any,
        sources: Sequence[str],
        expected: Sequence[str],
        grammar: Sequence[Any],
        goal: str,
        *,
        max_length: int,
        time_budget_s: float,
        prefixes: Sequence[tuple[str, list[str]]] = (),
    ) -> list[list[str]]:
        """Every composition this stage could be part of, computed but not run.

        The grammar is pure computation, so all the shapes worth trying for one
        mechanism -- alone, with a suffix, or after a stage the sentence names
        -- are enumerated without a single process.  Only the resulting
        pipelines cost anything, and each is verified by real bytes.
        """
        hypotheses: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()

        def suffixes(mid: Sequence[str], budget: int, exclude: str = "") -> list[list[str]]:
            if list(mid) == list(expected):
                return [[]]
            pipelines, _stats = synthesis.search(
                list(zip(mid, expected)),
                max_length=max(1, budget),
                beam=64,
                time_budget_s=time_budget_s,
                stages=grammar,
            )
            attempts = [list(chosen) for chosen in pipelines]
            # The grammar searches by bytes alone, so a suffix whose
            # intermediate is unchanged never appears in it (`sort -u` of
            # already-unique lines, then `wc -l`).  What the sentence names is
            # the other specification; it is tried and then verified too.
            requested = [item for item in self._requested_stages(goal) if item != exclude]
            if requested:
                attempts.append(requested)
            return attempts

        try:
            mid = [stage.apply(text) for text in sources]
        except ValueError:
            return hypotheses
        for chosen in suffixes(mid, max_length - 1):
            candidate = [stage.shell, *chosen]
            if tuple(candidate) not in seen:
                seen.add(tuple(candidate))
                hypotheses.append(candidate)
        for prefix_shell, prefixed in prefixes:
            try:
                prefixed_mid = [stage.apply(text) for text in prefixed]
            except ValueError:
                continue
            if prefixed_mid == prefixed:
                continue
            for chosen in suffixes(prefixed_mid, max_length - 2, exclude=prefix_shell):
                candidate = [prefix_shell, stage.shell, *chosen]
                if tuple(candidate) not in seen:
                    seen.add(tuple(candidate))
                    hypotheses.append(candidate)
        return hypotheses

    def _consider_grammar_fits(
        self,
        candidates: Sequence[Sequence[str]],
        stats: Mapping[str, Any],
        *,
        goal: str,
        examples: Sequence[tuple[str, str]],
        inputs: Sequence[tuple[str, str]],
        contradicted: list[tuple[list[str], list[str]]],
        evaluated: int,
        runs_before: int,
        started: float,
    ) -> tuple[dict[str, Any] | None, int]:
        """Admit the first exact, explainable pipeline in this candidate list.

        A fit is evidence, not proof, so each candidate is interrogated the
        same way the composed path interrogates its own: exact bytes on every
        example, then the sentence's own probes.  Returns the outcome and the
        number of commands it cost, or None when this list has nothing worth
        admitting -- which is the caller's signal to widen the grammar.
        """
        for stages in candidates:
            # A pipeline that contradicts the sentence is refused before it
            # costs a process: reading the request is free, running is not.
            unexplained = self._unexplained_request(goal, stages)
            if unexplained:
                contradicted.append((list(stages), unexplained))
                continue
            template = synthesis.command_for(stages)
            ok = True
            for index, (_, expected) in enumerate(inputs):
                command = template.replace("{path}", shlex.quote(examples[index][0]))
                result = self.computer.run(command)
                evaluated += 1
                if not result.ok or result.stdout != expected:
                    ok = False
                    break
            if not ok:
                continue
            unexplained = self._unexplained_request(goal, stages)
            if not unexplained:
                # The same behavioural questions the composed path asks: a
                # pipeline that fits the bytes but answers a different question
                # is a coincidence, not a mechanism.
                failure = self._sentence_probe_failure(goal, stages, examples)
                if failure:
                    unexplained = [failure]
            if not unexplained and self._depends_only_on_named_column(goal, stages, examples) is False:
                unexplained = [f"a count that depends on column {_ordinal_positions(goal)[0]}"]
            if unexplained:
                contradicted.append((list(stages), unexplained))
                continue
            skill = self._admit_synthesized(goal, stages, examples, template)
            outcome = self.solve(goal, bindings={"path": examples[0][0]})
            outcome.update(
                {
                    "learned": True,
                    "stages": list(stages),
                    "exact_hypotheses": len(candidates),
                    "probe_seconds": stats.get("seconds"),
                    "commands_run": max(evaluated, self._runs - runs_before),
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome, evaluated
        return None, evaluated

    def _compose(
        self,
        goal: str,
        examples: Sequence[tuple[str, str]],
        *,
        max_length: int,
        time_budget_s: float,
        workers: int = 16,
    ) -> tuple[list[str], dict[str, Any]] | None:
        """One documented mechanism feeding the known grammar.

        The machine's own tools are the mechanisms; the fixed grammar is what
        can follow them.  Candidate invocations are *fingerprinted* first --
        each is really run once, in parallel -- and only the ones that actually
        change the text are composed.  That is what makes an argument bundle
        found by keywords harmless: a wrong guess costs one process and is
        discarded before it can influence anything.

        A survivor is then applied to every example, the grammar is searched
        from what it produced, and the whole pipeline is run for real on every
        example.  Only exact bytes are admitted.
        """
        inputs = [(self.computer.read(path), expected) for path, expected in examples]
        sources = [text for text, _ in inputs]
        expected = [text for _, text in inputs]
        before = set(self.computer.admitted())
        grammar = self._base_grammar(inputs, goal)
        candidates = self._candidate_stages(goal, sources, self._demonstrated_manners(goal, examples))
        if not candidates:
            return None
        scratch = tempfile.mkdtemp(prefix="brain-compose-")
        try:
            runs_before = self._runs
            # What answered this kind of request before, cheapest first.  A
            # remembered mechanism is re-verified on these examples like
            # anything else; the memory only saves the search, never the proof.
            recalled = self._recall_mechanism(
                goal,
                examples,
                grammar,
                scratch,
                max_length=max_length,
                time_budget_s=time_budget_s,
            )
            if recalled is not None:
                pipeline, detail = recalled
                self._settle_admissions(before, winner=detail["tool"])
                detail["tested"] = max(1, self._runs - runs_before)
                return pipeline, detail
            # Second cheapest: the vocabulary this creature has already earned.
            # Every entry was verified on real bytes somewhere else; testing it
            # here costs a handful of processes instead of a fresh hunt.
            for stage in self._learned_stages()[:8]:
                for pipeline in self._hypotheses(
                    stage,
                    sources,
                    expected,
                    grammar,
                    goal,
                    max_length=max_length,
                    time_budget_s=time_budget_s,
                    prefixes=self._named_prefixes(goal, sources, grammar),
                ):
                    if not self._confirm(goal, pipeline, examples):
                        continue
                    record = self._learned.get(stage.shell) or {}
                    tool = str(record.get("tool", ""))
                    doc = self.vocabulary.doc(tool)
                    if doc is not None:
                        self._remember_mechanism(goal, doc, list(record.get("argv") or []))
                    self._settle_admissions(before, winner=tool)
                    prefix_shell = pipeline[0] if pipeline[0] != stage.shell else ""
                    return pipeline, {
                        "documented": [stage.shell],
                        "grammar": pipeline[2:] if prefix_shell else pipeline[1:],
                        "prefix": prefix_shell,
                        "tested": max(1, self._runs - runs_before),
                        "tool": tool,
                        "argv": list(record.get("argv") or []),
                        "reused_stage": True,
                    }
            # Trial order, strongest prior first:
            #
            # 1. the request names the tool ("fold each line at 40 characters");
            # 2. two independent grounded facts beat either alone (a position
            #    *and* the separator the data contains);
            # 3. among equals, the fewest arguments -- a bundle that needs one
            #    argument explains the same bytes more cheaply than one that
            #    needs two;
            # 4. then how much of the tool's own documentation the request
            #    actually uses.
            #
            # The winner is usually in the first handful, and a candidate that
            # is never reached costs nothing.
            named = set(discovery._words(goal))
            ordered = sorted(
                candidates,
                key=lambda row: (
                    0 if row[0].name in named else 1,
                    -row[4],
                    sum(1 for part in row[1] if part.startswith("-")),
                    -row[3],
                ),
            )
            tested = len(candidates)
            # Stages the sentence puts before the mechanism: "take the first
            # four rows, then sort them" is a different function from "sort
            # everything and keep four", because the selection happens first.
            prefixes = self._named_prefixes(goal, sources, grammar)

            def fingerprint(stage: Any) -> str | None:
                try:
                    return stage.apply(sources[0])
                except ValueError:
                    return None

            def verified(pipeline: Sequence[str]) -> bool:
                return self._confirm(goal, pipeline, examples)

            survivors: list[tuple[Any, Any, str]] = []
            # Fingerprinting is one process per candidate: run a chunk in
            # parallel, then test what it produced in evidence order, and stop
            # as soon as a pipeline is confirmed.  The first chunks are small on
            # purpose.  The candidate order is a prior and the best prior is
            # usually right, so probing one, then two, then four keeps the
            # common case at one process while still scanning a wide field
            # quickly when the prior is wrong.
            offset = 0
            width = 1
            while offset < len(ordered):
                chunk = ordered[offset:offset + width]
                offset += width
                width = min(width * 2, 8)
                stages = [
                    self._stage_for(doc, form, binary, cwd=scratch)
                    for doc, form, binary, _overlap, _strength in chunk
                ]
                with ThreadPoolExecutor(max_workers=8) as pool:
                    firsts = list(pool.map(fingerprint, stages))
                tail = self._requested_stages(goal)
                for (doc, form, _binary, _overlap, _strength), stage, first in zip(chunk, stages, firsts):
                    if first is None or first == sources[0]:
                        continue
                    if self._tail_impossible(first, tail, expected[0]):
                        continue
                    survivors.append((doc, form, _binary, _overlap, _strength))
                    for pipeline in self._hypotheses(
                        stage,
                        sources,
                        expected,
                        grammar,
                        goal,
                        max_length=max_length,
                        time_budget_s=time_budget_s,
                        prefixes=prefixes,
                    ):
                        if not verified(pipeline):
                            continue
                        pipeline = list(self._minimise(goal, pipeline, examples))
                        self._settle_admissions(before, winner=doc.name)
                        self._log_composition(
                            candidates, [(row, stage, first) for row in survivors], doc, form, tested
                        )
                        self._remember_mechanism(goal, doc, form)
                        self._learn_stage(doc, form, _binary)
                        prefix_shell = pipeline[0] if pipeline[0] != stage.shell else ""
                        return pipeline, {
                            "documented": [stage.shell],
                            "grammar": pipeline[2:] if prefix_shell else pipeline[1:],
                            "prefix": prefix_shell,
                            "tested": self._runs - runs_before,
                            "tool": doc.name,
                            "argv": list(form),
                        }
            self._settle_admissions(before, winner="")
            return None
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def _settle_admissions(self, before: set[str], *, winner: str) -> None:
        """Leave no authority behind from a probe.

        Trying a stranger means admitting it for one run.  Keeping it admitted
        afterwards would let every failed guess widen what the computer may
        execute, so only the winner of a successful search survives.
        """
        for name in set(self.computer.admitted()) - before:
            if name != winner:
                self.computer.revoke(name)

    def _log_composition(
        self,
        candidates: Sequence[tuple[discovery.ToolDoc, list[str], str, int, int]],
        survivors: Sequence[Any],
        winner: discovery.ToolDoc,
        form: Sequence[str],
        tested: int,
    ) -> None:
        """Record what was composed, and that everything else was rejected."""
        self.discovery_log.append(
            {
                "tool": winner.name,
                "reading": "composition",
                "source": "composed",
                "verified": True,
                "documentation": winner.summary,
                "argv": list(form),
            }
        )
        for (doc, _form, _binary, _overlap, _strength), _stage, _first in survivors:
            if doc.name == winner.name:
                continue
            self.discovery_log.append(
                {
                    "tool": doc.name,
                    "reading": "composition",
                    "source": "composed",
                    "verified": False,
                    "documentation": doc.summary,
                    "argv": [],
                }
            )
        del self.discovery_log[: max(0, len(self.discovery_log) - 200)]

    def _sentence_probe_failure(
        self, goal: str, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> str:
        """The first behavioural question the pipeline fails, or an empty string.

        These are not style checks: each one runs the pipeline on a text the
        examples did not contain and compares the answer against something the
        *sentence* determines.  They only ever reject, and each returns None
        (no failure) when the question does not apply.
        """
        if self._selection_matches_the_sentence(goal, stages, examples) is False:
            return "the answer does not select the lines the request describes"
        if self._order_ignores_input_row_order(goal, stages, examples) is False:
            return "the answer depends on the order of the rows"
        if self._order_holds_on_a_fresh_permutation(goal, stages, examples) is False:
            return "the answer is not ordered by the column the request names"
        return ""

    def _confirm(
        self, goal: str, pipeline: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool:
        """Is this pipeline both exactly right and an answer to the request?

        Three gates, in increasing cost: the real shell must reproduce every
        example byte for byte; the pipeline must do what the sentence says
        (position, separator, named operations, and where they apply); and,
        where it is checkable, a count over a named column must actually depend
        on that column.  Anything less is a coincidence that happens to fit.
        """
        # Cheapest first: reading the sentence costs nothing, running the
        # pipeline costs processes, and the column probe costs three more.  A
        # pipeline that contradicts the request is refused before it runs.
        if self._unexplained_request(goal, pipeline):
            return False
        try:
            if not self._matches_every_example(pipeline, examples):
                return False
        except AgentError:
            return False  # not a command this computer will execute
        if self._sentence_probe_failure(goal, pipeline, examples):
            return False
        return self._depends_only_on_named_column(goal, pipeline, examples) is not False

    def _minimise(
        self, goal: str, pipeline: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> tuple[str, ...]:
        """The same answer with every stage that earns nothing removed.

        A search that scans a wide field can arrive at a pipeline whose first
        stage only prepared the text for a stage that turned out not to need
        it: `pr -N 20 | awk 'length($0) > 20'` answers the length request, but
        the `pr` is dead weight the pipeline would carry forever.  Each stage is
        dropped in turn, and the shorter pipeline has to pass the same checks --
        examples, sentence probes, column dependence -- before the drop stands.
        So a stage that is load-bearing anywhere on the evidence stays.
        """
        best = tuple(pipeline)
        if len(best) > 1:
            # The sentence's own stage often does the whole job alone: an
            # `awk` length filter needs no preamble, even when the search found
            # one that happened to cancel out.  Try each stage by itself first,
            # since a single stage is the shortest answer there can be.
            for stage in best:
                if self._confirm(goal, [stage], examples):
                    return (stage,)
        changed = True
        while changed and len(best) > 1:
            changed = False
            for index in range(len(best)):
                shorter = best[:index] + best[index + 1:]
                if not shorter:
                    continue
                if self._confirm(goal, shorter, examples):
                    best = shorter
                    changed = True
                    break
        return best

    @classmethod
    def _shares_words(cls, option_words: set[str], goal_tokens: set[str]) -> bool:
        """Does the option describe itself with a word the sentence used?

        "characters" and "character" are the same word; exact set intersection
        cannot see that, and picking a byte selection for a request about
        characters is a real difference on non-ASCII data.
        """
        return any(cls._word_matches(left, right) for left in option_words for right in goal_tokens)

    @staticmethod
    def _word_matches(left: str, right: str) -> bool:
        """Do two words name the same thing up to inflection?

        "numerically" and "numeric" do; "country" and "count" do not, because
        the shorter word has to be at least four letters for a prefix to mean
        anything.
        """
        if left == right:
            return True
        short, long = (left, right) if len(left) <= len(right) else (right, left)
        return len(short) >= 4 and long.startswith(short)

    @classmethod
    def _qualifier_flags(cls, word: str, doc: discovery.ToolDoc) -> list[str]:
        """Switches of *this* tool whose own wording explains a qualifier.

        "numerically" is explained by sort's `-n, --numeric-sort` ("compare
        according to string numerical value").  Whatever a *different* tool
        means by `-n` -- ls's numeric owner IDs, split's numeric suffixes -- is
        not an explanation of this sentence, so only the tool that will run is
        consulted.
        """
        flags: list[str] = []
        for option in doc.options:
            if option.argument:
                continue  # a switch, not something that takes a value
            spelling = option.short or option.long
            if not spelling:
                continue
            words = set(discovery._words(option.description))
            words |= set(discovery._words(option.long.lstrip("-").replace("-", " ")))
            if any(cls._word_matches(word, candidate) for candidate in words):
                flags.append(spelling)
        return flags

    def _unexplained_modifiers(self, goal: str, stages: Sequence[str]) -> list[str]:
        """Qualifiers the request states that the pipeline does not implement.

        "Sort the rows by the second column, numerically" is not answered by a
        lexical sort that happens to fit two files: on the third file it is
        wrong, and the word said so all along.  A manner adverb that the
        documentation of a tool *in the pipeline* explains must appear as that
        tool's option; otherwise part of the request has been ignored, which is
        how a system ends up confidently wrong.
        """
        missing: list[str] = []
        for word in sorted(set(re.findall(r"[a-z]+", goal.lower()))):
            if len(word) < 6 or not word.endswith("ly"):
                continue  # manner adverbs only: qualifiers about *how*
            explained = False
            relevant = False
            for stage in stages:
                parts = shlex.split(stage)
                doc = self.vocabulary.doc(parts[0]) if parts else None
                if doc is None:
                    continue
                flags = self._qualifier_flags(word, doc)
                if not flags:
                    continue
                relevant = True
                if any(flag in parts for flag in flags):
                    explained = True
                    break
            if relevant and not explained:
                missing.append(word)
        return missing

    def _unexplained_structure(self, goal: str, stages: Sequence[str]) -> list[str]:
        """What the request says about the shape of the data that the stages ignore.

        A stage list can reproduce every example and still not be an answer.  On
        three rows, "reverse the first two" matches a truncated sort by the
        third column; the bytes agree and the sentence does not.  The request
        and the examples are two independent specifications, so a pipeline that
        satisfies one while contradicting the other is a coincidence, not
        knowledge.

        Only structure the request *names* is checked -- an ordinal beside a
        unit noun, a named separator -- and only as a necessary condition: the
        number has to occur, the character has to occur.  This cannot prove a
        pipeline right; it can prove one cannot be the answer.
        """
        text = " ".join(stages)
        missing: list[str] = []
        for position in _ordinal_positions(goal):
            # `-f2` and `-k 2` are the same claim; `-f 12` is not position 2.
            if not re.search(rf"(?<![\d.]){position}(?![\d.])", text):
                missing.append(f"position {position}")
        words = set(re.findall(r"[a-z]+", goal.lower()))
        for word, character in _SEPARATOR_WORDS.items():
            if word not in words:
                continue
            item = f"separator {character}"
            if item in missing:
                continue
            if character == "\t":
                present = "\t" in text or "\\t" in text
            else:
                present = character in text
            if not present:
                missing.append(item)
        return missing

    @staticmethod
    def _requested_prefixes(goal: str) -> list[str]:
        """Stages the sentence puts *before* the mechanism.

        "Take the first four rows, then sort them by the second column" is not
        "sort everything and keep four": the selection happens first, so the
        mechanism sees four rows, not all of them.  Only selections the
        sentence puts first are returned -- "keep the first two" is what
        remains *after* the transformation, which is the opposite end.
        """
        prefixes: list[str] = []
        for label, _pattern, role in _requested_operations(goal):
            if role != "prefix":
                continue
            if label.startswith("first "):
                prefixes.append("head -n " + label.split()[1])
            elif label.startswith("last "):
                prefixes.append("tail -n " + label.split()[1])
        return prefixes

    @staticmethod
    def _requested_stages(goal: str) -> list[str]:
        """The tail of a pipeline the sentence itself specifies, in order.

        When the request says "count the distinct values", it has named two
        operations and their order; the bytes only have to agree.  This is the
        same reading ``_requested_operations`` checks against, spelled as the
        stages that perform it.  Nothing here is guessed from the examples --
        a stage appears only because a phrase in the request asks for it, and
        selections the sentence puts first are not part of the tail.
        """
        stages: list[str] = []
        operations = _requested_operations(goal)
        if any(label == "distinct values" for label, _p, _r in operations):
            stages.append("sort -u")
        for label, _pattern, role in operations:
            if role == "prefix":
                continue
            if label.endswith(" characters"):
                size = label.split()[1]
                stages.append(f"cut -c 1-{size}" if label.startswith("first") else f"cut -c -{size}")
            elif label.startswith("first "):
                stages.append("head -n " + label.split()[1])
            elif label.startswith("last "):
                stages.append("tail -n " + label.split()[1])
        for label in (label for label, _p, _r in operations if label.startswith("a count")):
            if "characters in each line" in label:
                stages.append("awk '{print length($0)}'")
            elif "characters" in label:
                stages.append("wc -m")
            elif "words in each line" in label:
                stages.append("awk '{print NF}'")
            elif "words" in label:
                stages.append("wc -w")
            else:
                stages.append("wc -l")
        return stages

    def _unexplained_request(self, goal: str, stages: Sequence[str]) -> list[str]:
        """Everything the request says the stages do not do.

        Two kinds of statement are checked: the *structure* of the data (an
        ordinal beside a unit noun, a named separator) and the *operations* the
        sentence names outright ("keep the first two", "distinct", "count").
        A verified pipeline that ignores either is not an answer to this
        request, however exactly it reproduces the examples.
        """
        text = " ".join(stages)
        missing = self._unexplained_structure(goal, stages)
        missing.extend(self._unexplained_modifiers(goal, stages))
        first = stages[0] if stages else ""
        last = stages[-1] if stages else ""
        for label, pattern, role in _requested_operations(goal):
            if not re.search(pattern, text):
                missing.append(label)
                continue
            # Where the sentence puts an operation is part of what it says.
            # "Keep the first two" happens to what the sort left; a pipeline
            # that keeps two *before* sorting has answered a different
            # question, and on more rows it gives a different answer.
            if role == "suffix" and not re.search(pattern, last):
                missing.append(label + " last")
            elif role == "prefix" and not re.search(pattern, first):
                missing.append(label + " first")
        return missing

    _CONTAINMENT = re.compile(
        r"\b(contain|contains|containing|include|includes|including|with|having|match|matches|matching)\b"
    )
    _LENGTH_FILTER = re.compile(
        r"\b(longer|shorter|more|fewer|greater|less|bigger|smaller)\s+than\s+(\d{1,4})\s*"
        r"(?:character|characters|char|chars|byte|bytes)\b"
        r"|\b(at\s+least|at\s+most)\s+(\d{1,4})\s*(?:character|characters|char|chars|byte|bytes)\b"
    )
    _PREFIX_FILTER = re.compile(
        r"\b(?:start|starts|starting|begin|begins|beginning)\s+(?:with|by)\s+(\S+)"
    )
    _SUFFIX_FILTER = re.compile(r"\b(?:end|ends|ending)\s+with\s+(\S+)")

    @classmethod
    def _affix_pattern(cls, goal: str) -> str:
        """The regular expression a prefix or suffix request describes.

        "Lines that start with a" is the set of lines matching ``^a`` -- the
        sentence itself says what the pattern is, and the tool documents that it
        takes one.  Escaping the token keeps a literal dot or bracket literal.
        """
        found = cls._PREFIX_FILTER.search(goal.lower())
        if found:
            token = found.group(1).strip("'\"")
            if token:
                return "^" + re.escape(token)
        found = cls._SUFFIX_FILTER.search(goal.lower())
        if found:
            token = found.group(1).strip("'\"")
            if token:
                return re.escape(token) + "$"
        return ""

    def _line_predicate(self, goal: str) -> tuple[Any, str] | None:
        """The per-line test the sentence describes, if it describes one.

        "The lines that contain error", "the lines longer than 20 characters",
        "the lines that start with a" are all statements about what a line must
        satisfy.  Each defines a function on any text, which is what lets the
        answer be checked on a text the examples never contained instead of
        being taken on faith.
        """
        lowered = goal.lower()
        found = self._LENGTH_FILTER.search(lowered)
        if found:
            if found.group(1):
                relation, amount = found.group(1), int(found.group(2))
            else:
                relation, amount = found.group(3).replace(" ", ""), int(found.group(4))
            if relation in {"longer", "more", "greater", "bigger"}:
                test = (lambda line, n=amount: len(line) > n)
            elif relation in {"shorter", "fewer", "less", "smaller"}:
                test = (lambda line, n=amount: len(line) < n)
            elif relation == "atleast":
                test = (lambda line, n=amount: len(line) >= n)
            else:
                test = (lambda line, n=amount: len(line) <= n)
            return test, "length"
        found = self._PREFIX_FILTER.search(lowered)
        if found:
            token = found.group(1).strip("'\"")
            if token:
                return (lambda line, t=token: line.startswith(t)), "prefix"
        found = self._SUFFIX_FILTER.search(lowered)
        if found:
            token = found.group(1).strip("'\"")
            if token:
                return (lambda line, t=token: line.endswith(t)), "suffix"
        if self._CONTAINMENT.search(lowered):
            path, expected = "", ""
            return None, "containment"
        return None

    def _selection_matches_the_sentence(
        self, goal: str, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool | None:
        """Does the answer select the lines the sentence describes?

        A sentence that says what a line must be is a specification for *any*
        text, so it is checked on a probe the examples never contained.  A
        positional stand-in (`tail -n +2`) fits two files where the described
        line happens to come second, and fails immediately here.

        Returns None unless the reading applies and the examples already agree
        with it -- a sentence that means something else is not judged by a
        filter it did not ask for.
        """
        reading = self._line_predicate(goal)
        predicate, kind = reading if reading else (None, "")
        if predicate is None and kind != "containment":
            return None
        path, expected = examples[0]
        text = self.computer.read(path)
        if predicate is None:
            words = [
                word
                for word in sorted(_tokens(goal))
                if word.isalpha() and len(word) > 2 and word in text
                and word not in {"line", "lines"}
            ]
            if len(words) != 1:
                return None
            word = words[0]
            predicate = lambda line, w=word: w in line  # noqa: E731
        selected = "".join(line + "\n" for line in text.splitlines() if predicate(line))
        if expected != selected:
            return None
        # Two probes, both written by the sentence rather than by the examples:
        # one matching line at the front, one non-matching line at the end.
        matching = next(
            (candidate for candidate in ("a line for the test" * 3, "zzzz probe", "x")
             if predicate(candidate)),
            None,
        )
        missing = next(
            (candidate for candidate in ("", "q", "~", "###")
             if not predicate(candidate)),
            None,
        )
        if matching is None or missing is None:
            return None
        probe = matching + "\n" + text + missing + "\n"
        oracle = "".join(line + "\n" for line in probe.splitlines() if predicate(line))
        self._runs += 1
        result = self.computer.run(" | ".join(stages), stdin=probe)
        if not result.ok:
            return None
        return result.stdout == oracle

    @staticmethod
    def _orders_by_named_column(goal: str) -> int | None:
        """The column an ordering request says to order by, if it says one."""
        text = goal.lower()
        if not re.search(r"\b(sort|sorted|sorting|order|ordered|ordering|rank|ranked|arrange|arranged)\b", text):
            return None
        positions = _ordinal_positions(goal)
        return positions[0] if positions else None

    @staticmethod
    def _numbers(text: str) -> list[float] | None:
        try:
            return [float(value) for value in text]
        except ValueError:
            return None

    def _demonstrated_manners(
        self, goal: str, examples: Sequence[tuple[str, str]]
    ) -> list[str]:
        """Manners the examples *show*, which the sentence did not spell out.

        "Sort the rows by the second column" over 1, 2 and 10 is a numeric
        request even without the word: the shown answer is the numeric order,
        and no lexical order of those values produces it.  Likewise an answer
        that runs from large to small shows a reversed order.  The examples are
        half the specification, so what they demonstrate is evidence -- and the
        same exact-bytes verification still has to agree.
        """
        if not examples:
            return []
        position = self._orders_by_named_column(goal)
        if position is None:
            return []
        path, expected = examples[0]
        text = self.computer.read(path)
        separator = (self._separators([text, expected])[:1] or [""])[0]
        if not separator:
            return []
        source_rows = [row.split(separator) for row in text.splitlines()]
        answer_rows = [row.split(separator) for row in expected.splitlines()]
        if not answer_rows or any(
            len(row) < position for row in [*source_rows, *answer_rows]
        ):
            return []
        values = [row[position - 1] for row in source_rows]
        shown = [row[position - 1] for row in answer_rows]
        numbers = self._numbers(shown)
        manner: list[str] = []
        if numbers is not None and (
            numbers == sorted(numbers) or numbers == sorted(numbers, reverse=True)
        ):
            if sorted(values) != sorted(values, key=float):
                # A lexical sort of these values would have produced a
                # different order, so "numbers" is what the example shows.
                manner.append("numerically")
        if shown == sorted(shown, reverse=True) and shown != sorted(shown):
            manner.append("reverse")
        elif numbers is not None and numbers == sorted(numbers, reverse=True):
            if numbers != sorted(numbers):
                manner.append("reverse")
        return manner

    def _order_ignores_input_row_order(
        self, goal: str, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool | None:
        """Is the answer the same when the rows arrive in a different order?

        "Sort the rows by the second column" is a statement about the *values*
        in that column.  A pipeline whose answer changes when the same rows
        arrive in a different order is answering from the input's row order
        instead -- `sort -k 2 -t , | sort -r` fits two examples that way and is
        wrong on the third.  Reversal is the cheapest question that separates
        the two readings, and it can only reject: a pipeline that genuinely
        orders by values gives the same answer either way.

        Returns None when the question does not apply (no ordering verb, no
        named column, fewer than three rows, or a tie that makes reversal a
        legitimate difference).
        """
        position = self._orders_by_named_column(goal)
        if position is None:
            return None
        if any(label.startswith(("first ", "last ")) for label, _p, _r in _requested_operations(goal)):
            # "Take the first four rows, then sort them" is a statement about
            # these rows in this order.  Reversing the input legitimately gives
            # a different answer, so row order is part of the request and this
            # question cannot be asked.
            return None
        path, expected = examples[0]
        text = self.computer.read(path)
        rows = text.splitlines()
        if len(rows) < 3:
            return None
        separator = (self._separators([text])[:1] or [""])[0]
        if not separator:
            return None
        fields = [row.split(separator) for row in rows]
        if any(len(field) < position for field in fields):
            return None
        values = [field[position - 1] for field in fields]
        if len(set(values)) != len(values):
            return None  # equal keys make a different order in the ties legitimate
        pipeline = " | ".join(stages)

        def answer(payload: str) -> str | None:
            self._runs += 1
            result = self.computer.run(pipeline, stdin=payload)
            return result.stdout if result.ok else None

        straight = answer(text)
        if straight is None or straight != expected:
            return None
        reversed_text = "\n".join(reversed(rows)) + "\n"
        return answer(reversed_text) == straight

    @staticmethod
    def _column_order(text: str, separator: str, position: int) -> tuple[str, bool] | None | bool:
        """How a column is ordered: (direction, numeric), None if unordered.

        Returns ``True`` when the text has no such column at all -- there is
        nothing to judge, and a pipeline that drops the column (a projection)
        must not be refused for it.
        """
        rows = text.splitlines()
        if len(rows) < 2:
            return None
        columns = [row.split(separator) for row in rows]
        if any(len(column) < position for column in columns):
            return True
        values = [column[position - 1] for column in columns]

        def direction(sequence: Sequence[Any]) -> str | None:
            ascending = all(a <= b for a, b in zip(sequence, sequence[1:]))
            descending = all(a >= b for a, b in zip(sequence, sequence[1:]))
            return ("ascending" if ascending else "descending") if (ascending or descending) else None

        try:
            numbers: Sequence[Any] | None = [float(value) for value in values]
        except ValueError:
            numbers = None
        for sequence, numeric in ((numbers, True), (values, False)):
            if sequence is None:
                continue
            found = direction(sequence)
            if found is not None:
                return (found, numeric)
        return None

    def _order_holds_on_a_fresh_permutation(
        self, goal: str, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool | None:
        """Does the ordering claim survive values the examples did not contain?

        `sort -k 2 -t , | sort -r` reproduces "1, 2, 10" because reversing a
        lexical sort of these two files happens to agree with the numeric
        answer.  Reversing a *lexical* order is still lexical; the accident is
        exposed by moving the same values onto different rows and asking
        whether the answer is ordered the way the example was.  One probe, one
        run, and only for goals that name an ordering and a column.

        Returns None when the examples do not fix an order, the column is not
        present, or the probe output has no such column to judge.
        """
        position = self._orders_by_named_column(goal)
        if position is None:
            return None
        if stages and re.search(rf"(?<![\d.]){position}(?![\d.])", stages[-1]):
            # The stage that decides the final order already names the column.
            # A single `sort -k 2` states its key; there is nothing to test.
            return None
        path, expected = examples[0]
        text = self.computer.read(path)
        rows = text.splitlines()
        if len(rows) < 3:
            return None
        separator = (self._separators([text])[:1] or [""])[0]
        if not separator:
            return None
        fields = [row.split(separator) for row in rows]
        if any(len(field) < position for field in fields):
            return None
        values = [field[position - 1] for field in fields]
        if len(set(values)) != len(values):
            return None
        wanted = self._column_order(expected, separator, position)
        if not isinstance(wanted, tuple):
            return None
        # The same values on different rows: any answer that really orders by
        # this column lands in the same order, whatever route it took.
        rotated = [list(field) for field in fields]
        for field, value in zip(rotated, values[1:] + values[:1]):
            field[position - 1] = value
        probe = "\n".join(separator.join(field) for field in rotated) + "\n"
        self._runs += 1
        result = self.computer.run(" | ".join(stages), stdin=probe)
        if not result.ok:
            return None
        observed = self._column_order(result.stdout, separator, position)
        if observed is True:
            return None
        return observed == wanted

    def _depends_only_on_named_column(
        self, goal: str, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool | None:
        """Does the answer use the column the request names -- and nothing else?

        `ptx -g 2 -F , | sort -u | wc -l` reproduces "3" on two tables whose
        second column has three distinct values, and it does so without ever
        touching a column: the option is a gap width.  A count over a named
        column can be interrogated, because the answer must *move* when that
        column changes and must *not* move when the other columns do.  Two
        probes, three real runs, and a binding that was never used is exposed.

        Returns None when the question does not apply (no count is asked for,
        no column is named, the answer is not a single scalar, or the count is
        already 1 so a constant column cannot move it).  Only a definite False
        rejects: it means the stage list has been shown not to use the column
        it claims to use, which is a fact about behaviour, not about wording.
        """
        if not any(label.startswith("a count") for label, _p, _r in _requested_operations(goal)):
            return None
        positions = _ordinal_positions(goal)
        if not positions:
            return None
        path, expected = examples[0]
        if len(expected.strip().splitlines()) != 1 or expected.strip() == "1":
            return None
        text = self.computer.read(path)
        separators = self._separators([text])
        if not separators:
            return None
        separator, position = separators[0], positions[0]
        constant: list[str] = []
        others: list[str] = []
        for line in text.splitlines():
            fields = line.split(separator)
            if len(fields) < position:
                return None
            stable = list(fields)
            stable[position - 1] = "0"
            constant.append(separator.join(stable))
            others.append(
                separator.join(
                    field if index + 1 == position
                    else (field.upper() if field.upper() != field else field.lower())
                    for index, field in enumerate(fields)
                )
            )
        pipeline = " | ".join(stages)

        def answer(payload: str) -> str | None:
            self._runs += 1
            result = self.computer.run(pipeline, stdin=payload)
            return result.stdout if result.ok else None

        original = answer(text)
        if original is None:
            return None
        changed = answer("\n".join(constant) + "\n")
        untouched = answer("\n".join(others) + "\n")
        if changed is None or untouched is None:
            return None
        if changed == original:
            return False  # the named column does not move the answer
        if untouched != original:
            return False  # columns the request never named move it
        return True

    def _matches_every_example(
        self, stages: Sequence[str], examples: Sequence[tuple[str, str]]
    ) -> bool:
        """Run the whole pipeline for real on every example, byte for byte.

        Stage-by-stage agreement is evidence, not proof: pipes interact, and an
        exit status can hide a truncated stream.  The admitted command is one the
        shell actually produces these bytes with.
        """
        template = "cat {path} | " + " | ".join(stages)
        for path, expected in examples:
            self._runs += 1
            result = self.computer.run(template.replace("{path}", shlex.quote(path)))
            if not result.ok or result.stdout != expected:
                return False
        return True

    def _stage_for(
        self,
        doc: discovery.ToolDoc,
        form: Sequence[str],
        binary: str,
        *,
        cwd: str | None = None,
    ) -> Any:
        """One documented invocation as an exact, memoised pipeline stage.

        The stage is hermetic like every other probe: it reads its input from
        standard input, writes to standard output, and runs in a throwaway
        directory, because a tool nobody has vetted may write beside itself.
        """
        argv = [binary, *form]
        shell = " ".join([doc.name, *(_shell_spelling(part) for part in form)]).strip()
        memo: dict[str, str] = {}
        workdir = cwd or tempfile.mkdtemp(prefix="brain-stage-")
        env = {"PATH": ":".join(self.computer.search_dirs()), "LC_ALL": "C", "HOME": workdir}

        def apply(text: str) -> str:
            cached = memo.get(text)
            if cached is not None:
                return cached
            shared = (tuple(argv), text)
            cached = self._stage_memo.get(shared)
            if cached is not None:
                memo[text] = cached
                return cached
            if doc.name not in self.computer.admitted():
                self.computer.admit(doc.name, evidence={"summary": doc.summary, "usage": doc.usage, "argv": list(form)})
            self._runs += 1
            code, raw = discovery._run_capped(
                argv, cwd=workdir, env=env, timeout=2.0, limit=1_048_576, stdin_text=text
            )
            if code != 0:
                raise ValueError("STAGE_FAILED:" + doc.name)
            produced = discovery._decode(raw)
            memo[text] = produced
            if len(self._stage_memo) > 4096:
                self._stage_memo.clear()
            self._stage_memo[(tuple(argv), text)] = produced
            return produced

        # An unmodelled tool may consume or produce anything, so it accepts both
        # raw text and a line stream; the data, not a declared type, decides.
        return synthesis.Stage(shell, synthesis.LINES, synthesis.TEXT, apply)

    @staticmethod
    def _tail_impossible(text: str, tail: Sequence[str], expected: str) -> bool:
        """Can a known tail of stages turn this text into the expected answer?

        When the sentence names the operations that follow the mechanism --
        "count", "keep the first three", "the last two rows" -- the tail is
        fixed, so the answer is a pure function of the mechanism's output.  For
        a projection and a count that function is arithmetic on lines, and
        deciding it costs nothing, while deciding it by running the tail costs
        two processes per candidate.  Only a *definite* disagreement answers
        True; anything the arithmetic cannot decide is left to the real
        verification, which is unchanged.
        """
        if not tail or not expected:
            return False
        try:
            text.encode("ascii")
            expected.encode("ascii")
        except UnicodeEncodeError:
            return False
        lines = text.splitlines(keepends=True)
        if tail == ["sort -u", "wc -l"]:
            count = expected.strip()
            if count.isdigit():
                return len({line.rstrip("\n") for line in lines}) != int(count)
            return False
        if len(tail) == 1:
            match = re.fullmatch(r"(head|tail) -n (\d+)", tail[0])
            if match:
                amount = int(match.group(2))
                part = lines[:amount] if match.group(1) == "head" else lines[-amount:]
                return "".join(part) != expected
        return False

    def _named_atoms(
        self, goal: str, doc: discovery.ToolDoc, sources: Sequence[str]
    ) -> list[tuple[str, ...]]:
        """Argument groups of this tool whose *value* the sentence names.

        A pattern the sentence supplies ("the lines that contain error") and a
        character it names ("comma") are values, not inferences: the request
        already says what to pass.  A position ("the second column") is not --
        the value 2 appears nowhere in the sentence -- so it is not included
        here even though it is perfectly good evidence for ranking.
        """
        literal = "\n".join(sources)
        named_tokens = {word for word in _tokens(goal) if len(word) > 2 and word in literal}
        named_chars = set(self._named_characters(goal))
        named: list[tuple[str, ...]] = []
        for _score, parts, _placeholder in self._argument_atoms(goal, doc, sources):
            if not parts:
                continue
            if parts[-1] in named_tokens or parts[-1] in named_chars:
                named.append(tuple(parts))
        return named

    def _fully_named_mechanisms(
        self, goal: str, sources: Sequence[str], limit: int = 4
    ) -> list[discovery.ToolDoc]:
        """Tools whose arguments the sentence already supplies.

        "Replace every comma with a semicolon" names both characters; "the
        lines that contain error" names the pattern.  A command that consumes
        exactly those values needs no search at all: the request *is* the
        invocation.  A request that also names an operation -- keep three,
        count, distinct -- cannot be one command, so the shortcut stands down
        and leaves it to composition.
        """
        if _requested_operations(goal):
            return []
        literal = "\n".join(sources)
        if not any(len(word) > 2 and word in literal for word in _tokens(goal)) and not (
            self._named_characters(goal)
        ):
            return []
        out: list[tuple[int, str, discovery.ToolDoc]] = []
        for doc in self.vocabulary.read():
            if doc.name in discovery.DENY:
                continue
            named = self._named_atoms(goal, doc, sources)
            if not named:
                continue
            # Count distinct *values*, not spellings: a tool that offers the
            # same character under two option names has named one value, and a
            # translation that names two characters is the stronger candidate.
            out.append((len({parts[-1] for parts in named}), doc.name, doc))
        out.sort(key=lambda row: (-row[0], row[1]))
        return [doc for _count, _name, doc in out[:limit]]

    def _find_documented_mechanism(
        self,
        goal: str,
        examples: Sequence[tuple[str, str]],
        *,
        words: Sequence[str] | None = None,
        max_tools: int = 6,
        max_runs: int = 60,
        docs: Sequence[discovery.ToolDoc] | None = None,
        arguments: bool = True,
    ) -> dict[str, Any] | None:
        """Search the machine's documented surface for a command that fits.

        The examples are the specification: a candidate is admitted only if the
        real shell reproduces every example byte for byte.  Candidates are the
        tools whose own documentation mentions the goal -- each one bare first,
        because the simplest mechanism is usually the right one, and then with
        the option bundles its help text documents, bound only to values the
        request or the data supply.
        """
        # A request that names two operations needs at least three stages: the
        # mechanism and each named operation.  One command cannot be that, so
        # searching the single-command space would only spend processes.
        if len(self._requested_stages(goal)) >= 2:
            return None
        vocabulary = self.vocabulary
        vocabulary.read()
        sources = [self.computer.read(path) for path, _ in examples]
        runs = 0
        stopped = False
        attempts: list[dict[str, Any]] = []

        def attempt(doc: discovery.ToolDoc, form: list[str]) -> dict[str, Any] | None:
            nonlocal runs, stopped
            if runs >= max_runs:
                stopped = True
                return None
            # Arguments are data, not shell syntax: a separator such as `|`
            # is a pipe unless it is quoted, and then the *file name* becomes
            # the command.  Every part is quoted before it reaches the shell.
            # A tool that declares a file operand takes the path as an
            # argument; one that does not -- `tr , ';'` translates a stream --
            # would read the path *as data* and fail with "extra operand".  The
            # usage line says which kind it is, so the file is fed on standard
            # input exactly when the tool takes no file of its own.
            takes_file = any(
                self._FILE_NAME.match(operand.strip("[]").upper()) for operand in doc.operands
            )
            invocation = " ".join([doc.name, *(_shell_spelling(part) for part in form)])
            template = f"{invocation} {{path}}" if takes_file else f"cat {{path}} | {invocation}"
            try:
                self.computer.admit(
                    doc.name,
                    evidence={
                        "summary": doc.summary,
                        "usage": doc.usage,
                        "argv": list(form),
                        "examples": len(examples),
                    },
                )
            except AgentError:
                return None
            for index, (_path, expected) in enumerate(examples):
                if runs >= max_runs:
                    break
                # Candidates are tried on *copies*.  A tool that happens to
                # share a word with the request may well be destructive --
                # `unlink` matches "remove the header line" -- and a stranger
                # must never get a chance to modify, truncate or delete the
                # data it is being tested against.  The copy is a few bytes;
                # the demonstration is not replaceable.
                probe = self._example_copy(index, examples)
                result = self.computer.run(template.replace("{path}", shlex.quote(probe)))
                runs += 1
                if not result.ok or result.stdout != expected:
                    self.computer.revoke(doc.name)
                    attempts.append({"tool": doc.name, "argv": list(form), "verified": False})
                    return None
            # Exact bytes are necessary, not sufficient: a command that fits the
            # examples and ignores what the sentence says is the same
            # coincidence the composed path refuses.  Bare `sort` reproduces two
            # already-sorted files and answers nothing at all about "by the
            # third column".
            stage = [invocation]
            if self._unexplained_request(goal, stage) or self._sentence_probe_failure(
                goal, stage, examples
            ):
                self.computer.revoke(doc.name)
                attempts.append({"tool": doc.name, "argv": list(form), "verified": False})
                return None
            attempts.append({"tool": doc.name, "argv": list(form), "verified": True})
            return {
                "template": template,
                "stage": invocation,
                "tool": doc.name,
                "argv": list(form),
                "doc": doc.summary,
                "runs": runs,
            }

        ranked_docs = (
            list(docs)
            if docs is not None
            else vocabulary.ranked(
                words if words is not None else discovery._words(goal), limit=max_tools
            )
        )
        shortlist = [
            doc
            for doc in ranked_docs
            if doc.name not in discovery.DENY
            and any(name == doc.name for name, _ in vocabulary.executables())
        ]
        found: dict[str, Any] | None = None
        # Phase 1: the tools themselves, with no arguments at all.  A tool
        # whose synopsis requires a pattern cannot be run bare: `grep {path}`
        # makes the file name the pattern and reads nothing, which is not an
        # experiment worth two processes.
        for doc in shortlist:
            if stopped:
                break
            if any(
                self._OPERAND_PATTERN.match(operand.strip("[]").upper())
                for operand in doc.operands
            ):
                continue
            found = attempt(doc, [])
            if found is not None:
                break
        # Phase 2: documented arguments, tool by tool, simplest bundle first.
        # A *widened* pass skips this: breadth is what the widening is for, and
        # enumerating every tool's option bundles over forty tools costs the
        # search more than the answer is worth.  A tool that needs an argument
        # is found by the narrow pass, whose ranking was built for it.
        while found is None and not stopped and arguments:
            for doc in shortlist:
                for _strength, form in self._argument_forms(goal, doc, sources):
                    if not form or stopped:
                        continue
                    found = attempt(doc, form)
                    if found is not None or stopped:
                        break
                if found is not None or stopped:
                    break
            break
        for row in attempts:
            self.discovery_log.append(
                {
                    "tool": row["tool"],
                    "reading": "options",
                    "source": "documentation-options",
                    "verified": row["verified"],
                    "documentation": "",
                    "argv": row["argv"],
                }
            )
        if len(self.discovery_log) > 200:
            del self.discovery_log[: len(self.discovery_log) - 200]
        return found

    def _example_copy(self, index: int, examples: Sequence[tuple[str, str]]) -> str:
        """A private copy of an example input, for a candidate to touch.

        Every probe runs against one of these, never against the file the user
        demonstrated with.  A candidate that deletes its input then deletes a
        copy, and the verification still sees the real bytes.
        """
        path, _expected = examples[index]
        target = f".probe/example{index}.dat"
        self.computer.write(target, self.computer.read(path))
        return target

    def _admit_documented_skill(
        self,
        goal: str,
        found: Mapping[str, Any],
        examples: Sequence[tuple[str, str]],
    ) -> ShellSkill:
        template = str(found["template"])
        canary_path, canary_expected = examples[0]
        expected = canary_expected.strip()
        if re.fullmatch(r"-?\d+", expected):
            postcondition = r"^-?\d+$"
        elif expected:
            postcondition = r"\S"
        else:
            postcondition = r"\A\s*\Z"
        skill_id = "A-" + hashlib.sha256(
            json.dumps({"goal": goal, "template": template}, sort_keys=True).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=goal,
            template=template,
            slots={"path": canary_path},
            postcondition=postcondition,
            canary_input={canary_path: self.computer.read(canary_path)},
            canary_expected=canary_expected,
            keywords=sorted(_tokens(goal)),
        )
        if not self._canary_ok(skill):
            raise AgentError("DOCUMENTED_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        self.capabilities["argv:" + template] = {
            "template": template,
            "tool": found.get("tool"),
            "argv": list(found.get("argv", ())),
            "doc": found.get("doc", ""),
            "goal": goal,
        }
        self.memory.add(
            "skill",
            " ".join([goal, *sorted(_tokens(goal))]),
            {"skill_id": skill_id, "kind": "shell", "template": template,
             "argv": list(found.get("argv", ())), "tool": found.get("tool")},
            confidence=0.8,
            tags=("shell", "documented"),
        )
        self.memory.add(
            "episode",
            "learned from the machine's documentation: " + goal,
            {"skill_id": skill_id, "outcome": "learned", "tool": found.get("tool")},
            surprise=0.5,
            tags=("learn", "documented"),
        )
        self._resolve_impasse(goal)
        return skill

    def _admit_composed(
        self,
        goal: str,
        pipeline: Sequence[str],
        examples: Sequence[tuple[str, str]],
    ) -> ShellSkill:
        """Admit a composition, having already proved it on real examples.

        The canary is the same proof the search used: the real shell, the real
        pipeline, exact bytes.  A composed skill that cannot reproduce its own
        first example is refused like any other unverified mechanism.
        """
        stage = pipeline[0]
        template = "cat {path} | " + " | ".join(pipeline)
        canary_path, canary_expected = examples[0]
        expected = canary_expected.strip()
        if re.fullmatch(r"-?\d+", expected):
            postcondition = r"^-?\d+$"
        elif expected:
            postcondition = r"\S"
        else:
            postcondition = r"\A\s*\Z"
        skill_id = "C-" + hashlib.sha256(
            json.dumps({"goal": goal, "pipeline": list(pipeline)}, sort_keys=True).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=goal,
            template=template,
            slots={"path": canary_path},
            postcondition=postcondition,
            canary_input={canary_path: self.computer.read(canary_path)},
            canary_expected=canary_expected,
            keywords=sorted(_tokens(goal)),
        )
        if not self._canary_ok(skill):
            raise AgentError("COMPOSED_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        self.capabilities["pipeline:" + template] = {
            "template": template,
            "stages": list(pipeline),
            "goal": goal,
            "first_stage": stage,
        }
        self.memory.add(
            "skill",
            " ".join([goal, *sorted(_tokens(goal))]),
            {"skill_id": skill_id, "kind": "shell", "template": template, "stages": list(pipeline)},
            confidence=0.8,
            tags=("shell", "composed"),
        )
        self.memory.add(
            "episode",
            "composed a mechanism with the known grammar: " + goal,
            {"skill_id": skill_id, "outcome": "learned", "stages": list(pipeline)},
            surprise=0.6,
            tags=("learn", "composed"),
        )
        self._resolve_impasse(goal)
        return skill

    def _admit_synthesized(
        self,
        goal: str,
        stages: Sequence[str],
        examples: Sequence[tuple[str, str]],
        template: str,
    ) -> ShellSkill:
        canary_path, canary_expected = examples[0]
        canary_text = self.computer.read(canary_path)
        expected = canary_expected.strip()
        if re.fullmatch(r"-?\d+", expected):
            postcondition = r"^-?\d+$"
        elif expected:
            postcondition = r"\S"
        else:
            postcondition = r"\A\s*\Z"
        skill_id = "S-" + hashlib.sha256(
            json.dumps({"goal": goal, "stages": list(stages)}, sort_keys=True).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=goal,
            template=template,
            slots={"path": canary_path},
            postcondition=postcondition,
            canary_input={canary_path: canary_text},
            canary_expected=canary_expected,
            keywords=sorted(_tokens(goal)),
        )
        if not self._canary_ok(skill):
            raise AgentError("SYNTHESIZED_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        self._resolve_impasse(goal)
        self.memory.add(
            "skill",
            " ".join([goal, *sorted(_tokens(goal))]),
            {"skill_id": skill_id, "kind": "shell", "template": template, "stages": list(stages)},
            confidence=0.8,
            tags=("shell", "synthesized"),
        )
        self.memory.add(
            "episode",
            "learned by synthesis: " + goal,
            {"skill_id": skill_id, "outcome": "learned", "stages": list(stages)},
            surprise=0.6,
            tags=("learn", "synthesis"),
        )
        return skill

    # -- intent without examples ------------------------------------------
    def fulfil(
        self,
        goal: str,
        path: str,
        *,
        max_length: int = 4,
        time_budget_s: float = 3.0,
    ) -> dict[str, Any]:
        """Satisfy a goal whose success is *checkable from the result itself*.

        No example output is provided.  The creature reads the checkable
        property out of the goal ("sorted", "unique", "count", "lower"),
        derives the unique target those properties imply, synthesizes a
        pipeline, and then verifies the real output against the property and
        against content conservation.  Anything it cannot check fails closed.
        """
        started = time.perf_counter()
        if not self.computer.exists(path):
            raise AgentError("GOAL_INPUT_MISSING:" + path)
        source = self.computer.read(path)
        if not source:
            raise AgentError("GOAL_INPUT_EMPTY:" + path)
        properties = _properties_from_goal(goal)
        if not properties:
            # No checkable property is named, but the goal may still be exact:
            # "reverse each line" determines every output byte.  Discovery
            # reads the goal, finds a real tool that reproduces that reading,
            # and admits it only after the shell agrees twice.
            return self.discover(goal, path)
        unexplained = _unexplained_words(goal, properties, path)
        if unexplained:
            self._record_impasse(
                goal,
                {
                    "reason": "unmodelled_qualifier",
                    "words": unexplained,
                    "properties": list(properties),
                },
            )
            raise AgentError("GOAL_NOT_VERIFIABLE")
        target = _target_for(properties, source, goal)
        if target is None:
            # The goal *is* understood: its properties are checkable.  What is
            # missing is an exact mechanism -- "keep only the unique lines"
            # needs order-preserving deduplication, and no stage in the known
            # grammar does that (`sort -u` reorders, `uniq` only removes
            # adjacent repeats).  Answering with either would be wrong in a way
            # the goal itself forbids, so the gap goes on the record instead.
            self._record_impasse(
                goal,
                {
                    "reason": "no_exact_mechanism",
                    "properties": list(properties),
                    "unit": "words" if "words" in properties else "lines",
                },
            )
            raise AgentError("GOAL_PROPERTY_COMBINATION_UNSUPPORTED")
        stages = self._grammar([(source, target)], goal)
        candidates, stats = synthesis.search(
            [(source, target)],
            max_length=max_length,
            time_budget_s=time_budget_s,
            stages=stages,
        )
        if not candidates:
            raise AgentError("NO_PIPELINE_WITHIN_BUDGET")
        evaluated = 0
        for stages in candidates:
            template = synthesis.command_for(stages)
            result = self.computer.run(template.replace("{path}", shlex.quote(path)))
            evaluated += 1
            if not result.ok:
                continue
            # The target is the exact bytes the goal determines.  A pipeline
            # that merely *looks* right (an integer, or a sorted list) is not
            # the answer: the modelling layer only nominates candidates, and
            # the real shell has to reproduce the target byte for byte or the
            # candidate is rejected like any other.  This check caught a
            # word-count pipeline that was off by one on the real file while
            # its interpreter said it matched.
            if result.stdout != target:
                continue
            if not _check_properties(properties, result.stdout):
                continue
            if not _conserves(properties, source, result.stdout):
                continue
            skill = self._admit_property_skill(goal, properties, stages, path, source)
            outcome = self.solve(goal, bindings={"path": path})
            outcome.update(
                {
                    "learned": True,
                    "properties": list(properties),
                    "stages": list(stages),
                    "probe_seconds": stats.get("seconds"),
                    "commands_run": evaluated,
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome
        raise AgentError("NO_VERIFIED_PIPELINE")

    def _admit_property_skill(
        self,
        goal: str,
        properties: Sequence[str],
        stages: Sequence[str],
        path: str,
        source: str,
    ) -> ShellSkill:
        template = synthesis.command_for(stages)
        expected = self.computer.run(template.replace("{path}", shlex.quote(path))).stdout
        postcondition = r"^-?\d+$" if "count" in properties else (r"\S" if expected.strip() else r"\A\s*\Z")
        skill_id = "P-" + hashlib.sha256(
            json.dumps({"goal": goal, "stages": list(stages), "properties": list(properties)}, sort_keys=True).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=goal,
            template=template,
            slots={"path": path},
            postcondition=postcondition,
            canary_input={path: source},
            canary_expected=expected,
            keywords=sorted(_tokens(goal)),
            properties=list(properties),
        )
        if not self._canary_ok(skill):
            raise AgentError("PROPERTY_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        self._resolve_impasse(goal)
        self.memory.add(
            "skill",
            " ".join([goal, *sorted(_tokens(goal))]),
            {
                "skill_id": skill_id,
                "kind": "shell",
                "template": template,
                "stages": list(stages),
                "properties": list(properties),
            },
            confidence=0.75,
            tags=("shell", "property"),
        )
        self.memory.add(
            "episode",
            "learned from intent: " + goal,
            {"skill_id": skill_id, "outcome": "learned", "properties": list(properties)},
            surprise=0.5,
            tags=("learn", "property"),
        )
        return skill

    # -- extending the computer's own vocabulary ---------------------------
    def _machine(self) -> discovery.MachineVocabulary:
        """The machine's account of itself, cached across sessions.

        The cache lives outside the sandbox root: it records what the *machine*
        says about its tools, not what the creature has learned.  Learned
        capabilities go in the snapshot; documentation is re-derivable.
        """
        if self._vocabulary is None:
            digest = hashlib.sha256("|".join(self.computer.search_dirs()).encode()).hexdigest()[:12]
            cache = Path(tempfile.gettempdir()) / f"brain-vocabulary-{digest}.json"
            self._vocabulary = discovery.MachineVocabulary(
                self.computer.search_dirs(), cache_path=cache
            )
        return self._vocabulary

    @property
    def vocabulary(self) -> discovery.MachineVocabulary:
        """What this machine says it can do.  Read lazily, cached per machine."""
        return self._machine()

    @staticmethod
    def _probe_text(source: str, reading: discovery.Reading) -> str:
        """A second case any real mechanism must also get right.

        One file is one example, and a file can hide a wrong mechanism
        completely: if every line is a single character, reversing characters
        and doing nothing produce the same bytes.  The probe is built *against
        the reading* -- unsorted order for a sequence, multi-character and
        non-palindromic lines for characters, several words for words -- so a
        mechanism that merely fits the sample is rejected by the creature's own
        test instead of by a user.
        """
        distinct = list(dict.fromkeys(line for line in _lines(source) if line.strip()))
        while len(distinct) < 3:
            distinct.append(f"probe line {len(distinct)} zz")
        ordered = sorted(distinct[:4], key=lambda line: line.encode())
        probe = ordered[1:] + ordered[:1] + ordered[:1]
        if reading.unit == "character":
            probe = [line + "yz" if len(set(line)) < 2 else line for line in probe]
            probe.append("abcabc")
        elif reading.unit == "word":
            probe.append("alpha beta gamma")
        elif reading.unit == "byte":
            probe.append("abc")
        return "\n".join(probe) + "\n"

    def _verified_template(
        self,
        template: str,
        path: str,
        expected: str,
        reading: discovery.Reading,
        probe_text: str,
    ) -> bool:
        """Exact bytes twice, and on an adversarial probe -- never on the original.

        A candidate comes from a keyword match on a stranger's help text, and
        some tools on this machine destroy what they are given (`unlink` was
        one).  The verification therefore runs on a byte-identical copy: it
        proves exactly as much about the bytes and nothing at all about a
        candidate's right to touch the demonstration.
        """
        scratch = ".probe/verify.dat"
        self.computer.write(scratch, self.computer.read(path))
        command = template.replace("{path}", shlex.quote(scratch))
        first = self.computer.run(command)
        if not first.ok or first.stdout != expected:
            return False
        second = self.computer.run(command)
        if not second.ok or second.stdout != expected:
            return False
        probe_expected = reading.expected(probe_text)
        if probe_expected is None:
            return False
        probe_path = ".discovery-probe.txt"
        self.computer.write(probe_path, probe_text)
        try:
            probe = self.computer.run(template.replace("{path}", shlex.quote(probe_path)))
        finally:
            self.computer.path(probe_path).unlink(missing_ok=True)
        return probe.ok and probe.stdout == probe_expected

    def _find_command(
        self,
        reading: discovery.Reading,
        source: str,
        expected: str,
        path: str,
        probe_text: str,
        *,
        max_tools: int,
    ) -> dict[str, Any] | None:
        """Find a real mechanism for one reading, cheapest source first."""
        remembered = self.capabilities.get(reading.key())
        if remembered and self._verified_template(
            remembered["template"], path, expected, reading, probe_text
        ):
            return {
                "template": remembered["template"],
                "tool": remembered.get("tool"),
                "doc": remembered.get("doc", ""),
                "source": "memory",
                "stages": list(remembered.get("stages", ())),
            }

        # A mechanism the creature already speaks.  Only interpreter-exact
        # candidates are worth a real run, so this costs a handful of processes.
        examples = [(source, expected)]
        stages = self._grammar(examples, str(getattr(reading, "request", "")))
        candidates, _stats = synthesis.search(
            examples, max_length=2, beam=80, time_budget_s=0.5, stages=stages
        )
        for chosen in candidates[:12]:
            template = synthesis.command_for(chosen)
            try:
                if self._verified_template(template, path, expected, reading, probe_text):
                    return {
                        "template": template,
                        "tool": None,
                        "doc": "",
                        "source": "synthesis",
                        "stages": list(chosen),
                    }
            except AgentError:
                continue

        # A mechanism nameable by a word the machine already uses.  Reading a
        # name costs nothing and often finds the tool: ``rev`` for "reverse".
        vocabulary = self._machine()
        tried: set[str] = set()
        for name in vocabulary.name_candidates(reading.words, limit=4):
            tried.add(name)
            found = self._try_tool(
                name, reading, expected, path, probe_text, vocabulary, source="name"
            )
            if found is not None:
                return found

        # Ask the machine directly.  Every candidate is tried on a small probe
        # and only the ones that reproduce it exactly survive; documentation
        # then only orders them.  A tool nobody would have guessed is still
        # findable, because the experiment does not depend on vocabulary.
        probe_expected = reading.expected(probe_text)
        if probe_expected is None:
            return None
        # Reading the machine's self-descriptions is what makes the cheap
        # questions possible: which tools mention lines, which ones describe
        # reversing.  One scan, cached on disk, reused by every later goal.
        vocabulary.read()
        shortlist = [name for name in vocabulary.mentioning(reading.words, limit=48) if name not in tried]
        if shortlist:
            hits = vocabulary.sweep(probe_text, probe_expected, names=shortlist)
            for name in hits:
                if name in tried:
                    continue
                tried.add(name)
                found = self._try_tool(
                    name, reading, expected, path, probe_text, vocabulary, source="differential"
                )
                if found is not None:
                    return found

        for doc in vocabulary.ranked(reading.words, limit=max_tools):
            if doc.name in tried:
                continue
            tried.add(doc.name)
            found = self._try_tool(
                doc.name, reading, expected, path, probe_text, vocabulary, source="documentation"
            )
            if found is not None:
                return found

        # A documented mechanism that needs an argument.  The file and the
        # probe are two independent exact specifications, which is exactly the
        # evidence the argument search needs: a bare `nl` leaves blank lines
        # unnumbered, and `nl -b a` is only reachable through the tool's own
        # list of styles.
        probe_path = ".discovery-probe.txt"
        self.computer.write(probe_path, probe_text)
        try:
            found = self._find_documented_mechanism(
                " ".join(reading.words),
                [(path, expected), (probe_path, probe_expected)],
                words=reading.words,
            )
        finally:
            self.computer.path(probe_path).unlink(missing_ok=True)
        if found is not None:
            return {
                "template": found["template"],
                "tool": found["tool"],
                "doc": found["doc"],
                "source": "documentation-options",
                "stages": [found["tool"]],
            }

        # Nothing that mentions the goal, and nothing that matches its words:
        # try every tool on the machine before giving up.
        hits = vocabulary.sweep(probe_text, probe_expected)
        for name in hits:
            if name in tried:
                continue
            tried.add(name)
            found = self._try_tool(
                name, reading, expected, path, probe_text, vocabulary, source="differential"
            )
            if found is not None:
                return found
        return None

    def _try_tool(
        self,
        name: str,
        reading: discovery.Reading,
        expected: str,
        path: str,
        probe_text: str,
        vocabulary: discovery.MachineVocabulary,
        *,
        source: str = "documentation",
    ) -> dict[str, Any] | None:
        """Admit one real tool, or withdraw the admission if it does not hold.

        Admission happens before the run because the whole point of admission
        is that the computer surface only executes what it has accepted.  A
        candidate that fails the exact check is revoked, so a rejected guess
        leaves no authority behind.
        """
        template = f"{name} {{path}}"
        tags = vocabulary.executables()
        located = next((where for tool, where in tags if tool == name), "")
        vocabulary.read([(name, located)])
        doc = vocabulary.doc(name)
        try:
            self.computer.admit(
                name,
                evidence={
                    "summary": doc.summary if doc else "",
                    "usage": doc.usage if doc else "",
                    "reading": reading.describe(),
                    "verified_output_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                },
            )
        except AgentError:
            return None
        verified = self._verified_template(template, path, expected, reading, probe_text)
        self.discovery_log.append(
            {
                "tool": name,
                "reading": reading.key(),
                "source": source,
                "verified": verified,
                "documentation": doc.summary if doc else "",
            }
        )
        if len(self.discovery_log) > 200:
            del self.discovery_log[: len(self.discovery_log) - 200]
        if verified:
            return {
                "template": template,
                "tool": name,
                "doc": doc.summary if doc else "",
                "source": source,
                "stages": [name],
            }
        self.computer.revoke(name)
        return None

    def _admit_discovered_skill(
        self,
        goal: str,
        reading: discovery.Reading,
        found: Mapping[str, Any],
        path: str,
        source: str,
        expected: str,
    ) -> ShellSkill:
        template = str(found["template"])
        skill_id = "D-" + hashlib.sha256(
            json.dumps(
                {"goal": goal, "template": template, "reading": reading.key()}, sort_keys=True
            ).encode()
        ).hexdigest()[:12]
        skill = ShellSkill(
            skill_id=skill_id,
            description=goal,
            template=template,
            slots={"path": path},
            postcondition=r"\S" if expected.strip() else r"\A\s*\Z",
            canary_input={path: source},
            canary_expected=expected,
            keywords=sorted(set(_tokens(goal)) | set(reading.words)),
        )
        if not self._canary_ok(skill):
            raise AgentError("DISCOVERED_SKILL_FAILS_CANARY")
        self.skills[skill_id] = skill
        return skill

    def discover(self, goal: str, path: str, *, max_tools: int = 8) -> dict[str, Any]:
        """Do a goal the fixed vocabulary cannot express, by extending it.

        The steps are not a script over tasks: read the goal into every exact
        reading it admits, look for a mechanism in memory, then in the known
        grammar, then in the machine's own documentation -- and accept only
        what reproduces the reading exactly on the file *and* on a probe.  If
        two readings are both satisfiable the goal is ambiguous and the
        creature says so; if none is, it records an impasse.
        """
        started = time.perf_counter()
        if not self.computer.exists(path):
            raise AgentError("GOAL_INPUT_MISSING:" + path)
        source = self.computer.read(path)
        if not source:
            raise AgentError("GOAL_INPUT_EMPTY:" + path)
        options = discovery.readings(goal, path=path)
        if not options:
            self._record_impasse(goal)
            raise AgentError("GOAL_NOT_VERIFIABLE")
        verified: dict[str, tuple[discovery.Reading, dict[str, Any]]] = {}
        for reading in options:
            expected = reading.expected(source)
            if expected is None:
                continue
            probe_text = self._probe_text(source, reading)
            found = self._find_command(
                reading, source, expected, path, probe_text, max_tools=max_tools
            )
            if found is not None:
                verified.setdefault(found["template"], (reading, found))
        if not verified:
            self._record_impasse(goal)
            raise AgentError("NO_VERIFIED_CAPABILITY")
        if len(verified) > 1:
            self._record_impasse(goal)
            raise AgentError("GOAL_AMBIGUOUS:" + " | ".join(sorted(verified)))
        reading, found = next(iter(verified.values()))
        expected = reading.expected(source) or ""
        skill = self._admit_discovered_skill(goal, reading, found, path, source, expected)
        command = skill.bind({"path": path})
        if found.get("tool"):
            tool = str(found["tool"])
            self._stages[tool] = discovery.tool_stage(
                tool, lambda text, name=tool: self.computer.run(name, stdin=text).stdout
            )
        self.capabilities[reading.key()] = {
            "template": found["template"],
            "tool": found.get("tool"),
            "doc": found.get("doc", ""),
            "stages": list(found.get("stages", ())),
            "reading": reading.describe(),
            "goal": goal,
        }
        self.memory.add(
            "skill",
            " ".join([goal, reading.describe(), *reading.words]),
            {
                "skill_id": skill.skill_id,
                "reading": reading.key(),
                "template": found["template"],
                "tool": found.get("tool"),
                "doc": found.get("doc", ""),
                "source": found["source"],
            },
            confidence=0.9,
            surprise=0.6,
            tags=("capability", "discovered"),
        )
        self.memory.add(
            "episode",
            "extended its own vocabulary: " + goal,
            {"skill_id": skill.skill_id, "outcome": "learned", "tool": found.get("tool")},
            surprise=0.6,
            tags=("learn", "discovered"),
        )
        self._resolve_impasse(goal)
        return {
            "status": "PASS",
            "goal": goal,
            "reading": reading.describe(),
            "command": command,
            "stdout": expected,
            "tool": found.get("tool"),
            "documentation": found.get("doc", ""),
            "source": found["source"],
            "stages": list(found.get("stages", ())),
            "skill_id": skill.skill_id,
            "probe_verified": True,
            "seconds": round(time.perf_counter() - started, 4),
        }

    # -- deciding what to do ----------------------------------------------
    def observe(self, path: str) -> dict[str, str]:
        """Measure a file with generic, checkable features.

        These are observations, not task labels: nothing here mentions sorting,
        counting or totals.  They are the vocabulary in which a controller can
        be learned, and the same measurements are taken at learning time and at
        decision time, so a learned policy sees exactly what the teacher saw.
        """
        if not self.computer.exists(path):
            raise AgentError("OBSERVATION_INPUT_MISSING:" + path)
        text = self.computer.read(path)
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        nonempty = [line for line in lines if line.strip()]
        total = max(1, len(nonempty))
        comma_lines = [line for line in nonempty if "," in line]
        numeric_tails = 0
        for line in comma_lines:
            try:
                float(line.rsplit(",", 1)[-1].strip().strip('"'))
                numeric_tails += 1
            except ValueError:
                pass
        code_markers = ("def ", "import ", "return ", "= ", "(", "{", ";")
        codeish = any(marker in line for line in nonempty for marker in code_markers)
        unique = len({line.strip() for line in nonempty})
        comma_state = "none" if not comma_lines else ("some" if len(comma_lines) * 2 < total else "many")
        if not comma_lines:
            numeric_state = "na"
        else:
            numeric_state = "yes" if numeric_tails * 2 >= len(comma_lines) else "no"
        return {
            "comma": comma_state,
            "numeric_tail": numeric_state,
            "codeish": "yes" if codeish else "no",
            "lines": "tiny" if len(nonempty) < 10 else ("small" if len(nonempty) < 100 else "large"),
            "variety": "low" if unique * 2 < total else "high",
        }

    def learn_policy(
        self,
        name: str,
        traces: Sequence[tuple[Mapping[str, str], str]],
    ) -> dict[str, Any]:
        """Learn *what to do* from observed decisions, not from a written rule.

        Each trace is (state features, the action that was correct there).  The
        same predicate induction that learns data transforms learns a
        first-match decision list over the state features.  There is no oracle
        to probe here, so an under-determined set of traces is reported as
        such instead of being completed by a guess.
        """
        if not traces:
            raise AgentError("TRACES_REQUIRED")
        columns = sorted({key for state, _ in traces for key in state})
        rows = [{column: str(state.get(column, "")) for column in columns} for state, _ in traces]
        labels = [str(action) for _, action in traces]
        policy = induce_decisions(rows, labels, columns)
        if policy is None:
            raise AgentError("POLICY_NOT_INDUCIBLE")
        policy_id = "D-" + hashlib.sha256(
            json.dumps(policy.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:12]
        self.policies[policy_id] = policy
        evidence: dict[str, list[dict[str, str]]] = {}
        for row, label in zip(rows, labels):
            evidence.setdefault(label, []).append(dict(row))
        self.policy_evidence[policy_id] = evidence
        self.memory.add(
            "skill",
            " ".join([name, "decide", *sorted(columns)]),
            {"skill_id": policy_id, "kind": "policy", "name": name},
            confidence=0.7,
            tags=("policy",),
        )
        return {
            "schema": SCHEMA + "_POLICY",
            "policy_id": policy_id,
            "name": name,
            "rules": policy.to_dict()["rules"],
            "traces": len(traces),
            "features": columns,
        }

    def act(self, policy_id: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Decide, then do.  The decision comes from the learned policy."""
        policy = self.policies.get(policy_id)
        if policy is None:
            raise AgentError("POLICY_UNKNOWN:" + policy_id)
        state = self.observe(path)
        rule = policy.firing_rule(state)
        action = rule["action"] if rule is not None else None
        covered = True
        unseen: dict[str, str] = {}
        if action is not None:
            evidence = self.policy_evidence.get(policy_id, {}).get(action, [])
            if evidence:
                for feature, value in state.items():
                    if not any(row.get(feature) == value for row in evidence):
                        covered = False
                        unseen[feature] = value
        if action is None:
            self.memory.add(
                "episode",
                "no decision for " + path,
                {"outcome": "impasse", "goal": path, "resolved": False, "state": state},
                surprise=1.0,
                tags=("impasse", "policy"),
            )
            raise AgentError("POLICY_NO_MATCH")
        if not covered:
            # Acting is allowed, but the creature records that this situation
            # was never demonstrated: the decision is an extrapolation from
            # what it knows, and a teacher can correct it in one word.
            self.memory.add(
                "episode",
                "extrapolated a decision for " + path,
                {
                    "outcome": "impasse",
                    "goal": path,
                    "resolved": False,
                    "state": state,
                    "unseen": dict(unseen),
                    "action": action,
                },
                surprise=1.0,
                tags=("impasse", "policy"),
            )
        goal = action.format(path=path)
        outcome = self.solve(goal, **kwargs)
        outcome.update(
            {
                "policy_id": policy_id,
                "state": state,
                "action": action,
                "covered": covered,
                "unseen": dict(unseen),
            }
        )
        return outcome

    # -- memory -----------------------------------------------------------
    def consolidate(self) -> dict[str, Any]:
        before = self.memory.payload_bytes()
        stats = self.memory.consolidate()
        after = self.memory.payload_bytes()
        return {
            "schema": SCHEMA + "_CONSOLIDATION",
            "before_bytes": before,
            "after_bytes": after,
            "reduction": 1.0 - (after / before) if before else 0.0,
            **stats,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "memory": self.memory.snapshot(),
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "word_bindings": dict(self.word_bindings),
            "practice_log": list(self.practice_log),
            "policies": {k: v.to_dict() for k, v in self.policies.items()},
            "policy_evidence": {
                policy_id: {action: list(rows) for action, rows in by_action.items()}
                for policy_id, by_action in self.policy_evidence.items()
            },
            "open_questions": self.open_questions(),
            "capabilities": {key: dict(value) for key, value in self.capabilities.items()},
            "mechanisms": {key: dict(value) for key, value in self.mechanisms.items()},
            "learned_stages": {key: dict(value) for key, value in self._learned.items()},
            "admissions": {key: dict(value) for key, value in self.computer.admissions.items()},
            "discovered_stages": sorted(self._stages),
            "discovery_log": list(self.discovery_log),
            "model_dependency_count": 0,
            "network_dependency_count": 0,
            "incremental_spend_usd": 0,
        }

    def restore(self, payload: Mapping[str, Any]) -> "LivingAgent":
        """Reload a creature from its own snapshot (skills + learned salience)."""
        if payload.get("schema") != SCHEMA:
            raise AgentError("SNAPSHOT_SCHEMA_MISMATCH")
        memory = payload.get("memory") or {}
        if memory.get("schema") != CORE_SCHEMA + "_MEMORY":
            raise AgentError("SNAPSHOT_MEMORY_SCHEMA_MISMATCH")
        from canonical.runtime.living_core_v1 import MemoryEntry, SalienceModel

        self.memory = Memory()
        self.memory.clock = int(memory.get("clock", 0))
        self.memory.retrieval_log = list(memory.get("retrieval_log", []))
        salience = SalienceModel()
        for key, value in (memory.get("salience") or {}).get("weights", {}).items():
            if key not in salience.weights:
                raise AgentError("SNAPSHOT_SALIENCE_FEATURE_UNKNOWN")
            salience.weights[key] = float(value)
        salience.updates = int((memory.get("salience") or {}).get("updates", 0))
        self.memory.model = salience
        for row in memory.get("entries", []):
            entry = MemoryEntry(
                entry_id=str(row["entry_id"]),
                kind=str(row["kind"]),
                text=str(row["text"]),
                payload=dict(row["payload"]),
                created=int(row["created"]),
                last_used=int(row["last_used"]),
                uses=int(row.get("uses", 0)),
                successes=int(row.get("successes", 0)),
                failures=int(row.get("failures", 0)),
                surprise=float(row.get("surprise", 0.0)),
                cost_saved=float(row.get("cost_saved", 0.0)),
                confidence=float(row.get("confidence", 0.5)),
                retired=bool(row.get("retired", False)),
                tags=tuple(row.get("tags", ())),
            )
            self.memory.entries[entry.entry_id] = entry
            self.memory.order.append(entry.entry_id)
        self.skills = {
            str(key): ShellSkill.from_dict(value)
            for key, value in (payload.get("skills") or {}).items()
        }
        self.word_bindings = {str(k): str(v) for k, v in (payload.get("word_bindings") or {}).items()}
        self.practice_log = list(payload.get("practice_log", []))
        self.policies = {
            str(key): DecisionList.from_dict(value)
            for key, value in (payload.get("policies") or {}).items()
        }
        self.policy_evidence = {
            str(policy_id): {
                str(action): [dict(row) for row in rows]
                for action, rows in by_action.items()
            }
            for policy_id, by_action in (payload.get("policy_evidence") or {}).items()
        }
        self.capabilities = {
            str(key): dict(value) for key, value in (payload.get("capabilities") or {}).items()
        }
        self.mechanisms = {
            str(key): dict(value) for key, value in (payload.get("mechanisms") or {}).items()
        }
        self._learned = {
            str(key): dict(value) for key, value in (payload.get("learned_stages") or {}).items()
        }
        self._learned_cache = {}
        self.discovery_log = [dict(row) for row in (payload.get("discovery_log") or [])]
        self._stages = {}
        for name, record in (payload.get("admissions") or {}).items():
            try:
                # Re-admission is verification: the binary must still be where
                # it was and must still hash the same, or it is not admitted and
                # the capability that depended on it is not trusted.
                admitted = self.computer.admit(str(name), evidence=record.get("evidence"))
            except AgentError:
                continue
            if admitted["sha256"] != record.get("sha256"):
                self.computer.revoke(str(name))
                continue
            if str(name) in set(payload.get("discovered_stages") or ()):
                self._stages[str(name)] = discovery.tool_stage(
                    str(name), lambda text, tool=str(name): self.computer.run(tool, stdin=text).stdout
                )
        self.memory.rebuild_index()
        return self


__all__ = [
    "SCHEMA",
    "AgentError",
    "CommandResult",
    "Computer",
    "ShellSkill",
    "LivingAgent",
]
