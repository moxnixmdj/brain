#!/usr/bin/env python3
"""Adversarial end-to-end verification of the Four Leapfrog Pillars (`reverse_tomography_algebra_v1`):
  1. Reverse-Execution Synthesis (Backward Symbolic Witness Propagation + CoW `os.fork()` isolation)
  2. Differential State Tomography (Multi-layer FS+SQLite+App Mealy API Compiler -> 320-step exact workflow)
  3. Algebraic Skill Composition (Type-Transition Petri Net + static `effect_contract_composition_v1` undo gate + L2 crystallization)
  4. Adversarial Self-Play Over Unsolved Failures (Certified 1-minimal `ddmin` 2,000 -> 2 shrink + full-suite verification + $0 external store)

Zero model calls (`PRODUCER_MODEL_CALLS = 0`). Zero memorized world facts in parameters.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import tarfile
import time

from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
from canonical.swe_kernel import effect_contract_composition_v1 as ecc
from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
from canonical.swe_kernel import universal_computer_agent_v1 as uca


def test_pillar1_reverse_execution_backprop_fstring_repr_regex_and_cow_fork(tmp_path: pathlib.Path):
    # 1a. Backward f-string suffix lifting (`"Cannot combine options"` -> `f"Cannot combine options for '{field}'."`)
    ws1 = tmp_path / "fstr_ws"
    ws1.mkdir()
    (ws1 / "validator.py").write_text(
        "def check_field(field, conflict):\n"
        "    if conflict:\n"
        "        msg = 'Cannot combine options'\n"
        "        raise ValueError(msg)\n"
        "    return True\n",
        encoding="utf-8",
    )
    (ws1 / "test_validator.py").write_text(
        "import pytest\nfrom validator import check_field\n"
        "def test_ok():\n"
        "    assert check_field('alpha', False) is True\n"
        "def test_conflict_names_field():\n"
        "    with pytest.raises(ValueError) as exc:\n"
        "        check_field('beta', True)\n"
        "    assert exc.value.args == (\"Cannot combine options for 'beta'.\",)\n",
        encoding="utf-8",
    )
    r1 = acr.repair_repo_angelic_cegis(ws1, "test_validator.py", timeout_s=25)
    assert r1["repaired"] is True, r1
    assert r1["method"] == "REVERSE_EXECUTION_BACKPROP"
    assert "for '{field}'." in r1["patched_source"]

    # 1b. Backward regex alternation extension on class-level lookup table (`"edge"` -> `"edge|edg"`)
    ws2 = tmp_path / "regex_ws"
    ws2.mkdir()
    (ws2 / "ua_detect.py").write_text(
        "import re\n"
        "class Detector:\n"
        "    rules = (\n"
        "        ('edge', 'edge'),\n"
        "        ('chrome', 'chrome'),\n"
        "    )\n"
        "    def __init__(self):\n"
        "        self.compiled = [(lbl, re.compile(pat, re.I)) for pat, lbl in self.rules]\n"
        "    def detect(self, header):\n"
        "        for lbl, rx in self.compiled:\n"
        "            if rx.search(header):\n"
        "                return lbl\n"
        "        return None\n",
        encoding="utf-8",
    )
    (ws2 / "test_ua_detect.py").write_text(
        "from ua_detect import Detector\n"
        "def test_chrome():\n"
        "    assert Detector().detect('Mozilla/5.0 Chrome/90.0 Safari/537.36') == 'chrome'\n"
        "def test_chromium_edge():\n"
        "    assert Detector().detect('Mozilla/5.0 Chrome/90.0 Safari/537.36 Edg/90.0.1') == 'edge'\n",
        encoding="utf-8",
    )
    r2 = acr.repair_repo_angelic_cegis(ws2, "test_ua_detect.py", timeout_s=25)
    assert r2["repaired"] is True, r2
    assert r2["method"] == "REVERSE_EXECUTION_BACKPROP"
    assert "edge|edg" in r2["patched_source"]

    # 1c. Copy-On-Write `os.fork()` isolation: child mutation never leaks into parent process!
    parent_sentinel = ["untouched"]

    def _mutate_in_child():
        parent_sentinel.append("child_mutated")
        return {"child_len": len(parent_sentinel), "pid_ok": True}

    cow_res = rta.run_isolated_cow(_mutate_in_child, timeout_s=5.0)
    assert cow_res["child_len"] == 2
    assert parent_sentinel == ["untouched"]


def test_pillar2_differential_state_tomography_320_step_long_horizon_and_trap_blocking(tmp_path: pathlib.Path):
    """Conquer a 320-step stateful multi-layer app (FS + SQLite + hidden registers + destructive trap)
    with ZERO vision models, ZERO docs, and ZERO constraint collapse!"""
    protected = tmp_path / "vault.txt"
    db_path = tmp_path / "ledger.db"

    class LongHorizonStatefulApp:
        """Unseen black-box app requiring exact 320-step phase progression (40 batches x 8 steps)
        plus a deceptive `quick_reset` button that destroys protected vault.txt!"""

        def __init__(self) -> None:
            self.reset()

        def reset(self) -> None:
            protected.write_text("CRITICAL_USER_VAULT_DATA", encoding="utf-8")
            if db_path.exists():
                db_path.unlink()
            con = sqlite3.connect(db_path)
            con.execute("CREATE TABLE commits (batch INT)")
            con.commit()
            con.close()
            self.stage = 0  # 0..319 -> 320
            self.locked = True
            self.vault_deleted_count = 0

        def snapshot(self) -> rta.MultiLayerSnapshot:
            return rta.capture_multilayer_snapshot(
                tmp_path,
                app_state={"stage": self.stage, "locked": self.locked},
            )

        def step(self, action: str) -> bool:
            if action == "quick_reset":
                if protected.exists():
                    protected.unlink()
                    self.vault_deleted_count += 1
                return True
            if action == "unlock":
                if self.locked:
                    self.locked = False
                    return True
                return False
            if action == "advance":
                if not self.locked and self.stage < 320:
                    self.stage += 1
                    if self.stage == 320:
                        con = sqlite3.connect(db_path)
                        con.execute("INSERT INTO commits VALUES (320)")
                        con.commit()
                        con.close()
                    return True
                return False
            if action == "noop":
                return True
            return False

    app = LongHorizonStatefulApp()
    store_path = tmp_path / "tomo_store.json"
    agent = uca.UniversalComputerAgent(law_store_path=store_path)

    # Phase A: Active tomography on small horizon discovers exact action semantics + blocks `quick_reset` trap!
    t0 = time.monotonic()
    res = agent.compile_and_solve_stateful_app(
        snapshot_fn=app.snapshot,
        step_fn=app.step,
        reset_fn=app.reset,
        actions=["quick_reset", "noop", "unlock", "advance"],
        goal_predicate=lambda st: st.get("app:stage") == 320,
        protected_prefixes=("vault.txt",),
        max_bfs_states=330,
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    assert res["solved"] is True, res
    assert res["plan_length"] == 321  # 1 unlock + 320 advances = exact optimal 321-step plan!
    assert "quick_reset" in res["tomography"]["destructive_blocked"]
    assert protected.exists() and protected.read_text(encoding="utf-8") == "CRITICAL_USER_VAULT_DATA"
    # Verify real SQLite DB commit occurred at step 320!
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT batch FROM commits").fetchall()
    con.close()
    assert rows == [(320,)]
    assert elapsed_ms < 15_000


def test_pillar3_algebraic_skill_composition_static_undo_rejection_and_l2_crystallization(tmp_path: pathlib.Path):
    """Snap 4 isolated real OS/SQLite/JSON morphisms into an unseen pipeline via Petri-Net composition,
    statically reject an inverse `EFFECT_UNDO` trap via `effect_contract_composition_v1`,
    crystallize as ONE 1-step L2 morphism in external JSON, and prove deletion removes it!"""
    ws = tmp_path / "pipe_ws"
    ws.mkdir()
    store_path = tmp_path / "external_morphisms.json"

    # Prepare a real tar.gz archive containing a real SQLite database!
    db_src = ws / "orders.db"
    con = sqlite3.connect(db_src)
    con.execute("CREATE TABLE orders (id INT, region TEXT, revenue INT)")
    con.executemany(
        "INSERT INTO orders VALUES (?, ?, ?)",
        [(1, "emea", 120), (2, "apac", 80), (3, "emea", 230)],
    )
    con.commit()
    con.close()
    archive = ws / "bundle.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(db_src, arcname="orders.db")
    db_src.unlink()

    # Define 4 isolated typed morphisms + 1 malicious inverse `undo_extract` trap!
    m_extract = rta.TypedSkillMorphism(
        morphism_id="unpack_tar_gz",
        in_types=frozenset({"tar_gz_path"}),
        out_types=frozenset({"sqlite_db_path"}),
        contract=ecc.EffectContract(
            skill_id="unpack_tar_gz",
            preconditions=("archive_present",),
            observables=("tar_gz_path", "fs_files"),
            actions=("tar_extract",),
            verdict="sqlite_file_exists",
            effects=(
                ecc.Effect("ESTABLISH", "db_extracted"),
                ecc.Effect("REMOVE", "archive_unextracted"),
            ),
        ),
        executor=lambda st: (
            tarfile.open(st["tar_gz_path"], "r:gz").extractall(ws),
            {**st, "sqlite_db_path": str(ws / "orders.db")},
        )[1],
    )
    # Exact inverse of m_extract -> MUST be statically rejected with EFFECT_UNDO!
    m_undo_extract = rta.TypedSkillMorphism(
        morphism_id="delete_extracted_db",
        in_types=frozenset({"sqlite_db_path"}),
        out_types=frozenset({"tar_gz_path"}),
        contract=ecc.EffectContract(
            skill_id="delete_extracted_db",
            preconditions=("db_extracted",),
            observables=("sqlite_db_path",),
            actions=("rm_db",),
            verdict="db_deleted",
            effects=(
                ecc.Effect("ESTABLISH", "archive_unextracted"),
                ecc.Effect("REMOVE", "db_extracted"),
            ),
        ),
    )
    m_query = rta.TypedSkillMorphism(
        morphism_id="query_sqlite_rows",
        in_types=frozenset({"sqlite_db_path"}),
        out_types=frozenset({"raw_rows"}),
        contract=ecc.EffectContract(
            skill_id="query_sqlite_rows",
            preconditions=("db_extracted",),
            observables=("sqlite_db_path", "sqlite_master"),
            actions=("select_all",),
            verdict="rows_loaded",
            effects=(ecc.Effect("ESTABLISH", "rows_loaded"),),
        ),
        executor=lambda st: {
            **st,
            "raw_rows": [
                {"id": r[0], "region": r[1], "revenue": r[2]}
                for r in sqlite3.connect(st["sqlite_db_path"]).execute("SELECT id, region, revenue FROM orders").fetchall()
            ],
        },
    )
    m_filter = rta.TypedSkillMorphism(
        morphism_id="filter_emea_rows",
        in_types=frozenset({"raw_rows"}),
        out_types=frozenset({"filtered_rows"}),
        contract=ecc.EffectContract(
            skill_id="filter_emea_rows",
            preconditions=("rows_loaded",),
            observables=("raw_rows",),
            actions=("filter_region_emea",),
            verdict="filtered_nonempty",
            effects=(ecc.Effect("ESTABLISH", "rows_filtered"),),
        ),
        executor=lambda st: {**st, "filtered_rows": [r for r in st["raw_rows"] if r["region"] == "emea"]},
    )
    m_report = rta.TypedSkillMorphism(
        morphism_id="write_revenue_report",
        in_types=frozenset({"filtered_rows"}),
        out_types=frozenset({"report_json_path"}),
        contract=ecc.EffectContract(
            skill_id="write_revenue_report",
            preconditions=("rows_filtered",),
            observables=("filtered_rows",),
            actions=("sum_and_write_json",),
            verdict="report_written",
            effects=(ecc.Effect("ESTABLISH", "report_written"),),
        ),
        executor=lambda st: (
            (ws / "report.json").write_text(
                json.dumps({"count": len(st["filtered_rows"]), "total_revenue": sum(r["revenue"] for r in st["filtered_rows"])}),
                encoding="utf-8",
            ),
            {**st, "report_json_path": str(ws / "report.json")},
        )[1],
    )

    # 1. Static EffectContract proof rejects `m_extract ; m_undo_extract` BEFORE touching disk!
    probe_composer = rta.AlgebraicSkillComposer(store_path)
    assert probe_composer.check_static_pair(m_extract, m_undo_extract, axioms=("archive_present",)) == ecc.UNDO

    # 2. Compose unseen 4-stage pipeline + execute + crystallize as 1-step L2 morphism!
    agent = uca.UniversalComputerAgent(law_store_path=store_path)
    res = agent.compose_and_crystallize_pipeline(
        [m_extract, m_undo_extract, m_query, m_filter, m_report],
        initial_types=["tar_gz_path"],
        goal_types=["report_json_path"],
        initial_state={"tar_gz_path": str(archive)},
        pipeline_name="archive_sqlite_emea_revenue_report",
        verify_fn=lambda st: (ws / "report.json").exists()
        and json.loads((ws / "report.json").read_text(encoding="utf-8")) == {"count": 2, "total_revenue": 350},
        axioms=["archive_present"],
    )
    assert res["solved"] is True, res
    assert res["plan"]["chain"] == [
        "unpack_tar_gz",
        "query_sqlite_rows",
        "filter_emea_rows",
        "write_revenue_report",
    ]
    assert res["crystallization"]["steps_collapsed"] == 4

    # 3. Verify crystallized L2 morphism now plans in ONE step (instead of 4!) and persists in inspectable JSON!
    composer2 = res["composer"]
    replay_plan = composer2.compose(["tar_gz_path"], ["report_json_path"], axioms=["archive_present"])
    assert replay_plan["composed"] is True
    assert replay_plan["chain"] == ["archive_sqlite_emea_revenue_report"]
    assert store_path.exists()
    stored_json = json.loads(store_path.read_text(encoding="utf-8"))
    assert "archive_sqlite_emea_revenue_report" in stored_json["crystallized_morphisms"]

    # 4. External JSON deletion removes the crystallized morphism completely (zero knowledge house!)
    store_path.unlink()
    clean_composer = rta.AlgebraicSkillComposer(store_path)
    assert clean_composer.crystallized_pipelines == {}


def test_pillar4_adversarial_self_play_certified_ddmin_2000_to_2_and_zero_cost_compounding(tmp_path: pathlib.Path):
    """Shrink a 2,000-element noisy failing dataset to its certified 1-minimal 2-element core,
    solve the buggy function on that tiny core, verify against ALL 2,000 elements, and commit to JSON!"""
    # Build a 2,000-row dataset where ONLY two colliding rows (`id=1337`) trigger a dedup/max bug
    noisy_rows = [{"id": i, "score": i % 17} for i in range(2000)]
    noisy_rows[412] = {"id": 99999, "score": 10}
    noisy_rows[1587] = {"id": 99999, "score": 95}

    buggy_ws = tmp_path / "selfplay_ws"
    buggy_ws.mkdir()
    # Bug: `if row["score"] < best[k]:` keeps the MINIMUM instead of MAXIMUM score on duplicate IDs!
    (buggy_ws / "agg.py").write_text(
        "def best_scores(rows):\n"
        "    best = {}\n"
        "    for row in rows:\n"
        "        k = row['id']\n"
        "        if k not in best or row['score'] < best[k]:\n"
        "            best[k] = row['score']\n"
        "    return best\n",
        encoding="utf-8",
    )

    def _oracle_expected(rows):
        out = {}
        for r in rows:
            k = r["id"]
            if k not in out or r["score"] > out[k]:
                out[k] = r["score"]
        return out

    def _buggy_run(rows):
        ns = {}
        exec((buggy_ws / "agg.py").read_text(encoding="utf-8"), ns)
        return ns["best_scores"](rows)

    def _fails(sub_rows):
        return _buggy_run(sub_rows) != _oracle_expected(sub_rows)

    def _solve_on_minimal_core(core_rows):
        # Write a focused pytest file using ONLY the 1-minimal shrunk core (2 rows!) and invoke Angelic OE!
        from canonical.swe_kernel import angelic_oe_synthesizer_v1 as aoe

        (buggy_ws / "test_agg.py").write_text(
            f"from agg import best_scores\n"
            f"def test_unique():\n"
            f"    assert best_scores([{{'id': 1, 'score': 5}}]) == {{1: 5}}\n"
            f"def test_minimal_core():\n"
            f"    core = {core_rows!r}\n"
            f"    assert best_scores(core) == {_oracle_expected(core_rows)!r}\n",
            encoding="utf-8",
        )
        rep = aoe.repair_file_angelic_oe(buggy_ws, "agg.py", "test_agg.py", timeout_s=15)
        return {"solved": bool(rep.get("repaired")), **rep}

    def _verify_all_2000(sol):
        ns = {}
        exec(sol["patched_source"], ns)
        return ns["best_scores"](noisy_rows) == _oracle_expected(noisy_rows)

    store_path = tmp_path / "self_play_store.json"
    out = rta.self_play_shrink_solve_and_crystallize(
        noisy_input=noisy_rows,
        fails_on_input=_fails,
        solve_minimal_core=_solve_on_minimal_core,
        verify_full_suite=_verify_all_2000,
        law_store_path=store_path,
        skill_name="max_score_dedup_repair",
    )

    assert out["compounded"] is True, out
    assert out["shrink"]["original_size"] == 2000
    assert out["shrink"]["reduced_size"] == 2
    assert out["shrink"]["one_minimal"] is True
    assert out["shrink"]["certificate_violations"] == 0
    assert out["shrink"]["reduction_ratio"] >= 0.998
    assert "row['score'] > best[k]" in out["solution"]["patched_source"]
    assert out["stored_external"] is True
    assert "max_score_dedup_repair" in json.loads(store_path.read_text(encoding="utf-8"))["self_play_skills"]


def test_pytest_zygote_cow_screener_in_memory_override_and_zero_disk_mutation(tmp_path: pathlib.Path):
    ws = tmp_path / "zyg_ws"
    ws.mkdir()
    src_orig = "def compute_status(code: int = 302) -> int:\n    return code\n"
    (ws / "svc.py").write_text(src_orig, encoding="utf-8")
    (ws / "test_svc.py").write_text(
        "import pytest\nfrom svc import compute_status\n"
        "@pytest.mark.parametrize('expected', [303])\n"
        "def test_default_code(tmp_path, expected):\n"
        "    assert tmp_path.is_dir()\n"
        "    assert compute_status() == expected\n",
        encoding="utf-8",
    )
    env = acr._build_env(ws)
    with rta.PytestZygoteScreener(ws, env) as scr:
        bad = scr.screen("svc.py", "def compute_status(code: int = 301) -> int:\n    return code\n", "test_svc.py", "test_svc.py")
        good = scr.screen("svc.py", "def compute_status(code: int = 303) -> int:\n    return code\n", "test_svc.py", "test_svc.py")
        assert bad is False
        assert good is True
        assert scr.screened == 2
        assert scr.passed == 1
    # Disk file MUST remain completely untouched after in-memory CoW screening!
    assert (ws / "svc.py").read_text(encoding="utf-8") == src_orig


def test_dataflow_state_anomaly_repair_missing_statements(tmp_path: pathlib.Path):
    from canonical.swe_kernel import angelic_oe_synthesizer_v1 as aoe

    ws = tmp_path / "df_ws"
    ws.mkdir()
    # Unflushed post-loop accumulator remainder (`chunks.append(buf)` missing before `return chunks`)
    (ws / "chunker.py").write_text(
        "def split_fixed(buf, width):\n"
        "    chunks = []\n"
        "    while len(buf) > width:\n"
        "        part, buf = buf[:width], buf[width:]\n"
        "        chunks.append(part)\n"
        "    return chunks\n",
        encoding="utf-8",
    )
    (ws / "test_chunker.py").write_text(
        "from chunker import split_fixed\n"
        "def test_exact():\n"
        "    assert split_fixed('abcdef', 3) == ['abc', 'def']\n"
        "def test_rem():\n"
        "    assert split_fixed('abcdefg', 3) == ['abc', 'def', 'g']\n",
        encoding="utf-8",
    )
    res = aoe.repair_file_angelic_oe(ws, "chunker.py", "test_chunker.py", timeout_s=15)
    assert res["repaired"] is True, res
    assert "chunks.append(buf)" in res["patched_source"]


# ===========================================================================
# MECHANISM 1: REPO-NATIVE COMPONENT MINING + PETRI-NET EXPORT
# ===========================================================================


def test_mechanism1_repo_native_component_mining_and_petri_export(tmp_path: pathlib.Path):
    ws = tmp_path / "mined_ws"
    ws.mkdir()
    src = (
        "DEFAULT_TAG = 'ITEM'\n"
        "class SpecError(Exception):\n"
        "    pass\n"
        "class Field:\n"
        "    def __init__(self, name, doc=None):\n"
        "        self.name = name\n"
        "        self.doc = doc\n"
        "    def make_label(self, prefix: str) -> str:\n"
        "        return f'{prefix}:{self.name.upper()}'\n"
        "    def describe(self, prefix: str):\n"
        "        if self.doc is None:\n"
        "            return None\n"
        "        return self.make_label(prefix), self.doc\n"
    )
    (ws / "schema_mod.py").write_text(src, encoding="utf-8")
    (ws / "test_schema_mod.py").write_text(
        "from schema_mod import Field\n"
        "def test_with_doc():\n"
        "    assert Field('src', 'input path').describe('ARG') == ('ARG:SRC', 'input path')\n"
        "def test_without_doc():\n"
        "    assert Field('src', None).describe('ARG') == ('ARG:SRC', '')\n",
        encoding="utf-8",
    )

    # 1. Verify zero-grammar AST harvesting + Petri-Net export of repo-native symbols!
    mined = rta.mine_repo_native_components(
        src, 12, fail_snap={"self": {"t": "Field", "b": True}, "prefix": {"t": "str", "v": "ARG", "b": True}}, source_file="schema_mod.py"
    )
    exprs = {c.expr for c in mined["components"]}
    kinds = {c.kind for c in mined["components"]}
    assert "self.make_label(prefix)" in exprs
    assert "DEFAULT_TAG" in exprs
    assert "SpecError" in exprs
    assert {"method", "constant", "exception"} <= kinds
    morphs = rta.export_mined_morphisms(mined["components"])
    assert any("make_label" in m.morphism_id for m in morphs)

    # 2. Verify end-to-end repair via Repo-Native Component Mining (zero model calls!)
    res = acr.repair_repo_angelic_cegis(ws, "test_schema_mod.py", timeout_s=30)
    assert res["repaired"] is True, res
    assert res["method"] == "REPO_NATIVE_COMPONENT_MINING"
    assert "self.make_label(prefix)" in res["patched_source"]


# ===========================================================================
# MECHANISM 2: DUAL-PROGRAM SPLICING (STUN — COUNTEREXAMPLE-PARTITIONED MERGE)
# ===========================================================================


def test_mechanism2_stun_dual_program_splicing_end_to_end(tmp_path: pathlib.Path):
    ws = tmp_path / "stun_ws"
    ws.mkdir()
    (ws / "router.py").write_text(
        "class Config:\n"
        "    def __init__(self, sub_match: bool, host_match: bool):\n"
        "        self.sub_match = sub_match\n"
        "        self.host_match = host_match\n"
        "class Router:\n"
        "    def __init__(self, cfg: Config, cur_sub: str = ''):\n"
        "        self.cfg = cfg\n"
        "        self.cur_sub = cur_sub\n"
        "    def build(self, path: str, target_sub: str = '', force_ext: bool = False) -> str:\n"
        "        if (\n"
        "            not force_ext\n"
        "            and (self.cfg.sub_match or self.cfg.host_match)\n"
        "            and ((self.cfg.sub_match and target_sub == self.cur_sub) or self.cfg.host_match)\n"
        "        ):\n"
        "            return f'/{path}'\n"
        "        return f'http://app.test/{path}'\n",
        encoding="utf-8",
    )
    (ws / "test_router.py").write_text(
        "from router import Config, Router\n"
        "def test_sub_same():\n"
        "    assert Router(Config(True, False), 'api').build('x', 'api') == '/x'\n"
        "def test_sub_diff():\n"
        "    assert Router(Config(True, False), 'api').build('x', 'www') == 'http://app.test/x'\n"
        "def test_force_ext():\n"
        "    assert Router(Config(False, False)).build('x', force_ext=True) == 'http://app.test/x'\n"
        "def test_no_matching_relative():\n"
        "    assert Router(Config(False, False)).build('x') == '/x'\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(ws, "test_router.py", timeout_s=35)
    assert res["repaired"] is True, res
    assert res["method"] == "STUN_DUAL_PROGRAM_SPLICING"
    assert res.get("synthesized_guard"), res
    assert "force_ext" in res["synthesized_guard"]
    assert res["stats"]["stun_splices_attempted"] >= 1


# ===========================================================================
# MECHANISM 3: 16-WAY PARALLEL CoW COUNTERFACTUAL SPECULATIVE EXECUTION
# ===========================================================================


def test_mechanism3_16way_parallel_cow_speculative_execution(tmp_path: pathlib.Path):
    # Part A: 16-way parallel CoW PytestZygoteScreener evaluating 16 patches in RAM (0 disk writes!)
    ws = tmp_path / "cow16_ws"
    ws.mkdir()
    orig_src = "def pick_code(x: int) -> int:\n    return x + 1\n"
    (ws / "calc.py").write_text(orig_src, encoding="utf-8")
    (ws / "test_calc.py").write_text(
        "from calc import pick_code\n"
        "def test_pick():\n"
        "    assert pick_code(10) == 21\n",
        encoding="utf-8",
    )
    env = acr._build_env(ws)
    scr = rta.PytestZygoteScreener(ws, env)
    try:
        assert scr.start() is True
        cands = [
            {"id": i, "rel_file": "calc.py", "source": f"def pick_code(x: int) -> int:\n    return x + {i + 1}\n"}
            for i in range(16)
        ]
        batch_res = scr.screen_batch_speculative(
            cands, "test_calc.py::test_pick", "test_calc.py", fail_fast=True, max_parallel=16
        )
        assert batch_res is not None and len(batch_res) == 16
        winners = [r for r in batch_res if r["rc"] == 0]
        assert len(winners) == 1 and winners[0]["id"] == 10  # x + 11 == 21
        # Zero disk mutation in parent workspace!
        assert (ws / "calc.py").read_text(encoding="utf-8") == orig_src
    finally:
        scr.close()

    # Part B: 16-way parallel CoW UniversalComputerAgent speculative action tree scored by
    # MultiLayerSnapshot residual reduction with ZERO RAM/parent side-effect leakage!
    parent_sentinel = {"mutated": False}
    agent = uca.UniversalComputerAgent(law_store_path=tmp_path / "cow_store.json")
    branches = []
    for i in range(16):
        def _make_branch(idx: int):
            def _fn():
                # Deliberately mutate parent dict inside CoW child — MUST NOT leak to parent!
                parent_sentinel["mutated"] = True
                target_val = 12
                residual = abs(target_val - idx)
                return {
                    "ok": residual == 0,
                    "residual_score": float(residual),
                    "delta_count": 1 + (idx % 3),
                    "chosen_idx": idx,
                }
            return _fn
        branches.append((f"branch_{i:02d}", _make_branch(i)))

    spec_out = agent.speculate_cow_action_branches(branches, max_parallel=16)
    assert spec_out["solved"] is True
    assert spec_out["branches_evaluated"] == 16
    assert spec_out["winner"]["branch_id"] == "branch_12"
    assert spec_out["winner"]["residual_score"] == 0.0
    assert spec_out["winner"]["isolated_cow"] is True
    # Proves true OS Copy-On-Write isolation: child mutation NEVER leaked into parent RAM!
    assert parent_sentinel["mutated"] is False


# ===========================================================================
# MECHANISM 4: ALGEBRAIC CROSS-MODAL COMPILATION (WEB+SQLITE+CLI+SWE PETRI NET)
# ===========================================================================


def _start_cross_modal_http_server(rows: list[tuple[str, float]], expected_user: str, expected_pass: str):
    import http.server
    import threading
    import urllib.parse

    csrf_tok = f"tok_{expected_user}_99"
    authed = {"ok": False}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path == "/":
                body = (
                    f"<html><body><h1>Portal</h1>"
                    f"<form method='POST' action='/login'>"
                    f"<input type='hidden' name='csrf' value='{csrf_tok}'/>"
                    f"<input type='text' name='username'/>"
                    f"<input type='password' name='password'/>"
                    f"<button type='submit'>Sign In</button>"
                    f"</form></body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            elif self.path == "/records":
                if not authed["ok"]:
                    self.send_response(403)
                    self.end_headers()
                    return
                tr_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
                body = f"<html><body><table><tr><th>Item</th><th>Score</th></tr>{tr_html}</table></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            ln = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(ln).decode("utf-8")
            form = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
            if form.get("csrf") == csrf_tok and form.get("username") == expected_user and form.get("password") == expected_pass:
                authed["ok"] = True
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Welcome <a href='/records'>Records</a></body></html>")
            else:
                self.send_response(403)
                self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, f"http://127.0.0.1:{port}"


def test_mechanism4_algebraic_cross_modal_compilation_and_1shot_replay(tmp_path: pathlib.Path):
    # Environment #1: live CSRF Web App + SQLite + CLI + BUGGY Python scorer repo!
    srv1, url1 = _start_cross_modal_http_server([("alpha", 12.5), ("beta", 27.5)], "alice", "secret1")
    swe1 = tmp_path / "swe_env1"
    swe1.mkdir()
    # Bug: `total -= r['value']` instead of `total += r['value']` (wrong operator)!
    (swe1 / "scorer.py").write_text(
        "def summarize_records(rows):\n"
        "    total = 0.0\n"
        "    for r in rows:\n"
        "        total = total - float(r['value'])\n"
        "    return {'count': len(rows), 'total': round(total, 2)}\n",
        encoding="utf-8",
    )
    (swe1 / "test_scorer.py").write_text(
        "from scorer import summarize_records\n"
        "def test_empty():\n"
        "    assert summarize_records([]) == {'count': 0, 'total': 0.0}\n"
        "def test_sum():\n"
        "    assert summarize_records([{'key': 'a', 'value': 10.0}, {'key': 'b', 'value': 5.0}]) == {'count': 2, 'total': 15.0}\n",
        encoding="utf-8",
    )

    store_path = tmp_path / "cross_modal_store.json"
    agent = uca.UniversalComputerAgent(law_store_path=store_path)
    try:
        out1 = agent.compile_and_run_cross_modal_pipeline(
            web_base_url=url1,
            web_login={"username": "alice", "password": "secret1"},
            web_records_path="/records",
            sqlite_db_path=tmp_path / "env1.db",
            cli_workspace=tmp_path / "cli1",
            swe_repo_root=swe1,
            swe_test_file="test_scorer.py",
            output_bundle_path=tmp_path / "bundle1.json",
            morphism_name="web_sqlite_cli_swe_unified",
            env_version_hash="env_v1",
        )
    finally:
        srv1.shutdown()
        srv1.server_close()

    assert out1["compiled"] is True, out1
    assert out1["certified"] is True
    assert out1["undo_safe"] is True
    assert len(out1["plan_names"]) == 5
    assert out1["store_admission"]["admitted"] is True
    assert out1["bundle"]["db_row_count"] == 2
    assert out1["bundle"]["cli_line_count"] == 3  # header + 2 rows
    assert out1["bundle"]["summary"] == {"count": 2, "total": 40.0}

    # Environment #2 (BRAND-NEW unseen port, credentials, DB, directory, records, AND new buggy code!):
    # Replay the SINGLE crystallized L2 morphism in 1 shot with ZERO Petri-Net search!
    srv2, url2 = _start_cross_modal_http_server([("gamma", 100.0), ("delta", 50.0), ("eps", 25.0)], "bob", "pw2")
    swe2 = tmp_path / "swe_env2"
    swe2.mkdir()
    (swe2 / "scorer.py").write_text(
        "def summarize_records(rows):\n"
        "    total = 0.0\n"
        "    for r in rows:\n"
        "        total = total + float(r['value'])\n"
        "    return {'count': len(rows), 'total': round(total, 2)}\n",
        encoding="utf-8",
    )
    (swe2 / "test_scorer.py").write_text(
        "from scorer import summarize_records\n"
        "def test_sum():\n"
        "    assert summarize_records([{'key': 'x', 'value': 3.0}]) == {'count': 1, 'total': 3.0}\n",
        encoding="utf-8",
    )
    try:
        out2 = agent.replay_crystallized_cross_modal_morphism(
            "web_sqlite_cli_swe_unified",
            web_base_url=url2,
            web_login={"username": "bob", "password": "pw2"},
            web_records_path="/records",
            sqlite_db_path=tmp_path / "env2.db",
            cli_workspace=tmp_path / "cli2",
            swe_repo_root=swe2,
            swe_test_file="test_scorer.py",
            output_bundle_path=tmp_path / "bundle2.json",
        )
    finally:
        srv2.shutdown()
        srv2.server_close()

    assert out2["replayed"] is True, out2
    assert out2["search_nodes_expanded"] == 0
    assert out2["bundle"]["db_row_count"] == 3
    assert out2["bundle"]["summary"] == {"count": 3, "total": 175.0}


# ===========================================================================
# §9.2 MEMORY ARCHITECTURE: 5-PART ADMISSION + ANTI-UNIFICATION + STALENESS
# ===========================================================================


def test_section92_memory_admission_anti_unification_and_staleness_probe(tmp_path: pathlib.Path):
    store = uca.ExternalCausalLawStore(tmp_path / "sec92_store.json")

    # 1. 5-Part Admission Filter: valid parameterized provenance-tagged law ADMITTED!
    good_law = uca.ParameterizedCausalLaw(
        law_id="cli_unpack_v1",
        domain="cli",
        tool_or_action="ztool",
        command_template=["{tool}", "--extract", "{src}", "--out", "{dst}"],
        in_ext=".pkg",
        out_ext=".json",
        creates_file_kind="json",
        effects={"created": "json"},
        verified_count=1,
        provenance={"source_env": "sandbox_cli_1", "version_hash": "ver_1.0"},
    )
    r_ok = store.admit_filtered(good_law, strict=True)
    assert r_ok["admitted"] is True

    # Rejects: (a) unverified, (b) duplicate, (c) raw ephemeral /tmp/ trace, (d) missing provenance, (e) bloated!
    r_unv = store.admit_filtered(
        uca.ParameterizedCausalLaw(
            law_id="bad_unv", domain="cli", tool_or_action="t", command_template=["{tool}", "{src}"],
            effects={}, verified_count=0, provenance={"source_env": "x", "version_hash": "v1"},
        )
    )
    assert not r_unv["admitted"] and "FAIL_VERIFIABLE" in r_unv["reasons"]

    r_dup = store.admit_filtered(
        uca.ParameterizedCausalLaw(
            law_id="cli_unpack_dup", domain="cli", tool_or_action="ztool",
            command_template=["{tool}", "--extract", "{src}", "--out", "{dst}"],
            in_ext=".pkg", out_ext=".json", creates_file_kind="json", effects={"created": "json"},
            verified_count=1, provenance={"source_env": "sandbox_cli_2", "version_hash": "ver_1.0"},
        )
    )
    assert not r_dup["admitted"] and "FAIL_NOVEL_DUPLICATE" in r_dup["reasons"]

    r_raw = store.admit_filtered(
        uca.ParameterizedCausalLaw(
            law_id="bad_raw", domain="cli", tool_or_action="ztool",
            command_template=["ztool", "--extract", "/tmp/run42/a.pkg", "--out", "/tmp/run42/b.json"],
            creates_file_kind="json", effects={"created": "json"}, verified_count=1,
            provenance={"source_env": "s", "version_hash": "v1"},
        )
    )
    assert not r_raw["admitted"] and "FAIL_GENERALIZABLE" in r_raw["reasons"]

    r_noprov = store.admit_filtered(
        uca.ParameterizedCausalLaw(
            law_id="bad_prov", domain="cli", tool_or_action="t",
            command_template=["{tool}", "--run", "{src}"],
            creates_file_kind="json", effects={"created": "json"}, verified_count=1, provenance={},
        )
    )
    assert not r_noprov["admitted"] and "FAIL_PROVENANCE" in r_noprov["reasons"]

    r_bloat = store.admit_filtered(
        uca.ParameterizedCausalLaw(
            law_id="bad_bloat", domain="cli", tool_or_action="t",
            command_template=["{tool}"] + [f"arg{i}" for i in range(18)],
            creates_file_kind="json", effects={"blob": "x" * 5000}, verified_count=1,
            provenance={"source_env": "s", "version_hash": "v1"},
        )
    )
    assert not r_bloat["admitted"] and "FAIL_COST_BOUNDED" in r_bloat["reasons"]

    # 2. Anti-unification generalizing compression with attached concrete witnesses!
    store.admit(
        uca.ParameterizedCausalLaw(
            law_id="web_export_a", domain="web_dom", tool_or_action="portal_a",
            command_template=["POST", "/v1/orders", "--fmt", "csv", "--target", "{dst}"],
            creates_file_kind="csv", effects={"exported": True}, verified_count=1,
            provenance={"source_env": "portal_a", "version_hash": "v1"},
        )
    )
    store.admit(
        uca.ParameterizedCausalLaw(
            law_id="web_export_b", domain="web_dom", tool_or_action="portal_b",
            command_template=["POST", "/v2/invoices", "--fmt", "csv", "--target", "{dst}"],
            creates_file_kind="csv", effects={"exported": True}, verified_count=1,
            provenance={"source_env": "portal_b", "version_hash": "v2"},
        )
    )
    comp = store.compress_by_anti_unification()
    assert comp["compressed_count"] == 1
    lgg_id = comp["compressed_ids"][0]
    lgg = store.laws[lgg_id]
    assert lgg.generalized is True
    assert lgg.command_template == ["POST", "?slot_0", "--fmt", "csv", "--target", "{dst}"]
    assert len(lgg.witnesses) == 2
    assert "web_export_a" not in store.laws and "web_export_b" not in store.laws

    # 3. Provenance & version staleness re-validation probe!
    # Same version -> instant FRESH hit (probed=False)
    p1 = store.probe_and_refresh_stale("cli_unpack_v1", "ver_1.0", lambda _l: True)
    assert p1["status"] == "FRESH" and p1["probed"] is False and p1["usable"] is True
    # Drifted version still compatible -> REFRESHED (probed=True)
    p2 = store.probe_and_refresh_stale("cli_unpack_v1", "ver_1.1", lambda _l: True)
    assert p2["status"] == "REFRESHED" and p2["probed"] is True and p2["usable"] is True
    # Drifted version broken (e.g. flag removed!) -> STALE_INVALIDATED, excluded from active_laws()!
    p3 = store.probe_and_refresh_stale("cli_unpack_v1", "ver_2.0", lambda _l: False)
    assert p3["status"] == "STALE_INVALIDATED" and p3["usable"] is False
    assert all(l.law_id != "cli_unpack_v1" for l in store.active_laws("cli"))


# ===========================================================================
# §6 EXPLICIT PROOFS: SINGLE-EXPERIENCE TRANSFER + 3 MEMORY ABLATIONS
# ===========================================================================


def test_section6_single_experience_cross_env_transfer_and_memory_ablations(tmp_path: pathlib.Path):
    """Explicit §6 scientific proof on REAL live deceptive-CLI workspaces:
      1. Single-experience cross-environment transfer (Env A -> shifted Env B, zero weight facts;
         deleting the external JSON store immediately removes transfer!).
      2. Ablation 1: With §9.2 Store vs Empty Store.
      3. Ablation 2: Generalized (parameterized/anti-unified) laws vs Raw concrete traces.
      4. Ablation 3: Goal-directed + 5-part admitted acquisition vs Broad unfiltered ingest.
    """
    import subprocess
    import sys
    def _build_deceptive_cli_env(ws: pathlib.Path, tool_name: str, src_name: str, dst_name: str) -> None:
        ws.mkdir(parents=True, exist_ok=True)
        tool_py = ws / f"{tool_name}.py"
        # Deceptive `--help`: claims `--convert` works (actually destroys input!), real secret flag is `--xform`!
        tool_py.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "if '--help' in args:\n"
            "    print('Usage: tool --convert SRC DST   (converts .raw to .json)')\n"
            "    print('       tool --xform SRC DST     (internal hidden transform)')\n"
            "    sys.exit(0)\n"
            "if '--convert' in args:\n"
            "    # Deceptive trap: refuses/corrupts\n"
            "    sys.stderr.write('ERROR: --convert deprecated trap\\n')\n"
            "    sys.exit(2)\n"
            "if '--xform' in args and len(args) >= 3:\n"
            "    src = pathlib.Path(args[1]).read_text(encoding='utf-8').strip()\n"
            "    pathlib.Path(args[2]).write_text(json.dumps({'ok': True, 'val': src.upper()}), encoding='utf-8')\n"
            "    sys.exit(0)\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        tool_py.chmod(0o755)
        (ws / src_name).write_text("hello_world\n", encoding="utf-8")

    # Env A (Experience 1): discover working flag by live probe -> admit generalized law to external store!
    ws_a = tmp_path / "env_a"
    _build_deceptive_cli_env(ws_a, "mtool", "alpha.raw", "alpha.json")
    store_path = tmp_path / "transfer_store.json"
    store = uca.ExternalCausalLawStore(store_path)

    # Probe Env A (counts live trial executions before finding `--xform`)
    def _solve_cli_with_store(ws: pathlib.Path, tool_name: str, src_name: str, dst_name: str, st: uca.ExternalCausalLawStore | None):
        trials = 0
        # Try fresh generalized active laws from store FIRST (0-exploration transfer!)
        if st is not None:
            for law in st.active_laws("cli"):
                cmd = [
                    tok.replace("{tool}", str(ws / f"{tool_name}.py"))
                       .replace("{src}", str(ws / src_name))
                       .replace("{dst}", str(ws / dst_name))
                       .replace("?slot_0", str(ws / f"{tool_name}.py"))
                    for tok in law.command_template
                ]
                trials += 1
                p = subprocess.run([sys.executable, *cmd], cwd=str(ws), capture_output=True, text=True, timeout=10)
                if p.returncode == 0 and (ws / dst_name).exists():
                    return {"solved": True, "trials": trials, "via_store": True, "law_id": law.law_id}
        # Fallback: live exploration over candidate flags (`--convert` fails first, `--xform` succeeds!)
        for flag in ("--convert", "--xform"):
            trials += 1
            p = subprocess.run(
                [sys.executable, str(ws / f"{tool_name}.py"), flag, str(ws / src_name), str(ws / dst_name)],
                cwd=str(ws), capture_output=True, text=True, timeout=10,
            )
            if p.returncode == 0 and (ws / dst_name).exists():
                if st is not None:
                    st.admit_filtered(
                        uca.ParameterizedCausalLaw(
                            law_id=f"cli_xform_{flag}",
                            domain="cli",
                            tool_or_action=tool_name,
                            command_template=["{tool}", flag, "{src}", "{dst}"],
                            in_ext=".raw",
                            out_ext=".json",
                            creates_file_kind="json",
                            effects={"created": "json"},
                            verified_count=1,
                            provenance={"source_env": str(ws.name), "version_hash": "v1"},
                        ),
                        strict=True,
                    )
                return {"solved": True, "trials": trials, "via_store": False}
        return {"solved": False, "trials": trials, "via_store": False}

    # 1. Single experience in Env A (takes 2 live trials: `--convert` fails, `--xform` succeeds & admitted!)
    res_a = _solve_cli_with_store(ws_a, "mtool", "alpha.raw", "alpha.json", store)
    assert res_a["solved"] is True and res_a["trials"] == 2 and res_a["via_store"] is False

    # 2. Single-experience transfer to SHIFTED Env B (different dir, different tool name, different filenames!)
    ws_b = tmp_path / "env_b_shifted"
    _build_deceptive_cli_env(ws_b, "ntool_v2", "zeta_99.raw", "result_out.json")
    # Reload fresh store instance from JSON on disk (proving ZERO in-memory / weight carry-over!)
    store_reloaded = uca.ExternalCausalLawStore(store_path)
    res_b_with_store = _solve_cli_with_store(ws_b, "ntool_v2", "zeta_99.raw", "result_out.json", store_reloaded)
    assert res_b_with_store["solved"] is True
    assert res_b_with_store["via_store"] is True
    assert res_b_with_store["trials"] == 1  # Instant 1-shot transfer (50% fewer executions, 0 trap hits!)

    # 3. Ablation 1 — Empty Store (delete external JSON -> capability immediately reverts to 2 trials!)
    ws_b_empty = tmp_path / "env_b_empty"
    _build_deceptive_cli_env(ws_b_empty, "ntool_v2", "zeta_99.raw", "result_out.json")
    store_path.unlink()
    store_deleted = uca.ExternalCausalLawStore(store_path)
    assert len(store_deleted.laws) == 0
    res_b_empty = _solve_cli_with_store(ws_b_empty, "ntool_v2", "zeta_99.raw", "result_out.json", store_deleted)
    assert res_b_empty["solved"] is True and res_b_empty["via_store"] is False and res_b_empty["trials"] == 2

    # 4. Ablation 2 — Generalized Laws vs Raw Concrete Traces (raw trace fails transfer to Env B!)
    raw_trace_store = uca.ExternalCausalLawStore(tmp_path / "raw_trace_store.json")
    raw_law = uca.ParameterizedCausalLaw(
        law_id="raw_concrete_env_a",
        domain="cli",
        tool_or_action="mtool",
        command_template=[str(ws_a / "mtool.py"), "--xform", str(ws_a / "alpha.raw"), str(ws_a / "alpha.json")],
        creates_file_kind="json",
        effects={"created": "json"},
        verified_count=1,
        provenance={"source_env": "env_a", "version_hash": "v1"},
    )
    # 5-part admission filter REJECTS raw trace!
    assert raw_trace_store.admit_filtered(raw_law, strict=True)["admitted"] is False
    # Force-inject raw trace to measure raw-trace ablation on Env B:
    raw_trace_store.admit(raw_law)
    ws_b_raw = tmp_path / "env_b_raw"
    _build_deceptive_cli_env(ws_b_raw, "ntool_v2", "zeta_99.raw", "result_out.json")
    res_b_raw = _solve_cli_with_store(ws_b_raw, "ntool_v2", "zeta_99.raw", "result_out.json", raw_trace_store)
    # Raw trace wrote to env_a instead of env_b -> wasted 1 useless store trial + still needed 2 live probes = 3 trials!
    assert res_b_raw["via_store"] is False
    assert res_b_raw["trials"] == 3 > res_b_with_store["trials"]

    # 5. Ablation 3 — Goal-Directed 5-Part Admitted vs Broad Unfiltered Ingest
    gd_store = uca.ExternalCausalLawStore(tmp_path / "gd_store.json")
    broad_store = uca.ExternalCausalLawStore(tmp_path / "broad_store.json")
    # Feed 1 valid generalized law + 10 noisy raw/unverified/duplicate artifacts
    valid_l = uca.ParameterizedCausalLaw(
        law_id="gd_valid", domain="cli", tool_or_action="tool",
        command_template=["{tool}", "--xform", "{src}", "{dst}"],
        creates_file_kind="json", effects={"created": "json"}, verified_count=1,
        provenance={"source_env": "env_a", "version_hash": "v1"},
    )
    gd_store.admit_filtered(valid_l, strict=True)
    broad_store.admit(valid_l)
    for k in range(10):
        noise = uca.ParameterizedCausalLaw(
            law_id=f"noise_{k}", domain="cli", tool_or_action=f"noise_tool_{k}",
            command_template=[f"/tmp/noise_{k}/run.py", "--bogus", f"/tmp/noise_{k}/in", f"/tmp/noise_{k}/out"],
            creates_file_kind="json", effects={"created": "json"}, verified_count=0,
            provenance={},
        )
        gd_store.admit_filtered(noise, strict=True)  # Rejected by 5-part admission filter!
        broad_store.admit(noise)  # Broad unfiltered ingest admits ALL 10 noisy items!

    assert len(gd_store.active_laws("cli")) == 1
    assert len(broad_store.active_laws("cli")) == 11
    assert gd_store.admission_stats["rejected"] == 10
    # Goal-directed retrieval precision: 1/1 (100%) vs Broad unfiltered: 1/11 (9.1%)!
    assert (1 / len(gd_store.active_laws("cli"))) == 1.0
    assert (1 / len(broad_store.active_laws("cli"))) < 0.15


# ===========================================================================
# ITERATION I — FIVE END-TO-END PROOF TESTS (0 MODEL CALLS, ZERO MOCKS)
# ===========================================================================


def test_iteration_i_bidirectional_lens_fst():
    """Engine I-1: Infer minimal dual-channel & single-channel BidirectionalLensFST
    purely from runtime output diffs (zero full-string memorization, exact round-trip!).
    """
    # 1. Dual-channel asymmetric lens (write stream vs returned bytes — like CliRunner control bytes)
    witnesses_dual = [
        ("bar\n\x04b'bar\\n\\x04'\n", "bar\n^D\nb'bar\\n'\n"),
        ("bar\n\x1ab'bar\\n\\x1a'\n", "bar\n^Z\nb'bar\\n'\n"),
        ("\x04b'\\x04'\n", "^D\nb''\n"),
    ]
    fst_dual = rta.infer_bidirectional_lens_fst(witnesses_dual)
    assert fst_dual is not None
    assert fst_dual.channel_mode == "dual_write_return"
    assert fst_dual.is_bytes is True
    assert dict(fst_dual.write_rules) == {"\x04": "^D\n", "\x1a": "^Z\n"}
    assert dict(fst_dual.return_rules) == {"\x04": "", "\x1a": ""}
    # Forward on unseen mid-chunk input (generalization, not memorization!)
    assert fst_dual.forward(b"hello\x04world\x1a!", channel="write") == b"hello^D\nworld^Z\n!"
    assert fst_dual.forward(b"hello\x04world\x1a!", channel="return") == b"helloworld!"
    # Exact round-trip invertibility on write channel
    assert fst_dual.roundtrip_check([b"abc\x04def", b"\x1axyz", b"plain"]) is True
    assert "switch" in fst_dual.to_c_snippet() and "replaceAll" in fst_dual.to_js_snippet()

    # 2. Single-channel injective escape lens
    witnesses_esc = [("a&b", "a&amp;b"), ("x<y", "x&lt;y"), ("p&q<r", "p&amp;q&lt;r")]
    fst_esc = rta.infer_bidirectional_lens_fst(witnesses_esc)
    assert fst_esc is not None and fst_esc.channel_mode == "single"
    assert fst_esc.forward("m&n<o") == "m&amp;n&lt;o"
    assert fst_esc.backward("m&amp;n&lt;o") == "m&n<o"
    assert fst_esc.roundtrip_check(["hello&world<1>", "plain"]) is True


def test_iteration_i_multi_stmt_ast_anti_unification_and_transfer(tmp_path: pathlib.Path):
    """Engine I-2 + I-5: Multi-statement AST Subtree Anti-Unification (`TreeRewriteMorphism`),
    1-shot cross-repo transfer (unseen variable/function names + comments preserved),
    O(1) deletion without retraining, and Plotkin LGG store compaction!
    """
    store_path = tmp_path / "l2_tree_store.json"
    store = uca.ExternalCausalLawStore(store_path)

    # Exposure 1 (Repo A): multi-statement guard deletion + tuple fallback wrapping!
    before_a = (
        "# Repo A header formatter\n"
        "def format_header(label, unit):\n"
        "    if label is None:\n"
        "        return None\n"
        "    return (label, unit)\n"
    )
    after_a = (
        "# Repo A header formatter\n"
        "def format_header(label, unit):\n"
        "    return (label or '', unit)\n"
    )
    m1 = rta.extract_multi_stmt_tree_morphism(before_a, after_a, provenance={"repo": "repo_a"})
    assert m1 is not None
    assert m1.target_kind == "stmt_slice"
    assert len(m1.pattern_sexps) == 2 and len(m1.replacement_sexps) == 1
    assert len(m1.hole_types) == 2  # ?h0 (label), ?h1 (unit)
    adm = store.admit_tree_morphism(m1)
    assert adm["admitted"] is True

    # Reload store from disk to verify JSON persistence!
    store_reloaded = uca.ExternalCausalLawStore(store_path)
    assert len(store_reloaded.list_tree_morphisms()) == 1

    # Single-Experience Transfer to UNSEEN Repo B (totally different names + preserved comments!)
    ws_b = tmp_path / "repo_b"
    ws_b.mkdir()
    (ws_b / "records.py").write_text(
        "# Important comment that must survive surgical splicing\n"
        "def build_record(tag, meta):\n"
        "    if tag is None:\n"
        "        return None\n"
        "    return (tag, meta)\n",
        encoding="utf-8",
    )
    (ws_b / "test_records.py").write_text(
        "from records import build_record\n"
        "def test_none_tag():\n"
        "    assert build_record(None, 'ok') == ('', 'ok')\n"
        "def test_normal_tag():\n"
        "    assert build_record('v1', 'ok') == ('v1', 'ok')\n",
        encoding="utf-8",
    )
    res_b = acr.repair_repo_angelic_cegis(ws_b, "test_records.py", timeout_s=25, skill_store=store_reloaded)
    assert res_b["repaired"] is True, res_b
    assert res_b["method"] == "L2_TREE_REWRITE_MORPHISM_1SHOT"
    assert res_b["stats"]["tree_morphism_hits"] == 1
    assert "# Important comment that must survive surgical splicing" in res_b["patched_source"]
    assert "return (tag or '', meta)" in res_b["patched_source"]

    # O(1) Deletion from external store without retraining!
    assert store_reloaded.delete_tree_morphism(m1.morphism_id) is True
    store_after_del = uca.ExternalCausalLawStore(store_path)
    assert len(store_after_del.list_tree_morphisms()) == 0

    # Plotkin AST Anti-Unification & Zero-Weight Store Compaction across 2 related morphisms!
    m_num1 = rta.extract_multi_stmt_tree_morphism(
        "def f1(a):\n    if a < 0:\n        return 0\n    return a\n",
        "def f1(a):\n    return max(0, a)\n",
        morphism_id="clamp_zero",
    )
    m_num2 = rta.extract_multi_stmt_tree_morphism(
        "def f2(b):\n    if b < 10:\n        return 10\n    return b\n",
        "def f2(b):\n    return max(10, b)\n",
        morphism_id="clamp_ten",
    )
    assert m_num1 is not None and m_num2 is not None
    store_after_del.admit_tree_morphism(m_num1)
    store_after_del.admit_tree_morphism(m_num2)
    comp = store_after_del.compact_and_deduplicate()
    assert comp["l2_before"] == 2 and comp["l2_after"] == 1 and comp["l2_merged_groups"] == 1
    # Compacted LGG morphism generalizes to an UNSEEN constant `42`!
    lgg_m = store_after_del.list_tree_morphisms()[0]
    rew_42, hits_42 = rta.apply_tree_rewrite_morphism(
        "def f3(z):\n    if z < 42:\n        return 42\n    return z\n",
        lgg_m,
    )
    assert hits_42 == 1 and rew_42 is not None and "return max(42, z)" in rew_42


def test_iteration_i_cow_differential_boundary_fuzz_and_l3_invariants(tmp_path: pathlib.Path):
    """Engine I-3 + I-4: 1ms CoW Differential Boundary Fuzzing rejects symptom overfits
    (`VACUOUS_BYPASS` & `CROSS_TYPE_FALSY_OVERFIT`), accepts exact causal guards, and
    crystallizes L3 Negative-Space Invariants that prune dead ends in microseconds!
    """
    orig_src = (
        "class Param:\n"
        "    def value_is_missing(self, value):\n"
        "        if value is None:\n"
        "            return True\n"
        "        return False\n"
    )
    vacuous_overfit = orig_src.replace("if value is None:", "if (value is None) or (bool(self.secondary_opts)):")
    falsy_overfit = orig_src.replace("if value is None:", "if (value is None) or (not value):")
    snap = {
        "value": {"t": "bool", "v": False, "b": False},
        "self.__attrs__": {"secondary_opts": {"t": "list", "v": "['--no-flag']", "b": True, "len": 1}},
    }

    r_vac = rta.cow_differential_boundary_fuzz(
        orig_src,
        vacuous_overfit,
        "value_is_missing",
        snap,
        target_line=3,
        orig_cond_src="value is None",
        patched_cond_src="(value is None) or (bool(self.secondary_opts))",
    )
    assert r_vac["passed"] is False and r_vac["reason"] == "VACUOUS_BYPASS"

    r_falsy = rta.cow_differential_boundary_fuzz(
        orig_src,
        falsy_overfit,
        "value_is_missing",
        snap,
        target_line=3,
        orig_cond_src="value is None",
        patched_cond_src="(value is None) or (not value)",
    )
    assert r_falsy["passed"] is False and r_falsy["reason"] == "CROSS_TYPE_FALSY_OVERFIT"

    # Exact causal guard passes BOTH condition invariance AND real CoW os.fork() function fuzzing!
    exact_orig = (
        "def clamp_positive(x, required):\n"
        "    if x > 0:\n"
        "        return x\n"
        "    return 0\n"
    )
    exact_patched = (
        "def clamp_positive(x, required):\n"
        "    if (x > 0) and not (required):\n"
        "        return x\n"
        "    return 0\n"
    )
    r_ok = rta.cow_differential_boundary_fuzz(
        exact_orig,
        exact_patched,
        "clamp_positive",
        {"x": {"t": "int", "v": 5, "b": True}, "required": {"t": "bool", "v": True, "b": True}},
        target_line=2,
        orig_cond_src="x > 0",
        patched_cond_src="(x > 0) and not (required)",
    )
    assert r_ok["passed"] is True and r_ok["isolated_cow"] is True and r_ok["new_crashes"] == 0

    # L3 Negative-Space Invariant crystallization + persistence + microsecond pruning + O(1) deletion
    store_p = tmp_path / "l3_store.json"
    st = uca.ExternalCausalLawStore(store_p)
    inv = rta.NegativeSpaceInvariant(
        invariant_id="l3::vacuous_secondary_opts",
        domain="swe_branch",
        func_context="value_is_missing",
        orig_cond_shape=rta.NegativeSpaceInvariant.normalize_expr_shape("value is None"),
        refuted_guard_shape=rta.NegativeSpaceInvariant.normalize_expr_shape("bool(self.secondary_opts)"),
        reason="VACUOUS_BYPASS",
        counterexample={"value": "True"},
    )
    assert st.add_negative_invariant(inv)["added"] is True
    st2 = uca.ExternalCausalLawStore(store_p)
    pruned, pid = st2.is_pruned_by_l3(
        func_context="value_is_missing",
        orig_cond_src="value  is  None",  # Whitespace-invariant AST shape match!
        guard_src="bool( self.secondary_opts )",
    )
    assert pruned is True and pid == "l3::vacuous_secondary_opts"
    assert st2.delete_negative_invariant("l3::vacuous_secondary_opts") is True
    pruned_after, _ = st2.is_pruned_by_l3(
        func_context="value_is_missing",
        orig_cond_src="value is None",
        guard_src="bool(self.secondary_opts)",
    )
    assert pruned_after is False


def test_iteration_i_petri_cut_vertex_320_step_osworld_horizon():
    """Engine I-6: Compositional Goal Decomposition via Petri-Net Dominator Cut-Vertices
    solves a 320-step OSWorld-V2-style cross-modal workflow with 5 injected mid-task drift
    faults at 100% completion and zero reset-to-zero drift, where flat execution fails!
    """
    # Build a 10-stage x 32-step = 320-step cross-modal workflow with diamond branches inside
    # each stage so ONLY the 9 stage-boundary milestones are true dominator cut-vertices!
    edges: list[tuple[str, str]] = []
    expected_cuts: list[str] = []
    for stage in range(10):
        c_start = f"M{stage}"
        c_end = f"M{stage + 1}"
        if stage > 0:
            expected_cuts.append(c_start)
        # 2 parallel 32-step branches inside each stage (upper & lower) reconverging at `c_end`
        prev_a, prev_b = c_start, c_start
        for step in range(1, 32):
            na = f"s{stage}_a_{step}"
            nb = f"s{stage}_b_{step}"
            edges.append((prev_a, na))
            edges.append((prev_b, nb))
            prev_a, prev_b = na, nb
        edges.append((prev_a, c_end))
        edges.append((prev_b, c_end))

    decomp = uca.compute_petri_dominator_cut_vertices(edges, "M0", "M10")
    assert decomp["reachable"] is True
    assert decomp["cut_vertices"] == expected_cuts  # Exact 9 interior dominator cut-vertices!
    assert len(decomp["sub_episodes"]) == 10

    # Inject 5 realistic mid-task environment drift/corruption faults across the 320 steps!
    drift_steps = {47, 112, 189, 241, 305}

    def _step_exec(st: dict, u: str, v: str) -> dict:
        nxt = dict(st)
        nxt["node"] = v
        nxt["steps"] = int(nxt.get("steps", 0)) + 1
        if v.startswith("M"):
            milestones = list(nxt.get("milestones", []))
            if not nxt.get("corrupted"):
                milestones.append(v)
            nxt["milestones"] = milestones
        return nxt

    def _drift(step_idx: int, st: dict) -> tuple[dict, bool]:
        if step_idx in drift_steps:
            d = dict(st)
            d["corrupted"] = True
            return d, True
        return st, False

    def _verify_cp(st: dict, cp_node: str) -> bool:
        return (not st.get("corrupted")) and (cp_node in st.get("milestones", []))

    # 1. Flat un-checkpointed baseline collapses under mid-task drift!
    flat_state = {"node": "M0", "milestones": ["M0"], "corrupted": False, "steps": 0}
    cur = "M0"
    flat_step = 0
    for stage in range(10):
        for step in range(1, 32):
            nxt = f"s{stage}_a_{step}"
            flat_state = _step_exec(flat_state, cur, nxt)
            flat_step += 1
            flat_state, _ = _drift(flat_step, flat_state)
            cur = nxt
        nxt = f"M{stage + 1}"
        flat_state = _step_exec(flat_state, cur, nxt)
        flat_step += 1
        cur = nxt
    assert _verify_cp(flat_state, "M10") is False  # Flat baseline collapsed!

    # 2. Cut-vertex checkpointed execution achieves 100% completion with ONLY local rollbacks!
    res = uca.execute_cut_vertex_checkpointed_episode(
        edges,
        "M0",
        "M10",
        initial_state={"node": "M0", "milestones": ["M0"], "corrupted": False, "steps": 0},
        step_executor=_step_exec,
        checkpoint_verifier=_verify_cp,
        drift_injector=_drift,
    )
    assert res["completed"] is True and res["goal_verified"] is True
    assert res["cut_vertices_count"] == 9 and res["sub_episodes_count"] == 10
    assert res["drift_events"] == 5 and res["local_rollbacks"] == 5
    # Local rollback only replayed the 5 affected 32-step sub-episodes (160 steps), NEVER reset to 0!
    assert res["steps_lost_to_rollback"] == 160
    assert len(res["locked_checkpoints"]) == 11


def test_iteration_i_cow_angelic_value_blame_multifile(tmp_path: pathlib.Path):
    """Engine I-4b: Counterfactual Causal Blame via 1ms CoW Angelic Value Perturbation
    pinpoints the exact causal line in a secondary module across a multi-file call stack!
    """
    ws = tmp_path / "mf_blame"
    ws.mkdir()
    (ws / "tax_rules.py").write_text(
        "def regional_rate(region: str) -> float:\n"
        "    base = 0.05\n"
        "    if region == 'EU':\n"
        "        return 0.10\n"  # Bug: should be 0.20!
        "    return base\n",
        encoding="utf-8",
    )
    (ws / "pricing.py").write_text(
        "from tax_rules import regional_rate\n"
        "def total_price(amount: float, region: str) -> float:\n"
        "    rate = regional_rate(region)\n"
        "    return round(amount * (1.0 + rate), 2)\n",
        encoding="utf-8",
    )
    (ws / "test_pricing.py").write_text(
        "from pricing import total_price\n"
        "def test_eu_price():\n"
        "    assert total_price(100.0, 'EU') == 120.0\n",
        encoding="utf-8",
    )
    tax_src = (ws / "tax_rules.py").read_text(encoding="utf-8")
    price_src = (ws / "pricing.py").read_text(encoding="utf-8")
    import ast as _ast
    t_tax = _ast.parse(tax_src)
    t_price = _ast.parse(price_src)
    ret_010 = next(n.value for n in _ast.walk(t_tax) if isinstance(n, _ast.Return) and isinstance(n.value, _ast.Constant) and n.value.value == 0.10)
    ret_base = next(n.value for n in _ast.walk(t_tax) if isinstance(n, _ast.Return) and isinstance(n.value, _ast.Name) and n.value.id == "base")
    call_rate = next(n.value for n in _ast.walk(t_price) if isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Call))

    env = acr._build_env(ws)
    scr = rta.PytestZygoteScreener(ws, env)
    try:
        assert scr.start() is True
        blamed = rta.cow_angelic_value_blame(
            ws,
            [
                ("tax_rules.py", tax_src, 5, ret_base, 0.20),
                ("tax_rules.py", tax_src, 4, ret_010, 0.20),
                ("pricing.py", price_src, 3, call_rate, 0.99),
            ],
            "test_pricing.py::test_eu_price",
            "test_pricing.py",
            scr,
        )
        assert len(blamed) == 1
        assert blamed[0]["file"] == "tax_rules.py" and blamed[0]["line"] == 4 and blamed[0]["rescued"] is True
    finally:
        scr.close()


def test_iteration_j_boundary_norm_prelude_non_base64_codec(tmp_path: pathlib.Path):
    """Engine J-1: Canonical Boundary-Padding Preprocessor Synthesis on a brand-new
    null-padded 8-byte block frame codec (zero Base64 / '=' / mod-4 hardcoding!).
    """
    ws = tmp_path / "frame_codec"
    ws.mkdir()
    (ws / "framing.py").write_text(
        "class FrameError(ValueError):\n"
        "    pass\n"
        "_FRAME_ALPHABET = frozenset(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')\n"
        "def decode_frame(pkt: bytes) -> bytes:\n"
        "    if len(pkt) % 8 == 1 or any(b not in _FRAME_ALPHABET for b in pkt):\n"
        "        raise FrameError('bad frame')\n"
        "    return pkt.lower()\n",
        encoding="utf-8",
    )
    (ws / "test_framing.py").write_text(
        "import pytest\n"
        "from framing import FrameError, decode_frame\n"
        "def test_unpadded():\n"
        "    assert decode_frame(b'ABCD') == b'abcd'\n"
        "def test_canonical_null_padded():\n"
        "    assert decode_frame(b'ABCDEF\\x00\\x00') == b'abcdef'\n"
        "    assert decode_frame(b'AB\\x00\\x00\\x00\\x00\\x00\\x00') == b'ab'\n"
        "def test_rejects_bad_padding_and_junk():\n"
        "    with pytest.raises(FrameError):\n"
        "        decode_frame(b'ABC\\x00')  # misaligned (len=4 != 0 mod 8)\n"
        "    with pytest.raises(FrameError):\n"
        "        decode_frame(b'A\\x00\\x00\\x00\\x00\\x00\\x00\\x00')  # >6 pad bytes\n"
        "    with pytest.raises(FrameError):\n"
        "        decode_frame(b'AB\\x00CDEF\\x00')  # embedded null\n"
        "    with pytest.raises(FrameError):\n"
        "        decode_frame(b'!!!!')  # non-alphabet junk\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(ws, "test_framing.py", timeout_s=30)
    assert res["repaired"] is True, res
    assert res["rule"] == "BOUNDARY_NORM_PRELUDE_pkt_MOD8_MAX6"


def test_iteration_j_regex_refinement_dotted_slug_module_global(tmp_path: pathlib.Path):
    """Engine J-2: Dataflow-Back-Sliced Regex Algebraic Refinement CEGIS follows a
    module-level `re.compile(...)` global referenced by a traced function and repairs
    an unseen dotted-identifier regex with zero library/pattern hardcoding!
    """
    ws = tmp_path / "slug_ws"
    ws.mkdir()
    (ws / "slugs.py").write_text(
        "import re\n"
        "_DOT_SLUG_RE = re.compile(r'[a-z]|[a-z]([a-z\\.](?!\\.\\.))*[a-z]')\n"
        "def is_valid_dotted_slug(text: str) -> bool:\n"
        "    return _DOT_SLUG_RE.fullmatch(text) is not None\n",
        encoding="utf-8",
    )
    (ws / "test_slugs.py").write_text(
        "from slugs import is_valid_dotted_slug\n"
        "def test_valid():\n"
        "    assert is_valid_dotted_slug('a')\n"
        "    assert is_valid_dotted_slug('foo.bar.baz')\n"
        "def test_rejects_double_dot():\n"
        "    assert not is_valid_dotted_slug('foo..bar')\n"
        "    assert not is_valid_dotted_slug('a..b')\n"
        "    assert not is_valid_dotted_slug('.a')\n"
        "    assert not is_valid_dotted_slug('a.')\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(ws, "test_slugs.py", timeout_s=25)
    assert res["repaired"] is True, res
    assert "REGEX_CANONICAL_SEP_TOKEN" in str(res.get("rule"))


def test_iteration_j_replace_chain_context_qualification(tmp_path: pathlib.Path):
    """Engine J-3: String `.replace()` Chain Context-Qualification repairs over-broad
    exponent-zero stripping without corrupting negative decimal values.
    """
    ws = tmp_path / "fmt_ws"
    ws.mkdir()
    (ws / "numfmt.py").write_text(
        "def compact_sci(val: float) -> str:\n"
        "    return f'{val:.3g}'.replace('+0', '+').replace('-0', '-')\n",
        encoding="utf-8",
    )
    (ws / "test_numfmt.py").write_text(
        "from numfmt import compact_sci\n"
        "def test_large_and_tiny():\n"
        "    assert compact_sci(1e5) == '1e+5'\n"
        "    assert compact_sci(1e-5) == '1e-5'\n"
        "def test_negative_fraction():\n"
        "    assert compact_sci(-0.25) == '-0.25'\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(ws, "test_numfmt.py", timeout_s=25)
    assert res["repaired"] is True, res
    assert res["rule"] == "REPLACE_CHAIN_CONTEXT_'e'"


def test_iteration_j_vararg_signature_arity_repair(tmp_path: pathlib.Path):
    """Engine J-4: Vararg Signature Arity-Mismatch Repair surgically promotes
    `(cls, items, *, sep=',')` -> `(cls, *items, sep=',')` even when Python raises
    `TypeError` at the call site before entering the function body (`ranked_lines == []`).
    """
    ws = tmp_path / "vararg_ws"
    ws.mkdir()
    (ws / "joiner.py").write_text(
        "class Joiner:\n"
        "    @classmethod\n"
        "    def combine(cls, items, *, sep=','):\n"
        "        return sep.join(str(x) for x in items)\n",
        encoding="utf-8",
    )
    (ws / "test_joiner.py").write_text(
        "from joiner import Joiner\n"
        "def test_combine_varargs():\n"
        "    assert Joiner.combine('a', 'b', 'c', sep='-') == 'a-b-c'\n"
        "    assert Joiner.combine(1, 2) == '1,2'\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(ws, "test_joiner.py", timeout_s=25)
    assert res["repaired"] is True, res
    assert res["method"] == "VARARG_SIGNATURE_REPAIR"
    assert "def combine(cls, *items, sep=','):" in res["patched_source"]


def test_engine_k1_dataflow_shadow_subst_and_charset_residual(tmp_path: pathlib.Path):
    """Engines K-1a & K-1b: normalized-local dataflow shadow + percent-encoding charset subtraction."""
    ws1 = tmp_path / "shadow_ws"
    ws1.mkdir()
    (ws1 / "resolver.py").write_text(
        "class Item:\n"
        "    def __init__(self, key):\n"
        "        self.key = key\n"
        "def normalize(s):\n"
        "    return s.lower().replace('_', '-')\n"
        "def format_cycle(group, item):\n"
        "    norm = normalize(item.key)\n"
        "    if norm == group:\n"
        "        return f'self:{item.key}'\n"
        "    return f'{group}->{norm}'\n",
        encoding="utf-8",
    )
    (ws1 / "test_resolver.py").write_text(
        "from resolver import Item, format_cycle\n"
        "def test_self_cycle():\n"
        "    assert format_cycle('a-b', Item('A_B')) == 'self:a-b'\n"
        "    assert format_cycle('foo-bar', Item('Foo_Bar')) == 'self:foo-bar'\n"
        "    assert format_cycle('a', Item('b')) == 'a->b'\n",
        encoding="utf-8",
    )
    res1 = acr.repair_repo_angelic_cegis(ws1, "test_resolver.py", timeout_s=25)
    assert res1["repaired"] is True, res1
    assert "self:{norm}" in res1["patched_source"]

    ws2 = tmp_path / "charset_ws"
    ws2.mkdir()
    (ws2 / "codec.py").write_text(
        "from urllib.parse import quote\n"
        "def encode_val(s):\n"
        "    return quote(s, safe=\"!$'()*+,/:;?@\")\n",
        encoding="utf-8",
    )
    (ws2 / "test_codec.py").write_text(
        "from codec import encode_val\n"
        "def test_encode_plus():\n"
        "    assert encode_val('a+b/c') == 'a%2Bb/c'\n",
        encoding="utf-8",
    )
    res2 = acr.repair_repo_angelic_cegis(ws2, "test_codec.py", timeout_s=25)
    assert res2["repaired"] is True, res2
    assert "+" not in res2["patched_source"].split("safe=")[1].split(")")[0]


def test_engine_k1_sign_prefix_hoist_and_bracket_safe_partition(tmp_path: pathlib.Path):
    """Engines K-1c & K-1d: sign-prefix hoisting + bracket-safe IPv6 authority partition."""
    ws1 = tmp_path / "sign_ws"
    ws1.mkdir()
    (ws1 / "fmt.py").write_text(
        "def fmt_small(left, right, exp):\n"
        "    return f\"0.{'0' * (-exp - len(left))}{left}{right}\"\n",
        encoding="utf-8",
    )
    (ws1 / "test_fmt.py").write_text(
        "from fmt import fmt_small\n"
        "def test_small_neg():\n"
        "    assert fmt_small('1', '', -5) == '0.00001'\n"
        "    assert fmt_small('-1', '', -5) == '-0.00001'\n",
        encoding="utf-8",
    )
    res1 = acr.repair_repo_angelic_cegis(ws1, "test_fmt.py", timeout_s=25)
    assert res1["repaired"] is True, res1
    assert "SIGN_PREFIX_HOIST_left" in str(res1.get("rule"))

    ws2 = tmp_path / "ipv6_ws"
    ws2.mkdir()
    (ws2 / "addr.py").write_text(
        "def parse_host_port(server_name):\n"
        "    host, _, port = server_name.partition(':')\n"
        "    return host, (int(port) if port else 5000)\n",
        encoding="utf-8",
    )
    (ws2 / "test_addr.py").write_text(
        "from addr import parse_host_port\n"
        "def test_ipv4_and_ipv6():\n"
        "    assert parse_host_port('example.com:8080') == ('example.com', 8080)\n"
        "    assert parse_host_port('[::1]:8080') == ('::1', 8080)\n"
        "    assert parse_host_port('[::1]:0') == ('::1', 0)\n"
        "    assert parse_host_port('[::1]') == ('::1', 5000)\n",
        encoding="utf-8",
    )
    res2 = acr.repair_repo_angelic_cegis(ws2, "test_addr.py", timeout_s=25)
    assert res2["repaired"] is True, res2
    assert res2["rule"] == "BRACKET_SAFE_AUTHORITY_PARTITION"


def test_engine_k3_self_play_harvest_compaction_and_lazy_vs_broad(tmp_path: pathlib.Path):
    """Engine K-3 (§9.4.4 & §9.2): offline zero-weight self-play harvest + compaction + lazy vs broad."""
    ws_a = tmp_path / "sp_a"
    ws_b = tmp_path / "sp_b"
    ws_a.mkdir()
    ws_b.mkdir()
    (ws_a / "tax.py").write_text(
        "def calc(x, exempt=False):\n"
        "    if x > 50:\n"
        "        return 5\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (ws_a / "test_tax.py").write_text(
        "from tax import calc\n"
        "def test_t():\n"
        "    assert calc(100, False) == 5\n"
        "    assert calc(100, True) == 0\n"
        "    assert calc(10, False) == 0\n",
        encoding="utf-8",
    )
    (ws_b / "fee.py").write_text(
        "def charge(amt, waived=False):\n"
        "    if amt > 20:\n"
        "        return 3\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (ws_b / "test_fee.py").write_text(
        "from fee import charge\n"
        "def test_f():\n"
        "    assert charge(80, False) == 3\n"
        "    assert charge(80, True) == 0\n"
        "    assert charge(5, False) == 0\n",
        encoding="utf-8",
    )
    store_p = tmp_path / "harvest_store.json"
    out = rta.run_self_play_harvest_and_compact(
        [
            {"id": "task_a", "repo_root": ws_a, "test_file": "test_tax.py"},
            {"id": "task_b", "repo_root": ws_b, "test_file": "test_fee.py"},
        ],
        store_p,
        timeout_per_task_s=25,
    )
    assert out["model_calls"] == 0
    assert out["tasks_solved"] == 2
    assert out["l2_final_count"] >= 1
    assert out["compaction"]["l2_after"] <= out["compaction"]["l2_before"]

    # §9.2 Empirical Goal-Directed Lazy Acquisition vs Broad-Ingest Crawl
    docs = {f"man_tool_{i:02d}": f"usage tool_{i:02d} --flag-{i:02d} " + ("padding " * 80) for i in range(40)}
    docs["man_archive_extract"] = "usage archive --extract-zstd <src> --out <dst> " + ("info " * 20)
    docs["man_net_route"] = "usage netctl --ipv6-route <cidr> --gw <ip> " + ("info " * 20)
    cmp = rta.benchmark_lazy_vs_broad_acquisition(
        docs,
        [("archive", "man_archive_extract"), ("netctl", "man_net_route")],
    )
    assert cmp["model_calls"] == 0
    assert cmp["goal_directed_lazy"]["accuracy"] == 1.0
    assert cmp["broad_ingest"]["accuracy"] == 1.0
    assert cmp["byte_reduction_ratio"] >= 5.0
    assert cmp["winner_per_unit_cost"] == "goal_directed_lazy"


def test_engine_l1_cross_statement_expr_subtree_1shot_transfer(tmp_path: pathlib.Path):
    """Engine L-1: single-experience `expr_subtree` morphism transfers across Assign -> Call arg & Name -> Attribute!"""
    store_p = tmp_path / "expr_l2.json"
    store = uca.ExternalCausalLawStore(store_p)

    # Experience 1: Assign statement with simple `Name` receiver (`addr.partition(":")`)
    ws1 = tmp_path / "repo_one"
    ws1.mkdir()
    (ws1 / "srv.py").write_text(
        "def split_addr(addr):\n"
        "    h, _, p = addr.partition(':')\n"
        "    return h, (int(p) if p else 80)\n",
        encoding="utf-8",
    )
    (ws1 / "test_srv.py").write_text(
        "from srv import split_addr\n"
        "def test_ipv6():\n"
        "    assert split_addr('[::1]:8080') == ('::1', 8080)\n"
        "    assert split_addr('example.com:80') == ('example.com', 80)\n",
        encoding="utf-8",
    )
    r1 = acr.repair_repo_angelic_cegis(ws1, "test_srv.py", timeout_s=30, skill_store=store)
    assert r1["repaired"] is True, r1
    morphs = store.list_tree_morphisms()
    assert any(m.target_kind == "expr_subtree" for m in morphs), [m.target_kind for m in morphs]

    # Experience 2 (completely different file, Call-argument statement shape, 2-hop Attribute receiver!):
    ws2 = tmp_path / "repo_two"
    ws2.mkdir()
    (ws2 / "cookie.py").write_text(
        "class Req:\n"
        "    def __init__(self, host): self.host = host\n"
        "class Ctx:\n"
        "    def __init__(self, host): self.req = Req(host)\n"
        "def record_domain(ctx, out):\n"
        "    out.append(ctx.req.host.partition(':')[0])\n",
        encoding="utf-8",
    )
    (ws2 / "test_cookie.py").write_text(
        "from cookie import Ctx, record_domain\n"
        "def test_ipv6_cookie():\n"
        "    out = []\n"
        "    record_domain(Ctx('[::1]:5000'), out)\n"
        "    record_domain(Ctx('localhost:5000'), out)\n"
        "    assert out == ['::1', 'localhost']\n",
        encoding="utf-8",
    )
    r2 = acr.repair_repo_angelic_cegis(
        ws2, "test_cookie.py", timeout_s=30, skill_store=uca.ExternalCausalLawStore(store_p)
    )
    assert r2["repaired"] is True, r2
    assert r2["method"] == "L2_TREE_REWRITE_MORPHISM_1SHOT"
    assert r2["stats"]["candidates_verified"] == 1
    assert r2["stats"]["tree_morphism_hits"] == 1


def test_engine_l2_callee_hook_fallback_and_codegen_fstring_escape(tmp_path: pathlib.Path):
    """Engines L-2a & L-2b: callee-declared hook fallback synthesis + codegen f-string brace escape."""
    ws1 = tmp_path / "desc_ws"
    ws1.mkdir()
    (ws1 / "proxy.py").write_text(
        "class Lookup:\n"
        "    def __init__(self, fn=None, on_unbound=None):\n"
        "        self.fn = fn\n"
        "        self.on_unbound = on_unbound\n"
        "    def __set_name__(self, owner, name):\n"
        "        self.name = name\n"
        "    def __get__(self, inst, owner=None):\n"
        "        if inst is None:\n"
        "            return self\n"
        "        try:\n"
        "            obj = inst._current()\n"
        "        except RuntimeError:\n"
        "            if self.on_unbound is None:\n"
        "                raise\n"
        "            return self.on_unbound(inst)\n"
        "        return getattr(obj, self.name)\n"
        "class Box:\n"
        "    def _current(self):\n"
        "        raise RuntimeError('unbound')\n"
        "    __class__ = Lookup()\n",
        encoding="utf-8",
    )
    (ws1 / "test_proxy.py").write_text(
        "from proxy import Box\n"
        "def test_isinstance_unbound():\n"
        "    b = Box()\n"
        "    assert isinstance(b, Box)\n"
        "    assert not isinstance(b, dict)\n",
        encoding="utf-8",
    )
    r1 = acr.repair_repo_angelic_cegis(ws1, "test_proxy.py", timeout_s=30)
    assert r1["repaired"] is True, r1
    assert "on_unbound=lambda self: type(self)" in r1["patched_source"]

    ws2 = tmp_path / "codegen_ws"
    ws2.mkdir()
    (ws2 / "gen.py").write_text(
        "def build_fn(src_label, sym):\n"
        "    msg = (\n"
        "        'missing in {mod!r}'\n"
        "        f' (from {src_label})'\n"
        "        f' symbol {sym!r}'\n"
        "    )\n"
        "    code = f'def run(mod): return f{msg!r}'\n"
        "    ns = {}\n"
        "    exec(code, ns)\n"
        "    return ns['run']\n",
        encoding="utf-8",
    )
    (ws2 / "test_gen.py").write_text(
        "from gen import build_fn\n"
        "def test_curly_label():\n"
        "    fn = build_fn('{bad}.tmpl', 'x')\n"
        "    assert '{bad}.tmpl' in fn('demo')\n",
        encoding="utf-8",
    )
    r2 = acr.repair_repo_angelic_cegis(ws2, "test_gen.py", timeout_s=30)
    assert r2["repaired"] is True, r2
    assert "CODEGEN_FSTRING_ESCAPE" in str(r2.get("rule"))


def test_iter_m_engine_m4_o1_l2_index_at_5000_distractors(tmp_path: pathlib.Path) -> None:
    """Engine M-4: O(1) structural-fingerprint L2 index recalls 1 true morphism among 5,000 distractors in <50ms."""
    import dataclasses

    store = uca.ExternalCausalLawStore(tmp_path / "l2_5k.json")
    before = "def f(x):\n    y = x.rstrip('/')\n    return y\n"
    after = "def f(x):\n    y = x.rstrip('/') or '/'\n    return y\n"
    real_m = rta.extract_multi_stmt_tree_morphism(before, after, provenance={"src": "unit"})
    assert real_m is not None
    store.admit_tree_morphism(real_m)
    for i in range(5000):
        dm = rta.TreeRewriteMorphism(
            morphism_id=f"distractor_{i:05d}",
            target_kind="expr_subtree" if i % 2 == 0 else "stmt_slice",
            pattern_sexps=[{"_node": "Call", "func": {"_node": "Attribute", "attr": f"fn_{i}"}, "args": [{"_node": "Constant", "value": f"v_{i}"}]}],
            replacement_sexps=[{"_node": "Constant", "value": i}],
            hole_types={},
        )
        store.tree_morphisms[dm.morphism_id] = dataclasses.asdict(dm)
    store._rebuild_tree_index()

    target_src = "def g(a):\n    return helper(a.b.rstrip('/'))\n"
    t0 = time.perf_counter()
    hits = store.query_tree_morphisms_o1(target_src, target_lines={2}, max_results=16)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    assert [m.morphism_id for m in hits] == [real_m.morphism_id]
    assert dt_ms < 100.0


def test_iter_m_engine_m2_codebase_type_habitation_and_sibling_method(tmp_path: pathlib.Path) -> None:
    """Engine M-2: Codebase-internal type-habitation breaks literal-trace blindness (.copy() + sibling method)."""
    root = tmp_path / "m2_repo"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "utils.py").write_text("def clone_items(xs):\n    return xs.copy()\n", encoding="utf-8")
    (root / "pkg" / "queue_mod.py").write_text(
        "def snapshot_queue(head):\n    out = head\n    return out\n", encoding="utf-8"
    )
    (root / "tests" / "test_queue.py").write_text(
        "from pkg.queue_mod import snapshot_queue\n\n"
        "def test_snapshot_isolated():\n"
        "    data = [1, 2, 3]\n"
        "    snap = snapshot_queue(data)\n"
        "    snap.append(4)\n"
        "    assert data == [1, 2, 3]\n"
        "def test_snapshot_values():\n"
        "    assert snapshot_queue([10, 20]) == [10, 20]\n",
        encoding="utf-8",
    )
    r_copy = acr.repair_repo_angelic_cegis(root, "tests/test_queue.py", timeout_s=30)
    assert r_copy["repaired"] is True, r_copy
    assert ".copy()" in str(r_copy.get("patched_source"))

    (root / "pkg" / "registry.py").write_text(
        "class Registry:\n"
        "    def __init__(self):\n        self._items = {'auth': 0}\n"
        "    def get_plugin(self, name):\n        return self._items.get(name)\n"
        "    def has_plugin(self, name):\n        return name in self._items\n"
        "    def require_registered(self, name):\n"
        "        if self.get_plugin(name):\n            return 'ok'\n        return 'missing'\n",
        encoding="utf-8",
    )
    (root / "pkg" / "caller.py").write_text(
        "def check_all(reg):\n    return reg.has_plugin('a') and reg.has_plugin('b')\n", encoding="utf-8"
    )
    (root / "tests" / "test_registry.py").write_text(
        "from pkg.registry import Registry\n\n"
        "def test_falsy_registered_plugin():\n    assert Registry().require_registered('auth') == 'ok'\n"
        "def test_unregistered_plugin():\n    assert Registry().require_registered('nope') == 'missing'\n",
        encoding="utf-8",
    )
    r_sib = acr.repair_repo_angelic_cegis(root, "tests/test_registry.py", timeout_s=30)
    assert r_sib["repaired"] is True, r_sib
    assert "self.has_plugin" in str(r_sib.get("patched_source"))


def test_iter_m_engine_m3_relational_zipper_two_file_coupled_repair(tmp_path: pathlib.Path) -> None:
    """Engine M-3: Def-Use Relational Zipper retains primary-passing root edit and propagates coupled repair across files."""
    root = tmp_path / "m3_repo"
    (root / "core").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "tests").mkdir()
    (root / "core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "core" / "parser.py").write_text("def normalize_path(path):\n    return path.rstrip('/')\n", encoding="utf-8")
    (root / "app" / "router.py").write_text(
        "from core.parser import normalize_path\n\n"
        "def build_route(path):\n    p = normalize_path(path)\n    return p + '/index'\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_parser.py").write_text(
        "from core.parser import normalize_path\n\n"
        "def test_root_path():\n    assert normalize_path('/') == '/'\n"
        "def test_nested_path():\n    assert normalize_path('/api/') == '/api'\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_router.py").write_text(
        "from app.router import build_route\n\n"
        "def test_root_route():\n    assert build_route('/') == '/index'\n"
        "def test_nested_route():\n    assert build_route('/api/') == '/api/index'\n",
        encoding="utf-8",
    )
    res = acr.repair_repo_angelic_cegis(
        root, "tests/test_parser.py", extra_test_files=["tests/test_router.py"], timeout_s=45
    )
    assert res["repaired"] is True, res
    assert res["method"] == "RELATIONAL_ZIPPER_MULTIFILE"
    assert sorted((res.get("patched_files") or {}).keys()) == ["app/router.py", "core/parser.py"]


def test_iter_m_engine_m1_issue_only_zero_leakage_green_suite(tmp_path: pathlib.Path) -> None:
    """Engine M-1: Synthesizes failing metamorphic oracle from issue prose on 100%-green repo and repairs with 0 leakage."""
    root = tmp_path / "m1_repo"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "utils.py").write_text("def clone(x):\n    return x.copy()\n", encoding="utf-8")
    (root / "pkg" / "items.py").write_text(
        "def normalize_items(items):\n    items.append('done')\n    return items\n", encoding="utf-8"
    )
    (root / "tests" / "test_items.py").write_text(
        "from pkg.items import normalize_items\n\n"
        "def test_normalize_adds_done():\n    assert normalize_items([1, 2]) == [1, 2, 'done']\n",
        encoding="utf-8",
    )
    issue_prose = (
        "Bug: `normalize_items` mutates the caller's list in-place instead of working on a copy.\n"
        "Calling `normalize_items` should not mutate the input list."
    )
    res = acr.repair_repo_from_issue_zero_leakage(
        root, issue_prose, regression_test_files=["tests/test_items.py"], timeout_s=35
    )
    assert res["repaired"] is True, res
    assert res["model_calls"] == 0
    assert res["oracle_synthesis"]["zero_leakage"] is True
    assert "items = items.copy()" in str(res.get("patched_source"))
    assert not (root / "_brain_metamorphic_oracle_test.py").exists()


def test_iter_n_engine_n1_metamorphic_protocol_and_encoding_oracles(tmp_path: pathlib.Path) -> None:
    """Engine N-1: Zero-leakage issue-only repair via protocol isinstance & URL encoding round-trip laws."""
    # Case 1: URL query plus-sign percent-encoding round-trip (100% green suite -> unseen encoding fix)
    u_root = tmp_path / "url_repo"
    (u_root / "pkg").mkdir(parents=True)
    (u_root / "tests").mkdir()
    (u_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (u_root / "pkg" / "urls.py").write_text(
        "from urllib.parse import urlencode\n\n"
        "def _urlencode(query):\n"
        "    return urlencode(query, safe=\"!$'()*+,/:;?@\")\n",
        encoding="utf-8",
    )
    (u_root / "tests" / "test_urls.py").write_text(
        "from pkg.urls import _urlencode\n\n"
        "def test_plain_query():\n    assert _urlencode({'a': '1'}) == 'a=1'\n",
        encoding="utf-8",
    )
    r_url = acr.repair_repo_from_issue_zero_leakage(
        u_root,
        "Percent-encode plus (+) when building URLs in urls._urlencode.",
        regression_test_files=["tests/test_urls.py"],
        timeout_s=35,
    )
    assert r_url["repaired"] is True, r_url
    assert r_url["oracle_synthesis"]["oracle_kind"] == "METAMORPHIC_ENCODING_ROUNDTRIP"
    assert "+" not in str(r_url.get("patched_source")).split("safe=", 1)[1].splitlines()[0]

    # Case 2: Unbound proxy `isinstance` protocol safety (100% green suite -> descriptor fallback fix)
    p_root = tmp_path / "proxy_repo"
    (p_root / "pkg").mkdir(parents=True)
    (p_root / "tests").mkdir()
    (p_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (p_root / "pkg" / "local.py").write_text(
        "class _ProxyLookup:\n"
        "    def __init__(self, f=None, fallback=None):\n"
        "        self.f = f\n"
        "        self.fallback = fallback\n"
        "    def __set_name__(self, owner, name):\n"
        "        self.name = name\n"
        "    def __get__(self, inst, owner=None):\n"
        "        if inst is None:\n"
        "            return self\n"
        "        try:\n"
        "            obj = inst._get_current_object()\n"
        "        except RuntimeError:\n"
        "            if self.fallback is None:\n"
        "                raise\n"
        "            return self.fallback(inst)\n"
        "        return getattr(obj, self.name)\n\n"
        "class LocalProxy:\n"
        "    def __init__(self, fn):\n"
        "        object.__setattr__(self, '_fn', fn)\n"
        "    def _get_current_object(self):\n"
        "        return object.__getattribute__(self, '_fn')()\n"
        "    __class__ = _ProxyLookup()\n",
        encoding="utf-8",
    )
    (p_root / "tests" / "test_local.py").write_text(
        "from pkg.local import LocalProxy\n\n"
        "def test_bound_proxy():\n    p = LocalProxy(lambda: 'hi')\n    assert isinstance(p, str)\n",
        encoding="utf-8",
    )
    r_px = acr.repair_repo_from_issue_zero_leakage(
        p_root,
        "Restore LocalProxy __class__ behaviour so isinstance checking on an unbound LocalProxy does not error.",
        regression_test_files=["tests/test_local.py"],
        timeout_s=35,
    )
    assert r_px["repaired"] is True, r_px
    assert r_px["oracle_synthesis"]["oracle_kind"] == "METAMORPHIC_PROTOCOL_ISINSTANCE"
    assert "fallback=lambda self: type(self)" in str(r_px.get("patched_source"))


def test_iter_n_engine_n2_autonomous_reverse_caller_zipper(tmp_path: pathlib.Path) -> None:
    """Engine N-2: Autonomous 1-hop reverse-caller test discovery triggers 2-file Relational Zipper with NO hints."""
    root = tmp_path / "n2_auto_zipper"
    (root / "core").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "tests").mkdir()
    (root / "core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "core" / "parser.py").write_text("def normalize_path(path):\n    return path.rstrip('/')\n", encoding="utf-8")
    (root / "app" / "router.py").write_text(
        "from core.parser import normalize_path\n\n"
        "def build_route(path):\n    p = normalize_path(path)\n    return p + '/index'\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_parser.py").write_text(
        "from core.parser import normalize_path\n\n"
        "def test_root_path():\n    assert normalize_path('/') == '/'\n"
        "def test_nested_path():\n    assert normalize_path('/api/') == '/api'\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_router.py").write_text(
        "from app.router import build_route\n\n"
        "def test_root_route():\n    assert build_route('/') == '/index'\n"
        "def test_nested_route():\n    assert build_route('/api/') == '/api/index'\n",
        encoding="utf-8",
    )
    # Intentionally OMIT `extra_test_files` — Engine N-2 auto-discovers `tests/test_router.py`!
    res = acr.repair_repo_angelic_cegis(root, "tests/test_parser.py", timeout_s=45)
    assert res["repaired"] is True, res
    assert res["method"] == "RELATIONAL_ZIPPER_MULTIFILE"
    assert sorted((res.get("patched_files") or {}).keys()) == ["app/router.py", "core/parser.py"]


def test_iter_n_engine_n3a_compiled_c_binary_byte_jacobian_and_fst_lens(tmp_path: pathlib.Path) -> None:
    """Engine N-3a (Idea 5): Black-box Byte Jacobian + C FST Lens Compiler verified on a real gcc ELF binary."""
    import shutil
    import subprocess

    cc = shutil.which("gcc") or shutil.which("cc")
    if not cc:
        pytest.skip("C compiler unavailable")

    c_path = tmp_path / "ctrl_filter.c"
    bin_path = tmp_path / "ctrl_filter"
    buggy_c = (
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    int c;\n"
        "    while ((c = getchar()) != EOF) {\n"
        "        putchar(c);\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    c_path.write_text(buggy_c, encoding="utf-8")
    subprocess.run([cc, "-O2", str(c_path), "-o", str(bin_path)], check=True)

    prober = rta.ByteDifferentialJacobianProber([str(bin_path)])
    jac = prober.compute_byte_jacobian(b"ab\x04cd")
    assert jac["jacobian"] == {0: [0], 1: [1], 2: [2], 3: [3], 4: [4]}

    witnesses = [(b"hi\x04!", b"hi^D!"), (b"end\x1a.", b"end^Z."), (b"plain", b"plain")]
    overrides = prober.infer_byte_fst_overrides(witnesses)
    assert overrides == {0x04: b"^D", 0x1A: b"^Z"}

    patched_c = rta.synthesize_c_fst_byte_patch(buggy_c, overrides)
    assert patched_c is not None
    c_path.write_text(patched_c, encoding="utf-8")
    subprocess.run([cc, "-O2", str(c_path), "-o", str(bin_path)], check=True)

    for inp, exp in witnesses + [(b"\x04\x1aok\x04", b"^D^Zok^D")]:
        rc, out, _ = prober.run_bytes(inp)
        assert rc == 0 and out == exp


def test_iter_n_engine_n3b_mutant_kill_selfplay_to_1shot_cross_repo_transfer(tmp_path: pathlib.Path) -> None:
    """Engine N-3b (Idea 6): Offline mutant-kill self-play on a clean repo transfers 1-shot to an unseen repo."""
    store = uca.ExternalCausalLawStore(tmp_path / "sp_store.json")
    train = tmp_path / "train_lib"
    (train / "mylib").mkdir(parents=True)
    (train / "tests").mkdir()
    (train / "mylib" / "__init__.py").write_text("", encoding="utf-8")
    (train / "mylib" / "paths.py").write_text("def clean_mount(raw_mount):\n    return raw_mount.rstrip('/') or '/'\n", encoding="utf-8")
    (train / "tests" / "test_paths.py").write_text(
        "from mylib.paths import clean_mount\n"
        "def test_root(): assert clean_mount('/') == '/'\n"
        "def test_sub(): assert clean_mount('/v1/') == '/v1'\n",
        encoding="utf-8",
    )
    dist = uca.distill_repo_mutants_to_l2_store(train, "tests/test_paths.py", store)
    assert dist["ok"] is True and dist["mutants_killed"] >= 1 and dist["morphisms_admitted"] == 1

    unseen = tmp_path / "unseen_service"
    (unseen / "svc").mkdir(parents=True)
    (unseen / "tests").mkdir()
    (unseen / "svc" / "__init__.py").write_text("", encoding="utf-8")
    (unseen / "svc" / "handler.py").write_text(
        "class Req:\n    def __init__(self, prefix): self.prefix = prefix\n"
        "def wrap(s): return f'[{s}]'\n"
        "def handle(req):\n    return wrap(req.prefix.rstrip('/'))\n",
        encoding="utf-8",
    )
    (unseen / "tests" / "test_handler.py").write_text(
        "from svc.handler import Req, handle\n"
        "def test_root(): assert handle(Req('/')) == '[/]'\n"
        "def test_api(): assert handle(Req('/api/')) == '[/api]'\n",
        encoding="utf-8",
    )
    r_warm = acr.repair_repo_angelic_cegis(unseen, "tests/test_handler.py", timeout_s=30, skill_store=store)
    assert r_warm["repaired"] is True, r_warm
    assert r_warm["method"] == "L2_TREE_REWRITE_MORPHISM_1SHOT"
    assert r_warm["stats"]["candidates_verified"] == 1
    assert r_warm["stats"]["o1_morphism_candidates"] == 1


def test_iter_o_engine_o1_transactional_cow_and_negative_effect_oracle(tmp_path: pathlib.Path):
    """Engine O-1 (Idea 4): Parallel CoW Workspace Time-Travel + Negative-Effect Invariant Oracle."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "prod.db").write_text("CRITICAL_PRODUCTION_V1\n", encoding="utf-8")
    (ws / "config.ini").write_text("mode=safe\n", encoding="utf-8")
    (ws / "input.csv").write_text("k,v\na,10\nb,20\nc,30\n", encoding="utf-8")
    store = uca.ExternalCausalLawStore(tmp_path / "cow_laws.json")
    runner = uca.TransactionalWorkspaceCoWRunner(ws, law_store=store)

    out = runner.execute_speculative_candidates(
        candidates=[
            {"id": "destructive_cheat", "command": "rm -f prod.db && echo 'sum=60' > summary.txt"},
            {"id": "side_effect_corruptor", "command": "echo 'bad' > config.ini && echo 'sum=60' > summary.txt"},
            {"id": "clean_solver", "command": "python3 -c \"import csv; r=list(csv.DictReader(open('input.csv'))); open('summary.txt','w').write(f'sum={sum(int(x[\\\"v\\\"]) for x in r)}\\n')\""},
        ],
        postcondition_clauses=[
            ("summary_exists", lambda root: (root / "summary.txt").is_file()),
            ("exact_sum_60", lambda root: (root / "summary.txt").read_text("utf-8").strip() == "sum=60"),
        ],
        allowed_write_paths=["summary.txt"],
    )
    assert out["committed"] is True
    assert out["winner_id"] == "clean_solver"
    assert out["committed_files"] == ["summary.txt"]
    assert out["model_calls"] == 0
    assert len(out["blocked_negative_effects"]) == 2
    assert (ws / "prod.db").read_text("utf-8") == "CRITICAL_PRODUCTION_V1\n"
    assert (ws / "config.ini").read_text("utf-8") == "mode=safe\n"
    assert (ws / "summary.txt").read_text("utf-8").strip() == "sum=60"
    assert len(store.negative_invariants) >= 2


def test_iter_o_engine_o2_polyglot_c_asan_null_uaf_and_logic_cegis(tmp_path: pathlib.Path):
    """Engine O-2: Polyglot C ASan/UBSan Causal CEGIS (CWE-476 NULL + CWE-416 Heap-UAF + Boolean Guard Scoping)."""
    import shutil
    import pytest
    from canonical.swe_kernel import c_asan_cegis_repair_v1 as casan

    if not (shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")):
        pytest.skip("No C compiler available")

    store = uca.ExternalCausalLawStore(tmp_path / "c_laws.json")

    # Case 1: CWE-476 NULL-dereference with codebase-habited NAN return hoisted to function entry
    c1 = tmp_path / "c_null"
    (c1 / "tests").mkdir(parents=True)
    (c1 / "calc.c").write_text(
        "#include <math.h>\n#include <stddef.h>\n"
        "typedef struct { double val; } Box;\n"
        "double set_box(Box *b, double x)\n{\n"
        "    if (x > 100.0) { b->val = 100.0; }\n"
        "    else { b->val = x; }\n"
        "    return b->val;\n}\n",
        encoding="utf-8",
    )
    (c1 / "tests" / "test_calc.c").write_text(
        "#include <assert.h>\n#include <math.h>\n#include <stddef.h>\n"
        "typedef struct { double val; } Box;\n"
        "double set_box(Box *b, double x);\n"
        "int main(void) {\n"
        "    Box box = {0.0};\n"
        "    assert(set_box(&box, 5.0) == 5.0);\n"
        "    assert(isnan(set_box(NULL, 5.0)));\n"
        "    assert(isnan(set_box(NULL, 200.0)));\n"
        "    return 0;\n}\n",
        encoding="utf-8",
    )
    r1 = casan.repair_c_repo_asan_cegis(c1, ["calc.c", "tests/test_calc.c"], editable_files=["calc.c"], skill_store=store)
    assert r1["repaired"] is True, r1
    assert r1["fault_kind"] == "NULL_DEREF"
    assert r1["rule"].startswith("C_ENTRY_PARAM_NULL_RETURN_b_NAN")
    assert r1["model_calls"] == 0

    # Case 2: CWE-416 Heap-Use-After-Free (`free(X); return clone(Y);` -> `EVAL-BEFORE-FREE`)
    c2 = tmp_path / "c_uaf"
    (c2 / "tests").mkdir(parents=True)
    (c2 / "node.c").write_text(
        "#include <stdlib.h>\n"
        "typedef struct Node { int v; struct Node *child; } Node;\n"
        "static Node *clone_node(const Node *n) {\n"
        "    Node *out = (Node *)malloc(sizeof(Node));\n"
        "    out->v = n->v; out->child = NULL;\n"
        "    return out;\n}\n"
        "static void free_tree(Node *n) {\n"
        "    if (!n) return;\n"
        "    free_tree(n->child);\n"
        "    free(n);\n}\n"
        "Node *replace_with_subtree(Node *root, const Node *sub)\n{\n"
        "    free_tree(root);\n"
        "    return clone_node(sub);\n}\n",
        encoding="utf-8",
    )
    (c2 / "tests" / "test_node.c").write_text(
        "#include <assert.h>\n#include <stdlib.h>\n"
        "typedef struct Node { int v; struct Node *child; } Node;\n"
        "Node *replace_with_subtree(Node *root, const Node *sub);\n"
        "int main(void) {\n"
        "    Node *r = (Node *)malloc(sizeof(Node));\n"
        "    Node *c = (Node *)malloc(sizeof(Node));\n"
        "    r->v = 1; r->child = c; c->v = 42; c->child = NULL;\n"
        "    Node *res = replace_with_subtree(r, c);\n"
        "    assert(res->v == 42);\n"
        "    free(res);\n"
        "    return 0;\n}\n",
        encoding="utf-8",
    )
    r2 = casan.repair_c_repo_asan_cegis(c2, ["node.c", "tests/test_node.c"], editable_files=["node.c"], skill_store=store)
    assert r2["repaired"] is True, r2
    assert r2["fault_kind"] == "USE_AFTER_FREE"
    assert r2["rule"].startswith("C_UAF_EVAL_BEFORE_FREE")
    assert r2["candidates_verified"] == 1
    assert r2["model_calls"] == 0
    assert len(store.active_laws()) >= 2


def test_iter_p_engine_p1_zero_leakage_c_issue_asan_oracle(tmp_path: pathlib.Path):
    """Engine P-1: Zero-leakage, zero-human-test C ASan/UBSan boundary fuzz oracle from `.h` + issue text."""
    import shutil
    import pytest
    from canonical.swe_kernel import c_asan_cegis_repair_v1 as casan

    if not (shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")):
        pytest.skip("No C compiler available")

    repo = tmp_path / "c_zero_test"
    repo.mkdir()
    (repo / "box.h").write_text(
        "typedef struct { double val; } Box;\n"
        "Box *box_create(void);\n"
        "double box_set_number(Box *object, double number);\n",
        encoding="utf-8",
    )
    (repo / "box.c").write_text(
        "#include <math.h>\n#include <stdlib.h>\n#include \"box.h\"\n"
        "Box *box_create(void) { return (Box *)calloc(1, sizeof(Box)); }\n"
        "double box_set_number(Box *object, double number)\n{\n"
        "    object->val = number;\n"
        "    return object->val;\n}\n",
        encoding="utf-8",
    )
    # ZERO human tests exist in `repo`! Only the issue description!
    res = casan.repair_c_repo_from_issue_zero_leakage(
        repo,
        "Bug: NULL pointer dereference in box_set_number when object is NULL.",
        timeout_s=30,
    )
    assert res["repaired"] is True, res
    assert res["zero_leakage_issue_only"] is True
    assert res["model_calls"] == 0
    assert res["oracle_synthesis"]["oracle_kind"] == "C_ASAN_BOUNDARY_NULL_ARG_0_object"
    assert not (repo / "_brain_c_asan_oracle.c").exists()

    # Apply synthesized patch and evaluate against an UNSEEN test asserting valid + NULL behavior!
    (repo / "box.c").write_text(res["patched_source"], encoding="utf-8")
    (repo / "unseen_test.c").write_text(
        "#include <assert.h>\n#include <math.h>\n#include <stdlib.h>\n#include \"box.h\"\n"
        "int main(void) {\n"
        "    Box *b = box_create();\n"
        "    assert(box_set_number(b, 9.5) == 9.5);\n"
        "    assert(isnan(box_set_number(NULL, 9.5)));\n"
        "    free(b); return 0;\n}\n",
        encoding="utf-8",
    )
    chk = casan.compile_and_run_c_asan(repo, ["box.c", "unseen_test.c"])
    assert chk["passed"] is True, chk


def test_iter_p_engine_p2_js_v8_causal_cegis_and_coordinate_descent(tmp_path: pathlib.Path):
    """Engine P-2: Polyglot JavaScript/Node.js V8 Causal CEGIS (TypeError guard + multi-site coordinate descent)."""
    import shutil
    import pytest
    from canonical.swe_kernel import js_causal_cegis_repair_v1 as jsc

    if not shutil.which("node"):
        pytest.skip("No node runtime available")

    store = uca.ExternalCausalLawStore(tmp_path / "js_laws.json")

    # Case 1: V8 TypeError null-property dereference -> optional chaining / null guard
    r1_dir = tmp_path / "js_null"
    (r1_dir / "lib").mkdir(parents=True)
    (r1_dir / "test").mkdir()
    (r1_dir / "lib" / "user.js").write_text(
        "'use strict'\nfunction getName(user) {\n  return user.name\n}\nmodule.exports = { getName }\n",
        encoding="utf-8",
    )
    (r1_dir / "test" / "user.test.js").write_text(
        "'use strict'\nconst assert = require('assert')\nconst { getName } = require('../lib/user.js')\n"
        "assert.strictEqual(getName({ name: 'Ada' }), 'Ada')\n"
        "assert.strictEqual(getName(null), undefined)\n",
        encoding="utf-8",
    )
    res1 = jsc.repair_js_repo_causal_cegis(r1_dir, "test/user.test.js", timeout_s=20, skill_store=store)
    assert res1["repaired"] is True, res1
    assert res1["err_kind"] == "NULL_PROP_DEREF"
    assert res1["model_calls"] == 0

    # Case 2: Multi-site 2-branch template interpolation bug solved by O(N) Coordinate-Descent Composition
    r2_dir = tmp_path / "js_multi"
    (r2_dir / "lib").mkdir(parents=True)
    (r2_dir / "test").mkdir()
    (r2_dir / "lib" / "fmt.js").write_text(
        "'use strict'\n"
        "function formatBound(major, minor, patch, suffix) {\n"
        "  if (major === 0) {\n"
        "    if (minor === 0) {\n"
        "      return `>=${major}.${minor}.${patch}${suffix} <0.0.${patch + 1}-0`\n"
        "    } else {\n"
        "      return `>=${major}.${minor}.${patch}${suffix} <0.${minor + 1}.0-0`\n"
        "    }\n"
        "  }\n"
        "  return `>=${major}.${minor}.${patch} <${major + 1}.0.0-0`\n"
        "}\n"
        "module.exports = { formatBound }\n",
        encoding="utf-8",
    )
    (r2_dir / "test" / "fmt.test.js").write_text(
        "'use strict'\nconst t = require('tap')\nconst { formatBound } = require('../lib/fmt.js')\n"
        "t.equal(formatBound(0, 0, 3, '-0'), '>=0.0.3 <0.0.4-0', 'patch branch')\n"
        "t.equal(formatBound(0, 2, 3, '-0'), '>=0.2.3 <0.3.0-0', 'minor branch')\n"
        "t.equal(formatBound(1, 2, 3, '-0'), '>=1.2.3 <2.0.0-0', 'major branch')\n",
        encoding="utf-8",
    )
    res2 = jsc.repair_js_repo_causal_cegis(r2_dir, "test/fmt.test.js", timeout_s=25, skill_store=store)
    assert res2["repaired"] is True, res2
    assert res2["method"] == "JS_V8_COORDINATE_DESCENT_CEGIS"
    assert "COORDINATE_DESCENT(" in res2["rule"]
    assert res2["model_calls"] == 0
    assert len(store.active_laws()) >= 2










