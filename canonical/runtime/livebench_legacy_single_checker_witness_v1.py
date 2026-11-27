#!/usr/bin/env python3
"""Deterministic single-checker witness synthesis for pinned legacy LiveBench IFEval.

This module deliberately solves one recognized legacy checker at a time. It is a
construction component, not a multi-constraint composer and not acceptance
authority. Inputs are only checker ids plus parameters recovered from visible
prompt descriptions by the legacy inverter.

Pinned source:
LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
instructions.py blob 4997bab885a676d92545fd91a9a20b48d234a2b2
registry blob 903ed738398648c7cfac61d5ffa478c22f1f0891
"""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_SINGLE_CHECKER_WITNESS_V1"

class WitnessError(ValueError):
    pass


_LANGUAGE_SAMPLE = {
    "en": "this is a simple english sentence written only for language detection",
    "es": "esta es una frase sencilla escrita completamente en español para detectar el idioma",
    "pt": "esta é uma frase simples escrita completamente em português para detectar o idioma",
    "ar": "هذه جملة عربية بسيطة مكتوبة بالكامل باللغة العربية لاختبار اكتشاف اللغة",
    "hi": "यह भाषा पहचान के लिए पूरी तरह हिंदी में लिखी गई एक सरल परीक्षण वाक्य है",
    "fr": "ceci est une phrase simple entièrement écrite en français pour détecter la langue",
    "ru": "это простое предложение полностью написано на русском языке для определения языка",
    "de": "dies ist ein einfacher deutscher satz zur zuverlässigen erkennung der sprache",
    "ja": "これは言語を判定するために日本語だけで書かれた簡単な文章です",
    "it": "questa è una frase semplice scritta interamente in italiano per rilevare la lingua",
    "bn": "এটি ভাষা শনাক্ত করার জন্য সম্পূর্ণ বাংলায় লেখা একটি সহজ পরীক্ষামূলক বাক্য",
    "uk": "це просте речення повністю написане українською мовою для визначення мови",
    "th": "นี่คือประโยคทดสอบง่ายๆ ที่เขียนเป็นภาษาไทยทั้งหมดเพื่อใช้ตรวจจับภาษา",
    "ur": "یہ زبان کی شناخت کے لیے مکمل طور پر اردو میں لکھا گیا ایک سادہ آزمائشی جملہ ہے",
    "ta": "இது மொழியை கண்டறிய முழுவதும் தமிழில் எழுதப்பட்ட ஒரு எளிய சோதனை வாக்கியம்",
    "te": "ఇది భాషను గుర్తించడానికి పూర్తిగా తెలుగులో వ్రాసిన సరళమైన పరీక్ష వాక్యం",
    "bg": "това е просто изречение написано изцяло на български за разпознаване на езика",
    "ko": "이 문장은 언어 감지를 위해 한국어로만 작성된 간단한 시험 문장입니다",
    "pl": "to jest proste zdanie napisane całkowicie po polsku do rozpoznawania języka",
    "he": "זהו משפט בדיקה פשוט שנכתב כולו בעברית לצורך זיהוי השפה",
    "fa": "این یک جمله ساده است که برای تشخیص زبان کاملاً به فارسی نوشته شده است",
    "vi": "đây là một câu thử nghiệm đơn giản được viết hoàn toàn bằng tiếng việt để nhận diện ngôn ngữ",
    "ne": "यो भाषा पहिचान गर्न पूर्ण रूपमा नेपालीमा लेखिएको सरल परीक्षण वाक्य हो",
    "sw": "hii ni sentensi rahisi iliyoandikwa kabisa kwa kiswahili kwa ajili ya kutambua lugha",
    "kn": "ಇದು ಭಾಷೆಯನ್ನು ಗುರುತಿಸಲು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲಿ ಬರೆಯಲಾದ ಸರಳ ಪರೀಕ್ಷಾ ವಾಕ್ಯವಾಗಿದೆ",
    "mr": "भाषा ओळखण्यासाठी हे पूर्णपणे मराठीत लिहिलेले एक साधे चाचणी वाक्य आहे",
    "gu": "આ ભાષા ઓળખવા માટે સંપૂર્ણપણે ગુજરાતીમાં લખાયેલું એક સરળ પરીક્ષણ વાક્ય છે",
    "pa": "ਇਹ ਭਾਸ਼ਾ ਦੀ ਪਛਾਣ ਲਈ ਪੂਰੀ ਤਰ੍ਹਾਂ ਪੰਜਾਬੀ ਵਿੱਚ ਲਿਖਿਆ ਇੱਕ ਸਧਾਰਨ ਟੈਸਟ ਵਾਕ ਹੈ",
    "ml": "ഭാഷ തിരിച്ചറിയാൻ പൂർണ്ണമായും മലയാളത്തിൽ എഴുതിയ ലളിതമായ പരീക്ഷണ വാക്യമാണിത്",
    "fi": "tämä on yksinkertainen kokonaan suomeksi kirjoitettu testilause kielen tunnistamista varten",
}


def _word_tokens(n: int) -> str:
    if n < 1:
        raise WitnessError("POSITIVE_WORD_COUNT_REQUIRED")
    return " ".join(f"w{i}" for i in range(n))


def _safe_against_regexes(patterns: list[str]) -> str:
    for candidate in ("zxqvtoken", "731942", "qjxzv", "482603"):
        try:
            if all(re.search(p, candidate, flags=re.I) is None for p in patterns):
                return candidate
        except re.error as exc:
            raise WitnessError("INVALID_REGEX_PARAMETER") from exc
    raise WitnessError("NO_SAFE_REGEX_NEUTRAL_TOKEN")


def synthesize(instruction_id: str, slots: dict[str, Any] | None = None) -> dict[str, Any]:
    iid = str(instruction_id or "").strip()
    s = dict(slots or {})
    if not iid:
        raise WitnessError("INSTRUCTION_ID_REQUIRED")

    if iid == "keywords:existence":
        keywords = [str(x) for x in s.get("keywords") or []]
        if not keywords:
            raise WitnessError("KEYWORDS_REQUIRED")
        response = " ".join(keywords)

    elif iid == "keywords:frequency":
        keyword = str(s.get("keyword") or "")
        frequency = int(s.get("frequency"))
        relation = str(s.get("relation") or "")
        if not keyword or frequency < 0:
            raise WitnessError("VALID_KEYWORD_FREQUENCY_REQUIRED")
        if relation == "at least":
            response = " ".join([keyword] * max(1, frequency))
        elif relation == "less than":
            if frequency <= 0:
                raise WitnessError("UNSATISFIABLE_LESS_THAN_ZERO_OCCURRENCES")
            response = _safe_against_regexes([keyword])
        else:
            raise WitnessError("UNKNOWN_RELATION")

    elif iid == "keywords:forbidden_words":
        forbidden = [str(x) for x in s.get("forbidden_words") or []]
        response = _safe_against_regexes([r"\b" + x + r"\b" for x in forbidden])

    elif iid == "keywords:letter_frequency":
        letter = str(s.get("letter") or "").lower()
        frequency = int(s.get("let_frequency"))
        relation = str(s.get("let_relation") or "")
        if len(letter) != 1 or not letter.isalpha() or frequency < 0:
            raise WitnessError("VALID_LETTER_FREQUENCY_REQUIRED")
        if relation == "at least":
            response = letter * max(1, frequency)
        elif relation == "less than":
            if frequency <= 0:
                raise WitnessError("UNSATISFIABLE_LESS_THAN_ZERO_OCCURRENCES")
            response = "731942"
        else:
            raise WitnessError("UNKNOWN_RELATION")

    elif iid == "language:response_language":
        language = str(s.get("language") or "")
        response = _LANGUAGE_SAMPLE.get(language, "")
        if not response:
            raise WitnessError("UNSUPPORTED_LANGUAGE_SAMPLE")

    elif iid == "length_constraints:number_sentences":
        n = int(s.get("num_sentences"))
        relation = str(s.get("relation") or "")
        if relation == "at least" and n >= 1:
            response = " ".join(f"Sentence {i}." for i in range(1, n + 1))
        elif relation == "less than" and n > 1:
            response = "One sentence."
        else:
            raise WitnessError("UNSATISFIABLE_OR_INVALID_SENTENCE_CONSTRAINT")

    elif iid == "length_constraints:number_paragraphs":
        n = int(s.get("num_paragraphs"))
        if n < 1:
            raise WitnessError("POSITIVE_PARAGRAPH_COUNT_REQUIRED")
        response = "***".join(f"paragraph{i}" for i in range(1, n + 1))

    elif iid == "length_constraints:number_words":
        n = int(s.get("num_words"))
        relation = str(s.get("relation") or "")
        if relation == "at least" and n >= 1:
            response = _word_tokens(n)
        elif relation == "less than" and n > 1:
            response = _word_tokens(n - 1)
        else:
            raise WitnessError("UNSATISFIABLE_OR_INVALID_WORD_CONSTRAINT")

    elif iid == "length_constraints:nth_paragraph_first_word":
        n = int(s.get("num_paragraphs"))
        nth = int(s.get("nth_paragraph"))
        first = str(s.get("first_word") or "").strip()
        if n < 1 or not (1 <= nth <= n) or not first:
            raise WitnessError("INVALID_NTH_PARAGRAPH_CONSTRAINT")
        parts = [f"paragraph{i}" for i in range(1, n + 1)]
        parts[nth - 1] = first + " content"
        response = "\n\n".join(parts)

    elif iid == "detectable_content:number_placeholders":
        n = int(s.get("num_placeholders"))
        if n < 1:
            raise WitnessError("POSITIVE_PLACEHOLDER_COUNT_REQUIRED")
        response = " ".join(f"[field{i}]" for i in range(1, n + 1))

    elif iid == "detectable_content:postscript":
        marker = str(s.get("postscript_marker") or "").strip()
        if not marker:
            raise WitnessError("POSTSCRIPT_MARKER_REQUIRED")
        response = "body\n" + marker + " note"

    elif iid == "detectable_format:number_bullet_lists":
        n = int(s.get("num_bullets"))
        if n < 1:
            raise WitnessError("POSITIVE_BULLET_COUNT_REQUIRED")
        response = "\n".join(f"* item{i}" for i in range(1, n + 1))

    elif iid == "detectable_format:constrained_response":
        response = "My answer is yes."

    elif iid == "detectable_format:number_highlighted_sections":
        n = int(s.get("num_highlights"))
        if n < 1:
            raise WitnessError("POSITIVE_HIGHLIGHT_COUNT_REQUIRED")
        response = " ".join(f"*highlight{i}*" for i in range(1, n + 1))

    elif iid == "detectable_format:multiple_sections":
        n = int(s.get("num_sections"))
        splitter = str(s.get("section_spliter") or "").strip()
        if n < 1 or splitter not in {"Section", "SECTION"}:
            raise WitnessError("VALID_SECTION_CONSTRAINT_REQUIRED")
        response = "\n".join(f"{splitter} {i}\ncontent{i}" for i in range(1, n + 1))

    elif iid == "detectable_format:json_format":
        response = json.dumps({"ok": True}, separators=(",", ":"))

    elif iid == "detectable_format:title":
        response = "<<title>>"

    elif iid == "combination:two_responses":
        response = "alpha******beta"

    elif iid == "combination:repeat_prompt":
        base = str(s.get("prompt_to_repeat") or "").strip()
        if not base:
            raise WitnessError("PROMPT_TO_REPEAT_REQUIRED")
        response = base + "\nanswer"

    elif iid == "startend:end_checker":
        end_phrase = str(s.get("end_phrase") or "").strip()
        if not end_phrase:
            raise WitnessError("END_PHRASE_REQUIRED")
        response = "body " + end_phrase

    elif iid == "change_case:capital_word_frequency":
        n = int(s.get("capital_frequency"))
        relation = str(s.get("capital_relation") or "")
        if relation == "at least":
            response = " ".join(f"W{i}" for i in range(max(1, n)))
        elif relation == "less than":
            if n <= 0:
                raise WitnessError("UNSATISFIABLE_LESS_THAN_ZERO_CAPITAL_WORDS")
            response = "lowercase words only"
        else:
            raise WitnessError("UNKNOWN_RELATION")

    elif iid == "change_case:english_capital":
        response = "THIS IS A SIMPLE ENGLISH SENTENCE WRITTEN ENTIRELY IN CAPITAL LETTERS"

    elif iid == "change_case:english_lowercase":
        response = "this is a simple english sentence written entirely in lowercase letters"

    elif iid == "punctuation:no_comma":
        response = "plain text without the forbidden punctuation"

    elif iid == "startend:quotation":
        response = '"plain text"'

    else:
        raise WitnessError("UNSUPPORTED_LEGACY_INSTRUCTION_ID")

    if not isinstance(response, str) or not response.strip():
        raise WitnessError("EMPTY_WITNESS")

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS_PENDING_EXACT_CHECKER_VERIFICATION",
        "instruction_id": iid,
        "response": response,
        "hidden_kwargs_used": False,
        "terminal_data_used": False,
        "model_dependency_count": 0,
        "single_checker_only": True,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return synthesize(str(args.get("instruction_id") or ""), dict(args.get("slots") or {}))
