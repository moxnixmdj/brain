"""Wave 40 — `FRONTIER_BENCH_V1`: a held-out, oracle-judged capability benchmark.

Why this exists
---------------
Waves 37–39 made a great deal of capability *reachable* through `UnifiedModel`,
`Creature`, and `UnifiedFivePillarKernel`. None of it was **measured against a
held-out frontier**. Every wave reported its own tests passing, and its own
tests use its own fixtures. That is a closed loop: the thing being judged and
the thing judging are the same code path, and the instances are the ones the
author had in view while writing the engine.

This module opens the loop. For every one of the six capability classes the
creature claims, it:

1. **Generates fresh instances from a seed**, at run time, in the bench. Nothing
   is read from a stored answer key and nothing is copied from the unit-test
   fixtures, so editing a data file cannot raise a score.
2. **Judges each instance with an independent oracle** — a second
   implementation of the *task semantics* (brute-force search, explicit
   enumeration, a hand-written evaluator of the synthesised program's language,
   a subprocess that actually runs the repaired repository's tests, and direct
   reads of the files the engine claims to have written).
3. **Never uses the engine's own `pass` flag to score anything.** That flag is
   recorded separately as `sut_claimed`, so the report can state how often the
   engine's self-assessment agrees with the oracle.
4. **Fails closed.** An exception inside the system under test is `ERROR`
   (counted as a failure, with the exception text). An exception inside the
   oracle is `ERROR` too — a broken judge never silently passes a candidate. A
   category with no instances is `NO_INSTANCES` and the CLI exits non-zero: an
   empty benchmark is not a perfect score.

What it is not
--------------
This is **not** an external benchmark (SWE-bench, Terminal-Bench, …) and its
numbers are **not comparable** to any published number. It is an internal
instrument: it says whether the creature can still do, on instances it has
never seen, the six things it says it can do — and it flags the cases where it
says it did something it did not.

The `--self-check` mode calibrates the instrument itself: an honest kernel must
score 1.0, a liar that always reports success must score 0.0, and a stub that
always refuses must score strictly below the honest kernel. A bench that cannot
separate those three is measuring nothing.

Usage
-----
    python3 canonical/evaluation/frontier_bench_v1.py
    python3 canonical/evaluation/frontier_bench_v1.py --seed 7 --per-category 5 --json out.json
    python3 canonical/evaluation/frontier_bench_v1.py --self-check

Exit codes: `0` all instances pass and no errors; `1` any failure or error;
`2` no instances (empty or filtered to nothing).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]

BENCH_SCHEMA = "BRAIN_FRONTIER_BENCH_V1"
SCORECARD_SCHEMA = "BRAIN_FRONTIER_BENCH_SCORECARD_V1"
DEFAULT_SEED = 20261126

CATEGORIES: tuple[str, ...] = (
    "TRANSFER_UNDER_ISOMORPHISM",
    "WITNESS_INVERSION_GENERALIZATION",
    "COMPUTER_USE_GROUNDING",
    "MULTIFILE_REPAIR",
    "BELIEF_REVISION_ENTRENCHMENT",
    "CROSS_LANGUAGE_RULE_TRANSFER",
)

#: Categories whose instances are cheap and safe to run in a unit test.
FAST_CATEGORIES: tuple[str, ...] = tuple(c for c in CATEGORIES if c != "MULTIFILE_REPAIR")


# --------------------------------------------------------------------------- result types
@dataclass
class Judgement:
    """The oracle's verdict on one execution. `ok` is the only thing scored."""

    ok: bool
    reason: str
    expected: Any = None
    observed: Any = None
    sut_claimed: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "reason": str(self.reason),
            "expected": self.expected,
            "observed": self.observed,
            "sut_claimed": self.sut_claimed,
        }


@dataclass
class BenchInstance:
    """One held-out task: how to run it, and an independent oracle for judging it."""

    instance_id: str
    category: str
    run: Callable[[], Mapping[str, Any]]
    judge: Callable[[Mapping[str, Any]], Judgement]
    cleanup: Callable[[], None] | None = None
    notes: str = ""


@dataclass
class Sut:
    """The system under test, injected so a test can substitute a mutant.

    `kernel` must return a *fresh* object per call: belief state, caches and
    prospectively indexed cues are per-instance, exactly as a new process would
    have them.
    """

    kernel: Callable[[], Any]
    synth: Callable[..., Any] | None = None

    @classmethod
    def default(cls) -> "Sut":
        def _kernel() -> Any:
            from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import (
                UnifiedFivePillarKernel,
            )

            return UnifiedFivePillarKernel()

        def _synth(examples: Sequence[tuple[Any, Any]], *, held_out: Sequence[tuple[Any, Any]] = ()) -> Any:
            from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import (
                synthesize_by_witness_inversion,
            )

            return synthesize_by_witness_inversion(examples, held_out=held_out)

        return cls(kernel=_kernel, synth=_synth)


# --------------------------------------------------------------------------- finite machines
class FiniteMachine:
    """A tiny explicit machine, used for the transfer category.

    Two instances of this class built from the same spec are independent: the
    oracle always simulates on a *fresh* one, so an engine that mutates the
    environment it was handed cannot move the truth.
    """

    def __init__(self, modulus: int, step: int, jump: int, inc_name: str, jump_name: str) -> None:
        self.modulus = int(modulus)
        self.step = int(step)
        self.jump = int(jump)
        self.inc_name = str(inc_name)
        self.jump_name = str(jump_name)
        self.val = 0

    # -- environment protocol the engine drives ---------------------------------
    def reset(self) -> None:
        self.val = 0

    def state(self) -> int:
        return self.val

    def act(self, action: str) -> None:
        if action == self.inc_name:
            self.val = (self.val + self.step) % self.modulus
        elif action == self.jump_name:
            self.val = (self.val + self.jump) % self.modulus

    # -- oracle-side simulation (no engine code involved) ------------------------
    def simulate(self, plan: Iterable[str]) -> int:
        val = 0
        for action in plan:
            if action == self.inc_name:
                val = (val + self.step) % self.modulus
            elif action == self.jump_name:
                val = (val + self.jump) % self.modulus
            else:
                raise KeyError(f"plan names an action the machine does not have: {action!r}")
        return val

    def reachable(self) -> set[int]:
        seen = {0}
        frontier = [0]
        while frontier:
            cur = frontier.pop()
            for name in (self.inc_name, self.jump_name):
                nxt = (cur + (self.step if name == self.inc_name else self.jump)) % self.modulus
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        return seen

    def shortest_plan(self, goal: int, max_len: int = 12) -> list[str] | None:
        """Breadth-first: the shortest action sequence reaching `goal`, or `None`."""
        if goal % self.modulus == 0:
            return []
        seen = {0: []}
        frontier = [0]
        for _ in range(max_len):
            nxt_frontier: list[int] = []
            for cur in frontier:
                for name in (self.inc_name, self.jump_name):
                    nxt = (cur + (self.step if name == self.inc_name else self.jump)) % self.modulus
                    if nxt not in seen:
                        seen[nxt] = seen[cur] + [name]
                        if nxt == goal % self.modulus:
                            return seen[nxt]
                        nxt_frontier.append(nxt)
            frontier = nxt_frontier
        return None


def _fresh(spec: Mapping[str, Any]) -> FiniteMachine:
    """A machine built from a spec. Two calls with one spec are *different objects, same machine*.

    Note what is deliberately absent: a way to rebuild the machine with its two action names
    exchanged. That would not change how the machine is *presented*, it would change what the
    actions *do* — and a bench that quietly hands the engine a different machine from the one
    the oracle scores is measuring the bench's own arithmetic. Ordering is varied only through
    the `target_actions` list, which is presentation.
    """
    return FiniteMachine(int(spec["modulus"]), int(spec["step"]), int(spec["jump"]),
                         str(spec["inc_name"]), str(spec["jump_name"]))


# --------------------------------------------------------------------------- program evaluator
_PROG_AFFINE = re.compile(r"^affine\((-?\d+)\*x \+ (-?\d+)\)$")
_PROG_AFFINE_FLOAT = re.compile(r"^affine_float\((-?\d+(?:\.\d+)?)\*x \+ (-?\d+(?:\.\d+)?)\)$")
_PROG_SHIFT = re.compile(r"^shift\(x \+ (-?\d+)\)$")
_PROG_SCALE = re.compile(r"^scale\((-?\d+)\*x\)$")
_PROG_MOD = re.compile(r"^mod\(x % (-?\d+)\)$")
_PROG_ACRONYM = re.compile(r"^acronym_upper\((.+)\)$")
_PROG_EXTRACT = re.compile(r"^extract_between\(('.*?'|'.*'), ('.*?'|'.*')\)$")

_UNDEFINED = object()


def eval_program(program: str, x: Any) -> Any:
    """Evaluate a synthesised program string with the *bench's own* semantics.

    This is a second, independent implementation of the small language the
    synthesiser is allowed to emit. It shares no code with
    `synthesize_by_witness_inversion`; it only shares the *notation*. Unknown
    programs raise `ValueError` and the caller records that as a failure — a
    program the bench cannot interpret is not evidence of anything.

    Returns `_UNDEFINED` when the program's semantics are undefined on this
    input (e.g. a delimiter that is not present).
    """
    text = str(program).strip()
    if (m := _PROG_AFFINE.match(text)) is not None:
        a, b = int(m.group(1)), int(m.group(2))
        return a * x + b
    if (m := _PROG_AFFINE_FLOAT.match(text)) is not None:
        a, b = float(m.group(1)), float(m.group(2))
        return a * x + b
    if (m := _PROG_SHIFT.match(text)) is not None:
        return x + int(m.group(1))
    if (m := _PROG_SCALE.match(text)) is not None:
        return int(m.group(1)) * x
    if (m := _PROG_MOD.match(text)) is not None:
        return x % int(m.group(1))
    if (m := _PROG_ACRONYM.match(text)) is not None:
        sep = ast.literal_eval(m.group(1))
        parts = str(x).split(sep)
        return "".join(p[0] for p in parts if p).upper()
    if (m := _PROG_EXTRACT.match(text)) is not None:
        left = ast.literal_eval(m.group(1))
        right = ast.literal_eval(m.group(2))
        text_x = str(x)
        if left not in text_x or right not in text_x:
            return _UNDEFINED
        tail = text_x.split(left, 1)[1]
        if right not in tail:
            return _UNDEFINED
        return tail.split(right, 1)[0]
    raise ValueError(f"uninterpretable program: {program!r}")


# --------------------------------------------------------------------------- category 1: transfer
_WORD_POOL = (
    "advance", "retreat", "pulse", "drift", "sweep", "tilt", "orbit", "cascade",
    "nudge", "halt", "flip", "leap", "coil", "stride", "glide", "bounce",
)


def _build_transfer(rng: random.Random, index: int) -> BenchInstance:
    """Isomorphic plan transfer, plus unreachable-goal instances that must be refused."""
    kind = "ISO" if index % 3 != 2 else "UNREACHABLE"
    modulus = rng.choice((4, 5, 6, 7))
    step = 1
    jump = rng.choice((2, 3))
    if kind == "UNREACHABLE":
        # Same modulus, different generator: goal 3 is out of the reachable orbit.
        modulus = 6
        step, jump = 2, 4
    names = rng.sample(_WORD_POOL, 4)
    source_spec = {"modulus": modulus, "step": step, "jump": jump,
                   "inc_name": names[0], "jump_name": names[1]}
    target_spec = {"modulus": modulus, "step": step, "jump": jump,
                   "inc_name": names[2], "jump_name": names[3]} if kind == "ISO" else {
        "modulus": 6, "step": 2, "jump": 4, "inc_name": names[2], "jump_name": names[3]}
    goal = rng.choice((1, 2, 3)) if kind == "ISO" else 3

    reference = _fresh(target_spec)
    oracle_plan = reference.shortest_plan(goal)
    swap = bool(rng.getrandbits(1))  # target action order is not positional information
    source_plan = _fresh(source_spec).shortest_plan(goal) or []

    def run() -> Mapping[str, Any]:
        kernel = _CURRENT_SUT.kernel()
        return kernel.instant_learner.learn_and_transfer(
            source_env=_fresh(source_spec),
            source_actions=[source_spec["inc_name"], source_spec["jump_name"]],
            source_is_goal=lambda s, g=goal: s == g,
            source_plan=source_plan,
            target_env=_fresh(target_spec),
            target_actions=([target_spec["jump_name"], target_spec["inc_name"]] if swap
                            else [target_spec["inc_name"], target_spec["jump_name"]]),
            target_is_goal=lambda s, g=goal: s == g,
        )

    def judge(result: Mapping[str, Any]) -> Judgement:
        raw = (result.get("moore_isomorphism_transfer") or {})
        claimed = bool(raw.get("target_goal_verified_by_execution"))
        plan = raw.get("mapped_plan")
        status = str(raw.get("isomorphism_status") or "")
        if plan is None:
            # Declining is truthful exactly when no plan exists.
            ok = oracle_plan is None
            return Judgement(
                ok=ok,
                reason="REFUSED_AND_NO_PLAN_EXISTS" if ok else "REFUSED_A_SOLVABLE_INSTANCE",
                expected={"reachable_plan": oracle_plan, "refusal_required": oracle_plan is None},
                observed={"claimed": claimed, "status": status},
                sut_claimed=claimed,
            )
        try:
            end_state = _fresh(target_spec).simulate([str(a) for a in plan])
        except KeyError as exc:
            return Judgement(False, "PLAN_NAMES_ABSENT_ACTION", expected=oracle_plan,
                             observed=str(exc), sut_claimed=claimed)
        ok = end_state == goal % modulus
        return Judgement(
            ok=ok,
            reason="PLAN_REACHES_GOAL" if ok else "PLAN_MISSES_GOAL",
            expected={"goal": goal % modulus, "oracle_plan": oracle_plan},
            observed={"end_state": end_state, "plan": list(plan), "claimed_verified": claimed},
            sut_claimed=claimed,
        )

    return BenchInstance(
        instance_id=f"TRANSFER_UNDER_ISOMORPHISM#{index:02d}_{kind}",
        category="TRANSFER_UNDER_ISOMORPHISM",
        run=run,
        judge=judge,
        notes=f"modulus={modulus} step={step} jump={jump} goal={goal} goal_reachable={oracle_plan is not None}",
    )


# --------------------------------------------------------------------------- category 2: synthesis
_DELIM_PAIRS = (("<", ">"), ("[", "]"), ("{", "}"), ("(", ")"))
_NAMES = (
    "Ada Lovelace", "Alan Turing", "Grace Hopper", "Barbara Liskov", "Edsger Dijkstra",
    "Katherine Johnson", "Donald Knuth", "Frances Allen", "Ken Thompson", "Radia Perlman",
)


def _build_synthesis(rng: random.Random, index: int) -> BenchInstance:
    """Program synthesis judged by *held-out probes the engine never sees*."""
    family = ("AFFINE", "EXTRACT_BETWEEN", "ACRONYM")[index % 3]
    if family == "AFFINE":
        a = rng.choice((2, 3, 4, 5))
        b = rng.choice((-4, -3, -2, -1, 0, 1, 2, 3, 4, 5))
        truth: Callable[[Any], Any] = lambda x, a=a, b=b: a * x + b
        xs = [0, 1, 2, 3, 4, 5, 6, 7]
        rng.shuffle(xs)
        examples = [(x, truth(x)) for x in xs[:2]]
        held_out = [(xs[2], truth(xs[2]))]
        probes = [(x, truth(x)) for x in xs[3:7]]
        notes = f"family=AFFINE a={a} b={b}"
    elif family == "EXTRACT_BETWEEN":
        left, right = rng.choice(_DELIM_PAIRS)
        payloads = rng.sample(("alpha", "beta_x", "gamma42", "delta", "omega_7", "sigma"), 6)
        truth = lambda s, l=left, r=right: s.split(l, 1)[1].split(r, 1)[0]
        render = lambda p: f"hdr{p[0]}{left}{p}{right}tail{p[::-1]}"
        probe_payloads = ["zeta9", "kappa", "theta_1", "lambda_2"]
        examples = [(render(payloads[0]), payloads[0]), (render(payloads[1]), payloads[1])]
        held_out = [(render(payloads[2]), payloads[2])]
        probes = [(render(p), p) for p in probe_payloads]
        notes = f"family=EXTRACT_BETWEEN left={left!r} right={right!r}"
    else:
        sep = rng.choice((" ", "_", "."))
        picked = rng.sample(_NAMES, 6)
        truth = lambda s, sep=sep: "".join(p[0] for p in s.split(sep) if p).upper()
        render = lambda s: s.replace(" ", sep)
        examples = [(render(picked[0]), truth(render(picked[0]))), (render(picked[1]), truth(render(picked[1])))]
        held_out = [(render(picked[2]), truth(render(picked[2])))]
        probes = [(render(p), truth(render(p))) for p in picked[3:]]
        notes = f"family=ACRONYM sep={sep!r}"

    def run() -> Mapping[str, Any]:
        synth = _CURRENT_SUT.synth
        if synth is None:  # pragma: no cover - Sut.default always supplies one
            raise RuntimeError("SUT provides no synthesiser")
        return synth(examples, held_out=held_out)

    def judge(result: Mapping[str, Any]) -> Judgement:
        program = result.get("best_program")
        claimed = bool(result.get("pass"))
        if not program:
            return Judgement(False, "NO_PROGRAM_PRODUCED", expected=probes, observed=result.get("status"),
                             sut_claimed=claimed)
        mismatches: list[dict[str, Any]] = []
        for x, want in probes:
            try:
                got = eval_program(str(program), x)
            except ValueError as exc:
                return Judgement(False, "UNINTERPRETABLE_PROGRAM", expected="bench-language program",
                                 observed=f"{program!r}: {exc}", sut_claimed=claimed)
            except TypeError:
                # A program of the right notation applied to the wrong kind of value is a wrong
                # answer, not a broken judge: `affine(0*x + 0)` on a string is simply not the rule.
                mismatches.append({"input": x, "want": want, "got": "TYPE_ERROR"})
                continue
            if got is _UNDEFINED or got != want:
                mismatches.append({"input": x, "want": want, "got": None if got is _UNDEFINED else got})
        ok = not mismatches
        return Judgement(
            ok=ok,
            reason="GENERALISED_TO_HELD_OUT_PROBES" if ok else "FAILED_HELD_OUT_PROBES",
            expected={"probes": probes},
            observed={"program": program, "mismatches": mismatches},
            sut_claimed=claimed,
        )

    return BenchInstance(
        instance_id=f"WITNESS_INVERSION_GENERALIZATION#{index:02d}_{family}",
        category="WITNESS_INVERSION_GENERALIZATION",
        run=run,
        judge=judge,
        notes=notes,
    )


# --------------------------------------------------------------------------- category 3: computer use
_SENDERS = ("Zora", "Marcus", "Ines", "Tobias", "Yuki", "Priya", "Osman", "Lena")
_FILES = ("notes_a.txt", "notes_b.txt", "ledger.txt")


def _build_computer_use(rng: random.Random, index: int) -> BenchInstance:
    """Grounding judged by the *bytes on disk* and the resolved control index."""
    senders = rng.sample(_SENDERS, 3)
    target_sender = senders[rng.randrange(len(senders))]
    control = rng.choice(("star", "trash"))
    planned_index_base = rng.choice((5, 25, 105))  # never 0: 0 is the inbox root
    live_shift = rng.choice((7, 13, 29))
    use_ooxml = index % 3 == 0
    use_json = index % 3 == 1
    refusal_case = index % 3 == 2

    def _row(start: int, sender: str) -> list[dict[str, Any]]:
        return [
            {"index": start, "parent": 0, "tag": "div", "classes": "email-row", "text": ""},
            {"index": start + 1, "parent": start, "tag": "span", "classes": "sender", "text": sender},
            {"index": start + 2, "parent": start, "tag": "button", "classes": "star", "text": "", "can_click": True},
            {"index": start + 3, "parent": start, "tag": "button", "classes": "trash", "text": "", "can_click": True},
        ]

    planned = {"elements": [{"index": 0, "parent": -1, "tag": "div", "classes": "inbox", "text": ""}]}
    live = {"elements": [{"index": 0, "parent": -1, "tag": "div", "classes": "inbox", "text": ""}]}
    expected_control_index = None
    for pos, sender in enumerate(senders):
        planned["elements"].extend(_row(planned_index_base + 10 * (pos + 1), sender))
        live_rows = _row(live_shift + 10 * (pos + 1), sender)
        live["elements"].extend(live_rows)
        if sender == target_sender:
            expected_control_index = live_rows[0]["index"] + (2 if control == "star" else 3)

    established_a = f"established-{rng.randrange(10, 99)}"
    clobber = f"clobber-{rng.randrange(100, 999)}"
    established_b = f"established-b-{rng.randrange(10, 99)}"
    file_a, file_b = _FILES[0], _FILES[1]
    batch_steps = [
        {"writes": {file_a: established_a}, "establish_facts": [file_a]},
        {"writes": {file_a: clobber, file_b: established_b},
         "touches": [file_a, file_b], "establish_facts": [file_b]},
    ]
    expected_files = {file_a: established_a, file_b: established_b}

    docx_text_before = f"Draft {rng.randrange(10, 99)}"
    docx_text_after = f"Approved Final {rng.randrange(100, 999)}"
    json_updates = {"theme": rng.choice(("solarized", "nord", "dracula")), "revision": rng.randrange(1, 9)}

    state: dict[str, Any] = {}

    def run() -> Mapping[str, Any]:
        from canonical.runtime.ooxml_package_transaction import XmlSetText

        tmp = Path(tempfile.mkdtemp(prefix="frontier_bench_cu_"))
        state["dir"] = tmp
        docx_path = tmp / "report.docx"
        with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "[Content_Types].xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
            )
            zf.writestr(
                "word/document.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body><w:p><w:t>{docx_text_before}</w:t></w:p></w:body></w:document>",
            )
        json_path = tmp / "settings.json"
        json_path.write_text(json.dumps({"theme": "default", "revision": 0}), encoding="utf-8")

        kwargs: dict[str, Any] = {
            "instruction": f"Click {control} on the row for {target_sender} and log the batch",
            "workspace_dir": tmp,
            "observation": planned,
            "live_observation_before_dispatch": live,
            "record_identifier": target_sender,
            "control_word": control,
        }
        if refusal_case:
            # A text field holds edited-but-uncommitted content: claiming DONE is a lie.
            kwargs.pop("live_observation_before_dispatch")
            kwargs.pop("record_identifier")
            kwargs.pop("control_word")
            # The instruction must name the committing action: the ending the page implies is read
            # from the instruction, so a refusal instance that asks for a click is not a refusal.
            kwargs["instruction"] = f"Enter the {target_sender} title in the input field"
            kwargs["observation"] = {
                "elements": [
                    {"index": 0, "tag": "input", "text": "", "value": "edited", "can_type": True},
                    {"index": 1, "tag": "button", "text": "Save", "classes": "save", "can_click": True},
                ]
            }
            kwargs["attempt_done"] = True
            return _CURRENT_SUT.kernel().computer_use.execute_workflow(**kwargs)

        if use_ooxml:
            kwargs["ooxml_transaction"] = {
                "input_path": str(docx_path),
                "output_path": str(docx_path),
                "operations": [XmlSetText(member="word/document.xml", path=(0, 0, 0), text=docx_text_after)],
            }
        if use_json:
            kwargs["json_lens_patch"] = {"path": str(json_path), "updates": json_updates}
        kwargs["batch_steps"] = batch_steps
        return _CURRENT_SUT.kernel().computer_use.execute_workflow(**kwargs)

    def judge(result: Mapping[str, Any]) -> Judgement:
        claimed = bool(result.get("pass"))
        tmp = state.get("dir")
        if refusal_case:
            done_allowed = bool((result.get("done_gate") or {}).get("done_allowed"))
            ok = (not claimed) and (not done_allowed)
            return Judgement(
                ok=ok,
                reason="REFUSED_FALSE_DONE" if ok else "ACCEPTED_UNCOMMITTED_WORK_AS_DONE",
                expected={"must_claim_success": False, "done_allowed": False},
                observed={"claimed": claimed, "done_allowed": done_allowed},
                sut_claimed=claimed,
            )
        if tmp is None:
            return Judgement(False, "NO_WORKSPACE", sut_claimed=claimed)
        problems: list[str] = []
        for name, want in expected_files.items():
            path = Path(tmp) / name
            got = path.read_text(encoding="utf-8") if path.exists() else None
            if got != want:
                problems.append(f"{name}: want {want!r} got {got!r}")
        if use_ooxml:
            docx = Path(tmp) / "report.docx"
            try:
                with zipfile.ZipFile(docx) as zf:
                    member = zf.read("word/document.xml").decode("utf-8")
            except (OSError, KeyError, zipfile.BadZipFile) as exc:
                problems.append(f"docx unreadable: {exc}")
                member = ""
            if docx_text_after not in member:
                problems.append("docx text not replaced with the requested value")
        if use_json:
            try:
                current = json.loads((Path(tmp) / "settings.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                problems.append(f"json unreadable: {exc}")
                current = {}
            for key, want in json_updates.items():
                if current.get(key) != want:
                    problems.append(f"json {key}: want {want!r} got {current.get(key)!r}")
        frame_index = (result.get("relational_frame") or {}).get("index")
        if frame_index != expected_control_index:
            problems.append(f"control index: want {expected_control_index} got {frame_index}")
        ok = not problems
        return Judgement(
            ok=ok,
            reason="GROUNDED_ON_DISK_AND_INDEX" if ok else "GROUNDING_MISMATCH",
            expected={"files": expected_files, "control_index": expected_control_index},
            observed={"problems": problems},
            sut_claimed=claimed,
        )

    def cleanup() -> None:
        tmp = state.get("dir")
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)

    return BenchInstance(
        instance_id=f"COMPUTER_USE_GROUNDING#{index:02d}_{'REFUSAL' if refusal_case else 'GROUND'}",
        category="COMPUTER_USE_GROUNDING",
        run=run,
        judge=judge,
        cleanup=cleanup,
        notes=f"sender={target_sender} control={control} ooxml={use_ooxml} json={use_json}",
    )


# --------------------------------------------------------------------------- category 4: SWE repair
def _run_repo_tests(repo: Path, timeout: float = 60.0) -> dict[str, Any]:
    """Run the repository's own tests in a fresh interpreter — the real oracle."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    match = re.search(r"Ran (\d+) tests?", proc.stderr)
    return {
        "returncode": int(proc.returncode),
        "ran": int(match.group(1)) if match else 0,
        "tail": (proc.stderr or "")[-600:],
    }


def _write_repair_repo(root: Path, *, vacuous: bool, rng: random.Random) -> dict[str, Any]:
    module_a = rng.choice(("pricing", "ledger", "fees"))
    module_b = rng.choice(("invoice", "receipt", "statement"))
    func_a = rng.choice(("with_tax", "apply_fee", "net_total"))
    func_b = rng.choice(("gross", "gross_total", "charged"))
    rate_a = rng.choice((0.1, 0.2, 0.25))
    rate_b = rng.choice((0.3, 0.5, 0.4))
    base_a, base_b = 50.0, 80.0
    buggy = "net - net * rate"
    fixed = "net + net * rate"
    (root / f"{module_a}.py").write_text(
        f"def {func_a}(net, rate):\n    return {buggy}\n", encoding="utf-8"
    )
    (root / f"{module_b}.py").write_text(
        f"def {func_b}(net, rate):\n    return {buggy}\n", encoding="utf-8"
    )
    if vacuous:
        expect_a, expect_b = base_a - base_a * rate_a, base_b - base_b * rate_b
    else:
        expect_a, expect_b = base_a + base_a * rate_a, base_b + base_b * rate_b
    (root / f"test_{module_b}.py").write_text(
        textwrap.dedent(
            f"""
            import unittest
            from {module_a} import {func_a}
            from {module_b} import {func_b}


            class Spec(unittest.TestCase):
                def test_a(self):
                    self.assertAlmostEqual({func_a}({base_a}, {rate_a}), {expect_a})

                def test_b(self):
                    self.assertAlmostEqual({func_b}({base_b}, {rate_b}), {expect_b})
            """
        ),
        encoding="utf-8",
    )
    return {
        "files": (f"{module_a}.py", f"{module_b}.py"),
        "expect": (expect_a, expect_b),
        "fixed": fixed,
        "buggy": buggy,
    }


def _build_multifile_repair(rng: random.Random, index: int) -> BenchInstance:
    """Multi-file repair judged by running the repaired repo's tests in a subprocess."""
    vacuous = index % 2 == 1
    state: dict[str, Any] = {}

    def run() -> Mapping[str, Any]:
        tmp = Path(tempfile.mkdtemp(prefix="frontier_bench_swe_"))
        state["dir"] = tmp
        state["spec"] = _write_repair_repo(tmp, vacuous=vacuous, rng=rng)
        return _CURRENT_SUT.kernel().swe_kernel.repair_repository(tmp, apply_winning_patch=True)

    def judge(result: Mapping[str, Any]) -> Judgement:
        claimed = bool(result.get("pass"))
        tmp = state.get("dir")
        spec = state.get("spec") or {}
        if tmp is None or not spec:
            return Judgement(False, "NO_WORKSPACE", sut_claimed=claimed)
        tests = _run_repo_tests(Path(tmp))
        sources = {name: (Path(tmp) / name).read_text(encoding="utf-8") for name in spec["files"]}
        problems: list[str] = []
        if vacuous:
            # The oracle cannot fail on the buggy tree: the only truthful answer is refusal.
            if claimed:
                problems.append("claimed a repair the oracle cannot justify")
            for name, text in sources.items():
                if spec["buggy"] not in text:
                    problems.append(f"{name} was edited on a vacuous tree")
            if tests["returncode"] != 0:
                problems.append(f"left the repository broken (rc={tests['returncode']})")
            ok = not problems
            return Judgement(
                ok=ok,
                reason="REFUSED_VACUOUS_ORACLE" if ok else "REPAIRED_WITHOUT_AN_ORACLE",
                expected={"refusal_required": True, "tests_green": True},
                observed={"claimed": claimed, "problems": problems, "tests": tests["returncode"]},
                sut_claimed=claimed,
            )
        if tests["returncode"] != 0:
            problems.append(f"tests fail after repair (rc={tests['returncode']})")
        if tests["ran"] < 2:
            problems.append(f"only {tests['ran']} test(s) ran")
        touched = [name for name, text in sources.items() if spec["fixed"] in text]
        if len(touched) != len(spec["files"]):
            problems.append(f"only {touched} were closed; a sibling site was left behind")
        ok = not problems
        return Judgement(
            ok=ok,
            reason="REPO_TESTS_GREEN_AFTER_REPAIR" if ok else "REPO_TESTS_OR_SIBLINGS_NOT_CLOSED",
            expected={"files": list(spec["files"]), "tests_ran": 2},
            observed={"tests": tests, "touched": touched, "problems": problems},
            sut_claimed=claimed,
        )

    def cleanup() -> None:
        tmp = state.get("dir")
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)

    return BenchInstance(
        instance_id=f"MULTIFILE_REPAIR#{index:02d}_{'VACUOUS' if vacuous else 'REPAIR'}",
        category="MULTIFILE_REPAIR",
        run=run,
        judge=judge,
        cleanup=cleanup,
        notes=f"vacuous={vacuous}",
    )


# --------------------------------------------------------------------------- category 5: belief revision
def _build_belief_revision(rng: random.Random, index: int) -> BenchInstance:
    """AGM entrenchment / Sybil-echo defense judged against explicit root counts."""
    kind = ("REJECT_LOWER_RANK", "SUPERSEDE", "SYBIL_ECHO")[index % 3]
    subject = rng.choice(("gateway_ip", "dns_primary", "build_channel"))
    incumbent_value = f"10.{rng.randrange(0, 255)}.{rng.randrange(0, 255)}.1"
    challenger_value = f"10.{rng.randrange(0, 255)}.{rng.randrange(0, 255)}.2"
    if kind == "SYBIL_ECHO":
        challenger_value = incumbent_value  # same claim, echoed from a shared lineage

    def run() -> Mapping[str, Any]:
        memory = _CURRENT_SUT.kernel().memory
        if kind == "REJECT_LOWER_RANK":
            memory.stage_or_commit_belief(
                belief_id="incumbent", subject=subject, value=incumbent_value, source_id="root_a",
                parent_lineage_roots=["root_a", "root_b"],
            )
            challenger = memory.stage_or_commit_belief(
                belief_id="challenger", subject=subject, value=challenger_value, source_id="root_c",
                parent_lineage_roots=["root_c"],
            )
            return {"challenger": challenger, "authorized": memory.authorize_irreversible_action(
                required_belief_ids=["incumbent"]),
                "recalled": memory.recall_by_prospective_cues([f"subject:{subject}"])}
        if kind == "SUPERSEDE":
            memory.stage_or_commit_belief(
                belief_id="incumbent", subject=subject, value=incumbent_value, source_id="root_a",
                parent_lineage_roots=["root_a"],
            )
            challenger = memory.stage_or_commit_belief(
                belief_id="challenger", subject=subject, value=challenger_value, source_id="sensor_x",
                parent_lineage_roots=["root_x", "root_y"], attested_by_sensor=True,
            )
            return {"challenger": challenger, "authorized": memory.authorize_irreversible_action(
                required_belief_ids=["challenger"]),
                "recalled": memory.recall_by_prospective_cues([f"subject:{subject}"])}
        memory.stage_or_commit_belief(
            belief_id="incumbent", subject=subject, value=incumbent_value, source_id="root_a",
            parent_lineage_roots=["root_a"],
        )
        echo = memory.stage_or_commit_belief(
            belief_id="echo", subject=subject, value=challenger_value, source_id="mirror_of_root_a",
            parent_lineage_roots=["root_a"],
        )
        return {"challenger": echo, "authorized": memory.authorize_irreversible_action(
            required_belief_ids=["echo"]),
            "recalled": memory.recall_by_prospective_cues([f"subject:{subject}"])}

    def judge(result: Mapping[str, Any]) -> Judgement:
        challenger = result.get("challenger") or {}
        status = str(challenger.get("status") or "")
        authorized = bool((result.get("authorized") or {}).get("authorized"))
        hits = (result.get("recalled") or {}).get("hits") or []
        live_ids = sorted(str(h.get("belief_id")) for h in hits)
        problems: list[str] = []
        if kind == "REJECT_LOWER_RANK":
            # Two independent roots beat one: the challenger must be refused, not merged.
            if "REJECTED" not in status.upper():
                problems.append(f"challenger status {status!r} is not a lower-entrenchment rejection")
            if not authorized:
                problems.append("the entrenched incumbent is no longer allowed to authorize an action")
            if live_ids != ["incumbent"]:
                problems.append(f"prospective recall returned {live_ids}, not the surviving incumbent")
        elif kind == "SUPERSEDE":
            if "COMMITTED" not in status.upper():
                problems.append(f"attested challenger status {status!r} is not COMMITTED")
            if not authorized:
                problems.append("a committed attested belief cannot authorize an irreversible action")
            if challenger.get("retracted_incumbent") != "incumbent":
                problems.append("the superseded incumbent was not recorded as retracted")
            if live_ids != ["challenger"]:
                problems.append(f"prospective recall returned {live_ids}, not the attested challenger alone")
        else:
            # A single lineage cannot commit a belief, however many 'sources' repeat it.
            if "COMMITTED" in status.upper():
                problems.append("a shared-lineage echo was committed as independent corroboration")
            if authorized:
                problems.append("a shared-lineage echo authorized an irreversible action")
            if int(challenger.get("independent_root_count") or 0) > 1:
                problems.append("root lineage sets from one ancestor were counted as independent")
            committed_hits = [h.get("belief_id") for h in hits if str(h.get("status")) == "COMMITTED"
                              and str(h.get("belief_id")) == "echo"]
            if committed_hits:
                problems.append(f"the echo was recalled as committed corroboration: {committed_hits}")
        ok = not problems
        return Judgement(
            ok=ok,
            reason="BELIEF_STATE_MATCHES_ORACLE" if ok else "BELIEF_STATE_CONTRADICTS_ORACLE",
            expected={"kind": kind, "subject": subject},
            observed={"status": status, "authorized": authorized, "recalled": live_ids,
                      "problems": problems},
            # No single task-completion flag exists here, so nothing is counted as a claim.
            sut_claimed=None,
        )

    return BenchInstance(
        instance_id=f"BELIEF_REVISION_ENTRENCHMENT#{index:02d}_{kind}",
        category="BELIEF_REVISION_ENTRENCHMENT",
        run=run,
        judge=judge,
        notes=f"kind={kind} subject={subject}",
    )


# --------------------------------------------------------------------------- category 6: cross-language
_RULES = (
    ("<=", "<", "x <= hi", "x < hi"),
    (">=", ">", "x >= lo", "x > lo"),
    ("<", "<=", "x < hi", "x <= hi"),
    (">", ">=", "x > lo", "x >= lo"),
)
_LANG_TEMPLATES = {
    "typescript": (
        "function check(x: number, bound: number) {{ return {cond}; }}",
        "function check(x: number, bound: number) { return x {op} bound; }",
    ),
    "go": (
        "func check(x int, bound int) bool {{ return {cond} }}",
        "func check(x int, bound int) bool { return x {op} bound }",
    ),
    "rust": (
        "fn check(x: i64, bound: i64) -> bool {{ return {cond}; }}",
        "fn check(x: i64, bound: i64) -> bool { return x {op} bound; }",
    ),
}
_CMP = re.compile(r"x\s*(<=|>=|<|>)\s*bound")


def _build_cross_language(rng: random.Random, index: int) -> BenchInstance:
    """Rule transfer judged by re-deriving the predicate's truth table from the patch."""
    bug_op, fixed_op, source_before, source_after = _RULES[index % len(_RULES)]
    language = ("typescript", "go", "rust")[index % 3]
    buggy_tpl, _ = _LANG_TEMPLATES[language]
    buggy_source = buggy_tpl.format(cond=f"x {bug_op} bound")
    probes = (-3, -1, 0, 1, 3, 7)

    def _pred(op: str, x: int, bound: int) -> bool:
        return {"<": x < bound, "<=": x <= bound, ">": x > bound, ">=": x >= bound}[op]

    def verifier(patched: str) -> bool:
        match = _CMP.search(patched)
        return bool(match) and match.group(1) == fixed_op

    def run() -> Mapping[str, Any]:
        return _CURRENT_SUT.kernel().skill_ratchet.consolidate_and_transfer(
            before_snippet=f"def check(x, bound):\n    return {source_before}\n",
            after_snippet=f"def check(x, bound):\n    return {source_after}\n",
            target_language=language,
            target_buggy_source=buggy_source,
            target_verifier=verifier,
        )

    def judge(result: Mapping[str, Any]) -> Judgement:
        claimed = bool(result.get("pass"))
        transfer = result.get("cross_language_transfer") or {}
        patched = str(transfer.get("patched_source") or "")
        problems: list[str] = []
        match = _CMP.search(patched)
        if not match:
            problems.append("no comparable predicate in the patched source")
            got_op = None
        else:
            got_op = match.group(1)
            if got_op != fixed_op:
                problems.append(f"patched operator {got_op!r} is not the rule's {fixed_op!r}")
        semantic_ok = True
        if got_op is not None:
            # The bench's own truth table: the patch must differ from the bug and match the intent.
            for x in probes:
                for bound in (-1, 0, 2, 5):
                    if _pred(got_op, x, bound) != _pred(fixed_op, x, bound):
                        semantic_ok = False
                        problems.append(f"predicate mismatch at x={x} bound={bound}")
                        break
        if transfer.get("whole_task_correctness_proved") is True:
            problems.append("claimed whole-task correctness from a lexical rewrite")
        ok = not problems and semantic_ok
        return Judgement(
            ok=ok,
            reason="RULE_TRANSFERRED_SEMANTICALLY" if ok else "RULE_TRANSFER_MISMATCH",
            expected={"fixed_operator": fixed_op, "language": language},
            observed={"patched": patched, "operator": got_op, "problems": problems},
            sut_claimed=claimed,
        )

    return BenchInstance(
        instance_id=f"CROSS_LANGUAGE_RULE_TRANSFER#{index:02d}_{language.upper()}",
        category="CROSS_LANGUAGE_RULE_TRANSFER",
        run=run,
        judge=judge,
        notes=f"language={language} bug_op={bug_op} fixed_op={fixed_op}",
    )


_BUILDERS: dict[str, Callable[[random.Random, int], BenchInstance]] = {
    "TRANSFER_UNDER_ISOMORPHISM": _build_transfer,
    "WITNESS_INVERSION_GENERALIZATION": _build_synthesis,
    "COMPUTER_USE_GROUNDING": _build_computer_use,
    "MULTIFILE_REPAIR": _build_multifile_repair,
    "BELIEF_REVISION_ENTRENCHMENT": _build_belief_revision,
    "CROSS_LANGUAGE_RULE_TRANSFER": _build_cross_language,
}

_CURRENT_SUT: Sut = Sut.default()


# --------------------------------------------------------------------------- generation + scoring
def generate_instances(
    *,
    seed: int = DEFAULT_SEED,
    per_category: int = 3,
    categories: Sequence[str] | None = None,
) -> list[BenchInstance]:
    """Build the held-out instance set deterministically from `seed`.

    Answers are never stored: each `BenchInstance.judge` recomputes them from the
    instance's own spec (BFS, enumeration, a subprocess, or a file read).
    """
    if per_category < 1:
        raise ValueError("per_category must be >= 1; an empty benchmark is not a score")
    chosen = list(categories or CATEGORIES)
    unknown = [c for c in chosen if c not in _BUILDERS]
    if unknown:
        raise ValueError(f"unknown categories: {unknown}; known: {sorted(_BUILDERS)}")
    out: list[BenchInstance] = []
    for category in chosen:
        rng = random.Random(f"{seed}:{category}")
        for i in range(per_category):
            out.append(_BUILDERS[category](rng, i))
    return out


def instance_digest(instances: Sequence[BenchInstance]) -> str:
    """A stable fingerprint of the instance set (so a scorecard names what it measured)."""
    payload = json.dumps(
        [{"id": i.instance_id, "category": i.category, "notes": i.notes} for i in instances],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _empty_bucket() -> dict[str, Any]:
    return {"instances": 0, "passed": 0, "failed": 0, "errors": 0, "pass_rate": 0.0, "elapsed_ms": 0.0}


def run_bench(
    *,
    seed: int = DEFAULT_SEED,
    per_category: int = 3,
    categories: Sequence[str] | None = None,
    sut: Sut | None = None,
    instances: Sequence[BenchInstance] | None = None,
) -> dict[str, Any]:
    """Run the bench and return a scorecard. Never raises on a failing engine."""
    global _CURRENT_SUT
    spec = sut or Sut.default()
    previous = _CURRENT_SUT
    _CURRENT_SUT = spec
    t0 = time.perf_counter()
    try:
        bench = list(instances) if instances is not None else generate_instances(
            seed=seed, per_category=per_category, categories=categories
        )
        records: list[dict[str, Any]] = []
        by_category: dict[str, dict[str, Any]] = {}
        for inst in bench:
            bucket = by_category.setdefault(inst.category, _empty_bucket())
            bucket["instances"] += 1
            t_inst = time.perf_counter()
            record: dict[str, Any] = {"instance_id": inst.instance_id, "category": inst.category, "notes": inst.notes}
            try:
                result = inst.run()
            except Exception as exc:  # noqa: BLE001 - fail closed, record the engine's own failure
                record.update({
                    "status": "ERROR",
                    "stage": "SUT",
                    "reason": f"{type(exc).__name__}: {exc}",
                })
                bucket["errors"] += 1
                result = None
            if result is not None:
                try:
                    verdict = inst.judge(result)
                except Exception as exc:  # noqa: BLE001 - a broken judge never passes anything
                    record.update({
                        "status": "ERROR",
                        "stage": "ORACLE",
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
                    bucket["errors"] += 1
                else:
                    record.update(verdict.as_dict())
                    record["status"] = "PASS" if verdict.ok else "FAIL"
                    if verdict.ok:
                        bucket["passed"] += 1
                    else:
                        bucket["failed"] += 1
            record["elapsed_ms"] = round((time.perf_counter() - t_inst) * 1000.0, 3)
            records.append(record)
            if inst.cleanup is not None:
                try:
                    inst.cleanup()
                except Exception:  # noqa: BLE001 - cleanup must never change a verdict
                    pass
        for bucket in by_category.values():
            graded = bucket["passed"] + bucket["failed"] + bucket["errors"]
            bucket["pass_rate"] = round(bucket["passed"] / graded, 4) if graded else 0.0
        total = len(records)
        passed = sum(1 for r in records if r["status"] == "PASS")
        errors = sum(1 for r in records if r["status"] == "ERROR")
        # Two separate honesty metrics, never merged into one:
        #   false_success_claims -- the engine said it did the thing; the oracle says it did not.
        #   unclaimed_successes  -- the engine did the right thing without saying so (refusals,
        #                           lower-entrenchment rejections). Conservatism, not dishonesty.
        false_claims = [r for r in records if r.get("sut_claimed") is True and r["status"] == "FAIL"]
        unclaimed = [r for r in records if r.get("sut_claimed") is False and r["status"] == "PASS"]
        if total == 0:
            verdict = "BENCH_NO_INSTANCES"
        elif errors:
            verdict = "BENCH_INCOMPLETE__ORACLE_OR_ENGINE_ERROR"
        elif passed == total:
            verdict = "BENCH_COMPLETE__ALL_INSTANCES_PASS"
        else:
            verdict = "BENCH_COMPLETE__FAILURES_PRESENT"
        return {
            "schema": SCORECARD_SCHEMA,
            "bench": BENCH_SCHEMA,
            "seed": int(seed),
            "per_category": int(per_category),
            "categories": list(by_category),
            "instance_digest": instance_digest(bench),
            "instances": total,
            "passed": passed,
            "failed": total - passed - errors,
            "errors": errors,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "false_success_claims": len(false_claims),
            "false_success_claim_ids": [r["instance_id"] for r in false_claims],
            "unclaimed_successes": len(unclaimed),
            "unclaimed_success_ids": [r["instance_id"] for r in unclaimed],
            "scored_against_engine_claim": False,
            "stored_answers_used": False,
            "model_calls": 0,
            "spend_usd": 0.0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "by_category": by_category,
            "verdict": verdict,
            "records": records,
        }
    finally:
        _CURRENT_SUT = previous


# --------------------------------------------------------------------------- calibration controls
class _LiarSut(Sut):
    """A system that always reports success and never does the work."""

    def __init__(self) -> None:
        class _Everything:
            @staticmethod
            def learn_and_transfer(**_: Any) -> dict[str, Any]:
                return {
                    "pass": True,
                    "moore_isomorphism_transfer": {
                        "mapped_plan": [],
                        "target_goal_verified_by_execution": True,
                        "isomorphism_status": "WITNESS_FOUND__THE_TWO_ENVIRONMENTS_ARE_THE_SAME_MACHINE",
                    },
                }

            @staticmethod
            def execute_workflow(**_: Any) -> dict[str, Any]:
                return {"pass": True, "relational_frame": {"index": 0}, "done_gate": {"done_allowed": True}}

            @staticmethod
            def repair_repository(*_: Any, **__: Any) -> dict[str, Any]:
                return {"pass": True, "status": "PASS__SIBLING_CLOSED_MULTIFILE", "applied_files": []}

            @staticmethod
            def consolidate_and_transfer(**_: Any) -> dict[str, Any]:
                return {"pass": True, "cross_language_transfer": {"patched_source": "", "whole_task_correctness_proved": True}}

            class memory:  # noqa: N801 - mirrors the kernel's attribute layout
                @staticmethod
                def stage_or_commit_belief(**_: Any) -> dict[str, Any]:
                    return {"status": "COMMITTED", "can_authorize_irreversible": True,
                            "retracted_incumbent": "incumbent", "independent_root_count": 2}

                @staticmethod
                def authorize_irreversible_action(*_: Any, **__: Any) -> dict[str, Any]:
                    return {"authorized": True}

                @staticmethod
                def recall_by_prospective_cues(*_: Any, **__: Any) -> dict[str, Any]:
                    return {"hits": [], "hit_count": 0}

        everything = _Everything()
        super().__init__(
            kernel=lambda: type("K", (), {"instant_learner": everything, "computer_use": everything,
                                          "swe_kernel": everything, "memory": everything.memory,
                                          "skill_ratchet": everything})(),
            synth=lambda *a, **k: {"pass": True, "best_program": "affine(0*x + 0)", "survivor_count": 1},
        )


class _RefuseEverythingSut(Sut):
    """A stub that declines every instance. Truthful on refusal instances only."""

    def __init__(self) -> None:
        def _kernel() -> Any:
            raise RuntimeError("REFUSED__NO_CAPABILITY")

        super().__init__(kernel=_kernel, synth=lambda *a, **k: {"pass": False, "status": "REFUSED__NO_CAPABILITY"})


def bench_self_check(*, seed: int = DEFAULT_SEED, per_category: int = 3) -> dict[str, Any]:
    """Calibrate the instrument: honest, liar, and refusal stub must separate.

    A bench that cannot tell these three apart is measuring its own fixtures.
    `discrimination` is the honest pass rate minus the best of the two controls;
    it must be 1.0 for the instrument to be trusted on this instance set.
    """
    honest = run_bench(seed=seed, per_category=per_category)
    liar = run_bench(seed=seed, per_category=per_category, sut=_LiarSut())
    stub = run_bench(seed=seed, per_category=per_category, sut=_RefuseEverythingSut())
    discrimination = round(honest["pass_rate"] - max(liar["pass_rate"], stub["pass_rate"]), 4)
    return {
        "schema": "BRAIN_FRONTIER_BENCH_SELF_CHECK_V1",
        "seed": int(seed),
        "per_category": int(per_category),
        "honest_pass_rate": honest["pass_rate"],
        "liar_pass_rate": liar["pass_rate"],
        "refusal_stub_pass_rate": stub["pass_rate"],
        "discrimination": discrimination,
        "instrument_trustworthy": bool(discrimination >= 0.999 and liar["pass_rate"] == 0.0),
        "liar_false_success_claims": liar["false_success_claims"],
        "stub_false_success_claims": stub["false_success_claims"],
        "honest_verdict": honest["verdict"],
        "liar_verdict": liar["verdict"],
        "stub_verdict": stub["verdict"],
    }


# --------------------------------------------------------------------------- reporting
def format_table(scorecard: Mapping[str, Any]) -> str:
    header = f"{'category':38s} {'n':>3s} {'pass':>5s} {'fail':>5s} {'err':>4s} {'rate':>6s}"
    lines = [
        f"{scorecard.get('schema')}  seed={scorecard.get('seed')}  instances={scorecard.get('instances')}",
        header,
        "-" * len(header),
    ]
    for name in scorecard.get("categories") or ():
        bucket = (scorecard.get("by_category") or {}).get(name) or {}
        lines.append(
            f"{name:38s} {bucket.get('instances', 0):>3d} {bucket.get('passed', 0):>5d} "
            f"{bucket.get('failed', 0):>5d} {bucket.get('errors', 0):>4d} {bucket.get('pass_rate', 0.0):>6.3f}"
        )
    lines.append("-" * len(header))
    lines.append(
        f"{'TOTAL':38s} {scorecard.get('instances', 0):>3d} {scorecard.get('passed', 0):>5d} "
        f"{scorecard.get('failed', 0):>5d} {scorecard.get('errors', 0):>4d} {scorecard.get('pass_rate', 0.0):>6.3f}"
    )
    lines.append(
        f"false success claims: {scorecard.get('false_success_claims')}  "
        f"unclaimed successes: {scorecard.get('unclaimed_successes')}  "
        f"model_calls: {scorecard.get('model_calls')}  spend_usd: {scorecard.get('spend_usd')}  "
        f"elapsed_ms: {scorecard.get('elapsed_ms')}"
    )
    for record in scorecard.get("records") or ():
        if record.get("status") != "PASS":
            lines.append(f"  {record.get('status'):5s} {record['instance_id']}: {record.get('reason')}")
    lines.append(f"verdict: {scorecard.get('verdict')}")
    return "\n".join(lines)


def exit_code_for(scorecard: Mapping[str, Any]) -> int:
    if not scorecard.get("instances"):
        return 2
    if scorecard.get("errors"):
        return 1
    return 0 if scorecard.get("passed") == scorecard.get("instances") else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave 40 held-out capability benchmark (oracle-judged)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--per-category", type=int, default=3,
                        help="instances per capability class (default 3)")
    parser.add_argument("--category", action="append", choices=list(CATEGORIES), default=None,
                        help="restrict to one or more classes (default: all six)")
    parser.add_argument("--json", default=None, help="write the full scorecard to this path")
    parser.add_argument("--self-check", action="store_true",
                        help="also calibrate the instrument against a liar and a refusal stub")
    parser.add_argument("--quiet", action="store_true", help="print only the verdict line")
    args = parser.parse_args(argv)

    scorecard = run_bench(seed=args.seed, per_category=args.per_category, categories=args.category)
    if args.self_check:
        scorecard["self_check"] = bench_self_check(seed=args.seed, per_category=args.per_category)
    if args.quiet:
        print(f"verdict: {scorecard['verdict']}  pass_rate={scorecard['pass_rate']}")
    else:
        print(format_table(scorecard))
        if args.self_check:
            check = scorecard["self_check"]
            print(
                "self-check: honest={honest_pass_rate} liar={liar_pass_rate} stub={refusal_stub_pass_rate} "
                "discrimination={discrimination} trustworthy={instrument_trustworthy}".format(**check)
            )
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(scorecard, indent=1, sort_keys=False) + "\n", encoding="utf-8")
        print(f"scorecard: {args.json}")
    return exit_code_for(scorecard)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
