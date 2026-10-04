#!/usr/bin/env python3
"""Parametric collapse of the frozen LiveBench active15 word upper-bound domain.

For every conflict-compatible active15 contract tuple containing
length_constraints:number_words, the special JSON / repeat / two-response
routes are registry-conflicted with the word checker, so the canonical GENERAL
composer is the only relevant route.

For relation "less than", public thresholds are 100..500. The GENERAL composer
does not add padding in this branch. We conservatively sum the maximum number of
\w+ tokens contributed by every mandatory scaffold component, deliberately
including components that cannot coexist because of registry conflicts and the
five-instruction cap. If that over-approximation is still <100, every public
less-than threshold is satisfied whenever the remaining semantic constraints
are satisfiable.

The proof uses the exact frozen LiveBench count_words implementation to measure
each atomic scaffold form and binds the exact canonical composer/archetype blobs.
No terminal rows or target scores are consumed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_WORD_UPPER_DOMAIN_COLLAPSE_V1"
EXPECTED_ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
EXPECTED_COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PUBLIC_WORD_THRESHOLD_MIN = 100
PUBLIC_WORD_THRESHOLD_MAX = 500
EXPECTED_CONSERVATIVE_BOUND = 63


class WordCollapseError(RuntimeError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _bind_subject() -> dict[str, str]:
    actual = {
        "archetypes": _git_blob_sha(Path(archetypes.__file__).resolve()),
        "composer": _git_blob_sha(Path(composer.__file__).resolve()),
    }
    expected = {
        "archetypes": EXPECTED_ARCH_BLOB,
        "composer": EXPECTED_COMPOSER_BLOB,
    }
    if actual != expected:
        raise WordCollapseError(
            "SUBJECT_BLOB_DRIFT:" + json.dumps(
                {"expected": expected, "actual": actual},
                sort_keys=True,
            )
        )
    return actual


def _load_exact_count_words(livebench_root: Path):
    head = (
        __import__("subprocess")
        .run(
            ["git", "-C", str(livebench_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )
    if head != LIVEBENCH_COMMIT:
        raise WordCollapseError("LIVEBENCH_COMMIT_DRIFT:" + head)

    util = (
        livebench_root
        / "livebench/if_runner/instruction_following_eval/instructions_util.py"
    )
    got = _git_blob_sha(util)
    if got != PINNED_UTIL_BLOB:
        raise WordCollapseError("PINNED_UTIL_BLOB_DRIFT:" + got)

    sys.path.insert(0, str(livebench_root / "livebench/if_runner"))
    from instruction_following_eval import instructions_util

    return instructions_util.count_words


def prove(livebench_root: str | Path) -> dict[str, Any]:
    subject = _bind_subject()
    exact_count = _load_exact_count_words(Path(livebench_root).resolve())

    # Every atomic form below is copied from the bound GENERAL constructor's
    # response grammar. We use exact frozen count_words, not a local surrogate.
    packed = composer._packed_required(["alpha", "beta", "gamma", "delta", "omega"])
    atoms = {
        # All five required ASCII-alpha words are packed into one contiguous
        # word-character carrier.
        "existence_packed_carrier": exact_count(packed),
        "title": exact_count("<<" + composer._SAFE + ">>"),
        # Maximum 5 sections, each contributing 9Section, numeric index, body.
        "sections_max5": 5 * exact_count(
            "9SECTION 5\n" + composer._SAFE + "5"
        ),
        "bullets_max5": 5 * exact_count("* " + composer._SAFE + "5"),
        # At-least sentence mode has the maximum lexical footprint, n<=20.
        "sentences_max20": 20 * exact_count(composer._SAFE + "20."),
        # NTH wrapper adds the forced first word plus at most four other
        # paragraph carrier words around an already-counted core.
        "nth_wrapper_max5": exact_count(
            "alpha " + " ".join(composer._SAFE + str(i) for i in range(1, 5))
        ),
        # STAR paragraph wrapper adds at most four carrier paragraphs.
        "star_paragraph_extra_max4": exact_count(
            " ".join(composer._SAFE + str(i) for i in range(2, 6))
        ),
        # Conservative fallback, although it cannot coexist with the other
        # content-producing branches that make parts nonempty.
        "fallback": exact_count(composer._SAFE),
        "postscript_max": max(
            exact_count("P.S.+"),
            exact_count("P.P.S"),
        ),
        "end_phrase_max": max(
            exact_count("Any other questions?"),
            exact_count("Is there anything else I can help with?"),
        ),
        "quotation_wrapper": 0,
    }

    # Also bind the canonical local counter to the exact frozen public counter
    # on every atomic form used in the arithmetic certificate.
    samples = [
        packed,
        "<<" + composer._SAFE + ">>",
        "9SECTION 5\n" + composer._SAFE + "5",
        "* " + composer._SAFE + "5",
        composer._SAFE + "20.",
        "alpha " + " ".join(composer._SAFE + str(i) for i in range(1, 5)),
        " ".join(composer._SAFE + str(i) for i in range(2, 6)),
        composer._SAFE,
        "P.S.+",
        "P.P.S",
        "Any other questions?",
        "Is there anything else I can help with?",
    ]
    for sample in samples:
        local = composer._word_count(sample)
        public = exact_count(sample)
        if local != public:
            raise WordCollapseError(
                "WORD_COUNTER_EQUIVALENCE_FAILURE:"
                + repr(sample)
                + f":local={local}:public={public}"
            )

    bound = sum(atoms.values())
    if bound != EXPECTED_CONSERVATIVE_BOUND:
        raise WordCollapseError(
            f"CONSERVATIVE_BOUND_DRIFT:{bound}!={EXPECTED_CONSERVATIVE_BOUND}"
        )
    if not bound < PUBLIC_WORD_THRESHOLD_MIN:
        raise WordCollapseError("WORD_UPPER_COLLAPSE_FAILED")

    sets = archetypes.enumerate_compatible_sets()
    word_sets = [
        ids for ids in sets
        if composer.WORDS in ids
    ]
    forbidden_special = {
        composer.JSON_ID,
        composer.REPEAT,
        composer.TWO,
    }
    special_violations = [
        list(ids) for ids in word_sets
        if set(ids) & forbidden_special
    ]
    if special_violations:
        raise WordCollapseError(
            "WORD_CHECKER_REACHES_SPECIAL_ROUTE:"
            + json.dumps(special_violations[:20])
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_PUBLIC_WORD_LESS_THAN_THRESHOLDS_COLLAPSE_PARAMETRICALLY",
        "subject_blobs": subject,
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_util_blob": PINNED_UTIL_BLOB,
        },
        "structural_id_sets_total": len(sets),
        "word_constraint_structural_id_sets": len(word_sets),
        "word_constraint_special_route_violations": 0,
        "public_word_threshold_domain": {
            "min": PUBLIC_WORD_THRESHOLD_MIN,
            "max": PUBLIC_WORD_THRESHOLD_MAX,
            "count": PUBLIC_WORD_THRESHOLD_MAX - PUBLIC_WORD_THRESHOLD_MIN + 1,
        },
        "exact_atomic_word_bounds": atoms,
        "conservative_mandatory_word_bound": bound,
        "proof_inequality": f"{bound} < {PUBLIC_WORD_THRESHOLD_MIN} <= N <= {PUBLIC_WORD_THRESHOLD_MAX}",
        "consequence": (
            "FOR_EVERY_GENERATOR_ADMITTED_ACTIVE15_GENERAL_CONTRACT_WITH_WORD_RELATION_"
            "LESS_THAN_THE_WORD_CHECKER_IS_NEVER_THE_CAUSE_OF_UNSAT_OR_POINTWISE_LOSS_"
            "ALL_401_PUBLIC_THRESHOLDS_FORM_ONE_SEMANTIC_PROOF_CLASS"
        ),
        "deliberate_overapproximation": [
            "NTH_AND_STAR_PARAGRAPH_TERMS_ARE_BOTH_COUNTED_DESPITE_CONFLICT",
            "FALLBACK_IS_COUNTED_ALONGSIDE_NONEMPTY_PARTS",
            "ALL_CONTENT_TERMS_ARE_SUMMED_WITHOUT_USING_THE_FIVE_INSTRUCTION_CAP"
        ],
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "capability_credit": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    result = prove(ns.livebench_root)
    Path(ns.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "bound": result["conservative_mandatory_word_bound"],
        "word_sets": result["word_constraint_structural_id_sets"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
