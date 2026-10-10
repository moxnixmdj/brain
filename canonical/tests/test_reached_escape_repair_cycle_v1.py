from __future__ import annotations

from canonical.runtime import reached_escape_repair_cycle_v1 as cycle
from canonical.runtime import reached_escape_state_kernel_v1 as kernel


def state(regions=("r1", "r2"), policies=(), discriminators=()):
    return {
        "schema": kernel.STATE_SCHEMA,
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


def verifier(request):
    required = request["required_verified_property"]
    return {
        "schema": cycle.VERIFY_SCHEMA,
        "pass": True,
        "state_sha256": request["state_sha256"],
        "repair_sha256": request["repair_sha256"],
        "candidate_sha256": request["candidate_sha256"],
        "candidate_kind": request["candidate_kind"],
        "verified_properties": [required],
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }


def test_unsplittable_state_closes_via_verified_discriminator():
    def provider(request):
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
            "truth_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is True, out
    assert out["repair_cycle_closed"] is True
    assert out["repair_rounds_completed"] == 1
    assert out["final_result"]["certified_reached_state_admitted"] is True
    assert out["final_result"]["kernel_result"]["status"] == "STRICT_PROGRESS_WITH_DISCRIMINATOR"
    assert out["global_repair_acquirability_proved"] is False
    assert out["terminal_authority"] is False


def test_uncovered_region_closes_via_verified_policy():
    def provider(request):
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "POLICY",
            "candidate": {
                "policy_id": "p_common",
                "adequate_region_ids": ["r1", "r2"],
            },
            "truth_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }

    out = cycle.run(
        state(policies=[policy("p1", ("r1",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is True, out
    assert out["repair_cycle_closed"] is True
    assert out["repair_rounds_completed"] == 1
    assert out["final_result"]["certified_reached_state_admitted"] is True


def test_provider_cannot_self_certify():
    def provider(request):
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
            "truth_authority": True,
        }

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REPAIR_PROVIDER_AUTHORITY_ESCALATION"


def test_verifier_binding_mismatch_rejected():
    def provider(request):
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        }

    def bad_verifier(request):
        receipt = verifier(request)
        receipt["candidate_sha256"] = "sha256:" + ("0" * 64)
        return receipt

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=bad_verifier,
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__REPAIR_CANDIDATE_NOT_INDEPENDENTLY_VERIFIED"
    assert "CANDIDATE_SHA256" in out["reason"].upper()


def test_nonseparating_discriminator_rejected_before_verifier():
    calls = {"verifier": 0}

    def provider(request):
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "A"},
            },
        }

    def counting_verifier(request):
        calls["verifier"] += 1
        return verifier(request)

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=counting_verifier,
    )
    assert out["pass"] is False
    assert out["reason"] == "DISCRIMINATOR_DOES_NOT_SPLIT_ANY_CONFLICT_CLASS"
    assert calls["verifier"] == 0


def test_partial_policy_repair_can_compound_across_rounds():
    initial = state(
        regions=("r1", "r2", "r3"),
        policies=[policy("p1", ("r1",))],
    )
    issued = []

    def provider(request):
        repair = request["repair_request"]
        uncovered = repair.get("uncovered_region_ids") or []
        if uncovered:
            rid = uncovered[0]
            issued.append(rid)
            return {
                "schema": cycle.CANDIDATE_SCHEMA,
                "pass": True,
                "repair_sha256": request["repair_sha256"],
                "candidate_kind": "POLICY",
                "candidate": {
                    "policy_id": "p_" + rid,
                    "adequate_region_ids": [rid],
                },
            }
        issued.append("split")
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {
                "discriminator_id": "d_all",
                "outcomes": {"r1": "A", "r2": "B", "r3": "C"},
            },
        }

    out = cycle.run(initial, provider=provider, verifier=verifier, max_rounds=4)
    assert out["pass"] is True, out
    assert issued == ["r2", "r3", "split"]
    assert out["repair_rounds_completed"] == 3


def test_round_bound_never_becomes_global_acquirability_claim():
    def provider(request):
        uncovered = request["repair_request"].get("uncovered_region_ids") or []
        rid = uncovered[0]
        return {
            "schema": cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": request["repair_sha256"],
            "candidate_kind": "POLICY",
            "candidate": {
                "policy_id": "p_" + rid,
                "adequate_region_ids": [rid],
            },
        }

    out = cycle.run(
        state(regions=("r1", "r2", "r3"), policies=[]),
        provider=provider,
        verifier=verifier,
        max_rounds=1,
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__REPAIR_ROUND_BOUND_EXHAUSTED"
    assert out["global_repair_acquirability_proved"] is False
    assert out["global_escape_progress_totality_proved"] is False
    assert out["open_ended_mission_terminal_proved"] is False
