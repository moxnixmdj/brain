"""Tests for the answer fingerprint: a deletion's proof, and the bug the proof found.

The instrument exists to make one sentence checkable -- "this deletion removed code the runtime
did not reach". Pinned here: that comparison is exact, that the question set is the ledger's 404
exact targets, and that the runtime now answers the same question the same way in two processes
(it did not, for 1 of 404, until the float accumulation order was fixed).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import runtime_answer_fingerprint_v1 as F  # noqa: E402

TOOL = ROOT / "canonical/tools/runtime_answer_fingerprint_v1.py"


def test_compare_is_exact_not_approximate() -> None:
    a = {"digest": "x", "n": 2, "answers": [{"module": "m/a.py", "stem": "a", "find": ["p"], "route": ["q"]},
                                            {"module": "m/b.py", "stem": "b", "find": ["p2"], "route": []}]}
    b = json.loads(json.dumps(a))
    assert F.compare(a, b)["verdict"] == "UNCHANGED"
    b["answers"][1]["find"] = ["p3"]
    result = F.compare(a, b)
    assert result["verdict"] == "CHANGED"
    assert result["answers_moved"] == 1 and result["moved_stems"] == ["m/b.py"]
    # Same digest, different answers: the verdict must still say CHANGED.
    c = json.loads(json.dumps(a))
    c["answers"][0]["find"] = ["p9"]
    assert F.compare(a, c)["verdict"] == "CHANGED"


def test_questions_are_the_ledger_exact_targets() -> None:
    rows = F.questions(ROOT)
    assert len(rows) == 404
    assert all(row["query"] and row["stem"] for row in rows)
    assert len({row["module"] for row in rows}) == len(rows)
    assert len({row["stem"] for row in rows}) < len(rows), "two ledger rows share a stem: key by path"


def test_the_runtime_answers_the_same_question_the_same_way_in_two_processes() -> None:
    """The bug: idf contributions were summed in set order, so near-ties moved with the hash seed."""
    digests = []
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = ROOT / f"canonical/verification/.fingerprint_seed_{seed}.json"
        subprocess.run([sys.executable, str(TOOL), "--out", str(out)], check=True,
                       capture_output=True, env=env, cwd=str(ROOT))
        digests.append(json.loads(out.read_text())["digest"])
        out.unlink()
    assert digests[0] == digests[1], "answers depend on the hash seed again"


def test_the_deletion_receipt_says_it_moved_nothing() -> None:
    receipt = json.loads((ROOT / "canonical/verification/DELETION_RECEIPT_CONTRACT_GATE_20261127_V1.json").read_text())
    assert receipt["n_questions"] == 404
    assert receipt["deletion_moved_answers"] == 0
    assert receipt["fingerprint_with_gate"] == receipt["fingerprint_without_gate"]
    assert receipt["determinism_finding"]["answers_moved_by_fix"] == 1
    assert not (ROOT / "canonical/tools/contract_first_routing_v1.py").exists()
