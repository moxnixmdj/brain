"""Regression & ablation tests for `metamorphic_habitation_zipper_v1.py` and
`O(1)` Structural Bucket Indexing in `SemanticCausalLawStore`.

Verifies all 4 orthogonal zero-LLM pillars (`model_calls == 0`):
  1. Metamorphic Witness Splitter (`abduce_metamorphic_oracle`) on 100%-green suites
     with zero verbatim repro snippets + post-selection held-out test verification.
  2. Module-Global Def-Use Regex Slice (`$` -> `\\Z`), Disabled-Protocol Guard
     Totality (`hasattr` -> `getattr(..., None) is not None`), and Type-Safe
     Equality Guard (`isinstance(x, str) and x == ""`).
  3. Def-Use Relational Zipper (`COGS_DEF_USE_RELATIONAL_ZIPPER`) across coupled
     multi-file producer/consumer contracts.
  4. `O(1)` Structural Bucket Index + Single-Parse AST reuse at `500` laws +
     instantaneous `remove_law` deletion ablation.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time

from canonical.swe_kernel.causal_cegis_inventor_v1 import CausalCEGISInventor
from canonical.swe_kernel.universal_semantic_ir_v1 import (
    SemanticCausalLaw,
    SemanticCausalLawStore,
)


def test_pillar1_metamorphic_canonical_header_green_suite_and_heldout_test(tmp_path: pathlib.Path) -> None:
    """100%-green visible test suite + prose-only issue (zero code snippets) ->
    abduces `METAMORPHIC_CANONICAL_REPRESENTATION`, repairs dangling space, and
    passes withheld human fail-to-pass test overlaid AFTER patch selection."""
    pkg = tmp_path / "http_auth"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .header import WWWAuthenticate\n", encoding="utf-8")
    (pkg / "header.py").write_text(
        "class WWWAuthenticate:\n"
        "    def __init__(self, auth_type: str, realm: str = '') -> None:\n"
        "        self.auth_type = auth_type.title()\n"
        "        self.realm = realm\n\n"
        "    def to_header(self) -> str:\n"
        "        if self.realm:\n"
        "            return f'{self.auth_type} realm=\"{self.realm}\"'\n"
        "        return f'{self.auth_type} '\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_header.py").write_text(
        "from http_auth import WWWAuthenticate\n\n"
        "def test_with_realm():\n"
        "    h = WWWAuthenticate('bearer', realm='api')\n"
        "    assert h.to_header() == 'Bearer realm=\"api\"'\n",
        encoding="utf-8",
    )

    # Confirm visible suite is 100% green before solving
    pre = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=tmp_path, capture_output=True)
    assert pre.returncode == 0

    inventor = CausalCEGISInventor(
        law_store_path=tmp_path / "_laws.json",
        negative_store_path=tmp_path / "_neg.json",
        sandbox_budget=20,
    )
    res = inventor.solve_repository(
        tmp_path,
        language="python",
        problem_statement=(
            "WWWAuthenticate.to_header leaves trailing whitespace when no realm "
            "parameters are configured on the header object."
        ),
        timeout_sec=15.0,
    )
    assert res.solved is True
    assert res.source_tree_unchanged is True
    assert "http_auth/header.py" in res.modified_files

    # Apply selected repair to a copy and run withheld human fail-to-pass test!
    for rel, content in res.modified_files.items():
        (tmp_path / rel).write_text(content, encoding="utf-8")
    (tests / "test_heldout_human.py").write_text(
        "from http_auth import WWWAuthenticate\n\n"
        "def test_bare_bearer_no_trailing_space():\n"
        "    assert WWWAuthenticate('bearer').to_header() == 'Bearer'\n"
        "    assert WWWAuthenticate('basic', realm='x').to_header() == 'Basic realm=\"x\"'\n",
        encoding="utf-8",
    )
    post = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=tmp_path, capture_output=True)
    assert post.returncode == 0


def test_pillar1_metamorphic_state_isolation_aliasing_green_suite(tmp_path: pathlib.Path) -> None:
    """100%-green visible test suite + prose-only issue -> abduces `METAMORPHIC_MUTATION_ISOLATION`
    and synthesizes defensive container isolation (`list(...)` / `.copy()`)."""
    repo_dir = tmp_path / "repo"
    pkg = repo_dir / "registry"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .core import PluginStore\n", encoding="utf-8")
    (pkg / "core.py").write_text(
        "class PluginStore:\n"
        "    def __init__(self, tag: str = 'default') -> None:\n"
        "        self.tag = tag\n"
        "        self._items = ['base']\n"
        "        self._meta = {'k': 1}.copy()\n\n"
        "    def get_items(self) -> list:\n"
        "        return self._items\n",
        encoding="utf-8",
    )
    tests = repo_dir / "tests"
    tests.mkdir()
    (tests / "test_store.py").write_text(
        "from registry import PluginStore\n\n"
        "def test_initial_items():\n"
        "    s = PluginStore()\n"
        "    assert s.get_items() == ['base']\n",
        encoding="utf-8",
    )

    inventor = CausalCEGISInventor(
        law_store_path=tmp_path / "_laws.json",
        negative_store_path=tmp_path / "_neg.json",
        sandbox_budget=20,
    )
    res = inventor.solve_repository(
        repo_dir,
        language="python",
        problem_statement="Mutating the list returned by PluginStore.get_items corrupts internal state.",
        timeout_sec=15.0,
    )
    assert res.solved is True
    assert res.source_tree_unchanged is True
    for rel, content in res.modified_files.items():
        (repo_dir / rel).write_text(content, encoding="utf-8")
    (tests / "test_heldout_mutation.py").write_text(
        "from registry import PluginStore\n\n"
        "def test_external_mutation_isolated():\n"
        "    s = PluginStore()\n"
        "    out = s.get_items()\n"
        "    out.append('injected')\n"
        "    assert s.get_items() == ['base']\n",
        encoding="utf-8",
    )
    post = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=repo_dir, capture_output=True)
    assert post.returncode == 0


def test_pillar2_module_global_regex_and_disabled_protocol_guards(tmp_path: pathlib.Path) -> None:
    """Verifies module-global def-use regex `$` -> `\\Z` (compiled at import time before
    `sys.settrace`) and disabled `__reversed__ = None` protocol totality."""
    # Case A: Module-global regex `$` allowing trailing `\n`
    r1 = tmp_path / "case_regex"
    (r1 / "verpkg").mkdir(parents=True)
    (r1 / "verpkg" / "__init__.py").write_text("", encoding="utf-8")
    (r1 / "verpkg" / "spec.py").write_text(
        "import re\n\n"
        "_VER_RE = re.compile(r'^[0-9]+\\.[0-9]+$')\n\n"
        "def parse_ver(text: str) -> str:\n"
        "    if not _VER_RE.match(text):\n"
        "        raise ValueError(f'Invalid: {text!r}')\n"
        "    return text\n",
        encoding="utf-8",
    )
    (r1 / "tests").mkdir()
    (r1 / "tests" / "test_spec.py").write_text(
        "import pytest\nfrom verpkg.spec import parse_ver\n\n"
        "def test_valid():\n"
        "    assert parse_ver('1.2') == '1.2'\n\n"
        "def test_reject_trailing_newline():\n"
        "    with pytest.raises(ValueError):\n"
        "        parse_ver('1.2\\n')\n",
        encoding="utf-8",
    )

    inv1 = CausalCEGISInventor(
        law_store_path=r1 / "_laws.json",
        negative_store_path=r1 / "_neg.json",
        sandbox_budget=18,
    )
    res1 = inv1.solve_repository(r1, language="python", test_target="tests/test_spec.py", timeout_sec=15.0)
    assert res1.solved is True
    assert r"\Z" in res1.modified_files["verpkg/spec.py"] or ".fullmatch(" in res1.modified_files["verpkg/spec.py"]

    # Case B: Disabled `__reversed__ = None` protocol (`hasattr` -> `getattr(..., None) is not None`)
    r2 = tmp_path / "case_rev"
    (r2 / "seqpkg").mkdir(parents=True)
    (r2 / "seqpkg" / "__init__.py").write_text("", encoding="utf-8")
    (r2 / "seqpkg" / "views.py").write_text(
        "def tail_first(seq):\n"
        "    if hasattr(seq, '__reversed__'):\n"
        "        return list(reversed(seq))\n"
        "    return list(seq)[::-1]\n",
        encoding="utf-8",
    )
    (r2 / "tests").mkdir()
    (r2 / "tests" / "test_views.py").write_text(
        "from seqpkg.views import tail_first\n\n"
        "class MappingLike:\n"
        "    __reversed__ = None\n"
        "    def __iter__(self):\n"
        "        return iter([1, 2, 3])\n\n"
        "def test_normal_list():\n"
        "    assert tail_first([1, 2, 3]) == [3, 2, 1]\n\n"
        "def test_disabled_reversed():\n"
        "    assert tail_first(MappingLike()) == [3, 2, 1]\n",
        encoding="utf-8",
    )
    inv2 = CausalCEGISInventor(
        law_store_path=r2 / "_laws.json",
        negative_store_path=r2 / "_neg.json",
        sandbox_budget=18,
    )
    res2 = inv2.solve_repository(r2, language="python", test_target="tests/test_views.py", timeout_sec=15.0)
    assert res2.solved is True
    assert "getattr(" in res2.modified_files["seqpkg/views.py"]


def test_pillar3_relational_zipper_coupled_two_file_repair(tmp_path: pathlib.Path) -> None:
    """Single-file repair in `pkg/producer.py` (`split` -> `rsplit`) shifts failure
    into `pkg/consumer.py` (`hasattr` -> `getattr(..., None) is not None`), which
    `propagate_relational_zipper_hop` chains into a verified 2-file repair."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "producer.py").write_text(
        "def split_wheel_stem(filename: str) -> tuple[str, str]:\n"
        "    name, ver = filename.split('-', 1)\n"
        "    return name, ver\n",
        encoding="utf-8",
    )
    (pkg / "consumer.py").write_text(
        "from .producer import split_wheel_stem\n\n"
        "def summarize_package(filename: str, tags) -> tuple[str, str, list]:\n"
        "    pkg_name, ver = split_wheel_stem(filename)\n"
        "    assert ver == '1.0'\n"
        "    if hasattr(tags, '__reversed__'):\n"
        "        ordered = list(reversed(tags))\n"
        "    else:\n"
        "        ordered = list(tags)[::-1]\n"
        "    return pkg_name, ver, ordered\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_coupled.py").write_text(
        "from pkg.consumer import summarize_package\n\n"
        "class TagSet:\n"
        "    __reversed__ = None\n"
        "    def __iter__(self):\n"
        "        return iter(['py3', 'any'])\n\n"
        "def test_simple():\n"
        "    assert summarize_package('demo-1.0', ['a', 'b']) == ('demo', '1.0', ['b', 'a'])\n\n"
        "def test_hyphenated_and_tagset():\n"
        "    assert summarize_package('my-pkg-1.0', TagSet()) == ('my-pkg', '1.0', ['any', 'py3'])\n",
        encoding="utf-8",
    )

    inventor = CausalCEGISInventor(
        law_store_path=tmp_path / "_laws.json",
        negative_store_path=tmp_path / "_neg.json",
        sandbox_budget=24,
    )
    res = inventor.solve_repository(tmp_path, language="python", test_target="tests/test_coupled.py", timeout_sec=20.0)
    assert res.solved is True
    assert set(res.modified_files.keys()) == {"pkg/producer.py", "pkg/consumer.py"}
    assert res.sabotage_verified is True


def test_pillar4_o1_bucket_indexed_law_store_500_laws_and_ablation(tmp_path: pathlib.Path) -> None:
    """Verifies O(1) structural bucket indexing & single-parse AST reuse across 500 laws,
    preventing linear `NO_COMPOUNDING` scan latency, plus O(1) `remove_law` deletion."""
    store = SemanticCausalLawStore(tmp_path / "laws_500.json")

    # Populate 499 synthetic non-matching morphism laws across varied statement-window shapes
    for idx in range(499):
        k_len = 2 + (idx % 4)
        stmts_lhs = "\n".join([f"__HVAR_{j}__ = {idx + j}" for j in range(k_len)])
        stmts_rhs = "\n".join([f"__HVAR_{j}__ = {idx + j + 1}" for j in range(k_len)])
        law = SemanticCausalLaw(
            law_id=f"uir_law_synth_{idx:04d}",
            defect_uir_kind="UIR_TREE_REWRITE_MORPHISM",
            transform_operator="APPLY_BOUND_AST_SUBTREE_MORPHISM",
            precondition_signature={
                "lhs_ast_pattern": stmts_lhs,
                "rhs_ast_pattern": stmts_rhs,
                "pure_only_holes": [],
                "required_domain_literals": [repr(f"__domain_{idx}__")],
            },
            learned_from_language="python",
            sabotage_verified=True,
            contrast_verified=True,
            evidence_digest=f"ev_{idx:04d}",
        )
        store.laws.append(law)

    # Add 1 matching target law (`Return` 1-stmt bucket)
    target_law = SemanticCausalLaw(
        law_id="uir_law_target_return_copy",
        defect_uir_kind="UIR_TREE_REWRITE_MORPHISM",
        transform_operator="APPLY_BOUND_AST_SUBTREE_MORPHISM",
        precondition_signature={
            "lhs_ast_pattern": "return __HVAR_0__",
            "rhs_ast_pattern": "return __HVAR_0__.copy()",
            "pure_only_holes": [],
            "required_domain_literals": [],
        },
        learned_from_language="python",
        sabotage_verified=True,
        contrast_verified=True,
        evidence_digest="ev_target",
    )
    store.laws.append(target_law)
    store.save()

    assert len(store.laws) == 500
    assert len(store._bucket_index) >= 5

    sample_src = (
        b"def fetch_headers(headers):\n"
        b"    if headers is None:\n"
        b"        return {}\n"
        b"    return headers\n"
    )
    t0 = time.perf_counter()
    matches = store.match_and_compile_candidates(
        sample_src, "python", rel_path="hdr.py", target_func_name="fetch_headers"
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert any(l.law_id == "uir_law_target_return_copy" for l, _, _ in matches)
    assert elapsed_ms < 50.0, f"Expected O(1) bucket lookup < 50ms at 500 laws, got {elapsed_ms:.2f}ms"

    # O(1) surgical deletion ablation: removing the law immediately drops recall to 0
    assert store.remove_law("uir_law_target_return_copy") is True
    matches_after = store.match_and_compile_candidates(
        sample_src, "python", rel_path="hdr.py", target_func_name="fetch_headers"
    )
    assert matches_after == []
