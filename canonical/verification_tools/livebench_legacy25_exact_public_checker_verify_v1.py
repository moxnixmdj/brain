#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from canonical.runtime import livebench_legacy25_witness_compiler_v1 as compiler
from instruction_following_eval import instructions_registry as registry

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"

KIND_TO_ID = {
    "keyword_existence": "keywords:existence",
    "keyword_frequency": "keywords:frequency",
    "forbidden_words": "keywords:forbidden_words",
    "letter_frequency": "keywords:letter_frequency",
    "response_language": "language:response_language",
    "number_sentences": "length_constraints:number_sentences",
    "number_paragraphs": "length_constraints:number_paragraphs",
    "number_words": "length_constraints:number_words",
    "nth_paragraph_first_word": "length_constraints:nth_paragraph_first_word",
    "number_placeholders": "detectable_content:number_placeholders",
    "postscript": "detectable_content:postscript",
    "number_bullet_lists": "detectable_format:number_bullet_lists",
    "constrained_response": "detectable_format:constrained_response",
    "number_highlighted_sections": "detectable_format:number_highlighted_sections",
    "multiple_sections": "detectable_format:multiple_sections",
    "json_format": "detectable_format:json_format",
    "title": "detectable_format:title",
    "two_responses": "combination:two_responses",
    "repeat_prompt": "combination:repeat_prompt",
    "end_checker": "startend:end_checker",
    "capital_word_frequency": "change_case:capital_word_frequency",
    "english_capital": "change_case:english_capital",
    "english_lowercase": "change_case:english_lowercase",
    "no_comma": "punctuation:no_comma",
    "quotation": "startend:quotation",
}

@dataclass
class Case:
    kind: str
    checker: Any
    description: str
    prompt: str


def make(kind: str, kwargs: dict[str, Any] | None = None, prefix: str | None = None) -> Case:
    iid = KIND_TO_ID[kind]
    checker = registry.INSTRUCTION_DICT[iid](iid)
    desc = checker.build_description(**(kwargs or {}))
    prompt = (prefix.rstrip() + "\n" + desc) if prefix else desc
    return Case(kind, checker, desc, prompt)


def check_constructive(case: Case) -> tuple[bool, dict[str, Any]]:
    parsed = compiler.parse_specs(case.prompt)
    parsed_kinds = [x.kind for x in parsed]
    out = compiler.synthesize(case.prompt)
    ok = case.kind in parsed_kinds and out.get("status") == "PASS" and bool(case.checker.check_following(str(out.get("response") or "")))
    return ok, {"kind": case.kind, "instruction_id": KIND_TO_ID[case.kind], "parsed_kinds": parsed_kinds, "compiler_status": out.get("status"), "compiler_reason": out.get("reason")}


def check_blocked(case: Case) -> tuple[bool, dict[str, Any]]:
    parsed = compiler.parse_specs(case.prompt)
    parsed_kinds = [x.kind for x in parsed]
    out = compiler.synthesize(case.prompt)
    ok = case.kind in parsed_kinds and out.get("status") == "BLOCKED" and out.get("reason") == "LANGDETECT_DEPENDENT_FAMILY_REQUIRES_EXACT_VALIDATOR"
    return ok, {"kind": case.kind, "instruction_id": KIND_TO_ID[case.kind], "parsed_kinds": parsed_kinds, "compiler_status": out.get("status"), "compiler_reason": out.get("reason")}


def check_composition(cases: list[Case], prompt: str | None = None) -> tuple[bool, dict[str, Any]]:
    combined = prompt if prompt is not None else "\n".join(c.description for c in cases)
    out = compiler.synthesize(combined)
    response = str(out.get("response") or "")
    checker_results = [bool(c.checker.check_following(response)) for c in cases]
    parsed = [x.kind for x in compiler.parse_specs(combined)]
    ok = out.get("status") == "PASS" and all(checker_results) and all(c.kind in parsed for c in cases)
    return ok, {"kinds": [c.kind for c in cases], "parsed_kinds": parsed, "compiler_status": out.get("status"), "compiler_reason": out.get("reason"), "checker_results": checker_results}


def main() -> dict[str, Any]:
    constructive: list[Case] = []
    for n in range(1, 9):
        constructive.extend([
            make("keyword_frequency", {"keyword": "apple", "frequency": n, "relation": "at least"}),
            make("keyword_frequency", {"keyword": "apple", "frequency": n + 1, "relation": "less than"}),
            make("letter_frequency", {"letter": "a", "let_frequency": n, "let_relation": "at least"}),
            make("letter_frequency", {"letter": "a", "let_frequency": n + 1, "let_relation": "less than"}),
            make("number_sentences", {"num_sentences": n, "relation": "at least"}),
            make("number_sentences", {"num_sentences": n + 1, "relation": "less than"}),
            make("number_paragraphs", {"num_paragraphs": n}),
            make("number_words", {"num_words": n, "relation": "at least"}),
            make("number_words", {"num_words": n + 1, "relation": "less than"}),
            make("number_placeholders", {"num_placeholders": n}),
            make("number_bullet_lists", {"num_bullets": n}),
            make("number_highlighted_sections", {"num_highlights": n}),
            make("multiple_sections", {"section_spliter": "Section", "num_sections": n}),
            make("capital_word_frequency", {"capital_frequency": n, "capital_relation": "at least"}),
            make("capital_word_frequency", {"capital_frequency": n + 1, "capital_relation": "less than"}),
        ])
    for n in range(1, 6):
        for nth in range(1, n + 1):
            constructive.append(make("nth_paragraph_first_word", {"num_paragraphs": n, "nth_paragraph": nth, "first_word": "zebra"}))
    constructive.extend([
        make("keyword_existence", {"keywords": ["apple", "river"]}),
        make("forbidden_words", {"forbidden_words": ["apple", "river"]}),
        make("postscript", {"postscript_marker": "P.S."}),
        make("postscript", {"postscript_marker": "P.P.S"}),
        make("constrained_response"), make("json_format"), make("title"), make("two_responses"),
        make("repeat_prompt", {"prompt_to_repeat": "Write a funny haiku about moms."}, prefix="Write a funny haiku about moms."),
        make("end_checker", {"end_phrase": "Any other questions?"}), make("no_comma"), make("quotation"),
    ])
    blocked = [make("response_language", {"language": "en"}), make("english_capital"), make("english_lowercase")]
    failures=[]; constructive_pass=0
    for case in constructive:
        ok, detail=check_constructive(case)
        if ok: constructive_pass += 1
        else: failures.append({"phase":"constructive", **detail})
    blocked_pass=0
    for case in blocked:
        ok, detail=check_blocked(case)
        if ok: blocked_pass += 1
        else: failures.append({"phase":"blocked", **detail})
    compositions=[]
    compositions.append(([make("keyword_existence", {"keywords":["apple"]}), make("forbidden_words", {"forbidden_words":["omega"]})], None))
    compositions.append(([make("keyword_existence", {"keywords":["apple"]}), make("json_format")], None))
    compositions.append(([make("forbidden_words", {"forbidden_words":["omega"]}), make("json_format")], None))
    compositions.append(([make("keyword_existence", {"keywords":["apple"]}), make("two_responses")], None))
    compositions.append(([make("forbidden_words", {"forbidden_words":["omega"]}), make("two_responses")], None))
    compositions.append(([make("keyword_existence", {"keywords":["apple"]}), make("title")], None))
    compositions.append(([make("no_comma"), make("title")], None))
    compositions.append(([make("number_words", {"num_words":8,"relation":"at least"}), make("no_comma")], None))
    compositions.append(([make("number_placeholders", {"num_placeholders":2}), make("no_comma")], None))
    compositions.append(([make("number_highlighted_sections", {"num_highlights":2}), make("no_comma")], None))
    compositions.append(([make("multiple_sections", {"section_spliter":"Section","num_sections":2}), make("no_comma")], None))
    compositions.append(([make("end_checker", {"end_phrase":"Any other questions?"}), make("no_comma")], None))
    compositions.append(([make("capital_word_frequency", {"capital_frequency":3,"capital_relation":"at least"}), make("no_comma")], None))
    compositions.append(([make("quotation"), make("keyword_existence", {"keywords":["apple"]})], None))
    title=make("title"); repeat_prefix="Base request.\n"+title.description; repeat=make("repeat_prompt", {"prompt_to_repeat":repeat_prefix})
    compositions.append(([title, repeat], repeat_prefix+"\n"+repeat.description))
    composition_pass=0
    for cases,prompt in compositions:
        ok,detail=check_composition(cases,prompt)
        if ok: composition_pass += 1
        else: failures.append({"phase":"composition", **detail})
    expected_registry=set(KIND_TO_ID.values()); actual_registry=set(registry.INSTRUCTION_DICT.keys())
    registry_exact=expected_registry==actual_registry and len(actual_registry)==25
    if not registry_exact: failures.append({"phase":"registry","expected_count":len(expected_registry),"actual_count":len(actual_registry),"missing":sorted(expected_registry-actual_registry),"unexpected":sorted(actual_registry-expected_registry)})
    return {"schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY25_EXACT_PUBLIC_CHECKER_VERIFICATION_V1","pinned_livebench_commit":PINNED_LIVEBENCH_COMMIT,"status":"PASS" if not failures else "FAIL","registry_exact_25":registry_exact,"constructive_cases":len(constructive),"constructive_passed":constructive_pass,"fail_closed_language_cases":len(blocked),"fail_closed_language_passed":blocked_pass,"composition_cases":len(compositions),"composition_passed":composition_pass,"failures":failures,"terminal_cases_read":0,"semantic_quality_claim":False,"acceptance_credit_delta":0}


if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); args=ap.parse_args(); result=main(); payload=json.dumps(result,indent=2,sort_keys=True); print(payload)
    if args.output:
        with open(args.output,"w",encoding="utf-8") as f: f.write(payload+"\n")
    raise SystemExit(0 if result["status"]=="PASS" else 1)
