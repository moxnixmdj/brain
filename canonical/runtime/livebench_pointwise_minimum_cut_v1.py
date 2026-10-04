#!/usr/bin/env python3
"""Exact minimum-cut proof for LiveBench active-15 pointwise optimality.

This module removes the false requirement to prove the full raw slot Cartesian
product before reasoning about the *maximum achievable strict score*.

For the exact frozen Brain blobs bound below, every mandatory pointwise loss is
controlled by only two independent loss coordinates:

1. sentence_zero:
   number_sentences is active with relation="less than", threshold=1.
   Under strict nonempty evaluation that checker is intrinsically impossible,
   therefore the unique minimum sacrifice is NUMBER_SENTENCES.

2. forbidden_collision:
   FORBIDDEN is active and either the nth-paragraph first word is forbidden or
   the mandatory end phrase contains a forbidden public word. All such lexical
   contradictions share the same FORBIDDEN checker, so one minimum sacrifice
   removes the whole collision cluster.

Everything else can affect witness construction, but it cannot create another
mandatory-loss coordinate in the frozen feasibility/planner theorem. Therefore
pointwise maximum-score *classification* does not require the full slot
Cartesian product. The remaining load-bearing obligation is strictly narrower:
prove universal construction of the reduced (post-sacrifice) contract set.

No terminal row, hidden kwargs, terminal frequency, comparator response, or
target score is consumed here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feas

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_POINTWISE_MINIMUM_CUT_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "09a5d7810fd46713aaf06cf1d204fe140d1d8045",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
}

_SENTENCE_ZERO = "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE"
_NTH_FORBIDDEN = "NTH_FIRST_WORD_IS_FORBIDDEN_WORD"
_END_FORBIDDEN_PREFIX = "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:"


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings() -> dict[str, str]:
    root = _root()
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _contract(iid: str, **slots: Any) -> dict[str, Any]:
    return {"instruction_id": iid, "slots": slots}


def _skeleton(
    ids: Iterable[str],
    sig: lex.LexicalSignature,
    *,
    sentence_zero: bool,
) -> list[dict[str, Any]]:
    lexical = lex.representative_slots(sig)
    out: list[dict[str, Any]] = []
    for iid in ids:
        if iid == comp.EXIST:
            out.append(_contract(iid, **lexical[comp.EXIST]))
        elif iid == comp.FORBIDDEN:
            out.append(_contract(iid, **lexical[comp.FORBIDDEN]))
        elif iid == comp.PARAGRAPHS:
            out.append(_contract(iid, num_paragraphs=3))
        elif iid == comp.WORDS:
            out.append(_contract(iid, num_words=100, relation="less than"))
        elif iid == comp.SENTENCES:
            out.append(_contract(
                iid,
                num_sentences=1 if sentence_zero else 2,
                relation="less than",
            ))
        elif iid == comp.NTH:
            out.append(_contract(
                iid,
                num_paragraphs=3,
                nth_paragraph=2,
                **lexical[comp.NTH],
            ))
        elif iid == comp.POSTSCRIPT:
            out.append(_contract(iid, postscript_marker="P.P.S"))
        elif iid == comp.BULLETS:
            out.append(_contract(iid, num_bullets=3))
        elif iid == comp.TITLE:
            out.append(_contract(iid))
        elif iid == comp.SECTIONS:
            out.append(_contract(iid, section_spliter="Section", num_sections=3))
        elif iid == comp.JSON_ID:
            out.append(_contract(iid))
        elif iid == comp.REPEAT:
            out.append(_contract(iid, prompt_to_repeat="Public visible request."))
        elif iid == comp.TWO:
            out.append(_contract(iid))
        elif iid == comp.END:
            out.append(_contract(iid, **lexical[comp.END]))
        elif iid == comp.QUOTE:
            out.append(_contract(iid))
        else:
            raise AssertionError("UNKNOWN_ACTIVE_ID:" + iid)
    return out


def _expected_forbidden_collision(
    ids: set[str],
    sig: lex.LexicalSignature,
) -> bool:
    if comp.FORBIDDEN not in ids:
        return False
    nth = comp.NTH in ids and bool(sig.nth_in_forbidden)
    end = comp.END in ids and any(
        r.startswith(_END_FORBIDDEN_PREFIX)
        for r in lex.predicted_hard_collisions(sig)
    )
    return bool(nth or end)


def _expected_sacrifices(
    ids: set[str],
    sig: lex.LexicalSignature,
    *,
    sentence_zero: bool,
) -> tuple[str, ...]:
    dropped: list[str] = []
    if comp.SENTENCES in ids and sentence_zero:
        dropped.append(comp.SENTENCES)
    if _expected_forbidden_collision(ids, sig):
        dropped.append(comp.FORBIDDEN)
    return tuple(sorted(dropped))


def verify() -> dict[str, Any]:
    bindings = _verify_bindings()
    a = arch.verify()
    l = lex.verify()
    if a["compatible_set_count"] != 928:
        raise AssertionError("STRUCTURAL_QUOTIENT_DRIFT")
    if l["exact_reachable_signature_count"] != 192:
        raise AssertionError("LEXICAL_QUOTIENT_DRIFT")

    cases = 0
    loss_histogram: dict[int, int] = {0: 0, 1: 0, 2: 0}
    score_states: set[tuple[int, int, int, int]] = set()

    for ids_tuple in arch.enumerate_compatible_sets():
        ids = set(ids_tuple)
        for sig in lex.enumerate_signatures():
            for sentence_zero in (False, True):
                contracts = _skeleton(
                    ids_tuple,
                    sig,
                    sentence_zero=sentence_zero,
                )
                reasons = tuple(feas.hard_unsat_reasons(contracts))
                sacrificed = tuple(opt._sacrifice_ids(reasons))
                expected = _expected_sacrifices(
                    ids,
                    sig,
                    sentence_zero=sentence_zero,
                )
                if sacrificed != expected:
                    raise AssertionError(
                        "LOSS_CLASSIFICATION_MISMATCH:"
                        + repr((ids_tuple, sig, sentence_zero, reasons, sacrificed, expected))
                    )

                # Frozen theorem: no mandatory loss outside the two coordinates.
                if not set(sacrificed) <= {comp.SENTENCES, comp.FORBIDDEN}:
                    raise AssertionError("UNEXPECTED_SACRIFICE_ID")
                if len(sacrificed) > 2:
                    raise AssertionError("LOSS_DIMENSION_EXCEEDS_TWO")

                sentence_reason = _SENTENCE_ZERO in reasons
                if sentence_reason != (comp.SENTENCES in ids and sentence_zero):
                    raise AssertionError("SENTENCE_ZERO_CLASS_DRIFT")

                unknown = [
                    r for r in reasons
                    if r != _SENTENCE_ZERO
                    and r != _NTH_FORBIDDEN
                    and not str(r).startswith(_END_FORBIDDEN_PREFIX)
                ]
                if unknown:
                    raise AssertionError("UNKNOWN_MANDATORY_LOSS_REASON:" + repr(unknown))

                k = len(ids_tuple)
                passed = k - len(sacrificed)
                score = opt.strict_score_from_pass_count(k, passed)
                # Exact rational encoding avoids treating float identity as proof.
                if passed == k:
                    num, den = 1, 1
                else:
                    num, den = passed, 2 * k
                if abs(score - (num / den)) > 1e-15:
                    raise AssertionError("STRICT_SCORE_FORMULA_DRIFT")

                score_states.add((k, len(sacrificed), num, den))
                loss_histogram[len(sacrificed)] += 1
                cases += 1

    expected_cases = 928 * 192 * 2
    if cases != expected_cases:
        raise AssertionError("MINIMUM_CUT_CASE_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXACT_STRUCTURAL_X_LEXICAL_X_SENTENCE_PARTITION__"
            "ONLY_TWO_MANDATORY_LOSS_COORDINATES"
        ),
        "source_bindings": bindings,
        "structural_id_sets": 928,
        "reachable_lexical_signatures": 192,
        "sentence_partition_states": 2,
        "exact_classification_cases": cases,
        "mandatory_loss_coordinates": [
            {
                "coordinate": "sentence_zero",
                "minimum_sacrifice": comp.SENTENCES,
            },
            {
                "coordinate": "forbidden_collision_cluster",
                "minimum_sacrifice": comp.FORBIDDEN,
            },
        ],
        "maximum_mandatory_sacrifices_per_case": 2,
        "loss_histogram_over_classification_basis": loss_histogram,
        "reachable_strict_score_states": [
            {
                "instruction_count": k,
                "mandatory_loss_count": loss,
                "score_numerator": num,
                "score_denominator": den,
            }
            for k, loss, num, den in sorted(score_states)
        ],
        "deleted_proof_requirement": (
            "FULL_RAW_SLOT_CARTESIAN_PRODUCT_IS_NOT_REQUIRED_TO_CLASSIFY_THE_"
            "THEORETICAL_POINTWISE_MAXIMUM_PASS_COUNT"
        ),
        "remaining_load_bearing_obligation": (
            "UNIVERSALLY_PROVE_THE_COMPOSER_CONSTRUCTS_ALL_POST_SACRIFICE_"
            "GENERATOR_ADMITTED_CONTRACTS__NUMERIC_AND_VISIBLE_PROMPT_PARAMETERS_"
            "MAY_BE_PROVED_PARAMETRICALLY_INSTEAD_OF_CARTESIAN_ENUMERATION"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "THIS_DOES_NOT_YET_PROVE_UNIVERSAL_POST_SACRIFICE_CONSTRUCTION",
            "THIS_DOES_NOT_YET_BIND_LIVEBENCH_ACCEPTANCE",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_IS_GRANTED_BY_THIS_MODULE_ALONE",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
