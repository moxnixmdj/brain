"""The authority record must describe the runtime it authorises.

Measured 2026-11-09: CURRENT_TERMINAL_AUTHORITY.json pinned d0b1cceffc8c (fabric),
7dd0dd00cf40 (invoker) and 3867b354c878 (subruntime). The live blobs were 6c2cda114146,
d4500529fc3c and fe86b355746f. The R1 closure gate had been failing ever since, and nobody
ran it.

A hash pin that nobody re-checks is decoration. This test re-checks it, so the next drift
is a failing test rather than a silent false claim.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

FABRIC = "canonical/runtime/unified_cognitive_fabric_v1.py"
INVOKER = "canonical/runtime/live_capability_invoker_v1.py"
SUBRUNTIME = "canonical/runtime/live_brain_runtime_v1.py"


def _blob(rel: str) -> str:
    return subprocess.run(["git", "hash-object", rel], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


def test_the_authority_record_exists():
    assert AUTHORITY.is_file()
    json.loads(AUTHORITY.read_text())


def test_pinned_fabric_blob_matches_the_live_file():
    d = json.loads(AUTHORITY.read_text())
    node = d["live_capability_ownership_20261008_v1"]["unified_fabric"]
    assert node["git_blob_sha"] == _blob(FABRIC), (
        "authority pins a fabric it no longer describes -- re-pin and record the previous sha")


def test_pinned_invoker_blob_matches_the_live_file():
    d = json.loads(AUTHORITY.read_text())
    node = d["live_capability_ownership_20261008_v1"]["invoker"]
    assert node["git_blob_sha"] == _blob(INVOKER)


def test_pinned_subruntime_blob_matches_the_live_file():
    d = json.loads(AUTHORITY.read_text())
    node = d["live_capability_ownership_20261008_v1"]["subordinate_runtime"]
    assert node["git_blob_sha"] == _blob(SUBRUNTIME)


def test_a_repin_leaves_the_previous_sha_visible():
    """Drift history must survive the repair, or the repair hides the evidence."""
    d = json.loads(AUTHORITY.read_text())
    node = d["live_capability_ownership_20261008_v1"]["unified_fabric"]
    assert "git_blob_sha_previous" in node
    assert node["git_blob_sha_previous"] != node["git_blob_sha"]


def test_the_r1_gate_now_reports_closure():
    """The end-to-end gate, not just the pins: the fabric must close over its authority."""
    from canonical.runtime.unified_cognitive_fabric_v1 import catalog

    c = catalog()
    assert c["r1_structural_closure"] is True, c.get("known_r1_residuals")
    assert c["known_r1_residuals"] == []


# ---------------------------------------------------------------------------
# The false PASS this class produces.
#
# Re-pinning the authority to whatever the working tree currently contains makes
# the check answer "identical to itself": true by construction, and worthless.
# A pin is only meaningful if it names bytes that are IN A COMMIT. If the file
# has uncommitted edits, the pin describes code nobody has reviewed, nobody has
# run in CI, and that may never exist again.
#
# Source: daniel-ospina/agent-infra#3120 -- "REFUSES to compare against a tree
# that is not the pin ... A check that answers 'identical to the wrong tree' is
# the false PASS this class produces." And: "cannot-verify is never a pass."
# ---------------------------------------------------------------------------

PINS = [
    ("unified_fabric", FABRIC),
    ("invoker", INVOKER),
    ("subordinate_runtime", SUBRUNTIME),
]


def _head_blob(rel: str) -> str:
    return subprocess.run(["git", "rev-parse", f"HEAD:{rel}"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


def _dirty(rel: str) -> bool:
    out = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=ROOT,
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def test_the_pin_names_committed_bytes_not_a_working_tree():
    """A pin to uncommitted bytes is self-consistent and meaningless."""
    for node, rel in PINS:
        assert not _dirty(rel), (
            f"{rel} has uncommitted edits, so the authority pins bytes that are in no "
            "commit. Commit the runtime before re-pinning, or the pin is decoration.")


def test_the_pin_matches_head_not_merely_the_working_tree():
    """The stronger of the two equalities: the pin must survive a fresh clone."""
    d = json.loads(AUTHORITY.read_text())
    for node, rel in PINS:
        head = _head_blob(rel)
        assert head, f"cannot resolve HEAD:{rel} -- cannot-verify is never a pass"
        assert d["live_capability_ownership_20261008_v1"][node]["git_blob_sha"] == head, (
            f"{node}: pinned sha does not equal HEAD:{rel}. Re-pinning to a working-tree "
            "blob would make this test pass and the pin meaningless.")
