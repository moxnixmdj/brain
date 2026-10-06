from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import zero_ambient_namespace_brokered_launcher_v2 as ns

PAYLOAD = r'''import hashlib, json, os, socket, struct

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def recv_exact(s,n):
    out=b""
    while len(out)<n:
        b=s.recv(n-len(out))
        if not b:
            raise RuntimeError("eof")
        out+=b
    return out

r={}
try:
    direct=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    direct.settimeout(0.2)
    code=direct.connect_ex(("1.1.1.1",53))
    r["direct_network_blocked"]=code!=0
    direct.close()
except Exception:
    r["direct_network_blocked"]=True

p=pathlib.Path("/input/client.py")
try:
    p.write_text("tamper")
    r["input_write_blocked"]=False
except Exception:
    r["input_write_blocked"]=True

core={
  "schema":"PROJECT_BRAIN_ROOT3_BROKER_RPC_REQUEST_V1",
  "driver_id":"TEST_ECHO_V1",
  "driver_contract_git_blob_sha":"a"*40,
  "driver_implementation_git_blob_sha":"b"*40,
  "typed_args":r,
}
core["request_sha256"]=hashlib.sha256(canon(core)).hexdigest()
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
s=socket.socket(fileno=os.dup(fd))
raw=canon(core)
s.sendall(struct.pack("!I",len(raw))+raw)
(size,)=struct.unpack("!I",recv_exact(s,4))
response=json.loads(recv_exact(s,size).decode())
s.close()
ok=(
    response.get("ok") is True
    and response.get("request_sha256")==core["request_sha256"]
    and (response.get("result") or {}).get("echo")==r
    and r["direct_network_blocked"]
    and r["input_write_blocked"]
)
raise SystemExit(0 if ok else 9)
'''


class ZeroAmbientNamespaceBrokeredLauncherV2Tests(unittest.TestCase):
    def test_bidirectional_broker_does_not_widen_ambient_authority(self):
        with tempfile.TemporaryDirectory(
            prefix="brain-brokered-launcher-input-"
        ) as td:
            root=pathlib.Path(td)
            (root/"client.py").write_text(PAYLOAD,encoding="utf-8")
            result=ns.run_confined_brokered(
                {
                    "argv":["/usr/bin/python3","/input/client.py"],
                    "input_dir":str(root),
                    "limits":{
                        "pids":16,
                        "memory_mb":256,
                        "cpu_seconds":5,
                        "wallclock_s":10,
                        "scratch_mb":32,
                        "max_file_mb":8,
                        "nofile":32,
                        "broker_max_bytes":100000,
                    },
                },
                lambda request: {"echo":request["typed_args"]},
                max_requests=4,
            )

        self.assertEqual(result["status"],"CHILD_EXITED")
        self.assertEqual(result["returncode"],0)
        self.assertEqual(result["broker_status"],"CLEAN_EOF")
        self.assertEqual(result["broker_requests_served"],1)
        self.assertIsNone(result["broker_error"])
        self.assertEqual(result["material_effects_committed_by_launcher"],0)
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
