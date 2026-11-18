"""Tests for the renewability measurement.

Each rule here exists because it cost a measured error in this round:

  * a module that MOVES (packaging/ -> src/packaging/) is the same module -- keying by path made the
    biggest bump of the corpus report "nothing changed";
  * a module that does not import at the old revision taught nothing and is excluded, not counted as moved;
  * an arm that never RETURNED at the old revision was never learned -- a different exception at the new
    revision is not the environment moving a learned action (this inflated the moved set from 13 to 33);
  * a moved action must be split by KIND (removed / now raises / value changed), never added together;
  * blindness is per WITNESS as well as per prefix, because "learn it once" means one arbitrary witness.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import renewable_action_v1 as R  # noqa: E402

OLD = '''\
ALLOWED = {"x86_64", "aarch64"}


def accepts(arch):
    return arch in ALLOWED


def version_split(text):
    return text.split(".")


def constant():
    return 1
'''

# a major-style move: one action now raises, one action's value changes, one never moves
NEW = '''\
ALLOWED = {"x86_64", "aarch64"}


def accepts(arch, extra):
    return arch in ALLOWED


def version_split(text):
    return text.split(".") if text else []


def constant():
    return 1
'''


def _trees(tmp_path: pathlib.Path, old: str, new: str) -> tuple[pathlib.Path, pathlib.Path]:
    old_tree, new_tree = tmp_path / "old", tmp_path / "new"
    for tree, source in ((old_tree, old), (new_tree, new)):
        package = tree / "pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "core.py").write_text(source, encoding="utf-8")
    return old_tree, new_tree


def _row(tmp_path: pathlib.Path, old: str = OLD, new: str = NEW) -> dict:
    old_tree, new_tree = _trees(tmp_path, old, new)
    return R.measure_module(old_tree, new_tree, "pkg/core.py", "pkg.core")


def test_schema_and_zero_model(tmp_path):
    report = R.measure(tmp_path / "cache", tmp_path / "work", limit=0)
    assert report["schema"] == "BRAIN_RENEWABLE_ACTION_V1"
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert report["totals"]["callables"] == 0


def test_witnesses_are_deterministic_and_drawn_from_the_module_then_the_neutral_tokens():
    first = R.witnesses(OLD)
    assert first == R.witnesses(OLD)
    assert any(token.startswith("=") for token in first)
    assert first[-1] in R.NEUTRAL


def test_the_split_is_a_fixed_rule_not_a_seed():
    learned, held_out = R.split(R.witnesses(OLD))
    assert learned == R.witnesses(OLD)[0::2]
    assert held_out == R.witnesses(OLD)[1::2]


def test_the_structural_observable_is_the_declaration_not_the_behaviour():
    assert R.signatures(OLD)["accepts"] != R.signatures(NEW)["accepts"]
    assert R.signatures(OLD)["constant"] == R.signatures(NEW)["constant"]


def test_a_signature_change_is_caught_but_must_be_classified_by_kind(tmp_path):
    row = _row(tmp_path)
    entries = {entry["function"]: entry for entry in row["callables"]}
    assert entries["accepts"]["state"] in ("CAUGHT", "BLIND")
    assert entries["accepts"]["kind"] == "NOW_RAISES"


def test_an_action_that_never_moves_is_stable(tmp_path):
    row = _row(tmp_path)
    entries = {entry["function"]: entry for entry in row["callables"]}
    assert entries["constant"]["state"] == "STABLE"


def test_a_module_that_does_not_import_at_old_is_excluded_not_counted_as_moved(tmp_path):
    broken = "import a_module_that_does_not_exist\n\n\ndef accepts(arch):\n    return True\n"
    old_tree, new_tree = _trees(tmp_path, broken, broken.replace("True", "False"))
    row = R.measure_module(old_tree, new_tree, "pkg/core.py", "pkg.core")
    assert row["state"] == "MODULE_DOES_NOT_IMPORT_AT_OLD"


def test_an_arm_that_never_returned_at_old_is_not_a_learned_action(tmp_path):
    """Wrong-typed arguments raise in BOTH revisions; that is the instrument, not the environment."""
    needs_object = "def parse(parser):\n    return parser.pos\n"
    changed = "def parse(parser):\n    return parser.position\n"
    old_tree, new_tree = _trees(tmp_path, needs_object, changed)
    row = R.measure_module(old_tree, new_tree, "pkg/core.py", "pkg.core")
    entries = {entry["function"]: entry for entry in row["callables"]}
    assert entries["parse"]["state"] == "NEVER_OBSERVED_AT_OLD"


def test_nondeterminism_at_the_same_revision_is_excluded_and_named(tmp_path):
    import random
    flaky = "import random\n\n\ndef wobble(seed):\n    return random.random()\n"
    old_tree, new_tree = _trees(tmp_path, flaky, flaky)
    row = R.measure_module(old_tree, new_tree, "pkg/core.py", "pkg.core")
    entries = {entry["function"]: entry for entry in row["callables"]}
    assert entries["wobble"]["state"] == "EXCLUDED_UNSTABLE"


def test_kinds_are_never_added_together():
    assert R._kind({"old": "RETURNED|bool|True", "new": "NOT_CALLABLE||"}) == "REMOVED"
    assert R._kind({"old": "RETURNED|bool|True", "new": "RAISED|TypeError|"}) == "NOW_RAISES"
    assert R._kind({"old": "RETURNED|list|['a']", "new": "RETURNED|list|['a','b']"}) == "VALUE_CHANGED"


def test_a_module_that_move_paths_is_the_same_module(tmp_path):
    """packaging 21.0 has packaging/, 24.0 has src/packaging/: one module, not a disappearance."""
    old_tree = tmp_path / "o"
    new_tree = tmp_path / "n"
    (old_tree / "pkg").mkdir(parents=True)
    (old_tree / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (old_tree / "pkg" / "core.py").write_text(OLD, encoding="utf-8")
    (new_tree / "src" / "pkg").mkdir(parents=True)
    (new_tree / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (new_tree / "src" / "pkg" / "core.py").write_text(NEW, encoding="utf-8")
    old_modules, new_modules = R.package_modules(old_tree), R.package_modules(new_tree)
    assert "pkg.core" in old_modules and "pkg.core" in new_modules


def test_per_witness_risk_is_reported_for_every_move(tmp_path):
    row = _row(tmp_path)
    moved = [entry for entry in row["callables"] if entry.get("per_witness")]
    assert moved, row
    for entry in moved:
        stats = entry["per_witness"]
        assert stats["learned_arms"] >= 1
        assert 0.0 <= stats["blind_risk"] <= 1.0


def test_headline_reports_every_class_apart():
    report = {"totals": {"callables": 76, "modules": 22, "STABLE": 29, "CAUGHT": 13, "BLIND": 0,
                         "moved": 13, "blind_fraction_of_moved": 0.0,
                         "blind_and_structural": 0, "blind_and_identical_signature": 0,
                         "EXCLUDED_UNSTABLE": 4, "modules_excluded_import": 1}}
    line = R._headline(report)
    assert "76 learned actions" in line
    assert "13 moved" in line
    assert "0 were NOT" in line
    assert "vocabulary gap" in line
