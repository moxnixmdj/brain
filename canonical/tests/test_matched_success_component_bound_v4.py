import copy
import hashlib
import json

from canonical.runtime.matched_success_component_bound_v4 import (
    INPUT_SCHEMA,
    RULES,
    SCORERS,
    compile_v4,
)


def h(x):
    return hashlib.sha256(str(x).encode()).hexdigest()


def b(x):
    return hashlib.sha1(str(x).encode()).hexdigest()


def digest(x):
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def receipt(label, binding):
    return {
        "path": f"canonical/verification/{label}.json",
        "git_blob_sha": b(label),
        "independent_or_objective": True,
        "binding_sha256": digest(binding),
    }


def component(cid, i, kind, semantic):
    path, sha = SCORERS[kind]
    row = {
        "component_id": f"{cid}::{i}::{kind}",
        "kind": kind,
        "case_payload_sha256": h(f"{cid}:{i}:case"),
        "candidate_output_sha256": h(f"{cid}:{i}:output"),
        "scorer_result_sha256": h(f"{cid}:{i}:result"),
        "semantic_projection_sha256": semantic,
        "scorer_path": path,
        "scorer_git_blob_sha": sha,
        "base_scorer_pass": True,
    }
    row["receipt"] = receipt(f"{cid}_{i}_component", row)
    return row


def edge(cid, left, right, i):
    eid = left["component_id"] + "->" + right["component_id"]
    shape = h(f"{cid}:{i}:shape")

    def run(role, sem, terminal, bridge, composite):
        row = {
            "edge_id": eid,
            "run_role": role,
            "transported_semantic_sha256": sem,
            "transported_shape_sha256": shape,
            "downstream_terminal_semantic_sha256": terminal,
            "downstream_case_payload_sha256": right["case_payload_sha256"],
            "downstream_scorer_path": right["scorer_path"],
            "downstream_scorer_git_blob_sha": right["scorer_git_blob_sha"],
            "base_scorer_pass": True,
            "bridge_check_pass": bridge,
            "composite_pass": composite,
        }
        row["receipt"] = receipt(f"{cid}_{i}_{role}", row)
        return row

    return {
        "edge_id": eid,
        "true_run": run(
            "true",
            left["semantic_projection_sha256"],
            right["semantic_projection_sha256"],
            True,
            True,
        ),
        "ablated_run": run(
            "ablated",
            h(f"{cid}:{i}:decoy"),
            h(f"{cid}:{i}:bad-terminal"),
            False,
            False,
        ),
        "rescue_run": run(
            "rescue",
            left["semantic_projection_sha256"],
            right["semantic_projection_sha256"],
            True,
            True,
        ),
    }


def base():
    classes = []
    for cid, (kinds, atoms) in RULES.items():
        sems = [h(f"{cid}:semantic:{i}") for i in range(len(kinds))]
        comps = [
            component(cid, i, kind, sems[i])
            for i, kind in enumerate(kinds)
        ]
        edges = [
            edge(cid, comps[i], comps[i + 1], i)
            for i in range(len(comps) - 1)
        ]
        v3 = {
            "class_id": cid,
            "true_upstream_semantic_sha256": sems[0],
            "true_terminal_semantic_sha256": sems[-1],
            "true_run_semantics_sha256": h(cid + ":v3:true"),
            "ablated_run_semantics_sha256": h(cid + ":v3:ablated"),
            "rescue_run_semantics_sha256": h(cid + ":v3:rescue"),
        }
        v3["receipt"] = receipt(cid + "_v3", v3)

        class_digest = digest({
            "components": [c["semantic_projection_sha256"] for c in comps],
            "edges": [e["edge_id"] for e in edges],
            "v3": v3 | {"receipt": v3["receipt"]},
        })
        # Runtime hashes v3_binding without the receipt.
        class_digest = digest({
            "components": [c["semantic_projection_sha256"] for c in comps],
            "edges": [e["edge_id"] for e in edges],
            "v3": {k: v for k, v in v3.items() if k != "receipt"},
        })

        bridges = []
        for atom in atoms:
            row = {
                "class_id": cid,
                "atom": atom,
                "implication_rule_id":
                    "COMPONENT_BOUND_INTERVENTIONAL_V4::"
                    + atom.split(":", 1)[1],
                "class_evidence_sha256": class_digest,
            }
            bridges.append({
                "atom": atom,
                "implication_rule_id": row["implication_rule_id"],
                "receipt": receipt(cid + "_" + atom, row),
            })

        classes.append({
            "class_id": cid,
            "components": comps,
            "edges": edges,
            "v3_binding": v3,
            "atom_bridges": bridges,
        })
    return {"schema": INPUT_SCHEMA, "classes": classes}


def cls(doc, cid):
    return next(x for x in doc["classes"] if x["class_id"] == cid)


def rebind(raw, label):
    binding = {k: v for k, v in raw.items() if k != "receipt"}
    raw["receipt"] = receipt(label, binding)


def test_valid_component_bound_bundle_passes_candidate_compiler():
    out = compile_v4(base())
    assert out["status"].startswith(
        "PASS__COMPONENT_BOUND_INTERVENTIONAL_V4"
    )
    assert out["atom_count"] == 10
    assert out["kills_v3_scalar_transducer_countermodel"] is True
    assert out["scope_credit_authorized"] is False


def test_missing_actual_component_fails_closed():
    x = base()
    cls(x, "RESEARCH_TOOL_ARTIFACT")["components"].pop()
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "COMPONENT_COUNT_MISMATCH" in out["errors"][0]


def test_fake_component_scorer_identity_fails_closed():
    x = base()
    c = cls(x, "BROWSER_MEMORY_RECOVERY")["components"][0]
    c["scorer_git_blob_sha"] = "0" * 40
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "SCORER_IDENTITY_MISMATCH" in out["errors"][0]


def test_standalone_component_success_without_causal_flip_fails():
    x = base()
    e = cls(x, "RESEARCH_TOOL_ARTIFACT")["edges"][0]
    e["ablated_run"]["bridge_check_pass"] = True
    rebind(e["ablated_run"], "research_edge_ablated_rebound")
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "BRIDGE_INTERVENTION_PATTERN_INVALID" in out["errors"][0]


def test_same_semantic_ablation_fails_closed():
    x = base()
    e = cls(x, "CODING_DEBUG_TOOL_DISCOVERY")["edges"][0]
    e["ablated_run"]["transported_semantic_sha256"] = (
        e["true_run"]["transported_semantic_sha256"]
    )
    rebind(e["ablated_run"], "coding_edge_ablated_rebound")
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "ABLATION_NOT_DISTINCT" in out["errors"][0]


def test_v3_must_bind_actual_first_component_projection():
    x = base()
    row = cls(x, "AGENCY_THREE_TOOL_LONG_HORIZON")
    row["v3_binding"]["true_upstream_semantic_sha256"] = h("unrelated")
    rebind(row["v3_binding"], "agency_v3_rebound")
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "V3_UPSTREAM_NOT_FIRST_COMPONENT" in out["errors"][0]


def test_missing_atom_specific_bridge_fails_closed():
    x = base()
    cls(x, "INSTRUCTION_CHANGE_CONTROL")["atom_bridges"].pop()
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "ATOM_SET_MISMATCH" in out["errors"][0]


def test_component_receipt_substitution_fails_closed():
    x = base()
    c = cls(x, "CROSS_CAPABILITY_HANDOFF_ROLLBACK")["components"][0]
    c["candidate_output_sha256"] = h("substituted-output")
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "BINDING_SHA256_MISMATCH" in out["errors"][0]


def test_base_component_scorer_must_actually_pass():
    x = base()
    c = cls(x, "DELEGATION_SYNTHESIS_ARTIFACT")["components"][1]
    c["base_scorer_pass"] = False
    out = compile_v4(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "BASE_SCORER_NOT_PASS" in out["errors"][0]
