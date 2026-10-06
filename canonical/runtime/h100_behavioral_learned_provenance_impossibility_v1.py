from __future__ import annotations
import copy

class ProvenanceImpossibilityError(ValueError): pass

def compile_state_into_program(state, interpreter):
    if not callable(interpreter):
        raise ProvenanceImpossibilityError("INTERPRETER_NOT_CALLABLE")
    frozen=copy.deepcopy(state)
    def program(x):
        return interpreter(frozen,x)
    return program

def behavioral_equivalence(state,interpreter,inputs):
    compiled=compile_state_into_program(state,interpreter)
    rows=[]
    for x in inputs:
        a=interpreter(state,x)
        b=compiled(x)
        rows.append((a,b,a==b))
    return {
        "all_equal":all(r[2] for r in rows),
        "rows":rows,
        "compiled_accounted_learned_bytes":0,
        "state_information_still_embedded":True
    }
