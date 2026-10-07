from fractions import Fraction
from canonical.runtime.stochastic_kernel_transform_universality_v1 import (
    compose_kernels, deterministic_kernel, finite_transform_representation_certificate,
    normalize_kernel, pullback,
)

def test_deterministic_transform_is_kernel():
    k=deterministic_kernel(
        {"a":"x","b":"y"},
        source_states=("a","b"),target_states=("x","y"),
    )
    assert k["a"]=={"x":Fraction(1),"y":Fraction(0)}
    assert k["b"]=={"x":Fraction(0),"y":Fraction(1)}

def test_stochastic_kernel_composition_is_stochastic():
    k1={
        "a":{"m0":Fraction(1,4),"m1":Fraction(3,4)},
        "b":{"m0":Fraction(1,2),"m1":Fraction(1,2)},
    }
    k2={
        "m0":{"z0":Fraction(1),"z1":Fraction(0)},
        "m1":{"z0":Fraction(1,3),"z1":Fraction(2,3)},
    }
    out=compose_kernels(
        k1,k2,
        source_states=("a","b"),middle_states=("m0","m1"),target_states=("z0","z1"),
    )
    assert sum(out["a"].values())==1
    assert sum(out["b"].values())==1
    assert out["a"]["z1"]==Fraction(1,2)

def test_pullback_matches_direct_expectation_identity():
    k={
        "a":{"y0":Fraction(1,4),"y1":Fraction(3,4)},
        "b":{"y0":Fraction(1),"y1":Fraction(0)},
    }
    g={"y0":0,"y1":4}
    pb=pullback(k,g,source_states=("a","b"),target_states=("y0","y1"))
    assert pb["a"]==3
    assert pb["b"]==0

def test_representation_fails_closed_when_context_state_not_complete():
    assert not finite_transform_representation_certificate(
        complete_source_state_bound=False,
        complete_target_state_bound=True,
        randomized_transform_distribution_bound=True,
    )["pass"]

def test_complete_bound_deletes_transform_taxonomy_requirement_only():
    out=finite_transform_representation_certificate(
        complete_source_state_bound=True,
        complete_target_state_bound=True,
        randomized_transform_distribution_bound=True,
    )
    assert out["pass"]
    assert out["primitive_transform_taxonomy_required"] is False
    assert "BIND_TARGET_EVALUATOR_PULLBACKS" in out["required_remaining"]
    assert out["terminal_credit_delta"]==0
