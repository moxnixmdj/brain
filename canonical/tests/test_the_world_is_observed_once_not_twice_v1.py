#!/usr/bin/env python3
"""Observing the world must cost one walk per root, and must abort the walk it cannot afford.

`observe_world` is the third authority: what the filesystem says, not what the tool reports.
It runs before AND after every solve, so its cost is paid twice per request.

It used to walk each observation root **twice**:

    count = sum(1 for _ in root.rglob("*"))      # a full walk, purely to decide
    if count > _OBSERVATION_MAX_FILES: continue  # ... whether to walk it again
    _kernel._snapshot(str(root))                 # the walk that produces the answer

The guard was therefore paying the exact cost it existed to avoid, and the answer walk paid
it again.  Measured on the AST-audit sentence: 22 101 pathlib `_parse_args` calls and
0.12 s per observation -- more than compiling the goal and running the capability together.

The rewrite is one `os.scandir` pass that counts as it goes and gives up the moment a tree
is too large.  These tests hold both halves of that sentence: ONE walk, and the abort.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402


def _tree(base: pathlib.Path, files: int) -> pathlib.Path:
    (base / "pkg").mkdir(parents=True, exist_ok=True)
    for i in range(files):
        (base / "pkg" / ("m%d.py" % i)).write_text("x = %d\n" % i, encoding="utf-8")
    return base


def test_the_answer_walk_is_the_only_walk(tmp_path):
    base = _tree(tmp_path / "repo", 5)
    observed = adm._observe_tree(base, 4000)
    assert observed is not None
    assert len(observed) == 5
    assert all(key.startswith("pkg/") for key in observed)
    assert all(isinstance(val, tuple) and len(val) == 2 for val in observed.values())


def test_a_tree_over_the_cap_is_abandoned_instead_of_walked(tmp_path):
    base = _tree(tmp_path / "repo", 12)
    assert adm._observe_tree(base, 5) is None


def test_the_observation_never_uses_a_second_rglob(tmp_path):
    """The regression is a shape, not a timing: a second walk reappears as an rglob here."""
    source = pathlib.Path(adm.__file__).read_text(encoding="utf-8")
    observation = source.split("def _observe_tree(", 1)[1].split("\ndef ", 1)[0]
    # strip the docstring: it QUOTES the defect it replaced, which is not the defect
    observation = observation.split('"""', 2)[2] if observation.count('"""') >= 2 else observation
    assert "rglob" not in observation
    assert "scandir" in observation
    # and the count-then-walk pair that caused it must not come back.  The docstring
    # that explains the fix quotes the old line, so only CODE is searched.
    code = "\n".join(line for line in source.splitlines()
                     if not line.lstrip().startswith("#"))
    body = code.split("def observe_world(", 1)[1].split("\ndef ", 1)[0]
    assert "sum(1 for _ in root.rglob" not in body


def test_hidden_directories_are_skipped_like_the_kernel_skips_them(tmp_path):
    base = _tree(tmp_path / "repo", 2)
    (base / "__pycache__").mkdir()
    (base / "__pycache__" / "junk.pyc").write_bytes(b"\x00")
    (base / ".git").mkdir()
    (base / ".git" / "HEAD").write_text("ref\n", encoding="utf-8")
    observed = adm._observe_tree(base, 4000) or {}
    assert not [k for k in observed if k.startswith(("__pycache__", ".git"))]
