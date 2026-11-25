"""Tests for Generalized Live-Frame Differential Witness Inversion (`differential_witness_inversion_v1`)
and its integration with `CausalCEGISInventor` and `SemanticCausalLawStore`.
"""
from __future__ import annotations

import pathlib
import subprocess

from canonical.swe_kernel.causal_cegis_inventor_v1 import CausalCEGISInventor
from canonical.swe_kernel.differential_witness_inversion_v1 import (
    SCHEMA,
    _select_sibling_passing_tests,
)


def test_schema_and_pinned_witness_inversion_unchanged() -> None:
    assert SCHEMA == "BRAIN_DIFFERENTIAL_WITNESS_INVERSION_V1"
    diff = subprocess.run(
        ["git", "diff", "--", "canonical/swe_kernel/witness_inversion_v1.py"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert diff.stdout == ""


def test_select_sibling_passing_tests_balances_positive_and_negative_cases() -> None:
    failing = ["tests/test_spec.py::TestSpec::test_match[2rc1-==2.0.*-True]"]
    passing = [
        f"tests/test_spec.py::TestSpec::test_match[1.{i}-==1.{i}-True]"
        for i in range(10)
    ] + [
        f"tests/test_spec.py::TestSpec::test_match[1.{i}-==2.0.*-False]"
        for i in range(6)
    ]
    picked = _select_sibling_passing_tests(failing, passing, limit=8)
    assert len(picked) == 8
    assert any("False]" in p for p in picked)
    assert any("True]" in p for p in picked)


def test_pep570_posonly_type_guard_and_law_crystallization(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo_posonly"
    pkg = repo / "src" / "minitoml"
    tests = repo / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)

    (pkg / "__init__.py").write_text("from ._core import loads\n", encoding="utf-8")
    (pkg / "_core.py").write_text(
        "def loads(__s: str, /) -> dict:\n"
        "    cleaned = __s.replace('\\r\\n', '\\n')\n"
        "    return {'lines': cleaned.splitlines()}\n",
        encoding="utf-8",
    )
    (tests / "test_loads.py").write_text(
        "import unittest\n"
        "from minitoml import loads\n\n"
        "class TestLoads(unittest.TestCase):\n"
        "    def test_valid(self):\n"
        "        self.assertEqual(loads('a=1'), {'lines': ['a=1']})\n\n"
        "    def test_bytes_rejected(self):\n"
        "        with self.assertRaises(TypeError) as ctx:\n"
        "            loads(b'a=1')\n"
        "        self.assertEqual(str(ctx.exception), \"Expected str object, not 'bytes'\")\n",
        encoding="utf-8",
    )

    inv = CausalCEGISInventor(
        law_store_path=tmp_path / "laws.json",
        negative_store_path=tmp_path / "neg.json",
        sandbox_budget=18,
    )
    res = inv.solve_repository(repo, language="python", test_target="tests/test_loads.py")
    assert res.solved is True
    assert res.mechanism == "COGS_LIVE_DIFFERENTIAL_WITNESS_INVERSION"
    assert res.crystallized_law_id is not None
    assert res.source_tree_unchanged is True
    assert "isinstance(__s, str)" in res.unified_diff


def test_reexport_module_invariant_with_instantiation_lhs(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo_reexport"
    pkg = repo / "mypkg"
    tests = repo / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)

    (pkg / "_impl.py").write_text(
        "class DecodeError(ValueError):\n"
        "    pass\n",
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text(
        "from mypkg._impl import DecodeError\n",
        encoding="utf-8",
    )
    (tests / "test_err.py").write_text(
        "import unittest\n"
        "import mypkg\n\n"
        "class TestErr(unittest.TestCase):\n"
        "    def test_module_attr(self):\n"
        "        self.assertEqual(mypkg.DecodeError().__module__, 'mypkg')\n",
        encoding="utf-8",
    )

    inv = CausalCEGISInventor(
        law_store_path=tmp_path / "laws_mod.json",
        negative_store_path=tmp_path / "neg_mod.json",
        sandbox_budget=16,
    )
    res = inv.solve_repository(repo, language="python", test_target="tests/test_err.py")
    assert res.solved is True
    assert res.mechanism == "COGS_LIVE_DIFFERENTIAL_WITNESS_INVERSION"
    assert "DecodeError.__module__ = 'mypkg'" in res.unified_diff


def test_body_only_keyerror_ignores_return_annotation_subscript(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo_keyerr"
    pkg = repo / "cfgpkg"
    tests = repo / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)

    (pkg / "__init__.py").write_text(
        "from typing import Union\n\n"
        "def read_flag(env: dict, key: str) -> Union[str, bool, None]:\n"
        "    return env[key]\n",
        encoding="utf-8",
    )
    (tests / "test_cfg.py").write_text(
        "from cfgpkg import read_flag\n\n"
        "def test_present():\n"
        "    assert read_flag({'A': '1'}, 'A') == '1'\n\n"
        "def test_missing_returns_none():\n"
        "    assert read_flag({}, 'MISSING') is None\n",
        encoding="utf-8",
    )

    inv = CausalCEGISInventor(
        law_store_path=tmp_path / "laws_ke.json",
        negative_store_path=tmp_path / "neg_ke.json",
        sandbox_budget=16,
    )
    res = inv.solve_repository(repo, language="python", test_target="tests/test_cfg.py")
    assert res.solved is True
    assert "env.get(key)" in res.unified_diff


def test_prefix_slice_discovery_recall_and_surgical_remove_law_ablation(
    tmp_path: pathlib.Path,
) -> None:
    repo_a = tmp_path / "repo_a"
    (repo_a / "verpkg").mkdir(parents=True)
    (repo_a / "tests").mkdir(parents=True)
    (repo_a / "verpkg" / "__init__.py").write_text(
        "def match_prefix(padded_ver: list, split_spec: list) -> bool:\n"
        "    shortened = padded_ver[:len(split_spec)]\n"
        "    return shortened == split_spec\n",
        encoding="utf-8",
    )
    (repo_a / "tests" / "test_ver.py").write_text(
        "import pytest\n"
        "from verpkg import match_prefix\n\n"
        "@pytest.mark.parametrize('pv,sp,exp', [\n"
        "    ([2, 0, 1], [2, 0], True),\n"
        "    ([2, 1], [2, 0], False),\n"
        "    ([2], [2, 0], True),\n"
        "])\n"
        "def test_prefix(pv, sp, exp):\n"
        "    assert match_prefix(pv, sp) is exp\n",
        encoding="utf-8",
    )

    repo_b = tmp_path / "repo_b"
    (repo_b / "otherpkg").mkdir(parents=True)
    (repo_b / "tests").mkdir(parents=True)
    (repo_b / "otherpkg" / "__init__.py").write_text(
        "def check_segments(full_parts: list, target_parts: list) -> bool:\n"
        "    trimmed = full_parts[:len(target_parts)]\n"
        "    return trimmed == target_parts\n",
        encoding="utf-8",
    )
    (repo_b / "tests" / "test_seg.py").write_text(
        "import pytest\n"
        "from otherpkg import check_segments\n\n"
        "@pytest.mark.parametrize('fp,tp,exp', [\n"
        "    ([3, 1, 4], [3, 1], True),\n"
        "    ([3, 2], [3, 1], False),\n"
        "    ([3], [3, 0], True),\n"
        "])\n"
        "def test_seg(fp, tp, exp):\n"
        "    assert check_segments(fp, tp) is exp\n",
        encoding="utf-8",
    )

    inv = CausalCEGISInventor(
        law_store_path=tmp_path / "laws_xfer.json",
        negative_store_path=tmp_path / "neg_xfer.json",
        sandbox_budget=20,
    )
    r_disc = inv.solve_repository(repo_a, language="python", test_target="tests/test_ver.py")
    assert r_disc.solved is True
    assert r_disc.crystallized_law_id is not None

    r_rec = inv.solve_repository(repo_b, language="python", test_target="tests/test_seg.py")
    assert r_rec.solved is True
    assert r_rec.mechanism == f"SEMANTIC_LAW_RECALL:{r_disc.crystallized_law_id}"

    assert inv.law_store.remove_law(r_disc.crystallized_law_id) is True
    r_abl = inv.solve_repository(repo_b, language="python", test_target="tests/test_seg.py")
    assert r_abl.solved is True
    assert not r_abl.mechanism.startswith("SEMANTIC_LAW_RECALL:")
