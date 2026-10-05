#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT = Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
ACC = Path("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
F = Path("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V13.json")

def load(p): return json.loads(p.read_text())
def git_blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

root, acc, f = load(ROOT), load(ACC), load(F)
part = root["current_residual_root_partition"]
cur = root["current_acceptance"]
state = f["exact_state"]

assert (cur["accepted_families"], cur["proved_atomic"], cur["unresolved_atomic"], cur["terminal"]) == (5,14,24,False)
assert (part["root2_only_count"], part["root3_only_count"], part["root2_and_root3_count"], part["unresolved_total"]) == (15,6,3,24)
assert acc["saturation"]["proved_predicate_count"] == 14
assert acc["saturation"]["unresolved_predicate_count"] == 24

expected_r2_only = part["root2_only"]
expected_both = part["root2_and_root3"]
expected_r3_only = part["root3_only"]
expected_r2 = sorted(expected_r2_only + expected_both)
expected_r3 = sorted(expected_r3_only + expected_both)

assert state["accepted_families"] == 5
assert state["open_families"] == 14
assert state["proved_atomic"] == 14
assert state["unresolved_atomic"] == 24
assert state["root2_only_count"] == 15
assert state["root3_only_count"] == 6
assert state["root2_and_root3_count"] == 3
assert state["root2_touching_predicates"] == 18
assert state["root3_touching_predicates"] == 9
assert state["exact_root2_only"] == expected_r2_only
assert state["exact_root3_only"] == expected_r3_only
assert state["exact_root2_and_root3"] == expected_both
assert state["exact_root2_touching"] == expected_r2
assert state["exact_root3_touching"] == expected_r3

assert "LIVEBENCH_IF_GE_65_7" not in expected_r2
assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in expected_r3
assert all(not x.startswith("LIVEBENCH_IF_") for x in f.get("runnable_zero_reality", []))
assert "LIVEBENCH_IF_BRAIN_SCORE" not in f.get("fresh_reality_preserved_not_authorized", [])

sb=f["source_bindings"]
assert sb["terminal_root_state"]["git_blob_sha"] == git_blob_sha(ROOT)
assert sb["combined_root_projection"]["git_blob_sha"] == git_blob_sha(ROOT)
assert sb["acceptance_ledger_current"]["git_blob_sha"] == git_blob_sha(ACC)

assert f["execution_authority"] is False
assert f["promotion_authority"] is False
assert f["fresh_reality_authority"] is False
assert f["independent_verification_required"] is True
assert f["accounting"]["acceptance_credit_delta"] == 0
assert f["accounting"]["family_credit_delta"] == 0
print("ROOT2_V13_EXACT18_REBIND_PASS")
