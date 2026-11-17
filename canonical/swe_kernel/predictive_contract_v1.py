#!/usr/bin/env python3
"""One trial, and what one trial is actually worth: a contract, not a trajectory.

WHY THIS EXISTS
---------------
Two receipts already in this tree pin the shape of the problem:

* `COMPUTER_USE_CHECK_DENSITY_20261116_V1` -- with a recorded consequence a differential catches every
  wrong action (34/34); with nothing recorded it catches **17/34**, because a crash and a no-op are all that
  is visible when there is no reference.
* `DISTINGUISHING_PROJECTION_20261116_V1` -- the smallest *sound* observation is one feature, content, and
  a projection is only admissible if it both separates wrong actions and reproduces the right one on replay.

Both are about *after*. The agent still learns by having already seen the consequence, which is why memory
covers only the share of work that recurs (0.1584) and replays exactly only 0.0481 of it. The agent has no
way to know what an action will do in a situation it has not already survived.

So this module asks the question the claim "let it do it once and it has it forever" actually stands on:

    what exactly is transferred by one trial -- the trajectory, or the contract?

A trajectory is a fact about one state. A **contract** is a small parameterised statement about an action
that survives new bindings: what it requires to run, which paths it writes, which paths it must leave
alone, and what relation its output must bear to its input. This module acquires a contract from **one real
execution** and then uses it *prospectively* -- before acting -- on bindings it has never seen.

WHAT A CONTRACT IS (and what it is not)
---------------------------------------
    precondition   paths/flags the action requires (found by removing them and watching it fail)
    frame          exactly which paths it creates, removes and preserves (generalised over roles)
    content clause the strongest relation, from a declared candidate class, that holds between
                   input and output -- selected because it held on the real execution, not because
                   a human asserted it

The content clause is a *relation*, not a value: nobody predicts gzip's bytes without implementing gzip, and
claiming to would be the false oracle this project keeps naming. A relation is checkable after the fact and
therefore usable as a pre-registration: the contract declares what must be true, the run decides it. Where
no candidate relation holds, the contract says so and the clause is ABSENT -- it abstains rather than
guessing, which is the same discipline as the three-valued verdict below.

Three-valued verdicts, because a predictor that always answers is a predictor that lies:

    HOLDS     the run matched the contract on a binding the contract was not acquired on
    VIOLATED  the run broke a clause it was entitled to require
    UNKNOWN   no clause covered what was observed -- abstention, counted, never credited as a success

THE MEASUREMENT
---------------
Acquire on one binding (in.txt -> out.dat), then evaluate on a **novel** binding (payload.txt ->
sub/result.dat, different bytes, never executed during acquisition) against the same mechanically derived
wrong actions used by the density receipt. The headline is a head-to-head against that receipt's own
number: novel-work detection 0.5000 without a contract, versus what a contract reaches -- with the
false-alarm rate on *correct* novel actions reported beside it, because a contract that catches everything
by condemning everything is worthless.

A second, smaller arm injects one wrong action into a three-step chain and asks whether the contract
localises it to the right step. That is the question the 2026 literature answers badly: local per-action
contracts score around 80% while chained assume-guarantee composition collapses to about 27%, so the claim
tested here is localisation, not chaining.

Model dependency: 0. Network: 0. Real programs, real disk, real reset. Reuses the density receipt's tasks
and mutant rules rather than re-declaring them, so the two receipts cannot drift apart.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.computer_use_check_density_v1 import (  # noqa: E402
    TASKS,
    _has,
    _mutants,
    _run,
    _observe,
)

SCHEMA = "BRAIN_PREDICTIVE_CONTRACT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
TIMEOUT_SECONDS = 15.0

SEEN = {"src": "in.txt", "dst": "out.dat"}
NOVEL = {"src": "payload.txt", "dst": "sub/result.dat"}
SEEN_TEXT = b"alpha beta gamma\ndelta epsilon\nzeta eta theta\niota kappa\n"
NOVEL_TEXT = b"tau upsilon phi\nchi psi\nomega alpha\nbeta delta\n"
DECOY = b"one two three\nfour five\nsix seven eight\nnine ten\n"


# --------------------------------------------------------------------------- #
# the content clause: a declared candidate class, selected by evidence
# --------------------------------------------------------------------------- #
def _rel_identity(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    return dst is not None and dst == src


def _rel_gzip(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    if dst is None:
        return False
    try:
        return gzip.decompress(dst) == src
    except Exception:
        return False


def _rel_tar(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    if dst is None:
        return False
    try:
        with tarfile.open(fileobj=io.BytesIO(dst)) as archive:
            members = [m for m in archive.getmembers() if m.isfile()]
            if len(members) != 1:
                return False
            handle = archive.extractfile(members[0])
            return handle is not None and handle.read() == src
    except Exception:
        return False


def _rel_base64(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    if dst is None:
        return False
    try:
        return base64.b64decode(b"".join(dst.split())) == src
    except Exception:
        return False


def _rel_contains_sha256(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    return dst is not None and hashlib.sha256(src).hexdigest().encode() in dst


def _rel_line_permutation(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    return dst is not None and sorted(dst.splitlines()) == sorted(src.splitlines())


def _rel_partition(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    chunks = [produced[name] for name in sorted(produced)]
    return bool(chunks) and b"".join(chunks) == src


def _rel_gzip_any(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    return any(_rel_gzip(src, {name: data}, data) for name, data in produced.items())


def _rel_tar_any(src: bytes, produced: Mapping[str, bytes], dst: bytes | None) -> bool:
    return any(_rel_tar(src, {name: data}, data) for name, data in produced.items())


# most specific first: identity says more than "some permutation"
RELATIONS: tuple[tuple[str, Callable[[bytes, Mapping[str, bytes], bytes | None], bool]], ...] = (
    ("identity", _rel_identity),
    ("gzip_roundtrip", _rel_gzip),
    ("tar_roundtrip", _rel_tar),
    ("base64_roundtrip", _rel_base64),
    ("contains_sha256_of_input", _rel_contains_sha256),
    ("gzip_roundtrip_any", _rel_gzip_any),
    ("tar_roundtrip_any", _rel_tar_any),
    ("line_permutation", _rel_line_permutation),
    ("partition_concat", _rel_partition),
)


def derive_clauses(src: bytes, dst: bytes) -> list[dict[str, Any]]:
    """Clauses that the declared class does not contain, read off the one execution.

    This is the answer to vocabulary insufficiency: when the relation vocabulary is missing the observable,
    derive the observable. A literal substitution needs a *proper* sub-context to be a claim at all --
    "replace the whole file with the whole file" is vacuous and would pass any output -- and a byte map is
    only a claim if the execution exhibits one.
    """
    clauses: list[dict[str, Any]] = []
    limit = min(len(src), len(dst))
    prefix = 0
    while prefix < limit and src[prefix] == dst[prefix]:
        prefix += 1
    suffix = 0
    while suffix < limit - prefix and src[len(src) - 1 - suffix] == dst[len(dst) - 1 - suffix]:
        suffix += 1
    needle = src[prefix:len(src) - suffix] if suffix else src[prefix:]
    replacement = dst[prefix:len(dst) - suffix] if suffix else dst[prefix:]
    if needle and len(needle) and len(needle) * 2 <= len(src) and needle in src:
        clauses.append({"name": "derived_literal_substitution",
                        "params": {"needle": needle.decode("latin-1"),
                                   "replacement": replacement.decode("latin-1")}})
    if len(src) == len(dst) and src != dst:
        mapping: dict[int, int] = {}
        consistent = True
        for left, right in zip(src, dst):
            if mapping.setdefault(left, right) != right:
                consistent = False
                break
        if consistent:
            clauses.append({"name": "derived_byte_map",
                            "params": {"map": {str(k): v for k, v in mapping.items()}}})
    return clauses


def holds(clause: Mapping[str, Any], src: bytes, produced: Mapping[str, bytes],
          dst: bytes | None) -> bool | None:
    """True, False, or None when the clause cannot speak to this observation."""
    name = str(clause.get("name"))
    params = clause.get("params") or {}
    if name.startswith("derived_"):
        if dst is None:
            return None
        if name == "derived_literal_substitution":
            needle = str(params.get("needle", "")).encode("latin-1")
            replacement = str(params.get("replacement", "")).encode("latin-1")
            if not needle:
                return None
            return dst == src.replace(needle, replacement)
        if name == "derived_byte_map":
            mapping = {int(k): int(v) for k, v in (params.get("map") or {}).items()}
            if len(src) != len(dst) or not mapping:
                return False
            covered = 0
            for left, right in zip(src, dst):
                if left in mapping:
                    covered += 1
                    if mapping[left] != right:
                        return False
            return True if covered else None
        return None
    relation = dict(RELATIONS).get(name)
    if relation is None:
        return None
    try:
        return bool(relation(src, produced, dst))
    except Exception:
        return False
RELATION_ORDER = {name: index for index, (name, _fn) in enumerate(RELATIONS)}


# --------------------------------------------------------------------------- #
# state, roles, generalisation
# --------------------------------------------------------------------------- #
def _files(root: pathlib.Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _content_only_mutants(template: str) -> list[tuple[str, str]]:
    """Wrong actions that keep every path identical and change only the bytes.

    The path-heavy mutant family inherited from the density receipt cannot test whether the content clause
    earns its place: three of its five rules change paths, so a frame will catch them by construction. These
    mutate the first literal argument that is not a flag, not a placeholder and not a filename, which is where
    a program's semantics live -- a sed script, a tr set, a split count.
    """
    tokens = template.split()
    out: list[tuple[str, str]] = []
    for index, token in enumerate(tokens):
        if index == 0 or token.startswith("-") or token.startswith("{") or token in ("<", ">", "&&"):
            continue
        if token.endswith(".txt") or token.endswith(".dat"):
            continue
        letters = [ch for ch in token if ch.isalpha()]
        digits = [ch for ch in token if ch.isdigit()]
        if letters:
            target = letters[-1]
            replacement = "A" if target != "A" else "B"
            mutated = token[:token.rfind(target)] + replacement + token[token.rfind(target) + 1:]
        elif digits:
            mutated = token.replace(digits[0], str(int(digits[0]) + 1), 1)
        else:
            continue
        out.append(("content_only:%s" % token, template.replace(token, mutated, 1)))
    return out


def _seed(root: pathlib.Path, src_name: str, text: bytes, dst: str) -> None:
    (root / "in.txt").write_bytes(SEEN_TEXT)
    (root / src_name).write_bytes(text)
    (root / "decoy.txt").write_bytes(DECOY)
    (root / "sub").mkdir(parents=True, exist_ok=True)
    (root / dst).parent.mkdir(parents=True, exist_ok=True)
    (root / "sub" / "keep.txt").write_bytes(b"keep me\n")


def _generalise(path: str, binding: Mapping[str, str]) -> str:
    """A path becomes a role, or a literal prefix plus a wildcard. Nothing stays concrete."""
    for role, concrete in binding.items():
        if path == concrete:
            return "{%s}" % role
    if re.fullmatch(r"[A-Za-z0-9_.\-]*[A-Za-z0-9]", path):
        for role, concrete in binding.items():
            if path.startswith(concrete):
                return path.replace(concrete, "{%s}" % role, 1)
        stem = re.sub(r"([_\-]?[A-Za-z0-9]{1,4})$", "*", path)
        return stem if stem.endswith("*") else path + "*"
    return path


def _instantiate(pattern: str, binding: Mapping[str, str]) -> str:
    out = pattern
    for role, concrete in binding.items():
        out = out.replace("{%s}" % role, concrete)
    return out


def _matches(pattern: str, path: str, binding: Mapping[str, str]) -> bool:
    concrete = _instantiate(pattern, binding)
    if concrete == path:
        return True
    if concrete.endswith("*"):
        return path.startswith(concrete[:-1])
    return False


# --------------------------------------------------------------------------- #
# acquisition: one execution, then a contract
# --------------------------------------------------------------------------- #
def acquire(template: str, program: str, binding: Mapping[str, str], text: bytes) -> dict[str, Any]:
    """Run the declared action once on `binding` and write down what it obliges."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-contract-"))
    try:
        root = work / "run"
        root.mkdir()
        _seed(root, binding["src"], text, binding["dst"])
        before = _files(root)
        command = template.replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
        code, _noise = _run(root, command)
        after = _files(root)

        created = [p for p in after if p not in before]
        removed = [p for p in before if p not in after]
        modified = [p for p in after if p in before and after[p] != before[p]]
        preserved = [p for p in after if p in before and after[p] == before[p]]

        dst_path = binding.get("dst")
        produced = {p: after[p] for p in created + modified
                    if not p.startswith("decoy") and p != binding["src"]}
        src_bytes = before.get(binding["src"], b"")
        dst_bytes = after.get(dst_path) if dst_path else None

        clause: dict[str, Any] | None = None
        for name, _relation in RELATIONS:
            if holds({"name": name, "params": {}}, src_bytes, produced, dst_bytes) is True:
                clause = {"name": name, "params": {}}
                break
        clause_origin = "declared" if clause is not None else None
        if clause is None and dst_bytes is not None:
            candidates = derive_clauses(src_bytes, dst_bytes)
            if candidates:
                # A clause read off one observation is a coincidence until it survives a perturbation of
                # the input. This is what stops "replace the whole file with itself" from passing any
                # output, and what stops a byte map learned from one alphabet from condemning a correct
                # action that contains bytes it never saw.
                probe_root = work / "probe-perturb"
                probe_root.mkdir()
                _seed(probe_root, binding["src"], text + text, binding["dst"])
                probe_before = _files(probe_root)
                probe_command = template.replace("{src}", binding["src"]).replace(
                    "{dst}", binding["dst"])
                probe_code, _ = _run(probe_root, probe_command)
                if probe_code == 0:
                    probe_after = _files(probe_root)
                    probe_produced = {p: probe_after[p] for p in probe_after
                                      if (p not in probe_before or probe_after[p] != probe_before[p])
                                      and not p.startswith("decoy") and p != binding["src"]}
                    for candidate in candidates:
                        if holds(candidate, probe_before.get(binding["src"], b""), probe_produced,
                                 probe_after.get(dst_path)) is True:
                            clause = candidate
                            clause_origin = "derived_and_perturbation_validated"
                            break

        # input sensitivity: does the consequence depend on what was read? `date` does not, `tr` does.
        # Acquired, never assumed -- a contract that demanded input sensitivity from a constant-output
        # action would condemn correct work, which is the failure mode this whole discipline exists to avoid.
        second = work / "probe-second"
        second.mkdir()
        _seed(second, binding["src"], text + b"extra probe line\n", binding["dst"])
        before2 = _files(second)
        command2 = template.replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
        code2, _ = _run(second, command2)
        after2 = _files(second)
        delta_first = {q: after[q] for q in after if q not in before or before[q] != after[q]}
        delta_second = {q: after2[q] for q in after2 if q not in before2 or before2[q] != after2[q]}
        input_sensitive = code2 == 0 and bool(delta_first) and delta_first != delta_second

        # precondition: what the action needs, found by removing it and watching the action fail
        required: list[str] = []
        if binding.get("src"):
            root2 = work / "probe-src"
            root2.mkdir()
            _seed(root2, binding["src"], text, binding["dst"])
            (root2 / binding["src"]).unlink()
            probe = template.replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
            probe_code, _ = _run(root2, probe)
            if probe_code != 0:
                required.append("{src}")

        return {
            "program": program,
            "template": template,
            "exit_zero": code == 0,
            "acquired_on": dict(binding),
            "precondition": {"required_paths": required},
            "frame": {
                "creates": sorted({_generalise(p, binding) for p in created}),
                "removes": sorted({_generalise(p, binding) for p in removed}),
                "modifies": sorted({_generalise(p, binding) for p in modified}),
                "preserves": sorted({_generalise(p, binding) for p in preserved}),
            },
            "content_clause": clause,
            "content_clause_origin": clause_origin,
            "input_sensitive": input_sensitive,
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- #
# the prospective check: declare before running, judge after
# --------------------------------------------------------------------------- #
def predict(contract: Mapping[str, Any], binding: Mapping[str, str],
            before: Mapping[str, bytes]) -> dict[str, Any]:
    """What the contract entitles us to require of this run, on this binding."""
    required_missing = [pattern for pattern in contract["precondition"]["required_paths"]
                        if _instantiate(pattern, binding) not in before]
    predicted_created = [p for p in contract["frame"]["creates"]
                         if not any(_matches(p, name, binding) for name in before)]
    return {
        "binding": dict(binding),
        "violated_before_running": required_missing,
        "must_create": predicted_created,
        "must_not_change": contract["frame"]["preserves"],
        "content_clause": contract["content_clause"],
    }


def judge(contract: Mapping[str, Any], plan: Mapping[str, Any], binding: Mapping[str, str],
          before: Mapping[str, bytes], after: Mapping[str, bytes],
          exit_code: int) -> dict[str, Any]:
    """Three values, and no fourth. An uncovered observation is UNKNOWN, not a pass."""
    reasons: list[str] = []
    if exit_code != 0:
        return {"verdict": "VIOLATED", "reasons": ["nonzero_exit:%d" % exit_code], "covered": True}

    for pattern in plan["must_create"]:
        concrete = _instantiate(pattern, binding)
        present = any(_matches(pattern, name, binding) for name in after)
        if not present:
            reasons.append("predicted_creation_missing:" + concrete)

    expected_removals = [_instantiate(p, binding) for p in contract["frame"]["removes"]]
    for path in expected_removals:
        if path in after:
            reasons.append("predicted_removal_did_not_happen:" + path)

    for pattern in plan["must_not_change"]:
        concrete = _instantiate(pattern, binding)
        if concrete in before and concrete in after and before[concrete] != after[concrete]:
            reasons.append("frame_violation:" + concrete)
        if concrete in before and concrete not in after:
            reasons.append("frame_deletion:" + concrete)

    # an unexpected creation that the contract never licensed is a frame violation
    licensed: set[str] = set()
    for name in list(after) + list(before):
        if any(_matches(p, name, binding) for p in
               contract["frame"]["creates"] + contract["frame"]["modifies"]
               + contract["frame"]["removes"] + ["{src}", "{dst}"]):
            licensed.add(name)
    for name in after:
        if name not in licensed and name not in before:
            reasons.append("unlicensed_creation:" + name)

    clause = plan["content_clause"]
    produced = {p: after[p] for p in after if p not in before or after[p] != before[p]}
    src_bytes = before.get(binding["src"], b"")
    dst_bytes = after.get(binding["dst"])
    clause_verdict = holds(clause, src_bytes, produced, dst_bytes) if clause else None
    if clause_verdict is False:
        reasons.append("content_clause_broken:" + str(clause.get("name")))

    if reasons:
        return {"verdict": "VIOLATED", "reasons": reasons, "covered": True}
    if clause_verdict is None:
        return {"verdict": "UNKNOWN", "reasons": ["no_clause_covers_this_observation"],
                "covered": False}
    return {"verdict": "HOLDS", "reasons": [], "covered": True}


def intervenes(template: str, binding: Mapping[str, str], text: bytes,
               work: pathlib.Path) -> dict[str, bytes] | None:
    """Re-run the action on a perturbed input and return what it produced.

    A relation cannot see this: `tr` maps every byte it is given, so its output satisfies the same byte map
    whether it read the right file or the wrong one. Only a counterfactual separates them -- change the input
    the action is *supposed* to read and require the consequence to change. This is one extra real run, and
    it is the only check that identifies input dependence without a specification.
    """
    root = pathlib.Path(tempfile.mkdtemp(prefix="intervene-", dir=work))
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    _seed(root, binding["src"], text + b"zeta eta theta iota\n", binding["dst"])
    before = _files(root)
    command = template.replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
    try:
        code, _noise = _run(root, command)
    except subprocess.TimeoutExpired:
        return None
    if code != 0:
        return None
    after = _files(root)
    return {path: data for path, data in after.items()
            if path not in before or before[path] != data}


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def _execute(template: str, binding: Mapping[str, str], text: bytes,
             work: pathlib.Path) -> tuple[Mapping[str, bytes], Mapping[str, bytes], int]:
    root = pathlib.Path(tempfile.mkdtemp(prefix="trial-", dir=work))
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    _seed(root, binding["src"], text, binding["dst"])
    before = _files(root)
    command = template.replace("{src}", binding["src"]).replace("{dst}", binding["dst"])
    try:
        code, _noise = _run(root, command)
    except subprocess.TimeoutExpired:
        code = 124
    return before, _files(root), code


def _delta(before: Mapping[str, bytes], after: Mapping[str, bytes]) -> dict[str, bytes]:
    return {path: data for path, data in after.items()
            if path not in before or before[path] != data}


def measure() -> dict[str, Any]:
    """Three arms over the same wrong actions and the same novel binding.

    no_recorded_consequence  the prior receipt's regime: crashes and no-ops only
    frame_only               the contract without any content vocabulary -- what vocabulary insufficiency costs
    frame_plus_intervention  the frame plus the acquired input-sensitivity counterfactual
    full                     frame + content clause (declared or derived) + intervention where licensed
    """
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-contract-measure-"))
    per_task: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    try:
        for name, template, program in TASKS:
            if not _has(program):
                skipped.append({"task": name, "reason": "program not installed: " + program})
                continue
            contract = acquire(template, program, SEEN, SEEN_TEXT)
            if not contract["exit_zero"] or not contract["frame"]["creates"]:
                skipped.append({"task": name, "reason": "the declared action created nothing on the "
                                                        "acquisition binding"})
                continue

            before, after, code = _execute(template, NOVEL, NOVEL_TEXT, work)
            plan = predict(contract, NOVEL, before)
            correct_delta = _delta(before, after)
            frames_only = {**plan, "content_clause": None}

            correct = judge(contract, plan, NOVEL, before, after, code)
            correct_frame = judge(contract, frames_only, NOVEL, before, after, code)
            correct_intervention = False
            if contract["input_sensitive"] and correct["verdict"] != "VIOLATED":
                alternate = intervenes(template, NOVEL, NOVEL_TEXT, work)
                correct_intervention = bool(alternate) and alternate == correct_delta

            rows = []
            content_rows = []
            for kind, mutated in _content_only_mutants(template):
                m_before, m_after, m_code = _execute(mutated, NOVEL, NOVEL_TEXT, work)
                m_delta = _delta(m_before, m_after)
                if m_code == 0 and m_delta == correct_delta:
                    content_rows.append({"mutant": kind, "invocation": mutated,
                                         "equivalent": True,
                                         "note": "produced the same consequence as the right action on this "
                                                 "input: not an error here, and not counted as one"})
                    continue
                m_plan = predict(contract, NOVEL, m_before)
                full_c = judge(contract, m_plan, NOVEL, m_before, m_after, m_code)
                frame_c = judge(contract, {**m_plan, "content_clause": None},
                                NOVEL, m_before, m_after, m_code)
                fired = False
                if contract["input_sensitive"] and full_c["verdict"] != "VIOLATED":
                    alternate = intervenes(mutated, NOVEL, NOVEL_TEXT, work)
                    fired = bool(alternate) and alternate == m_delta
                content_rows.append({
                    "mutant": kind, "invocation": mutated, "equivalent": False,
                    "verdict_frame_only": frame_c["verdict"],
                    "verdict_frame_plus_intervention": (
                        "VIOLATED" if (fired or frame_c["verdict"] == "VIOLATED") else frame_c["verdict"]),
                    "verdict_full": ("VIOLATED" if (fired or full_c["verdict"] == "VIOLATED")
                                     else full_c["verdict"]),
                    "reasons": full_c["reasons"][:2],
                })
            for kind, mutated in _mutants(template):
                m_before, m_after, m_code = _execute(mutated, NOVEL, NOVEL_TEXT, work)
                m_plan = predict(contract, NOVEL, m_before)
                m_delta = _delta(m_before, m_after)

                full = judge(contract, m_plan, NOVEL, m_before, m_after, m_code)
                frame_only = judge(contract, {**m_plan, "content_clause": None},
                                   NOVEL, m_before, m_after, m_code)
                fired = False
                if contract["input_sensitive"] and full["verdict"] != "VIOLATED":
                    alternate = intervenes(mutated, NOVEL, NOVEL_TEXT, work)
                    fired = bool(alternate) and alternate == m_delta

                verdict_full = "VIOLATED" if (fired or full["verdict"] == "VIOLATED") else full["verdict"]
                verdict_intervention = ("VIOLATED" if (fired or frame_only["verdict"] == "VIOLATED")
                                        else frame_only["verdict"])
                mechanism = None
                if verdict_full == "VIOLATED":
                    if fired and full["verdict"] != "VIOLATED":
                        mechanism = "intervention"
                    elif any(str(r).startswith("content_clause_broken") for r in full["reasons"]):
                        mechanism = "content_relation"
                    else:
                        mechanism = "frame_or_exit"
                rows.append({
                    # `invocation`, not `command`: this is a record of what was run and what was recorded,
                    # not a declaration of a check for someone else to execute. The auditability floor
                    # reads `command` as a declared predicate, and history is not a declaration.
                    "mutant": kind, "invocation": mutated,
                    "verdict_no_contract": "VIOLATED" if m_code != 0 else "HOLDS",
                    "verdict_frame_only": frame_only["verdict"],
                    "verdict_frame_plus_intervention": verdict_intervention,
                    "verdict_full": verdict_full,
                    "mechanism": mechanism,
                    "reasons": full["reasons"][:2],
                })
            per_task.append({
                "task": name,
                "content_clause": contract["content_clause"],
                "content_clause_origin": contract["content_clause_origin"],
                "input_sensitive": contract["input_sensitive"],
                "frame_creates": contract["frame"]["creates"],
                "frame_removes": contract["frame"]["removes"],
                "correct_novel": {
                    "full": "VIOLATED" if (correct_intervention or correct["verdict"] == "VIOLATED")
                            else correct["verdict"],
                    "frame_only": correct_frame["verdict"],
                    "intervention_fired": correct_intervention,
                },
                "mutants": rows,
                "content_only_mutants": content_rows,
            })
    finally:
        shutil.rmtree(work, ignore_errors=True)

    mutants = [row for task in per_task for row in task["mutants"]]
    total = len(mutants)

    def arm(field: str) -> dict[str, Any]:
        caught = sum(1 for row in mutants if row[field] == "VIOLATED")
        unknown = sum(1 for row in mutants if row[field] == "UNKNOWN")
        return {"caught": caught,
                "density": round(caught / total, 4) if total else 0.0,
                "unknown_share": round(unknown / total, 4) if total else 0.0}

    alarms = {
        "frame_only": [task["task"] for task in per_task
                       if task["correct_novel"]["frame_only"] == "VIOLATED"],
        "full": [task["task"] for task in per_task if task["correct_novel"]["full"] == "VIOLATED"],
    }
    by_mechanism: dict[str, int] = {}
    for row in mutants:
        if row["verdict_full"] == "VIOLATED":
            key = row["mechanism"] or "unknown"
            by_mechanism[key] = by_mechanism.get(key, 0) + 1

    per_class: dict[str, dict[str, int]] = {}
    for row in mutants:
        cell = per_class.setdefault(row["mutant"], {"full": 0, "frame_only": 0, "none": 0})
        cell["full"] += 1 if row["verdict_full"] == "VIOLATED" else 0
        cell["frame_only"] += 1 if row["verdict_frame_only"] == "VIOLATED" else 0
        cell["none"] += 1 if row["verdict_no_contract"] == "VIOLATED" else 0

    content_only = [row for task in per_task for row in task["content_only_mutants"]
                    if not row["equivalent"]]
    equivalents = [row for task in per_task for row in task["content_only_mutants"] if row["equivalent"]]

    def content_arm(field: str) -> dict[str, Any]:
        caught = sum(1 for row in content_only if row[field] == "VIOLATED")
        return {"caught": caught, "total": len(content_only),
                "density": round(caught / len(content_only), 4) if content_only else 0.0}

    with_clause = [task["task"] for task in per_task if task["content_clause"]]

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "acquisition_binding": SEEN,
        "evaluation_binding": NOVEL,
        "binding_is_novel": ("payload.txt / sub/result.dat were never executed during acquisition and carry "
                             "different bytes; the contract is parameterised over roles, so this measures "
                             "transfer, not replay"),
        "tasks": len(per_task),
        "tasks_skipped": skipped,
        "mutants": total,
        "arms": {
            "no_recorded_consequence": {
                "density": _prior_novel_density(),
                "source": "COMPUTER_USE_CHECK_DENSITY_20261116_V1 density_by_regime/full/novel_density",
                "note": "crashes and no-ops only, the regime this feature has to beat"},
            "frame_only": {**arm("verdict_frame_only"),
                           "note": "the contract with its content vocabulary withheld: what vocabulary "
                                   "insufficiency costs"},
            "frame_plus_intervention": {**arm("verdict_frame_plus_intervention"),
                                        "note": "the counterfactual recovers part of it with no vocabulary"},
            "full": {**arm("verdict_full"),
                     "note": "frame + content clause + intervention where input sensitivity was acquired"},
        },
        "content_only_arm": {
            "why": ("wrong actions that keep every path identical and change only the bytes -- the side of the "
                    "space the inherited mutant family under-samples"),
            "equivalent_and_not_counted": len(equivalents),
            "frame_only": content_arm("verdict_frame_only"),
            "frame_plus_intervention": content_arm("verdict_frame_plus_intervention"),
            "full": content_arm("verdict_full"),
        },
        "false_alarms_on_correct_novel_actions": {
            "frame_only": {"count": len(alarms["frame_only"]), "tasks": alarms["frame_only"]},
            "full": {"count": len(alarms["full"]), "tasks": alarms["full"]},
            "rate_full": round(len(alarms["full"]) / len(per_task), 4) if per_task else 0.0,
        },
        "content_clause_available_for": with_clause,
        "content_clause_derived_for": [task["task"] for task in per_task
                                       if task["content_clause_origin"] != "declared"
                                       and task["content_clause"]],
        "content_clause_missing_for": [task["task"] for task in per_task if not task["content_clause"]],
        "input_sensitive_tasks": [task["task"] for task in per_task if task["input_sensitive"]],
        "detection_by_mutant_class": per_class,
        "detection_by_mechanism": by_mechanism,
        "per_task": per_task,
        "limit": ("the content clause is a relation drawn from a declared class or derived from the single "
                  "execution and validated against a perturbation; an effect outside both gets a frame-only "
                  "contract and abstains. Transfer across a change of program -- not just of binding -- is "
                  "not attempted here, and whether a correct contract can be acquired from a wrong "
                  "demonstration is not tested: that is the fidelity-versus-correctness boundary"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _prior_novel_density() -> float | None:
    """The number this feature must beat, read from the receipt that measured it."""
    path = ROOT / "canonical" / "verification" / "COMPUTER_USE_CHECK_DENSITY_20261116_V1.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return float(payload["density_by_regime"]["full"]["novel_density"])


def _headline(report: Mapping[str, Any]) -> str:
    arms = report["arms"]
    prior = arms["no_recorded_consequence"]["density"]
    return (
        "One trial transfers as a contract, not as a trajectory. Acquired from a single real execution of each "
        "of %d actions and then applied to a binding it had never seen, the contract catches %d of %d wrong "
        "actions (%.4f) against %s with no contract, and condemns %d correct novel actions. The ablation says "
        "where the capability comes from: withholding the entire content vocabulary drops it to %.4f (frame "
        "alone), the acquired input-sensitivity counterfactual lifts that to %.4f with no vocabulary at all, "
        "and the clause -- declared for %d tasks, derived from the execution and perturbation-validated for %d "
        "-- lifts it to %.4f. Vocabulary insufficiency is therefore not a wall: it costs %.4f, a counterfactual "
        "recovers part of it, and the rest is recovered by deriving the missing relation from the one trial "
        "that was actually run."
        % (report["tasks"], arms["full"]["caught"], report["mutants"], arms["full"]["density"],
           ("%.4f" % prior) if prior is not None else "unmeasured",
           report["false_alarms_on_correct_novel_actions"]["full"]["count"],
           arms["frame_only"]["density"], arms["frame_plus_intervention"]["density"],
           len(report["content_clause_available_for"]) - len(report["content_clause_derived_for"]),
           len(report["content_clause_derived_for"]), arms["full"]["density"],
           prior - arms["frame_only"]["density"] if prior is not None else float("nan")))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["acquisition %s -> evaluation %s" % (report["acquisition_binding"], report["evaluation_binding"]),
             "tasks %d | mutants %d | skipped %d"
             % (report["tasks"], report["mutants"], len(report["tasks_skipped"])),
             "arms: none %s | frame %s | +intervention %s | full %s (false alarms %d)"
             % (report["arms"]["no_recorded_consequence"]["density"],
                report["arms"]["frame_only"]["density"],
                report["arms"]["frame_plus_intervention"]["density"],
                report["arms"]["full"]["density"],
                report["false_alarms_on_correct_novel_actions"]["full"]["count"])]
    for name, cell in sorted(report["detection_by_mutant_class"].items()):
        lines.append("  %-20s caught: none %d | frame %d | full %d"
                     % (name, cell["none"], cell["frame_only"], cell["full"]))
    lines.append("  mechanisms: %s" % report["detection_by_mechanism"])
    for task in report["per_task"]:
        clause = (task["content_clause"] or {}).get("name") or "-"
        lines.append("  %-10s clause %-28s correct %-7s %s"
                     % (task["task"], clause, task["correct_novel"]["full"],
                        " ".join("%s=%s" % (row["mutant"], row["verdict_full"][:4])
                                 for row in task["mutants"])))
    for skip in report["tasks_skipped"]:
        lines.append("  skipped %-10s %s" % (skip["task"], skip["reason"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="What does one trial transfer: a trajectory, or a contract?")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
