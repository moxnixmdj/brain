"""One-sided source-bound imperative directive semantics.

This module recognizes only an explicit, closed lexical class of imperative
directives in bounded task text. It proves that the addressee is explicitly
required to perform the exact source-bound action phrase. It deliberately does
NOT split coordination, resolve pronouns, infer omitted arguments, or claim
full task semantics.
"""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any

SCHEMA="BRAIN_BOUNDED_IMPERATIVE_DIRECTIVE_SEMANTICS_V1"

VERBS=frozenset({
 "add","analyze","apply","assess","build","calculate","capture","cite","compare",
 "compile","complete","conduct","copy","create","describe","determine","develop",
 "document","draft","ensure","evaluate","explain","flag","focus","format","generate",
 "highlight","identify","include","indicate","list","maintain","mark","notify",
 "perform","populate","prepare","present","provide","recommend","reconcile",
 "reference","remove","replace","research","review","revise","save","select",
 "state","submit","summarize","update","use","verify","write"
})

_PREFIX=re.compile(r"^\s*(?:(?:[-*•]+|\d+[.)]|[A-Za-z][.)]|o)\s+)?",re.I)
_CONTEXT=re.compile(
 r"^(?P<marker>if|when|after|unless|once|for)\s+(?P<context>.+?),\s*(?P<rest>.+)$",
 re.I,
)
_HEAD=re.compile(r"^(?P<verb>[A-Za-z]+)\b(?P<rest>.*)$")

def _trim_span(text:str,start:int,end:int)->tuple[int,int]:
    while start<end and text[start].isspace(): start+=1
    while end>start and text[end-1].isspace(): end-=1
    while end>start and text[end-1] in ".!?": end-=1
    while end>start and text[end-1].isspace(): end-=1
    return start,end

def parse_directive(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_SOURCE","terminal_authority":False}

    pm=_PREFIX.match(text)
    core_start=pm.end() if pm else 0
    core=text[core_start:].strip()
    core_start=text.find(core,core_start)
    context=None

    cm=_CONTEXT.match(core)
    if cm:
        ctx_raw=cm.group("context")
        rest=cm.group("rest")
        ctx_local=core.find(ctx_raw)
        rest_local=core.find(rest,cm.start("rest"))
        context={
          "relation":"CONTEXT_"+cm.group("marker").upper(),
          "text":ctx_raw.strip(),
          "span":[core_start+ctx_local,core_start+ctx_local+len(ctx_raw)],
          "semantic_resolution":"RAW_SOURCE_BOUND_CONTEXT_ONLY",
        }
        core_start=core_start+rest_local
        core=rest.strip()
        core_start=text.find(core,core_start)

    if core.lower().startswith("please "):
        p=len(core)-len(core.lstrip())
        core_start+=p+7
        core=core[p+7:].lstrip()
        core_start=text.find(core,core_start)

    hm=_HEAD.match(core)
    if not hm:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"NOT_EXPLICIT_IMPERATIVE_DIRECTIVE","terminal_authority":False}
    verb=hm.group("verb").lower()
    if verb not in VERBS:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"IMPERATIVE_VERB_OUTSIDE_CERTIFIED_LEXICON","terminal_authority":False}

    verb_start=text.find(hm.group("verb"),core_start)
    verb_end=verb_start+len(hm.group("verb"))
    raw_rest=hm.group("rest")
    if not raw_rest.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"DIRECTIVE_ACTION_ARGUMENT_MISSING","terminal_authority":False}

    rest_start=core_start+hm.start("rest")
    obj_start,obj_end=_trim_span(text,rest_start,len(text))
    if obj_start>=obj_end:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"DIRECTIVE_ACTION_ARGUMENT_MISSING","terminal_authority":False}

    action_start=verb_start
    _,action_end=_trim_span(text,verb_start,len(text))
    action_text=text[action_start:action_end]
    object_text=text[obj_start:obj_end]

    payload={
      "actor":"ADDRESSEE",
      "predicate":verb,
      "object_text":object_text,
      "action_text":action_text,
      "modality":"REQUIRED",
      "polarity":"REQUIRED",
      "actor_source":"IMPLICIT_IMPERATIVE_ADDRESSEE",
      "predicate_span":[verb_start,verb_end],
      "object_span":[obj_start,obj_end],
      "action_span":[action_start,action_end],
      "argument_semantics_resolved":False,
      "coordination_split":False,
    }
    return {
      "schema":SCHEMA,
      "status":"RESOLVED_DIRECTIVE",
      "directive":payload,
      "context":context,
      "directive_sha256":sha256(action_text.encode("utf-8")).hexdigest(),
      "scope":"CLOSED_LEXICON_SOURCE_BOUND_IMPERATIVE_DIRECTIVES_ONLY",
      "terminal_authority":False,
      "soundness_boundary":"PROVES_ONLY_THE_EXPLICIT_REQUIRED_RAW_ACTION_PHRASE__NO_COORDINATION_SPLIT_PRONOUN_RESOLUTION_WORLD_KNOWLEDGE_OR_FULL_TASK_SEMANTICS",
    }
