#!/usr/bin/env python3
"""A stated path is data, not part of the ask.

Measured 2026-11-02, on the sentence

    "Tell me what changed in canonical/astra_runtime/tmp/<x> today"

the retrieval shortlist proposed exactly ONE candidate:
`git.history.bisect_regression.v1`, matched on the single term `runtime`.  That
word is not in the sentence.  It is in the DIRECTORY the sentence names.  The
row was selected, ran, and refused with NAMED_TEST_NOT_IN_GIT_HISTORY: a
question about a directory's history was handed to a row that wanted a test to
bisect.

The same sentence against a neutral directory proposed nothing at all -- the
honest reading, because none of its words ("tell", "what", "changed", "today")
matches any row.  So the token was contamination, and it is systematic in this
repository: every path begins `canonical/astra_runtime`, so `canonical`, `astra`
and `runtime` were voting on every request that named a file.

What is pinned here:

* a path-shaped token does not create a proposal (the neutral and the real path
  now behave the same way);
* the mask is not silent -- the shortlist reports what it removed;
* it cannot eat an address: a token that IS a capability id is kept;
* it cannot empty the ask: a sentence that is nothing but a path keeps the
  reading it had rather than collapsing to RELEVANCE_UNRESOLVED.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import capability_selection_retrieval_v1 as sel  # noqa: E402

REGISTRY = graph.load_registry()


def _proposals(goal: str) -> tuple[list[str], list[str]]:
    out = sel.shortlist(goal, REGISTRY, ROOT, 6)
    return ([p["capability_id"] for p in (out.get("proposals") or [])],
            list(out.get("stated_paths_masked_from_the_ask") or []))


def test_a_directory_name_does_not_choose_a_capability() -> None:
    named = "canonical/astra_runtime/tmp/path_token_probe"
    pathlib.Path(ROOT / named).mkdir(parents=True, exist_ok=True)
    (ROOT / "path_token_neutral").mkdir(parents=True, exist_ok=True)
    for goal in ("Tell me what changed in %s today" % named,
                 "Tell me what changed in path_token_neutral today"):
        proposals, masked = _proposals(goal)
        assert "git.history.bisect_regression.v1" not in proposals, (goal, proposals)
        assert all("runtime" not in cid for cid in proposals), (goal, proposals)


def test_the_mask_is_reported_rather_than_silent() -> None:
    named = "canonical/astra_runtime/tmp/path_token_probe"
    pathlib.Path(ROOT / named).mkdir(parents=True, exist_ok=True)
    proposals, masked = _proposals("Tell me what changed in %s today" % named)
    assert masked == [named], masked


def test_a_capability_addressed_by_its_own_id_is_kept() -> None:
    """Some registries carry capability ids that ARE repository paths.

    The live bound-capability registry does not (its ids look like
    `file.stat.v1`), but the unified model's does -- 294 of them. The guard is
    therefore tested against a registry that really contains one, so it cannot
    rot into a line nobody can reach.
    """
    path_id = "canonical/runtime/example_row_v1.py.auto.v1"
    synthetic = dict(REGISTRY)
    synthetic[path_id] = {
        "status": "VERIFIED_BOUND_CAPABILITY",
        "action_template": {"type": "invoke_capability", "args": {}},
        "keywords": ["summarise", "summary"],
        "provides": ["summary.output"],
    }
    _kept, masked = _mask_against("Summarise " + path_id, synthetic)
    assert masked == [], masked


def _mask_against(goal: str, registry: dict) -> tuple[list[str], list[str]]:
    out = sel.shortlist(goal, registry, ROOT, 6)
    return ([p["capability_id"] for p in (out.get("proposals") or [])],
            list(out.get("stated_paths_masked_from_the_ask") or []))


def test_a_stated_source_file_is_data_and_the_rows_it_names_still_rank() -> None:
    """Masking a path must not weaken the request that names it."""
    named = "canonical/astra_runtime/tmp/path_token_probe/notes.txt"
    pathlib.Path(ROOT / named).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / named).write_text("alpha\nbeta\n", encoding="utf-8")
    proposals, masked = _proposals("Count the lines in " + named)
    assert masked == [named], masked
    assert "file.line_count.v1" in proposals, proposals


def test_a_sentence_that_is_only_a_path_keeps_its_reading() -> None:
    """No query left means the mask does not apply, rather than RELEVANCE_UNRESOLVED."""
    out = sel.shortlist("canonical/astra_runtime/tmp/path_token_probe", REGISTRY, ROOT, 6)
    assert out.get("ranker_reason") != "OBJECTIVE_REQUIRED", out.get("ranker_reason")
    assert list(out.get("stated_paths_masked_from_the_ask") or []) == [], out


def test_the_ask_itself_still_ranks() -> None:
    """Masking paths must not weaken an ordinary request that names a file."""
    named = "canonical/astra_runtime/tmp/path_token_probe/notes.txt"
    (ROOT / named).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / named).write_text("alpha\nbeta\n", encoding="utf-8")
    proposals, _masked = _proposals("Count the lines in " + named)
    assert "file.line_count.v1" in proposals, proposals


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
