from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def build_universe():
    graph = _load("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json")
    proof = _load("canonical/governance/GLOBAL_TERMINAL_PROOF_CUT_V1.json")
    manifest = _load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
    v6 = _load("canonical/governance/RESIDUAL_MINIMUM_REALITY_CUT_VERDICT_V6.json")
    frozen = _load("canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json")

    proof_only = set(graph.get("proof_only_mechanism_obligations", []))
    open_lane_ids = set(graph.get("open_mechanism_residuals", []))
    shared_open = list(graph.get("shared_cross_lane_open_mechanisms", []))

    frozen_lanes = {
        row["id"]: row
        for row in frozen["shared_mechanism_accounting"]["lanes"]
    }
    lanes = []
    for row in graph["shared_mechanism_obligations"]:
        lane_id = row["id"]
        if lane_id in proof_only:
            hole = "?P"
        elif lane_id in open_lane_ids:
            hole = "?M"
        else:
            hole = "CLOSED"

        lane = copy.deepcopy(frozen_lanes.get(lane_id, {}))
        lane.update(
            {
                "id": lane_id,
                "hole_type": hole,
                "state": row["state"],
                "covers_families": row["covers_families"],
                "remaining": row["remaining"],
                "source": "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json",
            }
        )
        for name, value in row.items():
            if str(name).startswith("verified_") and str(name).endswith("_receipt"):
                lane[name] = value
            elif name in {
                "independent_mechanism_residual",
                "proof_only",
                "dependencies",
                "dependency_compression_receipt",
                "composition_dependencies",
            }:
                lane[name] = copy.deepcopy(value)
        lanes.append(lane)

    proofs = []
    for row in graph["open_family_proof_obligations"]:
        deps = ["G_REQUIRED_BEHAVIOR_CONTRACT_COMPLETENESS"]
        deps += [
            lane["id"]
            for lane in lanes
            if row["family"] in lane["covers_families"]
            and lane["hole_type"] != "CLOSED"
        ]
        proofs.append(
            {
                "id": row["id"],
                "family": row["family"],
                "hole_type": "?P",
                "proof_protocol": row["proof_protocol"],
                "bars": row.get("bars"),
                "protocol_path": row.get("protocol_path"),
                "blocked_by": deps,
                "source": "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json",
            }
        )

    tp = proof["snapshot"]["terminal_predicates"]
    gate_spec = [
        ("G_REQUIRED_BEHAVIOR_CONTRACT_COMPLETENESS", "?S", "every_required_behavior_contracted"),
        ("G_ADMISSIBLE_PROOF_COMPLETENESS", "?P", "every_required_behavior_has_admissible_proof"),
        ("G_DONOR_DEPENDENCE_ZERO", "?M", "donor_dependent_required_behaviors_zero"),
        ("G_UNEXPLAINED_BEHAVIOR_ZERO", "?M", "unexplained_required_behaviors_zero"),
        ("G_VERIFIER_MUTATIONS_ZERO", "?P", "unresolved_verifier_mutations_zero"),
        ("G_COMPOSITION_FAILURES_ZERO", "?M", "unresolved_composition_failures_zero"),
        ("G_OPUS_ACCEPTANCE_ALL_PASS", "?P", "all_frozen_opus_acceptance_predicates_pass"),
        ("G_FINAL_DONOR_DELETION_CLEANROOM", "?P", "final_donor_deletion_cleanroom_pass"),
        ("G_PROOF_BUNDLE_FROZEN", "?P", "proof_bundle_frozen"),
    ]
    gates = [
        {
            "id": gate_id,
            "hole_type": hole_type,
            "predicate": predicate,
            "current": bool(tp[predicate]),
            "closed": bool(tp[predicate]),
        }
        for gate_id, hole_type, predicate in gate_spec
    ]

    selected = v6.get("execution_order", {}).get(
        "parallel_independent_cut_members",
        v6.get("selected_observations", []),
    )

    regenerated = copy.deepcopy(frozen)
    regenerated["family_accounting"] = {
        "expected": manifest["expected_family_count"],
        "closed": graph["closed_family_surfaces"],
        "open_proof_count": len(proofs),
        "open_proofs": proofs,
    }
    regenerated["shared_mechanism_accounting"] = {
        "expected_lane_keys": ["M0", "M1", "M2", "M3", "M4", "M5"],
        "lanes": lanes,
    }
    regenerated["global_terminal_gates"] = gates
    regenerated["local_v6_subcut"] = {
        "valid_for_scope": ["M0A", "M1A", "M1B"],
        "exact_minimum": v6["exact_minimum"] is True,
        "selected_observations": selected,
        "globally_authorized": False,
        "disposition": "PRESERVE_AS_VALID_LOCAL_SUBCUT__DO_NOT_SPEND_CLEAN_BATCHES_UNTIL_OUTER_GLOBAL_MINIMUM_REALITY_CUT_PROVES_NONDOMINATION",
    }

    open_spec = [
        x["id"] for x in gates if x["hole_type"] == "?S" and not x["closed"]
    ]
    open_gate_mech = [
        x["id"] for x in gates if x["hole_type"] == "?M" and not x["closed"]
    ]
    open_proof = (
        [x["id"] for x in lanes if x["hole_type"] == "?P"]
        + [x["id"] for x in proofs]
        + [x["id"] for x in gates if x["hole_type"] == "?P" and not x["closed"]]
    )

    cut = copy.deepcopy(frozen["global_cut"])
    cut["exact_cut_ready"] = False
    cut["open_specification_holes"] = open_spec
    cut["open_mechanism_holes"] = (
        list(graph.get("open_mechanism_residuals", []))
        + shared_open
        + open_gate_mech
    )
    cut["open_proof_holes"] = open_proof
    regenerated["global_cut"] = cut

    counts = copy.deepcopy(frozen["counts"])
    counts.update(
        {
            "families_total": manifest["expected_family_count"],
            "families_closed": len(graph["closed_family_surfaces"]),
            "families_open_proof": len(proofs),
            "shared_mechanism_lanes": len(lanes),
            "open_specification_holes": len(open_spec),
            "open_mechanism_lanes": len(graph.get("open_mechanism_residuals", [])),
        }
    )
    if "open_shared_cross_lane_mechanism_primitive_count" in counts:
        counts["open_shared_cross_lane_mechanism_primitive_count"] = len(shared_open)
    regenerated["counts"] = counts

    return regenerated


if __name__ == "__main__":
    print(json.dumps(build_universe(), sort_keys=True, indent=2))
