#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, tempfile, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parents[5]
PKG=pathlib.Path(__file__).resolve().parent
MANIFEST=PKG/"COMPOSED_CONFIGURATION_V1.json"
BUILDER=PKG/"build_overlay.py"

def blob_sha(path):
    p=path.resolve()
    cp=subprocess.run(["git","hash-object",str(p)],cwd=ROOT,text=True,capture_output=True,check=True)
    return cp.stdout.strip()

m=json.loads(MANIFEST.read_text(encoding="utf-8"))
assert m["underlying_capability_invention"] is False
assert m["opus_5_5_credit"]==0
assert m["components"]["harness"]["base_config_blob"]==blob_sha(ROOT/m["components"]["harness"]["base_config_path"])
assert m["components"]["harness"]["manifest_blob"]==blob_sha(ROOT/"canonical/capabilities/internalized/software_engineering/mini_swe_agent_2_4_6/INTERNALIZATION_MANIFEST.json")
assert m["components"]["methodology"]["manifest_blob"]==blob_sha(ROOT/"canonical/capabilities/internalized/software_engineering/superpowers_6_4_2/INTERNALIZATION_MANIFEST.json")
assert m["components"]["methodology"]["evaluation_protocol_blob"]==blob_sha(ROOT/"canonical/capabilities/internalized/software_engineering/superpowers_6_4_2/EVALUATION_PROTOCOL_V1.json")
for name,sha in m["components"]["methodology"]["skill_pins"].items():
    p=ROOT/f"canonical/capabilities/internalized/software_engineering/superpowers_6_4_2/skills/{name}/SKILL.md"
    assert blob_sha(p)==sha,(name,blob_sha(p),sha)
with tempfile.TemporaryDirectory() as td:
    out=pathlib.Path(td)/"overlay.yaml"
    subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True)
    text=out.read_text(encoding="utf-8")
    assert text.startswith("agent:\n  system_template: |\n")
    assert "BRAIN FAIL-CLOSED COMPLETION CONTRACT" in text
    for name in m["components"]["methodology"]["skill_pins"]:
        assert f"SUPERPOWERS SKILL: {name}" in text
print("BRAIN_MINI_SWE_SUPERPOWERS_COMPOSED_PACKAGE_PASS")
