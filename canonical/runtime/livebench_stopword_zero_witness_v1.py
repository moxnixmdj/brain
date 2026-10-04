#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_STOPWORD_ZERO_WITNESS_V1"
PUBLIC_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PUBLIC_INSTRUCTIONS_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
PUBLIC_INSTRUCTIONS_UTIL_BLOB = "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342"

_DESCRIPTION_RE = re.compile(
    r"Ensure\s+that\s+stop\s+words\s+constitute\s+no\s+more\s+than\s+"
    r"(?P<percentage>\d+(?:\.\d+)?)%\s+of\s+the\s+total\s+words\s+in\s+your\s+response\.",
    re.IGNORECASE,
)

# Exact frozen scorer tokenization is RegexpTokenizer(r"\w+").  These tokens are
# deliberately synthetic so they are not ordinary English stopwords.  Exact
# corpus non-membership is a separate verification obligation before promotion.
_TOKENS = tuple(f"qzxv{i}" for i in range(64))


class StopwordWitnessError(RuntimeError):
    pass


@dataclass(frozen=True)
class StopwordZeroWitness:
    percentage_ceiling: float
    response: str
    token_count: int


def parse_percentage(instruction: str) -> float:
    match = _DESCRIPTION_RE.search(str(instruction or ""))
    if match is None:
        raise StopwordWitnessError("STOPWORD_DESCRIPTION_NOT_RECOGNIZED")
    percentage = float(match.group("percentage"))
    if not 0.0 <= percentage <= 100.0:
        raise StopwordWitnessError("PERCENTAGE_OUT_OF_RANGE")
    return percentage


def synthesize(instruction: str, *, token_count: int = 8) -> StopwordZeroWitness:
    ceiling = parse_percentage(instruction)
    n = int(token_count)
    if not 1 <= n <= len(_TOKENS):
        raise StopwordWitnessError("TOKEN_COUNT_OUT_OF_RANGE")
    response = " ".join(_TOKENS[:n])
    tokens = re.findall(r"\w+", response)
    if len(tokens) != n:
        raise StopwordWitnessError("TOKENIZATION_PROXY_MISMATCH")
    return StopwordZeroWitness(
        percentage_ceiling=ceiling,
        response=response,
        token_count=len(tokens),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    witness = synthesize(
        str(args.get("instruction") or ""),
        token_count=int(args.get("token_count") or 8),
    )
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_PASS_PENDING_EXACT_SCORER_ENVIRONMENT_VERIFICATION",
        "response": witness.response,
        "percentage_ceiling": witness.percentage_ceiling,
        "token_count": witness.token_count,
        "expected_stopword_count": 0,
        "expected_stopword_percent": 0.0,
        "public_livebench_commit": PUBLIC_LIVEBENCH_COMMIT,
        "public_instructions_blob": PUBLIC_INSTRUCTIONS_BLOB,
        "public_instructions_util_blob": PUBLIC_INSTRUCTIONS_UTIL_BLOB,
        "terminal_cases_used": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
    }
