import hashlib
import importlib
import sys
import types
import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import (
    checked_predicate_id,
    evaluate as evaluate_domain_truth,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
)


RAW = "loss-absorbing cushion"
SOURCE = "doc:A"
SCOPE = "finance:regulatory-capital:2026"
TARGET = "CCOB"
RELATION = "LEFT_ENTAILS_RIGHT"


def mention_id():
    return "MENTION:" + hashlib.sha256(
        (SOURCE + "\n" + SCOPE + "\n" + RAW).encode("utf-8")
    ).hexdigest()


def edge_receipt():
    return {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "scope_id": SCOPE,
        "source_id": mention_id(),
        "target_id": TARGET,
        "relation": "ENTAILS",
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
    }


def relation_problem():
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": SCOPE,
        "left_id": mention_id(),
        "right_id": TARGET,
        "entailment_receipts": [edge_receipt()],
        "counterexample_receipts": [],
    }
    return {
        "required_relation": RELATION,
        "entailment_dag_evidence": evidence,
        "expected_entailment_dag_sha256": evidence_sha256(evidence),
    }


def truth_payload():
    atom = checked_predicate_id(
        source_id=SOURCE,
        raw_span=RAW,
        scope_id=SCOPE,
        target_concept_id=TARGET,
        required_relation=RELATION,
    )
    return atom, {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": atom,
        "raw_span": RAW,
        "source_id": SOURCE,
        "scope_id": SCOPE,
        "target_concept_id": TARGET,
        "required_relation": RELATION,
        "candidate_concepts": [{
            "concept_id": TARGET,
            "surface": "capital conservation buffer",
            "required_atoms": [],
            "forbidden_atoms": [],
        }],
        "relation_problems": {
            TARGET: relation_problem(),
        },
    }


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
            "discriminator_id": "domain-map-edge-disc",
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
    def test_domain_truth_stays_unknown_without_edge_verifier(self):
        _atom, payload = truth_payload()
        out = evaluate_domain_truth(payload)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNKNOWN__DOMAIN_MAPPING_RELATION_NOT_PROVED",
        )

    def test_domain_truth_uses_injected_edge_verifier(self):
        _atom, payload = truth_payload()
        out = evaluate_domain_truth(
            payload,
            relation_edge_verifier=lambda value: value,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(
            out["mapping_result"]["verified_mapping"]["relation"],
            RELATION,
        )
        self.assertFalse(out["terminal_authority"])

    def test_injected_edge_verifier_reaches_p3_cegar_truth_refinement(self):
        atom, truth = truth_payload()
        payload = {
            "context_id": "ctx-domain-map-edge",
            "v3_input": {"task": {"claims": []}},
            "cegar_problem": {"formal_source_constraints": []},
            "truth_payloads_by_discriminator_id": {},
            "truth_payloads_by_predicate_id": {atom: truth},
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
            out = loop.evaluate(
                payload,
                relation_edge_verifier=lambda value: value,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            seen[1]["formal_source_constraints"],
            [{"op": "ATOM", "id": atom}],
        )
        self.assertEqual(out["refinement_steps"], 1)
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
