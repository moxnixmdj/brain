#!/usr/bin/env python3
"""Focused live tests for Minimal Epistemic Core v1 (Jobs 1+2+3+4a+5a), ARC-AGI-3 agent, Micro-Models, and UnifiedModel/Harbor wiring."""
from __future__ import annotations

import pathlib
import tarfile
import tempfile

from canonical.swe_kernel.minimal_epistemic_core_v1 import (
    DominoMemory,
    FastCoWVerifier,
    GitASTPrior,
    LiveIntrospector,
    LocalMicroModelBackend,
    PriorRepairEngine,
    SpecExtractor,
)


def test_local_micro_model_backend_fail_closed_loopback_only(monkeypatch):
    # Unset -> strictly disabled, 0 calls
    monkeypatch.delenv("BRAIN_LOCAL_LLM_ENDPOINT", raising=False)
    b0 = LocalMicroModelBackend()
    assert b0.enabled is False
    assert b0.propose_python_patches("def f(x): return x\n", "bug") == []
    assert b0.calls == 0
    # Remote non-loopback URL MUST be rejected (prevents accidental cloud calls)
    b_remote = LocalMicroModelBackend(endpoint="https://api.openai.com/v1/chat/completions")
    assert b_remote.enabled is False
    # Loopback URL accepted as opt-in endpoint
    b_local = LocalMicroModelBackend(endpoint="http://127.0.0.1:8080/v1/chat/completions")
    assert b_local.enabled is True


def test_unified_model_and_harbor_kernel_wiring():
    import io
    from canonical.runtime.brain_unified_model_v1 import UnifiedModel, load_model
    from canonical.runtime.harbor_swe_zero_model_agent_v1 import _build_kernel_tar_gz

    um = UnifiedModel(load_model())
    st = um.minimal_core_status()
    assert st["ok"] is True and st["k3_model_calls"] == 0

    # Repair wired through UnifiedModel (0 LLM calls)
    buggy = "def is_pos(x):\n    return x < 0\n"
    tst = "assert is_pos(3) is True\nassert is_pos(-1) is False\n"
    rep = um.minimal_core_repair(buggy, tst)
    assert rep["fixed"] is True and rep["k3_model_calls"] == 0

    # Lie detector wired through UnifiedModel
    lie = um.minimal_core_check_test_strength(buggy, "assert True\n")
    assert lie["is_lie"] is True and lie["k3_model_calls"] == 0

    # DominoMemory + SubspaceMemoryEncoder wired through UnifiedModel
    conv = {
        "session_1_date_time": "1:00 pm on 10 May, 2023",
        "session_1": [
            {"speaker": "Alice", "dia_id": "D1:1", "text": "Yesterday I visited Tokyo for work."},
            {"speaker": "Bob", "dia_id": "D1:2", "text": "Sounds great, I cooked ramen at home."},
        ],
    }
    mem_r = um.minimal_domino_memory("retrieve", conversation=conv, query="When did Alice visit Tokyo?", top_k=2, subspace_fusion=True)
    assert mem_r["ok"] is True and mem_r["turn_ids"][0] == "D1:1" and mem_r["k3_model_calls"] == 0

    # ARC-AGI-3 factory wired through UnifiedModel
    agent = um.minimal_arc3_create_agent()
    assert hasattr(agent, "play_level")

    # Harbor container kernel bundle includes minimal_epistemic_core_v1.py
    tgz = _build_kernel_tar_gz()
    with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as tf:
        names = set(tf.getnames())
    assert "canonical/swe_kernel/minimal_epistemic_core_v1.py" in names


def test_job1_live_introspector_scope_and_siblings():
    import ast
    src = "from math import floor\ndef f(text, prefix):\n    val = text.endswith(prefix)\n    return floor(1.5)\n"
    syms = LiveIntrospector.scope_symbols(ast.parse(src))
    assert "text" in syms["params"] and "prefix" in syms["params"]
    assert "val" in syms["locals"]
    assert "floor" in syms["imports"]
    assert "startswith" in LiveIntrospector.sibling_methods("endswith")
    assert "ceil" in LiveIntrospector.sibling_functions("floor")


def test_job2_domino_memory_cascade_supersession_and_temporal():
    dm = DominoMemory()
    dm.assert_fact("f1", "city=Paris", entity_key=("alice", "city"))
    dm.assert_fact("d1", "tz=CET", deps=("f1",))
    dm.assert_fact("d2", "greeting=Bonjour", deps=("d1",))
    assert dm.has_fact("d2")
    # Superseding alice's city must automatically cascade-retract f1 -> d1 -> d2!
    retracted = dm.assert_fact("f2", "city=Tokyo", entity_key=("alice", "city"))
    assert set(retracted) == {"f1", "d1", "d2"}
    assert dm.has_fact("f2") and not dm.has_fact("d2")

    sdate = DominoMemory.resolve_session_date("1:56 pm on 8 May, 2023")
    assert sdate is not None
    assert "7 May 2023" in DominoMemory.resolve_relative_dates("I went yesterday.", sdate)

    conv = {
        "session_1_date_time": "1:56 pm on 8 May, 2023",
        "session_1": [
            {"dia_id": "D1:1", "speaker": "Caroline", "text": "I went to a support group yesterday."},
            {"dia_id": "D1:2", "speaker": "Melanie", "text": "I ran a charity marathon for health."},
        ],
    }
    idx = DominoMemory.index_conversation(conv)
    r_ok = DominoMemory.retrieve_turns(idx, "When did Caroline go to the support group?", top_k=2)
    assert r_ok["dia_ids"][0] == "D1:1" and not r_ok["speaker_conflict"]
    r_adv = DominoMemory.retrieve_turns(idx, "What did Caroline run in the charity marathon?", top_k=2)
    assert r_adv["speaker_conflict"] is True


def test_job3_fast_cow_verifier_and_five_mutant_lie_detector():
    good_code = "def clamp(x):\n    if x < 0:\n        return 0\n    return x + 1\n"
    good_test = "assert clamp(-3) == 0\nassert clamp(4) == 5\n"
    bad_test = "assert True\n"
    out = FastCoWVerifier.run_isolated(good_code, good_test, timeout_s=0.1)
    assert out.passed
    # Infinite loop must be terminated cleanly within timeout
    loop_code = "def hang():\n    while True:\n        pass\n"
    out_loop = FastCoWVerifier.run_isolated(loop_code, "hang()", timeout_s=0.04)
    assert not out_loop.passed

    real_chk = FastCoWVerifier.check_test_strength(good_code, good_test)
    lie_chk = FastCoWVerifier.check_test_strength(good_code, bad_test)
    assert real_chk["is_lie"] is False and real_chk["killed"] >= 3
    assert lie_chk["is_lie"] is True and lie_chk["killed"] == 0


def test_job4a_and_job5a_end_to_end_cold_start_repair():
    # Bug 1: function/method misuse (endswith -> startswith)
    buggy_fn = "def has_pre(words, p):\n    return [w for w in words if w.endswith(p)]\n"
    test_fn = "assert has_pre(['abc', 'xyz', 'ab'], 'ab') == ['abc', 'ab']\n"
    doc_fn = "Filter strings starting with prefix.\n>>> has_pre(['abc', 'bca'], 'a')\n['abc']\n"
    spec = SpecExtractor.doctest_assertions(buggy_fn, "has_pre", docstring=doc_fn)
    assert "has_pre(['abc', 'bca'], 'a')" in spec

    eng = PriorRepairEngine(prior=GitASTPrior())
    res = eng.repair(buggy_fn, test_fn, entry_point="has_pre", docstring=doc_fn, use_doctests=True, timeout_s=0.1)
    assert res["fixed"] is True
    assert res["op_kind"] == "method_sibling"
    assert "startswith" in res["source"]

    # Bug 2: operator + off-by-one bug
    buggy_cmp = "def count_pos(nums):\n    return sum(1 for x in nums if x < 0)\n"
    test_cmp = "assert count_pos([-1, 0, 2, 5]) == 2\n"
    res2 = eng.repair(buggy_cmp, test_cmp, timeout_s=0.1)
    assert res2["fixed"] is True
    assert FastCoWVerifier.run_isolated(res2["source"], "assert count_pos([-5, 0, 1, 9, 10]) == 3", 0.1).passed


def test_step3_minimal_arc3_agent_hud_border_bar_and_affordance_pruning():
    import numpy as np
    from canonical.swe_kernel.minimal_arc3_agent_v1 import GamePrior, MinimalArc3Agent

    # Synthetic 16x16 world with a 1px bottom-row timer HUD that ticks on EVERY step (even walls!)
    prior = GamePrior(shape=(16, 16))
    f0 = np.zeros((16, 16), dtype=np.int16)
    f0[15, :] = 7  # energy bar along row 15
    for step_i in range(4):
        f_next = f0.copy()
        f_next[15, 15 - step_i] = 0
        raw_px, world_px, _ = prior.observe_diff(f0, f_next)
        assert raw_px == 1 and world_px == 0
        f0 = f_next
    # After >=3 distinct ticks on row 15, entire row 15 must be masked as HUD!
    assert bool(np.all(prior.hud_mask[15, :]))
    # Two frames differing ONLY in the HUD bar must now share the exact same world_key!
    fa = np.zeros((16, 16), dtype=np.int16); fa[5, 5] = 3; fa[15, 2] = 7
    fb = np.zeros((16, 16), dtype=np.int16); fb[5, 5] = 3; fb[15, 9] = 0
    assert prior.world_key(fa) == prior.world_key(fb)

    # End-to-end synthetic 1-level click game where ONLY color 9 advances to win in 2 clicks
    state = {"clicks": 0, "tick": 0}
    def make_frame():
        fr = np.zeros((16, 16), dtype=np.int16)
        fr[15, max(0, 15 - state["tick"]):] = 4  # ticking HUD bar
        fr[2:5, 2:5] = 2  # dead color 2
        fr[2:5, 10:13] = 5  # dead color 5
        fr[8:11, 8:11] = 9  # interactive color 9!
        if state["clicks"] >= 1:
            fr[11:14, 11:14] = 9  # real 3x3 world object change (9 px, not 1px HUD tick!)
        return fr

    def get_obs():
        lvl = 1 if state["clicks"] >= 2 else 0
        return make_frame(), [6], ("WIN" if lvl else "NOT_FINISHED"), lvl

    def step_fn(spec):
        state["tick"] += 1
        if spec["is_click"] and make_frame()[spec["y"], spec["x"]] == 9:
            state["clicks"] += 1
        return get_obs()

    def reset_fn():
        state["clicks"] = 0
        state["tick"] = 0
        return get_obs()

    agent = MinimalArc3Agent()
    res = agent.play_level(get_obs, step_fn, reset_fn, budget=12, start_level=0)
    assert res["solved"] is True and res["actions_used"] <= 8


def test_step4_micro_models_reranker_subspace_and_ast_lm():
    import numpy as np
    from canonical.swe_kernel.minimal_micro_models_v1 import (
        AstOpcodeMicroLM,
        OverfitRerankerMicroModel,
        SubspaceMemoryEncoder,
        extract_rerank_features,
    )

    # Micro-Model A: OverfitRerankerMicroModel
    buggy = "def f(x):\n    return x > 0\n"
    c_good = {"source": "def f(x):\n    return x < 0\n", "op_kind": "cmp_swap", "score": 4.0, "delta": 1}
    c_bad = {"source": "def f(x):\n    return x != 0\n", "op_kind": "cmp_swap", "score": 3.0, "delta": 1}
    f_g = extract_rerank_features(buggy, c_good, "Return True if x is below zero.", n_ex_passers=2, buggy_passed_ex=False)
    f_b = extract_rerank_features(buggy, c_bad, "Return True if x is below zero.", n_ex_passers=2, buggy_passed_ex=False)
    clf = OverfitRerankerMicroModel(dim=len(f_g))
    clf.fit(np.vstack([f_g, f_b]), np.array([1.0, 0.0]))
    probs = clf.predict_proba(np.vstack([f_g, f_b]))
    assert probs[0] > probs[1] and clf.size_bytes < 1024

    # Micro-Model B: SubspaceMemoryEncoder
    texts = [
        "Alice adopted a golden retriever puppy at the shelter.",
        "The puppy loves running in the park every morning.",
        "Bob cooked spicy pasta for dinner last night.",
        "We watched a documentary about deep sea volcanoes.",
    ]
    enc = SubspaceMemoryEncoder(n_components=3)
    st = enc.fit_conversation(texts, [1, 1, 2, 3])
    scores = enc.query_scores("puppy shelter")
    assert st["size_bytes"] > 0 and int(np.argmax(scores)) == 0

    # Micro-Model C: AstOpcodeMicroLM
    srcs = [
        "def add(a, b):\n    if a < 0:\n        return b\n    return a + b\n",
        "def mul(a, b):\n    if a == 0:\n        return 0\n    return a * b\n",
    ]
    lm1 = AstOpcodeMicroLM(max_order=1); lm1.fit_sources(srcs)
    lm3 = AstOpcodeMicroLM(max_order=3); lm3.fit_sources(srcs)
    e1 = lm1.eval_cross_entropy(srcs)
    e3 = lm3.eval_cross_entropy(srcs)
    assert e3["bits_per_node"] < e1["bits_per_node"]


def test_arc3_v3_undo_detection_and_cross_level_win_transfer():
    """Verify MinimalArc3Agent v3 detects A7 undo, prioritizes post-mechanic keystones, and transfers winning classes."""
    import numpy as np
    from canonical.swe_kernel.minimal_arc3_agent_v1 import MinimalArc3Agent

    # Toy 16x16 grid: A4 moves player right; hitting switch at x=4 fires mechanic (+6px color change),
    # then A5 submits & wins; A7 undoes the last move!
    hist: list[tuple[int, bool]] = [(2, False)]

    def make_frame():
        x, sw = hist[-1]
        fr = np.zeros((16, 16), dtype=np.int16)
        fr[7:9, x:x + 2] = 3  # 2x2 avatar
        if not sw:
            fr[7:9, 5:7] = 8  # switch ahead
        else:
            fr[2:5, 2:5] = 11  # 9-pixel distant door opened (mechanic fired!)
        return fr

    def get_obs():
        x, sw = hist[-1]
        win = (x == -1)
        return make_frame(), [1, 2, 3, 4, 5, 7], ("WIN" if win else "NOT_FINISHED"), (1 if win else 0)

    def step_fn(spec):
        aid = int(spec["aid"])
        x, sw = hist[-1]
        if aid == 7:
            if len(hist) > 1:
                hist.pop()
        elif aid == 4 and x < 10:
            nx = x + 1
            nsw = sw or (nx >= 4)
            hist.append((nx, nsw))
        elif aid == 3 and x > 1:
            hist.append((x - 1, sw))
        elif aid == 5 and sw:
            hist.append((-1, True))
        return get_obs()

    def reset_fn():
        hist[:] = [(2, False)]
        return get_obs()

    agent = MinimalArc3Agent()
    res = agent.play_level(get_obs, step_fn, reset_fn, budget=30, start_level=0)
    assert res["solved"] is True
    assert res["novel_mechanics_seen"] >= 1
    assert agent.prior.win_cls_hits.get("A5", 0) >= 1


def test_unified_fast_spine_dark_organs_and_multifile_repo_repair(tmp_path):
    """Verify UnifiedFastSpine wires BM25, ProducerLineage, InducedEditBasis, DBSP-PPR, and Harbor bundle."""
    import tarfile, io
    from canonical.swe_kernel.unified_fast_spine_v1 import UnifiedFastSpine, self_check as spine_self_check
    from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin
    from canonical.runtime.harbor_swe_zero_model_agent_v1 import _build_kernel_tar_gz

    sc = spine_self_check()
    assert sc["pass"] is True
    assert sc["core_organs_loaded"] is True
    assert sc["repair_method"] in ("MINIMAL_SUBTREE_TRANSFER_COW_V1", "INDUCED_EDIT_BASIS_COW_V1")
    assert sc["splice_method"] == "DUAL_PROGRAM_SPLICING_COW_V1"

    # Multi-file repo (>5 files, proving the old <=3-file ceiling is lifted!)
    for i in range(6):
        (tmp_path / f"helper_{i}.py").write_text(f"def helper_{i}(x):\n    return x + {i}\n", encoding="utf-8")
    (tmp_path / "quota_guard.py").write_text(
        "def allows_quota(used, limit):\n    return used <= limit\n",
        encoding="utf-8",
    )
    (tmp_path / "test_quota_guard.py").write_text(
        "from quota_guard import allows_quota\n"
        "assert allows_quota(1, 5) is True\n"
        "assert allows_quota(5, 5) is False\n"
        "assert allows_quota(6, 5) is False\n",
        encoding="utf-8",
    )

    bus = Wave53To54UnifiedCapabilityBusMixin()
    loc = bus.unified_fast_localize_repo(tmp_path, "allows_quota off-by-one when used equals limit")
    assert loc["source_files"][0]["path"] == "quota_guard.py"

    rep = bus.unified_fast_repair_repo(tmp_path, "allows_quota off-by-one when used equals limit")
    assert rep["repaired"] is True
    assert rep["patched_file"] == "quota_guard.py"
    assert "used < limit" in rep["patched_files"]["quota_guard.py"]

    # Negative control: weak test must be refused by FastCoWVerifier lie detector
    bad_dir = tmp_path / "weak_repo"
    bad_dir.mkdir()
    (bad_dir / "mod.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (bad_dir / "test_mod.py").write_text("from mod import add\nassert True\n", encoding="utf-8")
    weak_rep = UnifiedFastSpine().repair_repo_fast(bad_dir, "add returns wrong sum")
    assert weak_rep["repaired"] is False

    # Hybrid DominoMemory + DBSPBiTemporalPPRMemory via bus
    hyb = bus.unified_fast_hybrid_memory(
        [
            {"dia_id": "D1:1", "speaker": "Maya", "text": "Maya visited Cobalt Harbor yesterday."},
            {"dia_id": "D1:2", "speaker": "Liam", "text": "Cobalt Harbor hosts the Silver Beacon."},
            {"dia_id": "D1:3", "speaker": "Maya", "text": "Rainy afternoon tea."},
        ],
        "Which beacon is linked to Maya?",
        top_k=3,
    )
    assert "D1:2" in hyb["dia_ids"]

    # Harbor container tarball must bundle UnifiedFastSpine + its pure-stdlib dark jewels
    tar_bytes = _build_kernel_tar_gz()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        names = set(tf.getnames())
    for req in (
        "canonical/swe_kernel/unified_fast_spine_v1.py",
        "canonical/swe_kernel/bm25_code_localizer_v1.py",
        "canonical/swe_kernel/producer_lineage_graph_v1.py",
        "canonical/swe_kernel/guarded_meaning_ir_v1.py",
        "canonical/swe_kernel/induced_edit_basis_v1.py",
        "canonical/swe_kernel/minimal_subtree_transfer_v1.py",
    ):
        assert req in names


def test_strike1_plotkin_lgg_subtree_transfer_self_play_and_dual_splicing():
    """Verify Plotkin LGG minimal-subtree origination, zero-LLM self-play, and multi-bug dual splicing."""
    from canonical.swe_kernel.minimal_subtree_transfer_v1 import MinimalSubtreeTransferStore
    from canonical.swe_kernel.unified_fast_spine_v1 import UnifiedFastSpine

    # 1. Plotkin LGG shared-subexpr lifting transfers `t.cast(T, expr) -> expr` across completely unseen names!
    store = MinimalSubtreeTransferStore(allow_one_scope_hole=True)
    donor_b = "def wrap(env):\n    return t.cast('WSGIResponse', self.get_response(env))\n"
    donor_a = "def wrap(env):\n    return self.get_response(env)\n"
    assert store.learn_from_file_pair(donor_b, donor_a) >= 1

    unseen_src = "def make_fn(f):\n    return t.cast(F, new_func)\n"
    proposals = store.propose_source_rewrites(unseen_src, max_candidates=20)
    assert any("return new_func" in p["source"] for p in proposals)

    # 2. Zero-LLM self-play warm start learns inverse rules directly from green code
    spine = UnifiedFastSpine()
    green = "def clip_hi(x, hi):\n    return x < hi\n"
    green_test = "assert clip_hi(1, 2) is True\nassert clip_hi(2, 2) is False\n"
    sp = spine.self_play_warm_start(green, green_test, max_mutants=4)
    assert sp["mutants_learned"] >= 1 and sp["model_calls"] == 0

    # 3. Assertion-Granular Dual-Program Splicing solves a 2-bug function no single edit passes!
    two_bug = (
        "def shift_pair(x, y):\n"
        "    a = x - 1\n"
        "    b = y - 1\n"
        "    return (a, b)\n"
    )
    two_test = (
        "assert shift_pair(5, 10)[0] == 6\n"
        "assert shift_pair(5, 10)[1] == 11\n"
        "assert shift_pair(0, 0) == (1, 1)\n"
    )
    res = spine.repair_function_fast(two_bug, two_test, max_candidates=60)
    assert res["fixed"] is True
    assert res["method"] == "DUAL_PROGRAM_SPLICING_COW_V1"


def test_strike2_arc3_v4_border_only_hud_never_masks_interior_objects():
    """Verify ARC-AGI-3 V4 restricts step-counter HUD masking strictly to outer border strips."""
    import numpy as np
    from canonical.swe_kernel.minimal_arc3_agent_v1 import GamePrior

    gp = GamePrior((16, 16))
    f0 = np.zeros((16, 16), dtype=np.int32)
    f1 = f0.copy()
    f1[8, 8] = 5  # 1-pixel interior switch toggle — MUST NOT be masked as HUD!
    f1[8, 9] = 5
    raw_px, world_px, grew = gp.observe_diff(f0, f1)
    assert raw_px == 2 and world_px == 2 and grew is False
    assert bool(gp.hud_mask[8, 8]) is False

    # Outer border 1-px step-counter tick SHOULD be detected as HUD!
    f2 = f0.copy()
    f2[0, 5] = 7
    raw_px2, world_px2, grew2 = gp.observe_diff(f0, f2)
    assert raw_px2 == 1 and world_px2 == 0 and grew2 is True
    assert bool(gp.hud_mask[0, 5]) is True


def test_strike3_and_4_continual_memory_drift_retraction_and_unified_model_wiring():
    """Verify InstantContinualMemory (0% stale leakage, 1-counterexample narrowing, CU transfer) on UnifiedModel."""
    from canonical.runtime.brain_unified_model_v1 import UnifiedModel, load_model

    um = UnifiedModel(load_model())
    cm = um.unified_fast_continual_memory()

    # 1. Bi-temporal schema migration: 0% stale leakage on current, 100% exact t=1 time-travel
    cm.assert_fact("auth_svc", "port", "8080", t_valid=1, supersede=True)
    cm.assert_fact("auth_svc", "port", "9090", t_valid=2, supersede=True)
    assert cm.current_slot_values("auth_svc", "port") == ["9090"]
    assert cm.current_slot_values("auth_svc", "port", t_valid=1) == ["8080"]

    # 2. Single-counterexample condition narrowing + clean deletion
    cmd = ["vacuum_tool", "db.sqlite"]
    r_pos = cm.observe_action_outcome(cmd, ["has_tool", "db_present", "writable"], succeeded=True)
    assert r_pos["condition_status"] == "OPEN__ONE_SUCCESS_BUYS_NO_CONDITION"
    cm.observe_action_outcome(cmd, ["has_tool", "db_present"], succeeded=False)
    assert cm.check_action_condition(cmd, ["has_tool", "db_present", "writable"])["applies"] is True
    assert cm.check_action_condition(cmd, ["has_tool", "db_present"])["applies"] is False
    assert cm.delete_action_condition(cmd) is True
    assert cm.check_action_condition(cmd, ["has_tool", "db_present", "writable"])["applies"] is False

    # 3. Cross-environment hole-abstracted CU procedure transfer + single-counterexample refutation
    proc = cm.induce_cu_procedure(
        domain="cli",
        goal_kind="diff_export",
        concrete_steps=[{"cmd": ["git", "-C", "/tmp/ws1/repo", "diff"], "out": "/tmp/ws1/p.diff"}],
        hole_bindings={"__REPO_DIR__": "/tmp/ws1/repo", "__OUTPUT_PATH__": "/tmp/ws1/p.diff"},
        env_observables=["domain:cli", "has_git", "clean_tree"],
    )
    assert proc is not None
    recalled = cm.recall_cu_procedures(
        domain="cli",
        goal_kind="diff_export",
        env_observables=["domain:cli", "has_git", "clean_tree"],
        hole_bindings={"__REPO_DIR__": "/opt/unseen/repo", "__OUTPUT_PATH__": "/opt/unseen/p.diff"},
    )
    assert len(recalled) == 1 and recalled[0]["steps"][0]["cmd"][2] == "/opt/unseen/repo"
    cm.refute_cu_procedure(proc["procedure_id"], failed_env_observables=["domain:cli", "has_git"])
    assert cm.recall_cu_procedures(
        domain="cli",
        goal_kind="diff_export",
        env_observables=["domain:cli", "has_git"],
        hole_bindings={"__REPO_DIR__": "/opt/unseen/repo", "__OUTPUT_PATH__": "/opt/unseen/p.diff"},
    ) == []

    # 4. Awakened DARK organs directly reachable from UnifiedModel front door (0 LLM calls)
    fl = um.unified_fast_four_levers(64, sym_group_size=4, demo_bits=2.0)
    assert fl["quotient_prior_bits"] == 4.0 and fl["remaining_bits"] == 2.0 and fl["k3_model_calls"] == 0
    st = um.minimal_core_status()
    assert st["ok"] is True and st["unified_fast_spine"]["wired_organ_count"] >= 40


def test_master_plan_strikes_a_through_e_end_to_end():
    """Verify Strikes A (Dark Registry), B (ARC-3 V5 ObjectWorldModel), C (E-Stitch + Polyglot CST),
    D (2048-bit HDC + PathHD KG + Temporal Resolution + Speaker-Swap Abstention), and
    E (CompiledWorkflowGraph + Tsetlin Guards + Failure-Node Recovery Grafting)."""
    import numpy as np
    from canonical.runtime.brain_unified_model_v1 import UnifiedModel, load_model
    from canonical.swe_kernel.hdc_semantic_engine_v1 import (
        MaxSATTsetlinClassifier,
        PathHDKnowledgeGraph,
        RandomIndexingEncoder,
    )
    from canonical.swe_kernel.minimal_arc3_agent_v1 import ObjectWorldModel, _extract_diff_components
    from canonical.swe_kernel.minimal_subtree_transfer_v1 import MinimalSubtreeTransferStore

    um = UnifiedModel(load_model())

    # --- Strike A: DarkCapabilityRegistry (29/29 stdlib dark engines verified + live invoke) ---
    probe = um.unified_fast_probe_dark_engines()
    assert probe["stdlib_engines_verified"] == probe["stdlib_engines_total"] == 29
    assert probe["k3_model_calls"] == 0
    ans_shape = um.unified_fast_invoke_dark_engine("answer_shape", "When did Alice move to Austin?")
    assert ans_shape["engine"] == "answer_shape" and ans_shape["model_calls"] == 0

    # --- Strike B: ARC-AGI-3 V5 ObjectWorldModel (connected-component diff + avatar/wall learning) ---
    f0 = np.zeros((20, 20), dtype=np.int32)
    f0[8:10, 6:8] = 3      # avatar color 3
    f0[8:10, 10:12] = 9    # wall color 9 two pixels right of f1
    f1 = np.zeros((20, 20), dtype=np.int32)
    f1[8:10, 8:10] = 3     # avatar stepped +2 right
    f1[8:10, 10:12] = 9
    hud = np.zeros((20, 20), dtype=bool)
    diff = f0 != f1
    comps = _extract_diff_components(f0, diff, 8, 9, 6, 9)
    assert len(comps) >= 1 and any(c["color"] == 3 for c in comps)
    owm = ObjectWorldModel()
    owm.observe_move("ACTION4", "s0", "s1", f0, f1, hud, moved=True)
    assert owm.avatar_color == 3 and owm.move_step.get("ACTION4") == (2, 0)
    # Two bumps into color-9 barrier teach solid-wall physics -> predicts blocked on ACTION4!
    owm.observe_move("ACTION4", "s1", "s1", f1, f1, hud, moved=False)
    owm.observe_move("ACTION4", "s1", "s1", f1, f1, hud, moved=False)
    assert 9 in owm.wall_colors(thresh=2)
    assert owm.is_predicted_wall("ACTION4", f1, thresh=2) is True

    # --- Strike C: E-Stitch Algebraic Equivalence Transfer + Polyglot CST 1-Shot Transfer ---
    store = MinimalSubtreeTransferStore(allow_one_scope_hole=True)
    assert store.learn_from_file_pair("def f(a, b):\n    return a < b\n", "def f(a, b):\n    return a <= b\n") >= 1
    store.compress_library_estitch()
    # Cross-syntax De Morgan transfer: `not (x >= y)` is algebraically equivalent to `x < y` -> rewrites to `x <= y`!
    e_props = store.propose_source_rewrites("def g(x, y):\n    return not (x >= y)\n", max_candidates=12)
    assert any("x <= y" in p["source"] for p in e_props)

    sk_js = um.unified_fast_learn_polyglot_skill(
        "m.js",
        "function maxVal(a, b) { if (a < b) { return a; } return b; }",
        "function maxVal(a, b) { if (a > b) { return a; } return b; }",
    )
    assert sk_js["learned"] is True and sk_js["language"] == "js"
    js_cands = um.unified_fast_spine().apply_polyglot_skills(
        "pick.js", "function pick(x, y) { if (x < y) { return x; } return y; }"
    )
    assert any("x > y" in c["source"] for c in js_cands)

    # --- Strike D: Zero-weight 2048-bit HDC + PathHD KG + Temporal Resolution + Adversarial Abstention ---
    enc = RandomIndexingEncoder()
    enc.observe_documents([
        "database timeout error occurred in postgres connection pool",
        "postgres connection pool hit database timeout limit",
    ])
    assert enc.similarity("parse_url_query", "parsing_urls_queries") > 0.30
    assert enc.similarity("database timeout error", "postgres connection pool") > enc.similarity(
        "database timeout error", "orchard apple harvest basket"
    ) + 0.08

    kg = PathHDKnowledgeGraph(enc)
    kg.ingest_turn("I live in Seattle.", speaker="Alice", turn_idx=1, source_id="D1:1")
    kg.ingest_turn("I moved to Austin last month.", speaker="Alice", turn_idx=2, source_id="D1:2")
    now_hits = kg.query_facts("Where does Alice currently live?", top_k=3)
    assert now_hits and "austin" in now_hits[0][1].obj.lower()

    conv = {
        "session_1_date_time": "1:56 pm on 8 May, 2023",
        "session_1": [
            {"dia_id": "D1:1", "speaker": "Caroline", "text": "I went to the LGBTQ support group yesterday!"},
            {"dia_id": "D1:2", "speaker": "Melanie", "text": "Awesome! I ran a charity marathon and realized self-care is vital."},
        ],
    }
    qa_time = um.unified_fast_answer_hybrid_memory(conv, "When did Caroline go to the LGBTQ support group?")
    assert qa_time["abstained"] is False and "7 May 2023" in qa_time["answer"]
    # Adversarial speaker-swap question MUST abstain cleanly!
    qa_adv = um.unified_fast_answer_hybrid_memory(conv, "What did Caroline realize after her charity marathon?")
    assert qa_adv["abstained"] is True

    # MaxSAT Tsetlin Classifier: learn + 1-counterexample refutation
    tc = MaxSATTsetlinClassifier(["has_tb", "is_go", "writable"])
    tc.fit([tc.encode_features(["has_tb", "writable"])], [tc.encode_features(["is_go"])])
    assert tc.predict(tc.encode_features(["has_tb", "writable"])) is True
    assert tc.predict(tc.encode_features(["is_go"])) is False

    # --- Strike E: CompiledWorkflowGraph (hole abstraction + Tsetlin guard + recovery grafting) ---
    execs = {
        "load": lambda st, p: st.update({"vals": list(st["db"][p["tbl"]])}) or True,
        "clean": lambda st, p: (
            False if (st.get("fault") and not st.get("fixed"))
            else (st.update({"vals": [v for v in st["vals"] if v > 0]}) or True)
        ),
        "heal": lambda st, p: st.update({"vals": [abs(v) for v in st["vals"] if v != 0], "fixed": True}) or True,
        "verify": lambda st, p: (len(st["vals"]) > 0 and (st.update({"sum": sum(st["vals"])}) or True)),
    }
    um.unified_fast_compile_workflow_graph(
        "wf_test_v1",
        [
            {"kind": "DataOp", "op": "load", "params": {"tbl": "jan"}},
            {"kind": "DataOp", "op": "clean", "params": {}},
            {"kind": "CheckOp", "op": "verify", "params": {}},
        ],
        hole_bindings={"tbl": "jan"},
        positive_env_features=[["rw_mode"]],
        negative_env_features=[["ro_mode"]],
    )
    st_ok = {"db": {"dec": [3, -1, 7]}}
    r_ok = um.unified_fast_execute_workflow_graph("wf_test_v1", st_ok, execs, bindings={"tbl": "dec"}, env_features=["rw_mode"])
    assert r_ok["succeeded"] is True and st_ok["sum"] == 10
    r_blk = um.unified_fast_execute_workflow_graph("wf_test_v1", {"db": {"dec": [1]}}, execs, bindings={"tbl": "dec"}, env_features=["ro_mode"])
    assert r_blk["succeeded"] is False and r_blk["reason"] == "GUARD_REJECTED"
    st_f = {"db": {"dec": [3, -2, 5]}, "fault": True}
    r_f = um.unified_fast_execute_workflow_graph("wf_test_v1", st_f, execs, bindings={"tbl": "dec"}, env_features=["rw_mode"])
    assert r_f["succeeded"] is False and r_f["failed_node_idx"] == 1
    um.unified_fast_graft_workflow_recovery("wf_test_v1", 1, [{"kind": "DataOp", "op": "heal", "params": {}}])
    st_h = {"db": {"dec": [3, -2, 5]}, "fault": True}
    r_h = um.unified_fast_execute_workflow_graph("wf_test_v1", st_h, execs, bindings={"tbl": "dec"}, env_features=["rw_mode"])
    assert r_h["succeeded"] is True and st_h["sum"] == 10




