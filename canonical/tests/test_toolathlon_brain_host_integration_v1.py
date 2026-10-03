from __future__ import annotations
import asyncio
import unittest

from canonical.runtime import toolathlon_brain_host_integration_v1 as h


class FakeGateway:
    def __init__(self):
        self.calls=[]
        self.tools=[
            {"name":"expensive_search","description":"Search workspace","inputSchema":{"type":"object","properties":{"q":{"type":"string"}}},"cost":10},
            {"name":"cheap_search","description":"Search workspace","inputSchema":{"type":"object","properties":{"q":{"type":"string"}}},"cost":1},
            {"name":"forbidden_delete","description":"Delete object","inputSchema":{"type":"object"},"cost":0.1,"authorized":False},
        ]

    async def __call__(self, req):
        self.calls.append(req)
        if req["method"]=="tools/list":
            return {"jsonrpc":"2.0","id":req["id"],"result":{"tools":self.tools}}
        if req["method"]=="tools/call":
            name=req["params"]["name"]
            if name not in {x["name"] for x in self.tools}:
                return {"jsonrpc":"2.0","id":req["id"],"error":{"code":-32602,"message":"Tool not found"}}
            return {"jsonrpc":"2.0","id":req["id"],"result":{"content":[{"type":"text","text":"ok:"+name}],"isError":False}}
        raise AssertionError(req)


class FixedSubstrate:
    def __init__(self, cheap=True, inject=False):
        self.seen=[]
        self.cheap=cheap
        self.inject=inject

    async def __call__(self, kind, payload):
        self.seen.append((kind,payload))
        encoded=repr(payload)
        if kind=="SUBPROBLEM":
            out={"goal":"Find document.","required_capabilities":["SEARCH_WORKSPACE"],"constraint":None}
            if self.inject:
                out["selected_tool"]="cheap_search"
            return out
        if kind=="SCHEMA_JUDGMENT":
            # The substrate sees one anonymous schema, never the tool id/cost.
            assert "cheap_search" not in encoded
            assert "expensive_search" not in encoded
            assert "'cost'" not in encoded
            return {"supported":self.cheap}
        if kind=="ARGUMENTS":
            assert "cheap_search" not in encoded
            assert "expensive_search" not in encoded
            assert "'cost'" not in encoded
            return {"arguments":{"q":"needle"}}
        raise AssertionError(kind)


class Integration(unittest.TestCase):
    def test_exact_wire_list_to_brain_select_to_call(self):
        async def go():
            gateway=FakeGateway()
            substrate=FixedSubstrate(cheap=True)
            out=await h.execute_one_brain_selected_step(
                rpc=gateway,substrate=substrate,task_context="Find the document.")
            self.assertEqual(out["selected_tool_id"],"cheap_search")
            methods=[x["method"] for x in gateway.calls]
            self.assertEqual(methods,["tools/list","tools/call"])
            self.assertEqual(gateway.calls[-1]["params"]["name"],"cheap_search")
            self.assertEqual(gateway.calls[-1]["params"]["arguments"],{"q":"needle"})
            self.assertEqual(out["terminal_credit"],0)
        asyncio.run(go())

    def test_negative_cheap_schema_advances_to_expensive(self):
        class S(FixedSubstrate):
            def __init__(self):
                super().__init__(); self.n=0
            async def __call__(self,kind,payload):
                if kind=="SCHEMA_JUDGMENT":
                    self.seen.append((kind,payload)); self.n+=1
                    return {"supported": self.n>1}
                return await super().__call__(kind,payload)
        async def go():
            gateway=FakeGateway()
            out=await h.execute_one_brain_selected_step(
                rpc=gateway,substrate=S(),task_context="Find the document.")
            self.assertEqual(out["selected_tool_id"],"expensive_search")
            self.assertEqual(gateway.calls[-1]["params"]["name"],"expensive_search")
        asyncio.run(go())

    def test_substrate_route_injection_fails_before_tool_call(self):
        async def go():
            gateway=FakeGateway()
            with self.assertRaisesRegex(h.ToolathlonBrainHostError,"SUBPROBLEM_CONTRACT_REJECTED"):
                await h.execute_one_brain_selected_step(
                    rpc=gateway,substrate=FixedSubstrate(inject=True),task_context="Find.")
            self.assertEqual([x["method"] for x in gateway.calls],["tools/list"])
        asyncio.run(go())

    def test_gateway_error_fails_closed(self):
        class BadGateway(FakeGateway):
            async def __call__(self,req):
                if req["method"]=="tools/list":
                    return await super().__call__(req)
                self.calls.append(req)
                return {"jsonrpc":"2.0","id":req["id"],"error":{"code":-32603,"message":"boom"}}
        async def go():
            with self.assertRaisesRegex(h.ToolathlonBrainHostError,"GATEWAY_ERROR"):
                await h.execute_one_brain_selected_step(
                    rpc=BadGateway(),substrate=FixedSubstrate(),task_context="Find.")
        asyncio.run(go())

    def test_argument_synthesis_cannot_change_selected_identity(self):
        class S(FixedSubstrate):
            async def __call__(self,kind,payload):
                if kind=="ARGUMENTS":
                    self.seen.append((kind,payload))
                    return {"arguments":{"q":"needle"},"selected_tool":"expensive_search"}
                return await super().__call__(kind,payload)
        async def go():
            gateway=FakeGateway()
            out=await h.execute_one_brain_selected_step(
                rpc=gateway,substrate=S(),task_context="Find.")
            self.assertEqual(out["selected_tool_id"],"cheap_search")
            self.assertEqual(gateway.calls[-1]["params"]["name"],"cheap_search")
        asyncio.run(go())

    def test_malformed_tool_list_fails_closed(self):
        async def rpc(req):
            return {"jsonrpc":"2.0","id":req["id"],"result":{"tools":[{"description":"missing name"}]}}
        async def go():
            with self.assertRaisesRegex(h.ToolathlonBrainHostError,"NORMALIZATION_FAILED"):
                await h.gateway_list_tools(rpc)
        asyncio.run(go())


if __name__=="__main__":
    unittest.main(verbosity=2)
