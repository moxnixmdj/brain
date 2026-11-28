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

