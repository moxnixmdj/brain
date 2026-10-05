#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from canonical.runtime.hidden_evaluator_target_free_characterization_v1 import (
    characterize_target_free_monotone_dominance,
)

ROOT = Path(__file__).resolve().parents[2]

GOVERNANCE = "canonical/governance/HIDDEN_EVALUATOR_TARGET_FREE_MONOTONE_DOMINANCE_CHARACTERIZATION_V1.json"
RUNTIME = "canonical/runtime/hidden_evaluator_target_free_characterization_v1.py"
AUTHOR_TESTS = "canonical/tests/test_hidden_evaluator_target_free_characterization_v1.py"
WOLFRAM = "canonical/verification/HIDDEN_EVALUATOR_TARGET_FREE_MONOTONE_DOMINANCE_WOLFRAM_VERIFICATION_20261005_V1.json"

EXPECTED_BLOBS = {
    GOVERNANCE: "a4175910f1a1d88f683b25cecc94d6252002f9d1",
    RUNTIME: "78cd1f82a174de8ffe178d25137f2df5f244a4ed",
    AUTHOR_TESTS: "92164bda42531db133102f1ed910d2df4ec9bf05",
    WOLFRAM: "ac5911a29eb50cf89b7fb7a409b2d20b1383600b",
}

EXPECTED_COUNTS = {
    1: (1, 1),
    2: (3, 9),
    3: (19, 133),
    4: (219, 3285),
}


def git_blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def labeled_partial_orders(n: int):
    elems = tuple(range(n))
    off_diag = tuple((a, b) for a in elems for b in elems if a != b)
    for bits in itertools.product((0, 1), repeat=len(off_diag)):
        relation = {(a, a) for a in elems}
        relation.update(edge for edge, present in zip(off_diag, bits) if present)

        if any(
            a != b and (a, b) in relation and (b, a) in relation
            for a in elems
            for b in elems
        ):
            continue

        transitive = True
        for a, b in relation:
            for c, d in relation:
                if b == c and (a, d) not in relation:
                    transitive = False
                    break
            if not transitive:
                break
        if transitive:
            yield relation


def support_sets(n: int):
    for mask in range(1, 1 << n):
        yield {i for i in range(n) if mask & (1 << i)}


def independent_oracle(relation: set[tuple[int, int]], support: set[int], n: int):
    elems = tuple(range(n))
    greatest = [g for g in elems if all((g, y) in relation for y in elems)]

    # Necessity is checked only through monotone upper-set indicators:
    # for every y, Q(Up(y))=1 iff every positive-mass support point dominates y.
    upper_set_condition = all(
        all((b, y) in relation for b in support)
        for y in elems
    )
    greatest_singleton_condition = (
        len(greatest) == 1 and support == {greatest[0]}
    )
    assert upper_set_condition == greatest_singleton_condition

    witness_y = None
    if not greatest_singleton_condition:
        for y in elems:
            if any((b, y) not in relation for b in support):
                witness_y = y
                break
        assert witness_y is not None

    return greatest, greatest_singleton_condition, witness_y


def main() -> int:
    for path, expected in EXPECTED_BLOBS.items():
        actual = git_blob_sha(path)
        assert actual == expected, (path, actual, expected)

    governance = load(GOVERNANCE)
    wolfram = load(WOLFRAM)

    theorem = governance["theorem"]
    assert theorem["id"] == "TARGET_FREE_UNIVERSAL_MONOTONE_DOMINANCE_IFF_UNIQUE_GREATEST_SUPPORT"
    defs = theorem["definitions"]
    assert "FINITE_SCOPE_COMPLETE" in defs["Y"]
    assert "PARTIAL_ORDER" in defs["GE"]
    assert "ALL_BOUNDED_REAL_VALUED_UTILITIES_MONOTONE" in defs["U_MONO"]

    nonclaims = set(governance["hard_nonclaims"])
    assert "NO_CLAIM_ANY_ROOT3_PREDICATE_IS_CLOSED_NOW" in nonclaims
    assert "NO_CLAIM_FINITE_OUTCOME_ABSTRACTION_IS_SCOPE_COMPLETE_UNLESS_SEPARATELY_PROVED" in nonclaims
    assert governance["acceptance_credit_delta"] == 0
    assert governance["family_credit_delta"] == 0
    assert governance["capability_credit_delta"] == 0
    assert governance["ownership_credit_delta"] == 0
    assert governance["execution_authority"] is False
    assert governance["promotion_authority"] is False
    assert governance["fresh_reality_authority"] is False

    detail = []
    total_posets = 0
    total_supports = 0

    for n in range(1, 5):
        poset_count = 0
        support_count = 0
        names = [f"Y{i}" for i in range(n)]

        for relation in labeled_partial_orders(n):
            poset_count += 1
            strict_edges = [
                [names[a], names[b]]
                for a, b in sorted(relation)
                if a != b
            ]

            for support in support_sets(n):
                support_count += 1
                greatest, expected_universal, witness_y = independent_oracle(
                    relation, support, n
                )

                cert = {
                    "outcomes": names,
                    "dominance_edges": strict_edges,
                    "brain_support": [names[i] for i in sorted(support)],
                }
                verdict = characterize_target_free_monotone_dominance(cert)
                assert verdict["status"] == "PASS", (n, relation, support, verdict)
                assert verdict["target_free_universal_monotone_dominance"] is expected_universal

                expected_greatest = names[greatest[0]] if greatest else None
                assert verdict["greatest_element"] == expected_greatest

                if expected_universal:
                    assert verdict["counterexample"] is None
                    assert verdict["target_distribution_or_additional_evaluator_information_required"] is False
                else:
                    cex = verdict["counterexample"]
                    assert cex is not None
                    y = int(cex["target_distribution"].split("Y", 1)[1])
                    assert y == witness_y
                    expected_upper = [
                        names[z] for z in range(n) if (z, y) in relation
                    ]
                    expected_bad = [
                        names[b] for b in sorted(support) if (b, y) not in relation
                    ]
                    assert cex["upper_set"] == expected_upper
                    assert cex["brain_support_outside_upper_set"] == expected_bad
                    assert expected_bad
                    assert verdict["target_distribution_or_additional_evaluator_information_required"] is True

        assert (poset_count, support_count) == EXPECTED_COUNTS[n]
        total_posets += poset_count
        total_supports += support_count
        detail.append(
            {
                "n": n,
                "labeled_posets": poset_count,
                "support_tests": support_count,
                "mismatches": 0,
            }
        )

    assert total_posets == 242
    assert total_supports == 3428

    receipt = wolfram["wolfram_exhaustive_enumeration"]
    assert receipt["total_labeled_posets"] == total_posets
    assert receipt["total_support_tests"] == total_supports
    assert receipt["total_mismatches"] == 0
    assert receipt["results"] == detail
    assert wolfram["independent_terminal_verification"] is False
    assert wolfram["promotion_authority"] is False

    print("INDEPENDENT_TARGET_FREE_MONOTONE_CHARACTERIZATION_PASS")
    print(json.dumps({"labeled_posets": total_posets, "support_tests": total_supports, "mismatches": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
