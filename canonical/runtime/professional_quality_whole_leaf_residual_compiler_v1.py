"""Fail-closed whole-leaf residual compiler for professional quality."""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_COMPILER_V1"

class WholeLeafResidualError(ValueError):
    pass

def _s(v: Any) -> str:
    return " ".join(str(v or "").split())

def compile_whole_leaf_residuals(entries: Sequence[Mapping[str, Any]], expected_leaf_ids: Sequence[str]) -> dict[str, Any]:
    expected = sorted({_s(x) for x in expected_leaf_ids if _s(x)})
    if not expected or len(expected) != len(list(expected_leaf_ids)):
        raise WholeLeafResidualError("EXPECTED_LEAF_IDS_INVALID")
    by_leaf: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for raw in entries:
        if not isinstance(raw, Mapping) or not _s(raw.get("scope_id")):
            raise WholeLeafResidualError("ENTRY_INVALID")
        leaves = raw.get("contributes_to_leaf_ids")
        receipt = raw.get("source_receipt")
        if not isinstance(leaves, list) or not leaves or not isinstance(receipt, Mapping):
            raise WholeLeafResidualError("ENTRY_EVIDENCE_INVALID")
        if not _s(receipt.get("path")) or not _s(receipt.get("git_blob_sha")):
            raise WholeLeafResidualError("ENTRY_RECEIPT_BINDING_REQUIRED")
        for leaf in leaves:
            leaf_id = _s(leaf)
            if not leaf_id:
                raise WholeLeafResidualError("LEAF_ID_EMPTY")
            by_leaf[leaf_id].append(raw)
    observed = sorted(by_leaf)
    if observed != expected:
        raise WholeLeafResidualError("LEAF_UNIVERSE_MISMATCH")
    rows=[]
    closed=0
    for leaf_id in expected:
        ws=by_leaf[leaf_id]
        totality=any(isinstance(w.get("whole_leaf_totality_certificate"), Mapping) and w["whole_leaf_totality_certificate"].get("independently_verified") is True and _s(w["whole_leaf_totality_certificate"].get("leaf_id"))==leaf_id for w in ws)
        union=any(isinstance(w.get("certified_complete_union"), Mapping) and w["certified_complete_union"].get("independently_verified") is True and w["certified_complete_union"].get("covers_all_admissible_inputs") is True and _s(w["certified_complete_union"].get("leaf_id"))==leaf_id for w in ws)
        is_closed=totality or union
        if any(w.get("global_leaf_closure") is True for w in ws) and not is_closed:
            raise WholeLeafResidualError("UNSUPPORTED_GLOBAL_LEAF_CLOSURE_CLAIM:"+leaf_id)
        closed += int(is_closed)
        rows.append({"leaf_id":leaf_id,"bounded_witness_scope_count":len(ws),"whole_leaf_closed":is_closed,"residual":None if is_closed else "TOTALITY_OR_CERTIFIED_COMPLETE_UNION_REQUIRED"})
    return {"schema":SCHEMA,"status":"ALL_WHOLE_LEAVES_CLOSED" if closed==len(expected) else "OPEN__WHOLE_LEAF_TOTALITY_OR_COMPLETE_UNION_REQUIRED","expected_leaf_count":len(expected),"closed_leaf_count":closed,"open_leaf_count":len(expected)-closed,"leaves":rows,"quantifier_rule":"BOUNDED_SCOPE_WITNESSES_DO_NOT_ENTAIL_WHOLE_LEAF_INPUT_DOMAIN_TOTALITY","promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
