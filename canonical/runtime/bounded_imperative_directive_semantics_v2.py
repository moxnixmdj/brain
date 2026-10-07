"""Fail-closed source-bound imperative directive semantics.

V2 repairs two soundness bugs found by full GDPval falsification: naive
sentence splitting inside filenames/decimals, and noun/headline uses of
imperative-looking words. It proves only the explicit raw required action
phrase, never whole-task semantics.
"""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any

SCHEMA="BRAIN_BOUNDED_IMPERATIVE_DIRECTIVE_SEMANTICS_V2"
VERBS=frozenset("""add analyze apply assess build calculate capture cite compare compile complete conduct copy create describe determine develop document draft ensure evaluate explain flag focus format generate highlight identify include indicate list maintain mark notify perform populate prepare present provide recommend reconcile reference remove replace research review revise save select state submit summarize update use verify write""".split())
AMBIGUOUS_HEADS=frozenset("develop draft focus list present reference research review state use".split())
_PREFIX=re.compile(r"^\s*(?:(?:[-*•]+|\d+[.)]|[A-Za-z][.)]|o)\s+)?",re.I)
_CONTEXT=re.compile(r"^(?P<marker>if|when|after|unless|once|for)\s+(?P<context>.+?),\s*(?P<rest>.+)$",re.I)
_HEAD=re.compile(r"^(?P<verb>[A-Za-z]+)\b(?P<rest>.*)$")
_DECLARATIVE_TAIL=re.compile(r"^(?:[A-Za-z][\w'-]*\s+){0,4}(?:is|are|was|were|has|have|will|can|may|should|must|shows|includes|contains|provides)\b",re.I)
_SENTENCE_BOUNDARY=re.compile(r"(?<=[.!?])\s+(?=(?:[-*•]+\s*|\d+[.)]\s*|[A-Z][A-Za-z]))")
_TITLE_TOKEN=re.compile(r"^[A-Z][A-Za-z0-9&/-]*$")

def segment_task_text(text:str)->list[str]:
    if not isinstance(text,str) or not text.strip(): return []
    out=[]
    for raw in re.split(r"\n+",text):
        line=raw.strip()
        if not line: continue
        out.extend(p.strip() for p in _SENTENCE_BOUNDARY.split(line) if p.strip())
    return out

def _trim(text:str)->str:
    return re.sub(r"[.!?]+\s*$","",text).rstrip()

def parse_directive(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_SOURCE","terminal_authority":False}
    source=text; core=source.strip()
    pm=_PREFIX.match(core); had_prefix=bool(pm and pm.group(0))
    if pm: core=core[pm.end():].strip()
    context=None; had_context=False
    cm=_CONTEXT.match(core)
    if cm:
        had_context=True
        context={"relation":"CONTEXT_"+cm.group("marker").upper(),"text":cm.group("context").strip(),"semantic_resolution":"RAW_SOURCE_BOUND_CONTEXT_ONLY"}
        core=cm.group("rest").strip()
    explicit_please=False
    if core.lower().startswith("please "):
        explicit_please=True; core=core[7:].lstrip()
    hm=_HEAD.match(core)
    if not hm:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"NOT_EXPLICIT_IMPERATIVE_DIRECTIVE","terminal_authority":False}
    verb=hm.group("verb").lower(); rest=hm.group("rest").strip()
    if verb not in VERBS:
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"IMPERATIVE_VERB_OUTSIDE_CERTIFIED_LEXICON","terminal_authority":False}
    if not rest:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"DIRECTIVE_ACTION_ARGUMENT_MISSING","terminal_authority":False}
    if rest.startswith("/"):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"SLASH_HEADING_OR_LABEL_AMBIGUITY","terminal_authority":False}
    if verb in AMBIGUOUS_HEADS and _DECLARATIVE_TAIL.match(rest):
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"NOUN_HEADED_DECLARATIVE_AMBIGUITY","terminal_authority":False}
    plain=re.sub(r"[:.!?]+$","",rest).strip(); tokens=plain.split()
    if verb in AMBIGUOUS_HEADS and not explicit_please and not had_context:
        if rest.endswith(":") and len(tokens)<=3:
            return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"SHORT_HEADING_AMBIGUITY","terminal_authority":False}
        if len(tokens)<=3 and tokens and all(_TITLE_TOKEN.fullmatch(tok) for tok in tokens):
            return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"TITLE_LABEL_AMBIGUITY","terminal_authority":False}
    action=_trim(core)
    return {
      "schema":SCHEMA,"status":"RESOLVED_DIRECTIVE",
      "directive":{"actor":"ADDRESSEE","predicate":verb,"object_text":_trim(rest),"action_text":action,"modality":"REQUIRED","polarity":"REQUIRED","actor_source":"IMPLICIT_IMPERATIVE_ADDRESSEE","argument_semantics_resolved":False,"coordination_split":False},
      "context":context,"source_text":source,
      "source_sha256":sha256(source.encode()).hexdigest(),"directive_sha256":sha256(action.encode()).hexdigest(),
      "scope":"CLOSED_LEXICON_SOURCE_BOUND_IMPERATIVE_DIRECTIVES_WITH_AMBIGUITY_GUARDS_ONLY",
      "terminal_authority":False,
      "soundness_boundary":"PROVES_ONLY_THE_EXPLICIT_REQUIRED_RAW_ACTION_PHRASE__NO_COORDINATION_SPLIT_PRONOUN_RESOLUTION_WORLD_KNOWLEDGE_OR_WHOLE_TASK_SEMANTICS",
      "parse_cues":{"explicit_please":explicit_please,"leading_context":had_context,"list_prefix":had_prefix},
    }
