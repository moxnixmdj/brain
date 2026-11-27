import hashlib
import json
import unittest

from canonical.runtime.aa_briefcase_authority_convention_sweep_v1 import (
    REVIEW_SCHEMA,
    discover_candidates,
    verify_review,
)
from canonical.runtime.aa_briefcase_pre_generation_contract_v1 import (
    MANIFEST_SCHEMA,
    PreGenerationError,
    verify_pre_generation_contract,
)


def ingress():
    return {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_LOSSLESS_TASK_INGRESS_V1",
        "ingress_sha256": "i" * 64,
        "deliverables": ["market_model.xlsx"],
        "obligations": [
            {"obligation_id": "o1"},
            {"obligation_id": "o2"},
        ],
        "source_files": [
            {"path": "shared/standards.docx", "sha256": "a" * 64, "size_bytes": 1},
            {"path": "week/input.xlsx", "sha256": "b" * 64, "size_bytes": 1},
        ],
        "all_nonempty_context_and_task_lines_preserved_exactly": True,
        "all_declared_source_files_preserved_by_path_hash_and_size": True,
    }


def parse_manifest():
    return {
        "status": "PASS__ALL_DECLARED_SOURCES_PARSED",
        "ingress_sha256": "i" * 64,
        "parse_manifest_sha256": "p" * 64,
        "unsupported_or_unparsed_source_count": 0,
        "receipts": [
            {
                "source_path": "shared/standards.docx",
                "source_sha256": "a" * 64,
                "parsed_representation_sha256": "1" * 64,
                "parsed": {"format": "docx", "text": "Firm standard: all outputs must use USD."},
            },
            {
                "source_path": "week/input.xlsx",
                "source_sha256": "b" * 64,
                "parsed_representation_sha256": "2" * 64,
                "parsed": {"format": "xlsx", "text": "Build downside and upside scenario and reconcile top-down to bottom-up."},
            },
        ],
    }


def sweep_and_review():
    sweep = discover_candidates(parse_manifest())
    rows = []
    for c in sweep["candidates"]:
        classes = set(c["classes"])
        if "PROFESSIONAL_CONVENTION" in classes or "ASSUMPTION_CONTROL" in classes:
            action, targets = "CONVENTION", ["currency"]
        elif "SCENARIO_STRUCTURE" in classes:
            action, targets = "SCENARIO_STRUCTURE", ["transition"]
        elif "RECONCILIATION_STRUCTURE" in classes:
            action, targets = "RECONCILIATION_STRUCTURE", ["market_size"]
        elif c["high_signal"]:
            action, targets = "AUTHORITY", [c["source_path"]]
        else:
            action, targets = "DIMENSION", ["pricing"]
        rows.append({"candidate_id": c["candidate_id"], "action": action, "target_ids": targets})
    review = {"schema": REVIEW_SCHEMA, "sweep_sha256": sweep["sweep_sha256"], "rows": rows}
    verdict = verify_review(sweep, review)
    assert verdict["pass"], verdict
    return sweep, review, verdict


def scenario(sid):
    return {
        "id": sid,
        "given": ["bound evidence"],
        "when": ["requirement is realized"],
        "then": ["observable output contains required structure"],
    }


def contract():
    sweep, review, verdict = sweep_and_review()
    value_sha = hashlib.sha256(b"USD").hexdigest()
    c = {
        "schema": MANIFEST_SCHEMA,
        "ingress_sha256": "i" * 64,
        "parse_manifest_sha256": "p" * 64,
        "review_verdict_sha256": verdict["review_verdict_sha256"],
        "authority_sources": [
            {
                "source_path": "shared/standards.docx",
                "authority_rank": 0,
                "content_sha256": "a" * 64,
                "parsed_representation_sha256": "1" * 64,
                "supersedes": [],
            },
            {
                "source_path": "week/input.xlsx",
                "authority_rank": 1,
                "content_sha256": "b" * 64,
                "parsed_representation_sha256": "2" * 64,
                "supersedes": [],
            },
        ],
        "required_dimension_ids": ["pricing", "market_size"],
        "dimensions": [
            {
                "dimension_id": "pricing",
                "requirement_ids": ["r1"],
                "source_paths": ["week/input.xlsx"],
                "task_obligation_ids": ["o1"],
                "coverage_receipt": "d1",
            },
            {
                "dimension_id": "market_size",
                "requirement_ids": ["r2"],
                "source_paths": ["week/input.xlsx"],
                "task_obligation_ids": ["o2"],
                "coverage_receipt": "d2",
            },
        ],
        "required_convention_ids": ["currency"],
        "conventions": [
            {
                "convention_id": "currency",
                "candidates": [
                    {
                        "source_path": "shared/standards.docx",
                        "authority_rank": 0,
                        "value_sha256": value_sha,
                    }
                ],
                "effective_source_path": "shared/standards.docx",
                "binding_receipt": "c1",
            }
        ],
        "scenario_axes": [
            {
                "axis_id": "transition",
                "states": ["downside", "upside"],
                "requirement_ids": ["r1"],
                "output_ids": ["out"],
                "source_paths": ["week/input.xlsx"],
                "task_obligation_ids": ["o1"],
            }
        ],
        "reconciliations": [
            {
                "reconciliation_id": "market_size",
                "method_ids": ["top_down", "bottom_up"],
                "requirement_ids": ["r2"],
                "output_id": "out",
                "source_paths": ["week/input.xlsx"],
                "task_obligation_ids": ["o2"],
            }
        ],
        "requirements": [
            {
                "id": "r1",
                "kind": "SCENARIO",
                "critical": True,
                "task_obligation_ids": ["o1"],
                "source_paths": ["shared/standards.docx", "week/input.xlsx"],
                "dimension_ids": ["pricing"],
                "convention_ids": ["currency"],
                "output_ids": ["out"],
                "scenario_axis_ids": ["transition"],
                "reconciliation_ids": [],
                "dependencies": [],
                "children": [],
                "open_questions": [],
                "clauses": [],
                "scenarios": [scenario("r1-s1")],
            },
            {
                "id": "r2",
                "kind": "RECONCILIATION",
                "critical": True,
                "task_obligation_ids": ["o2"],
                "source_paths": ["week/input.xlsx"],
                "dimension_ids": ["market_size"],
                "convention_ids": [],
                "output_ids": ["out"],
                "scenario_axis_ids": [],
                "reconciliation_ids": ["market_size"],
                "dependencies": [],
                "children": [],
                "open_questions": [],
                "clauses": [],
                "scenarios": [scenario("r2-s1")],
            },
        ],
        "outputs": [
            {
                "output_id": "out",
                "deliverable_path": "market_model.xlsx",
                "requirement_ids": ["r1", "r2"],
            }
        ],
    }
    return sweep, review, c


class T(unittest.TestCase):
    def test_complete_contract_passes(self):
        sweep, review, c = contract()
        out = verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)
        self.assertTrue(out["pre_generation_structural_authority"])
        self.assertTrue(out["all_explicit_task_obligations_reach_requirement_graph"])
        self.assertTrue(out["all_declared_sources_parsed_and_structurally_bound"])
        self.assertFalse(out["semantic_completeness_self_certified"])

    def test_missing_task_obligation_blocks(self):
        sweep, review, c = contract()
        c["requirements"][1]["task_obligation_ids"] = []
        with self.assertRaisesRegex(PreGenerationError, "TASK_OBLIGATION_COVERAGE_MISMATCH"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_missing_dimension_blocks(self):
        sweep, review, c = contract()
        c["dimensions"] = c["dimensions"][:1]
        with self.assertRaisesRegex(PreGenerationError, "DIMENSION_SET_MISMATCH"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_missing_convention_blocks(self):
        sweep, review, c = contract()
        c["conventions"] = []
        with self.assertRaisesRegex(PreGenerationError, "CONVENTION_SET_MISMATCH"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_authority_conflict_blocks(self):
        sweep, review, c = contract()
        c["conventions"][0]["candidates"].append({
            "source_path": "week/input.xlsx",
            "authority_rank": 0,
            "value_sha256": hashlib.sha256(b"NZD").hexdigest(),
        })
        c["authority_sources"][1]["authority_rank"] = 0
        with self.assertRaisesRegex(PreGenerationError, "CONVENTION_AUTHORITY_CONFLICT"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_single_state_scenario_blocks(self):
        sweep, review, c = contract()
        c["scenario_axes"][0]["states"] = ["base"]
        with self.assertRaisesRegex(PreGenerationError, "SCENARIO_AXIS_REQUIRES_AT_LEAST_TWO_STATES"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_single_method_reconciliation_blocks(self):
        sweep, review, c = contract()
        c["reconciliations"][0]["method_ids"] = ["top_down"]
        with self.assertRaisesRegex(PreGenerationError, "RECONCILIATION_REQUIRES_AT_LEAST_TWO_METHODS"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_output_requirement_inverse_mismatch_blocks(self):
        sweep, review, c = contract()
        c["outputs"][0]["requirement_ids"] = ["r1"]
        with self.assertRaisesRegex(PreGenerationError, "OUTPUT_REQUIREMENT_INVERSE_MISMATCH"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)

    def test_unbound_source_blocks(self):
        sweep, review, c = contract()
        for req in c["requirements"]:
            req["source_paths"] = [p for p in req["source_paths"] if p != "shared/standards.docx"]
        c["conventions"][0]["candidates"] = [{
            "source_path": "week/input.xlsx",
            "authority_rank": 1,
            "value_sha256": hashlib.sha256(b"USD").hexdigest(),
        }]
        c["conventions"][0]["effective_source_path"] = "week/input.xlsx"
        with self.assertRaisesRegex(PreGenerationError, "DECLARED_SOURCE_NOT_SEMANTICALLY_BOUND"):
            verify_pre_generation_contract(ingress(), parse_manifest(), sweep, review, c)
