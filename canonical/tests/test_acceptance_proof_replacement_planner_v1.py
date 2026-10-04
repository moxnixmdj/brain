from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_proof_replacement_planner_v1 import (
    INPUT_SCHEMA,
    compile_replacement_frontier,
)
from canonical.runtime.proof_obligation_delta_compiler_v1 import INPUT_SCHEMA as DELTA_SCHEMA

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


def receipt(path: str, sha: str = SHA_A):
    return {"path": path, "git_blob_sha": sha}


def delta_payload():
    return {
        "schema": DELTA_SCHEMA,
        "target": {
            "id": "P",
            "scope_components": [
                {"id": "scope", "source_path": "target.json", "source_sha": SHA_A},
            ],
            "required_atoms": ["A"],
            "required_invariants": ["I"],
            "metric_requirements": [
                {"metric": "score", "direction": "higher", "threshold": 1.0},
            ],
        },
        "witness": {
            "id": "W",
            "scope_components": [
                {"id": "w_scope", "source_path": "witness.json", "source_sha": SHA_B},
            ],
            "proved_atoms": ["WA"],
            "proved_invariants": ["WI"],
            "metric_bounds": {"w_score": {"lower": 1.0}},
        },
        "scope_bindings": [
            {
                "witness_component": "w_scope",
                "target_component": "scope",
                "relation": "EXACT",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/scope.json", SHA_C),
            }
        ],
        "atom_bindings": [
            {
                "witness_atom": "WA",
                "target_atom": "A",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/atom.json", SHA_C),
            }
        ],
        "invariant_bindings": [
            {
                "witness_invariant": "WI",
                "target_invariant": "I",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/invariant.json", SHA_C),
            }
        ],
        "metric_bindings": [
            {
                "witness_metric": "w_score",
                "target_metric": "score",
                "verified": True,
                "independent": True,
                "receipt": receipt("canonical/verification/metric.json", SHA_C),
            }
        ],
    }


def implication_payload():
    return {
        "target": {
            "scope_ref": "scope:P",
            "required_atoms": ["A"],
            "metric_requirements": [
                {"metric": "score", "direction": "higher", "threshold": 1.0},
            ],
        },
        "witness": {
            "scope_ref": "scope:W",
            "proved_atoms": ["A"],
            "metric_bounds": {"score": {"lower": 1.0}},
            "verified": True,
            "independent": True,
            "contamination_clean": True,
        },
        "verified_scope_relations": [
            {
                "witness_scope": "scope:W",
                "target_scope": "scope:P",
                "relation": "SUPERSET",
                "verified": True,
                "independent": True,
                "receipt": "canonical/verification/scope-relation.json@" + SHA_C,
            }
        ],
        "verified_implications": [],
    }


def base():
    return {
        "schema": INPUT_SCHEMA,
        "target": {
            "id": "P",
            "scope_ref": "scope:P",
            "receipt": receipt("canonical/governance/target.json"),
        },
        "allow_fresh_reality": False,
        "route_candidates": [],
    }


class AcceptanceProofReplacementPlannerTests(unittest.TestCase):
    def test_verified_delta_candidate_is_found_but_zero_credit(self):
        d = base()
        d["route_candidates"] = [
            {
                "route_id": "ceiling",
                "kind": "OBJECTIVE_CEILING",
                "mode": "DELTA",
                "zero_reality": True,
                "critical_path_seconds": 2,
                "payload": delta_payload(),
            }
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["status"], "PROVED_REPLACEMENT_CANDIDATE_FOUND__ZERO_CREDIT")
        self.assertEqual(out["closure_candidates"][0]["route_id"], "ceiling")
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_scope_safe_implication_candidate_is_found(self):
        d = base()
        d["route_candidates"] = [
            {
                "route_id": "formal",
                "kind": "FORMAL_IMPLICATION",
                "mode": "IMPLICATION",
                "zero_reality": True,
                "critical_path_seconds": 1,
                "payload": implication_payload(),
            }
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["closure_candidates"][0]["proof_status"], "PASS")

    def test_unproved_routes_are_ordered_by_proof_precedence(self):
        d = base()
        d["route_candidates"] = [
            {
                "route_id": "metamorphic",
                "kind": "METAMORPHIC_INVARIANT",
                "mode": "UNPROVED",
                "zero_reality": True,
                "critical_path_seconds": 1,
            },
            {
                "route_id": "formal",
                "kind": "FORMAL_IMPLICATION",
                "mode": "UNPROVED",
                "zero_reality": True,
                "critical_path_seconds": 10,
            },
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(
            [x["route_id"] for x in out["zero_reality_attempt_frontier"]],
            ["formal", "metamorphic"],
        )

    def test_fresh_empirical_route_is_blocked_without_authority(self):
        d = base()
        d["route_candidates"] = [
            {
                "route_id": "empirical",
                "kind": "MATCHED_EMPIRICAL",
                "mode": "UNPROVED",
                "zero_reality": False,
                "critical_path_seconds": 1,
            }
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["zero_reality_attempt_frontier"], [])
        self.assertEqual(out["blocked_fresh_reality_routes"][0]["route_id"], "empirical")
        self.assertFalse(out["fresh_reality_authority"])

    def test_target_identity_mismatch_fails_closed(self):
        d = base()
        payload = delta_payload()
        payload["target"]["id"] = "OTHER"
        d["route_candidates"] = [
            {
                "route_id": "bad",
                "kind": "OBJECTIVE_CEILING",
                "mode": "DELTA",
                "zero_reality": True,
                "critical_path_seconds": 1,
                "payload": payload,
            }
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ROUTE_TARGET_IDENTITY_MISMATCH:bad", out["errors"])

    def test_name_similarity_never_closes_missing_atom(self):
        d = base()
        payload = delta_payload()
        payload["witness"]["proved_atoms"] = ["A"]
        payload["atom_bindings"] = []
        d["route_candidates"] = [
            {
                "route_id": "name-only",
                "kind": "FORMAL_IMPLICATION",
                "mode": "DELTA",
                "zero_reality": True,
                "critical_path_seconds": 1,
                "payload": payload,
            }
        ]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["closure_candidates"], [])
        self.assertEqual(out["zero_reality_attempt_frontier"][0]["status"], "PROOF_ATTEMPT_RESIDUAL_OPEN")

    def test_duplicate_route_id_fails_closed(self):
        d = base()
        row = {
            "route_id": "same",
            "kind": "FORMAL_IMPLICATION",
            "mode": "UNPROVED",
            "zero_reality": True,
            "critical_path_seconds": 1,
        }
        d["route_candidates"] = [copy.deepcopy(row), copy.deepcopy(row)]
        out = compile_replacement_frontier(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ROUTE_ID_DUPLICATE:same", out["errors"])

    def test_target_must_be_content_addressed(self):
        d = base()
        d["target"]["receipt"] = {"path": "target.json", "git_blob_sha": "bad"}
        out = compile_replacement_frontier(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_RECEIPT_NOT_CONTENT_ADDRESSED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
