from canonical.runtime.residual_dependency_eliminator import (
    ResidualClaim,
    eliminate_batch,
    eliminate_payload,
    eliminate_residual,
)


def ev():
    return {"artifact": "canonical/evidence/example.json"}


def test_owned_route_deleted():
    out = eliminate_residual(
        ResidualClaim("D0-x", "edit", exact_owned_route=True, evidence=ev())
    )
    assert out["status"] == "ELIMINATED"
    assert out["disposition"] == "REUSE_OWNED_EXACT_ROUTE"


def test_jit_deleted():
    out = eliminate_residual(
        ResidualClaim("S0-x", "template", retrievable_source_grounded=True, evidence=ev())
    )
    assert out["disposition"] == "JIT_SOURCE_GROUNDED_KNOWLEDGE"


def test_nonidentifiable_deleted_as_abstention():
    out = eliminate_residual(
        ResidualClaim(
            "S0-y",
            "cause",
            finite_hypothesis_space=True,
            observationally_nonidentifiable=True,
            evidence=ev(),
        )
    )
    assert out["disposition"] == "PRINCIPLED_NONIDENTIFIABILITY_ABSTENTION"


def test_verifier_complete_bypass():
    out = eliminate_residual(
        ResidualClaim(
            "G0-x",
            "candidate",
            verifier_complete_for_scope=True,
            proposal_source_has_zero_authority=True,
            evidence=ev(),
        )
    )
    assert out["disposition"] == "VERIFIER_COMPLETE_PROPOSAL_SUBSTRATE_BYPASS"


def test_unverifiable_ranking_survives():
    out = eliminate_residual(
        ResidualClaim(
            "G0-y",
            "ranking",
            verifier_complete_for_scope=True,
            proposal_source_has_zero_authority=True,
            terminal_success_requires_unverifiable_ranking=True,
            evidence=ev(),
        )
    )
    assert out["status"] == "SURVIVES"
    assert out["implementation_authorized"] is True


def test_bounded_synthesis_deleted():
    out = eliminate_residual(
        ResidualClaim(
            "G0-z",
            "rule",
            bounded_owned_synthesis_applies=True,
            evidence=ev(),
        )
    )
    assert out["disposition"] == "BOUNDED_BRAIN_OWNED_SYNTHESIS"


def test_missing_evidence_fails_closed():
    out = eliminate_residual(ResidualClaim("x", "y"))
    assert out["status"] == "FAIL_CLOSED"


def test_batch_only_survivor_authorized():
    out = eliminate_batch(
        [
            ResidualClaim("a", "owned", exact_owned_route=True, evidence=ev()),
            ResidualClaim("b", "novel", evidence=ev()),
        ]
    )
    assert out["status"] == "PASS"
    assert out["surviving_residual_ids"] == ["b"]
    assert out["implementation_count"] == 1


def test_exact_derivation_deleted():
    out = eliminate_residual(
        ResidualClaim("s0-derive", "derived template", exactly_derivable=True, evidence=ev())
    )
    assert out["disposition"] == "EXACT_DEDUCTIVE_CLOSURE"

def test_dependency_relocation_deleted():
    out = eliminate_residual(
        ResidualClaim(
            "D0-broad",
            "native artifact edit from high-level request",
            mechanical_suffix_owned=True,
            decomposes_to_existing_residuals=True,
            dependency_residual_ids=("S0", "G0"),
            evidence=ev(),
        )
    )
    assert out["status"] == "ELIMINATED"
    assert out["disposition"] == "DEPENDENCY_RELOCATION__OWNED_MECHANICAL_SUFFIX_PLUS_EXISTING_RESIDUALS"
    assert out["dependency_residual_ids"] == ["S0", "G0"]

def test_dependency_relocation_incomplete_fails_closed():
    out = eliminate_residual(
        ResidualClaim("D0-bad","bad relocation",mechanical_suffix_owned=True,evidence=ev())
    )
    assert out["status"] == "FAIL_CLOSED"

def test_dependency_relocation_self_cycle_fails_closed():
    out = eliminate_residual(
        ResidualClaim(
            "D0-self","self cycle",
            mechanical_suffix_owned=True,
            decomposes_to_existing_residuals=True,
            dependency_residual_ids=("D0-self",),
            evidence=ev(),
        )
    )
    assert out["status"] == "FAIL_CLOSED"


def test_proof_only_deferral_deletes_preproof_implementation():
    out = eliminate_residual(
        ResidualClaim(
            "S0-tail",
            "unmeasured semantic tail",
            terminal_failure_required_before_implementation=True,
            repeatable_solvable_terminal_failure_observed=False,
            current_composed_route_exists=True,
            evidence=ev(),
        )
    )
    assert out["status"] == "ELIMINATED"
    assert out["disposition"] == "PROOF_ONLY_DEFERRED__MEASURE_CURRENT_COMPOSED_ROUTE_FIRST"
    assert out["implementation_authorized"] is False


def test_proof_only_deferral_requires_current_route():
    out = eliminate_residual(
        ResidualClaim(
            "S0-bad",
            "unmeasured tail without route",
            terminal_failure_required_before_implementation=True,
            current_composed_route_exists=False,
            evidence=ev(),
        )
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "PROOF_ONLY_DEFERRAL_REQUIRES_CURRENT_COMPOSED_ROUTE"


def test_observed_repeatable_failure_reopens_implementation():
    out = eliminate_residual(
        ResidualClaim(
            "S0-reopened",
            "terminal localized tail",
            terminal_failure_required_before_implementation=True,
            repeatable_solvable_terminal_failure_observed=True,
            current_composed_route_exists=True,
            evidence=ev(),
        )
    )
    assert out["status"] == "SURVIVES"
    assert out["implementation_authorized"] is True


def test_payload_three_proof_only_tails_reduce_to_zero_preproof_survivors():
    payload = {
        "claims": [
            {
                "residual_id": "S0_LONG_RANGE",
                "required_behavior": "long range semantics",
                "terminal_failure_required_before_implementation": True,
                "repeatable_solvable_terminal_failure_observed": False,
                "current_composed_route_exists": True,
                "evidence": {"authority": "canonical/governance/S0_G0_ZERO_REALITY_SATURATION_V1.json"},
            },
            {
                "residual_id": "S0_MULTIMODAL",
                "required_behavior": "raw multimodal binding",
                "terminal_failure_required_before_implementation": True,
                "repeatable_solvable_terminal_failure_observed": False,
                "current_composed_route_exists": True,
                "evidence": {"authority": "canonical/governance/S0_G0_ZERO_REALITY_SATURATION_V1.json"},
            },
            {
                "residual_id": "G0_NOVEL",
                "required_behavior": "novel structure",
                "terminal_failure_required_before_implementation": True,
                "repeatable_solvable_terminal_failure_observed": False,
                "current_composed_route_exists": True,
                "evidence": {"authority": "canonical/governance/G0_DEPENDENCY_COMPRESSION_V1.json"},
            },
        ]
    }
    out = eliminate_payload(payload)
    assert out["status"] == "PASS"
    assert out["implementation_count"] == 0
    assert out["surviving_residual_ids"] == []


def test_payload_unknown_field_fails_closed():
    out = eliminate_payload({"claims": [{
        "residual_id":"x","required_behavior":"y","evidence":ev(),"invented":True
    }]})
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"].startswith("UNKNOWN_CLAIM_FIELDS")
