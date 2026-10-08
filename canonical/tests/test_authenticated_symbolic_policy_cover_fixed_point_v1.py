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
