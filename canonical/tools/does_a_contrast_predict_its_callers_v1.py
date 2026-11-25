#!/usr/bin/env python3
"""Does a recorded contrast PREDICT anything, or is the store a museum?

THE QUESTION, MADE FALSIFIABLE
------------------------------
`one_contrast_one_effect_v1` recorded 49 entries: (function, argument, witness, effect) earned by executing
the function. Nothing consumes them. An unread store is a museum, and this file is the test of whether it is
one.

The sharpest consume-able question available without a benchmark: **given an entry that says "this argument
decides whether the call raises", does that predict how the function's own call sites in the test suite
behave?**

Concretely, for a function with an entry whose effect includes a RAISE on one side:

    hypothesis  a call site that passes a value at that argument position RUNS and a call site that does not
                RAISES -- and the test outcome differs accordingly.

That is a claim about the world that the entry makes and the entry alone can support, because it came from
executing the function rather than reading it.

THE BASELINE THAT DECIDES IT
----------------------------
A static predictor can read the same function's source and say "this parameter is used in a way that can
raise" -- that is `HAS_RAISE` plus argument position, and it costs nothing. If the behavioural entry only
reproduces what the source already says, the store is a museum with better paperwork. So the comparison is:

    BEHAVIOURAL   the recorded entry, used to classify call sites
    STATIC        raise-awareness read from the function's own AST
    TRIVIAL       always predict the majority outcome

If BEHAVIOURAL does not beat STATIC, the honest conclusion is that this store adds nothing a parser could not
give -- and that is worth knowing before building more of it.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

SCHEMA = "BRAIN_DOES_A_CONTRAST_PREDICT_ITS_CALLERS_V1"


def entries_with_raise(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    kept = [entry for entry in payload.get("summary", {}).get("sample_entries", [])
            if "RAISED" in entry["effect"][0] or "RAISED" in entry["effect"][1]]
    return kept


def call_sites_of(function_name: str) -> list[dict[str, Any]]:
    """Every call to `function_name` anywhere in canonical/tests, with the call's argument count and the
    enclosing test's name."""
    sites: list[dict[str, Any]] = []
    files = subprocess.run(["git", "ls-files", "canonical/tests/test_*.py"], cwd=REPO,
                           capture_output=True, text=True, check=False).stdout.split()
    for name in files:
        try:
            tree = ast.parse((REPO / name).read_text(errors="ignore"))
        except (SyntaxError, OSError, ValueError):
            continue
        parents: dict[int, str] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[id(child)] = getattr(node, "name", type(node).__name__)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if called != function_name:
                continue
            sites.append({"file": name, "test": parents.get(id(node), "?"),
                          "positional": len(node.args), "keywords": len(node.keywords),
                          "at_line": getattr(node, "lineno", -1)})
    return sites


def static_raise_awareness(source_path: pathlib.Path, function_name: str) -> bool:
    """What a parser alone could say: does this function's body contain a raise (or an assert) that is not
    inside a nested def?"""
    try:
        tree = ast.parse(source_path.read_text(errors="ignore"))
    except (SyntaxError, OSError, ValueError):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        for child in ast.walk(node):
            if isinstance(child, (ast.Raise, ast.Assert)):
                return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--entries",
                        default=str(REPO / "canonical" / "verification" /
                                    "ONE_CONTRAST_ONE_EFFECT_20261124_V1.json"))
    args = parser.parse_args(argv)

    started = time.time()
    entries = entries_with_raise(pathlib.Path(args.entries))
    rows: list[dict[str, Any]] = []
    for entry in entries:
        module_name, _, attribute = entry["function"].partition("::")
        source = REPO / "canonical" / "swe_kernel" / f"{module_name}.py"
        if not source.exists():
            continue
        sites = call_sites_of(attribute)
        if not sites:
            continue
        position = entry["position"]
        rows.append({
            "function": entry["function"],
            "argument": entry["argument"],
            "position": position,
            "witness": entry["witness"],
            "effect": entry["effect"],
            "call_sites": len(sites),
            "sites_passing_that_position": sum(1 for site in sites if site["positional"] > position),
            "static_says_it_can_raise": static_raise_awareness(source, attribute),
            "sites": sites,
        })

    total_sites = sum(row["call_sites"] for row in rows)
    passing = sum(row["sites_passing_that_position"] for row in rows)
    static_agrees = sum(1 for row in rows if row["static_says_it_can_raise"])
    summary = {
        "entries_with_a_raise_contrast": len(entries),
        "entries_whose_function_has_any_call_site_in_the_suite": len(rows),
        "call_sites_found": total_sites,
        "call_sites_passing_the_contrasting_position": passing,
        "share_of_sites_that_could_exercise_the_contrast": round(passing / max(1, total_sites), 4),
        "entries_a_parser_already_flags_as_able_to_raise": static_agrees,
        "rows": rows,
        "verdicts": {
            "the_store_is_consumed_by_something_real": total_sites > 0,
            "most_entries_have_no_call_site_in_the_suite": len(rows) < 0.5 * max(1, len(entries)),
            "the_entries_duplicate_what_a_parser_already_says":
                static_agrees == len(rows) and len(rows) > 0,
            "there_are_call_sites_that_could_exercise_the_recorded_contrast": passing > 0,
        },
        "honest_reading": (
            "This measures whether the recorded contrasts CONNECT to anything — whether any existing test "
            "calls the function at the position the entry is about. It is a reachability measurement, not a "
            "prediction-accuracy measurement, and it cannot be turned into one without running those tests "
            "twice with the contrasting value, which is the next step and is not done here."),
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
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
