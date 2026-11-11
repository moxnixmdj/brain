import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/"canonical/governance/TARGET_TERMINAL_HOMOGENEITY_THEOREM_20261007_V1.json"

def load(): return json.loads(P.read_text())

def test_four_certificate_forms():
    assert len(load()["admissible_certificate_forms"])==4

def test_opposite_worlds_block_certification():
    assert "DIFFERENT_T" in load()["theorem"]["necessity"]

def test_query_requires_partition_reduction():
    assert "REMOVE_AN_OPPOSITE_TERMINAL_WORLD" in load()["query_rule"]

def test_zero_credit():
    assert load()["accounting"]["terminal_credit_delta"]==0
