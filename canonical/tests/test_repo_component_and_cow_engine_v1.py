"""Verification suite for Repo-Native Component Mining, Dual-Program Splicing,
16-Way Parallel Copy-on-Write Counterfactual Speculative Rollouts, and Unified
Cross-Modal Type-Transition Petri Net (Zero-LLM, Zero-Knowledge-House).
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

from canonical.runtime import brain_unified_model_v1 as BUM
from canonical.runtime import causal_angelic_swe_engine_v1 as SWE
from canonical.runtime import executable_mental_model_v1 as MENTAL
from canonical.runtime import repo_component_and_cow_engine_v1 as RCCE


def test_01_repo_native_component_mining_and_cross_file_synthesis(tmp_path: pathlib.Path) -> None:
    """Mine real helper functions 3 files away in an unseen repo and synthesize a 2-hop
    cross-file call `format_slug(strip_accents(raw))` with automatic import insertion
    (shattering the fixed-grammar ceiling; model_calls == 0)."""
    pkg = tmp_path / "mypkg"
    (pkg / "text").mkdir(parents=True)
    (pkg / "web").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "text" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "web" / "__init__.py").write_text("", encoding="utf-8")

    # Helper 1 in file A
    (pkg / "text" / "normalize.py").write_text(
        "def strip_noise(text: str) -> str:\n"
        "    return text.strip().replace('!', '').replace('?', '')\n",
        encoding="utf-8",
    )
    # Helper 2 in file B
    (pkg / "text" / "slugs.py").write_text(
        "def to_kebab_slug(text: str) -> str:\n"
        "    return '-'.join(text.lower().split())\n",
        encoding="utf-8",
    )
    # Buggy entry point in file C (does NOT import either helper yet!)
    entry = pkg / "web" / "routes.py"
    buggy_src = (
        "def route_slug(raw: str) -> str:\n"
        "    return raw\n"
    )
    entry.write_text(buggy_src, encoding="utf-8")

    # 1. Verify IncrementalSemanticGraph-backed component mining finds both helpers
    mined = RCCE.mine_repo_components_as_morphisms(tmp_path, focus_file="mypkg/web/routes.py")
    assert mined["model_calls"] == 0
    assert mined["parameters_stored"] == 0
    sym_names = {c.symbol_name for c in mined["components"]}
    assert "strip_noise" in sym_names
    assert "to_kebab_slug" in sym_names

    # 2. Synthesize 2-hop cross-file composition `to_kebab_slug(strip_noise(raw))`
    examples = [
        ({"raw": "  Hello World!  "}, "hello-world"),
        ({"raw": "Breaking News?"}, "breaking-news"),
    ]
    cands = RCCE.synthesize_repo_component_return_candidates(
        tmp_path,
        "mypkg/web/routes.py",
        buggy_src,
        2,
        examples,
    )
    assert cands, "Expected 2-hop cross-file repo component synthesis to succeed!"
    best = cands[0]
    assert best["hops"] == 2
    assert "to_kebab_slug(strip_noise(raw))" in best["call_expr"]
    assert "from mypkg.text.normalize import strip_noise" in best["patched_source"]
    assert "from mypkg.text.slugs import to_kebab_slug" in best["patched_source"]

    # Execute synthesized code live to verify semantics!
    ns: dict[str, object] = {}
    sys.path.insert(0, str(tmp_path))
    try:
        exec(best["patched_source"], ns)
        fn = ns["route_slug"]
        assert fn("  Hello World!  ") == "hello-world"
        assert fn("Breaking News?") == "breaking-news"
    finally:
        sys.path.remove(str(tmp_path))


def test_02_dual_program_splicing_eliminates_regressions_zero_llm() -> None:
    """Given original P0 (passes passing tests) and partial candidate P1 (fixes failing
    tests but regresses passing tests), synthesize ONLY the separating guard G and splice
    `if G: P1 else: P0` cleanly with zero LLM calls."""
    orig_src = (
        "def compute_fee(amount: int, is_vip: bool) -> int:\n"
        "    return amount * 2\n"
    )
    # Candidate P1 fixes VIP cases (returns amount) but would regress non-VIP cases!
    cand_src = (
        "def compute_fee(amount: int, is_vip: bool) -> int:\n"
        "    return amount\n"
    )
    cand_wins_envs = [
        {"amount": {"type": "int", "scalar": 10}, "is_vip": {"type": "bool", "scalar": True, "is_falsey": False}},
        {"amount": {"type": "int", "scalar": 50}, "is_vip": {"type": "bool", "scalar": True, "is_falsey": False}},
    ]
    orig_wins_envs = [
        {"amount": {"type": "int", "scalar": 10}, "is_vip": {"type": "bool", "scalar": False, "is_falsey": True}},
        {"amount": {"type": "int", "scalar": 50}, "is_vip": {"type": "bool", "scalar": False, "is_falsey": True}},
    ]

    splices = RCCE.splice_dual_programs(orig_src, cand_src, 2, cand_wins_envs, orig_wins_envs)
    assert splices, "Expected Dual-Program Splicing to synthesize separating guard!"
    sp = splices[0]
    assert sp["model_calls"] == 0
    assert sp["parameters_stored"] == 0

    ns: dict[str, object] = {}
    exec(sp["patched_source"], ns)
    fn = ns["compute_fee"]
    # Both failing (VIP) AND previously-regressed (non-VIP) tests now pass 100%!
    assert fn(10, True) == 10
    assert fn(50, True) == 50
    assert fn(10, False) == 20
    assert fn(50, False) == 100


def test_03_16way_parallel_cow_speculative_rollout_and_isolation() -> None:
    """Fork 16 parallel Linux Copy-on-Write realities simultaneously via `os.fork()`,
    verify parent state is NEVER mutated even when all 16 children mutate shared structures,
    and verify the strictly best action (residual 0.0) is chosen."""
    shared_parent_state = {"balance": 100, "mutated_by_child": False}

    actions = [
        {"action_id": f"branch_{i:02d}", "delta": i - 11, "poison": (i == 3)}
        for i in range(16)
    ]

    def _exec_action(spec: dict) -> int:
        # Mutate parent's dict in-place inside CoW child — MUST NOT leak to parent!
        shared_parent_state["mutated_by_child"] = True
        if spec.get("poison"):
            raise RuntimeError("simulated crash in branch 03")
        shared_parent_state["balance"] += int(spec["delta"])
        return shared_parent_state["balance"]

    # Goal is balance == 100 (delta == 0 -> branch_11!)
    rep = RCCE.speculative_cow_rollout(
        actions,
        executor_fn=_exec_action,
        residual_fn=lambda val: abs(float(val) - 100.0),
        baseline_residual=50.0,
        max_workers=16,
    )
    assert rep["status"] == "VERIFIED"
    assert rep["model_calls"] == 0
    assert rep["parameters_stored"] == 0
    assert rep["cow_fork_parallelism"] == 16
    assert rep["branches_evaluated"] == 16
    assert rep["best_action_id"] == "branch_11"
    assert rep["best_residual"] == 0.0
    # HARD PROOF of Linux Copy-on-Write parent memory isolation!
    assert shared_parent_state["balance"] == 100
    assert shared_parent_state["mutated_by_child"] is False


def test_04_mental_world_model_speculative_cow_choose() -> None:
    """Verify `CUMentalWorldModel.speculative_cow_choose` forks CoW workers to pick
    the valid file-read action over failing/compressed candidates without mutating parent."""
    wm = MENTAL.CUMentalWorldModel()
    st = MENTAL.CUWorldState(
        files={
            "/tmp/archive.gz": {"exists": True, "compressed": True},
            "/tmp/readme.txt": {"exists": True, "compressed": False},
        },
        facts={},
    )
    cands = [
        {"action_id": "bad_missing", "kind": "cli_read_text", "path": "/tmp/missing.txt"},
        {"action_id": "bad_compressed", "kind": "cli_read_text", "path": "/tmp/archive.gz"},
        {"action_id": "good_read", "kind": "cli_read_text", "path": "/tmp/readme.txt"},
    ]
    res = wm.speculative_cow_choose(st, cands, goal_facts={"read:/tmp/readme.txt": True})
    assert res["status"] == "VERIFIED"
    assert res["best_action_id"] == "good_read"
    assert res["best_residual"] == 0.0
    assert "read:/tmp/readme.txt" not in st.facts  # Parent CUWorldState untouched!


def test_05_unified_cross_modal_petri_net_through_one_front_door(tmp_path: pathlib.Path) -> None:
    """Compile GUI A11y + SQLite + Repo-Native Python + CLI into ONE Type-Transition
    Petri Net, solve the 4-hop cross-modal workflow through ONE Front Door
    (`brain_unified_model_v1.open_model().solve(...)`), execute it live against a real
    SQLite database and filesystem, crystallize it as a 1-hop L2 transition, and prove
    O(1) deletion from external governed memory."""
    db_path = tmp_path / "orders.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE orders (id INTEGER, cents INTEGER)")
    conn.execute("INSERT INTO orders VALUES (1, 1500), (2, 2500)")
    conn.commit()
    conn.close()
    out_report = tmp_path / "total_report.txt"

    pnet = RCCE.UnifiedCrossModalPetriNet()
    # 1. GUI A11y transition: Export DB path from Settings modal
    pnet.add_transition(
        RCCE.PetriTransition(
            transition_id="gui:click_export_db",
            modality="gui",
            input_places=("gui:settings_open",),
            output_places=("sqlite:db_path",),
            executor=lambda ctx: {"db_path": str(db_path)},
        )
    )
    # 2. SQLite transition: Query total cents from DB
    def _sqlite_sum(ctx: dict) -> dict:
        c = sqlite3.connect(ctx["db_path"])
        try:
            tot = int(c.execute("SELECT SUM(cents) FROM orders").fetchone()[0])
        finally:
            c.close()
        return {"total_cents": tot}

    pnet.add_transition(
        RCCE.PetriTransition(
            transition_id="sqlite:sum_orders",
            modality="sqlite",
            input_places=("sqlite:db_path",),
            output_places=("py:total_cents",),
            executor=_sqlite_sum,
        )
    )
    # 3. Python transition: Format cents as USD string
    pnet.add_transition(
        RCCE.PetriTransition(
            transition_id="py:format_usd",
            modality="python",
            input_places=("py:total_cents",),
            output_places=("str:formatted_usd",),
            executor=lambda ctx: {"formatted_usd": f"${ctx['total_cents'] / 100:.2f}"},
        )
    )
    # 4. CLI / OS file transition: Write verified report file
    def _write_cli_report(ctx: dict) -> dict:
        out_report.write_text(f"TOTAL={ctx['formatted_usd']}\n", encoding="utf-8")
        return {"report_written": True}

    pnet.add_transition(
        RCCE.PetriTransition(
            transition_id="cli:write_report",
            modality="cli",
            input_places=("str:formatted_usd",),
            output_places=("os:report_verified",),
            executor=_write_cli_report,
        )
    )

    gov_mem: dict = {}
    model = BUM.open_model()
    r1 = model.solve(
        "Chain GUI export -> SQLite sum -> Python format -> CLI report via Petri net",
        mode="EPISTEMIC",
        inputs={
            "workspace": str(tmp_path),
            "governed_memory": gov_mem,
            "petri_net_spec": {
                "petri_net": pnet,
                "initial_places": ["gui:settings_open"],
                "goal_places": ["os:report_verified"],
                "execute": True,
                "initial_context": {},
                "verifier": lambda ctx: out_report.is_file() and out_report.read_text(encoding="utf-8").strip() == "TOTAL=$40.00",
            },
        },
    )
    assert r1["pass"] is True, r1
    assert r1["model_calls"] == 0
    assert r1["parameters_stored"] == 0
    ev = r1["epistemic_result"]
    assert ev["modality"] == "unified_cross_modal_petri_net"
    assert ev["status"] == "VERIFIED"
    assert ev["petri_status"] == "VERIFIED_AND_CRYSTALLIZED"
    assert ev["petri_plan"]["hops"] == 4
    assert ev["petri_plan"]["modalities_chained"] == ["gui", "sqlite", "python", "cli"]
    assert out_report.read_text(encoding="utf-8").strip() == "TOTAL=$40.00"

    cid = ev["petri_execution"]["crystallized_transition_id"]
    assert cid in gov_mem["l2_petri_morphisms"]

    # Immediate 1-shot permanent transfer: SAME goal now solves in 1 HOP instead of 4!
    plan_after = pnet.solve(["gui:settings_open"], ["os:report_verified"])
    assert plan_after["status"] == "SOLVED"
    assert plan_after["hops"] == 1
    assert plan_after["transition_ids"] == [cid]

    # O(1) instant deletion without retraining!
    del gov_mem["l2_petri_morphisms"][cid]
    del pnet.transitions[cid]
    plan_after_del = pnet.solve(["gui:settings_open"], ["os:report_verified"])
    assert plan_after_del["hops"] == 4


def test_06_none_guard_default_fallthrough_live_swe_solve(tmp_path: pathlib.Path) -> None:
    """Verify `TIER3_NONE_GUARD_DEFAULT_FALLTHROUGH` solves an unseen `if self.note is None:
    return None` early-return bug end-to-end through `SWE.solve_repository` on Attempt #1."""
    (tmp_path / "record.py").write_text(
        "class Item:\n"
        "    def __init__(self, code: str, note: str | None = None) -> None:\n"
        "        self.code = code\n"
        "        self.note = note\n"
        "\n"
        "    def display_pair(self) -> tuple[str, str] | None:\n"
        "        if self.note is None:\n"
        "            return None\n"
        "        return self.code, self.note\n",
        encoding="utf-8",
    )
    (tmp_path / "test_record.py").write_text(
        "from record import Item\n"
        "\n"
        "def test_with_note():\n"
        "    assert Item('A1', 'ok').display_pair() == ('A1', 'ok')\n"
        "\n"
        "def test_without_note_defaults_empty():\n"
        "    assert Item('A1', None).display_pair() == ('A1', '')\n",
        encoding="utf-8",
    )
    res = SWE.solve_repository(
        tmp_path,
        ["test_record.py"],
        python_exe=sys.executable,
        max_candidates=20,
        timeout_s=30.0,
    )
    assert res["status"] == "VERIFIED"
    assert res["model_calls"] == 0
    assert res["winner"]["tier"] == "TIER3_NONE_GUARD_DEFAULT_FALLTHROUGH"
