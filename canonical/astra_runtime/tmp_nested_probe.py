import sys, pathlib
sys.path.insert(0, "/home/user/brain")
import json, subprocess
from canonical.runtime import root3_confined_shell_executor_v1 as sh
pol = sh._prepare({
 "effect_class":"ARBITRARY_COMMAND_EXECUTION",
 "callsite":{"module_path":"canonical/runtime/astra_runtime.py","lineno":357,"process_api":"subprocess.run"},
 "args":[["bash","-lc","echo INNER_OK && python canonical/runtime/verify_pending_cli_binding.py --help 2>&1 | head -3"]],
 "kwargs":{"cwd":str(sh.ROOT),"capture_output":True,"text":True}})["policy"]
res = sh._run_confined_with_popen(pol, subprocess.Popen)
print("INNER RESULT:", json.dumps({k:v for k,v in res.items() if k.endswith("b64")==False}, indent=1)[:300])
print("stdout:", __import__("base64").b64decode(res["stdout_b64"]).decode()[:300])
print("stderr:", __import__("base64").b64decode(res["stderr_b64"]).decode()[:300])
