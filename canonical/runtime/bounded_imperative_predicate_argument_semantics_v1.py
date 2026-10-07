from __future__ import annotations
import re
from typing import Any

SCHEMA="BRAIN_BOUNDED_IMPERATIVE_PREDICATE_ARGUMENT_SEMANTICS_V1"
VERBS={
"add","analyze","attach","build","calculate","compare","complete","conduct","consider",
"convert","copy","create","determine","develop","document","draft","emphasize","ensure",
"enter","evaluate","export","fill","flag","format","highlight","identify","include",
"incorporate","indicate","list","make","mention","organize","perform","prepare","present",
"provide","recommend","reconcile","record","reference","remove","rename","replace","report",
"review","save","select","show","submit","summarize","update","use","verify","write"
}
MULTI_VERB=re.compile(r"\b(?:and|or|but)\s+(?:also\s+)?("+ "|".join(sorted(VERBS)) +r")\b",re.I)
CORE=re.compile(r"(?P<verb>[A-Za-z]+)\s+(?P<object>.+?)\s*$",re.I)
BULLET=re.compile(r"^(?:[-•]+|\d+[.)])\s*")
POLITE=re.compile(r"^(?:please|also)\s*,?\s*",re.I)

def parse_imperative(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_SOURCE","terminal_authority":False}
    lead=len(text)-len(text.lstrip()); core=text.lstrip(); explicit_marker=False
    m=BULLET.match(core)
    if m:
        explicit_marker=True; lead+=m.end(); core=core[m.end():]
    m=POLITE.match(core)
    if m:
        explicit_marker=True; lead+=m.end(); core=core[m.end():]
    m=CORE.match(core)
    if not m:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"OUTSIDE_BOUNDED_IMPERATIVE_GRAMMAR","terminal_authority":False}
    verb=m.group("verb").lower(); raw_obj=m.group("object").strip(); obj=raw_obj.rstrip(".!?").strip()
    if verb not in VERBS:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"IMPERATIVE_VERB_NOT_IN_BOUND_SET","terminal_authority":False}
    if not obj:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"OBJECT_MISSING","terminal_authority":False}
    terminal_sentence=bool(re.search(r"[.!?]\s*$",text))
    if not explicit_marker and not terminal_sentence:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"IMPERATIVE_MOOD_NOT_HIGH_CONFIDENCE","terminal_authority":False}
    if raw_obj.endswith(":"):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"LIST_INTRODUCER_INCOMPLETE","terminal_authority":False}
    if re.match(r"^(?:and|or|but)\b",obj,re.I):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"OBJECT_STARTS_COORDINATION","terminal_authority":False}
    if re.match(r"^(?:is|are|was|were|has|have|had|means|refers)\b",obj,re.I):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"DECLARATIVE_LOOKALIKE","terminal_authority":False}
    if MULTI_VERB.search(obj):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"MULTI_PREDICATE_IMPERATIVE","terminal_authority":False}
    vs=m.span("verb"); os=m.span("object")
    return {
      "schema":SCHEMA,"status":"RESOLVED",
      "semantic_graph":{
        "subject":"IMPLICIT_ADDRESSEE","subject_span":None,
        "predicate":verb,"predicate_span":[lead+vs[0],lead+vs[1]],
        "object":obj,"object_span":[lead+os[0],lead+os[0]+len(obj)],
        "modality":"imperative","polarity":"REQUIRED","voice":"IMPERATIVE"
      },
      "terminal_authority":False,
      "scope":"HIGH_CONFIDENCE_DIRECT_EXPLICIT_IMPERATIVE_CLAUSES_WITH_BOUND_VERB_SET_ONLY"
    }
