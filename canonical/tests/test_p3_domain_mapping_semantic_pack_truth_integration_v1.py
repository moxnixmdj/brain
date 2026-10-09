import importlib
from hashlib import sha1
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from canonical.runtime.domain_mapping_truth_certificate_v1 import checked_predicate_id


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = "canonical/evidence/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_20261009_V1.json"
VERIFY_PATH = "canonical/verification/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_VERIFY_20261009_V1.json"
SCOPE = "finance:global-standard-terminology:basel-rbc30-fsb-tlac:2026-10-09"
TARGET = "BASEL::CAPITAL_CONSERVATION_BUFFER"
RAW = (
    "The buffer is 2.5% of RWA, comprised of Common Equity Tier 1 (CET1), "
    "above the regulatory minimum capital requirement, and can be drawn "
    "down as losses are incurred."
)


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


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
            "discriminator_id": "semantic-pack-domain-map-disc",
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
    def test_verified_semantic_pack_refines_p3_without_prebuilt_relation_problem(self):
        atom = checked_predicate_id(
            source_id="case",
            raw_span=RAW,
            scope_id=SCOPE,
            target_concept_id=TARGET,
            required_relation="LEFT_ENTAILS_RIGHT",
        )
        pack = json.loads((ROOT / PACK_PATH).read_text(encoding="utf-8"))
        verify_raw = (ROOT / VERIFY_PATH).read_bytes()

        truth_payload = {
            "truth_kind": "DOMAIN_MAPPING_RELATION",
            "predicate_id": atom,
            "raw_span": RAW,
            "source_id": "case",
            "scope_id": SCOPE,
            "target_concept_id": TARGET,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "candidate_concepts": [
                {
                    "concept_id": TARGET,
                    "surface": "capital conservation buffer",
                    "required_atoms": [],
                    "forbidden_atoms": [],
                },
                {
                    "concept_id": "FSB::TLAC",
                    "surface": "total loss-absorbing capacity",
                    "required_atoms": [],
                    "forbidden_atoms": [],
                },
            ],
            "semantic_pack": pack,
            "semantic_pack_verification_ref": {
                "path": VERIFY_PATH,
                "git_blob_sha": _blob(verify_raw),
            },
        }
        payload = {
            "context_id": "ctx-semantic-pack-domain-map",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
