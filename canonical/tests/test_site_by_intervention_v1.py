"""Tests for site identification by intervention.

The rules that must hold, because each one cost a measured failure:

  * the candidate set is NOT filtered by textual occurrence -- filtering by occurrence is the rule this
    module exists to replace;
  * a callable whose text contains the value but whose output ignores it is NOT the site;
  * a callable that needs the value as a COLLECTION is only sensitive in the element shape (this bug made
    the true `riscv64` site look inert);
  * the judge must re-encode the value in the shape the intervention discovered (this bug made a real
    discriminating pair read as wrong-at-fixed);
  * a responding site the change did not move is reported as such and never counted as a win.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import instruction_contract_for_code_v1 as IC  # noqa: E402
from canonical.swe_kernel import site_by_intervention_v1 as S  # noqa: E402

SOURCE = textwrap.dedent(
    '''\
    ALLOWED = {"x86_64", "aarch64"}


    def mentions_but_ignores(arch):
        """riscv64 appears in this docstring and nowhere in the behaviour."""
        return arch == "always"


    def decides_as_element(archs):
        return any(arch in ALLOWED for arch in archs)


    def decides_as_scalar(arch):
        return arch in ALLOWED
    '''
)


def test_schema_and_zero_model():
    assert S.SCHEMA == "BRAIN_SITE_BY_INTERVENTION_V1"
    report = S.measure(None)
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert "OCCURS" in report["the_one_rule_that_changed"]


def test_candidates_are_every_callable_not_only_the_ones_that_mention_the_value():
    names = {site["function"] for site in S.candidate_sites(SOURCE)}
    assert names == {"mentions_but_ignores", "decides_as_element", "decides_as_scalar"}


def test_counterfactuals_come_from_the_module_s_own_vocabulary_and_end_with_the_null():
    values = S.counterfactuals(SOURCE, "riscv64")
    assert values[-1] == ""
    assert 1 <= len(values) <= S.MAX_CONTRASTS
    assert all(value == "" or value in SOURCE for value in values)
    assert "riscv64" not in values


def test_occurrence_is_not_sensitivity(tmp_path):
    """`mentions_but_ignores` contains the value in its text and no witness in its behaviour."""
    tree = _tree(tmp_path, SOURCE)
    sites = S.candidate_sites(SOURCE)
    result = S.intervene(tree, "m", sites, "riscv64", ["x86_64", ""])
    assert "mentions_but_ignores#0#scalar" not in result["responding"]


def test_a_collection_is_only_reached_in_the_element_shape(tmp_path):
    """The bug that cost this round its first answer: a str is not a list of archs."""
    tree = _tree(tmp_path, SOURCE)
    sites = [site for site in S.candidate_sites(SOURCE) if site["function"] == "decides_as_element"]
    result = S.intervene(tree, "m", sites, "riscv64", ["x86_64", ""])
    assert "decides_as_element#0#element" in result["responding"]
    assert "decides_as_element#0#scalar" not in result["responding"]


def test_the_judge_honours_the_shape_it_was_given(tmp_path):
    """Round 4's own encoding is unchanged for a clause with no shape, and honoured when it has one."""
    scalar = IC._calls_for({"function": "f", "value": "v", "required": 1, "value_index": 0}, "m")
    assert scalar[0]["args"] == ["=v"]
    element = IC._calls_for({"function": "f", "value": "v", "required": 1, "value_index": 0,
                             "shape": "element"}, "m")
    assert element[0]["args"] == ['@json:["v"]']


def test_a_responding_site_the_change_did_not_move_is_not_a_win(tmp_path):
    """The claim holds in both states: a comment-only change cannot make it discriminating."""
    same = SOURCE
    repo, commit = _repo(tmp_path, same, same + "\n# a comment changed nothing\n",
                         message="Support x86_64 as a supported architecture")
    work = tmp_path / "work"
    work.mkdir()
    row = S.judge_instruction(repo, commit, work)
    assert row["state"] == "SITE_NAMED_BUT_THE_CHANGE_DID_NOT_MOVE_IT", row


def test_a_real_instruction_names_a_discriminating_site_end_to_end(tmp_path):
    parent = 'ALLOWED = {"x86_64"}\n\n\ndef _have_compatible_abi(executable, archs):\n    return any(a in ALLOWED for a in archs)\n'
    fixed = 'ALLOWED = {"x86_64", "riscv64"}\n\n\ndef _have_compatible_abi(executable, archs):\n    return any(a in ALLOWED for a in archs)\n'
    repo, commit = _repo(tmp_path, parent, fixed,
                         message="Add riscv64 as a supported manylinux architecture")
    work = tmp_path / "work"
    work.mkdir()
    row = S.judge_instruction(repo, commit, work)
    assert row["state"] == "SITE_NAMED_AND_DISCRIMINATING", row
    site = row["modules"][0]["site"]
    assert site["shape"] == "element"
    assert site["parent"]["value_repr"] == "False"
    assert site["fixed"]["value_repr"] == "True"


def test_nothing_responds_is_refused_by_name(tmp_path):
    source = "def constant():\n    return 1\n"
    repo, commit = _repo(tmp_path, source, source + "\n# nothing\n",
                         message="Add riscv64 as a supported architecture")
    work = tmp_path / "work"
    work.mkdir()
    row = S.judge_instruction(repo, commit, work)
    assert row["state"] == S.REFUSED_NO_SITE_RESPONDS, row


def test_every_site_responding_is_refused_by_name(tmp_path):
    source = ("def echo(text):\n    return repr([text])\n\n\n"
              "def shout(text):\n    return repr([text, 1])\n")
    repo, commit = _repo(tmp_path, source, source + "\n# a comment is a real diff\n",
                         message="Add riscv64 as a supported architecture")
    work = tmp_path / "work"
    work.mkdir()
    row = S.judge_instruction(repo, commit, work)
    assert row["state"] == S.REFUSED_EVERY_SITE_RESPONDS, row


def test_no_direction_and_no_value_are_refused_before_any_execution(tmp_path):
    source = "def f(x):\n    return x\n"
    repo, commit = _repo(tmp_path, source, source + "\n# x\n", message="riscv64 was mentioned")
    work = tmp_path / "work"
    work.mkdir()
    row = S.judge_instruction(repo, commit, work)
    assert row["state"] == IC.NO_DIRECTION
    assert row["modules"] == []


def test_headline_reports_every_state_apart():
    report = S.measure({"states": {"commits": 40, "site_named": 5, "site_named_and_discriminating": 1,
                                   "site_named_but_change_did_not_move_it": 4,
                                   "site_named_but_wrong_at_the_fixed_state": 0, "refused": 35},
                        "verdict_census": {"SITE_NAMED_AND_DISCRIMINATING": 1}, "commits": []})
    line = S._headline(report)
    assert "40 real commits" in line
    assert "1 of those are DISCRIMINATING" in line
    assert "4 responded but the change did not move them" in line


# --------------------------------------------------------------------------- #
def _tree(tmp_path: pathlib.Path, source: str) -> pathlib.Path:
    tree = tmp_path / "tree"
    tree.mkdir(exist_ok=True)
    (tree / "m.py").write_text(source, encoding="utf-8")
    return tree


def _repo(tmp_path: pathlib.Path, parent: str, fixed: str,
          message: str = "Add riscv64 as a supported architecture") -> tuple[pathlib.Path, dict]:
    def git(*argv: str) -> str:
        return subprocess.run(("git",) + argv, cwd=str(tmp_path), capture_output=True, text=True,
                              check=True).stdout

    git("init", "-q")
    git("config", "user.email", "producer@localhost")
    git("config", "user.name", "producer")
    package = tmp_path / "pkg"
    package.mkdir(exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "tags.py").write_text(parent, encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "before")
    (package / "tags.py").write_text(fixed, encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", message)
    sha = git("rev-parse", "HEAD").strip()
    return tmp_path, {"sha": sha, "message": message, "sources": ["pkg/tags.py"], "tests": []}
