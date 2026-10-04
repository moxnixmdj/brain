#!/usr/bin/env python3
"""Prompt-only inversion for the pinned legacy LiveBench IFEval grammar.

Source authority:
LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
livebench/if_runner/instruction_following_eval/instructions.py
blob 4997bab885a676d92545fd91a9a20b48d234a2b2

No terminal question ids, kwargs, prompts, responses, or scores are used here.
"""
from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_PROMPT_INVERTER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

LANGUAGE_NAME_TO_CODE = {
    "English":"en","Spanish":"es","Portuguese":"pt","Arabic":"ar","Hindi":"hi",
    "French":"fr","Russian":"ru","German":"de","Japanese":"ja","Italian":"it",
    "Bengali":"bn","Ukrainian":"uk","Thai":"th","Urdu":"ur","Tamil":"ta",
    "Telugu":"te","Bulgarian":"bg","Korean":"ko","Polish":"pl","Hebrew":"he",
    "Persian":"fa","Vietnamese":"vi","Nepali":"ne","Swahili":"sw","Kannada":"kn",
    "Marathi":"mr","Gujarati":"gu","Punjabi":"pa","Malayalam":"ml","Finnish":"fi",
}

@dataclass(frozen=True)
class Match:
    instruction_id: str
    start: int
    end: int
    slots: dict[str, Any]
    matched_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _m(pattern: str, prompt: str, instruction_id: str, convert=None):
    out=[]
    for m in re.finditer(pattern,prompt,flags=re.I|re.S):
        slots={k:v.strip() for k,v in m.groupdict().items() if v is not None}
        if convert:
            slots=convert(slots)
        out.append(Match(instruction_id,m.start(),m.end(),slots,m.group(0)))
    return out

def _list_slot(name: str):
    def conv(slots):
        raw=slots[name]
        try:
            value=ast.literal_eval(raw)
        except Exception:
            value=None
        if isinstance(value,(list,tuple)) and all(isinstance(x,str) for x in value):
            slots[name]=list(value)
        else:
            slots[name]=[x.strip(" \"'") for x in raw.strip("[]").split(",") if x.strip()]
        return slots
    return conv

def _ints(*names):
    def conv(slots):
        for n in names:
            if n in slots:
                slots[n]=int(slots[n])
        return slots
    return conv

def recognize(prompt: str) -> list[dict[str, Any]]:
    p=str(prompt or "")
    if not p:
        return []
    c=[]

    c += _m(r"Include keywords (?P<keywords>\[[^\]]*\]) in the response\.",p,"keywords:existence",_list_slot("keywords"))
    c += _m(r"In your response, the word (?P<keyword>.+?) should appear (?P<relation>less than|at least) (?P<frequency>\d+) times\.",p,"keywords:frequency",_ints("frequency"))
    c += _m(r"Do not include keywords (?P<forbidden_words>\[[^\]]*\]) in the response\.",p,"keywords:forbidden_words",_list_slot("forbidden_words"))
    c += _m(r"In your response, the letter (?P<letter>[A-Za-z]) should appear (?P<let_relation>less than|at least) (?P<let_frequency>\d+) times\.",p,"keywords:letter_frequency",_ints("let_frequency"))

    def lang(slots):
        name=slots.pop("language_name")
        slots["language"]=LANGUAGE_NAME_TO_CODE.get(name,name)
        slots["language_name"]=name
        return slots
    c += _m(r"Your ENTIRE response should be in (?P<language_name>[A-Za-z]+) language, no other language is allowed\.",p,"language:response_language",lang)

    c += _m(r"Your response should contain (?P<relation>less than|at least) (?P<num_sentences>\d+) sentences\.",p,"length_constraints:number_sentences",_ints("num_sentences"))
    c += _m(r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",p,"length_constraints:number_paragraphs",_ints("num_paragraphs"))
    c += _m(r"Answer with (?P<relation>less than|at least) (?P<num_words>\d+) words\.",p,"length_constraints:number_words",_ints("num_words"))
    c += _m(r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\\\n\\\\n' in python\. Paragraph (?P<nth_paragraph>\d+) must start with word (?P<first_word>[^\s.]+)\.",p,"length_constraints:nth_paragraph_first_word",_ints("num_paragraphs","nth_paragraph"))

    c += _m(r"The response must contain at least (?P<num_placeholders>\d+) placeholders represented by square brackets, such as \[address\]\.",p,"detectable_content:number_placeholders",_ints("num_placeholders"))
    c += _m(r"At the end of your response, please explicitly add a postscript starting with (?P<postscript_marker>P\.P\.S|P\.S\.|[^\s.]+)",p,"detectable_content:postscript")

    c += _m(r"Your answer must contain exactly (?P<num_bullets>\d+) bullet points\. Use the markdown bullet points such as:",p,"detectable_format:number_bullet_lists",_ints("num_bullets"))
    c += _m(r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)",p,"detectable_format:constrained_response")
    c += _m(r"Highlight at least (?P<num_highlights>\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.",p,"detectable_format:number_highlighted_sections",_ints("num_highlights"))
    c += _m(r"Your response must have (?P<num_sections>\d+) sections\. Mark the beginning of each section with (?P<section_spliter>Section|SECTION) X, such as:",p,"detectable_format:multiple_sections",_ints("num_sections"))
    c += _m(r"Entire output should be wrapped in JSON format\. You can use markdown ticks such as ```\.",p,"detectable_format:json_format")
    c += _m(r"Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>\.",p,"detectable_format:title")
    c += _m(r"Give two different responses\. Responses and only responses should be separated by 6 asterisk symbols: \*\*\*\*\*\*\.",p,"combination:two_responses")

    repeat_patterns=[
        r"First repeat the request word for word without change, then give your answer \(1\. do not say any words or characters before repeating the request; 2\. the request you need to repeat does not include this sentence\)",
        r"First, repeat the request word for word without change, then give your answer \(Notes?: 1\. do NOT say any words or characters before repeating the request; 2\. the request you need to repeat does not include this sentence\)",
        r"First repeat the question above without change of words, then give your answer\.",
    ]
    for pat in repeat_patterns:
        for m in re.finditer(pat,p,flags=re.I|re.S):
            base=p[:m.start()].rstrip()
            c.append(Match("combination:repeat_prompt",m.start(),m.end(),{"prompt_to_repeat":base},m.group(0)))

    c += _m(r"Finish your response with this exact phrase (?P<end_phrase>.+?)\. No other words should follow this phrase\.",p,"startend:end_checker")
    c += _m(r"In your response, words with all capital letters should appear (?P<capital_relation>less than|at least) (?P<capital_frequency>\d+) times\.",p,"change_case:capital_word_frequency",_ints("capital_frequency"))
    c += _m(r"Your entire response should be in English, and in all capital letters\.",p,"change_case:english_capital")
    c += _m(r"Your entire response should be in English, and in all lowercase letters\. No capital letters are allowed\.",p,"change_case:english_lowercase")
    c += _m(r"In your entire response, refrain from the use of any commas\.",p,"punctuation:no_comma")
    c += _m(r"Wrap your entire response with double quotation marks\.",p,"startend:quotation")

    # Prefer longest duplicate match for a checker family; terminal runtime never receives IDs/kwargs.
    c.sort(key=lambda x:(x.instruction_id,-(x.end-x.start),x.start))
    chosen=[]
    seen=set()
    for item in c:
        if item.instruction_id in seen:
            continue
        chosen.append(item); seen.add(item.instruction_id)
    chosen.sort(key=lambda x:(x.start,x.end,x.instruction_id))
    return [x.to_dict() for x in chosen]

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    prompt=str((args or {}).get("prompt") or "")
    return {
        "schema":SCHEMA,
        "matches":recognize(prompt),
        "terminal_data_used":False,
        "hidden_kwargs_used":False,
        "model_dependency_count":0,
    }
