"""Observation by replaying the environment's own scenarios.

Round 7 ended with a census, not a triumph: of the 41 real actions round 6 could never exercise, reading
the environment's own call sites as *data* unlocked exactly 1 (2.4%), and 34 were refused because those call
sites pass constructed objects -- a parser state, a dict accumulator, a Signer. The conclusion was structural:

    the environment proves EXPRESSIONS, never VALUES. So binding cannot be a lookup; it must be evaluation.

This round takes that conclusion literally and removes the need to encode arguments at all.

WHAT THIS DOES
--------------
Instead of inventing an argument vector and calling the target directly, run the environment's OWN test
suite and record what happens at every call into the package: the callable, its arity and argument types,
and whether it returned (with a normalised digest of the return) or raised (with the exception's name).
An internal function whose arguments are a live `ParserState` and a live `dict` therefore becomes observable
without anyone ever constructing a `ParserState`: the environment's own test constructs it.

The record is the shape the 2026 specification-mining literature calls the carrying object -- "construction
and call arguments, selected pre-state and post-state values, and whether the call returns normally or
throws" (arXiv 2608.13240, Aug 2026) -- with the one thing that literature insists on removed: the language
model. Nothing here is prompted, sampled, or guessed. The observation IS the execution.

WHY THIS IS THE RIGHT ORGAN, AND NOT A FIXTURE LIBRARY
------------------------------------------------------
* A fixture library is a knowledge house: hand-written arguments for N packages, useless on package N+1.
* Mining literals (round 7) is lookup, and lookup is capped at 2.4% because the environment's arguments are
  objects.
* Running the environment's own scenarios asks the environment to construct its own inputs, which is the
  only construction that is guaranteed to be real. It also generalises to computer use for the same reason:
  an action on a machine is learned by executing it once, not by describing it.

WHAT IS REFUSED, BY NAME
------------------------
    SUITE_DID_NOT_RUN            the tree's own tests could not be executed at all
    NO_TEST_SUITE_IN_TREE        there is nothing in the environment that exercises it
    NOT_REACHED_BY_OWN_SUITE     the suite ran but never called this action
    NONDETERMINISTIC_AT_OLD      two runs of the same suite at the same revision disagreed
    REACHED_AT_OLD_ONLY          the old suite reaches it, the new one does not (a test change, not a code move)
    GONE_AT_NEW                  the callable no longer exists in the later release

WHAT IS MEASURED
----------------
On round 6's exact denominator (the real callables of 22 real modules across three real release bumps):
how many actions that could never be exercised by scalar witnesses are exercised by the environment's own
suite; whether each observation is stable across two runs at the same revision; and how many of them the
release bump MOVES, split into now-raises, now-returns, arity/type change, and value change.

Reuses (never rebuilds): `witness_inversion_v1` (fetch/materialise), `renewable_action_v1`
(package_modules, witnesses, split, SHAPES), `site_by_intervention_v1.candidate_sites` (the callable
universe), `argument_construction_v1.observe` (the round-6 baseline, recomputed here rather than remembered).
Authority: NONE -- sandbox measurement, not independent verification. No model is used or consulted.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import argument_construction_v1 as ARG  # noqa: E402
from canonical.swe_kernel import renewable_action_v1 as REN  # noqa: E402
from canonical.swe_kernel import site_by_intervention_v1 as SITE  # noqa: E402
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402

SCHEMA = "BRAIN_SCENARIO_OBSERVATION_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0

SUITE_TIMEOUT_S = 420
MAX_RECORDS = 400_000

REFUSED_SUITE = "REFUSED__SUITE_DID_NOT_RUN"
REFUSED_NO_SUITE = "REFUSED__NO_TEST_SUITE_IN_TREE"
REFUSED_NOT_REACHED = "REFUSED__NOT_REACHED_BY_OWN_SUITE"
REFUSED_NONDETERMINISTIC = "REFUSED__NONDETERMINISTIC_AT_OLD"
REFUSED_OLD_ONLY = "REFUSED__REACHED_AT_OLD_ONLY"
REFUSED_GONE = "REFUSED__GONE_AT_NEW"

MOVE_NOW_RAISES = "NOW_RAISES"
MOVE_NOW_RETURNS = "NOW_RETURNS"
MOVE_ARITY = "SIGNATURE_CHANGED"
MOVE_VALUE = "VALUE_CHANGED"
MIX = "EXERCISE_MIX_CHANGED"
STABLE = "STABLE"

_HEX = re.compile(r"0x[0-9a-fA-F]+")
_TMP = re.compile(r"(/[^\s'\"]*?(?:tmp|temp|pytest)[^\s'\"]*)")


def _normalise(text: str) -> str:
    """Volatile text out, so two runs of the same code compare equal and two revisions do not."""
    text = _HEX.sub("0x?", text)
    text = _TMP.sub("<path>", text)
    return text[:120]


def _digest(value: Any, depth: int = 0) -> str:
    """A value's observable shape: exact for stable literals, type-only for objects.

    Printing an object's repr would smuggle addresses and timings into the record and make every revision
    look like a move. Type-only is the honest ceiling for objects, and it is why a move in a returned object
    is recorded as a type change rather than pretended to be a value change.
    """
    if value is None or isinstance(value, (bool, int, float)):
        return _normalise(repr(value))
    if isinstance(value, str):
        return _normalise(repr(value))
    if isinstance(value, (bytes, bytearray)):
        return "bytes:" + hashlib.sha256(bytes(value)).hexdigest()[:12]
    if isinstance(value, (list, tuple)) and depth < 2:
        head = ",".join(_digest(item, depth + 1) for item in list(value)[:8])
        return f"{type(value).__name__}[{len(value)}]({head})"
    if isinstance(value, dict) and depth < 2 and len(value) <= 12:
        items = sorted((_digest(k, depth + 1), _digest(v, depth + 1)) for k, v in value.items())
        return "dict{" + ",".join(f"{k}:{v}" for k, v in items) + "}"
    if isinstance(value, (set, frozenset)) and depth < 2 and len(value) <= 12:
        return "{" + ",".join(sorted(_digest(item, depth + 1) for item in value)) + "}"
    return type(value).__name__


BOOTSTRAP = '''\
"""Runs the environment's own tests and records what happened at every call into the package."""
import json, os, sys

TARGETS = set(json.loads(os.environ["BRAIN_TARGETS"]))
PACKAGE = os.path.abspath(os.environ["BRAIN_PACKAGE_ROOT"])
OUT = os.environ["BRAIN_RECORD_OUT"]
CAP = int(os.environ["BRAIN_RECORD_CAP"])

{helpers}

records = []


def _local(frame):
    code = frame.f_code
    name = code.co_name
    key = (code.co_filename, name)
    arity = code.co_argcount + code.co_kwonlyargcount

    def trace(frame, event, arg):
        if event == "return":
            records.append({{"f": os.path.relpath(code.co_filename, PACKAGE), "n": name, "a": arity,
                            "o": "RETURNED|" + _digest(arg)}})
            return None
        if event == "exception":
            exc = arg[1]
            records.append({{"f": os.path.relpath(code.co_filename, PACKAGE), "n": name, "a": arity,
                            "o": "RAISED|" + type(exc).__name__}})
            return None
        return trace

    return trace


def trace(frame, event, arg):
    if event != "call":
        return None
    code = frame.f_code
    if code.co_name in TARGETS and os.path.abspath(code.co_filename).startswith(PACKAGE):
        if len(records) >= CAP:
            return None
        return _local(frame)
    return None


def main():
    sys.settrace(trace)
    import pytest
    args = sys.argv[1:]
    code = pytest.main(args)
    sys.settrace(None)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump({{"exit": int(code), "records": records}}, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def _bootstrap_source() -> str:
    prelude = "import hashlib, re\nfrom typing import Any\n_HEX = re.compile(r'0x[0-9a-fA-F]+')\n" \
              "_TMP = re.compile(r\"(/[^\\s'\\\"]*?(?:tmp|temp|pytest)[^\\s'\\\"]*)\")\n"
    helpers = prelude + "".join(textwrap.dedent(_source(fn)) for fn in (_normalise, _digest))
    return BOOTSTRAP.format(helpers=helpers)


def _source(obj: Any) -> str:
    import inspect
    return inspect.getsource(obj)


def tests_root(tree: pathlib.Path) -> pathlib.Path | None:
    for name in ("tests", "test", "testsuite"):
        candidate = tree / name
        if candidate.is_dir() and any(candidate.rglob("test_*.py")):
            return candidate
    for candidate in sorted(tree.rglob("test_*.py")):
        if "site-packages" not in candidate.parts and ".venv" not in candidate.parts:
            return candidate.parent
    return None


def package_root(tree: pathlib.Path) -> pathlib.Path:
    """Where the package's importable code lives: `src/` when the project uses a src layout."""
    if (tree / "src").is_dir():
        return tree / "src"
    return tree


def run_suite(tree: pathlib.Path, targets: set[str], timeout_s: int = SUITE_TIMEOUT_S) -> dict[str, Any]:
    """One real execution of the environment's own tests, under a recording tracer."""
    suite = tests_root(tree)
    if suite is None:
        return {"state": REFUSED_NO_SUITE, "records": []}
    package = package_root(tree)
    with tempfile.TemporaryDirectory(prefix="scenario-") as scratch:
        script = pathlib.Path(scratch) / "runner.py"
        script.write_text(_bootstrap_source(), encoding="utf-8")
        out = pathlib.Path(scratch) / "records.json"
        env = dict(os.environ)
        env.update({
            "BRAIN_TARGETS": json.dumps(sorted(targets)),
            "BRAIN_PACKAGE_ROOT": str(package),
            "BRAIN_RECORD_OUT": str(out),
            "BRAIN_RECORD_CAP": str(MAX_RECORDS),
            "PYTHONPATH": os.pathsep.join([str(package), str(tree), env.get("PYTHONPATH", "")]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        })
        try:
            proc = subprocess.run([sys.executable, str(script), str(suite.relative_to(tree)),
                                   "-q", "--no-header", "-p", "no:cacheprovider",
                                   "--continue-on-collection-errors"],
                                  cwd=str(tree), env=env, capture_output=True, text=True,
                                  timeout=timeout_s)
            exit_code = proc.returncode
            tail = (proc.stdout or "")[-300:]
        except subprocess.TimeoutExpired:
            return {"state": REFUSED_SUITE, "detail": f"timeout after {timeout_s}s", "records": []}
        if not out.is_file():
            return {"state": REFUSED_SUITE, "detail": "no records written", "exit": exit_code,
                    "tail": tail, "records": []}
        payload = json.loads(out.read_text(encoding="utf-8"))
    return {"state": "RAN", "exit": payload["exit"], "records": payload["records"]}


def _by_callable(records: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[str]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for record in records:
        grouped.setdefault((record["f"], record["n"]), []).append(
            f"{record['o']}|arity={record['a']}")
    for key in grouped:
        grouped[key].sort()
    return grouped


def _family(outcomes: Sequence[str]) -> set[str]:
    return {"RAISED" if entry.startswith("RAISED") else "RETURNED" for entry in outcomes}


def classify(old_pair: Sequence[str], old_repeat: Sequence[str],
             new: Sequence[str] | None) -> tuple[str, str]:
    """What happened to this action, using only what the environment itself did."""
    if list(old_pair) != list(old_repeat):
        return REFUSED_NONDETERMINISTIC, "two runs of the same suite at the same revision disagreed"
    if new is None:
        return REFUSED_GONE, "the callable is not reached at the later release"
    if not new:
        return REFUSED_OLD_ONLY, "the later suite never reaches it"
    if list(new) == list(old_pair):
        return STABLE, "identical observations"
    if set(new) == set(old_pair):
        # the same outcomes in different proportions: the suite changed what it exercises, the code did not
        return MIX, "the same outcomes, exercised in different proportions -- a test change, not a move"
    old_families, new_families = _family(old_pair), _family(new)
    if old_families == {"RETURNED"} and new_families == {"RAISED"}:
        return MOVE_NOW_RAISES, "returned at the old release, raises at the new one"
    if old_families == {"RAISED"} and new_families == {"RETURNED"}:
        return MOVE_NOW_RETURNS, "raised at the old release, returns at the new one"
    old_arity = {entry.split("arity=")[-1] for entry in old_pair}
    new_arity = {entry.split("arity=")[-1] for entry in new}
    if old_arity != new_arity:
        return MOVE_ARITY, "the callable's own arity changed"
    return MOVE_VALUE, "the same call produced a different observable"


def observe_repo(repo: str, old: str, new: str, cache: pathlib.Path, work: pathlib.Path,
                 repeat: bool = True) -> dict[str, Any]:
    """The whole denominator: every real callable of every real module, observed through its own suite."""
    clone = witness.fetch(repo, old, new, cache)
    row: dict[str, Any] = {"repo": repo, "old": old, "new": new}
    if clone is None:
        row["state"] = "FETCH_FAILED"
        return row
    old_tree, note_old = witness.materialise(clone, old, work, suffix="-so")
    new_tree, note_new = witness.materialise(clone, new, work, suffix="-sn")
    if old_tree is None or new_tree is None:
        row["state"] = "MATERIALISE_FAILED"
        row["detail"] = note_old or note_new
        return row

    old_modules, new_modules = REN.package_modules(old_tree), REN.package_modules(new_tree)
    # records are keyed relative to the IMPORTABLE root (src/ for src layouts), modules relative to the tree
    prefix = package_root(old_tree).relative_to(old_tree)
    rows: list[dict[str, Any]] = []
    for module, path in sorted(old_modules.items()):
        relative = str(path.relative_to(old_tree))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            sites = SITE.candidate_sites(source)
        except Exception as exc:  # noqa: BLE001 - named, never counted
            rows.append({"module": module, "relative": relative, "state": "INSTRUMENT_FAILED",
                         "detail": type(exc).__name__ + ": " + str(exc)[:140]})
            continue
        if not sites:
            rows.append({"module": module, "relative": relative, "state": "NO_DRIVABLE_CALLABLE"})
            continue
        key_relative = (str(pathlib.Path(relative).relative_to(prefix))
                        if str(prefix) != "." else relative)
        names = {site["function"] for site in sites}
        tokens = REN.witnesses(source)
        baseline_calls = [{"function": site["function"], "args": SITE._tokens(site, token, shape)}
                          for site in sites for token in tokens for shape in REN.SHAPES]
        baseline = ARG.observe(old_tree, module, baseline_calls)
        already = {call["function"] for call, outcome in zip(baseline_calls, baseline)
                   if outcome.startswith("RETURNED")}
        unexercised = names - already

        old_run = run_suite(old_tree, names)
        old_again = run_suite(old_tree, names) if repeat and old_run["state"] == "RAN" else old_run
        new_run = run_suite(new_tree, names) if old_run["state"] == "RAN" else {"state": old_run["state"],
                                                                               "records": []}
        if old_run["state"] != "RAN":
            rows.append({"module": module, "relative": relative, "state": old_run["state"],
                         "detail": old_run.get("detail") or old_run.get("tail", "")[:140],
                         "unexercised": len(unexercised)})
            continue

        old_group = _by_callable(old_run["records"])
        again_group = _by_callable(old_again["records"]) if old_again["state"] == "RAN" else old_group
        new_group = _by_callable(new_run["records"]) if new_run["state"] == "RAN" else {}

        verdicts: list[dict[str, Any]] = []
        reached_unexercised = 0
        moved_unexercised = 0
        seen: set[str] = set()
        for site in sorted(sites, key=lambda entry: entry["function"]):
            name = site["function"]
            if name in seen:  # the same name twice is one action, not two (round 7 counted 82 of 81)
                continue
            seen.add(name)
            key = (key_relative, name)
            old_pair = old_group.get(key)
            if not old_pair:
                verdict = REFUSED_NOT_REACHED
                note = "the suite ran but never called it"
            else:
                verdict, note = classify(old_pair, again_group.get(key, old_pair), new_group.get(key))
            if name in unexercised and old_pair:
                reached_unexercised += 1
                if verdict in (MOVE_NOW_RAISES, MOVE_NOW_RETURNS, MOVE_ARITY, MOVE_VALUE):
                    moved_unexercised += 1
            verdicts.append({
                "function": name, "state": verdict, "note": note,
                "round6_unexercised": name in unexercised,
                "observations": len(old_pair or []),
                "example": (old_pair or [None])[0],
                # a move must carry both sides of the evidence, or the claim cannot be checked
                "old_only": sorted(set(old_pair or []) - set(new_group.get(key) or [])),
                "new_only": sorted(set(new_group.get(key) or []) - set(old_pair or [])),
            })
        rows.append({"module": module, "relative": relative, "state": "MEASURED",
                     "callables": verdicts,
                     "suite_exit_old": old_run.get("exit"),
                     "suite_exit_new": new_run.get("exit"),
                     "reached_unexercised": reached_unexercised,
                     "moved_unexercised": moved_unexercised,
                     "unexercised": len(unexercised)})
    row["modules"] = rows
    row["state"] = "MEASURED"
    return row


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {"modules": 0, "modules_measured": 0, "callables": 0,
                              "modules_with_incomplete_suite": 0,
                              "round6_unexercised": 0, "reached_unexercised": 0,
                              "moved_unexercised": 0, "moves": {}, "module_states": {}}
    for row in rows:
        for module in row.get("modules", []):
            totals["modules"] += 1
            totals["module_states"][module["state"]] = totals["module_states"].get(module["state"], 0) + 1
            if module["state"] != "MEASURED":
                totals["round6_unexercised"] += module.get("unexercised", 0)
                continue
            totals["modules_measured"] += 1
            if module.get("suite_exit_old") or module.get("suite_exit_new"):
                totals["modules_with_incomplete_suite"] += 1
            totals["callables"] += len(module["callables"])
            totals["round6_unexercised"] += module["unexercised"]
            totals["reached_unexercised"] += module["reached_unexercised"]
            totals["moved_unexercised"] += module["moved_unexercised"]
            for verdict in module["callables"]:
                totals["moves"][verdict["state"]] = totals["moves"].get(verdict["state"], 0) + 1
    unexercised = totals["round6_unexercised"]
    totals["reached_fraction"] = round(totals["reached_unexercised"] / unexercised, 4) if unexercised else 0.0
    totals["moved_fraction_of_reached"] = (round(totals["moved_unexercised"] / totals["reached_unexercised"], 4)
                                           if totals["reached_unexercised"] else 0.0)
    return totals


def _headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    moves = totals["moves"]
    parts = [f"{totals['callables']} real actions observed by running the environment's own suites "
             f"in {totals['modules_measured']} real modules."]
    parts.append(f"Of the {totals['round6_unexercised']} that scalar witnesses could not exercise, "
                 f"{totals['reached_unexercised']} ({totals['reached_fraction']}) are exercised by the "
                 f"environment's own tests.")
    parts.append(f"The release bump moves {totals['moved_unexercised']} of those {totals['reached_unexercised']} "
                 f"({totals['moved_fraction_of_reached']} of those now observable, and "
                 f"{round(totals['moved_unexercised'] / totals['round6_unexercised'], 4) if totals['round6_unexercised'] else 0.0}"
                 f" of the whole unexercised set).")
    parts.append("Refusals by name: " + ", ".join(f"{state} {count}" for state, count in sorted(moves.items())
                                                  if state.startswith("REFUSED__")) + ".")
    return " ".join(parts)


def measure(cache: pathlib.Path, work: pathlib.Path, limit: int | None = None,
            repeat: bool = True) -> dict[str, Any]:
    cache.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    corpus = list(witness.CORPUS_REPOS)[:limit] if limit else list(witness.CORPUS_REPOS)
    rows = [observe_repo(repo, old, new, cache, work, repeat=repeat) for repo, old, new in corpus]
    report = {"schema": SCHEMA, "corpus": corpus, "model_calls": MODEL_CALLS,
              "network_calls": NETWORK_CALLS, "repos": rows}
    report["totals"] = summarise(rows)
    report["headline"] = _headline(report)
    report["authority"] = "NONE -- sandbox measurement, not independent verification"
    return report


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--cache", type=pathlib.Path, default=pathlib.Path("/tmp/perm-cache"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/scenario-work"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--single", action="store_true", help="one run at the old revision (faster, weaker)")
    args = parser.parse_args(argv)
    report = measure(args.cache, args.work, limit=args.limit, repeat=not args.single)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(report["headline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
