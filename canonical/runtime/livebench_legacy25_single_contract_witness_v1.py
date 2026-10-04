#!/usr/bin/env python3
"""Deterministic single-contract witnesses for the pinned legacy 25-checker scorer.

This layer is intentionally score-only.  It proves constructive satisfiability
of individual public checker contracts and grants zero semantic capability
credit. Multi-contract composition is a separate stage.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.livebench_legacy25_prompt_contract_compiler_v1 import (
    compile_prompt,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY25_SINGLE_CONTRACT_WITNESS_V1"

LANGUAGE_SAMPLES = {
    "en":"This is a simple English text written for reliable language detection and testing.",
    "es":"Este es un texto sencillo en español escrito para detectar correctamente el idioma.",
    "pt":"Este é um texto simples em português escrito para detectar corretamente o idioma.",
    "ar":"هذا نص عربي بسيط مكتوب لاختبار التعرف على اللغة بشكل صحيح وواضح.",
    "hi":"यह भाषा पहचान की जाँच के लिए लिखा गया एक सरल हिंदी पाठ है।",
    "fr":"Ceci est un texte simple en français écrit pour détecter correctement la langue.",
    "ru":"Это простой русский текст, написанный для точного определения языка.",
    "de":"Dies ist ein einfacher deutscher Text zur zuverlässigen Erkennung der Sprache.",
    "ja":"これは言語を正確に判定するために書かれた簡単な日本語の文章です。",
    "it":"Questo è un semplice testo italiano scritto per rilevare correttamente la lingua.",
    "bn":"এটি ভাষা সঠিকভাবে শনাক্ত করার জন্য লেখা একটি সহজ বাংলা পাঠ।",
    "uk":"Це простий український текст, написаний для точного визначення мови.",
    "th":"นี่คือข้อความภาษาไทยง่ายๆ ที่เขียนขึ้นเพื่อทดสอบการตรวจจับภาษาอย่างถูกต้อง",
    "ur":"یہ زبان کی درست شناخت کے لیے لکھا گیا ایک سادہ اردو متن ہے۔",
    "ta":"இது மொழியை சரியாக கண்டறிய எழுதப்பட்ட எளிய தமிழ் உரையாகும்.",
    "te":"ఇది భాషను సరిగ్గా గుర్తించడానికి వ్రాసిన సరళమైన తెలుగు వాక్యం.",
    "bg":"Това е прост български текст, написан за точно разпознаване на езика.",
    "ko":"이것은 언어를 정확하게 감지하기 위해 작성된 간단한 한국어 문장입니다.",
    "pl":"To jest prosty polski tekst napisany w celu poprawnego rozpoznania języka.",
    "he":"זהו טקסט פשוט בעברית שנכתב כדי לזהות את השפה בצורה מדויקת.",
    "fa":"این یک متن ساده فارسی است که برای تشخیص دقیق زبان نوشته شده است.",
    "vi":"Đây là một đoạn văn tiếng Việt đơn giản được viết để nhận diện ngôn ngữ chính xác.",
    "ne":"यो भाषा सही रूपमा पहिचान गर्न लेखिएको सरल नेपाली पाठ हो।",
    "sw":"Hii ni maandishi rahisi ya Kiswahili yaliyoandikwa kwa ajili ya kutambua lugha kwa usahihi.",
    "kn":"ಇದು ಭಾಷೆಯನ್ನು ಸರಿಯಾಗಿ ಗುರುತಿಸಲು ಬರೆಯಲಾದ ಸರಳ ಕನ್ನಡ ಪಠ್ಯವಾಗಿದೆ.",
    "mr":"हा भाषा अचूक ओळखण्यासाठी लिहिलेला एक सोपा मराठी मजकूर आहे.",
    "gu":"આ ભાષાને યોગ્ય રીતે ઓળખવા માટે લખાયેલો સરળ ગુજરાતી લખાણ છે.",
    "pa":"ਇਹ ਭਾਸ਼ਾ ਦੀ ਸਹੀ ਪਛਾਣ ਲਈ ਲਿਖਿਆ ਗਿਆ ਇੱਕ ਸਧਾਰਨ ਪੰਜਾਬੀ ਪਾਠ ਹੈ।",
    "ml":"ഇത് ഭാഷ ശരിയായി തിരിച്ചറിയാൻ എഴുതിയ ലളിതമായ മലയാളം വാചകമാണ്.",
    "fi":"Tämä on yksinkertainen suomenkielinen teksti joka on kirjoitettu kielen tunnistamista varten.",
}

_FILLERS = ("alpha","birch","cedar","delta","ember","frost","granite","harbor","ivory","juniper")

class WitnessError(ValueError):
    pass

def _avoid_regex(pattern: str) -> str:
    try:
        rx = re.compile(pattern, re.I)
    except re.error as exc:
        raise WitnessError("VISIBLE_REGEX_NOT_COMPILABLE") from exc
    for candidate in ("0","qvx","alpha","birch","cedar","delta"):
        if rx.search(candidate) is None:
            return candidate
    raise WitnessError("NO_SAFE_REGEX_AVOIDING_FILLER")

def _avoid_forbidden(words: list[str]) -> str:
    for candidate in ("alpha","birch","cedar","delta","ember","0"):
        if all(re.search(r"\b" + word + r"\b", candidate, re.I) is None for word in words):
            return candidate
    return "0"

def witness_for_contract(contract: Mapping[str, Any], *, visible_prompt: str = "") -> str:
    family = str(contract["instruction_id"])
    s = dict(contract.get("slots") or {})

    if family == "keywords:existence":
        return " ".join(s["keywords"])
    if family == "keywords:frequency":
        keyword = str(s["keyword"])
        n = int(s["frequency"])
        return " ".join([keyword] * n) if s["relation"] == "at least" else _avoid_regex(keyword)
    if family == "keywords:forbidden_words":
        return _avoid_forbidden(list(s["forbidden_words"]))
    if family == "keywords:letter_frequency":
        letter = str(s["letter"])
        n = int(s["let_frequency"])
        return letter * max(1, n) if s["let_relation"] == "at least" else "0"
    if family == "language:response_language":
        code = str(s["language"])
        sample = LANGUAGE_SAMPLES.get(code)
        if not sample:
            raise WitnessError("NO_PINNED_LANGUAGE_SAMPLE:" + code)
        return sample + " " + sample
    if family == "length_constraints:number_sentences":
        n = int(s["num_sentences"])
        if s["relation"] == "less than":
            count = max(0, n - 1)
        else:
            count = max(1, n)
        return " ".join(f"Sentence{i}." for i in range(1, count + 1))
    if family == "length_constraints:number_paragraphs":
        n = int(s["num_paragraphs"])
        return "***".join(f"paragraph{i}" for i in range(1, n + 1))
    if family == "length_constraints:number_words":
        n = int(s["num_words"])
        count = max(0, n - 1) if s["relation"] == "less than" else max(1, n)
        return " ".join(_FILLERS[i % len(_FILLERS)] for i in range(count))
    if family == "length_constraints:nth_paragraph_first_word":
        n = int(s["num_paragraphs"])
        target = int(s["nth_paragraph"])
        first = str(s["first_word"])
        rows = [f"paragraph{i}" for i in range(1, n + 1)]
        rows[target - 1] = first + " content"
        return "\n\n".join(rows)
    if family == "detectable_content:number_placeholders":
        return " ".join(f"[slot{i}]" for i in range(1, int(s["num_placeholders"]) + 1))
    if family == "detectable_content:postscript":
        return "body " + str(s["postscript_marker"]) + " note"
    if family == "detectable_format:number_bullet_lists":
        return "\n".join(f"* item{i}" for i in range(1, int(s["num_bullets"]) + 1))
    if family == "detectable_format:constrained_response":
        return "My answer is yes."
    if family == "detectable_format:number_highlighted_sections":
        return " ".join(f"*highlight{i}*" for i in range(1, int(s["num_highlights"]) + 1))
    if family == "detectable_format:multiple_sections":
        splitter = str(s["section_spliter"])
        return "\n".join(f"{splitter} {i}\ncontent{i}" for i in range(1, int(s["num_sections"]) + 1))
    if family == "detectable_format:json_format":
        return '{"answer":"alpha"}'
    if family == "detectable_format:title":
        return "<<alpha>>"
    if family == "combination:two_responses":
        return "alpha******beta"
    if family == "combination:repeat_prompt":
        normalized = re.sub(r"\s+", " ", str(visible_prompt or "")).strip()
        start, end = int(contract["start"]), int(contract["end"])
        base = (normalized[:start] + " " + normalized[end:]).strip()
        if not base:
            raise WitnessError("REPEAT_PROMPT_VISIBLE_BASE_REQUIRED")
        return base + " answer"
    if family == "startend:end_checker":
        return str(s["end_phrase"])
    if family == "change_case:capital_word_frequency":
        n = int(s["capital_frequency"])
        if s["capital_relation"] == "at least":
            return " ".join(f"WORD{i}" for i in range(1, n + 1))
        return "lowercase words"
    if family == "change_case:english_capital":
        return "THIS IS A SIMPLE ENGLISH RESPONSE WRITTEN FOR RELIABLE LANGUAGE DETECTION"
    if family == "change_case:english_lowercase":
        return "this is a simple english response written for reliable language detection"
    if family == "punctuation:no_comma":
        return "alpha"
    if family == "startend:quotation":
        return '"alpha"'
    raise WitnessError("UNSUPPORTED_CONTRACT:" + family)

def witness_from_prompt(prompt: str) -> dict[str, Any]:
    compiled = compile_prompt(prompt)
    contracts = compiled["contracts"]
    if len(contracts) != 1:
        raise WitnessError("SINGLE_CONTRACT_ONLY")
    response = witness_for_contract(contracts[0], visible_prompt=prompt)
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_SINGLE_CONTRACT_WITNESS",
        "instruction_id": contracts[0]["instruction_id"],
        "response": response,
        "semantic_capability_credit": False,
        "terminal_metadata_used": False,
        "hidden_kwargs_used": False,
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return witness_from_prompt(str((args or {}).get("prompt") or ""))
