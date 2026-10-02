"""Information-safe bounded proof for whole-dimension structured-method graphs.

The candidate receives a normalized method specification (the contract's declared
input boundary). The independent evaluator derives expected branch selection, typed
intermediate consequences, requirement lineage/exclusions, and output values without
importing the candidate compiler.

The generated population covers every currently missing dimension from
STRUCTURED_METHOD_SCOPE_AUDIT_V1, but only for the frozen normalized-rule grammar.
It therefore remains preflight evidence, not whole-open-ended terminal authority.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import random
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_WHOLE_DIMENSION_PROOF_V1"


def _cond(cond: Mapping[str, Any] | None, vals: Mapping[str, Any]) -> bool:
    if cond is None:
        return True
    op = cond["op"]
    a = vals[cond["field"]]
    b = cond.get("value")
    if op == "eq": return a == b
    if op == "neq": return a != b
    if op == "gt": return a > b
    if op == "ge": return a >= b
    if op == "lt": return a < b
    if op == "le": return a <= b
    raise ValueError("COND")


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool) or not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("INPUT")
    r = random.Random((seed << 13) ^ ordinal ^ 0x570C)
    regulated = (ordinal % 2 == 0)
    mode = "regulated" if regulated else "standard"
    base_a = r.randint(20, 80)
    base_b = r.randint(10, 40)
    adj = r.randint(1, 10)
    bonus = r.randint(1, 8)
    limit = r.uniform(0.8, 3.0)

    schema_fields = [
        {"id": "amount_a", "type": "number", "dimension": "currency", "value": float(base_a)},
        {"id": "amount_b", "type": "number", "dimension": "currency", "value": float(base_b)},
        {"id": "adjustment", "type": "number", "dimension": "currency", "value": float(adj)},
        {"id": "bonus", "type": "number", "dimension": "currency", "value": float(bonus)},
        {"id": "review_limit", "type": "number", "dimension": "dimensionless", "value": float(limit)},
        {"id": "mode", "type": "enum", "dimension": "dimensionless", "value": mode},
    ]
    requirements = [
        {"id": "REQ_SCHEMA", "source_kind": "schema"},
        {"id": "REQ_FORMULA", "source_kind": "formula"},
        {"id": "REQ_CALLOUT", "source_kind": "feature_callout"},
        {"id": "REQ_STANDARD_REG", "source_kind": "standard", "applies_when": {"field": "mode", "op": "eq", "value": "regulated"}},
        {"id": "REQ_STANDARD_STD", "source_kind": "standard", "applies_when": {"field": "mode", "op": "eq", "value": "standard"}},
        {"id": "REQ_EXCLUDED", "source_kind": "constraint", "applies_when": {"field": "amount_a", "op": "lt", "value": -1}},
    ]
    common_rules = [
        {
            "id": "R_SUBTOTAL",
            "op": "sum",
            "inputs": ["amount_a", "amount_b"],
            "output": "subtotal",
            "output_type": "number",
            "output_dimension": "currency",
            "consumes_requirements": ["REQ_SCHEMA", "REQ_FORMULA"],
            "invariants": [{"kind": "min", "value": 0}],
        },
        {
            "id": "R_RATIO",
            "op": "ratio",
            "inputs": ["amount_a", "amount_b"],
            "output": "ratio",
            "output_type": "number",
            "output_dimension": "dimensionless",
            "consumes_requirements": ["REQ_CALLOUT"],
            "invariants": [{"kind": "min", "value": 0}],
        },
        {
            "id": "R_REVIEW",
            "op": "threshold_gt",
            "inputs": ["ratio"],
            "threshold": float(limit),
            "output": "needs_review",
            "output_type": "boolean",
            "output_dimension": "dimensionless",
            "consumes_requirements": ["REQ_CALLOUT"],
            "invariants": [],
        },
    ]
    branches = [
        {
            "id": "REGULATED_BRANCH",
            "when": [{"field": "mode", "op": "eq", "value": "regulated"}],
            "rules": [
                {
                    "id": "R_FINAL_REG",
                    "op": "difference",
                    "inputs": ["subtotal", "adjustment"],
                    "output": "final_amount",
                    "output_type": "number",
                    "output_dimension": "currency",
                    "consumes_requirements": ["REQ_STANDARD_REG"],
                    "invariants": [{"kind": "min", "value": 0}],
                }
            ],
        },
        {
            "id": "STANDARD_BRANCH",
            "when": [{"field": "mode", "op": "eq", "value": "standard"}],
            "rules": [
                {
                    "id": "R_FINAL_STD",
                    "op": "sum",
                    "inputs": ["subtotal", "bonus"],
                    "output": "final_amount",
                    "output_type": "number",
                    "output_dimension": "currency",
                    "consumes_requirements": ["REQ_STANDARD_STD"],
                    "invariants": [{"kind": "min", "value": 0}],
                }
            ],
        },
    ]
    return {
        "schema": SCHEMA,
        "case_id": f"STRUCTURED-METHOD-{seed}-{ordinal}",
        "schema_fields": schema_fields,
        "requirements": requirements,
        "common_rules": common_rules,
        "branches": branches,
        "required_outputs": ["final_amount", "needs_review"],
    }


def public_case(case: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(case))


def _expected(case: Mapping[str, Any]) -> dict[str, Any]:
    values = {x["id"]: x["value"] for x in case["schema_fields"]}
    meta = {x["id"]: {"type": x["type"], "dimension": x["dimension"]} for x in case["schema_fields"]}

    applicable = {}
    exclusions = []
    for req in case["requirements"]:
        if _cond(req.get("applies_when"), values):
            applicable[req["id"]] = req["source_kind"]
        else:
            exclusions.append({
                "requirement_id": req["id"],
                "source_kind": req["source_kind"],
                "reason": "APPLICABILITY_CONDITION_FALSE",
                "condition": deepcopy(req.get("applies_when")),
            })

    branches = [b for b in case["branches"] if all(_cond(c, values) for c in b["when"])]
    if len(branches) != 1:
        raise ValueError("ORACLE_BRANCH")
    selected = branches[0]
    rules = list(case["common_rules"]) + list(selected["rules"])
    nodes = []
    consumers = {rid: [] for rid in applicable}

    pending = list(rules)
    while pending:
        progressed = False
        remain = []
        for rule in pending:
            if not all(x in values for x in rule["inputs"]):
                remain.append(rule)
                continue
            op = rule["op"]
            vs = [values[x] for x in rule["inputs"]]
            if op == "sum": value = vs[0] + vs[1]
            elif op == "difference": value = vs[0] - vs[1]
            elif op == "ratio": value = float(vs[0]) / float(vs[1])
            elif op == "scale": value = float(vs[0]) * float(rule["factor"])
            elif op == "threshold_gt": value = float(vs[0]) > float(rule["threshold"])
            elif op == "identity": value = vs[0]
            else: raise ValueError("ORACLE_OP")
            values[rule["output"]] = value
            meta[rule["output"]] = {
                "type": rule["output_type"],
                "dimension": rule["output_dimension"],
            }
            inv = deepcopy(rule.get("invariants", []))
            for x in inv:
                if x["kind"] == "min" and not value >= x["value"]: raise ValueError("ORACLE_MIN")
                if x["kind"] == "max" and not value <= x["value"]: raise ValueError("ORACLE_MAX")
                if x["kind"] == "must_be_true" and value is not True: raise ValueError("ORACLE_TRUE")
            consumes = sorted(rule.get("consumes_requirements", []))
            for rid in consumes:
                if rid not in consumers:
                    raise ValueError("ORACLE_CONSUMES")
                consumers[rid].append(rule["id"])
            nodes.append({
                "rule_id": rule["id"],
                "operation": op,
                "inputs": list(rule["inputs"]),
                "output": rule["output"],
                "output_type": rule["output_type"],
                "output_dimension": rule["output_dimension"],
                "consumes_requirements": consumes,
                "invariants": inv,
                "evaluated_value": value,
            })
            progressed = True
        if not progressed: raise ValueError("ORACLE_DAG")
        pending = remain

    if any(not xs for xs in consumers.values()):
        raise ValueError("ORACLE_LINEAGE")
    lineage = [
        {
            "requirement_id": rid,
            "source_kind": applicable[rid],
            "consumer_rule_ids": sorted(consumers[rid]),
        }
        for rid in sorted(applicable)
    ]
    outputs = [
        {
            "id": oid,
            "type": meta[oid]["type"],
            "dimension": meta[oid]["dimension"],
            "value": values[oid],
        }
        for oid in case["required_outputs"]
    ]
    return {
        "selected_branch_id": selected["id"],
        "nodes": nodes,
        "requirement_lineage": lineage,
        "justified_exclusions": sorted(exclusions, key=lambda x: x["requirement_id"]),
        "outputs": outputs,
    }


def score(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping) or candidate.get("status") != "COMPILED":
        return {"pass": False, "reason": "CANDIDATE_NOT_COMPILED"}
    expected = _expected(case)
    for key in ("selected_branch_id", "nodes", "requirement_lineage", "justified_exclusions", "outputs"):
        if candidate.get(key) != expected[key]:
            return {"pass": False, "reason": "MISMATCH:" + key}
    return {"pass": True, "reason": "PASS"}


def run_batch(seed: int, count: int, solver) -> dict[str, Any]:
    rows = []
    by_branch = defaultdict(lambda: {"pass": 0, "total": 0})
    for i in range(count):
        case = generate_case(seed, i)
        try:
            out = solver(public_case(case))
            verdict = score(case, out)
        except Exception as exc:
            verdict = {"pass": False, "reason": type(exc).__name__ + ":" + str(exc)}
        branch = "REGULATED" if i % 2 == 0 else "STANDARD"
        by_branch[branch]["total"] += 1
        by_branch[branch]["pass"] += int(bool(verdict["pass"]))
        rows.append({"case_id": case["case_id"], "pass": bool(verdict["pass"]), "reason": verdict["reason"]})
    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema": "PROJECT_BRAIN_STRUCTURED_METHOD_WHOLE_DIMENSION_PREFLIGHT_RESULT_V1",
        "case_count": count,
        "passed": passed,
        "failed": count - passed,
        "all_pass": passed == count,
        "by_branch": dict(by_branch),
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
