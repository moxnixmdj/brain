import asyncio
import unittest
from dataclasses import dataclass

from canonical.runtime.harbor_environment_transport import (
    HarborEnvironmentTransport,
    HarborTransportError,
    execute_predeclared_action,
)

@dataclass
class R:
    return_code: int
    stdout: str=""
    stderr: str=""

class FakeEnvironment:
    def __init__(self):
        self.commands=[]
    async def exec(self, command, **kwargs):
        self.commands.append((command,kwargs))
        if command=="printf hello":
            return R(0,"hello","")
        if "read_bytes" in command:
            return R(0,"fixture","")
        return R(0,"","")

class HarborEnvironmentTransportTests(unittest.TestCase):
    def test_exec(self):
        async def run():
            env=FakeEnvironment()
            t=HarborEnvironmentTransport(env)
            r=await t.exec("printf hello",timeout_sec=9)
            self.assertEqual(r.stdout,"hello")
            self.assertEqual(env.commands[0][1],{"timeout_sec":9})
        asyncio.run(run())

    def test_read_and_write_actions(self):
        async def run():
            t=HarborEnvironmentTransport(FakeEnvironment())
            r=await execute_predeclared_action(t,{"type":"terminal_read_text","args":{"path":"/tmp/a"}})
            self.assertEqual(r["text"],"fixture")
            w=await execute_predeclared_action(t,{"type":"terminal_write_text","args":{"path":"/tmp/a","text":"abc"}})
            self.assertEqual(w["returncode"],0)
        asyncio.run(run())

    def test_reject_unknown_action(self):
        async def run():
            t=HarborEnvironmentTransport(FakeEnvironment())
            with self.assertRaises(HarborTransportError):
                await execute_predeclared_action(t,{"type":"shell","args":{"command":"id"}})
        asyncio.run(run())

    def test_reject_relative_path(self):
        async def run():
            t=HarborEnvironmentTransport(FakeEnvironment())
            with self.assertRaises(HarborTransportError):
                await t.read_text("../secret")
        asyncio.run(run())

if __name__=="__main__":
    unittest.main(verbosity=2)
