#!/usr/bin/env python3
"""Does a learned action survive being planned once and replayed onto a changed file?

THE CLAIM UNDER TEST
--------------------
"Learn the action once, then replay it forever." Replay has two halves that are usually confused:

  * the EDIT is a function of the state it was proved on -- the skill proves *that* state becomes
    an equivalent one, and nothing else;
  * the PLAN is the text edit that realization produced -- a set of line replacements.

A plan made on state S0 and applied to state S1 (S1 = S0 after some other step) is not covered by
the proof at all. This module measures how often that distinction is load-bearing on real code: for
real functions with several eligible sites, take an ordered pair of sites (A, B), let A run, and ask
three separate questions.

  1. Is B still eligible after A? (`DISABLED_BY_A` if not; `ENABLED_BY_A` if B only becomes
     eligible after A -- capability a snapshot plan cannot even see.)
  2. Does B, applied live, do what B says? (the skill's own proof, on the state it is applied to)
  3. Does B's PLAN, replayed onto the changed file, produce the same program as applying B live?

Question 3 is the one that decides "replay forever". The plan is extracted with `difflib` from the
real edit (no synthetic offsets), and replayed by line index onto the post-A file -- exactly what a
recorded macro does in a changed file, and what a recorded GUI action sequence does in a changed
window. A replay that parses but no longer performs the claimed edit is a SILENT CORRUPTION, and
that is counted separately from a replay that merely differs.

The operation is the bundle's own learned `inline` skill; the sites are real; the oracle is the
skill's own proof executed per step. No model is called: 0 calls, $0.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import pathlib
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import learned_skill_verdict_v1 as lv  # noqa: E402
from canonical.swe_kernel import one_demonstration_identifies_v1 as identify  # noqa: E402

SCHEMA = "action_replay_under_change_v1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
DEFAULT_PATTERN = "canonical/swe_kernel/*.py"
DEFAULT_PAIRS = 40
FOLLOW_UP_PER_FILE = 10


def inline_skill() -> dict[str, Any]:
    return identify.inline_skill()


def apply_skill(skill: Mapping[str, Any], path: str, function: str, variable: str, text: str, *,
                python_executable: str | None = None) -> dict[str, Any]:
    """Run the learned action on a given text and return what it did."""
    request = {"path0": path, "str1": function, "str0": variable}
    with tempfile.TemporaryDirectory(prefix="brain_replay_") as scratch:
        workdir = pathlib.Path(scratch)
        target = workdir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        run = lv.run_program(lv.source_with_request(skill, request), workdir=workdir,
                            python_executable=python_executable)
        after = target.read_text(encoding="utf-8")
    return {"performed": int(run.get("returncode") or 0) == 0, "after": after,
            "stdout": str(run.get("stdout") or "")[-200:],
            "reason": str(run.get("stdout") or "").strip().splitlines()[:1]}


def plan_of(before: str, after: str) -> list[tuple[int, int, list[str]]]:
    """The text plan a realization produces: replace lines [i1,i2) with these lines."""
    left = before.splitlines(keepends=True)
    right = after.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
    return [(i1, i2, right[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes()
            if tag != "equal"]


def replay_plan(plan: Sequence[tuple[int, int, list[str]]], text: str) -> str:
    """Apply a recorded plan to a file it was NOT made for, by line index. This is replay."""
    lines = text.splitlines(keepends=True)
    for i1, i2, replacement in sorted(plan, key=lambda item: item[0], reverse=True):
        if i1 > len(lines):
            continue
        lines[i1:i2] = replacement
    return "".join(lines)


def first_changed_index(before: str, after: str) -> int | None:
    """Zero-based index of the first line a plan changed, or None when nothing changed.

    `drift` in a record is the distance between the line a plan was written to edit and the line
    the live re-decision edited. Zero drift means the state did not move under the plan.
    """
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    for index, (left, right) in enumerate(zip(old, new)):
        if left != right:
            return index
    return None if len(old) == len(new) else min(len(old), len(new))


def edit_landed(text: str, function: str, variable: str) -> bool:
    """Did the claimed edit land? True exactly when `variable` is no longer bound in `function`.

    The operation's sentence is "this variable is inlined, so its binding is gone". The check reads
    the file, not the program's output, and answers only that sentence -- so `False` means the text
    still binds the name the operation said it removed, whatever else the text looks like.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for statement in node.body:
                for inner in ast.walk(statement):
                    if (isinstance(inner, ast.Name) and inner.id == variable
                            and isinstance(inner.ctx, ast.Store)):
                        return False
            return True
    return False


def eligible_sites(pattern: str = DEFAULT_PATTERN, *, limit: int = 400,
                   repo: pathlib.Path = ROOT,
                   python_executable: str | None = None) -> list[dict[str, Any]]:
    """Real sites where the learned operation actually performs, found by running it."""
    skill = inline_skill()
    universe, _scan = identify.reach.all_sites(repo=repo, pattern=pattern)
    by_file: dict[str, list[Mapping[str, Any]]] = {}
    for site in universe:
        by_file.setdefault(str(site["path"]), []).append(site)

    def attempt(site: Mapping[str, Any]) -> dict[str, Any] | None:
        text = (repo / str(site["path"])).read_text(encoding="utf-8")
        tried = apply_skill(skill, str(site["path"]), str(site["function"]),
                            str(site["variable"]), text,
                            python_executable=python_executable)
        if not tried["performed"]:
            return None
        return {"path": str(site["path"]), "function": str(site["function"]),
                "variable": str(site["variable"]), "after": tried["after"]}

    found: list[dict[str, Any]] = []
    tried_files: set[str] = set()
    # A cheap sample finds where the operation lives at all; then every remaining site
    # in a hit file is tested, because that is where a second replayable site can exist.
    for site in identify.reach.sample(universe, limit):
        path = str(site["path"])
        if path in tried_files:
            continue
        tried_files.add(path)
        hit = attempt(site)
        if hit is None:
            continue
        found.append(hit)
        for sibling in by_file[path][:FOLLOW_UP_PER_FILE]:
            if (str(sibling["function"]), str(sibling["variable"])) == (
                    str(site["function"]), str(site["variable"])):
                continue
            other = attempt(sibling)
            if other is not None:
                found.append(other)
    return found


def measure_pair(skill: Mapping[str, Any], first: Mapping[str, Any],
                 second: Mapping[str, Any], *,
                 python_executable: str | None = None) -> dict[str, Any]:
    path, function, variable = str(second["path"]), str(second["function"]), str(second["variable"])
    first_function, first_variable = str(first["function"]), str(first["variable"])
    original = (ROOT / path).read_text(encoding="utf-8")
    before_b = apply_skill(skill, path, function, variable, original,
                           python_executable=python_executable)
    step_a = apply_skill(skill, path, first_function, first_variable, original,
                         python_executable=python_executable)
    record: dict[str, Any] = {"path": path, "first": [first_function, first_variable],
                              "second": [function, variable],
                              "eligible_before": before_b["performed"]}
    if not step_a["performed"]:
        record["status"] = "FIRST_STEP_NOT_ELIGIBLE"
        return record
    live = apply_skill(skill, path, function, variable, step_a["after"],
                       python_executable=python_executable)
    record["eligible_after"] = live["performed"]
    if before_b["performed"] and not live["performed"]:
        record["status"] = "DISABLED_BY_THE_FIRST_STEP"
        return record
    if live["performed"] and not before_b["performed"]:
        record["status"] = "ENABLED_BY_THE_FIRST_STEP"
        return record
    if not (before_b["performed"] and live["performed"]):
        record["status"] = "NEITHER"
        return record
    plan = plan_of(original, before_b["after"])
    planned_at = min((span[0] for span in plan), default=None)
    live_at = first_changed_index(original, live["after"])
    replayed = replay_plan(plan, step_a["after"])
    record["planned_line"], record["live_line"] = planned_at, live_at
    record["drift"] = (None if planned_at is None or live_at is None else live_at - planned_at)
    record["replay_equals_live"] = replayed == live["after"]
    if replayed != live["after"]:
        try:
            ast.parse(replayed)
            parses = True
        except SyntaxError:
            parses = False
        record["replay_parses"] = parses
        record["replay_claims_the_edit"] = edit_landed(replayed, function, variable)
        if parses and not record["replay_claims_the_edit"]:
            record["status"] = "SILENT_CORRUPTION"
        elif not parses:
            record["status"] = "REPLAY_DOES_NOT_PARSE"
        else:
            record["status"] = "REPLAY_DIFFERS_BUT_HOLDS"
    else:
        record["status"] = "REPLAY_MATCHES_LIVE"
    return record


def _one_sample(pattern: str, *, pairs: int, candidates: int, index: int = 0,
                python_executable: str | None) -> dict[str, Any]:
    skill = inline_skill()
    sites = eligible_sites(pattern, limit=candidates, python_executable=python_executable)
    by_path: dict[str, list[dict[str, Any]]] = {}
    for site in sites:
        by_path.setdefault(site["path"], []).append(site)
    records: list[dict[str, Any]] = []
    for _path, members in sorted(by_path.items()):
        if len(members) < 2:
            continue
        for first in members:
            for second in members:
                if len(records) >= pairs:
                    break
                if (first["function"], first["variable"]) == (second["function"],
                                                               second["variable"]):
                    continue
                record = measure_pair(skill, first, second,
                                      python_executable=python_executable)
                record["sample"] = index
                records.append(record)
            if len(records) >= pairs:
                break
        if len(records) >= pairs:
            break
    return {"index": index, "candidates": candidates, "eligible_sites": len(sites),
            "files_with_two_eligible_sites": sum(1 for m in by_path.values() if len(m) >= 2),
            "records": records}


def measure(pattern: str = DEFAULT_PATTERN, *, pairs: int = DEFAULT_PAIRS,
            candidates: int = 400, samples: int = 1,
            python_executable: str | None = None) -> dict[str, Any]:
    """Independent samples of the same population; the spread is part of the answer."""
    runs = [_one_sample(pattern, pairs=pairs,
                        candidates=int(candidates * (1 + 0.3 * index)), index=index,
                        python_executable=python_executable)
            for index in range(max(1, samples))]
    seen: set[tuple[str, tuple[str, str], tuple[str, str]]] = set()
    records: list[dict[str, Any]] = []
    for run in runs:
        for record in run["records"]:
            key = (record["path"], tuple(record["first"]), tuple(record["second"]))
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    fingerprint = hashlib.sha256()
    for file in sorted(q for q in ROOT.glob(pattern) if q.is_file()):
        fingerprint.update(("%s:%d\n" % (file.relative_to(ROOT), file.stat().st_size)).encode())
    counts: dict[str, int] = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    comparable = [record for record in records
                  if record["status"] in {"REPLAY_MATCHES_LIVE", "REPLAY_DIFFERS_BUT_HOLDS",
                                          "SILENT_CORRUPTION", "REPLAY_DOES_NOT_PARSE"}]
    stale = [record for record in comparable if not record.get("replay_equals_live")]
    matches = [record for record in comparable if record.get("replay_equals_live")]
    per_sample: dict[int, dict[str, int]] = {}
    for record in records:
        bucket = per_sample.setdefault(int(record.get("sample", 0)), {})
        bucket[record["status"]] = bucket.get(record["status"], 0) + 1
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "pattern": pattern,
        "corpus_sha256": fingerprint.hexdigest(),
        "samples": [{"index": run["index"], "candidates": run["candidates"], "eligible_sites": run["eligible_sites"],
                     "files_with_two_eligible_sites": run["files_with_two_eligible_sites"],
                     "pairs": len(run["records"])} for run in runs],
        "eligible_sites_found": sum(run["eligible_sites"] for run in runs),
        "files_with_several_eligible_sites": sum(run["files_with_two_eligible_sites"]
                                                for run in runs),
        "pairs_measured": len(records),
        "counts": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
        "per_sample_counts": {str(key): dict(sorted(value.items()))
                              for key, value in sorted(per_sample.items())},
        "pairs_where_replay_was_possible": len(comparable),
        "pairs_where_the_recorded_plan_is_stale": len(stale),
        "silent_corruptions": counts.get("SILENT_CORRUPTION", 0),
        "drifts": sorted({record.get("drift") for record in stale
                          if record.get("drift") is not None}),
        "stale_at_zero_drift": sum(1 for record in stale if record.get("drift") == 0),
        "matches_at_zero_drift": sum(1 for record in matches if record.get("drift") == 0),
        "records": records,
        "what_this_shows": (
            "The operation stayed legal on the changed state in %d of %d pairs, so legality "
            "survived the change. The recorded plan did not: %d of %d replays are stale, %d of "
            "them produce a file that still parses while the binding the edit claimed to remove "
            "is still there, and %d of the %d correct replays had zero drift"
            % (len(comparable), len(records), len(stale), len(comparable),
               counts.get("SILENT_CORRUPTION", 0), sum(1 for r in matches if r.get("drift") == 0),
               len(matches))),
    }


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["%d independent samples, %d ordered pairs of learned operations on real files"
             % (len(report["samples"]), report["pairs_measured"])]
    for status, count in report["counts"].items():
        lines.append("  %-28s %d" % (status, count))
    for run in report["samples"]:
        bucket = report["per_sample_counts"].get(str(run["index"]), {})
        lines.append("  sample candidates=%d: eligible=%d, files with two=%d, pairs=%d, "
                     "corrupt=%d, stale=%d"
                     % (run["candidates"], run["eligible_sites"],
                        run["files_with_two_eligible_sites"], run["pairs"],
                        bucket.get("SILENT_CORRUPTION", 0),
                        sum(count for status, count in bucket.items()
                            if status != "REPLAY_MATCHES_LIVE")))
    lines.append("  recorded plan stale on %d of %d replayable pairs; silent corruptions %d"
                 % (report["pairs_where_the_recorded_plan_is_stale"],
                    report["pairs_where_replay_was_possible"], report["silent_corruptions"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Does a learned action survive being planned once and replayed onto a changed "
                    "file?")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--pairs", type=int, default=DEFAULT_PAIRS)
    parser.add_argument("--candidates", type=int, default=400)
    parser.add_argument("--samples", type=int, default=1)
    ns = parser.parse_args(argv)
    report = measure(ns.pattern, pairs=ns.pairs, candidates=ns.candidates, samples=ns.samples)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
