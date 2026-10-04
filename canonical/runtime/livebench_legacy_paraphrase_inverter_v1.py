#!/usr/bin/env python3
"""Paraphrase-tolerant visible-prompt inverter for legacy LiveBench IFEval.

Design constraints:
- visible prompt text only;
- no instruction_id_list, hidden kwargs, question ids, answers, or scorer feedback;
- public classic IFEval wording is a nonterminal development corpus;
- return every recovered checker instance, including repeated checker families;
- fail closed on parameter-bearing cues that cannot be reconstructed exactly.

This is a candidate parser. It earns no terminal/acceptance credit until an
independent public-corpus verifier proves the advertised coverage.
"""
from __future__ import annotations

import ast
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_PARAPHRASE_INVERTER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PUBLIC_CLASSIC_IFEVAL_COMMIT = "e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
PUBLIC_CLASSIC_IFEVAL_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"

LEGACY_IDS = {
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "language:response_language",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
    "startend:quotation",
}

LANG = {
    "english":"en","spanish":"es","portuguese":"pt","arabic":"ar","hindi":"hi",
    "french":"fr","russian":"ru","german":"de","japanese":"ja","italian":"it",
    "bengali":"bn","ukrainian":"uk","thai":"th","urdu":"ur","tamil":"ta",
    "telugu":"te","bulgarian":"bg","korean":"ko","polish":"pl","hebrew":"he",
    "persian":"fa","vietnamese":"vi","nepali":"ne","swahili":"sw","kannada":"kn",
    "marathi":"mr","gujarati":"gu","punjabi":"pa","malayalam":"ml","finnish":"fi",
}
NUM_WORD = {
    "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,
    "nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,
    "fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,
    "twenty":20,"thirty":30,"forty":40,"fifty":50,
}

_REPEAT_LINES = [
    re.compile(r"^\s*First repeat the request word for word without change.*$", re.I),
    re.compile(r"^\s*First repeat the sentence above word for word without change.*$", re.I),
    re.compile(r"^\s*First repeat the exact request above.*$", re.I),
    re.compile(r"^\s*First repeat the request above.*$", re.I),
    re.compile(r"^\s*Repeat the (?:request|sentence) above.*$", re.I),
]

def _num(s: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    if s in NUM_WORD:
        return NUM_WORD[s]
    raise ValueError(s)

def _quoted_values(s: str) -> list[str]:
    vals = []
    for a,b,c in re.findall(r'"([^"]+)"|\'([^\']+)\'|“([^”]+)”', s):
        vals.append(a or b or c)
    return vals

def _dedupe(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen=set(); out=[]
    for m in sorted(matches, key=lambda x:(x["start"],x["end"],x["instruction_id"],repr(sorted(x["kwargs"].items())))):
        key=(m["instruction_id"], tuple(sorted((k,repr(v)) for k,v in m["kwargs"].items())))
        if key in seen:
            continue
        seen.add(key); out.append(m)
    return out

def _add(out, iid, start, end, kwargs=None, route="PARAPHRASE_REGEX"):
    out.append({
        "instruction_id": iid, "start": int(start), "end": int(end),
        "kwargs": dict(kwargs or {}), "route": route,
    })

def _relation_from_phrase(phrase: str, n: int) -> tuple[str,int]:
    p=phrase.lower()
    if any(x in p for x in ("more than","greater than","over ")):
        return "at least", n+1
    if any(x in p for x in ("at least","or more","minimum","no fewer than")):
        return "at least", n
    if any(x in p for x in ("at most","or less","no more than","maximum")):
        return "less than", n+1
    return "less than", n

def _recover_repeat_prompt(prompt: str) -> str | None:
    # Public legacy IFEval puts the repeat meta-instruction after the request.
    # Preserve all prior visible request text exactly modulo outer whitespace.
    for pat in _REPEAT_LINES:
        m=pat.search(prompt)
        if m:
            prefix=prompt[:m.start()].strip()
            return prefix or None
    # multiline variants with a blank line and meta wording
    m=re.search(
        r"(?:\n\s*)+(?:First\s+)?repeat\s+(?:the\s+)?(?:exact\s+)?(?:request|sentence)"
        r"(?:\s+above)?(?:\s+word\s+for\s+word)?(?:\s+without\s+change)?[^.\n]*(?:\.[^\n]*)?",
        prompt, re.I
    )
    if m:
        prefix=prompt[:m.start()].strip()
        return prefix or None
    return None

def recognize(prompt: str) -> dict[str, Any]:
    text=str(prompt or "")
    low=text.lower()
    out: list[dict[str,Any]]=[]
    unresolved=[]

    # Fixed/static families.
    for m in re.finditer(r"(?:do not|don't|should not|must not|not allowed to|refrain from|avoid)\s+(?:the\s+)?(?:use of\s+|using\s+|use\s+)?(?:any\s+)?commas?\b|without\s+(?:using\s+)?(?:any\s+)?commas?\b", text, re.I):
        _add(out,"punctuation:no_comma",m.start(),m.end())

    if re.search(r"(?:json\s+format|json\s+block|wrapped\s+in\s+json|output\s+(?:in|as)\s+json)", text, re.I):
        m=re.search(r"(?:json\s+format|json\s+block|wrapped\s+in\s+json|output\s+(?:in|as)\s+json)", text, re.I)
        _add(out,"detectable_format:json_format",m.start(),m.end())

    if re.search(r"(?:double\s+angular\s+brackets|<<\s*(?:title|[^>\n]{1,40})\s*>>)", text, re.I):
        m=re.search(r"(?:double\s+angular\s+brackets|<<\s*(?:title|[^>\n]{1,40})\s*>>)", text, re.I)
        _add(out,"detectable_format:title",m.start(),m.end())

    # Entire response wrapped in double quotation marks.
    qpat=re.search(r"(?:wrap|wrapped|put|surround).{0,55}(?:entire|whole).{0,30}(?:response|answer|reply).{0,35}(?:double\s+(?:quotation\s+marks|quotes)|quotation\s+marks)|double\s+(?:quotation\s+marks|quotes).{0,35}(?:around|surrounding).{0,35}(?:entire|whole)", text, re.I|re.S)
    if qpat:
        _add(out,"startend:quotation",qpat.start(),qpat.end())

    # Constrained fixed answer choices.
    if "my answer is yes." in low and "my answer is no." in low and "my answer is maybe." in low:
        i=min(low.index("my answer is yes."),low.index("my answer is no."),low.index("my answer is maybe."))
        _add(out,"detectable_format:constrained_response",i,i+20)

    # Two responses separated by six asterisks. Tolerate prose typo saying 6 while
    # displaying 7; scorer still splits on the fixed six-star token.
    tw=re.search(r"(?:two|2)\s+(?:different\s+)?(?:responses|answers|critiques|versions|limericks|jokes).{0,120}(?:6|six)\s+asterisk|separate.{0,80}(?:responses|answers|them|two).{0,50}\*{6,}", text, re.I|re.S)
    if tw:
        _add(out,"combination:two_responses",tw.start(),tw.end())

    # Repeat prompt and exact visible prefix recovery.
    rp=_recover_repeat_prompt(text)
    if rp is not None:
        m=re.search(r"(?:repeat).{0,100}(?:request|sentence|exact request)", text[len(rp):], re.I|re.S)
        st=len(rp)+(m.start() if m else 0); en=len(rp)+(m.end() if m else 1)
        _add(out,"combination:repeat_prompt",st,en,{"prompt_to_repeat":rp},"VISIBLE_PREFIX_RECOVERY")

    # English case constraints.
    lc=re.search(r"(?:all|entirely|only)\s+lower(?:\s*case|case)|all\s+lowercase|without\s+(?:using\s+)?capital\s+letters|no\s+capital\s+letters|lowercase\s+letters", text, re.I)
    if lc:
        _add(out,"change_case:english_lowercase",lc.start(),lc.end())
    uc=re.search(r"(?:all|entirely|only)\s+capital\s+letters|all\s+caps\b|all\s+uppercase|no\s+lowercase\s+letters|only\s+capital\s+letters", text, re.I)
    if uc:
        _add(out,"change_case:english_capital",uc.start(),uc.end())

    # Response language. Require exclusivity cue to avoid ordinary content mentions.
    lang_names="|".join(sorted((re.escape(x) for x in LANG), key=len, reverse=True))
    for m in re.finditer(rf"(?:only\s+(?:the\s+)?|entirely\s+in\s+|entire\s+response\s+(?:should\s+be\s+)?in\s+|using\s+only\s+(?:the\s+)?|in\s+the\s+)(?P<lang>{lang_names})(?:\s+language)?(?:\s*,?\s*(?:no\s+other\s+language|and\s+no\s+other\s+language))?", text, re.I):
        window=text[m.start():min(len(text),m.end()+80)].lower()
        pre=text[max(0,m.start()-50):m.end()].lower()
        if any(x in window or x in pre for x in ("only","no other language","entirely","entire response")):
            name=m.group("lang").lower()
            _add(out,"language:response_language",m.start(),m.end(),{"language":LANG[name]})

    # Number of words.
    word_patterns=[
        r"(?P<rel>at least|more than|no fewer than|less than|fewer than|at most|no more than|under)\s+(?P<n>\d+)\s+words?\b",
        r"(?P<n>\d+)\s*(?P<plus>\+)\s*words?\b",
        r"(?P<n>\d+)\s+or\s+(?P<dir>more|fewer|less)\s+words?\b",
        r"(?:maximum|max)\s+(?:of\s+)?(?P<n>\d+)\s+words?\b",
    ]
    for pat in word_patterns:
        for m in re.finditer(pat,text,re.I):
            gd=m.groupdict(); n=int(gd["n"])
            if gd.get("plus"): rel,val="at least",n
            elif gd.get("dir"):
                rel,val=("at least",n) if gd["dir"].lower()=="more" else ("less than",n+1)
            elif "maximum" in m.group(0).lower() or re.search(r"\bmax\b",m.group(0),re.I):
                rel,val="less than",n+1
            else: rel,val=_relation_from_phrase(gd.get("rel") or "",n)
            _add(out,"length_constraints:number_words",m.start(),m.end(),{"relation":rel,"num_words":val})

    # Number of sentences.
    sent_patterns=[
        r"(?P<rel>at least|more than|less than|fewer than|at most|no more than|under)\s+(?P<n>\d+)\s+sentences?\b",
        r"(?P<n>\d+)\s+or\s+(?P<dir>more|fewer|less)\s+sentences?\b",
    ]
    for pat in sent_patterns:
        for m in re.finditer(pat,text,re.I):
            gd=m.groupdict(); n=int(gd["n"])
            if gd.get("dir"): rel,val=("at least",n) if gd["dir"].lower()=="more" else ("less than",n+1)
            else: rel,val=_relation_from_phrase(gd.get("rel") or "",n)
            _add(out,"length_constraints:number_sentences",m.start(),m.end(),{"relation":rel,"num_sentences":val})
    for m in re.finditer(r"(?:have|contain|write)\s+(?:more\s+than\s+)?(?P<n>\d+)\s+sentences?\b",text,re.I):
        if not any(x["instruction_id"]=="length_constraints:number_sentences" and abs(x["start"]-m.start())<30 for x in out):
            n=int(m.group("n")); phrase=m.group(0).lower()
            rel,val=("at least",n+1) if "more than" in phrase else ("at least",n)
            _add(out,"length_constraints:number_sentences",m.start(),m.end(),{"relation":rel,"num_sentences":val})

    # Exact paragraph count with *** divider.
    for m in re.finditer(r"(?:exactly\s+|there\s+(?:should|must)\s+be\s+|provide.{0,20}in\s+)?(?P<n>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:paragraphs?|sections?).{0,120}(?:\*{3}|markdown\s+divider)", text, re.I|re.S):
        n=_num(m.group("n"))
        if "***" in m.group(0) or "divider" in m.group(0).lower():
            _add(out,"length_constraints:number_paragraphs",m.start(),m.end(),{"num_paragraphs":n})

    # nth paragraph first word and exact paragraph count.
    nth_words={"first":1,"second":2,"third":3,"fourth":4,"fifth":5,"sixth":6,"seventh":7,"last":-1}
    for m in re.finditer(r"(?P<nth>first|second|third|fourth|fifth|sixth|seventh|last|\d+(?:st|nd|rd|th)?)\s+paragraph\s+(?:must|should|has\s+to)\s+start\s+with\s+(?:the\s+)?word\s+[\"']?(?P<word>[A-Za-z][\w-]*)",text,re.I):
        raw=m.group("nth").lower()
        nth=int(re.match(r"\d+",raw).group()) if raw[0].isdigit() else nth_words[raw]
        # nearby exact paragraph total
        pre=text[max(0,m.start()-180):m.start()]
        nums=list(re.finditer(r"(?:exactly\s+)?(?P<n>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+paragraphs?",pre,re.I))
        if nums:
            total=_num(nums[-1].group("n"))
            if nth==-1: nth=total
            _add(out,"length_constraints:nth_paragraph_first_word",m.start(),m.end(),{"first_word":m.group("word").lower(),"num_paragraphs":total,"nth_paragraph":nth})
        else:
            unresolved.append({"instruction_id":"length_constraints:nth_paragraph_first_word","reason":"PARAGRAPH_TOTAL_NOT_RECOVERED","span":m.group(0)})

    # Placeholders.
    for m in re.finditer(r"at\s+least\s+(?P<n>\d+)\s+placeholders?\b|include\s+at\s+least\s+(?P<n2>\d+)\s+placeholders?\b", text,re.I):
        n=int(m.group("n") or m.group("n2"))
        _add(out,"detectable_content:number_placeholders",m.start(),m.end(),{"num_placeholders":n})

    # Highlighted sections.
    for m in re.finditer(r"(?:highlight|highlighted|at\s+least)\s+(?:at\s+least\s+)?(?P<n>\d+|two|three|four|five|six|seven|eight|nine|ten|fifteen)\s+(?:text\s+)?sections?.{0,80}(?:markdown|\*highlighted)|at\s+least\s+(?P<n2>\d+|two|three|four|five|six|seven|eight|nine|ten|fifteen)\s+sections?.{0,80}highlight",text,re.I|re.S):
        n=_num(m.group("n") or m.group("n2"))
        _add(out,"detectable_format:number_highlighted_sections",m.start(),m.end(),{"num_highlights":n})

    # Exact bullet count.
    for m in re.finditer(r"(?:exactly\s+|contain\s+exactly\s+|include\s+exactly\s+|write\s+exactly\s+)(?P<n>\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:very\s+short\s+)?bullet\s+points?\b|(?P<n2>\d+|two|three|four|five|six|seven|eight|nine|ten)\s+bullet\s+points?.{0,35}(?:exact|must|should)",text,re.I):
        n=_num(m.group("n") or m.group("n2"))
        _add(out,"detectable_format:number_bullet_lists",m.start(),m.end(),{"num_bullets":n})

    # Multiple sections labelled SECTION/PARAGRAPH X.
    for m in re.finditer(r"(?P<n>\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:sections?|paragraphs?).{0,100}(?P<label>SECTION|Section|PARAGRAPH)\s+X|(?:have|include|with)\s+(?P<n2>\d+|two|three|four|five|six|seven|eight|nine|ten)\s+sections?.{0,100}(?P<label2>SECTION|Section|PARAGRAPH)\s+X",text,re.I|re.S):
        n=_num(m.group("n") or m.group("n2"))
        lab=m.group("label") or m.group("label2")
        # preserve canonical visible capitalization where semantically relevant
        visible=re.search(r"(SECTION|Section|PARAGRAPH)\s+X",m.group(0))
        splitter=visible.group(1) if visible else lab
        _add(out,"detectable_format:multiple_sections",m.start(),m.end(),{"section_spliter":splitter,"num_sections":n})

    # Postscript marker.
    for m in re.finditer(r"(?:post\s*script|postscript|at\s+the\s+end.{0,30}){0,1}.{0,20}(?P<mark>P\.P\.S|P\.S\.)(?:\b|\s|$)",text,re.I):
        mark=m.group("mark").upper()
        if mark=="P.S": mark="P.S."
        _add(out,"detectable_content:postscript",m.start(),m.end(),{"postscript_marker":mark})

    # Exact ending phrase. Prefer quoted payload after strong end cue.
    end_patterns=[
        r"(?:finish|end)(?:\s+(?:your|the))?\s+(?:response|answer|poem|article)?\s*(?:with)?\s*(?:this|the)?\s*exact\s+phrase(?:\s+of)?\s*[:\"]*\s*[\"“](?P<x>[^\"”]+)[\"”]",
        r"(?:very\s+last\s+sentence|very\s+end).{0,50}(?:should|must)\s+(?:be|read)\s+[\"“](?P<x>[^\"”]+)[\"”]",
        r"(?:must|should)\s+end\s+with\s+(?:the\s+)?(?:exact\s+)?phrase\s+[\"“](?P<x>[^\"”]+)[\"”]",
    ]
    for pat in end_patterns:
        for m in re.finditer(pat,text,re.I|re.S):
            _add(out,"startend:end_checker",m.start(),m.end(),{"end_phrase":m.group("x").strip()})

    # Capital-word frequency.
    cap_patterns=[
        r"(?:words?\s+(?:with|in)\s+all\s+capital\s+letters|all[- ]caps\s+words?|words?\s+in\s+all\s+caps).{0,80}(?P<rel>at\s+least|less\s+than|at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+times?",
        r"(?P<rel>at\s+least|less\s+than|at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+(?:words?\s+)?(?:in\s+)?all\s+caps",
    ]
    for pat in cap_patterns:
        for m in re.finditer(pat,text,re.I|re.S):
            n=int(m.group("n")); rel,val=_relation_from_phrase(m.group("rel"),n)
            _add(out,"change_case:capital_word_frequency",m.start(),m.end(),{"capital_relation":rel,"capital_frequency":val})
    # "Use some words in all caps ... at most 10 times" implies at least one too.
    for m in re.finditer(r"use\s+some\s+words?\s+in\s+all\s+caps.{0,100}(?:at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+times?",text,re.I|re.S):
        n=int(m.group("n"))
        _add(out,"change_case:capital_word_frequency",m.start(),m.end(),{"capital_relation":"less than","capital_frequency":n+1})
        _add(out,"change_case:capital_word_frequency",m.start(),m.end(),{"capital_relation":"at least","capital_frequency":1})

    # Letter / symbol frequency.
    letter_patterns=[
        r"(?:the\s+)?letter\s+[\"']?(?P<char>[^\"'\s])[\"']?\s+(?:should|must)\s+appear\s+(?P<rel>at\s+least|less\s+than|at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+times?",
        r"(?P<rel>do\s+not\s+include|without)\s+the\s+letter\s+[\"']?(?P<char2>[^\"'\s])[\"']?",
        r"(?:contain|include)\s+(?P<n3>\d+)\s+or\s+more\s+(?P<kind>exclamation\s+marks?|hashtags?).{0,20}[\"']?(?P<char3>[!#])[\"']?",
        r"at\s+least\s+(?P<n4>\d+)\s+(?P<kind2>hashtags?).{0,30}[\"'](?P<char4>#)[\"']",
    ]
    for pat in letter_patterns:
        for m in re.finditer(pat,text,re.I|re.S):
            gd=m.groupdict()
            ch=gd.get("char") or gd.get("char2") or gd.get("char3") or gd.get("char4")
            if gd.get("char2"):
                rel,val="less than",1
            elif gd.get("n3") or gd.get("n4"):
                rel,val="at least",int(gd.get("n3") or gd.get("n4"))
            else:
                n=int(gd["n"]); rel,val=_relation_from_phrase(gd["rel"],n)
            _add(out,"keywords:letter_frequency",m.start(),m.end(),{"let_relation":rel,"letter":ch.lower(),"let_frequency":val})
    # "letter x should appear at most once" etc.
    for m in re.finditer(r"letter\s+[\"']?(?P<char>[A-Za-z])[\"']?\s+should\s+appear\s+at\s+most\s+(?P<n>once|twice|\d+)",text,re.I):
        n={"once":1,"twice":2}.get(m.group("n").lower(), int(m.group("n")) if m.group("n").isdigit() else 0)
        _add(out,"keywords:letter_frequency",m.start(),m.end(),{"let_relation":"less than","letter":m.group("char").lower(),"let_frequency":n+1})

    # Keyword frequency. Keep this before existence; frequency-bearing mentions
    # must not be double-counted as mere existence.
    freq_spans=[]
    freq_patterns=[
        r"(?:word|keyword)\s+[\"']?(?P<kw>[\w-]+)[\"']?\s+(?:should|must)\s+appear\s+(?P<rel>at\s+least|less\s+than|at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+times?",
        r"(?:use|include|mention)\s+(?:the\s+)?(?:word|keyword)\s+[\"']?(?P<kw>[\w-]+)[\"']?.{0,35}(?P<rel>at\s+least|more\s+than|less\s+than|at\s+most|no\s+more\s+than)\s+(?P<n>\d+)\s+times?",
        r"(?:word|keyword)\s+[\"']?(?P<kw>[\w-]+)[\"']?.{0,30}(?P<n>\d+)\s+or\s+more\s+times?",
        r"mention\s+(?:the\s+)?(?:word|keyword)\s+[\"'](?P<kw>[\w-]+)[\"']\s+for\s+more\s+than\s+(?P<n>\d+)\s+times?",
        r"include\s+(?:the\s+)?word\s+(?P<kw>[\w-]+)\s+at\s+least\s+(?P<n>\d+)\s+times?",
    ]
    for pat in freq_patterns:
        for m in re.finditer(pat,text,re.I|re.S):
            gd=m.groupdict(); n=int(gd["n"]); phrase=m.group(0).lower()
            if "or more" in phrase: rel,val="at least",n
            else: rel,val=_relation_from_phrase(gd.get("rel") or phrase,n)
            _add(out,"keywords:frequency",m.start(),m.end(),{"relation":rel,"keyword":gd["kw"].lower(),"frequency":val})
            freq_spans.append((m.start(),m.end()))

    # Forbidden words/lists.
    forb_patterns=[
        r"(?:do not|don't|must not|should not|avoid|without)\s+(?:include|including|use|using|say|mention)?\s*(?:the\s+)?(?:following\s+)?(?:keywords?|words?)\s*[:\-]?\s*(?P<body>[^\n.!?]+)",
        r"(?:the\s+)?(?:word|keyword)\s+[\"'](?P<one>[\w-]+)[\"']\s+(?:should|must)\s+not\s+appear",
        r"refrain\s+from\s+(?:using|mentioning)\s+(?:the\s+)?(?:word|keyword)\s+[\"']?(?P<one2>[\w-]+)",
    ]
    for pat in forb_patterns:
        for m in re.finditer(pat,text,re.I):
            gd=m.groupdict()
            vals=[]
            if gd.get("one") or gd.get("one2"): vals=[(gd.get("one") or gd.get("one2")).lower()]
            else:
                body=gd.get("body") or ""
                vals=_quoted_values(body)
                if not vals:
                    # comma-separated bare list after colon/cue
                    cand=re.split(r",|\band\b",body,flags=re.I)
                    vals=[re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9_-]+$","",x).lower() for x in cand]
                    vals=[x for x in vals if x and x not in {"response","reply","answer"}][:8]
            if vals:
                _add(out,"keywords:forbidden_words",m.start(),m.end(),{"forbidden_words":sorted(set(v.lower() for v in vals))})

    # Existence keywords. Require explicit include/mention/contain keyword/word cue,
    # then strip any token already captured by a frequency constraint.
    exist_patterns=[
        r"(?:include|contain|mention|use)\s+(?:the\s+)?(?:following\s+)?(?:keywords?|words?)\s*[:\-]?\s*(?P<body>[^\n.!?]+)",
        r"(?:must|should)\s+include\s+(?:the\s+)?(?:keywords?|words?)\s*(?P<body>[^\n.!?]+)",
    ]
    freq_kws={m["kwargs"]["keyword"] for m in out if m["instruction_id"]=="keywords:frequency"}
    forb_kws={v for m in out if m["instruction_id"]=="keywords:forbidden_words" for v in m["kwargs"]["forbidden_words"]}
    for pat in exist_patterns:
        for m in re.finditer(pat,text,re.I):
            body=m.group("body")
            if re.search(r"\b(?:at least|more than|less than|at most|times?|should appear)\b",body,re.I):
                continue
            vals=_quoted_values(body)
            if not vals:
                # Restrict bare extraction to short explicit keyword lists.
                if "keyword" in m.group(0).lower():
                    vals=[re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9_-]+$","",x).strip() for x in re.split(r",|\band\b",body,flags=re.I)]
                    vals=[x for x in vals if x][:5]
            vals=[v.lower() for v in vals if v.lower() not in freq_kws and v.lower() not in forb_kws]
            if vals:
                _add(out,"keywords:existence",m.start(),m.end(),{"keywords":sorted(vals)})

    matches=_dedupe(out)
    ids=[m["instruction_id"] for m in matches]
    unknown=[x for x in ids if x not in LEGACY_IDS]
    status="PASS_CANDIDATE" if not unresolved and not unknown else "FAIL_CLOSED"
    return {
        "schema":SCHEMA,
        "status":status,
        "matches":matches,
        "recognized_instruction_ids":ids,
        "recognized_instruction_instance_count":len(matches),
        "unresolved_parameter_cues":unresolved,
        "unknown_instruction_ids":unknown,
        "visible_prompt_only":True,
        "hidden_instruction_id_list_read":False,
        "hidden_kwargs_read":False,
        "terminal_case_metadata_read":False,
        "model_dependency_count":0,
        "network_used":False,
    }

def run(args: dict[str,Any], root=None) -> dict[str,Any]:
    return recognize(str((args or {}).get("prompt") or ""))

if __name__=="__main__":
    import argparse,json
    ap=argparse.ArgumentParser(); ap.add_argument("prompt")
    ns=ap.parse_args()
    print(json.dumps(recognize(ns.prompt),indent=2,ensure_ascii=False,sort_keys=True))
