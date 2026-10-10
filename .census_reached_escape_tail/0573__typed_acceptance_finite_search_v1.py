"""Finite complete proposal search for typed declarative acceptance programs.

Given explicit finite domains for every candidate field, exhaustively enumerate the
Cartesian product and evaluate each candidate with the same typed acceptance
program used by the verifier.

Completeness is ONLY over the declared finite domains. The generator has no
authority and its selected proposal must still be independently re-verified by the
Universal Verified Adaptive Solver.
"""
from __future__ import annotations

from itertools import product
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.typed_acceptance_program_v1 import verify

SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_FINITE_SEARCH_V1"
MAX_CANDIDATES_HARD = 100_000


class FiniteProposalSearchError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def search(
    program: Mapping[str, Any],
    *,
    trusted_values: Mapping[str, Any],
    candidate_domains: Mapping[str, Sequence[Any]],
    max_candidates: int = MAX_CANDIDATES_HARD,
) -> dict[str, Any]:
    try:
        if not isinstance(program, Mapping):
            raise FiniteProposalSearchError("PROGRAM_NOT_OBJECT")
        if not isinstance(trusted_values, Mapping):
            raise FiniteProposalSearchError("TRUSTED_VALUES_NOT_OBJECT")
        if not isinstance(candidate_domains, Mapping) or not candidate_domains:
            raise FiniteProposalSearchError("CANDIDATE_DOMAINS_INVALID")
        if (
            not isinstance(max_candidates, int)
            or isinstance(max_candidates, bool)
            or max_candidates < 1
            or max_candidates > MAX_CANDIDATES_HARD
        ):
            raise FiniteProposalSearchError("MAX_CANDIDATES_INVALID")

        fields = program.get("fields")
        if not isinstance(fields, list):
            raise FiniteProposalSearchError("PROGRAM_FIELDS_INVALID")
        candidate_ids = sorted(
            str(row.get("id"))
            for row in fields
            if isinstance(row, Mapping) and row.get("source") == "candidate"
        )
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise FiniteProposalSearchError("PROGRAM_CANDIDATE_FIELDS_INVALID")
        if set(candidate_domains) != set(candidate_ids):
            raise FiniteProposalSearchError("CANDIDATE_DOMAIN_FIELD_SET_MISMATCH")

        domains: list[list[Any]] = []
        total = 1
        for fid in candidate_ids:
            raw = candidate_domains[fid]
            if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
                raise FiniteProposalSearchError("CANDIDATE_DOMAIN_INVALID:" + fid)
            values = list(raw)
            canon = [_canon(v) for v in values]
            if len(canon) != len(set(canon)):
                raise FiniteProposalSearchError("CANDIDATE_DOMAIN_DUPLICATE:" + fid)
            values = [v for _, v in sorted(zip(canon, values), key=lambda x: x[0])]
            total *= len(values)
            if total > max_candidates:
                return {
                    "schema": SCHEMA,
                    "status": "BOUND_EXCEEDED",
                    "pass": False,
                    "declared_candidate_count": total,
                    "max_candidates": max_candidates,
                    "complete_over_declared_domains": False,
                    "proposal_authority": False,
                    "terminal_authority": False,
                }
            domains.append(values)

        passing: list[dict[str, Any]] = []
        examined = 0
        for values in product(*domains):
            candidate = dict(zip(candidate_ids, values))
            verdict = verify(
                program,
                trusted_values=trusted_values,
                candidate_values=candidate,
            )
            examined += 1
            if verdict.get("status") == "FAIL_CLOSED":
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "pass": False,
                    "reason": "DECLARED_DOMAIN_CONTAINS_INVALID_TYPED_CANDIDATE",
                    "invalid_candidate": candidate,
                    "verdict": verdict,
                    "examined": examined,
                    "complete_over_declared_domains": False,
                    "proposal_authority": False,
                    "terminal_authority": False,
                }
            if verdict.get("pass") is True:
                passing.append(candidate)

        passing.sort(key=_canon)
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__ACCEPTED_CANDIDATES_FOUND"
                if passing
                else "NO_ACCEPTED_CANDIDATE_IN_DECLARED_DOMAINS"
            ),
            "pass": bool(passing),
            "declared_candidate_count": total,
            "examined": examined,
            "passing_count": len(passing),
            "selected_candidate": passing[0] if passing else None,
            "passing_candidates": passing,
            "complete_over_declared_domains": True,
            "proposal_authority": False,
            "terminal_authority": False,
            "scope_boundary": (
                "EXHAUSTIVE_ONLY_OVER_EXPLICIT_FINITE_CANDIDATE_DOMAINS;"
                "NO_CLAIM_THE_REAL_SOLUTION_LIES_IN_THOSE_DOMAINS"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "proposal_authority": False,
            "terminal_authority": False,
        }
