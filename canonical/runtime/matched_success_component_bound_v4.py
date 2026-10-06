from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_COMPONENT_BOUND_INPUT_V4"
OUTPUT_SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_COMPONENT_BOUND_OUTPUT_V4"
H40 = re.compile(r"^[0-9a-f]{40}$")
H64 = re.compile(r"^[0-9a-f]{64}$")

SCORERS = {
    "browser": ("canonical/runtime/browser_state_information_safe_proof.py", "3723d3233d6058f0a43491e4654a21490f992d1e"),
    "delegation_v2": ("canonical/runtime/delegation_whole_scope_proof_v2.py", "928466401b36e4f3b09c517950cc050432a0616f"),
    "delegation_v3": ("canonical/runtime/delegation_structural_variety_proof_v3.py", "f5e1f45519278ed2cafa27d23b8602b0a362a492"),
    "tool": ("canonical/runtime/tool_discovery_information_safe_proof_v2.py", "5e8a953864e13ec76768c3e8920644107c65a644"),
    "m0": ("canonical/runtime/m0a_raw_source_terminal_suite_v2.py", "63b5daacfa5623c38228d41f6a84e548890d252d"),
    "m0_change": ("canonical/runtime/m0a_raw_source_terminal_suite_v2.py", "63b5daacfa5623c38228d41f6a84e548890d252d"),
    "structured": ("canonical/runtime/contract_native_proof_suites.py", "0210790c7dd705ef328e1b55d529a30c5c6c3337"),
    "p1": ("canonical/runtime/contract_native_proof_suites.py", "0210790c7dd705ef328e1b55d529a30c5c6c3337"),
    "p2": ("canonical/runtime/contract_native_proof_suites.py", "0210790c7dd705ef328e1b55d529a30c5c6c3337"),
    "p3": ("canonical/runtime/contract_native_proof_suites.py", "0210790c7dd705ef328e1b55d529a30c5c6c3337"),
    "native": ("canonical/runtime/native_artifact_cross_format_proof_v1.py", "904eb61171f5ee775ff7824c1be7778d7acc4a23"),
}

RULES = {
    "AGENCY_THREE_TOOL_LONG_HORIZON": (
        ("browser", "tool", "delegation_v2"),
        (
            "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
            "dimension:long_horizon_state_retention",
            "dimension:minimal_oversight_completion",
        ),
    ),
    "INSTRUCTION_CHANGE_CONTROL": (
        ("m0", "m0_change", "delegation_v2"),
        (
            "dimension:multi_constraint_instruction_compliance",
            "dimension:requirement_change",
        ),
    ),
    "RESEARCH_TOOL_ARTIFACT": (
        ("tool", "p3", "native"),
        ("dimension:research_plus_tool_use_plus_artifact_creation",),
    ),
    "BROWSER_MEMORY_RECOVERY": (
        ("browser", "p1"),
        ("dimension:browser_or_computer_action_plus_memory_plus_recovery",),
    ),
    "CODING_DEBUG_TOOL_DISCOVERY": (
        ("structured", "p1", "tool"),
        ("dimension:coding_plus_debugging_plus_tool_discovery",),
    ),
    "DELEGATION_SYNTHESIS_ARTIFACT": (
        ("delegation_v3", "p3", "native"),
        ("dimension:delegation_plus_evidence_synthesis_plus_artifact_production",),
    ),
    "CROSS_CAPABILITY_HANDOFF_ROLLBACK": (
        ("delegation_v2", "tool", "p1", "p2"),
        ("dimension:cross_capability_state_handoff_and_rollback",),
    ),
}
ALL_ATOMS = {a for _, atoms in RULES.values() for a in atoms}


class V4Error(ValueError):
    pass


def _digest(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _sha(v: Any, n: str) -> str:
    if not isinstance(v, str) or not H64.fullmatch(v):
        raise V4Error(n + "_INVALID")
    return v


def _token(v: Any, n: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise V4Error(n + "_INVALID")
    return v.strip()


def _receipt(raw: Any, prefix: str, binding: Mapping[str, Any]) -> None:
    if not isinstance(raw, Mapping):
        raise V4Error(prefix + "_INVALID")
    if not isinstance(raw.get("path"), str) or not raw["path"]:
        raise V4Error(prefix + "_PATH_INVALID")
    if not isinstance(raw.get("git_blob_sha"), str) or not H40.fullmatch(raw["git_blob_sha"]):
        raise V4Error(prefix + "_BLOB_INVALID")
    if raw.get("independent_or_objective") is not True:
        raise V4Error(prefix + "_INDEPENDENCE_NOT_TRUE")
    expected = _digest(binding)
    if raw.get("binding_sha256") != expected:
        raise V4Error(prefix + "_BINDING_SHA256_MISMATCH")


def _component(cid: str, i: int, raw: Any, kind: str) -> dict[str, Any]:
    p = f"{cid}_COMP_{i}"
    if not isinstance(raw, Mapping) or raw.get("kind") != kind:
        raise V4Error(p + "_KIND_MISMATCH")
    path, blob = SCORERS[kind]
    if raw.get("scorer_path") != path or raw.get("scorer_git_blob_sha") != blob:
        raise V4Error(p + "_SCORER_IDENTITY_MISMATCH")
    row = {
        "component_id": _token(raw.get("component_id"), p + "_ID"),
        "kind": kind,
        "case_payload_sha256": _sha(raw.get("case_payload_sha256"), p + "_CASE"),
        "candidate_output_sha256": _sha(raw.get("candidate_output_sha256"), p + "_OUTPUT"),
        "scorer_result_sha256": _sha(raw.get("scorer_result_sha256"), p + "_RESULT"),
        "semantic_projection_sha256": _sha(raw.get("semantic_projection_sha256"), p + "_SEMANTIC"),
        "scorer_path": path,
        "scorer_git_blob_sha": blob,
        "base_scorer_pass": raw.get("base_scorer_pass"),
    }
    if row["base_scorer_pass"] is not True:
        raise V4Error(p + "_BASE_SCORER_NOT_PASS")
    _receipt(raw.get("receipt"), p + "_RECEIPT", row)
    return row


def _edge(cid: str, i: int, raw: Any, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    p = f"{cid}_EDGE_{i}"
    if not isinstance(raw, Mapping):
        raise V4Error(p + "_INVALID")
    edge_id = left["component_id"] + "->" + right["component_id"]
    if raw.get("edge_id") != edge_id:
        raise V4Error(p + "_ID_MISMATCH")

    runs = {}
    for role in ("true", "ablated", "rescue"):
        rr = raw.get(role + "_run")
        if not isinstance(rr, Mapping):
            raise V4Error(p + "_" + role.upper() + "_INVALID")
        row = {
            "edge_id": edge_id,
            "run_role": role,
            "transported_semantic_sha256": _sha(rr.get("transported_semantic_sha256"), p + "_SEM"),
            "transported_shape_sha256": _sha(rr.get("transported_shape_sha256"), p + "_SHAPE"),
            "downstream_terminal_semantic_sha256": _sha(rr.get("downstream_terminal_semantic_sha256"), p + "_TERM"),
            "downstream_case_payload_sha256": _sha(
                rr.get("downstream_case_payload_sha256"),
                p + "_CASE",
            ),
            "downstream_case_template_sha256": _sha(
                rr.get("downstream_case_template_sha256"),
                p + "_CASE_TEMPLATE",
            ),
            "downstream_scorer_path": right["scorer_path"],
            "downstream_scorer_git_blob_sha": right["scorer_git_blob_sha"],
            "base_scorer_pass": rr.get("base_scorer_pass"),
            "bridge_check_pass": rr.get("bridge_check_pass"),
            "composite_pass": rr.get("composite_pass"),
        }
        _receipt(rr.get("receipt"), p + "_" + role.upper() + "_RECEIPT", row)
        runs[role] = row

    t, a, r = runs["true"], runs["ablated"], runs["rescue"]
    if t["transported_semantic_sha256"] != left["semantic_projection_sha256"]:
        raise V4Error(p + "_TRUE_NOT_FROM_UPSTREAM_COMPONENT")
    if r["transported_semantic_sha256"] != t["transported_semantic_sha256"]:
        raise V4Error(p + "_RESCUE_NOT_RESTORED")
    if a["transported_semantic_sha256"] == t["transported_semantic_sha256"]:
        raise V4Error(p + "_ABLATION_NOT_DISTINCT")
    if not (t["transported_shape_sha256"] == a["transported_shape_sha256"] == r["transported_shape_sha256"]):
        raise V4Error(p + "_SHAPE_MISMATCH")
    if not (
        t["downstream_case_template_sha256"]
        == a["downstream_case_template_sha256"]
        == r["downstream_case_template_sha256"]
    ):
        raise V4Error(p + "_CASE_TEMPLATE_MISMATCH")
    if t["downstream_case_payload_sha256"] != right["case_payload_sha256"]:
        raise V4Error(p + "_TRUE_CASE_NOT_COMPONENT_CASE")
    if r["downstream_case_payload_sha256"] != t["downstream_case_payload_sha256"]:
        raise V4Error(p + "_RESCUE_CASE_NOT_RESTORED")
    if a["downstream_case_payload_sha256"] == t["downstream_case_payload_sha256"]:
        raise V4Error(p + "_ABLATION_CASE_NOT_DISTINCT")
    if not all(x["base_scorer_pass"] is True for x in (t, a, r)):
        raise V4Error(p + "_BASE_SCORER_NOT_RUN_OR_NOT_PASS")
    if (t["bridge_check_pass"], a["bridge_check_pass"], r["bridge_check_pass"]) != (True, False, True):
        raise V4Error(p + "_BRIDGE_INTERVENTION_PATTERN_INVALID")
    if (t["composite_pass"], a["composite_pass"], r["composite_pass"]) != (True, False, True):
        raise V4Error(p + "_COMPOSITE_INTERVENTION_PATTERN_INVALID")
    if t["downstream_terminal_semantic_sha256"] != right["semantic_projection_sha256"]:
        raise V4Error(p + "_TRUE_TERMINAL_NOT_DOWNSTREAM_COMPONENT")
    if r["downstream_terminal_semantic_sha256"] != t["downstream_terminal_semantic_sha256"]:
        raise V4Error(p + "_RESCUE_TERMINAL_NOT_RESTORED")
    if a["downstream_terminal_semantic_sha256"] == t["downstream_terminal_semantic_sha256"]:
        raise V4Error(p + "_ABLATION_TERMINAL_NOT_DISTINCT")
    return {"edge_id": edge_id, "runs": runs}


def compile_v4(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise V4Error("SCHEMA_INVALID")
        rows = doc.get("classes")
        if not isinstance(rows, list):
            raise V4Error("CLASSES_INVALID")
        parsed = {str(x.get("class_id")): x for x in rows if isinstance(x, Mapping)}
        if set(parsed) != set(RULES) or len(parsed) != len(rows):
            raise V4Error("CLASS_SET_MISMATCH")

        covered = set()
        summaries = {}
        for cid, (kinds, atoms) in RULES.items():
            raw = parsed[cid]
            comps_raw = raw.get("components")
            if not isinstance(comps_raw, list) or len(comps_raw) != len(kinds):
                raise V4Error(cid + "_COMPONENT_COUNT_MISMATCH")
            comps = [_component(cid, i, comps_raw[i], kind) for i, kind in enumerate(kinds)]
            if len({c["component_id"] for c in comps}) != len(comps):
                raise V4Error(cid + "_COMPONENT_ID_DUPLICATE")

            edges_raw = raw.get("edges")
            if not isinstance(edges_raw, list) or len(edges_raw) != len(comps) - 1:
                raise V4Error(cid + "_EDGE_COUNT_MISMATCH")
            edges = [_edge(cid, i, edges_raw[i], comps[i], comps[i + 1]) for i in range(len(edges_raw))]

            bridges = raw.get("atom_bridges")
            if not isinstance(bridges, list):
                raise V4Error(cid + "_ATOM_BRIDGES_INVALID")
            atom_map = {str(x.get("atom")): x for x in bridges if isinstance(x, Mapping)}
            if set(atom_map) != set(atoms) or len(atom_map) != len(bridges):
                raise V4Error(cid + "_ATOM_SET_MISMATCH")
            class_digest = _digest({
                "components": [
                    {
                        "component_id": c["component_id"],
                        "kind": c["kind"],
                        "semantic_projection_sha256":
                            c["semantic_projection_sha256"],
                        "scorer_result_sha256":
                            c["scorer_result_sha256"],
                    }
                    for c in comps
                ],
                "edges": [
                    {
                        "edge_id": e["edge_id"],
                        "true_transport": e["runs"]["true"][
                            "transported_semantic_sha256"
                        ],
                        "ablated_transport": e["runs"]["ablated"][
                            "transported_semantic_sha256"
                        ],
                        "true_terminal": e["runs"]["true"][
                            "downstream_terminal_semantic_sha256"
                        ],
                        "ablated_terminal": e["runs"]["ablated"][
                            "downstream_terminal_semantic_sha256"
                        ],
                    }
                    for e in edges
                ],
            })
            for atom in atoms:
                bridge = atom_map[atom]
                binding = {
                    "class_id": cid,
                    "atom": atom,
                    "implication_rule_id": "COMPONENT_BOUND_INTERVENTIONAL_V4::" + atom.split(":", 1)[1],
                    "class_evidence_sha256": class_digest,
                }
                if bridge.get("implication_rule_id") != binding["implication_rule_id"]:
                    raise V4Error(cid + "_ATOM_RULE_MISMATCH")
                _receipt(bridge.get("receipt"), cid + "_ATOM_RECEIPT", binding)
                covered.add(atom)

            summaries[cid] = {"component_count": len(comps), "edge_count": len(edges), "atoms": sorted(atoms)}

        if covered != ALL_ATOMS:
            raise V4Error("TEN_ATOM_COVERAGE_MISMATCH")
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__COMPONENT_BOUND_INTERVENTIONAL_V4__INDEPENDENT_EXACT_RECEIPT_VERIFICATION_REQUIRED",
            "class_count": len(summaries),
            "atom_count": len(covered),
            "covered_atoms": sorted(covered),
            "classes": summaries,
            "kills_v3_scalar_transducer_countermodel": True,
            "synthetic_v3_binding_required": False,
            "actual_component_chain_is_semantic_authority": True,
            "scope_credit_authorized": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except (V4Error, KeyError, TypeError) as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "scope_credit_authorized": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
