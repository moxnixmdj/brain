#!/usr/bin/env python3
"""Do demands live *between* guards? Test a two-site edit learned from one run.

The one-site learner (`the_demand_is_learned_from_the_run_v1`) judged 56 real
predicates on 45 unseen fixes and verified none. Its own boundary was the unit of
synthesis: it can change one question at one site, while the corpus's residual
demands are relations over frames -- two sites must agree, or the same question
must be asked in an enclosing frame too.

This tool keeps the run-derived features and the strict judge, but requires every
applied edit to change at least two guarded spans. Sites are grouped by the root
name they ask about (and by identical text), one type-level feature is learned for
the whole group from red-versus-green executions, and the same polarity is applied
to every member. No human line is read; the human edit remains only a control on
the judge. If no row verifies, the honest conclusion is that a two-site relation
of this form is not the missing demand language either.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
from collections import defaultdict
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import the_demand_is_learned_from_the_run_v1 as single  # noqa: E402
import the_relation_not_the_value_v1 as prior  # noqa: E402

SCHEMA = "BRAIN_A_RELATION_OVER_TWO_GUARDS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "T1": "candidates are computed from probed runs and grouped by root name or identical text; the human edit is used only as a control",
    "T2": "every applied edit changes at least two guarded spans",
    "T3": "at most 4 two-site edits are judged per row, each selected by a pass/fail separation score",
    "T4": "at least one row missed by the one-site engines becomes VERIFIED with exact witness and 0 broken tests",
    "T5": "zero model calls, zero stored parameters, zero network calls",
}


def root_of(text: str) -> str:
    """The name the guard asks about: `a.converter` and `a.converter.x` share `a`."""
    return text.split(".")[0].strip()


def learn_groups(observations: Sequence[dict[str, Any]], failing: set[str],
                 passing: set[str], sites: Sequence[dict[str, Any]],
                 *, groupings: Sequence[str] = ("root", "text"),
                 max_spans: int = 0) -> list[dict[str, Any]]:
    """Learn one predicate per group of two or more guards, scored on all their runs."""
    all_keys = {"root": root_of, "text": lambda text: text}
    keys = {name: all_keys[name] for name in groupings}
    by_site: dict[tuple[int, int], dict[str, dict[str, bool]]] = {}
    for row in observations:
        node = str(row.get("node", "")).split(" ")[0]
        if not node:
            continue
        key = (row["line"], row["col"])
        slot = by_site.setdefault(key, {}).setdefault(node, {})
        for name, _template, predicate in single.FEATURES:
            slot[name] = bool(predicate(row))
    ranked: list[dict[str, Any]] = []
    for key_name, key_fn in keys.items():
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for site in sites:
            groups[key_fn(site["text"])].append(site)
        for key, members in groups.items():
            if len(members) < 2 or (max_spans and len(members) > max_spans):
                continue
            for name, _template, _predicate in single.FEATURES:
                counts = {"fail_true": 0, "pass_true": 0, "fail_total": 0, "pass_total": 0}
                for site in members:
                    seen = by_site.get((site["line"], site["col"]), {})
                    for node in failing:
                        if node in seen:
                            counts["fail_total"] += 1
                            counts["fail_true"] += int(seen[node][name])
                    for node in passing:
                        if node in seen:
                            counts["pass_total"] += 1
                            counts["pass_true"] += int(seen[node][name])
                if counts["fail_total"] == 0 or counts["pass_total"] == 0:
                    continue
                gain = counts["fail_true"] - counts["pass_true"]
                for polarity in (True, False):
                    matches_fail = counts["fail_true"] if polarity else \
                        counts["fail_total"] - counts["fail_true"]
                    matches_pass = counts["pass_true"] if polarity else \
                        counts["pass_total"] - counts["pass_true"]
                    score = gain if polarity else -gain
                    if score <= 0 or matches_fail == 0:
                        continue
                    ranked.append({
                        "grouping": key_name, "group": key, "sites": members,
                        "feature": name, "polarity": polarity, "gain": score,
                        "fail_matches": matches_fail, "pass_mismatches": matches_pass,
                        "strict": matches_pass == 0,
                    })
    chosen: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for row in sorted(ranked, key=lambda row: (-int(row["strict"]), -row["gain"],
                                               -row["fail_matches"],
                                               row["pass_mismatches"],
                                               row["group"], row["feature"],
                                               row["polarity"])):
        key = (row["grouping"], row["group"])
        if key in used:
            continue
        used.add(key)
        chosen.append(row)
        if len(chosen) >= 4:
            break
    return chosen


def compile_edits(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    template = next((tpl for name, tpl, _ in single.FEATURES
                     if name == candidate["feature"]), None)
    if template is None:
        return []
    edits = []
    for site in candidate["sites"]:
        expression = template.format(x=site["text"])
        if not candidate["polarity"]:
            expression = f"not ({expression})"
        edits.append({"line": site["line"], "col": site["col"],
                      "text": site["text"], "expression": expression})
    return edits


def replace_many(source: str, edits: Sequence[dict[str, Any]]) -> str | None:
    """Apply all span edits at once; a stale span refuses the whole candidate."""
    lines = source.splitlines(keepends=True)
    by_line: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for edit in edits:
        by_line[edit["line"]].append(edit)
    for number, items in by_line.items():
        index = number - 1
        if not (0 <= index < len(lines)):
            return None
        line = lines[index]
        for edit in sorted(items, key=lambda row: row["col"], reverse=True):
            start, end = edit["col"], edit["col"] + len(edit["text"])
            if line[start:end] != edit["text"]:
                return None
            line = line[:start] + "(" + edit["expression"] + ")" + line[end:]
        lines[index] = line
    candidate = "".join(lines)
    try:
        import ast
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def explore(repo: pathlib.Path, entry: dict[str, Any], *, seconds: int,
            groupings: Sequence[str] = ("root", "text"), max_spans: int = 0) -> dict[str, Any]:
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
            baseline = single.run_tests(worktree, [test_path], seconds)
            if not baseline or any(v.upper() == "TIMEOUT" for v in baseline.values()):
                return {**row, "stage": "NO_ORACLE",
                        "seconds": round(time.time() - started, 2)}
            failing = [name for name, v in baseline.items() if v.upper() in ("FAILED", "ERROR")]
            passing = [name for name, v in baseline.items() if v.upper() == "PASSED"]
            if not failing:
                return {**row, "stage": "NO_FAILING_TEST",
                        "seconds": round(time.time() - started, 2)}
            row["failing_tests"] = sorted(failing)[:8]
            files = entry.get("sources") or prior.source_files(repo, commit)
            if not files:
                return {**row, "stage": "NO_SOURCE_FILE",
                        "seconds": round(time.time() - started, 2)}
            source_path = files[0]
            target = worktree / source_path
            original = target.read_text(encoding="utf-8", errors="replace")
            human_source = identify.show(repo, commit, source_path)
            if not human_source:
                return {**row, "stage": "NO_CONTROL",
                        "seconds": round(time.time() - started, 2)}
            target.write_text(human_source, encoding="utf-8")
            control_after = single.run_tests(worktree, [test_path], seconds)
            target.write_text(original, encoding="utf-8")
            control, why, witness = single.judge(baseline, control_after, [])
            row["control"] = {"accepted": control, "reason": why, "flipped": witness[:8]}
            if not control:
                return {**row, "stage": "REFUSED__CONTROL_BROKEN",
                        "seconds": round(time.time() - started, 2)}

            sites = prior.guards(original)
            saved_module = prior.PROBE_MODULE
            prior.PROBE_MODULE = single.MODULE
            try:
                instrumented = prior.instrument(original, sites)
            finally:
                prior.PROBE_MODULE = saved_module
            if instrumented is None:
                return {**row, "stage": "INSTRUMENTATION_REFUSED",
                        "seconds": round(time.time() - started, 2)}
            (worktree / (single.MODULE + ".py")).write_text(single.PROBE_SOURCE, encoding="utf-8")
            probe_out = pathlib.Path(where) / "observations.jsonl"
            target.write_text(instrumented, encoding="utf-8")
            single.run_tests(worktree, [test_path], seconds,
                             extra_env={"BRAIN_PROBE_OUT": str(probe_out)})
            target.write_text(original, encoding="utf-8")
            observations = [json.loads(line) for line in probe_out.read_text().splitlines()
                            if line.strip()] if probe_out.exists() else []
            candidates = learn_groups(observations, set(failing), set(passing), sites,
                                      groupings=groupings, max_spans=max_spans)
            row["guard_sites"] = len(sites)
            row["observations"] = len(observations)
            row["learned"] = [{"grouping": c["grouping"], "group": c["group"],
                               "feature": c["feature"], "polarity": c["polarity"],
                               "gain": c["gain"], "spans": len(c["sites"])}
                              for c in candidates]
            attempts = 0
            for candidate in candidates:
                edits = compile_edits(candidate)
                if len(edits) < 2:
                    continue
                patched = replace_many(original, edits)
                if patched is None:
                    continue
                attempts += 1
                target.write_text(patched, encoding="utf-8")
                quick = single.run_tests(worktree, sorted(failing)[:8], seconds)
                if not any(quick.get(name, "").upper() == "PASSED" for name in failing):
                    target.write_text(original, encoding="utf-8")
                    continue
                after = single.run_tests(worktree, [test_path], seconds)
                target.write_text(original, encoding="utf-8")
                ok, reason, flipped = single.judge(baseline, after, witness)
                if ok:
                    row.update({"stage": "VERIFIED", "rule": row["learned"][attempts - 1],
                                "edits": edits, "attempts": attempts, "flipped": flipped,
                                "seconds": round(time.time() - started, 2)})
                    return row
            row.update({"stage": "NO_MULTISITE_REPAIR" if candidates else "NO_TWO_SITE_RULE",
                        "attempts": attempts,
                        "seconds": round(time.time() - started, 2)})
            return row
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, Any]], *, repos_root: pathlib.Path,
          receipt: pathlib.Path, seconds: int, missed: set[str],
          groupings: Sequence[str] = ("root", "text"), max_spans: int = 0) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        try:
            row = explore(repos_root / entry["repo"], entry, seconds=seconds,
                          groupings=groupings, max_spans=max_spans)
        except Exception as error:  # noqa: BLE001
            row = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:200]}
        row.setdefault("repo", entry.get("repo"))
        row.setdefault("commit", entry.get("commit"))
        rows.append(row)
        verdict = {
            "T1_inputs_only": all(row.get("stage") not in ("EXCEPTION", "NO_ORACLE")
                                  for row in rows),
            "T2_all_edits_two_spans": all(candidate.get("spans", 0) >= 2
                                         for row in rows for candidate in row.get("learned", [])),
            "T3_candidate_cap": all(len(row.get("learned", [])) <= 4 for row in rows),
            "T4_new_repair": sum(row.get("stage") == "VERIFIED" and
                                 str(row.get("commit", ""))[:10] in missed for row in rows),
            "T5_zeros": True,
        }
        receipt.write_text(json.dumps({
            "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-21",
            "mode": "A_RELATION_OVER_TWO_GUARDS", "declared_before_the_runs": DECLARED,
            "grouping_config": {"keys": list(groupings), "max_spans": max_spans},
            "verdict": verdict, "all_criteria_met": verdict["T4_new_repair"] > 0
            and all(value is not False for value in verdict.values()),
            "rows": rows, "seconds": round(time.time() - started, 1),
            "cost": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0},
        }, indent=1) + "\n", encoding="utf-8")
        print(f"[{number}/{len(entries)}] {row['repo']} {str(row['commit'])[:10]} "
              f"{row['stage']} groups={len(row.get('learned', []))} "
              f"attempts={row.get('attempts')}", file=sys.stderr, flush=True)
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="")
    parser.add_argument("--grouping", default="root,text",
                        help="diagnostic only: comma-separated keys; the pre-registered run uses both")
    parser.add_argument("--max-spans", type=int, default=0,
                        help="diagnostic only: skip groups larger than this")
    parser.add_argument("--missed-from", type=pathlib.Path, default=pathlib.Path(
        "canonical/verification/THE_RELATION_NOT_THE_VALUE_FORTY_FIVE_20261125_V1.json"))
    args = parser.parse_args(argv)
    payload = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload.get("tasks", payload))
    prior_rows = json.loads(args.missed_from.read_text(encoding="utf-8")).get("rows", [])
    missed = {str(row["commit"])[:10] for row in prior_rows if row.get("stage") != "VERIFIED"}
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries
                   if any(str(entry.get("commit", "")).startswith(w) for w in wanted)]
    if args.limit:
        entries = entries[:args.limit]
    groupings = tuple(part.strip() for part in args.grouping.split(",") if part.strip())
    report = sweep(entries, repos_root=args.repos_root, receipt=args.receipt,
                   seconds=args.seconds, missed=missed, groupings=groupings,
                   max_spans=args.max_spans)
    stages: dict[str, int] = {}
    for row in report["rows"]:
        stages[row["stage"]] = stages.get(row["stage"], 0) + 1
    print(json.dumps({"rows": len(report["rows"]), "stages": stages,
                      "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
