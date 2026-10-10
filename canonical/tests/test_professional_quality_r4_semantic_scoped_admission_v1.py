from copy import deepcopy
import json

from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped

KIND = "CONTENT_ADDRESSED_TYPED_MECHANICAL_MEASUREMENT_SEMANTICS"


def _entry():
    registry = json.loads(scoped.REGISTRY.read_text())
    return next(x for x in registry["entries"] if x.get("claim_kind") == KIND)


def test_r4_semantic_entry_is_admitted_with_zero_global_credit():
    out = scoped.validate_entry(_entry())
    assert out["admitted"] is True, out
    assert out["root_id"] == "R4_MEASUREMENT_CONSTRUCT"
    assert out["contributes_to_leaf_ids"] == ["PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC"]
    assert "NO_AUTOMATIC_FIELD_TO_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT" in out["claim_scope"]["limitations"]
    assert out["semantic_leaf_credit"] is False
    assert out["global_leaf_credit"] is False


def test_r4_semantic_global_overclaim_is_rejected():
    entry = deepcopy(_entry())
    entry["global_root_closure"] = True
    out = scoped.validate_entry(entry)
    assert out["admitted"] is False, out
    assert "GLOBAL_ROOT_CLOSURE_FORBIDDEN" in out["errors"]


def test_r4_semantic_stale_scope_is_rejected():
    entry = deepcopy(_entry())
    entry["scope_governance"]["git_blob_sha"] = "0" * 40
    out = scoped.validate_entry(entry)
    assert out["admitted"] is False, out
    assert "SCOPE_STALE" in out["errors"]
