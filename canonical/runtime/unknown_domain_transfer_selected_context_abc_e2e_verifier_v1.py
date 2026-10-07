from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_BUNDLE_20261007_V1.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"0faa62fce4bc2f2a99c173b0a10a32d5e1c6a244",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py":"2da564d27a318a99713165208126aaaf36ebc924",
 "canonical/verification/UNKNOWN_DOMAIN_V7_WINDOWS_V8_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json":"d65875f9abba55d9a58a4f2566f3719bebfb0a04",
 "canonical/governance/UNKNOWN_DOMAIN_V7_WINDOWS_V8_ACCEPTANCE_REDUCTION_20261005_V1.json":"ebe8edcda3e0aa7dcffab6032834532a6f06c5f7",
}
ROUTE=(
 "canonical/runtime/unknown_domain_direct_candidate_v1.py",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py",
)
BANNED_IMPORT_ROOTS={"os","subprocess","socket","requests","httpx","urllib","pathlib","shutil","tempfile","multiprocessing"}
BANNED_CALL_NAMES={"open","exec","eval","compile","__import__","system","Popen","run","remove","unlink","rename","replace","write_text","write_bytes"}

def blob(path:Path)->str:
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _route_pure(path:Path):
 tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 bad=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):
   for a in n.names:
    if a.name.split(".")[0] in BANNED_IMPORT_ROOTS: bad.append("IMPORT:"+a.name)
  elif isinstance(n,ast.ImportFrom):
   if (n.module or "").split(".")[0] in BANNED_IMPORT_ROOTS: bad.append("IMPORT_FROM:"+(n.module or ""))
  elif isinstance(n,ast.Call):
   fn=""
   if isinstance(n.func,ast.Name): fn=n.func.id
   elif isinstance(n.func,ast.Attribute): fn=n.func.attr
   if fn in BANNED_CALL_NAMES: bad.append("CALL:"+fn)
 return sorted(set(bad))

def verify():
 errors=[]
 for rel,want in EXPECTED.items():
  p=ROOT/rel
  if not p.is_file(): errors.append("SOURCE_MISSING:"+rel); continue
  got=blob(p)
  if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)
 b=json.loads((ROOT/BUNDLE).read_text(encoding="utf-8"))
 if b.get("target_predicate")!="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT": errors.append("PREDICATE_DRIFT")
 if (b.get("E2E") or {}).get("scope_complete") is not True: errors.append("SCOPE_NOT_COMPLETE")
 if (b.get("E2E") or {}).get("independent_or_objective") is not True: errors.append("E2E_NOT_INDEPENDENT")
 if (b.get("selected_brain_route") or {}).get("external_model_calls")!=0: errors.append("MODEL_CALLS_NONZERO")
 if (b.get("selected_brain_route") or {}).get("learned_bytes")!=0: errors.append("LEARNED_BYTES_NONZERO")
 purity={}
 for rel in ROUTE:
  hits=_route_pure(ROOT/rel)
  purity[rel]=hits
  if hits: errors.append("ROUTE_MATERIAL_EFFECT_SURFACE:"+rel+":"+",".join(hits))
 from canonical.runtime import unknown_domain_direct_v6_universal_proof_v1 as proof
 try:
  out=proof.prove(ROOT)
 except Exception as exc:
  errors.append("UNIVERSAL_PROOF_EXCEPTION:"+type(exc).__name__+":"+str(exc))
  out={}
 if out.get("status")!="PASS__UNIVERSAL_TOTAL_STRING_STRUCTURAL_ID_AND_EXACT_FLOAT_BOUND_EVALUATOR":
  errors.append("UNIVERSAL_PROOF_NOT_PASS")
 if out.get("target_predicate")!="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT":
  errors.append("UNIVERSAL_PREDICATE_DRIFT")
 if (out.get("scope") or {}).get("terminal_or_production_cases_generated")!=0:
  errors.append("PROOF_CONSUMED_REALITY")
 return {
  "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_VERIFIER_V1",
  "status":"PASS__DIRECT_E2E_SCOPE_COMPLETE_BOUND_ROUTE_PURE__ZERO_REALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "route_purity_hits":purity,
  "universal_proof_status":out.get("status"),
  "production_or_terminal_cases_generated":(out.get("scope") or {}).get("terminal_or_production_cases_generated"),
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
