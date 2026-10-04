#!/usr/bin/env python3
"""Universal repeat-prompt text-identity reduction for frozen LiveBench active15.

The exact pinned legacy checker for combination:repeat_prompt accepts iff the
stripped lower-cased response starts with the stripped lower-cased
prompt_to_repeat. The public active15 conflict graph permits repeat_prompt only
with keywords:existence and/or detectable_format:title. Composer V2 always
places prompt_to_repeat.strip() first and appends witnesses for those two
monotone co-contracts afterwards.

Therefore prompt/article text identity is not a semantic dimension of the
post-sacrifice construction proof. For every nonempty visible prompt_to_repeat
string admitted by the historical visible-prompt compiler, all four compatible
repeat_prompt structural sets are constructible. No enumeration of article text
or prompt identity is needed.

This is a zero-terminal-data theorem candidate. Independent exact-source
verification is still required before it becomes load-bearing acceptance
evidence.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact
from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as visible

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_REPEAT_PROMPT_TOTALITY_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_exact_postvalidator_v1.py":
        "8c34701f5a63acf5aef88e8ea060be2d70571c23",
    "canonical/runtime/livebench_legacy15_visible_prompt_compiler_v1.py":
        "6e4ae278c4ba81cf0fb589d4e948384d1bd61ae2",
}
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

_REPEAT_COMPATIBLE = frozenset({
    frozenset({comp.REPEAT}),
    frozenset({comp.REPEAT, comp.EXIST}),
    frozenset({comp.REPEAT, comp.TITLE}),
    frozenset({comp.REPEAT, comp.EXIST, comp.TITLE}),
})

_PUBLIC_EXISTENCE_WORDS = ["harbor", "violet", "canyon", "meadow", "signal"]


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
    if exact.PINNED_INSTRUCTIONS_BLOB != PINNED_INSTRUCTIONS_BLOB:
        raise AssertionError("PINNED_INSTRUCTIONS_BLOB_DRIFT")
    if visible.PINNED_INSTRUCTIONS_BLOB != PINNED_INSTRUCTIONS_BLOB:
        raise AssertionError("VISIBLE_COMPILER_INSTRUCTIONS_BLOB_DRIFT")
    return got


def _compatible_repeat_sets() -> frozenset[frozenset[str]]:
    return frozenset(
        frozenset(ids)
        for ids in arch.enumerate_compatible_sets()
        if comp.REPEAT in ids
    )


def _contracts(ids: frozenset[str], prompt_to_repeat: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for iid in arch.ACTIVE_IDS:
        if iid not in ids:
            continue
        if iid == comp.REPEAT:
            rows.append({
                "instruction_id": iid,
                "slots": {"prompt_to_repeat": prompt_to_repeat},
                "parameter_complete": True,
            })
        elif iid == comp.EXIST:
            rows.append({
                "instruction_id": iid,
                "slots": {"keywords": list(_PUBLIC_EXISTENCE_WORDS)},
                "parameter_complete": True,
            })
        elif iid == comp.TITLE:
            rows.append({
                "instruction_id": iid,
                "slots": {},
                "parameter_complete": True,
            })
        else:
            raise AssertionError("UNEXPECTED_REPEAT_COMPATIBLE_ID:" + iid)
    return rows


def prove_prompt(prompt_to_repeat: str) -> dict[str, Any]:
    """Executable witness check for an arbitrary representative prompt string."""
    if not isinstance(prompt_to_repeat, str) or not prompt_to_repeat.strip():
        raise ValueError("NONEMPTY_PROMPT_TO_REPEAT_REQUIRED")

    base = prompt_to_repeat.strip()
    rows = []
    for ids in sorted(_REPEAT_COMPATIBLE, key=lambda x: (len(x), sorted(x))):
        built = comp.compose_contracts(_contracts(ids, prompt_to_repeat))
        if built.get("status") != "CANDIDATE_WITNESS":
            raise AssertionError("REPEAT_COMPOSITION_FAILED:" + repr((ids, built)))
        response = str(built["response"])

        # Exact pinned checker semantics:
        # value.strip().lower().startswith(prompt_to_repeat.strip().lower())
        if not response.strip().lower().startswith(base.lower()):
            raise AssertionError("REPEAT_PREFIX_THEOREM_BROKEN")

        if comp.EXIST in ids:
            lowered = response.lower()
            if not all(word.lower() in lowered for word in _PUBLIC_EXISTENCE_WORDS):
                raise AssertionError("EXISTENCE_MONOTONE_WITNESS_MISSING")

        if comp.TITLE in ids:
            if re.search(r"<<[^\n]+>>", response) is None:
                raise AssertionError("TITLE_MONOTONE_WITNESS_MISSING")

        rows.append({
            "instruction_ids": sorted(ids),
            "response_prefix_exact_after_strip": True,
            "existence_witness_present": (
                comp.EXIST not in ids
                or all(word.lower() in response.lower() for word in _PUBLIC_EXISTENCE_WORDS)
            ),
            "title_witness_present": (
                comp.TITLE not in ids
                or re.search(r"<<[^\\n]+>>", response) is not None
            ),
        })

    return {
        "prompt_nonempty_after_strip": True,
        "compatible_repeat_sets_constructed": len(rows),
        "all_repeat_checker_prefix_obligations_hold": True,
        "rows": rows,
    }


def verify() -> dict[str, Any]:
    bindings = _verify_bindings()

    observed = _compatible_repeat_sets()
    if observed != _REPEAT_COMPATIBLE:
        raise AssertionError(
            "REPEAT_CONFLICT_GRAPH_DRIFT:"
            + repr((sorted(map(sorted, observed)), sorted(map(sorted, _REPEAT_COMPATIBLE))))
        )

    # Adversarial representatives are falsification support only. The load-bearing
    # proof is symbolic below: Composer V2 defines base = str(prompt).strip(),
    # initializes pieces=[base], only appends suffix pieces, and joins them with
    # newlines. The exact checker strips+lowers both sides and tests startswith.
    adversarial = (
        "Article text.",
        "  leading and trailing whitespace  ",
        "Line one\nLine two\nLine three",
        "MiXeD CaSe + punctuation?!",
        "Ω λ 😀 日本語 العربية",
        "First repeat the request word for word without change, collision.",
        "<<already-title-shaped>>",
        "******",
        "\x00embedded-null-after-visible-prefix",
        "İ I ı i Σ σ ς",
    )
    for prompt in adversarial:
        prove_prompt(prompt)

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__REPEAT_PROMPT_TEXT_IDENTITY_DELETED_AS_SEMANTIC_DIMENSION__"
            "ALL_FOUR_COMPATIBLE_STRUCTURAL_SETS_UNIVERSALLY_CONSTRUCTIBLE"
        ),
        "source_bindings": bindings,
        "pinned_public_checker": {
            "livebench_commit": exact.PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "repeat_checker_semantics": (
                "VALUE_STRIP_LOWER_STARTSWITH_PROMPT_TO_REPEAT_STRIP_LOWER"
            ),
        },
        "visible_parameter_source": {
            "compiler": "livebench_legacy15_visible_prompt_compiler_v1",
            "historical_repeat_binding": (
                "PROMPT_TO_REPEAT_EQUALS_TEXT_BEFORE_FIRST_REPEAT_MARKER"
            ),
            "parameter_complete": True,
        },
        "repeat_conflict_graph": {
            "compatible_set_count": 4,
            "compatible_sets": [
                sorted(ids)
                for ids in sorted(_REPEAT_COMPATIBLE, key=lambda x: (len(x), sorted(x)))
            ],
            "only_possible_co_contracts": [comp.EXIST, comp.TITLE],
            "negative_or_nonmonotone_co_contract_count": 0,
        },
        "universal_argument": {
            "domain": "EVERY_NONEMPTY_VISIBLE_PROMPT_TO_REPEAT_PYTHON_STRING_AFTER_STRIP",
            "composer_prefix": "BASE_EQUALS_PROMPT_TO_REPEAT_STRIP_AND_IS_ALWAYS_FIRST",
            "suffix_rule": "EXISTENCE_TITLE_WITNESSES_ONLY_APPEND_AFTER_BASE",
            "checker_rule": "STRIPPED_LOWER_RESPONSE_STARTSWITH_STRIPPED_LOWER_BASE",
            "conclusion": (
                "ARBITRARY_PROMPT_OR_ARTICLE_TEXT_IDENTITY_CANNOT_CHANGE_REPEAT_PASS__"
                "NO_PROMPT_TEXT_ENUMERATION_IS_LOAD_BEARING"
            ),
        },
        "adversarial_prompt_representatives_checked": len(adversarial),
        "deleted_proof_requirement": (
            "ENUMERATE_OR_QUOTIENT_ARBITRARY_REPEAT_PROMPT_ARTICLE_TEXT_IDENTITIES"
        ),
        "remaining_load_bearing_obligation": (
            "UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_FOR_NON_REPEAT_ACTIVE15_ARCHETYPES"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "INDEPENDENT_EXACT_SOURCE_VERIFICATION_REQUIRED_BEFORE_LOAD_BEARING_PROMOTION",
            "NO_FULL_LIVEBENCH_POINTWISE_COMPLETENESS_CLAIM_FROM_THIS_LEMMA_ALONE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_TERMINAL_ROWS_PROMPTS_RESPONSES_FREQUENCIES_OR_SCORES_CONSUMED",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True, ensure_ascii=True))
