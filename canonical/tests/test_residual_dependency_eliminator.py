from canonical.runtime.residual_dependency_eliminator import (
    ResidualClaim,
    eliminate_batch,
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
