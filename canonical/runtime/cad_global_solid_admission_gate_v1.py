from __future__ import annotations

REQUIRED_GLOBAL_CATEGORIES = {
    "GLOBAL_VOLUME",
    "GLOBAL_SURFACE_AREA",
    "PRINCIPAL_INERTIA",
    "CONVEX_HULL_VOLUME_AND_AREA",
    "EULER_NUMBER",
    "GLOBAL_CURVATURE_DISTRIBUTION",
}

class CADAdmissionError(ValueError):
    pass

def _sha256(v, label):
    if not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v.lower()):
        raise CADAdmissionError(label + "_SHA256_INVALID")

def _auth(receipt, label):
    if not isinstance(receipt, dict):
        raise CADAdmissionError(label + "_RECEIPT_MISSING")
    if receipt.get("independent_or_objective") is not True:
        raise CADAdmissionError(label + "_NOT_INDEPENDENT_OR_OBJECTIVE")
    if receipt.get("drawing_bound") is not True:
        raise CADAdmissionError(label + "_DRAWING_NOT_BOUND")
    if receipt.get("candidate_bound") is not True:
        raise CADAdmissionError(label + "_CANDIDATE_NOT_BOUND")
    _sha256(receipt.get("drawing_sha256"), label + "_DRAWING")
    _sha256(receipt.get("candidate_sha256"), label + "_CANDIDATE")

def verify(contract, candidate):
    if not isinstance(contract, dict) or not isinstance(candidate, dict):
        raise CADAdmissionError("OBJECT_REQUIRED")
    if contract.get("scope_complete") is not True:
        raise CADAdmissionError("DRAWING_CONTRACT_NOT_SCOPE_COMPLETE")
    _sha256(contract.get("drawing_sha256"), "DRAWING")
    _sha256(candidate.get("candidate_sha256"), "CANDIDATE")

    required_views = list(map(str, contract.get("required_views") or []))
    if not required_views or len(set(required_views)) != len(required_views):
        raise CADAdmissionError("REQUIRED_VIEW_SET_INVALID")
    view_receipts = candidate.get("view_receipts")
    if not isinstance(view_receipts, dict) or set(view_receipts) != set(required_views):
        raise CADAdmissionError("VIEW_RECEIPT_SET_MISMATCH")
    for view in required_views:
        r = view_receipts[view]
        _auth(r, "VIEW_" + view)
        if r.get("global_envelope_match") is not True:
            raise CADAdmissionError("VIEW_" + view + "_GLOBAL_ENVELOPE_MISMATCH")

    declared = set(map(str, contract.get("global_categories") or []))
    if not REQUIRED_GLOBAL_CATEGORIES <= declared:
        missing = sorted(REQUIRED_GLOBAL_CATEGORIES - declared)
        raise CADAdmissionError("GLOBAL_CATEGORY_CONTRACT_INCOMPLETE:" + ",".join(missing))
    receipts = candidate.get("global_receipts")
    if not isinstance(receipts, dict) or set(receipts) != declared:
        raise CADAdmissionError("GLOBAL_RECEIPT_SET_MISMATCH")
    for category in sorted(declared):
        r = receipts[category]
        _auth(r, "GLOBAL_" + category)
        status = r.get("status")
        if status == "PROVED_MATCH":
            if r.get("match") is not True:
                raise CADAdmissionError("GLOBAL_" + category + "_MATCH_FALSE")
        elif status == "PROVED_DERIVATIVE":
            if r.get("derivation_proved") is not True:
                raise CADAdmissionError("GLOBAL_" + category + "_DERIVATION_UNPROVED")
        else:
            raise CADAdmissionError("GLOBAL_" + category + "_STATUS_INVALID")

    topology = contract.get("topology")
    if not isinstance(topology, dict) or topology.get("scope_complete") is not True:
        raise CADAdmissionError("TOPOLOGY_CONTRACT_INCOMPLETE")
    expected_euler = topology.get("expected_euler")
    if not isinstance(expected_euler, int) or isinstance(expected_euler, bool):
        raise CADAdmissionError("EXPECTED_EULER_MISSING")
    topo = candidate.get("topology_receipt")
    _auth(topo, "TOPOLOGY")
    if topo.get("observed_euler") != expected_euler:
        raise CADAdmissionError("TOPOLOGY_EULER_MISMATCH")

    if candidate.get("watertight") is not True:
        raise CADAdmissionError("NOT_WATERTIGHT")
    if candidate.get("one_connected_solid") is not True:
        raise CADAdmissionError("NOT_ONE_CONNECTED_SOLID")

    return {
        "pass": True,
        "required_view_count": len(required_views),
        "global_category_count": len(declared),
        "expected_euler": expected_euler,
        "terminal_credit_delta": 0,
    }
