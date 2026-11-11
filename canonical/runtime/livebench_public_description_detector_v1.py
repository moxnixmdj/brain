#!/usr/bin/env python3
"""Total conservative detector for the pinned public LiveBench IF description language.

Generated from literal-only self._description_pattern assignments at pinned
LiveBench commit 8f8e5c381a16e3f24257776edd53471fe86f8091. It does not use terminal prompts,
hidden instruction IDs, hidden kwargs, or case-specific data.

A detection means a prompt contains the literal skeleton of a public checker
description. False positives are permitted and only cause fail-closed blocking.
The derivation target is zero false negatives for rendered public descriptions.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_DESCRIPTION_DETECTOR_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PUBLIC_DESCRIPTION_PATTERNS = {
  "KeywordChecker": {
    "family": "legacy",
    "id": "keywords:existence",
    "patterns": [
      "Include keywords {keywords} in the response."
    ]
  },
  "KeywordFrequencyChecker": {
    "family": "legacy",
    "id": "keywords:frequency",
    "patterns": [
      "In your response, the word {keyword} should appear {relation} {frequency} times."
    ]
  },
  "ForbiddenWords": {
    "family": "legacy",
    "id": "keywords:forbidden_words",
    "patterns": [
      "Do not include keywords {forbidden_words} in the response."
    ]
  },
  "LetterFrequencyChecker": {
    "family": "legacy",
    "id": "keywords:letter_frequency",
    "patterns": [
      "In your response, the letter {letter} should appear {let_relation} {let_frequency} times."
    ]
  },
  "ResponseLanguageChecker": {
    "family": "legacy",
    "id": "language:response_language",
    "patterns": [
      "Your ENTIRE response should be in {language} language, no other language is allowed."
    ]
  },
  "NumberOfSentences": {
    "family": "legacy",
    "id": "length_constraints:number_sentences",
    "patterns": [
      "Your response should contain {relation} {num_sentences} sentences."
    ]
  },
  "ParagraphChecker": {
    "family": "legacy",
    "id": "length_constraints:number_paragraphs",
    "patterns": [
      "There should be {num_paragraphs} paragraphs. Paragraphs are separated with the markdown divider: ***"
    ]
  },
  "NumberOfWords": {
    "family": "legacy",
    "id": "length_constraints:number_words",
    "patterns": [
      "Answer with {relation} {num_words} words."
    ]
  },
  "ParagraphFirstWordCheck": {
    "family": "legacy",
    "id": "length_constraints:nth_paragraph_first_word",
    "patterns": [
      "There should be {num_paragraphs} paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\\n\\\n' in python. Paragraph {nth_paragraph} must start with word {first_word}."
    ]
  },
  "PlaceholderChecker": {
    "family": "legacy",
    "id": "detectable_content:number_placeholders",
    "patterns": [
      "The response must contain at least {num_placeholders} placeholders represented by square brackets, such as [address]."
    ]
  },
  "PostscriptChecker": {
    "family": "legacy",
    "id": "detectable_content:postscript",
    "patterns": [
      "At the end of your response, please explicitly add a postscript starting with {postscript}"
    ]
  },
  "BulletListChecker": {
    "family": "legacy",
    "id": "detectable_format:number_bullet_lists",
    "patterns": [
      "Your answer must contain exactly {num_bullets} bullet points. Use the markdown bullet points such as:\n* This is point 1. \n* This is point 2"
    ]
  },
  "ConstrainedResponseChecker": {
    "family": "legacy",
    "id": "detectable_format:constrained_response",
    "patterns": [
      "Answer with one of the following options: {response_options}"
    ]
  },
  "HighlightSectionChecker": {
    "family": "legacy",
    "id": "detectable_format:number_highlighted_sections",
    "patterns": [
      "Highlight at least {num_highlights} sections in your answer with markdown, i.e. *highlighted section*."
    ]
  },
  "SectionChecker": {
    "family": "legacy",
    "id": "detectable_format:multiple_sections",
    "patterns": [
      "Your response must have {num_sections} sections. Mark the beginning of each section with {section_spliter} X, such as:\n{section_spliter} 1\n[content of section 1]\n{section_spliter} 2\n[content of section 2]"
    ]
  },
  "JsonFormat": {
    "family": "legacy",
    "id": "detectable_format:json_format",
    "patterns": [
      "Entire output should be wrapped in JSON format. You can use markdown ticks such as ```."
    ]
  },
  "TitleChecker": {
    "family": "legacy",
    "id": "detectable_format:title",
    "patterns": [
      "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    ]
  },
  "TwoResponsesChecker": {
    "family": "legacy",
    "id": "combination:two_responses",
    "patterns": [
      "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******."
    ]
  },
  "RepeatPromptThenAnswer": {
    "family": "legacy",
    "id": "combination:repeat_prompt",
    "patterns": [
      "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)"
    ]
  },
  "EndChecker": {
    "family": "legacy",
    "id": "startend:end_checker",
    "patterns": [
      "Finish your response with this exact phrase {ender}. No other words should follow this phrase."
    ]
  },
  "CapitalWordFrequencyChecker": {
    "family": "legacy",
    "id": "change_case:capital_word_frequency",
    "patterns": [
      "In your response, words with all capital letters should appear {relation} {frequency} times."
    ]
  },
  "CapitalLettersEnglishChecker": {
    "family": "legacy",
    "id": "change_case:english_capital",
    "patterns": [
      "Your entire response should be in English, and in all capital letters."
    ]
  },
  "LowercaseLettersEnglishChecker": {
    "family": "legacy",
    "id": "change_case:english_lowercase",
    "patterns": [
      "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed."
    ]
  },
  "CommaChecker": {
    "family": "legacy",
    "id": "punctuation:no_comma",
    "patterns": [
      "In your entire response, refrain from the use of any commas."
    ]
  },
  "QuotationChecker": {
    "family": "legacy",
    "id": "startend:quotation",
    "patterns": [
      "Wrap your entire response with double quotation marks."
    ]
  },
  "WordCountRangeChecker": {
    "family": "modern",
    "id": "count:word_count_range",
    "patterns": [
      "The response must contain between {min_words} and {max_words} words."
    ]
  },
  "UniqueWordCountChecker": {
    "family": "modern",
    "id": "count:unique_word_count",
    "patterns": [
      "Use at least {N} unique words in the response."
    ]
  },
  "StopWordPercentageChecker": {
    "family": "modern",
    "id": "ratio:stop_words",
    "patterns": [
      "Ensure that stop words constitute no more than {percentage}% of the total words in your response."
    ]
  },
  "SentTypeRatioChecker": {
    "family": "modern",
    "id": "ratio:sentence_type",
    "patterns": [
      "Maintain a 2:1 ratio of declarative to interrogative sentences."
    ]
  },
  "SentBalanceChecker": {
    "family": "modern",
    "id": "ratio:sentence_balance",
    "patterns": [
      "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced."
    ]
  },
  "ConjunctionCountChecker": {
    "family": "modern",
    "id": "count:conjunctions",
    "patterns": [
      "Use at least {small_n} different coordinating conjunctions in the response."
    ]
  },
  "PersonNameCountChecker": {
    "family": "modern",
    "id": "count:person_names",
    "patterns": [
      "Mention at least {N} different person names in the response, from this list of person names: Emma, Liam, Sophia, Jackson, Olivia, Noah, Ava, Lucas, Isabella, Mason, Mia, Ethan, Charlotte, Alexander, Amelia, Benjamin, Harper, Leo, Zoe, Daniel, Chloe, Samuel, Lily, Matthew, Grace, Owen, Abigail, Gabriel, Ella, Jacob, Scarlett, Nathan, Victoria, Elijah, Layla, Nicholas, Audrey, David, Hannah, Christopher, Penelope, Thomas, Nora, Andrew, Aria, Joseph, Claire, Ryan, Stella, Jonathan ."
    ]
  },
  "NGramOverlapChecker": {
    "family": "modern",
    "id": "ratio:overlap",
    "patterns": [
      "Maintain a trigram overlap of {percentage}% (±2%) with the provided reference text."
    ]
  },
  "NumbersCountChecker": {
    "family": "modern",
    "id": "count:numbers",
    "patterns": [
      "Include exactly {N} numbers in the response; do not use commas within the numbers."
    ]
  },
  "AlphabetLoopChecker": {
    "family": "modern",
    "id": "words:alphabet",
    "patterns": [
      "Each word must start with the next letter of the alphabet, looping back to 'A' after 'Z'."
    ]
  },
  "ThreeVowelChecker": {
    "family": "modern",
    "id": "words:vowel",
    "patterns": [
      "Your response must contain at most three different vowels."
    ]
  },
  "ConsonantClusterChecker": {
    "family": "modern",
    "id": "words:consonants",
    "patterns": [
      "Ensure each word in your response has at least one consonant cluster (two or more consonants together)."
    ]
  },
  "IncrementingAlliterationChecker": {
    "family": "modern",
    "id": "sentence:alliteration_increment",
    "patterns": [
      "Each sentence must have a longer sequence of consecutive alliterative words than the previous one."
    ]
  },
  "PalindromeChecker": {
    "family": "modern",
    "id": "words:palindrome",
    "patterns": [
      "Include at least 10 single-word palindromes, each at least 5 characters long."
    ]
  },
  "PunctuationCoverChecker": {
    "family": "modern",
    "id": "count:punctuation",
    "patterns": [
      "Use every standard punctuation mark at least once, including (but not limited to) semicolons, colons, and the interrobang (?!)."
    ]
  },
  "NestedParenthesesChecker": {
    "family": "modern",
    "id": "format:parentheses",
    "patterns": [
      "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."
    ]
  },
  "NestedQuotesChecker": {
    "family": "modern",
    "id": "format:quotes",
    "patterns": [
      "Include quotes within quotes within quotes, at least 3 levels deep, alternating between double quotes and single quotes."
    ]
  },
  "PrimeLengthsChecker": {
    "family": "modern",
    "id": "words:prime_lengths",
    "patterns": [
      "Use only words with lengths that are prime numbers."
    ]
  },
  "OptionsResponseChecker": {
    "family": "modern",
    "id": "format:options",
    "patterns": [
      "Answer with one of the following options: {options}. Do not give any explanation."
    ]
  },
  "NewLineWordsChecker": {
    "family": "modern",
    "id": "format:newline",
    "patterns": [
      "Write each word on a new line."
    ]
  },
  "EmojiSentenceChecker": {
    "family": "modern",
    "id": "format:emoji",
    "patterns": [
      "Please use an emoji at the end of every sentence, prior to any punctuation."
    ]
  },
  "CharacterCountUniqueWordsChecker": {
    "family": "modern",
    "id": "ratio:sentence_words",
    "patterns": [
      "Respond with three sentences, all containing the same number of characters; the sentences cannot be identical."
    ]
  },
  "NthWordJapaneseChecker": {
    "family": "modern",
    "id": "count:words_japanese",
    "patterns": [
      "Every {N}th word of your response must be in Japanese, using Japanese characters.",
      "Every {N}st of your response must be in Japanese, using Japanese characters.",
      "Every {N}nd of your response must be in Japanese, using Japanese characters.",
      "Every {N}rd of your response must be in Japanese, using Japanese characters."
    ]
  },
  "StartWithVerbChecker": {
    "family": "modern",
    "id": "words:start_verb",
    "patterns": [
      "The response must start with a verb."
    ]
  },
  "LimitedWordRepeatChecker": {
    "family": "modern",
    "id": "words:repeats",
    "patterns": [
      "The response should not repeat any word more than {small_n} times."
    ]
  },
  "IncludeKeywordChecker": {
    "family": "modern",
    "id": "sentence:keyword",
    "patterns": [
      "The response must include keyword \"{word}\" in the {N}-th sentence."
    ]
  },
  "PronounCountChecker": {
    "family": "modern",
    "id": "count:pronouns",
    "patterns": [
      "The response should include at least {N} personal pronouns."
    ]
  },
  "AlternateParitySyllablesChecker": {
    "family": "modern",
    "id": "words:odd_even_syllables",
    "patterns": [
      "Alternate between words with odd and even numbers of syllables."
    ]
  },
  "LastWordFirstNextChecker": {
    "family": "modern",
    "id": "words:last_first",
    "patterns": [
      "The last word of each sentence must become the first word of the next sentence."
    ]
  },
  "ParagraphLastFirstWordMatchChecker": {
    "family": "modern",
    "id": "words:paragraph_last_first",
    "patterns": [
      "Write at least two paragraphs, where each paragraph ends with exactly the same word it started with, and separate paragraphs with two newlines."
    ]
  },
  "IncrementingWordCountChecker": {
    "family": "modern",
    "id": "sentence:increment",
    "patterns": [
      "Each sentence must contain exactly {small_n} more words than the previous one."
    ]
  },
  "NoConsecutiveFirstLetterChecker": {
    "family": "modern",
    "id": "words:no_consecutive",
    "patterns": [
      "No two consecutive words can share the same first letter."
    ]
  },
  "IndentStairsChecker": {
    "family": "modern",
    "id": "format:line_indent",
    "patterns": [
      "Create stairs by incrementally indenting each new line."
    ]
  },
  "QuoteExplanationChecker": {
    "family": "modern",
    "id": "format:quote_unquote",
    "patterns": [
      "Every quoted phrase must be followed by an unquoted explanation."
    ]
  },
  "SpecialBulletPointsChecker": {
    "family": "modern",
    "id": "format:list",
    "patterns": [
      "Answer with a newline-separated list of items, instead of bullet points use {sep}."
    ]
  },
  "ItalicsThesisChecker": {
    "family": "modern",
    "id": "format:thesis",
    "patterns": [
      "Each section must begin with a thesis statement in italics, use HTML to indicate the italics."
    ]
  },
  "SubBulletPointsChecker": {
    "family": "modern",
    "id": "format:sub-bullets",
    "patterns": [
      "Your response must include newline-separated bullet points denoted by * and at least one sub-bullet point denoted by - for each bullet point."
    ]
  },
  "SomeBulletPointsChecker": {
    "family": "modern",
    "id": "format:no_bullets_bullets",
    "patterns": [
      "Your answer must contain at least two sentences ending in a period followed by at least two newline-separated bullet points denoted by *."
    ]
  },
  "PrintMultiplesChecker": {
    "family": "modern",
    "id": "custom:multiples",
    "patterns": [
      "Count from 10 to 50 but only print multiples of 7."
    ]
  },
  "MultipleChoiceQuestionsChecker": {
    "family": "modern",
    "id": "custom:mcq_count_length",
    "patterns": [
      "Generate 4 multiple choice questions with 5 options each about '20th century art history'. Each question should start with the label \"Question\". The questions should get progressively longer. Do not provide an explanation."
    ]
  },
  "ReverseNewlineChecker": {
    "family": "modern",
    "id": "custom:reverse_newline",
    "patterns": [
      "List the countries of Africa in reverse alphabetical order, each on a new line."
    ]
  },
  "WordReverseOrderChecker": {
    "family": "modern",
    "id": "custom:word_reverse",
    "patterns": [
      "What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per word."
    ]
  },
  "CharacterReverseOrderChecker": {
    "family": "modern",
    "id": "custom:character_reverse",
    "patterns": [
      "What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per letter."
    ]
  },
  "SentenceAlphabetChecker": {
    "family": "modern",
    "id": "custom:sentence_alphabet",
    "patterns": [
      "Tell me a 26-sentence story where each sentence's first word starts with the letters of the alphabet in order."
    ]
  },
  "EuropeanCapitalsSortChecker": {
    "family": "modern",
    "id": "custom:european_capitals_sort",
    "patterns": [
      "Give me the names of all capital cities of european countries whose latitude is higher than than 45 degrees? List the capital cities without country names, separated by commas, sorted by latitude, from highest to lowest."
    ]
  },
  "CityCSVChecker": {
    "family": "modern",
    "id": "custom:csv_city",
    "patterns": [
      "Generate CSV data: The column names are [\"ID\", \"Country\", \"City\", \"Year\", \"Count\"], the data should be comma delimited. Please generate 7 rows."
    ]
  },
  "SpecialCharacterCSVChecker": {
    "family": "modern",
    "id": "custom:csv_special_character",
    "patterns": [
      "Generate CSV data: The column names are [\"ProductID\", \"Category\", \"Brand\", \"Price\", \"Stock\"], the data should be comma delimited. Please generate 14 rows. Add one field which contains a special character and enclose it in double quotes."
    ]
  },
  "QuotesCSVChecker": {
    "family": "modern",
    "id": "custom:csv_quotes",
    "patterns": [
      "Generate CSV data: The column names are [\"StudentID\", \"Subject\", \"Grade\", \"Semester\", \"Score\"], the data should be tab delimited. Please generate 3 rows and enclose each single field in double quotes."
    ]
  },
  "DateFormatListChecker": {
    "family": "modern",
    "id": "custom:date_format_list",
    "patterns": [
      "List the start dates of all the battles Napoleon fought separated by commas, use the following date format: YYYY-MM-DD. Do not provide an explanation."
    ]
  },
  "KeywordsMultipleChecker": {
    "family": "modern",
    "id": "count:keywords_multiple",
    "patterns": [
      "Include keyword '{keyword1}' exactly once in your response, keyword '{keyword2}' exactly twice in your response, keyword '{keyword3}' exactly three times in your response, keyword '{keyword4}' exactly five times in your response, and keyword '{keyword5}' exactly seven times in your response."
    ]
  },
  "KeywordSpecificPositionChecker": {
    "family": "modern",
    "id": "words:keywords_specific_position",
    "patterns": [
      "Include keyword '{keyword}' in the {n}-th sentence, as the {m}-th word of that sentence."
    ]
  },
  "WordsPositionChecker": {
    "family": "modern",
    "id": "words:words_position",
    "patterns": [
      "The second word in your response and the second to last word in your response should be the word '{keyword}'."
    ]
  },
  "RepeatChangeChecker": {
    "family": "modern",
    "id": "repeat:repeat_change",
    "patterns": [
      "Repeat the request, but change the first word of the repeated request, (do not say anything before repeating the request; the request you need to repeat does not include this sentence) and do not answer the actual request! Request: {prompt_to_repeat}"
    ]
  },
  "RepeatSimpleChecker": {
    "family": "modern",
    "id": "repeat:repeat_simple",
    "patterns": [
      "Only output this sentence here, ignore all other requests."
    ]
  },
  "RepeatSpanChecker": {
    "family": "modern",
    "id": "repeat:repeat_span",
    "patterns": [
      "Copy the span of words that lies between (and including) index {n_start} and {n_end}, the indices are character indices!"
    ]
  },
  "TitleCaseChecker": {
    "family": "modern",
    "id": "format:title_case",
    "patterns": [
      "Write the entire response in title case (capitalize the first letter of every word)."
    ]
  },
  "OutputTemplateChecker": {
    "family": "modern",
    "id": "format:output_template",
    "patterns": [
      "Use this exact template for your response: My Answer: [answer] My Conclusion: [conclusion] Future Outlook: [outlook]"
    ]
  },
  "NoWhitespaceChecker": {
    "family": "modern",
    "id": "format:no_whitespace",
    "patterns": [
      "The output should not contain any whitespace."
    ]
  }
}


def _literal_regex(text: str) -> str:
    pieces = re.split(r"(\\s+)", text)
    return "".join(r"\\s+" if p and p.isspace() else re.escape(p) for p in pieces if p)


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    pieces = re.split(r"(\\{[^{}]+\\})", pattern)
    body = []
    for piece in pieces:
        if not piece:
            continue
        if re.fullmatch(r"\\{[^{}]+\\}", piece):
            body.append(r".*?")
        else:
            body.append(_literal_regex(piece))
    return re.compile("".join(body), flags=re.DOTALL)


_COMPILED = {
    checker: [
        (index, pattern, pattern_to_regex(pattern))
        for index, pattern in enumerate(meta["patterns"])
    ]
    for checker, meta in PUBLIC_DESCRIPTION_PATTERNS.items()
}


def detect_public_descriptions(prompt: str) -> list[dict[str, Any]]:
    prompt = str(prompt or "")
    detections: list[dict[str, Any]] = []
    for checker, compiled in _COMPILED.items():
        meta = PUBLIC_DESCRIPTION_PATTERNS[checker]
        for index, pattern, regex in compiled:
            for match in regex.finditer(prompt):
                detections.append({
                    "checker": checker,
                    "family": meta["family"],
                    "id": meta["id"],
                    "pattern_index": index,
                    "span": [match.start(), match.end()],
                    "matched_text": match.group(0),
                })
    detections.sort(key=lambda x: (x["span"][0], x["span"][1], x["checker"], x["pattern_index"]))
    return detections


def synthetic_render(pattern: str, token: str = "X") -> str:
    return re.sub(r"\\{[^{}]+\\}", token, pattern)


def verify_registry_self_coverage() -> dict[str, Any]:
    failures = []
    total_patterns = 0
    for checker, meta in PUBLIC_DESCRIPTION_PATTERNS.items():
        for index, pattern in enumerate(meta["patterns"]):
            total_patterns += 1
            rendered = synthetic_render(pattern)
            got = {
                d["checker"]
                for d in detect_public_descriptions(rendered)
            }
            if checker not in got:
                failures.append({
                    "checker": checker,
                    "pattern_index": index,
                    "pattern": pattern,
                    "rendered": rendered,
                    "detected": sorted(got),
                })
    return {
        "schema": SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "checker_count": len(PUBLIC_DESCRIPTION_PATTERNS),
        "pattern_count": total_patterns,
        "failures": failures,
        "terminal_case_content_used": False,
        "hidden_metadata_used": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_registry_self_coverage(), indent=2, sort_keys=True, ensure_ascii=False))
