from __future__ import annotations

import math

from canonical.runtime.h100_oracle_free_role_family_v1 import discover


def rows(xs, fn):
    return [{"opaque_a": float(x), "opaque_b": float(fn(float(x)))} for x in xs]


XS = [-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]


def test_exp_abs_role_and_family_are_discovered_without_labels():
    data = rows(XS, lambda x: 0.7 * math.exp(0.47 * abs(x)))
    out = discover(data)
    assert out["status"] == "UNIQUE_ROLE_AND_FAMILY_IDENTIFIED"
    assert out["selected"]["input_column"] == "opaque_a"
    assert out["selected"]["target_column"] == "opaque_b"
    assert out["selected"]["family"] == "exp_abs"
    assert out["semantic_side_information"] == {
        "target_column_supplied": False,
        "input_column_supplied": False,
        "family_supplied": False,
        "ontology_label_supplied": False,
    }


def test_threshold_role_and_family_are_discovered_without_labels():
    data = rows(XS, lambda x: -0.2 + 0.9 * (1.0 if x >= 0.8 else -1.0))
    out = discover(data)
    assert out["status"] == "UNIQUE_ROLE_AND_FAMILY_IDENTIFIED"
    assert out["selected"]["input_column"] == "opaque_a"
    assert out["selected"]["target_column"] == "opaque_b"
    assert out["selected"]["family"] == "threshold_step"


def test_sinusoid_role_and_family_are_discovered_without_labels():
    data = rows(XS, lambda x: -0.7 + 0.25*x + 0.8*math.sin(2.41*x - 0.6))
    out = discover(data)
    assert out["status"] == "UNIQUE_ROLE_AND_FAMILY_IDENTIFIED"
    assert out["selected"]["input_column"] == "opaque_a"
    assert out["selected"]["target_column"] == "opaque_b"
    assert out["selected"]["family"] == "linear_trend_sinusoid"


def test_bidirectionally_exact_linear_relation_abstains():
    data = rows(XS, lambda x: 2.0*x + 1.0)
    out = discover(data)
    assert out["status"] == "ABSTAIN__ROLE_ORIENTATION_NONIDENTIFIABLE"
    assert out["exact_directed_hypothesis_count"] == 2
    assert out["selected"] is None


def test_column_names_do_not_carry_semantics():
    data = [{"zz9": r["opaque_b"], "q17": r["opaque_a"]} for r in rows(
        XS, lambda x: 0.7 * math.exp(0.47 * abs(x))
    )]
    out = discover(data)
    assert out["status"] == "UNIQUE_ROLE_AND_FAMILY_IDENTIFIED"
    assert out["selected"]["input_column"] == "q17"
    assert out["selected"]["target_column"] == "zz9"
    assert out["selected"]["family"] == "exp_abs"
