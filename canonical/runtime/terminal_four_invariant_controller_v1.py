from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "authority_v3": ("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V3.json", "142cb46ac1bf0b5c570e6d2dc121dfca6f6e1544"),
    "target_cut": ("canonical/governance/TARGET_COMPLETENESS_INFORMATION_CUT_20261007_V1.json", "305b16f88c19ee5046ad0eb7ba0d57da6fab740b"),
    "acceptance_gap": ("canonical/governance/ACCEPTANCE_PROOF_VS_CAPABILITY_GAP_RECONCILIATION_20261007_V1.json", "ae65cb68d78215f81043c080a39dbcf6200697ac"),
    "g_route": ("canonical/governance/G_ROUTE_FIVE_GENERATOR_DOMINANCE_RECONCILIATION_20261007_V1.json", "2bb66217cf42c737282428e053ad42033c30811b"),
    "jit": ("canonical/governance/JIT_KNOWLEDGE_CAPABILITY_NONSMUGGLING_BOUNDARY_20261007_V1.json", "dad1fdb93f102e01b38193da546721ab611bb83f"),
    "pstar": ("canonical/governance/PSTAR_PERSISTENT_RESIDUAL_THEOREM_20261007_V1.json", "7839f6a69898b88b71309d3d04563ce0ee332970"),
}

def git_blob_sha(path: str) -> str:
    b = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def project():
    errors = []
    for name, (path, expected) in SOURCES.items():
        if git_blob_sha(path) != expected:
            errors.append("DRIFT:" + name)

    if errors:
        return {"pass": False, "status": "FAIL_CLOSED_SOURCE_DRIFT", "errors": errors, "terminal": False}

    a3 = load(SOURCES["authority_v3"][0])
    tc = load(SOURCES["target_cut"][0])
    ag = load(SOURCES["acceptance_gap"][0])
    gr = load(SOURCES["g_route"][0])
    jit = load(SOURCES["jit"][0])
    ps = load(SOURCES["pstar"][0])

    if a3["current_truth"]["current_open_truth_obligations"] != 29:
        errors.append("CURRENT_TRUTH_COUNT_DRIFT")
    if a3["current_truth"]["accepted_families"] != 5 or a3["current_truth"]["open_families"] != 14:
        errors.append("FAMILY_COUNT_DRIFT")
    if "U_SUBSET_D" not in tc["theorem"]["necessary_information_form"]:
        errors.append("TARGET_COMPLETENESS_CUT_DRIFT")
    if ag["truth_repair"]["open_family_state"] != "TARGET_RELATIVE_CAPABILITY_PARITY_UNRESOLVED__NOT_PROVED_PASS__NOT_PROVED_FAIL":
        errors.append("UNKNOWN_PARITY_SEMANTICS_DRIFT")
    ids = {x["id"] for x in gr["remaining_g_route_requirements"]}
    required = {
        "G_TARGET_GENERATION_COMPLETENESS",
        "G_DOMINANCE_PRESERVING_TRANSFER",
        "G_RESOURCE_SAFETY_AUTHORITY_TRANSFER",
        "G_L2_DONOR_INDEPENDENT_EFFECT_TOTALITY",
    }
    if not required.issubset(ids):
        errors.append("G_ROUTE_REQUIRED_RESIDUAL_DRIFT")
    normalized = ["_".join(str(x).split()) for x in jit["not_admissible_as_mere_knowledge"]]
    if not any("DYNAMICALLY_SOLVING_THE_TARGET_TASK" in x for x in normalized):
        errors.append("JIT_NONSMUGGLING_DRIFT")
    p_req = " ".join(ps["theorem"]["positive_p_requires"])
    if "A_D_V_U_R" not in p_req or "ROUTE_SET_COMPLETE" not in p_req:
        errors.append("PSTAR_LAST_RESORT_DRIFT")

    invariants = {
        "A_TARGET_COVERAGE": False,
        "B_TARGET_RELATIVE_DISTRIBUTIONAL_DOMINANCE": False,
        "C_COMPOSITION_AND_TRANSFORM_CLOSURE": False,
        "D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE": False,
    }
    terminal = all(invariants.values()) and not errors

    return {
        "pass": not errors,
        "status": "PASS__FOUR_INVARIANT_PROJECTION__TERMINAL_FALSE__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "current_open_truth_obligations": 29 if not errors else None,
        "accepted_families": 5 if not errors else None,
        "open_families": 14 if not errors else None,
        "invariants": invariants,
        "terminal": terminal,
        "new_capability_mechanism_authorized_from_missing_proof": False,
        "broad_benchmark_authorized_without_identified_information_gain": False,
        "persistent_opus_specific_residual_authorized_without_pstar_proof": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = project()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
