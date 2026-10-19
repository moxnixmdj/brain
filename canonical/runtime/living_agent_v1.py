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
import tempfile
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
        digest = hashlib.sha256(located.read_bytes()).hexdigest()
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
        if not candidates:
            raise AgentError("NO_PIPELINE_WITHIN_BUDGET")

        evaluated = 0
        for stages in candidates:
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
        raise AgentError("NO_VERIFIED_PIPELINE")

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
        stages = synthesis.instantiate([(source, target)]) + tuple(self._stages.values())
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
        stages = synthesis.instantiate(examples) + tuple(self._stages.values())
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
        shortlist = [name for name in vocabulary.mentioning(reading.words, limit=48) if name not in tried]
        for names in (shortlist,):
            hits = vocabulary.sweep(probe_text, probe_expected, names=names)
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
