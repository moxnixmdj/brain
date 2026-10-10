import hashlib
import json
from pathlib import Path

from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

ROOT = Path(__file__).resolve().parents[2]
CLAIM = ROOT / "canonical/governance/ESCAPE_PROGRESS_TOTALITY_FROZEN_13_CLAIM_20261010_V1.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
QUOTIENT = ROOT / "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def _sha256_json(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def test_escape_progress_frozen_13_claim_is_exact_and_fail_closed():
    claim = json.loads(CLAIM.read_text(encoding="utf-8"))
    quotient = json.loads(QUOTIENT.read_text(encoding="utf-8"))

    assert _blob_sha(MISSION) == claim["mission_blob_sha"]
    assert _blob_sha(QUOTIENT) == claim["scope"]["quotient_git_blob_sha"]
    assert claim["scope"]["obligation_ids"] == quotient["independent_open_obligations"]
    assert len(claim["scope"]["obligation_ids"]) == 13

    assert _sha256_json(claim["scope"]) == claim["scope_sha256"]
    assert _sha256_json(claim["target_predicate"]) == claim["target_predicate_sha256"]
    assert _sha256_json(claim["semantics"]) == claim["semantics_sha256"]

    result = validate_claim(claim, current_mission_blob_sha=_blob_sha(MISSION))
    assert result["pass"] is True
    assert result["claim_id"] == claim["claim_id"]
    assert result["global_mission_completion_derivable"] is False
    assert result["terminal_credit_delta"] == 0

    assert claim["claim_kind"] == "BOUNDED_SUBGOAL"
    assert "NO_GLOBAL_OPEN_ENDED_MISSION_COMPLETION" in claim["hard_nonclaims"]
    assert claim["terminal_credit_delta"] == 0
