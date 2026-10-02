"""Independent reference proof for the P1 V6 executable causal cut-set kernel."""
from __future__ import annotations

import itertools
from typing import Any, Mapping

DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")
KINDS = ("AUTHORITY", "SCOPE", "SCHEMA", "PROVENANCE", "INVARIANT", "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY")


def check(aid: str, kind: str, passed: bool) -> dict[str, Any]:
    return {"id": f"{aid}:{kind}", "kind": kind, "pass": passed, "evidence": [f"receipt:{aid}:{kind}"]}


def row(aid: str, *, deps=(), reads=(), writes=(), comp="SEQUENTIAL", failed_kind=None):
    checks = [] if failed_kind == "INVARIANT" else [check(aid, "INVARIANT", True)]
    if failed_kind is not None:
        checks.append(check(aid, failed_kind, False))
    return {
        "action_id": aid,
        "depends_on": list(deps),
        "reads": list(reads),
        "writes": list(writes),
        "dependency_composition": comp,
        "checks": checks,
    }


def generate_case(domain: str, kind: str, pattern: str) -> dict[str, Any]:
    p = domain.lower() + ":"
    if pattern == "SINGLE":
        rows = [
            row("A0", writes=[p+"seed"]),
            row("A1", deps=["A0"], reads=[p+"seed"], writes=[p+"root"], failed_kind=kind),
            row("A2", deps=["A1"], reads=[p+"root"], writes=[p+"terminal"]),
        ]
    elif pattern == "DELAYED":
        rows = [
            row("A0", writes=[p+"seed"]),
            row("A1", deps=["A0"], reads=[p+"seed"], writes=[p+"root"], failed_kind=kind),
            row("A2", deps=["A1"], reads=[p+"root"], writes=[p+"mid1"]),
            row("A3", deps=["A2"], reads=[p+"mid1"], writes=[p+"mid2"]),
            row("A4", deps=["A3"], reads=[p+"mid2"], writes=[p+"terminal"]),
        ]
    elif pattern == "INTERACTION":
        kind2 = KINDS[(KINDS.index(kind)+3) % len(KINDS)]
        rows = [
            row("A0", writes=[p+"seed"]),
            row("A1", deps=["A0"], reads=[p+"seed"], writes=[p+"left"], failed_kind=kind),
            row("A2", deps=["A0"], reads=[p+"seed"], writes=[p+"right"], failed_kind=kind2),
            row("A3", deps=["A1","A2"], reads=[p+"left",p+"right"], writes=[p+"terminal"], comp="CONJUNCTIVE"),
        ]
    elif pattern == "AMBIGUOUS":
        kind2 = KINDS[(KINDS.index(kind)+1) % len(KINDS)]
        rows = [
            row("A0", writes=[p+"seed"]),
            row("A1", deps=["A0"], reads=[p+"seed"], writes=[p+"left"], failed_kind=kind),
            row("A2", deps=["A0"], reads=[p+"seed"], writes=[p+"right"], failed_kind=kind2),
            row("A3", deps=["A1","A2"], reads=[p+"left",p+"right"], writes=[p+"terminal"], comp="ALTERNATIVE"),
        ]
    else:
        raise ValueError(pattern)
    return {"task": {"domain": domain, "trajectory": rows, "terminal_failed_resources": [p+"terminal"]}}


def false_earliest_alternative_case(domain="CODE", early_kind="SCOPE", true_kind="STATE_TRANSITION"):
    p = domain.lower() + ":"
    rows = [
        row("A0", writes=[p+"seed"]),
        row("A1", deps=["A0"], reads=[p+"seed"], writes=[p+"left"], failed_kind=early_kind),
        row("A2", deps=["A0"], reads=[p+"seed"], writes=[p+"right"]),
        row("A3", deps=["A1","A2"], reads=[p+"left",p+"right"], writes=[p+"merged"], comp="ALTERNATIVE"),
        row("A4", deps=["A3"], reads=[p+"merged"], writes=[p+"terminal"], failed_kind=true_kind),
    ]
    return {"task": {"domain": domain, "trajectory": rows, "terminal_failed_resources": [p+"terminal"]}}


def suite_cases():
    return [generate_case(d,k,p) for d in DOMAINS for k in KINDS for p in ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")]


def _reference_parse(task: Mapping[str, Any]):
    rows = task["trajectory"]
    order = []
    by = {}
    writer = {}
    for r in rows:
        aid = r["action_id"]
        deps = set(r["depends_on"])
        for resource in r["reads"]:
            if resource in writer:
                deps.add(writer[resource])
        by[aid] = (tuple(sorted(deps)), r["dependency_composition"], tuple(r["checks"]))
        order.append(aid)
        for resource in r["writes"]:
            writer[resource] = aid
    terminals = [writer[x] for x in task["terminal_failed_resources"]]
    return order, by, terminals


def reference_success(task: Mapping[str, Any], repaired: set[str]) -> bool:
    order, by, terminals = _reference_parse(task)
    memo: dict[str, bool] = {}
    def ok(aid: str) -> bool:
        if aid in memo:
            return memo[aid]
        deps, comp, checks = by[aid]
        local = all(c["pass"] is True or c["id"] in repaired for c in checks)
        if not deps:
            depok = True
        elif comp == "ALTERNATIVE":
            depok = any(ok(d) for d in deps)
        else:
            depok = all(ok(d) for d in deps)
        memo[aid] = local and depok
        return memo[aid]
    return all(ok(t) for t in terminals)


def reference_minimal_sets(task: Mapping[str, Any]) -> list[frozenset[str]]:
    ids = sorted(c["id"] for r in task["trajectory"] for c in r["checks"] if c["pass"] is False)
    rescuers = []
    for n in range(len(ids)+1):
        for combo in itertools.combinations(ids,n):
            s=frozenset(combo)
            if any(x.issubset(s) for x in rescuers):
                continue
            if reference_success(task,set(s)):
                rescuers.append(s)
    return rescuers


def output_sets(out: Mapping[str, Any]) -> list[frozenset[str]]:
    if out.get("status") == "AMBIGUOUS":
        return sorted((frozenset(x["check_ids"]) for x in out["minimal_rescue_sets"]), key=lambda s: tuple(sorted(s)))
    if out.get("status") in {"IDENTIFIED","INTERACTION"}:
        return [frozenset(out["minimal_repair_check_ids"])]
    return []


def score(task: Mapping[str, Any], out: Mapping[str, Any]) -> dict[str, Any]:
    expected = sorted(reference_minimal_sets(task), key=lambda s: tuple(sorted(s)))
    got = sorted(output_sets(out), key=lambda s: tuple(sorted(s)))
    if expected != got:
        return {"pass": False, "reason": "MINIMAL_RESCUE_SET_MISMATCH", "expected": [sorted(x) for x in expected], "got": [sorted(x) for x in got]}
    if not expected:
        return {"pass": out.get("status") == "ESCALATE", "reason": "NO_RESCUE_EXPECTED"}
    expected_status = "AMBIGUOUS" if len(expected)>1 else ("IDENTIFIED" if len(expected[0])==1 else "INTERACTION")
    if out.get("status") != expected_status:
        return {"pass": False, "reason": "STATUS_MISMATCH", "expected_status": expected_status}
    for s in expected:
        if not reference_success(task,set(s)):
            return {"pass":False,"reason":"CLAIMED_SET_DOES_NOT_EXECUTABLY_RESCUE"}
        for cid in s:
            if reference_success(task,set(s-{cid})):
                return {"pass":False,"reason":"CLAIMED_SET_NOT_MINIMAL"}
    return {"pass":True,"reason":"PASS__INDEPENDENT_EXECUTABLE_RESCUE"}


def prove(candidate_module) -> dict[str, Any]:
    failures=[]
    cases=suite_cases()
    for i,c in enumerate(cases):
        out=candidate_module.solve(c)
        verdict=score(c["task"],out)
        if verdict["pass"] is not True:
            failures.append((i,verdict,out))
    counterexamples=[]
    for d in DOMAINS:
        c=false_earliest_alternative_case(d)
        out=candidate_module.solve(c)
        verdict=score(c["task"],out)
        if verdict["pass"] is not True or out.get("minimal_repair_check_ids") != ["A4:STATE_TRANSITION"]:
            counterexamples.append((d,verdict,out))
    return {
        "pass": not failures and not counterexamples,
        "cross_product_cases": len(cases),
        "false_earliest_alternative_cases": len(DOMAINS),
        "total_cases": len(cases)+len(DOMAINS),
        "failures": failures,
        "counterexample_failures": counterexamples,
    }
