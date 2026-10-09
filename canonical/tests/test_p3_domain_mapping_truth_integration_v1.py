import importlib
import sys
import types
import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import checked_predicate_id


RAW = "loss-absorbing cushion"
SCOPE = "finance:regulatory-capital:2026"
TARGET = "CCOB"


def _install_import_stubs():
    robust = types.ModuleType(
        "canonical.runtime.p3_robust_policy_adequacy_cegar_v1"
    )
    robust.solve = lambda _problem: None
    sys.modules[robust.__name__] = robust

    selection = types.ModuleType(
        "canonical.runtime.p3_source_positive_selection_cell_v1"
    )
    selection.evaluate = lambda _payload, repo_root=None: None
    sys.modules[selection.__name__] = selection

    legacy = types.ModuleType(
        "canonical.runtime.selected_semantic_truth_certificate_v1"
    )
    legacy.evaluate = lambda _payload: {
        "pass": False,
        "status": "LEGACY_PATH_REJECTED_DOMAIN_MAPPING_PAYLOAD",
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
    }
    sys.modules[legacy.__name__] = legacy


_install_import_stubs()
loop = importlib.import_module(
    "canonical.runtime.p3_bound_relevance_cegar_loop_v1"
)


def selected(atom):
    return {
        "pass": False,
        "status": (
            "UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED"
        ),
        "common_policy_certified": False,
        "selected_discriminator": {
            "discriminator_id": "domain-map-disc",
            "formula": {"op": "ATOM", "id": atom},
            "cost_units": 1.0,
            "branches": [],
        },
    }


def common():
    return {
        "pass": True,
        "status": "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
        "common_policy_certified": True,
        "selected_policy_id": "p",
    }


def realized():
    return {
        "pass": True,
        "status": "PASS__P3_SOURCE_POSITIVE_SELECTION_CELL",
        "selected_policy_id": "p",
        "selected_claim_ids": ["A"],
        "rendered_text": "A",
        "render_trace": [],
    }


class Tests(unittest.TestCase):
    def test_domain_mapping_truth_refines_existing_p3_loop(self):
        atom = checked_predicate_id(
            source_id="doc:A",
            raw_span=RAW,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            required_relation="SEMANTIC_IDENTITY",
        )
        truth_payload = {
            "truth_kind": "DOMAIN_MAPPING_RELATION",
            "predicate_id": atom,
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": TARGET,
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [{
                "concept_id": TARGET,
                "surface": "capital conservation buffer",
                "required_atoms": [],
                "forbidden_atoms": [],
            }],
            "relation_problems": {
                TARGET: {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "explicit_definition_sources": [{
                        "source_id": "doc:A",
                        "scope_id": SCOPE,
                        "source_text": (
                            "Loss-absorbing cushion means capital conservation buffer."
                        ),
                    }],
                }
            },
        }
        payload = {
            "context_id": "ctx-domain-map",
            "v3_input": {"task": {"claims": []}},
            "cegar_problem": {"formal_source_constraints": []},
            "truth_payloads_by_discriminator_id": {},
            "truth_payloads_by_predicate_id": {atom: truth_payload},
            "source_positive_selection_contracts": {
                "p": {"selected_policy_id": "p"}
            },
            "max_refinement_steps": 2,
        }
        seen = []

        def solve(problem):
            seen.append(problem)
            return selected(atom) if len(seen) == 1 else common()

        with patch.object(loop, "solve_cegar", side_effect=solve), patch.object(
            loop, "evaluate_selection", return_value=realized()
        ):
            out = loop.evaluate(payload)

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            seen[1]["formal_source_constraints"],
            [{"op": "ATOM", "id": atom}],
        )
        self.assertEqual(out["refinement_steps"], 1)
        self.assertFalse(out["terminal_authority"])


    def test_unknown_domain_mapping_truth_preserves_proof_request(self):
        atom = checked_predicate_id(
            source_id="doc:A",
            raw_span=RAW,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            required_relation="SEMANTIC_IDENTITY",
        )
        truth_payload = {
            "truth_kind": "DOMAIN_MAPPING_RELATION",
            "predicate_id": atom,
            "raw_span": RAW,
            "source_id": "doc:A",
            "scope_id": SCOPE,
            "target_concept_id": TARGET,
            "required_relation": "SEMANTIC_IDENTITY",
            "candidate_concepts": [{
                "concept_id": TARGET,
                "surface": "capital conservation buffer",
                "required_atoms": [],
                "forbidden_atoms": [],
            }],
            "relation_problems": {
                TARGET: {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "candidate_relations": [{
                        "relation": "SIMILAR",
                        "score": 0.999,
                        "source": "embedding",
                    }],
                }
            },
        }
        payload = {
            "context_id": "ctx-domain-map-open",
            "v3_input": {"task": {"claims": []}},
            "cegar_problem": {"formal_source_constraints": []},
            "truth_payloads_by_discriminator_id": {},
            "truth_payloads_by_predicate_id": {atom: truth_payload},
            "source_positive_selection_contracts": {},
            "max_refinement_steps": 1,
        }
        with patch.object(loop, "solve_cegar", return_value=selected(atom)):
            out = loop.evaluate(payload)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
        )
        requests = out["detail"]["proof_requests"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["truth_kind"], "DOMAIN_MAPPING_RELATION")
        self.assertEqual(requests[0]["target_concept_id"], TARGET)
        self.assertEqual(requests[0]["required_relation"], "SEMANTIC_IDENTITY")
        self.assertFalse(requests[0]["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
