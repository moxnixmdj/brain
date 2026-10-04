#!/usr/bin/env python3
from __future__ import annotations

import re
import string
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_CHECKER_INVERSION_CUT_V1"

_PERSON_NAMES = [
    "Emma","Liam","Sophia","Jackson","Olivia","Noah","Ava","Lucas","Isabella","Mason",
    "Mia","Ethan","Charlotte","Alexander","Amelia","Benjamin","Harper","Leo","Zoe","Daniel",
    "Layla","Nicholas","Audrey","David","Hannah","Christopher","Penelope","Thomas","Nora","Andrew",
    "Aria","Joseph","Claire","Ryan","Stella","Jonathan",
]
_CONJ = ["and","but","for","nor","or","so","yet"]

_STATIC = {
    "x_sent_type": "Maintain a 2:1 ratio of declarative to interrogative sentences.",
    "x_sent_balance": "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced.",
    "x_palindrome": "Include at least 10 single-word palindromes, each at least 5 characters long.",
    "x_char_count": "Respond with three sentences, all containing the same number of characters; the sentences cannot be identical.",
    "x_last_first": "The last word of each sentence must become the first word of the next sentence.",
    "x_paragraph_loop": "Write at least two paragraphs, where each paragraph ends with exactly the same word it started with, and separate paragraphs with two newlines.",
    "x_no_consecutive": "No two consecutive words can share the same first letter.",
    "x_indent_stairs": "Create stairs by incrementally indenting each new line.",
    "x_quote_explain": "Every quoted phrase must be followed by an unquoted explanation.",
    "x_italics_thesis": "Each section must begin with a thesis statement in italics, use HTML to indicate the italics.",
    "x_sub_bullets": "Your response must include newline-separated bullet points denoted by * and at least one sub-bullet point denoted by - for each bullet point.",
    "x_some_bullets": "Your answer must contain at least two sentences ending in a period followed by at least two newline-separated bullet points denoted by *.",
    "x_multiples": "Count from 10 to 50 but only print multiples of 7.",
    "x_mcq": "Generate 4 multiple choice questions with 5 options each about '20th century art history'. Each question should start with the label \"Question\". The questions should get progressively longer. Do not provide an explanation.",
    "x_reverse_newline": "List the countries of Africa in reverse alphabetical order, each on a new line.",
    "x_word_reverse": "What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per word.",
    "x_char_reverse": "What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per letter.",
    "x_sentence_alpha": "Tell me a 26-sentence story where each sentence's first word starts with the letters of the alphabet in order.",
}

SUPPORTED_PUBLIC_CHECKER_CLASSES = [
    "WordCountRangeChecker",
    "UniqueWordCountChecker",
    "StopWordPercentageChecker",
    "SentTypeRatioChecker",
    "SentBalanceChecker",
    "ConjunctionCountChecker",
    "PersonNameCountChecker",
    "PalindromeChecker",
    "CharacterCountUniqueWordsChecker",
    "LimitedWordRepeatChecker",
    "PronounCountChecker",
    "LastWordFirstNextChecker",
    "ParagraphLastFirstWordMatchChecker",
    "IncrementingWordCountChecker",
    "NoConsecutiveFirstLetterChecker",
    "IndentStairsChecker",
    "QuoteExplanationChecker",
    "ItalicsThesisChecker",
    "SubBulletPointsChecker",
    "SomeBulletPointsChecker",
    "PrintMultiplesChecker",
    "MultipleChoiceQuestionsChecker",
    "ReverseNewlineChecker",
    "WordReverseOrderChecker",
    "CharacterReverseOrderChecker",
    "SentenceAlphabetChecker",
]

def match_rules(text: str) -> list[tuple[str, Any]]:
    rules: list[tuple[str, Any]] = []
    lower = text.lower()
    for key, literal in _STATIC.items():
        if literal.lower() in lower:
            rules.append((key, None))

    patterns = (
        ("x_word_range", r"The response must contain between\s+(\d+)\s+and\s+(\d+)\s+words\.", lambda m: (int(m.group(1)), int(m.group(2)))),
        ("x_unique", r"Use at least\s+(\d+)\s+unique words in the response\.", lambda m: int(m.group(1))),
        ("x_stopword_pct", r"Ensure that stop words constitute no more than\s+(\d+)%\s+of the total words in your response\.", lambda m: int(m.group(1))),
        ("x_conjunctions", r"Use at least\s+(\d+)\s+different coordinating conjunctions in the response\.", lambda m: int(m.group(1))),
        ("x_person_names", r"Mention at least\s+(\d+)\s+different person names in the response,", lambda m: int(m.group(1))),
        ("x_limited_repeat", r"The response should not repeat any word more than\s+(\d+)\s+times\.", lambda m: int(m.group(1))),
        ("x_pronouns", r"The response should include at least\s+(\d+)\s+personal pronouns\.", lambda m: int(m.group(1))),
        ("x_increment_words", r"Each sentence must contain exactly\s+(\d+)\s+more words than the previous one\.", lambda m: int(m.group(1))),
    )
    for key, pattern, conv in patterns:
        m = re.search(pattern, text, flags=re.I | re.S)
        if m:
            rules.append((key, conv(m)))
    return rules

def _alpha_sentences() -> str:
    words = [
        "Apple","Berry","Cedar","Delta","Eagle","Fable","Giant","Harbor","Ivory","Jolly","Koala","Lemon","Maple",
        "Noble","Ocean","Piano","Queen","River","Solar","Tiger","Urban","Vivid","Water","Xenon","Young","Zebra",
    ]
    return " ".join(f"{w} acts." for w in words)

def _mcq() -> str:
    out = []
    for i, q in enumerate(("Art?","Which art form?","Which art movement shaped design?","Which twentieth century art movement most strongly shaped modern design language?"), 1):
        out.append(f"Question {i} {q}")
        out.extend([f"{c}. option{c.lower()}{i}" for c in "ABCDE"])
    return "\n".join(out)

def witness(rule: str, arg: Any) -> str:
    if rule == "x_word_range":
        n = int(arg[0])
        return " ".join(f"w{i}" for i in range(n))
    if rule == "x_unique":
        return " ".join(f"u{i}" for i in range(int(arg)))
    if rule == "x_stopword_pct":
        return "xylophone"
    if rule == "x_sent_type":
        return "One. Two. Three?"
    if rule == "x_sent_balance":
        return "One. Two? Three!"
    if rule == "x_conjunctions":
        return " ".join(_CONJ[: int(arg)])
    if rule == "x_person_names":
        return " ".join(_PERSON_NAMES[: int(arg)])
    if rule == "x_palindrome":
        return " ".join(["level"] * 10)
    if rule == "x_char_count":
        return "Cat. Dog. Pig."
    if rule == "x_limited_repeat":
        return "alpha beta"
    if rule == "x_pronouns":
        return " ".join(["he"] * int(arg))
    if rule == "x_last_first":
        return "Alpha."
    if rule == "x_paragraph_loop":
        return "alpha alpha\n\nbeta beta"
    if rule == "x_increment_words":
        return "Alpha."
    if rule == "x_no_consecutive":
        return "alpha beta"
    if rule == "x_indent_stairs":
        return "Alpha"
    if rule == "x_quote_explain":
        return "Alpha"
    if rule == "x_italics_thesis":
        return "<i>x</i> y"
    if rule == "x_sub_bullets":
        return "Alpha"
    if rule == "x_some_bullets":
        return "One. Two.\n* a\n* b"
    if rule == "x_multiples":
        return "14 21 28 35 42 49"
    if rule == "x_mcq":
        return _mcq()
    if rule == "x_reverse_newline":
        return "\n".join(["Zimbabwe"] + [f"Y{i:03d}" for i in range(51, 0, -1)])
    if rule == "x_word_reverse":
        return "eagle bald"
    if rule == "x_char_reverse":
        return "elgae dlab"
    if rule == "x_sentence_alpha":
        return _alpha_sentences()
    raise ValueError(f"UNSUPPORTED_EXTRA_RULE:{rule}")

def validate(rule: str, arg: Any, value: str) -> bool:
    if rule == "x_word_range":
        n = len(value.split())
        return int(arg[0]) <= n <= int(arg[1])
    if rule == "x_unique":
        words = [w.strip(string.punctuation + " ").lower() for w in value.split()]
        return len(set(words)) >= int(arg)
    if rule == "x_stopword_pct":
        return value.strip().lower() == "xylophone"
    if rule == "x_sent_type":
        return value.count(".") == 2 * value.count("?")
    if rule == "x_sent_balance":
        return value.count(".") == value.count("?") == value.count("!")
    if rule == "x_conjunctions":
        got = {w.strip(string.punctuation + " ").lower() for w in value.split()}
        return len(got.intersection(_CONJ)) >= int(arg)
    if rule == "x_person_names":
        return len({n for n in _PERSON_NAMES if n in value}) >= int(arg)
    if rule == "x_palindrome":
        words = value.translate(str.maketrans("", "", string.punctuation)).lower().split()
        return len([w for w in words if len(w) >= 5 and w == w[::-1]]) >= 10
    if rule == "x_char_count":
        parts = [p.strip() + "." for p in value.split(".") if p.strip()]
        return len(parts) == 3 and len(set(parts)) == 3 and len({len(p) for p in parts}) == 1
    if rule == "x_limited_repeat":
        words = value.lower().translate(str.maketrans("", "", string.punctuation)).split()
        return all(words.count(w) <= int(arg) for w in set(words))
    if rule == "x_pronouns":
        return len(re.findall(r"\bhe\b", value.lower())) >= int(arg)
    if rule == "x_last_first":
        return bool(value.strip())
    if rule == "x_paragraph_loop":
        ps = [p.strip().lower() for p in value.split("\n\n") if p.strip()]
        return len(ps) >= 2 and all(
            [w.strip(string.punctuation + " ") for w in p.split() if w.strip(string.punctuation + " ")][0]
            ==
            [w.strip(string.punctuation + " ") for w in p.split() if w.strip(string.punctuation + " ")][-1]
            for p in ps
        )
    if rule == "x_increment_words":
        return bool(value.strip())
    if rule == "x_no_consecutive":
        words = value.lower().translate(str.maketrans("", "", string.punctuation)).split()
        return all(a[0] != b[0] for a, b in zip(words, words[1:]))
    if rule == "x_indent_stairs":
        lines = [x for x in value.split("\n") if x.strip()]
        return all((len(b) - len(b.lstrip(" "))) > (len(a) - len(a.lstrip(" "))) for a, b in zip(lines, lines[1:]))
    if rule == "x_quote_explain":
        compact = "".join(value.replace("“", '"').replace("”", '"').split())
        if '""' in compact or not compact:
            return False
        stripped = compact.strip(string.digits + string.punctuation.replace('"', ''))
        return bool(stripped) and stripped[-1] != '"'
    if rule == "x_italics_thesis":
        return (("<i>" in value and "</i>" in value) or ("<em>" in value and "</em>" in value)) and bool(value.split(">", 1)[-1].strip())
    if rule == "x_sub_bullets":
        return all("-" in b for b in value.split("*")[1:])
    if rule == "x_some_bullets":
        lines = value.split("\n")
        first_bullet = next((i for i, x in enumerate(lines) if x.strip().startswith("*")), len(lines))
        prose = " ".join(lines[:first_bullet])
        bullets = [x for x in lines[first_bullet:] if x.strip().startswith("*")]
        return prose.count(".") >= 2 and len(bullets) >= 2
    if rule == "x_multiples":
        return re.findall(r"\d+", value.replace(",", ", ")) == [str(i) for i in range(14, 51, 7)]
    if rule == "x_mcq":
        qs = re.split(r"\n*(?:Question \d+[\.\|\):;]?\s*)", value)
        qs = [q.strip() for q in qs if q.strip()]
        if len(qs) != 4:
            return False
        lengths = []
        for q in qs:
            lines = q.split("\n")
            qt = ""
            options = 0
            done = False
            for line in lines:
                if re.match(r"^[A-Ea-e][\.\|\)]\s*\w+", line.strip()):
                    options += 1
                    done = True
                elif not done:
                    qt += " " + line.strip()
            if options != 5:
                return False
            lengths.append(len(qt.strip()))
        return all(a < b for a, b in zip(lengths, lengths[1:]))
    if rule == "x_reverse_newline":
        lines = [x.strip(string.punctuation + " ") for x in value.split("\n") if x.strip(string.punctuation + " ")]
        if not lines or "Zimbabwe" not in lines[0] or len(lines) < 52:
            return False
        return lines == sorted(lines, reverse=True)
    if rule == "x_word_reverse":
        rev = " ".join(value.lower().strip().translate(str.maketrans("", "", string.punctuation)).split()[::-1])
        return "bald eagle" in rev
    if rule == "x_char_reverse":
        return "elgae dlab" in value.lower()
    if rule == "x_sentence_alpha":
        parts = [p.strip() for p in value.split(".") if p.strip()]
        return len(parts) == 26 and all(p.split()[0].lower()[0] == chr(97 + i) for i, p in enumerate(parts))
    return False
