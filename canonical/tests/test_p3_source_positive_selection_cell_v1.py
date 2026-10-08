import json
import pathlib
import tempfile
from unittest.mock import patch

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.p3_source_positive_selection_cell_v1 import (
    CONTRACT_SCHEMA, RECEIPT_SCHEMA, _digest, evaluate,
)
from canonical.tests.test_p3_policy_influence_relevance_cell_v1 import public_case


def adequacy_payload(public, selected=None):
    selected=selected or ["A","B"]
    return {
        "cell_id":"ctx",
        "selected_policy_id":"P_B",
        "cell_scope_sound":True,
        "brain_owned_policy_proved":True,
        "deployed_route_exactly_realizes_policy":True,
        "authorized_resource_bound_proved":True,
        "source_text":"Apply the bound selection rule.",
        "source_id":"task",
        "claims":[],
        "decision_basis":["x"],
        "policy_conditions":{"P_B":{"op":"TRUE"}},
        "policy_adequacy_bindings":{"P_B":{}},
        "content_bindings":{
            "p3_v3_input_sha256":_digest(public),
            "selected_claim_ids_sha256":_digest(selected),
        },
    }


def bind(root, public, selected=None, adequacy=None, **overrides):
    selected=selected or ["A","B"]
    adequacy=adequacy or adequacy_payload(public,selected)
    receipt={
        "schema":RECEIPT_SCHEMA,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "selected_policy_binding_authenticated":True,
        "deployed_route_exactly_realizes_selected_claim_policy":True,
        "selected_policy_id":"P_B",
        "selected_claim_ids_sha256":_digest(selected),
        "v3_input_sha256":_digest(public),
        "positive_adequacy_payload_sha256":_digest(adequacy),
    }
    receipt.update(overrides)
    p=root/"canonical/verification/p3_source_positive_selection_test_receipt.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(receipt,sort_keys=True,separators=(",",":")).encode()
    p.write_bytes(raw)
    return {
        "schema":CONTRACT_SCHEMA,
        "selected_policy_id":"P_B",
        "selected_claim_ids":selected,
        "positive_adequacy_payload":adequacy,
        "selection_binding_ref":{
            "path":"canonical/verification/p3_source_positive_selection_test_receipt.json",
            "git_blob_sha":git_blob_id(raw,object_format="sha1"),
        },
    }


def positive(policy_id="P_B"):
    return {
        "pass":True,
        "status":"PASS__SOURCE_PROVED_POSITIVE_ADEQUACY_CELL_ADMISSIBLE_TO_D_B",
        "selected_policy_id":policy_id,
        "db_admission_authorized":True,
        "interpretation_set_enumeration_required":False,
        "exact_interpretation_set_completeness_required":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def test_source_positive_selection_closes_without_world_enumeration():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2)
        contract=bind(root,public)
        with patch("canonical.runtime.p3_source_positive_selection_cell_v1.evaluate_positive",return_value=positive()):
            out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is True,out
        assert out["selected_claim_ids"]==["A","B"]
        assert out["selected_policy_adequacy_verified"] is True
        assert out["interpretation_set_enumeration_required"] is False
        assert out["complete_world_partition_required"] is False


def test_selection_binding_drift_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2); contract=bind(root,public)
        contract["selected_claim_ids"]=["A","C"]
        out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"] in {"POSITIVE_ADEQUACY_SELECTION_BINDING_MISMATCH","SELECTION_BINDING_SELECTED_CLAIMS_MISMATCH"}


def test_positive_adequacy_policy_id_must_match_selection():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2)
        adequacy=adequacy_payload(public); adequacy["selected_policy_id"]="P_C"
        contract=bind(root,public,adequacy=adequacy)
        out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="POSITIVE_ADEQUACY_POLICY_ID_MISMATCH"


def test_positive_adequacy_must_bind_exact_v3_and_selection():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2)
        adequacy=adequacy_payload(public)
        adequacy["content_bindings"]["p3_v3_input_sha256"]="sha256:bad"
        contract=bind(root,public,adequacy=adequacy)
        out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="POSITIVE_ADEQUACY_V3_INPUT_BINDING_MISMATCH"


def test_unproved_positive_adequacy_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2); contract=bind(root,public)
        with patch("canonical.runtime.p3_source_positive_selection_cell_v1.evaluate_positive",return_value={"pass":False,"status":"UNRESOLVED__POSITIVE_ADEQUACY_NOT_ENTAILED","db_admission_authorized":False}):
            out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="SOURCE_POSITIVE_ADEQUACY_NOT_CERTIFIED"


def test_selection_cannot_omit_required_claim():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2)
        contract=bind(root,public,selected=["B"])
        out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="SELECTED_POLICY_OMITS_REQUIRED_CLAIM"


def test_selection_cannot_exceed_budget():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2)
        contract=bind(root,public,selected=["A","B","C"])
        out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="SELECTED_POLICY_EXCEEDS_ITEM_BUDGET"


def test_positive_route_keeps_outer_authority_zero():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); public=public_case(2); contract=bind(root,public)
        with patch("canonical.runtime.p3_source_positive_selection_cell_v1.evaluate_positive",return_value=positive()):
            out=evaluate({"v3_input":public,"source_positive_selection_contract":contract},repo_root=root)
        assert out["pass"] is True,out
        for k in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            assert out[k] is False
        assert out["terminal_credit_delta"]==0
