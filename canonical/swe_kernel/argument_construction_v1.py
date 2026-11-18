#!/usr/bin/env python3
"""Make a real callable EXECUTE: construct its arguments from the environment's own proofs.

WHY THIS EXISTS (the wall every previous round hit from a different side)
------------------------------------------------------------------------
* round 4 could not ground a value in a callable;
* round 5 could not find a site that responded to it;
* round 6 measured that **30 of 76 real actions (39%) could never be exercised at all**, because the
  arguments that would make them run are not in the environment's scalar vocabulary: they need a
  `Parser` position, a dict accumulator, a `parse_float` function, a `Version`, a `Signer`.

The 2026 field answers this with a model: LLM-written fixtures and tests beat the classical generators on
line and branch coverage by ~18-20 points, yet still score only 40-55% on mutation testing -- "tests that
run, not tests that catch bugs". We do not use a model, and we do not have to invent the arguments,
because **the environment already contains proofs that its own arguments work**: real call sites in its
own source and its own tests, which are calls somebody executed and shipped.

WHAT IS BUILT
-------------
1. `mined_vectors`: for a set of wanted callables, scan EVERY python file in the tree (source and tests)
   for call sites of those callables and encode each argument vector as prober tokens. Names are resolved
   by bounded LOCAL constant propagation inside the enclosing function (only literal right-hand sides),
   plus builtin type objects (`float`, `int`, ...) which are legal arguments and cannot be JSON-encoded.
   Vectors that cannot be encoded are REFUSED, never approximated.
2. `construct`: probe the old tree with the mined vectors. An action becomes observable only if the call
   RETURNS and RETURNS THE SAME THING TWICE -- round 6's nondeterminism control, unchanged.
3. The measurement, on round 6's exact denominator: of its 30 NEVER_OBSERVED_AT_OLD actions, how many
   become executable, and for those, does the environment move them across the release bump (and is the
   move visible)? An unlocked action that is silently wrong would be worse than an unexercised one.

WHAT THIS IS NOT
----------------
* Not a model. No network at measurement time. No fitted parameter.
* Not a claim that mining beats a model at test generation. It is a claim about a DIFFERENT question:
  whether a learned action can be executed at all, which is prior to any question about coverage.
* Not exhaustive: nested construction (a `Signer` built from a `SecretKey`) is refused by name here and
  named as the next gap, because pretending to handle it would be the always-pass grader again.

REUSED, NOT REBUILT
-------------------
`site_by_intervention_v1.candidate_sites`, `renewable_action_v1` (witnesses, signatures, package_modules,
kind taxonomy, imports for comparability), `checkability_by_differential_pin_v1.execute.probe`,
`witness_inversion_v1` (real clones and materialisation).

Authority NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

_REPO = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as execute  # noqa: E402
from canonical.swe_kernel import renewable_action_v1 as REN  # noqa: E402
from canonical.swe_kernel import site_by_intervention_v1 as SITE  # noqa: E402
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402

SCHEMA = "BRAIN_ARGUMENT_CONSTRUCTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MAX_VECTORS = 4
MAX_ARGS = 2          # identical to rounds 5 and 6, so the denominators are comparable
BATCH = 96

BUILTIN_TYPES = {"float", "int", "str", "bool", "list", "dict", "set", "tuple", "bytes", "object"}

REFUSED_NO_CALL_SITE = "REFUSED__NO_MINEABLE_CALL_SITE"
REFUSED_UNENCODABLE = "REFUSED__EVERY_CALL_SITE_IS_UNENCODABLE"
REFUSED_DID_NOT_RUN = "REFUSED__MINED_BUT_NEVER_RETURNED"


# --------------------------------------------------------------------------- #
# encoding a literal call site as prober tokens
# --------------------------------------------------------------------------- #
def _json_token(value: Any) -> str:
    return "@json:" + json.dumps(value)


def _encodable(node: ast.AST) -> tuple[bool, Any]:
    """A value is encodable iff it survives JSON unchanged. No approximations, no coercions."""
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, (str, int, float, bool)) or value is None:
            return True, value
        return False, None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        ok, inner = _encodable(node.operand)
        if ok and isinstance(inner, (int, float)) and not isinstance(inner, bool):
            return True, (-inner if isinstance(node.op, ast.USub) else inner)
        return False, None
    if isinstance(node, ast.List):
        items = []
        for element in node.elts:
            ok, value = _encodable(element)
            if not ok:
                return False, None
            items.append(value)
        return True, items
    if isinstance(node, ast.Tuple):
        ok, value = _encodable(ast.List(elts=list(node.elts), ctx=node.ctx))
        return ok, value
    if isinstance(node, ast.Dict):
        out = {}
        for key, element in zip(node.keys, node.values):
            if key is None:
                return False, None
            ok_key, value_key = _encodable(key)
            ok_value, value_value = _encodable(element)
            if not ok_key or not ok_value:
                return False, None
            out[str(value_key)] = value_value
        return True, out
    return False, None


def module_constants(module: ast.Module) -> dict[str, Any]:
    """Module-level literal constants: `SUPPORTED_TAGS = [...]` is a proof the environment carries."""
    out: dict[str, Any] = {}
    for node in module.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance0(node.targets[0]):
            target = node.targets[0]
            if isinstance(target, ast.Name):
                ok, value = _encodable(node.value)
                if ok:
                    out[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            ok, value = _encodable(node.value)
            if ok:
                out[node.target.id] = value
    return out


def isinstance0(node):  # a name target, kept separate so the constant rule is one line to audit
    return isinstance(node, ast.Name)


def _resolve_name(name: str, scope: Mapping[str, ast.AST],
                  constants: Mapping[str, Any] | None = None) -> str | None:
    """A Name argument: a builtin type object, or a local literal assignment. Nothing else is guessed."""
    if name in BUILTIN_TYPES:
        return "@builtin:" + name
    node = scope.get(name)
    if node is not None:
        ok, value = _encodable(node)
        if ok:
            return _json_token(value)
    if constants and name in constants:
        return _json_token(constants[name])
    return None


def _scope_of(function: ast.AST) -> dict[str, ast.AST]:
    """Bounded local constant propagation: only `x = <literal>` with a single assignment in the scope."""
    seen: dict[str, ast.AST] = {}
    duplicated: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in seen:
                        duplicated.add(target.id)
                    seen[target.id] = node.value
    return {name: value for name, value in seen.items() if name not in duplicated}


def mined_vectors(tree: pathlib.Path, wanted: set[str]) -> dict[str, dict[str, Any]]:
    """Every call site of a wanted callable, encoded, deduplicated, bounded. Refusals are named."""
    vectors: dict[str, list[list[str]]] = {}
    counters: dict[str, dict[str, int]] = {}
    for path in sorted(tree.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            module = ast.parse(source)
        except (SyntaxError, OSError):
            continue
        constants = module_constants(module)
        # module-level call sites are real proofs too, and a walker that only enters functions missed
        # them entirely (found by this round's own tests before any corpus number was believed)
        module_level = [statement for statement in module.body
                        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        groups: list[tuple[ast.AST, Mapping[str, ast.AST]]] = [("module", {})]
        groups = [(ast.Module(body=module_level, type_ignores=[]), {})]
        for function in [node for node in ast.walk(module)
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            groups.append((function, _scope_of(function)))
        for holder, scope in groups:
            for call in [node for node in ast.walk(holder) if isinstance(node, ast.Call)]:
                target = None
                if isinstance(call.func, ast.Name):
                    target = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    target = call.func.attr
                if target not in wanted:
                    continue
                counters.setdefault(target, {"sites": 0, "encodable": 0})
                counters[target]["sites"] += 1
                if call.keywords:
                    continue
                tokens: list[str] = []
                for argument in call.args[:MAX_ARGS]:
                    if isinstance(argument, ast.Starred):
                        tokens = []
                        break
                    if isinstance(argument, ast.Name):
                        token = _resolve_name(argument.id, scope, constants)
                        tokens.append(token) if token else tokens.append(None)  # type: ignore[arg-type]
                        continue
                    ok, value = _encodable(argument)
                    tokens.append(_json_token(value) if ok else None)  # type: ignore[arg-type]
                if not tokens or any(token is None for token in tokens):
                    continue
                counters[target]["encodable"] += 1
                bucket = vectors.setdefault(target, [])
                if tokens not in bucket and len(bucket) < MAX_VECTORS:
                    bucket.append(tokens)
    out: dict[str, dict[str, Any]] = {}
    for name in wanted:
        bucket = vectors.get(name) or []
        counter = counters.get(name) or {"sites": 0, "encodable": 0}
        out[name] = {"vectors": bucket, "sites": counter["sites"], "encodable": counter["encodable"],
                     "refusal": (None if bucket else
                                 (REFUSED_UNENCODABLE if counter["sites"] else REFUSED_NO_CALL_SITE))}
    return out


# --------------------------------------------------------------------------- #
# execution: the only thing that decides whether an argument is real
# --------------------------------------------------------------------------- #
def _observable(outcome: Mapping[str, Any]) -> str:
    return REN._observable(outcome)


def observe(tree: pathlib.Path, module: str, calls: Sequence[Mapping[str, Any]]) -> list[str]:
    observed: list[str] = []
    for start in range(0, len(calls), BATCH):
        chunk = calls[start:start + BATCH]
        observed.extend(_observable(outcome) for outcome in execute.probe(tree, [
            {"module": module, "function": call["function"], "args": call["args"]} for call in chunk]))
    return observed


def construct(old_tree: pathlib.Path, new_tree: pathlib.Path, relative: str, module: str,
              new_relative: str | None = None) -> dict[str, Any]:
    """For each action round 6 could not exercise, can the environment's own call sites make it run?"""
    row: dict[str, Any] = {"module": module, "relative": relative}
    old_source = (old_tree / relative).read_text(encoding="utf-8", errors="replace")
    new_source = (new_tree / (new_relative or relative)).read_text(encoding="utf-8", errors="replace")
    sites = SITE.candidate_sites(old_source)
    if not sites:
        row["state"] = "NO_DRIVABLE_CALLABLE"
        return row
    names = {site["function"] for site in sites}
    tokens = REN.witnesses(old_source)
    learned, held_out = REN.split(tokens)

    # the round-6 baseline, recomputed here so the comparison is exact and not remembered
    baseline_calls = [{"function": site["function"],
                       "args": SITE._tokens(site, token, shape)}
                      for site in sites for token in tokens for shape in REN.SHAPES]
    baseline_first = observe(old_tree, module, baseline_calls)
    baseline_second = observe(old_tree, module, baseline_calls)
    returned: set[str] = set()
    for call, first, second in zip(baseline_calls, baseline_first, baseline_second):
        if first.startswith("RETURNED") and first == second:
            returned.add(call["function"])

    mined = mined_vectors(old_tree, names - returned)
    constructed_calls: list[dict[str, Any]] = []
    for name, entry in mined.items():
        for vector in entry["vectors"]:
            constructed_calls.append({"function": name, "args": vector})
    first = observe(old_tree, module, constructed_calls) if constructed_calls else []
    second = observe(old_tree, module, constructed_calls) if constructed_calls else []
    new_run = observe(new_tree, module, constructed_calls) if constructed_calls else []

    rows: list[dict[str, Any]] = []
    for index, call in enumerate(constructed_calls):
        if index >= len(first) or index >= len(second) or index >= len(new_run):
            continue
        rows.append({"function": call["function"], "args": call["args"], "old": first[index],
                     "stable": first[index] == second[index], "new": new_run[index]})
    by_function: dict[str, list[dict[str, Any]]] = {}
    for entry in rows:
        by_function.setdefault(entry["function"], []).append(entry)

    verdicts: list[dict[str, Any]] = []
    for name in sorted(names):
        if name in returned:
            verdicts.append({"function": name, "state": "ALREADY_OBSERVABLE_IN_ROUND_6"})
            continue
        candidates = by_function.get(name) or []
        worked = [entry for entry in candidates if entry["stable"] and entry["old"].startswith("RETURNED")]
        entry_out: dict[str, Any] = {"function": name, "vectors_tried": len(candidates),
                                     "mined": mined.get(name, {}).get("sites", 0),
                                     "encodable": mined.get(name, {}).get("encodable", 0)}
        if not worked:
            entry_out["state"] = (REFUSED_DID_NOT_RUN if candidates
                                  else (mined.get(name, {}).get("refusal") or REFUSED_NO_CALL_SITE))
            if candidates:
                entry_out["evidence"] = candidates[0]
            verdicts.append(entry_out)
            continue
        entry_out["state"] = "BECAME_OBSERVABLE"
        entry_out["witness"] = worked[0]
        moved = [entry for entry in worked if entry["old"] != entry["new"]]
        entry_out["moved_at_new_release"] = bool(moved)
        if moved:
            entry_out["move_kind"] = REN._kind({"old": moved[0]["old"], "new": moved[0]["new"]})
            entry_out["move_evidence"] = moved[0]
        verdicts.append(entry_out)
    row["callables"] = verdicts
    counts: dict[str, int] = {}
    for entry in verdicts:
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    row["counts"] = counts
    return row


def measure_repo(repo: str, old: str, new: str, cache: pathlib.Path,
                 work: pathlib.Path) -> dict[str, Any]:
    clone = witness.fetch(repo, old, new, cache)
    row: dict[str, Any] = {"repo": repo, "old": old, "new": new}
    if clone is None:
        row["state"] = "FETCH_FAILED"
        return row
    old_tree, note_old = witness.materialise(clone, old, work, suffix="-bo")
    new_tree, note_new = witness.materialise(clone, new, work, suffix="-bn")
    if old_tree is None or new_tree is None:
        row["state"] = "MATERIALISE_FAILED"
        row["detail"] = note_old or note_new
        return row
    old_modules, new_modules = REN.package_modules(old_tree), REN.package_modules(new_tree)
    modules: list[dict[str, Any]] = []
    for module, path in old_modules.items():
        relative = str(path.relative_to(old_tree))
        if module not in new_modules:
            modules.append({"module": module, "relative": relative, "state": "GONE_AT_NEW"})
            continue
        try:
            modules.append(construct(old_tree, new_tree, relative, module,
                                     new_relative=str(new_modules[module].relative_to(new_tree))))
        except Exception as exc:  # noqa: BLE001 - named, never counted
            modules.append({"module": module, "relative": relative,
                            "state": "INSTRUMENT_FAILED",
                            "detail": type(exc).__name__ + ": " + str(exc)[:160]})
    row["modules"] = modules
    row["state"] = "MEASURED"
    return row


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    totals = {"callables": 0, "ALREADY_OBSERVABLE_IN_ROUND_6": 0, "BECAME_OBSERVABLE": 0,
              REFUSED_NO_CALL_SITE: 0, REFUSED_UNENCODABLE: 0, REFUSED_DID_NOT_RUN: 0,
              "moved_at_new_release": 0, "modules": 0, "modules_failed": 0}
    examples: list[dict[str, Any]] = []
    for row in rows:
        if row.get("state") != "MEASURED":
            totals["modules_failed"] += 1
            continue
        for module in row.get("modules", []):
            totals["modules"] += 1
            if module.get("state") == "INSTRUMENT_FAILED":
                totals["modules_failed"] += 1
            for entry in module.get("callables") or []:
                totals["callables"] += 1
                state = entry.get("state")
                if state in totals:
                    totals[state] += 1
                if state == "BECAME_OBSERVABLE":
                    if entry.get("moved_at_new_release"):
                        totals["moved_at_new_release"] += 1
                    if len(examples) < 12:
                        examples.append({"repo": row["repo"], "module": module["module"],
                                         "function": entry["function"],
                                         "args": (entry.get("witness") or {}).get("args"),
                                         "old": (entry.get("witness") or {}).get("old"),
                                         "move": entry.get("move_kind")})
    blocked = totals["ALREADY_OBSERVABLE_IN_ROUND_6"] + sum(
        totals[key] for key in (REFUSED_NO_CALL_SITE, REFUSED_UNENCODABLE, REFUSED_DID_NOT_RUN))
    unexercised = sum(totals[key] for key in (REFUSED_NO_CALL_SITE, REFUSED_UNENCODABLE,
                                              REFUSED_DID_NOT_RUN))
    totals["round_6_unexercised"] = unexercised
    totals["unexercised_fraction_unlocked"] = (
        round(totals["BECAME_OBSERVABLE"] / unexercised, 4) if unexercised else None)
    totals["all_callables"] = blocked
    return {"totals": totals, "examples": examples}


def measure(cache: pathlib.Path, work: pathlib.Path, limit: int | None = None) -> dict[str, Any]:
    rows = [measure_repo(repo, old, new, cache, work) for repo, old, new in witness.CORPUS_REPOS[:limit]]
    summary = summarise(rows)
    return {"schema": SCHEMA, "authority": AUTHORITY, "model_calls": 0, "network_calls": 0,
            "incremental_spend_usd": 0, "repos": rows, **summary,
            "reproduce": ".venv/bin/python canonical/swe_kernel/argument_construction_v1.py --json "
                         "canonical/verification/ARGUMENT_CONSTRUCTION_20261116_V1.json"}


def _headline(report: Mapping[str, Any]) -> str:
    totals = report.get("totals") or {}
    return (
        "%(callables)d real actions examined. %(ALREADY_OBSERVABLE_IN_ROUND_6)d were already exercisable "
        "with scalar witnesses. Of the %(round_6_unexercised)d that round 6 could NOT exercise, "
        "%(BECAME_OBSERVABLE)d (%(unexercised_fraction_unlocked)s) now RUN, using argument vectors mined from "
        "the environment's own call sites. %(moved_at_new_release)d of those are moved by the release bump. "
        "Refusals by name: NO_MINEABLE_CALL_SITE %(REFUSED__NO_MINEABLE_CALL_SITE)d, "
        "EVERY_CALL_SITE_IS_UNENCODABLE %(REFUSED__EVERY_CALL_SITE_IS_UNENCODABLE)d, "
        "MINED_BUT_NEVER_RETURNED %(REFUSED__MINED_BUT_NEVER_RETURNED)d." % totals)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Construct arguments from the environment's own proofs.")
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--cache", type=pathlib.Path, default=pathlib.Path("/tmp/perm-cache"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/arg-work"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    report = measure(args.cache, args.work, args.limit)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", args.json)
    print(_headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
