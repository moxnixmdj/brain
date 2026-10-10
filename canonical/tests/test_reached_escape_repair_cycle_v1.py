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


def alternative_id(request, candidate_kind):
    provider_kind = (
        "EVIDENCE_ACQUISITION"
        if candidate_kind == "DISCRIMINATOR"
        else "CAPABILITY_SYNTHESIS"
    )
    matches = [
        row
        for row in request["alternatives"]
        if row["basis"]["provider_kind"] == provider_kind
    ]
    assert len(matches) == 1, matches
    return matches[0]["alternative_id"]


def candidate(request, candidate_kind, payload, **extra):
    return {
        "schema": cycle.CANDIDATE_SCHEMA,
        "pass": True,
        "repair_sha256": request["repair_sha256"],
        "repair_dispatch_sha256": request["repair_dispatch_sha256"],
        "alternative_id": alternative_id(request, candidate_kind),
        "candidate_kind": candidate_kind,
        "candidate": payload,
        **extra,
    }


def verifier(request):
    required = request["required_verified_property"]
    return {
        "schema": cycle.VERIFY_SCHEMA,
        "pass": True,
        "state_sha256": request["state_sha256"],
        "repair_sha256": request["repair_sha256"],
        "repair_dispatch_sha256": request["repair_dispatch_sha256"],
        "alternative_id": request["alternative_id"],
        "candidate_sha256": request["candidate_sha256"],
        "candidate_kind": request["candidate_kind"],
        "verified_properties": [required],
        "independent_verification": True,
        "verifier_id": "TEST_INDEPENDENT_REACHED_ESCAPE_VERIFIER",
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }


def test_unsplittable_state_closes_via_verified_discriminator():
    def provider(request):
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
            truth_authority=False,
            verification_authority=False,
            promotion_authority=False,
            acceptance_authority=False,
            terminal_authority=False,
        )

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
    assert out["repair_trace"][0]["alternative_id"].startswith("escape-repair:")
    assert out["repair_trace"][0]["repair_dispatch_sha256"]
    assert out["global_repair_acquirability_proved"] is False
    assert out["terminal_authority"] is False


def test_uncovered_region_closes_via_verified_policy():
    def provider(request):
        return candidate(
            request,
            "POLICY",
            {
                "policy_id": "p_common",
                "adequate_region_ids": ["r1", "r2"],
            },
            truth_authority=False,
            verification_authority=False,
            promotion_authority=False,
            acceptance_authority=False,
            terminal_authority=False,
        )

    out = cycle.run(
        state(policies=[policy("p1", ("r1",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is True, out
    assert out["repair_cycle_closed"] is True
    assert out["repair_rounds_completed"] == 1
    assert out["final_result"]["certified_reached_state_admitted"] is True


def test_provider_and_verifier_callable_must_be_distinct():
    def both(request):
        if request.get("schema") == cycle.VERIFY_REQUEST_SCHEMA:
            return {
                "schema": cycle.VERIFY_SCHEMA,
                "pass": True,
                "state_sha256": request["state_sha256"],
                "repair_sha256": request["repair_sha256"],
                "repair_dispatch_sha256": request["repair_dispatch_sha256"],
                "alternative_id": request["alternative_id"],
                "candidate_sha256": request["candidate_sha256"],
                "candidate_kind": request["candidate_kind"],
                "verified_properties": [request["required_verified_property"]],
                "independent_verification": True,
                "verifier_id": "FAKE_SELF_VERIFIER",
            }
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        )

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=both,
        verifier=both,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REPAIR_PROVIDER_AND_VERIFIER_NOT_INDEPENDENT"


def test_provider_cannot_self_certify():
    def provider(request):
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
            truth_authority=True,
        )

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REPAIR_PROVIDER_AUTHORITY_ESCALATION"


def test_stale_dispatch_binding_is_rejected():
    def provider(request):
        row = candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        )
        row["repair_dispatch_sha256"] = "0" * 64
        return row

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__REPAIR_CANDIDATE_BINDING_INVALID"


def test_wrong_dispatch_alternative_is_rejected():
    def provider(request):
        row = candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        )
        row["alternative_id"] = "escape-repair:not-the-bound-alternative"
        return row

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REPAIR_ALTERNATIVE_BINDING_INVALID"


def test_verifier_binding_mismatch_rejected():
    def provider(request):
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        )

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
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "A"},
            },
        )

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


def test_policy_then_discriminator_can_compound_across_rounds():
    initial = state(
        regions=("r1", "r2", "r3"),
        policies=[policy("p1", ("r1",))],
    )
    issued = []

    def provider(request):
        repair = request["repair_request"]
        uncovered = list(repair.get("uncovered_region_ids") or [])
        if uncovered:
            issued.append("policy:" + ",".join(uncovered))
            return candidate(
                request,
                "POLICY",
                {
                    "policy_id": "p_uncovered",
                    "adequate_region_ids": uncovered,
                },
            )
        issued.append("split")
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d_all",
                "outcomes": {"r1": "A", "r2": "B", "r3": "C"},
            },
        )

    out = cycle.run(initial, provider=provider, verifier=verifier, max_rounds=4)
    assert out["pass"] is True, out
    assert issued == ["policy:r2,r3", "split"]
    assert out["repair_rounds_completed"] == 2


def test_certification_restored_on_final_allowed_round_is_success():
    def provider(request):
        return candidate(
            request,
            "DISCRIMINATOR",
            {
                "discriminator_id": "d1",
                "outcomes": {"r1": "A", "r2": "B"},
            },
        )

    out = cycle.run(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        provider=provider,
        verifier=verifier,
        max_rounds=1,
    )
    assert out["pass"] is True, out
    assert out["status"] == "PASS__REACHED_ESCAPE_REPAIR_CYCLE_CLOSED"
    assert out["repair_rounds_completed"] == 1


def test_round_bound_never_becomes_global_acquirability_claim():
    def provider(request):
        repair = request["repair_request"]
        uncovered = list(repair.get("uncovered_region_ids") or [])
        assert uncovered
        return candidate(
            request,
            "POLICY",
            {
                "policy_id": "p_uncovered",
                "adequate_region_ids": uncovered,
            },
        )

    out = cycle.run(
        state(
            regions=("r1", "r2", "r3"),
            policies=[policy("p1", ("r1",))],
        ),
        provider=provider,
        verifier=verifier,
        max_rounds=1,
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__REPAIR_ROUND_BOUND_EXHAUSTED"
    assert out["global_repair_acquirability_proved"] is False
    assert out["global_escape_progress_totality_proved"] is False
    assert out["open_ended_mission_terminal_proved"] is False
