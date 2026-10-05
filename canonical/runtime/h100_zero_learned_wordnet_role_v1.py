"""Zero-learned WordNet lexical role acquisition for H100.

The runtime consumes raw WordNet index/data text supplied as external knowledge.
It does not contain task-specific cue mappings. Role evidence comes from generic
definition/relation language and must be directional; otherwise it abstains.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_WORDNET_ROLE_V1"
_IDENT=re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_LIST=re.compile(r"^\s*([^:;]+)\s*:\s*([^;]+?)\s*;\s*([^:;]+)\s*:\s*([^.;]+)\.?\s*$")

# Generic semantic evidence. None of the frozen challenge cue lemmas are listed.
_INPUT_EVIDENCE=(
    "bring about","brings about","responsible for","source of","origin of",
    "from which","preceding","precedes","causal","determining","determines",
    "ingredient","component used","starting material","producer of",
)
_OUTPUT_EVIDENCE=(
    "caused by","follows from","following from","arises from","resulting from",
    "produced by","created by","end result","final result","thing produced",
    "something produced","something that follows","conclusion of",
)

class LexicalRoleError(ValueError):
    pass

def _norm_lemma(word:str)->str:
    w=word.strip().lower().replace(" ","_")
    if not w:
        raise LexicalRoleError("LEMMA_EMPTY")
    return w

def _parse_index(index_text:str)->dict[str,list[int]]:
    out={}
    for line in index_text.splitlines():
        line=line.strip()
        if not line or line.startswith(" "):
            continue
        parts=line.split()
        if len(parts)<6 or parts[0].startswith("#"):
            continue
        lemma=parts[0]
        try:
            synset_cnt=int(parts[2])
            p_cnt=int(parts[3])
            offset_start=6+p_cnt
            offsets=[int(x) for x in parts[offset_start:offset_start+synset_cnt]]
        except (ValueError,IndexError):
            continue
        if offsets:
            out[lemma]=offsets
    return out

def _parse_data(data_text:str)->dict[int,dict[str,Any]]:
    out={}
    for line in data_text.splitlines():
        if not line or line[0].isspace():
            continue
        before,sep,gloss=line.partition("|")
        parts=before.split()
        if len(parts)<5:
            continue
        try:
            offset=int(parts[0])
            w_cnt=int(parts[3],16)
        except ValueError:
            continue
        pos=4
        words=[]
        try:
            for _ in range(w_cnt):
                words.append(parts[pos].lower())
                pos+=2
        except IndexError:
            continue
        out[offset]={"words":words,"gloss":gloss.strip().lower() if sep else ""}
    return out

def lookup_senses(lemma:str,index_text:str,data_text:str)->list[dict[str,Any]]:
    idx=_parse_index(index_text)
    data=_parse_data(data_text)
    key=_norm_lemma(lemma)
    offsets=idx.get(key,[])
    return [data[o] for o in offsets if o in data]

def _score_role(senses:list[dict[str,Any]])->tuple[int,int,list[str]]:
    input_score=0
    output_score=0
    evidence=[]
    for sense in senses:
        text=(" ".join(sense.get("words",[]))+" "+sense.get("gloss","")).lower().replace("_"," ")
        for phrase in _INPUT_EVIDENCE:
            if phrase in text:
                input_score+=1
                evidence.append("INPUT:"+phrase)
        for phrase in _OUTPUT_EVIDENCE:
            if phrase in text:
                output_score+=1
                evidence.append("OUTPUT:"+phrase)
    return input_score,output_score,sorted(set(evidence))

def classify_lemma_role(lemma:str,index_text:str,data_text:str)->dict[str,Any]:
    senses=lookup_senses(lemma,index_text,data_text)
    if not senses:
        return {"role":"UNKNOWN","input_score":0,"output_score":0,"evidence":[]}
    i,o,e=_score_role(senses)
    if i>0 and o==0:
        role="INPUT"
    elif o>0 and i==0:
        role="OUTPUT"
    else:
        role="UNKNOWN"
    return {"role":role,"input_score":i,"output_score":o,"evidence":e}

def _fields(text:str)->tuple[str,list[str],str,str]:
    m=_FIELD_LIST.match(text)
    if not m:
        raise LexicalRoleError("TASK_TEXT_FORMAT_INVALID")
    left_cue,left_values,right_cue,right_value=m.groups()
    vals=[v.strip() for v in re.split(r"\s*,\s*|\s+and\s+",left_values) if v.strip()]
    target=right_value.strip()
    if not vals or any(_IDENT.fullmatch(v) is None for v in vals) or _IDENT.fullmatch(target) is None:
        raise LexicalRoleError("TASK_FIELDS_INVALID")
    return left_cue.strip(),sorted(vals),right_cue.strip(),target

def induce_roles_from_wordnet(text:str,*,noun_index:str,noun_data:str)->dict[str,Any]:
    left_cue,fields,right_cue,target=_fields(text)
    left=classify_lemma_role(left_cue.rstrip("s"),noun_index,noun_data)
    right=classify_lemma_role(right_cue.rstrip("s"),noun_index,noun_data)
    if left["role"]=="INPUT" and right["role"]=="OUTPUT":
        status="ROLES_IDENTIFIED"
        inputs=fields
        out_target=target
    else:
        status="ABSTAIN_DIRECTION_NOT_IDENTIFIED"
        inputs=[]
        out_target=None
    return {
        "schema":SCHEMA,
        "status":status,
        "inputs":inputs,
        "target":out_target,
        "left_cue_role":left,
        "right_cue_role":right,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "hard_nonclaim":"WORDNET_LEXICAL_EVIDENCE_IS_NOT_OPEN_WORLD_SEMANTIC_UNDERSTANDING",
    }
