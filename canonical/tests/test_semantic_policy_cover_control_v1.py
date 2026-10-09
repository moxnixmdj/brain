from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import semantic_policy_cover_control_v1 as control


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def _write_json(path: Path, value) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return _git_blob(raw)


class SemanticPolicyCoverControlV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fixture(self, candidates, policy_conditions):
        candidates = sorted(candidates)
        cert_path = self.root / "canonical/governance/universe.json"
        cert = {
            "schema": control.UNIVERSE_SCHEMA,
            "universe_id": "U",
            "candidate_ids_sha256": control._sha(candidates),
            "candidate_count": len(candidates),
            "candidate_set_completeness_proved": True,
        }
        cert_blob = _write_json(cert_path, cert)
        verify_path = self.root / "canonical/verification/universe.json"
        verify = {
            "schema": control.UNIVERSE_VERIFY_SCHEMA,
            "universe_id": "U",
            "subject_git_blob_sha": cert_blob,
            "pass": True,
            "candidate_set_completeness_independently_verified": True,
        }
        verify_blob = _write_json(verify_path, verify)
        universe_binding = {
            "certificate_path": "canonical/governance/universe.json",
            "certificate_blob_sha": cert_blob,
            "independent_verification_path": "canonical/verification/universe.json",
            "independent_verification_blob_sha": verify_blob,
        }

        policy_bindings = {}
        for policy_id, condition in policy_conditions.items():
            adequacy_path = (
                self.root / "canonical/governance" / (policy_id + ".json")
            )
            adequacy = {
                "schema": control.ADEQUACY_SCHEMA,
                "policy_id": policy_id,
                "policy_condition_sha256": control._sha(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }
            adequacy_blob = _write_json(adequacy_path, adequacy)
            policy_verify_path = (
                self.root / "canonical/verification" / (policy_id + ".json")
            )
            policy_verify = {
                "schema": control.ADEQUACY_VERIFY_SCHEMA,
                "policy_id": policy_id,
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }
            policy_verify_blob = _write_json(
                policy_verify_path, policy_verify
            )
            policy_bindings[policy_id] = {
                "adequacy_certificate_path": (
                    "canonical/governance/" + policy_id + ".json"
                ),
                "adequacy_certificate_blob_sha": adequacy_blob,
                "independent_verification_path": (
                    "canonical/verification/" + policy_id + ".json"
                ),
                "independent_verification_blob_sha": policy_verify_blob,
            }
        return universe_binding, policy_bindings

    def test_common_policy_eliminates_need_to_resolve_meaning(self):
        candidates = ["collateral-margin", "profit-margin"]
        atoms = {
            candidate: control.candidate_atom(candidate)
            for candidate in candidates
        }
        conditions = {
            "SAFE_COMMON": {"op": "TRUE"},
            "PROFIT_ONLY": {"op": "ATOM", "id": atoms["profit-margin"]},
            "COLLATERAL_ONLY": {
                "op": "ATOM",
                "id": atoms["collateral-margin"],
            },
        }
        universe, bindings = self._fixture(candidates, conditions)
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [],
            },
            repo_root=self.root,
        )
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["selected_policy_id"], "SAFE_COMMON")
        self.assertFalse(result["semantic_identity_required"])
        self.assertFalse(result["terminal_signature_required"])

    def test_minimum_policy_changing_discriminator_is_selected(self):
        candidates = ["collateral-margin", "profit-margin"]
        atoms = {
            candidate: control.candidate_atom(candidate)
            for candidate in candidates
        }
        conditions = {
            "PROFIT": {"op": "ATOM", "id": atoms["profit-margin"]},
            "COLLATERAL": {
                "op": "ATOM",
                "id": atoms["collateral-margin"],
            },
        }
        universe, bindings = self._fixture(candidates, conditions)
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [
                    {
                        "observation_id": "expensive",
                        "outcome_map_complete": True,
                        "outcomes": {
                            "profit-margin": "profit",
                            "collateral-margin": "collateral",
                        },
                        "cost_units": 9,
                    },
                    {
                        "observation_id": "cheap",
                        "outcome_map_complete": True,
                        "outcomes": {
                            "profit-margin": "profit",
                            "collateral-margin": "collateral",
                        },
                        "cost_units": 1,
                    },
                ],
            },
            repo_root=self.root,
        )
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["status"],
            "OPEN__MINIMUM_POLICY_CHANGING_SEMANTIC_DISCRIMINATOR_SELECTED",
        )
        self.assertEqual(result["next_observation_id"], "cheap")
        self.assertEqual(result["minimum_worst_case_cost_units"], 1.0)

    def test_multistep_minimax_cost_is_exact(self):
        candidates = ["a", "b", "c", "d"]
        conditions = {
            "P_" + candidate: {
                "op": "ATOM",
                "id": control.candidate_atom(candidate),
            }
            for candidate in candidates
        }
        universe, bindings = self._fixture(candidates, conditions)
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [
                    {
                        "observation_id": "bit1",
                        "outcome_map_complete": True,
                        "outcomes": {"a": 0, "b": 0, "c": 1, "d": 1},
                        "cost_units": 2,
                    },
                    {
                        "observation_id": "bit2",
                        "outcome_map_complete": True,
                        "outcomes": {"a": 0, "b": 1, "c": 0, "d": 1},
                        "cost_units": 1,
                    },
                ],
            },
            repo_root=self.root,
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["minimum_worst_case_cost_units"], 3.0)
        self.assertIn(result["next_observation_id"], {"bit1", "bit2"})

    def test_incomplete_policy_cover_fails_closed(self):
        candidates = ["a", "b"]
        conditions = {
            "P_A": {"op": "ATOM", "id": control.candidate_atom("a")},
        }
        universe, bindings = self._fixture(candidates, conditions)
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [],
            },
            repo_root=self.root,
        )
        self.assertEqual(
            result["status"],
            "FAIL_CLOSED__AUTHENTICATED_POLICY_COVER_INCOMPLETE",
        )
        self.assertEqual(result["uncovered_candidate_ids"], ["b"])

    def test_universe_blob_tamper_is_rejected(self):
        candidates = ["a"]
        conditions = {"P": {"op": "TRUE"}}
        universe, bindings = self._fixture(candidates, conditions)
        path = self.root / "canonical/governance/universe.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["candidate_count"] = 99
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [],
            },
            repo_root=self.root,
        )
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIn(
            "CANDIDATE_UNIVERSE_CERTIFICATE_BLOB_DRIFT",
            result["reason"],
        )

    def test_policy_blob_tamper_is_rejected(self):
        candidates = ["a"]
        conditions = {"P": {"op": "TRUE"}}
        universe, bindings = self._fixture(candidates, conditions)
        path = self.root / "canonical/governance/P.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["adequacy_proved"] = False
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [],
            },
            repo_root=self.root,
        )
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertIn("ADEQUACY_CERTIFICATE_BLOB_DRIFT", result["reason"])

    def test_indistinguishable_policy_regions_remain_open(self):
        candidates = ["a", "b"]
        conditions = {
            "P_A": {"op": "ATOM", "id": control.candidate_atom("a")},
            "P_B": {"op": "ATOM", "id": control.candidate_atom("b")},
        }
        universe, bindings = self._fixture(candidates, conditions)
        result = control.solve(
            {
                "universe_id": "U",
                "candidate_ids": candidates,
                "candidate_universe_binding": universe,
                "policy_conditions": conditions,
                "policy_adequacy_bindings": bindings,
                "observations": [
                    {
                        "observation_id": "useless",
                        "outcome_map_complete": True,
                        "outcomes": {"a": "same", "b": "same"},
                        "cost_units": 0,
                    }
                ],
            },
            repo_root=self.root,
        )
        self.assertEqual(
            result["status"],
            (
                "OPEN__POLICY_DISTINCT_SEMANTIC_CANDIDATES_NOT_"
                "SEPARABLE_BY_DECLARED_OBSERVATIONS"
            ),
        )
        self.assertIsNotNone(result["conflicting_policy_region_witness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
