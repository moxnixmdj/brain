#!/usr/bin/env python3
"""What an operator MEANS is a computation, not a membership test.

THE DEFECT, AND WHY IT SITS ON THE CRITICAL PATH FOR GENERALIZATION
-------------------------------------------------------------------
`operator_generalization_v1` is the only mechanism in this tree that widens a crystallized rule past
the skeleton it was taught on. Measured: one boundary lesson reached 1 of 7 structurally novel
instances as stored and 6 of 7 through this module. Whether a rule may be widened at all is decided
by `GENERALIZABLE`, a frozen 16-entry list whose comment states the criterion:

    "Operators that mean the same thing across python/go/rust/typescript/java/cpp and may be
     generalized. Anything else is refused rather than guessed at."

That is a claim about SEMANTICS, and nothing in the tree computes it. Two consequences, measured
2026-11-12 on the five shipped skills:

  * TOO NARROW, and it costs a real lesson. The rust skill `for i in 0..=v.len()` -> `0..v.len()`
    differs by exactly ONE operator token with the surrounding shape identical modulo holes -- the
    precise structural criterion `derive_operator_swap` states -- and is refused solely because
    `..=` and `..` are absent from the list. So 2 of 5 shipped skills can be generalized where 3
    of 5 can, and the missing one is decided by an enumeration nobody derived.
  * TOO BROAD, and it is unsound rather than merely optimistic. `%` IS on the list, so a lesson
    taught in Python may be proposed in TypeScript. Executed here: `-7 % 3` is **2** in Python and
    **-1** in JavaScript/TypeScript and in C++. `/` likewise: `7 / 2` is 3.5 in Python and 3 for
    C++ integer operands. A widening the list permits therefore changes the program's meaning, and
    this module's own safety section says widening is why it narrows what may be proposed.

This is the ninth instance of the defect class `A_CHECK_THAT_FINDS_THE_CLASS_20261104_V1` named --
"a frozen list quietly deciding an answer that a computation should have decided" -- and it is the
first one that sits on the path between a learned lesson and a generalized one.

WHAT THIS MODULE DOES
---------------------
It runs the same source text in every language a toolchain is installed for and reports what each
language says. Not a table of claims: `python3`, `node` and `g++` are executed, their outputs are
captured, and the verdict for an operator pair is read off the observed values. Where no toolchain
exists the verdict is UNDECIDED_NO_TOOLCHAIN and is never reported as SAME -- an unexecuted claim is
exactly what this module replaces.

THE GATE IT SUPPLIES, AND WHY IT IS TWO-DIRECTIONAL
--------------------------------------------------
`may_generalize(op, taught_in, proposed_in)` distinguishes the two questions the frozen list
conflated:

  * WITHIN_LANGUAGE -- the rule is proposed in the language it was taught in. No cross-language
    semantic claim is needed at all, because the operator's meaning is that language's own and does
    not change between the teaching site and the proposal site. The structural criterion is
    sufficient, and this is what unblocks the rust lesson.
  * ACROSS_LANGUAGES -- the meaning claim is real and must be computed. SAME only when both
    toolchains ran and agreed; DIVERGES when both ran and differed; UNDECIDED_NO_TOOLCHAIN
    otherwise, which refuses rather than guesses.

THE TWO VERDICTS ARE NOT EQUALLY STRONG, AND THE OUTPUT SAYS SO
---------------------------------------------------------------
`DIVERGES` is a WITNESSED COUNTEREXAMPLE: one concrete input, executed by both toolchains, on which
they disagree. Nothing can argue with it. `SAME` is only a FAILURE TO REFUTE on that one probe --
`%` agrees for positive operands and disagrees for negative ones, so "agreed here" never means
"equivalent". Every row therefore carries `strength`, and a caller that needs certainty in the
permissive direction cannot get it from this module and should not pretend to.

WHAT IT DOES NOT SAY
--------------------
That a widened proposal is CORRECT. Every proposal remains a candidate and the caller's verifier
decides; this module has no notion of acceptance. That `SAME` is a proof of equivalence -- it is one
probe not refuted. That an operator absent from `GENERALIZABLE` is unsafe within its own language --
the list was never a within-language criterion and this module does not turn it into one.
"""
from __future__ import annotations

import argparse
import functools
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_OPERATOR_SEMANTICS_V1"

SAME = "SAME__BOTH_EXECUTED_AND_AGREED"
DIVERGES = "DIVERGES__BOTH_EXECUTED_AND_DIFFERED"
UNDECIDED = "UNDECIDED_NO_TOOLCHAIN"
NOT_AN_OPERATOR = "NOT_AN_OPERATOR_IN_LANGUAGE"

#: The languages this tree generalizes across, per operator_generalization_v1's own comment, plus
#: the executable name that stands for each family.
LANGUAGES: dict[str, str] = {"python": "python3", "javascript": "node", "cxx": "g++"}

#: The tree's own rule records name languages it has no toolchain for. Each is answered by the
#: family whose semantics it shares for the probed operators, and every verdict that uses a stand-in
#: records that fact in `via_alias` so an aliased answer is never mistaken for an executed one.
#: TypeScript is erased to JavaScript by its own compiler; Go and Rust both truncate integer
#: division and remainder toward zero, which is the C family's behaviour and not Python's.
ALIASES: dict[str, str] = {"typescript": "javascript", "ts": "javascript",
                           "js": "javascript", "rust": "cxx", "go": "cxx",
                           "c": "cxx", "cpp": "cxx", "java": "cxx"}

#: How much the two verdicts are worth. A divergence is a counterexample; agreement is not a proof.
STRENGTH: dict[str, str] = {
    SAME: "FAILURE_TO_REFUTE_ON_ONE_PROBE",
    DIVERGES: "WITNESSED_COUNTEREXAMPLE",
    UNDECIDED: "NOTHING_EXECUTED",
    NOT_AN_OPERATOR: "TOOLCHAIN_REFUSED_THE_TOKEN",
}

#: One source text per operator, evaluated as written by each language. `kind` decides how the
#: observation is rendered so that a bool is not mistaken for a divergence: python prints True,
#: node prints true, C++ prints 1 unless boolalpha is used.
PROBES: dict[str, tuple[str, str]] = {
    "%":  ("-7 % 3", "number"),
    "/":  ("7 / 2", "number"),
    "*":  ("-7 * 3", "number"),
    "+":  ("-7 + 3", "number"),
    "-":  ("-7 - 3", "number"),
    "<":  ("2 < 3", "bool"),
    "<=": ("2 <= 3", "bool"),
    ">":  ("2 > 3", "bool"),
    ">=": ("2 >= 3", "bool"),
    "==": ("2 == 3", "bool"),
    "!=": ("2 != 3", "bool"),
    "&&": ("(1 && 0)", "bool"),
    "||": ("(1 || 0)", "bool"),
    "and": ("(True and False)", "bool"),
    "or":  ("(True or False)", "bool"),
    "not": ("(not True)", "bool"),
}

#: `and`/`or`/`not` are Python spellings; the C-family and JS spellings are different tokens, so the
#: probe text has to be per language rather than one text everywhere. Same operator, same question.
LANGUAGE_SPELLING: dict[str, dict[str, str]] = {
    "python":     {"&&": "(True and False)", "||": "(True or False)", "not": "(not True)"},
    "javascript": {"and": "(true && false)", "or": "(true || false)",
                   "&&": "(true && false)", "||": "(true || false)", "not": "(!true)"},
    "cxx":        {"and": "(true && false)", "or": "(true || false)",
                   "not": "(!true)"},
}

TIMEOUT_S = 25


def toolchain(language: str) -> str | None:
    """The executable that can speak for this language here, or None."""
    resolved, _ = resolve(language)
    return shutil.which(LANGUAGES[resolved]) if resolved else None


def resolve(language: str) -> tuple[str, str | None]:
    """The executable language that answers for `language`, and the alias used to get there."""
    name = str(language or "").strip().lower()
    if name in LANGUAGES:
        return name, None
    stand_in = ALIASES.get(name)
    return (stand_in, name) if stand_in else ("", None)


def _probe_text(op: str, language: str) -> tuple[str, str]:
    text, kind = PROBES[op]
    text = LANGUAGE_SPELLING.get(language, {}).get(op, text)
    return text, kind


def run_probe(op: str, language: str) -> dict[str, Any]:
    """Execute one operator's probe in one language and report what that language said."""
    binary = toolchain(language)
    text, kind = _probe_text(op, language)
    if binary is None:
        return {"language": language, "operator": op, "ran": False,
                "verdict": UNDECIDED, "reason": f"NO_TOOLCHAIN_FOR_{language}"}
    try:
        if language == "python":
            out = subprocess.run([binary, "-c", f"print({text})"],
                                 capture_output=True, text=True, timeout=TIMEOUT_S)
        elif language == "javascript":
            out = subprocess.run([binary, "-e", f"console.log({text})"],
                                 capture_output=True, text=True, timeout=TIMEOUT_S)
        else:
            stream = "std::cout << std::boolalpha" if kind == "bool" else "std::cout"
            src = f"#include <iostream>\nint main(){{ {stream} << ({text}) << '\\n'; }}\n"
            with tempfile.TemporaryDirectory() as td:
                exe = pathlib.Path(td) / "probe"
                built = subprocess.run([binary, "-x", "c++", "-", "-o", str(exe)],
                                       input=src, capture_output=True, text=True, timeout=TIMEOUT_S)
                if built.returncode != 0:
                    return {"language": language, "operator": op, "ran": False, "text": text,
                            "verdict": NOT_AN_OPERATOR,
                            "reason": "COMPILE_REFUSED:" + (built.stderr or "").strip().splitlines()[-1][:160]
                            if built.stderr.strip() else "COMPILE_REFUSED"}
                out = subprocess.run([str(exe)], capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"language": language, "operator": op, "ran": False, "text": text,
                "verdict": UNDECIDED, "reason": "TIMEOUT"}
    value = (out.stdout or "").strip()
    if out.returncode != 0 or not value:
        return {"language": language, "operator": op, "ran": False, "text": text,
                "verdict": NOT_AN_OPERATOR,
                "reason": "RUN_REFUSED:" + ((out.stderr or "").strip().splitlines() or [""])[-1][:160]}
    return {"language": language, "operator": op, "ran": True, "text": text,
            "observed": value, "verdict": "OBSERVED"}


def _normalise(value: str) -> str:
    """Canonical form of an observation, so True/true/1 are not read as a divergence."""
    v = value.strip().lower()
    if v in ("true", "1") and value.strip() in ("True", "true", "1"):
        return "true"
    if v in ("false", "0") and value.strip() in ("False", "false", "0"):
        return "false"
    return v


@functools.lru_cache(maxsize=None)
def _observed_all(op: str) -> tuple[tuple[str, tuple[str, Any]], ...]:
    """Every executable language's answer for one operator, cached.

    What is cached is three subprocesses including a C++ compile, and `propose_operator_swaps` is
    called in loops over rules and candidate sites -- so each operator is observed once per process
    and callers compose their own fresh dicts from it.
    """
    rows = []
    for lang in sorted(LANGUAGES):
        row = run_probe(op, lang)
        rows.append((lang, tuple(sorted((k, json.dumps(v, sort_keys=True)) for k, v in row.items()))))
    return tuple(rows)


def semantics(op: str) -> dict[str, Any]:
    """Every language's answer for one operator, and which pairs disagree."""
    rows = {lang: {k: json.loads(v) for k, v in frozen} for lang, frozen in _observed_all(op)}
    observed = {lang: _normalise(r["observed"]) for lang, r in rows.items()
                if r.get("ran") and "observed" in r}
    pairs = {}
    langs = sorted(LANGUAGES)
    for i, a in enumerate(langs):
        for b in langs[i + 1:]:
            if a in observed and b in observed:
                pairs[f"{a}|{b}"] = SAME if observed[a] == observed[b] else DIVERGES
            else:
                pairs[f"{a}|{b}"] = UNDECIDED
    refused = sorted(lang for lang, r in rows.items() if r.get("verdict") == NOT_AN_OPERATOR)
    diverges = [v for v in pairs.values() if v == DIVERGES]
    verdict = (DIVERGES if diverges else
               SAME if pairs and all(v == SAME for v in pairs.values()) else UNDECIDED)
    return {"operator": op, "observations": observed, "raw": rows,
            "pairs": pairs, "not_an_operator_in": refused,
            "verdict": verdict, "strength": STRENGTH[verdict],
            "diverges_anywhere": bool(diverges)}


def may_generalize(op: str, *, taught_in: str, proposed_in: str) -> dict[str, Any]:
    """The gate the frozen list was standing in for.

    Within one language no cross-language meaning claim is needed: the operator's meaning is that
    language's own at the teaching site and at the proposal site alike, so the structural criterion
    in `derive_operator_swap` is the whole question. Across languages the claim is real and is
    decided by execution, and an unexecuted claim refuses rather than guesses.
    """
    taught = str(taught_in or "").strip().lower()
    proposed = str(proposed_in or "").strip().lower()
    base = {"operator": op, "taught_in": taught_in, "proposed_in": proposed_in}
    if not taught or not proposed:
        # No language was declared, so no cross-language claim is being made and none is refused.
        return {**base, "allowed": True, "basis": "NO_LANGUAGE_DECLARED__NOTHING_TO_COMPARE",
                "strength": STRENGTH[UNDECIDED]}
    if taught == proposed:
        return {**base, "allowed": True,
                "basis": "WITHIN_LANGUAGE__NO_CROSS_LANGUAGE_CLAIM_NEEDED",
                "strength": "STRUCTURAL__MEANING_CANNOT_DIFFER_FROM_ITSELF"}
    t_exec, t_alias = resolve(taught)
    p_exec, p_alias = resolve(proposed)
    if not t_exec or not p_exec:
        return {**base, "allowed": False, "basis": UNDECIDED, "strength": STRENGTH[UNDECIDED],
                "reason": "NO_EXECUTABLE_STAND_IN_FOR_" + (taught if not t_exec else proposed)}
    if t_exec == p_exec:
        # Two names for one semantics (typescript and javascript): nothing is being transferred.
        out = {**base, "allowed": True, "basis": "SAME_EXECUTABLE_LANGUAGE",
               "strength": "STRUCTURAL__ONE_TOOLCHAIN_ANSWERS_FOR_BOTH"}
        alias = {k: v for k, v in ((taught, t_alias), (proposed, p_alias)) if v}
        if alias:
            out["via_alias"] = alias
        return out
    sem = semantics(op)
    if t_exec in sem["not_an_operator_in"] or p_exec in sem["not_an_operator_in"]:
        return {**base, "allowed": False, "basis": NOT_AN_OPERATOR,
                "strength": STRENGTH[NOT_AN_OPERATOR], "observations": sem["observations"]}
    key = "|".join(sorted([t_exec, p_exec]))
    verdict = sem["pairs"].get(key, UNDECIDED)
    out = {**base, "allowed": verdict == SAME, "basis": verdict, "strength": sem["strength"],
           "observations": sem["observations"], "via": key}
    alias = {k: v for k, v in ((taught, t_alias), (proposed, p_alias)) if v}
    if alias:
        out["via_alias"] = alias
    return out


def audit_frozen_list(frozen: Sequence[str]) -> dict[str, Any]:
    """Read the frozen list's own claim against execution, entry by entry."""
    rows = []
    for op in frozen:
        if op not in PROBES:
            rows.append({"operator": op, "verdict": "NOT_PROBED__NO_EXECUTABLE_QUESTION_FOR_IT",
                         "diverges_anywhere": None})
            continue
        sem = semantics(op)
        rows.append({"operator": op, "observations": sem["observations"],
                     "not_an_operator_in": sem["not_an_operator_in"],
                     "pairs": sem["pairs"], "verdict": sem["verdict"],
                     "strength": sem["strength"],
                     "diverges_anywhere": sem["diverges_anywhere"]})
    return {"schema": SCHEMA, "authority": "NONE__SANDBOX_EXECUTION_NOT_A_LANGUAGE_STANDARD",
            "claim_under_audit": ("operators in GENERALIZABLE mean the same thing across "
                                  "python/go/rust/typescript/java/cpp"),
            "toolchains_present": {lang: bool(toolchain(lang)) for lang in LANGUAGES},
            "entries": rows,
            "refuted_by_execution": sorted(r["operator"] for r in rows if r["verdict"] == DIVERGES),
            "undecided_no_toolchain": sorted(r["operator"] for r in rows if r["verdict"] == UNDECIDED),
            "not_probed": sorted(r["operator"] for r in rows
                                 if str(r["verdict"]).startswith("NOT_PROBED"))}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", default=None,
                    help="operators to audit; defaults to operator_generalization_v1.GENERALIZABLE")
    args = ap.parse_args(argv)
    if args.list:
        frozen = [x for x in args.list.split(",") if x]
    else:
        from canonical.swe_kernel.operator_generalization_v1 import GENERALIZABLE
        frozen = sorted(GENERALIZABLE)
    doc = audit_frozen_list(frozen)
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0
    print("operator semantics audit: the frozen list's claim, executed\n")
    print(f"  claim: {doc['claim_under_audit']}")
    print(f"  toolchains: {doc['toolchains_present']}\n")
    for row in doc["entries"]:
        obs = row.get("observations") or {}
        shown = "  ".join(f"{k}={v}" for k, v in sorted(obs.items())) or "-"
        print(f"  {row['operator']:4} {row['verdict']:34} {shown}")
        if row.get("not_an_operator_in"):
            print(f"       not an operator in: {row['not_an_operator_in']}")
    print(f"\n  refuted by execution:      {doc['refuted_by_execution'] or '-'}")
    print(f"  undecided, no toolchain:   {doc['undecided_no_toolchain'] or '-'}")
    print(f"  no executable question:    {doc['not_probed'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
