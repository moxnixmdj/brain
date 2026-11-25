"""Real end-to-end verification of Walls 1-4: Metamorphic Witness Abduction,
Codebase Type-Habitation, Multi-File Relational Zipper, O(1) L2 Transfer/Deletion,
and Document-as-Test-Suite Replay (0 model calls, 0 neural weights).
"""
from __future__ import annotations

import ast
import io
import pathlib
import tarfile
import time

from canonical.runtime import harbor_swe_zero_model_agent_v1 as harbor_agent
from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
from canonical.swe_kernel import perfect_algorithm_v1 as perfect_alg
from canonical.swe_kernel.universal_computer_agent_v1 import ExternalCausalLawStore


def test_wall1_issue_only_metamorphic_abduction_and_heldout_verification(tmp_path: pathlib.Path) -> None:
    """Pristine parent repo where 100% of visible tests PASS before solving.

    No post-fix test exists during repair. The engine must abduce a failing
    metamorphic witness solely from the issue description + codebase AST,
    repair the source without regressing existing tests, delete the temporary
    witness file, and pass a held-out assertion revealed ONLY after selection.
    """
    # Case A: Protocol dunder set to None (`__reversed__ = None`)
    repo_a = tmp_path / "repo_dunder"
    (repo_a / "seqlib").mkdir(parents=True)
    (repo_a / "tests").mkdir(parents=True)
    (repo_a / "seqlib" / "__init__.py").write_text("from .ops import last_item\n", encoding="utf-8")
    (repo_a / "seqlib" / "ops.py").write_text(
        "def last_item(iterable):\n"
        "    if hasattr(iterable, '__reversed__'):\n"
        "        return next(reversed(iterable))\n"
        "    items = list(iterable)\n"
        "    return items[-1]\n",
        encoding="utf-8",
    )
    (repo_a / "tests" / "test_ops.py").write_text(
        "from seqlib.ops import last_item\n\n"
        "def test_basic_list():\n"
        "    assert last_item([1, 2, 3]) == 3\n",
        encoding="utf-8",
    )
    # Confirm pristine parent is 100% green BEFORE solving
    assert mhz.run_pytest_targets(repo_a, ["tests/test_ops.py"])["ok"]

    res_a = mhz.repair_repo_unified_zero_model(
        repo_a,
        "tests/test_ops.py",
        issue_text="last_item crashes with TypeError when __reversed__ is None on a custom iterable",
        timeout_s=20.0,
        keep_patch_applied=True,
    )
    assert res_a["model_calls"] == 0
    assert res_a["repaired"] is True
    assert res_a["metamorphic_witness"] == "PROTOCOL_DUNDER_NONE"
    assert not (repo_a / "_brain_metamorphic_witness_v1.py").exists()

    # Post-selection held-out human test grading
    (repo_a / "tests" / "test_heldout_dunder.py").write_text(
        "from seqlib.ops import last_item\n\n"
        "class BlockedReverse:\n"
        "    __reversed__ = None\n"
        "    def __iter__(self):\n"
        "        return iter(['a', 'b', 'c'])\n\n"
        "def test_heldout():\n"
        "    assert last_item(BlockedReverse()) == 'c'\n",
        encoding="utf-8",
    )
    assert mhz.run_pytest_targets(repo_a, ["tests/test_ops.py", "tests/test_heldout_dunder.py"])["ok"]

    # Case B: Mutation aliasing on returned head slice
    repo_b = tmp_path / "repo_alias"
    (repo_b / "iterlib").mkdir(parents=True)
    (repo_b / "tests").mkdir(parents=True)
    (repo_b / "iterlib" / "__init__.py").write_text("from .spy import peek_head\n", encoding="utf-8")
    (repo_b / "iterlib" / "spy.py").write_text(
        "from itertools import chain, islice\n\n"
        "def peek_head(iterable, n=1):\n"
        "    it = iter(iterable)\n"
        "    head = list(islice(it, n))\n"
        "    return head, chain(head, it)\n",
        encoding="utf-8",
    )
    (repo_b / "tests" / "test_spy.py").write_text(
        "from iterlib.spy import peek_head\n\n"
        "def test_basic_spy():\n"
        "    h, it = peek_head([10, 20, 30], 2)\n"
        "    assert h == [10, 20] and list(it) == [10, 20, 30]\n",
        encoding="utf-8",
    )
    assert mhz.run_pytest_targets(repo_b, ["tests/test_spy.py"])["ok"]

    res_b = mhz.repair_repo_unified_zero_model(
        repo_b,
        "tests/test_spy.py",
        issue_text="Modifying the returned head list from peek_head mutates the returned iterator because of aliasing",
        timeout_s=20.0,
        keep_patch_applied=True,
    )
    assert res_b["model_calls"] == 0
    assert res_b["repaired"] is True
    assert res_b["metamorphic_witness"] == "MUTATION_ALIASING"

    (repo_b / "tests" / "test_heldout_alias.py").write_text(
        "from iterlib.spy import peek_head\n\n"
        "def test_heldout_mutation():\n"
        "    h, it = peek_head([1, 2, 3], 2)\n"
        "    h.clear()\n"
        "    assert list(it) == [1, 2, 3]\n",
        encoding="utf-8",
    )
    assert mhz.run_pytest_targets(repo_b, ["tests/test_spy.py", "tests/test_heldout_alias.py"])["ok"]


def test_wall2_type_habitation_module_defuse_and_exception_lattice(tmp_path: pathlib.Path) -> None:
    """Verify module-global regex `$ -> \\Z`, exception lattice widening, and generator materialization."""
    # 1. Module-global regex `$` -> `\Z` def-use tracking (fault line is NOT inside failing function!)
    r1 = tmp_path / "repo_regex"
    (r1 / "validator").mkdir(parents=True)
    (r1 / "tests").mkdir(parents=True)
    (r1 / "validator" / "__init__.py").write_text("", encoding="utf-8")
    (r1 / "validator" / "names.py").write_text(
        "import re\n"
        "_VALID_RE = re.compile(r'^[a-z0-9-]+$')\n\n"
        "def is_valid_name(name: str) -> bool:\n"
        "    return _VALID_RE.match(name) is not None\n",
        encoding="utf-8",
    )
    (r1 / "tests" / "test_names.py").write_text(
        "from validator.names import is_valid_name\n\n"
        "def test_rejects_trailing_newline():\n"
        "    assert is_valid_name('pkg-1') is True\n"
        "    assert is_valid_name('pkg-1\\n') is False\n",
        encoding="utf-8",
    )
    out1 = mhz.repair_repo_unified_zero_model(r1, "tests/test_names.py", timeout_s=15.0)
    assert out1["repaired"] is True and out1["model_calls"] == 0
    assert out1["mechanism"] == "TYPE_HABITATION__REGEX_END_ANCHOR_Z"

    # 2. Exception-lattice widening from live uncaught OverflowError
    r2 = tmp_path / "repo_exc"
    (r2 / "conv").mkdir(parents=True)
    (r2 / "tests").mkdir(parents=True)
    (r2 / "conv" / "__init__.py").write_text("", encoding="utf-8")
    (r2 / "conv" / "num.py").write_text(
        "def safe_int(val, default=0):\n"
        "    try:\n"
        "        return int(val)\n"
        "    except (TypeError, ValueError):\n"
        "        try:\n"
        "            return int(float(val))\n"
        "        except (TypeError, ValueError):\n"
        "            return default\n",
        encoding="utf-8",
    )
    (r2 / "tests" / "test_num.py").write_text(
        "from conv.num import safe_int\n\n"
        "def test_overflow_returns_default():\n"
        "    assert safe_int('42') == 42\n"
        "    assert safe_int('1e10000', 0) == 0\n",
        encoding="utf-8",
    )
    out2 = mhz.repair_repo_unified_zero_model(r2, "tests/test_num.py", timeout_s=15.0)
    assert out2["repaired"] is True and out2["model_calls"] == 0
    assert out2["mechanism"] == "TYPE_HABITATION__EXCEPTION_LATTICE_WIDEN"

    # 3. Live generator returned by callback materialized via `tuple(...)`
    r3 = tmp_path / "repo_gen"
    (r3 / "builder").mkdir(parents=True)
    (r3 / "tests").mkdir(parents=True)
    (r3 / "builder" / "__init__.py").write_text("", encoding="utf-8")
    (r3 / "builder" / "schema.py").write_text(
        "def build_fields(fields, transformer=None):\n"
        "    items = tuple(fields)\n"
        "    if transformer is not None:\n"
        "        items = transformer(items)\n"
        "    return list(items) + list(items)\n",
        encoding="utf-8",
    )
    (r3 / "tests" / "test_schema.py").write_text(
        "from builder.schema import build_fields\n\n"
        "def test_generator_transformer():\n"
        "    out = build_fields(['a', 'b'], transformer=lambda fs: (f.upper() for f in fs))\n"
        "    assert out == ['A', 'B', 'A', 'B']\n",
        encoding="utf-8",
    )
    out3 = mhz.repair_repo_unified_zero_model(r3, "tests/test_schema.py", timeout_s=15.0)
    assert out3["repaired"] is True and out3["model_calls"] == 0
    assert out3["mechanism"] in ("TYPE_HABITATION__ITERABLE_TUPLE_WRAP", "TYPE_HABITATION__ITERABLE_LIST_WRAP")


def test_wall3_relational_zipper_multifile_cascade(tmp_path: pathlib.Path) -> None:
    """Verify multi-file coupled refactor repair across 4 files (relocated import + 2 caller arity sites)."""
    repo = tmp_path / "repo_cascade"
    (repo / "app").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "app" / "legacy.py").write_text("DEPRECATED = True\n", encoding="utf-8")
    (repo / "app" / "crypto.py").write_text(
        "def digest_key(key: str, namespace: str) -> str:\n"
        "    return f'{namespace}:{key}'\n",
        encoding="utf-8",
    )
    (repo / "app" / "svc_a.py").write_text(
        "from app.legacy import digest_key\n\n"
        "def make_a(key: str, namespace: str = 'svcA') -> str:\n"
        "    return digest_key(key)\n",
        encoding="utf-8",
    )
    (repo / "app" / "svc_b.py").write_text(
        "from app.legacy import digest_key\n\n"
        "def make_b(key: str, namespace: str = 'svcB') -> str:\n"
        "    return digest_key(key)\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_cascade.py").write_text(
        "from app.svc_a import make_a\n"
        "from app.svc_b import make_b\n\n"
        "def test_both_services():\n"
        "    assert make_a('k1') == 'svcA:k1'\n"
        "    assert make_b('k2') == 'svcB:k2'\n",
        encoding="utf-8",
    )
    res = mhz.repair_repo_unified_zero_model(repo, "tests/test_cascade.py", timeout_s=20.0)
    assert res["repaired"] is True and res["model_calls"] == 0
    assert res["mechanism"] == "RELATIONAL_ZIPPER_MULTIFILE"
    assert sorted(res["modified_files"]) == ["app/svc_a.py", "app/svc_b.py"]
    assert len(res["hops"]) == 3
    assert mhz.run_pytest_targets(repo, ["tests/test_cascade.py"])["ok"]


def test_single_experience_o1_l2_cross_repo_transfer_and_o1_deletion(tmp_path: pathlib.Path) -> None:
    """Learn ONCE from Repo A, transfer via O(1) L2 recall to unseen Repo B (different names), then O(1) delete."""
    store = ExternalCausalLawStore(str(tmp_path / "external_skill_store.json"))

    # Source Repo A
    repo_a = tmp_path / "source_repo_alpha"
    (repo_a / "alpha").mkdir(parents=True)
    (repo_a / "tests").mkdir(parents=True)
    (repo_a / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (repo_a / "alpha" / "matcher.py").write_text(
        "import re\n"
        "PAT = re.compile(r'[a-z]+')\n"
        "def exact_word(word: str) -> bool:\n"
        "    return PAT.match(word) is not None\n",
        encoding="utf-8",
    )
    (repo_a / "tests" / "test_alpha.py").write_text(
        "from alpha.matcher import exact_word\n\n"
        "def test_exact():\n"
        "    assert exact_word('abc') is True\n"
        "    assert exact_word('abc123') is False\n",
        encoding="utf-8",
    )
    r_learn = mhz.repair_repo_unified_zero_model(repo_a, "tests/test_alpha.py", timeout_s=15.0, skill_store=store)
    assert r_learn["repaired"] is True
    admitted = r_learn.get("admitted_morphisms") or []
    assert len(admitted) >= 1

    # Completely unseen Target Repo B (different package, file, class, method, variable names!)
    repo_b = tmp_path / "target_repo_beta"
    (repo_b / "beta").mkdir(parents=True)
    (repo_b / "tests").mkdir(parents=True)
    (repo_b / "beta" / "__init__.py").write_text("", encoding="utf-8")
    (repo_b / "beta" / "cors.py").write_text(
        "import re\n"
        "class Policy:\n"
        "    def __init__(self, rx: str):\n"
        "        self.compiled = re.compile(rx)\n"
        "    def allows(self, origin: str) -> bool:\n"
        "        return bool(self.compiled.match(origin))\n",
        encoding="utf-8",
    )
    (repo_b / "tests" / "test_beta.py").write_text(
        "from beta.cors import Policy\n\n"
        "def test_cors_exact():\n"
        "    p = Policy(r'https://good\\.example')\n"
        "    assert p.allows('https://good.example') is True\n"
        "    assert p.allows('https://good.example.evil.com') is False\n",
        encoding="utf-8",
    )
    r_xfer = mhz.repair_repo_unified_zero_model(
        repo_b, "tests/test_beta.py", timeout_s=15.0, skill_store=store, keep_patch_applied=False
    )
    assert r_xfer["repaired"] is True
    assert r_xfer["mechanism"] == "O1_L2_TREE_MORPHISM_RECALL"
    mid = r_xfer["morphism_id"]
    assert mid in admitted

    # O(1) surgical deletion from external inspectable store -> immediate removal with zero residual recall!
    t0 = time.perf_counter()
    deleted = store.delete_tree_morphism(mid)
    del_ms = (time.perf_counter() - t0) * 1000.0
    assert deleted is True
    assert del_ms < 50.0

    r_after_del = mhz.repair_repo_unified_zero_model(
        repo_b, "tests/test_beta.py", timeout_s=15.0, skill_store=store, keep_patch_applied=False
    )
    assert r_after_del["repaired"] is True
    assert r_after_del["mechanism"] != "O1_L2_TREE_MORPHISM_RECALL"


def test_wall4_perfect_algorithm_document_as_test_suite_and_security_gates() -> None:
    """Verify dict-wrapped local_guide docs + `$ ` shell transcripts + IN_VOCABULARY / MATCHED gates."""
    shell_doc = [{"title": "echo", "body": "Usage:\n$ echo brain-zero-model\nbrain-zero-model\n"}]
    ok = perfect_alg._plan_from_document(shell_doc, actions=["echo"], goal="print marker")
    assert ok["status"] == "PASS__PLAN_FROM_A_DOCUMENT"
    assert ok["plan"] == ["echo brain-zero-model"]
    assert ok["authority"] == "EXTERNAL_DOCUMENT_REPLAYED_AND_SELF_CHECKED"

    # Security gate: command outside caller's actions MUST NOT run or enter plan
    smuggle = [{"body": "$ id\nuid=0(root)\n"}]
    refused_vocab = perfect_alg._plan_from_document(smuggle, actions=["echo"], goal="print marker")
    assert refused_vocab["status"] == "REFUSED__NOTHING_MATCHED_INSIDE_THE_PLAN_SPACE"
    assert refused_vocab["gate"] == "IN_VOCABULARY"

    # Integrity gate: guide whose printed answer disagrees with real replay MUST be refused
    lying = [{"body": "$ echo real-out\nfabricated-out\n"}]
    refused_match = perfect_alg._plan_from_document(lying, actions=["echo"], goal="print marker")
    assert refused_match["status"] == "REFUSED__NOTHING_REPRODUCED_THE_DOCUMENTS_OUTPUT"
    assert refused_match["gate"] == "MATCHED"

    # Python `>>>` transcript wrapped inside dict document
    py_doc = [{"text": ">>> import math\n>>> math.gcd(24, 36)\n12\n"}]
    ok_py = perfect_alg._plan_from_document(py_doc, actions=["math.gcd"], goal="gcd")
    assert ok_py["status"] == "PASS__PLAN_FROM_A_DOCUMENT"


def test_harbor_bundle_and_zero_model_ast_audit() -> None:
    """Verify Harbor tar.gz ships metamorphic_habitation_zipper_v1 and contains zero LLM/network clients."""
    bundle = harbor_agent._build_kernel_tar_gz()
    with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as tf:
        names = set(tf.getnames())
    assert "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py" in names
    assert "run_repair.py" in names

    # Strict AST audit for zero runtime model or HTTP SDK dependencies
    forbidden_roots = {
        "openai", "anthropic", "google", "litellm", "transformers", "torch",
        "vllm", "ollama", "httpx", "requests", "aiohttp", "urllib",
    }
    src_path = pathlib.Path(mhz.__file__)
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(forbidden_roots), f"Forbidden runtime imports found: {imported & forbidden_roots}"


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
