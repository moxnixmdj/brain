from __future__ import annotations
import ast,hashlib,importlib.util,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ROUTE={
 "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
 "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":"7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
 "canonical/runtime/livebench_legacy15_contract_composer_v2.py":"d73ec366b32252996258eae6d10d67d4d6a5e042",
 "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":"71e637c70edf1c582e28ea38b3b798965c803a06",
}
ALLOWED_STDLIB={"__future__","typing","re","json","itertools","collections"}
ALLOWED_INTERNAL={
 "livebench_legacy15_composition_archetypes_v1",
 "livebench_legacy15_slot_feasibility_v1",
 "livebench_legacy15_contract_composer_v2",
 "livebench_legacy15_pointwise_optimal_v1",
}
FORBIDDEN_CALL_NAMES={
 "open","remove","unlink","rename","replace","mkdir","makedirs","rmdir",
 "system","popen","Popen","check_call","check_output","urlopen","request",
 "connect","send","sendall","write_bytes","write_text","touch"
}
FORBIDDEN_MODULE_PREFIXES=("os","subprocess","socket","urllib","requests","httpx","shutil","tempfile","pathlib","browser","selenium","playwright")

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def _is_main_guard(node:ast.If)->bool:
    t=node.test
    if not isinstance(t,ast.Compare) or len(t.ops)!=1 or not isinstance(t.ops[0],ast.Eq):
        return False
    left=t.left
    comps=t.comparators
    vals=[left]+list(comps)
    saw_name=any(isinstance(x,ast.Name) and x.id=="__name__" for x in vals)
    saw_main=any(isinstance(x,ast.Constant) and x.value=="__main__" for x in vals)
    return saw_name and saw_main

class Scan(ast.NodeVisitor):
    def __init__(self):
        self.errors=[]
        self.internal=set()
    def visit_If(self,node):
        if _is_main_guard(node):
            return
        self.generic_visit(node)
    def visit_Import(self,node):
        for a in node.names:
            root=a.name.split(".")[0]
            if root in FORBIDDEN_MODULE_PREFIXES:
                self.errors.append("FORBIDDEN_IMPORT:"+a.name)
            elif root not in ALLOWED_STDLIB:
                self.errors.append("UNDECLARED_IMPORT:"+a.name)
    def visit_ImportFrom(self,node):
        mod=str(node.module or "")
        root=mod.split(".")[0]
        if mod=="canonical.runtime":
            for a in node.names:
                self.internal.add(a.name)
                if a.name not in ALLOWED_INTERNAL:
                    self.errors.append("UNDECLARED_INTERNAL_IMPORT:"+a.name)
        elif root in FORBIDDEN_MODULE_PREFIXES:
            self.errors.append("FORBIDDEN_IMPORT:"+mod)
        elif root not in ALLOWED_STDLIB:
            self.errors.append("UNDECLARED_IMPORT:"+mod)
    def visit_Call(self,node):
        name=None
        if isinstance(node.func,ast.Name):
            name=node.func.id
        elif isinstance(node.func,ast.Attribute):
            name=node.func.attr
        if name in FORBIDDEN_CALL_NAMES:
            self.errors.append("FORBIDDEN_CALL:"+str(name))
        self.generic_visit(node)

def verify():
    errors=[]
    union_internal=set()
    for rel,want in ROUTE.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("ROUTE_SOURCE_MISSING:"+rel); continue
        got=blob(p)
        if got!=want:
            errors.append("ROUTE_BLOB_DRIFT:"+rel)
        tree=ast.parse(p.read_text(encoding="utf-8"),filename=rel)
        s=Scan(); s.visit(tree)
        errors.extend(rel+":"+x for x in s.errors)
        union_internal|=s.internal

    expected_internal={
      "livebench_legacy15_composition_archetypes_v1",
      "livebench_legacy15_slot_feasibility_v1",
      "livebench_legacy15_contract_composer_v2",
    }
    if union_internal!=expected_internal:
        errors.append("INTERNAL_IMPORT_CLOSURE_MISMATCH:"+repr(sorted(union_internal)))

    try:
        p=ROOT/"canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
        spec=importlib.util.spec_from_file_location("brain_livebench_d_audit_route",p)
        if spec is None or spec.loader is None: raise RuntimeError("ROUTE_LOAD_FAILED")
        m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
        out=m.run({"contracts":[{"instruction_id":"detectable_format:title","slots":{}}]})
        if out.get("status")!="CANDIDATE_POINTWISE_OPTIMAL": errors.append("ROUTE_EXEC_STATUS")
        if out.get("model_dependency_count")!=0: errors.append("MODEL_DEPENDENCY_NONZERO")
        if out.get("terminal_rows_used") is not False: errors.append("TERMINAL_ROWS_USED")
        if out.get("target_scores_used") is not False: errors.append("TARGET_SCORES_USED")
    except Exception as exc:
        errors.append("ROUTE_EXEC_FAILED:"+type(exc).__name__+":"+str(exc))

    return {
      "schema":"PROJECT_BRAIN_V13_LIVEBENCH_ACTIVE15_D_ROUTE_VERIFIER_V1",
      "status":"PASS__ZERO_MATERIAL_EFFECT_FOOTPRINT__DONOR_INDEPENDENT_ROUTE__D_DELTA_CLOSED" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "material_effect_count":0 if not errors else None,
      "model_dependency_count":0 if not errors else None,
      "D_delta_closed":not errors,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
