"""Tests for the checkability constructor.

The module does one thing: it asks whether a real change has a postcondition that can be CONSTRUCTED without
the author's tests, without the author's intent and without a model. Every test here is about one of the four
honesty rules that make its numbers worth reading: the alphabet comes from the artifact, the probe cannot smuggle
in the answer, stability is measured inside one interpreter, and a pin is never reported as a proof of intent.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as C  # noqa: E402


def test_schema_and_authority_are_the_producers():
    assert C.SCHEMA == "BRAIN_CHECKABILITY_BY_DIFFERENTIAL_PIN_V1"
    assert C.AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
    assert C.MAX_ARGS >= 1 and C.MAX_CALLABLES >= 1


def test_the_argument_alphabet_requires_no_knowledge_of_any_repository():
    """If the alphabet needed domain knowledge, the answer would be smuggled in through the back door."""
    assert C.ARG_TOKENS == ("none", "empty_str", "zero", "one", "minus_one", "empty_bytes",
                            "empty_tuple", "empty_list", "empty_dict", "zero_float", "star", "a")
    for forbidden in ("open", "eval", "exec", "import"):
        assert forbidden not in C.ARG_TOKENS


def test_module_literals_come_from_the_artifact_itself():
    source = 'def f():\n    return "alpha" + "beta"\n\n\nX = "gamma"\n'
    literals = C.module_literals(source)
    assert all(item.startswith("=") for item in literals)
    assert "=alpha" in literals and "=beta" in literals and "=gamma" in literals
    # a marker, not a guess: the prober strips it back to the literal the file actually contains
    assert "=" not in literals[0][1:]


def test_module_literals_are_bounded_and_stable():
    source = "VALUES = [%s]\n" % ", ".join('"%s"' % ("x" * (index % 5 + 1)) for index in range(200))
    literals = C.module_literals(source, limit=14)
    assert len(literals) <= 14
    assert len(set(literals)) == len(literals)
    # shortest first: the smallest vocabulary that could still discriminate
    assert len(literals[0]) <= len(literals[-1])


def test_module_literals_refuse_unparseable_source():
    assert C.module_literals("def f(:\n") == []


def test_public_callables_is_read_from_the_module_not_from_a_diff():
    source = textwrap.dedent(
        """\
        def public_one(a):
            return a


        def _private(a):
            return a


        class Public:
            pass


        class _Private:
            pass


        def two(a, b=1):
            return a
        """
    )
    offered = C.public_callables(source, ["pkg", "mod"])
    names = [item["function"] for item in offered]
    assert names == ["public_one", "Public", "two"]
    assert {item["function"]: item["required"] for item in offered} == {
        "public_one": 1, "Public": 0, "two": 1}


def test_public_callables_refuses_what_it_cannot_drive():
    source = textwrap.dedent(
        """\
        def variadic(*args):
            return args


        def keywords(*, a):
            return a


        def too_many(a, b, c, d):
            return a
        """
    )
    assert C.public_callables(source, ["pkg", "mod"]) == []


# --------------------------------------------------------------------------- #
# the pin rule, end to end, on a real git history
# --------------------------------------------------------------------------- #
@pytest.fixture()
def two_state_repo(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """A real repository, two real commits, and a real behaviour change between them."""

    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True, text=True,
                              check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "core.py").write_text(
        textwrap.dedent(
            '''\
            def describe(token):
                """Return a word for the token.

                >>> describe("")
                'empty-old'
                """
                return "empty-old"
            '''
        ),
        encoding="utf-8",
    )
    git("add", "-A")
    git("commit", "-qm", "before")
    (package / "core.py").write_text(
        textwrap.dedent(
            '''\
            def describe(token):
                """Return a word for the token.

                >>> describe("")
                'empty-new'
                """
                return "empty-new"
            '''
        ),
        encoding="utf-8",
    )
    git("add", "-A")
    git("commit", "-qm", "after")
    sha = git("rev-parse", "HEAD").strip()
    return tmp_path, sha


def test_a_real_change_is_pinned_without_any_test(two_state_repo):
    repo, sha = two_state_repo
    commit = {"sha": sha, "message": "after", "sources": ["pkg/core.py"], "tests": []}
    work = repo / "work"
    work.mkdir()
    record = C.pins_for_commit(repo, commit, work)
    assert record["modules_probed"] == 1
    assert record["pins"] >= 1, record
    row = record["modules"][0]
    first = row["pins"][0]
    assert first["call"]["function"] == "describe"
    assert first["parent"]["outcome"] == "RETURNED" and first["fixed"]["outcome"] == "RETURNED"
    assert first["parent"]["value_repr"] != first["fixed"]["value_repr"]
    assert first["stable"] is True
    # the state is named, and what it names is a pin: behaviour that must not change, never a proof of intent
    assert record["state"] == "CHECKABLE_WITHOUT_ANY_TEST"
    assert isinstance(record["pins"], int)


def test_the_artifact_s_own_examples_move_with_the_code_and_so_cannot_discriminate(two_state_repo):
    """The measured disappointment, pinned so it cannot be quietly forgotten.

    A doctest lives in the same file as the code, and the author of a change updates it in the same commit. So
    it passes at BOTH states and cannot tell the two apart: the artifact's own examples are not an independent
    specification source, however much they look like one.
    """
    repo, sha = two_state_repo
    commit = {"sha": sha, "message": "after", "sources": ["pkg/core.py"], "tests": []}
    work = repo / "work"
    work.mkdir()
    doctests = C.pins_for_commit(repo, commit, work)["doctests"]
    assert doctests["examples_run"] == 1
    assert doctests["discriminating"] == 0, doctests
    assert doctests["modules"][0]["parent"]["returncode"] == 0
    assert doctests["modules"][0]["fixed"]["returncode"] == 0


def test_stability_is_measured_inside_one_interpreter(tmp_path):
    """The bug this replaces: two processes compared and called 'unstable' whatever differed in the machine."""
    module = tmp_path / "stable.py"
    module.write_text("def value(token):\n    return 7\n", encoding="utf-8")
    outcomes = C.probe(tmp_path, [{"module": "stable", "function": "value", "args": ["zero"]}])
    assert outcomes[0]["outcome"] == "RETURNED"
    assert outcomes[0]["stable"] is True
    assert outcomes[0]["value_repr"] == "7"


def test_a_probe_that_cannot_import_says_so_instead_of_guessing(tmp_path):
    outcomes = C.probe(tmp_path, [{"module": "not_here_at_all", "function": "f", "args": []}])
    assert outcomes[0]["outcome"] == "IMPORT_FAILED"
    assert "detail" in outcomes[0]


def test_measure_without_a_corpus_reports_no_numbers():
    report = C.measure(None)
    assert report["schema"] == C.SCHEMA
    assert report["states"]["commits"] == 0 and report["states"]["checkable"] == 0
    assert "not fetched in this run" in report["corpus"]
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_headline_states_both_denominators_and_calls_the_pin_what_it_is():
    report = {"states": {"commits": 40, "with_tests": 21, "untested": 19, "probed": 13,
                         "checkable": 4, "pins": 156}}
    line = C._headline(report)
    assert "40 real commits" in line and "19" in line and "13" in line
    assert "regression pin, never a proof of intent" in line
    assert "21.1%" in line and "78.9%" in line


def test_commits_touching_sources_keeps_the_commits_that_ship_no_tests(tmp_path):
    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True, text=True,
                              check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "first")
    git("tag", "old")
    (tmp_path / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "second, no tests")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("from mod import f\n\n\ndef test_f():\n    assert f() == 2\n",
                                       encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "third, with tests")
    git("tag", "new")
    found = C.commits_touching_sources(tmp_path, "old", "new")
    # only commits that touch a source file: adding a test to unchanged code is not a change under test
    assert len(found) == 1
    assert found[0]["tests"] == []            # and this one shipped no specification at all
    assert found[0]["sources"] == ["mod.py"]
