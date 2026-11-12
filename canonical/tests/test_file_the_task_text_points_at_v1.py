#!/usr/bin/env python3
"""The files of a project in the order a task's text points at them: the words counted, how a text
names a file, the scores, the order, and the candidates made from the first files."""
from __future__ import annotations

import collections
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import file_the_task_text_points_at_v1 as finder  # noqa: E402
from canonical.runtime import function_the_task_text_points_at_v1 as pointer  # noqa: E402
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25  # noqa: E402

STORE = ("class Store:\n    def save(self, content_type, db):\n        content_type.save(update_fields={'model'})\n        return db\n\n"
         "    def load(self, a):\n        return a\n")
HELPERS = "def helper(x):\n    return x + 1\n\n\ndef other(save):\n    return save\n"
SOURCES = {"pkg/store.py": STORE, "pkg/util/helpers.py": HELPERS, "pkg/__init__.py": "import os\n\nLIMIT = 3\n", "setup.py": "from setuptools import setup\nsetup()\n"}
TEXT = "Store.save() writes to the wrong database.\n```\ncontent_type.save(using=db, update_fields={'model'})\n```\n"


def documents(sources=SOURCES):
    return {path: finder.document(path, source) for path, source in sources.items()}


# --------------------------------------------------------------------------- #
# the words, counted
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text", [STORE, HELPERS, TEXT, "", "RenameContentType update_fields HTTPServer for_each x_y", "a a a b"])
def test_counted_is_the_words_of_the_function_organ_counted(text):
    assert finder.counted(text) == collections.Counter(pointer.words(text))


def test_a_word_counts_as_often_as_it_stands_and_so_do_its_parts():
    found = finder.counted("update_fields update_fields fields")
    assert found["update_fields"] == 2 and found["update"] == 2 and found["fields"] == 3


def test_a_document_is_the_words_of_the_text_and_of_the_path():
    found = finder.document("pkg/util/helpers.py", "x = 1\n")
    assert found["pkg"] == 1 and found["util"] == 1 and found["helpers"] == 1 and found["x"] == 1 and found["py"] == 1
    assert finder.document("a/b.py", "b = b\n")["b"] == 3


# --------------------------------------------------------------------------- #
# how a text names a file
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text, level", [
    ("see pkg/util/helpers.py line 3", finder.WRITTEN_OUT),
    ('File "/usr/lib/python3/site-packages/pkg/util/helpers.py", line 3', finder.WRITTEN_OUT),
    ("util/helpers.py", finder.WRITTEN_OUT),
    ("pkg.util.helpers.helper is wrong", finder.WRITTEN_OUT),
    ("from pkg.util.helpers import helper", finder.WRITTEN_OUT),
    ("util.helpers", finder.WRITTEN_OUT),
    ("in helpers.py", finder.FILE_NAME_ONLY),
    ("the helpers are wrong", finder.NOT_NAMED),
    ("helpers", finder.NOT_NAMED),
    ("xhelpers.py", finder.NOT_NAMED),
    ("helpers.pyc", finder.NOT_NAMED),
    ("util.helpers_old", finder.NOT_NAMED),
    ("myutil.helpers", finder.NOT_NAMED),
    ("", finder.NOT_NAMED),
])
def test_how_much_of_a_path_the_text_writes_out(text, level):
    assert finder.named("pkg/util/helpers.py", text) == level


@pytest.mark.parametrize("text, level", [
    ("pkg/forms/__init__.py", finder.WRITTEN_OUT),
    ("forms/__init__.py", finder.WRITTEN_OUT),
    ("import pkg.forms", finder.WRITTEN_OUT),
    ("pkg.forms is the package", finder.WRITTEN_OUT),
    ("pkg.forms.ModelForm", finder.NOT_NAMED),                         # something inside the package, in whichever of its files
    ("pkg.forms.models", finder.NOT_NAMED),
    ("the forms", finder.NOT_NAMED),
    ("__init__.py", finder.NOT_NAMED),
])
def test_a_package_is_named_by_its_directory(text, level):
    assert finder.named("pkg/forms/__init__.py", text) == level


def test_a_file_at_the_top_is_named_by_its_file_name_only():
    assert finder.named("setup.py", "setup.py fails") == finder.FILE_NAME_ONLY
    assert finder.named("setup.py", "the setup fails") == finder.NOT_NAMED
    assert finder.named("pkg/__init__.py", "import pkg") == finder.NOT_NAMED
    assert finder.named("pkg/__init__.py", "pkg/__init__.py") == finder.WRITTEN_OUT


def test_a_module_inside_a_longer_dotted_name_is_named():
    assert finder.named("django/db/models/query.py", "django.db.models.query.QuerySet.filter()") == finder.WRITTEN_OUT
    assert finder.named("django/db/models/query.py", "django.db.models.query_utils.Q") == finder.NOT_NAMED
    assert finder.named("django/db/models/sql/query.py", "django.db.models.query.QuerySet") == finder.NOT_NAMED
    assert finder.named("django/db/models/sql/query.py", "see query.py") == finder.FILE_NAME_ONLY


# --------------------------------------------------------------------------- #
# the scores
# --------------------------------------------------------------------------- #
def test_the_scores_are_what_the_trees_scorer_gives_for_the_same_words_in_lists():
    found = documents()
    names = list(found)
    mine = finder.scores(found, pointer.words(TEXT))
    theirs = bm25._bm25_scores(pointer.words(TEXT), [list(found[name].elements()) for name in names])
    for name, (score, _) in zip(names, theirs):
        assert mine[name] == pytest.approx(score, abs=1e-12)
    assert mine["pkg/store.py"] > mine["pkg/util/helpers.py"] > 0 == mine["setup.py"]


def test_the_scores_hold_for_other_texts_and_for_repeated_words():
    found = documents()
    names = list(found)
    for text in ("helper helper helper x", "setup os LIMIT pkg", "nothing in common", ""):
        mine = finder.scores(found, pointer.words(text))
        theirs = bm25._bm25_scores(pointer.words(text), [list(found[name].elements()) for name in names])
        assert [mine[name] for name in names] == pytest.approx([score for score, _ in theirs], abs=1e-12)


def test_the_constants_are_the_trees():
    import inspect
    assert (finder.K1, finder.B) == (1.5, 0.75)
    assert "k1=1.5, b=0.75" in str(inspect.signature(bm25._bm25_scores))


def test_no_document_or_only_empty_ones_score_nothing():
    assert finder.scores({}, ["a"]) == {}
    assert finder.scores({"a.py": collections.Counter(), "b.py": collections.Counter()}, ["a"]) == {"a.py": 0.0, "b.py": 0.0}


def test_a_rare_word_outweighs_words_that_stand_in_nearly_every_file():
    sources = {f"pkg/filler_{n}.py": "common1 = common2 = common3 = common4 = 0\n" for n in range(5)}
    sources["pkg/target.py"] = "common1 = rare = 0\n"
    assert finder.order(documents(sources), "common1 common2 common3 common4 rare")[0] == "pkg/target.py"
    assert finder.order(documents(sources), "common1 common2 common3 common4")[0] == "pkg/filler_0.py"


# --------------------------------------------------------------------------- #
# the order
# --------------------------------------------------------------------------- #
def test_the_file_the_text_is_about_comes_first():
    assert finder.order(documents(), TEXT)[0] == "pkg/store.py"
    assert finder.order(documents(), "helper(x) returns x + 2")[0] == "pkg/util/helpers.py"


def test_a_file_the_text_names_comes_before_a_file_with_a_higher_score():
    text = TEXT + "\nIt started in setup.py.\n"
    assert finder.order(documents(), text)[:2] == ["setup.py", "pkg/store.py"]
    assert finder.order(documents(), text, use_names=False)[0] == "pkg/store.py"


def test_a_file_written_out_comes_before_a_file_named_by_its_name_alone():
    text = "setup.py and pkg/util/helpers.py and Store.save content_type update_fields"
    assert finder.order(documents(), text)[:3] == ["pkg/util/helpers.py", "setup.py", "pkg/store.py"]


def test_files_named_alike_are_ordered_by_score_and_ties_by_path():
    sources = {"a/query.py": "alpha = 1\n", "b/query.py": "alpha = beta = 1\n", "c/other.py": "alpha = beta = gamma = 1\n"}
    assert finder.order(documents(sources), "query.py alpha beta gamma") == ["b/query.py", "a/query.py", "c/other.py"]
    same = {"b.py": "x = 1\n", "a.py": "x = 1\n"}
    assert finder.order(documents(same), "nothing") == ["a.py", "b.py"]


def test_the_order_holds_every_file_once_whatever_the_text():
    for text in (TEXT, "", "setup.py", "pkg.util.helpers"):
        for use_names in (True, False):
            assert sorted(finder.order(documents(), text, use_names=use_names)) == sorted(SOURCES)
    assert finder.order({}, TEXT) == []


# --------------------------------------------------------------------------- #
# the candidates
# --------------------------------------------------------------------------- #
def test_with_one_file_the_candidates_are_the_function_organs_for_that_file():
    made = finder.candidates(documents(), SOURCES.__getitem__, TEXT)
    assert made and {path for path, _, _ in made} == {"pkg/store.py"}
    assert [(function, text) for _, function, text in made] == pointer.candidates(STORE, TEXT)


def test_the_first_candidate_is_the_quoted_line_in_the_function_the_text_is_about():
    path, function, text = finder.candidates(documents(), SOURCES.__getitem__, TEXT)[0]
    assert (path, function.name) == ("pkg/store.py", "Store.save") and "content_type.save(using=db, update_fields={'model'})" in text


def test_only_the_first_files_are_read():
    read = []

    def source_of(path):
        read.append(path)
        return SOURCES[path]

    finder.candidates(documents(), source_of, TEXT)
    assert set(read) == {"pkg/store.py"}
    read.clear()
    finder.candidates(documents(), source_of, TEXT, files_tried=2)
    assert set(read) == {"pkg/store.py", "pkg/util/helpers.py"}


def test_with_more_files_their_functions_are_ranked_together():
    sources = dict(SOURCES)
    sources["pkg/noise.py"] = "def noise(database, wrong, writes):\n    return database, wrong, writes, database, wrong, writes\n"
    text = TEXT + "\nIt started in pkg/noise.py.\n"
    found = documents(sources)
    assert finder.order(found, text)[:2] == ["pkg/noise.py", "pkg/store.py"]
    assert not any(path == "pkg/store.py" for path, _, _ in finder.candidates(found, sources.__getitem__, text))
    both = finder.candidates(found, sources.__getitem__, text, files_tried=2)
    assert both[0][0] == "pkg/store.py" and both[0][1].name == "Store.save"


def test_there_are_at_most_so_many_candidates():
    made = finder.candidates(documents(), SOURCES.__getitem__, TEXT, files_tried=3)
    assert 0 < len(made) <= pointer.FUNCTIONS * pointer.OF_EACH
    assert len({(path, function) for path, function, _ in made}) <= pointer.FUNCTIONS
    assert len(finder.candidates(documents(), SOURCES.__getitem__, TEXT, files_tried=3, functions=1, of_each=2)) == 2


def test_an_order_handed_over_is_used_as_it_is():
    made = finder.candidates(documents(), SOURCES.__getitem__, TEXT, in_order=["pkg/util/helpers.py", "pkg/store.py"])
    assert {path for path, _, _ in made} <= {"pkg/util/helpers.py"}


def test_no_file_no_function_or_no_code_line_gives_no_candidate():
    assert finder.candidates({}, SOURCES.__getitem__, TEXT) == []
    only = {"setup.py": SOURCES["setup.py"]}
    assert finder.candidates(documents(only), only.__getitem__, TEXT) == []
    assert finder.candidates(documents(), SOURCES.__getitem__, "Store.save writes to the wrong database") == []
