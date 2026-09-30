#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, tempfile, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
GUARD=ROOT/"execution_guard"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

aa=load("actions_admission",GUARD/"actions_admission.py")
storemod=load("github_ref_store_live",GUARD/"github_ref_store_live.py")
gr=load("github_actions_guarded_run_live",GUARD/"github_actions_guarded_run_live.py")

class MemStore:
    def __init__(self, fail_key=None, false_key=None):
        self.data={}; self.fail_key=fail_key; self.false_key=false_key
    def create(self,key,value):
        if self.fail_key and self.fail_key(key): raise RuntimeError("INJECTED_STORE_UNCERTAINTY")
        if self.false_key and self.false_key(key): return False
        if key in self.data: return False
        self.data[key]=json.loads(json.dumps(value))
        return True
    def read(self,key): return self.data.get(key)

def expect(exc, fn):
    try: fn()
    except exc: return True
    except Exception as e: raise AssertionError(f"expected {exc.__name__}, got {type(e).__name__}: {e}")
    raise AssertionError(f"expected {exc.__name__}")

def frozen(gate="g1",problem=None):
    p=problem or aa.problem_sha256("same causal problem")
    return aa.FrozenExecution(
      gate_id=gate,problem_sha256=p,task_sha256="a"*64,runtime_sha256="b"*64,
      canonical_base="c"*40,authorization_sha256="d"*64)

def main():
    checks={}
    s=MemStore()
    first=aa.admit_current_run_once(s,frozen(),"owner-1","run-1")
    checks["first_admission_pass"]=first["status"]=="CURRENT_RUN_ADMITTED"
    checks["duplicate_same_gate_denied"]=expect(aa.AdmissionDenied,lambda: aa.admit_current_run_once(s,frozen(),"owner-2","run-2"))
    s2=MemStore()
    aa.admit_current_run_once(s2,frozen(gate="gA"),"owner-1","run-1")
    checks["same_problem_different_gate_denied"]=expect(aa.AdmissionDenied,lambda: aa.admit_current_run_once(s2,frozen(gate="gB"),"owner-2","run-2"))
    s3=MemStore(fail_key=lambda k:k.startswith("gates/"))
    checks["reservation_uncertainty_fails_closed"]=expect(aa.AdmissionDenied,lambda: aa.admit_current_run_once(s3,frozen(),"owner","run"))
    s4=MemStore(fail_key=lambda k:k.startswith("dispatches/"))
    checks["dispatch_ack_uncertainty_fails_closed"]=expect(aa.DispatchUncertain,lambda: aa.admit_current_run_once(s4,frozen(),"owner","run"))
    s5=MemStore(false_key=lambda k:k.startswith("dispatches/"))
    checks["dispatch_ack_nonpersist_fails_closed"]=expect(aa.DispatchUncertain,lambda: aa.admit_current_run_once(s5,frozen(),"owner","run"))

    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); p=root/"candidate.txt"; p.write_text("alpha",encoding="utf-8")
        raw=p.read_bytes()
        blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()
        sha=hashlib.sha256(raw).hexdigest()
        pins=[{"path":"candidate.txt","git_blob_sha1":blob,"sha256":sha}]
        checks["frozen_pin_accepts_exact_bytes"]=gr.verify_pins(root,pins)==["candidate.txt"]
        p.write_text("beta",encoding="utf-8")
        checks["pin_drift_rejected"]=expect(RuntimeError,lambda: gr.verify_pins(root,pins))
        checks["path_escape_rejected"]=expect(ValueError,lambda: gr.verify_pins(root,[{"path":"../escape.txt"}]))

    base_commit="1"*40; base_tree="2"*40
    records={}; commits={}
    def req(method,path,payload=None):
        if method=="POST" and path.endswith("/git/commits"):
            sha=("3"*39)+str((len(commits)+1)%10); commits[sha]=payload; return 201,{"sha":sha},{}
        if method=="POST" and path.endswith("/git/refs"):
            ref=payload["ref"]; sha=payload["sha"]
            if ref in records: return 422,{"message":"Reference already exists"},{}
            records[ref]=sha; return 201,{"ref":ref,"object":{"sha":sha}},{}
        if method=="GET" and "/git/ref/heads/" in path:
            import urllib.parse
            short=urllib.parse.unquote(path.split("/git/ref/heads/",1)[1]); ref="refs/heads/"+short
            if ref not in records:return 404,{},{}
            return 200,{"object":{"sha":records[ref]}},{}
        if method=="GET" and "/git/commits/" in path:
            sha=path.rsplit("/",1)[1]; return 200,{"message":commits[sha]["message"]},{}
        raise AssertionError((method,path,payload))
    rs=storemod.GitHubRefStore(req,"o/r",base_commit,base_tree,"test")
    checks["immutable_store_create"]=rs.create("k",{"x":1}) is True
    checks["immutable_store_duplicate_rejected"]=rs.create("k",{"x":2}) is False
    checks["immutable_store_roundtrip"]=rs.read("k")=={"x":1}
    # Tamper with immutable record envelope and ensure integrity verification rejects it.
    short,_=rs._ref("k"); ref="refs/heads/"+short; sha=records[ref]
    msg=commits[sha]["message"]; env=json.loads(msg[len(rs.PREFIX):]); env["record"]={"x":999}
    commits[sha]["message"]=rs.PREFIX+json.dumps(env,separators=(",",":"))
    checks["corrupt_record_rejected"]=expect(storemod.StoreUnavailable,lambda: rs.read("k"))

    report={
      "schema":"PROJECT_BRAIN_SCOPED_SELF_VERIFICATION_RECOVERY_FRESH_VERIFICATION_V1",
      "scope":"DUPLICATE_EXECUTION_SUPPRESSION__UNCERTAINTY_FAIL_CLOSED__IMMUTABLE_RECORD_INTEGRITY__FROZEN_PIN_DRIFT_REJECTION",
      "current_bytes":{
        "actions_admission_sha256":hashlib.sha256((GUARD/"actions_admission.py").read_bytes()).hexdigest(),
        "github_ref_store_sha256":hashlib.sha256((GUARD/"github_ref_store_live.py").read_bytes()).hexdigest(),
        "guarded_run_sha256":hashlib.sha256((GUARD/"github_actions_guarded_run_live.py").read_bytes()).hexdigest()
      },
      "checks":checks,
      "all_pass":all(checks.values()),
      "incremental_spend_usd":0,
      "claim_limits":["NO_GENERAL_DEBUGGING_INTELLIGENCE_CLAIM","NO_GENERAL_ERROR_RECOVERY_CLAIM","NO_WHOLE_OPUS_SELF_VERIFICATION_FAMILY_CLAIM"]
    }
    out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"SELF_VERIFICATION_RECOVERY_REPORT.json"
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    if not report["all_pass"]: raise SystemExit(1)

if __name__=="__main__": main()
