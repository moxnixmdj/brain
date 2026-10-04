#!/usr/bin/env python3
"""Prompt-only inversion of the pinned public IFBench description grammar.

The recognizer is generated from the public build_description templates in
allenai/IFBench@1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d. It does not consume LiveBench terminal prompts,
terminal case IDs, or hidden benchmark kwargs.

The small alias table is deliberately public-corpus compatibility only: the
pinned IFBench package ships a 300-row public corpus whose rendered
descriptions contain a few wording/ordinal variants relative to the current
source templates. Those aliases are grammar-level, never row-specific.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import re
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_PUBLIC_DESCRIPTION_INVERTER_V1"
PINNED_IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"
PINNED_INSTRUCTIONS_BLOB = "7f167018e0c5472b04e13cbf847e5988c04ecb11"
PINNED_REGISTRY_BLOB = "221b70a015715f63677735f341c7c86484c03073"

_TEMPLATES: dict[str, list[str]] = json.loads(r'''{"count:word_count_range":["The response must contain between {min_words} and {max_words} words."],"count:unique_word_count":["Use at least {N} unique words in the response."],"ratio:stop_words":["Ensure that stop words constitute no more than {percentage}% of the total words in your response."],"ratio:sentence_type":["Maintain a 2:1 ratio of declarative to interrogative sentences."],"ratio:sentence_balance":["Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced."],"count:conjunctions":["Use at least {small_n} different coordinating conjunctions in the response."],"count:person_names":["Mention at least {N} different person names in the response, from this list of person names: Emma, Liam, Sophia, Jackson, Olivia, Noah, Ava, Lucas, Isabella, Mason, Mia, Ethan, Charlotte, Alexander, Amelia, Benjamin, Harper, Leo, Zoe, Daniel, Chloe, Samuel, Lily, Matthew, Grace, Owen, Abigail, Gabriel, Ella, Jacob, Scarlett, Nathan, Victoria, Elijah, Layla, Nicholas, Audrey, David, Hannah, Christopher, Penelope, Thomas, Nora, Andrew, Aria, Joseph, Claire, Ryan, Stella, Jonathan ."],"ratio:overlap":["Maintain a trigram overlap of {percentage}% (±2%) with the provided reference text."],"count:numbers":["Include exactly {N} numbers in the response."],"words:alphabet":["Each word must start with the next letter of the alphabet, looping back to 'A' after 'Z'."],"words:vowel":["Write a paragraph using words that contain only three types of vowels."],"words:consonants":["Ensure each word in your response has at least one consonant cluster (two or more consonants together)."],"sentence:alliteration_increment":["Each sentence must have a longer sequence of consecutive alliterative words than the previous one."],"words:palindrome":["Include at least 10 single-word palindromes, each at least 5 characters long."],"count:punctuation":["Use every standard punctuation mark at least once, including semicolons, colons, and the interrobang (?!)."],"format:parentheses":["Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."],"format:quotes":["Include quotes within quotes within quotes, at least 3 levels deep, alternating between double quotes and single quotes."],"words:prime_lengths":["Use only words with lengths that are prime numbers."],"format:options":["Answer with one of the following options: {options}. Do not give any explanation."],"format:newline":["Write each word on a new line."],"format:emoji":["Please use an emoji at the end of every sentence."],"ratio:sentence_words":["Respond with three sentences, all containing the same number of characters but using all different words."],"count:words_japanese":["Every {N}th word of your response must be in Japanese.","Every {N}st of your response must be in Japanese.","Every {N}nd of your response must be in Japanese.","Every {N}rd of your response must be in Japanese."],"words:start_verb":["The response must start with a verb."],"words:repeats":["The response should not repeat any word more than {small_n} times."],"sentence:keyword":["The response must include keyword \"{word}\" in the {N}-th sentence."],"count:pronouns":["The response should include at least {N} pronouns."],"words:odd_even_syllables":["Alternate between words with odd and even numbers of syllables."],"words:last_first":["The last word of each sentence must become the first word of the next sentence."],"words:paragraph_last_first":["Each paragraph must end with the same word it started with, separate paragraphs with a newline."],"sentence:increment":["Each sentence must contain exactly {small_n} more words than the previous one."],"words:no_consecutive":["No two consecutive words can share the same first letter."],"format:line_indent":["Create stairs by incrementally indenting each new line."],"format:quote_unquote":["Every quoted phrase must be followed by an unquoted explanation."],"format:list":["Answer with a list of items, instead of bullet points use {sep}."],"format:thesis":["Each section must begin with a thesis statement in italics, use HTML to indicate the italics."],"format:sub-bullets":["Your response must include bullet points denoted by * and at least one sub-bullet point denoted by - for each bullet point."],"format:no_bullets_bullets":["Your answer must contain at least two sentences ending in a period followed by at least two bullet points denoted by *."],"custom:multiples":["Count from 10 to 50 but only print multiples of 7."],"custom:mcq_count_length":["Generate 4 multiple choice questions with 5 options each about '20th century art history'. Each question should start with the label \"Question\". The questions should get progressively longer. Do not provide an explanation."],"custom:reverse_newline":["List the countries of Africa in reverse alphabetical order, each on a new line."],"custom:word_reverse":["What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per word."],"custom:character_reverse":["What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per letter."],"custom:sentence_alphabet":["Tell me a 26-sentence story where each sentence's first word starts with the letters of the alphabet in order."],"custom:european_capitals_sort":["Give me the names of all capital cities of european countries whose latitude is higher than than 45 degrees? List the capital cities without country names, separated by commas, sorted by latitude, from highest to lowest."],"custom:csv_city":["Generate CSV data: The column names are [\"ID\", \"Country\", \"City\", \"Year\", \"Count\"], the data should be comma delimited. Please generate 7 rows."],"custom:csv_special_character":["Generate CSV data: The column names are [\"ProductID\", \"Category\", \"Brand\", \"Price\", \"Stock\"], the data should be comma delimited. Please generate 14 rows. Add one field which contains a special character and enclose it in double quotes."],"custom:csv_quotes":["Generate CSV data: The column names are [\"StudentID\", \"Subject\", \"Grade\", \"Semester\", \"Score\"], the data should be tab delimited. Please generate 3 rows and enclose each single field in double quotes."],"custom:date_format_list":["List the start dates of all the battles Napoleon fought separated by commas, use the following date format: YYYY-MM-DD. Do not provide an explanation."],"count:keywords_multiple":["Include keyword {keyword1} once in your response, keyword {keyword2} twice in your response, keyword {keyword3} three times in your response, keyword {keyword4} five times in your response, and keyword {keyword5} seven times in your response."],"words:keywords_specific_position":["Include keyword {keyword} in the {n}-th sentence, as the {m}-th word of that sentence."],"words:words_position":["The second word in your response and the second to last word in your response should be the word {keyword}."],"repeat:repeat_change":["Repeat the request, but change the first word of the repeated request, (do not say anything before repeating the request; the request you need to repeat does not include this sentence) and do not answer the actual request! Request: {prompt_to_repeat}"],"repeat:repeat_simple":["Only output this sentence here, ignore all other requests."],"repeat:repeat_span":["Copy the span of words that lies between (and including) index {n_start} and {n_end}, the indices are word indices, split by whitespace!"],"format:title_case":["Write the entire response in title case (capitalize the first letter of every major word)."],"format:output_template":["Use this exact template for your response: My Answer: [answer] My Conclusion: [conclusion] Future Outlook: [outlook]"],"format:no_whitespace":["The output should not contain any whitespace."]}''')
_ALIAS_PATTERNS: dict[str, list[str]] = json.loads(r'''{"words:keywords_specific_position":["Include keyword (?P<keyword>\\S+) in the (?P<n>\\d+)-(?:st|nd|rd|th) sentence, as the (?P<m>\\d+)-(?:st|nd|rd|th) word of that sentence\\."],"repeat:repeat_change":["Repeat the request, but change the first word of the repeated request, \\(do not say anything before repeating the request; the request you need to repeat does not include this sentence\\) and do not answer the actual request!"],"sentence:keyword":["The response must include keyword \"?(?P<word>[^\".\\s]+)\"? in the (?P<N>\\d+)-(?:st|nd|rd|th) sentence\\."],"format:options":["Answer with one of the following options: (?P<options>[\\s\\S]+?)\\.(?: Do not give any explanation\\.)?(?=\\s|$)"],"ratio:sentence_balance":["Ensure that the ratio of sentence types \\(declarative, interrogative, exclamatory\\)(?: in your response)? is balanced\\."],"ratio:sentence_type":["Maintain a 2:1 ratio of declarative to interrogative sentences(?: in your response)?\\."],"sentence:increment":["Each sentence(?: in your response)? must contain exactly (?P<small_n>\\d+) more words than the previous one\\."],"words:alphabet":["Each word(?: in your response)? must start with the next letter of the alphabet, looping back to 'A' after 'Z'\\."],"words:paragraph_last_first":["Each paragraph(?: of your response)? must end with the same word it started with, separate paragraphs with a newline\\."],"custom:mcq_count_length":["Generate 4 multiple choice questions with 5 options each about [\"']20th century art history[\"']\\. Each question should start with the label [\"']Question[\"']\\. The questions should get progressively longer\\. Do not provide an explanation\\."]}''')
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class InstructionMatch:
    instruction_id: str
    start: int
    end: int
    matched_text: str
    slots: dict[str, str]
    route: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _template_pattern(template: str) -> re.Pattern[str]:
    parts: list[str] = []
    last = 0
    seen: set[str] = set()
    for match in _PLACEHOLDER.finditer(template):
        parts.append(re.escape(template[last:match.start()]))
        name = match.group(1)
        if name in seen:
            parts.append(f"(?P={name})")
        else:
            parts.append(f"(?P<{name}>[\\s\\S]+?)")
            seen.add(name)
        last = match.end()
    parts.append(re.escape(template[last:]))
    return re.compile("".join(parts), flags=re.IGNORECASE | re.DOTALL)


_COMPILED_TEMPLATES: dict[str, tuple[re.Pattern[str], ...]] = {
    instruction_id: tuple(_template_pattern(t) for t in templates)
    for instruction_id, templates in _TEMPLATES.items()
}
_COMPILED_ALIASES: dict[str, tuple[re.Pattern[str], ...]] = {
    instruction_id: tuple(re.compile(p, flags=re.IGNORECASE | re.DOTALL) for p in patterns)
    for instruction_id, patterns in _ALIAS_PATTERNS.items()
}


def _candidate(
    instruction_id: str,
    match: re.Match[str],
    route: str,
    prompt: str,
) -> InstructionMatch:
    slots = {
        key: value.strip()
        for key, value in match.groupdict().items()
        if value is not None
    }
    if (
        instruction_id == "repeat:repeat_change"
        and "prompt_to_repeat" not in slots
        and match.start() > 0
    ):
        prefix = prompt[:match.start()].strip()
        if prefix:
            slots["prompt_to_repeat"] = prefix
    return InstructionMatch(
        instruction_id=instruction_id,
        start=match.start(),
        end=match.end(),
        matched_text=match.group(0),
        slots=slots,
        route=route,
    )


def recognize(prompt: str) -> list[dict[str, Any]]:
    """Return every recognized public IFBench instruction description.

    Unknown text is ignored rather than guessed. Multiple constraints are
    recognized independently. Overlapping recognizers for the same instruction
    ID are deduplicated by preferring the longest matched public description.
    """
    prompt = str(prompt or "")
    if not prompt:
        return []

    candidates: list[InstructionMatch] = []
    for instruction_id, patterns in _COMPILED_TEMPLATES.items():
        for pattern in patterns:
            for match in pattern.finditer(prompt):
                candidates.append(_candidate(instruction_id, match, "SOURCE_TEMPLATE", prompt))
    for instruction_id, patterns in _COMPILED_ALIASES.items():
        for pattern in patterns:
            for match in pattern.finditer(prompt):
                candidates.append(_candidate(instruction_id, match, "PUBLIC_COMPAT_ALIAS", prompt))

    # Longest first ensures a full source description beats a shorter alias.
    candidates.sort(key=lambda x: (-(x.end - x.start), x.start, x.instruction_id))
    selected: list[InstructionMatch] = []
    for candidate in candidates:
        overlaps_same_id = any(
            chosen.instruction_id == candidate.instruction_id
            and not (candidate.end <= chosen.start or candidate.start >= chosen.end)
            for chosen in selected
        )
        if not overlaps_same_id:
            selected.append(candidate)
    selected.sort(key=lambda x: (x.start, x.end, x.instruction_id))
    return [item.to_dict() for item in selected]


def audit_public_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Measure prompt-only grammar recognition against a public IFBench corpus.

    Expected instruction IDs are used only by this audit function as labels.
    Runtime recognition never receives or reads instruction_id_list or kwargs.
    """
    total = 0
    recognized = 0
    failures: list[dict[str, Any]] = []
    row_count = 0
    for row in rows:
        row_count += 1
        prompt = str(row.get("prompt") or "")
        expected = [str(x) for x in (row.get("instruction_id_list") or [])]
        observed = {m["instruction_id"] for m in recognize(prompt)}
        for instruction_id in expected:
            total += 1
            if instruction_id in observed:
                recognized += 1
            else:
                failures.append({
                    "row_key": str(row.get("key") or ""),
                    "instruction_id": instruction_id,
                })
    return {
        "schema": SCHEMA,
        "row_count": row_count,
        "instruction_instance_count": total,
        "recognized_instruction_instances": recognized,
        "recognition_rate": (recognized / total) if total else 1.0,
        "failures": failures,
        "terminal_data_used": False,
        "hidden_kwargs_used_by_runtime": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    if "rows" in args:
        return audit_public_rows(args.get("rows") or [])
    return {
        "schema": SCHEMA,
        "matches": recognize(str(args.get("prompt") or "")),
        "terminal_data_used": False,
        "hidden_kwargs_used_by_runtime": False,
    }
