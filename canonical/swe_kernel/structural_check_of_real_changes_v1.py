#!/usr/bin/env python3
"""Does a specification read off structure alone judge a REAL change -- with no test and no intent?

THE HOLE THIS FILLS
-------------------
Three rounds in this tree measured the same term from three sides:

  * reach: 75.2% of 2,178 real fix pieces are named by no operator any other task ever produced;
  * witness inversion: 18 of 18 real witnesses demanded content the artifact did not contain;
  * checkability: of 19 real commits that ship no test, 13 could be driven through their own public
    surface and 0 yielded a stable differential pin.

The last of those ended on a named lever rather than a conclusion: *construct the discriminating input*.
This module asks the cheapest question that decides whether that lever exists at all, and it asks it with
machinery the tree already owns. `canonical/swe_kernel/specification_from_structure_v1.py` derives laws from
a module's own names, arities, annotations and inverse pairs, confirms them by executing the module as it
stands, and refuses anything VACUOUS or REFUTED. Its published measurement is on THIS repository's code:
407 laws confirmed over 12 modules, 23 functions with a confirmed law, 8 mutants killed, blind-spot rate
0.652.

What had never been measured is the question this tree's bottleneck lives on:

    take a REAL commit. Confirm the laws of the module as it stands AFTER the change. Then hand the judge
    the module as it stood BEFORE the change. Does any confirmed law reject it?

If yes, then a checkable postcondition existed for that change without anybody writing a test and without
anybody stating an intent: the structure of the new code is itself the specification, and the old code is
the first thing it rejects. If no, then even a confirmed specification cannot see the change, and the
discriminating input really is knowledge that only intent or a test can supply.

WHAT THIS IS AND IS NOT
-----------------------
A kill is **effect certification, never intent verification**. A law confirmed on the fixed code rejects the
parent because the change altered the module's own structure-implied behaviour; it does not say the change
is what the user asked for. If the fixed code were wrong, the law would confirm on the wrong code and still
kill the parent. That distinction is carried in the receipt in those words, because the round it belongs to
is about which term binds, and a dishonest conversion would destroy the answer.

Nothing is modified: every state is a materialised checkout and every execution happens in the organ's own
bounded child. No model, no network, no parameters, nothing stored.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import specification_from_structure_v1 as structure  # noqa: E402  read, not modified
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402  materialisation seam

SCHEMA = "BRAIN_STRUCTURAL_CHECK_OF_REAL_CHANGES_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

MAX_FUNCTIONS_PER_MODULE = 12
MAX_LITERALS = 12
CALL_TIMEOUT_S = 0.4


def module_literals(source: str, limit: int = MAX_LITERALS) -> dict[str, list[Any]]:
    """Real geometry for the grid: the values this module already talks about, never invented ones."""
    pools: dict[str, list[Any]] = {"str": [], "int": []}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return pools
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, str) and 0 < len(value) <= 60 and value not in pools["str"]:
                pools["str"].append(value)
            elif isinstance(value, int) and not isinstance(value, bool) and value not in pools["int"]:
                pools["int"].append(value)
    pools["str"] = pools["str"][:limit]
    pools["int"] = pools["int"][:limit]
    return pools


def module_name_for(relative: str) -> str | None:
    parts = relative[:-3].split("/")
    while parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or None


def judge_one_module(module: str, parent_source: str, fixed_source: str) -> dict[str, Any]:
    """The organ's own pipeline, end to end: derive on the new code, then let its laws see the old code."""
    derived = structure.derive(fixed_source, module)
    functions = derived.get("functions") or []
    record: dict[str, Any] = {"module": module, "functions_offered": len(functions)}
    if not functions:
        record["state"] = "NO_PUBLIC_STRUCTURE"
        return record
    accepted = functions[:MAX_FUNCTIONS_PER_MODULE]
    narrowed = dict(derived)
    narrowed["functions"] = accepted
    variants = [{"variant_id": "parent::" + entry["name"], "function": entry["name"],
                 "source": parent_source} for entry in accepted]
    try:
        payload = structure.child_payload(module_name=module, baseline_source=fixed_source,
                                          derived=narrowed, variants=variants,
                                          call_timeout_s=CALL_TIMEOUT_S,
                                          extra_pools=module_literals(fixed_source))
        result = structure.run_child(payload, timeout_s=240.0)
    except (RuntimeError, ValueError) as exc:
        record["state"] = "ORGAN_FAILED"
        record["detail"] = str(exc)[:300]
        return record
    confirmations = result.get("confirmations") or []
    judgements = result.get("judgements") or []
    confirmed = [row for row in confirmations if row.get("verdict") == structure.CONFIRMED]
    not_applicable = [row for row in confirmations if row.get("verdict") == structure.NOT_APPLICABLE]
    vacuous = [row for row in confirmations if row.get("verdict") == structure.VACUOUS]
    refuted = [row for row in confirmations if row.get("verdict") == structure.REFUTED]

    kills, totality_only, unreadable = [], [], []
    for judged in judgements:
        killed_by = [item for item in (judged.get("killed_by") or [])]
        if not killed_by:
            continue
        if "IMPORT_FAILED" in killed_by:
            unreadable.append(judged["variant_id"])
            continue
        kinds = {identifier.split(":", 1)[0] for identifier in killed_by}
        if kinds == {"TOTALITY"}:
            totality_only.append(judged["variant_id"])
        else:
            kills.append({"function": judged.get("function"), "laws": killed_by,
                          "counterexample": judged.get("counterexample")})
    record.update({
        "laws_proposed": len(derived.get("invariants") or []),
        "laws_confirmed": len(confirmed),
        "laws_vacuous": len(vacuous),
        "laws_refuted": len(refuted),
        "laws_not_applicable": len(not_applicable),
        "functions_judged": len(judgements),
        "killed_by_a_law": len(kills),
        "killed_by_totality_only": len(totality_only),
        "parent_unreadable": len(unreadable),
        "kills": kills[:6],
        "functions_with_a_confirmed_law": len({row["function"] for row in confirmed}),
        "confirmed_kinds": {kind: sum(1 for row in confirmed if row.get("kind") == kind)
                            for kind in sorted({row.get("kind") for row in confirmed})},
    })
    if kills:
        record["state"] = "THE_CHANGE_IS_CHECKABLE_FROM_STRUCTURE_ALONE"
    elif totality_only or unreadable:
        record["state"] = "ONLY_TOTALITY_OR_UNREADABLE"
    else:
        record["state"] = "THE_LAWS_CANNOT_SEE_THE_CHANGE"
    return record


def commits_touching_sources(clone: pathlib.Path, old: str, new: str) -> list[dict[str, Any]]:
    """Real commits that change a source file, whether or not they ship a test."""
    log = witness._git("log", "--format=COMMIT|%H|%s", "--name-only", "%s..%s" % (old, new), cwd=clone)
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in log.splitlines():
        if line.startswith("COMMIT|"):
            if current:
                records.append(current)
            _, sha, message = line.split("|", 2)
            current = {"sha": sha, "message": message, "files": []}
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    if current:
        records.append(current)
    found: list[dict[str, Any]] = []
    for record in records:
        sources = [f for f in record["files"]
                   if f.endswith(".py") and "/tests/" not in f and not f.startswith("tests/")
                   and not pathlib.PurePosixPath(f).name.startswith("test_")]
        tests = [f for f in record["files"]
                 if f.endswith(".py") and ("/tests/" in f or pathlib.PurePosixPath(f).name.startswith("test_"))]
        if sources:
            found.append({"sha": record["sha"], "message": record["message"],
                          "sources": sources, "tests": tests})
    return found


def judge_commit(clone: pathlib.Path, commit: Mapping[str, Any], work: pathlib.Path) -> dict[str, Any]:
    """Both real states of one real commit, judged by the new code's own structure-derived laws."""
    parent_rev = witness._git("rev-parse", "%s^" % commit["sha"], cwd=clone).strip()
    parent_tree, note = witness.materialise(clone, parent_rev, work)
    fixed_tree, note_two = witness.materialise(clone, commit["sha"], work, suffix="-spec")
    record: dict[str, Any] = {"commit": commit["sha"], "message": commit["message"][:90],
                              "ships_a_test": bool(commit["tests"]), "sources": list(commit["sources"])}
    if parent_tree is None or fixed_tree is None:
        record["state"] = "NO_TREE"
        record["detail"] = note or note_two
        return record
    modules = []
    for relative in commit["sources"]:
        if not relative.endswith(".py"):
            continue
        parent_file, fixed_file = parent_tree / relative, fixed_tree / relative
        if not parent_file.is_file() or not fixed_file.is_file():
            continue
        module = module_name_for(relative)
        if module is None:
            continue
        modules.append(judge_one_module(module, parent_file.read_text(encoding="utf-8", errors="replace"),
                                        fixed_file.read_text(encoding="utf-8", errors="replace")))
    record["modules"] = modules
    record["killed_by_a_law"] = sum(row.get("killed_by_a_law", 0) for row in modules)
    record["laws_confirmed"] = sum(row.get("laws_confirmed", 0) for row in modules)
    record["state"] = ("THE_CHANGE_IS_CHECKABLE_FROM_STRUCTURE_ALONE"
                       if record["killed_by_a_law"] else
                       ("ORGAN_FAILED" if modules and all(row.get("state") in ("ORGAN_FAILED",)
                                                          for row in modules) else
                        "THE_LAWS_CANNOT_SEE_THE_CHANGE"))
    return record


def run_corpus(cache: pathlib.Path, work: pathlib.Path, limit: int = 40,
               only_untested: bool = False) -> dict[str, Any]:
    states: dict[str, int] = {"commits": 0, "with_tests": 0, "untested": 0, "judged": 0,
                              "checkable": 0, "kills": 0, "laws_confirmed": 0,
                              "organ_failed": 0, "only_totality": 0}
    rows: list[dict[str, Any]] = []
    for repo, old, new in witness.CORPUS_REPOS:
        if states["commits"] >= limit:
            break
        clone = witness.fetch(repo, old, new, cache)
        if clone is None:
            continue
        for commit in commits_touching_sources(clone, old, new):
            if states["commits"] >= limit:
                break
            states["commits"] += 1
            if commit["tests"]:
                states["with_tests"] += 1
                if only_untested:
                    continue
            else:
                states["untested"] += 1
            row = judge_commit(clone, commit, work)
            row["repo"] = repo
            rows.append(row)
            if row.get("modules"):
                states["judged"] += 1
            if row.get("killed_by_a_law"):
                states["checkable"] += 1
                states["kills"] += row["killed_by_a_law"]
            states["laws_confirmed"] += row.get("laws_confirmed", 0)
            if row.get("state") == "ORGAN_FAILED":
                states["organ_failed"] += 1
            if any(module.get("state") == "ONLY_TOTALITY_OR_UNREADABLE" for module in row.get("modules", [])):
                states["only_totality"] += 1
    return {"states": states, "commits": rows}


def _headline(report: Mapping[str, Any]) -> str:
    states = report["states"]
    judged = states.get("judged") or 0
    share = (states.get("checkable", 0) / judged) if judged else 0.0
    return (
        "%d real commits were taken at both states. The tree's own structural specifier -- laws read off a "
        "module's names, arities, annotations and inverse pairs, confirmed by executing the module as it "
        "stands -- confirmed %d laws across %d judged commits, and %d of those commits were rejected by one "
        "of those laws when the PRE-change module was put in front of the judge: %.1f%% of the judged set. "
        "That is a checkable postcondition for a real change with no test written and no intent stated -- "
        "but it certifies the EFFECT of the change, never that the change is what anyone wanted: a law "
        "confirmed on wrong code would reject its parent just the same. The remaining %.1f%% is invisible to "
        "structure, and that remainder is what only intent or a test can supply."
        % (states.get("commits", 0), states.get("laws_confirmed", 0), judged,
           states.get("checkable", 0), 100.0 * share, 100.0 * (1.0 - share)))


def measure(corpus: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "reused_not_rebuilt": {
            "organ": "canonical/swe_kernel/specification_from_structure_v1.py -- derive, build_grid, "
                     "child_payload, run_child, unchanged",
            "materialisation": "canonical/swe_kernel/witness_inversion_v1.py -- materialise and the repo "
                               "environment seam, unchanged",
            "prior_measurement": "canonical/verification/SPECIFICATION_FROM_STRUCTURE_20261116_V1.json -- "
                                 "407 laws confirmed on this repository, blind-spot rate 0.652",
        },
        "the_question": ("can a specification read off a module's own structure judge a real change, when no "
                         "test was written and no intent was stated? The parent of a real commit is put in "
                         "front of the judge as a variant, and the judge is the organ's own confirmed laws."),
        "what_a_kill_is": ("EFFECT CERTIFICATION, NEVER INTENT VERIFICATION. A law confirmed on the fixed "
                           "code rejects the parent because the change altered structure-implied behaviour. "
                           "It does not say the change is what was asked for, and a wrong change would be "
                           "confirmed and its parent rejected just the same."),
        "states": {"commits": 0, "with_tests": 0, "untested": 0, "judged": 0, "checkable": 0,
                   "kills": 0, "laws_confirmed": 0, "organ_failed": 0, "only_totality": 0},
        "commits": [],
    }
    if corpus is None:
        report["corpus"] = ("not fetched in this run: no clone cache and no network measurement. The organ "
                            "wiring is tested offline; the corpus number is producer-run and pinned by "
                            "commit in the receipt.")
        return report
    report.update(corpus)
    report["states"] = corpus["states"]
    report["what_this_shows"] = _headline(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Can structure alone judge a real change? Put the parent in front of the organ's judge.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--cache", default="/tmp/structure/cache")
    parser.add_argument("--work", default="/tmp/structure/work")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--only-untested", action="store_true")
    ns = parser.parse_args(argv)
    corpus = None
    if ns.corpus:
        corpus = run_corpus(pathlib.Path(ns.cache), pathlib.Path(ns.work), limit=ns.limit,
                            only_untested=ns.only_untested)
    report = measure(corpus)
    print(json.dumps({key: report[key] for key in ("schema", "states") if key in report}, indent=1))
    if "what_this_shows" in report:
        print(report["what_this_shows"])
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
