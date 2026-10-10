"""Minimal Brain-owned requirement graph and test-obligation kernel.

Mechanism adapted from ZhangHanDong/agent-spec at
2483398da89bd392186849bb865aae969667ac0a (MIT), specifically the causal
ideas in src/spec_knowledge/requirement_graph.rs and
src/spec_knowledge/test_obligations.rs.

This is intentionally *not* a natural-language specification parser. It accepts
already-normalized behavioral requirements and deterministically checks graph,
coverage, ambiguity and test-obligation completeness.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Diagnostic:
    code: str
    requirement_id: str | None
    message: str


def _ids(requirements: list[dict[str, Any]]) -> list[str]:
    return [str(r.get("id", "")).strip() for r in requirements]


def _cycles(requirements: list[dict[str, Any]], field: str) -> list[list[str]]:
    by_id = {str(r["id"]): r for r in requirements if r.get("id")}
    seen_cycles: set[tuple[str, ...]] = set()
    found: list[list[str]] = []

    def visit(node: str, path: list[str], active: set[str]) -> None:
        if node in active:
            i = path.index(node)
            cyc = path[i:] + [node]
            key = tuple(sorted(set(cyc[:-1])))
            if key not in seen_cycles:
                seen_cycles.add(key)
                found.append(cyc)
            return
        r = by_id.get(node)
        if not r:
            return
        active.add(node)
        path.append(node)
        for nxt in r.get(field, []) or []:
            nxt = str(nxt)
            if nxt in by_id:
                visit(nxt, path, active)
        path.pop()
        active.remove(node)

    for rid in by_id:
        visit(rid, [], set())
    return found


def validate_requirement_graph(
    requirements: list[dict[str, Any]],
    *,
    expected_required_ids: list[str] | None = None,
) -> dict[str, Any]:
    diagnostics: list[Diagnostic] = []
    ids = _ids(requirements)
    nonempty = [x for x in ids if x]

    for i, rid in enumerate(ids):
        if not rid:
            diagnostics.append(Diagnostic("missing-requirement-id", None, f"requirement index {i} has no id"))

    counts: dict[str, int] = {}
    for rid in nonempty:
        counts[rid] = counts.get(rid, 0) + 1
    for rid, count in counts.items():
        if count > 1:
            diagnostics.append(Diagnostic("duplicate-requirement-id", rid, f"{rid} occurs {count} times"))

    known = set(nonempty)
    if expected_required_ids is not None:
        expected = {str(x) for x in expected_required_ids}
        for missing in sorted(expected - known):
            diagnostics.append(Diagnostic("required-node-omitted", missing, f"required node {missing} is absent"))
        for unexpected in sorted(known - expected):
            diagnostics.append(Diagnostic("unexpected-requirement-node", unexpected, f"unexpected node {unexpected}"))

    for req in requirements:
        rid = str(req.get("id", "")) or None
        for dep in req.get("dependencies", []) or []:
            if str(dep) not in known:
                diagnostics.append(Diagnostic("dangling-dependency", rid, f"{rid} depends on missing {dep}"))
        for child in req.get("children", []) or []:
            if str(child) not in known:
                diagnostics.append(Diagnostic("dangling-child", rid, f"{rid} references missing child {child}"))

        critical = bool(req.get("critical", True))
        children = req.get("children", []) or []
        scenarios = req.get("scenarios", []) or []
        questions = req.get("open_questions", []) or []
        if critical and not children and not scenarios:
            diagnostics.append(Diagnostic("critical-leaf-without-scenario", rid, f"{rid} is critical leaf with no scenario"))
        if questions:
            diagnostics.append(Diagnostic("blocked-open-questions", rid, f"{rid} has unresolved questions"))

        clauses = req.get("clauses", []) or []
        for j, clause in enumerate(clauses):
            if not str(clause.get("id", "")).strip():
                diagnostics.append(Diagnostic("clause-without-id", rid, f"{rid} clause {j} has no stable id"))
            if str(clause.get("keyword", "")).upper() in {"MUST", "MUST NOT"}:
                covered = set(str(x) for x in clause.get("covered_by_scenarios", []) or [])
                scenario_ids = set(str(s.get("id", "")) for s in scenarios)
                if not (covered & scenario_ids):
                    diagnostics.append(Diagnostic("normative-clause-uncovered", rid, f"{rid} normative clause lacks scenario coverage"))

    for field, code in (("dependencies", "dependency-cycle"), ("children", "child-cycle")):
        for cyc in _cycles(requirements, field):
            diagnostics.append(Diagnostic(code, cyc[0], " -> ".join(cyc)))

    diagnostics.sort(key=lambda d: ((d.requirement_id or ""), d.code, d.message))
    return {
        "schema": "BRAIN_REQUIREMENT_GRAPH_VALIDATION_V1",
        "pass": not diagnostics,
        "requirement_count": len(requirements),
        "diagnostics": [asdict(d) for d in diagnostics],
    }


def build_test_obligations(requirements: list[dict[str, Any]]) -> dict[str, Any]:
    obligations: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    for req in requirements:
        rid = str(req.get("id", ""))
        if not rid:
            continue
        scenarios = req.get("scenarios", []) or []
        if bool(req.get("critical", True)) and not scenarios and not (req.get("children", []) or []):
            diagnostics.append(Diagnostic("critical-leaf-without-test-obligation", rid, f"{rid} has no scenario-derived obligation"))
        for scenario in scenarios:
            sid = str(scenario.get("id", "")).strip()
            if not sid:
                diagnostics.append(Diagnostic("scenario-without-id", rid, f"{rid} contains scenario without stable id"))
                continue
            then = [str(x) for x in scenario.get("then", []) or []]
            if not then:
                diagnostics.append(Diagnostic("scenario-without-observable-outcome", rid, f"{rid}/{sid} has no observable Then outcome"))
            obligations.append({
                "requirement_id": rid,
                "scenario_id": sid,
                "given": [str(x) for x in scenario.get("given", []) or []],
                "when": [str(x) for x in scenario.get("when", []) or []],
                "then": then,
                "independent_of_implementation": True,
            })
    obligations.sort(key=lambda x: (x["requirement_id"], x["scenario_id"]))
    diagnostics.sort(key=lambda d: ((d.requirement_id or ""), d.code, d.message))
    return {
        "schema": "BRAIN_SPEC_DERIVED_TEST_OBLIGATIONS_V1",
        "pass": not diagnostics,
        "obligations": obligations,
        "diagnostics": [asdict(d) for d in diagnostics],
    }


def compile_requirement_contract(
    requirements: list[dict[str, Any]],
    *,
    expected_required_ids: list[str] | None = None,
) -> dict[str, Any]:
    graph = validate_requirement_graph(requirements, expected_required_ids=expected_required_ids)
    tests = build_test_obligations(requirements)
    return {
        "schema": "BRAIN_COMPILED_REQUIREMENT_CONTRACT_V1",
        "pass": bool(graph["pass"] and tests["pass"]),
        "graph": graph,
        "test_obligations": tests,
    }


def seeded_requirement_mutations(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate structural mutants that a complete requirement gate must kill."""
    import copy
    mutants: list[dict[str, Any]] = []
    expected = _ids(requirements)

    for i, req in enumerate(requirements):
        if bool(req.get("critical", True)):
            m = copy.deepcopy(requirements)
            removed = m.pop(i)
            mutants.append({"id": f"delete:{removed.get('id')}", "requirements": m, "expected_ids": expected})

        if not (req.get("children", []) or []):
            m = copy.deepcopy(requirements)
            m[i]["scenarios"] = []
            mutants.append({"id": f"drop-scenarios:{req.get('id')}", "requirements": m, "expected_ids": expected})

        m = copy.deepcopy(requirements)
        m[i]["open_questions"] = ["seeded unresolved ambiguity"]
        mutants.append({"id": f"open-question:{req.get('id')}", "requirements": m, "expected_ids": expected})

    if requirements:
        m = copy.deepcopy(requirements)
        m[0].setdefault("dependencies", []).append("REQ-NONEXISTENT")
        mutants.append({"id": "dangling-dependency", "requirements": m, "expected_ids": expected})
    if len(requirements) >= 2:
        m = copy.deepcopy(requirements)
        a, b = str(m[0]["id"]), str(m[1]["id"])
        m[0]["dependencies"] = [b]
        m[1]["dependencies"] = [a]
        mutants.append({"id": "dependency-cycle", "requirements": m, "expected_ids": expected})

    return mutants


def requirement_mutation_score(requirements: list[dict[str, Any]]) -> dict[str, Any]:
    mutants = seeded_requirement_mutations(requirements)
    killed: list[str] = []
    survived: list[str] = []
    for mutant in mutants:
        result = compile_requirement_contract(
            mutant["requirements"],
            expected_required_ids=mutant["expected_ids"],
        )
        (killed if not result["pass"] else survived).append(mutant["id"])
    total = len(mutants)
    return {
        "schema": "BRAIN_REQUIREMENT_MUTATION_SCORE_V1",
        "total": total,
        "killed": len(killed),
        "survived": len(survived),
        "kill_fraction": (len(killed) / total) if total else 1.0,
        "killed_ids": sorted(killed),
        "survived_ids": sorted(survived),
        "pass": total > 0 and not survived,
    }


def validate_requirement_output_reachability(
    requirements: list[dict[str, Any]],
    *,
    calculation_nodes: list[dict[str, Any]],
    calculation_edges: list[dict[str, Any]],
    outputs: list[str],
    exclusions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fail closed unless every non-excluded requirement reaches a final output."""
    req_ids = {str(r.get("id", "")).strip() for r in requirements if str(r.get("id", "")).strip()}
    node_ids = [str(n.get("id", "")).strip() for n in calculation_nodes]
    nonempty_nodes = [x for x in node_ids if x]
    known_nodes = set(nonempty_nodes)
    output_ids = {str(x) for x in outputs}
    diagnostics: list[Diagnostic] = []

    if len(nonempty_nodes) != len(calculation_nodes):
        diagnostics.append(Diagnostic("calculation-node-without-id", None, "one or more calculation nodes lack stable ids"))
    if len(set(nonempty_nodes)) != len(nonempty_nodes):
        diagnostics.append(Diagnostic("duplicate-calculation-node-id", None, "calculation node ids must be unique"))

    for out in sorted(output_ids - known_nodes):
        diagnostics.append(Diagnostic("unknown-output-node", None, f"output {out} is not a calculation node"))

    adjacency: dict[str, list[str]] = {n: [] for n in known_nodes}
    for edge in calculation_edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src not in known_nodes or dst not in known_nodes:
            diagnostics.append(Diagnostic("dangling-calculation-edge", None, f"{src}->{dst}"))
            continue
        adjacency[src].append(dst)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        cyclic = any(visit(nxt) for nxt in adjacency.get(node, ()))
        visiting.remove(node)
        visited.add(node)
        return cyclic

    if any(visit(n) for n in sorted(known_nodes)):
        diagnostics.append(Diagnostic("calculation-cycle", None, "calculation graph contains a cycle"))

    exclusion_map = {
        str(x.get("requirement_id", "")): str(x.get("justification", "")).strip()
        for x in (exclusions or [])
    }
    for rid, justification in sorted(exclusion_map.items()):
        if rid not in req_ids:
            diagnostics.append(Diagnostic("exclusion-for-unknown-requirement", rid or None, rid))
        elif not justification:
            diagnostics.append(Diagnostic("empty-exclusion-justification", rid, rid))

    bindings: dict[str, list[str]] = {}
    for node in calculation_nodes:
        rid = str(node.get("requirement_id", "")).strip()
        nid = str(node.get("id", "")).strip()
        if rid:
            bindings.setdefault(rid, []).append(nid)
            if rid not in req_ids:
                diagnostics.append(Diagnostic("node-bound-to-unknown-requirement", rid, nid))

    def reaches_output(start: str) -> bool:
        stack = [start]
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in output_ids:
                return True
            stack.extend(adjacency.get(node, ()))
        return False

    uncovered: list[str] = []
    for rid in sorted(req_ids):
        if exclusion_map.get(rid):
            continue
        starts = [n for n in bindings.get(rid, []) if n in known_nodes]
        if not starts:
            uncovered.append(f"{rid}:NO_CALCULATION_NODE")
        elif not any(reaches_output(n) for n in starts):
            uncovered.append(f"{rid}:NO_OUTPUT_PATH")

    return {
        "schema": "BRAIN_REQUIREMENT_OUTPUT_REACHABILITY_V1",
        "pass": not diagnostics and not uncovered,
        "uncovered": uncovered,
        "diagnostics": [asdict(d) for d in diagnostics],
    }


def compile_structured_method_contract(
    requirements: list[dict[str, Any]],
    *,
    expected_required_ids: list[str] | None = None,
    calculation_nodes: list[dict[str, Any]],
    calculation_edges: list[dict[str, Any]],
    outputs: list[str],
    exclusions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compose normalized requirement validation with requirement-to-output reachability."""
    base = compile_requirement_contract(requirements, expected_required_ids=expected_required_ids)
    reachability = validate_requirement_output_reachability(
        requirements,
        calculation_nodes=calculation_nodes,
        calculation_edges=calculation_edges,
        outputs=outputs,
        exclusions=exclusions,
    )
    return {
        "schema": "BRAIN_STRUCTURED_METHOD_CONTRACT_V1",
        "pass": bool(base["pass"] and reachability["pass"]),
        "requirement_contract": base,
        "output_reachability": reachability,
    }
