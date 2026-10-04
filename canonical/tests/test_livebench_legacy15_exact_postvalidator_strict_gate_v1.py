import re

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as p


class Forbidden:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self, *, forbidden_words):
        self.words = list(forbidden_words)

    def check_following(self, value):
        return all(re.search(r"\\b" + w + r"\\b", value, re.I) is None for w in self.words)


class ZeroSentenceRaw:
    def __init__(self, iid):
        self.iid = iid

    def build_description(self, *, num_sentences, relation):
        self.threshold = num_sentences
        self.relation = relation

    def check_following(self, value):
        # Model the exact load-bearing asymmetry: raw checker can accept blank.
        if self.relation == "less than" and self.threshold == 1:
            return value.strip() == ""
        return False


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_strict_gate_rejects_blank_even_when_raw_forbidden_checker_passes():
    registry = {"keywords:forbidden_words": Forbidden}
    out = p.evaluate_with_registry(
        "",
        [c("keywords:forbidden_words", forbidden_words=["omega"])],
        registry,
    )
    assert out["checker_results"] == [False]
    assert out["true_checker_count"] == 0

    out = p.evaluate_with_registry(
        "alpha",
        [c("keywords:forbidden_words", forbidden_words=["omega"])],
        registry,
    )
    assert out["checker_results"] == [True]
    assert out["true_checker_count"] == 1


def test_strict_gate_makes_raw_zero_sentence_escape_uncreditable():
    registry = {"length_constraints:number_sentences": ZeroSentenceRaw}
    row = c(
        "length_constraints:number_sentences",
        num_sentences=1,
        relation="less than",
    )
    raw = ZeroSentenceRaw(row["instruction_id"])
    raw.build_description(**row["slots"])
    assert raw.check_following("") is True

    out = p.evaluate_with_registry("", [row], registry)
    assert out["checker_results"] == [False]
    assert out["true_checker_count"] == 0

    out = p.evaluate_with_registry("x", [row], registry)
    assert out["checker_results"] == [False]
    assert out["true_checker_count"] == 0


def test_postvalidator_binds_frozen_evaluation_main_blob():
    assert p.PINNED_EVALUATION_MAIN_BLOB == "4a341984936c4d609644a3b77f8c030ac5aa7269"
