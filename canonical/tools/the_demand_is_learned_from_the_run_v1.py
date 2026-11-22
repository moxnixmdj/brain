#!/usr/bin/env python3
"""Can a demand predicate be *learned* from a failing run instead of hand-written?

The previous round (`THE_DEMAND_IS_A_RELATION_20261125_V1.md`) recovered 2 of 75 real
one-line fixes with ONE hand-written relation, `x is not None`, at run-selected guard
sites. It concluded that the next move is not an eighth hand-written form but a demand
language learned from the run, with the project's own suite as judge. This tool tests
that conclusion on the 45 commits the engine had never seen.

What is computed, in order:

1. checkout the parent, copy in the commit's test file, run the suite -> failing nodes;
2. instrument every boolean-position guard with a probe that records the value's
   *type-level* features (None, truthiness, zero, empty literal, size, builtin type)
   and the pytest node that reached it; run the suite once;
3. for each guard, score each feature by how well its truth value separates the
   failing nodes from the passing nodes; the two highest-scoring polarities are the
   learned predicate candidates -- no candidate is named from the human edit;
4. compile the selected feature into a guard expression, run the witness nodes first
   and then the whole suite, and accept only if the control (the human edit, used
   solely to validate the judge) is accepted and the candidate flips every test the
   control flips while breaking none;
5. write an auditable receipt and never store a parameter or a learned weight.

The pre-registered claim is that at least one row that the fixed-form engine missed
becomes verified this way. If not, the honest result is that a predicate learned from
one run's guard values is not the missing demand language either.
"""
from __future__ import annotations

import argparse
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

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import the_relation_not_the_value_v1 as prior  # noqa: E402

SCHEMA = "BRAIN_THE_DEMAND_IS_LEARNED_FROM_THE_RUN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PRIOR_MODULE = "the_relation_not_the_value_v1"
MODULE = "brain_run_probe"
FAILING = ("FAILED", "ERROR")

DECLARED: dict[str, str] = {
    "L1": "candidate predicates are computed from probed guard values and pass/fail runs; the human edit is used only as a control on the judge",
    "L2": "every counted row has a real failing test and an accepted control on its project's own suite",
    "L3": "at most 4 compiled predicates are judged per row; each is selected by a pass/fail separation score, not by trying it against the hidden suite",
    "L4": "at least one row missed by the fixed is-not-None engine becomes VERIFIED with exact witness footprint and 0 broken tests",
    "L5": "zero model calls, zero stored parameters, zero network calls at run time",
}

PROBE_SOURCE = '''"""Records type-level facts about values the program asks a yes/no question of."""
import json
import os


def probe(line, col, value):
    facts = {
        "line": line,
        "col": col,
        "node": os.environ.get("PYTEST_CURRENT_TEST", ""),
        "type": type(value).__name__,
        "repr": repr(value)[:120],
        "is_none": value is None,
        "is_bool": type(value) is bool,
        "truthy": bool(value),
        "zero": type(value) in (int, float) and value == 0,
        "empty_str": type(value) is str and value == "",
        "is_str": type(value) is str,
        "is_list": type(value) is list,
        "is_dict": type(value) is dict,
        "is_tuple": type(value) is tuple,
        "is_set": type(value) is set,
        "is_int": type(value) is int,
        "is_float": type(value) is float,
    }
    try:
        facts["has_len"] = True
        facts["length"] = len(value)
    except Exception:
        facts["has_len"] = False
        facts["length"] = 0
    path = os.environ.get("BRAIN_PROBE_OUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(facts) + "\\n")
    return value
'''

# (feature name, compiled expression over the guarded expression x, predicate on facts)
FEATURES: tuple[tuple[str, str, Any], ...] = (
    ("is_none", "(({x}) is None)", lambda f: f["is_none"]),
    ("truthy", "bool(({x}))", lambda f: f["truthy"]),
    ("falsey", "not (({x}))", lambda f: not f["truthy"]),
    ("zero", "(({x}) == 0)", lambda f: f["zero"]),
    ("empty_str", '(({x}) == "")', lambda f: f["empty_str"]),
    ("empty_collection", "(len(({x})) == 0)",
     lambda f: f["has_len"] and f["length"] == 0 and not f["is_str"]),
    ("nonempty_collection", "(len(({x})) > 0)",
     lambda f: f["has_len"] and f["length"] > 0),
    ("is_str", "isinstance(({x}), str)", lambda f: f["is_str"]),
    ("is_list", "isinstance(({x}), list)", lambda f: f["is_list"]),
    ("is_dict", "isinstance(({x}), dict)", lambda f: f["is_dict"]),
    ("is_tuple", "isinstance(({x}), tuple)", lambda f: f["is_tuple"]),
    ("is_set", "isinstance(({x}), set)", lambda f: f["is_set"]),
    ("is_int", "isinstance(({x}), int)", lambda f: f["is_int"]),
    ("is_float", "isinstance(({x}), float)", lambda f: f["is_float"]),
    ("is_bool", "isinstance(({x}), bool)", lambda f: f["is_bool"]),
)


def run_tests(worktree: pathlib.Path, targets: Sequence[str], seconds: int,
              extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """The same oracle as the earlier engine, with node-id targets for a cheap prefilter."""
    command = [sys.executable, "-m", "pytest", *targets, "-v", "--tb=no", "-p",
               "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ,
                                   **identify.fresh_bytecode(worktree), **(extra_env or {})})
    except subprocess.TimeoutExpired:
        return {"<timed out>": "TIMEOUT"}
    outcomes: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        stripped = line.strip()
        after = identify.VERDICT_AFTER.match(stripped)
        if after:
            outcomes[after.group(1)] = after.group(2)
            continue
        before = identify.VERDICT_BEFORE.match(stripped)
        if before:
            outcomes[before.group(2)] = before.group(1)
    return outcomes


def judge(baseline: dict[str, str], after: dict[str, str],
          witness: Sequence[str]) -> tuple[bool, str, list[str]]:
    failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
    passing = [name for name, verdict in baseline.items() if verdict.upper() == "PASSED"]
    flipped = [name for name in failing if after.get(name, "").upper() == "PASSED"]
    broken = [name for name in passing if after.get(name, "").upper() in FAILING]
    if not flipped:
        return False, "NO_TEST_FLIPPED", []
    if set(witness) - set(flipped):
        return False, f"PARTIAL_FLIP={len(set(witness) - set(flipped))}", flipped
    if broken:
        return False, f"BROKE={len(broken)}", flipped
    return True, "VERIFIED", flipped


def learn(observations: Sequence[dict[str, Any]], failing: set[str],
           passing: set[str], sites: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """A predicate is learned by separating failed from passing runs at one guard site.

    Each feature is evaluated at each site on one value per test. `gain` is
    fail-matches minus pass-matches; its negation has exactly the opposite gain, so
    one score produces both polarities. A strict candidate matches no passing run.
    """
    by_site: dict[tuple[int, int], dict[str, dict[str, bool]]] = {}
    for row in observations:
        if not row.get("node"):
            continue
        key = (row["line"], row["col"])
        slot = by_site.setdefault(key, {})
        node = str(row["node"]).split(" ")[0]
        slot.setdefault(node, {})
        for name, _template, predicate in FEATURES:
            slot[node][name] = bool(predicate(row))
    ranked: list[dict[str, Any]] = []
    for site in sites:
        key = (site["line"], site["col"])
        values = by_site.get(key, {})
        fail_nodes = [node for node in values if node in failing]
        pass_nodes = [node for node in values if node in passing]
        if not fail_nodes or not pass_nodes:
            continue
        for name, _template, _predicate in FEATURES:
            fail_true = sum(values[node][name] for node in fail_nodes)
            pass_true = sum(values[node][name] for node in pass_nodes)
            gain = fail_true - pass_true
            for polarity in (True, False):
                matches_fail = fail_true if polarity else len(fail_nodes) - fail_true
                matches_pass = pass_true if polarity else len(pass_nodes) - pass_true
                score = gain if polarity else -gain
                if score <= 0 or matches_fail == 0:
                    continue
                ranked.append({
                    "line": site["line"], "col": site["col"], "text": site["text"],
                    "feature": name, "polarity": polarity,
                    "gain": score, "fail_matches": matches_fail,
                    "pass_mismatches": matches_pass,
                    "strict": matches_pass == 0,
                    "observed_value": next((row.get("repr") for row in observations
                                            if (row["line"], row["col"]) == key
                                            and str(row.get("node", "")).split(" ")[0] in failing), ""),
                })
    # At most one compiled predicate per site, so a file with hundreds of observed
    # guards cannot swamp a row. Prefer strict separation, then the largest gain.
    chosen: list[dict[str, Any]] = []
    used: set[tuple[int, int]] = set()
    for candidate in sorted(ranked, key=lambda row: (-int(row["strict"]), -row["gain"],
                                                     -row["fail_matches"],
                                                     row["pass_mismatches"],
                                                     row["feature"], row["polarity"])):
        key = (candidate["line"], candidate["col"])
        if key in used:
            continue
        used.add(key)
        chosen.append(candidate)
        if len(chosen) >= 4:
            break
    return chosen


def compile_rule(candidate: dict[str, Any]) -> str | None:
    template = next((tpl for name, tpl, _ in FEATURES if name == candidate["feature"]), None)
    if template is None:
        return None
    expression = template.format(x=candidate["text"])
    if not candidate["polarity"]:
        expression = f"not ({expression})"
    return expression


def replace(source: str, candidate: dict[str, Any], expression: str) -> str | None:
    lines = source.splitlines(keepends=True)
    index = candidate["line"] - 1
    if not (0 <= index < len(lines)):
        return None
    line = lines[index]
    start, end = candidate["col"], candidate["col"] + len(candidate["text"])
    if line[start:end] != candidate["text"]:
        return None
    lines[index] = line[:start] + "(" + expression + ")" + line[end:]
    try:
        import ast
        ast.parse("".join(lines))
    except SyntaxError:
        return None
    return "".join(lines)


def explore(repo: pathlib.Path, entry: dict[str, Any], *, seconds: int) -> dict[str, Any]:
    started = time.time()
    commit, test_path = entry["commit"], entry["test"]
    row: dict[str, Any] = {"repo": entry.get("repo"), "commit": commit, "test": test_path,
                           "parameters_stored": 0}
    with __import__("tempfile").TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                                str(worktree), f"{commit}^"],
                               capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "stage": "WORKTREE_FAILED"}
        try:
            (worktree / test_path).write_text(identify.show(repo, commit, test_path),
                                              encoding="utf-8")
            baseline = run_tests(worktree, [test_path], seconds)
            # An empty verdict map (collection error, missing dependency, strict
            # config warning) or a timeout is NOT evidence that the parent passes.
            if not baseline or any(verdict.upper() == "TIMEOUT" for verdict in baseline.values()):
                return {**row, "stage": "NO_ORACLE",
                        "reason": "empty verdicts or timeout on the parent suite",
                        "seconds": round(time.time() - started, 2)}
            failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
            if not failing:
                return {**row, "stage": "NO_FAILING_TEST",
                        "seconds": round(time.time() - started, 2)}
            passing = [name for name, verdict in baseline.items() if verdict.upper() == "PASSED"]
            if not passing:
                return {**row, "stage": "NO_PASSING_TEST",
                        "seconds": round(time.time() - started, 2)}
            row.update({"failing_tests": sorted(failing)[:8], "baseline_verdicts": len(baseline)})
            files = entry.get("sources") or prior.source_files(repo, commit)
            if not files:
                return {**row, "stage": "NO_SOURCE_FILE",
                        "seconds": round(time.time() - started, 2)}
            source_path = files[0]
            target = worktree / source_path
            original = target.read_text(encoding="utf-8", errors="replace")

            # The human edit validates the judge only. Nothing about it is used to
            # choose, compile or rank a candidate.
            human_source = identify.show(repo, commit, source_path)
            if not human_source:
                return {**row, "stage": "NO_CONTROL",
                        "seconds": round(time.time() - started, 2)}
            target.write_text(human_source, encoding="utf-8")
            control_after = run_tests(worktree, [test_path], seconds)
            target.write_text(original, encoding="utf-8")
            control, why, witness = judge(baseline, control_after, [])
            row["control"] = {"accepted": control, "reason": why,
                              "flipped": witness[:8]}
            if not control:
                return {**row, "stage": "REFUSED__CONTROL_BROKEN",
                        "seconds": round(time.time() - started, 2)}

            sites = prior.guards(original)
            # The older engine's instrument() reads PROBE_MODULE from its module
            # global. Restore it immediately so a shared pytest process cannot
            # inherit our probe name and fail that engine's own tests.
            saved_module = prior.PROBE_MODULE
            prior.PROBE_MODULE = MODULE
            try:
                instrumented = prior.instrument(original, sites)
            finally:
                prior.PROBE_MODULE = saved_module
            if instrumented is None:
                return {**row, "stage": "INSTRUMENTATION_REFUSED",
                        "seconds": round(time.time() - started, 2)}
            (worktree / (MODULE + ".py")).write_text(PROBE_SOURCE, encoding="utf-8")
            probe_out = pathlib.Path(where) / "observations.jsonl"
            env = {"BRAIN_PROBE_OUT": str(probe_out)}
            target.write_text(instrumented, encoding="utf-8")
            run_tests(worktree, [test_path], seconds, extra_env=env)
            target.write_text(original, encoding="utf-8")
            observations = [json.loads(line) for line in probe_out.read_text().splitlines()
                            if line.strip()] if probe_out.exists() else []
            row["guard_sites"] = len(sites)
            row["observations"] = len(observations)
            candidates = learn(observations, set(failing), set(passing), sites)
            row["learned"] = [{"line": c["line"], "text": c["text"],
                               "feature": c["feature"], "polarity": c["polarity"],
                               "gain": c["gain"], "pass_mismatches": c["pass_mismatches"],
                               "observed_value": c["observed_value"]} for c in candidates]
            attempts = 0
            for candidate in candidates:
                expression = compile_rule(candidate)
                if expression is None:
                    continue
                patched = replace(original, candidate, expression)
                if patched is None:
                    continue
                attempts += 1
                target.write_text(patched, encoding="utf-8")
                # A cheap witness run first: a predicate that does not flip a single
                # failing test is not worth a whole suite run.
                quick = run_tests(worktree, sorted(failing)[:8], seconds)
                if not any(quick.get(name, "").upper() == "PASSED" for name in failing):
                    target.write_text(original, encoding="utf-8")
                    continue
                after = run_tests(worktree, [test_path], seconds)
                target.write_text(original, encoding="utf-8")
                ok, reason, flipped = judge(baseline, after, witness)
                if ok:
                    row.update({"stage": "VERIFIED", "rule": candidate,
                                "replacement": expression, "attempts": attempts,
                                "flipped": flipped,
                                "seconds": round(time.time() - started, 2)})
                    return row
            row.update({"stage": "NO_LEARNED_REPAIR" if candidates else "NO_SEPARATING_RULE",
                        "attempts": attempts, "seconds": round(time.time() - started, 2)})
            return row
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, Any]], *, repos_root: pathlib.Path,
          receipt: pathlib.Path, seconds: int,
          missed: set[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = repos_root / entry["repo"]
        try:
            row = explore(repo, entry, seconds=seconds)
        except Exception as error:  # noqa: BLE001
            row = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:200]}
        row.setdefault("repo", entry.get("repo"))
        row.setdefault("commit", entry.get("commit"))
        rows.append(row)
        verdict = {
            "L1_inputs_only": all(row.get("stage") != "EXCEPTION" for row in rows),
            "L2_real_witness_and_control": sum(row.get("control", {}).get("accepted", False)
                                               for row in rows),
            "L3_candidate_cap": all(len(row.get("learned", [])) <= 4 for row in rows),
            "L4_new_repair": sum(row.get("stage") == "VERIFIED" and
                                 str(row.get("commit", ""))[:10] in missed for row in rows),
            "L5_zeros": True,
        }
        receipt.write_text(json.dumps({
            "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-21",
            "mode": "LEARN_THE_DEMAND_FROM_THE_RUN", "declared_before_the_runs": DECLARED,
            "verdict": verdict, "all_criteria_met": verdict["L4_new_repair"] > 0
            and all(value is not False for value in verdict.values()),
            "rows": rows, "seconds": round(time.time() - started, 1),
            "cost": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0},
        }, indent=1) + "\n", encoding="utf-8")
        print(f"[{number}/{len(entries)}] {row['repo']} {str(row['commit'])[:10]} "
              f"{row['stage']} learned={len(row.get('learned', []))} "
              f"attempts={row.get('attempts')}", file=sys.stderr, flush=True)
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="")
    parser.add_argument("--missed-from", type=pathlib.Path, default=pathlib.Path(
        "canonical/verification/THE_RELATION_NOT_THE_VALUE_FORTY_FIVE_20261125_V1.json"))
    args = parser.parse_args(argv)
    payload = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload.get("tasks", payload))
    prior_rows = json.loads(args.missed_from.read_text(encoding="utf-8")).get("rows", [])
    missed = {str(row["commit"])[:10] for row in prior_rows
              if row.get("stage") != "VERIFIED"}
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries
                   if any(str(entry.get("commit", "")).startswith(w) for w in wanted)]
    if args.limit:
        entries = entries[:args.limit]
    report = sweep(entries, repos_root=args.repos_root, receipt=args.receipt,
                   seconds=args.seconds, missed=missed)
    stages: dict[str, int] = {}
    for row in report["rows"]:
        stages[row["stage"]] = stages.get(row["stage"], 0) + 1
    print(json.dumps({"rows": len(report["rows"]), "stages": stages,
                      "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
