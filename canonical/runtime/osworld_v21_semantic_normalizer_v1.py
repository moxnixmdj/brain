"""Task-independent semantic normalization for the OSWorld capability stack.

Maps a bounded set of ordinary action paraphrases onto already-verified canonical
operations. Quoted spans are preserved byte-for-byte so user data is never
rewritten as control language.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_SEMANTIC_NORMALIZER_V1"

_RULES=(
    ("CLICK_TAP", re.compile(r"\b(?:tap|activate|hit)\b", re.I), "click"),
    ("OPEN_VISIT", re.compile(r"\b(?:visit|launch|browse\s+to|go\s+to)\b", re.I), "open"),
    ("SEARCH_LOOK_FOR", re.compile(r"\b(?:look\s+for|look\s+up|search\s+up)\b", re.I), "search for"),
    ("FILL_IN", re.compile(r"\bfill\s+in\b", re.I), "fill"),
    ("SELECT_PICK", re.compile(r"\bpick\b", re.I), "select"),
    ("EDIT_MODIFY", re.compile(r"\b(?:modify|amend)\b", re.I), "edit"),
    ("DELETE_ERASE", re.compile(r"\berase\b", re.I), "delete"),
    ("RUN_EXECUTE", re.compile(r"\bexecute\b", re.I), "run"),
)

_QUOTE_RE=re.compile(r'("([^"\\]|\\.)*"|“[^”]*”|\'([^\'\\]|\\.)*\')')

def normalize_instruction(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        raise ValueError("INSTRUCTION_REQUIRED")
    parts=_QUOTE_RE.split(text)
    # re.split with capture groups emits nested capture fragments; rebuild using finditer
    chunks=[]
    pos=0
    for m in _QUOTE_RE.finditer(text):
        if m.start()>pos:
            chunks.append((False,text[pos:m.start()]))
        chunks.append((True,m.group(0)))
        pos=m.end()
    if pos<len(text):
        chunks.append((False,text[pos:]))
    if not chunks:
        chunks=[(False,text)]

    applied=[]
    out=[]
    for protected,chunk in chunks:
        if protected:
            out.append(chunk)
            continue
        current=chunk
        for rule_id,pattern,replacement in _RULES:
            new,count=pattern.subn(replacement,current)
            if count:
                applied.extend([rule_id]*count)
                current=new
        out.append(current)

    normalized="".join(out)
    return {
        "schema":SCHEMA,
        "original":text,
        "normalized":normalized,
        "changed":normalized!=text,
        "applied_rules":applied,
        "task_specific_policy_data":False,
        "external_model_dependency":False,
    }
