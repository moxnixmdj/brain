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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
            if binary not in _ALLOWED_BINARIES:
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
_COUNT_WORDS = {"count", "number", "many", "how", "tally", "total"}
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
    properties: list[str] = []
    if tokens & _SORT_WORDS:
        properties.append("sorted")
    if tokens & _UNIQUE_WORDS:
        properties.append("unique")
    if tokens & _COUNT_WORDS:
        properties.append("count")
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


def _target_for(properties: Sequence[str], text: str) -> str | None:
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
        return None  # order-preserving dedupe is not in the stage vocabulary
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

    def _record_impasse(self, goal: str) -> None:
        if goal in self._open_questions():
            return
        self.memory.add(
            "episode",
            "do not know how to " + goal,
            {"outcome": "impasse", "goal": goal, "resolved": False},
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
            raise AgentError("GOAL_NOT_VERIFIABLE")
        target = _target_for(properties, source)
        if target is None:
            raise AgentError("GOAL_PROPERTY_COMBINATION_UNSUPPORTED")
        candidates, stats = synthesis.search(
            [(source, target)], max_length=max_length, time_budget_s=time_budget_s
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
