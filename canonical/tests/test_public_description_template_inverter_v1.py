from canonical.runtime import public_description_template_inverter_v1 as inv


SOURCE = r'''
class Instruction:
    pass

class StaticChecker(Instruction):
    def build_description(self):
        self._description_pattern = "Write each word on a new line."
        return self._description_pattern

class ParameterChecker(Instruction):
    def build_description(self, *, N=None, keyword=None):
        self._description_pattern = (
            "Use {keyword} exactly {N} times; repeat {keyword}."
        )
        return self._description_pattern.format(keyword=keyword, N=N)

class BranchChecker(Instruction):
    def build_description(self, n=None):
        if n == 1:
            self._description_pattern = "Use {n} item."
        else:
            self._description_pattern = "Use {n} items."
        return self._description_pattern.format(n=n)
'''


def test_extracts_static_parameterized_and_branch_templates():
    specs = inv.extract_templates(SOURCE)
    by_class = {}
    for spec in specs:
        by_class.setdefault(spec.class_name, []).append(spec)
    assert set(by_class) == {"StaticChecker", "ParameterChecker", "BranchChecker"}
    assert len(by_class["BranchChecker"]) == 2
    p = by_class["ParameterChecker"][0]
    assert p.rendered_fields == ("keyword", "N")
    assert p.declared_parameters == ("N", "keyword")
    assert p.nonrendered_parameters == ()


def test_matches_repeated_field_with_backreference():
    specs = inv.extract_templates(SOURCE)
    prompt = "Request. Use alpha exactly 3 times; repeat alpha."
    matches = inv.match_prompt(prompt, specs)
    hit = [x for x in matches if x["class_name"] == "ParameterChecker"]
    assert len(hit) == 1
    assert hit[0]["parameters"] == {"keyword": "alpha", "N": "3"}


def test_repeated_field_mismatch_does_not_match():
    specs = inv.extract_templates(SOURCE)
    prompt = "Use alpha exactly 3 times; repeat beta."
    assert not [x for x in inv.match_prompt(prompt, specs) if x["class_name"] == "ParameterChecker"]


def test_nonrendered_parameter_is_explicit_not_guessed():
    source = """
class Instruction: pass
class HiddenChecker(Instruction):
    def build_description(self, visible=None, hidden=None):
        self._description_pattern = "Visible {visible}."
        return self._description_pattern.format(visible=visible)
"""
    spec = inv.extract_templates(source)[0]
    assert spec.rendered_fields == ("visible",)
    assert spec.nonrendered_parameters == ("hidden",)


def test_source_is_parsed_never_executed():
    source = """
raise RuntimeError("MUST_NOT_EXECUTE")
class Instruction: pass
class SafeChecker(Instruction):
    def build_description(self):
        self._description_pattern = "Safe static constraint."
        return self._description_pattern
"""
    specs = inv.extract_templates(source)
    assert [x.class_name for x in specs] == ["SafeChecker"]


def test_audit_fails_closed_on_missing_expected_class():
    report = inv.audit(SOURCE, expected_classes=["StaticChecker", "AbsentChecker"])
    assert report["all_expected_classes_covered"] is False
    assert report["missing_expected_classes"] == ["AbsentChecker"]
