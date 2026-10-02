import copy
import hashlib
import json
from pathlib import Path

from canonical.runtime.canonical_proof_atom_basis_v1 import atom_id, compile_basis

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


global_frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
sub = load("canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json")

out = compile_basis(global_frontier, sub)
assert out["status"] == "PASS__EXACT_CANONICAL_PROOF_ATOM_BASIS_COMPILED__ZERO_CREDIT", out
assert out["global_unresolved_predicate_count"] == 31
assert out["global_certificate_count"] == 17
assert out["matched_child_target_count"] == 11
assert out["matched_child_certificate_count"] == 11
assert out["leaf_requirement_occurrence_count"] == 40
assert out["leaf_atom_count"] == 40
assert out["exact_duplicate_savings"] == 0

parent_requirements = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
assert set(out["refined_parent_requirements"]) == parent_requirements
assert not parent_requirements.intersection({x["proposition"] for x in out["atoms"]})

for atom in out["atoms"]:
    expected = "PA1:" + hashlib.sha256(atom["proposition"].encode("utf-8")).hexdigest()
    assert atom["atom_id"] == expected
    assert atom["associated_target_count"] == len(atom["associated_target_predicates"])
    assert atom["occurrence_count"] >= 1

# Exact duplicates may deduplicate, but only when the literal is byte-identical.
g2 = copy.deepcopy(global_frontier)
first_non_parent = next(c for c in g2["certificates"] if c["id"] != "MATCHED_SCOPE_BINDING_CERTIFICATE")
literal = first_non_parent["requires"][0]
other = next(
    c for c in g2["certificates"]
    if c["id"] not in ("MATCHED_SCOPE_BINDING_CERTIFICATE", first_non_parent["id"])
)
other["requires"].append(literal)
dedup = compile_basis(g2, sub)
assert dedup["leaf_requirement_occurrence_count"] == 41
assert dedup["leaf_atom_count"] == 40
assert dedup["exact_duplicate_savings"] == 1
row = next(x for x in dedup["atoms"] if x["proposition"] == literal)
assert row["occurrence_count"] == 2

# Similar-looking text is not normalized or merged.
g3 = copy.deepcopy(global_frontier)
other = next(c for c in g3["certificates"] if c["id"] != "MATCHED_SCOPE_BINDING_CERTIFICATE")
base = other["requires"][0]
other["requires"].append(base + " ")
separate = compile_basis(g3, sub)
assert separate["leaf_requirement_occurrence_count"] == 41
assert separate["leaf_atom_count"] == 41
assert atom_id(base) != atom_id(base + " ")

# Child partition must remain lossless and one-to-one.
bad = copy.deepcopy(sub)
bad["certificates"][0]["target_predicates"] = bad["certificates"][1]["target_predicates"]
failed = compile_basis(global_frontier, bad)
assert failed["status"] == "FAIL_CLOSED"

assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert out["new_reality_units_consumed"] == 0

print("test_canonical_proof_atom_basis_v1: PASS")
