from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import capability_parallel_frontier_v2 as p


class ParallelFrontierV2CompletionTests(unittest.TestCase):
    def test_12_of_12_routes_to_verified_same_subject_composition_gate_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prof_path = root / p.PROFESSIONAL_SOURCE_REL
            assurance_path = root / p.CURRENT_ASSURANCE_REL
            prof_path.parent.mkdir(parents=True, exist_ok=True)

            professional = {
                "status": "X__12_OF_12_CURRENT_ROOT_BINDINGS__COMPOSITION_NEXT__NOT_LIVE_DEFAULT",
                "next": "RUN_SAME_SUBJECT_COMPOSITION_GATE_AT_12_OF_12",
                "same_subject_root_binding_frontier": {
                    "verified_root_subject_binding_count": 12,
                },
                "final_subject": {
                    "subject_id": "SUBJECT-V7",
                    "subject_sha256": "sha256-v7",
                },
            }
            assurance = {
                "schema": "PROJECT_BRAIN_CURRENT_ASSURANCE_CLOSURE_COMPILER_POINTER_V1",
                "status": (
                    "CURRENT_UVCK_V2_CANDIDATE__"
                    "12_OF_12_CURRENT_ROOT_SUBJECT_BINDINGS__"
                    "COMPOSITION_NEXT__NOT_LIVE_DEFAULT"
                ),
                "activation": {
                    "live_default": False,
                    "required_before_promotion": sorted(
                        p.EXPECTED_ASSURANCE_PROMOTION_BLOCKERS
                    ),
                },
                "terminal_authority": False,
                "live_default": False,
                "professional_quality_same_subject_frontier": {
                    "subject_id": "SUBJECT-V7",
                    "subject_sha256": "sha256-v7",
                    "verified_root_subject_binding_count": 12,
                    "root_count": 12,
                    "next": "SAME_SUBJECT_COMPOSITION",
                },
            }
            prof_path.write_text(json.dumps(professional), encoding="utf-8")
            assurance_path.write_text(json.dumps(assurance), encoding="utf-8")

            frontier = {
                "frontier_id": "F-COMPLETE",
                "scope": {
                    "source_set": [
                        {
                            "path": p.PROFESSIONAL_SOURCE_REL,
                            "git_blob_sha": "stale-professional",
                        },
                        {
                            "path": p.CURRENT_ASSURANCE_REL,
                            "git_blob_sha": "stale-assurance",
                        },
                    ]
                },
                "currentness_findings": [
                    {"id": "PROFESSIONAL_CURRENT", "truth": "R12_NEXT"},
                    {"id": "ASSURANCE_CURRENT_PATH", "truth": "R12_NEXT"},
                ],
                "candidates": [
                    {
                        "work_id": "PROFESSIONAL_QUALITY_V7_R12_META_COMPOSITION_CLOSURE_BINDING",
                        "scheduler_state": "READY_EXECUTION",
                        "prerequisites_satisfied": True,
                        "prerequisite_work_ids": [],
                        "mutation_keys": ["canonical:professional-quality"],
                        "authority_keys": ["authority:professional-v7-subject"],
                        "explicit_conflict_work_ids": [],
                        "evidence_conflict_keys": [],
                        "evidence_acquisition_mode": "READ_ONLY",
                        "vector_evidence_state": "PARTIAL",
                        "vector_evidence": {},
                        "read_only_evidence": {},
                    },
                    {
                        "work_id": "ASSURANCE_UVCK_V2_PROMOTION_GATES",
                        "scheduler_state": "BLOCKED",
                        "prerequisites_satisfied": False,
                        "prerequisite_work_ids": ["DOMAIN", "REGRESSION"],
                        "mutation_keys": ["canonical:assurance"],
                        "authority_keys": ["authority:uvck-v2-promotion"],
                        "explicit_conflict_work_ids": [],
                        "evidence_conflict_keys": [],
                        "evidence_acquisition_mode": "READ_ONLY",
                        "vector_evidence_state": "PARTIAL",
                        "vector_evidence": {},
                        "read_only_evidence": {},
                    },
                ],
            }

            refreshed = p.refresh_supported_dynamic_sources(frontier, root=root)
            row = refreshed["candidates"][0]

            self.assertEqual(
                row["work_id"],
                "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_COMPOSITION_GATE",
            )
            self.assertEqual(row["scheduler_state"], "READY_EVIDENCE")
            self.assertEqual(row["evidence_acquisition_mode"], "READ_ONLY")
            self.assertTrue(row["prerequisites_satisfied"])
            self.assertEqual(
                row["read_only_evidence"]["composition_gate_runtime_git_blob_sha"],
                p.PROFESSIONAL_COMPOSITION_GATE_RUNTIME_SHA,
            )
            self.assertEqual(
                refreshed["dynamic_currentness"]["professional_next_root"],
                "SAME_SUBJECT_COMPOSITION_GATE",
            )

            out = p.plan_parallel_frontier(refreshed, root=root)
            self.assertIn(
                "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_COMPOSITION_GATE",
                out["parallel_read_only_evidence_work_ids"],
            )
            self.assertNotIn(
                "PROFESSIONAL_QUALITY_V7_SAME_SUBJECT_COMPOSITION_GATE",
                out["parallel_full_execution_work_ids"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
