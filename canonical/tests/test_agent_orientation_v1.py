"""Agent orientation contract: the fixed minimum every agent must know before acting.

These tests prove three things against the live tree (no historical git reads):

1. The root README, the machine-readable contract and the cited laws agree byte-for-byte
   (objective verbatim, every prohibition quote present in its law, every cited law current).
2. The intent check rejects exactly the mistakes made on 2026-10-14 (an objective rewrite,
   a model in the producer path, "not progress" presented as progress, a stale contract,
   a summary treated as authority) and accepts a correct block.
3. Every action intent in the tree that carries an ``agent_orientation`` block is valid
   against the current contract, so the example agents copy from is itself correct.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_guard import agent_orientation_check_v1 as orient  # noqa: E402

CONTRACT = ROOT / orient.CONTRACT_PATH
README = ROOT / orient.README_PATH
OBJECTIVE = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"


def _contract() -> tuple[dict, str]:
    raw = CONTRACT.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _good_block(contract: dict, sha: str) -> dict:
    return {
        "contract": orient.CONTRACT_PATH,
        "contract_sha256": sha,
        "objective_verbatim": OBJECTIVE,
        "progress_class": "INDEPENDENT_FALSIFICATION_OF_A_FALSE_GENERAL_CLAIM",
        "progress_evidence_paths": ["canonical/capabilities/true/TRUE_CAPABILITY_AUDIT_20261014_V1.json"],
        "route_class": "REUSE",
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "conversation_memory_is_authority": False,
        "laws_read_this_session": list(contract["current_laws"]["must_read_before_consequential_action"]),
    }


def _good_intent(contract: dict, sha: str) -> dict:
    return {
        "action_kind": "CAPABILITY_MEASUREMENT",
        "selected_route": "MEASURE_ON_FRESH_INSTANCES_WITH_AN_INDEPENDENT_ORACLE",
        "agent_orientation": _good_block(contract, sha),
    }


# ----------------------------------------------------------------------------- consistency

def test_contract_readme_and_laws_are_consistent():
    errors = orient.verify_errors(ROOT)
    assert errors == [], errors


def test_objective_is_quoted_verbatim_from_the_mission_file():
    contract, _ = _contract()
    mission = json.loads((ROOT / "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json").read_text(encoding="utf-8"))
    assert contract["objective"]["verbatim"] == mission["real_objective"] == OBJECTIVE
    assert contract["objective"]["terminality_verbatim"] == mission["mission_terminality"]
    assert "NO_FINITE_FRONTIER_MODEL_OR_BENCHMARK_DEFINES_FINAL_MISSION_COMPLETION" in mission["mission_terminality"]
    assert mission["opus_5_5_role"] == "FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE"
    readme = README.read_text(encoding="utf-8")
    assert OBJECTIVE in readme
    assert mission["mission_terminality"] in readme


def test_every_prohibition_quote_is_verbatim_in_a_current_law():
    contract, _ = _contract()
    ids = set()
    for row in contract["permanent_prohibitions"]:
        text = (ROOT / row["law"]).read_text(encoding="utf-8")
        assert row["quote"] in text, row["id"]
        current, why = orient.is_current_law(ROOT, row["law"])
        assert current, (row["id"], why)
        ids.add(row["id"])
    required = {
        "NO_MODEL_PRODUCER_COGNITION",
        "HOSTING_DOES_NOT_LAUNDER",
        "ONLY_THE_OWNER_CAN_RESCIND",
        "K3_FORBIDDEN",
        "OBJECTIVE_CANNOT_BE_REPLACED",
        "MEMORY_IS_NOT_AUTHORITY",
        "NEVER_WIDEN_THE_TOLERANCE",
        "TERMINAL_TRUTH_NOT_EDITABLE",
    }
    assert required <= ids, sorted(required - ids)


def test_law_version_table_marks_highest_version_current_and_superseded_files_uncitable():
    table = orient.law_version_table(ROOT)
    lock = table["FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK"]
    assert lock["current"].endswith("_V10.md")
    assert "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md" in lock["history"]
    engine = table["CAPABILITY_ACQUISITION_ENGINE_LAW"]
    assert engine["current"].endswith("_V8.md")
    assert orient.is_current_law(ROOT, "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md")[0] is False
    assert orient.is_current_law(ROOT, "canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md")[0] is False
    assert orient.is_current_law(ROOT, "canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md")[0] is True


def test_superseded_claims_quote_their_superseding_source():
    contract, _ = _contract()
    claims = {row["claim"] for row in contract["no_longer_true_do_not_repeat"]}
    assert any("invention is forbidden" in c for c in claims)
    assert any("unreachable" in c for c in claims)
    engine = (ROOT / "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md").read_text(encoding="utf-8")
    assert "The V7 global underlying-capability invention ban is superseded." in engine


def test_route_order_and_progress_classes_match_the_development_law():
    contract, _ = _contract()
    law = (ROOT / "canonical/laws/GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md").read_text(encoding="utf-8")
    assert contract["route_order"] == [
        "DELETE", "BYPASS", "REUSE", "ADAPT", "SUBSTITUTE", "COMPOSE", "CONFIGURE", "INTEGRATE", "SYNTHESIZE_NEW_PRIMITIVE",
    ]
    assert contract["route_order_quote"] in law
    assert contract["progress"]["not_progress_quote"] in law
    classes = set(contract["progress"]["classes"])
    assert {
        "VERIFIED_REUSABLE_CAPABILITY_GAIN",
        "VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN",
        "VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY",
        "INDEPENDENT_FALSIFICATION_OF_A_FALSE_GENERAL_CLAIM",
        "GOVERNANCE_GUARD_NO_PROGRESS_CLAIM",
    } == classes


def test_canonical_readme_no_longer_points_at_superseded_law():
    text = (ROOT / "canonical/README.md").read_text(encoding="utf-8")
    assert "MISSION_LOCK_V10.md" in text
    assert "MISSION_LOCK_V7.md" not in text
    assert "ARBITRAGE_STRATEGY_V7.md" not in text
    assert "invention is forbidden by the current mission lock" not in text
    assert OBJECTIVE in text
    assert "FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE" in text


# ----------------------------------------------------------------------------- intent check

def test_intent_check_accepts_a_correct_block():
    contract, sha = _contract()
    intent = _good_intent(contract, sha)
    errors = orient.orientation_errors(intent, contract, sha, ["canonical/capabilities/true/TRUE_CAPABILITY_AUDIT_20261014_V1.json"], lambda rel: (ROOT / rel).exists())
    assert errors == [], errors


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda b, i: b.__setitem__("objective_verbatim", "REACH_OPUS_5_5_PARITY_ON_19_FAMILIES"), "ORIENTATION_OBJECTIVE_NOT_VERBATIM"),
        (lambda b, i: b.__setitem__("producer_cognition_model_dependency_count", 1), "ORIENTATION_MODEL_DEPENDENCY_COUNT_NOT_ZERO"),
        (lambda b, i: b.__setitem__("producer_cognition_model_dependency_count", False), "ORIENTATION_MODEL_DEPENDENCY_COUNT_NOT_ZERO"),
        (lambda b, i: b.__setitem__("incremental_spend_usd", 5), "ORIENTATION_INCREMENTAL_SPEND_NOT_ZERO"),
        (lambda b, i: b.__setitem__("progress_class", "MORE_CERTIFICATION_OF_UNCHANGED_BEHAVIOR"), "ORIENTATION_PROGRESS_CLASS_INVALID"),
        (lambda b, i: b.__setitem__("progress_class", "GOVERNANCE_GUARD_NO_PROGRESS_CLAIM"), "ORIENTATION_NO_PROGRESS_CLASS_ONLY_FOR_GOVERNANCE_GUARD"),
        (lambda b, i: b.__setitem__("contract_sha256", "0" * 64), "ORIENTATION_CONTRACT_SHA_MISMATCH"),
        (lambda b, i: b.__setitem__("conversation_memory_is_authority", True), "ORIENTATION_CONVERSATION_MEMORY_MUST_BE_DECLARED_NON_AUTHORITY"),
        (lambda b, i: b.pop("conversation_memory_is_authority"), "ORIENTATION_CONVERSATION_MEMORY_MUST_BE_DECLARED_NON_AUTHORITY"),
        (lambda b, i: b.__setitem__("route_class", "ASK_A_MODEL"), "ORIENTATION_ROUTE_CLASS_INVALID"),
        (lambda b, i: b.__setitem__("route_class", "SYNTHESIZE_NEW_PRIMITIVE"), "ORIENTATION_EARLIER_ROUTES_EXHAUSTED_REASON_REQUIRED"),
        (lambda b, i: b.__setitem__("progress_evidence_paths", []), "ORIENTATION_EVIDENCE_PATHS_MISSING"),
        (lambda b, i: b.__setitem__("progress_evidence_paths", ["canonical/does/not/exist.json"]), "ORIENTATION_EVIDENCE_PATH_NOT_IN_HEAD"),
        (lambda b, i: b.__setitem__("laws_read_this_session", ["AGENTS.md"]), "ORIENTATION_MUST_READ_NOT_ACKNOWLEDGED"),
        (lambda b, i: i.__setitem__("selected_route", "ALLOW_A_MODEL_AS_A_COMPONENT_ON_HARD_CASES"), "ORIENTATION_FORBIDDEN_ROUTE_SELECTED:selected_route"),
        (lambda b, i: i.__setitem__("selected_surviving_route", "REWRITE_THE_TERMINAL_OBJECTIVE_TO_SOMETHING_REACHABLE"), "ORIENTATION_FORBIDDEN_ROUTE_SELECTED:selected_surviving_route"),
    ],
)
def test_intent_check_rejects_each_known_mistake(mutation, expected):
    contract, sha = _contract()
    intent = _good_intent(contract, sha)
    mutation(intent["agent_orientation"], intent)
    errors = orient.orientation_errors(intent, contract, sha, ["canonical/capabilities/true/TRUE_CAPABILITY_AUDIT_20261014_V1.json"], lambda rel: (ROOT / rel).exists())
    assert any(e.startswith(expected) for e in errors), (expected, errors)


def test_intent_check_requires_the_block_and_a_contract():
    contract, sha = _contract()
    assert orient.orientation_errors({"action_kind": "X"}, contract, sha) == ["ORIENTATION_BLOCK_MISSING:agent_orientation"]
    assert orient.orientation_errors(_good_intent(contract, sha), None, None) == ["ORIENTATION_CONTRACT_UNAVAILABLE"]
    assert orient.orientation_errors("not-a-mapping", contract, sha) == ["ORIENTATION_INTENT_INVALID"]


def test_evidence_must_be_changed_by_the_pull_request_when_a_diff_is_known():
    contract, sha = _contract()
    intent = _good_intent(contract, sha)
    errors = orient.orientation_errors(intent, contract, sha, ["README.md"], lambda rel: (ROOT / rel).exists())
    assert "ORIENTATION_EVIDENCE_NOT_CHANGED_BY_THIS_PR" in errors
    errors = orient.orientation_errors(intent, contract, sha, [], lambda rel: (ROOT / rel).exists())
    assert errors == []


def test_governance_guard_may_claim_no_progress():
    contract, sha = _contract()
    intent = _good_intent(contract, sha)
    intent["action_kind"] = "GOVERNANCE_GUARD"
    intent["agent_orientation"]["progress_class"] = "GOVERNANCE_GUARD_NO_PROGRESS_CLAIM"
    errors = orient.orientation_errors(intent, contract, sha, [], lambda rel: (ROOT / rel).exists())
    assert errors == []


def test_every_committed_intent_with_an_orientation_block_is_valid():
    contract, sha = _contract()
    seen = 0
    for path in sorted((ROOT / "canonical/action_intents").glob("*.json")):
        intent = json.loads(path.read_text(encoding="utf-8"))
        if "agent_orientation" not in intent:
            continue
        seen += 1
        errors = orient.orientation_errors(intent, contract, sha, [], lambda rel: (ROOT / rel).exists())
        assert errors == [], (path.name, errors)
    assert seen >= 1


def test_a_changed_contract_invalidates_old_acknowledgements():
    contract, sha = _contract()
    intent = _good_intent(contract, sha)
    changed = copy.deepcopy(contract)
    changed["permanent_prohibitions"].append({"id": "NEW_RULE", "law": "AGENTS.md", "quote": "Nothing merges over a red referee.", "plain": "x"})
    new_sha = hashlib.sha256(json.dumps(changed).encode("utf-8")).hexdigest()
    errors = orient.orientation_errors(intent, changed, new_sha, [], lambda rel: (ROOT / rel).exists())
    assert any(e.startswith("ORIENTATION_CONTRACT_SHA_MISMATCH") for e in errors)


# ----------------------------------------------------------------------------- CLI and gate

def test_cli_verify_and_brief_run_from_a_clean_interpreter():
    proc = subprocess.run([sys.executable, "execution_guard/agent_orientation_check_v1.py", "verify"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["ok"] is True
    proc = subprocess.run([sys.executable, "execution_guard/agent_orientation_check_v1.py", "brief"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert OBJECTIVE in out
    assert "A Brain-credited result MUST NOT depend on another model for producer cognition." in out
    assert "FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md  MUST-READ" in out
    assert "terminal_truth_achieved: false" in out
    assert "verify: CONSISTENT" in out


def test_cli_intent_check_rejects_an_objective_rewrite(tmp_path):
    contract, sha = _contract()
    bad = _good_intent(contract, sha)
    bad["agent_orientation"]["objective_verbatim"] = "REACH_OPUS_5_5_PARITY"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    proc = subprocess.run([sys.executable, "execution_guard/agent_orientation_check_v1.py", "intent-check", str(bad_path)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 1
    assert "ORIENTATION_OBJECTIVE_NOT_VERBATIM" in proc.stdout


def test_load_bearing_gate_wires_the_orientation_check_from_the_base_tree():
    gate = (ROOT / "execution_guard/enforce_load_bearing_primary_pr.py").read_text(encoding="utf-8")
    assert "orientation_errors_for(intent, ns.base, ns.head, files)" in gate
    assert "blob_at(base, CONTRACT_PATH)" in gate
    workflow = (ROOT / ".github/workflows/load-bearing-primary-admission.yml").read_text(encoding="utf-8")
    assert "cp execution_guard/agent_orientation_check_v1.py /tmp/trusted_agent_orientation_check_v1.py" in workflow
