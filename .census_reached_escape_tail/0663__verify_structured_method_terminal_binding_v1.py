"""Verify structured-method terminal population binding before global terminal wave."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
BIND="canonical/governance/STRUCTURED_METHOD_TERMINAL_POPULATION_BINDING_V1.json"
FILES={
 "candidate":"canonical/runtime/structured_method_normalized_rule_graph_v3.py",
 "independent_oracle":"canonical/runtime/structured_method_normalized_rule_oracle_v3.py",
 "terminal_population_generator":"canonical/runtime/structured_method_terminal_population_v1.py",
 "scope_gate_input":"canonical/governance/STRUCTURED_METHOD_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json",
 "scope_gate_receipt":"canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
 "normalized_rule_verification":"canonical/verification/STRUCTURED_METHOD_NORMALIZED_RULE_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
 "population_protocol":"canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
}
def sha(p:Path):
 d=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def verify(root:Path):
 b=json.loads((root/BIND).read_text()); e=[]
 for k,p in FILES.items():
  if sha(root/p)!=b["exact_blobs"][k]: e.append("BLOB_DRIFT:"+k)
 reg=json.loads((root/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json").read_text())
 if b["proof_mode"] not in reg["terminal_acceptance_proof_modes"]: e.append("PROOF_MODE")
 if b["acceptance"]["terminal_acceptance_proof_mode"]!=b["proof_mode"]: e.append("MODE_MISMATCH")
 if b["population"]["sample_count"]!=2000: e.append("POPULATION_COUNT")
 for k in ("adaptive_case_selection","case_replacement","replay_for_tuning"):
  if b["population"][k] is not False: e.append("POPULATION_"+k.upper())
 if b["population"]["post_freeze_beacon"] is not None: e.append("BEACON_ALREADY_SET")
 if b["acceptance"]["allowed_failed_cases"]!=0: e.append("NONZERO_FAILURE_ALLOWANCE")
 if b["scope_gate"]["status"]!="INDEPENDENT_PASS__ADMISSIBLE_SUBSTITUTION__ZERO_UNRESOLVED_DIMENSIONS": e.append("SCOPE_GATE")
 receipt=json.loads((root/FILES["scope_gate_receipt"]).read_text())
 if receipt["verdict"]["admissible"] is not True or receipt["workflow_conclusion"]!="success": e.append("SCOPE_RECEIPT")
 norm=json.loads((root/FILES["normalized_rule_verification"]).read_text())
 if norm["workflow_conclusion"]!="success": e.append("NORMALIZED_RULE_RECEIPT")
 if b["boundary"].get("target_weakened") is not False: e.append("TARGET_WEAKENED")
 if b["information_boundary"].get("candidate_receives_hidden_oracle") is not False: e.append("ORACLE_VISIBLE")
 if b.get("execution_authority") is not False or b.get("terminal_results_observed")!=0: e.append("PREWAVE_OVERCLAIM")
 return {"status":"PASS" if not e else "FAIL_CLOSED","errors":sorted(set(e)),"execution_authority":False}
