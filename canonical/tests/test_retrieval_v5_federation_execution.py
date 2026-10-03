from __future__ import annotations

import copy
import unittest

from canonical.runtime import public_source_federation_v2 as federation
from canonical.runtime import public_source_federation_executor_v2 as executor


def queries():
    return [
        {"text": "valid_route_top1", "basis": "OBSERVABLE_API_SYMBOLS"},
        {"text": "工具发现 Toolathlon", "basis": "MULTILINGUAL_BRIDGE_VARIANT"},
        {"text": "اكتشاف الأدوات Toolathlon", "basis": "MULTILINGUAL_BRIDGE_VARIANT"},
        {"text": "обнаружение инструментов Toolathlon", "basis": "MULTILINGUAL_BRIDGE_VARIANT"},
    ]


def fake_success(query, limit=8, timeout=15, query_override=None):
    q=query_override or query
    domain=q.split()[0].removeprefix("site:")
    return {
        "status":"CANDIDATES_DISCOVERED",
        "candidates":[
            {"url":f"https://{domain}/candidate","title":"candidate"},
            {"url":"https://wrong.example/off-domain","title":"wrong"},
        ],
        "retrieval_provenance":[{"backend":"FAKE","candidate_count":2}],
        "backend_errors":[],
    }


class RetrievalV5FederationExecutionTests(unittest.TestCase):
    def fed(self, per_source=1):
        return federation.compile_federation(queries(),max_queries_per_source=per_source)

    def test_partial_batch_cannot_consume_epoch(self):
        fed=self.fed(1)
        out=executor.execute(fed,max_requests=3,discover_fn=fake_success)
        self.assertFalse(out["epoch_consumption_authorized"],out)
        self.assertEqual(len(out["remaining_request_ids"]),fed["request_count"]-3,out)
        self.assertEqual(len(out["consumed_request_ids_after"]),3,out)

    def test_all_successfully_executed_cells_can_consume_epoch_but_not_prove_nonexistence(self):
        fed=self.fed(1)
        out=executor.execute(fed,max_requests=64,discover_fn=fake_success)
        self.assertTrue(out["epoch_consumption_authorized"],out)
        self.assertEqual(out["remaining_request_ids"],[],out)
        self.assertFalse(out["nonexistence_claim_authorized"],out)
        self.assertFalse(out["complete"],out)
        self.assertEqual(out["candidate_count"],14,out)

    def test_retryable_failure_remains_unconsumed_and_blocks_epoch(self):
        fed=self.fed(1)
        target=fed["requests"][0]["domain"]
        def flaky(query,limit=8,timeout=15,query_override=None):
            q=query_override or query
            if f"site:{target}" in q:
                raise RuntimeError("temporary outage")
            return fake_success(query,limit,timeout,query_override)
        out=executor.execute(fed,max_requests=64,discover_fn=flaky)
        self.assertFalse(out["epoch_consumption_authorized"],out)
        self.assertEqual(len(out["failed_retryable_request_ids"]),1,out)
        self.assertIn(fed["requests"][0]["request_id"],out["remaining_request_ids"],out)
        cell=next(x for x in out["cells"] if x["request_id"]==fed["requests"][0]["request_id"])
        self.assertFalse(cell["consumed"])
        self.assertTrue(cell["retryable"])

    def test_off_domain_candidates_are_filtered(self):
        fed=self.fed(1)
        out=executor.execute(fed,max_requests=1,discover_fn=fake_success)
        self.assertEqual(out["candidate_count"],1,out)
        self.assertEqual(out["candidates"][0]["federation_domain"],fed["requests"][0]["domain"])

    def test_consumed_cells_are_skipped_without_replay(self):
        fed=self.fed(1)
        first=executor.execute(fed,max_requests=2,discover_fn=fake_success)
        second=executor.execute(
            fed,
            consumed_request_ids=first["consumed_request_ids_after"],
            max_requests=2,
            discover_fn=fake_success,
        )
        self.assertGreaterEqual(second["skipped_consumed_request_count"],2,second)
        self.assertTrue(
            set(first["newly_consumed_request_ids"]).isdisjoint(second["newly_consumed_request_ids"]),
            second,
        )

    def test_request_id_tamper_fails_before_execution(self):
        fed=self.fed(1)
        bad=copy.deepcopy(fed)
        bad["requests"][0]["request_id"]="0"*24
        with self.assertRaises(executor.FederationExecutionError):
            executor.execute(bad,discover_fn=fake_success)

    def test_candidate_self_promotion_is_retryable_failure_not_consumption(self):
        fed=self.fed(1)
        fed["requests"]=fed["requests"][:1]
        def bad(query,limit=8,timeout=15,query_override=None):
            domain=(query_override or query).split()[0].removeprefix("site:")
            return {
                "status":"CANDIDATES_DISCOVERED",
                "candidates":[{"url":f"https://{domain}/x","verified_sufficient":True}],
                "retrieval_provenance":[{"backend":"BAD"}],
                "backend_errors":[],
            }
        out=executor.execute(fed,discover_fn=bad)
        self.assertFalse(out["epoch_consumption_authorized"],out)
        self.assertEqual(out["newly_consumed_request_ids"],[],out)
        self.assertEqual(len(out["failed_retryable_request_ids"]),1,out)
        self.assertEqual(out["acceptance_credit"],0)

    def test_epoch_receipt_is_deterministic(self):
        fed=self.fed(1)
        a=executor.execute(fed,max_requests=5,discover_fn=fake_success)
        b=executor.execute(copy.deepcopy(fed),max_requests=5,discover_fn=fake_success)
        self.assertEqual(a["source_epoch_sha256"],b["source_epoch_sha256"])


if __name__=="__main__":
    unittest.main(verbosity=2)
