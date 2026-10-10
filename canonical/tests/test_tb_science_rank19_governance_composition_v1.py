import hashlib
import json
from pathlib import Path

from canonical.runtime.tb_science_rank19_capability_first_admission_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
ADMISSION = "canonical/governance/TB_SCIENCE_RANK19_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"
VERIFY = "canonical/verification/TB_SCIENCE_RANK19_CAPABILITY_FIRST_ADMISSION_INDEPENDENT_VERIFICATION_20261010_V2.json"
AUTHORITY = "canonical/governance/TB_SCIENCE_RANK19_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V2.json"
CURRENT = "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_rank19_governance_composition_is_hash_closed_and_still_zero_exposure():
    out = verify()
    assert out["pass"] is True, out

    admission = load(ADMISSION)
    receipt = load(VERIFY)
    authority = load(AUTHORITY)
    current = load(CURRENT)

    cap = authority["capability_first_checkpoint_admission"]
    assert cap["path"] == ADMISSION
    assert cap["git_blob_sha"] == blob(ADMISSION)
    assert cap["verification_path"] == VERIFY
    assert cap["verification_git_blob_sha"] == blob(VERIFY)
    assert cap["authorized"] is True
    assert cap["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"
    assert cap["execution_authority_minted_by_admission"] is False

    assert receipt["result"]["pass"] is True
    assert receipt["result"]["task_read"] is False
    assert receipt["result"]["task_started"] is False
    assert receipt["result"]["benchmark_trials_consumed"] == 0

    staged = current["staged_rank19"]
    assert staged["authority_path"] == AUTHORITY
    assert staged["authority_git_blob_sha"] == blob(AUTHORITY)
    assert staged["execution_authority_effective"] is False

    current_cap = current["capability_first_checkpoint_admission"]
    assert current_cap["path"] == ADMISSION
    assert current_cap["git_blob_sha"] == blob(ADMISSION)
    assert current_cap["verification_path"] == VERIFY
    assert current_cap["verification_git_blob_sha"] == blob(VERIFY)
    assert current_cap["authorized"] is True
    assert current_cap["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"

    assert current["next"] == "BUILD_AND_ZERO_EXPOSURE_VERIFY_PUBLIC_V13_RANK19_EXECUTION_SURFACE_BOUND_TO_CAPABILITY_FIRST_ADMISSION_V2__NO_TASK_READ"
    assert admission["execution_authority"] is False
    assert authority["execution_authority"] is True
    assert authority["execution_authority_effective"] is False
