import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/OSWORLD_V21_PINNED_TASK_UNIVERSE_IDENTITY_20261010_V1.json"

def test_osworld_v21_task_identity_closed_without_semantic_overclaim():
    j=json.loads(P.read_text(encoding="utf-8"))
    h=j["public_release_bindings"]["task_hash_manifest"]
    c=j["consequence"]
    b=j["source_access_boundary"]
    assert h["task_count"]==108
    assert h["source_revision"]=="0a1aadad95aa79b00b3783e717d865089ab06e26"
    assert h["sha256"]=="c54d428329be5ca72742a6becd49ee83cf739df5dea429bba182e1f3f21badfb"
    assert c["exact_pinned_108_task_population_identity_closed"] is True
    assert c["exact_task_file_content_hash_universe_closed"] is True
    assert c["exact_task_semantics_closed"] is False
    assert c["exact_task_union_semantic_coverage_matrix_closed"] is False
    assert b["information_theoretic_externality_proved"] is False
    assert "NO_TASK_CLASS_CONTENT_ACCESSED" in j["hard_nonclaims"]
    assert j["accounting"]["acceptance_credit_delta"]==0
    assert j["accounting"]["terminal_credit_delta"]==0
