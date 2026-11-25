"""Comprehensive fast verification suite (`< 12s`) for the Unified Zero-LLM Architecture:
  1. `repo_component_petri_v1`: Repo-native component mining, mapped comprehensions, Optional tuple
     coalescing + guard elision, `.rstrip()` monoid normalization, exception-handler Petri widening.
  2. `causal_cegis_inventor_v1`: Same-file orthogonal multi-hunk patch algebra, counterexample-
     partitioned dual-program splicing (`if G: P_cand else: P_orig`), symmetric `is not None -> x`
     narrowing, and prewarmed `os.fork()` Zygote pytest fast gate.
  3. `speculative_cow_petri_agent_v1`: 5-layer differential state tomography, `ZygotePrewarmedPool`
     parallel CoW speculative rollouts, standing invariant enforcement (`NO_LOSS_WITHOUT_CONSENT`),
     interactive Mealy BFS grid mapping, tail- & head-truncated SQLite B-tree forensics, 3-way
     `§9.2` skill-store ablation + staleness invalidation, and 360-step cross-modal Petri planning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

from canonical.swe_kernel.causal_cegis_inventor_v1 import (
    CausalCEGISInventor,
    merge_orthogonal_file_patches,
    synthesize_dual_program_splice,
    synthesize_obsegraph_branch_repairs,
)
from canonical.swe_kernel.repo_component_petri_v1 import (
    synthesize_exception_handler_widening,
    synthesize_repo_petri_repairs,
)
from canonical.swe_kernel.speculative_cow_petri_agent_v1 import (
    CandidateMorphism,
    CrossModalPetriPlanner,
    EpistemicPetriSkillStore,
    ExplicitConstraintLedger,
    InteractiveGridMealyExplorer,
    PetriTransition,
    SpeculativeCoWRolloutEngine,
    capture_tomography_snapshot,
    recover_corrupted_or_truncated_sqlite,
    solve_exact_arithmetic_expression,
    solve_terminal_workspace,
)


def test_repo_component_mapped_comprehension_and_trailing_delimiter_monoid(tmp_path: Path) -> None:
    src = (
        "class Argument:\n"
        "    def get_help_record(self, ctx):\n"
        "        return ('ARG', '')\n\n"
        "def collect_records(args, ctx):\n"
        "    records = args\n"
        "    return records\n"
    )
    (tmp_path / "mod.py").write_text(src, encoding="utf-8")
    patches, _ = synthesize_repo_petri_repairs(
        repo_root=tmp_path,
        rel_path="mod.py",
        source_text=src,
        line_no=6,
        pass_samples=[],
        fail_samples=[{"locals": {"args": {"type": "list"}, "ctx": {"type": "Context"}}}],
        escaping_exceptions=[],
    )
    assert any("get_help_record(ctx)" in p for p, _ in patches)

    fmt_src = (
        "class Auth:\n"
        "    def to_header(self):\n"
        "        return f'{self.scheme} {self.params}'\n"
    )
    (tmp_path / "auth.py").write_text(fmt_src, encoding="utf-8")
    fmt_patches, _ = synthesize_repo_petri_repairs(
        repo_root=tmp_path,
        rel_path="auth.py",
        source_text=fmt_src,
        line_no=3,
        pass_samples=[],
        fail_samples=[{"locals": {"self": {"type": "Auth"}}}],
        escaping_exceptions=[],
    )
    assert any(".rstrip()" in p for p, _ in fmt_patches)


def test_exception_handler_petri_widening_from_runtime_trace() -> None:
    src = (
        "def prompt_loop(read_fn):\n"
        "    try:\n"
        "        return read_fn()\n"
        "    except EOFError:\n"
        "        return 'ABORTED'\n"
    )
    patches = synthesize_exception_handler_widening(
        source_text=src,
        line_no=3,
        escaping_exceptions=[
            {"rel_path": "cli.py", "lineno": 3, "func": "prompt_loop", "exc_type": "KeyboardInterrupt"}
        ],
        rel_path="cli.py",
        in_scope_exceptions={"EOFError", "KeyboardInterrupt", "ValueError"},
    )
    assert any("(EOFError, KeyboardInterrupt)" in p for p, _ in patches)


def test_symmetric_optional_truthy_narrowing_on_empty_string() -> None:
    src = (
        "def render_envvar(envvar):\n"
        "    if envvar is not None:\n"
        "        return f'[env: {envvar}]'\n"
        "    return ''\n"
    )
    patches, _ = synthesize_obsegraph_branch_repairs(
        source_text=src,
        line_no=2,
        pass_samples=[
            {"locals": {"envvar": {"type": "NoneType", "is_none": True, "truthy": False}}},
            {"locals": {"envvar": {"type": "str", "is_none": False, "truthy": True, "repr": "'PORT'"}}},
        ],
        fail_samples=[
            {"locals": {"envvar": {"type": "str", "is_none": False, "truthy": False, "repr": "''"}}}
        ],
    )
    assert any("if envvar:" in p for p, _ in patches)


def test_same_file_orthogonal_multihunk_merge_and_overlap_rejection(tmp_path: Path) -> None:
    orig = (
        "def alpha(x):\n"
        "    return x + 1\n\n"
        "def beta(y):\n"
        "    return y - 1\n"
    )
    (tmp_path / "pair.py").write_text(orig, encoding="utf-8")
    p_a = {"pair.py": orig.replace("return x + 1", "return x")}
    p_b = {"pair.py": orig.replace("return y - 1", "return y")}
    merged = merge_orthogonal_file_patches(tmp_path, p_a, p_b)
    assert merged is not None
    assert "return x\n" in merged["pair.py"] and "return y\n" in merged["pair.py"]

    # Overlapping edit at the exact same line must be rejected cleanly
    p_a2 = {"pair.py": orig.replace("return x + 1", "return x * 2")}
    assert merge_orthogonal_file_patches(tmp_path, p_a, p_a2) is None


def test_dual_program_counterexample_splice_and_same_file_two_hunk_end_to_end(tmp_path: Path) -> None:
    # 1. Direct unit test of `synthesize_dual_program_splice`
    orig = "def compute(val):\n    return val.strip()\n"
    cand = "def compute(val):\n    return ''\n"
    splices = synthesize_dual_program_splice(
        orig_src=orig,
        cand_src=cand,
        fail_samples_by_line={2: [{"locals": {"val": {"type": "NoneType", "is_none": True, "truthy": False}}}]},
        reg_samples_by_line={2: [{"locals": {"val": {"type": "str", "is_none": False, "truthy": True, "repr": "' hi '"}}}]},
    )
    assert splices and "if val is None:" in splices[0][0]

    # 2. End-to-end 2-hunk same-file repair via `CausalCEGISInventor` (`COGS_COUPLED_MULTIFILE_BEAM`)
    repo = tmp_path / "two_hunk_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "envfmt.py").write_text(
        "def fmt_help(envvar):\n"
        "    if envvar is not None:\n"
        "        return f'env={envvar}'\n"
        "    return 'no-env'\n\n"
        "def fmt_err(envvar):\n"
        "    if envvar is not None:\n"
        "        return f'missing({envvar})'\n"
        "    return 'missing'\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_envfmt.py").write_text(
        "from pkg.envfmt import fmt_help, fmt_err\n\n"
        "def test_help_normal():\n"
        "    assert fmt_help('HOME') == 'env=HOME'\n"
        "    assert fmt_help(None) == 'no-env'\n\n"
        "def test_help_empty_str():\n"
        "    assert fmt_help('') == 'no-env'\n\n"
        "def test_err_normal():\n"
        "    assert fmt_err('HOME') == 'missing(HOME)'\n"
        "    assert fmt_err(None) == 'missing'\n\n"
        "def test_err_empty_str():\n"
        "    assert fmt_err('') == 'missing'\n",
        encoding="utf-8",
    )
    inv = CausalCEGISInventor(sandbox_budget=24, enable_law_crystallization=False)
    res = inv.solve_repository(repo, test_target="tests/test_envfmt.py", language="python", timeout_sec=8.0)
    assert res.solved is True
    assert res.sabotage_verified is True
    assert res.overfit_falsifier_passed is True
    assert res.source_tree_unchanged is True


def test_standing_invariant_blocks_unconsented_file_deletion_in_cow_rollout(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "precious_notes.txt").write_text("do not delete me\n", encoding="utf-8")
    (ws / "run.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    os.chmod(ws / "run.sh", 0o644)

    snap = capture_tomography_snapshot(ws)
    ledger = ExplicitConstraintLedger.from_instruction_and_snapshot(
        "Fix /app/run.sh so it executes cleanly.", snap
    )
    engine = SpeculativeCoWRolloutEngine()
    destructive = CandidateMorphism(
        name="destructive_chmod_and_rm",
        domain="shell_repair",
        command_or_spec="rm -f precious_notes.txt && chmod u+rx run.sh",
        target_rel="run.sh",
    )
    # Destructive morphism alone MUST be rejected by `NO_LOSS_WITHOUT_CONSENT`!
    bad_out = engine.evaluate_and_commit(ws, ledger, [destructive])
    assert bad_out.committed is False
    assert (ws / "precious_notes.txt").read_text(encoding="utf-8") == "do not delete me\n"


def test_sqlite_forensics_recovers_both_tail_and_head_truncated_databases(tmp_path: Path) -> None:
    full_db = tmp_path / "full.db"
    conn = sqlite3.connect(full_db)
    conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, word TEXT, value INT);")
    for idx in range(12):
        conn.execute("INSERT INTO items (word, value) VALUES (?, ?);", (f"w_{idx}", idx * 10))
    conn.commit()
    conn.close()

    raw = full_db.read_bytes()
    assert len(raw) >= 8192
    # 1. Head-truncated raw `0x0d` leaf page (page 1 stripped off the front!)
    head_trunc = tmp_path / "head_trunc.db"
    head_trunc.write_bytes(raw[4096:8192])
    rows_head = recover_corrupted_or_truncated_sqlite(head_trunc, fallback_col_names=["word", "value"])
    assert len(rows_head) == 12
    assert rows_head[0] == {"word": "w_0", "value": 0}
    assert rows_head[-1] == {"word": "w_11", "value": 110}

    # 2. Tail-truncated multi-page DB (retaining page 1 `sqlite_master` + partial page 2!)
    tail_trunc = tmp_path / "tail_trunc.db"
    tail_trunc.write_bytes(raw[:8192])
    # Force expected_pages > 2 in SQLite header bytes 28..32 to simulate missing page 3
    patched = bytearray(tail_trunc.read_bytes())
    patched[28:32] = (5).to_bytes(4, "big")
    tail_trunc.write_bytes(bytes(patched))
    rows_tail = recover_corrupted_or_truncated_sqlite(tail_trunc)
    assert len(rows_tail) == 12
    assert rows_tail[3]["word"] == "w_3" and rows_tail[3]["value"] == 30


def test_interactive_mealy_explorer_and_3way_skill_ablation_and_long_horizon_petri(tmp_path: Path) -> None:
    # 1. Interactive Mealy BFS on a loopy 5x5 maze
    grid = [
        "#####",
        "#  S#",
        "# # #",
        "#E  #",
        "#####",
    ]
    pos = [1, 3]
    dirs = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}

    def _oracle(cmd: str) -> str:
        d = cmd.split()[-1]
        dr, dc = dirs[d]
        nr, nc = pos[0] + dr, pos[1] + dc
        if grid[nr][nc] == "#":
            return "hit wall"
        pos[0], pos[1] = nr, nc
        return "reached exit" if grid[nr][nc] == "E" else "moved"

    mapped = InteractiveGridMealyExplorer.explore_callable_oracle(_oracle)
    assert mapped["cell_grid_map"] == "\n".join(grid)

    # 2. Exact rational arithmetic solver
    expr = solve_exact_arithmetic_expression([3, 8, 11, 19, 25, 75], 462)
    assert expr is not None and eval(expr) == 462  # noqa: S307

    # 3. 3-Way Skill Store Ablation (`empty` vs `raw_trace` vs `generalized_s92`) + staleness invalidation
    probes_env_b: dict[str, int] = {}
    for mode in ("empty", "raw_trace", "generalized_s92"):
        m_dir = tmp_path / f"mode_{mode}"
        store = EpistemicPetriSkillStore(m_dir / "skills.json", mode=mode)
        for env_name, rel_script in (("A", "alpha/job.sh"), ("B", "beta/worker.sh")):
            ws = m_dir / env_name
            (ws / Path(rel_script).parent).mkdir(parents=True)
            sp = ws / rel_script
            sp.write_bytes(b"#!/usr/bin/env bash\r\necho ready\r\n")
            os.chmod(sp, 0o644)
            out = solve_terminal_workspace(ws, f"Fix /app/{rel_script} so it runs.", skill_store=store, task_id=env_name)
            assert out.committed is True
            if env_name == "B":
                probes_env_b[mode] = out.probes_executed
        if mode == "generalized_s92":
            assert len(store.skills) == 1
            recalled = store.instantiate_candidates(
                domain="shell_repair",
                workspace_root=m_dir / "B",
                target_rel="beta/worker.sh",
                current_world_fingerprint="drifted_v99",
                staleness_validator=lambda _: False,
            )
            assert recalled == []
            assert store.skills[0].invalidated_stale is True

    # Generalized §9.2 skill store strictly outperforms both empty store AND raw_trace!
    assert probes_env_b["generalized_s92"] < probes_env_b["empty"] < probes_env_b["raw_trace"]

    # 4. 360-step cross-modal Petri planner with 120 standing-violating shortcut traps
    transitions: list[PetriTransition] = []
    for i in range(120):
        transitions.extend(
            [
                PetriTransition(f"trap_{i}", "cli", frozenset({f"s_{i}"}), frozenset({f"s_{i+1}", "bad_delete"})),
                PetriTransition(f"ui_{i}", "ui", frozenset({f"s_{i}", "keep_data"}), frozenset({f"u_{i}"}), frozenset({f"s_{i}"})),
                PetriTransition(f"cli_{i}", "cli", frozenset({f"u_{i}", "keep_data"}), frozenset({f"c_{i}"}), frozenset({f"u_{i}"})),
                PetriTransition(f"sql_{i}", "sqlite", frozenset({f"c_{i}", "keep_data"}), frozenset({f"s_{i+1}"}), frozenset({f"c_{i}"})),
            ]
        )
    plan = CrossModalPetriPlanner.plan_trajectory(
        frozenset({"s_0", "keep_data"}),
        frozenset({"s_120", "keep_data"}),
        frozenset({"bad_delete"}),
        transitions,
    )
    assert plan is not None and len(plan) == 360


def test_multi_statement_ast_subtree_anti_unification_and_effect_undo_refusal(tmp_path: Path) -> None:
    from canonical.swe_kernel.universal_semantic_ir_v1 import (
        CONTRACT_EFFECT_UNDO,
        SemanticCausalLawStore,
        lift_verified_diff_to_semantic_law,
    )

    before_src = (
        b"class Argument:\n"
        b"    def get_help_record(self, ctx):\n"
        b"        if self.help is None:\n"
        b"            return None\n"
        b"        return self.make_metavar(ctx), self.help\n"
    )
    after_src = (
        b"class Argument:\n"
        b"    def get_help_record(self, ctx):\n"
        b"        return (self.make_metavar(ctx), self.help or '')\n"
    )

    law = lift_verified_diff_to_semantic_law(
        before_bytes=before_src,
        after_bytes=after_src,
        language="python",
        sabotage_verified=True,
        contrast_verified=True,
    )
    assert law is not None
    assert law.defect_uir_kind == "UIR_TREE_REWRITE_MORPHISM"

    store = SemanticCausalLawStore(tmp_path / "laws.json")
    assert store.admit_law(law) is True

    # Inverse morphism must be statically refused as EFFECT_UNDO
    inv_law = lift_verified_diff_to_semantic_law(
        before_bytes=after_src,
        after_bytes=before_src,
        language="python",
        sabotage_verified=True,
        contrast_verified=True,
    )
    assert inv_law is not None
    assert store.check_contract_composition(law, inv_law)["verdict"] == CONTRACT_EFFECT_UNDO
    assert store.admit_law(inv_law) is False

    # 1-shot instantiation on completely unseen class/method/attribute names
    unseen = (
        b"class OptionFlag:\n"
        b"    def build_row(self, env, compact=False):\n"
        b"        if self.summary is None:\n"
        b"            return None\n"
        b"        return (self.render_spec(env, compact), self.summary)\n"
    )
    cands = store.match_and_compile_candidates(unseen, "python", target_func_name="build_row")
    assert len(cands) == 1
    assert "return (self.render_spec(env, compact), self.summary or '')" in cands[0][1].decode()

    # O(1) surgical revocation
    assert store.remove_law(law.law_id) is True
    assert store.match_and_compile_candidates(unseen, "python", target_func_name="build_row") == []


def test_bidirectional_fst_caret_and_affix_lens_roundtrip_and_repo_solve(tmp_path: Path) -> None:
    from canonical.swe_kernel.cow_lens_fuzz_and_negative_space_v1 import (
        synthesize_bidirectional_fst_lens,
    )

    caret_lens = synthesize_bidirectional_fst_lens(
        [(b"echo\x04eof\x1a!", "echo^Deof^Z!"), (b"lit^caret\x7f", "lit^^caret^?")]
    )
    assert caret_lens is not None and caret_lens.roundtrip_verified
    ns: dict[str, object] = {}
    exec(caret_lens.compile_forward_fn_source("fwd"), ns)  # noqa: S102
    exec(caret_lens.compile_backward_fn_source("bwd"), ns)  # noqa: S102
    assert ns["fwd"](b"a\x04b\x1a") == "a^Db^Z"  # type: ignore[operator]
    assert ns["bwd"]("a^Db^Z") == b"a\x04b\x1a"  # type: ignore[operator]

    rstrip_lens = synthesize_bidirectional_fst_lens([("/api/v1/", "/api/v1"), ("/", "/")])
    assert rstrip_lens is not None and rstrip_lens.lens_family == "DELIMITER_RSTRIP_IDENTITY_FLOOR_LENS"

    # End-to-end repository solve via FST witness synthesis
    repo = tmp_path / "ctrl_repo"
    repo.mkdir()
    (repo / "echo_codec.py").write_text(
        "def format_echo(chunk: bytes) -> str:\n"
        "    s = chunk.decode('latin1')\n"
        "    return s\n"
    )
    (repo / "test_echo_codec.py").write_text(
        "from echo_codec import format_echo\n"
        "def test_ascii(): assert format_echo(b'ok\\n') == 'ok\\n'\n"
        "def test_ctrl_bytes(): assert format_echo(b'in\\x04out\\x1a') == 'in^Dout^Z'\n"
    )
    inv = CausalCEGISInventor(law_store_path=tmp_path / "fst_laws.json", sandbox_budget=24)
    res = inv.solve_repository(repo, language="python", test_target="test_echo_codec.py", timeout_sec=10.0)
    assert res.solved is True


def test_cow_64_boundary_fuzzer_angelic_blame_and_l3_negative_space(tmp_path: Path) -> None:
    from canonical.swe_kernel.cow_lens_fuzz_and_negative_space_v1 import (
        NegativeSpaceInvariantStore,
        angelic_cow_fault_blame,
        verify_cow_boundary_invariance,
    )

    orig = b"def pair(x):\n    return (x, x)\n"
    unsafe = b"def pair(x):\n    return (x, x.strip())\n"
    safe = b"def pair(x):\n    return (x, x or '')\n"
    v_bad = verify_cow_boundary_invariance(orig, unsafe, "pair")
    v_ok = verify_cow_boundary_invariance(orig, safe, "pair")
    assert not v_bad.passed and v_bad.new_unexpected_crashes > 0
    assert v_ok.passed and v_ok.cases_executed == 64

    class _Chain:
        @staticmethod
        def a(s: str) -> str:
            return s.strip()

        @staticmethod
        def b(s: str) -> str:
            return s.rstrip("/")

        @staticmethod
        def c(s: str) -> str:
            return f"<{s}>"

    blamed = angelic_cow_fault_blame(
        failing_callable=lambda: (_ for _ in ()).throw(AssertionError())
        if _Chain.c(_Chain.b(_Chain.a("/"))) != "</>"
        else None,
        suspect_targets=[(_Chain, "a"), (_Chain, "b"), (_Chain, "c")],
        angelic_values=["/"],
    )
    assert blamed == ["b"]

    neg = NegativeSpaceInvariantStore(tmp_path / "neg.json")
    rec = neg.record_refutation(
        orig_snippet="return (self.make_metavar(ctx), self.help)",
        cand_snippet="return (self.make_metavar(ctx), self.help.strip())",
        refutation_reason="COW_64_BOUNDARY_REGRESSION",
    )
    assert rec is not None
    assert (
        neg.is_refuted(
            "return (self.render_flag(env), self.doc)",
            "return (self.render_flag(env), self.doc.strip())",
        )
        is not None
    )
    assert neg.revoke_invariant(rec.invariant_id) is True
    assert (
        neg.is_refuted(
            "return (self.render_flag(env), self.doc)",
            "return (self.render_flag(env), self.doc.strip())",
        )
        is None
    )


def test_articulation_point_cut_vertex_360_step_checkpoint_rollback() -> None:
    t_undo_1 = PetriTransition("off", "ui", frozenset({"ON"}), frozenset({"OFF"}), frozenset({"ON"}))
    t_undo_2 = PetriTransition("on", "ui", frozenset({"OFF"}), frozenset({"ON"}), frozenset({"OFF"}))
    ok_u, msg_u = CrossModalPetriPlanner.verify_plan_effect_contracts([t_undo_1, t_undo_2])
    assert not ok_u and "EFFECT_UNDO" in msg_u

    calls = {"n": 0}

    def _flaky_317() -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient fault at step 317")

    steps = [
        PetriTransition(
            action_id=f"st_{i:03d}",
            modality=("ui", "cli", "sqlite", "fs")[i % 4],
            preconditions=frozenset({f"p_{i}", "CONSENT_OK"}),
            add_tokens=frozenset({f"p_{i+1}"}),
            executor=_flaky_317 if i == 317 else None,
        )
        for i in range(360)
    ]
    plan = CrossModalPetriPlanner.plan_trajectory(
        frozenset({"p_0", "CONSENT_OK"}),
        frozenset({"p_360"}),
        frozenset({"LOSS_WITHOUT_CONSENT"}),
        steps,
    )
    assert plan is not None and len(plan) == 360
    res = CrossModalPetriPlanner.execute_checkpointed_horizon(
        initial_tokens=frozenset({"p_0", "CONSENT_OK"}),
        goal_tokens=frozenset({"p_360"}),
        forbidden_tokens=frozenset({"LOSS_WITHOUT_CONSENT"}),
        plan=plan,
        max_episode_len=30,
    )
    assert res["completed"] is True
    assert res["episode_count"] == 12
    assert res["articulation_cuts"] == 12
    assert res["rollbacks_performed"] == 1
    assert res["steps_replayed_on_rollback"] == 30


def test_issue_only_oracle_abduction_without_test_leakage(tmp_path: Path) -> None:
    repo = tmp_path / "hdr_repo"
    repo.mkdir()
    (repo / "hdr.py").write_text(
        'class AuthHeader:\n'
        '    def __init__(self, scheme: str, params: str = "") -> None:\n'
        '        self.scheme = scheme\n'
        '        self.params = params\n'
        '    def render(self) -> str:\n'
        '        return f"{self.scheme} {self.params}"\n',
        encoding="utf-8",
    )
    # Existing baseline test passes 100% (no failing test in repo!)
    tdir = repo / "tests"
    tdir.mkdir()
    (tdir / "test_hdr.py").write_text(
        'from hdr import AuthHeader\n'
        'def test_with_params() -> None:\n'
        '    assert AuthHeader("Bearer", "realm=api").render() == "Bearer realm=api"\n',
        encoding="utf-8",
    )
    issue = (
        'Bug: `AuthHeader("Bearer").render()` adds a trailing space when params are empty.\n'
        'Expected output: `"Bearer"` instead of `"Bearer "`.\n'
    )
    inv = CausalCEGISInventor(law_store_path=tmp_path / "laws.json", sandbox_budget=30)
    res = inv.solve_repository(repo, language="python", problem_statement=issue, timeout_sec=15.0)
    assert res.solved is True
    assert list(res.modified_files.keys()) == ["hdr.py"]
    assert not (repo / "_cogs_abduced_issue_repro_test.py").exists()
    assert res.source_tree_unchanged is True


def test_semantic_law_store_subsumption_compaction(tmp_path: Path) -> None:
    from canonical.swe_kernel.universal_semantic_ir_v1 import (
        SemanticCausalLawStore,
        lift_verified_diff_to_semantic_law,
    )

    general_law = lift_verified_diff_to_semantic_law(
        before_bytes=(
            b"def f(self):\n"
            b"    if self.help is None:\n"
            b"        return None\n"
            b"    return (self.name, self.help)\n"
        ),
        after_bytes=(
            b"def f(self):\n"
            b"    return (self.name, self.help or '')\n"
        ),
        language="python",
        sabotage_verified=True,
        contrast_verified=True,
    )
    alpha_dup_law = lift_verified_diff_to_semantic_law(
        before_bytes=(
            b"def g(item):\n"
            b"    if item.doc is None:\n"
            b"        return None\n"
            b"    return (item.label, item.doc)\n"
        ),
        after_bytes=(
            b"def g(item):\n"
            b"    return (item.label, item.doc or '')\n"
        ),
        language="python",
        sabotage_verified=True,
        contrast_verified=True,
    )
    assert general_law is not None and alpha_dup_law is not None
    store = SemanticCausalLawStore(tmp_path / "compact_laws.json")
    store.laws = [general_law, alpha_dup_law]
    stats = store.compact_laws()
    assert stats == {"before": 2, "after": 1, "pruned": 1}


def test_harbor_container_worker_zero_llm_fallback(tmp_path: Path) -> None:
    import base64
    import subprocess

    worker = Path(__file__).resolve().parents[1] / "runtime" / "harbor_container_solver_worker_v1.py"
    req = {
        "goal": 'Create a file called hello.txt with "Hello, world!" as the content.',
        "inputs": {"harbor_task": 'Create a file called hello.txt with "Hello, world!" as the content.'},
        "mode": "EPISTEMIC",
    }
    b64 = base64.b64encode(json.dumps(req).encode("utf-8")).decode("ascii")
    proc = subprocess.run(
        ["env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "python3", "-I", "-B", str(worker), b64],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8").strip() == "Hello, world!"
    assert '"PASS__ZERO_LLM_COW_PETRI_TERMINAL"' in proc.stdout


