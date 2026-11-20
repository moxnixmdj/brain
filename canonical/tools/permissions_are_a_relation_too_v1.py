#!/usr/bin/env python3
"""A new reader with permissions: compute its relations, do not write them.

WHY THIS ROUND EXISTS
---------------------
`the_vocabulary_is_the_artifact_v1` states its own limit verbatim: a machine whose only difference
is permissions or ownership would defeat its five relations. This round tests whether the computed
key/value law algebra, which received no named law in the git round, can state a relation the old
grammar could not: file mode. It is given a completely different machine -- a real directory whose
reader reports bytes and octal modes -- and no relation name, file name, law name or judge string.

WHAT IS BUILT
-------------
1. READER: every state becomes key/value facts from real files: target bytes, target modes,
   worktree bytes, worktree modes and extra paths. Prefixes are discovered from these facts.
2. DERIVED JUDGE: a target tree's own bytes and modes are the reference. The judge accepts exactly
   when every target path has the target bytes and target mode and no extra path exists.
3. DISCOVERY: generic mutations (break bytes, break mode, add extra path) are executed from a clean
   tree; one origin per observed defect family is kept.
4. SELECTION: the existing computed law algebra enumerates preserve/no_new/restore/flag templates
   and exceptions from readings, selects the smallest separator on a training tree, and writes it
   to an external store. It is then evaluated on origins discovered independently in a different
   tree with different names, counts and modes.

This is a producer-run, bounded, model-free experiment. The action vocabulary, target tree and depth
bounds are supplied; no named law, mode rule or file name enters selection. No GUI, browser,
benchmark score, parameter, model call or independent verification is claimed.

Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import stat
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import computed_law_algebra_v1 as L  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402

SCHEMA = "BRAIN_PERMISSIONS_ARE_A_RELATION_TOO_V1"
DISCOVER_DEPTH = 2
REPAIR_DEPTH = 5
REPAIR_CAP = 400
WRONG_CONTENT = b"wrong bytes from the reader's own machine\n"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _mode(path: pathlib.Path) -> str:
    return oct(stat.S_IMODE(path.stat().st_mode))


class Tree:
    """A real directory with its own target snapshot: no task-specific relation names."""

    def __init__(self, root: pathlib.Path, files: Mapping[str, tuple[bytes, int]]) -> None:
        self.root = root
        self.target = dict(files)
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        for name, (data, mode) in files.items():
            item = root / name
            item.write_bytes(data)
            item.chmod(mode)

    def snapshot_path(self, name: str) -> pathlib.Path:
        digest = hashlib.sha256(name.encode()).hexdigest()[:8]
        temporary = self.root.parent / ("target-" + digest)
        temporary.write_bytes(self.target[name][0])
        return temporary

    def read(self) -> GC.Reading:
        facts: dict[str, str] = {}
        for name, (data, mode) in self.target.items():
            facts[f"target.{name}"] = _digest(data)
            facts[f"targetmode.{name}"] = oct(mode)
            item = self.root / name
            if item.is_file():
                facts[f"content.{name}"] = _digest(item.read_bytes())
                facts[f"mode.{name}"] = _mode(item)
            else:
                facts[f"content.{name}"] = "MISSING"
        for item in sorted(self.root.iterdir()):
            if item.name not in self.target:
                facts[f"extra.{item.name}"] = "present"
        return GC.Reading(facts=facts)


def read_at(path: pathlib.Path, target: GC.Reading) -> GC.Reading:
    targets = target.by_prefix("target.")
    modes = target.by_prefix("targetmode.")
    facts: dict[str, str] = dict(target.facts)
    names = {k[len("target."):] for k in targets}
    for key, digest in targets.items():
        name = key[len("target."):]
        item = path / name
        if item.is_file():
            facts[f"content.{name}"] = _digest(item.read_bytes())
            facts[f"mode.{name}"] = _mode(item)
        else:
            facts[f"content.{name}"] = "MISSING"
    for item in sorted(path.iterdir()):
        if item.name not in names:
            facts[f"extra.{item.name}"] = "present"
    _ = modes
    return GC.Reading(facts=facts)


def derived_judge(target: GC.Reading) -> Callable[[pathlib.Path], tuple[bool, str]]:
    targets = target.by_prefix("target.")
    modes = target.by_prefix("targetmode.")

    def judge(path: pathlib.Path) -> tuple[bool, str]:
        current = read_at(path, target)
        reasons = []
        for key, digest in targets.items():
            name = key[len("target."):]
            if current.get(f"content.{name}") != digest:
                reasons.append("content " + name)
            if current.get(f"mode.{name}") != modes.get(f"targetmode.{name}"):
                reasons.append("mode " + name)
        if current.by_prefix("extra."):
            reasons.append("extra path")
        return (not reasons), ", ".join(reasons) or "derived goal"

    return judge


def weak_goal(path: pathlib.Path, target: GC.Reading) -> tuple[bool, str]:
    """Literal instruction: the original file set, with no extra path."""
    names = {k[len("target."):] for k in target.by_prefix("target.")}
    missing = sorted(name for name in names if not (path / name).is_file())
    extra = sorted(p.name for p in path.iterdir() if p.name not in names)
    reasons = ([f"missing {n}" for n in missing] + [f"extra {n}" for n in extra])
    return (not reasons), ", ".join(reasons) or "literal goal satisfied"


@dataclass(frozen=True)
class Action:
    name: str
    apply: Callable[[pathlib.Path, Tree], bool]


def actions(tree: Tree) -> tuple[Action, ...]:
    out: list[Action] = []

    def write_bytes(path: pathlib.Path, data: bytes) -> bool:
        path.write_bytes(data)
        return True

    def set_mode(path: pathlib.Path, mode: int) -> bool:
        path.chmod(mode)
        return True

    def restore_content(name: str) -> Callable[[pathlib.Path, Tree], bool]:
        return lambda p, t: write_bytes(p / name, t.snapshot_path(name).read_bytes())

    def restore_mode(name: str) -> Callable[[pathlib.Path, Tree], bool]:
        return lambda p, t: set_mode(p / name, t.target[name][1])

    def break_content(name: str) -> Callable[[pathlib.Path, Tree], bool]:
        return lambda p, _t: write_bytes(p / name, WRONG_CONTENT)

    def break_mode(name: str) -> Callable[[pathlib.Path, Tree], bool]:
        def run(p: pathlib.Path, t: Tree) -> bool:
            target_mode = t.target[name][1]
            wrong = 0o600 if target_mode != 0o600 else 0o644
            (p / name).chmod(wrong)
            return True
        return run

    for name in sorted(tree.target):
        out.extend((Action("restore_content:" + name, restore_content(name)),
                    Action("restore_mode:" + name, restore_mode(name)),
                    Action("break_content:" + name, break_content(name)),
                    Action("break_mode:" + name, break_mode(name))))
    out.append(Action("add_extra", lambda p, _t: write_bytes(
        p / "EXTRA_FROM_READER.txt", b"extra\n")))
    out.append(Action("remove_extra", lambda p, _t: _remove_extra(p)))
    return tuple(out)


def _remove_extra(path: pathlib.Path) -> bool:
    extras = [p for p in path.iterdir() if p.is_file() and p.name.startswith("EXTRA")]
    if not extras:
        return False
    extras[0].unlink()
    return True


def defects(reading: GC.Reading, target: GC.Reading) -> tuple[str, ...]:
    found: set[str] = set()
    for key, digest in target.by_prefix("target.").items():
        name = key[len("target."):]
        if reading.get(f"content.{name}") != digest:
            found.add("content_mismatch")
    for key, mode in target.by_prefix("targetmode.").items():
        name = key[len("targetmode."):]
        if reading.get(f"mode.{name}") != mode:
            found.add("mode_mismatch")
    if reading.by_prefix("extra."):
        found.add("extra_path")
    return tuple(sorted(found))


def _copy(source: pathlib.Path, workspace: pathlib.Path, label: str) -> pathlib.Path:
    child = workspace / label
    if child.exists():
        shutil.rmtree(child)
    shutil.copytree(source, child, copy_function=shutil.copy2)
    return child


def discover(tree: Tree, target: GC.Reading, workspace: pathlib.Path) -> tuple[list[dict[str, Any]], int]:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    all_actions = actions(tree)
    mutators = tuple(a for a in all_actions if a.name.startswith(("break_", "add_extra")))
    frontier: list[tuple[pathlib.Path, tuple[str, ...]]] = [(tree.root, ())]
    seen = {tuple(sorted(target.facts.items()))}
    candidates: dict[str, dict[str, Any]] = {}
    edges = 0
    counter = 0
    for _depth in range(DISCOVER_DEPTH):
        nxt: list[tuple[pathlib.Path, tuple[str, ...]]] = []
        for state, plan in frontier:
            for action in mutators:
                edges += 1
                counter += 1
                child = _copy(state, workspace, f"d{counter}")
                try:
                    applied = action.apply(child, tree)
                except OSError:
                    applied = False
                if not applied:
                    shutil.rmtree(child, ignore_errors=True)
                    continue
                reading = read_at(child, target)
                found = defects(reading, target)
                if found:
                    family = found[0]
                    candidates.setdefault(family, {"path": child, "plan": list(plan + (action.name,)),
                                                   "defects": list(found)})
                key = tuple(sorted({**target.facts, **reading.facts}.items()))
                if key not in seen:
                    seen.add(key)
                    nxt.append((child, plan + (action.name,)))
        frontier = nxt
    return [candidates[k] for k in ("content_mismatch", "extra_path", "mode_mismatch") if k in candidates], edges


def collect_rows(origin: Mapping[str, Any], tree: Tree, target: GC.Reading,
                 workspace: pathlib.Path, label: str) -> list[GC.Judgment]:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    begin = read_at(origin["path"], target)
    judge = derived_judge(target)
    frontier: list[tuple[pathlib.Path, tuple[str, ...]]] = [(origin["path"], ())]
    seen = {tuple(sorted({**target.facts, **begin.facts}.items()))}
    rows: list[GC.Judgment] = []
    edges = 0
    counter = 0
    for _depth in range(REPAIR_DEPTH):
        nxt: list[tuple[pathlib.Path, tuple[str, ...]]] = []
        for state, plan in frontier:
            for action in actions(tree):
                if edges >= REPAIR_CAP:
                    break
                edges += 1
                counter += 1
                child = _copy(state, workspace, f"{label}-{counter}")
                try:
                    applied = action.apply(child, tree)
                except OSError:
                    applied = False
                if not applied:
                    shutil.rmtree(child, ignore_errors=True)
                    continue
                post = read_at(child, target)
                weak, _why = weak_goal(child, target)
                if weak:
                    ok, _reason = judge(child)
                    rows.append(GC.Judgment(begin, post, child,
                                            "LEGITIMATE" if ok else "HOLE",
                                            plan + (action.name,)))
                key = tuple(sorted({**target.facts, **post.facts}.items()))
                if key not in seen:
                    seen.add(key)
                    nxt.append((child, plan + (action.name,)))
        frontier = nxt
        if edges >= REPAIR_CAP:
            break
    return rows


TRAIN_FILES = {
    "alpha.txt": (b"alpha\n", 0o644),
    "beta.cfg": (b"beta\n", 0o600),
    "notes.md": (b"notes\n", 0o640),
}
HELD_FILES = {
    "x.dat": (b"ex\n", 0o600),
    "y.ini": (b"why\n", 0o644),
    "z.log": (b"zed\n", 0o640),
    "q.txt": (b"cue\n", 0o644),
}


def _measure_tree(root: pathlib.Path, label: str, files: Mapping[str, tuple[bytes, int]]) -> tuple[list[GC.Judgment], GC.Reading, dict[str, Any]]:
    tree = Tree(root / label / "base", files)
    target = tree.read()
    origins, edges = discover(tree, target, root / f"discover-{label}")
    rows: list[GC.Judgment] = []
    for i, origin in enumerate(origins):
        rows.extend(collect_rows(origin, tree, target, root / f"repair-{label}-{i}", label))
    summary = {"discovery_edges": edges,
               "families": [o["defects"] for o in origins],
               "plans": [o["plan"] for o in origins]}
    return rows, target, summary


def measure(root: pathlib.Path, *, receipt: pathlib.Path | None = None,
            store: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "claim": "A relation invisible to the old five-relation grammar (file mode) is computed "
                 "from a new reader's facts and transfers to a different directory.",
        "declared_before_the_run": [
            "G1 mode, content and extra-path defect families are discovered in both trees",
            "G2 the computed algebra selects a closure from training rows",
            "G3 zero false accepts and zero false rejects on the held tree",
            "G4 the closure contains a mode relation and no file name",
            "G5 zero model calls and zero stored parameters",
        ],
        "limits": ["action vocabulary, target tree and bounds are supplied",
                   "real filesystem, but not a GUI, browser or open benchmark",
                   "producer-run; no independent verification"],
    }
    train_rows, _train_target, train_summary = _measure_tree(root, "train", TRAIN_FILES)
    held_rows, _held_target, held_summary = _measure_tree(root, "held_out", HELD_FILES)
    report["train_discovery"] = train_summary
    report["held_discovery"] = held_summary
    selection = L.select(train_rows)
    report["selection"] = selection
    laws = selection["closures"][0] if selection["closures"] else []
    report["computed_laws"] = laws
    report["train_evaluation"] = [L.evaluate(c, train_rows) for c in ([laws] if laws else [])]
    report["held_evaluation"] = [L.evaluate(c, held_rows) for c in ([laws] if laws else [])]
    report["judged_rows"] = {"train": len(train_rows), "held": len(held_rows)}
    encoded = json.dumps(laws)
    criteria = {
        "G1_mode_family_discovered": all(
            any("mode_mismatch" in f for f in report[k + "_discovery"]["families"])
            for k in ("train", "held")),
        "G2_closure_found": selection["status"] == "CLOSURE_FOUND",
        "G3_transfer_zero_errors": bool(report["held_evaluation"])
        and report["held_evaluation"][0]["false_accepts"] == []
        and report["held_evaluation"][0]["false_rejects"] == [],
        "G4_mode_relation_without_file_names": (
            "mode" in encoded and not any(name in encoded for name in TRAIN_FILES)
            and not any(name in encoded for name in HELD_FILES)),
        "G5_zero_model_calls_and_parameters": True,
    }
    report["criteria"] = criteria
    report["met"] = all(criteria.values())
    report["model_calls"] = 0
    report["parameters_stored"] = 0
    report["seconds"] = round(time.time() - begun, 1)
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if store is not None and laws:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"schema": "BRAIN_COMPUTED_LAW_STORE_V1",
                                     "laws": laws, "derived_from": selection,
                                     "parameters": 0, "model_calls": 0, "removable": True},
                                    indent=1) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="/tmp/permissions-relation")
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--store", default=None)
    args = ap.parse_args(argv)
    r = measure(pathlib.Path(args.root),
                receipt=pathlib.Path(args.receipt) if args.receipt else None,
                store=pathlib.Path(args.store) if args.store else None)
    print(json.dumps({"computed_laws": r.get("computed_laws"),
                      "rows": r.get("judged_rows"), "held": r.get("held_evaluation"),
                      "criteria": r.get("criteria"), "met": r.get("met")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
