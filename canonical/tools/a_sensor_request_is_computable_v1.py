#!/usr/bin/env python3
"""A missing sensor cannot be invented from the old view, but its request can be computed.

WHY THIS ROUND EXISTS
---------------------
`WHAT_A_REFUSAL_BUYS_20261116_V1.md` measured five real actions and found one boundary:

    mkdir newdir -> BEYOND_THIS_OBSERVABLE
    effect on disk = true; every admissible view from the content reader = empty
    "unblocking it needs an observation that reports path kind ... an interface change"

The project stopped at naming the sensor. That is correct as an epistemology claim -- no predicate
built from the same readings can reach the effect -- but incomplete as an engineering claim: the
refusal knows the effect happened, so it can ask for the *smallest* new field that makes the effect
testable, then verify that the field closes the hole. This round measures that missing step.

WHAT IS BUILT
-------------
1. OLD READER: regular contents only, exactly the view that called `mkdir` unlearnable.
2. SENSOR BANK: every `st_*` field that the OS itself reports on `os.stat_result`, discovered at
   run time. No field is chosen because a human knows what a directory is.
3. REQUEST: from ONE positive execution, repeated only to decide whether a field is stable, choose
   the field/value relation with the fewest false fires on real control actions. The request names a
   raw field, never a path, action, goal or task word.
4. CLOSURE: after widening the reader with that field, the same computation decides unseen actions
   in a different tree with different names, counts, modes and action arguments.
5. ABLATION: the tempting shortcut "a new path appeared" is measured separately; if it fires on
   file creation or a symlink, the field-value part of the closure is load-bearing, not decoration.

This does NOT retract the older law. A sensor is not grown from the old readings; it is requested
from a sensor bank outside them, and the request is accepted only by execution. No model, no
parameters, no benchmark score, no GUI/browser claim, no independent verification.

Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_A_SENSOR_REQUEST_IS_COMPUTABLE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
ABSENT = "ABSENT"
FIELDS = tuple(sorted(name for name in dir(os.stat_result) if name.startswith("st_")))

TRAIN_FILES = {"payload.dat": (b"alpha\n", 0o644), "notes.md": (b"beta\n", 0o600)}
HELD_FILES = {"x.dat": (b"ex\n", 0o600), "y.ini": (b"why\n", 0o644),
              "z.log": (b"zed\n", 0o640), "q.txt": (b"cue\n", 0o644)}

COMMANDS: dict[str, tuple[str, ...]] = {
    "noop": (),
    "mkdir": ("mkdir", "new_directory"),
    "mkdir_p": ("mkdir", "-p", "fresh_parent/fresh_child"),
    "touch": ("touch", "fresh.txt"),
    "write_file": ("sh", "-c", "printf 'written\\n' > made.txt"),
    "symlink": ("sh", "-c", "ln -s payload.dat link.dat 2>/dev/null || ln -s x.dat link.dat"),
    "chmod": ("sh", "-c", "chmod 700 payload.dat 2>/dev/null || chmod 700 x.dat"),
    "rmdir": ("sh", "-c", "mkdir gone_dir && rmdir gone_dir"),
}
POSITIVE = ("mkdir", "mkdir_p")
CONTROLS = ("touch", "write_file", "symlink", "chmod", "rmdir", "noop")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def build(root: pathlib.Path, files: Mapping[str, tuple[bytes, int]]) -> pathlib.Path:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name, (data, mode) in files.items():
        item = root / name
        item.write_bytes(data)
        item.chmod(mode)
    return root


@dataclass(frozen=True)
class Observation:
    """A real state, read twice: once by the old blind reader, once by the sensor bank."""

    old: dict[str, str]
    fields: dict[tuple[str, str], Any]
    paths: dict[str, bool]

    def field(self, path: str, name: str) -> Any:
        return self.fields.get((path, name), ABSENT)


def observe(root: pathlib.Path) -> Observation:
    old: dict[str, str] = {}
    fields: dict[tuple[str, str], Any] = {}
    paths: dict[str, bool] = {}
    for item in sorted(root.rglob("*")):
        rel = item.relative_to(root).as_posix()
        paths[rel] = True
        try:
            info = item.lstat()
        except OSError:
            continue
        for name in FIELDS:
            fields[(rel, name)] = getattr(info, name)
        if item.is_file():
            old[rel] = digest(item.read_bytes())
    return Observation(old=old, fields=fields, paths=paths)


def run_action(base: pathlib.Path, workspace: pathlib.Path, name: str) -> dict[str, Any]:
    """Execute a real binary on a fresh copy; the only source of truth is the machine."""
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(base, workspace, copy_function=shutil.copy2)
    before = observe(workspace)
    command = COMMANDS[name]
    if not command:
        return {"name": name, "returncode": 0, "before": before,
                "after": observe(workspace), "argv": []}
    done = subprocess.run(command, cwd=str(workspace), capture_output=True, timeout=20)
    return {"name": name, "returncode": done.returncode, "before": before,
            "after": observe(workspace), "argv": list(command),
            "cwd": str(workspace)}


def new_paths(before: Observation, after: Observation) -> list[str]:
    return sorted(path for path in after.paths if path not in before.paths)


def old_sees_change(row: Mapping[str, Any]) -> bool:
    return row["before"].old != row["after"].old


def fires(predicate: Mapping[str, Any], before: Observation, after: Observation) -> bool:
    created = new_paths(before, after)
    if not created:
        return False
    if predicate["kind"] == "new_path":
        return True
    if predicate["kind"] == "new_path_field_value":
        return any(after.field(path, predicate["field"]) == predicate["value"]
                   for path in created)
    raise ValueError("unknown predicate kind")


def candidates_from_demo(demo: Mapping[str, Any], repeat: Mapping[str, Any],
                         controls: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One positive experience; the repeat only decides field stability, never selection."""
    created = new_paths(demo["before"], demo["after"])
    repeated = new_paths(repeat["before"], repeat["after"])
    stable: list[dict[str, Any]] = []
    unstable: list[str] = []
    for field in FIELDS:
        values = [demo["after"].field(path, field) for path in created]
        second = [repeat["after"].field(path, field) for path in repeated]
        if values and values == second and all(value != ABSENT for value in values):
            stable.append({"kind": "new_path_field_value",
                           "field": field, "value": values[0]})
        else:
            unstable.append(field)
    scored = []
    for predicate in stable:
        false_fires = [row["name"] for row in controls if fires(predicate, row["before"], row["after"])]
        scored.append((len(false_fires), predicate["field"], predicate, false_fires))
    scored.sort(key=lambda item: (item[0], item[1]))
    best = scored[0][0] if scored else None
    tied = sorted(item[1] for item in scored if item[0] == best)
    return [item[2] for item in scored], {
        "positive_executions": 1,
        "stability_repeats": 1,
        "control_actions": list(CONTROLS),
        "unstable_fields": unstable,
        "minimal_false_fires": best,
        "minimal_tie_fields": tied,
        "tie_break": "alphabetical field order; ties are reported, not hidden",
        "scored": [{"field": item[1], "false_fires": item[3]} for item in scored],
    }


def evaluate(predicate: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    hits, false_accepts, false_rejects = [], [], []
    for row in rows:
        fired = fires(predicate, row["before"], row["after"])
        expected = row["name"] in POSITIVE
        if fired:
            hits.append(row["name"])
        if fired and not expected:
            false_accepts.append(row["name"])
        if expected and not fired:
            false_rejects.append(row["name"])
    return {"rows": len(rows), "hits": hits,
            "false_accepts": false_accepts, "false_rejects": false_rejects}


def _run_tree(root: pathlib.Path, files: Mapping[str, tuple[bytes, int]], label: str) -> dict[str, Any]:
    base = build(root / f"{label}-base", files)
    rows = {name: run_action(base, root / f"{label}-{name}", name) for name in COMMANDS}
    return {"base": base, "rows": rows}


def measure(root: pathlib.Path, *, receipt: pathlib.Path | None = None,
            store: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    train = _run_tree(root, TRAIN_FILES, "train")
    held = _run_tree(root, HELD_FILES, "held")
    train_rows = list(train["rows"].values())
    held_rows = list(held["rows"].values())

    demo, repeat = train["rows"]["mkdir"], run_action(train["base"], root / "train-repeat", "mkdir")
    controls = [train["rows"][name] for name in CONTROLS]
    pool, diagnostics = candidates_from_demo(demo, repeat, controls)
    selected = pool[0] if pool else None
    naive = {"kind": "new_path"}
    naive_train = evaluate(naive, train_rows)
    naive_held = evaluate(naive, held_rows)
    selected_train = evaluate(selected, train_rows) if selected else None
    selected_held = evaluate(selected, held_rows) if selected else None
    encoded = json.dumps(selected or {})

    criteria = {
        "H1_old_reader_blind_to_mkdir": all(
            not old_sees_change(tree["rows"]["mkdir"]) and
            not old_sees_change(tree["rows"]["mkdir_p"]) for tree in (train, held)),
        "H2_effect_real_on_disk": all(
            any(row["name"] == "mkdir" and row["returncode"] == 0
                and "new_directory" in new_paths(row["before"], row["after"])
                and (pathlib.Path(row["cwd"]) / "new_directory").is_dir()
                for row in tree["rows"].values()) for tree in (train, held)),
        "H3_request_computed_from_one_positive": selected is not None
        and selected["field"] in FIELDS
        and not any(name in encoded for name in TRAIN_FILES)
        and not any(name in encoded for name in HELD_FILES),
        "H4_closure_zero_errors": bool(selected_train and selected_held)
        and selected_train["false_accepts"] == [] and selected_train["false_rejects"] == []
        and selected_held["false_accepts"] == [] and selected_held["false_rejects"] == [],
        "H5_naive_new_path_ablation_loses": bool(naive_train["false_accepts"])
        and bool(naive_held["false_accepts"]),
        "H6_zero_model_calls_and_parameters": True,
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "claim": "A sensor missing from the old view is requested from an OS-derived field bank; "
                 "the widened reader closes the hole on a different tree without path names or "
                 "hand-written kind predicates.",
        "declared_before_the_run": [
            "H1 the content-only reader sees no mkdir/mkdir_p change in either tree",
            "H2 the mkdir effect is real on disk",
            "H3 one positive execution selects a request from dynamically discovered stat fields",
            "H4 the selected field/value relation has zero errors on both trees",
            "H5 'a new path appeared' alone has false accepts",
            "H6 zero model calls and zero stored parameters",
        ],
        "limits": ["a real filesystem with a supplied action bank and depth-one mutations",
                   "interface widening is requested, not grown from the old readings",
                   "no GUI, browser, benchmark score or independent verification"],
        "sensor_bank_fields": list(FIELDS),
        "selection_diagnostics": diagnostics,
        "sensor_request": selected,
        "naive_train": naive_train,
        "naive_held": naive_held,
        "selected_train": selected_train,
        "selected_held": selected_held,
        "criteria": criteria,
        "met": all(criteria.values()),
        "model_calls": 0,
        "parameters_stored": 0,
        "seconds": round(time.time() - begun, 1),
    }
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if store is not None and selected is not None:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"schema": "BRAIN_SENSOR_REQUEST_STORE_V1",
                                     "request": {"field": selected["field"]},
                                     "learned_relation": selected,
                                     "derived_from": "one positive execution plus stability repeat",
                                     "removable": True, "parameters": 0, "model_calls": 0},
                                    indent=1) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="/tmp/sensor-request")
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--store", default=None)
    args = ap.parse_args(argv)
    report = measure(pathlib.Path(args.root),
                     receipt=pathlib.Path(args.receipt) if args.receipt else None,
                     store=pathlib.Path(args.store) if args.store else None)
    print(json.dumps({"sensor_request": report["sensor_request"],
                      "naive_held": report["naive_held"],
                      "selected_train": report["selected_train"],
                      "selected_held": report["selected_held"],
                      "criteria": report["criteria"], "met": report["met"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
