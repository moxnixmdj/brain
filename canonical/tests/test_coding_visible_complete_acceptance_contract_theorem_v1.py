import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical/runtime/coding_visible_complete_acceptance_contract_v1.py"
RUNTIME_TEST = ROOT / "canonical/tests/test_coding_visible_complete_acceptance_contract_v1.py"
THEOREM = ROOT / "canonical/governance/CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_ADEQUACY_THEOREM_20261009_V1.json"
CERT = ROOT / "canonical/governance/CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"
BEHAVIOR = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"

EXPECTED_ATOMS = [
    "CODING_VISIBLE_ACCEPTANCE_CONTRACT_FINITE_V1",
    "CODING_VISIBLE_ACCEPTANCE_CHECKERS_TOTAL_V1",
    "CODING_VISIBLE_ACCEPTANCE_CONJUNCTION_SOUND_COMPLETE_V1",
    "CODING_VISIBLE_ACCEPTANCE_SOURCE_AUTHORIZED_V1",
    "CODING_VISIBLE_ACCEPTANCE_BUILDER_INDEPENDENT_V1",
    "CODING_VISIBLE_ACCEPTANCE_CHECK_BUDGET_SUFFICIENT_V1",
    "CODING_VISIBLE_ACCEPTANCE_PRETERMINAL_ADMISSIBLE_V1",
]


def blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atom_ids(condition):
    assert condition["op"] == "AND"
    return [row["id"] for row in condition["args"]]


def test_exact_source_blobs_and_condition_match():
    theorem = load(THEOREM)
    cert = load(CERT)
    assert blob(RUNTIME) == "2f5245e36feae21db3d22f299dc66cacf84b8a09"
    assert blob(RUNTIME_TEST) == "e8ec412529838166eb09a886d10e69a60695c517"
    assert blob(THEOREM) == "c52c9b15811c60b80db0a69b2d974657ebec61cd"
    assert blob(BEHAVIOR) == "ae250d5bc5da73b23600670be354ffba31e65e53"
    assert theorem["exact_policy"]["git_blob_sha"] == blob(RUNTIME)
    assert cert["exact_policy"]["git_blob_sha"] == blob(RUNTIME)
    assert cert["exact_sources"]["theorem"]["git_blob_sha"] == blob(THEOREM)
    assert cert["exact_sources"]["runtime_test"]["git_blob_sha"] == blob(RUNTIME_TEST)
    assert cert["exact_sources"]["behavior_registry"]["git_blob_sha"] == blob(BEHAVIOR)
    assert theorem["condition"] == cert["policy_condition"]
    assert atom_ids(theorem["condition"]) == EXPECTED_ATOMS


def test_region_is_strictly_not_finite_candidate_or_transform_taxonomy_bound():
    theorem = load(THEOREM)
    adequacy = theorem["adequacy"]
    assert adequacy["adequate_for_every_member"] is True
    assert adequacy["constructive_liveness"] is True
    assert adequacy["candidate_space_may_be_infinite_or_implicit"] is True
    assert adequacy["candidate_enumeration_required"] is False
    assert adequacy["transform_taxonomy_required"] is False
    assert adequacy["unique_semantic_interpretation_required"] is False
    relation = theorem["relation_to_existing_regions"]
    assert relation["finite_exact_oracle_region"].startswith("INCOMPARABLE__")
    assert relation["typed_acceptance_region"].startswith("INCOMPARABLE__")
    assert relation["robust_finite_multi_interpretation_region"].startswith("INCOMPARABLE__")


def test_membership_and_semantic_premises_never_self_certify():
    theorem = load(THEOREM)
    cert = load(CERT)
    boundary = theorem["boundary"]
    assert boundary["acceptance_contract_completeness_self_certified"] is False
    assert boundary["source_authorization_self_certified"] is False
    assert boundary["condition_truth_requires_separate_source_authority"] is True
    assert boundary["target_membership_self_certified"] is False
    assert boundary["arbitrary_cursorbench_membership_proved"] is False
    assert cert["membership_self_certified"] is False
    assert cert["target_membership_proved"] is False


def test_no_whole_cursorbench_or_terminal_credit():
    theorem = load(THEOREM)
    cert = load(CERT)
    assert theorem["boundary"]["whole_cursorbench_cover_proved"] is False
    assert theorem["boundary"]["whole_specification_residual_closed"] is False
    assert cert["whole_behavior_adequacy"] is False
    assert cert["whole_cursorbench_adequacy"] is False
    assert theorem["promotion_authority"] is False
    assert theorem["terminal_authority"] is False
    assert cert["promotion_authority"] is False
    assert cert["terminal_authority"] is False
    for doc in (theorem, cert):
        assert doc["accounting"]["acceptance_credit_delta"] == 0
        assert doc["accounting"]["terminal_credit_delta"] == 0


def test_cursorbench_private_grader_visibility_is_explicit_nonclaim():
    theorem = load(THEOREM)
    cert = load(CERT)
    assert "NO_CLAIM_CURSORBENCH_EXPOSES_A_COMPLETE_VISIBLE_ACCEPTANCE_CONTRACT" in theorem["hard_nonclaims"]
    assert "NO_CLAIM_PRIVATE_CURSORBENCH_GRADERS_ARE_PRETERMINAL_ADMISSIBLE" in theorem["hard_nonclaims"]
    assert "NO_PRIVATE_CURSORBENCH_CONTEXT_MEMBERSHIP" in cert["hard_nonclaims"]
