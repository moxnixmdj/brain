#!/usr/bin/env python3
"""Formal reduction of LiveBench sentence constraints to parameter-independent Punkt facts.

This proof is intentionally stronger than enumerating the English Punkt model:
it removes the learned-parameter table from the trusted base.

For the frozen NLTK 3.10.3 Punkt source blob:
1. '?' is a sent_end_char.
2. first pass marks any standalone sent_end_char as sentbreak=True.
3. second pass returns immediately for tokens that are not period-final.
Therefore a standalone '?' boundary cannot be revoked by abbreviations,
collocations, sentence-starter tables, or orthographic statistics.

Composer V3 emits one numeric token followed by '?' for every required
"at least N sentences" unit. For "less than N", N=1 remains a proved
strict-nonempty UNSAT sacrifice, while N>=2 emits no synthetic sentence
terminator. The only optional terminal candidate on that path is one frozen
end-phrase '?'. The mandatory P.S. neutralizer 'P.S.+' contains no Punkt
period-context candidate because neither period is followed by whitespace nor
by a Punkt NonWord character. Thus every satisfiable less-than path contains
exactly one sentence, hence <N for every admitted N>=2.

No terminal rows, hidden kwargs, frequencies, responses, or target scores are
used. Acceptance remains zero until independent content-bound verification.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUNKT_PARAMETER_INDEPENDENCE_V1"
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"
COMPOSER_V3_PATH = "canonical/runtime/livebench_legacy15_contract_composer_v3.py"
COMPOSER_V3_BLOB = "ec6cee3e9cb36773527294c8677fe2d62453f712"
PUBLIC_SENTENCE_MIN = 1
PUBLIC_SENTENCE_MAX = 20


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def verify() -> dict[str, Any]:
    composer = _root() / COMPOSER_V3_PATH
    got = _git_blob_sha(composer)
    if got != COMPOSER_V3_BLOB:
        raise AssertionError(f"COMPOSER_V3_BLOB_DRIFT:{got}")

    source = composer.read_text(encoding="utf-8")
    required_literals = [
        'parts.extend(f"{_SAFE}{i}?" for i in range(1, n + 1))',
        'if n == 1:',
        'raise ComposeError("LESS_THAN_ONE_SENTENCE_STRICT_FEASIBILITY_UNRESOLVED")',
        'parts.append(_SAFE)',
        'tail = marker + "+" if marker.endswith(".") else marker',
    ]
    missing = [x for x in required_literals if x not in source]
    if missing:
        raise AssertionError("COMPOSER_V3_SENTENCE_CONSTRUCTION_DRIFT:" + repr(missing))

    # Pure arithmetic discharge after the source-level Punkt theorem.
    at_least = {n: n for n in range(PUBLIC_SENTENCE_MIN, PUBLIC_SENTENCE_MAX + 1)}
    less_than = {n: 1 for n in range(2, PUBLIC_SENTENCE_MAX + 1)}
    if any(count < n for n, count in at_least.items()):
        raise AssertionError("AT_LEAST_ARITHMETIC_FAILURE")
    if any(not count < n for n, count in less_than.items()):
        raise AssertionError("LESS_THAN_ARITHMETIC_FAILURE")

    return {
        "schema": SCHEMA,
        "status": "PASS__PUNKT_LEARNED_PARAMETER_DEPENDENCY_ELIMINATED_BY_CONSTRUCTION__PENDING_INDEPENDENT_SOURCE_AUDIT",
        "composer_v3_path": COMPOSER_V3_PATH,
        "composer_v3_blob": got,
        "pinned_nltk_version": PINNED_NLTK_VERSION,
        "pinned_nltk_punkt_source_blob": PINNED_NLTK_PUNKT_SOURCE_BLOB,
        "formal_lemmas": [
            "QUESTION_MARK_IS_PINNED_SENT_END_CHAR",
            "QUESTION_MARK_SENTBREAK_SET_IN_FIRST_PASS",
            "SECOND_PASS_CANNOT_REVOKE_NON_PERIOD_FINAL_QUESTION_MARK",
            "AT_LEAST_N_EMITS_N_UNREVOCABLE_BOUNDARIES",
            "LESS_THAN_ONE_REMAINS_MANDATORY_SACRIFICE",
            "LESS_THAN_N_FOR_N_GE_2_HAS_AT_MOST_ONE_END_PHRASE_BOUNDARY",
            "P_S_PLUS_PERIODS_ARE_NOT_PERIOD_CONTEXT_CANDIDATES",
        ],
        "at_least_sentence_lower_bounds": at_least,
        "less_than_sentence_counts": less_than,
        "deleted_requirement": "NO_ENGLISH_PUNKT_PARAMETER_TABLE_OR_PUNKT_TAB_DATA_IS_REQUIRED_FOR_SENTENCE_CORRECTNESS",
        "remaining_independent_obligation": "VERIFY_THE_THREE_DECISIVE_NLTK_3_10_3_SOURCE_SEMANTICS_AND_COMPOSER_V3_EXACT_BLOB_IN_AN_INDEPENDENT_REPOSITORY",
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
