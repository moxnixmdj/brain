"""End-to-end zero-mock tests for Wave 43 & Wave 44 Frontier Leapfrog
(`wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py`), wired directly into
`UnifiedModel`, `Creature`, and `unified_hidden_capability_federation_v1`
(K3=0 default, $0 spend)."""

from __future__ import annotations

import pathlib
import subprocess
import tempfile

from canonical.runtime.brain_unified_model_v1 import load_unified_model
from canonical.runtime.creature_runtime_v1 import boot as boot_creature
from canonical.runtime.osworld_v21_generic_policy_v1 import COMP_NS, STATE_NS
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)
from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import (
    ALL_W40_W44_AWAKENED_DARK_MODULES,
    WAVE43_44_AWAKENED_DARK_MODULES,
)


def test_w43_44_awakened_dark_matter_inventory_complete() -> None:
    model = load_unified_model()
    inv = model.wave43_44_awakened_inventory()
    assert inv["wave43_44_declared"] == 23
    assert inv["wave43_44_present"] == 23
    assert inv["waves_40_to_44_total_declared"] == len(ALL_W40_W44_AWAKENED_DARK_MODULES) == 67
    assert inv["waves_40_to_44_total_present"] == 67
    assert inv["all_present"] is True
    assert inv["model_calls"] == 0
    assert len(WAVE43_44_AWAKENED_DARK_MODULES) == 23


def test_w43_git_history_seeding_online_learning_and_fixedbench_abstention() -> None:
    model = load_unified_model()

    # 1. FixedBench gate: already-passing function MUST abstain and touch 0 bytes
    clean_src = "def compute_margin(revenue, cost):\n    return revenue - cost\n"
    fb = model.git_history_seeded_repair(
        "FIXEDBENCH_GATE",
        {
            "source": clean_src,
            "fn_name": "compute_margin",
            "test_cases": [((100, 40), 60), ((50, 20), 30)],
        },
    )
    assert fb["pass"] is True
    assert fb["already_passing"] is True
    assert fb["action"] == "ABSTAIN__ALREADY_PASSING_FIXEDBENCH"
    assert fb["bytes_modified"] == 0
    assert fb["model_calls"] == 0

    # 2. Mine a real temporary git repo strictly prior to HEAD at $0.00
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@brain.local"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Brain Test"], cwd=repo, check=True)
        (repo / "calc.py").write_text("def clamp(x):\n    return x\n", encoding="utf-8")
        subprocess.run(["git", "add", "calc.py"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
        (repo / "calc.py").write_text(
            "def clamp(x):\n    if x is None:\n        return 0\n    if x < 0:\n        return 0\n    return x\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "calc.py"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "guard none and negative"], cwd=repo, check=True)

        mined = model.git_history_seeded_repair(
            "MINE_REPO_HISTORY",
            {
                "repo_path": repo,
                "base_commit": "HEAD",
                "commit_limit": 20,
                "target_source": "def scale(val):\n    return val * 2\n",
            },
        )
        assert mined["pass"] is True
        assert mined["mined_template_count"] >= 1
        assert mined["model_calls"] == 0

    # 3. Online alpha-canonical & operator-swap generalization on renamed unseen function
    buggy_unseen = "def compute_margin(revenue, cost):\n    return revenue + cost\n"
    prior_demo = (
        "demo_sub",
        "def delta(a, b):\n    return a + b\n",
        "def delta(a, b):\n    return a - b\n",
    )
    repaired = model.git_history_seeded_repair(
        "REPAIR_WITH_HISTORY",
        {
            "buggy_source": buggy_unseen,
            "fn_name": "compute_margin",
            "test_cases": [((100, 40), 60), ((50, 20), 30), ((10, 10), 0)],
            "prior_verified_demos": [prior_demo],
            "enforce_input_dependency_gate": True,
        },
    )
    assert repaired["pass"] is True
    assert repaired["abstained"] is False
    assert "revenue - cost" in repaired["repaired_source"]
    assert repaired["model_calls"] == 0


def test_w43_causal_dual_slice_constant_hole_cegis_and_anti_slop_gate() -> None:
    model = load_unified_model()

    # 1. Cross-file CausalDataFlowGraph dual-slicing + truthiness guard detection
    files = {
        "pricing.py": (
            "def normalize(val):\n"
            "    if val:\n"
            "        return val\n"
            "    return -1\n"
        ),
        "checkout.py": (
            "from pricing import normalize\n"
            "def total(amount):\n"
            "    base = normalize(amount)\n"
            "    return base * 2\n"
        ),
    }
    sliced = model.trace_literal_causal_slice_gate(
        "CAUSAL_DUAL_SLICE",
        {
            "files": files,
            "error_file": "pricing.py",
            "error_line": 2,
            "target_source": files["pricing.py"],
        },
    )
    assert sliced["pass"] is True
    assert sliced["graph_node_count"] >= 2
    assert len(sliced["boolean_coercion_guards"]) >= 1
    assert sliced["model_calls"] == 0

    # 2. Constant-hole CEGIS repairs a regex literal missing '-' inside character class
    regex_bug = (
        "import re\n"
        "def is_int_token(s):\n"
        "    return bool(re.match(r'^[0-9]+$', s))\n"
    )
    cegis = model.trace_literal_causal_slice_gate(
        "CONSTANT_HOLE_CEGIS",
        {
            "buggy_source": regex_bug,
            "fn_name": "is_int_token",
            "test_cases": [(("42",), True), (("-7",), True), (("abc",), False)],
            "extra_chars": "-",
        },
    )
    assert cegis["pass"] is True
    assert "-" in str(cegis["new_value"])
    assert cegis["model_calls"] == 0

    # 3. Anti-slop input-dependency gate blocks reward-hacking constant stub
    orig = "def bill(subtotal, discount):\n    return subtotal + discount\n"
    good_fix = "def bill(subtotal, discount):\n    return subtotal - discount\n"
    slop_cheat = "def bill(subtotal, discount):\n    return 80\n"
    ok_gate = model.trace_literal_causal_slice_gate("ANTI_SLOP_GATE", {"before_source": orig, "after_source": good_fix})
    bad_gate = model.trace_literal_causal_slice_gate("ANTI_SLOP_GATE", {"before_source": orig, "after_source": slop_cheat})
    assert ok_gate["admitted"] is True
    assert bad_gate["admitted"] is False
    assert "PATCH_STOPPED_READING_ITS_INPUTS" in bad_gate["structural_gate"]["reason"]


def test_w43_cow_contrastive_minimax_pinning_and_filing_key_diagnostics() -> None:
    model = load_unified_model()

    # Hidden precondition: auth=True AND signed=True (ignores verbose)
    def hidden_oracle(st: dict[str, bool]) -> bool:
        return bool(st["auth"] and st["signed"])

    res = model.cow_contrastive_minimax_op(
        "CONTRASTIVE_MINIMAX_PIN",
        {
            "feature_names": ["auth", "signed", "verbose"],
            "initial_state": {"auth": True, "signed": True, "verbose": False},
            "oracle": hidden_oracle,
            "max_queries": 12,
        },
    )
    assert res["pass"] is True
    assert res["pinned"] is True
    assert res["after_single_demo_survivors"] > 1  # 1 passive demo CANNOT pin it!
    assert res["final_survivor_count"] == 1
    assert sorted(tuple(x) for x in res["pinned_guard"]) == [("auth", True), ("signed", True)]
    assert res["model_calls"] == 0

    # Filing-key collision diagnostic
    diag = model.cow_contrastive_minimax_op(
        "DIAGNOSE_FILING_KEYS",
        {
            "feature_keys": {"task_a": "k1", "task_b": "k1", "task_c": "k2"},
            "winners": {"task_a": ["p1"], "task_b": ["p2"], "task_c": ["p3"]},
            "goal_text": "replace text in document",
        },
    )
    assert diag["pass"] is True
    assert diag["filing_key_score"]["collisions"] == 1
    assert diag["filing_key_score"]["answerable"] == 1


def test_w44_meme_dbsp_cascade_deletion_absence_openviking_deltamem_memrl() -> None:
    model = load_unified_model()

    suite = model.meme_dbsp_memory_op("RUN_MEME_SUITE")
    assert suite["pass"] is True
    assert suite["overall_accuracy"] == 1.0
    assert suite["cascade_accuracy"] == 1.0
    assert suite["absence_accuracy"] == 1.0
    assert suite["task_scores"] == {"ER": 1.0, "Agg": 1.0, "Tr": 1.0, "Del": 1.0, "Cas": 1.0, "Abs": 1.0}
    assert suite["deltamem_memrl_verified"] is True
    assert suite["model_calls"] == 0

    # Verify OpenViking progressive context disclosure tiers (L0 < L1 < L2)
    with tempfile.TemporaryDirectory() as tmp:
        eng = model._get_meme_memory_engine(root_dir=tmp)
        eng.assert_fact("budget", 500, valid_from=1, note="Q4 allocation")
        q0 = eng.query_entity("budget", tier="L0")
        q1 = eng.query_entity("budget", tier="L1")
        q2 = eng.query_entity("budget", tier="L2")
        assert len(q0["context_view"]) < len(q1["context_view"]) < len(q2["context_view"])


def test_w44_webmcp_document_model_context_and_osworld_a11y_hcu() -> None:
    model = load_unified_model()

    # 1. Chrome 150+ WebMCP compiler lifts declarative HTML + XHR into document.modelContext
    html_doc = (
        '<form toolname="create_invoice" tooldescription="Create a customer invoice" method="POST" action="/api/invoices">'
        '<input name="customer" type="text" required />'
        '<input name="amount" type="number" required />'
        '</form>'
    )
    compiled = model.webmcp_osworld_hcu_op(
        "COMPILE_WEBMCP",
        {
            "html_source": html_doc,
            "observed_xhr_calls": [{"method": "POST", "url": "https://erp.local/api/export", "json_body": {"fmt": "csv"}}],
            "page_origin": "https://erp.local",
        },
    )
    assert compiled["pass"] is True
    assert compiled["chrome_150_compliant"] is True
    assert "document.modelContext ?? navigator.modelContext" in compiled["polyfill_js"]
    assert "provideContext" not in compiled["polyfill_js"]
    assert compiled["tool_count"] == 2

    # 2. Channel-0 WebMCP routing (zero pixels!)
    ch0 = model.webmcp_osworld_hcu_op(
        "ROUTE_OSWORLD_HCU",
        {
            "instruction": "create customer invoice",
            "webmcp_tools": compiled["tools"],
        },
    )
    assert ch0["selected_channel"] == "CHANNEL_0_WEBMCP_DOCUMENT_MODEL_CONTEXT"
    assert ch0["pixel_vision_required"] is False

    # 3. Channel-1 OSWorld 2.1 AT-SPI A11y XML -> deterministic PyAutoGUI click (zero pixels!)
    a11y_xml = (
        f'<desktop xmlns:st="{STATE_NS}" xmlns:cp="{COMP_NS}">'
        '<application name="LibreOffice Calc">'
        '<push-button name="Export PDF" st:visible="true" st:showing="true" '
        'cp:screencoord="(400, 300)" cp:size="(100, 40)" />'
        "</application></desktop>"
    )
    ch1 = model.webmcp_osworld_hcu_op(
        "ROUTE_OSWORLD_HCU",
        {
            "instruction": "Export PDF from spreadsheet",
            "a11y_xml": a11y_xml,
        },
    )
    assert ch1["selected_channel"] == "CHANNEL_1_OSWORLD_STRUCTURAL_A11Y"
    assert ch1["pixel_vision_required"] is False
    assert ch1["compiled_pyautogui"] == "pyautogui.click(x=450, y=320, button='left')"


def test_w44_nested_cms_skillrl_gea_and_rqgm_selective_erasure() -> None:
    model = load_unified_model()

    # 1. Nested Learning CMS multi-frequency clock protection
    r_anchor1 = model.nested_skillrl_rqgm_gea_op("CMS_UPDATE", {"band": "anchor_invariant", "key": "k3_zero", "value": True, "tick": 1})
    r_anchor2 = model.nested_skillrl_rqgm_gea_op("CMS_UPDATE", {"band": "anchor_invariant", "key": "k3_zero", "value": False, "tick": 2})
    r_sleep_wait = model.nested_skillrl_rqgm_gea_op("CMS_UPDATE", {"band": "sleep", "key": "consolidated", "value": "v1", "tick": 5})
    r_sleep_ok = model.nested_skillrl_rqgm_gea_op("CMS_UPDATE", {"band": "sleep", "key": "consolidated", "value": "v1", "tick": 16})
    assert r_anchor1["admitted"] is True
    assert r_anchor2["admitted"] is False
    assert r_anchor2["reason"] == "ANCHOR_INVARIANT_PROTECTED_FROM_OVERWRITE"
    assert r_sleep_wait["admitted"] is False
    assert r_sleep_ok["admitted"] is True

    # 2. SkillRL differential success + counterfactual-failure distillation
    sk = model.nested_skillrl_rqgm_gea_op(
        "SKILLRL_DISTILL",
        {
            "trajectories": [
                {
                    "goal": "fix boolean guard",
                    "success": True,
                    "steps": [
                        {"action": "trace_run", "backtrack": False, "log": "x" * 200},
                        {"action": "bad_try", "backtrack": True, "log": "y" * 200},
                        {"action": "rewrite_is_not_none", "backtrack": False, "log": "z" * 200},
                    ],
                },
                {
                    "goal": "fix boolean guard",
                    "success": False,
                    "steps": [{"action": "return_constant", "log": "w" * 300}],
                    "failure_reason": "PATCH_STOPPED_READING_ITS_INPUTS",
                    "counterfactual_fix": "Preserve all original function parameters",
                },
            ]
        },
    )
    assert sk["pass"] is True
    assert sk["added_skills"] == 1
    assert sk["added_counterfactual_failure_lessons"] == 1
    assert sk["compression_ratio"] > 2.0

    # 3. GEA group evolution merges complementary solved tasks
    gea = model.nested_skillrl_rqgm_gea_op(
        "GEA_EVOLVE",
        {
            "agents": [
                {"agent_id": "a1", "score": 0.6, "solved_tasks": ["t1", "t2"], "skills": ["s1"]},
                {"agent_id": "a2", "score": 0.6, "solved_tasks": ["t2", "t3", "t4"], "skills": ["s2"]},
            ],
            "group_size": 2,
        },
    )
    assert gea["pass"] is True
    assert gea["offspring_solved_count"] == 4
    assert gea["synergy_gain"] == 1

    # 4. RQGM anchor-gated evaluator upgrade with selective utility erasure
    rq_rej = model.nested_skillrl_rqgm_gea_op("RQGM_CO_EVOLVE", {"current_anchor_accuracy": 0.90, "candidate_anchor_accuracy": 0.88})
    assert rq_rej["evaluator_upgraded"] is False
    rq_acc = model.nested_skillrl_rqgm_gea_op("RQGM_CO_EVOLVE", {"current_anchor_accuracy": 0.90, "candidate_anchor_accuracy": 0.95})
    assert rq_acc["evaluator_upgraded"] is True
    assert len(rq_acc["selectively_erased_utility_ids"]) >= 1
    assert rq_acc["lineage_preserved_count"] >= 1


def test_w43_44_federation_concept_resolution_and_creature_parity() -> None:
    # 1. Cross-disciplinary concept resolution for unfamiliar frontier names
    c_meme = resolve_cross_disciplinary_concept("meme benchmark dependency cascade absence")
    assert any("LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY" in str(m) for m in c_meme["matched_families"])

    c_webmcp = resolve_cross_disciplinary_concept("chrome 150 webmcp document.modelContext")
    assert any("LEAPFROG_W44_WEBMCP_GUI_ROOM_OSWORLD_HCU" in str(m) for m in c_webmcp["matched_families"])

    c_hist = resolve_cross_disciplinary_concept("fixedbench abstention arise causal dual slicing")
    assert any("LEAPFROG_W43_GIT_HISTORY_SEEDED_REPAIR" in str(m) for m in c_hist["matched_families"])

    # 2. Federated dispatch parity
    fed = run_federated_engine("LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY", {"operation": "RUN_MEME_SUITE"})
    assert fed["pass"] is True
    assert fed["cascade_accuracy"] == 1.0
    assert fed["absence_accuracy"] == 1.0

    # 3. Creature runtime end-to-end parity
    with tempfile.TemporaryDirectory() as tmp:
        creature = boot_creature(tmp, identity="wave43-44-test")
        cr_meme = creature.meme_dbsp_memory_op("RUN_MEME_SUITE")
        assert cr_meme["pass"] is True
        assert cr_meme["overall_accuracy"] == 1.0
        cr_webmcp = creature.webmcp_osworld_hcu_op(
            "COMPILE_WEBMCP",
            {"html_source": '<form toolname="ping"><input name="x" /></form>'},
        )
        assert cr_webmcp["pass"] is True
        assert cr_webmcp["chrome_150_compliant"] is True
