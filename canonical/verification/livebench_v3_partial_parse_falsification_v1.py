#!/usr/bin/env python3
"""Deterministic falsification of LiveBench structural-witness V3 partial parsing.

Uses only:
- the current Brain V3 runtime under test; and
- the frozen PUBLIC LiveBench PalindromeChecker semantics.

No terminal LiveBench case content, ids, kwargs, or responses are read.
"""
from __future__ import annotations

import json
import re
import string

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as v3

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_V3_PARTIAL_PARSE_FALSIFICATION_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_IFBENCH_INSTRUCTIONS_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
SUBJECT_V3_BLOB = "ff977b2e34d551e5a2751852bb77d23c7c503647"

PALINDROME_DESCRIPTION = (
    "Include at least 10 single-word palindromes, each at least 5 characters long."
)
PROMPT = (
    "Use at least 5 unique words in the response. "
    + PALINDROME_DESCRIPTION
)

REQUEST = {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "public-synthetic-partial-parse-counterexample",
    "task_payload": {"instruction": PROMPT},
    "allowed_tools": [],
}


def frozen_palindrome_checker(value: str) -> tuple[bool, list[str]]:
    # Exact semantics of the frozen public PalindromeChecker.check_following:
    # punctuation removal, lowercase whitespace tokenization, >=10 palindromes
    # each length >=5.
    stripped = str(value).translate(str.maketrans("", "", string.punctuation))
    words = stripped.lower().split()
    palindromes = [word for word in words if word == word[::-1] and len(word) >= 5]
    return len(palindromes) >= 10, palindromes


def unique_word_floor_pass(value: str) -> bool:
    words = re.findall(r"\b\w+\b", str(value), flags=re.UNICODE)
    return len({w.lower() for w in words}) >= 5


def reproduce() -> dict:
    out = v3.infer(REQUEST)
    answer = str(out.get("answer") or "")
    palindrome_pass, palindromes = frozen_palindrome_checker(answer)

    # The counterexample is load-bearing only if V3 actually claims its
    # model-independent structural route, the recognized subset passes, and
    # the simultaneously present public registered constraint fails.
    assert out.get("status") == "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE", out
    assert out.get("response_route") == "LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3", out
    assert unique_word_floor_pass(answer), answer
    assert not palindrome_pass, (answer, palindromes)

    return {
        "schema": SCHEMA,
        "status": "PASS__COUNTEREXAMPLE_REPRODUCED",
        "subject_v3_git_blob_sha": SUBJECT_V3_BLOB,
        "frozen_public_livebench_commit": FROZEN_LIVEBENCH_COMMIT,
        "frozen_public_ifbench_instructions_git_blob_sha": FROZEN_IFBENCH_INSTRUCTIONS_BLOB,
        "synthetic_prompt": PROMPT,
        "v3_status": out.get("status"),
        "v3_response_route": out.get("response_route"),
        "v3_answer": answer,
        "recognized_unique_word_floor_pass": True,
        "public_palindrome_checker_pass": False,
        "public_palindromes_found": palindromes,
        "public_palindromes_required": 10,
        "terminal_cases_used": 0,
        "incremental_spend_usd": 0,
        "deduction": (
            "VALIDATION_AGAINST_ONLY_THE_COMPILER_RECOVERED_SUBSET_DOES_NOT_PROVE_"
            "ALL_REGISTERED_PUBLIC_IFBENCH_CONSTRAINTS_IN_THE_SAME_PROMPT"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(reproduce(), indent=2, sort_keys=True, ensure_ascii=False))
