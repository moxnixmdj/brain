#!/usr/bin/env python3
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as v1

SCHEMA = "PROJECT_BRAIN_INSTRUCTION_CONSTRAINT_COMPILER_V2"

class ConstraintV2Error(RuntimeError):
    pass

@dataclass(frozen=True)
class ExtraConstraints:
    no_whitespace: bool = False
    title_case: bool = False
    newline_words: bool = False
    sentence_ratio_2_to_1: bool = False
    sentence_types_balanced: bool = False
    punctuation_cover: bool = False
    nested_delimiter_depth: int | None = None
    max_word_repeat: int | None = None
    min_pronouns: int | None = None
    allowed_options: tuple[str, ...] = ()
    require_output_template: bool = False
    bullet_marker: str | None = None
    require_sub_bullets: bool = False
    require_sentence_then_bullets: bool = False
    require_italic_thesis: bool = False
    paragraph_cycle: bool = False
    sentence_word_increment: int | None = None
    no_same_initial_adjacent: bool = False
    keyword_sentence: tuple[str, int] | None = None
    keyword_position: tuple[str, int, int] | None = None
    repeated_position_word: str | None = None

@dataclass(frozen=True)
class Program:
    base: v1.ConstraintSet
    extra: ExtraConstraints

_WORD_RE = re.compile(r"\b[^\W_]+(?:['’-][^\W_]+)*\b", re.UNICODE)
_SENT_RE = re.compile(r"[^.!?]*(?:[.!?]+|$)", re.S)
_PRONOUNS = {
    "i","me","my","mine","myself","we","us","our","ours","ourselves",
    "you","your","yours","yourself","yourselves","he","him","his","himself",
    "she","her","hers","herself","it","its","itself","they","them","their",
    "theirs","themselves",
}
_FILLER = (
    "amber birch cedar delta ember frost granite harbor ivory juniper kinetic "
    "lumen meadow nectar orbit prairie quartz river summit timber umber velvet "
    "willow xenon yarrow zephyr"
).split()

def _words(text: str) -> list[str]:
    return _WORD_RE.findall(str(text or ""))

def _sentences(text: str) -> list[str]:
    out=[]
    for m in _SENT_RE.finditer(str(text or "")):
        s=m.group(0).strip()
        if s:
            out.append(s)
    return out

def _split_options(raw: str) -> tuple[str, ...]:
    raw=" ".join(str(raw or "").split())
    if "/" in raw:
        parts=raw.split("/")
    elif re.search(r"\bor\b",raw,re.I):
        parts=re.split(r"\bor\b",raw,flags=re.I)
    else:
        parts=raw.split(",")
    return tuple(x.strip() for x in parts if x.strip())

def compile_program(instruction: str) -> Program:
    text=str(instruction or "")
    if not text.strip():
        raise ConstraintV2Error("INSTRUCTION_REQUIRED")
    base=v1.compile_constraints(text)

    no_ws=bool(re.search(r"(?:output|response).*not contain any whitespace|no whitespace",text,re.I))
    title=bool(re.search(r"(?:entire\s+)?(?:response|answer).*title case|write.*title case",text,re.I))
    newline=bool(re.search(r"(?:write|put) each word on (?:a )?new line",text,re.I))
    ratio=bool(re.search(r"2\s*:\s*1 ratio of declarative to interrogative",text,re.I))
    balanced=bool(re.search(r"sentence types.*declarative.*interrogative.*exclamatory.*balanced",text,re.I|re.S))
    punct=bool(re.search(r"every standard punctuation mark at least once",text,re.I))
    depth=5 if re.search(r"nest (?:parentheses|brackets|delimiters).*at least\s*5\s*levels",text,re.I|re.S) else None

    maxrep=None
    m=re.search(r"(?:not|never) repeat any word more than\s+(\d+)\s+times",text,re.I)
    if m:
        maxrep=int(m.group(1))
    minpro=None
    m=re.search(r"(?:include|use) at least\s+(\d+)\s+personal pronouns",text,re.I)
    if m:
        minpro=int(m.group(1))

    options=()
    m=re.search(r"answer with one of the following options:\s*(.*?)\.\s*(?:do not|don't) give any explanation",text,re.I|re.S)
    if m:
        options=_split_options(m.group(1))

    template=bool(
        re.search(r"use this exact template.*?My Answer:.*?My Conclusion:.*?Future Outlook:",text,re.I|re.S)
    )

    bullet=None
    m=re.search(r"newline-separated list of items.*?use\s+(.+?)\s*(?:instead|as the marker|\.)",text,re.I|re.S)
    if m:
        candidate=" ".join(m.group(1).split()).strip(" '"")
        if candidate and len(candidate)<=32:
            bullet=candidate

    subbul=bool(re.search(r"bullet points.*denoted by\s*\*.*sub-bullet.*denoted by\s*-",text,re.I|re.S))
    somebul=bool(re.search(r"at least two sentences.*followed by at least two.*bullet points",text,re.I|re.S))
    italics=bool(re.search(r"(?:section|response).*thesis statement in italics.*HTML",text,re.I|re.S))
    para=bool(re.search(r"at least two paragraphs.*each paragraph ends with.*same word it started with",text,re.I|re.S))
    noadj=bool(re.search(r"no two consecutive words.*same first letter",text,re.I))

    inc=None
    m=re.search(r"each sentence must contain exactly\s+(\d+)\s+more words than the previous",text,re.I)
    if m:
        inc=int(m.group(1))

    kw_sent=None
    m=re.search(r"(?:include|contain) keyword\s+[\"']([^\"']+)[\"']\s+in the\s+(\d+)(?:st|nd|rd|th|-th)\s+sentence",text,re.I)
    if m:
        kw_sent=(m.group(1),int(m.group(2)))

    kw_pos=None
    m=re.search(
        r"(?:include|contain) keyword\s+[\"']([^\"']+)[\"']\s+in the\s+(\d+)(?:st|nd|rd|th|-th)\s+sentence.*?"
        r"(\d+)(?:st|nd|rd|th|-th)\s+word",
        text,re.I|re.S,
    )
    if m:
        kw_pos=(m.group(1),int(m.group(2)),int(m.group(3)))

    repeated=None
    m=re.search(r"second word.*second to last word.*(?:be|should be)\s+(?:the word\s+)?[\"']([^\"']+)[\"']",text,re.I|re.S)
    if m:
        repeated=m.group(1)

    if no_ws and newline:
        raise ConstraintV2Error("CONTRADICTORY_WHITESPACE_CONSTRAINTS")
    if ratio and balanced:
        raise ConstraintV2Error("CONTRADICTORY_SENTENCE_RATIO_CONSTRAINTS")
    if no_ws and base.min_words is not None and base.min_words>1:
        raise ConstraintV2Error("NO_WHITESPACE_WITH_MULTIWORD_REQUIREMENT")

    extra=ExtraConstraints(
        no_whitespace=no_ws,
        title_case=title,
        newline_words=newline,
        sentence_ratio_2_to_1=ratio,
        sentence_types_balanced=balanced,
        punctuation_cover=punct,
        nested_delimiter_depth=depth,
        max_word_repeat=maxrep,
        min_pronouns=minpro,
        allowed_options=options,
        require_output_template=template,
        bullet_marker=bullet,
        require_sub_bullets=subbul,
        require_sentence_then_bullets=somebul,
        require_italic_thesis=italics,
        paragraph_cycle=para,
        sentence_word_increment=inc,
        no_same_initial_adjacent=noadj,
        keyword_sentence=kw_sent,
        keyword_position=kw_pos,
        repeated_position_word=repeated,
    )
    return Program(base=base,extra=extra)

def _delimiter_depth(value: str) -> int:
    pairs={')':'(',']':'[','}':'{'}
    stack=[]
    best=0
    for ch in value:
        if ch in "([{":
            stack.append(ch)
            best=max(best,len(stack))
        elif ch in pairs:
            if not stack or stack[-1]!=pairs[ch]:
                return -1
            stack.pop()
    return best if not stack else -1

def validate_program(response: str, p: Program) -> tuple[bool,list[str]]:
    value=str(response or "")
    ok,errors=v1.validate_response(value,p.base)
    errors=list(errors)
    e=p.extra
    words=_words(value)

    if e.no_whitespace and any(ch.isspace() for ch in value):
        errors.append("NO_WHITESPACE")
    if e.title_case:
        for w in words:
            if w and not (w[0].isupper() and (len(w)==1 or w[1:].islower())):
                errors.append("TITLE_CASE"); break
    if e.newline_words:
        lines=[ln.strip() for ln in value.splitlines() if ln.strip()]
        if not lines or any(len(_words(ln))!=1 for ln in lines) or len(lines)!=len(words):
            errors.append("NEWLINE_WORDS")

    sents=_sentences(value)
    if e.sentence_ratio_2_to_1:
        d=sum(s.rstrip().endswith(".") for s in sents)
        q=sum(s.rstrip().endswith("?") for s in sents)
        if q<1 or d!=2*q:
            errors.append("SENTENCE_RATIO_2_TO_1")
    if e.sentence_types_balanced:
        d=sum(s.rstrip().endswith(".") for s in sents)
        q=sum(s.rstrip().endswith("?") for s in sents)
        x=sum(s.rstrip().endswith("!") for s in sents)
        if d<1 or not (d==q==x):
            errors.append("SENTENCE_TYPES_BALANCED")
    if e.punctuation_cover:
        for ch in ".,!?;:":
            if ch not in value:
                errors.append("PUNCTUATION_COVER"); break
        if "?!" not in value and "!?" not in value and "‽" not in value:
            errors.append("INTERROBANG")
    if e.nested_delimiter_depth is not None and _delimiter_depth(value)<e.nested_delimiter_depth:
        errors.append("NESTED_DELIMITER_DEPTH")

    lower=[w.lower() for w in words]
    counts=Counter(lower)
    if e.max_word_repeat is not None and counts and max(counts.values())>e.max_word_repeat:
        errors.append("MAX_WORD_REPEAT")
    if e.min_pronouns is not None and sum(w in _PRONOUNS for w in lower)<e.min_pronouns:
        errors.append("MIN_PRONOUNS")
    if e.allowed_options and value.strip() not in e.allowed_options:
        errors.append("ALLOWED_OPTIONS")
    if e.require_output_template:
        if not all(x in value for x in ("My Answer:","My Conclusion:","Future Outlook:")):
            errors.append("OUTPUT_TEMPLATE")
    if e.bullet_marker is not None:
        starts=[ln for ln in value.splitlines() if ln.strip().startswith(e.bullet_marker)]
        if len(starts)<2:
            errors.append("BULLET_MARKER")
    if e.require_sub_bullets:
        blocks=value.splitlines()
        top=[i for i,ln in enumerate(blocks) if ln.lstrip().startswith("*")]
        if not top:
            errors.append("SUB_BULLETS")
        else:
            for idx,i in enumerate(top):
                end=top[idx+1] if idx+1<len(top) else len(blocks)
                if not any(blocks[j].lstrip().startswith("-") for j in range(i+1,end)):
                    errors.append("SUB_BULLETS"); break
    if e.require_sentence_then_bullets:
        bullet_start=next((i for i,ln in enumerate(value.splitlines()) if ln.lstrip().startswith("*")),None)
        if bullet_start is None:
            errors.append("SENTENCE_THEN_BULLETS")
        else:
            prefix="\n".join(value.splitlines()[:bullet_start])
            bullets=sum(ln.lstrip().startswith("*") for ln in value.splitlines()[bullet_start:])
            if len(_sentences(prefix))<2 or bullets<2:
                errors.append("SENTENCE_THEN_BULLETS")
    if e.require_italic_thesis:
        if not re.search(r"<(?:i|em)>\s*[^<]+\s*</(?:i|em)>\s*\S+",value,re.I|re.S):
            errors.append("ITALIC_THESIS")
    if e.paragraph_cycle:
        paras=[x.strip() for x in value.split("\n\n") if x.strip()]
        if len(paras)<2:
            errors.append("PARAGRAPH_CYCLE")
        else:
            for para in paras:
                ws=[w.lower() for w in _words(para)]
                if not ws or ws[0]!=ws[-1]:
                    errors.append("PARAGRAPH_CYCLE"); break
    if e.sentence_word_increment is not None:
        counts_sent=[len(_words(s)) for s in sents]
        if len(counts_sent)<2 or any(counts_sent[i+1]!=counts_sent[i]+e.sentence_word_increment for i in range(len(counts_sent)-1)):
            errors.append("SENTENCE_WORD_INCREMENT")
    if e.no_same_initial_adjacent:
        for a,b in zip(lower,lower[1:]):
            if a and b and a[0]==b[0]:
                errors.append("NO_SAME_INITIAL_ADJACENT"); break
    if e.keyword_sentence is not None:
        word,n=e.keyword_sentence
        if len(sents)<n or word.lower() not in sents[n-1].lower():
            errors.append("KEYWORD_SENTENCE")
    if e.keyword_position is not None:
        word,n,m=e.keyword_position
        if len(sents)<n:
            errors.append("KEYWORD_POSITION")
        else:
            sw=[w.lower() for w in _words(sents[n-1])]
            if len(sw)<m or sw[m-1]!=word.lower():
                errors.append("KEYWORD_POSITION")
    if e.repeated_position_word is not None:
        if len(words)<4 or words[1]!=e.repeated_position_word or words[-2]!=e.repeated_position_word:
            errors.append("REPEATED_POSITION_WORD")

    return (not errors,errors)

def _seed_candidates(instruction: str, p: Program) -> list[str]:
    e=p.extra
    candidates=[]

    base=v1.synthesize_formal_only(instruction)
    if base.get("response"):
        candidates.append(str(base["response"]))

    if p.base.exact_response is not None:
        candidates.append(p.base.exact_response)
    if e.allowed_options:
        candidates.extend(e.allowed_options)
    if e.no_whitespace:
        candidates.append("Alpha")
    if e.title_case:
        candidates.append("Alpha Beta")
    if e.newline_words:
        candidates.append("alpha\nbeta")
    if e.sentence_ratio_2_to_1:
        candidates.append("Alpha. Beta. Gamma?")
    if e.sentence_types_balanced:
        candidates.append("Alpha. Beta? Gamma!")
    if e.punctuation_cover:
        candidates.append("Alpha, beta; gamma: delta?! End.")
    if e.nested_delimiter_depth:
        candidates.append("([{((alpha))}])")
    if e.require_output_template:
        candidates.append("My Answer: Alpha My Conclusion: Beta Future Outlook: Gamma")
    if e.bullet_marker:
        candidates.append(f"{e.bullet_marker} alpha\n{e.bullet_marker} beta")
    if e.require_sub_bullets:
        candidates.append("* alpha\n- beta\n* gamma\n- delta")
    if e.require_sentence_then_bullets:
        candidates.append("Alpha. Beta.\n* gamma\n* delta")
    if e.require_italic_thesis:
        candidates.append("<i>Thesis</i> body")
    if e.paragraph_cycle:
        candidates.append("alpha middle alpha\n\nbeta middle beta")
    if e.sentence_word_increment is not None:
        n=e.sentence_word_increment
        first=["alpha"]
        second=["beta"]+["gamma"+str(i) for i in range(n)]
        candidates.append(" ".join(first)+". "+" ".join(second)+".")
    if e.no_same_initial_adjacent:
        candidates.append("alpha beta cedar delta")
    if e.keyword_sentence is not None:
        word,n=e.keyword_sentence
        ss=[]
        for i in range(1,n+1):
            ss.append((word if i==n else "alpha")+ ".")
        candidates.append(" ".join(ss))
    if e.keyword_position is not None:
        word,n,m=e.keyword_position
        ss=[]
        for i in range(1,n+1):
            ws=[f"w{i}x{j}" for j in range(1,max(m,2)+1)]
            if i==n:
                ws[m-1]=word
            ss.append(" ".join(ws)+".")
        candidates.append(" ".join(ss))
    if e.repeated_position_word is not None:
        k=e.repeated_position_word
        candidates.append(f"alpha {k} beta {k} gamma")

    if e.min_pronouns is not None:
        candidates.append(" ".join(["I"]*e.min_pronouns))
    if e.max_word_repeat is not None:
        candidates.append("alpha beta cedar delta")

    candidates += ["alpha","Alpha.","alpha beta","Run.","alpha beta cedar delta"]

    # Small generic composition closure: concatenate compatible seed shapes
    # using three neutral separators. Exact post-validation decides admissibility.
    seeds=list(dict.fromkeys(x for x in candidates if x))
    for a in seeds[:12]:
        for b in seeds[:12]:
            if a==b:
                continue
            candidates.extend([a+" "+b,a+"\n"+b])
            if len(candidates)>350:
                break
        if len(candidates)>350:
            break
    return list(dict.fromkeys(candidates))

def synthesize_formal_v2(instruction: str) -> dict[str,Any]:
    try:
        p=compile_program(instruction)
    except (v1.ConstraintError,ConstraintV2Error) as exc:
        return {
            "schema":SCHEMA,"status":"BLOCKED","response":None,
            "validation_errors":[type(exc).__name__+":"+str(exc)],
            "semantic_seed_required":True,"model_dependency_count":0,
        }

    for candidate in _seed_candidates(instruction,p):
        ok,errors=validate_program(candidate,p)
        if ok:
            return {
                "schema":SCHEMA,
                "status":"FORMAL_CONSTRAINTS_SATISFIED",
                "response":candidate,
                "base_constraints":asdict(p.base),
                "extra_constraints":asdict(p.extra),
                "validation_errors":[],
                "semantic_seed_required":p.base.exact_response is None,
                "model_dependency_count":0,
                "hard_nonclaim":"FORMAL_OUTPUT_CONSTRAINT_SATISFACTION_DOES_NOT_BY_ITSELF_PROVE_SEMANTIC_TASK_QUALITY",
            }

    return {
        "schema":SCHEMA,
        "status":"BLOCKED",
        "response":None,
        "base_constraints":asdict(p.base),
        "extra_constraints":asdict(p.extra),
        "validation_errors":["NO_CONSTRUCTIVE_WITNESS_IN_BOUNDED_GENERIC_CANDIDATE_SET"],
        "semantic_seed_required":True,
        "model_dependency_count":0,
    }

def run(args: dict, root=None) -> dict:
    return synthesize_formal_v2(str((args or {}).get("instruction") or ""))

if __name__=="__main__":
    import argparse,json
    ap=argparse.ArgumentParser()
    ap.add_argument("instruction")
    ns=ap.parse_args()
    print(json.dumps(synthesize_formal_v2(ns.instruction),indent=2,sort_keys=True))
