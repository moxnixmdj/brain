from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import capability_parallel_frontier_v2 as p


def candidate(
    work_id: str,
    *,
    state: str = "READY_EXECUTION",
    complete: bool = False,
    read_only: bool = True,
    mutation_keys=None,
    benefit_overrides=None,
    cost_overrides=None,
):
    row = {
        "work_id": work_id,
        "scheduler_state": state,
        "prerequisites_satisfied": True,
        "prerequisite_work_ids": [],
        "mutation_keys": mutation_keys or [],
        "authority_keys": [],
        "explicit_conflict_work_ids": [],
        "evidence_conflict_keys": [],
        "evidence_acquisition_mode": "READ_ONLY" if read_only else "MUTATING",
        "vector_evidence_state": "COMPLETE" if complete else "UNBOUND",
    }
    if complete:
        values = {}
        for lcb, ucb in p.BENEFIT_INTERVALS:
            values[lcb] = 1
            values[ucb] = 1
        for lcb, ucb in p.COST_INTERVALS:
            values[lcb] = 1
            values[ucb] = 1
        values.update(benefit_overrides or {})
        values.update(cost_overrides or {})
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


def assurance_state(count: int):
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
    }


def dynamic_frontier(root: Path, count: int):
    prof_path = root / p.PROFESSIONAL_SOURCE_REL
    assurance_path = root / p.CURRENT_ASSURANCE_REL
    prof_path.parent.mkdir(parents=True, exist_ok=True)
    prof_path.write_text(json.dumps(professional_state(count)), encoding="utf-8")
    assurance_path.write_text(json.dumps(assurance_state(count)), encoding="utf-8")
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


class ParallelFrontierV2Tests(unittest.TestCase):
    def test_stale_frontier_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, source = frontier(root, [candidate("A")])
            source.write_text('{"changed": true}\n', encoding="utf-8")
            with self.assertRaisesRegex(p.ParallelFrontierError, "LIVE_WORK_FRONTIER_STALE"):
                p.plan_parallel_frontier(f, root=root)

    def test_unknown_vectors_parallelize_read_only_evidence_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(root, [candidate("A"), candidate("B")])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["parallel_read_only_evidence_work_ids"], ["A", "B"])
            self.assertEqual(out["parallel_full_execution_work_ids"], [])

    def test_incomplete_mutating_work_fails_closed_from_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(root, [candidate("A", read_only=False)])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["parallel_full_execution_work_ids"], [])
            self.assertEqual(out["mutating_incomplete_vector_work_ids"], ["A"])

    def test_exact_separated_intervals_prove_dominance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefit_overrides={
                    "expected_capability_gain_lcb": 2,
                    "expected_capability_gain_ucb": 2,
                },
                cost_overrides={
                    "wall_clock_cost_lcb": 1,
                    "wall_clock_cost_ub": 1,
                },
            )
            b = candidate(
                "B",
                complete=True,
                benefit_overrides={
                    "expected_capability_gain_lcb": 1,
                    "expected_capability_gain_ucb": 1,
                },
                cost_overrides={
                    "wall_clock_cost_lcb": 2,
                    "wall_clock_cost_ub": 2,
                },
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["dominated_by"], {"B": ["A"]})
            self.assertEqual(out["parallel_full_execution_work_ids"], ["A"])

    def test_overlapping_benefit_intervals_do_not_fake_dominance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefit_overrides={
                    "expected_capability_gain_lcb": 2,
                    "expected_capability_gain_ucb": 3,
                },
            )
            b = candidate(
                "B",
                complete=True,
                benefit_overrides={
                    "expected_capability_gain_lcb": 1,
                    "expected_capability_gain_ucb": 4,
                },
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["dominated_by"], {})
            self.assertEqual(out["parallel_full_execution_work_ids"], ["A", "B"])

    def test_overlapping_cost_intervals_do_not_fake_dominance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                cost_overrides={"wall_clock_cost_lcb": 1, "wall_clock_cost_ub": 3},
            )
            b = candidate(
                "B",
                complete=True,
                cost_overrides={"wall_clock_cost_lcb": 2, "wall_clock_cost_ub": 4},
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["dominated_by"], {})

    def test_inverted_benefit_interval_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefit_overrides={
                    "expected_capability_gain_lcb": 3,
                    "expected_capability_gain_ucb": 2,
                },
            )
            f, _ = frontier(root, [a])
            with self.assertRaisesRegex(p.ParallelFrontierError, "BENEFIT_INTERVAL_INVERTED"):
                p.plan_parallel_frontier(f, root=root)

    def test_inverted_cost_interval_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                cost_overrides={"wall_clock_cost_lcb": 4, "wall_clock_cost_ub": 3},
            )
            f, _ = frontier(root, [a])
            with self.assertRaisesRegex(p.ParallelFrontierError, "COST_INTERVAL_INVERTED"):
                p.plan_parallel_frontier(f, root=root)

    def test_success_probability_ucb_over_one_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                benefit_overrides={
                    "success_probability_lcb": 1,
                    "success_probability_ucb": "3/2",
                },
            )
            f, _ = frontier(root, [a])
            with self.assertRaisesRegex(p.ParallelFrontierError, "SUCCESS_PROBABILITY_BOUND_GT_ONE"):
                p.plan_parallel_frontier(f, root=root)

    def test_conflicting_incomparable_complete_work_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = candidate(
                "A",
                complete=True,
                mutation_keys=["shared"],
                benefit_overrides={
                    "expected_capability_gain_lcb": 2,
                    "expected_capability_gain_ucb": 3,
                },
            )
            b = candidate(
                "B",
                complete=True,
                mutation_keys=["shared"],
                benefit_overrides={
                    "expected_efficiency_gain_lcb": 2,
                    "expected_efficiency_gain_ucb": 3,
                },
            )
            f, _ = frontier(root, [a, b])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["parallel_full_execution_work_ids"], [])
            self.assertEqual(out["unresolved_full_execution_conflict_components"], [["A", "B"]])

    def test_dynamic_professional_and_assurance_follow_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, prof_path, assurance_path = dynamic_frontier(root, 9)
            prof_path.write_text(json.dumps(professional_state(10)), encoding="utf-8")
            assurance_path.write_text(json.dumps(assurance_state(10)), encoding="utf-8")
            out = p.refresh_supported_dynamic_sources(f, root=root)
            self.assertEqual(
                out["candidates"][0]["work_id"],
                "PROFESSIONAL_QUALITY_V7_R11_ADAPTIVE_INTEGRITY_SECURITY_BINDING",
            )
            self.assertEqual(out["dynamic_currentness"]["assurance_professional_count"], 10)

    def test_sleeping_work_is_nonprimary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f, _ = frontier(root, [candidate("A"), candidate("S", state="SLEEPING")])
            out = p.plan_parallel_frontier(f, root=root)
            self.assertEqual(out["ready_candidate_ids"], ["A"])
            self.assertEqual(out["nonprimary_candidate_ids"], ["S"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
