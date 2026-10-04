import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = "canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V5.json"
LEDGER = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _blob_sha(rel):
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def test_v5_is_bound_to_current_13_25_acceptance_ledger():
    p = _load(POLICY)
    ledger = _load(LEDGER)
    assert ledger["saturation"]["proved_predicate_count"] == 13
    assert ledger["saturation"]["unresolved_predicate_count"] == 25
    assert p["exact_live_state"]["proved_atomic"] == 13
    assert p["exact_live_state"]["unresolved_atomic"] == 25
    assert p["acceptance_binding"]["git_blob_sha"] == _blob_sha(LEDGER)


def test_preempirical_macro_actions_cover_every_residual_exactly_once():
    p = _load(POLICY)
    residual = set(p["residual_predicates"])
    assert len(residual) == 25

    pre = [
        set(x["target_predicates"])
        for x in p["macro_actions"][:3]
    ]
    assert not (pre[0] & pre[1])
    assert not (pre[0] & pre[2])
    assert not (pre[1] & pre[2])
    assert set().union(*pre) == residual

    partition = p["pre_empirical_partition"]
    assert partition["union_count"] == 25
    assert partition["pairwise_disjoint"] is True


def test_closed_unknown_domain_atom_is_deleted_from_active_work():
    p = _load(POLICY)
    assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in p["residual_predicates"]
    assert all(
        "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
        not in (x["target_predicates"] if isinstance(x["target_predicates"], list) else [])
        for x in p["macro_actions"]
    )
    assert "NO_REOPEN_UNKNOWN_DOMAIN_DIRECT_AUDIT_UNLESS_ITS_V6_PROOF_BINDING_IS_INVALIDATED" in p["hard_rules"]


def test_fresh_reality_stays_blocked_until_fixed_point():
    p = _load(POLICY)
    d = p["macro_actions"][3]
    assert d["id"] == "D__ONE_FINAL_EMPIRICAL_SUPERWAVE"
    assert "FIXED_POINT" in d["concurrency"]
    assert p["fresh_reality_authority"] is False
    assert p["execution_authority"] is False
    assert p["promotion_authority"] is False


def test_prepromotion_falsification_gate_is_mandatory_but_zero_credit():
    p = _load(POLICY)
    gate = p["global_controls"]["prepromotion_falsification_gate"]
    assert gate["required_before"].startswith("ANY_CANONICAL_ACCEPTANCE_LEDGER_MUTATION")
    assert gate["grants_credit"] is False
    assert any("PREPROMOTION_FALSIFICATION_GATE" in x for x in p["hard_rules"])


def test_tb4_eight_task_recovery_is_only_attainability_not_pass_claim():
    p = _load(POLICY)
    b = p["macro_actions"][1]
    t = b["tb4_math"]
    assert t["current_upper_successes"] == 180
    assert t["required_successes"] == 220
    assert t["minimum_recovered_tasks_for_attainability"] == 8
    assert 5 * (36 + 8) == 220
    assert "NOT_A_HIGH_PROBABILITY_PASS_PLAN" in t["hard_rule"]
