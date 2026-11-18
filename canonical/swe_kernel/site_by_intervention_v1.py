#!/usr/bin/env python3
"""Name the SITE by intervention instead of by textual occurrence.

WHY THIS EXISTS (the exact hole round 4 left)
---------------------------------------------
`instruction_contract_for_code_v1` compiled 2 of 40 real commit messages into a contract over the
environment's own callables, and BOTH were wrong at the fixed state, for one reason stated in its own
receipt:

    the value's textual site is not the callable that decides it.

`riscv64` occurs in the text of `_have_compatible_abi`, which returns False in both states; what the
commit changed is the generator that lists supported architectures. `--disable-gil` is a build flag named
in prose. Occurrence is not causation, and no amount of re-reading the message recovers the site.

The tree already owns the positive half of this. `interventional_goal_v1` states the theorem it rests on
in its own docstring:

    M5_NONINTERVENTIONAL_ROOT_CAUSE_IDENTIFIABILITY_001
    "UNIQUE_ROOT_CAUSE_IS_NOT_IDENTIFIABLE_IN GENERAL FROM DECLARED OBSERVATIONS ALONE"
    premises: NO_REPLAY_OR_INTERVENTION.

So this module changes exactly ONE thing and keeps everything else comparable:

    round 4 grounds a clause by TEXTUAL OCCURRENCE of the value in a callable;
    round 5 grounds it by DO-INTERVENTION on the value, and asks which callable's observable output moves.

A site is a callable plus a parameter position. The intervention is `f(..., position := value)` against
`f(..., position := other)`, where `other` is a counterfactual drawn from the module's OWN vocabulary --
another string literal the file itself contains -- and, last, the empty string. If nothing about the
call's observable outcome changes when the value changes, that callable does not decide the value's fate
and it is not the site, no matter how the sentence's words sit in its text.

REUSED, NOT REBUILT
-------------------
* `instruction_contract_for_code_v1` -- `named_values`, `direction_of`, `judge_contract`, `FILLERS`,
  `MAX_ARGUMENTS`, the clause language and its verdicts. The verdicts are therefore directly comparable
  with round 4's own numbers, clause for clause.
* `checkability_by_differential_pin_v1.execute.probe` -- one child process per tree, real imports, real
  exceptions, identity stripped from reprs.
* `structural_check_of_real_changes_v1` -- corpus enumeration, module naming.
* `witness_inversion_v1` -- materialisation of both states of a real commit.

NOT BUILT, DELIBERATELY: no model, no network at run time, no gradient, no fitted parameter, no knowledge
house. Every number is an exact count of executions that ran. `$0`, `K3 = 0`.

WHAT WOULD MAKE THIS A FALSE WIN
--------------------------------
A site that responds to the value is not yet a discriminating site: the commit may not have moved it.
Those two states are counted apart (`SITE_NAMED_BUT_THE_CHANGE_DID_NOT_MOVE_IT`), and a clause is only
called DISCRIMINATING by the round-4 judge itself, which requires the fixed state to hold and the parent
to fail. Reporting a responding site as a win would be the always-pass grader with a third layer of
indirection, and it is refused here by construction.

Authority NONE. Producer-run sandbox measurement. Not independent verification.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys
import tempfile
from typing import Any, Mapping, Sequence

_REPO = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.swe_kernel import instruction_contract_for_code_v1 as IC  # noqa: E402
from canonical.swe_kernel import structural_check_of_real_changes_v1 as corpus  # noqa: E402
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402
from canonical.swe_kernel import checkability_by_differential_pin_v1 as execute  # noqa: E402

SCHEMA = "BRAIN_SITE_BY_INTERVENTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MAX_SITES = 24
MAX_CONTRASTS = 2
MAX_CALLS = 96

REFUSED_NO_VALUE = IC.NO_VALUE
REFUSED_NO_DIRECTION = IC.NO_DIRECTION
REFUSED_NO_SITE_RESPONDS = "REFUSED__NO_SITE_RESPONDS_TO_THE_VALUE"
REFUSED_EVERY_SITE_RESPONDS = "REFUSED__EVERY_SITE_RESPONDS"
REFUSED_TOO_MANY_SITES = "REFUSED__MORE_CANDIDATE_SITES_THAN_THE_BUDGET"


# --------------------------------------------------------------------------- #
# candidate sites: every callable, not only the ones whose text mentions the value
# --------------------------------------------------------------------------- #
def candidate_sites(module_source: str) -> list[dict[str, Any]]:
    """Every module-level callable the prober can drive, one site per parameter position.

    Deliberately NOT filtered by occurrence: occurrence is the rule this module exists to replace. The
    filter is only mechanical -- it must be importable, callable with literals, and bounded in arity.
    """
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return []
    sites: list[dict[str, Any]] = []
    for function in tree.body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if function.args.vararg is not None or function.args.kwarg is not None:
            continue
        required = (len(function.args.posonlyargs) + len(function.args.args)
                    - len(function.args.defaults))
        if required > IC.MAX_ARGUMENTS:
            continue
        names = [argument.arg for argument in (list(function.args.posonlyargs) + list(function.args.args))]
        for index in range(max(required, 1)):
            sites.append({"function": function.name, "required": required, "value_index": index,
                          "arguments": names[:required]})
        if len(sites) >= MAX_SITES:
            break
    return sites[:MAX_SITES]


def counterfactuals(module_source: str, value: str) -> list[str]:
    """Counterfactual values drawn from the module's OWN vocabulary, never invented.

    A same-shape alternative the file already contains is the fairest contrast: it differs in the one way
    the sentence is about (which value) and agrees in every way the file already decided.
    """
    pool: list[str] = []
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                if 3 <= len(text) <= 60 and text != value and any(ch.isalnum() for ch in text):
                    if text not in pool:
                        pool.append(text)
    # the null always survives truncation: it is the one contrast that needs no vocabulary
    return pool[:max(MAX_CONTRASTS - 1, 1)] + [""]


SHAPES = ("scalar", "element")


def _encoded(value: str, shape: str) -> str:
    if shape == "scalar":
        return "=" + value
    return "@json:" + json.dumps([value])


def _tokens(site: Mapping[str, Any], value: str | None, shape: str = "scalar") -> list[str]:
    required = int(site.get("required") or 0)
    tokens = [IC.FILLERS[position % len(IC.FILLERS)] for position in range(required)]
    if required and value is not None:
        tokens[int(site.get("value_index") or 0)] = _encoded(value, shape)
    return tokens


def _calls(module: str, sites: Sequence[Mapping[str, Any]], value: str,
           contrasts: Sequence[str]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for shape in SHAPES:
        for site in sites:
            key = [site["function"], site["value_index"], shape]
            calls.append({"module": module, "function": site["function"],
                          "args": _tokens(site, value, shape), "_site": key, "_arm": "value"})
            for contrast in contrasts:
                calls.append({"module": module, "function": site["function"],
                              "args": _tokens(site, contrast, shape), "_site": key,
                              "_arm": "contrast"})
    return calls[:MAX_CALLS]


def _observable(outcome: Mapping[str, Any]) -> str:
    return "|".join(str(outcome.get(key) or "") for key in ("outcome", "type", "value_repr"))


def intervene(tree: pathlib.Path, module: str, sites: Sequence[Mapping[str, Any]], value: str,
              contrasts: Sequence[str]) -> dict[str, Any]:
    """ONE child process, every site, every arm. Returns what responded and what separated it."""
    calls = _calls(module, sites, value, contrasts)
    if not calls:
        return {"observations": [], "sensitive": {}, "probed": 0}
    stripped = [{key: item[key] for key in ("module", "function", "args")} for item in calls]
    outcomes = execute.probe(tree, stripped)
    observations: list[dict[str, Any]] = []
    sensitive: dict[str, Any] = {}
    for call, outcome in zip(calls, outcomes):
        key = "%s#%d#%s" % tuple(call["_site"])
        observations.append({"site": call["_site"], "arm": call["_arm"],
                             "args": call["args"], "observable": _observable(outcome)})
        if call["_arm"] == "value":
            sensitive.setdefault(key, {"value": _observable(outcome), "contrasts": [],
                                       "separated_by": None})
        else:
            entry = sensitive.setdefault(key, {"value": None, "contrasts": [], "separated_by": None})
            entry["contrasts"].append(_observable(outcome))
            if entry.get("value") is not None and _observable(outcome) != entry["value"] and not entry["separated_by"]:
                entry["separated_by"] = call["args"]
    responding = [key for key, entry in sensitive.items()
                  if entry.get("value") is not None
                  and any(item != entry["value"] for item in entry["contrasts"])]
    return {"observations": observations, "sensitive": sensitive, "responding": sorted(responding),
            "probed": len(calls)}


# --------------------------------------------------------------------------- #
# the comparison: the same instruction, two grounding rules
# --------------------------------------------------------------------------- #
def judge_instruction(clone: pathlib.Path, commit: Mapping[str, Any], work: pathlib.Path) -> dict[str, Any]:
    instruction = commit["message"]
    parent_rev = witness._git("rev-parse", "%s^" % commit["sha"], cwd=clone).strip()
    parent_tree, note = witness.materialise(clone, parent_rev, work)
    fixed_tree, note_two = witness.materialise(clone, commit["sha"], work, suffix="-site")
    row: dict[str, Any] = {"commit": commit["sha"], "instruction": instruction[:120],
                           "ships_a_test": bool(commit["tests"]), "sources": list(commit["sources"])}
    if parent_tree is None or fixed_tree is None:
        row["state"] = "NO_TREE"
        row["detail"] = note or note_two
        return row
    values = IC.named_values(instruction)
    direction = IC.direction_of(instruction)
    row["values"] = values
    row["direction"] = direction
    if not values:
        row["state"] = REFUSED_NO_VALUE
        row["modules"] = []
        return row
    if direction is None:
        row["state"] = REFUSED_NO_DIRECTION
        row["modules"] = []
        return row
    judged: list[dict[str, Any]] = []
    for relative in commit["sources"]:
        if not relative.endswith(".py"):
            continue
        fixed_file, parent_file = fixed_tree / relative, parent_tree / relative
        if not fixed_file.is_file() or not parent_file.is_file():
            continue
        module = corpus.module_name_for(relative)
        if module is None:
            continue
        source = fixed_file.read_text(encoding="utf-8", errors="replace")
        sites = candidate_sites(source)
        entry: dict[str, Any] = {"module": module, "sites_considered": len(sites)}
        if not sites:
            entry["state"] = REFUSED_NO_SITE_RESPONDS
            judged.append(entry)
            continue
        value = values[0]
        contrasts = counterfactuals(source, value)
        entry["contrasts"] = contrasts
        fixed_result = intervene(fixed_tree, module, sites, value, contrasts)
        entry["probed_on_fixed"] = fixed_result["probed"]
        if not fixed_result["responding"]:
            entry["state"] = REFUSED_NO_SITE_RESPONDS
            judged.append(entry)
            continue
        if len(fixed_result["responding"]) == len({"%s#%d#%s" % (site["function"], site["value_index"], shape)
                                                  for site in sites for shape in SHAPES}):
            entry["state"] = REFUSED_EVERY_SITE_RESPONDS
            entry["responding"] = fixed_result["responding"]
            judged.append(entry)
            continue
        # a responding site is a candidate, not a verdict: the change must have moved it. Ask the
        # round-4 judge itself, at that site, so the verdicts are the same language.
        best: dict[str, Any] | None = None
        for key in fixed_result["responding"]:
            function, index, shape = key.rsplit("#", 2)
            clause = {"operator": {"WIDENING": "ACCEPTS_NAMED", "NARROWING": "REJECTS_NAMED",
                                   "REPAIR": "STILL_RUNS"}[direction],
                      "value": value, "function": function, "required": len(
                          next((site["arguments"] for site in sites
                                if site["function"] == function), [])),
                      "value_index": int(index), "direction": direction, "shape": shape}
            contract = {"clauses": [clause], "refusals": [], "direction": direction}
            outcome = IC.judge_contract(contract, module, parent_tree, fixed_tree)
            clause_row = dict(outcome["clauses"][0]) if outcome["clauses"] else {"verdict": outcome["verdict"]}
            clause_row["site"] = key
            clause_row["shape"] = shape
            clause_row["separated_by"] = fixed_result["sensitive"][key]["separated_by"]
            if best is None or (clause_row.get("verdict") == "DISCRIMINATING"
                                and best.get("verdict") != "DISCRIMINATING"):
                best = clause_row
            if clause_row.get("verdict") == "DISCRIMINATING":
                best = clause_row
                break
        entry["responding"] = fixed_result["responding"]
        entry["site"] = best
        entry["state"] = {"DISCRIMINATING": "SITE_NAMED_AND_DISCRIMINATING",
                          "VACUOUS": "SITE_NAMED_BUT_THE_CHANGE_DID_NOT_MOVE_IT",
                          "WRONG_AT_FIXED": "SITE_NAMED_BUT_WRONG_AT_THE_FIXED_STATE",
                          "UNCHECKABLE": "SITE_NAMED_BUT_UNCHECKABLE"}.get(
                              (best or {}).get("verdict"), "SITE_NAMED_BUT_UNCHECKABLE")
        judged.append(entry)
    row["modules"] = judged
    states = {entry.get("state") for entry in judged}
    for winner in ("SITE_NAMED_AND_DISCRIMINATING", "SITE_NAMED_BUT_WRONG_AT_THE_FIXED_STATE",
                   "SITE_NAMED_BUT_THE_CHANGE_DID_NOT_MOVE_IT"):
        if winner in states:
            row["state"] = winner
            break
    else:
        row["state"] = (REFUSED_EVERY_SITE_RESPONDS if REFUSED_EVERY_SITE_RESPONDS in states
                        else REFUSED_NO_SITE_RESPONDS)
    return row


# --------------------------------------------------------------------------- #
# corpus
# --------------------------------------------------------------------------- #
def run_corpus(cache: pathlib.Path, work: pathlib.Path, limit: int = 40) -> dict[str, Any]:
    states: dict[str, int] = {"commits": 0, "with_tests": 0, "untested": 0,
                              "site_named": 0, "site_named_and_discriminating": 0,
                              "site_named_but_change_did_not_move_it": 0,
                              "site_named_but_wrong_at_the_fixed_state": 0,
                              "refused": 0}
    census: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for repo, old, new in witness.CORPUS_REPOS:
        if states["commits"] >= limit:
            break
        clone = witness.fetch(repo, old, new, cache)
        if clone is None:
            continue
        for commit in corpus.commits_touching_sources(clone, old, new):
            if states["commits"] >= limit:
                break
            states["commits"] += 1
            states["with_tests" if commit["tests"] else "untested"] += 1
            row = judge_instruction(clone, commit, work)
            row["repo"] = repo
            rows.append(row)
            state = row.get("state")
            if state and state.startswith("SITE_NAMED"):
                states["site_named"] += 1
                if state == "SITE_NAMED_AND_DISCRIMINATING":
                    states["site_named_and_discriminating"] += 1
                elif state == "SITE_NAMED_BUT_THE_CHANGE_DID_NOT_MOVE_IT":
                    states["site_named_but_change_did_not_move_it"] += 1
                elif state == "SITE_NAMED_BUT_WRONG_AT_THE_FIXED_STATE":
                    states["site_named_but_wrong_at_the_fixed_state"] += 1
            else:
                states["refused"] += 1
            key = state or "UNKNOWN"
            census[key] = census.get(key, 0) + 1
    return {"states": states, "verdict_census": census, "commits": rows}


def measure(report: Mapping[str, Any] | None) -> dict[str, Any]:
    body = dict(report or {"states": {}, "verdict_census": {}, "commits": []})
    body["schema"] = SCHEMA
    body["authority"] = AUTHORITY
    body["model_calls"] = 0
    body["network_calls"] = 0
    body["incremental_spend_usd"] = 0
    body["the_one_rule_that_changed"] = (
        "grounding: round 4 asked where the sentence's value OCCURS in a callable; round 5 asks whose "
        "observable output MOVES when the value is intervened on. Everything else -- the value reader, the "
        "direction reader, the clause language, FILLERS, MAX_ARGUMENTS, judge_contract and all four "
        "verdicts -- is imported from round 4 unchanged, so the two receipts are clause-for-clause comparable.")
    body["reused_not_rebuilt"] = {
        "compiler": "canonical/swe_kernel/instruction_contract_for_code_v1.py -- named_values, direction_of, "
                    "judge_contract, FILLERS, MAX_ARGUMENTS, read only",
        "execution": "canonical/swe_kernel/checkability_by_differential_pin_v1.py -- execute.probe, read only",
        "corpus": "canonical/swe_kernel/structural_check_of_real_changes_v1.py -- commits_touching_sources, "
                  "module_name_for, read only",
        "materialisation": "canonical/swe_kernel/witness_inversion_v1.py -- materialise, fetch, read only",
        "the_theory": "canonical/swe_kernel/interventional_goal_v1.py and "
                      "canonical/capabilities/opus55/M5_NONINTERVENTIONAL_ROOT_CAUSE_IDENTIFIABILITY_001.json -- "
                      "a single observational trace does not identify a cause; a DO-intervention does",
    }
    return body


def _headline(report: Mapping[str, Any]) -> str:
    states = report.get("states") or {}
    census = report.get("verdict_census") or {}
    parts = ", ".join("%s %d" % (kind.replace("_", " "), count)
                      for kind, count in sorted(census.items(), key=lambda item: -item[1]))
    return (
        "%d real commits, each handed its own message. %d named a value the environment RESPONDS to at a "
        "callable the message never had to point at; %d of those are DISCRIMINATING by round 4's own judge "
        "(the fixed state holds and the parent fails), %d responded but the change did not move them, and %d "
        "responded but are wrong at the fixed state. %d were refused by name. Census: %s."
        % (states.get("commits", 0), states.get("site_named", 0),
           states.get("site_named_and_discriminating", 0),
           states.get("site_named_but_change_did_not_move_it", 0),
           states.get("site_named_but_wrong_at_the_fixed_state", 0),
           states.get("refused", 0), parts or "none"))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Name the site by intervention, not by occurrence.")
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--cache", type=pathlib.Path, default=pathlib.Path("/tmp/site-cache"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/site-work"))
    args = parser.parse_args(argv)
    if not args.corpus:
        print(_headline(measure(None)))
        return 0
    args.work.mkdir(parents=True, exist_ok=True)
    report = measure(run_corpus(args.cache, args.work, limit=args.limit))
    if args.json:
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", args.json)
    print(_headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
