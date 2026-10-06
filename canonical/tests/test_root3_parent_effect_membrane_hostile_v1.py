from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

HOST_SENTINEL = pathlib.Path("/tmp/brain-root3-parent-private-child-probe-v1")

PAYLOAD = r'''import ctypes, json, os, pathlib, socket, subprocess
r={}
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(0.2)
    code=s.connect_ex(("1.1.1.1",53))
    r["outbound_connect_code"]=int(code)
    r["outbound_connect_blocked"]=code!=0
    s.close()
except Exception as e:
    r["outbound_connect_blocked"]=True
    r["outbound_connect_error"]=type(e).__name__+":"+str(e)
r["host_home_visible"]=pathlib.Path("/home/sprite").exists()
r["host_proc_visible"]=pathlib.Path("/proc/self/status").exists()
p=pathlib.Path("/input/hostile.py")
r["input_readable"]=p.is_file()
try:
    p.write_text("tamper")
    r["input_write_blocked"]=False
except Exception as e:
    r["input_write_blocked"]=True
    r["input_write_error"]=type(e).__name__
try:
    cp=subprocess.run(["/bin/sh","-c","echo child >/tmp/brain-root3-parent-private-child-probe-v1"],check=False)
    r["private_child_returncode"]=cp.returncode
    r["private_child_file_exists"]=pathlib.Path("/tmp/brain-root3-parent-private-child-probe-v1").exists()
except Exception as e:
    r["private_child_error"]=type(e).__name__+":"+str(e)
try:
    pathlib.Path("/tmp/m").mkdir(exist_ok=True)
    libc=ctypes.CDLL(None,use_errno=True)
    rc=libc.mount(ctypes.c_char_p(b"tmpfs"),ctypes.c_char_p(b"/tmp/m"),ctypes.c_char_p(b"tmpfs"),ctypes.c_ulong(0),ctypes.c_void_p())
    err=ctypes.get_errno()
    r["native_mount_rc"]=int(rc)
    r["native_mount_errno"]=int(err)
    r["native_mount_blocked"]=rc!=0
except Exception as e:
    r["native_mount_blocked"]=True
    r["native_mount_error"]=type(e).__name__+":"+str(e)
try:
    u=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    u.bind("/tmp/private.sock")
    r["private_unix_socket_created"]=True
    u.close()
except Exception as e:
    r["private_unix_socket_created"]=False
    r["private_unix_socket_error"]=type(e).__name__+":"+str(e)
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(r,sort_keys=True)+"\n").encode())
'''

class ParentMembraneHostileTests(unittest.TestCase):
    def test_native_and_nonprocess_host_effects_are_confined(self):
        try:
            HOST_SENTINEL.unlink()
        except FileNotFoundError:
            pass
        with tempfile.TemporaryDirectory(prefix="brain-parent-membrane-input-") as td:
            root=pathlib.Path(td)
            (root/"hostile.py").write_text(PAYLOAD,encoding="utf-8")
            result=ns.run_confined({
                "argv":["/usr/bin/python3","/input/hostile.py"],
                "input_dir":str(root),
                "limits":{
                    "pids":16,"memory_mb":256,"cpu_seconds":5,"wallclock_s":10,
                    "scratch_mb":32,"max_file_mb":8,"nofile":32,"broker_max_bytes":100000,
                },
            })
        self.assertEqual(result["status"],"CHILD_EXITED")
        payload=json.loads(result["broker_payload"].decode("utf-8"))
        self.assertTrue(payload["outbound_connect_blocked"])
        self.assertFalse(payload["host_home_visible"])
        self.assertFalse(payload["host_proc_visible"])
        self.assertTrue(payload["input_readable"])
        self.assertTrue(payload["input_write_blocked"])
        self.assertTrue(payload["native_mount_blocked"])
        self.assertEqual(payload["native_mount_errno"],1)
        self.assertEqual(payload["private_child_returncode"],0)
        self.assertTrue(payload["private_child_file_exists"])
        self.assertTrue(payload["private_unix_socket_created"])
        self.assertFalse(HOST_SENTINEL.exists())
        self.assertEqual(result["material_effects_committed"],0)
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
