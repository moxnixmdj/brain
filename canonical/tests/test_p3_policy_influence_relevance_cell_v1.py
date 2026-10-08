import json
import pathlib
import tempfile

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.p3_policy_influence_relevance_cell_v1 import (
    CONTRACT_SCHEMA,
    RECEIPT_SCHEMA,
    _contract_body,
    _digest,
    evaluate,
)
from canonical.tests.test_p3_membership_frontdoor_v6 import base, req, ev


def opt(cid, text):
    return {"claim_id": cid, "text": text, "required": False}


def public_case(max_items=2):
    public = base(
        [
            req("A", "Revenue growth is 12."),
            opt("B", "Margin rate is 8."),
            opt("C", "Debt ratio is 3."),
        ],
        [
            ev("E1", "Report states Revenue growth is 12."),
            ev("E2", "Report states Margin rate is 8."),
            ev("E3", "Report states Debt ratio is 3."),
        ],
    )
    public["task"]["audience_profile"]["constraints"]["max_items"] = max_items
    return public


def contract_body():
    return {
        "schema": CONTRACT_SCHEMA,
        "environment_id": "p3",
        "goal_id": "capacity_binding_selection",
        "discriminator_ids": ["D", "E"],
        "current_discriminator_values": {"D": "NEED_B", "E": "X1"},
        "worlds": [
            {
                "world_id": "WB0",
                "discriminator_values": {"D": "NEED_B", "E": "X0"},
                "adequate_policy_ids": ["P_B"],
            },
            {
                "world_id": "WB1",
                "discriminator_values": {"D": "NEED_B", "E": "X1"},
                "adequate_policy_ids": ["P_B"],
            },
            {
                "world_id": "WC0",
                "discriminator_values": {"D": "NEED_C", "E": "X0"},
                "adequate_policy_ids": ["P_C"],
            },
            {
                "world_id": "WC1",
                "discriminator_values": {"D": "NEED_C", "E": "X1"},
                "adequate_policy_ids": ["P_C"],
            },
        ],
        "policies": [
            {"policy_id": "P_B", "selected_claim_ids": ["A", "B"]},
            {"policy_id": "P_C", "selected_claim_ids": ["A", "C"]},
        ],
    }


def bind(root, public, body, **overrides):
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "environment_id": body["environment_id"],
        "goal_id": body["goal_id"],
        "contract_body_sha256": _digest(_contract_body(body)),
        "v3_input_sha256": _digest(public),
        "source_compatible_world_overapproximation_sound": True,
        "world_universe_complete_for_declared_scope": True,
        "policy_adequacy_authenticated": True,
        "discriminator_semantics_authenticated": True,
        "current_discriminator_values_authenticated": True,
        "selection_policy_bindings_authenticated": True,
    }
    receipt.update(overrides)
    path = root / "canonical/verification/p3_policy_influence_test_receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    out = dict(body)
    out["verification_ref"] = {
        "path": "canonical/verification/p3_policy_influence_test_receipt.json",
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }
    return out


def make_payload(root, max_items=2):
    public = public_case(max_items=max_items)
    body = contract_body()
    return {
        "context_id": "ctx",
        "v3_input": public,
        "policy_influence_contract": bind(root, public, body),
    }


def test_policy_noninterference_closes_capacity_binding_selection():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        p = make_payload(root)
        out = evaluate(p, repo_root=root)
        assert out["pass"] is True, out
        assert out["selected_policy_id"] == "P_B"
        assert out["selected_claim_ids"] == ["A", "B"]
        assert out["relevance_bits"] == {"D": "RELEVANT", "E": "IRRELEVANT"}
        assert out["policy_influence_noninterference_verified"] is True


def test_residual_world_variation_inside_exact_bucket_is_allowed_when_common_policy_survives():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        body["worlds"].append({
            "world_id": "WB1_ALT",
            "discriminator_values": {"D": "NEED_B", "E": "X1"},
            "adequate_policy_ids": ["P_B"],
        })
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is True, out
        assert out["selected_policy_id"] == "P_B"


def test_full_bucket_without_common_policy_fails_with_constructive_world_set():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        body["worlds"].append({
            "world_id": "WB1_CONFLICT",
            "discriminator_values": {"D": "NEED_B", "E": "X1"},
            "adequate_policy_ids": ["P_C"],
        })
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"] == "DISCRIMINATOR_BUCKET_HAS_NO_COMMON_POLICY"
        assert "WB1" in out["detail"]["world_ids"]
        assert "WB1_CONFLICT" in out["detail"]["world_ids"]


def test_contract_drift_after_verification_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        p = make_payload(root)
        p["policy_influence_contract"]["current_discriminator_values"]["E"] = "X0"
        out = evaluate(p, repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "POLICY_INFLUENCE_CONTRACT_DIGEST_MISMATCH"


def test_unverified_receipt_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        contract = bind(root, public, body, independent_verified=False)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"].endswith("independent_verified")


def test_policy_cannot_omit_required_claim():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        body["policies"][0]["selected_claim_ids"] = ["B"]
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"] == "POLICY_OMITS_REQUIRED_CLAIM"


def test_policy_cannot_exceed_explicit_item_budget():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case(max_items=2)
        body = contract_body()
        body["policies"][0]["selected_claim_ids"] = ["A", "B", "C"]
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"] == "POLICY_EXCEEDS_ITEM_BUDGET"


def test_current_discriminator_bucket_must_be_inside_verified_universe():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        body["current_discriminator_values"] = {"D": "NEED_X", "E": "X1"}
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"] == "CURRENT_DISCRIMINATOR_BUCKET_NOT_IN_VERIFIED_WORLD_UNIVERSE"


def test_claim_order_cannot_be_smuggled_through_policy():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        public = public_case()
        body = contract_body()
        body["policies"][0]["selected_claim_ids"] = ["B", "A"]
        contract = bind(root, public, body)
        out = evaluate(
            {"v3_input": public, "policy_influence_contract": contract},
            repo_root=root,
        )
        assert out["pass"] is False
        assert out["reason"] == "POLICY_SELECTION_ORDER_MUST_PRESERVE_CLAIM_ORDER"


def test_positive_cell_never_mints_outer_authority():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        out = evaluate(make_payload(root), repo_root=root)
        assert out["pass"] is True, out
        for field in (
            "source_authorization_verified",
            "policy_adequacy_authority",
            "db_admission_authority",
            "u_subtraction_authority",
            "terminal_authority",
        ):
            assert out[field] is False
        assert out["terminal_credit_delta"] == 0
