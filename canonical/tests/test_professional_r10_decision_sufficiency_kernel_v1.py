from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r10_decision_sufficiency_kernel_v1 as k

ROOT=Path(__file__).resolve().parents[2]
LEGACY=ROOT/"canonical/runtime/one_shot_reality_closure_v2.py"
KEEP={"_canon","_sha","_s","compile_decision_sufficient_contract","compile_minimum_information_contract"}
CONSTANTS={"DECISION_SUFFICIENT_SCHEMA","MINIMUM_INFORMATION_SCHEMA"}


def legacy_namespace():
    tree=ast.parse(LEGACY.read_text(encoding="utf-8"))
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.Assign):
            names={x.id for x in node.targets if isinstance(x,ast.Name)}
            if names & CONSTANTS:
                nodes.append(node)
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in KEEP:
            nodes.append(node)
    prelude=ast.parse(
        "from copy import deepcopy\n"
        "from hashlib import sha256\n"
        "import json\n"
        "from typing import Any, Mapping, Sequence\n"
    ).body
    mod=ast.Module(body=prelude+nodes,type_ignores=[])
    ast.fix_missing_locations(mod)
    ns={}
    exec(compile(mod,str(LEGACY),"exec"),ns,ns)
    return ns


def sample_gap():
    return {
        "schema":"PROJECT_BRAIN_PROOF_CARRYING_GAP_CONTRACT_V1",
        "gap_class":"PENDING_ACQUISITION_OR_EXPERIMENT",
        "required_action":"SEARCH_SIMULATE_EXPERIMENT_OR_ACQUIRE_MINIMUM_NEEDED_EVIDENCE",
        "basis_digest":"1"*64,
        "pending_semantic_work_digest":"2"*64,
        "basis":{
            "constructive_internal_blockers":["ROOT1_GAP"],
            "evidence_blockers":[
                "MISSING_FACT",
                "MISSING_FACT",
                "R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",
            ],
            "r2_acquisition_requests":[{
                "cell_id":"FINANCE_SEMANTIC_ADEQUACY_TAIL",
                "request_sha256":"8"*64,
                "source_r2_authority_sha256":"9"*64,
                "required_action":"ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
                "remaining_boundary":"UNBOUND_SEMANTIC_MANIFEST_OR_EVIDENCE",
                "wake_conditions":["WAKE_A","WAKE_B"],
            }],
        },
        "constructive_capability_contracts":[{
            "contract_id":"constructive:test",
            "basis":{
                "required_result":"PASS",
                "repair_class":"TEST_REPAIR",
                "acceptance_condition":"UNCHANGED_VERIFIER_PASS",
                "verification_authority_sha256":"a"*64,
            },
        }],
    }


class ProfessionalR10DecisionSufficiencyKernelV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy=legacy_namespace()

    def test_decision_contract_exactly_matches_legacy(self):
        gap=sample_gap()
        self.assertEqual(
            k.compile_decision_sufficient_contract(gap),
            self.legacy["compile_decision_sufficient_contract"](gap),
        )

    def test_minimum_information_contract_exactly_matches_legacy(self):
        gap=sample_gap()
        kd=k.compile_decision_sufficient_contract(gap)
        ld=self.legacy["compile_decision_sufficient_contract"](gap)
        self.assertEqual(
            k.compile_minimum_information_contract(gap,kd),
            self.legacy["compile_minimum_information_contract"](gap,ld),
        )

    def test_lossless_identity_and_no_omission(self):
        out=k.compile_decision_sufficient_contract(sample_gap())
        self.assertTrue(out["pass"])
        self.assertEqual(out["reduction_mode"],"LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION")
        self.assertEqual(out["omitted_evidence"],[])
        self.assertFalse(out["verification_authority_mutation_allowed"])
        self.assertFalse(out["terminal_credit"])

    def test_minimum_information_deduplicates_generic_blockers(self):
        gap=sample_gap()
        decision=k.compile_decision_sufficient_contract(gap)
        out=k.compile_minimum_information_contract(gap,decision)
        self.assertEqual(out["structured_r2_request_count"],1)
        kinds=[x["kind"] for x in out["requests"]]
        self.assertEqual(kinds.count("R2_STRUCTURED_POLICY_CHANGING_ACQUISITION"),1)
        self.assertEqual(kinds.count("GENERIC_EVIDENCE_BLOCKER"),1)
        self.assertEqual(out["proof_precedence"][-1],"FULL_EMPIRICAL_EVALUATION_LAST")

    def test_structured_request_preserves_wake_conditions(self):
        gap=sample_gap()
        decision=k.compile_decision_sufficient_contract(gap)
        out=k.compile_minimum_information_contract(gap,decision)
        row=next(x for x in out["requests"] if x["kind"]=="R2_STRUCTURED_POLICY_CHANGING_ACQUISITION")
        self.assertEqual(row["r2_cell_id"],"FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertEqual(row["wake_conditions"],["WAKE_A","WAKE_B"])
        self.assertFalse(row["full_benchmark_default"])


if __name__=="__main__":
    unittest.main(verbosity=2)
