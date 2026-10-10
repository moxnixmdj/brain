from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import capability_parallel_frontier_v1 as p


def candidate(
    work_id: str,
    *,
    state: str = "READY_EXECUTION",
    complete: bool = False,
    read_only: bool = True,
    mutation_keys=None,
    authority_keys=None,
    evidence_conflict_keys=None,
    benefits=None,
    costs=None,
):
    row = {
        "work_id": work_id,
        "scheduler_state": state,
        "prerequisites_satisfied": True,
        "prerequisite_work_ids": [],
        "mutation_keys": mutation_keys or [],
        "authority_keys": authority_keys or [],
        "explicit_conflict_work_ids": [],
        "evidence_conflict_keys": evidence_conflict_keys or [],
        "evidence_acquisition_mode": "READ_ONLY" if read_only else "MUTATING",
        "vector_evidence_state": "COMPLETE" if complete else "UNBOUND",
    }
    if complete:
        values = {
            "expected_capability_gain_lcb": 1,
            "expected_efficiency_gain_lcb": 1,
            "expected_reliability_gain_lcb": 1,
            "reuse_breadth_lcb": 1,
            "generalization_lcb": 1,
            "success_probability_lcb": 1,
            "wall_clock_cost_ub": 1,
            "compute_cost_ub": 1,
            "memory_cost_ub": 1,
            "complexity_cost_ub": 1,
        }
        values.update(benefits or {})
        values.update(costs or {})
        row.update(values)
        row["vector_evidence"] = {
            field: "evidence/" + work_id + "/" + field for field in p.VECTOR_FIELDS
        }
    return row


def frontier(root: Path, candidates):
    source = root / "source.json"
    source.write_text('{"ok": true}\n', encoding="utf-8")
    return {
        "frontier_id": "F1",
        "scope": {
            "source_set": [
                {
                    "path": "source.json",
                    "git_blob_sha": p._git_blob_sha(source),
                }
            ]
        },
        "candidates": candidates,
    }, source


class ParallelFrontierTests(unittest.TestCase):
    def test_stale_frontier_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, source = frontier(root, [candidate("A")])
            source.write_text('{"changed": true}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                p.ParallelFrontierError,
                "LIVE_WORK_FRONTIER_STALE:source.json",
            ):
                p.plan_parallel_frontier(f, root=root)

    def test_unknown_vectors_can_parallelize_read_only_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(root, [candidate("A"), candidate("B")])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(
                out["parallel_read_only_evidence_work_ids"],
                ["A", "B"],
            )
            self.assertEqual(out["parallel_full_execution_work_ids"], [])

    def test_incomplete_mutating_work_does_not_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(root, [candidate("A", read_only=False)])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["parallel_read_only_evidence_work_ids"], [])
            self.assertEqual(out["mutating_incomplete_vector_work_ids"], ["A"])

    def test_dimensionwise_dominance_prunes_without_scalarization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefits={"expected_capability_gain_lcb": 2},
                costs={"wall_clock_cost_ub": 1},
            )
            b = candidate(
                "B",
                complete=True,
                benefits={"expected_capability_gain_lcb": 1},
                costs={"wall_clock_cost_ub": 2},
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["dominated_by"], {"B": ["A"]})
            self.assertEqual(out["parallel_full_execution_work_ids"], ["A"])

    def test_nonconflicting_complete_work_runs_in_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefits={"expected_capability_gain_lcb": 2, "expected_efficiency_gain_lcb": 0},
                costs={"wall_clock_cost_ub": 2},
                mutation_keys=["domain:a"],
            )
            b = candidate(
                "B",
                complete=True,
                benefits={"expected_capability_gain_lcb": 0, "expected_efficiency_gain_lcb": 2},
                costs={"wall_clock_cost_ub": 2},
                mutation_keys=["domain:b"],
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(
                out["parallel_full_execution_work_ids"],
                ["A", "B"],
            )
            self.assertEqual(out["unresolved_full_execution_conflict_components"], [])

    def test_conflicting_incomparable_work_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefits={"expected_capability_gain_lcb": 2, "expected_efficiency_gain_lcb": 0},
                mutation_keys=["shared"],
            )
            b = candidate(
                "B",
                complete=True,
                benefits={"expected_capability_gain_lcb": 0, "expected_efficiency_gain_lcb": 2},
                mutation_keys=["shared"],
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["parallel_full_execution_work_ids"], [])
            self.assertEqual(
                out["unresolved_full_execution_conflict_components"],
                [["A", "B"]],
            )

    def test_sleeping_work_is_not_primary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(
                root,
                [
                    candidate("A"),
                    candidate("S", state="SLEEPING"),
                ],
            )
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["ready_candidate_ids"], ["A"])
            self.assertEqual(out["nonprimary_candidate_ids"], ["S"])

    def test_ready_candidate_requires_satisfied_prerequisites(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            row = candidate("A")
            row["prerequisites_satisfied"] = False
            f, _ = frontier(root, [row])
            with self.assertRaisesRegex(
                p.ParallelFrontierError,
                "READY_CANDIDATE_PREREQUISITES_NOT_SATISFIED:A",
            ):
                p.plan_parallel_frontier(f, root=root)


    def test_dynamic_professional_pointer_follow_rekeys_next_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prof_path = root / p.PROFESSIONAL_SOURCE_REL
            prof_path.parent.mkdir(parents=True, exist_ok=True)
            old_prof = {
                "status": "X__R9_NEXT__NOT_LIVE_DEFAULT",
                "next": "BIND_R9_TEMPORAL_DEPLOYMENT_TO_V7_PROOF_BOUND_EXECUTION_SUBJECT",
                "same_subject_root_binding_frontier": {
                    "verified_root_subject_binding_count": 8
                },
            }
            prof_path.write_text(json.dumps(old_prof), encoding="utf-8")
            old_sha = p._git_blob_sha(prof_path)
            f = {
                "frontier_id": "F-DYN",
                "scope": {
                    "source_set": [
                        {
                            "path": p.PROFESSIONAL_SOURCE_REL,
                            "git_blob_sha": old_sha,
                        }
                    ]
                },
                "currentness_findings": [
                    {"id": "PROFESSIONAL_CURRENT", "truth": "R9_NEXT"}
                ],
                "candidates": [
                    {
                        "work_id": "PROFESSIONAL_QUALITY_V7_R9_TEMPORAL_DEPLOYMENT_BINDING",
                        "scheduler_state": "READY_EXECUTION",
                        "prerequisites_satisfied": True,
                        "prerequisite_work_ids": [],
                        "mutation_keys": ["professional"],
                        "authority_keys": ["v7"],
                        "explicit_conflict_work_ids": [],
                        "evidence_conflict_keys": [],
                        "evidence_acquisition_mode": "READ_ONLY",
                        "vector_evidence_state": "PARTIAL",
                        "vector_evidence": {},
                        "read_only_evidence": {},
                    }
                ],
            }
            new_prof = {
                "status": "X__R10_NEXT__NOT_LIVE_DEFAULT",
                "next": "BIND_R10_ANALYSIS_DECISION_TO_V7_PROOF_BOUND_EXECUTION_SUBJECT",
                "same_subject_root_binding_frontier": {
                    "verified_root_subject_binding_count": 9
                },
            }
            prof_path.write_text(json.dumps(new_prof), encoding="utf-8")
            out = p.refresh_supported_dynamic_sources(f, root=root)
            row = out["candidates"][0]
            self.assertEqual(
                row["work_id"],
                "PROFESSIONAL_QUALITY_V7_R10_ANALYSIS_DECISION_BINDING",
            )
            self.assertEqual(
                out["dynamic_currentness"]["professional_next_root"],
                "R10_ANALYSIS_DECISION",
            )
            self.assertEqual(
                out["scope"]["source_set"][0]["git_blob_sha"],
                p._git_blob_sha(prof_path),
            )

    def test_dynamic_professional_pointer_follow_fails_on_incoherent_next(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prof_path = root / p.PROFESSIONAL_SOURCE_REL
            prof_path.parent.mkdir(parents=True, exist_ok=True)
            prof_path.write_text(
                json.dumps(
                    {
                        "status": "X__R10_NEXT",
                        "next": "BIND_R11_WRONG_ROOT",
                        "same_subject_root_binding_frontier": {
                            "verified_root_subject_binding_count": 9
                        },
                    }
                ),
                encoding="utf-8",
            )
            f = {
                "frontier_id": "F-DYN",
                "scope": {
                    "source_set": [
                        {
                            "path": p.PROFESSIONAL_SOURCE_REL,
                            "git_blob_sha": "stale",
                        }
                    ]
                },
                "candidates": [
                    {
                        "work_id": "PROFESSIONAL_QUALITY_V7_R9_TEMPORAL_DEPLOYMENT_BINDING"
                    }
                ],
            }
            with self.assertRaisesRegex(
                p.ParallelFrontierError,
                "CURRENT_PROFESSIONAL_NEXT_ROOT_INCOHERENT",
            ):
                p.refresh_supported_dynamic_sources(f, root=root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
