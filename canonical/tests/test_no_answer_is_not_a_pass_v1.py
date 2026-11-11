"""A question that got no answer is not a pass.

Measured 2026-11-09: `how many unique words in data.txt` returned
    pass=True, layer=ADMITTED_CONFINEMENT, answer=None
because the carrier executed `wc -w` -- a correct execution of the WRONG command -- and its
exit 0 was read as success. A caller checking `pass` gets a green light and no number. That is
the exact failure mode this project exists to refuse: a report asserting success with no
evidence.

Two defects, both fixed and pinned here:
  1. `unique words` did not RESOLVE to any query kind (no refinement edge from
     `uniquelines` to `words`), so the door fell past the bridge and ran raw `wc -w`.
  2. a layer that executed but produced no answer reported pass=True.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_one_model_v3 as D
from canonical.runtime import computer_env_v1 as cenv

BASE = ROOT / "canonical" / "astra_runtime" / "tmp"


def _ws() -> pathlib.Path:
    BASE.mkdir(parents=True, exist_ok=True)
    d = pathlib.Path(tempfile.mkdtemp(prefix="noans_", dir=str(BASE)))
    # lines=3  words=6  unique lines=2  unique words=4  bytes=12
    (d / "data.txt").write_text("a b\nc d\na b\n")
    return d


def test_unique_words_resolves_to_a_kind():
    assert cenv.query_kind("how many unique words in data.txt") == "uniquewords"
    assert cenv.query_kind("how many distinct words in data.txt") == "uniquewords"


def test_two_unrelated_questions_in_one_sentence_are_still_refused():
    """The ambiguity guard must not be weakened to make the new kind work."""
    assert cenv.query_kind("how many bytes per line in data.txt") is None


def test_a_correct_shape_still_answers():
    d = _ws()
    r = D.resolve("how many words in data.txt", root=str(d), execute=True)
    assert r["pass"] is True, r
    assert r.get("answer") == 6, r


def test_a_layer_that_produced_no_answer_refuses_by_name():
    d = _ws()
    r = D.resolve("how many unique words in data.txt", root=str(d), execute=True)
    assert r["pass"] is False
    assert r["status"] == "FAIL_CLOSED__EXECUTION_PRODUCED_NO_ANSWER"
    # A refusal carries no `answer` key at all -- absence is the correct encoding of "there
    # is no answer", and asserting `r["answer"] is None` would have been a test that only
    # passes because the key happens to exist.
    assert "answer" not in r, r.get("answer")
    assert r["detail"]["confined"] is True, "the confinement still held; only the answer is absent"


def test_the_wrong_command_is_no_longer_silently_green():
    """The specific regression: `wc -w` answering a 'unique words' question with 6."""
    d = _ws()
    r = D.resolve("how many unique words in data.txt", root=str(d), execute=True)
    assert r.get("answer") != 6, "a raw word count was returned as the unique-word answer"
