import sys; sys.path.insert(0,"/home/user/brain")
import json, base64, subprocess
from canonical.runtime import root3_confined_shell_executor_v1 as sh
pol = sh._prepare({
 "effect_class":"ARBITRARY_COMMAND_EXECUTION",
 "callsite":{"module_path":"canonical/runtime/astra_runtime.py","lineno":357,"process_api":"subprocess.run"},
 "args":[["bash","-lc","echo NS2_REAL_OK; ls /input/canonical >/dev/null && echo INPUT_OK; dd if=/dev/urandom bs=16 count=1 >/tmp/r.bin 2>/dev/null && echo URAND_OK"]],
 "kwargs":{"cwd":sh.ROOT,"capture_output":True,"text":True,"timeout":60}})["policy"]
res = sh._run_confined_with_popen(pol, subprocess.Popen)
print("rc:",res["returncode"]); print(base64.b64decode(res["stdout_b64"]).decode()[:200])
print("ERR:", base64.b64decode(res["stderr_b64"]).decode()[:400])
