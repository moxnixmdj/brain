import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSURANCE = ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
FRONTIER = ROOT / "canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_current_mission_binds_exact_current_assurance_bytes():
    assurance = load(ASSURANCE)
    mission = load(MISSION)
    binding = mission["current_assurance_closure_compiler"]
    assert binding["git_blob_sha"] == git_blob_sha(ASSURANCE)
    assert assurance["terminal_authority"] is False
    assert assurance["activation"]["live_default"] is False

def test_terminal_binds_exact_current_mission_bytes_in_all_live_chain_fields():
    terminal = load(TERMINAL)
    mission_sha = git_blob_sha(MISSION)
    assert terminal["authoritative_sources"]["current_mission_objective"]["git_blob_sha"] == mission_sha
    chain = terminal["pointer_chain_reconciliation_20261009"]
    assert chain["current_mission_git_blob_sha"] == mission_sha
    assert chain["current_assurance_git_blob_sha"] == git_blob_sha(ASSURANCE)

def test_active_planning_overlay_binds_exact_current_primitive_u_frontier():
    terminal = load(TERMINAL)
    binding = terminal["authoritative_sources"]["universal_escape_resolver_v2_active_planning_overlay"]["primitive_u_frontier"]
    assert binding["git_blob_sha"] == git_blob_sha(FRONTIER)
    frontier = load(FRONTIER)
    assert frontier["schema"] == "PROJECT_BRAIN_CURRENT_PRIMITIVE_U_FRONTIER_V3"
    assert frontier["current_truth"]["terminal"] is False

def test_chain_repair_preserves_objective_and_zero_credit():
    assurance = load(ASSURANCE)
    mission = load(MISSION)
    terminal = load(TERMINAL)
    rec = terminal["current_authority_chain_provenance_reconciliation_20261009_v1"]
    assert mission["real_objective"] == terminal["terminal_objective"]
    assert assurance["terminal_credit_delta"] == 0
    assert terminal["accounting"]["terminal_credit_delta"] == 0
    assert rec["semantic_credit_delta"] == 0
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
    assert "TERMINAL_FALSE" in terminal["terminal_semantics_override"]["current_truth"]
