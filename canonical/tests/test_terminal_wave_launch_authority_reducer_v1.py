from __future__ import annotations
import unittest
from canonical.runtime.terminal_wave_launch_authority_reducer_v1 import evaluate_documents


class TerminalWaveLaunchAuthorityReducerTests(unittest.TestCase):
    def _fixture(self):
        routes=[]; contracts=[]; receipts={}; blobs={}
        for i in range(12):
            bid=f"B{i}"
            ex=f"runtime/e{i}.py"; te=f"tests/t{i}.py"; es=f"e{i:02d}"; ts=f"t{i:02d}"; rp=f"verify/r{i}.json"
            routes.append({
                "behavior_id":bid,
                "executor_status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
                "executor":ex,"tests":te,
                "executor_blob_sha":es,"executor_test_blob_sha":ts,
                "independent_executor_verification":rp,
                "terminal_result_status":"NOT_EXECUTED",
            })
            contracts.append({"behavior_id":bid,"proof_state":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE","blockers":[]})
            receipts[rp]={
                "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS",
                "exact_brain_blobs":{ex:es,te:ts},
                "terminal_results_observed":0,
                "fresh_terminal_evidence_consumed":0,
            }
            blobs[ex]=es; blobs[te]=ts
        pre={"pass":True,"execution_authority":True}
        parent_producers={"portfolios":{}}
        for portfolio in ("T0","T1","T2","T3"):
            producer=f"runtime/parent_{portfolio}.py"
            producer_test=f"tests/parent_{portfolio}.py"
            producer_sha=f"parent-{portfolio}-sha"
            producer_test_sha=f"parent-{portfolio}-test-sha"
            receipt=f"verify/parent_{portfolio}.json"
            parent_producers["portfolios"][portfolio]={
                "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
                "producer":producer,
                "tests":producer_test,
                "producer_blob_sha":producer_sha,
                "test_blob_sha":producer_test_sha,
                "independent_verification":receipt,
                "real_parent_case_producer":True,
                "post_freeze_selection_only":True,
                "same_case_instrumentation":True,
                "hidden_oracle_isolated":True,
                "parent_terminal_acceptance_derived":True,
                "direct_instrumentation_verdict_derived":True,
                "no_stub_receipts":True,
            }
            receipts[receipt]={
                "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS",
                "exact_brain_blobs":{producer:producer_sha,producer_test:producer_test_sha},
                "verified":[
                    "REAL_PARENT_CASE_PRODUCER",
                    "POST_FREEZE_SELECTION_ONLY",
                    "SAME_CASE_INSTRUMENTATION",
                    "PARENT_TERMINAL_ACCEPTANCE_DERIVED",
                    "DIRECT_INSTRUMENTATION_VERDICT_DERIVED",
                    "NO_STUB_RECEIPTS",
                    "ZERO_TERMINAL_CASES_CONSUMED",
                ],
                "terminal_results_observed":0,
                "fresh_terminal_evidence_consumed":0,
            }
            blobs[producer]=producer_sha
            blobs[producer_test]=producer_test_sha
        manifest={
            "route_count":12,"implemented_executor_count":12,"bound_executor_count":12,
            "routes":routes,"launch_authority":False,
            "terminal_results_observed":0,"fresh_terminal_evidence_consumed":0,
        }
        basis={"contracts":contracts}
        return pre,manifest,basis,parent_producers,receipts,blobs

    def _eval(self, pre, manifest, basis, parent_producers, receipts, blobs):
        return evaluate_documents(
            pre,manifest,basis,parent_producers,
            load_verification=lambda p: receipts[p],
            blob_sha=lambda p: blobs.get(p),
        )

    def test_complete_current_state_authorizes(self):
        args=self._fixture()
        out=self._eval(*args)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["launch_authority"])
        self.assertEqual(out["route_count"],12)

    def test_writable_launch_flag_is_not_required(self):
        args=list(self._fixture())
        args[1]["launch_authority"]=False
        out=self._eval(*args)
        self.assertTrue(out["pass"],out)

    def test_one_stale_executor_fails_closed(self):
        pre,manifest,basis,parent_producers,receipts,blobs=self._fixture()
        manifest["routes"][3]["executor_blob_sha"]="new"
        out=self._eval(pre,manifest,basis,parent_producers,receipts,blobs)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTOR_BLOB_DRIFT:B3",out["failed_predicates"])

    def test_missing_independent_receipt_fails_closed(self):
        pre,manifest,basis,parent_producers,receipts,blobs=self._fixture()
        manifest["routes"][2]["independent_executor_verification"]=None
        out=self._eval(pre,manifest,basis,parent_producers,receipts,blobs)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTOR_INDEPENDENT_RECEIPT_MISSING:B2",out["failed_predicates"])

    def test_missing_real_parent_producer_fails_closed(self):
        pre,manifest,basis,parent_producers,receipts,blobs=self._fixture()
        parent_producers["portfolios"]["T2"]["producer"]=None
        out=self._eval(pre,manifest,basis,parent_producers,receipts,blobs)
        self.assertFalse(out["pass"])
        self.assertIn("PARENT_PRODUCER_BINDING_FIELDS_MISSING:T2",out["failed_predicates"])

    def test_stub_parent_producer_semantics_fail_closed(self):
        pre,manifest,basis,parent_producers,receipts,blobs=self._fixture()
        parent_producers["portfolios"]["T1"]["no_stub_receipts"]=False
        out=self._eval(pre,manifest,basis,parent_producers,receipts,blobs)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PARENT_PRODUCER_SEMANTIC_FLAG_MISSING:T1:no_stub_receipts",
            out["failed_predicates"],
        )

    def test_prequalification_failure_fails_closed(self):
        pre,manifest,basis,parent_producers,receipts,blobs=self._fixture()
        pre["pass"]=False; pre["execution_authority"]=False
        out=self._eval(pre,manifest,basis,parent_producers,receipts,blobs)
        self.assertFalse(out["pass"])
        self.assertIn("PREQUALIFICATION_NOT_AUTHORIZED",out["failed_predicates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
