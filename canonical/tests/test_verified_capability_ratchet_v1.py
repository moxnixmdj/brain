import pytest

from canonical.runtime.mdl_program_induction_v1 import Primitive, synthesize, verify
from canonical.runtime.verified_capability_ratchet_v1 import (
    CapabilityRatchetError,
    extend_registry,
    promote_verified_program,
)


def base_primitives():
    return [
        Primitive("ADD_1", 1, lambda x: x + 1),
        Primitive("DOUBLE", 1, lambda x: x * 2),
    ]


def test_verified_program_becomes_zero_learned_macro_and_compresses_future_search():
    primitives = base_primitives()

    first = synthesize(
        examples=[(1, 3), (2, 5), (5, 11)],
        primitives=primitives,
        max_description_length=3,
    )
    assert first["program"] == ["DOUBLE", "ADD_1"]

    receipt = verify(
        program=first["program"],
        examples=[(7, 15), (10, 21)],
        primitives=primitives,
    )
    assert receipt["pass"] is True

    promoted = promote_verified_program(
        primitive_id="AFFINE_2X_PLUS_1",
        program=first["program"],
        primitives=primitives,
        verification_receipt=receipt,
        macro_cost=1,
    )
    assert promoted.manifest["persistent_learned_state_bytes"] == 0
    assert promoted.manifest["requires_retraining_for_reuse"] is False

    extended = extend_registry(primitives, [promoted])
    future_examples = [(1, 7), (2, 11), (3, 15)]

    with_macro = synthesize(
        examples=future_examples,
        primitives=extended,
        max_description_length=2,
    )
    assert with_macro["status"] == "EXACT_PROGRAM_FOUND"
    assert with_macro["program"] == ["AFFINE_2X_PLUS_1", "AFFINE_2X_PLUS_1"]
    assert with_macro["description_length"] == 2

    without_macro = synthesize(
        examples=future_examples,
        primitives=primitives,
        max_description_length=4,
    )
    assert without_macro["status"] == "EXACT_PROGRAM_FOUND"
    assert without_macro["description_length"] == 4

    assert with_macro["description_length"] < without_macro["description_length"]
    assert with_macro["persistent_learned_state_bytes"] == 0


def test_unverified_program_cannot_enter_capability_library():
    primitives = base_primitives()
    receipt = verify(
        program=["DOUBLE", "ADD_1"],
        examples=[(7, 999)],
        primitives=primitives,
    )
    assert receipt["pass"] is False

    with pytest.raises(CapabilityRatchetError, match="VERIFICATION_NOT_PASS"):
        promote_verified_program(
            primitive_id="BAD_MACRO",
            program=["DOUBLE", "ADD_1"],
            primitives=primitives,
            verification_receipt=receipt,
        )


def test_verification_must_bind_exact_program_and_registry():
    primitives = base_primitives()
    receipt = verify(
        program=["DOUBLE", "ADD_1"],
        examples=[(7, 15)],
        primitives=primitives,
    )

    with pytest.raises(CapabilityRatchetError, match="VERIFICATION_PROGRAM_MISMATCH"):
        promote_verified_program(
            primitive_id="MISMATCHED",
            program=["ADD_1", "DOUBLE"],
            primitives=primitives,
            verification_receipt=receipt,
        )
