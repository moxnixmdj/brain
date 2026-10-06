from __future__ import annotations
import hashlib, json
from typing import Any, Callable

class RepresentationInvariantError(ValueError):
    pass

def canonical_blob(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def parameterized_linear(parameters:dict[str,float],x:float)->float:
    return float(parameters["a"])*float(x)+float(parameters["b"])

def compile_parameters_as_code_constants(parameters:dict[str,float])->Callable[[float],float]:
    a=float(parameters["a"]); b=float(parameters["b"])
    def f(x:float)->float:
        return a*float(x)+b
    return f

def externalize_code_constants_as_frozen_blob(a:float,b:float)->tuple[dict[str,float],Callable[[dict[str,float],float],float]]:
    blob={"a":float(a),"b":float(b)}
    def fixed_program(params:dict[str,float],x:float)->float:
        return float(params["a"])*float(x)+float(params["b"])
    return blob,fixed_program

def behavior_fingerprint(fn:Callable[[float],float],xs:list[float])->str:
    ys=[fn(float(x)) for x in xs]
    return hashlib.sha256(canonical_blob(ys)).hexdigest()

def learned_to_code_equivalent(parameters:dict[str,float],xs:list[float])->dict:
    param_fn=lambda x: parameterized_linear(parameters,x)
    code_fn=compile_parameters_as_code_constants(parameters)
    return {
        "equivalent":all(param_fn(x)==code_fn(x) for x in xs),
        "parameter_blob_bytes":len(canonical_blob(parameters)),
        "code_constant_payload_bytes":len(canonical_blob({"a":float(parameters["a"]),"b":float(parameters["b"])})),
        "parameter_behavior_sha256":behavior_fingerprint(param_fn,xs),
        "compiled_behavior_sha256":behavior_fingerprint(code_fn,xs),
    }

def code_to_blob_equivalent(a:float,b:float,xs:list[float])->dict:
    code_fn=lambda x: float(a)*float(x)+float(b)
    blob,program=externalize_code_constants_as_frozen_blob(a,b)
    blob_fn=lambda x: program(blob,x)
    return {
        "equivalent":all(code_fn(x)==blob_fn(x) for x in xs),
        "blob_bytes":len(canonical_blob(blob)),
        "code_behavior_sha256":behavior_fingerprint(code_fn,xs),
        "blob_behavior_sha256":behavior_fingerprint(blob_fn,xs),
    }

def accounting_conclusion()->dict:
    return {
      "learned_bytes_representation_invariant":False,
      "total_persistent_capability_bearing_information_should_be_reported":True,
      "deduction":"SEMANTIC_CLASSIFICATION_AS_LEARNED_VS_CODE_CAN_CHANGE_UNDER_BEHAVIOR_PRESERVING_REFACTORING",
      "h100_terminal_credit_delta":0
    }
