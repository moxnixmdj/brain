#!/usr/bin/env python3
"""Does knowledge earned on one function transfer to a function nobody showed you?

THE CLAIM UNDER TEST
--------------------
§6 needs single-experience transfer: learn from one experience, apply it to an unseen environment. V27 proved
an earned contrast BINDS to real outcomes. V28 proved a contrast cannot PREDICT by shape. So the only transfer
worth testing is the one that does not go through shape at all:

    if two functions in different modules agree on what a contrast does, the effect is a property of a
    FAMILY of code and can be carried across modules.
    if they do not agree more than chance, the effect is idiosyncratic to the function and single-experience
    transfer cannot exist for this kind of knowledge.

METHOD -- and why the null is the whole experiment
-------------------------------------------------
1. Pick ONE witness pair. Probe every function of arity >= 1 in a module with it, in a subprocess, and record
   the effect kind: RAISED, VALUE, or NONE.
2. For every pair of functions in DIFFERENT modules, ask whether they agree.
3. Compare the observed agreement with the same calculation after permuting the labels within each module.

Step 3 is the entire experiment. Cross-module agreement has a structural floor: most functions return a value
and never raise, so agreement will be high no matter what. Only the gap over the permuted null says whether
the agreement carries information about WHICH function it is.

This is the same instrument correction as V28, applied before the fact instead of after: no accuracy number
is reported without the number it would have had by chance.
"""
from __future__ import annotations

import argparse
import inspect
import itertools
import json
import pathlib
import random
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import one_contrast_one_effect_v1 as contrast  # noqa: E402

SCHEMA = "BRAIN_TRANSFER_EARNED_CONTRAST_V1"
WITNESS = ("", "a")          # the pair V26 found most informative: empty string against one character


def probe_file_with_witness(path: pathlib.Path, position: int = 0) -> dict[str, Any]:
    """Call every function of arity > position with FIRST and with SECOND, record the effect kind.

    WHY position 0 ONLY. Probing every position would multiply the run and, worse, would let a function be
    labelled by whichever argument happened to contrast -- a search that finds a difference somewhere is not
    a transferable fact. Fixing the position is the semantically honest choice: "the first argument" is a
    property of the function's interface, not of our search.
    """
    # A `__main__` guard does NOT protect against MODULE-LEVEL argparse. `causal_dependency_repair_v1`
    # builds an ArgumentParser at import time; it read this process's argv, saw the module path and the
    # witness value, printed its usage and called exit(2) -- killing the probe while passing is_import_safe.
    # Measured, not theorised. Blanking argv for the duration of the import is the smallest fix that keeps
    # the module's behaviour while removing this process's arguments from its view.
    saved_argv = sys.argv[:]
    sys.argv = [path.name]
    try:
        module = contrast.load_module(path)
    finally:
        sys.argv = saved_argv
    if module is None:
        return {"importable": False, "functions": []}
    rows = []
    for attr in dir(module):
        if attr.startswith("_"):
            continue
        obj = getattr(module, attr)
        if not inspect.isfunction(obj) or obj.__module__ != module.__name__:
            continue
        if attr == "main":
            continue                                   # an entry point parses argv; it is not behaviour
        try:
            parameters = list(inspect.signature(obj).parameters.values())
        except (ValueError, TypeError):
            continue
        required = [p for p in parameters if p.default is inspect.Parameter.empty]
        if len(parameters) <= position or parameters[position].kind in (
                inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if required and parameters[0].default is inspect.Parameter.empty and position == 0:
            pass                                    # the witness IS the first argument
        # Fill the OTHER arguments from the repo's own annotation ladder. Holding them at None measured
        # which functions crash on None, not what the witness contrast does -- the first run of this file
        # produced labels like "AttributeError vs AttributeError" for that reason and carried no signal.
        args = []
        for index, parameter in enumerate(parameters):
            if index == position:
                args.append(WITNESS[0])
                continue
            bucket = contrast.type_bucket(parameter.annotation)
            ladder = contrast.LADDER.get(bucket or "", [None])
            args.append(ladder[0])
        outs = {}
        for label, value in (("first", WITNESS[0]), ("second", WITNESS[1])):
            probe_args = list(args)
            probe_args[position] = value
            # SystemExit is a BaseException, so `contrast.call` (which catches Exception) lets argparse's
            # exit(2) ESCAPE the probe. Measured on `causal_dependency_repair_v1::main`, whose first
            # argument is an argv list: passing "" made argparse parse the empty string as an argument
            # vector and kill the whole run. A probe must observe an exit, not die of one.
            try:
                outs[label] = contrast.canonical(contrast.call(obj, tuple(probe_args)))
            except BaseException as escape:            # noqa: BLE001 -- deliberate, see above
                outs[label] = f"EXITED:{type(escape).__name__}"
        if outs["first"] == outs["second"]:
            kind = "NONE"
            effect = outs["first"]
        elif any(value.startswith("EXITED") for value in outs.values()):
            kind = "EXITED"
            effect = f"{outs['first']} -> {outs['second']}"
        elif outs["first"].startswith("RAISED") != outs["second"].startswith("RAISED"):
            kind = "RAISED"
            effect = f"{outs['first']} -> {outs['second']}"
        else:
            kind = "VALUE"
            effect = f"{outs['first']} -> {outs['second']}"
        rows.append({"name": attr, "kind": kind, "effect": effect[:200],
                     "arity": len(parameters)})
    return {"importable": True, "functions": rows}


def probe_module(module_name: str, source: pathlib.Path) -> list[dict[str, Any]]:
    """Run the witness probe in a SUBPROCESS (import-time side effects must not reach this process)."""
    result = subprocess.run([sys.executable, __file__, "--probe-witness", str(source)],
                            capture_output=True, text=True, check=False, timeout=180)
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            return [{"module": module_name, **row} for row in record.get("functions", [])]
    return []


def agreement(pairs) -> float:
    if not pairs:
        return 0.0
    return sum(1 for a, b in pairs if a == b) / len(pairs)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    parser.add_argument("--all-safe", action="store_true",
                        help="probe every import-safe module (the full population this instrument can see)")
    parser.add_argument("--modules", default="",
                        help="comma-separated swe_kernel module names; default = the 12 largest by size")
    parser.add_argument("--shuffles", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261124)
    parser.add_argument("--probe-witness", default=None,
                        help="internal: probe one file with the fixed witness and print JSON")
    args = parser.parse_args(argv)
    if args.probe_witness:
        print(json.dumps(probe_file_with_witness(pathlib.Path(args.probe_witness))))
        return 0
    if not args.out:
        parser.error("--out is required unless --probe-witness is given")
    started = time.time()

    kernel = REPO / "canonical" / "swe_kernel"
    if args.all_safe:
        names = [path.stem for path in sorted(kernel.glob("*.py"))
                 if path.stem != "__init__" and contrast.is_import_safe(path)]
    elif args.modules:
        names = [name.strip() for name in args.modules.split(",") if name.strip()]
    else:
        # The population is IMPORT-SAFE modules only. The first selection took the 12 largest files by size
        # and every one of them was refused for lacking a __main__ guard -- the V26 isolation rule doing its
        # job, but it also means "the biggest modules" is not a population this instrument can measure.
        # 71 of 134 modules are import-safe; 12 spread evenly across them, not the 12 largest. Taking the
        # largest repeatedly selected files that are all refused, which silently shrank the population to
        # one module and produced a "verdict" from a sample of one.
        candidates = [path for path in sorted(kernel.glob("*.py"))
                      if path.stem != "__init__" and contrast.is_import_safe(path)]
        step = max(1, len(candidates) // 12)
        names = [path.stem for path in candidates[::step]][:12]

    per_module: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        source = kernel / f"{name}.py"
        if not source.exists():
            continue
        rows = probe_module(name, source)
        if rows:
            per_module[name] = rows

    labels = {name: [row["kind"] for row in rows] for name, rows in per_module.items()}
    modules = sorted(labels)

    # observed: every cross-module function pair sharing the same arity-agnostic index position
    observed_pairs = []
    for left, right in itertools.combinations(modules, 2):
        for a, b in zip(labels[left], labels[right]):
            observed_pairs.append((a, b))
    observed = agreement(observed_pairs)

    # null: permute labels WITHIN each module, so the module's own label mix is preserved and only the
    # association between a label and the function that produced it is destroyed
    rng = random.Random(args.seed)
    nulls = []
    for _ in range(args.shuffles):
        shuffled = {name: rng.sample(values, len(values)) for name, values in labels.items()}
        pairs = []
        for left, right in itertools.combinations(modules, 2):
            for a, b in zip(shuffled[left], shuffled[right]):
                pairs.append((a, b))
        nulls.append(agreement(pairs))
    null_mean = sum(nulls) / max(1, len(nulls))
    null_sd = (sum((value - null_mean) ** 2 for value in nulls) / max(1, len(nulls))) ** 0.5

    raised = sum(1 for values in labels.values() for kind in values if kind == "RAISED")
    total = sum(len(values) for values in labels.values())
    z = (observed - null_mean) / null_sd if null_sd else 0.0

    summary = {
        "witness_pair": list(WITNESS),
        "modules_probed": len(modules),
        "functions_labelled": total,
        "raised_rate": round(raised / max(1, total), 4),
        "cross_module_pairs": len(observed_pairs),
        "observed_agreement": round(observed, 4),
        "null_agreement_mean": round(null_mean, 4),
        "null_agreement_sd": round(null_sd, 4),
        "gap_over_null": round(observed - null_mean, 4),
        "gap_in_null_sds": round(z, 2),
        "sensitivity_to_the_rare_class": round(
            (observed - null_mean) * len(observed_pairs) / max(1, raised) if raised else 0.0, 4),
        "per_module": {name: {"functions": len(values),
                              "raised": sum(1 for kind in values if kind == "RAISED")}
                       for name, values in labels.items()},
        "verdicts": {
            "agreement_is_above_chance": z > 3.0,
            "the_effect_is_idiosyncratic_to_the_function": z <= 3.0,
            "there_is_enough_rare_class_to_measure": raised >= 10,
        },
        "reading": (
            "Cross-module agreement about what a contrast does is compared with the same measurement after "
            "permuting labels within each module. If the gap over the null is small, then knowing what a "
            "contrast did to one function tells you almost nothing about another -- which is the death of "
            "single-experience transfer for this knowledge, and the reason to stop building on it."),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_function": per_module,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_module"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
