import json
from pathlib import Path
from canonical.runtime.livebench_if_execution_precommit_v2 import verify_precommit_v2

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical/governance/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json"

def load():
    return json.loads(MANIFEST.read_text())

def test_exact_successor_precommit_passes_zero_credit():
    o=verify_precommit_v2(load())
    assert o["successor_precommit_pass"] is True
    assert o["resource_fit_truth_repair_bound"] is True
    assert o["shadow_v2_bound"] is True
    assert o["terminal_cases_consumed"] == 0
    assert o["case_reveal_authority"] is False
    assert o["shadow_collection_authority"] is False
    assert o["acceptance_credit_authorized"] is False

def test_spacy_repair_cannot_be_removed():
    x=load()
    x["environment"]["packages"]=[p for p in x["environment"]["packages"] if p[0]!="spacy"]
    assert verify_precommit_v2(x)["successor_precommit_pass"] is False

def test_shadow_v1_cannot_reenter():
    x=load()
    x["harness"]["shadow_lease_runtime_path"]="canonical/runtime/shadow_reality_lease_v1.py"
    assert verify_precommit_v2(x)["successor_precommit_pass"] is False

def test_any_component_mutation_fails_digest():
    for component in ("candidate","harness","scorer","environment","policy"):
        x=load(); x[component]["_mutation"]="x"
        assert verify_precommit_v2(x)["successor_precommit_pass"] is False
