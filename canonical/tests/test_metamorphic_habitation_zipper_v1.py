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
