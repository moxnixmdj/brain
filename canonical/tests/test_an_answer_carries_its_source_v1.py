"""r47: every answer carries its provenance, and the type heuristic has an honest score.

WHY PROVENANCE
--------------
r46 closed with the warning that a typed answer must never stand as a factual claim
without its source, and that 23/23 correct is exactly the condition under which an empty
result starts to look like a finding. A number with no pedigree is indistinguishable from
a lucky guess. Every recall now returns `provenance`: the argv that ran, the exit code,
the sha256 of the stdout actually observed, and an explicit statement when the answer is
an empty result.

WHY THE SCORE BELOW IS 28/30 AND NOT 27/27
------------------------------------------
infer_contract_from_goal was first scored 23/23 on the 23 goals in the r41 track. Those
goals were written to match the heuristic, so that was a closed loop and worth nothing.
Rewritten as natural phrasings, it scored 23/27. The vocabulary was widened against those
-- which makes 27/27 a TRAINING number, also worth nothing.

The number in this file is from phrasings composed AFTER the vocabulary was frozen, with
no consultation: 28/30. The two misses are pinned rather than patched, because widening
the vocabulary until the test passes is how a heuristic becomes a lookup table of its own
test set.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzzz\n"


def _teach(tmp, goal_word, prog):
    t = tmp / f"{goal_word.replace(' ', '_')}_t.txt"; t.write_text(FIXTURE, encoding="utf-8")
    h = tmp / f"{goal_word.replace(' ', '_')}_h.txt"; h.write_text(FIXTURE, encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    db = str(tmp / f"{goal_word.replace(' ', '_')}.sqlite")
    r = K.compile_and_qualify_skill(
        goal=f"{goal_word} {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": prog + [str(t)]}],
        postcondition=None, heldout_goal=f"{goal_word} {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    assert r.get("pass"), r.get("status")
    return db, h


def test_a_normal_answer_carries_argv_exit_and_stdout_hash():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db, h = _teach(tmp, "unique lines of", ["sort", "-u"])
        hit = K.recall_and_execute_workflow(f"unique lines of {h}", cwd=str(tmp), db_path=db)
        prov = hit["provenance"]
        assert prov["schema"] == "ANSWER_PROVENANCE_V1"
        assert prov["answer_type"] == "stdout_lines"
        step = prov["steps"][0]
        assert step["argv"][0] in ("sort", "sort.exe")
        assert step["exit"] == 0
        assert len(step["stdout_sha256"]) == 64
        assert prov["empty_result"] is False


def test_an_empty_answer_says_so_in_words():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db, _ = _teach(tmp, "lines containing zzz", ["grep", "zzz"])
        none_file = tmp / "none.txt"; none_file.write_text("aaa\nbbb\n", encoding="utf-8")
        hit = K.recall_and_execute_workflow(f"lines containing zzz {none_file}",
                                            cwd=str(tmp), db_path=db)
        assert hit["answer"] == []
        assert hit["provenance"]["empty_result"] is True
        assert "nothing matched" in hit["provenance"]["claim"]


def test_provenance_says_how_to_check_the_answer():
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        db, h = _teach(tmp, "sha256 of", ["sha256sum"])
        hit = K.recall_and_execute_workflow(f"sha256 of {h}", cwd=str(tmp), db_path=db)
        assert "reproducible" in hit["provenance"]["how_to_check"]


# ------------------------------------------------------ the honest score
FRESH = [
    ("let me see the file config.yaml", "stdout_lines"),
    ("read me report.txt", "stdout_lines"),
    ("spot any FAILED entries in build.log", "stdout_lines"),
    ("replace tabs with spaces throughout notes.txt", "stdout_lines"),
    ("list every occurrence of DONE in tasks.md", "stdout_lines"),
    ("break the overlong lines in notes.txt", "stdout_lines"),
    ("search for panic in server.log", "stdout_lines"),
    ("peek at the top of results.csv", "stdout_lines"),
    ("add numbers to the lines of poem.txt", "stdout_lines"),
    ("dump the bytes of payload.bin", "stdout_lines"),
    ("concatenate the lines of left.txt", "stdout_lines"),
    ("invert the character order of each line in word.txt", "stdout_lines"),
    ("change every instance of foo to bar in src.txt", "stdout_lines"),
    ("dedupe and order the lines of raw.txt", "stdout_lines"),
    ("gimme list.txt in backwards order", "stdout_lines"),
    ("what are the last entries of events.jsonl", "stdout_lines"),
    ("convert indentation to tabs in source.py", "stdout_lines"),
    ("remove adjacent repeats from stream.txt", "stdout_lines"),
    ("squash consecutive duplicates in list.csv", "stdout_lines"),
    ("give me the md5 signature of bundle.tar.gz", "stdout_first_token"),
    ("produce the sha256 fingerprint for image.iso", "stdout_first_token"),
    ("what does the sha256 of release.zip come out as", "stdout_first_token"),
    ("what number of lines does report.txt contain", "stdout_integer_value"),
    ("count how many lines report.txt has", "stdout_integer_value"),
    ("report.txt has how many lines", "stdout_integer_value"),
    ("count the lines of report.txt", "stdout_integer_value"),
    ("what is in notes.txt", "stdout_lines"),
    ("turn the tabs into spaces in table.tsv", "stdout_lines"),
]


def test_the_fresh_heldout_score_is_28_of_30():
    """Pinned so the number cannot drift silently upward by tuning."""
    correct = sum(1 for g, want in FRESH
                  if K.infer_contract_from_goal(g)["kind"] == want)
    assert correct == len(FRESH), f"{correct}/{len(FRESH)}"


@pytest.mark.parametrize("goal,want", [
    ("verify the integrity of backup.iso", "stdout_first_token"),   # says 'integrity', not 'checksum'
    ("how long is report.txt in lines", "stdout_integer_value"),    # says 'how long'
])
def test_the_two_known_misses_are_pinned_not_patched(goal, want):
    """These two fail. They are recorded rather than fixed, because widening the vocabulary
    until the held-out set passes is how a heuristic turns into a copy of its own test set."""
    got = K.infer_contract_from_goal(goal)["kind"]
    assert got != want, (
        "this phrasing now passes -- if that was intentional, move it out of the known-miss "
        "list and re-measure the fresh set; do not silently delete this test"
    )
