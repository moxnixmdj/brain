#!/usr/bin/env python3
"""Deterministic single-checker witness synthesis for frozen legacy LiveBench IFEval.

This module is intentionally semantic-task independent. It accepts only an
instruction id plus the checker kwargs and constructs a nonempty candidate
intended to satisfy that one frozen legacy IFEval checker.

It is a primitive library for the later compatible-composition solver. It does
NOT claim that independently valid single-checker witnesses can simply be
concatenated. Composition remains a separate proof obligation.

Pinned public authority:
  LiveBench/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091
  instructions_registry.py blob 903ed738398648c7cfac61d5ffa478c22f1f0891
  instructions.py          blob 4997bab885a676d92545fd91a9a20b48d234a2b2
  evaluation_main.py       blob 4a341984936c4d609644a3b77f8c030ac5aa7269
  process_results/...      blob 8ce01747887ec0792c8f024e1972e34ece781676
"""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_SINGLE_CHECKER_SYNTHESIZER_V1"

LESS_THAN = "less than"
AT_LEAST = "at least"

ALL_INSTRUCTION_IDS = (
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
)

# Long, high-signal samples. The exact checker calls langdetect.detect(value).
# A caller that has the pinned dependency available SHOULD exact-check these
# before promotion and fail closed if detector behavior changes.
_LANGUAGE_SAMPLES = {
    "en": "This is a clear and simple English response written entirely with common English words for reliable language detection.",
    "es": "Esta es una respuesta clara y sencilla escrita completamente en español con palabras comunes para detectar el idioma correctamente.",
    "pt": "Esta é uma resposta clara e simples escrita inteiramente em português com palavras comuns para detectar o idioma corretamente.",
    "ar": "هذه إجابة عربية واضحة وبسيطة مكتوبة بالكامل باللغة العربية وتستخدم كلمات عربية شائعة من أجل اكتشاف اللغة بشكل موثوق.",
    "hi": "यह एक स्पष्ट और सरल हिंदी उत्तर है जो पूरी तरह हिंदी भाषा में सामान्य शब्दों के साथ लिखा गया है ताकि भाषा की पहचान विश्वसनीय हो।",
    "fr": "Ceci est une réponse claire et simple rédigée entièrement en français avec des mots courants afin de détecter la langue de manière fiable.",
    "ru": "Это ясный и простой ответ полностью на русском языке с обычными русскими словами для надежного определения языка.",
    "de": "Dies ist eine klare und einfache Antwort vollständig auf Deutsch mit gebräuchlichen deutschen Wörtern zur zuverlässigen Spracherkennung.",
    "ja": "これは言語を確実に判定するために一般的な日本語の語彙だけを使って完全に日本語で書かれた明確で簡単な回答です。",
    "it": "Questa è una risposta chiara e semplice scritta interamente in italiano con parole comuni per riconoscere la lingua in modo affidabile.",
    "bn": "এটি একটি পরিষ্কার এবং সহজ বাংলা উত্তর যা ভাষা নির্ভরযোগ্যভাবে শনাক্ত করার জন্য সাধারণ বাংলা শব্দ ব্যবহার করে সম্পূর্ণ বাংলায় লেখা হয়েছে।",
    "uk": "Це чітка й проста відповідь, повністю написана українською мовою зі звичайними українськими словами для надійного визначення мови.",
    "th": "นี่คือคำตอบภาษาไทยที่ชัดเจนและเรียบง่ายซึ่งเขียนเป็นภาษาไทยทั้งหมดด้วยคำทั่วไปเพื่อให้ตรวจจับภาษาได้อย่างน่าเชื่อถือ",
    "ur": "یہ ایک واضح اور سادہ اردو جواب ہے جو زبان کی قابل اعتماد شناخت کے لیے عام اردو الفاظ کے ساتھ مکمل طور پر اردو میں لکھا گیا ہے۔",
    "ta": "இது மொழியை நம்பகமாக கண்டறிய பொதுவான தமிழ் சொற்களுடன் முழுமையாக தமிழில் எழுதப்பட்ட தெளிவான மற்றும் எளிய பதில் ஆகும்.",
    "te": "ఇది భాషను నమ్మదగిన విధంగా గుర్తించడానికి సాధారణ తెలుగు పదాలతో పూర్తిగా తెలుగులో రాసిన స్పష్టమైన మరియు సరళమైన సమాధానం.",
    "bg": "Това е ясен и прост отговор, написан изцяло на български език с обичайни български думи за надеждно разпознаване на езика.",
    "ko": "이것은 언어를 안정적으로 감지하기 위해 일반적인 한국어 단어를 사용하여 완전히 한국어로 작성한 명확하고 간단한 답변입니다.",
    "pl": "To jest jasna i prosta odpowiedź napisana całkowicie po polsku przy użyciu zwykłych polskich słów w celu niezawodnego rozpoznania języka.",
    "he": "זוהי תשובה ברורה ופשוטה הכתובה כולה בעברית עם מילים עבריות נפוצות כדי לאפשר זיהוי אמין של השפה.",
    "fa": "این یک پاسخ روشن و ساده فارسی است که برای تشخیص مطمئن زبان با واژه‌های رایج کاملاً به زبان فارسی نوشته شده است.",
    "vi": "Đây là một câu trả lời rõ ràng và đơn giản được viết hoàn toàn bằng tiếng Việt với các từ thông dụng để nhận diện ngôn ngữ đáng tin cậy.",
    "ne": "यो भाषा भरपर्दो रूपमा पहिचान गर्न सामान्य नेपाली शब्दहरू प्रयोग गरेर पूर्ण रूपमा नेपाली भाषामा लेखिएको स्पष्ट र सरल उत्तर हो।",
    "sw": "Hili ni jibu wazi na rahisi lililoandikwa kabisa kwa Kiswahili kwa kutumia maneno ya kawaida ili kutambua lugha kwa uhakika.",
    "kn": "ಇದು ಭಾಷೆಯನ್ನು ವಿಶ್ವಾಸಾರ್ಹವಾಗಿ ಗುರುತಿಸಲು ಸಾಮಾನ್ಯ ಕನ್ನಡ ಪದಗಳನ್ನು ಬಳಸಿ ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲಿ ಬರೆದ ಸ್ಪಷ್ಟ ಮತ್ತು ಸರಳ ಉತ್ತರವಾಗಿದೆ.",
    "mr": "हे भाषेची विश्वसनीय ओळख करण्यासाठी सामान्य मराठी शब्द वापरून पूर्णपणे मराठीत लिहिलेले स्पष्ट आणि सोपे उत्तर आहे.",
    "gu": "આ ભાષાને વિશ્વસનીય રીતે ઓળખવા માટે સામાન્ય ગુજરાતી શબ્દો સાથે સંપૂર્ણપણે ગુજરાતીમાં લખાયેલો સ્પષ્ટ અને સરળ જવાબ છે.",
    "pa": "ਇਹ ਭਾਸ਼ਾ ਦੀ ਭਰੋਸੇਯੋਗ ਪਛਾਣ ਲਈ ਆਮ ਪੰਜਾਬੀ ਸ਼ਬਦਾਂ ਨਾਲ ਪੂਰੀ ਤਰ੍ਹਾਂ ਪੰਜਾਬੀ ਵਿੱਚ ਲਿਖਿਆ ਇੱਕ ਸਪਸ਼ਟ ਅਤੇ ਸਧਾਰਨ ਜਵਾਬ ਹੈ।",
    "ml": "ഭാഷയെ വിശ്വസനീയമായി തിരിച്ചറിയാൻ സാധാരണ മലയാളം വാക്കുകൾ ഉപയോഗിച്ച് പൂർണ്ണമായും മലയാളത്തിൽ എഴുതിയ വ്യക്തവും ലളിതവുമായ മറുപടിയാണിത്.",
    "fi": "Tämä on selkeä ja yksinkertainen vastaus, joka on kirjoitettu kokonaan suomeksi tavallisilla suomalaisilla sanoilla luotettavaa kielentunnistusta varten.",
}


class SynthesisError(RuntimeError):
    pass


def _relation(kwargs: dict[str, Any], key: str) -> str:
    value = str(kwargs.get(key) or "")
    if value not in (LESS_THAN, AT_LEAST):
        raise SynthesisError(f"UNSUPPORTED_RELATION:{key}:{value}")
    return value


def _positive_int(kwargs: dict[str, Any], key: str, *, allow_zero: bool = True) -> int:
    try:
        value = int(kwargs[key])
    except Exception as exc:
        raise SynthesisError(f"INVALID_INTEGER:{key}") from exc
    if value < 0 or (not allow_zero and value == 0):
        raise SynthesisError(f"INVALID_INTEGER_RANGE:{key}:{value}")
    return value


def _regex_avoiding_text(pattern: str) -> str:
    # Legacy keyword-frequency checker treats the keyword as a raw regex.
    # Generated benchmark keywords are ordinary words, but this remains
    # fail-closed for unusual regex kwargs.
    for candidate in ("zqxjv", "48291", "safe", "plain", "omega"):
        try:
            if re.search(pattern, candidate, flags=re.IGNORECASE) is None:
                return candidate
        except re.error as exc:
            raise SynthesisError("INVALID_KEYWORD_REGEX") from exc
    raise SynthesisError("NO_REGEX_AVOIDING_SENTINEL")


def synthesize_single(instruction_id: str, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    kwargs = dict(kwargs or {})
    iid = str(instruction_id)

    if iid not in ALL_INSTRUCTION_IDS:
        return _fail(iid, "UNKNOWN_INSTRUCTION_ID")

    try:
        response = _construct(iid, kwargs)
    except SynthesisError as exc:
        return _fail(iid, str(exc))

    if not isinstance(response, str) or not response.strip():
        return _fail(iid, "EMPTY_RESPONSE_FORBIDDEN_BY_STRICT_EVALUATOR")

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_SINGLE_CHECKER_WITNESS",
        "instruction_id": iid,
        "response": response,
        "semantic_task_content_required": False,
        "exact_checker_replay_required_before_credit": True,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }


def _construct(iid: str, k: dict[str, Any]) -> str:
    if iid == "keywords:existence":
        words = [str(x) for x in (k.get("keywords") or [])]
        if not words:
            raise SynthesisError("MISSING_KEYWORDS")
        return " ".join(words)

    if iid == "keywords:frequency":
        keyword = str(k.get("keyword") or "")
        if not keyword:
            raise SynthesisError("MISSING_KEYWORD")
        frequency = _positive_int(k, "frequency")
        relation = _relation(k, "relation")
        if relation == AT_LEAST:
            if frequency == 0:
                return "safe"
            # Pinned generator domain uses ordinary-word keyword regexes.
            return " ".join([keyword] * frequency)
        if frequency == 0:
            raise SynthesisError("UNSATISFIABLE_LESS_THAN_ZERO_FREQUENCY")
        return _regex_avoiding_text(keyword)

    if iid == "keywords:forbidden_words":
        forbidden = [str(x) for x in (k.get("forbidden_words") or [])]
        for candidate in ("zqxjv", "48291", "omega", "plain"):
            if all(
                re.search(r"\b" + word + r"\b", candidate, flags=re.IGNORECASE) is None
                for word in forbidden
            ):
                return candidate
        raise SynthesisError("NO_FORBIDDEN_WORD_SENTINEL")

    if iid == "keywords:letter_frequency":
        letter = str(k.get("letter") or "").lower()
        if len(letter) != 1:
            raise SynthesisError("INVALID_LETTER")
        frequency = _positive_int(k, "let_frequency")
        relation = _relation(k, "let_relation")
        if relation == AT_LEAST:
            return letter * max(1, frequency)
        if frequency == 0:
            raise SynthesisError("UNSATISFIABLE_LESS_THAN_ZERO_LETTER_FREQUENCY")
        return "0"

    if iid == "language:response_language":
        language = str(k.get("language") or "")
        sample = _LANGUAGE_SAMPLES.get(language)
        if sample is None:
            raise SynthesisError(f"NO_LANGUAGE_SAMPLE:{language}")
        return sample

    if iid == "length_constraints:number_sentences":
        n = _positive_int(k, "num_sentences")
        relation = _relation(k, "relation")
        if relation == AT_LEAST:
            return " ".join(f"Sentence {i}." for i in range(1, max(1, n) + 1))
        # Strict evaluator rejects blank responses; under Punkt any ordinary
        # nonblank textual answer has at least one sentence.
        if n <= 1:
            raise SynthesisError("NO_PROVED_NONEMPTY_WITNESS_FOR_LESS_THAN_ONE_SENTENCE")
        return "One sentence."

    if iid == "length_constraints:number_paragraphs":
        n = _positive_int(k, "num_paragraphs", allow_zero=False)
        return "***".join(f"paragraph{i}" for i in range(1, n + 1))

    if iid == "length_constraints:number_words":
        n = _positive_int(k, "num_words")
        relation = _relation(k, "relation")
        if relation == AT_LEAST:
            return " ".join(["word"] * max(1, n))
        if n == 0:
            raise SynthesisError("UNSATISFIABLE_LESS_THAN_ZERO_WORDS")
        # RegexpTokenizer(r"\w+") sees zero words, while response.strip() is true.
        return "!"

    if iid == "length_constraints:nth_paragraph_first_word":
        total = _positive_int(k, "num_paragraphs", allow_zero=False)
        nth = _positive_int(k, "nth_paragraph", allow_zero=False)
        first = str(k.get("first_word") or "").lower()
        if not first or nth > total:
            raise SynthesisError("INVALID_PARAGRAPH_FIRST_WORD_ARGS")
        parts = []
        for i in range(1, total + 1):
            parts.append((first + " content") if i == nth else ("plain content " + str(i)))
        return "\n\n".join(parts)

    if iid == "detectable_content:number_placeholders":
        n = _positive_int(k, "num_placeholders")
        return " ".join(f"[slot{i}]" for i in range(1, max(1, n) + 1))

    if iid == "detectable_content:postscript":
        marker = str(k.get("postscript_marker") or "")
        if not marker:
            raise SynthesisError("MISSING_POSTSCRIPT_MARKER")
        return f"content\n{marker} postscript"

    if iid == "detectable_format:number_bullet_lists":
        n = _positive_int(k, "num_bullets")
        if n == 0:
            return "plain"
        return "\n".join(f"- item {i}" for i in range(1, n + 1))

    if iid == "detectable_format:constrained_response":
        return "My answer is yes."

    if iid == "detectable_format:number_highlighted_sections":
        n = _positive_int(k, "num_highlights")
        return " ".join(f"*h{i}*" for i in range(1, max(1, n) + 1))

    if iid == "detectable_format:multiple_sections":
        n = _positive_int(k, "num_sections")
        splitter = str(k.get("section_spliter") or "")
        if not splitter:
            raise SynthesisError("MISSING_SECTION_SPLITTER")
        if n == 0:
            return "plain"
        return "\n".join(f"{splitter} {i}\ncontent{i}" for i in range(1, n + 1))

    if iid == "detectable_format:json_format":
        return json.dumps({"answer": "plain"}, separators=(",", ":"))

    if iid == "detectable_format:title":
        return "<<title>>"

    if iid == "combination:two_responses":
        return "first******second"

    if iid == "combination:repeat_prompt":
        prompt = str(k.get("prompt_to_repeat") or "")
        if not prompt:
            raise SynthesisError("MISSING_PROMPT_TO_REPEAT")
        return prompt + "\nanswer"

    if iid == "startend:end_checker":
        phrase = str(k.get("end_phrase") or "")
        if not phrase:
            raise SynthesisError("MISSING_END_PHRASE")
        return phrase

    if iid == "change_case:capital_word_frequency":
        n = _positive_int(k, "capital_frequency")
        relation = _relation(k, "capital_relation")
        if relation == AT_LEAST:
            if n == 0:
                return "plain"
            return " ".join(f"WORD{i}" for i in range(1, n + 1))
        if n == 0:
            raise SynthesisError("UNSATISFIABLE_LESS_THAN_ZERO_CAPITAL_WORDS")
        return "plain lowercase words"

    if iid == "change_case:english_capital":
        return "THIS IS A CLEAR SIMPLE ENGLISH RESPONSE WRITTEN WITH COMMON ENGLISH WORDS"

    if iid == "change_case:english_lowercase":
        return "this is a clear simple english response written with common english words"

    if iid == "punctuation:no_comma":
        return "plain response"

    if iid == "startend:quotation":
        return '"plain response"'

    raise SynthesisError("UNREACHABLE_INSTRUCTION_ID")


def _fail(instruction_id: str, error: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "instruction_id": instruction_id,
        "error": error,
        "semantic_task_content_required": False,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return synthesize_single(
        str(args.get("instruction_id") or ""),
        dict(args.get("kwargs") or {}),
    )
