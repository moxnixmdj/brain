"""Tests of the measurement "what does one bug fix teach".

The organ that is measured is not this file's subject: most tests here put a stand-in where the
organ and its oracle go, so that what is pinned is the measurement -- who is taught what, who
is asked what, what counts as repaired, and how it is counted. One class at the end runs the
real organ and the real test oracle on three small programs written here.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as tool  # noqa: E402

TAIL = '\n\n"""\nWhat the program is for.\n\nInput:\n    x: a number\n"""\n'

# name -> (code with the defect, code as published correct)
PROGRAMS = {
    "add_one": ("def add_one(x):\n    return x - 1\n", "def add_one(x):\n    return x + 1\n"),
    "at_most": ("def at_most(x, top):\n    if x < top:\n        return x\n    return top\n",
                "def at_most(x, top):\n    if x <= top:\n        return x\n    return top\n"),
    "at_least": ("def at_least(x, low):\n    if x > low:\n        return x\n    return low\n",
                 "def at_least(x, low):\n    if x >= low:\n        return x\n    return low\n"),
    "always_right": ("def always_right(x):\n    return x\n", "def always_right(x):\n    return x\n"),
    # the same one-line change as at_most, in another program
    "capped": ("def capped(x, top):\n    x = abs(x)\n    if x < top:\n        return x\n    return top\n",
               "def capped(x, top):\n    x = abs(x)\n    if x <= top:\n        return x\n    return top\n"),
}
TESTS = {
    "add_one": "    assert add_one(1) == 2\n    assert add_one(-1) == 0\n",
    "at_most": "    assert at_most(1, 3) == 1\n    assert at_most(5, 3) == 3\n    assert at_most(3.0, 3) == 3.0 and type(at_most(3.0, 3)) is float\n",
    "at_least": "    assert at_least(5, 3) == 5\n    assert at_least(1, 3) == 3\n    assert at_least(3.0, 3) == 3.0 and type(at_least(3.0, 3)) is float\n",
    "always_right": "    assert always_right(4) == 4\n",
    "capped": "    assert capped(-1, 3) == 1\n    assert capped(5, 3) == 3\n    assert capped(3.0, 3) == 3.0 and type(capped(3.0, 3)) is float\n",
}


def write_benchmark(root: pathlib.Path, names=("add_one", "at_most", "at_least", "always_right")) -> pathlib.Path:
    """A benchmark laid out like QuixBugs: buggy files end with a description in a string, correct
    files start with a blank line, one of them ends with another solution in a string."""
    for folder in ("python_programs", "correct_python_programs", "python_testcases", "json_testcases"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "conftest.py").write_text(textwrap.dedent('''
        import pytest


        def pytest_addoption(parser):
            parser.addoption("--correct", action="store_true")


        def pytest_configure(config):
            pytest.use_correct = config.getoption("--correct")
    '''))
    (root / "python_testcases" / "load_testdata.py").write_text("def load_json_testcases(name):\n    return []\n")
    for name in names:
        buggy, correct = PROGRAMS[name]
        (root / "python_programs" / f"{name}.py").write_text("\n" + buggy + TAIL)
        extra = '\n"""\ndef ' + name + '(x):\n    pass\n"""\n' if name == "at_most" else ""
        (root / "correct_python_programs" / f"{name}.py").write_text("\n" + correct + extra)
        (root / "python_testcases" / f"test_{name}.py").write_text(
            "import pytest\n\nif pytest.use_correct:\n"
            f"    from correct_python_programs.{name} import {name}\nelse:\n    from python_programs.{name} import {name}\n\n\n"
            f"def test_{name}():\n{TESTS[name]}")
    (root / "python_programs" / "node.py").write_text("class Node:\n    pass\n")
    (root / "python_testcases" / "node.py").write_text("class Node:\n    pass\n")
    (root / "python_testcases" / "test_orphan.py").write_text("def test_orphan():\n    assert True\n")    # no program of that name
    return root


class _Verdict:
    def __init__(self, passed, count, returncode, error=None):
        self.passed = passed
        self.evidence = {"test_count": count, "returncode": returncode}
        if error:
            self.evidence = {"error": error}


class FakeOracle:
    """Stands where ProjectTestOracle goes: runs the program's assertions in this process."""
    log: list = []

    def __init__(self, name):
        self.name, self.calls = name, 0

    def __call__(self, candidate):
        self.calls += 1
        FakeOracle.log.append((self.name, candidate))
        scope: dict = {}
        try:
            exec(compile(candidate, self.name, "exec"), scope)                      # noqa: S102 -- three-line programs written above
            exec("def _check():\n" + TESTS[self.name], scope)                       # noqa: S102
            scope["_check"]()
        except AssertionError:
            return _Verdict(False, 1, 1)
        except Exception as error:  # noqa: BLE001
            return _Verdict(False, None, None, type(error).__name__)
        return _Verdict(True, 1, 0)


def _changed_line(before, after):
    """(line removed, line put in its place) of a one-line change, or None."""
    a, b = before.split("\n"), after.split("\n")
    if len(a) != len(b):
        return None
    differing = [(x, y) for x, y in zip(a, b) if x != y]
    return differing[0] if len(differing) == 1 else None


class FakeStore:
    """Stands where VerifiedSkillStore goes, and keeps what it holds in a real file, as the organ
    does. A lesson is a one-line change; two lessons with the same change are the same rule. It
    repairs a source that contains the removed line by putting the other in its place -- if the
    target's tests then pass."""
    recalls: list = []                 # (rules held, source, flags, whether each rule was calibrated)
    refuse: set = set()                # 'before' texts it will not store
    refuse_on_import: set = set()      # rule ids it will not import
    lie_about: set = set()             # sources for which it "accepts" a patch that does not pass
    shipped: list = []                 # what a store "the tree ships with" starts from

    def __init__(self, path):
        self.path = pathlib.Path(path)
        if not self.path.exists():
            self._write([])

    def _read(self):
        import json
        return json.loads(self.path.read_text())

    def _write(self, rules):
        import json
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rules))

    def crystallize_code_fix(self, *, before_snippet, after_snippet, language, error_class, contract, training_verifier):
        assert language == "python" and contract == tool.CONTRACT and error_class == tool.ERROR_CLASS
        change = _changed_line(before_snippet, after_snippet)
        if before_snippet in FakeStore.refuse or change is None:
            return {"crystallized": False, "reason": "FAKE_REFUSAL"}
        rule = {"skill_id": "rule:" + change[0].strip() + "->" + change[1].strip(), "removed": change[0], "added": change[1],
                "taught_on": before_snippet}
        self._write([r for r in self._read() if r["skill_id"] != rule["skill_id"]] + [rule])
        return {"crystallized": True, "skill_id": rule["skill_id"], "hole_count": 0}

    def lookup_rules(self, language):
        return self._read()

    def export_bundle(self):
        return {"rules": self._read()}

    def import_bundle(self, bundle):
        held = self._read()
        report = {"accepted": 0, "merged": 0, "refused": 0}
        for rule in bundle["rules"]:
            if rule["skill_id"] in FakeStore.refuse_on_import:
                report["refused"] += 1
            elif any(r["skill_id"] == rule["skill_id"] for r in held):
                report["merged"] += 1
            else:
                held.append(dict(rule))
                report["accepted"] += 1
        self._write(held)
        return report

    def recall_and_apply_verified(self, *, source_text, language, verifier, required_verification_kind, scope_id, context, **flags):
        assert required_verification_kind == "TEST_SUITE" and scope_id == tool.SCOPE and context == tool.CONTEXT
        held = self._read()
        FakeStore.recalls.append(([rule["taught_on"] for rule in held], source_text, dict(flags),
                                  [bool(rule.get("calibrated")) for rule in held]))
        if source_text in FakeStore.lie_about and held:
            return {"patched_source": source_text + "\n# untouched\n", "skill_id": held[0]["skill_id"],
                    "recall_strategy": "lie", "scope_tier": "NONE"}
        for rule in held:
            lines = source_text.split("\n")
            if rule["removed"] in lines:
                candidate = "\n".join(rule["added"] if line == rule["removed"] else line for line in lines)
                if verifier(candidate).passed:
                    return {"patched_source": candidate, "skill_id": rule["skill_id"],
                            "recall_strategy": "statement", "scope_tier": "SCOPE_STATEMENT"}
        return None


def _fake_calibrate(path):
    store = FakeStore(path)
    rules = store._read()
    for rule in rules:
        rule["calibrated"] = True
    store._write(rules)
    return {rule["skill_id"]: {"result": "FAKE", "scope": "SCOPE_STATEMENT"} for rule in rules}


def _fake_shipped_store(path):
    store = FakeStore(path)
    store._write([dict(rule) for rule in FakeStore.shipped])
    return store


class WithStandIns(unittest.TestCase):
    """The measurement with a stand-in organ and a stand-in oracle: fast, and nothing here depends on
    what the real organ happens to do."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        self.root = write_benchmark(self.dir / "bench")
        FakeStore.recalls, FakeStore.refuse, FakeStore.lie_about = [], set(), set()
        FakeStore.refuse_on_import, FakeStore.shipped = set(), []
        FakeOracle.log = []
        self._saved = (tool._store, tool.oracle_for, tool.calibrate, tool._shipped_store)
        tool._store = FakeStore
        tool.oracle_for = lambda project, name, timeout_s=tool.DEFAULT_TIMEOUT_S: FakeOracle(name)
        tool.calibrate = _fake_calibrate
        tool._shipped_store = _fake_shipped_store

    def tearDown(self):
        tool._store, tool.oracle_for, tool.calibrate, tool._shipped_store = self._saved
        shutil.rmtree(self.dir, ignore_errors=True)

    def _measure(self, names=("add_one", "at_most", "at_least"), **options):
        return tool.measure(self.root, list(names), self.dir / "work", **options)

    def _lessons_in(self, name):
        return FakeStore(self.dir / "work" / "stores" / f"{name}.sqlite")._read()

    def test_only_programs_with_both_versions_and_a_test_are_listed(self):
        self.assertEqual(tool.program_names(self.root), ["add_one", "always_right", "at_least", "at_most"])

    def test_a_program_that_already_passes_is_not_a_target_and_is_never_taught(self):
        measured = self._measure(names=("add_one", "always_right"))
        self.assertEqual(measured["targets"], ["add_one"])
        self.assertFalse(measured["census"]["always_right"]["can_be_a_target"])
        self.assertNotIn("always_right", measured["lessons"])
        self.assertFalse((self.dir / "work" / "stores" / "always_right.sqlite").exists())
        self.assertFalse([held for held, source, flags, calibrated in FakeStore.recalls if "always_right" in source])

    def test_the_census_says_whether_the_oracle_could_count_the_failure(self):
        checked = tool.census(self.root, ["add_one"], self.dir / "projects")
        row = checked["add_one"]
        self.assertTrue(row["can_be_a_target"])
        self.assertTrue(row["buggy_fails_in_a_way_the_oracle_counts"])
        self.assertEqual((row["fix"]["lines_removed"], row["fix"]["lines_added"]), (1, 1))
        # an oracle that could not run the tests at all: still a failure, but not one it counted
        saved = tool.oracle_for

        class Broken(FakeOracle):
            def __call__(self, candidate):
                verdict = super().__call__(candidate)
                return verdict if verdict.passed else _Verdict(False, None, None, "TypeError")
        tool.oracle_for = lambda project, name, timeout_s=tool.DEFAULT_TIMEOUT_S: Broken(name)
        try:
            row = tool.census(self.root, ["add_one"], self.dir / "projects")["add_one"]
        finally:
            tool.oracle_for = saved
        self.assertTrue(row["can_be_a_target"])
        self.assertFalse(row["buggy_fails_in_a_way_the_oracle_counts"])

        class NeverFinishes(FakeOracle):
            def __call__(self, candidate):
                verdict = super().__call__(candidate)
                return verdict if verdict.passed else _Verdict(False, 0, 124)       # timed out: no test was counted
        tool.oracle_for = lambda project, name, timeout_s=tool.DEFAULT_TIMEOUT_S: NeverFinishes(name)
        try:
            row = tool.census(self.root, ["add_one"], self.dir / "projects")["add_one"]
        finally:
            tool.oracle_for = saved
        self.assertTrue(row["can_be_a_target"])
        self.assertFalse(row["buggy_fails_in_a_way_the_oracle_counts"])
        self.assertEqual((row["buggy"]["test_count"], row["buggy"]["returncode"]), (0, 124))

    def test_each_fix_is_taught_once_alone_and_exactly_as_published(self):
        measured = self._measure()
        self.assertEqual(measured["taught"], ["add_one", "at_least", "at_most"])
        for name in measured["taught"]:
            lessons = self._lessons_in(name)
            self.assertEqual(len(lessons), 1, name)
            buggy = (self.root / "python_programs" / f"{name}.py").read_text()
            self.assertEqual(lessons[0]["taught_on"], buggy)
            wrong, right = _changed_line(PROGRAMS[name][0], PROGRAMS[name][1])
            self.assertEqual((lessons[0]["removed"], lessons[0]["added"]), (wrong, right))     # the published change, whole
        # the fix handed to the organ is the buggy file with that one line changed: the description at its end is left alone
        handed = {}
        saved = FakeStore.crystallize_code_fix

        def watching(self, **given):
            handed[given["before_snippet"]] = given["after_snippet"]
            return saved(self, **given)
        FakeStore.crystallize_code_fix = watching
        try:
            self._measure()
        finally:
            FakeStore.crystallize_code_fix = saved
        for name in measured["taught"]:
            buggy = (self.root / "python_programs" / f"{name}.py").read_text()
            self.assertEqual(handed[buggy], buggy.replace(PROGRAMS[name][0], PROGRAMS[name][1]))
            self.assertTrue(handed[buggy].endswith(TAIL))

    def test_the_same_bug_again_is_asked_of_the_lesson_from_that_bug_only(self):
        measured = self._measure()
        for setting in tool.SETTINGS:
            again = measured["outcomes"]["same_bug_again"][setting]
            self.assertEqual(sorted(again), ["add_one", "at_least", "at_most"])
            for name, outcome in again.items():
                self.assertTrue(outcome["repaired"], (setting, name))
                self.assertTrue(outcome["is_the_published_fix"])
                self.assertEqual(outcome["from_the_lesson_of"], [name])
                self.assertEqual((outcome["lessons_given"], outcome["rules_held"], outcome["rules_refused_on_the_way"]), (1, 1, 0))

    def test_no_recall_about_another_bug_ever_holds_that_bugs_own_lesson(self):
        measured = self._measure()
        buggy = {name: (self.root / "python_programs" / f"{name}.py").read_text() for name in ("add_one", "at_most", "at_least")}
        own, single_other, all_other = 0, 0, 0
        for held, source, flags, calibrated in FakeStore.recalls:
            if not held:
                continue                                                        # asked of what the tree ships with
            if source in held:
                self.assertEqual(held, [source])                               # only in "the same bug again"
                own += 1
            elif len(held) == 1:
                single_other += 1
            else:
                self.assertEqual(sorted(held), sorted(text for name, text in buggy.items() if text != source))
                all_other += 1
        settings = len(tool.SETTINGS)
        self.assertEqual((own, single_other, all_other), (3 * settings, 6 * settings, 3 * settings))
        self.assertEqual(len(FakeStore.recalls), (3 + 6 + 3 + 3) * settings)                 # and three with what the tree ships with: nothing
        for setting in tool.SETTINGS:
            for teacher, row in measured["outcomes"]["one_fix"][setting].items():
                self.assertNotIn(teacher, row)
                self.assertEqual(sorted(row), sorted(set(measured["targets"]) - {teacher}))
                self.assertFalse(any(outcome["repaired"] for outcome in row.values()))
            self.assertFalse(any(o["repaired"] for o in measured["outcomes"]["all_other_fixes"][setting].values()))

    def test_the_two_settings_are_the_organs_defaults_and_everything_switched_on(self):
        self._measure()
        seen = {}
        for held, source, flags, calibrated in FakeStore.recalls:
            if held:
                seen.setdefault(tuple(sorted(flags.items())), set()).add(all(calibrated))
        off = tuple(sorted({"allow_operator_generalization": False, "allow_scope_escalation": False,
                            "allow_cross_scope_transfer": False}.items()))
        on = tuple(sorted({"allow_operator_generalization": True, "allow_scope_escalation": True,
                           "allow_cross_scope_transfer": True}.items()))
        self.assertEqual(seen, {off: {True}, on: {False}})      # defaults go with the calibrated rule, as in production
        with self.assertRaises(ValueError):
            self._measure(settings=("as_wide_as_it_gets",))

    def test_a_fix_the_organ_refuses_is_reported_and_teaches_nothing(self):
        FakeStore.refuse = {(self.root / "python_programs" / "at_most.py").read_text()}
        measured = self._measure()
        self.assertEqual(measured["taught"], ["add_one", "at_least"])
        self.assertEqual(measured["lessons"]["at_most"], {"crystallized": False, "reason": "FAKE_REFUSAL",
                                                          "skill_id": None, "hole_count": None})
        self.assertEqual(sorted(measured["targets"]), ["add_one", "at_least", "at_most"])    # it is still a bug to repair
        summary = tool.summarise(measured)
        self.assertEqual(summary["fixes_the_organ_refused_to_store"], {"FAKE_REFUSAL": ["at_most"]})
        self.assertEqual(summary["fixes_the_organ_stored_as_lessons"], 2)
        for setting in tool.SETTINGS:
            self.assertNotIn("at_most", measured["outcomes"]["same_bug_again"][setting])
            self.assertIn("at_most", measured["outcomes"]["all_other_fixes"][setting])
            self.assertEqual(measured["outcomes"]["all_other_fixes"][setting]["at_most"]["rules_held"], 2)
            self.assertEqual(measured["outcomes"]["all_other_fixes"][setting]["add_one"]["rules_held"], 1)
            self.assertEqual(measured["outcomes"]["all_other_fixes"][setting]["add_one"]["lessons_given"], 1)

    def test_a_patch_the_organ_accepts_but_the_tests_reject_is_not_a_repair(self):
        FakeStore.lie_about = {(self.root / "python_programs" / "at_least.py").read_text()}
        measured = self._measure()
        for setting in tool.SETTINGS:
            for teacher, row in measured["outcomes"]["one_fix"][setting].items():
                if teacher != "at_least":
                    self.assertTrue(row["at_least"]["proposed"])
                    self.assertFalse(row["at_least"]["repaired"])
                    self.assertFalse(row["at_least"]["is_the_published_fix"])
            other = measured["outcomes"]["all_other_fixes"][setting]["at_least"]
            self.assertTrue(other["proposed"] and not other["repaired"])
        summary = tool.summarise(measured)["settings"]["as_taught"]
        self.assertEqual(summary["one_fix_then_another_bug"]["pairs_repaired"], 0)
        self.assertEqual(summary["all_other_fixes_then_this_bug"]["proposed_but_failed_the_second_check"], ["at_least"])
        self.assertEqual(summary["all_other_fixes_then_this_bug"]["repaired"], 0)

    def test_the_summary_counts_what_the_outcomes_say(self):
        measured = self._measure()
        # put two repairs in by hand: one lesson repairs two other bugs, one of them with another patch than the published one
        pairs = measured["outcomes"]["one_fix"]["widest"]
        pairs["add_one"]["at_most"].update(repaired=True, proposed=True, strategy="operator_generalization",
                                           is_the_published_fix=True, oracle_calls=3)
        pairs["add_one"]["at_least"].update(repaired=True, proposed=True, strategy="operator_generalization",
                                            is_the_published_fix=False, oracle_calls=2)
        pairs["at_most"]["at_least"].update(repaired=True, proposed=True, strategy="statement", is_the_published_fix=True)
        pairs["at_least"]["add_one"]["problem"] = "RECALL_TOOK_TOO_LONG"
        measured["outcomes"]["all_other_fixes"]["widest"]["at_least"].update(
            repaired=True, proposed=True, strategy="statement", is_the_published_fix=True, from_the_lesson_of=["at_most"])
        summary = tool.summarise(measured)
        self.assertEqual((summary["programs"], summary["usable_as_targets"], summary["not_usable"]), (3, 3, []))
        wide = summary["settings"]["widest"]["one_fix_then_another_bug"]
        self.assertEqual((wide["pairs_repaired"], wide["pairs_tried"], wide["of_which_with_the_published_fix"]), (3, 6, 2))
        self.assertEqual(wide["other_bugs_repaired_per_lesson"], {"least": 0, "middle": 1, "most": 2})
        self.assertEqual(wide["lessons_that_repair_no_other_bug"], 1)
        self.assertEqual(wide["lessons_that_repair_each_such_target"], {"at_least": 2, "at_most": 1})
        self.assertEqual(wide["targets_some_lesson_repairs"], 2)
        self.assertEqual(wide["by_strategy"], {"operator_generalization": 2, "statement": 1})
        self.assertEqual(wide["test_runs"], 5)
        self.assertEqual(wide["recalls_with_a_problem"], 1)
        others = summary["settings"]["widest"]["all_other_fixes_then_this_bug"]
        self.assertEqual((others["repaired"], others["of"]), (1, 3))
        self.assertEqual(others["which"], {"at_least": {"from_the_lesson_of": ["at_most"], "strategy": "statement",
                                                        "is_the_published_fix": True}})
        self.assertEqual(others["lessons_given_and_different_rules_held"], {"least": [2, 2], "most": [2, 2]})
        self.assertEqual(others["recalls_that_lost_a_rule_on_the_way"], [])
        self.assertEqual(wide["recalls_that_lost_a_rule_on_the_way"], 0)
        narrow = summary["settings"]["as_taught"]
        self.assertEqual(narrow["one_fix_then_another_bug"]["pairs_repaired"], 0)
        self.assertEqual(narrow["same_bug_again"], {"repaired": 3, "of": 3, "not_repaired": []})

    def test_the_one_fix_question_can_be_asked_of_a_sample_of_lessons_drawn_by_seed(self):
        first = self._measure(one_fix_teachers=2, seed=7)
        self.assertEqual(len(first["one_fix_teachers"]), 2)
        self.assertEqual(sorted(first["outcomes"]["one_fix"]["as_taught"]), first["one_fix_teachers"])
        self.assertEqual(len(first["outcomes"]["all_other_fixes"]["as_taught"]), 3)       # the other questions are not sampled
        again = self._measure(one_fix_teachers=2, seed=7)
        self.assertEqual(again["one_fix_teachers"], first["one_fix_teachers"])
        everyone = self._measure(one_fix_teachers=99)
        self.assertEqual(everyone["one_fix_teachers"], ["add_one", "at_least", "at_most"])

    def test_a_lesson_does_repair_another_bug_with_the_same_one_line_change_and_that_is_counted(self):
        write_benchmark(self.root, names=("add_one", "at_most", "at_least", "capped"))
        measured = self._measure(names=("add_one", "at_most", "at_least", "capped"))
        for setting in tool.SETTINGS:
            pairs = measured["outcomes"]["one_fix"][setting]
            repaired = sorted((teacher, target) for teacher, row in pairs.items() for target, o in row.items() if o["repaired"])
            self.assertEqual(repaired, [("at_most", "capped"), ("capped", "at_most")])
            hit = pairs["at_most"]["capped"]
            self.assertTrue(hit["is_the_published_fix"])
            self.assertEqual(hit["from_the_lesson_of"], ["at_most"])
            self.assertGreaterEqual(hit["oracle_calls"], 1)
            others = measured["outcomes"]["all_other_fixes"][setting]
            self.assertEqual(sorted(t for t, o in others.items() if o["repaired"]), ["at_most", "capped"])
            self.assertEqual(others["capped"]["from_the_lesson_of"], ["at_most"])          # never from its own lesson
            self.assertEqual(others["at_most"]["from_the_lesson_of"], ["capped"])
            # two of the three lessons given for add_one are one and the same rule
            self.assertEqual((others["add_one"]["lessons_given"], others["add_one"]["rules_held"]), (3, 2))
            self.assertEqual((others["capped"]["lessons_given"], others["capped"]["rules_held"]), (3, 3))
        # one more repair put in by hand, so that the lessons repair 0, 0, 1 and 2 other bugs
        measured["outcomes"]["one_fix"]["widest"]["at_most"]["add_one"].update(repaired=True, proposed=True, strategy="by hand")
        wide = tool.summarise(measured)["settings"]["widest"]["one_fix_then_another_bug"]
        self.assertEqual(wide["other_bugs_repaired_per_lesson"], {"least": 0, "middle": 1, "most": 2})
        self.assertEqual(wide["lessons_that_repair_no_other_bug"], 2)
        self.assertEqual(wide["pairs_repaired"], 3)
        summary = tool.summarise(measured)["settings"]["as_taught"]
        self.assertEqual(summary["one_fix_then_another_bug"]["pairs_repaired"], 2)
        self.assertEqual(summary["one_fix_then_another_bug"]["pairs_tried"], 12)
        self.assertEqual(summary["one_fix_then_another_bug"]["lessons_that_repair_each_such_target"], {"at_most": 1, "capped": 1})
        self.assertEqual(summary["one_fix_then_another_bug"]["lessons_that_repair_no_other_bug"], 2)
        self.assertEqual(summary["all_other_fixes_then_this_bug"]["repaired"], 2)
        self.assertEqual(summary["all_other_fixes_then_this_bug"]["lessons_given_and_different_rules_held"],
                         {"least": [3, 2], "most": [3, 3]})

    def test_a_store_built_for_one_recall_holds_nothing_of_the_recall_before(self):
        measured = self._measure()
        stores = self.dir / "work" / "stores"
        scratch = self.dir / "work" / "scratch" / "recall.sqlite"
        tool.store_holding([stores / "add_one.sqlite", stores / "at_most.sqlite"], scratch)
        where, tally = tool.store_holding([stores / "at_least.sqlite"], scratch)
        self.assertEqual(tally, {"lessons": 1, "rules": 1, "refused": 0})
        self.assertEqual([rule["taught_on"] for rule in FakeStore(where)._read()],
                         [(self.root / "python_programs" / "at_least.py").read_text()])
        self.assertEqual(self._lessons_in("add_one")[0]["taught_on"], (self.root / "python_programs" / "add_one.py").read_text())
        self.assertEqual(len(self._lessons_in("add_one")), 1)                           # the lesson stores themselves are only read
        del measured

    def test_a_rule_lost_between_the_lesson_and_the_recall_is_seen(self):
        measured = self._measure()
        self.assertEqual(tool.summarise(measured)["lessons_whose_calibrated_copy_lost_the_rule"], [])
        self.assertEqual({lesson["rules_in_the_calibrated_copy"] for lesson in measured["lessons"].values()}, {1})
        FakeStore.refuse_on_import = {self._lessons_in("at_most")[0]["skill_id"]}
        again = self._measure()
        # the copy made for calibration lost it already, and says so ...
        self.assertEqual(again["lessons"]["at_most"]["rules_in_the_calibrated_copy"], 0)
        summary = tool.summarise(again)
        self.assertEqual(summary["lessons_whose_calibrated_copy_lost_the_rule"], ["at_most"])
        # ... and every recall that was to hold that rule shows that it did not
        lost = again["outcomes"]["same_bug_again"]["as_taught"]["at_most"]
        self.assertEqual((lost["lessons_given"], lost["rules_held"], lost["rules_refused_on_the_way"]), (1, 0, 0))
        lost = again["outcomes"]["same_bug_again"]["widest"]["at_most"]
        self.assertEqual((lost["lessons_given"], lost["rules_held"], lost["rules_refused_on_the_way"]), (1, 0, 1))
        for setting in tool.SETTINGS:
            self.assertFalse(again["outcomes"]["same_bug_again"][setting]["at_most"]["repaired"])
            self.assertEqual(summary["settings"][setting]["same_bug_again"]["not_repaired"], ["at_most"])
            self.assertEqual(summary["settings"][setting]["one_fix_then_another_bug"]["recalls_that_lost_a_rule_on_the_way"], 2)
        self.assertEqual(summary["settings"]["widest"]["all_other_fixes_then_this_bug"]["recalls_that_lost_a_rule_on_the_way"],
                         ["add_one", "at_least"])

    def test_what_the_tree_ships_with_is_asked_about_every_bug_and_is_never_a_lesson_from_here(self):
        wrong, right = _changed_line(PROGRAMS["at_least"][0], PROGRAMS["at_least"][1])
        FakeStore.shipped = [{"skill_id": "shipped", "removed": wrong, "added": right, "taught_on": "somewhere else"}]
        measured = self._measure()
        self.assertEqual(measured["python_rules_the_tree_ships_with"], 1)
        for setting in tool.SETTINGS:
            shipped = measured["outcomes"]["already_held"][setting]
            self.assertEqual(sorted(shipped), ["add_one", "at_least", "at_most"])
            self.assertEqual({name: o["repaired"] for name, o in shipped.items()},
                             {"add_one": False, "at_least": True, "at_most": False})
            self.assertEqual({o["lessons_given"] for o in shipped.values()}, {0})
            self.assertEqual({o["rules_held"] for o in shipped.values()}, {1})
            self.assertTrue(shipped["at_least"]["is_the_published_fix"])
            self.assertNotIn("is_the_published_fix", shipped["add_one"])
            # and none of it is in a recall that was about lessons given here
            for teacher, row in measured["outcomes"]["one_fix"][setting].items():
                self.assertEqual({o["rules_held"] for o in row.values()}, {1})
        block = tool.summarise(measured)["settings"]["widest"]["what_the_tree_ships_with_then_this_bug"]
        self.assertEqual((block["repaired"], block["of"], block["which"], block["rules_held"]), (1, 3, ["at_least"], [1]))
        held_somewhere_else = [held for held, source, flags, calibrated in FakeStore.recalls if "somewhere else" in held]
        self.assertEqual(len(held_somewhere_else), 3 * len(tool.SETTINGS))
        self.assertTrue(all(held == ["somewhere else"] for held in held_somewhere_else))

    def test_the_command_line_writes_what_was_measured(self):
        import json
        out = self.dir / "result.json"
        work = self.dir / "cli-work"
        work.mkdir()                                                             # it may be there already
        code = tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(work), "--programs", "add_one", "at_most",
                          "--settings", "as_taught", "--out", str(out)])
        self.assertEqual(code, 0)
        written = json.loads(out.read_text())
        self.assertEqual(written["schema"], tool.SCHEMA)
        self.assertEqual(written["programs"], ["add_one", "at_most"])
        self.assertEqual(sorted(written["outcomes"]["one_fix"]), ["as_taught"])
        self.assertEqual(written["parameters"]["settings"], {"as_taught": tool.SETTINGS["as_taught"]})
        self.assertEqual(written["summary"]["fixes_the_organ_stored_as_lessons"], 2)
        self.assertEqual(written["producer_cognition_model_dependency_count"], 0)
        self.assertEqual(written["incremental_spend_usd"], 0)
        self.assertEqual(written["parameters"]["seed"], 0)
        self.assertEqual(len(written["environment"]["benchmark_sha256"]), 64)
        self.assertEqual(written["environment"]["python"], sys.version.split()[0])
        self.assertTrue((work / "projects" / "add_one" / "python_programs" / "add_one.py").is_file())
        # every program when none is named; a census alone when that is asked for; an earlier census reused when one is given
        census_only = self.dir / "census.json"
        self.assertEqual(tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(work), "--census-only",
                                    "--out", str(census_only)]), 0)
        checked = json.loads(census_only.read_text())
        self.assertEqual(sorted(checked["census"]), ["add_one", "always_right", "at_least", "at_most"])
        self.assertNotIn("outcomes", checked)
        checked["census"]["add_one"]["can_be_a_target"] = False                  # an earlier census that says otherwise is believed
        census_only.write_text(json.dumps(checked))
        reused = self.dir / "reused.json"
        self.assertEqual(tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(work), "--programs", "add_one", "at_most",
                                    "--census-from", str(census_only), "--out", str(reused)]), 0)
        self.assertEqual(json.loads(reused.read_text())["targets"], ["at_most"])
        self.assertEqual(tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(work), "--programs", "add_one",
                                    "--settings", "as_taught"]), 0)                # no --out: nothing is written, nothing breaks

    def test_an_organ_that_raises_or_never_returns_costs_one_recall_not_the_run(self):
        store = FakeStore(self.dir / "x.sqlite")
        store._write([{"skill_id": "r", "removed": "a", "added": "b", "taught_on": "t"}])

        def raises(**kwargs):
            raise KeyError("inside the organ")
        store.recall_and_apply_verified = raises
        saved = tool._store
        tool._store = lambda path: store
        try:
            outcome = tool.recall(self.dir / "x.sqlite", "source", FakeOracle("add_one"), "as_taught")
            self.assertEqual((outcome["proposed"], outcome["problem"]), (False, "ORGAN_RAISED_KeyError"))
            limit = tool.RECALL_WALL_LIMIT_S
            tool.RECALL_WALL_LIMIT_S = 1

            def hangs(**kwargs):
                import time
                time.sleep(30)
            store.recall_and_apply_verified = hangs
            try:
                outcome = tool.recall(self.dir / "x.sqlite", "source", FakeOracle("add_one"), "as_taught")
            finally:
                tool.RECALL_WALL_LIMIT_S = limit
            self.assertEqual((outcome["proposed"], outcome["problem"]), (False, "RECALL_TOOK_TOO_LONG"))
            self.assertLess(outcome["seconds"], 5)
            import signal
            self.assertEqual(signal.alarm(0), 0)                                   # no alarm is left ticking after a recall
            store.recall_and_apply_verified = lambda **kwargs: None
            quiet = tool.recall(self.dir / "x.sqlite", "source", FakeOracle("add_one"), "widest")
            self.assertEqual(quiet, {"proposed": False, "oracle_calls": 0, "seconds": quiet["seconds"]})
            self.assertEqual(signal.alarm(0), 0)
        finally:
            tool._store = saved


class ReadingTheBenchmark(unittest.TestCase):
    def test_a_description_at_the_end_of_a_file_is_split_off_and_a_string_in_a_statement_is_not(self):
        code = "def f(x):\n    return x\n"
        self.assertEqual(tool.split_trailing_docstring(code + TAIL), (code, TAIL))
        self.assertEqual("".join(tool.split_trailing_docstring(code + TAIL)), code + TAIL)
        self.assertEqual(tool.split_trailing_docstring(code), (code, ""))
        assigned = 'def f(x):\n    return x\n\nNOTE = """\nkept\n"""\n'
        self.assertEqual(tool.split_trailing_docstring(assigned), (assigned, ""))
        self.assertEqual(tool.split_trailing_docstring('"""'), ('"""', ""))
        only_words = '"""\nonly words\n"""\n'
        self.assertEqual(tool.split_trailing_docstring(only_words), (only_words, ""))        # no code to split it from
        inside = 'def f(x):\n    """\n    says what f does\n    """\n    return x\n'
        self.assertEqual(tool.split_trailing_docstring(inside), (inside, ""))                # a string inside, code after it
        tight = 'x = 1\n"""\nwords\n"""\n'
        self.assertEqual(tool.split_trailing_docstring(tight), ("x = 1\n", '"""\nwords\n"""\n'))   # no blank line between

    def test_the_fix_is_the_published_difference_and_nothing_else(self):
        buggy = "\ndef f(a, b):\n    if a < b:   \n        return a\n    return b\n" + TAIL
        correct = "\n\ndef f(a, b):\n    if a <= b:\n        return a\n    return b\n\n\"\"\"\ndef f(a, b):\n    return min(a, b)\n\"\"\"\n"
        fix = tool.reference_fix(buggy, correct)
        self.assertEqual(fix["fixed_source"], "\ndef f(a, b):\n    if a <= b:\n        return a\n    return b\n" + TAIL)
        self.assertEqual((fix["lines_removed"], fix["lines_added"], len(fix["hunks"])), (1, 1, 1))
        self.assertEqual(fix["hunks"][0]["added"], ["    if a <= b:"])
        added = tool.reference_fix("def f(a):\n    return a\n", "def f(a):\n    a = a or 0\n    return a\n")
        self.assertEqual((added["lines_removed"], added["lines_added"]), (0, 1))
        self.assertEqual(added["fixed_source"], "def f(a):\n    a = a or 0\n    return a\n")
        same = tool.reference_fix("def f(a):\n    return a  \n", "\ndef f(a):\n    return a\n")
        self.assertEqual((same["hunks"], same["fixed_source"]), ([], "def f(a):\n    return a  \n"))   # spaces at a line's end are not a defect

    def test_a_program_needs_both_versions_to_be_listed(self):
        directory = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        try:
            root = write_benchmark(directory / "bench")
            (root / "correct_python_programs" / "at_most.py").unlink()
            (root / "python_programs" / "at_least.py").unlink()
            self.assertEqual(tool.program_names(root), ["add_one", "always_right"])
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_project_takes_the_data_its_tests_load_and_does_without_helpers_that_are_not_there(self):
        directory = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        try:
            root = write_benchmark(directory / "bench")
            (root / "json_testcases" / "add_one.json").write_text("[[1], 2]\n")
            for missing in (root / "python_programs" / "node.py", root / "python_testcases" / "node.py"):
                missing.unlink()
            project = tool.build_project(root, "add_one", directory / "projects")
            files = sorted(path.relative_to(project).as_posix() for path in project.rglob("*") if path.is_file())
            self.assertEqual(files, ["conftest.py", "json_testcases/add_one.json", "python_programs/add_one.py",
                                     "python_testcases/load_testdata.py", "python_testcases/test_add_one.py"])
            self.assertEqual((project / "json_testcases" / "add_one.json").read_text(), "[[1], 2]\n")
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_store_made_here_starts_empty_though_the_organ_would_start_one_from_what_the_tree_ships_with(self):
        directory = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        try:
            self.assertEqual(tool._store(directory / "empty.sqlite").lookup_rules("python"), [])
            shipped = tool._shipped_store(directory / "shipped.sqlite").lookup_rules("python")
            self.assertTrue(shipped)                                             # the tree does ship with some
            again = tool._shipped_store(directory / "shipped.sqlite").lookup_rules("python")
            self.assertEqual(len(again), len(shipped))
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_program_becomes_a_project_of_its_own_without_its_answer(self):
        directory = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        try:
            root = write_benchmark(directory / "bench")
            project = tool.build_project(root, "at_most", directory / "projects")
            files = sorted(path.relative_to(project).as_posix() for path in project.rglob("*") if path.is_file())
            self.assertEqual(files, ["conftest.py", "python_programs/at_most.py", "python_programs/node.py",
                                     "python_testcases/load_testdata.py", "python_testcases/node.py",
                                     "python_testcases/test_at_most.py"])
            self.assertEqual((project / "python_programs" / "at_most.py").read_text(),
                             (root / "python_programs" / "at_most.py").read_text())
            (project / "left_over.txt").write_text("from an earlier run")
            tool.build_project(root, "at_most", directory / "projects")
            self.assertFalse((project / "left_over.txt").exists())                 # built again from nothing
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_the_same_code_is_the_same_whatever_its_blank_lines(self):
        self.assertTrue(tool._same_code("a = 1\n\n\nb = 2  \n", "\na = 1\nb = 2\n"))
        self.assertFalse(tool._same_code("a = 1\nb = 2\n", "a = 1\nb = 3\n"))
        self.assertFalse(tool._same_code("if x:\n    a = 1\n", "if x:\n  a = 1\n"))    # indentation is code

    def test_the_benchmark_hash_follows_the_files_that_matter(self):
        directory = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-test-"))
        try:
            root = write_benchmark(directory / "bench")
            first = tool.benchmark_sha256(root, ["add_one", "at_most"])
            self.assertEqual(first, tool.benchmark_sha256(root, ["at_most", "add_one"]))
            self.assertNotEqual(first, tool.benchmark_sha256(root, ["add_one"]))
            (root / "python_testcases" / "test_add_one.py").write_text("def test_add_one():\n    assert True\n")
            self.assertNotEqual(first, tool.benchmark_sha256(root, ["add_one", "at_most"]))
        finally:
            shutil.rmtree(directory, ignore_errors=True)


class WithTheRealOrganAndTheRealTests(unittest.TestCase):
    """Three small programs, the tree's own store and its own test oracle. Slow (it runs pytest in
    copies of each project), so everything is measured once and then looked at."""

    @classmethod
    def setUpClass(cls):
        cls.dir = pathlib.Path(tempfile.mkdtemp(prefix="one-fix-real-"))
        cls.root = write_benchmark(cls.dir / "bench", names=("add_one", "at_most", "at_least", "capped"))
        cls.measured = tool.measure(cls.root, ["add_one", "at_least", "at_most", "capped"], cls.dir / "work", timeout_s=20)
        cls.summary = tool.summarise(cls.measured)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_the_real_oracle_fails_the_buggy_versions_countably_and_passes_the_published_fixes(self):
        for name, row in self.measured["census"].items():
            self.assertTrue(row["can_be_a_target"], name)
            self.assertTrue(row["buggy_fails_in_a_way_the_oracle_counts"], name)
            self.assertEqual(row["buggy"]["test_count"], 1)
            self.assertTrue(row["with_the_published_fix"]["passed"])

    def test_what_the_organ_stores_it_recalls_on_the_same_bug(self):
        self.assertTrue(self.measured["taught"])                     # at least one of three one-token fixes is accepted as a lesson
        for setting in tool.SETTINGS:
            again = self.measured["outcomes"]["same_bug_again"][setting]
            self.assertEqual(sorted(again), self.measured["taught"])
            for name, outcome in again.items():
                self.assertTrue(outcome["repaired"], (setting, name))
                self.assertEqual(outcome["from_the_lesson_of"], [name])
                self.assertGreaterEqual(outcome["oracle_calls"], 1)                # the organ asked the tests before it answered

    def test_every_recall_was_about_the_right_number_of_lessons(self):
        taught = self.measured["taught"]
        for setting in tool.SETTINGS:
            for teacher, row in self.measured["outcomes"]["one_fix"][setting].items():
                for target, outcome in row.items():
                    self.assertNotEqual(teacher, target)
                    self.assertEqual((outcome["lessons_given"], outcome["rules_held"], outcome["rules_refused_on_the_way"]), (1, 1, 0))
            for target, outcome in self.measured["outcomes"]["all_other_fixes"][setting].items():
                self.assertEqual(outcome["lessons_given"], len([t for t in taught if t != target]))
                self.assertLessEqual(outcome["rules_held"], outcome["lessons_given"])
                self.assertEqual(outcome["rules_refused_on_the_way"], 0)
                if outcome["repaired"]:
                    self.assertNotIn(target, outcome["from_the_lesson_of"])

    def test_what_the_tree_ships_with_was_asked_and_held_no_lesson_from_here(self):
        self.assertGreater(self.measured["python_rules_the_tree_ships_with"], 0)
        for setting in tool.SETTINGS:
            shipped = self.measured["outcomes"]["already_held"][setting]
            self.assertEqual(sorted(shipped), sorted(self.measured["targets"]))
            for outcome in shipped.values():
                self.assertEqual(outcome["lessons_given"], 0)
                self.assertEqual(outcome["rules_held"], self.measured["python_rules_the_tree_ships_with"])

    def test_the_summary_adds_up(self):
        self.assertEqual(self.summary["programs"], 4)
        self.assertEqual(self.summary["fixes_the_organ_stored_as_lessons"]
                         + sum(len(v) for v in self.summary["fixes_the_organ_refused_to_store"].values()), 4)
        for setting in tool.SETTINGS:
            block = self.summary["settings"][setting]
            pairs = self.measured["outcomes"]["one_fix"][setting]
            self.assertEqual(block["one_fix_then_another_bug"]["pairs_tried"], sum(len(row) for row in pairs.values()))
            self.assertEqual(block["one_fix_then_another_bug"]["pairs_repaired"],
                             sum(1 for row in pairs.values() for o in row.values() if o["repaired"]))
            self.assertEqual(block["same_bug_again"]["repaired"], block["same_bug_again"]["of"])


if __name__ == "__main__":
    unittest.main()
