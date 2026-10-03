#!/usr/bin/env python3
from __future__ import annotations
import unittest

from canonical.runtime import residual_witness_backend_router_v1 as router
from canonical.runtime import residual_witness_retrieval_compiler_v1 as core


class ResidualWitnessBackendRouterTests(unittest.TestCase):
    def setUp(self):
        router.clear_external_providers()
        self.residual={
            "residual_id":"R1",
            "effect":"Decode a binary telemetry envelope",
            "required_capabilities":["telemetry.decode"],
            "observables":{"api_symbols":["decode_frame"]},
        }
        self.program=core.compile_residual(self.residual)
        self.state=core.initial_state(self.program)
        self.action={
            "action":"QUERY",
            "query_id":"Q000",
            "query":self.program["query_lattice"][0]["text"],
            "basis":self.program["query_lattice"][0]["basis"],
            "language_hint":self.program["query_lattice"][0]["language_hint"],
            "surface":"CODE_CONTENT",
        }

    def test_candidate_backend_never_closes_acceptance(self):
        out=router.execute_action(
            self.program,self.state,self.action,
            lambda action:{
                "backend_id":"FAKE",
                "candidates":[{"repository":"example/repo","path":"codec.py"}],
                "complete":False,
            },
        )
        self.assertEqual(out["status"],"BACKEND_EXECUTED",out)
        self.assertEqual(out["result"]["candidate_count"],1,out)
        self.assertEqual(out["result"]["candidates"][0]["sufficiency_status"],"UNVERIFIED",out)
        self.assertFalse(out["terminal"]["stop"],out)

    def test_no_result_without_complete_receipt_remains_unknown(self):
        out=router.execute_action(
            self.program,self.state,self.action,
            lambda action:{
                "backend_id":"FAKE",
                "candidates":[],
                "complete":True,
                "independently_complete":False,
            },
        )
        self.assertFalse(out["result"]["completeness_admitted"],out)
        self.assertEqual(out["terminal"]["status"],"UNKNOWN_CONTINUE_RETRIEVAL",out)

    def test_independently_complete_empty_cell_is_admitted(self):
        out=router.execute_action(
            self.program,self.state,self.action,
            lambda action:{
                "backend_id":"FROZEN",
                "candidates":[],
                "complete":True,
                "independently_complete":True,
                "completeness_receipt":"receipt://frozen/code/Q000",
            },
        )
        cell=[
            x for x in out["state"]["cells"]
            if x["query_id"]=="Q000" and x["surface"]=="CODE_CONTENT"
        ][0]
        self.assertEqual(cell["state"],"EXHAUSTIVELY_CLOSED",out)
        self.assertTrue(cell["independently_complete"],out)

    def test_backend_cannot_self_verify_candidate(self):
        out=router.execute_action(
            self.program,self.state,self.action,
            lambda action:{
                "backend_id":"BAD",
                "candidates":[{"repository":"x/y","verified_sufficient":True}],
            },
        )
        self.assertEqual(out["status"],"BACKEND_FAILED_TRANSIENT",out)
        self.assertIn("BACKEND_CANDIDATE_SELF_VERIFICATION",out["error"],out)
        self.assertEqual(
            [x for x in out["state"]["cells"] if x["query_id"]=="Q000" and x["surface"]=="CODE_CONTENT"][0]["state"],
            "FAILED_TRANSIENT",
        )

    def test_unbound_backend_fails_closed_and_moves_on(self):
        # Drive the compiler until it asks for an unbound surface, then verify
        # the router records unbound instead of inventing a negative result.
        state=self.state
        seen=0
        while seen<200:
            action=core.next_action(self.program,state)
            self.assertEqual(action["action"],"QUERY",action)
            if action["surface"] not in router.default_providers():
                out=router.execute_next(self.program,state,providers={})
                self.assertEqual(out["status"],"BACKEND_UNBOUND",out)
                cell=[
                    x for x in out["state"]["cells"]
                    if x["query_id"]==action["query_id"] and x["surface"]==action["surface"]
                ][0]
                self.assertEqual(cell["state"],"FAILED_PERMANENT",out)
                self.assertFalse(out["terminal"]["stop"],out)
                return
            state=core.update_cell(
                state,
                query_id=action["query_id"],
                surface=action["surface"],
                cell_state="QUERIED_NO_CANDIDATE",
            )
            seen+=1
        self.fail("NO_UNBOUND_SURFACE_REACHED")

    def test_only_independent_receipt_can_add_witness(self):
        state=router.accept_independent_witness(
            self.state,
            witness_id="repo@sha",
            residual_id="R1",
            source_surface="CODE_CONTENT",
            independent_receipt="receipt://independent/pass",
        )
        terminal=core.terminal_status(state)
        self.assertTrue(terminal["stop"],terminal)
        self.assertEqual(terminal["status"],"VERIFIED_WITNESS_FOUND",terminal)

    def test_builtin_zero_cost_routes_are_bound(self):
        bound=set(router.default_providers())
        self.assertTrue({"PACKAGE_REGISTRY","OPEN_WEB","DOCUMENTATION","SCHOLARLY"}.issubset(bound))


if __name__=="__main__":
    unittest.main(verbosity=2)
