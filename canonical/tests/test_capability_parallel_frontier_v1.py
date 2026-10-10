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


def professional_state(count: int):
    next_index = count + 1
    next_name = p.PROFESSIONAL_ROOT_NAMES[next_index]
    return {
        "status": f"X__R{next_index}_NEXT__NOT_LIVE_DEFAULT",
        "next": f"BIND_R{next_index}_{next_name}_TO_V7_PROOF_BOUND_EXECUTION_SUBJECT",
        "same_subject_root_binding_frontier": {
            "verified_root_subject_binding_count": count,
        },
        "final_subject": {
            "subject_id": "SUBJECT-V7",
            "subject_sha256": "sha256-v7",
        },
    }


def assurance_state(count: int, *, marker: str = ""):
    next_index = count + 1
    next_name = p.PROFESSIONAL_ROOT_NAMES[next_index]
    return {
        "schema": "PROJECT_BRAIN_CURRENT_ASSURANCE_CLOSURE_COMPILER_POINTER_V1",
        "status": (
            "CURRENT_UVCK_V2_CANDIDATE__"
            + f"{count}_OF_12_CURRENT_ROOT_SUBJECT_BINDINGS__"
            + f"R{next_index}_{next_name}_NEXT__NOT_LIVE_DEFAULT"
        ),
        "activation": {
            "live_default": False,
            "required_before_promotion": sorted(p.EXPECTED_ASSURANCE_PROMOTION_BLOCKERS),
        },
        "terminal_authority": False,
        "live_default": False,
        "professional_quality_same_subject_frontier": {
            "subject_id": "SUBJECT-V7",
            "subject_sha256": "sha256-v7",
            "verified_root_subject_binding_count": count,
            "root_count": 12,
            "next": f"R{next_index}_{next_name}",
        },
        "test_marker": marker,
    }


def dynamic_frontier(root: Path, count: int):
    prof_path = root / p.PROFESSIONAL_SOURCE_REL
    assurance_path = root / p.CURRENT_ASSURANCE_REL
    prof_path.parent.mkdir(parents=True, exist_ok=True)
    prof = professional_state(count)
    assurance = assurance_state(count)
    prof_path.write_text(json.dumps(prof), encoding="utf-8")
    assurance_path.write_text(json.dumps(assurance), encoding="utf-8")
    next_index = count + 1
    next_name = p.PROFESSIONAL_ROOT_NAMES[next_index]
    return {
        "frontier_id": "F-DYN",
        "scope": {
            "source_set": [
                {
                    "path": p.PROFESSIONAL_SOURCE_REL,
                    "git_blob_sha": p._git_blob_sha(prof_path),
                },
                {
                    "path": p.CURRENT_ASSURANCE_REL,
                    "git_blob_sha": p._git_blob_sha(assurance_path),
                },
            ]
        },
        "currentness_findings": [
            {"id": "PROFESSIONAL_CURRENT", "truth": f"R{next_index}_NEXT"},
            {"id": "ASSURANCE_CURRENT_PATH", "truth": f"R{next_index}_NEXT"},
        ],
        "candidates": [
            {
                "work_id": f"PROFESSIONAL_QUALITY_V7_R{next_index}_{next_name}_BINDING",
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
            },
            {
                "work_id": "ASSURANCE_UVCK_V2_PROMOTION_GATES",
                "scheduler_state": "BLOCKED",
                "prerequisites_satisfied": False,
                "prerequisite_work_ids": ["DOMAIN", "REGRESSION"],
                "mutation_keys": ["assurance"],
                "authority_keys": ["uvck"],
                "explicit_conflict_work_ids": [],
                "evidence_conflict_keys": [],
                "evidence_acquisition_mode": "READ_ONLY",
                "vector_evidence_state": "PARTIAL",
                "vector_evidence": {},
                "read_only_evidence": {},
            },
        ],
    }, prof_path, assurance_path


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
            f, prof_path, assurance_path = dynamic_frontier(root, 8)
            prof_path.write_text(json.dumps(professional_state(9)), encoding="utf-8")
            assurance_path.write_text(json.dumps(assurance_state(9)), encoding="utf-8")
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
            self.assertEqual(out["dynamic_currentness"]["assurance_professional_count"], 9)
            self.assertTrue(out["dynamic_currentness"]["assurance_current_pointer_follow"])

    def test_dynamic_assurance_pointer_follow_runs_when_professional_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, prof_path, assurance_path = dynamic_frontier(root, 9)
            old_prof_sha = p._git_blob_sha(prof_path)
            assurance_path.write_text(
                json.dumps(assurance_state(9, marker="new-byte-state")),
                encoding="utf-8",
            )
            out = p.refresh_supported_dynamic_sources(f, root=root)
            self.assertEqual(
                out["scope"]["source_set"][0]["git_blob_sha"],
                old_prof_sha,
            )
            self.assertEqual(
                out["scope"]["source_set"][1]["git_blob_sha"],
                p._git_blob_sha(assurance_path),
            )
            self.assertTrue(out["dynamic_currentness"]["assurance_current_pointer_follow"])

    def test_dynamic_assurance_pointer_follow_fails_on_count_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _, assurance_path = dynamic_frontier(root, 9)
            assurance_path.write_text(json.dumps(assurance_state(8)), encoding="utf-8")
            with self.assertRaisesRegex(
                p.ParallelFrontierError,
                "CURRENT_ASSURANCE_PROFESSIONAL_COUNT_MISMATCH",
            ):
                p.refresh_supported_dynamic_sources(f, root=root)

    def test_dynamic_professional_pointer_follow_fails_on_incoherent_next(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, prof_path, assurance_path = dynamic_frontier(root, 9)
            bad = professional_state(9)
            bad["next"] = "BIND_R11_WRONG_ROOT"
            prof_path.write_text(json.dumps(bad), encoding="utf-8")
            assurance_path.write_text(json.dumps(assurance_state(9)), encoding="utf-8")
            with self.assertRaisesRegex(
                p.ParallelFrontierError,
                "CURRENT_PROFESSIONAL_NEXT_ROOT_INCOHERENT",
            ):
                p.refresh_supported_dynamic_sources(f, root=root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
