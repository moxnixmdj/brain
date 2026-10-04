import json
from pathlib import Path
from canonical.runtime.livebench_if_execution_precommit_v2 import verify_precommit

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical/governance/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json"

def manifest():
    return json.loads(MANIFEST.read_text())

def test_repaired_precommit_passes_and_proves_zero_case_resource_fit():
    out=verify_precommit(manifest())
    assert out["precommit_pass"] is True
    assert out["resource_fit_proved"] is True
    assert out["shadow_lease_v2_bound"] is True
    assert out["terminal_cases_consumed"] == 0
    assert out["shadow_collection_authority"] is False
    assert out["acceptance_credit_authorized"] is False

def test_removing_spacy_repair_fails_closed():
    m=manifest()
    m["environment"]["packages"]=[x for x in m["environment"]["packages"] if x[0]!="spacy"]
    assert verify_precommit(m)["precommit_pass"] is False

def test_reverting_shadow_lease_to_v1_fails_closed():
    m=manifest()
    m["harness"]["shadow_lease_runtime_path"]="canonical/runtime/shadow_reality_lease_v1.py"
    assert verify_precommit(m)["precommit_pass"] is False

def test_resource_receipt_drift_fails_closed():
    m=manifest()
    m["resource_fit_verification"]["git_blob_sha"]="0"*40
    assert verify_precommit(m)["precommit_pass"] is False

def test_terminal_case_exposure_fails_closed():
    m=manifest()
    m["case_exposure"]["terminal_cases_consumed"]=1
    assert verify_precommit(m)["precommit_pass"] is False
