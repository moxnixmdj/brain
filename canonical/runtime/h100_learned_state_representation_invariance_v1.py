from __future__ import annotations
import json, math

class RepresentationAccountingError(ValueError): pass

def learned_linear(x:float, weights:dict)->float:
    return float(weights["bias"])+float(weights["slope"])*float(x)

def compile_weights_into_program_literals(weights:dict)->str:
    b=float(weights["bias"]); s=float(weights["slope"])
    if not math.isfinite(b) or not math.isfinite(s):
        raise RepresentationAccountingError("NONFINITE_WEIGHT")
    return f"def predict(x):\n    return ({b!r}) + ({s!r}) * float(x)\n"

def execute_compiled_linear(x:float, weights:dict)->float:
    return float(weights["bias"])+float(weights["slope"])*float(x)

def naive_filetype_accounting(weights:dict)->dict:
    learned_blob=json.dumps(weights,sort_keys=True,separators=(",",":")).encode()
    code=compile_weights_into_program_literals(weights).encode()
    return {
        "weights_file_learned_bytes":len(learned_blob),
        "compiled_source_naively_counted_learned_bytes":0,
        "compiled_source_bytes":len(code),
        "same_capability":all(
            learned_linear(x,weights)==execute_compiled_linear(x,weights)
            for x in (-3.0,-1.0,0.0,2.5,9.0)
        )
    }

def provenance_accounting(weights:dict)->dict:
    code=compile_weights_into_program_literals(weights).encode()
    return {
        "persistent_training_derived_capability_bytes_lower_bound":len(code),
        "representation":"SOURCE_LITERAL",
        "must_count_as_learned_derived":True
    }
