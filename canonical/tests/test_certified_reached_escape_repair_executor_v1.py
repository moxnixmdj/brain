from __future__ import annotations

from canonical.runtime import certified_reached_escape_repair_executor_v1 as e
from canonical.runtime import certified_reached_escape_state_constructor_v1 as c
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(policies=(), discriminators=()):
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


def candidate(alternative):
    row = {
        "schema": e.CANDIDATE_SCHEMA,
        "alternative_id": alternative["alternative_id"],
        "proposal": {"opaque": True},
    }
    return row


def provider_for(kind, *, authority_escalation=False):
    def provider(req):
        assert req["candidate_only"] is True
        assert req["provider_truth_authority"] is False
        alt = req["alternative"]
        assert alt["basis"]["provider_kind"] == kind
        cand = candidate(alt)
        return {
            "pass": True,
            "receipt_sha256": "a" * 64,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "truth_authority": authority_escalation,
            "candidate_delta": cand,
            "candidate_delta_sha256": e._sha(cand),
        }
    return provider


def verifier_with_delta(delta):
    def verifier(req):
        return {
            "schema": e.VERIFICATION_SCHEMA,
            "pass": True,
            "receipt_sha256": "b" * 64,
            "candidate_delta_sha256": req["candidate_delta_sha256"],
            "alternative_id": req["alternative"]["alternative_id"],
            "verified_delta": delta,
            "verified_delta_sha256": e._sha(delta),
            "verification_authority_mutated": False,
        }
    return verifier


def test_missing_independent_verifier_blocks_before_provider():
    calls = []
    def provider(req):
        calls.append(req)
        raise AssertionError("provider must not be called")
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider,
        evidence_acquisition_provider=provider,
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__INDEPENDENT_CANDIDATE_VERIFIER_REQUIRED"
    assert calls == []


def test_common_policy_repair_succeeds_only_after_recertification():
    delta = {
        "kind": "ADD_POLICY",
        "row": policy("p_common", ("r1", "r2")),
    }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider_for("CAPABILITY_SYNTHESIS"),
        candidate_verifier=verifier_with_delta(delta),
    )
    assert out["pass"] is True, out
    assert out["repair_verified"] is True
    assert out["selected_provider_kind"] == "CAPABILITY_SYNTHESIS"
    assert out["constructor_result"]["certified_reached_state_admitted"] is True
    assert out["constructor_result"]["kernel_result"]["status"] == "TERMINALIZE_WITH_COMMON_POLICY"
    assert out["global_repair_acquirability_proved"] is False


def test_discriminator_repair_succeeds_only_after_recertification():
    delta = {
        "kind": "ADD_DISCRIMINATOR",
        "row": {
            "discriminator_id": "d",
            "authenticated": True,
            "safe": True,
            "truthful": True,
            "complete": True,
            "outcomes": {"r1": "A", "r2": "B"},
        },
    }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        evidence_acquisition_provider=provider_for("EVIDENCE_ACQUISITION"),
        candidate_verifier=verifier_with_delta(delta),
    )
    assert out["pass"] is True, out
    assert out["repair_verified"] is True
    assert out["selected_provider_kind"] == "EVIDENCE_ACQUISITION"
    assert out["constructor_result"]["kernel_result"]["status"] == "STRICT_PROGRESS_WITH_DISCRIMINATOR"


def test_uncovered_region_policy_repair_succeeds():
    delta = {
        "kind": "ADD_POLICY",
        "row": policy("p2", ("r2",)),
    }
    out = e.execute(
        state(
            policies=[policy("p1", ("r1",))],
            discriminators=[{
                "discriminator_id": "d",
                "authenticated": True,
                "safe": True,
                "truthful": True,
                "complete": True,
                "outcomes": {"r1": 0, "r2": 1},
            }],
        ),
        capability_synthesis_provider=provider_for("CAPABILITY_SYNTHESIS"),
        candidate_verifier=verifier_with_delta(delta),
    )
    assert out["pass"] is True, out
    assert out["constructor_result"]["certified_reached_state_admitted"] is True


def test_provider_authority_escalation_is_rejected():
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider_for(
            "CAPABILITY_SYNTHESIS", authority_escalation=True
        ),
        candidate_verifier=verifier_with_delta({
            "kind": "ADD_POLICY",
            "row": policy("p_common", ("r1", "r2")),
        }),
    )
    assert out["pass"] is False
    assert any("PROVIDER_AUTHORITY_ESCALATION" in x.get("reason", "") for x in out["attempts"])


def test_verifier_candidate_binding_mismatch_is_rejected():
    def bad_verifier(req):
        delta = {"kind": "ADD_POLICY", "row": policy("p_common", ("r1", "r2"))}
        return {
            "schema": e.VERIFICATION_SCHEMA,
            "pass": True,
            "receipt_sha256": "b" * 64,
            "candidate_delta_sha256": "0" * 64,
            "alternative_id": req["alternative"]["alternative_id"],
            "verified_delta": delta,
            "verified_delta_sha256": e._sha(delta),
            "verification_authority_mutated": False,
        }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider_for("CAPABILITY_SYNTHESIS"),
        candidate_verifier=bad_verifier,
    )
    assert out["pass"] is False
    assert any("INDEPENDENT_VERIFICATION_CANDIDATE_MISMATCH" in x.get("reason", "") for x in out["attempts"])


def test_verified_but_insufficient_delta_does_not_count_as_repair():
    delta = {
        "kind": "ADD_POLICY",
        "row": policy("p_extra", ("r1",)),
    }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider_for("CAPABILITY_SYNTHESIS"),
        candidate_verifier=verifier_with_delta(delta),
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION"
    assert any(x.get("recertified") is False for x in out["attempts"])
    assert out["terminal_credit_delta"] == 0


def test_candidate_digest_mismatch_is_rejected():
    def bad_provider(req):
        cand = candidate(req["alternative"])
        return {
            "pass": True,
            "receipt_sha256": "a" * 64,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "candidate_delta": cand,
            "candidate_delta_sha256": "0" * 64,
        }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=bad_provider,
        candidate_verifier=verifier_with_delta({
            "kind": "ADD_POLICY",
            "row": policy("p_common", ("r1", "r2")),
        }),
    )
    assert out["pass"] is False
    assert any("PROVIDER_CANDIDATE_DIGEST_MISMATCH" in x.get("reason", "") for x in out["attempts"])


def test_already_certified_state_skips_all_providers():
    calls = []
    def never(req):
        calls.append(req)
        raise AssertionError
    out = e.execute(
        state(policies=[policy("p", ("r1", "r2"))]),
        capability_synthesis_provider=never,
        evidence_acquisition_provider=never,
        candidate_verifier=never,
    )
    assert out["pass"] is True
    assert out["status"] == "PASS__STATE_ALREADY_CERTIFIED"
    assert out["repair_verified"] is False
    assert calls == []


def test_no_success_path_claims_global_totality_or_terminal_authority():
    delta = {
        "kind": "ADD_POLICY",
        "row": policy("p_common", ("r1", "r2")),
    }
    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        capability_synthesis_provider=provider_for("CAPABILITY_SYNTHESIS"),
        candidate_verifier=verifier_with_delta(delta),
    )
    assert out["pass"] is True
    assert out["global_repair_acquirability_proved"] is False
    assert out["global_escape_progress_totality_proved"] is False
    assert out["promotion_authority"] is False
    assert out["acceptance_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_verified_delta_kind_must_match_selected_alternative():
    def verifier(req):
        delta = {
            "kind": "ADD_POLICY",
            "row": policy("p_common", ("r1", "r2")),
        }
        return {
            "schema": e.VERIFICATION_SCHEMA,
            "pass": True,
            "receipt_sha256": "b" * 64,
            "candidate_delta_sha256": req["candidate_delta_sha256"],
            "alternative_id": req["alternative"]["alternative_id"],
            "verified_delta": delta,
            "verified_delta_sha256": e._sha(delta),
            "verification_authority_mutated": False,
        }

    out = e.execute(
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
        evidence_acquisition_provider=provider_for("EVIDENCE_ACQUISITION"),
        candidate_verifier=verifier,
    )
    assert out["pass"] is False
    assert any(
        "VERIFIED_DELTA_KIND_MISMATCH_WITH_EVIDENCE_ALTERNATIVE"
        in x.get("reason", "")
        for x in out["attempts"]
    )
