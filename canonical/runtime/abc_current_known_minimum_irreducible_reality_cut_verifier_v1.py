from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CUT="canonical/governance/ABC_CURRENT_KNOWN_MINIMUM_IRREDUCIBLE_REALITY_CUT_20261007_V1.json"
EXPECTED={
 "canonical/governance/ABC_CURRENT_BOUND_ZERO_REALITY_SATURATION_20261007_V1.json":"bfe6e36cf09abb6f0740dba77b273d5300c582a5",
 "canonical/governance/ABC_ZERO_REALITY_FIXED_POINT_RESIDUAL_MAP_20261007_V3.json":"c73391693f4cbae6efc9fc11f396c3a3be25875a",
 "canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json":"0fa75e451bba19754a4296283c0095e4182ca97d",
 "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json":"d9ac894594ebcd2883520f7b7977a3548420541c",
 "canonical/governance/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_V1.json":"43b5c74b5caf3b3065feaf98a87f798e7c14aead",
 "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json":"d9c41440ec78886b5ba44c7eeda6f0c2680839ae",
}

def blob(p:str)->str:
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p:str):
 return json.loads((ROOT/p).read_text(encoding="utf-8"))

def verify():
 errors=[]
 for p,h in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  got=blob(p)
  if got!=h: errors.append("SOURCE_DRIFT:"+p+":"+got)
 if errors:
  return {"pass":False,"errors":errors,"terminal":False,"terminal_credit_delta":0}

 cut=load(CUT)
 fmap=load("canonical/governance/ABC_ZERO_REALITY_FIXED_POINT_RESIDUAL_MAP_20261007_V3.json")
 sat=load("canonical/governance/ABC_CURRENT_BOUND_ZERO_REALITY_SATURATION_20261007_V1.json")
 superp=load("canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json")
 brain_first=load("canonical/governance/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_V1.json")

 open_rows=fmap["open_refinements"]
 if len(open_rows)!=13: errors.append("OPEN_ROW_COUNT_NOT_13")
 if sat["saturation_conclusion"]["open_refinement_count_after"]!=13: errors.append("SATURATION_NOT_13")
 comp=[x for x in open_rows if x["family"]=="MULTI_CAPABILITY_COMPOSITION"]
 if len(comp)!=1: errors.append("COMPOSITION_ROW_COUNT")
 comp_res=set(comp[0]["residuals"]) if comp else set()
 if comp_res!={"SELECTED_CONTEXT_LOCAL_C_FOR_ALL_REACHED_MIXED_CAPABILITY_TRANSFORMS"}:
  errors.append("COMPOSITION_RESIDUAL_DRIFT")

 noncomp=[x for x in open_rows if x["family"]!="MULTI_CAPABILITY_COMPOSITION"]
 expected_res=set()
 expected_fams=set()
 for row in noncomp:
  expected_fams.add(row["family"])
  expected_res.update(row["residuals"])
 package_res=[]
 package_fams=set()
 ids=[]
 for pkg in cut["reality_packages"]:
  ids.append(pkg["id"])
  package_res.extend(pkg["residuals"])
  package_fams.update(pkg["families"])
 if len(ids)!=9 or len(set(ids))!=9: errors.append("PACKAGE_COUNT_OR_IDS")
 if set(package_res)!=expected_res:
  errors.append("RESIDUAL_COVER_MISMATCH")
 # The only deliberate cross-family duplicate is AA, but residual list itself should
 # be present once in the cut.
 if len(package_res)!=len(set(package_res)):
  errors.append("DUPLICATE_RESIDUAL_IN_PACKAGES")
 if package_fams!=expected_fams:
  errors.append("FAMILY_COVER_MISMATCH")
 if len(expected_fams)!=12: errors.append("NONCOMP_FAMILY_COUNT_NOT_12")
 if cut["event_driven_after_reality"]["direct_new_target_reality_required"] is not False:
  errors.append("COMPOSITION_DIRECT_REALITY_DRIFT")

 # R2 claims must be licensed by frozen matched design.
 r2=next((x for x in cut["reality_packages"] if x["id"]=="R2_SHARED_MATCHED_SUPERPORTFOLIO"),None)
 if r2 is None: errors.append("R2_MISSING")
 else:
  core={x["family"] for x in superp["core_families"]}
  optional={x["family"] for x in superp["optional_scope_extensions"]}
  supported=core|optional
  missing=set(r2["families"])-supported
  if missing: errors.append("R2_UNSUPPORTED_FAMILY:"+",".join(sorted(missing)))
  direct=set(brain_first["scope_boundary"]["directly_applicable_to"])
  if "AGENCY_MATCHED_SUCCESS_NONINFERIOR" not in direct:
   errors.append("AGENCY_NOT_BRAIN_FIRST_ELIGIBLE")

 # Cut must not invent closure/authority.
 if cut["accounting"]["terminal_credit_delta"]!=0: errors.append("CREDIT_DRIFT")
 if cut["coverage"]["all_13_open_refinements_accounted_for"] is not True:
  errors.append("ACCOUNTING_FLAG_FALSE")
 if cut["minimality_boundary"]["claim"]!="CURRENT_KNOWN_NONREDUNDANT_CUT_UNDER_THE_FROZEN_RESIDUAL_IDENTITIES_AND_ALREADY_VERIFIED_SHARED_EXECUTION_RELATIONS":
  errors.append("MINIMALITY_OVERCLAIM_OR_DRIFT")

 return {
  "schema":"PROJECT_BRAIN_ABC_CURRENT_KNOWN_MINIMUM_IRREDUCIBLE_REALITY_CUT_VERIFIER_V1",
  "status":"PASS__13_OPEN_REFINEMENTS_TO_9_CURRENT_KNOWN_REALITY_PACKAGES_PLUS_EVENT_DRIVEN_COMPOSITION__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":sorted(errors),
  "open_refinement_count":13 if not errors else None,
  "noncomposition_family_count":12 if not errors else None,
  "unique_noncomposition_residual_count":len(expected_res) if not errors else None,
  "reality_package_count":9 if not errors else None,
  "composition_direct_reality_required":False if not errors else None,
  "U_empty":False,
  "terminal":False,
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 out=verify()
 print(json.dumps(out,indent=2,sort_keys=True))
 raise SystemExit(0 if out["pass"] else 1)
