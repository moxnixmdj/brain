from canonical.runtime import certified_reached_escape_state_constructor_v2 as c
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(*, policies=(), discriminators=()):
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": "r1"}, {"region_id": "r2"}],
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


def receipt(claim, kind, verified, authority_id="TEST_AUTHORITY"):
    core = {
        "schema": c.RECEIPT_SCHEMA,
        "pass": True,
        "claim_sha256": c._digest(claim),
        "candidate_state_sha256": claim["candidate_state_sha256"],
        "authority_kind": kind,
        "authority_id": authority_id,
        "verification_authority_mutated": False,
        "verified": verified,
    }
    return {**core, "receipt_sha256": c._digest(core)}


def policy_verifier(claim):
    return receipt(
        claim,
        "POLICY_ADEQUACY_SAFETY_AND_RESOURCE",
        {
            "safe": True,
            "adequate_region_ids": list(claim["adequate_region_ids"]),
            "resource_bound": {"amount": 3, "unit": "WORK_UNIT"},
        },
    )


def discriminator_verifier(claim):
    return receipt(
        claim,
        "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE",
        {
            "safe": True,
            "truthful": True,
            "complete": True,
            "outcomes": dict(claim["outcomes"]),
            "resource_bound": {"amount": 2, "unit": "WORK_UNIT"},
        },
    )


def test_caller_true_flags_do_not_create_policy_authority():
    out = c.construct(state(policies=[policy("fake", ("r1", "r2"))]))
    assert out["pass"] is False, out
    assert out["status"] == "FAIL_CLOSED__REACHED_ESCAPE_TRUTH_AUTHORITY"
    assert "POLICY_ADEQUACY_SAFETY_AND_RESOURCE_VERIFIER_REQUIRED" in out["reason"]
    assert out["certified_reached_state_admitted"] is False
    assert out["candidate_authority_flags_ignored"] is True
    assert out["verified_state"] is None
    assert out["verified_state_sha256"] is None


def test_verified_policy_receipt_allows_existing_finite_certificate_path():
    out = c.construct(
        state(policies=[policy("p", ("r1", "r2"))]),
        policy_authority_verifier=policy_verifier,
    )
    assert out["pass"] is True, out
    assert out["truth_authority_bound"] is True
    assert out["certified_reached_state_admitted"] is True
    assert out["verified_state"]["policies"] == [{
        "policy_id": "p",
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": ["r1", "r2"],
    }]
    assert out["verified_state"]["discriminators"] == []
    assert out["verified_state_sha256"] == c._digest(out["verified_state"])
    assert out["kernel_result"]["status"] == "TERMINALIZE_WITH_COMMON_POLICY"
    assert out["resource_admissibility_proved"] is True
    assert out["resource_unit"] == "WORK_UNIT"
    assert out["terminal_authority"] is False


def test_spoofed_discriminator_flags_do_not_create_truth_authority():
    out = c.construct(
        state(
            policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
            discriminators=[disc("fake-d", {"r1": "A", "r2": "B"})],
        ),
        policy_authority_verifier=policy_verifier,
    )
    assert out["pass"] is False, out
    assert "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE_VERIFIER_REQUIRED" in out["reason"]


def test_verified_policy_and_discriminator_receipts_allow_strict_progress():
    out = c.construct(
        state(
            policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
            discriminators=[disc("d", {"r1": "A", "r2": "B"})],
        ),
        policy_authority_verifier=policy_verifier,
        discriminator_authority_verifier=discriminator_verifier,
    )
    assert out["pass"] is True, out
    assert out["truth_authority_bound"] is True
    assert out["kernel_result"]["status"] == "STRICT_PROGRESS_WITH_DISCRIMINATOR"
    assert out["kernel_result"]["all_nonempty_branches_strict_subsets"] is True


def test_wrong_claim_binding_is_rejected():
    def bad_verifier(claim):
        r = policy_verifier(claim)
        r["claim_sha256"] = "sha256:" + "0" * 64
        core = dict(r)
        core.pop("receipt_sha256")
        r["receipt_sha256"] = c._digest(core)
        return r

    out = c.construct(
        state(policies=[policy("p", ("r1", "r2"))]),
        policy_authority_verifier=bad_verifier,
    )
    assert out["pass"] is False
    assert "CLAIM_BINDING_MISMATCH" in out["reason"]


def test_authority_mutation_is_rejected():
    def mutating_verifier(claim):
        r = policy_verifier(claim)
        r["verification_authority_mutated"] = True
        core = dict(r)
        core.pop("receipt_sha256")
        r["receipt_sha256"] = c._digest(core)
        return r

    out = c.construct(
        state(policies=[policy("p", ("r1", "r2"))]),
        policy_authority_verifier=mutating_verifier,
    )
    assert out["pass"] is False
    assert "AUTHORITY_MUTATION_FORBIDDEN" in out["reason"]


def test_receipt_from_different_candidate_state_is_rejected():
    def wrong_state_verifier(claim):
        r = policy_verifier(claim)
        r["candidate_state_sha256"] = "sha256:" + "1" * 64
        core = dict(r)
        core.pop("receipt_sha256")
        r["receipt_sha256"] = c._digest(core)
        return r

    out = c.construct(
        state(policies=[policy("p", ("r1", "r2"))]),
        policy_authority_verifier=wrong_state_verifier,
    )
    assert out["pass"] is False
    assert "STATE_BINDING_MISMATCH" in out["reason"]


def test_missing_resource_bound_is_rejected():
    def no_resource_verifier(claim):
        return receipt(
            claim,
            "POLICY_ADEQUACY_SAFETY_AND_RESOURCE",
            {
                "safe": True,
                "adequate_region_ids": list(claim["adequate_region_ids"]),
            },
        )

    out = c.construct(
        state(policies=[policy("p", ("r1", "r2"))]),
        policy_authority_verifier=no_resource_verifier,
    )
    assert out["pass"] is False
    assert "RESOURCE_BOUND_REQUIRED" in out["reason"]


def test_incompatible_resource_units_fail_closed():
    def discriminator_other_unit(claim):
        return receipt(
            claim,
            "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE",
            {
                "safe": True,
                "truthful": True,
                "complete": True,
                "outcomes": dict(claim["outcomes"]),
                "resource_bound": {"amount": 1, "unit": "OTHER_UNIT"},
            },
        )

    out = c.construct(
        state(
            policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
            discriminators=[disc("d", {"r1": "A", "r2": "B"})],
        ),
        policy_authority_verifier=policy_verifier,
        discriminator_authority_verifier=discriminator_other_unit,
    )
    assert out["pass"] is False
    assert "RESOURCE_UNITS_NOT_COMPARABLE" in out["reason"]


def test_empty_policy_frontier_needs_no_fake_authority_and_remains_repair_required():
    out = c.construct(state())
    assert out["pass"] is False, out
    assert out["truth_authority_bound"] is True
    assert out["resource_admissibility_proved"] is False
    assert out["status"] == "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED"
    assert out["certificate_status"] == "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY"
    assert out["terminal_credit_delta"] == 0
