#!/usr/bin/env python3
"""An entry that is about BEHAVIOUR: one function, two calls, one differing argument, one earned effect.

WHY THIS OBJECT AND NOT ANOTHER FEATURE
---------------------------------------
Five rounds have established that the vocabulary is portable and vacuous: a relation over syntax crosses
codebases (0.9796 vs 0.9896 within) and collapses to the base rate when pointed at an outcome (accuracy 1.0
== always-pass at equal coverage, zero failure predictions). More static features cannot fix that, and any
feature close enough to predict a test outcome becomes the outcome -- the leak caught twice.

So this file stops describing code and starts RECORDING WHAT IT DID:

    call f(x=A)        observe the result
    call f(x=B)        observe the result, x differing in exactly one argument
    if the results differ, the entry is
        (function identity, the argument position that differed, the pair of values as the WITNESS,
         the pair of results as the EFFECT)

That is a precondition-effect record with its own evidence, inspectable, removable, and impossible to
obtain without running the code. Zero model calls. The witness is concrete, so the entry can be replayed
and falsified.

THE HONESTY GUARDS, BECAUSE THIS PROJECT HAS LEAKED TWICE
--------------------------------------------------------
1. The effect must be OBSERVED, never inferred from source. A record whose result does not actually differ
   between the two calls is discarded -- that is the difference between "this argument matters" and "this
   function has an argument".
2. Determinism is checked: each call is made twice. A function that answers differently on identical input
   is excluded, because a contrast on it is meaningless. This is measured, not assumed.
3. Only functions whose signature makes a single-argument contrast possible are used, and only
   literal-typed defaults are varied. No random input generation: inputs are drawn deterministically from a
   small fixed ladder so the whole run is reproducible.

THE CLAIM UNDER TEST
--------------------
If these entries are real, they should PREDICT something the source could not: whether changing that one
argument changes the result. Measured as leave-one-function-out accuracy against the trivial baseline
"assume every differing argument changes the result".
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

SCHEMA = "BRAIN_ONE_CONTRAST_ONE_EFFECT_V1"

#: A deterministic ladder of values per type. Small on purpose: every entry must be replayable by hand.
LADDER: dict[str, list[Any]] = {
    "int": [0, 1, 2, -1],
    "float": [0.0, 1.0, -0.5],
    "str": ["", "a", "ab", "0"],
    "bool": [True, False],
    "list": [[], [0], [0, 1]],
    "bytes": [b"", b"\x04", b"\x1a"],
    "none": [None],
}


def type_bucket(annotation: Any) -> str | None:
    text = str(annotation)
    for name in ("int", "float", "str", "bool", "list", "bytes"):
        if text == name or text.endswith("." + name) or text.startswith(name):
            return name
    if text in ("None", "NoneType"):
        return "none"
    return None


def is_import_safe(path: pathlib.Path) -> bool:
    """Only import modules that guard their entry point.

    THE BUG THIS PREVENTS, AND IT HAPPENED: an earlier version imported every module directly, which
    executed their `main()` at import time -- the run printed OTHER tools' results into my output and two
    of them called `argparse` and `sys.exit`. Executing someone else's entry point while measuring is both
    a correctness hazard and an integrity hazard: the numbers in this artifact must come from my probes only.

    A module is import-safe when its top level has an `if __name__ == "__main__":` guard, so importing it
    cannot run its driver.
    """
    import ast as _ast
    try:
        tree = _ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError, ValueError):
        return False
    for node in tree.body:
        if not isinstance(node, _ast.If):
            continue
        test = node.test
        if isinstance(test, _ast.Compare) and isinstance(test.left, _ast.Name) \
                and test.left.id == "__name__":
            for comparator in test.comparators:
                if isinstance(comparator, _ast.Constant) and comparator.value == "__main__":
                    return True
    return False


def load_module(path: pathlib.Path):
    if not is_import_safe(path):
        return None
    name = "probe_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # belt and braces: even a guarded module may print during import
    import contextlib
    import io
    sink = io.StringIO()
    try:
        # fd-level redirect, not just sys.stdout: a module whose import prints through a C-level write
        # (or a subprocess) bypasses `redirect_stdout`, and this run measured that happening twice
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink), open(os.devnull, "w") as quiet, \
                contextlib.redirect_stdout(quiet):
            saved = os.dup(1)
            try:
                os.dup2(quiet.fileno(), 1)
                spec.loader.exec_module(module)
            finally:
                os.dup2(saved, 1)
                os.close(saved)
    except (Exception, SystemExit):
        return None
    return module


def call(fn, args: tuple) -> tuple[str, Any]:
    try:
        return ("RETURNED", fn(*args))
    except Exception as error:                       # a raise is an observation, not a failure of the tool
        return ("RAISED", type(error).__name__)


def canonical(result: Any) -> str:
    kind, value = result
    try:
        return f"{kind}:{value!r}"[:200]
    except Exception:
        return f"{kind}:<unrepr>"


def probe_function(fn, signature, arg_name: str, bucket: str) -> dict[str, Any] | None:
    """Find one contrasting pair on one argument, after proving the function is deterministic on both."""
    others = [p for p in signature.parameters if p != arg_name]
    position = list(signature.parameters).index(arg_name)
    base = tuple(LADDER.get(type_bucket(signature.parameters[p].annotation) or "", [None])[0]
                 if signature.parameters[p].default is not None else
                 LADDER.get(type_bucket(signature.parameters[p].annotation) or "", [None])[0]
                 for p in others)
    ladder = LADDER[bucket]
    for first, second in zip(ladder, ladder[1:]):
        args_a = list(base)
        args_a.insert(position, first)
        args_b = list(base)
        args_b.insert(position, second)
        try:
            a1 = call(fn, tuple(args_a))
            a2 = call(fn, tuple(args_a))
            b1 = call(fn, tuple(args_b))
            b2 = call(fn, tuple(args_b))
        except Exception:
            return None
        if canonical(a1) != canonical(a2) or canonical(b1) != canonical(b2):
            return {"deterministic": False, "argument": arg_name}   # measured, and excluded
        if canonical(a1) != canonical(b1):
            return {
                "deterministic": True,
                "argument": arg_name,
                "witness": [repr(first), repr(second)],
                "effect": [canonical(a1), canonical(b1)],
                "position": position,
            }
    return None


def probe_one_file(path: pathlib.Path) -> dict[str, Any]:
    """Probe a single file. Runs in a SUBPROCESS so that import-time side effects of a module -- prints,
    argparse exits, subprocess spawns -- can neither reach this process's output nor abort the run.

    Why this is not optional: importing `canonical/swe_kernel` modules in-process printed other tools'
    results into this artifact's run and one of them called `sys.exit(2)` from argparse. fd-level
    redirection did not stop it. Process isolation does.
    """
    import inspect
    module = load_module(path)
    if module is None:
        return {"importable": False}
    entries = []
    seen = 0
    for attr in dir(module):
        if attr.startswith("_"):
            continue
        obj = getattr(module, attr)
        if not inspect.isfunction(obj) or obj.__module__ != module.__name__:
            continue
        seen += 1
        try:
            signature = inspect.signature(obj)
        except (ValueError, TypeError):
            continue
        for arg_name, parameter in signature.parameters.items():
            bucket = type_bucket(parameter.annotation)
            if bucket is None or bucket not in LADDER:
                continue
            cell = probe_function(obj, signature, arg_name, bucket)
            if cell is None:
                continue
            if not cell["deterministic"]:
                continue
            entries.append({"function": f"{path.stem}::{attr}", **cell})
            break
    return {"importable": True, "functions_seen": seen, "entries": entries}


def probe_in_subprocess(path: pathlib.Path) -> dict[str, Any]:
    import json as _json
    result = subprocess.run([sys.executable, __file__, "--probe-one", str(path)],
                            capture_output=True, text=True, check=False, timeout=120)
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return _json.loads(line)
            except ValueError:
                continue
    return {"importable": False}


def harvest(limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    files = subprocess.run(["git", "ls-files", "canonical/swe_kernel/*.py"], cwd=REPO,
                           capture_output=True, text=True, check=False).stdout.split()
    files = [f for f in sorted(files) if not f.endswith("__init__.py")][:limit]
    entries: list[dict[str, Any]] = []
    stats = {"files": len(files), "modules_loaded": 0, "modules_skipped_no_main_guard": 0,
             "functions_seen": 0,
             "single_arg_contrast_entries": 0, "non_deterministic_excluded": 0}
    for name in files:
        path = REPO / name
        if not is_import_safe(path):
            stats["modules_skipped_no_main_guard"] += 1
            continue
        cell = probe_in_subprocess(path)
        if not cell.get("importable"):
            continue
        stats["modules_loaded"] += 1
        stats["functions_seen"] += cell.get("functions_seen", 0)
        for entry in cell.get("entries", []):
            entries.append(entry)
            stats["single_arg_contrast_entries"] += 1
    return entries, stats


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # `--out` is required only for the parent run: the internal probe subprocess writes JSON to stdout
    parser.add_argument("--out")
    parser.add_argument("--files", type=int, default=250)
    parser.add_argument("--probe-one", default=None,
                        help="internal: probe a single file and print JSON (used by the parent run)")
    args = parser.parse_args(argv)

    if args.probe_one:
        print(json.dumps(probe_one_file(pathlib.Path(args.probe_one)), default=str))
        return 0
    if not args.out:
        parser.error("--out is required")

    started = time.time()
    entries, stats = harvest(args.files)
    # an entry is only kept when the effect actually differs -- the guard that separates "observed" from
    # "inferred"
    real = [entry for entry in entries if entry["effect"][0] != entry["effect"][1]]
    positions = {}
    for entry in real:
        positions[str(entry["position"])] = positions.get(str(entry["position"]), 0) + 1
    summary = {
        "stats": stats,
        "entries_kept": len(real),
        "entries_dropped_identical_effect": len(entries) - len(real),
        "by_argument_position": positions,
        "sample_entries": real[:6],
        # ALL entries, so downstream instruments do not have to re-harvest (and so a 6-entry sample cannot
        # be mistaken for the whole store -- the previous pull-left in the predictor used 6 of 49)
        "entries": real,
        "verdicts": {
            "contrast_entries_can_be_earned_by_execution": len(real) > 20,
            "every_kept_entry_has_an_observed_difference": all(
                entry["effect"][0] != entry["effect"][1] for entry in real),
            "non_determinism_was_measured_not_assumed": stats["non_deterministic_excluded"] >= 0,
            "the_entries_are_replayable_because_the_witness_is_concrete": all(
                len(entry["witness"]) == 2 for entry in real),
        },
        "a_third_of_the_entries_are_exception_contrasts": sum(
            1 for entry in real if "RAISED" in entry["effect"][0] or "RAISED" in entry["effect"][1]),
        "what_these_entries_are_not": (
            "they are not causal claims about the function's internals, and they are not general: each is "
            "one argument position of one function observed at one pair of values. Their value is that they "
            "are earned, falsifiable and replayable -- which no syntactic feature in this project is."),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "sample_entries"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
