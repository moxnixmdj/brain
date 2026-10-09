from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as loop
from canonical.runtime import executable_skill_program_v7 as skill_program
from canonical.runtime import executable_skill_verification_authenticator_v1 as authenticator
from canonical.runtime import r3_independent_learning_verifier_v1 as independent


class VerifiedCrossScopeGeneralizationTests(unittest.TestCase):
    def candidate(self):
        steps = [{"index": 0, "op": "cap.demo", "inputs": ["A"], "outputs": ["B"]}]
        digest = skill_program.candidate_digest(
            source_episode_ids=["e1", "e2"],
            steps=steps,
            preconditions=["A"],
            postconditions=["B"],
            invalidators=[],
        )
        return {
            "schema": skill_program.SCHEMA,
            "status": "EXECUTABLE_SKILL_CANDIDATE_ONLY",
            "source_episode_ids": ["e1", "e2"],
            "source_episode_receipts": ["r1", "r2"],
            "source_scopes": ["scope-a"],
            "steps": steps,
            "preconditions": ["A"],
            "postconditions": ["B"],
            "invalidators": [],
            "candidate_sha256": digest,
            "verified_skill": False,
            "reuse_authorized": False,
            "candidate_only": True,
        }

    def legacy_receipt(self, candidate, *, relation="PROVEN_SUPERSET", predicate=None):
        out = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": ["e1", "e2"],
            "behavior_preserving_on_claimed_scope": True,
            "scope_relation": relation,
            "receipt_id": "SKVR:test",
        }
        if predicate is not None:
            out["scope_predicate"] = predicate
        return out

    def test_unbound_proven_superset_stays_source_scope_only(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(candidate),
        )
        state = {
            "skills": {
                "skill:test": {
                    "active": True,
                    "skill": verified,
                    "pareto_metrics": {},
                }
            }
        }
        problem = {
            "task_id": "t",
            "initial_facts": ["A"],
            "target_effects": ["B"],
            "capabilities": [
                {"id": "cap.demo", "requires": ["A"], "provides": ["B"]}
            ],
        }
        self.assertIsNone(
            loop._select_active_skill(
                problem,
                state,
                scope_id="scope-b",
                known_absent_invalidators=[],
            )
        )
        same_scope = loop._select_active_skill(
            problem,
            state,
            scope_id="scope-a",
            known_absent_invalidators=[],
        )
        self.assertIsNotNone(same_scope)

    def test_structural_match_verified_superset_reuses_across_scope(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(
                candidate,
                predicate=loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            ),
        )
        state = {
            "skills": {
                "skill:test": {
                    "active": True,
                    "skill": verified,
                    "pareto_metrics": {},
                }
            }
        }
        problem = {
            "task_id": "t",
            "initial_facts": ["A"],
            "target_effects": ["B"],
            "capabilities": [
                {"id": "cap.demo", "requires": ["A"], "provides": ["B"]}
            ],
        }
        selected = loop._select_active_skill(
            problem,
            state,
            scope_id="scope-b",
            known_absent_invalidators=[],
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected["skill_id"], "skill:test")

    def test_cross_scope_reuse_still_requires_exact_executable_structure(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(
                candidate,
                predicate=loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            ),
        )
        state = {
            "skills": {
                "skill:test": {
                    "active": True,
                    "skill": verified,
                    "pareto_metrics": {},
                }
            }
        }
        drifted = {
            "task_id": "t",
            "initial_facts": ["A"],
            "target_effects": ["B"],
            "capabilities": [
                {"id": "cap.demo", "requires": ["A"], "provides": ["C"]}
            ],
        }
        self.assertIsNone(
            loop._select_active_skill(
                drifted,
                state,
                scope_id="scope-b",
                known_absent_invalidators=[],
            )
        )

    def test_pareto_generalization_credit_requires_bound_predicate(self):
        candidate = self.candidate()
        unbound = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(candidate),
        )
        bound = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(
                candidate,
                predicate=loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            ),
        )
        self.assertEqual(loop._skill_pareto_row("skill:u", unbound)["generalization"], 1)
        self.assertEqual(loop._skill_pareto_row("skill:b", bound)["generalization"], 2)

    @mock.patch.object(independent, "resolve_receipt_bytes")
    def test_generalization_admits_non_effectful_source_proof(self, resolve):
        resolve.return_value = {
            "document": {
                "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
                "verification_basis": independent.NON_EFFECTFUL_VERIFICATION_BASIS,
                "non_effectful_trace": True,
            }
        }
        out = independent._assert_generalizable_source_proof(
            {"verification_binding": {"verification": {}}},
            repo_root=Path("."),
        )
        self.assertEqual(out, "NON_EFFECTFUL")

    @mock.patch.object(independent, "resolve_receipt_bytes")
    def test_generalization_admits_reverified_bound_carrier_effectful_source(self, resolve):
        resolve.return_value = {
            "document": {
                "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
                "verification_basis": independent.BOUND_CARRIER_VERIFICATION_BASIS,
                "bound_carrier_effectful_trace": True,
                "effect_outcomes_reverified": True,
                "trace_reverified": True,
                "state_lineage_reverified": True,
                "behavior_verified": True,
                "exact_byte_bound": True,
                "non_effectful_trace": False,
            }
        }
        out = independent._assert_generalizable_source_proof(
            {"verification_binding": {"verification": {}}},
            repo_root=Path("."),
        )
        self.assertEqual(out, "BOUND_CARRIER_EFFECTFUL")

    @mock.patch.object(independent, "resolve_receipt_bytes")
    def test_generalization_rejects_generic_effectful_readback_source(self, resolve):
        resolve.return_value = {
            "document": {
                "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
                "verification_basis": independent.EFFECTFUL_READBACK_VERIFICATION_BASIS,
                "bound_carrier_effectful_trace": False,
                "effect_outcomes_reverified": True,
                "trace_reverified": True,
                "state_lineage_reverified": True,
                "behavior_verified": True,
                "exact_byte_bound": True,
                "non_effectful_trace": False,
            }
        }
        with self.assertRaisesRegex(
            independent.R3IndependentVerificationError,
            "GENERALIZATION_SOURCE_PROOF_CLASS_NOT_ADMITTED",
        ):
            independent._assert_generalizable_source_proof(
                {"verification_binding": {"verification": {}}},
                repo_root=Path("."),
            )

    @mock.patch.object(independent, "resolve_receipt_bytes")
    def test_generalization_rejects_incomplete_bound_carrier_proof(self, resolve):
        base = {
            "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
            "verification_basis": independent.BOUND_CARRIER_VERIFICATION_BASIS,
            "bound_carrier_effectful_trace": True,
            "effect_outcomes_reverified": True,
            "trace_reverified": True,
            "state_lineage_reverified": True,
            "behavior_verified": True,
            "exact_byte_bound": True,
            "non_effectful_trace": False,
        }
        for missing in (
            "effect_outcomes_reverified",
            "trace_reverified",
            "state_lineage_reverified",
            "behavior_verified",
            "exact_byte_bound",
        ):
            row = dict(base)
            row[missing] = False
            resolve.return_value = {"document": row}
            with self.assertRaisesRegex(
                independent.R3IndependentVerificationError,
                "GENERALIZATION_SOURCE_PROOF_CLASS_NOT_ADMITTED",
            ):
                independent._assert_generalizable_source_proof(
                    {"verification_binding": {"verification": {}}},
                    repo_root=Path("."),
                )

    def test_full_generalization_verifier_and_authenticator_accept_two_bound_carrier_sources(self):
        steps = [
            {
                "index": 0,
                "op": "cap.demo",
                "inputs": ["A"],
                "outputs": ["B"],
            }
        ]

        def episode(eid, scope, receipt_id):
            program = skill_program.program_digest(
                steps=steps,
                preconditions=["A"],
                postconditions=["B"],
                invalidators=[],
            )
            return {
                "episode_id": eid,
                "scope_id": scope,
                "steps": steps,
                "preconditions": ["A"],
                "postconditions": ["B"],
                "invalidators": [],
                "program_sha256": program,
                "verification_receipt": {
                    "independent_verified": True,
                    "exact_byte_bound": True,
                    "conclusion": "success",
                    "behavior_verified": True,
                    "episode_id": eid,
                    "scope_id": scope,
                    "program_sha256": program,
                    "receipt_id": receipt_id,
                },
            }

        ep1 = episode("e1", "scope-a", "ER:e1")
        ep2 = episode("e2", "scope-b", "ER:e2")
        candidate = skill_program.induce_candidate([ep1, ep2])
        raw1 = {
            "episode_id": "e1",
            "verification_binding": {"verification": {"path": "v1"}},
        }
        raw2 = {
            "episode_id": "e2",
            "verification_binding": {"verification": {"path": "v2"}},
        }
        bound_doc = {
            "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
            "verification_basis": independent.BOUND_CARRIER_VERIFICATION_BASIS,
            "bound_carrier_effectful_trace": True,
            "effect_outcomes_reverified": True,
            "trace_reverified": True,
            "state_lineage_reverified": True,
            "behavior_verified": True,
            "exact_byte_bound": True,
            "non_effectful_trace": False,
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_path = root / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "episodes": {
                            "episode:e1": raw1,
                            "episode:e2": raw2,
                        }
                    }
                ),
                encoding="utf-8",
            )

            def reauth(raw, *, repo_root):
                eid = raw["episode_id"]
                return {
                    "pass": True,
                    "authenticated_episode": ep1 if eid == "e1" else ep2,
                }

            with mock.patch.object(
                independent,
                "reauthenticate_episode_record",
                side_effect=reauth,
            ), mock.patch.object(
                independent,
                "resolve_receipt_bytes",
                return_value={"document": bound_doc},
            ):
                binding = independent.verify_skill_request(
                    {
                        "kind": "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
                        "candidate": candidate,
                        "requested_scope_relation": "PROVEN_SUPERSET",
                        "requested_scope_predicate": (
                            independent.STRUCTURAL_MATCH_SCOPE_PREDICATE
                        ),
                        "supported_scope_predicates": [
                            independent.STRUCTURAL_MATCH_SCOPE_PREDICATE
                        ],
                    },
                    repo_root=root,
                    state_path=state_path,
                    receipt_dir="receipts",
                )

            self.assertIsInstance(binding, dict)
            receipt = json.loads(
                (root / binding["receipt"]["path"]).read_text(encoding="utf-8")
            )
            verification = json.loads(
                (root / binding["verification"]["path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["scope_relation"], "PROVEN_SUPERSET")
            self.assertEqual(
                receipt["scope_predicate"],
                independent.STRUCTURAL_MATCH_SCOPE_PREDICATE,
            )
            self.assertEqual(
                verification["generalization_source_proof_classes"],
                ["BOUND_CARRIER_EFFECTFUL", "BOUND_CARRIER_EFFECTFUL"],
            )
            authenticated = authenticator.authenticate_and_verify(
                candidate,
                binding,
                repo_root=root,
            )
            self.assertTrue(authenticated["pass"], authenticated)
            skill = authenticated["verified_skill"]
            self.assertTrue(skill["reuse_authorized"])
            self.assertEqual(skill["scope_relation"], "PROVEN_SUPERSET")
            self.assertEqual(
                skill["scope_predicate"],
                independent.STRUCTURAL_MATCH_SCOPE_PREDICATE,
            )

    @mock.patch(
        "canonical.runtime.executable_skill_verification_authenticator_v1.resolve_receipt_bytes"
    )
    def test_authenticator_binds_scope_predicate_in_both_receipts(self, resolve):
        candidate = self.candidate()
        predicate = loop.VERIFIED_SUPERSET_SCOPE_PREDICATE
        receipt_doc = {
            "schema": authenticator.RECEIPT_SCHEMA,
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": ["e1", "e2"],
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": predicate,
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
        }
        verify_doc = {
            "schema": authenticator.VERIFY_SCHEMA,
            "subject_git_blob_sha": "blob-receipt",
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": ["e1", "e2"],
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": predicate,
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
        }
        resolve.side_effect = [
            {"document": receipt_doc, "git_blob_sha": "blob-receipt", "path": "receipt.json"},
            {"document": verify_doc, "git_blob_sha": "blob-verify", "path": "verify.json"},
        ]
        out = authenticator.authenticate_and_verify(
            candidate,
            {"receipt": {}, "verification": {}},
            repo_root=Path("."),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["verified_skill"]["scope_predicate"], predicate)

    @mock.patch(
        "canonical.runtime.executable_skill_verification_authenticator_v1.resolve_receipt_bytes"
    )
    def test_authenticator_rejects_scope_predicate_disagreement(self, resolve):
        candidate = self.candidate()
        predicate = loop.VERIFIED_SUPERSET_SCOPE_PREDICATE
        receipt_doc = {
            "schema": authenticator.RECEIPT_SCHEMA,
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": ["e1", "e2"],
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": predicate,
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
        }
        verify_doc = {
            "schema": authenticator.VERIFY_SCHEMA,
            "subject_git_blob_sha": "blob-receipt",
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": ["e1", "e2"],
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": "",
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": independent.INDEPENDENT_VERIFIER_ID,
        }
        resolve.side_effect = [
            {"document": receipt_doc, "git_blob_sha": "blob-receipt", "path": "receipt.json"},
            {"document": verify_doc, "git_blob_sha": "blob-verify", "path": "verify.json"},
        ]
        out = authenticator.authenticate_and_verify(
            candidate,
            {"receipt": {}, "verification": {}},
            repo_root=Path("."),
        )
        self.assertFalse(out["pass"], out)
        self.assertIn("SKILL_SCOPE_PREDICATE_BINDING_MISMATCH", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
