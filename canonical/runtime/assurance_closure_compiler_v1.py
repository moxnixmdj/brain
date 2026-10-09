"""UVCK V2 Assurance Closure Compiler V1.

A tiny deterministic meta-assurance kernel above Project Brain's existing
controllers. It does not synthesize semantic truth, execute actions, or grant
terminal authority. It answers one question:

    Is the declared root closed under the currently supplied support graph,
    freshness, defeaters, execution closure, and adversarial closure?

New architectural primitives are justified only when a challenge cannot be
represented with the fixed primitive vocabulary below. Open obligations inside
that vocabulary remain ordinary residuals for the existing fixed-point solver.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ASSURANCE_CLOSURE_COMPILER_V1"
GRAPH_SCHEMA = "PROJECT_BRAIN_ASSURANCE_CLOSURE_GRAPH_V1"

PRIMITIVE_TYPES = frozenset({
    "CLAIM",
    "OBLIGATION",
    "ASSUMPTION",
    "EVIDENCE",
    "DEPENDENCY",
    "DEFEATER",
    "EFFECT",
    "AUTHORITY",
    "RESOURCE",
    "MONITOR",
    "EPOCH",
    "TRANSITION",
})

TERMINAL_LEAF_TYPES = frozenset({"EVIDENCE", "ASSUMPTION", "EPOCH"})
NODE_STATUSES = frozenset({
    "SUPPORTED",
    "OPEN",
    "STALE",
    "PROVEN_IRRELEVANT",
    "REJECTED",
})

FOUR_GATES = (
    "representation_closure",
    "proof_closure",
    "execution_closure",
    "adversarial_closure",
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        **_base("FAIL_CLOSED", passed=False),
        "reason": reason,
        **extra,
    }


def _as_ids(value: Any, field: str) -> tuple[list[str] | None, str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list):
        return None, f"{field}_NOT_LIST"
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            return None, f"{field}_ID_INVALID"
        out.append(item)
    if len(out) != len(set(out)):
        return None, f"{field}_DUPLICATE_ID"
    return out, None


def evaluate(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one explicit assurance graph.

    The compiler is intentionally conservative:
    * unknown primitive types => representation gap / new primitive candidate;
    * dangling references or dependency cycles => fail closed;
    * OPEN/STALE support or unresolved defeaters => OPEN residual;
    * a supported defeater against a root => COUNTERPROVED;
    * full closure requires all four gates.
    """
    if not isinstance(graph, Mapping):
        return _fail("GRAPH_NOT_OBJECT")
    if graph.get("schema") != GRAPH_SCHEMA:
        return _fail("GRAPH_SCHEMA_INVALID")

    raw_nodes = graph.get("nodes")
    if not isinstance(raw_nodes, list):
        return _fail("NODES_NOT_LIST")

    roots, error = _as_ids(graph.get("root_ids"), "ROOT_IDS")
    if error is not None or not roots:
        return _fail(error or "ROOT_IDS_REQUIRED")

    nodes: dict[str, dict[str, Any]] = {}
    unsupported_types: set[str] = set()
    malformed: list[str] = []

    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            malformed.append("NODE_NOT_OBJECT")
            continue
        node_id = raw.get("id")
        node_type = raw.get("type")
        status = raw.get("status")
        if not isinstance(node_id, str) or not node_id.strip() or node_id != node_id.strip():
            malformed.append("NODE_ID_INVALID")
            continue
        if node_id in nodes:
            return _fail("DUPLICATE_NODE_ID", node_id=node_id)
        if not isinstance(node_type, str) or not node_type:
            malformed.append(f"NODE_TYPE_INVALID:{node_id}")
            continue
        if node_type not in PRIMITIVE_TYPES:
            unsupported_types.add(node_type)
        if status not in NODE_STATUSES:
            malformed.append(f"NODE_STATUS_INVALID:{node_id}")
            continue
        deps, dep_error = _as_ids(raw.get("depends_on"), f"DEPENDS_ON:{node_id}")
        defeaters, defeater_error = _as_ids(raw.get("defeated_by"), f"DEFEATED_BY:{node_id}")
        if dep_error or defeater_error:
            malformed.append(dep_error or defeater_error or "NODE_REFERENCE_INVALID")
            continue
        node = deepcopy(dict(raw))
        node["depends_on"] = deps
        node["defeated_by"] = defeaters
        nodes[node_id] = node

    if malformed:
        return _fail("MALFORMED_NODE_SET", errors=sorted(malformed))

    missing_roots = sorted(set(roots) - set(nodes))
    if missing_roots:
        return _fail("ROOT_NODE_MISSING", missing_root_ids=missing_roots)

    refs: set[str] = set()
    for node in nodes.values():
        refs.update(node["depends_on"])
        refs.update(node["defeated_by"])
    dangling = sorted(refs - set(nodes))
    if dangling:
        return _fail("DANGLING_NODE_REFERENCE", dangling_ids=dangling)

    # Dependency cycles are not allowed to self-certify. A future cycle proof
    # must be represented as an explicit admitted evidence/foundation node,
    # not by circular graph support.
    color: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node_id: str) -> None:
        state = color.get(node_id, 0)
        if state == 2:
            return
        if state == 1:
            if node_id in stack:
                start = stack.index(node_id)
                cycles.append(stack[start:] + [node_id])
            return
        color[node_id] = 1
        stack.append(node_id)
        for dep in nodes[node_id]["depends_on"]:
            visit(dep)
        stack.pop()
        color[node_id] = 2

    for root_id in roots:
        visit(root_id)

    if cycles:
        return _fail(
            "UNSUPPORTED_DEPENDENCY_CYCLE",
            cycles=cycles,
            representation_closure=(not unsupported_types),
            new_primitive_required=bool(unsupported_types),
            unsupported_primitive_types=sorted(unsupported_types),
        )

    open_residuals: set[str] = set()
    stale_ids: set[str] = set()
    unsupported_leaf_ids: set[str] = set()
    unresolved_defeaters: set[str] = set()
    active_defeaters: set[str] = set()
    proved_irrelevant: set[str] = set()
    memo: dict[str, bool] = {}

    def closed(node_id: str) -> bool:
        if node_id in memo:
            return memo[node_id]
        node = nodes[node_id]
        status = node["status"]

        if status == "PROVEN_IRRELEVANT":
            proved_irrelevant.add(node_id)
            memo[node_id] = True
            return True
        if status == "OPEN":
            open_residuals.add(node_id)
            for dep in node["depends_on"]:
                closed(dep)
            memo[node_id] = False
            return False
        if status == "STALE":
            stale_ids.add(node_id)
            open_residuals.add(node_id)
            for dep in node["depends_on"]:
                closed(dep)
            memo[node_id] = False
            return False
        if status == "REJECTED":
            open_residuals.add(node_id)
            for dep in node["depends_on"]:
                closed(dep)
            memo[node_id] = False
            return False

        # Defeater semantics are order-independent. Any SUPPORTED defeater
        # counterproves the node even when an earlier defeater is unresolved.
        # Only when no active defeater exists may OPEN/STALE defeaters classify
        # the node as an unresolved assurance residual.
        supported_defeaters = [
            defeater_id
            for defeater_id in node["defeated_by"]
            if nodes[defeater_id]["status"] == "SUPPORTED"
        ]
        if supported_defeaters:
            active_defeaters.update(supported_defeaters)
            memo[node_id] = False
            return False

        unresolved_here = [
            defeater_id
            for defeater_id in node["defeated_by"]
            if nodes[defeater_id]["status"] in {"OPEN", "STALE"}
        ]
        if unresolved_here:
            unresolved_defeaters.update(unresolved_here)
            open_residuals.update(unresolved_here)
            memo[node_id] = False
            return False

        deps = node["depends_on"]
        if not deps:
            if node["type"] in TERMINAL_LEAF_TYPES and node.get("authoritative_leaf") is True:
                memo[node_id] = True
                return True
            unsupported_leaf_ids.add(node_id)
            open_residuals.add(node_id)
            memo[node_id] = False
            return False

        ok = all(closed(dep) for dep in deps)
        memo[node_id] = ok
        return ok

    root_closed = {root_id: closed(root_id) for root_id in roots}

    representation_closure = not unsupported_types
    proof_closure = all(root_closed.values()) and not active_defeaters and not unresolved_defeaters

    # Generic graph input cannot self-certify execution or independent
    # adversarial closure. Those gates must be derived by a trusted adapter or
    # verifier entrypoint, never by caller booleans embedded in the graph.
    execution_closure = False
    adversarial_closure = False

    gates = {
        "representation_closure": representation_closure,
        "proof_closure": proof_closure,
        "execution_closure": execution_closure,
        "adversarial_closure": adversarial_closure,
    }

    if active_defeaters:
        status = "COUNTERPROVED"
        passed = False
    elif unsupported_types:
        status = "OPEN__NEW_PRIMITIVE_REPRESENTATION_REQUIRED"
        passed = False
    elif not proof_closure:
        status = "OPEN__ASSURANCE_RESIDUAL"
        passed = False
    elif not execution_closure:
        status = "OPEN__EXECUTION_CLOSURE_REQUIRED"
        passed = False
    elif not adversarial_closure:
        status = "OPEN__ADVERSARIAL_CLOSURE_REQUIRED"
        passed = False
    else:
        status = "CLOSED__ALL_FOUR_ASSURANCE_GATES"
        passed = True

    residual = sorted(open_residuals | unresolved_defeaters | unsupported_leaf_ids)

    return {
        **_base(status, passed=passed),
        "graph_sha256": digest(graph),
        "root_ids": roots,
        "root_closed": root_closed,
        "closure_gates": gates,
        "open_residual_ids": residual,
        "stale_ids": sorted(stale_ids),
        "active_defeater_ids": sorted(active_defeaters),
        "unresolved_defeater_ids": sorted(unresolved_defeaters),
        "unsupported_leaf_ids": sorted(unsupported_leaf_ids),
        "proved_irrelevant_ids": sorted(proved_irrelevant),
        "unsupported_primitive_types": sorted(unsupported_types),
        "new_primitive_required": bool(unsupported_types),
        "existing_kernel_expressive": not unsupported_types,
        "closure_theorem": (
            "CLOSED_IFF_REPRESENTATION_AND_PROOF_AND_EXECUTION_AND_ADVERSARIAL_CLOSURE"
        ),
    }


def compile_controller_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Compile the existing R2 fixed-point result into a V2 closure graph.

    This adapter deliberately grants no additional authority. Existing PASS
    results can establish the execution gate only when the existing controller
    already says semantic acceptance and actual goal satisfaction are verified.
    Integrated adversarial closure remains a separate obligation.
    """
    if not isinstance(result, Mapping):
        raise TypeError("RESULT_NOT_OBJECT")

    passed = result.get("pass") is True
    root_status = "SUPPORTED" if passed else "OPEN"
    nodes: list[dict[str, Any]] = []

    if passed:
        evidence_id = "controller:verified-goal-satisfaction"
        nodes.append({
            "id": evidence_id,
            "type": "EVIDENCE",
            "status": "SUPPORTED",
            "authoritative_leaf": True,
            "source_schema": result.get("schema"),
            "source_status": result.get("status"),
        })
        nodes.append({
            "id": "root:goal",
            "type": "CLAIM",
            "status": root_status,
            "depends_on": [evidence_id],
            "defeated_by": [],
        })
    else:
        nodes.append({
            "id": "root:goal",
            "type": "CLAIM",
            "status": "OPEN",
            "depends_on": ["obligation:next-edge"],
            "defeated_by": [],
        })
        nodes.append({
            "id": "obligation:next-edge",
            "type": "OBLIGATION",
            "status": "OPEN",
            "required_edge": (
                result.get("next_required_edge")
                or result.get("next_required_effect")
                or result.get("status")
                or "UNSPECIFIED_OPEN_EDGE"
            ),
        })

    return {
        "schema": GRAPH_SCHEMA,
        "root_ids": ["root:goal"],
        "nodes": nodes,
        "source_result_sha256": digest(dict(result)),
        "source_terminal_authority": result.get("terminal_authority") is True,
    }


def evaluate_controller_result(result: Mapping[str, Any]) -> dict[str, Any]:
    graph = compile_controller_result(result)
    out = evaluate(graph)
    execution_closed = bool(
        result.get("pass") is True
        and result.get("semantic_acceptance_complete") is True
        and result.get("actual_goal_satisfaction_verified") is True
    )
    out["closure_gates"]["execution_closure"] = execution_closed
    out["closure_gates"]["adversarial_closure"] = False
    if (
        out["closure_gates"]["representation_closure"]
        and out["closure_gates"]["proof_closure"]
        and execution_closed
    ):
        out["status"] = "OPEN__ADVERSARIAL_CLOSURE_REQUIRED"
    out["pass"] = False
    out["compiled_from_controller_result"] = True
    out["source_result_sha256"] = graph["source_result_sha256"]
    return out
