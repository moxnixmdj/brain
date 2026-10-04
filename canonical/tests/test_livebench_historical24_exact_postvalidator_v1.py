import re

import pytest

from canonical.runtime import livebench_historical24_exact_postvalidator_v1 as exact


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


class Placeholder:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self, *, num_placeholders):
        self.n = num_placeholders

    def check_following(self, value):
        return len(re.findall(r"\[.*?\]", value)) >= self.n


class NoComma:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self):
        pass

    def check_following(self, value):
        return "," not in value


class Constrained:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self):
        pass

    def check_following(self, value):
        return any(
            x in value
            for x in ("My answer is yes.", "My answer is no.", "My answer is maybe.")
        )


def test_extra9_slot_shapes_are_bound():
    assert exact.SLOT_KEYS["keywords:frequency"] == (
        "keyword",
        "frequency",
        "relation",
    )
    assert exact.SLOT_KEYS["keywords:letter_frequency"] == (
        "letter",
        "let_frequency",
        "let_relation",
    )
    assert exact.SLOT_KEYS["detectable_content:number_placeholders"] == (
        "num_placeholders",
    )
    assert exact.SLOT_KEYS["change_case:capital_word_frequency"] == (
        "capital_frequency",
        "capital_relation",
    )
    assert exact.SLOT_KEYS["punctuation:no_comma"] == ()


def test_extra_checker_vector_uses_strict_nonempty_gate():
    rows = [
        c("detectable_content:number_placeholders", num_placeholders=2),
        c("punctuation:no_comma"),
    ]
    registry = {
        "detectable_content:number_placeholders": Placeholder,
        "punctuation:no_comma": NoComma,
    }
    out = exact.evaluate_with_registry("[a] [b]", rows, registry)
    assert out["checker_results"] == [True, True]
    assert out["true_checker_count"] == 2

    empty = exact.evaluate_with_registry("", [c("punctuation:no_comma")], registry)
    assert empty["checker_results"] == [False]
    assert empty["strict_response_eligible"] is False


def test_constrained_response_is_structurally_standalone():
    rows = [c("detectable_format:constrained_response")]
    registry = {"detectable_format:constrained_response": Constrained}
    out = exact.evaluate_with_registry("My answer is yes.", rows, registry)
    assert out["checker_results"] == [True]

    with pytest.raises(
        exact.Historical24PostvalidationError,
        match="HISTORICAL24_CONFLICT_GRAPH_REJECTED",
    ):
        exact.evaluate_with_registry(
            "My answer is yes.",
            rows + [c("punctuation:no_comma")],
            {
                "detectable_format:constrained_response": Constrained,
                "punctuation:no_comma": NoComma,
            },
        )


def test_wrong_visible_slot_shape_fails_closed():
    with pytest.raises(
        exact.Historical24PostvalidationError,
        match="VISIBLE_SLOT_SHAPE_MISMATCH",
    ):
        exact.evaluate_with_registry(
            "x",
            [
                c(
                    "keywords:frequency",
                    keyword="alpha",
                    frequency=1,
                    relation="at least",
                    invented="bad",
                )
            ],
            {},
        )


def test_capital_frequency_requires_hermetic_nltk():
    assert exact.contracts_require_nltk(
        [
            c(
                "change_case:capital_word_frequency",
                capital_frequency=3,
                capital_relation="at least",
            )
        ]
    )
