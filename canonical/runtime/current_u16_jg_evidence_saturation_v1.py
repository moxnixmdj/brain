from __future__ import annotations

U16 = (
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "CYBERSECURITY",
    "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
    "HEALTHCARE",
    "MATHEMATICAL_REASONING_ARXIVMATH",
    "MULTILINGUAL_PERFORMANCE",
    "LONG_CONTEXT",
    "CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META",
)


def compile_u16_saturation(doc: dict) -> dict:
    rows = doc.get("items")
    if not isinstance(rows, list):
        raise ValueError("ITEMS_INVALID")
    by_id = {str(r.get("id")): r for r in rows if isinstance(r, dict)}
    if set(by_id) != set(U16) or len(rows) != len(U16):
        raise ValueError("U16_ID_SET_MISMATCH")
    bad = sorted(
        item for item in U16
        if by_id[item].get("scan_state") != "SATURATED_NO_BOUND_CERTIFICATE"
    )
    if bad:
        raise ValueError("UNSATURATED:" + ",".join(bad))
    if not isinstance(doc.get("source_universe"), list) or not doc["source_universe"]:
        raise ValueError("SOURCE_UNIVERSE_EMPTY")
    for src in doc["source_universe"]:
        if not isinstance(src, dict):
            raise ValueError("SOURCE_ROW_INVALID")
        sha = str(src.get("git_blob_sha", ""))
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("SOURCE_SHA_INVALID")
    return {
        "status": "PASS__U16_CURRENT_AUTHORITY_SCAN_SATURATED__ZERO_BOUND_J_G_T_CERTIFICATES",
        "u_item_count": len(U16),
        "bound_j_certificate_count": 0,
        "bound_g_certificate_count": 0,
        "bound_t_certificate_count": 0,
        "future_theorem_impossibility_claimed": False,
        "terminal_credit": False,
    }
