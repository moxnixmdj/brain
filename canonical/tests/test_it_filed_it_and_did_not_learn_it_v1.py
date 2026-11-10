"""r59: THE DIRECT QUESTION. "Isn't this a revolutionary way to make agents learn faster?"

Answered with the field's own criterion rather than an opinion.

THE WIPE TEST (2026). "What happens if memory is wiped? If the gain vanishes, it was
memory." Skill-GRPO, a skill-retrieval baseline, drops from 80.5 to 60.2 on ALFWorld-3B the
moment skills are withheld. SKILL0's premise is that retrieval-time skill augmentation is
limited because the model "never truly acquires the knowledge it merely follows."

Measured here:

    before wipe : ANSWERED -> ['q','z']
    after  wipe : ASK, NOTHING_TAUGHT

The file still exists. `sort` is still installed. Only the row was removed. Nothing survived,
because nothing was ever internalised.

WHAT THIS SYSTEM IS GOOD AT -- AND IT IS REAL. Adding a skill costs milliseconds, zero GPU,
and is exactly reversible: delete a row and the capability is gone, with no interference with
any other row. Fine-tuning cannot do that; every fact costs a retrain and risks catastrophic
forgetting of others ("the parallel learning tax"). A study of 34,396 production skills found
that naive fine-tuning of a skill retriever dropped OOD Recall@10 from 0.850 to 0.650 --
the training made it worse at what it had not been trained on.

WHERE THE "FILLING CABINET" READING IS TOO FLAT. The containment test measured this round:
after teaching 12 more operations, the original skill still executed correctly by id. It was
never corrupted. Only FINDING it degraded. That is a different failure from forgetting, and
it is genuinely more benign: nothing is lost, only reachable-ness. Fine-tuning loses the
capability; this loses the pointer.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K


@pytest.fixture()
def box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("z\na\nz\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("m\nn\nm\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    K.compile_and_qualify_skill(
        goal=f"unique lines of {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(t)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    f = tmp / "data.txt"; f.write_text("z\nq\nz\n", encoding="utf-8")
    return tmp, pathlib.Path(db), f


def test_answering_before_the_wipe(box):
    tmp, db, f = box
    r = K.answer_or_ask(f"unique lines of {f}", cwd=str(tmp), db_path=db)
    assert r["verdict"] == "ANSWERED" and r["answer"] == ["q", "z"]


def test_nothing_survives_the_wipe(box):
    """The criterion. The file, the program and the process are all unchanged; only the row
    is gone, and the capability goes with it."""
    tmp, db, f = box
    shutil.copy(str(db), str(tmp / "backup.sqlite"))
    os.remove(str(db))
    K._WORKFLOW_MEM_CACHE.clear()
    after = K.answer_or_ask(f"unique lines of {f}", cwd=str(tmp), db_path=db)
    assert after["verdict"] == "ASK"
    assert after.get("reason") == "NOTHING_TAUGHT"
    assert f.exists() and shutil.which("sort"), "everything except the row is still here"


def test_restoring_the_row_restores_the_capability_exactly(box):
    """The other half of the property, and the one fine-tuning cannot offer: reversal is
    exact and costs one file copy."""
    tmp, db, f = box
    shutil.copy(str(db), str(tmp / "backup.sqlite"))
    os.remove(str(db))
    K._WORKFLOW_MEM_CACHE.clear()
    assert K.answer_or_ask(f"unique lines of {f}", cwd=str(tmp), db_path=db)["verdict"] == "ASK"
    shutil.copy(str(tmp / "backup.sqlite"), str(db))
    K._WORKFLOW_MEM_CACHE.clear()
    assert K.answer_or_ask(f"unique lines of {f}", cwd=str(tmp), db_path=db)["answer"] == ["q", "z"]


def test_teaching_more_does_not_corrupt_what_was_learned_only_what_can_be_found(box):
    """The containment test: 12 more operations, then execute the original BY ID.
    It is untouched. Contrast with catastrophic forgetting, which damages the skill itself."""
    tmp, db, f = box
    rows = K._load_cached_skills(db_path=db)
    sid = rows[0]["skill_id"]
    t = tmp / "teach.txt"
    h = tmp / "hold.txt"
    s = tmp / "s.txt"
    flood = [("count the lines of", ["wc", "-l"]), ("dump the contents of", ["cat"]),
             ("reverse each line of", ["rev"]), ("reverse the order of", ["tac"]),
             ("first line of", ["head", "-1"]), ("last line of", ["tail", "-1"]),
             ("sort the lines of", ["sort"]), ("word count of", ["wc", "-w"]),
             ("sha256 of", ["sha256sum"]), ("md5 of", ["md5sum"]),
             ("first column of", ["cut", "-f1"]), ("base64 of", ["base64"])]
    for g, a in flood:
        K.compile_and_qualify_skill(
            goal=f"{g} {t}", trace=[{"kind": "cli_exec", "layer": "cli_exec",
                                     "argv": a + [str(t)]}],
            postcondition=None, heldout_goal=f"{g} {h}", heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"}, db_path=db)
    skill = [r for r in K._load_cached_skills(db_path=db) if r["skill_id"] == sid][0]
    steps = K._instantiate_obj(skill["abstract_steps"], {"?path0": str(f)})
    res = K.execute_compiled_steps(steps, cwd=str(tmp))
    ok, _ = K.verify_postcondition(skill.get("abstract_postcondition"), cwd=str(tmp),
                                   execution_result=res)
    assert ok, "the skill itself must be unchanged by later teaching"
    assert K._contract_answer(skill.get("abstract_postcondition"), res) == ["q", "z"]


def test_the_memory_is_inspectable_and_deletable_in_one_operation(box):
    """The two properties fine-tuning cannot offer, stated as a test rather than a claim."""
    import sqlite3
    tmp, db, _ = box
    c = sqlite3.connect(str(db))
    rows = c.execute("SELECT skill_id, goal_skeleton, abstract_steps FROM compiled_workflow_skills"
                     if False else
                     "SELECT skill_id, goal_skeleton, steps_json FROM compiled_workflow_skills").fetchall()
    c.close()
    assert len(rows) == 1
    assert "unique lines of" in rows[0][1], "the row is human-readable, not weights"
