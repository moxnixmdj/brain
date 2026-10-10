from __future__ import annotations

from copy import deepcopy

from canonical.runtime import certified_reached_escape_repair_dispatch_v1 as d
from canonical.runtime import certified_reached_escape_state_constructor_v1 as c
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(regions=("r1", "r2"), policies=(), discriminators=()):
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": rid} for rid in regions],
        "policies": list(policies),
        "discriminators": list(discriminators),
    }


def policy(pid, covers):
    return {
        "policy_id": pid,
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": list(covers),
    }


def disc(did, outcomes):
    return {
        "discriminator_id": did,
        "authenticated": True,
        "safe": True,
        "truthful": True,
        "complete": True,
        "outcomes": dict(outcomes),
    }


def test_unsplittable_compiles_exact_or_alternatives():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    assert out["pass"] is False
    contract = out["repair_dispatch_contract"]
    assert contract["pass"] is True
    assert contract["alternative_semantics"] == "ANY_ONE_VERIFIED_ALTERNATIVE_MAY_CLOSE_THE_REPAIR"
    assert contract["alternative_count"] == 2
    kinds = {row["basis"]["provider_kind"] for row in contract["alternatives"]}
    classes = {row["basis"]["repair_class"] for row in contract["alternatives"]}
    assert kinds == {"CAPABILITY_SYNTHESIS", "EVIDENCE_ACQUISITION"}
    assert classes == {
        "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION",
        "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
    }
    assert contract["provider_success_is_terminal_success"] is False
    assert contract["constructor_recertification_required"] is True
    assert contract["global_repair_acquirability_proved"] is False


def test_uncovered_region_compiles_policy_only_alternative():
    out = c.construct(
        state(
            policies=[policy("p1", ("r1",))],
            discriminators=[disc("d", {"r1": 0, "r2": 1})],
        )
    )
    contract = out["repair_dispatch_contract"]
    assert contract["alternative_count"] == 1
    alt = contract["alternatives"][0]["basis"]
    assert alt["provider_kind"] == "CAPABILITY_SYNTHESIS"
    assert alt["repair_class"] == "ACQUIRE_OR_SYNTHESIZE_REGION_ADEQUATE_POLICY"
    assert alt["exact_scope"]["uncovered_region_ids"] == ["r2"]


def test_repair_digest_tampering_fails_closed():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    bad = deepcopy(out["repair_request"])
    bad["repair_sha256"] = "sha256:" + "0" * 64
    result = d.run({
        "state_sha256": out["state_sha256"],
        "repair_request": bad,
    })
    assert result["pass"] is False
    assert result["reason"] == "REPAIR_DIGEST_MISMATCH"


def test_state_binding_mismatch_fails_closed():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    result = d.run({
        "state_sha256": "sha256:" + "1" * 64,
        "repair_request": out["repair_request"],
    })
    assert result["pass"] is False
    assert result["reason"] == "REPAIR_STATE_BINDING_MISMATCH"


def test_unsupported_repair_class_fails_closed_even_with_valid_digest():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    bad = deepcopy(out["repair_request"])
    bad["required_postcondition_any"] = [{
        "repair_class": "MAGIC",
        "postcondition": "DO_MAGIC",
    }]
    bad.pop("repair_sha256", None)
    bad["repair_sha256"] = "sha256:" + d._sha(bad)
    result = d.run({
        "state_sha256": out["state_sha256"],
        "repair_request": bad,
    })
    assert result["pass"] is False
    assert result["reason"] == "UNSUPPORTED_REPAIR_CLASS:MAGIC"


def test_every_alternative_forbids_provider_self_authentication():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    for alt in out["repair_dispatch_contract"]["alternatives"]:
        basis = alt["basis"]
        assert basis["candidate_only"] is True
        assert basis["provider_may_not_self_authenticate_candidate"] is True
        assert basis["verification_authority_mutation_allowed"] is False
        req = alt["provider_receipt_requirements"]
        assert req["independent_candidate_verification_required"] is True
        assert req["candidate_delta_sha256_required"] is True
        assert "RECERTIFICATION" in alt["success_condition"]


def test_certified_state_has_no_repair_dispatch_contract():
    out = c.construct(state(policies=[policy("p", ("r1", "r2"))]))
    assert out["pass"] is True
    assert out["certified_reached_state_admitted"] is True
    assert "repair_dispatch_contract" not in out


def test_dispatch_contract_is_deterministic():
    s = state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    a = c.construct(s)
    b = c.construct(deepcopy(s))
    assert a["repair_dispatch_sha256"] == b["repair_dispatch_sha256"]
    assert a["repair_dispatch_contract"] == b["repair_dispatch_contract"]


def test_no_dispatch_path_grants_terminal_or_global_totality_credit():
    out = c.construct(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    )
    contract = out["repair_dispatch_contract"]
    assert contract["global_repair_acquirability_proved"] is False
    assert contract["global_escape_progress_totality_proved"] is False
    assert contract["terminal_authority"] is False
    assert contract["terminal_credit_delta"] == 0
    for alt in contract["alternatives"]:
        assert alt["terminal_credit"] is False
