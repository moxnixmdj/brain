from __future__ import annotations
import ast, copy, importlib.util, json, tempfile
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_EXECUTABLE_REFINEMENT_VERIFIER_REFINEMENT_CHECKER_V1"
SPEC_SCHEMA="PROJECT_BRAIN_EXECUTABLE_REFINEMENT_VERIFIER_ABSTRACT_SPEC_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_EXECUTABLE_REFINEMENT_VERIFIER_REFINEMENT_RECEIPT_V1"

def _blob(p:Path)->str:
    b=p.read_bytes(); return sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()

def _fail(reason:str,**kw):
    return {"schema":RECEIPT_SCHEMA,"pass":False,"refinement_verified":False,
            "reason":reason,"terminal_authority":False,"terminal_credit_delta":0,**kw}

def _subject(spec,root):
    s=spec.get("subject")
    if not isinstance(s,Mapping): return None,"SUBJECT_REQUIRED"
    try:
        p=(root/str(s["path"])).resolve(strict=True); p.relative_to(root.resolve())
    except Exception:return None,"SUBJECT_PATH_INVALID"
    if _blob(p)!=s.get("git_blob_sha"):return None,"SUBJECT_BLOB_DRIFT"
    return p,None

def _load(p):
    n="_erv_ref_"+sha256(str(p).encode()).hexdigest()[:12]
    sp=importlib.util.spec_from_file_location(n,p)
    if sp is None or sp.loader is None:raise RuntimeError("SUBJECT_IMPORT_FAILED")
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def _static(src):
    tree=ast.parse(src); direct=set(); suffix=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            name=n.func.id if isinstance(n.func,ast.Name) else None
            if name=="_fail" and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
                direct.add(n.args[0].value)
        if isinstance(n,ast.JoinedStr):
            for v in n.values:
                if isinstance(v,ast.Constant) and isinstance(v.value,str) and v.value.startswith("_"):
                    suffix.add(v.value[1:])
    return direct,suffix

def _repo():
    td=tempfile.TemporaryDirectory();r=Path(td.name)
    a=r/"canonical/governance/abstract.json";c=r/"canonical/runtime/concrete.py";p=r/"canonical/verification/proof.json"
    for q in (a,c,p):q.parent.mkdir(parents=True,exist_ok=True)
    a.write_text('{"schema":"ABSTRACT_V1"}\n');c.write_text("def run(x):\n    return x\n");p.write_text('{"pass":true}\n')
    return td,r,a,c,p

def _cert(m,a,c,p):
    return {"schema":m.SCHEMA,"proof_class":"DECLARATIVE_BOUNDING","subject_id":"fixture",
      "abstract_spec":{"path":"canonical/governance/abstract.json","git_blob_sha":m.git_blob_sha(a),"semantic_version":"ABSTRACT_V1"},
      "concrete_implementation":[{"path":"canonical/runtime/concrete.py","git_blob_sha":m.git_blob_sha(c)}],
      "state_mapping":{"proved":True,"mode":"IDENTITY"},
      "input_binding":{"proved":True,"mode":"DIRECT_TYPED_MAPPING"},
      "transition_refinement":{"coverage_mode":"DECLARED_FINITE_PARTITION","unsupported_behavior":"FAIL_CLOSED",
        "classes":[{"case_id":"PASS","kind":"PASS"},{"case_id":"FAIL","kind":"FAIL_CLOSED"}]},
      "observation_refinement":{"proved":True,"mode":"EXACT_GOAL_PROJECTION"},
      "nondeterminism_contract":{"proved":True,"mode":"DETERMINISTIC"},
      "safety_refinement":{"proved":True},"liveness_refinement":{"required":False,"proved":False},
      "proof_dependencies":[{"path":"canonical/verification/proof.json","git_blob_sha":m.git_blob_sha(p)}],
      "terminal_credit_delta":0}

def _good(m,root,cert,spec):
    o=m.verify_certificate(copy.deepcopy(cert),repo_root=root)
    return all(o.get(k)==v for k,v in spec["success_projection"].items()),o

def _mutations():
    return {
      "CERTIFICATE_SCHEMA_INVALID":lambda x:x.__setitem__("schema","BAD"),
      "CERTIFICATE_FIELD_SET_INVALID":lambda x:x.pop("input_binding"),
      "PROOF_CLASS_UNSUPPORTED":lambda x:x.__setitem__("proof_class","MAGIC"),
      "SUBJECT_ID_REQUIRED":lambda x:x.__setitem__("subject_id"," "),
      "NONZERO_TERMINAL_CREDIT_FORBIDDEN":lambda x:x.__setitem__("terminal_credit_delta",1),
      "CONCRETE_IMPLEMENTATION_BINDING_INVALID":lambda x:x.__setitem__("concrete_implementation",[]),
      "STATE_MAPPING_UNPROVED":lambda x:x.__setitem__("state_mapping",{"proved":False,"mode":"IDENTITY"}),
      "STATE_MAPPING_MODE_UNSUPPORTED":lambda x:x.__setitem__("state_mapping",{"proved":True,"mode":"MAGIC"}),
      "INPUT_BINDING_UNPROVED":lambda x:x.__setitem__("input_binding",{"proved":False,"mode":"DIRECT_TYPED_MAPPING"}),
      "INPUT_BINDING_MODE_UNSUPPORTED":lambda x:x.__setitem__("input_binding",{"proved":True,"mode":"MAGIC"}),
      "TRANSITION_REFINEMENT_INVALID":lambda x:x.__setitem__("transition_refinement",None),
      "TRANSITION_COVERAGE_MODE_UNSUPPORTED":lambda x:x["transition_refinement"].__setitem__("coverage_mode","MAGIC"),
      "UNSUPPORTED_BEHAVIOR_MUST_FAIL_CLOSED":lambda x:x["transition_refinement"].__setitem__("unsupported_behavior","PASS"),
      "TRANSITION_CLASSES_REQUIRED":lambda x:x["transition_refinement"].__setitem__("classes",[]),
      "TRANSITION_CLASS_INVALID":lambda x:x["transition_refinement"].__setitem__("classes",[{"case_id":"X","kind":"PASS","extra":1}]),
      "TRANSITION_CLASS_ID_INVALID":lambda x:x["transition_refinement"].__setitem__("classes",[{"case_id":"","kind":"PASS"}]),
      "TRANSITION_CLASS_KIND_UNSUPPORTED":lambda x:x["transition_refinement"]["classes"][0].__setitem__("kind","MAGIC"),
      "OBSERVATION_REFINEMENT_UNPROVED":lambda x:x.__setitem__("observation_refinement",{"proved":False,"mode":"EXACT_GOAL_PROJECTION"}),
      "OBSERVATION_REFINEMENT_MODE_UNSUPPORTED":lambda x:x.__setitem__("observation_refinement",{"proved":True,"mode":"MAGIC"}),
      "NONDETERMINISM_CONTRACT_UNPROVED":lambda x:x.__setitem__("nondeterminism_contract",{"proved":False,"mode":"DETERMINISTIC"}),
      "NONDETERMINISM_MODE_UNSUPPORTED":lambda x:x.__setitem__("nondeterminism_contract",{"proved":True,"mode":"MAGIC"}),
      "SAFETY_REFINEMENT_UNPROVED":lambda x:x.__setitem__("safety_refinement",{"proved":False}),
      "LIVENESS_REFINEMENT_INVALID":lambda x:x.__setitem__("liveness_refinement",{"required":"yes","proved":False}),
      "LIVENESS_REFINEMENT_REQUIRED_BUT_UNPROVED":lambda x:x.__setitem__("liveness_refinement",{"required":True,"proved":False}),
      "PROOF_DEPENDENCIES_INVALID":lambda x:x.__setitem__("proof_dependencies","bad")}

def _artifact_cases(m,root,base,a,c,p):
    cases=[]
    def add(name,mut):cases.append((name,mut))
    add("ABSTRACT_SPEC_NOT_OBJECT",lambda x:x.__setitem__("abstract_spec",[]))
    add("ABSTRACT_SPEC_FIELD_SET_INVALID",lambda x:x["abstract_spec"].__setitem__("extra",1))
    add("ABSTRACT_SPEC_PATH_INVALID",lambda x:x["abstract_spec"].__setitem__("path","missing"))
    add("ABSTRACT_SPEC_BLOB_DRIFT",lambda x:x["abstract_spec"].__setitem__("git_blob_sha","0"*40))
    add("ABSTRACT_SPEC_SEMANTIC_VERSION_REQUIRED",lambda x:x["abstract_spec"].__setitem__("semantic_version",""))
    add("CONCRETE_IMPLEMENTATION_0_NOT_OBJECT",lambda x:x.__setitem__("concrete_implementation",[[]]))
    add("CONCRETE_IMPLEMENTATION_0_FIELD_SET_INVALID",lambda x:x["concrete_implementation"][0].__setitem__("extra",1))
    add("CONCRETE_IMPLEMENTATION_0_PATH_INVALID",lambda x:x["concrete_implementation"][0].__setitem__("path","missing"))
    add("CONCRETE_IMPLEMENTATION_0_BLOB_DRIFT",lambda x:x["concrete_implementation"][0].__setitem__("git_blob_sha","0"*40))
    add("PROOF_DEPENDENCY_0_NOT_OBJECT",lambda x:x.__setitem__("proof_dependencies",[[]]))
    add("PROOF_DEPENDENCY_0_FIELD_SET_INVALID",lambda x:x["proof_dependencies"][0].__setitem__("extra",1))
    add("PROOF_DEPENDENCY_0_PATH_INVALID",lambda x:x["proof_dependencies"][0].__setitem__("path","missing"))
    add("PROOF_DEPENDENCY_0_BLOB_DRIFT",lambda x:x["proof_dependencies"][0].__setitem__("git_blob_sha","0"*40))
    second=c.parent/"concrete2.py";second.write_text("x=2\n")
    dep2=p.parent/"proof2.json";dep2.write_text("{}\n")
    def c1(x):
        x["concrete_implementation"].append({"path":"canonical/runtime/concrete2.py","git_blob_sha":"0"*40})
    def p1(x):
        x["proof_dependencies"].append({"path":"canonical/verification/proof2.json","git_blob_sha":"0"*40})
    add("CONCRETE_IMPLEMENTATION_1_BLOB_DRIFT",c1);add("PROOF_DEPENDENCY_1_BLOB_DRIFT",p1)
    return cases

def verify(spec:Mapping[str,Any],*,repo_root:str|Path):
    try:
      if not isinstance(spec,Mapping) or spec.get("schema")!=SPEC_SCHEMA:return _fail("SPEC_SCHEMA_INVALID")
      root=Path(repo_root).resolve();sp,e=_subject(spec,root)
      if e or sp is None:return _fail(e or "SUBJECT_INVALID")
      src=sp.read_text();direct,suffix=_static(src)
      if direct!=set(spec["direct_fail_reasons"]):return _fail("DIRECT_FAIL_REASON_CENSUS_MISMATCH",source=sorted(direct))
      if suffix!=set(spec["artifact_binding_error_suffixes"]):return _fail("ARTIFACT_SUFFIX_CENSUS_MISMATCH",source=sorted(suffix))
      m=_load(sp);cs=spec["constants"]
      checks=[
       (m.SCHEMA,cs["schema"]),(m.RECEIPT_SCHEMA,cs["receipt_schema"]),
       (sorted(m.SUPPORTED_PROOF_CLASSES),cs["supported_proof_classes"]),
       (sorted(m.ALLOWED_TRANSITION_KINDS),cs["allowed_transition_kinds"]),
       (sorted(m.ALLOWED_COVERAGE_MODES),cs["allowed_coverage_modes"]),
       (sorted(m.ALLOWED_INPUT_BINDING_MODES),cs["allowed_input_binding_modes"]),
       (sorted(m.ALLOWED_STATE_MAPPING_MODES),cs["allowed_state_mapping_modes"]),
       (sorted(m.ALLOWED_OBSERVATION_MODES),cs["allowed_observation_modes"]),
       (sorted(m.ALLOWED_NONDETERMINISM_MODES),cs["allowed_nondeterminism_modes"]),
       (sorted(m._REQUIRED_FIELDS),cs["required_fields"])]
      if any(a!=b for a,b in checks):return _fail("CONSTANT_SURFACE_MISMATCH")
      if src.count('label=f"CONCRETE_IMPLEMENTATION_{index}"')!=1 or src.count('label=f"PROOF_DEPENDENCY_{index}"')!=1:
          return _fail("INDEX_PARAMETRIC_LOOP_SHAPE_MISMATCH")
      td,r,a,c,p=_repo()
      try:
        base=_cert(m,a,c,p);ok,o=_good(m,r,base,spec)
        if not ok:return _fail("SUCCESS_PROJECTION_MISMATCH",observed=o)
        rows=[{"case":"BASE_SUCCESS"}]
        raw_cases=[("CERTIFICATE_NOT_OBJECT",None),*list(_mutations().items())]
        for reason,mut in raw_cases:
          x=[] if reason=="CERTIFICATE_NOT_OBJECT" else copy.deepcopy(base)
          if mut:mut(x)
          out=m.verify_certificate(x,repo_root=r)
          if out.get("pass") is not False or out.get("reason")!=reason:return _fail("DIRECT_WITNESS_FAILED:"+reason,observed=out)
          rows.append({"case":reason})
        for reason,mut in _artifact_cases(m,r,base,a,c,p):
          x=copy.deepcopy(base);mut(x);out=m.verify_certificate(x,repo_root=r)
          if out.get("pass") is not False or out.get("reason")!=reason:return _fail("ARTIFACT_WITNESS_FAILED:"+reason,observed=out)
          rows.append({"case":reason})
        dims=[
          ("proof_class",sorted(m.SUPPORTED_PROOF_CLASSES)),
          ("transition_kind",sorted(m.ALLOWED_TRANSITION_KINDS)),
          ("coverage",sorted(m.ALLOWED_COVERAGE_MODES)),
          ("input",sorted(m.ALLOWED_INPUT_BINDING_MODES)),
          ("state",sorted(m.ALLOWED_STATE_MAPPING_MODES)),
          ("observation",sorted(m.ALLOWED_OBSERVATION_MODES)),
          ("nondeterminism",sorted(m.ALLOWED_NONDETERMINISM_MODES))]
        accepts=[]
        for dim,vals in dims:
          for val in vals:
            x=copy.deepcopy(base)
            if dim=="proof_class":x["proof_class"]=val
            elif dim=="transition_kind":x["transition_refinement"]["classes"][0]["kind"]=val
            elif dim=="coverage":x["transition_refinement"]["coverage_mode"]=val
            elif dim=="input":x["input_binding"]["mode"]=val
            elif dim=="state":x["state_mapping"]["mode"]=val
            elif dim=="observation":x["observation_refinement"]["mode"]=val
            else:x["nondeterminism_contract"]["mode"]=val
            good,out=_good(m,r,x,spec)
            if not good:return _fail("ALLOWED_VALUE_REJECTED:"+dim+":"+val,observed=out)
            accepts.append({"dimension":dim,"value":val})
        material={"subject":spec["subject"],"rejects":rows,"accepts":accepts}
        return {"schema":RECEIPT_SCHEMA,"pass":True,"refinement_verified":True,
          "assurance_level":"STATIC_FAIL_CENSUS_PLUS_REJECTION_AND_ACCEPTANCE_WITNESS_EXECUTION",
          "subject":copy.deepcopy(dict(spec["subject"])),"rejection_witness_count":len(rows),
          "acceptance_witness_count":len(accepts),"witness_count":len(rows)+len(accepts),
          "receipt_sha256":sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
          "repository_wide_refinement":False,"transitive_dependency_refinement":False,
          "semantic_truth_authority":False,"execution_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
      finally:td.cleanup()
    except Exception as e:return _fail("CHECKER_EXCEPTION:"+type(e).__name__+":"+str(e))
