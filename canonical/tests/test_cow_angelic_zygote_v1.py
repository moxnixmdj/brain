"""Clean-room unit, integration, and zero-model audit tests for `cow_angelic_zygote_v1.py`
and its integration into `metamorphic_habitation_zipper_v1.py` and `harbor_swe_zero_model_agent_v1.py`.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap

from canonical.runtime import harbor_swe_zero_model_agent_v1 as harbor_agent
from canonical.swe_kernel import cow_angelic_zygote_v1 as caz
from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz


FORBIDDEN_MODEL_IMPORTS = {
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "litellm",
    "transformers",
    "vllm",
    "ollama",
    "cohere",
    "mistralai",
    "boto3",
    "groq",
}


def test_zero_model_ast_and_generality_audit() -> None:
    """Strictly verify zero LLM SDK imports, `PRODUCER_MODEL_CALLS == 0`, and Harbor bundling."""
    assert caz.PRODUCER_MODEL_CALLS == 0
    assert mhz.PRODUCER_MODEL_CALLS == 0
    assert "canonical/swe_kernel/cow_angelic_zygote_v1.py" in harbor_agent._KERNEL_FILES

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    for rel in (
        "canonical/swe_kernel/cow_angelic_zygote_v1.py",
        "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
        "canonical/runtime/harbor_swe_zero_model_agent_v1.py",
    ):
        src = (repo_root / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in FORBIDDEN_MODEL_IMPORTS, f"Forbidden import {alias.name} in {rel}"
                    assert alias.name not in FORBIDDEN_MODEL_IMPORTS, f"Forbidden import {alias.name} in {rel}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in FORBIDDEN_MODEL_IMPORTS, f"Forbidden import {node.module} in {rel}"
                assert node.module not in FORBIDDEN_MODEL_IMPORTS, f"Forbidden import {node.module} in {rel}"


def test_cow_zygote_server_isolates_and_evaluates(tmp_path: pathlib.Path) -> None:
    """Verify `PytestCoWZygoteServer` runs parallel isolated fork evaluations without mutating disk."""
    pkg = tmp_path / "mini_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    mod_p = pkg / "calc.py"
    orig_src = textwrap.dedent("""\
        def double_positive(x):
            if x > 0:
                return x * 3
            return 0
    """)
    mod_p.write_text(orig_src, encoding="utf-8")
    test_p = tmp_path / "test_calc.py"
    test_p.write_text(
        textwrap.dedent("""\
            from mini_pkg.calc import double_positive

            def test_pos():
                assert double_positive(4) == 8

            def test_zero():
                assert double_positive(0) == 0
        """),
        encoding="utf-8",
    )

    fixed_src = orig_src.replace("return x * 3", "return x * 2")
    wrong_src = orig_src.replace("return x * 3", "return x * 5")

    with caz.PytestCoWZygoteServer(tmp_path) as srv:
        results = srv.eval_batch(
            [
                {"edits": {"mini_pkg/calc.py": wrong_src}},
                {"edits": {"mini_pkg/calc.py": fixed_src}},
            ],
            [test_p.name],
            max_workers=2,
            timeout_s=10.0,
        )
    assert len(results) == 2
    assert results[0]["ok"] is False
    assert results[1]["ok"] is True
    # Disk file must remain untouched by in-memory CoW forks
    assert mod_p.read_text(encoding="utf-8") == orig_src


def test_differential_ochiai_spectrum_ranks_faulty_line(tmp_path: pathlib.Path) -> None:
    """Verify `PytestCoWZygoteServer.trace_differential_spectrum` ranks the faulty branch highest."""
    pkg = tmp_path / "app_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "router.py").write_text(
        textwrap.dedent("""\
            def route(path):
                norm = path.strip()
                if norm.startswith("/admin"):
                    return "denied"
                return "ok"
        """),
        encoding="utf-8",
    )
    (tmp_path / "test_router.py").write_text(
        textwrap.dedent("""\
            from app_pkg.router import route

            def test_public():
                assert route("/home") == "ok"

            def test_admin():
                assert route("/admin") == "allowed"
        """),
        encoding="utf-8",
    )
    with caz.PytestCoWZygoteServer(tmp_path) as srv:
        spec = srv.trace_differential_spectrum(
            failing_targets=["test_router.py::test_admin"],
            passing_targets=["test_router.py::test_public"],
            timeout_s=10.0,
        )
    assert spec.get("ok") is True
    assert "app_pkg/router.py" in spec.get("ranked_files", [])
    line_scores = spec.get("line_scores", {}).get("app_pkg/router.py", {})
    assert line_scores
    # Line 4 (`return "denied"`) is executed ONLY by the failing test -> highest Ochiai score (1.0)!
    top_line = max(line_scores.items(), key=lambda kv: kv[1])
    assert int(top_line[0]) == 4
    assert float(top_line[1]) == 1.0


def test_angelic_separating_guard_and_algebraic_repair_end_to_end(tmp_path: pathlib.Path) -> None:
    """Clean-room end-to-end test: angelic separating guard + f-string unwrap via unified engine."""
    # Case 1: Missing boolean guard (solved by `ANGELIC_SEPARATING_GUARD`)
    repo1 = tmp_path / "repo_guard"
    repo1.mkdir()
    (repo1 / "widget.py").write_text(
        textwrap.dedent("""\
            class Widget:
                def __init__(self, show_tag=False, tag=None):
                    self.show_tag = show_tag
                    self.tag = tag

                def describe(self):
                    if self.show_tag:
                        return f"tag={self.tag.upper()}"
                    return "none"
        """),
        encoding="utf-8",
    )
    (repo1 / "test_widget.py").write_text(
        textwrap.dedent("""\
            from widget import Widget

            def test_hidden():
                assert Widget(show_tag=False, tag="a").describe() == "none"

            def test_shown_with_tag():
                assert Widget(show_tag=True, tag="a").describe() == "tag=A"

            def test_shown_without_tag():
                assert Widget(show_tag=True, tag=None).describe() == "none"
        """),
        encoding="utf-8",
    )
    res1 = mhz.repair_repo_unified_zero_model(repo1, "test_widget.py", timeout_s=20.0, keep_patch_applied=False)
    assert res1["repaired"] is True
    assert res1["model_calls"] == 0

    # Case 2: F-string call-wrapper unwrap (`{list(enc)}` -> `{enc!r}`)
    repo2 = tmp_path / "repo_fstr"
    repo2.mkdir()
    (repo2 / "fmt.py").write_text(
        textwrap.dedent("""\
            def check_encoding(enc):
                if enc != "UTF-8":
                    raise ValueError(f"unsupported encoding {list(enc)}")
                return True
        """),
        encoding="utf-8",
    )
    (repo2 / "test_fmt.py").write_text(
        textwrap.dedent("""\
            import pytest
            from fmt import check_encoding

            def test_ok():
                assert check_encoding("UTF-8") is True

            def test_bad():
                with pytest.raises(ValueError, match="unsupported encoding 'latin1'"):
                    check_encoding("latin1")
        """),
        encoding="utf-8",
    )
    res2 = mhz.repair_repo_unified_zero_model(repo2, "test_fmt.py", timeout_s=20.0, keep_patch_applied=False)
    assert res2["repaired"] is True
    assert res2["model_calls"] == 0
    assert "{enc!r}" in res2["unified_diff"]


def test_wall1_docstring_and_inline_oracle_scoping(tmp_path: pathlib.Path) -> None:
    """Verify Wall-1 docstring oracles strictly scope to issue-referenced functions and catch regex `$`."""
    (tmp_path / "names.py").write_text(
        textwrap.dedent("""\
            import re

            _NAME_RE = re.compile(r"^[a-z0-9-]+$")

            def normalize_pkg(name: str) -> str:
                return re.sub(r"[-_.]+", "-", name).lower()

            def is_valid_pkg(name: str) -> bool:
                \"\"\"Return True if name is valid normalized form (unchanged under normalize_pkg).\"\"\"
                return _NAME_RE.match(name) is not None

            def unrelated_helper(x: str) -> str:
                \"\"\"Equivalent to normalize_pkg.\"\"\"
                return x.upper()
        """),
        encoding="utf-8",
    )
    # Issue mentions `is_valid_pkg` only -> must NOT generate spurious oracle for `unrelated_helper`!
    specs = caz.mine_docstring_metamorphic_oracles(
        tmp_path,
        ["names.py"],
        "is_valid_pkg accepts trailing newlines and double hyphens",
    )
    target_syms = {s.func_name for s in specs}
    assert "unrelated_helper" not in target_syms
    assert any(s.kind in ("DOCSTRING_ROUNDTRIP_ORACLE", "DOCSTRING_REGEX_NEWLINE_ORACLE") for s in specs)

    # Inline issue reproducer extraction
    issue = textwrap.dedent("""\
        Calling `is_valid_pkg("foo\\n")` fails:
        ```python
        from names import is_valid_pkg
        assert is_valid_pkg("foo\\n") is False
        ```
    """)
    repro = caz.extract_inline_issue_reproducer(issue)
    assert repro is not None
    assert "is_valid_pkg" in repro
    assert "def test_inline_issue_reproducer" in repro


def test_negative_space_guard_records_prunes_and_deletes_o1(tmp_path: pathlib.Path) -> None:
    """Verify `NegativeSpaceGuard` records structural refutations, prunes alpha-equivalent edits,
    persists inspectable JSON, and supports O(1) deletion."""
    store_p = tmp_path / "neg_space.json"
    nsg = caz.NegativeSpaceGuard(store_p)
    orig_a = "def f(alpha):\n    return alpha + 1\n"
    bad_a = "def f(alpha):\n    return alpha - 1\n"
    # Alpha-renamed twin in a different file/repo
    orig_b = "def g(beta):\n    return beta + 1\n"
    bad_b = "def g(beta):\n    return beta - 1\n"

    assert nsg.is_refuted(orig_a, bad_a) is False
    fp = nsg.record_refutation(orig_a, bad_a, "BROKEN_BASELINE_TEST")
    assert fp
    assert nsg.count() == 1
    assert nsg.is_refuted(orig_a, bad_a) is True
    # Alpha-renamed equivalent bad edit is ALSO pruned in O(1)!
    assert nsg.is_refuted(orig_b, bad_b) is True

    # Reload from disk and verify O(1) deletion cleanly removes it
    nsg2 = caz.NegativeSpaceGuard(store_p)
    assert nsg2.is_refuted(orig_b, bad_b) is True
    assert nsg2.delete_invariant(fp) is True
    assert nsg2.count() == 0
    assert caz.NegativeSpaceGuard(store_p).is_refuted(orig_b, bad_b) is False
