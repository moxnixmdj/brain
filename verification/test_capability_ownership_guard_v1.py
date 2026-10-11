import importlib.util
from pathlib import Path

path=Path(__file__).with_name("capability_ownership_guard_v1.py")
spec=importlib.util.spec_from_file_location("guard",path)
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

good={
 "runtime_general_purpose_model_dependencies":[],
 "external_runtime_cognition":False,
 "donor_removed":True,
 "answer_leakage":False,
 "heldout_tuning":False,
 "runtime_dependency_closure_verified":True,
 "brain_owned_artifact_hashes":["sha256:brain"],
 "fresh_qualification_receipts":["sha256:qualification"],
}
assert guard.verify(good)==[]

bad=dict(good)
bad["runtime_general_purpose_model_dependencies"]=["external-model"]
assert "RUNTIME_GENERAL_PURPOSE_MODEL_PRESENT" in guard.verify(bad)

bad=dict(good)
bad["external_runtime_cognition"]=True
assert "REQUIRED_FALSE_external_runtime_cognition" in guard.verify(bad)

bad=dict(good)
bad["donor_removed"]=False
assert "REQUIRED_TRUE_donor_removed" in guard.verify(bad)

print("PASS_CAPABILITY_OWNERSHIP_GUARD_V1")
