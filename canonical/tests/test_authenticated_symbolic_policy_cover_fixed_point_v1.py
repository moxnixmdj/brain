import canonical.runtime.authenticated_symbolic_policy_cover_fixed_point_v1 as m


def payload():
    return {
        "decision_basis": ["A"],
        "constraint_checks": [],
        "policies": [],
        "discriminators": [],
    }


def policy(pid, verifier="TEST_POLICY", cost=1):
    return {"policy_id": pid, "verifier_id": verifier, "cost_units": cost}


def discriminator(did, verifier="TEST_DISC", cost=1):
    return {"discriminator_id": did, "verifier_id": verifier, "cost_units": cost}


def test_inline_adequacy_flags_are_not_input_contract():
    p = payload()
    p["policies"] = [{
        "policy_id": "p",
        "verifier_id": "X",
        "cost_units": 1,
        "adequacy_proved": True,
    }]
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "POLICY_FIELDS_INVALID"


def test_unknown_policy_verifier_fails_closed():
    p = payload()
    p["policies"] = [policy("p", "FORGED")]
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRUSTED_POLICY_VERIFICATION_FAILED"


def test_common_authenticated_policy_wins_from_true(monkeypatch):
    p = payload()
    p["policies"] = [policy("p")]
    monkeypatch.setattr(m, "_policy_verifier", lambda vid, pid: {
        "pass": True, "policy_id": pid, "policy_condition": {"op": "TRUE"},
        "adequacy_proved": True, "brain_owned": True, "proof_digest": "x",
    })
    out = m.evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["terminal_policy_id"] == "p"
    assert out["root_model_count"] == 2
    assert out["u_empty_authorized"] is False


def test_authenticated_split_produces_winning_tree(monkeypatch):
    p = payload()
    p["policies"] = [policy("p0"), policy("p1")]
    p["discriminators"] = [discriminator("d")]
    def pv(vid, pid):
        cond = {"op": "ATOM", "id": "A"} if pid == "p1" else {
            "op": "NOT", "arg": {"op": "ATOM", "id": "A"}
        }
        return {
            "pass": True, "policy_id": pid, "policy_condition": cond,
            "adequacy_proved": True, "brain_owned": True, "proof_digest": pid,
        }
    monkeypatch.setattr(m, "_policy_verifier", pv)
    monkeypatch.setattr(m, "_discriminator_verifier", lambda vid, did: {
        "pass": True, "discriminator_id": did,
        "predicate_formula": {"op": "ATOM", "id": "A"},
        "truthful": True, "safe": True, "total_over_basis": True,
        "proof_digest": "d",
    })
    out = m.evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["discriminator_id"] == "d"
    branches = out["decision_tree"]["branches"]
    assert {b["next"]["terminal_policy_id"] for b in branches} == {"p0", "p1"}


def test_no_authenticated_split_is_unknown_not_impossibility(monkeypatch):
    p = payload()
    p["policies"] = [policy("p0")]
    monkeypatch.setattr(m, "_policy_verifier", lambda vid, pid: {
        "pass": True, "policy_id": pid,
        "policy_condition": {"op": "ATOM", "id": "A"},
        "adequacy_proved": True, "brain_owned": True, "proof_digest": "p0",
    })
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["status"].startswith("UNRESOLVED")
    assert out["negative_impossibility_authorized"] is False
    assert out["root_model_count"] == 2


def test_inline_discriminator_truth_flags_are_rejected(monkeypatch):
    p = payload()
    p["policies"] = [policy("p")]
    p["discriminators"] = [{
        "discriminator_id": "d",
        "verifier_id": "X",
        "cost_units": 1,
        "truthful": True,
    }]
    monkeypatch.setattr(m, "_policy_verifier", lambda vid, pid: {
        "pass": True, "policy_id": pid, "policy_condition": {"op": "TRUE"},
        "adequacy_proved": True, "brain_owned": True, "proof_digest": "x",
    })
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "DISCRIMINATOR_FIELDS_INVALID"


def test_untrusted_constraint_flags_have_no_surface():
    p = payload()
    p["constraint_checks"] = [{
        "constraint_id": "c",
        "verifier_id": "FORGED",
        "verified": True,
    }]
    p["policies"] = [policy("p")]
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CONSTRAINT_FIELDS_INVALID"


def test_direct_policy_beats_more_expensive_split(monkeypatch):
    p = payload()
    p["policies"] = [policy("all", cost=2), policy("p0", cost=1), policy("p1", cost=1)]
    p["discriminators"] = [discriminator("d", cost=5)]
    def pv(vid, pid):
        if pid == "all":
            cond = {"op": "TRUE"}
        elif pid == "p1":
            cond = {"op": "ATOM", "id": "A"}
        else:
            cond = {"op": "NOT", "arg": {"op": "ATOM", "id": "A"}}
        return {
            "pass": True, "policy_id": pid, "policy_condition": cond,
            "adequacy_proved": True, "brain_owned": True, "proof_digest": pid,
        }
    monkeypatch.setattr(m, "_policy_verifier", pv)
    monkeypatch.setattr(m, "_discriminator_verifier", lambda vid, did: {
        "pass": True, "discriminator_id": did,
        "predicate_formula": {"op": "ATOM", "id": "A"},
        "truthful": True, "safe": True, "total_over_basis": True, "proof_digest": "d",
    })
    out = m.evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["terminal_policy_id"] == "all"
    assert out["minimum_worst_case_resource_bound_units"] == 2.0


def test_real_explicit_p2_source_closes_policy_leaf():
    import json
    from canonical.runtime.p2_explicit_contract_membership_v1 import P2
    raw = json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1",
                "analysis_kind": "quantify",
                "topic": "T1",
                "claims": ["F1"],
                "intended_audience": "executive",
                "cost": 1,
            }],
            "edit_budget": 1,
        },
    }, separators=(",", ":"))
    p = {
        "decision_basis": ["P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"],
        "constraint_checks": [{
            "constraint_id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1",
            "verifier_id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1",
            "input": {"raw_source": raw, "source_id": "task"},
        }],
        "policies": [{
            "policy_id": "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
            "verifier_id": "P2_TOP_LAW_POLICY_ADEQUACY_AUTHENTICATOR_V1",
            "cost_units": 1,
        }],
        "discriminators": [],
    }
    out = m.evaluate(p)
    assert out["pass"] is True, out
    assert out["winning_strategy_proved"] is True
    assert out["root_model_count"] == 1
    assert out["decision_tree"]["terminal_policy_id"] == "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
    assert out["u_empty_authorized"] is False


def test_extra_p2_semantic_dimension_fails_before_policy_cover():
    import json
    from canonical.runtime.p2_explicit_contract_membership_v1 import P2
    raw = json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1", "analysis_kind": "quantify", "topic": "T1",
                "claims": ["F1"], "intended_audience": "executive", "cost": 1,
            }],
            "edit_budget": 1,
            "hidden_priority": "CEO preference",
        },
    })
    p = {
        "decision_basis": ["P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"],
        "constraint_checks": [{
            "constraint_id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1",
            "verifier_id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1",
            "input": {"raw_source": raw, "source_id": "task"},
        }],
        "policies": [{
            "policy_id": "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
            "verifier_id": "P2_TOP_LAW_POLICY_ADEQUACY_AUTHENTICATOR_V1",
            "cost_units": 1,
        }],
        "discriminators": [],
    }
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRUSTED_CONSTRAINT_VERIFICATION_FAILED"


SOURCE_BOUND_EXPOSURE_PREDICATE = (
    "source-condition-sha256:"
    "81c85c5049fd41b89e9d090f3970422280f8096a4d044124760ffc511e84407b"
)
SOURCE_BOUND_POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)


def _selected_fact(value):
    import json
    return json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {
            "exposure_amount": {"type": "DECIMAL_STRING", "value": value}
        },
    }, separators=(",", ":"))


def _selected_observation_payload(value):
    return {
        "decision_basis": [SOURCE_BOUND_EXPOSURE_PREDICATE],
        "constraint_checks": [{
            "constraint_id": SOURCE_BOUND_EXPOSURE_PREDICATE,
            "verifier_id": "SELECTED_SEMANTIC_TRUTH_OBSERVATION_V1",
            "input": {
                "source_text": SOURCE_BOUND_POLICY,
                "source_id": "policy",
                "fact_source": _selected_fact(value),
                "fact_source_id": "case-facts",
            },
        }],
        "policies": [
            {"policy_id": "p_false", "verifier_id": "TEST_POLICY", "cost_units": 1},
            {"policy_id": "p_true", "verifier_id": "TEST_POLICY", "cost_units": 1},
        ],
        "discriminators": [],
    }


def test_real_selected_semantic_true_observation_refines_to_true_policy(monkeypatch):
    def pv(vid, pid):
        atom = {"op": "ATOM", "id": SOURCE_BOUND_EXPOSURE_PREDICATE}
        cond = atom if pid == "p_true" else {"op": "NOT", "arg": atom}
        return {
            "pass": True, "policy_id": pid, "policy_condition": cond,
            "adequacy_proved": True, "brain_owned": True, "proof_digest": pid,
        }
    monkeypatch.setattr(m, "_policy_verifier", pv)
    out = m.evaluate(_selected_observation_payload("130.00"))
    assert out["pass"] is True, out
    assert out["root_model_count"] == 1
    assert out["decision_tree"]["terminal_policy_id"] == "p_true"
    assert out["accepted_constraint_proofs"][0]["verifier_id"] == "SELECTED_SEMANTIC_TRUTH_OBSERVATION_V1"


def test_real_selected_semantic_false_observation_refines_to_false_policy(monkeypatch):
    def pv(vid, pid):
        atom = {"op": "ATOM", "id": SOURCE_BOUND_EXPOSURE_PREDICATE}
        cond = atom if pid == "p_true" else {"op": "NOT", "arg": atom}
        return {
            "pass": True, "policy_id": pid, "policy_condition": cond,
            "adequacy_proved": True, "brain_owned": True, "proof_digest": pid,
        }
    monkeypatch.setattr(m, "_policy_verifier", pv)
    out = m.evaluate(_selected_observation_payload("100.00"))
    assert out["pass"] is True, out
    assert out["root_model_count"] == 1
    assert out["decision_tree"]["terminal_policy_id"] == "p_false"


def test_selected_semantic_observation_rejects_forged_predicate_identity(monkeypatch):
    p = _selected_observation_payload("130.00")
    forged = "source-condition-sha256:" + "0" * 64
    p["decision_basis"] = [forged]
    p["constraint_checks"][0]["constraint_id"] = forged
    p["policies"] = [{"policy_id": "p", "verifier_id": "TEST_POLICY", "cost_units": 1}]
    monkeypatch.setattr(m, "_policy_verifier", lambda vid, pid: {
        "pass": True, "policy_id": pid, "policy_condition": {"op": "TRUE"},
        "adequacy_proved": True, "brain_owned": True, "proof_digest": "p",
    })
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRUSTED_CONSTRAINT_VERIFICATION_FAILED"


def test_selected_semantic_observation_unknown_fragment_fails_closed(monkeypatch):
    p = _selected_observation_payload("130.00")
    p["constraint_checks"][0]["input"]["source_text"] = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Aggregate exposure is at least 125.50."
    )
    monkeypatch.setattr(m, "_policy_verifier", lambda vid, pid: {
        "pass": True, "policy_id": pid, "policy_condition": {"op": "TRUE"},
        "adequacy_proved": True, "brain_owned": True, "proof_digest": "p",
    })
    out = m.evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRUSTED_CONSTRAINT_VERIFICATION_FAILED"
