from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def build_universe():
    graph = _load("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json")
    proof = _load("canonical/governance/GLOBAL_TERMINAL_PROOF_CUT_V1.json")
    manifest = _load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
    v6 = _load("canonical/governance/RESIDUAL_MINIMUM_REALITY_CUT_VERDICT_V6.json")
    registry = _load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")

    def lane_key(x):
        return str(x).split("_", 1)[0]

    lanes = []
    for row in graph["shared_mechanism_obligations"]:
        key = lane_key(row["id"])
        if key in {"M0", "M1"} or str(row.get("state", "")).startswith("OPEN_PROOF_ONLY"):\n            hole = "?P"\n        elif row.get("state") == "OPEN":\n            hole = "?M"\n        else:\n            hole = "CLOSED"
        lane = {
            "id": row["id"],
            "hole_type": hole,
            "state": row["state"],
            "covers_families": row["covers_families"],
            "remaining": row["remaining"],
            "source": "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json",
        }
        # Receipt bindings are canonical evidence metadata, not scheduling logic.
        # Preserve them in the generated projection so regeneration cannot erase
        # verified mechanism provenance that was bound into the obligation graph.
        for name, value in row.items():
            if str(name).startswith("verified_") and str(name).endswith("_receipt"):
                lane[name] = value
        lanes.append(lane)

    proofs = []
    for row in graph["open_family_proof_obligations"]:
        deps = ["G_REQUIRED_BEHAVIOR_CONTRACT_COMPLETENESS"]
        deps += [x["id"] for x in lanes if row["family"] in x["covers_families"] and x["hole_type"] != "CLOSED"]
        proofs.append({
            "id": row["id"],
            "family": row["family"],
            "hole_type": "?P",
            "proof_protocol": row["proof_protocol"],
            "bars": row.get("bars"),
            "protocol_path": row.get("protocol_path"),
            "blocked_by": deps,
            "source": "canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json",
        })

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
    gates = [{"id":i,"hole_type":h,"predicate":p,"current":bool(tp[p]),"closed":bool(tp[p])} for i,h,p in gate_spec]
    spec_open = any(x["hole_type"] == "?S" and not x["closed"] for x in gates)
    mech_open = any(x["hole_type"] == "?M" for x in lanes) or any(x["hole_type"] == "?M" and not x["closed"] for x in gates)
    selected = v6.get("execution_order", {}).get("parallel_independent_cut_members", v6.get("selected_observations", []))

    # Blob SHAs are frozen in the snapshot and intentionally not regenerated here.
    frozen = _load("canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json")
    regenerated = dict(frozen)
    regenerated["family_accounting"] = {
        "expected": manifest["expected_family_count"],
        "closed": graph["closed_family_surfaces"],
        "open_proof_count": len(proofs),
        "open_proofs": proofs,
    }
    regenerated["shared_mechanism_accounting"] = {
        "expected_lane_keys": ["M0","M1","M2","M3","M4","M5"],
        "lanes": lanes,
    }
    regenerated["global_terminal_gates"] = gates
    regenerated["local_v6_subcut"] = {
        "valid_for_scope": ["M0A","M1A","M1B"],
        "exact_minimum": v6["exact_minimum"] is True,
        "selected_observations": selected,
        "globally_authorized": False,
        "disposition": "PRESERVE_AS_VALID_LOCAL_SUBCUT__DO_NOT_SPEND_CLEAN_BATCHES_UNTIL_OUTER_GLOBAL_MINIMUM_REALITY_CUT_PROVES_NONDOMINATION",
    }
    regenerated["global_cut"] = {
        "exact_cut_ready": (not spec_open and not mech_open),
        "reason": (None if (not spec_open and not mech_open) else ("OPEN_SPECIFICATION_AND_MECHANISM_HOLES_EXIST_OUTSIDE_LOCAL_V6_SCOPE" if spec_open and mech_open else ("OPEN_SPECIFICATION_HOLES_EXIST_OUTSIDE_LOCAL_V6_SCOPE" if spec_open else "OPEN_MECHANISM_HOLES_EXIST_OUTSIDE_LOCAL_V6_SCOPE"))),
        "open_specification_holes": [x["id"] for x in gates if x["hole_type"] == "?S" and not x["closed"]],
        "open_mechanism_holes": [x["id"] for x in lanes if x["hole_type"] == "?M"] + [x["id"] for x in gates if x["hole_type"] == "?M" and not x["closed"]],
        "open_proof_holes": [x["id"] for x in lanes if x["hole_type"] == "?P"] + [x["id"] for x in proofs] + [x["id"] for x in gates if x["hole_type"] == "?P" and not x["closed"]],
    }
    regenerated["counts"] = {
        "families_total": manifest["expected_family_count"],
        "families_closed": len(graph["closed_family_surfaces"]),
        "families_open_proof": len(proofs),
        "shared_mechanism_lanes": len(lanes),
        "open_specification_holes": sum(1 for x in gates if x["hole_type"] == "?S" and not x["closed"]),
        "open_mechanism_lanes": sum(1 for x in lanes if x["hole_type"] == "?M"),
    }
    return regenerated

if __name__ == "__main__":
    print(json.dumps(build_universe(), sort_keys=True, indent=2))
