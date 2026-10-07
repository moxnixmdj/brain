import json
from pathlib import Path
from canonical.runtime.v13_accepted_five_db_saturation_verifier_v1 import verify

ROOT=Path(__file__).resolve().parents[2]
B=ROOT/"canonical/governance/V13_ACCEPTED_FIVE_DB_SATURATION_20261007_V1.json"

def test_current_five_regions_verify():
    x=verify()
    assert x["pass"] is True,x
    assert x["db_region_count"]==5
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0

def test_scope_overclaim_guards():
    b=json.loads(B.read_text())
    h=set(b["hard_nonclaims"])
    assert "NO_CLAIM_THE_FIVE_REGIONS_COVER_ALL_OPUS55_USEFUL_CONTEXTS" in h
    assert "NO_CLAIM_EXACT_SYMBOLIC_EXTENDS_BEYOND_THE_FROZEN_OPERATION_CLASSES" in h
    assert "NO_CLAIM_CONTINUITY_EXTENDS_TO_GENERAL_SEMANTIC_MEMORY_QUALITY_OR_ARBITRARY_COGNITION" in h

def test_exact_region_cardinality():
    b=json.loads(B.read_text())
    assert len(b["regions"])==5
    assert len({x["id"] for x in b["regions"]})==5
    assert all(x["add_to_D_B"] is True for x in b["regions"])
