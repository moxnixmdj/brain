#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

TRUE_FIELDS=("donor_removed","runtime_dependency_closure_verified")
FALSE_FIELDS=("external_runtime_cognition","answer_leakage","heldout_tuning")
NONEMPTY=("brain_owned_artifact_hashes","fresh_qualification_receipts")

def verify(obj):
    errors=[]
    deps=obj.get("runtime_general_purpose_model_dependencies")
    if deps is None: errors.append("MISSING_RUNTIME_MODEL_DEPENDENCIES")
    elif deps != []: errors.append("RUNTIME_GENERAL_PURPOSE_MODEL_PRESENT")
    for k in TRUE_FIELDS:
        if obj.get(k) is not True: errors.append("REQUIRED_TRUE_"+k)
    for k in FALSE_FIELDS:
        if obj.get(k) is not False: errors.append("REQUIRED_FALSE_"+k)
    for k in NONEMPTY:
        v=obj.get(k)
        if not isinstance(v,(list,dict)) or not v: errors.append("REQUIRED_NONEMPTY_"+k)
    return sorted(errors)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("manifest")
    a=ap.parse_args()
    p=Path(a.manifest); raw=p.read_bytes(); obj=json.loads(raw)
    errors=verify(obj)
    print(json.dumps({
        "schema":"PROJECT_BRAIN_CAPABILITY_OWNERSHIP_GUARD_V1",
        "manifest_sha256":hashlib.sha256(raw).hexdigest(),
        "pass":not errors,
        "errors":errors,
    },sort_keys=True))
    raise SystemExit(0 if not errors else 1)

if __name__=="__main__":
    main()
