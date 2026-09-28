#!/usr/bin/env python3
import json, pathlib, subprocess

p=pathlib.Path("canonical/astra_runtime/tmp/PROJECT_BRAIN_DATAMATRIX.png")
rows=[]
for label,argv in [
    ("default",["dmtxread",str(p)]),
    ("edge1",["dmtxread","-e","1",str(p)]),
]:
    proc=subprocess.run(argv,text=True,capture_output=True,timeout=30)
    rows.append({
      "label":label,
      "argv":argv,
      "returncode":proc.returncode,
      "stdout":proc.stdout,
      "stderr":proc.stderr,
    })
print(json.dumps(rows,sort_keys=True))
