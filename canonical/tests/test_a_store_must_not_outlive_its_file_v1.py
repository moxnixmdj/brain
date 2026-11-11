"""A skill store must not be served from memory after its file changes.

THE DEFECT THIS PINS (measured 2026-11-09, proven by construction)
-----------------------------------------------------------------
Create an empty store at a path, load it (caching zero skills), then replace the file with
a populated one. Recall for a skill that IS on disk returns MISS, forever, for the life of
the process. The bytes are correct; the memory is stale.

Every stat-based defence fails on this host. After `shutil.copyfile`, these were ALL
identical before and after the replacement:

    st_mtime_ns  SAME
    st_ctime_ns  SAME
    st_size      SAME   (16384 -- both files are one page)
    st_ino       SAME

So no stamp -- not (mtime,size), not even (mtime,size,ctime,ino) -- can distinguish the two
files. The only correct rule is that a lookup re-reads, and that the connection used to
re-read is opened AFTER the decision, because the old connection may hold a stale snapshot:
popping the cache and then querying that same connection returned zero skills for a store
that had one.

This is the worst class of failure in the tree: not a refusal, not a wrong answer, but a
memory that silently forgets everything taught to it.
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SHIPPED = _ROOT / "canonical" / "astra_runtime" / "tmp" / "compiled_workflows_v1.sqlite"


@pytest.fixture()
def work():
    base = _ROOT / "canonical" / "astra_runtime" / "tmp"
    d = pathlib.Path(tempfile.mkdtemp(prefix="stale_", dir=str(base)))
    yield d
    C._WORKFLOW_MEM_CACHE.clear()
    C._WORKFLOW_INDEX_CACHE.clear()
    shutil.rmtree(d, ignore_errors=True)


def _goal(work: pathlib.Path) -> str:
    (work / "d.txt").write_text("a\nb\na\n", encoding="utf-8")
    return f"how many unique lines in {(work / 'd.txt').relative_to(_ROOT)}"


def test_a_populated_store_replaces_a_cached_empty_one(work):
    if not _SHIPPED.exists():
        pytest.skip("shipped store not present")
    db = work / "skills.sqlite"
    _, conn = C._connect_db(db)
    conn.close()
    C._WORKFLOW_MEM_CACHE.clear()
    C._WORKFLOW_INDEX_CACHE.clear()
    assert C._load_cached_skills(db) == []          # cached as EMPTY under this path

    shutil.copyfile(_SHIPPED, db)                   # bytes change; NO stat field changes

    assert len(C._load_cached_skills(db)) == 1, "the store is on disk but memory says it is empty"
    assert C.recall_and_execute_workflow(_goal(work), db_path=db) is not None


def test_a_stat_stamp_could_not_have_caught_it(work):
    """Records WHY the fix is 're-read', not 'compare a stamp'."""
    db = work / "s.sqlite"
    db.write_bytes(b"x" * 16384)
    before = db.stat()
    shutil.copyfile(_SHIPPED, db)
    after = db.stat()
    assert before.st_mtime_ns == after.st_mtime_ns
    assert before.st_ctime_ns == after.st_ctime_ns
    assert before.st_size == after.st_size
    assert before.st_ino == after.st_ino


def test_the_normal_path_still_answers(work):
    """The nearest world in which the re-read must not break ordinary recall."""
    assert C.recall_and_execute_workflow(_goal(work)) is not None
