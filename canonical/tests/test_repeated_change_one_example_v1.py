"""The measure of one example of a repeated change: what counts as a change, as right, as not the
developers'; how the questions are put; how the organ's refusals, failures and slowness are told apart."""
import json
import time

import pytest

from canonical.tools import repeated_change_one_example_measure_v1 as measure

BEFORE = "import six\n\n\ndef f(a):\n    x = six.text_type(a)\n    return x\n"
AFTER = "def f(a):\n    x = str(a)\n    return x\n"


def lines(text):
    return measure.statement_lines(text)


# ----------------------------------------------------------------------------- what a change is
def test_one_replaced_line_is_one_change():
    assert measure.changes(["a = 1", "b = 2"], ["a = 1", "b = 3"]) == {(1, ("b = 2",), ("b = 3",))}


def test_a_run_replaced_by_a_run_of_the_same_length_is_taken_line_by_line():
    got = measure.changes(["a = 1", "b = 2", "c = 3"], ["a = 9", "b = 8", "c = 3"])
    assert got == {(0, ("a = 1",), ("a = 9",)), (1, ("b = 2",), ("b = 8",))}


def test_lines_taken_out_or_put_in_are_one_change_with_their_place():
    assert measure.changes(["a = 1", "b = 2"], ["a = 1"]) == {(1, ("b = 2",), ())}
    assert measure.changes(["a = 1"], ["z = 0", "a = 1"]) == {(0, (), ("z = 0",))}


def test_the_same_lines_are_no_change():
    assert measure.changes(["a = 1"], ["a = 1"]) == set()


def test_layout_and_comments_are_not_changes():
    assert lines("x = (1 +\n     2)  # why\n") == lines("x = 1 + 2\n")


def test_a_text_python_cannot_read_has_no_lines():
    assert measure.statement_lines("print 'old python'\n") is None


def test_only_import_lines_are_told_apart():
    assert measure.only_imports((0, ("import six",), ()))
    assert measure.only_imports((0, ("from a import b",), ("from a import c",)))
    assert not measure.only_imports((0, ("x = six.text_type(a)",), ("x = str(a)",)))
    assert not measure.only_imports((0, ("import six",), ("x = 1",)))


# ----------------------------------------------------------------------------- the score
def test_the_developers_own_text_is_right_everywhere():
    one = measure.score(BEFORE, AFTER, AFTER)
    assert one["developers_changes"] == 2 and one["developers_changes_not_imports"] == 1
    assert one["right"] == 2 and one["right_not_imports"] == 1 and one["not_what_the_developers_did"] == 0
    assert one["the_whole_file_as_the_developers_left_it"] and one["all_but_imports_as_the_developers_left_it"]


def test_nothing_made_is_nothing_right_and_nothing_wrong():
    one = measure.score(BEFORE, AFTER, None)
    assert (one["organ_changes"], one["right"], one["not_what_the_developers_did"]) == (0, 0, 0)
    assert not one["the_whole_file_as_the_developers_left_it"] and not one["all_but_imports_as_the_developers_left_it"]


def test_the_code_changed_and_the_import_left_is_all_but_imports():
    got = "import six\n\n\ndef f(a):\n    x = str(a)\n    return x\n"
    one = measure.score(BEFORE, AFTER, got)
    assert one["right"] == 1 and one["right_not_imports"] == 1 and one["not_what_the_developers_did"] == 0
    assert one["all_but_imports_as_the_developers_left_it"] and not one["the_whole_file_as_the_developers_left_it"]


def test_a_change_the_developers_did_not_make_is_counted_against_the_organ():
    got = "import six\n\n\ndef f(a):\n    x = str(a)\n    return str(x)\n"
    one = measure.score(BEFORE, AFTER, got)
    assert one["right"] == 1 and one["not_what_the_developers_did"] == 1
    assert not one["all_but_imports_as_the_developers_left_it"]


def test_the_right_line_changed_the_wrong_way_is_not_right():
    got = "import six\n\n\ndef f(a):\n    x = repr(a)\n    return x\n"
    one = measure.score(BEFORE, AFTER, got)
    assert one["right"] == 0 and one["not_what_the_developers_did"] == 1


def test_an_organ_text_that_cannot_be_read_is_said_and_counts_as_nothing():
    one = measure.score(BEFORE, AFTER, "def f(:\n")
    assert one["organ_text_cannot_be_read"] and one["organ_changes"] == 0


def test_a_file_that_cannot_be_read_is_not_scored():
    with pytest.raises(ValueError):
        measure.score("print 'x'\n", AFTER, AFTER)


def test_two_files_are_put_together_or_not_at_all():
    assert measure.put_together("a = 1\n", "b = 2\n") == "a = 1\n\n\nb = 2\n"
    assert measure.put_together("a = 1", "b = 2\n") == "a = 1\n\n\nb = 2\n"
    assert measure.put_together("a = (\n", "b = 2\n") is None


def test_empty_lines_are_not_lines():
    assert lines("import six\n\n\ndef f(a):\n    return a\n") == ["import six", "def f(a):", "    return a"]


# ----------------------------------------------------------------------------- the questions
def files(count):
    return [{"path": f"m{i}.py", "before": f"import six\nv{i} = six.text_type({i})\nkeep = {i}\n", "after": f"v{i} = str({i})\nkeep = {i}\n"} for i in range(count)]


def knows_the_answer(pool):
    answers = {item["before"]: item["after"] for item in pool}
    return lambda target, before, after: (answers[target], None)


def test_every_file_is_the_example_for_every_other_and_every_two_for_every_third():
    pool = files(4)
    row = measure.one_pull_request(pool, organ=knows_the_answer(pool))
    assert row["itself"]["asked"] == 4 and row["one_example"]["asked"] == 4 * 3 and row["two_examples"]["asked"] == 6 * 2
    assert row["one_example"]["edited"] == 12 and row["one_example"]["right_not_imports"] == row["one_example"]["developers_changes_not_imports"] == 12
    assert row["one_example"]["the_whole_file_as_the_developers_left_it"] == 12 and row["one_example"]["not_what_the_developers_did"] == 0
    assert [item["path"] for item in row["per_file_as_the_example"]] == ["m0.py", "m1.py", "m2.py", "m3.py"]
    assert all(item["asked"] == 3 and item["right_not_imports"] == 3 for item in row["per_file_as_the_example"])


def test_two_examples_are_given_as_one_text_in_the_order_of_the_files():
    pool, seen = files(3), []

    def organ(target, before, after):
        seen.append((before, after))
        return None, "refused: no"
    measure.one_pull_request(pool, organ=organ)
    assert (measure.put_together(pool[0]["before"], pool[1]["before"]), measure.put_together(pool[0]["after"], pool[1]["after"])) in seen


def test_two_examples_can_be_left_out():
    row = measure.one_pull_request(files(3), organ=lambda *a: (None, "refused: no"), two_examples=False)
    assert row["two_examples"]["asked"] == 0 and row["one_example"]["asked"] == 6


def test_a_refusal_is_counted_with_its_reason_and_makes_nothing():
    row = measure.one_pull_request(files(3), organ=lambda *a: (None, "refused: nothing in the file has the form the example changed (x -> y)"))
    one = row["one_example"]
    assert one["edited"] == 0 and one["right"] == 0 and one["developers_changes_not_imports"] == 6
    assert one["why_not"] == {"refused: nothing in the file has the form the example changed": 6}


def test_a_wrong_edit_is_an_edit_with_changes_that_are_not_the_developers():
    row = measure.one_pull_request(files(3), organ=lambda target, before, after: (target.replace("keep", "kept"), None), two_examples=False)
    one = row["one_example"]
    assert one["edited"] == 6 and one["right"] == 0 and one["not_what_the_developers_did"] == 6 and one["edited_and_every_change_right"] == 0


def test_examples_that_cannot_be_put_together_are_counted_and_make_nothing(monkeypatch):
    pool = files(3)
    whole = measure.put_together
    monkeypatch.setattr(measure, "put_together", lambda first, second: None if pool[1]["before"] in (first, second) or pool[1]["after"] in (first, second) else whole(first, second))
    row = measure.one_pull_request(pool, organ=knows_the_answer(pool))
    assert row["two_examples_could_not_be_put_together"] == 2 and row["two_examples"]["asked"] == 3 and row["two_examples"]["edited"] == 1
    assert row["two_examples"]["why_not"]["refused: the two examples could not be put together as one text"] == 2


def test_elsewhere_puts_every_foreign_example_to_every_file():
    pool, foreign, asked = files(3), files(5)[3:], []

    def organ(target, before, after):
        asked.append((target, before))
        return target.replace("keep", "kept"), None
    total = measure.elsewhere(pool, foreign, organ=organ)
    assert total["asked"] == 6 and len(set(asked)) == 6 and total["not_what_the_developers_did"] == 6 and total["right"] == 0


def pulls():
    return [{"name": "a/b#1", "kind": "k1", "query": "q1", "title": "t1", "files": files(3)},
            {"name": "c/d#2", "kind": "k2", "query": "q2", "title": "t2", "files": files(6)[3:]},
            {"name": "e/f#3", "kind": "k2", "query": "q2", "title": "t3", "files": files(9)[6:]}]


def test_the_foreign_examples_come_only_from_pull_requests_of_another_phrase():
    given = pulls()
    befores = {pull["name"]: {item["before"] for item in pull["files"]} for pull in given}
    used = {}

    def organ(target, before, after):
        home = next(name for name, own in befores.items() if target in own)
        source = next((name for name, own in befores.items() if before in own), None)
        if source is not None and source != home:
            used.setdefault(home, set()).add(source)
        return None, "refused: no"
    measure.measure(given, organ=organ, two_examples=False)
    assert used == {"a/b#1": {"c/d#2", "e/f#3"}, "c/d#2": {"a/b#1"}, "e/f#3": {"a/b#1"}}


def test_the_summary_adds_the_pull_requests_up_and_gives_the_shares():
    given = pulls()
    everything = [item for pull in given for item in pull["files"]]
    answers = {item["before"]: item["after"] for item in everything}
    home = {item["before"]: pull["name"] for pull in given for item in pull["files"]}

    def organ(target, before, after):          # right inside a/b#1, a refusal inside the others, a wrong edit from elsewhere
        source = home.get(before)
        if source is None or source == home[target]:
            return (answers[target], None) if home[target] == "a/b#1" else (None, "refused: no")
        return target.replace("keep", "kept"), None
    per_pull = measure.measure(given, organ=organ)
    summary = measure.summarise(per_pull)
    assert summary["pull_requests"] == 3 and summary["files"] == 9
    one = summary["one_example"]
    assert one["asked"] == 18 and one["edited"] == 6 and one["share_edited"] == round(6 / 18, 4)
    assert one["of_the_developers_changes_made"] == round(6 / 18, 4) and one["of_the_organs_changes_right"] == 1.0
    assert one["why_not"] == {"refused: no": 12, "edited": 6}
    assert summary["elsewhere"]["asked"] == 3 * 2 + 3 * 1 + 3 * 1 and summary["elsewhere"]["of_the_organs_changes_right"] == 0.0
    assert summary["pull_requests_where_one_example_made_any_of_the_developers_changes"] == 1
    assert summary["by_kind_of_change"]["k1"]["one_example"]["of_the_developers_changes_made"] == 1.0
    assert summary["by_kind_of_change"]["k2"]["one_example"]["of_the_developers_changes_made"] == 0.0
    assert summary["by_kind_of_change"]["k2"]["pull_requests"] == 2


def test_a_share_of_nothing_is_not_a_number():
    assert measure.rates(measure._empty())["of_the_organs_changes_right"] is None


def test_like_refusals_are_counted_together():
    first = measure.reason_class("refused: line 12 of the example was changed, but the same code was left alone")
    second = measure.reason_class("refused: line 7 of the example was changed, but the same code was left alone")
    assert first == second and "N" in first
    assert measure.reason_class("refused: the change uses 'six', which the file does not define") == measure.reason_class("refused: the change uses 'os', which the file does not define")
    assert measure.reason_class(None) == "edited"


# ----------------------------------------------------------------------------- the organ itself
EXAMPLE_BEFORE = "class T:\n    def test_a(self):\n        self.assertEquals(f(1), 2)\n\n    def test_b(self):\n        self.assertEquals(g(), [])\n"
EXAMPLE_AFTER = EXAMPLE_BEFORE.replace("assertEquals", "assertEqual")
TARGET_BEFORE = "class U:\n    def test_c(self):\n        value = h()\n        self.assertEquals(value, 'x')  # kept\n"


def test_the_organ_repeats_a_renamed_method_from_one_example():
    got, why = measure.the_organ(TARGET_BEFORE, EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert why is None and "# kept" in got
    one = measure.score(TARGET_BEFORE, TARGET_BEFORE.replace("assertEquals", "assertEqual"), got)
    assert one["right"] == 1 and one["not_what_the_developers_did"] == 0 and one["the_whole_file_as_the_developers_left_it"]


def test_the_organs_refusal_is_given_in_its_words():
    got, why = measure.the_organ("x = 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert got is None and why.startswith("refused: nothing in the file has the form the example changed")


def test_a_failure_of_the_organ_is_not_a_refusal(monkeypatch):
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ
    monkeypatch.setattr(organ, "edit_by_example", lambda *a: (_ for _ in ()).throw(KeyError("broken")))
    assert measure.the_organ("x = 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER) == (None, "error: KeyError")


def test_an_organ_that_takes_too_long_is_stopped_and_said_so(monkeypatch):
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ
    monkeypatch.setattr(measure, "CALL_LIMIT_S", 1)
    monkeypatch.setattr(organ, "edit_by_example", lambda *a: time.sleep(5))
    started = time.time()
    assert measure.the_organ("x = 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER) == (None, "stopped: more than 1 s")
    assert time.time() - started < 4


USED_ANOTHER_WAY = ("class U:\n    def test_c(self):\n        self.assertEquals(h(), 'x')\n\n"
                    "    def test_d(self):\n        self.assertEquals(h(), 'x', 'said when it fails')\n")


def test_a_use_the_example_did_not_show_makes_the_organ_refuse_the_file_or_leave_that_use_alone():
    """The check that a new callee takes the arguments of the call site, and the two ways through it.

    `assertEquals` is a name the standard library kept for `assertEqual`, so a call of another shape
    is no longer refused: the callee is the same function and takes what it always took.  The
    refusal this test was written for is still what happens to a change between two *different*
    names, and `test_a_rename_between_two_different_names_is_still_refused_for_another_call_shape`
    holds it.
    """
    whole, why = measure.the_organ(USED_ANOTHER_WAY, EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert why is None
    assert "self.assertEqual(h(), 'x', 'said when it fails')" in whole
    got, why = measure.the_organ_leaving_the_rest(USED_ANOTHER_WAY, EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert why is None
    assert got == whole


def test_a_rename_between_two_different_names_is_still_refused_for_another_call_shape():
    """`yaml.load` -> `yaml.safe_load` has the same shape as an alias and must keep being refused."""
    before = "import yaml\n\n\ndef settings(h):\n    return yaml.load(h)\n"
    after = before.replace("load(", "safe_load(")
    target = ("import yaml\n\n\ndef mine(h):\n    return yaml.load(h, Loader=yaml.FullLoader)\n")
    whole, why = measure.the_organ(target, before, after)
    assert whole is None
    assert "called with 1 argument and the keyword Loader" in why, why
    assert "may not work with the new code" in why, why


def test_the_alias_exception_is_only_for_a_rename_and_only_for_a_kept_name():
    """Two guards on one exemption: the shape must be a rename, and the pair must be a kept name."""
    from canonical.swe_kernel.taught_actions import kept_under_an_old_name_v1 as kept
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ
    assert kept.alias_of("assertEquals", "assertEqual")
    assert kept.alias_of("assertRaisesRegexp", "assertRaisesRegex")
    assert not kept.alias_of("load", "safe_load")
    reshaped_before = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEquals(f(1), 2)\n"
    reshaped_after = ("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n"
                      "        self.assertEqual(f(1), 2, 'why')\n")
    rules = organ.learn(reshaped_before, reshaped_after)
    assert all(organ.kept_alias(rule) is None for rule in rules)


def test_leaving_the_rest_changes_what_the_whole_file_way_changes_when_every_use_was_shown():
    assert measure.the_organ_leaving_the_rest(TARGET_BEFORE, EXAMPLE_BEFORE, EXAMPLE_AFTER) == measure.the_organ(TARGET_BEFORE, EXAMPLE_BEFORE, EXAMPLE_AFTER)


def test_leaving_the_rest_still_refuses_a_file_with_nothing_of_that_form():
    got, why = measure.the_organ_leaving_the_rest("x = 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert got is None and why.startswith("refused: nothing in the file has the form the example changed")


SHOWN_ON_ONE_OBJECT = ("class W:\n    def stop(self):\n        if self.thread.isAlive():\n            self.thread.join()\n",
                       "class W:\n    def stop(self):\n        if self.thread.is_alive():\n            self.thread.join()\n")
ON_ANOTHER_OBJECT = "def wait(t):\n    while t.isAlive():\n        pass\n"


def test_with_every_try_kept_the_wider_reading_of_one_example_is_used():
    strict, why = measure.the_organ(ON_ANOTHER_OBJECT, *SHOWN_ON_ONE_OBJECT)
    assert strict is None and why.startswith("refused: nothing in the file has the form the example changed")
    got, why = measure.the_organ_with_every_try_kept(ON_ANOTHER_OBJECT, *SHOWN_ON_ONE_OBJECT)
    assert why is None and "while t.is_alive():" in got


def test_with_every_try_kept_a_use_the_example_did_not_show_is_changed_too():
    got, why = measure.the_organ_with_every_try_kept(USED_ANOTHER_WAY, EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert why is None and "assertEquals" not in got and "self.assertEqual(h(), 'x', 'said when it fails')" in got


def test_with_every_try_kept_a_file_with_nothing_of_that_form_is_still_refused():
    got, why = measure.the_organ_with_every_try_kept("x = 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert got is None and why.startswith("refused: nothing in the file has the form the example changed, however widely")


# ----------------------------------------------------------------------------- which files are used
def test_a_file_is_used_only_when_python_reads_it_and_its_code_changed():
    assert measure.usable(BEFORE, AFTER)
    assert not measure.usable("print 'x'\n", "print('x')\n")
    assert not measure.usable("x = (1 +\n 2)\n", "x = 1 + 2  # same code\n")
    assert not measure.usable(None, AFTER) and not measure.usable(BEFORE, None)
    assert not measure.usable("x = 1\n" + "#" * measure.MAX_BYTES, "x = 2\n")


def test_the_draw_is_the_same_every_time_and_loses_no_file():
    paths = [f"p{i}.py" for i in range(30)]
    assert measure.draw(paths) == measure.draw(list(reversed(paths))) and sorted(measure.draw(paths)) == sorted(paths)
    assert measure.draw(paths) != sorted(paths) and measure.draw(paths, seed=1) != measure.draw(paths)


def test_what_is_recorded_of_a_pull_request_has_no_text_and_can_be_checked():
    kept = measure.without_texts([{"name": "a/b#1", "repo": "a/b", "number": 1, "before_at": "s1", "after_at": "s2", "files": files(2)}])
    assert kept[0]["before_at"] == "s1" and "before" not in kept[0]["files"][0] and len(kept[0]["files"][0]["before_sha256"]) == 64


# ----------------------------------------------------------------------------- the same files again
def recorded_and_github():
    pool = files(2)
    pull = {"name": "a/b#1", "repo": "a/b", "number": 1, "title": "t", "before_at": "s1", "after_at": "s2", "kind": "k", "query": "q", "files": pool}
    recorded = measure.without_texts([pull])
    github = {}
    for item in pool:
        github[f"repos/a/b/contents/{item['path']}?ref=s1"] = item["before"]
        github[f"repos/a/b/contents/{item['path']}?ref=s2"] = item["after"]
    return pull, recorded, github


def test_the_files_a_record_names_are_fetched_again_and_are_the_same(monkeypatch):
    pull, recorded, github = recorded_and_github()
    asked = []
    monkeypatch.setattr(measure, "gh", lambda path, raw=False: asked.append((path, raw)) or github.get(path))
    again = measure.fetched_again(recorded, say=lambda line: None)
    assert again == [{**{key: value for key, value in pull.items() if key != "files"}, "files": pull["files"]}]
    assert all(raw for _, raw in asked) and len(asked) == 4
    assert measure.without_texts(again) == recorded


def test_a_text_that_is_not_the_recorded_one_stops_the_fetching(monkeypatch):
    _, recorded, github = recorded_and_github()
    changed = dict(github, **{"repos/a/b/contents/m1.py?ref=s2": "v1 = repr(1)\n"})
    monkeypatch.setattr(measure, "gh", lambda path, raw=False: changed.get(path))
    with pytest.raises(RuntimeError, match="a/b#1 m1.py: the text after the change is not the one the record names"):
        measure.fetched_again(recorded, say=lambda line: None)


def test_a_file_that_is_gone_stops_the_fetching(monkeypatch):
    _, recorded, github = recorded_and_github()
    gone = {path: text for path, text in github.items() if path != "repos/a/b/contents/m0.py?ref=s1"}
    monkeypatch.setattr(measure, "gh", lambda path, raw=False: gone.get(path))
    with pytest.raises(RuntimeError, match="m0.py: the text before the change"):
        measure.fetched_again(recorded, say=lambda line: None)


def test_fetching_again_from_the_command_line_writes_the_pull_requests_with_their_texts(tmp_path, monkeypatch, capsys):
    pull, recorded, github = recorded_and_github()
    record, out = tmp_path / "record.json", tmp_path / "pulls.json"
    record.write_text(json.dumps({"pull_requests": recorded}))
    monkeypatch.setattr(measure, "gh", lambda path, raw=False: github.get(path))
    monkeypatch.setattr(measure, "collect", lambda *a, **k: pytest.fail("the search must not be made"))
    assert measure.main(["--collect", str(out), "--as-recorded-in", str(record)]) == 0
    assert json.loads(out.read_text())[0]["files"] == pull["files"] and "1 pull requests, 2 files" in capsys.readouterr().out
