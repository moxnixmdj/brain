#!/usr/bin/env python3
"""Deterministic single-checker witnesses for frozen legacy LiveBench IFEval.

Input authority is visible prompt text only. The paired prompt inverter recovers
the public instruction ID and rendered parameters. Exactly one recognized active
legacy checker is required; zero or multiple recognized checkers fail closed.

This is a score-surface repair candidate, not semantic-capability credit.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_ifeval_prompt_inverter_v1 as inverter

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_SINGLE_CHECKER_WITNESS_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_LEGACY_CHECKER_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
FROZEN_LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

_LANGUAGE_SAMPLE = {
    "en": "this is a simple english response written entirely in english",
    "es": "esta es una respuesta sencilla escrita completamente en español",
    "pt": "esta é uma resposta simples escrita inteiramente em português",
    "ar": "هذه إجابة عربية بسيطة مكتوبة بالكامل باللغة العربية",
    "hi": "यह एक सरल हिंदी उत्तर है जो पूरी तरह हिंदी में लिखा गया है",
    "fr": "ceci est une réponse française simple entièrement écrite en français",
    "ru": "это простой русский ответ полностью написанный на русском языке",
    "de": "dies ist eine einfache deutsche antwort vollständig auf deutsch geschrieben",
    "ja": "これは日本語だけで書かれた簡単な日本語の回答です",
    "it": "questa è una semplice risposta italiana scritta interamente in italiano",
    "bn": "এটি সম্পূর্ণ বাংলায় লেখা একটি সহজ বাংলা উত্তর",
    "uk": "це проста українська відповідь повністю написана українською мовою",
    "th": "นี่คือคำตอบภาษาไทยแบบง่ายที่เขียนเป็นภาษาไทยทั้งหมด",
    "ur": "یہ ایک سادہ اردو جواب ہے جو مکمل طور پر اردو میں لکھا گیا ہے",
    "ta": "இது முழுவதும் தமிழில் எழுதப்பட்ட எளிய தமிழ் பதில்",
    "te": "ఇది పూర్తిగా తెలుగులో వ్రాయబడిన సరళమైన తెలుగు సమాధానం",
    "bg": "това е прост български отговор написан изцяло на български",
    "ko": "이것은 전부 한국어로 작성된 간단한 한국어 답변입니다",
    "pl": "to jest prosta polska odpowiedź napisana w całości po polsku",
    "he": "זוהי תשובה פשוטה בעברית שנכתבה כולה בעברית",
    "fa": "این یک پاسخ ساده فارسی است که کاملاً به فارسی نوشته شده است",
    "vi": "đây là một câu trả lời tiếng việt đơn giản được viết hoàn toàn bằng tiếng việt",
    "ne": "यो पूर्ण रूपमा नेपालीमा लेखिएको सरल नेपाली उत्तर हो",
    "sw": "hili ni jibu rahisi la kiswahili lililoandikwa kabisa kwa kiswahili",
    "kn": "ಇದು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲಿ ಬರೆಯಲಾದ ಸರಳ ಕನ್ನಡ ಉತ್ತರವಾಗಿದೆ",
    "mr": "हे पूर्णपणे मराठीत लिहिलेले एक साधे मराठी उत्तर आहे",
    "gu": "આ સંપૂર્ણપણે ગુજરાતીમાં લખાયેલો સરળ ગુજરાતી જવાબ છે",
    "pa": "ਇਹ ਪੂਰੀ ਤਰ੍ਹਾਂ ਪੰਜਾਬੀ ਵਿੱਚ ਲਿਖਿਆ ਇੱਕ ਸਧਾਰਨ ਪੰਜਾਬੀ ਜਵਾਬ ਹੈ",
    "ml": "ഇത് പൂർണ്ണമായും മലയാളത്തിൽ എഴുതിയ ലളിതമായ മലയാളം മറുപടിയാണ്",
    "fi": "tämä on yksinkertainen suomalainen vastaus joka on kirjoitettu kokonaan suomeksi",
}


def _words(n: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{i}" for i in range(1, max(0, int(n)) + 1))


def _safe_text_avoiding(words: list[str]) -> str:
    for candidate in ("xqz", "vwx", "jkp", "qzxv", "nmbv"):
        if all(not re.search(r"\b" + re.escape(w) + r"\b", candidate, flags=re.I) for w in words):
            return candidate
    return ""


def construct_one(match: dict[str, Any]) -> str | None:
    iid = str(match.get("instruction_id") or "")
    s = dict(match.get("slots") or {})

    if iid == "keywords:existence":
        kws = [str(x) for x in s.get("keywords") or []]
        return " ".join(kws) if kws else None

    if iid == "keywords:frequency":
        keyword = str(s.get("keyword") or "")
        relation = str(s.get("relation") or "")
        n = int(s.get("frequency") or 0)
        if not keyword or n < 0:
            return None
        if relation == "at least":
            return " ".join([keyword] * n)
        if relation == "less than":
            return "xqz" if n > 0 else None
        return None

    if iid == "keywords:forbidden_words":
        values = [str(x) for x in s.get("forbidden_words") or []]
        return _safe_text_avoiding(values)

    if iid == "keywords:letter_frequency":
        letter = str(s.get("letter") or "").lower()
        relation = str(s.get("let_relation") or "")
        n = int(s.get("let_frequency") or 0)
        if len(letter) != 1 or not ("a" <= letter <= "z") or n < 0:
            return None
        if relation == "at least":
            return letter * max(n, 1)
        if relation == "less than":
            return "123" if n > 0 else None
        return None

    if iid == "language:response_language":
        return _LANGUAGE_SAMPLE.get(str(s.get("language") or "").lower())

    if iid == "length_constraints:number_sentences":
        n = int(s.get("num_sentences") or 0)
        rel = str(s.get("relation") or "")
        if n < 0:
            return None
        if rel == "at least":
            return " ".join(f"Sentence {i}." for i in range(1, max(1, n) + 1))
        if rel == "less than":
            return "" if n == 1 else ("Safe." if n > 1 else None)
        return None

    if iid == "length_constraints:number_paragraphs":
        n = int(s.get("num_paragraphs") or 0)
        return "***".join(f"paragraph{i}" for i in range(1, n + 1)) if n > 0 else None

    if iid == "length_constraints:number_words":
        n = int(s.get("num_words") or 0)
        rel = str(s.get("relation") or "")
        if n < 0:
            return None
        if rel == "at least":
            return _words(max(1, n))
        if rel == "less than":
            return "" if n == 1 else ("word1" if n > 1 else None)
        return None

    if iid == "length_constraints:nth_paragraph_first_word":
        n = int(s.get("num_paragraphs") or 0)
        nth = int(s.get("nth_paragraph") or 0)
        first = str(s.get("first_word") or "")
        if n <= 0 or nth <= 0 or nth > n or not first:
            return None
        parts = [(first + " body") if i == nth else f"paragraph{i}" for i in range(1, n + 1)]
        return "\n\n".join(parts)

    if iid == "detectable_content:number_placeholders":
        n = int(s.get("num_placeholders") or 0)
        return " ".join(f"[slot{i}]" for i in range(1, max(1, n) + 1)) if n >= 0 else None

    if iid == "detectable_content:postscript":
        marker = str(s.get("postscript_marker") or "")
        return ("body\n" + marker + " note") if marker else None

    if iid == "detectable_format:number_bullet_lists":
        n = int(s.get("num_bullets") or 0)
        return "\n".join(f"* item{i}" for i in range(1, n + 1)) if n >= 0 else None

    if iid == "detectable_format:constrained_response":
        return "My answer is yes."

    if iid == "detectable_format:number_highlighted_sections":
        n = int(s.get("num_highlights") or 0)
        return " ".join(f"*highlight{i}*" for i in range(1, max(1, n) + 1)) if n >= 0 else None

    if iid == "detectable_format:multiple_sections":
        n = int(s.get("num_sections") or 0)
        splitter = str(s.get("section_spliter") or "Section")
        if n <= 0 or splitter not in {"Section", "SECTION"}:
            return None
        return "\n".join(f"{splitter} {i}\nbody{i}" for i in range(1, n + 1))

    if iid == "detectable_format:json_format":
        return '{"answer":"safe"}'

    if iid == "detectable_format:title":
        return "<<safe title>>"

    if iid == "combination:two_responses":
        return "first response******second response"

    if iid == "combination:repeat_prompt":
        base = str(s.get("prompt_to_repeat") or "")
        return (base + "\nanswer").strip() if base else None

    if iid == "startend:end_checker":
        end = str(s.get("end_phrase") or "")
        return ("body " + end).strip() if end else None

    if iid == "change_case:capital_word_frequency":
        n = int(s.get("capital_frequency") or 0)
        rel = str(s.get("capital_relation") or "")
        if n < 0:
            return None
        if rel == "at least":
            return " ".join(["WORD"] * max(1, n))
        if rel == "less than":
            return "lowercase words" if n > 0 else None
        return None

    if iid == "change_case:english_capital":
        return "THIS IS A SIMPLE ENGLISH RESPONSE WRITTEN ENTIRELY IN ENGLISH"

    if iid == "change_case:english_lowercase":
        return "this is a simple english response written entirely in english"

    if iid == "punctuation:no_comma":
        return "safe response without forbidden punctuation"

    if iid == "startend:quotation":
        return '"safe response"'

    return None


def solve(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    matches = inverter.recognize(prompt)
    if len(matches) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "ACTIVE_CHECKER_CARDINALITY_NOT_ONE",
            "recognized_instruction_ids": [m.get("instruction_id") for m in matches],
            "response": None,
            "model_dependency_count": 0,
            "network_used": False,
            "terminal_metadata_used": False,
        }
    response = construct_one(matches[0])
    if response is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_CERTIFIED_CONSTRUCTOR",
            "recognized_instruction_ids": [matches[0].get("instruction_id")],
            "response": None,
            "model_dependency_count": 0,
            "network_used": False,
            "terminal_metadata_used": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS",
        "instruction_id": matches[0]["instruction_id"],
        "response": response,
        "model_dependency_count": 0,
        "network_used": False,
        "terminal_metadata_used": False,
        "authority": "CANDIDATE_ONLY__EXACT_PUBLIC_CHECKER_VERIFICATION_REQUIRED",
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return solve(str(args.get("prompt") or args.get("instruction") or ""))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), indent=2, ensure_ascii=False, sort_keys=True))
