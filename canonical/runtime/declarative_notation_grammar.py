"""Safe declarative token-grammar compiler for formal engineering notation.

Capability vs knowledge split:
- Brain owns this generic parser/validator mechanism.
- A notation standard contributes declarative grammar rows as JIT knowledge.
- No Python eval, code hooks, or arbitrary regex execution is permitted.

A rule is:
{
  "id": "surface_finish",
  "kind": "surface_finish",
  "atoms": [
    {"literal": "SF"},
    {"capture": "roughness", "type": "number", "min": 0},
    {"capture": "units", "type": "enum", "values": ["UM","MM"], "optional": true}
  ]
}
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_DECLARATIVE_TOKEN_GRAMMAR_V1"
_TOKEN_RE=re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*|\d+(?:\.\d+)?|\|")

_ALLOWED_TYPES={"number","int","identifier","enum","unit"}
_UNITS={"MM","CM","M","IN","UM","DEG"}

def tokenize(text:str)->list[str]:
    if not isinstance(text,str):
        raise ValueError("text must be a string")
    # Normalize common engineering glyphs into explicit tokens.
    s=text.upper().replace("Ø"," DIA ").replace("⌀"," DIA ").replace("°"," DEG ")
    s=s.replace("×"," X ").replace("⌴"," CBORE ").replace("⌵"," CSK ")
    return _TOKEN_RE.findall(s)

def _validate_rule(rule:Mapping[str,Any])->list[str]:
    errors=[]
    rid=rule.get("id")
    if not isinstance(rid,str) or not rid:
        errors.append("RULE_ID_INVALID")
    if not isinstance(rule.get("kind"),str) or not rule.get("kind"):
        errors.append(f"RULE_KIND_INVALID:{rid}")
    atoms=rule.get("atoms")
    if not isinstance(atoms,list) or not atoms:
        errors.append(f"RULE_ATOMS_INVALID:{rid}")
        return errors
    seen=set()
    for i,a in enumerate(atoms):
        if not isinstance(a,Mapping):
            errors.append(f"ATOM_NOT_OBJECT:{rid}:{i}")
            continue
        has_lit="literal" in a
        has_cap="capture" in a
        if has_lit==has_cap:
            errors.append(f"ATOM_SHAPE_INVALID:{rid}:{i}")
            continue
        if has_lit:
            if not isinstance(a.get("literal"),str) or not a["literal"]:
                errors.append(f"LITERAL_INVALID:{rid}:{i}")
            if a.get("optional") not in (None,False,True):
                errors.append(f"OPTIONAL_INVALID:{rid}:{i}")
        else:
            name=a.get("capture"); typ=a.get("type")
            if not isinstance(name,str) or not name or name in seen:
                errors.append(f"CAPTURE_INVALID_OR_DUPLICATE:{rid}:{i}")
            else:
                seen.add(name)
            if typ not in _ALLOWED_TYPES:
                errors.append(f"CAPTURE_TYPE_INVALID:{rid}:{i}:{typ}")
            if typ=="enum":
                vals=a.get("values")
                if not isinstance(vals,list) or not vals or any(not isinstance(x,str) for x in vals):
                    errors.append(f"ENUM_VALUES_INVALID:{rid}:{i}")
            for key in ("min","max"):
                if key in a and not isinstance(a[key],(int,float)):
                    errors.append(f"BOUND_INVALID:{rid}:{i}:{key}")
    return errors

def validate_grammar(rules:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(rules,Sequence) or isinstance(rules,(str,bytes)):
        raise ValueError("rules must be a sequence")
    errors=[]
    ids=set()
    for rule in rules:
        if not isinstance(rule,Mapping):
            errors.append("RULE_NOT_OBJECT")
            continue
        errors.extend(_validate_rule(rule))
        rid=rule.get("id")
        if isinstance(rid,str):
            if rid in ids: errors.append(f"RULE_ID_DUPLICATE:{rid}")
            ids.add(rid)
    return {"schema":SCHEMA,"valid":not errors,"errors":sorted(set(errors))}

def _coerce(token:str,atom:Mapping[str,Any])->tuple[bool,Any]:
    typ=atom["type"]
    try:
        if typ=="number":
            value=float(token)
        elif typ=="int":
            if not re.fullmatch(r"\d+",token): return False,None
            value=int(token)
        elif typ=="identifier":
            if not re.fullmatch(r"[A-Z_][A-Z0-9_.-]*",token): return False,None
            value=token
        elif typ=="enum":
            values={str(x).upper() for x in atom["values"]}
            if token.upper() not in values: return False,None
            value=token.upper()
        elif typ=="unit":
            if token.upper() not in _UNITS: return False,None
            value=token.upper().lower()
        else:
            return False,None
    except ValueError:
        return False,None
    if isinstance(value,(int,float)):
        if "min" in atom and value<float(atom["min"]): return False,None
        if "max" in atom and value>float(atom["max"]): return False,None
    return True,value

def _match_rule(tokens:list[str],rule:Mapping[str,Any])->dict[str,Any]|None:
    atoms=list(rule["atoms"])
    memo={}

    def rec(i:int,j:int,captures:dict[str,Any]):
        key=(i,j,tuple(sorted(captures.items())))
        if key in memo: return None
        memo[key]=True
        if j==len(atoms):
            return captures if i==len(tokens) else None
        atom=atoms[j]
        optional=bool(atom.get("optional",False))

        def consume():
            if i>=len(tokens): return None
            tok=tokens[i]
            if "literal" in atom:
                if tok.upper()!=str(atom["literal"]).upper(): return None
                return rec(i+1,j+1,dict(captures))
            ok,val=_coerce(tok,atom)
            if not ok: return None
            nxt=dict(captures); nxt[str(atom["capture"])]=val
            return rec(i+1,j+1,nxt)

        got=consume()
        if got is not None: return got
        if optional:
            return rec(i,j+1,dict(captures))
        return None

    return rec(0,0,{})

def parse_with_grammar(text:str,rules:Sequence[Mapping[str,Any]])->dict[str,Any]:
    verdict=validate_grammar(rules)
    if not verdict["valid"]:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GRAMMAR_INVALID","details":verdict["errors"]}
    tokens=tokenize(text)
    if not tokens:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY_OR_UNTOKENIZABLE"}
    matches=[]
    for rule in rules:
        captures=_match_rule(tokens,rule)
        if captures is not None:
            matches.append({"rule_id":rule["id"],"kind":rule["kind"],"captures":captures})
    if not matches:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_RULE_MATCH","tokens":tokens}
    if len(matches)>1:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_RULE_MATCH","matches":matches}
    out=matches[0]
    return {
        "schema":SCHEMA,"status":"PARSED","tokens":tokens,
        **out,"terminal_authority":False,
        "scope":"FORMAL_NOTATION_EXPRESSIBLE_IN_SAFE_DECLARATIVE_TOKEN_GRAMMAR",
    }
