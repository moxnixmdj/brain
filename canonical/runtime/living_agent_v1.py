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
        try:
            completed = subprocess.run(
                ["/bin/sh", "-c", command],
                cwd=workdir,
                env=env,
                input=stdin if stdin is not None else "",
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )
            out = completed.stdout
            err = completed.stderr
            truncated = len(out) > _STDOUT_CAP or len(err) > _STDERR_CAP
            return CommandResult(
                completed.returncode,
                out[:_STDOUT_CAP],
                err[:_STDERR_CAP],
                time.perf_counter() - started,
                truncated=truncated,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(124, str(exc.stdout or "")[-20_000:], "TIMEOUT", self.timeout, truncated=True)


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


def _requested_operations(goal: str) -> list[tuple[str, str, str]]:
    """Operations the sentence names: (label, stage spelling, where it belongs).

    "Keep the first two" fixes an operation no matter what the examples show,
    and it fixes *where* it happens: after the transformation.  On two rows,
    "keep the first two, sorted by the third column" is byte-identical to
    "sort those two by the third column" -- and on a third row it is not.
    Only readings the sentence states outright are listed; anything vaguer is
    left to the bytes.
    """
    text = goal.lower()
    requested: list[tuple[str, str, str]] = []
    for match in _SELECTION.finditer(text):
        direction, amount = match.group(1), match.group(2)
        count = int(amount) if amount.isdigit() else _NUMBER_WORDS[amount]
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
    if re.search(r"\b(count|counts|how many|number of)\b", text):
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
            outcome["seconds"] = round(time.perf_counter() - started, 4)
            return outcome

        # 3. synthesize from behaviour
        inputs = [(self.computer.read(path), expected) for path, expected in examples]
        candidates, stats = synthesis.search(
            inputs, max_length=max_length, time_budget_s=time_budget_s
        )
        evaluated = 0
        # A grammar fit is evidence, not proof.  A pipeline can reproduce every
        # example and still ignore what the sentence says about them: on three
        # rows, "reverse the first two" matches a truncated sort by the third
        # column exactly.  Such a fit is kept on the record and the search moves
        # on; only a pipeline that answers both specifications is admitted here.
        contradicted: list[tuple[list[str], list[str]]] = []
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
                    "commands_run": evaluated,
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
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
                    "commands_run": detail["tested"],
                    "seconds": round(time.perf_counter() - started, 4),
                }
            )
            return outcome
        found = self._find_documented_mechanism(goal, examples)
        if found is not None:
            skill = self._admit_documented_skill(goal, found, examples)
            outcome = self.solve(goal, bindings={"path": examples[0][0]})
            outcome.update(
                {
                    "learned": True,
                    "tool": found["tool"],
                    "argv": list(found["argv"]),
                    "source": "documentation-options",
                    "commands_run": found["runs"],
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
    # A *position* in the data is a different kind of argument from an
    # *amount*: a key or a field takes an index the request can name, while a
    # width or a count is only meaningful if the request names the number.
    _POSITION_WORDS = {
        "key", "keys", "field", "fields", "column", "columns", "position",
        "location", "list", "range", "index",
    }
    _AMOUNT_WORDS = {
        "number", "width", "line", "lines", "byte", "bytes", "size", "count",
        "length", "increment", "digit", "digits", "start", "first",
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
                    if positions and words & self._POSITION_WORDS:
                        atoms.append((5, [spelling, str(positions[0])], placeholder))
                    elif quantities and words & (self._POSITION_WORDS | self._AMOUNT_WORDS):
                        atoms.append((4, [spelling, str(quantities[0])], placeholder))
                elif kind == "char":
                    if separators and words & (self._CHAR_WORDS | {"field", "fields"}):
                        atoms.append((4, [spelling, separators[0]], placeholder))
                continue
            if tokens & words:
                atoms.append((1, [spelling], placeholder))
        atoms.sort(key=lambda row: (-row[0], row[1]))
        return atoms

    def _argument_forms(
        self, goal: str, doc: discovery.ToolDoc, sources: Sequence[str]
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
        forms: list[tuple[int, list[str]]] = [(0, [])]
        for score, tokens, _placeholder in atoms:
            forms.append((score, list(tokens)))
        for first in range(len(atoms)):
            for second in range(first + 1, len(atoms)):
                if atoms[first][2] == atoms[second][2]:
                    continue
                if atoms[first][1][0] == atoms[second][1][0]:
                    continue
                forms.append(
                    (atoms[first][0] + atoms[second][0], list(atoms[first][1]) + list(atoms[second][1]))
                )
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
        unique.sort(
            key=lambda row: (
                cls_flags(row[1]),
                -row[0],
                len(" ".join(row[1])),
                row[1],
            )
        )
        strong = [row for row in unique if row[0] >= 2][:8]
        weak = [row for row in unique if row[0] < 2][:2]
        return strong + weak

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

    def _base_grammar(self, inputs: Sequence[tuple[str, str]]) -> tuple[Any, ...]:
        """The grammar whose stages cost nothing to apply.

        Every stage here is pure computation, which is what a *search* needs:
        it applies stages to hundreds of intermediate texts, and an earned
        stage would turn each of those into a process.  Earned stages are
        tried deliberately, in their own loop, where each costs one run.
        """
        return synthesis.instantiate(inputs) + tuple(self._stages.values())

    def _grammar(self, inputs: Sequence[tuple[str, str]]) -> tuple[Any, ...]:
        """The fixed grammar plus everything this creature has earned."""
        base = self._base_grammar(inputs)
        seen = {stage.shell for stage in base}
        return base + tuple(stage for stage in self._learned_stages() if stage.shell not in seen)

    def _candidate_stages(
        self,
        goal: str,
        sources: Sequence[str],
        *,
        limit: int = 64,
    ) -> list[tuple[discovery.ToolDoc, list[str], str, int, int]]:
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
        wanted = set(discovery._words(goal)) | self._structure_words(sources)
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
            if overlap >= 2:
                scored.append((overlap, doc.name, doc))
        scored.sort(key=lambda row: (-row[0], row[1]))
        per_tool: list[list[tuple[discovery.ToolDoc, list[str], str, int, int]]] = []
        for overlap, _name, doc in scored:
            forms = [
                (doc, form, located[doc.name], overlap, strength)
                for strength, form in self._argument_forms(goal, doc, sources)
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
        grammar = self._base_grammar(inputs)
        candidates = self._candidate_stages(goal, sources)
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
            stages = [
                self._stage_for(doc, form, binary, cwd=scratch)
                for doc, form, binary, _overlap, _strength in candidates
            ]

            def fingerprint(stage: Any) -> str | None:
                try:
                    return stage.apply(sources[0])
                except ValueError:
                    return None

            with ThreadPoolExecutor(max_workers=workers) as pool:
                firsts = list(pool.map(fingerprint, stages))
            survivors = [
                (candidate, stage, first)
                for candidate, stage, first in zip(candidates, stages, firsts)
                if first is not None and first != sources[0]
            ]
            # Cheapest explanation first: a single documented argument is tried
            # before any pair, even when the pair carries more keyword weight.
            # Evidence first, then parsimony: a bundle whose arguments are both
            # grounded by the request or the data is more promising than a
            # one-argument bundle from a tool that merely shares a word, and
            # among equals the shorter bundle wins.
            survivors.sort(
                key=lambda row: (
                    -row[0][4],
                    sum(1 for part in row[0][1] if part.startswith("-")),
                )
            )
            tested = len(candidates)
            # Stages the sentence puts before the mechanism: "take the first
            # four rows, then sort them" is a different function from "sort
            # everything and keep four", because the selection happens first.
            prefixes = self._named_prefixes(goal, sources, grammar)

            def verified(pipeline: Sequence[str]) -> bool:
                return self._confirm(goal, pipeline, examples)

            for (doc, form, _binary, _overlap, _strength), stage, _first in survivors[:16]:
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
                    self._settle_admissions(before, winner=doc.name)
                    self._log_composition(candidates, survivors, doc, form, tested)
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
        return self._depends_only_on_named_column(goal, pipeline, examples) is not False

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
            if label.startswith("first "):
                stages.append("head -n " + label.split()[1])
            elif label.startswith("last "):
                stages.append("tail -n " + label.split()[1])
        if any(label == "a count" for label, _p, _r in operations):
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
        if "a count" not in [label for label, _p, _r in _requested_operations(goal)]:
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

    def _find_documented_mechanism(
        self,
        goal: str,
        examples: Sequence[tuple[str, str]],
        *,
        words: Sequence[str] | None = None,
        max_tools: int = 6,
        max_runs: int = 60,
    ) -> dict[str, Any] | None:
        """Search the machine's documented surface for a command that fits.

        The examples are the specification: a candidate is admitted only if the
        real shell reproduces every example byte for byte.  Candidates are the
        tools whose own documentation mentions the goal -- each one bare first,
        because the simplest mechanism is usually the right one, and then with
        the option bundles its help text documents, bound only to values the
        request or the data supply.
        """
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
            template = " ".join([doc.name, *(_shell_spelling(part) for part in form), "{path}"])
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
            for path, expected in examples:
                if runs >= max_runs:
                    break
                result = self.computer.run(template.replace("{path}", shlex.quote(path)))
                runs += 1
                if not result.ok or result.stdout != expected:
                    self.computer.revoke(doc.name)
                    attempts.append({"tool": doc.name, "argv": list(form), "verified": False})
                    return None
            attempts.append({"tool": doc.name, "argv": list(form), "verified": True})
            return {
                "template": template,
                "tool": doc.name,
                "argv": list(form),
                "doc": doc.summary,
                "runs": runs,
            }

        shortlist = [
            doc
            for doc in vocabulary.ranked(
                words if words is not None else discovery._words(goal), limit=max_tools
            )
            if doc.name not in discovery.DENY
            and any(name == doc.name for name, _ in vocabulary.executables())
        ]
        found: dict[str, Any] | None = None
        # Phase 1: the tools themselves, with no arguments at all.
        for doc in shortlist:
            if stopped:
                break
            found = attempt(doc, [])
            if found is not None:
                break
        # Phase 2: documented arguments, tool by tool, simplest bundle first.
        while found is None and not stopped:
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
        stages = self._grammar([(source, target)])
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
        """Exact bytes on the real file, twice, and on an adversarial probe."""
        command = template.replace("{path}", shlex.quote(path))
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
        stages = self._grammar(examples)
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
