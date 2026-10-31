import sys, pathlib, shutil, json, hashlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B = pathlib.Path("canonical/astra_runtime/tmp/tx")
if B.exists(): shutil.rmtree(B)
B.mkdir(parents=True)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
# 1. destructive refactor sentence
d=B/"destr"; (d/"pkg").mkdir(parents=True)
src=d/"pkg/util.py"; src.write_text("def add(a,b):\n    return a+b\n\n\ndef caller():\n    return add(1,2)\n")
before=digest(src); files_before=sorted(p.name for p in d.rglob('*') if p.is_file())
r=adm.solve({"task_id":"DES","goal":f"Rename the parameter old_price to price in the python module {d}/pkg/util.py and save the report to {d}/r7.json."})
after = digest(src) if src.exists() else "DELETED"
files_after=sorted(p.name for p in d.rglob('*') if p.is_file())
print("DESTRUCT:", r.get("status"), "| cap:", r.get("compiled_capability_id"), "| source existed:", src.exists(), "| bytes same:", before==after)
print("  before:", files_before, "after:", files_after)
# 2. unrelated sentence naming a source file, catch-all shell
d2=B/"txshell"; (d2/"pkg").mkdir(parents=True)
src2=d2/"pkg/util.py"; src2.write_text("def add(a,b):\n    return a+b\n")
r2=adm.solve({"task_id":"SH","goal":f"Clean up the python module {d2}/pkg/util.py and save the summary to {d2}/s.json."})
print("SHELLCLAIM:", r2.get("status"), "| cap:", r2.get("compiled_capability_id"), "| source exists:", src2.exists())
