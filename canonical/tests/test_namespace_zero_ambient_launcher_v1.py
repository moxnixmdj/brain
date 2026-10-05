from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest

from canonical.runtime.namespace_zero_ambient_launcher_v1 import (
    NamespaceConfinementError,
    canonical_policy,
    launcher_properties,
    spawn_confined,
)

class NamespaceZeroAmbientLauncherTests(unittest.TestCase):
    def test_policy_rejects_relative_argv(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(NamespaceConfinementError, "ARGV0_MUST_BE_ABSOLUTE"):
                canonical_policy({"argv":["python3"],"input_dir":td})

    def test_policy_rejects_ambient_env(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(NamespaceConfinementError, "ENV_NOT_ALLOWLISTED"):
                canonical_policy({"argv":["/usr/bin/python3"],"input_dir":td,"env":{"TOKEN":"x"}})

    def test_launcher_properties_are_fail_closed(self):
        p=launcher_properties()
        self.assertFalse(p["ambient_host_network"])
        self.assertFalse(p["ambient_host_filesystem"])
        self.assertFalse(p["ambient_stdio_application_channel"])
        self.assertTrue(p["declared_input_read_only"])
        self.assertEqual(p["single_deliberate_application_channel"],"BROKER_SOCKET_FD")
        self.assertEqual(p["capability_bounding_set"],"EMPTY")
        self.assertFalse(p["execution_authority"])

@unittest.skipUnless(
    os.environ.get("PROJECT_BRAIN_RUN_NAMESPACE_ESCAPE_TEST")=="1",
    "real namespace test enabled only on a compatible Linux carrier",
)
class NamespaceIntegrationTests(unittest.TestCase):
    def test_child_has_one_broker_channel_and_read_only_input(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            child=root/"child.py"
            child.write_text(
                "import json,os,socket\n"
                "fd=int(os.environ['PROJECT_BRAIN_BROKER_FD'])\n"
                "out={}\n"
                "try:\n open('/input/child.py','ab').write(b'x'); out['input_readonly']=False\n"
                "except OSError:\n out['input_readonly']=True\n"
                "s=socket.socket(); s.settimeout(.2)\n"
                "try:\n s.connect(('1.1.1.1',53)); out['outer_network_blocked']=False\n"
                "except OSError:\n out['outer_network_blocked']=True\n"
                "os.write(fd,(json.dumps(out,sort_keys=True)+'\\n').encode())\n",
                encoding="utf-8",
            )
            with spawn_confined({
                "argv":["/usr/bin/python3","-I","/input/child.py"],
                "input_dir":str(root),
                "env":{"PYTHONDONTWRITEBYTECODE":"1"},
                "limits":{"cpu_seconds":2,"memory_mb":256,"file_size_mb":1,"open_fds":32,"processes":32,"scratch_mb":64},
            }) as confined:
                confined.broker.settimeout(5)
                raw=b""
                while not raw.endswith(b"\n"):
                    chunk=confined.broker.recv(65536)
                    if not chunk:
                        break
                    raw+=chunk
                rc=confined.process.wait(timeout=5)
                report=json.loads(raw.decode())
                self.assertEqual(rc,0)
                self.assertTrue(report["input_readonly"])
                self.assertTrue(report["outer_network_blocked"])

if __name__=="__main__":
    unittest.main(verbosity=2)
