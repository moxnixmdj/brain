#!/usr/bin/env python3
"""Compile a stated instruction into a checkable pair for CODE, with no model and no test.

WHY THIS EXISTS
---------------
Four rounds measured four answers to one question, and each was a zero with a named cause:

  * reach: 75.2% of real fix pieces are named by no operator another task ever produced;
  * witness inversion: 18 of 18 real witnesses demanded content the artifact did not contain;
  * checkability by behaviour: 0 of 13 drivable unguarded commits yielded a stable pin, and the artifact's
    own doctests discriminate 0 times;
  * checkability by structure: 40 commits, 188 confirmed laws, 0 kills -- and 174 of those laws were bare
    totality, so structure can barely state a law about real code.

The cause common to all four: **real work extends a specification instead of violating a property**, so the
specification is not inside the artifact. It is inside the one place nobody had compiled: the sentence that
asked for the work.

The tree already compiled a sentence into a check for COMPUTER USE -- `canonical/runtime/instruction_contract_v1.py`
turns "Click on the \"No\" button." into a trace contract, with a closed clause language and refusals named one
by one. Nothing did it for code. The 2026 field has converged on the same move from the other side, always with
a model in the compile phase: ContextCov compiles AGENTS.md prose into AST queries and shell shims, RefineAct
formalises instructions into Prolog, AgentGuardUtil compiles policy into typed executable rules, and the
"Compiled AI" line (arXiv 2604.05150) exists precisely to spend the model once and run without it. This module
is that compile step for code with NO model at all: the instruction's own named value, the environment's own
callable, the direction the instruction's own verb states, and execution as the only judge.

THE LANGUAGE, ALL OF IT
-----------------------
An instruction is compiled only when it supplies both halves of a discriminating pair:

    a VALUE the instruction names         ("Add riscv64 as a supported manylinux architecture" -> riscv64)
    a DIRECTION its verb states           (add/support/accept/allow -> WIDENING;  remove/reject/drop -> NARROWING)

and the value must be GROUNDED in the environment's own code -- it must occur inside a callable the module
defines, not merely in a comment. Then the clause is one of:

    ACCEPTS_NAMED     a call carrying the named value returns at the fixed state where it raised at the parent
    REJECTS_NAMED     the same call raises at the fixed state where it returned at the parent
    NAMED_IN_OUTCOME  the outcome at the fixed state contains the named value where the parent's did not
    STILL_RUNS        every probe that ran at the parent also runs at the fixed state (a regression clause:
                      it cannot discriminate, it can only refuse a change that broke something else)

Everything else is refused BY NAME, because a refusal is the census of what an oracle would need:

    REFUSED__NO_VALUE_IN_THE_INSTRUCTION                  the sentence names nothing checkable
    REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT    vocabulary insufficiency, named exactly
    REFUSED__THE_NAMED_VALUE_IS_NOT_IN_A_CALLABLE         it occurs only in prose or comments
    REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION              a value with no stated direction is not a pair
    REFUSED__NO_SINGLE_ARGUMENT_CALLABLE                  the value cannot be driven through a call

WHAT THIS IS AND IS NOT
-----------------------
A contract is checked in BOTH directions, and both are reported: it can PASS at the fixed state and FAIL at
the parent (DISCRIMINATING -- the pair was worth having), PASS at both (VACUOUS -- it cannot see the change),
or FAIL at the fixed state (WRONG -- the compilation itself is wrong). A compiler scored only on its successes
is the "always-pass grader" this tree has already refused once.

A contract says "the instruction's own named value is accepted here", never "the change is what the user
wanted". No model, no network, no parameters, nothing stored, and no file is modified.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as execute  # noqa: E402  execution seam
from canonical.swe_kernel import structural_check_of_real_changes_v1 as corpus  # noqa: E402  corpus seam
from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402  materialisation seam

SCHEMA = "BRAIN_INSTRUCTION_CONTRACT_FOR_CODE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

MAX_PROPOSALS = 4
MAX_CALLS = 12
MAX_ARGUMENTS = 2
FILLERS = ("empty_str", "a", "none")

NO_VALUE = "REFUSED__NO_VALUE_IN_THE_INSTRUCTION"
VALUE_NOT_IN_ENVIRONMENT = "REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT"
VALUE_NOT_IN_A_CALLABLE = "REFUSED__THE_NAMED_VALUE_IS_NOT_IN_A_CALLABLE"
NO_DIRECTION = "REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION"
NO_CALLABLE = "REFUSED__NO_SINGLE_ARGUMENT_CALLABLE"

#: The whole verb vocabulary. Two directions and one repair reading; everything else is refused, not guessed.
WIDENING = ("add", "support", "supports", "supported", "accept", "accepts", "allow", "allows", "enable",
            "enables", "recognise", "recognize", "handle", "handles", "include", "includes", "permit")
NARROWING = ("remove", "removes", "reject", "rejects", "disallow", "disallows", "drop", "drops", "disable",
             "disables", "forbid", "forbids", "ban", "bans", "retire")
REPAIR = ("fix", "fixes", "correct", "corrects", "repair", "repairs", "validate", "validates", "clamp",
          "clamps", "check", "checks", "detect", "detects")

_STOPWORDS = frozenset("""a an the and or but if then than that this these those for from with without into onto
to of in on at by as is are was were be been being it its it's we you they he she i not no yes all any some
more most much many few less least very just only also too so such can could should would may might must will
shall do does did done doing have has had having there here when where which who whom whose what why how""".split())

_QUOTED = re.compile(r'"([^"\n]{1,60})"|`([^`\n]{1,60})`|\'([^\'\n]{1,60})\'')
#: values a librarian would name: identifiers with a digit or an underscore, dotted/versioned tokens, flags
_VALUEISH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9]*(?:[_.][A-Za-z0-9]+)+"
                       r"|(?<![A-Za-z0-9_])[A-Za-z]*[0-9][A-Za-z0-9_.]*"
                       r"|(?<![A-Za-z0-9_])--?[A-Za-z][A-Za-z0-9-]*")


def named_values(instruction: str) -> list[str]:
    """What the sentence actually names. Quoted things first: a quote is the author pointing."""
    found: list[str] = []
    for match in _QUOTED.finditer(instruction):
        for group in match.groups():
            if group and group.strip():
                found.append(group.strip())
    for match in _VALUEISH.finditer(instruction):
        found.append(match.group(0))
    out: list[str] = []
    for value in found:
        # a fragment of a longer named value is the same naming said twice, not a second proposal
        if any(len(other) > len(value) and value in other for other in found):
            continue
        if len(value) < 3 or value.lower() in _STOPWORDS or value in out:
            continue
        out.append(value)
    return out[:MAX_PROPOSALS]


def direction_of(instruction: str) -> str | None:
    """The direction is what the sentence's own verb says -- never a word inside a value it names:
    "Support --disable-gil builds" widens, even though the flag it widens about contains `disable`."""
    sentence = instruction
    for value in named_values(instruction):
        sentence = sentence.replace(value, " ")
    words = re.findall(r"[a-z]+", sentence.lower())
    if any(word in NARROWING for word in words):
        return "NARROWING"
    if any(word in WIDENING for word in words):
        return "WIDENING"
    if any(word in REPAIR for word in words):
        return "REPAIR"
    return None


def ground_sites(value: str, module_source: str) -> tuple[list[dict[str, Any]], str | None]:
    """Every callable the value occurs in is a candidate site, and the choice between them is made by
    execution, not by which one happens to come first: a claim about a value is about the site where that
    value changes what happens."""
    if not value:
        return [], VALUE_NOT_IN_ENVIRONMENT
    try:
        tree = ast.parse(module_source)
    except SyntaxError:
        return [], VALUE_NOT_IN_ENVIRONMENT
    lowered = value.lower()
    sites: list[dict[str, Any]] = []
    for function in tree.body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        segment = ast.get_source_segment(module_source, function) or ""
        if lowered not in segment.lower():
            continue
        if function.args.vararg is not None or function.args.kwarg is not None:
            continue
        required = len(function.args.posonlyargs) + len(function.args.args) - len(function.args.defaults)
        if required > MAX_ARGUMENTS:
            continue
        names = [argument.arg for argument in (list(function.args.posonlyargs) + list(function.args.args))]
        names = names[:required]
        # one site per parameter position. Which parameter carries the named value is not decidable from
        # names -- "riscv64" shares no run with either `archs` or `executable` -- so it is decided the only
        # way this tree decides anything: by executing both and keeping the position that discriminates.
        for index in range(max(required, 1)):
            sites.append({"function": function.name, "required": required, "value_index": index,
                          "arguments": names})
    if sites:
        return sites, None
    if lowered in module_source.lower():
        return [], VALUE_NOT_IN_A_CALLABLE
    return [], VALUE_NOT_IN_ENVIRONMENT


def ground(value: str, module_source: str) -> dict[str, Any]:
    """The first candidate site, for callers that want one. Kept because refusal names must not change."""
    sites, refusal = ground_sites(value, module_source)
    if not sites:
        return {"grounded": False, "refusal": refusal}
    return {"grounded": True, **sites[0]}


def compile_contract(instruction: str, module: str, fixed_source: str) -> dict[str, Any]:
    """The compile step: a sentence plus the environment, or a refusal with the missing half named."""
    contract: dict[str, Any] = {"instruction": instruction, "module": module, "clauses": [], "refusals": []}
    values = named_values(instruction)
    if not values:
        contract["refusals"].append({"refusal": NO_VALUE, "why": "the sentence names nothing checkable"})
        return contract
    direction = direction_of(instruction)
    if direction is None:
        contract["refusals"].append({"refusal": NO_DIRECTION, "why": "no verb states what should happen",
                                     "values": values})
        return contract
    contract["direction"] = direction
    for value in values:
        grounded = ground(value, fixed_source)
        if not grounded.get("grounded"):
            contract["refusals"].append({"refusal": grounded.get("refusal"), "value": value,
                                         "function": grounded.get("function")})
            continue
        operator = {"WIDENING": "ACCEPTS_NAMED", "NARROWING": "REJECTS_NAMED",
                    "REPAIR": "STILL_RUNS"}[direction]
        contract["clauses"].append({"operator": operator, "value": value,
                                    "function": grounded["function"], "required": grounded["required"],
                                    "direction": direction})
    # a regression clause only means something beside a grounded clause: on its own it can neither
    # discriminate nor refuse, and a contract that is only STILL_RUNS is a refusal wearing a verdict
    if contract["clauses"]:
        contract["clauses"].append({"operator": "STILL_RUNS", "value": None, "function": None,
                                    "direction": direction})
    return contract


def _calls_for(clause: Mapping[str, Any], module: str) -> list[dict[str, Any]]:
    value = clause.get("value")
    if value is None or clause.get("function") is None:
        return []
    required = int(clause.get("required") or 0)
    index = int(clause.get("value_index") or 0)
    shape = str(clause.get("shape") or "scalar")
    encoded = ("=" + str(value)) if shape == "scalar" else ("@json:" + json.dumps([value]))
    tokens = [FILLERS[position % len(FILLERS)] for position in range(required)]
    if required:
        tokens[index] = encoded
    calls = [{"module": module, "function": clause["function"], "args": tokens}]
    # the same callable driven through values that are not the named one: the contrast that keeps a
    # widening clause from being satisfied by 'it returns now' for an unrelated reason
    for other in ("empty_str", "zero", "a"):
        contrast = [FILLERS[position % len(FILLERS)] for position in range(required)]
        if required:
            contrast[0] = other
        calls.append({"module": module, "function": clause["function"], "args": contrast})
    return calls[:MAX_CALLS]


_FALSY = {"false", "none", "0", "", "[]", "()", "{}", "set()", "frozenset()"}


def _succeeded(outcome: Mapping[str, Any]) -> bool:
    """Returning is not accepting. `supports_arch("riscv64") -> False` is the environment saying the named
    value is NOT accepted, so a bool that came back False must never satisfy an acceptance clause -- that
    would be the always-pass grader with one more layer of indirection."""
    if outcome.get("outcome") != "RETURNED":
        return False
    if outcome.get("type") == "bool":
        return bool(outcome.get("value_repr")) and str(outcome.get("value_repr")).lower() != "false"
    return str(outcome.get("value_repr")).strip().lower() not in _FALSY


def _text(outcome: Mapping[str, Any]) -> str:
    return " ".join(str(outcome.get(key) or "") for key in ("value_repr", "message_shape", "type"))


def judge_contract(contract: Mapping[str, Any], module: str, parent_tree: pathlib.Path,
                   fixed_tree: pathlib.Path) -> dict[str, Any]:
    """Both directions, always. A clause that changed nothing is vacuous; one that fails at the fixed state
    is a wrong compilation, and it is reported as one."""
    result: dict[str, Any] = {"clauses": [], "verdict": None}
    discriminating = 0
    vacuous = 0
    wrong = 0
    for index, clause in enumerate(contract.get("clauses") or []):
        calls = _calls_for(clause, module)
        if not calls:
            result["clauses"].append({"operator": clause["operator"], "verdict": "NOT_APPLICABLE"})
            continue
        before = execute.probe(parent_tree, calls)
        after = execute.probe(fixed_tree, calls)
        named = calls[0]
        parent_outcome = before[0] if before else {}
        fixed_outcome = after[0] if after else {}
        operator = clause["operator"]
        if operator == "ACCEPTS_NAMED":
            holds = _succeeded(fixed_outcome)
            held_at_parent = _succeeded(parent_outcome)
        elif operator == "REJECTS_NAMED":
            holds = not _succeeded(fixed_outcome) and fixed_outcome.get("outcome") == "RAISED"
            held_at_parent = not _succeeded(parent_outcome) and parent_outcome.get("outcome") == "RAISED"
        elif operator == "NAMED_IN_OUTCOME":
            holds = str(clause.get("value") or "").lower() in _text(fixed_outcome).lower()
            held_at_parent = str(clause.get("value") or "").lower() in _text(parent_outcome).lower()
        else:  # STILL_RUNS
            holds = True
            held_at_parent = True
            for entry_before, entry_after in zip(before, after):
                if entry_before.get("outcome") == "RETURNED" and entry_after.get("outcome") != "RETURNED":
                    holds = False
        if not holds:
            verdict = "WRONG_AT_FIXED"
            wrong += 1
        elif held_at_parent and operator != "STILL_RUNS":
            verdict = "VACUOUS"
            vacuous += 1
        elif operator == "STILL_RUNS":
            verdict = "PASS"
        else:
            verdict = "DISCRIMINATING"
            discriminating += 1
        result["clauses"].append({
            "operator": operator, "value": clause.get("value"), "verdict": verdict,
            "parent": {k: parent_outcome.get(k) for k in ("outcome", "type", "value_repr")},
            "fixed": {k: fixed_outcome.get(k) for k in ("outcome", "type", "value_repr")},
        })
    if wrong:
        result["verdict"] = "WRONG_AT_FIXED"
    elif discriminating:
        result["verdict"] = "DISCRIMINATING"
    elif vacuous:
        result["verdict"] = "VACUOUS"
    else:
        result["verdict"] = "UNCHECKABLE"
    result.update({"discriminating_clauses": discriminating, "vacuous_clauses": vacuous,
                   "wrong_clauses": wrong})
    return result


def judge_commit(clone: pathlib.Path, commit: Mapping[str, Any], work: pathlib.Path) -> dict[str, Any]:
    """One real commit: its own message is the stated instruction, exactly as a user's sentence would be."""
    parent_rev = witness._git("rev-parse", "%s^" % commit["sha"], cwd=clone).strip()
    parent_tree, note = witness.materialise(clone, parent_rev, work)
    fixed_tree, note_two = witness.materialise(clone, commit["sha"], work, suffix="-contract")
    record: dict[str, Any] = {"commit": commit["sha"], "instruction": commit["message"][:120],
                              "ships_a_test": bool(commit["tests"]), "sources": list(commit["sources"])}
    if parent_tree is None or fixed_tree is None:
        record["state"] = "NO_TREE"
        record["detail"] = note or note_two
        return record
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
        contract = compile_contract(commit["message"], module,
                                    fixed_file.read_text(encoding="utf-8", errors="replace"))
        if not contract["clauses"]:
            judged.append({"module": module, "refusals": contract["refusals"], "verdict": "REFUSED"})
            continue
        outcome = judge_contract(contract, module, parent_tree, fixed_tree)
        outcome["module"] = module
        outcome["refusals"] = contract["refusals"]
        outcome["direction"] = contract.get("direction")
        judged.append(outcome)
    record["modules"] = judged
    record["verdict"] = ("DISCRIMINATING" if any(item.get("verdict") == "DISCRIMINATING" for item in judged)
                         else ("WRONG_AT_FIXED" if any(item.get("verdict") == "WRONG_AT_FIXED"
                                                       for item in judged)
                               else ("VACUOUS" if any(item.get("verdict") == "VACUOUS" for item in judged)
                                     else "REFUSED")))
    record["refusal_kinds"] = sorted({refusal.get("refusal") for item in judged
                                      for refusal in (item.get("refusals") or []) if refusal.get("refusal")})
    return record


def run_corpus(cache: pathlib.Path, work: pathlib.Path, limit: int = 40,
               only_untested: bool = False) -> dict[str, Any]:
    states: dict[str, int] = {"commits": 0, "with_tests": 0, "untested": 0, "compiled": 0,
                              "refused": 0, "discriminating": 0, "vacuous": 0, "wrong_at_fixed": 0}
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
            if commit["tests"]:
                states["with_tests"] += 1
                if only_untested:
                    continue
            else:
                states["untested"] += 1
            row = judge_commit(clone, commit, work)
            row["repo"] = repo
            rows.append(row)
            if row["verdict"] == "REFUSED":
                states["refused"] += 1
            else:
                states["compiled"] += 1
                states[{"DISCRIMINATING": "discriminating", "VACUOUS": "vacuous",
                        "WRONG_AT_FIXED": "wrong_at_fixed"}.get(row["verdict"], "vacuous")] += 1
            for kind in row.get("refusal_kinds") or []:
                census[kind] = census.get(kind, 0) + 1
    return {"states": states, "refusal_census": census, "commits": rows}


def _headline(report: Mapping[str, Any]) -> str:
    states, census = report["states"], report.get("refusal_census") or {}
    compiled = states.get("compiled", 0) or 0
    discriminating = states.get("discriminating", 0)
    share = (100.0 * discriminating / compiled) if compiled else 0.0
    refused = ", ".join("%s x%d" % (kind.replace("REFUSED__", ""), count)
                        for kind, count in sorted(census.items(), key=lambda item: -item[1])) or "none"
    return (
        "%d real commits were handed their own message as the stated instruction. %d compiled into a "
        "contract over the environment's own code and %d were refused by name (%s). Of the compiled, %d were "
        "DISCRIMINATING -- the contract passed at the fixed state and failed at its parent, which is a "
        "checkable pair that did not exist before anything was learned, executed or verified by a test -- and "
        "%d were VACUOUS and %d were WRONG AT THE FIXED STATE, both reported because a compiler scored only on "
        "its successes is the always-pass grader this tree already refused. %.1f%% of the compilable set "
        "yielded a discriminating pair."
        % (states.get("commits", 0), compiled, states.get("refused", 0), refused,
           discriminating, states.get("vacuous", 0), states.get("wrong_at_fixed", 0), share))


def measure(corpus_report: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "reused_not_rebuilt": {
            "the_pattern": "canonical/runtime/instruction_contract_v1.py -- a small closed clause language, "
                           "refusals named one by one, falsifiable in both directions; read, not modified",
            "execution": "canonical/swe_kernel/checkability_by_differential_pin_v1.py -- probe, read only",
            "corpus": "canonical/swe_kernel/structural_check_of_real_changes_v1.py -- commits_touching_sources, "
                      "module_name_for, read only",
            "materialisation": "canonical/swe_kernel/witness_inversion_v1.py -- materialise, read only",
        },
        "the_language": {"values": "quoted strings and value-shaped tokens the sentence itself names",
                         "directions": {"WIDENING": list(WIDENING), "NARROWING": list(NARROWING),
                                        "REPAIR": list(REPAIR)},
                         "clauses": ["ACCEPTS_NAMED", "REJECTS_NAMED", "NAMED_IN_OUTCOME", "STILL_RUNS"],
                         "refusals": [NO_VALUE, VALUE_NOT_IN_ENVIRONMENT, VALUE_NOT_IN_A_CALLABLE,
                                      NO_DIRECTION, NO_CALLABLE]},
        "what_a_contract_is": ("the instruction's own named value, grounded in a callable the environment "
                               "defines, driven at both states, judged in both directions. It says 'the named "
                               "value is accepted here', never 'the change is what the user wanted'."),
        "states": {"commits": 0, "with_tests": 0, "untested": 0, "compiled": 0, "refused": 0,
                   "discriminating": 0, "vacuous": 0, "wrong_at_fixed": 0},
        "refusal_census": {},
        "commits": [],
    }
    if corpus_report is None:
        report["corpus"] = ("not fetched in this run: no clone cache and no network measurement. The compiler "
                            "is tested offline; the corpus number is producer-run and pinned by commit in the "
                            "receipt.")
        return report
    report.update(corpus_report)
    report["states"] = corpus_report["states"]
    report["refusal_census"] = corpus_report.get("refusal_census") or {}
    report["what_this_shows"] = _headline(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a stated instruction into a checkable pair for code -- or refuse by name.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--cache", default="/tmp/contract/cache")
    parser.add_argument("--work", default="/tmp/contract/work")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--only-untested", action="store_true")
    ns = parser.parse_args(argv)
    corpus_report = None
    if ns.corpus:
        corpus_report = run_corpus(pathlib.Path(ns.cache), pathlib.Path(ns.work), limit=ns.limit,
                                   only_untested=ns.only_untested)
    report = measure(corpus_report)
    print(json.dumps({key: report[key] for key in ("schema", "states", "refusal_census") if key in report},
                     indent=1))
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
