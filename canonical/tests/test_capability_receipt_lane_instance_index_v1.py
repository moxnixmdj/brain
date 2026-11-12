"""An instance index, so "run it again" stops meaning "run it on the same input".

Round 17 measured that all 296 independently verified experiences pass zero arguments, and named the
six-line cause: `declared_probe_args()` fills every `${input.*}` placeholder with a **constant**, so
instance k is instance 1. This round ships the change with the one property that makes it safe —
**instance 0 is byte-identical to what the lane already issued**, so no existing receipt or attestation
is disturbed.

Pinned:

* `_at_instance(base, 0)` returns `base` exactly; index 1 appends a suffix; 2 differs from 1;
* a free-text input becomes a distinct sample (`...#i1`), never a capability id with a suffix bolted
  on; a path input keeps its extension (`...__i1.json`), so the probe sink stays a file;
* `declared_probe_args` and `execute_and_receipt` keep index 0 as their default, so every existing
  caller and every one of the 296 records is untouched;
* the verify path replays the producer's recorded index instead of assuming 0 — a re-run that ignored
  it would attest a different instance than the one receipted;
* the input space is real where it exists: 126 of the 145 curated capabilities declare at least one
  `${input.*}`, so the missing thing was never the inputs — it was varying them.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
CAPABILITY = "code.patch.tree_sitter.verify.v1"
SHA = "0123456789abcdef"


def test_instance_zero_is_exactly_what_the_lane_already_issued():
    assert lane._at_instance("canonical/x/a.json", 0, is_path=True) == "canonical/x/a.json"
    assert lane._at_instance("anything at all", 0, is_path=False) == "anything at all"
    args0 = lane.declared_probe_args(str(ROOT), CAPABILITY, SHA, 0)
    legacy_sink = lane._probe_output_path(CAPABILITY, SHA)
    for key, value in args0.items():
        assert value in (CAPABILITY, legacy_sink), (key, value)


def test_a_later_instance_is_a_different_point_in_the_input_space():
    one = lane.declared_probe_args(str(ROOT), CAPABILITY, SHA, 1)
    two = lane.declared_probe_args(str(ROOT), CAPABILITY, SHA, 2)
    zero = lane.declared_probe_args(str(ROOT), CAPABILITY, SHA, 0)
    assert one != zero and two != one and two != zero
    assert one["edits"].endswith("#i1")
    assert one["output_path"].endswith("__i1.json")


def test_free_text_and_paths_are_treated_differently():
    assert lane._at_instance("cap.id.v1", 3, is_path=False) == "cap.id.v1#i3"
    assert lane._at_instance("d/file.json", 3, is_path=True) == "d/file__i3.json"
    assert lane._at_instance("no_extension", 3, is_path=True) == "no_extension__i3"


def test_the_default_is_still_zero_everywhere_it_matters():
    probe = inspect.signature(lane.declared_probe_args).parameters
    execute = inspect.signature(lane.execute_and_receipt).parameters
    assert probe["instance_index"].default == 0
    assert execute["instance_index"].default == 0


def test_the_verifier_replays_the_producers_instance_not_zero():
    source = (ROOT / "canonical/runtime/capability_receipt_lane_v1.py").read_text(encoding="utf-8")
    assert 'instance_index=int(producer.get("instance_index") or 0)' in source, (
        "a verifier that assumes instance 0 would attest a different instance than was receipted")


def test_the_inputs_were_never_the_missing_thing():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    declaring = [cid for cid, entry in registry.items()
                 if re.search(r"\$\{input\.", json.dumps((entry.get("action_template") or {}).get("args") or {}))]
    assert len(declaring) >= 120, len(declaring)
    assert len(declaring) > len(registry) // 2, "most curated capabilities declare inputs"
