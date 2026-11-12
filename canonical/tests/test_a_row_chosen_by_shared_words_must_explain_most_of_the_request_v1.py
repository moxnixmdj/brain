"""A row chosen by shared words must explain most of the request, or it does not start.

Measured 2026-11-11 on main (3b9c5d1f) with shell requests written by other people (a public corpus,
not vendored here): a sentence such as "Show information about all users who are logged in" shares
``all`` and ``who`` with the python symbol index, ``source_root`` is filled with ``.``, the index of
this repository is built and verified, and the front door reports ``pass``.  The run was correct and
the answer was to a different request.  Some refused sentences had already written a file where the
sentence pointed, because the refusal came after the run.

The rule under test (``request_words_explained_by_row`` in
``canonical/runtime/live_brain_route_admission_v1.py``): a row chosen by the lexical match -- or a
row that opts in with ``request_word_coverage: majority`` -- is refused BEFORE it starts when the
content words of the sentence it says nothing about outnumber the ones it explains.

The sentences below are written for this file.  Each of the seven in ``STRANGER_SENTENCES`` came
back ``pass`` on main before the rule.

Run:  PYTHONPATH=. python3 canonical/tests/test_a_row_chosen_by_shared_words_must_explain_most_of_the_request_v1.py
"""
from __future__ import annotations

import json
import shutil
import sys

from canonical.runtime import live_brain_route_admission_v1 as door

SCRATCH = "canonical/astra_runtime/tmp/zqmw"
REFUSAL = "FAIL_CLOSED__MOST_OF_THE_REQUEST_IS_NOT_EXPLAINED_BY_CAPABILITY"
LEXICAL = "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"
TYPED = "SWE_TYPED_PLAN_V1"

STRANGER_SENTENCES = (
    "Show information about all users who are logged in right now",
    "Count all the mp3 files below the music folder",
    "Search all python files in the current folder for the word import",
    "Open a remote shell with the key file {f} as user deploy on port 2222",
    "Show the entire saved command history of this shell",
    "Report the exit status of the previous command",
    "Show the git log as a table with one column per author",
)


def _rows() -> dict:
    """The rows as the door reads them: the snapshot file overrides the registry file."""
    base = door.ROOT / "canonical/runtime"
    rows = dict(json.loads((base / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"])
    rows.update(json.loads((base / "BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json").read_text(encoding="utf-8"))["capabilities"])
    return rows


def _lexical(inputs: dict | None = None) -> dict:
    return {"compiler_mode": LEXICAL, "inputs": dict(inputs or {})}


# ---- the split -----------------------------------------------------------------------------------

def test_only_content_words_are_counted() -> None:
    entry = {
        "keywords": ["index", "symbols"],
        "action_template": {
            "args": {"source_root": "${input.source_root}", "output_path": "${input.output_path}"},
            "expect": {"field": "output_verified", "type": "field_equals", "value": True},
            "type": "invoke_capability",
        },
    }
    explained, unexplained = door.request_words_explained_by_row(
        'Index the symbols of the 3 modules under src/pkg and save the result to out/index.json, '
        'expecting "a value" of line_total',
        {"matched_tokens": ["index"]}, {"source_root": "src/pkg", "output_path": "out/index.json"},
        "demo.symbols.v1", entry)
    # closed-class words, the number, both paths, the quoted text, the identifier and the words that
    # say where the result goes are neither; "expecting" is NOT explained by the template's own
    # format word "expect".
    assert explained == ["index", "symbols"], explained
    assert unexplained == ["modules", "expecting"], unexplained


def test_a_word_the_row_bound_as_data_is_neither() -> None:
    explained, unexplained = door.request_words_explained_by_row(
        "Evaluate alpha plus beta with sympy", {"matched_tokens": ["evaluate", "sympy"]},
        {"expression": "alpha plus beta"}, "demo.expression.v1", {"keywords": ["evaluate", "sympy"]})
    assert explained == ["evaluate", "sympy"] and unexplained == [], (explained, unexplained)


def test_a_declared_served_word_counts_and_the_evidence_beside_it_does_not() -> None:
    entry = {"keywords": ["commit"],
             "request_words_also_served": {"words": ["changed", "since"],
                                           "required_by": ["some/test.py :: What changed since the last commit?"]}}
    explained, unexplained = door.request_words_explained_by_row(
        "What changed since the last commit?", {"matched_tokens": ["commit"]}, {}, "demo.git.v1", entry)
    assert explained == ["changed", "since", "commit"], explained
    assert unexplained == ["last"], unexplained  # "last" appears only in the evidence line


# ---- the scope -----------------------------------------------------------------------------------

def test_the_rule_is_scoped_by_data_and_a_tie_is_not_a_refusal() -> None:
    check = door.row_chosen_by_words_explains_too_little
    entry = {"keywords": ["history", "log"]}
    sentence = "Print the entire saved command history"
    matched = {"matched_tokens": ["history"]}
    typed = {"compiler_mode": TYPED, "inputs": {}}
    cid = "demo.history.v1"
    assert check(sentence, matched, _lexical(), cid, entry) == (["history"], ["print", "entire", "command"])
    # a typed plan is chosen by a pattern grammar, not by counting words ...
    assert check(sentence, matched, typed, cid, entry) is None
    # ... unless the row opts in
    assert check(sentence, matched, typed, cid, dict(entry, request_word_coverage="majority")) is not None
    # the strict check owns a strict row
    assert check(sentence, matched, _lexical(), cid, dict(entry, request_word_coverage="required")) is None
    # nothing is unexplained when every word was read
    read = dict(matched, admission_basis="EVERY_WORD_OF_THE_SENTENCE_READ_BY_TAUGHT_MEANINGS")
    assert check(sentence, read, _lexical(), cid, entry) is None
    # a sentence that names the row states its identity
    assert check("Run the demo.history.v1.", {"matched_tokens": []}, _lexical(), cid, entry) is None
    # one explained, one unexplained: a tie passes; one more unexplained word does not
    assert check("Print the history", matched, _lexical(), cid, entry) is None
    assert check("Print the command history", matched, _lexical(), cid, entry) == (["history"], ["print", "command"])


def test_the_sentences_this_repository_sends_its_own_rows_are_not_refused() -> None:
    check = door.row_chosen_by_words_explains_too_little
    rows = _rows()
    # the heartbeat's jq phrasings: the second one is a tie, which is why a tie passes
    jq_inputs = {"jq_filter": ".tag", "json_path": "a/doc.json", "output_path": "a/out.txt"}
    for sentence in ('Apply the jq filter ".tag" to a/doc.json with jq and write the output to a/out.txt.',
                     'Use jq to run the filter ".tag" on a/doc.json, saving the output to a/out.txt.',
                     'Query a/doc.json with jq filter ".tag" and store the output in a/out.txt.'):
        assert check(sentence, {"matched_tokens": ["jq"]}, _lexical(jq_inputs), "json.query.jq",
                     rows["json.query.jq"]) is None, sentence
    # the test selector's own question (canonical/tests/test_the_answer_must_be_the_effect_that_was_stated_v1.py)
    cid = "python.source.change_impact.testselect.v1"
    assert check("Which tests do I need to run after changing pkg/calc.py?", {"matched_tokens": ["tests"]},
                 _lexical({"changed_paths": ["pkg/calc.py"]}), cid, rows[cid]) is None
    # the repository questions the git row's own tests require; the row is typed and opted in
    cid = "git.repository.operate.v1"
    typed = {"compiler_mode": TYPED, "inputs": {"op": "log", "repo_root": ".", "rev": "HEAD"}}
    for sentence, matched in (("What changed since the last commit?", ["commit"]),
                              ("Who last changed line 2 of a/notes.txt?", []),
                              ("Who last changed the function line_total in a/service.py?", []),
                              ("Show me the recent commits.", ["show"])):
        assert check(sentence, {"matched_tokens": matched}, typed, cid, rows[cid]) is None, sentence


def test_a_wrong_selection_this_repository_makes_itself_is_refused() -> None:
    # The heartbeat's knowledge-status goal reaches the docx verifier on the single word "verify"
    # (family KNOWLEDGE_FETCH_ASSESS_ASSERT, 0 of 6 on main).
    cid = "docx.document.verify.intent_ooxml"
    verdict = door.row_chosen_by_words_explains_too_little(
        'Verify the knowledge status on a/assessment.json with expected status "CONFLICTED"',
        {"matched_tokens": ["verify"]}, _lexical({"path": "a/assessment.json"}), cid, _rows()[cid])
    assert verdict is not None and verdict[0] == ["verify"], verdict


def test_the_two_registry_files_carry_the_same_declarations_and_every_word_has_a_sentence() -> None:
    base = door.ROOT / "canonical/runtime"
    registry = json.loads((base / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]
    snapshot = json.loads((base / "BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json").read_text(encoding="utf-8"))["capabilities"]
    declaring = sorted(cid for cid, row in registry.items()
                       if row.get("request_words_also_served") or row.get("request_word_coverage") == "majority")
    assert declaring == ["git.repository.operate.v1", "python.source.change_impact.testselect.v1"], declaring
    assert registry["git.repository.operate.v1"]["request_word_coverage"] == "majority"
    for cid in declaring:
        for key in ("request_word_coverage", "request_words_also_served"):
            assert registry[cid].get(key) == snapshot[cid].get(key), (cid, key)
        served = registry[cid]["request_words_also_served"]
        for word in served["words"]:
            assert any(word in line.split("::", 1)[1].lower() for line in served["required_by"]), (cid, word)
        for line in served["required_by"]:
            assert (door.ROOT / line.split("::", 1)[0].strip()).is_file(), line


# ---- through the front door ----------------------------------------------------------------------

def test_a_stranger_sentence_does_not_pass_and_nothing_is_written() -> None:
    folder = door.ROOT / SCRATCH
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    refused_by_the_rule = 0
    try:
        (folder / "k1.txt").write_bytes(b"alpha\nbeta\n")
        for index, sentence in enumerate(STRANGER_SENTENCES):
            names_before = sorted(path.name for path in door.ROOT.iterdir())
            result = door.solve({"task_id": "stranger_%d" % index,
                                 "goal": sentence.replace("{f}", SCRATCH + "/k1.txt")})
            assert result.get("pass") is not True, (sentence, result.get("status"))
            assert sorted(path.name for path in door.ROOT.iterdir()) == names_before, sentence
            assert (folder / "k1.txt").read_bytes() == b"alpha\nbeta\n", sentence
            if result.get("status") == REFUSAL:
                refused_by_the_rule += 1
                assert result.get("refused_before_execution") is True and result.get("executed") is False, sentence
                assert len(result["unexplained_request_words"]) > len(result["explained_request_words"]), sentence
                assert result.get("compiled_capability_id"), sentence
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    # the three git sentences do not depend on what else is in the checkout
    assert refused_by_the_rule >= 3, refused_by_the_rule


def test_the_repository_questions_are_not_refused_by_this_rule() -> None:
    for index, sentence in enumerate(("Show me the recent commits.", "What changed since the last commit?",
                                      "Run the git.repository.operate.v1.")):
        result = door.solve({"task_id": "repo_question_%d" % index, "goal": sentence})
        assert result.get("status") != REFUSAL, (sentence, result.get("failure_class"))


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    failed = 0
    for test in tests:
        try:
            test()
            print("ok  ", test.__name__)
        except Exception as exc:  # noqa: BLE001 - every failure is reported, none hides another
            failed += 1
            print("FAIL", test.__name__ + ":", repr(exc)[:400])
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
