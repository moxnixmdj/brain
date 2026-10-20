from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as loop
from canonical.runtime import executable_skill_program_v7 as skill_program
from canonical.runtime import executable_skill_verification_authenticator_v1 as authenticator


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

    @mock.patch.object(
        loop, "reauthenticate_skill_record",
        lambda skill, repo_root=None: {"pass": True, "verified_skill": skill},
    )
    def test_unbound_proven_superset_stays_source_scope_only(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(candidate),
        )
        # The store is content-addressed: a skill is keyed by the id derived
        # from the skill itself and carries its family. Keying it by a literal
        # name, as these tests did, meant the selector could never match it --
        # so the two reuse tests failed, and the drift test passed for the
        # wrong reason: it returned None whatever the drift was.
        sid = loop._skill_id(verified)
        state = {
            "skills": {
                sid: {
                    "active": True,
                    "skill": verified,
                    "family_id": loop._family_id(verified),
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

    @mock.patch.object(
        loop, "reauthenticate_skill_record",
        lambda skill, repo_root=None: {"pass": True, "verified_skill": skill},
    )
    def test_structural_match_verified_superset_reuses_across_scope(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(
                candidate,
                predicate=loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            ),
        )
        # The store is content-addressed: a skill is keyed by the id derived
        # from the skill itself and carries its family. Keying it by a literal
        # name, as these tests did, meant the selector could never match it --
        # so the two reuse tests failed, and the drift test passed for the
        # wrong reason: it returned None whatever the drift was.
        sid = loop._skill_id(verified)
        state = {
            "skills": {
                sid: {
                    "active": True,
                    "skill": verified,
                    "family_id": loop._family_id(verified),
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
        self.assertEqual(selected["skill_id"], sid)

    @mock.patch.object(
        loop, "reauthenticate_skill_record",
        lambda skill, repo_root=None: {"pass": True, "verified_skill": skill},
    )
    def test_cross_scope_reuse_still_requires_exact_executable_structure(self):
        candidate = self.candidate()
        verified = skill_program.verify_candidate(
            candidate=candidate,
            verification_receipt=self.legacy_receipt(
                candidate,
                predicate=loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            ),
        )
        # The store is content-addressed: a skill is keyed by the id derived
        # from the skill itself and carries its family. Keying it by a literal
        # name, as these tests did, meant the selector could never match it --
        # so the two reuse tests failed, and the drift test passed for the
        # wrong reason: it returned None whatever the drift was.
        sid = loop._skill_id(verified)
        state = {
            "skills": {
                sid: {
                    "active": True,
                    "skill": verified,
                    "family_id": loop._family_id(verified),
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
            "independent_verifier_id": "independent:test",
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
            "independent_verifier_id": "independent:test",
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
