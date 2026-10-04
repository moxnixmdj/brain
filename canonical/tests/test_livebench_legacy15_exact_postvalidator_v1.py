import pytest

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as p


class ContainsInstruction:
    def __init__(self, iid):
        self.iid = iid
        self.needle = ""

    def build_description(self, *, keywords):
        self.needle = str(keywords[0])

    def check_following(self, response):
        return self.needle in response


class ForbidInstruction:
    def __init__(self, iid):
        self.iid = iid
        self.word = ""

    def build_description(self, *, forbidden_words):
        self.word = str(forbidden_words[0])

    def check_following(self, response):
        return self.word not in response


def contract(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_registry_adapter_preserves_contract_order_and_boolean_vector():
    registry = {
        "keywords:existence": ContainsInstruction,
        "keywords:forbidden_words": ForbidInstruction,
    }
    out = p.evaluate_with_registry(
        "alpha",
        [
            contract("keywords:existence", keywords=["alpha"]),
            contract("keywords:forbidden_words", forbidden_words=["omega"]),
        ],
        registry,
    )
    assert out["status"] == "PASS__EXACT_PINNED_CHECKER_VECTOR"
    assert out["checker_results"] == [True, True]
    assert out["true_checker_count"] == 2
    assert out["terminal_data_used"] is False
    assert out["acceptance_credit"] is False


def test_parameter_incomplete_fails_closed():
    row = {
        "instruction_id": "keywords:existence",
        "slots": {"keywords": ["alpha"]},
        "parameter_complete": False,
    }
    with pytest.raises(p.ExactPostvalidationError, match="PARAMETER_INCOMPLETE"):
        p.evaluate_with_registry("alpha", [row], {"keywords:existence": ContainsInstruction})


def test_unknown_or_conflicting_ids_fail_closed_before_checker_execution():
    unknown = contract("not:a_checker")
    with pytest.raises(p.ExactPostvalidationError, match="NON_ACTIVE15"):
        p.evaluate_with_registry("", [unknown], {})

    conflict = [
        contract("detectable_format:json_format"),
        contract("length_constraints:number_words", num_words=2, relation="at least"),
    ]
    with pytest.raises(p.ExactPostvalidationError, match="CONFLICT_GRAPH"):
        p.evaluate_with_registry("", conflict, {})


def test_missing_visible_slot_fails_closed_before_checker_defaults():
    row = {
        "instruction_id": "startend:end_checker",
        "slots": {},
        "parameter_complete": True,
    }
    with pytest.raises(p.ExactPostvalidationError, match="VISIBLE_SLOT_SHAPE_MISMATCH"):
        p.evaluate_with_registry("", [row], {"startend:end_checker": ContainsInstruction})


def test_extra_visible_slot_fails_closed():
    row = {
        "instruction_id": "detectable_format:title",
        "slots": {"invented": 1},
        "parameter_complete": True,
    }
    with pytest.raises(p.ExactPostvalidationError, match="VISIBLE_SLOT_SHAPE_MISMATCH"):
        p.evaluate_with_registry("", [row], {"detectable_format:title": ContainsInstruction})


def test_none_visible_slot_fails_closed():
    row = {
        "instruction_id": "startend:end_checker",
        "slots": {"end_phrase": None},
        "parameter_complete": True,
    }
    with pytest.raises(p.ExactPostvalidationError, match="VISIBLE_SLOT_VALUE_NONE"):
        p.evaluate_with_registry("", [row], {"startend:end_checker": ContainsInstruction})


def test_strict_scorer_rejects_empty_response_before_checker_truth():
    registry = {"keywords:forbidden_words": ForbidInstruction}
    out = p.evaluate_with_registry(
        "",
        [contract("keywords:forbidden_words", forbidden_words=["omega"])],
        registry,
    )
    # ForbiddenWords.check_following("") would be True in isolation, but the
    # frozen strict evaluator gates every checker with response.strip().
    assert out["checker_results"] == [False]
    assert out["true_checker_count"] == 0
    assert out["strict_nonempty_response_gate_applied"] is True


def test_whitespace_only_response_is_also_strictly_rejected():
    registry = {"keywords:forbidden_words": ForbidInstruction}
    out = p.evaluate_with_registry(
        " \n\t ",
        [contract("keywords:forbidden_words", forbidden_words=["omega"])],
        registry,
    )
    assert out["checker_results"] == [False]
