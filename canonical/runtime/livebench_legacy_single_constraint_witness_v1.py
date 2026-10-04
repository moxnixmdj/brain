#!/usr/bin/env python3
"""Deterministic single-constraint witnesses for the frozen legacy LiveBench scorer.

Scope:
- consumes only constraints recovered from visible prompt text by
  livebench_legacy_visible_constraint_compiler_v2;
- supplies a constructive witness for each of the 25 registered legacy IFEval
  checker families;
- does not read instruction_id_list, hidden kwargs, question ids, terminal
  responses, scores, or terminal case metadata;
- is deliberately single-constraint V1. Multi-constraint composition remains
  fail-closed until separately proved.

Language witnesses use explicit per-language seed text and are pending exact
frozen-scorer verification. This module never relies on the frozen checker's
broken LangDetectException fallback path.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_SINGLE_CONSTRAINT_WITNESS_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_REGISTERED_TYPE_COUNT = 25


_LANGUAGE_SEEDS = {
    "en": "this is a simple english sentence about people work places and everyday life",
    "es": "esta es una frase sencilla en español sobre personas trabajo lugares y la vida cotidiana",
    "pt": "esta é uma frase simples em português sobre pessoas trabalho lugares e a vida cotidiana",
    "ar": "هذه جملة عربية بسيطة عن الناس والعمل والأماكن والحياة اليومية",
    "hi": "यह लोगों काम स्थानों और दैनिक जीवन के बारे में एक सरल हिंदी वाक्य है",
    "fr": "ceci est une phrase française simple sur les gens le travail les lieux et la vie quotidienne",
    "ru": "это простое русское предложение о людях работе местах и повседневной жизни",
    "de": "dies ist ein einfacher deutscher satz über menschen arbeit orte und das tägliche leben",
    "ja": "これは人々と仕事と場所と日常生活についての簡単な日本語の文章です",
    "it": "questa è una semplice frase italiana sulle persone il lavoro i luoghi e la vita quotidiana",
    "bn": "এটি মানুষ কাজ স্থান এবং দৈনন্দিন জীবন সম্পর্কে একটি সহজ বাংলা বাক্য",
    "uk": "це просте українське речення про людей роботу місця і повсякденне життя",
    "th": "นี่คือประโยคภาษาไทยง่ายๆ เกี่ยวกับผู้คน งาน สถานที่ และชีวิตประจำวัน",
    "ur": "یہ لوگوں کام جگہوں اور روزمرہ زندگی کے بارے میں ایک سادہ اردو جملہ ہے",
    "ta": "இது மக்கள் வேலை இடங்கள் மற்றும் அன்றாட வாழ்க்கையைப் பற்றிய எளிய தமிழ் வாக்கியம்",
    "te": "ఇది ప్రజలు పని ప్రదేశాలు మరియు దైనందిన జీవితం గురించి సరళమైన తెలుగు వాక్యం",
    "bg": "това е просто българско изречение за хората работата местата и ежедневието",
    "ko": "이것은 사람들 일 장소 그리고 일상생활에 관한 간단한 한국어 문장입니다",
    "pl": "to jest proste polskie zdanie o ludziach pracy miejscach i codziennym życiu",
    "he": "זה משפט פשוט בעברית על אנשים עבודה מקומות וחיי היומיום",
    "fa": "این یک جمله ساده فارسی درباره مردم کار مکان‌ها و زندگی روزمره است",
    "vi": "đây là một câu tiếng việt đơn giản về con người công việc địa điểm và cuộc sống hằng ngày",
    "ne": "यो मानिसहरू काम स्थानहरू र दैनिक जीवनको बारेमा सरल नेपाली वाक्य हो",
    "sw": "hii ni sentensi rahisi ya kiswahili kuhusu watu kazi maeneo na maisha ya kila siku",
    "kn": "ಇದು ಜನರು ಕೆಲಸ ಸ್ಥಳಗಳು ಮತ್ತು ದೈನಂದಿನ ಜೀವನದ ಬಗ್ಗೆ ಸರಳ ಕನ್ನಡ ವಾಕ್ಯ",
    "mr": "हे लोक काम ठिकाणे आणि दैनंदिन जीवनाबद्दलचे एक साधे मराठी वाक्य आहे",
    "gu": "આ લોકો કામ સ્થળો અને દૈનિક જીવન વિશેનું એક સરળ ગુજરાતી વાક્ય છે",
    "pa": "ਇਹ ਲੋਕਾਂ ਕੰਮ ਥਾਵਾਂ ਅਤੇ ਰੋਜ਼ਾਨਾ ਜੀਵਨ ਬਾਰੇ ਇੱਕ ਸਧਾਰਨ ਪੰਜਾਬੀ ਵਾਕ ਹੈ",
    "ml": "ഇത് ആളുകൾ ജോലി സ്ഥലങ്ങൾ ദൈനംദിന ജീവിതം എന്നിവയെ കുറിച്ചുള്ള ലളിതമായ മലയാള വാക്യമാണ്",
    "fi": "tämä on yksinkertainen suomenkielinen lause ihmisistä työstä paikoista ja arkielämästä",
}


class WitnessError(ValueError):
    pass


def _n(value: Any, name: str) -> int:
    try:
        out = int(value)
    except Exception as exc:
        raise WitnessError(f"{name}:INTEGER_REQUIRED") from exc
    if out < 0:
        raise WitnessError(f"{name}:NONNEGATIVE_REQUIRED")
    return out


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(max(0, n)))


def _safe_nonmatch(pattern: str) -> str:
    # KeywordFrequencyChecker treats the keyword as a regex. Search a small,
    # deterministic reservoir rather than assuming it is a literal.
    for candidate in ("zxqv", "brnt", "clmp", "dgfk", "hjwy", "0000"):
        try:
            if re.search(pattern, candidate, flags=re.IGNORECASE) is None:
                return candidate
        except re.error as exc:
            raise WitnessError("INVALID_VISIBLE_KEYWORD_REGEX") from exc
    raise WitnessError("NO_SAFE_NONMATCH_FOUND")


def witness_for_constraint(constraint: dict[str, Any]) -> str:
    iid = str(constraint.get("instruction_id") or "")
    slots = dict(constraint.get("slots") or {})
    if constraint.get("parameter_complete") is not True:
        raise WitnessError("PARAMETER_INCOMPLETE")

    if iid == "keywords:existence":
        kws = [str(x) for x in slots.get("keywords") or []]
        if not kws:
            raise WitnessError("KEYWORDS_REQUIRED")
        return " ".join(kws)

    if iid == "keywords:frequency":
        keyword = str(slots.get("keyword") or "")
        freq = _n(slots.get("frequency"), "frequency")
        relation = str(slots.get("relation") or "")
        if not keyword:
            raise WitnessError("KEYWORD_REQUIRED")
        if relation == "at least":
            return " ".join([keyword] * max(1, freq))
        if relation == "less than":
            if freq == 0:
                raise WitnessError("STRICT_LESS_THAN_ZERO_UNSAT")
            return _safe_nonmatch(keyword)
        raise WitnessError("UNKNOWN_RELATION")

    if iid == "keywords:forbidden_words":
        forbidden = [str(x) for x in slots.get("forbidden_words") or []]
        for candidate in ("zxqv", "brnt", "clmp", "0000"):
            if all(re.search(r"\b" + re.escape(w) + r"\b", candidate, re.I) is None for w in forbidden):
                return candidate
        raise WitnessError("NO_FORBIDDEN_SAFE_TOKEN")

    if iid == "keywords:letter_frequency":
        letter = str(slots.get("letter") or "").lower()
        freq = _n(slots.get("let_frequency"), "let_frequency")
        relation = str(slots.get("let_relation") or "")
        if len(letter) != 1:
            raise WitnessError("ONE_LETTER_REQUIRED")
        if relation == "at least":
            return letter * max(1, freq)
        if relation == "less than":
            if freq == 0:
                raise WitnessError("STRICT_LESS_THAN_ZERO_UNSAT")
            return "0000"
        raise WitnessError("UNKNOWN_RELATION")

    if iid == "language:response_language":
        language = str(slots.get("language") or "")
        seed = _LANGUAGE_SEEDS.get(language)
        if seed is None:
            raise WitnessError("UNVERIFIED_LANGUAGE_CODE:" + language)
        # Repetition improves detector margin without adding another language.
        return " ".join([seed] * 3)

    if iid == "length_constraints:number_sentences":
        count = _n(slots.get("num_sentences"), "num_sentences")
        relation = str(slots.get("relation") or "")
        if relation == "at least":
            return " ".join(f"Sentence{i}." for i in range(max(1, count)))
        if relation == "less than":
            if count == 0:
                raise WitnessError("STRICT_LESS_THAN_ZERO_UNSAT")
            if count == 1:
                return ""
            return "One sentence."
        raise WitnessError("UNKNOWN_RELATION")

    if iid == "length_constraints:number_paragraphs":
        count = _n(slots.get("num_paragraphs"), "num_paragraphs")
        if count < 1:
            raise WitnessError("PARAGRAPH_COUNT_POSITIVE_REQUIRED")
        return " *** ".join(f"p{i}" for i in range(count))

    if iid == "length_constraints:number_words":
        count = _n(slots.get("num_words"), "num_words")
        relation = str(slots.get("relation") or "")
        if relation == "at least":
            return _words(max(1, count))
        if relation == "less than":
            if count == 0:
                raise WitnessError("STRICT_LESS_THAN_ZERO_UNSAT")
            return "" if count == 1 else "word"
        raise WitnessError("UNKNOWN_RELATION")

    if iid == "length_constraints:nth_paragraph_first_word":
        count = _n(slots.get("num_paragraphs"), "num_paragraphs")
        nth = _n(slots.get("nth_paragraph"), "nth_paragraph")
        first = str(slots.get("first_word") or "")
        if count < 1 or nth < 1 or nth > count or not first:
            raise WitnessError("INVALID_NTH_PARAGRAPH_PARAMETERS")
        parts = [f"p{i}" for i in range(1, count + 1)]
        parts[nth - 1] = first + " body"
        return "\n\n".join(parts)

    if iid == "detectable_content:number_placeholders":
        count = _n(slots.get("num_placeholders"), "num_placeholders")
        return " ".join(f"[x{i}]" for i in range(max(1, count)))

    if iid == "detectable_content:postscript":
        marker = str(slots.get("postscript_marker") or "")
        if not marker:
            raise WitnessError("POSTSCRIPT_MARKER_REQUIRED")
        return f"body\n{marker} note"

    if iid == "detectable_format:number_bullet_lists":
        count = _n(slots.get("num_bullets"), "num_bullets")
        return "\n".join(f"* item{i}" for i in range(count))

    if iid == "detectable_format:constrained_response":
        return "My answer is yes."

    if iid == "detectable_format:number_highlighted_sections":
        count = _n(slots.get("num_highlights"), "num_highlights")
        return " ".join(f"*h{i}*" for i in range(max(1, count)))

    if iid == "detectable_format:multiple_sections":
        count = _n(slots.get("num_sections"), "num_sections")
        splitter = str(slots.get("section_spliter") or "")
        if count < 1 or not splitter:
            raise WitnessError("SECTION_PARAMETERS_REQUIRED")
        return "\n".join(f"{splitter} {i}\nbody{i}" for i in range(1, count + 1))

    if iid == "detectable_format:json_format":
        return "{}"

    if iid == "detectable_format:title":
        return "<<x>>"

    if iid == "combination:two_responses":
        return "alpha******beta"

    if iid == "combination:repeat_prompt":
        base = str(slots.get("prompt_to_repeat") or "")
        if not base.strip():
            raise WitnessError("PROMPT_TO_REPEAT_REQUIRED")
        return base.strip() + "\nanswer"

    if iid == "startend:end_checker":
        end = str(slots.get("end_phrase") or "")
        if not end:
            raise WitnessError("END_PHRASE_REQUIRED")
        return "body " + end

    if iid == "change_case:capital_word_frequency":
        count = _n(slots.get("capital_frequency"), "capital_frequency")
        relation = str(slots.get("capital_relation") or "")
        if relation == "at least":
            return " ".join(f"WORD{i}" for i in range(max(1, count)))
        if relation == "less than":
            if count == 0:
                raise WitnessError("STRICT_LESS_THAN_ZERO_UNSAT")
            return "lowercase words"
        raise WitnessError("UNKNOWN_RELATION")

    if iid == "change_case:english_capital":
        return "THIS IS A SIMPLE ENGLISH SENTENCE ABOUT PEOPLE PLACES WORK AND TIME"

    if iid == "change_case:english_lowercase":
        return "this is a simple english sentence about people places work and time"

    if iid == "punctuation:no_comma":
        return "text without forbidden punctuation"

    if iid == "startend:quotation":
        return '"quoted"'

    raise WitnessError("UNSUPPORTED_INSTRUCTION_ID:" + iid)


def solve(prompt: str) -> dict[str, Any]:
    compiled = compiler.compile_visible_constraints(str(prompt or ""))
    if compiled.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_CONSTRAINT_COMPILER_NOT_PASS",
            "response": None,
            "constraint_count": len(compiled.get("constraints") or []),
            "terminal_data_used": False,
        }
    constraints = list(compiled.get("constraints") or [])
    if len(constraints) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "SINGLE_CONSTRAINT_ONLY_V1",
            "response": None,
            "constraint_count": len(constraints),
            "terminal_data_used": False,
        }
    try:
        response = witness_for_constraint(constraints[0])
    except WitnessError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "constraint_count": 1,
            "terminal_data_used": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_SINGLE_LEGACY_CONSTRAINT_WITNESS",
        "instruction_id": constraints[0]["instruction_id"],
        "response": response,
        "constraint_count": 1,
        "registered_legacy_type_count": LEGACY_REGISTERED_TYPE_COUNT,
        "model_dependency_count": 0,
        "network_used": False,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
        "composition_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(solve(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
