"""The same question, asked many ways, must get the same answer.

WHY THIS FILE EXISTS.

The door used to dispatch on English phrasings: eight compiled regexes, three
mutually-unaware lists of nouns and verbs, each added one defect at a time. Anything
phrased with words nobody had written a pattern for was not answered -- and, worse,
was often quietly answered with something else. Ten phrasings of two questions scored
three out of ten.

Phrasing is unbounded. Referents are not. So the door now resolves what a sentence
NAMES against the tree, tries every operation those things permit, and keeps only an
operation that both re-checks against the tree and accounts for the question's own
words (`operation_trial_v1`).

That reframe is only real if it is shown: the SAME question in many wordings must give
the SAME answer. A paraphrase test is not a nicety here -- it is the difference between
a dispatcher that resolves meaning and a list of templates with a new name.

Each test asserts:
  1. every phrasing is answered (nothing silently falls through), and
  2. the ANSWER is identical across phrasings -- the operation and the value a person
     reads -- so it cannot pass by answering twelve different things twelve ways.

The values are checked against hand-computed facts about the fixture, never against
whatever the code happened to produce. A test that asserts today's output only freezes
today's bugs.
"""

import pathlib

import pytest

from canonical.runtime import autonomous_v1 as A


def _tree(tmp_path: pathlib.Path, **files: str) -> str:
    for name, body in files.items():
        path = tmp_path / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return str(tmp_path)


def _answer(question: str, root: str) -> dict:
    out = A.run(goal=question, root=root)
    answer = out.get("answer")
    assert answer is not None, f"the door did not treat this as a question: {question!r}"
    return answer


def _value(question: str, root: str) -> tuple[str, object]:
    """What a person actually gets: the operation, and the value it reports."""
    answer = _answer(question, root)
    assert answer["answered"] is True, (question, answer["verdict"], answer["unresolved_terms"])
    comp = answer["computation"]
    assert comp is not None, question
    return comp["operation"], comp["value"]


# ---------------------------------------------------------------------------
# Asking how long a file is. Four lines was chosen so that "how long" and "how
# many lines" cannot be confused with a coincidence.
# ---------------------------------------------------------------------------

HOW_LONG = [
    "how many lines are in data.py",
    "how long is data.py",
    "line count of data.py",
    "count the lines in data.py",
    "number of lines in data.py",
    "lines in data.py",
    "what is the line count of data.py",
    "tell me how many lines data.py has",
    "how many lines does data.py have",
    "data.py - how many lines",
]


def test_every_way_of_asking_how_long_a_file_is_gets_the_number_of_lines(tmp_path):
    root = _tree(tmp_path, **{"data.py": "a\nb\nc\nd\n"})
    answers = {q: _value(q, root) for q in HOW_LONG}

    for question, (operation, value) in answers.items():
        assert value == 4, f"{question!r} -> {value!r}, not the number of lines"
        assert operation == "count_lines", f"{question!r} was answered by {operation}"

    # THE POINT: one answer, eleven ways of asking.
    assert len(set(answers.values())) == 1, answers


# ---------------------------------------------------------------------------
# Asking what a file says. Every one of these must return the CONTENT, and must
# not return a count -- "3 line(s)" is true about the file and is not an answer to
# "what does it say".
# ---------------------------------------------------------------------------

WHAT_IT_SAYS = [
    "what does data.py say",
    "show me data.py",
    "display data.py",
    "let me see data.py",
    "what is written in data.py",
    "cat data.py",
    "print data.py",
    "read data.py",
    "the contents of data.py",
    "what is in data.py",
]


def test_every_way_of_asking_what_a_file_says_returns_the_content(tmp_path):
    root = _tree(tmp_path, **{"data.py": "alpha\nbeta\n"})
    answers = {}
    for question in WHAT_IT_SAYS:
        answer = _answer(question, root)
        assert answer["answered"] is True, (question, answer["verdict"])
        answers[question] = answer["computation"]["operation"]
        # The content itself must be reachable in the answer, not only a line count.
        assert answer["computation"]["body"] == ["alpha", "beta"], question

    assert len(set(answers.values())) == 1, answers


# ---------------------------------------------------------------------------
# A question with a computable answer must produce the number.
# ---------------------------------------------------------------------------

AMOUNTS = "region,amount\nnorth,100\nsouth,150\nwest,250\n"


def test_the_same_total_is_reachable_from_many_wordings_and_equals_the_hand_sum(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": AMOUNTS})
    phrasings = [
        "what is the total of the amounts in sales.csv",
        "what is the total amount in sales.csv",
        "add up the amounts in sales.csv",
        "sum the amount column in sales.csv",
        "how much is it altogether in sales.csv",
        "what do the amounts add up to in sales.csv",
    ]
    values = {}
    for question in phrasings:
        operation, value = _value(question, root)
        values[question] = (operation, value)

    for question, (operation, value) in values.items():
        assert value == 500, f"{question!r} -> {value!r}; 100+150+250 is 500"
        assert operation == "aggregate_sum", question

    assert len(set(values.values())) == 1, values


def test_largest_smallest_and_average_are_told_apart_by_the_word_used(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": AMOUNTS})
    assert _value("largest amount in sales.csv", root) == ("aggregate_max", 250)
    assert _value("biggest amount in sales.csv", root) == ("aggregate_max", 250)
    assert _value("smallest amount in sales.csv", root) == ("aggregate_min", 100)
    assert _value("lowest amount in sales.csv", root) == ("aggregate_min", 100)
    operation, value = _value("average amount in sales.csv", root)
    assert operation == "aggregate_mean"
    assert abs(float(value) - (100 + 150 + 250) / 3) < 1e-6, value


def test_rows_and_lines_are_different_questions_with_different_answers(tmp_path):
    # Three data rows under one header, in five physical lines? No -- four lines, one
    # header, three data rows. The two counts must not converge.
    root = _tree(tmp_path, **{"sales.csv": AMOUNTS})
    assert _value("how many rows are in sales.csv", root) == ("count_rows", 3)
    assert _value("number of rows in sales.csv", root) == ("count_rows", 3)
    assert _value("how many lines are in sales.csv", root) == ("count_lines", 4)


def test_a_directory_question_counts_the_files_it_can_see(tmp_path):
    root = _tree(tmp_path, **{"a.py": "x\n", "b.md": "y\n", "c.json": "z\n"})
    for question in ("how many files are in this directory",
                     "how many files are here",
                     "count the files in this directory"):
        operation, value = _value(question, root)
        assert value == 3, (question, value)
        assert operation == "count_files", question


# ---------------------------------------------------------------------------
# The other half of answering: refusing when the answer is not there.
# A door that answers everything is not smart, it is agreeable.
# ---------------------------------------------------------------------------

def test_a_word_that_is_not_in_the_named_file_is_reported_missing_not_answered(tmp_path):
    root = _tree(tmp_path, **{"data.py": "revenue = 10\n"})
    answer = _answer("what is the profit margin in data.py", root)
    assert answer["answered"] is False
    assert set(answer["unresolved_terms"]) == {"profit", "margin"}, answer["unresolved_terms"]

    out = A.run(goal="what is the profit margin in data.py", root=root)
    assert out["verification"]["verified"] is False
    # The specific fact survives: it looked in the file the question named.
    assert out["verification"]["reason"] == "SUBJECT_ABSENT_FROM_NAMED_FILE"
    assert out["verification"]["unresolved"] == ["profit", "margin"]


def test_a_word_that_is_in_the_file_is_answered_with_the_line_it_is_on(tmp_path):
    root = _tree(tmp_path, **{"conf.json": '{"retries": 3}\n'})
    operation, value = _value("what is retries in conf.json", root)
    assert operation == "locate"
    # The VALUE must be the line, not a count of how many lines matched.
    assert "retries" in str(value) and "3" in str(value), value


def test_nothing_in_the_tree_is_not_the_same_as_absent_from_the_named_file(tmp_path):
    root = _tree(tmp_path, **{"data.py": "x\n"})
    answer = _answer("what is a zzz_absent_thing", root)
    assert answer["answered"] is False
    assert answer["verdict"] == "NOTHING_FOUND", answer["verdict"]


# ---------------------------------------------------------------------------
# The attempt history never disappears. A failed operation is part of the answer.
# ---------------------------------------------------------------------------

def test_operations_that_were_tried_and_failed_stay_in_the_answer(tmp_path):
    root = _tree(tmp_path, **{"data.py": "x\n"})
    answer = _answer("what is the total of the amounts in data.py", root)
    tried = {a["operation"] for a in answer["attempted"]}
    assert "aggregate_sum" in tried, answer["attempted"]
    # It was tried, it did not answer, and the answer says so.
    assert answer["answered"] is False


# ---------------------------------------------------------------------------
# Changes to the tree are not questions. Routing them as questions is how a write
# request would silently become a read.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("goal", [
    "delete data.py",
    "remove data.py",
    "write a report to out.txt",
    "append to data.py",
])
def test_an_instruction_to_change_the_tree_is_not_answered_as_a_question(goal, tmp_path):
    root = _tree(tmp_path, **{"data.py": "x\n"})
    out = A.run(goal=goal, root=root)
    assert out.get("answer") is None, out


@pytest.fixture(autouse=True)
def _no_persistent_memory():
    """A test run must not write to the creature's committed memory store."""
    from canonical.tests._memory import no_persistent_memory

    with no_persistent_memory():
        yield
