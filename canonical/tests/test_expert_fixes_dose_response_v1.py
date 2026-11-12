"""The dose of expert fixes: which pairs are read, how the doses are drawn, what one question about
one bug writes down, what the counts come to, and how shards are put together."""
import json
import pathlib

import pytest

from canonical.runtime import edit_kind_learning_v1 as kinds
from canonical.tools import expert_fixes_dose_response_measure_v1 as measure

MINUS_TO_PLUS = ("x = int(input())\ny = int(input())\nprint(x - y)\n", "x = int(input())\ny = int(input())\nprint(x + y)\n")
LESS_TO_LESS_EQUAL = ("n = int(input())\nif n < 3:\n    print('a')\n", "n = int(input())\nif n <= 3:\n    print('a')\n")
ONE_TO_ZERO = ("s = input()\nprint(s[1])\n", "s = input()\nprint(s[0])\n")
NOTHING = ("print(1)\n", "print(1)\n")
PAIRS = {"condefects/t1/1": MINUS_TO_PLUS, "condefects/t2/2": LESS_TO_LESS_EQUAL, "condefects/t3/3": ONE_TO_ZERO, "condefects/t4/4": NOTHING}

BUG = {"name": "Python/900", "number": 900, "entry": "f", "bug_type": "operator misuse",
       "buggy": "def f(a, b):\n    return a - b\n", "fixed": "def f(a, b):\n    return a + b\n",
       "test": "def check(f):\n    assert f(1, 2) == 3\n\ncheck(f)\n"}


def passing(*programs):
    """A screen and a fresh interpreter that pass exactly these programs, and count what they are given."""
    seen = []

    def is_one(program):
        return any(kinds.same_program(program, wanted) for wanted in programs)

    def check(given):
        seen.extend(given)
        return next((index for index, program in enumerate(given) if is_one(program)), None)
    return check, is_one, seen


def write_pair(root, task, submission, faulty, correct):
    where = root / "Code" / task / "Python" / submission
    where.mkdir(parents=True)
    (where / "faultyVersion.py").write_text(faulty, encoding="utf-8")
    if correct is not None:
        (where / "correctVersion.py").write_text(correct, encoding="utf-8")


# ----------------------------------------------------------------------------- the lessons
def test_the_pairs_are_read_by_task_and_submission_in_order(tmp_path):
    write_pair(tmp_path, "abc2_b", "77", *LESS_TO_LESS_EQUAL)
    write_pair(tmp_path, "abc1_a", "12", *MINUS_TO_PLUS)
    (tmp_path / "Code" / "abc1_a" / "Java" / "5").mkdir(parents=True)
    (tmp_path / "Code" / "abc1_a" / "Java" / "5" / "faultyVersion.java").write_text("class A {}")
    pairs, unreadable = measure.condefects_pairs(tmp_path)
    assert list(pairs) == ["condefects/abc1_a/12", "condefects/abc2_b/77"] and unreadable == []
    assert pairs["condefects/abc1_a/12"] == MINUS_TO_PLUS


def test_a_pair_that_cannot_be_read_is_named_and_left_out(tmp_path):
    write_pair(tmp_path, "abc1_a", "1", *MINUS_TO_PLUS)
    write_pair(tmp_path, "abc1_a", "2", "print(1)\n", None)
    write_pair(tmp_path, "abc1_a", "3", "print(1)\n", "print(2)\n")
    (tmp_path / "Code" / "abc1_a" / "Python" / "3" / "correctVersion.py").write_bytes(b"\xff\xfe\x00bad")
    pairs, unreadable = measure.condefects_pairs(tmp_path)
    assert list(pairs) == ["condefects/abc1_a/1"] and unreadable == ["condefects/abc1_a/2", "condefects/abc1_a/3"]


def test_the_hash_of_the_pairs_follows_their_text_and_not_their_order():
    turned = dict(reversed(list(PAIRS.items())))
    assert measure.pairs_sha256(PAIRS) == measure.pairs_sha256(turned)
    changed = dict(PAIRS, **{"condefects/t1/1": (MINUS_TO_PLUS[0], MINUS_TO_PLUS[1] + "\n")})
    assert measure.pairs_sha256(changed) != measure.pairs_sha256(PAIRS)


def test_an_order_holds_every_name_once_and_is_the_seeds():
    names = [f"n{i}" for i in range(40)]
    assert sorted(measure.order_of(names, 1)) == sorted(names)
    assert measure.order_of(names, 1) == measure.order_of(list(reversed(names)), 1)
    assert measure.order_of(names, 1) != measure.order_of(names, 2) and measure.order_of(names, 1) != sorted(names)


def test_every_pair_is_shown_once_and_one_that_changes_nothing_teaches_nothing():
    memory = measure.taught(PAIRS)
    assert sorted(memory.lessons) == ["condefects/t1/1", "condefects/t2/2", "condefects/t3/3"] and memory.taught_nothing == ["condefects/t4/4"]


def test_backwards_shows_the_correct_program_first():
    forwards, backwards = measure.taught(PAIRS), measure.taught(PAIRS, backwards=True)
    plus_made_minus = "def f(a, b):\n    return a + b\n"
    assert any(kinds.same_program(c, BUG["buggy"]) for c, _, _ in kinds.ranking(backwards.votes(plus_made_minus)))
    assert not any(kinds.same_program(c, BUG["buggy"]) for c, _, _ in kinds.ranking(forwards.votes(plus_made_minus)))


# ----------------------------------------------------------------------------- the doses
def names(count):
    return [f"condefects/t/{i:03d}" for i in range(count)]


def test_the_doses_of_one_order_are_nested_and_every_seed_has_its_own():
    everything = names(50)
    asked = measure.doses(everything, everything, sizes=(3, 10, 30), seeds=(1, 2))
    assert [question["label"] for question in asked] == ["3/1", "10/1", "30/1", "3/2", "10/2", "30/2", "all"]
    by = {question["label"]: question["only"] for question in asked}
    assert by["3/1"] == by["10/1"][:3] and by["10/1"] == by["30/1"][:10] and by["3/1"] != by["3/2"]
    assert by["3/1"] == measure.order_of(everything, 1)[:3] and sorted(by["all"]) == everything
    assert [question["shown"] for question in asked] == [3, 10, 30, 3, 10, 30, 50]


def test_a_dose_counts_every_pair_shown_and_asks_only_with_those_that_taught():
    everything = names(20)
    order = measure.order_of(everything, 7)
    teaching = [name for name in everything if name not in order[:2]]
    asked = measure.doses(everything, teaching, sizes=(5,), seeds=(7,))
    assert asked[0]["shown"] == 5 and asked[0]["only"] == order[2:5]
    assert asked[1]["shown"] == 20 and len(asked[1]["only"]) == 18


def test_a_size_as_large_as_everything_is_left_to_all_and_all_can_be_left_out():
    everything = names(10)
    assert [q["label"] for q in measure.doses(everything, everything, sizes=(3, 10, 30), seeds=(1,))] == ["3/1", "all"]
    assert [q["label"] for q in measure.doses(everything, everything, sizes=(3,), seeds=(1,), with_all=False)] == ["3/1"]


# ----------------------------------------------------------------------------- one question
def bench_for(*programs):
    check, accepted, seen = passing(*programs)
    return measure.hef.Bench(BUG, check, accepted), seen


def test_the_lesson_that_holds_the_change_repairs_the_bug_and_the_others_do_not():
    memory = measure.taught(PAIRS)
    votes = memory.votes(BUG["buggy"])
    bench, _ = bench_for(BUG["fixed"])
    with_it = measure.one_question(bench, votes, ["condefects/t1/1"], 200, None, {})
    assert with_it["repaired"] and with_it["is_the_published_fix"] and with_it["right_as_far_as_checked"]
    assert with_it["published_fix_rank"] == with_it["first_pass_rank"] and with_it["lessons"] == 1 and with_it["candidates"] >= 1
    without = measure.one_question(bench, votes, ["condefects/t2/2", "condefects/t3/3"], 200, None, {})
    assert not without["repaired"] and without["first_pass_rank"] is None and without["published_fix_rank"] is None
    assert not without["right_as_far_as_checked"] and not without["is_the_published_fix"]


def test_no_lessons_is_no_candidates():
    bench, seen = bench_for(BUG["fixed"])
    row = measure.one_question(bench, measure.taught(PAIRS).votes(BUG["buggy"]), [], 200, None, {})
    assert (row["lessons"], row["candidates"], row["repaired"], row["published_fix_rank"]) == (0, 0, False, None) and seen == []


def test_the_budget_stops_the_running_but_not_the_looking():
    memory = measure.taught(PAIRS)
    votes = memory.votes(BUG["buggy"])
    everything = sorted(memory.lessons)
    bench, _ = bench_for(BUG["fixed"])
    whole = measure.one_question(bench, votes, everything, 200, None, {})
    place = whole["published_fix_rank"]
    assert whole["repaired"] and place is not None
    if place > 1:
        fresh, seen = bench_for(BUG["fixed"])
        short = measure.one_question(fresh, votes, everything, place - 1, None, {})
        assert not short["repaired"] and short["published_fix_rank"] == place and len(seen) == place - 1


def test_the_published_fix_at_the_third_place_needs_a_budget_of_three():
    programs = ["def f(a, b):\n    return a * b", "def f(a, b):\n    return b - a", "def f(a, b):\n    return a + b"]
    votes = {program: {"lesson": (1.0 / (place + 1), "operator")} for place, program in enumerate(programs)}
    check, accepted, seen = passing(BUG["fixed"])
    two = measure.one_question(measure.hef.Bench(BUG, check, accepted), votes, ["lesson"], 2, None, {})
    assert not two["repaired"] and two["published_fix_rank"] == 3 and two["candidates"] == 3 and len(seen) == 2
    check, accepted, seen = passing(BUG["fixed"])
    three = measure.one_question(measure.hef.Bench(BUG, check, accepted), votes, ["lesson"], 3, None, {})
    assert three["repaired"] and three["first_pass_rank"] == 3 and three["right_as_far_as_checked"] and len(seen) == 3
    assert measure.one_question(measure.hef.Bench(BUG, check, accepted), votes, ["another lesson"], 3, None, {})["candidates"] == 0


TWO_PLACES = dict(BUG, buggy="def f(a, b):\n    if a < b:\n        return a - b\n    return b\n",
                  fixed="def f(a, b):\n    if a < b:\n        return a + b\n    return b\n")


def test_a_candidate_that_passes_and_is_not_the_published_fix_is_repaired_and_not_right():
    memory = measure.taught(PAIRS)
    votes = memory.votes(TWO_PLACES["buggy"])
    ranked = [c for c, _, _ in kinds.ranking(votes) if kinds.is_a_program(c)]
    assert any(kinds.same_program(c, TWO_PLACES["fixed"]) for c in ranked)
    other = next(c for c in ranked if not kinds.same_program(c, TWO_PLACES["fixed"]))
    check, accepted, _ = passing(other)
    row = measure.one_question(measure.hef.Bench(TWO_PLACES, check, accepted), votes, sorted(memory.lessons), 200, None, {})
    assert row["repaired"] and not row["is_the_published_fix"] and not row["right_as_far_as_checked"]
    assert row["published_fix_rank"] is not None and row["candidates"] >= 2


# ----------------------------------------------------------------------------- one bug
def asked_of(memory, sizes=(1, 2), seeds=(1, 2)):
    return measure.doses(list(PAIRS), memory.lessons, sizes=sizes, seeds=seeds)


def test_every_dose_of_every_memory_is_asked_and_no_candidate_is_run_twice(tmp_path):
    memories = {"forwards": measure.taught(PAIRS), "backwards": measure.taught(PAIRS, backwards=True)}
    questions = {"forwards": asked_of(memories["forwards"]), "backwards": asked_of(memories["backwards"], sizes=(2,), seeds=(1,))}
    check, accepted, seen = passing(BUG["fixed"])
    row = measure.one_bug(BUG, memories, questions, tmp_path / "w", check=check, accepted=accepted)
    assert row["usable"] and all(row["benchmark_holds"].values())
    assert list(row["forwards"]["doses"]) == ["1/1", "2/1", "1/2", "2/2", "all"] and list(row["backwards"]["doses"]) == ["2/1", "all"]
    assert row["forwards"]["doses"]["all"]["repaired"] and not row["backwards"]["doses"]["all"]["repaired"]
    asked_about = seen[2:]                      # after the two programs that show the benchmark holds
    assert len(asked_about) == len(set(asked_about)) == row["candidates_run"]
    assert row["forwards"]["candidates_of_every_lesson"] >= row["forwards"]["doses"]["all"]["candidates"]


def test_a_candidate_two_memories_both_make_is_run_once(tmp_path):
    plus_to_minus = ("p = int(input())\nq = int(input())\nprint(p + q)\n", "p = int(input())\nq = int(input())\nprint(p - q)\n")
    both_ways = {"condefects/t1/1": MINUS_TO_PLUS, "condefects/t5/5": plus_to_minus}
    memories = {"forwards": measure.taught(both_ways), "backwards": measure.taught(both_ways, backwards=True)}
    questions = {arm: measure.doses(list(both_ways), memory.lessons, sizes=(), seeds=()) for arm, memory in memories.items()}
    check, accepted, seen = passing(BUG["fixed"])
    row = measure.one_bug(BUG, memories, questions, tmp_path / "w", check=check, accepted=accepted)
    assert row["forwards"]["doses"]["all"]["repaired"] and row["backwards"]["doses"]["all"]["repaired"]
    asked_about = seen[2:]
    assert len(asked_about) == len(set(asked_about)) == row["candidates_run"]


def test_a_bug_whose_benchmark_does_not_hold_is_not_asked_anything(tmp_path):
    memories = {"forwards": measure.taught(PAIRS)}
    check, accepted, seen = passing(BUG["fixed"], BUG["buggy"])
    row = measure.one_bug(BUG, memories, {"forwards": asked_of(memories["forwards"])}, tmp_path / "w", check=check, accepted=accepted)
    assert not row["usable"] and "forwards" not in row and not row["benchmark_holds"]["buggy_fails_in_the_screen"]


# ----------------------------------------------------------------------------- what it came to
def dose(rank=None, right=False, published=False, place=None, candidates=10):
    return {"lessons": 1, "candidates": candidates, "published_fix_rank": place, "first_pass_rank": rank, "repaired": rank is not None,
            "is_the_published_fix": published, "right_as_far_as_checked": right}


QUESTIONS = {"forwards": [{"label": "3/1", "size": "3", "seed": 1, "shown": 3, "only": ["a", "b"]},
                          {"label": "3/2", "size": "3", "seed": 2, "shown": 3, "only": ["c"]},
                          {"label": "all", "size": "all", "seed": None, "shown": 9, "only": ["a", "b", "c"]}]}
PER_BUG = {
    "Python/1": {"usable": True, "forwards": {"doses": {"3/1": dose(1, True, True, 1), "3/2": dose(), "all": dose(150, True, False, 300, 400)}}},
    "Python/2": {"usable": True, "forwards": {"doses": {"3/1": dose(12, False, False, None), "3/2": dose(7, True, True, 7), "all": dose(2, True, True, 2, 600)}}},
    "Python/3": {"usable": True, "forwards": {"doses": {"3/1": dose(), "3/2": dose(None, False, False, 250), "all": dose(None, False, False, 201, 800)}}},
    "Python/4": {"usable": False},
}


def test_the_counts_are_over_the_usable_bugs_per_order_and_as_a_mean():
    summary = measure.summarise(PER_BUG, QUESTIONS, budget=200)
    assert (summary["bugs"], summary["usable"], summary["not_usable"]) == (4, 3, ["Python/4"])
    three = summary["forwards"]["3"]
    assert three["orders"] == 2 and [cell["repaired"] for cell in three["by_order"]] == [2, 1] and three["repaired_mean"] == 1.5
    assert [cell["right_as_far_as_checked"] for cell in three["by_order"]] == [1, 1] and three["right_as_far_as_checked_mean"] == 1.0
    assert three["by_order"][0]["repaired_within"] == {"1": 1, "10": 1, "100": 2, "200": 2}
    assert three["by_order"][0]["taught_something"] == 2 and three["by_order"][0]["first_pass_rank_median"] == 6.5
    assert [cell["published_fix_among_the_candidates"] for cell in three["by_order"]] == [1, 2]
    assert [cell["published_fix_within_the_budget"] for cell in three["by_order"]] == [1, 1]
    everything = summary["forwards"]["all"]
    assert everything["orders"] == 1 and everything["repaired_mean"] == 2 and everything["by_order"][0]["the_published_fix"] == 1
    assert everything["published_fix_among_the_candidates_mean"] == 3 and everything["published_fix_within_the_budget_mean"] == 1
    assert everything["by_order"][0]["candidates_median"] == 600


def test_the_recorded_questions_have_no_lists_and_still_give_the_same_counts():
    kept = measure.without_the_names(QUESTIONS)
    assert all("only" not in question and len(question["only_sha256"]) == 64 for question in kept["forwards"])
    assert [question["taught_something"] for question in kept["forwards"]] == [2, 1, 3]
    assert measure.summarise(PER_BUG, kept, budget=200) == measure.summarise(PER_BUG, QUESTIONS, budget=200)
    other = measure.without_the_names({"forwards": [dict(QUESTIONS["forwards"][0], only=["a", "x"])]})
    assert other["forwards"][0]["only_sha256"] != kept["forwards"][0]["only_sha256"]


# ----------------------------------------------------------------------------- shards
def shard(names, **changed):
    record = {"schema": measure.SCHEMA, "which": "scored", "shard": "0/2", "code_sha256": {"a": "1"}, "lessons": {"pairs": 4}, "benchmark": {"b": "2"},
              "questions": measure.without_the_names(QUESTIONS), "parameters": {"budget": 200}, "seconds": 5.0, "generated_utc": "2026-11-12T10:00:00Z",
              "per_bug": {name: PER_BUG[name] for name in names}, "summary": {"old": True}}
    record.update(changed)
    return record


def test_shards_are_put_together_in_the_order_of_the_bugs():
    whole = measure.merged([shard(["Python/3", "Python/1"]), shard(["Python/2", "Python/4"], shard="1/2", seconds=7.0, generated_utc="2026-11-12T11:00:00Z")])
    assert list(whole["per_bug"]) == ["Python/1", "Python/2", "Python/3", "Python/4"] and whole["shards"] == ["0/2", "1/2"]
    assert whole["seconds"] == 12.0 and whole["generated_utc"] == "2026-11-12T11:00:00Z" and "summary" not in whole


def test_shards_of_different_code_or_with_the_same_bug_are_refused():
    with pytest.raises(ValueError, match="differ in code_sha256"):
        measure.merged([shard(["Python/1"]), shard(["Python/2"], code_sha256={"a": "other"})])
    with pytest.raises(ValueError, match="in two shards"):
        measure.merged([shard(["Python/1"]), shard(["Python/1"])])


def test_merging_from_the_command_line_writes_the_whole_record_with_its_counts(tmp_path, capsys):
    one, two, out = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "whole.json"
    one.write_text(json.dumps(shard(["Python/1", "Python/3"])))
    two.write_text(json.dumps(shard(["Python/2", "Python/4"], shard="1/2")))
    assert measure.main(["--merge", str(one), str(two), "--out", str(out)]) == 0
    whole = json.loads(out.read_text())
    assert whole["summary"] == json.loads(json.dumps(measure.summarise(PER_BUG, QUESTIONS, budget=200)))
    assert '"repaired_mean": 1.5' in capsys.readouterr().out


# ----------------------------------------------------------------------------- the command line
def test_a_checkout_at_another_commit_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(measure, "checkout_commit", lambda root: "0" * 40)
    with pytest.raises(SystemExit):
        measure.main(["--condefects", str(tmp_path), "--humanevalfix", str(tmp_path / "h.jsonl"), "--work-dir", str(tmp_path / "w"), "--out", str(tmp_path / "o.json")])


def test_measuring_needs_the_lessons_the_bugs_and_a_place_to_work(tmp_path):
    with pytest.raises(SystemExit):
        measure.main(["--out", str(tmp_path / "o.json")])


def test_the_commit_of_a_directory_that_is_no_checkout_is_none(tmp_path):
    assert measure.checkout_commit(tmp_path / "nowhere") is None


def humanevalfix_row(number, buggy_body, fixed_body, checks):
    return {"task_id": f"Python/{number}", "entry_point": "f", "bug_type": "operator misuse", "declaration": "def f(a, b):\n",
            "buggy_solution": buggy_body, "canonical_solution": fixed_body, "test": f"def check(f):\n{checks}\n\ncheck(f)"}


def test_from_the_files_to_the_record_with_the_real_screen(tmp_path, monkeypatch):
    lessons = tmp_path / "ConDefects"
    for number, (faulty, correct) in enumerate(PAIRS.values()):
        write_pair(lessons, f"abc{number}_a", str(number), faulty, correct)
    bugs = tmp_path / "humanevalpack.jsonl"
    bugs.write_text("\n".join(json.dumps(row) for row in (
        humanevalfix_row(901, "    return a - b\n", "    return a + b\n", "    assert f(1, 2) == 3\n    assert f(5, 5) == 10"),
        humanevalfix_row(902, "    return a * a\n", "    return a ** b\n", "    assert f(2, 3) == 8"))) + "\n")
    monkeypatch.setattr(measure, "SIZES", (2,))
    monkeypatch.setattr(measure, "BACKWARDS_SIZES", (2,))
    out = tmp_path / "record.json"
    assert measure.main(["--condefects", str(lessons), "--any-commit", "--humanevalfix", str(bugs), "--work-dir", str(tmp_path / "work"),
                         "--bugs", "Python/901", "Python/902", "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert "not_ended" not in record and record["which"] == "named" and record["model_calls"] == 0
    assert record["lessons"]["pairs"] == 4 and record["lessons"]["forwards"]["taught_something"] == 3 and record["lessons"]["forwards"]["taught_nothing"] == 1
    assert [question["label"] for question in record["questions"]["forwards"]] == [f"2/{seed}" for seed in measure.ORDER_SEEDS] + ["all"]
    first, second = record["per_bug"]["Python/901"], record["per_bug"]["Python/902"]
    assert first["usable"] and second["usable"]
    assert first["forwards"]["doses"]["all"]["repaired"] and first["forwards"]["doses"]["all"]["is_the_published_fix"]
    assert not first["backwards"]["doses"]["all"]["repaired"] and not second["forwards"]["doses"]["all"]["repaired"]
    everything = record["summary"]["forwards"]["all"]
    assert record["summary"]["usable"] == 2 and everything["repaired_mean"] == 1 and everything["right_as_far_as_checked_mean"] == 1
    assert not (tmp_path / "work" / "Python_901").exists()
    assert set(record["code_sha256"]) >= {"canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/expert_fixes_dose_response_measure_v1.py"}
