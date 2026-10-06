from __future__ import annotations
import ast

REFERENCE_MACHINE_ID="H100_U0_PYCORE_3137_V1"
ALLOWED_BUILTINS={
    "abs":abs,"all":all,"any":any,"bool":bool,"enumerate":enumerate,"float":float,
    "int":int,"isinstance":isinstance,"len":len,"list":list,"max":max,"min":min,
    "range":range,"round":round,"set":set,"sorted":sorted,"str":str,"sum":sum,
    "tuple":tuple,"zip":zip,
}
FORBIDDEN_NODES=(
    ast.Import,ast.ImportFrom,ast.Attribute,ast.With,ast.AsyncWith,ast.Try,ast.Raise,
    ast.Global,ast.Nonlocal,ast.Lambda,ast.ClassDef,ast.Await,ast.Yield,ast.YieldFrom,
)
FORBIDDEN_NAMES={
    "__builtins__","eval","exec","open","compile","globals","locals","vars",
    "getattr","setattr","delattr","input","help","dir","memoryview",
}

class ReferenceMachineError(ValueError): pass

def parse_and_validate(source:str)->ast.Module:
    if not isinstance(source,str) or not source.strip():
        raise ReferenceMachineError("SOURCE_INVALID")
    try:
        tree=ast.parse(source,mode="exec")
    except SyntaxError as exc:
        raise ReferenceMachineError("SOURCE_SYNTAX") from exc
    for node in ast.walk(tree):
        if isinstance(node,FORBIDDEN_NODES):
            raise ReferenceMachineError("FORBIDDEN_AST:"+type(node).__name__)
        if isinstance(node,ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ReferenceMachineError("FORBIDDEN_NAME:"+node.id)
    return tree

def canonical_program_bytes(source:str)->bytes:
    tree=parse_and_validate(source)
    return ast.dump(tree,annotate_fields=True,include_attributes=False).encode("utf-8")

def target_program_bits(source:str)->int:
    return 8*len(canonical_program_bytes(source))

def execute(source:str, public_input):
    tree=parse_and_validate(source)
    glb={"__builtins__":ALLOWED_BUILTINS}
    loc={"PUBLIC_INPUT":public_input}
    exec(compile(tree,"<H100_U0_TARGET>","exec"),glb,loc)
    if "solve" not in loc or not callable(loc["solve"]):
        raise ReferenceMachineError("SOLVE_FUNCTION_MISSING")
    return loc["solve"](public_input)

def machine_contract()->dict:
    return {
        "reference_machine_id":REFERENCE_MACHINE_ID,
        "allowed_builtins":sorted(ALLOWED_BUILTINS),
        "forbidden_ast":[x.__name__ for x in FORBIDDEN_NODES],
        "forbidden_names":sorted(FORBIDDEN_NAMES),
        "imports_allowed":False,
        "attribute_access_allowed":False,
    }
