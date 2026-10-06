import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"canonical/governance/PSTAR_INSTRUCTION_FOLLOWING_SCOPE_FIRST_APPLICATION_20261007_V1.json"
def load(): return json.loads(P.read_text())
def test_family(): assert load()["family"]=="INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT"
def test_positive_p_not_forced(): assert load()["pstar_routes"]["P"]=="NOT_FORCED"
def test_real_owned_r_evidence_present(): assert len(load()["owned_r_evidence"])==3
def test_all_nonpersistent_classes_must_be_attacked():
    s=" ".join(load()["decisive_positive_p_falsifier_needed"]["must_prove"])
    for x in ["NO_SOUND_A_ROUTE","NO_ADMISSIBLE_JIT","NO_BRAIN_OWNED_PROBE","ABSTENTION","GENERAL_BRAIN_OWNED_R_ROUTE"]:
        assert x in s
def test_zero_credit(): assert load()["accounting"]["terminal_credit_delta"]==0
