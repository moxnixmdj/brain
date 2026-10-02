import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_proof_atom_basis_v1 import compile_basis

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

class TerminalProofAtomBasisV1Tests(unittest.TestCase):
    def setUp(self):
        self.frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        self.sub = load("canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json")
        self.activation = load("canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json")

    def test_live_basis_is_exact_and_zero_credit(self):
        out = compile_basis(self.frontier, self.sub, self.activation)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["unresolved_predicate_count"], 31)
        self.assertEqual(out["effective_certificate_count"], 27)
        self.assertEqual(out["covered_predicate_count"], 31)
        self.assertEqual(out["uncovered_predicates"], [])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_parent_requirements_are_replaced_by_children(self):
        out = compile_basis(self.frontier, self.sub, self.activation)
        reqs = {x["requirement"] for x in out["proof_atoms"]}
        self.assertNotIn("MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS", reqs)
        self.assertNotIn("MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS", reqs)
        child_reqs = [r for c in self.sub["certificates"] for r in c["requires"]]
        self.assertTrue(set(child_reqs).issubset(reqs))

    def test_exact_duplicates_merge_once(self):
        f = copy.deepcopy(self.frontier)
        rows = [c for c in f["certificates"] if c["id"] != "MATCHED_SCOPE_BINDING_CERTIFICATE"]
        requirement = rows[0]["requires"][0]
        rows[1]["requires"].append(requirement)
        out = compile_basis(f, self.sub, self.activation)
        self.assertTrue(out["status"].startswith("PASS"), out)
        hits = [x for x in out["proof_atoms"] if x["requirement"] == requirement]
        self.assertEqual(len(hits), 1)
        self.assertGreaterEqual(hits[0]["certificate_fanout_count"], 2)

    def test_nonidentical_requirements_do_not_merge(self):
        f = copy.deepcopy(self.frontier)
        rows = [c for c in f["certificates"] if c["id"] != "MATCHED_SCOPE_BINDING_CERTIFICATE"]
        requirement = rows[0]["requires"][0]
        rows[1]["requires"].append(requirement + "_SIMILAR")
        out = compile_basis(f, self.sub, self.activation)
        reqs = {x["requirement"] for x in out["proof_atoms"]}
        self.assertIn(requirement, reqs)
        self.assertIn(requirement + "_SIMILAR", reqs)

    def test_cross_target_child_inheritance_fails_closed(self):
        sub = copy.deepcopy(self.sub)
        sub["certificates"][0]["requires"][0] = sub["certificates"][1]["requires"][0]
        out = compile_basis(self.frontier, sub, self.activation)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_missing_child_fails_closed(self):
        sub = copy.deepcopy(self.sub)
        sub["certificates"] = sub["certificates"][:-1]
        out = compile_basis(self.frontier, sub, self.activation)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_inactive_refinement_fails_closed(self):
        activation = copy.deepcopy(self.activation)
        activation["status"] = "CANDIDATE_ONLY"
        out = compile_basis(self.frontier, self.sub, activation)
        self.assertEqual(out["status"], "FAIL_CLOSED")

if __name__ == "__main__":
    unittest.main()
