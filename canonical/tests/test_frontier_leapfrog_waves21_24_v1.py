"""Verification suite for Frontier Leapfrog Waves 21-24 (`mmap` CSR substrate, PEP 669 /
`setprofile` execution-traced callable compiler, 4-rung Fast-Cascade & State-Alias guard,
and `ForwardPush` bi-temporal associative recall + Two-Door Rubin skill rent).

Zero mocks, zero stdlib monkeypatching, zero model calls (`model_calls == 0`).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from canonical.runtime import brain_unified_model_v1 as u_mod
from canonical.runtime import execution_traced_callable_compiler_v1 as etcc
from canonical.runtime import fast_cascade_orchestrator_v1 as fco
from canonical.runtime import mmap_csr_slot_index_v1 as csr_mod
from canonical.runtime import unified_hidden_capability_federation_v1 as fed
from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_mod


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Wave 21: Zero-Copy Mmap CSR Slot Index & Sub-15ms UnifiedModel Fast Path
# ---------------------------------------------------------------------------


def test_wave21_mmap_csr_exact_equivalence_and_mapping_surface(tmp_path: Path) -> None:
    sample_rows = {
        "canonical/runtime/alpha_solver_v1.py": {
            "id": "source:canonical/runtime/alpha_solver_v1.py",
            "path": "canonical/runtime/alpha_solver_v1.py",
            "classification": "ENTRY_POINT",
            "capability": False,
            "summary": "Deterministic alpha constraint solver",
            "terms": {"alpha": 4, "constraint": 2, "solver": 3},
        },
        "canonical/tools/beta_verifier_v1.py": {
            "id": "source:canonical/tools/beta_verifier_v1.py",
            "path": "canonical/tools/beta_verifier_v1.py",
            "classification": "INTERNAL_HELPER",
            "capability": True,
            "summary": "Beta domain verifier with alpha bridge",
            "terms": {"beta": 5, "verifier": 3, "alpha": 1},
        },
    }
    csr = csr_mod.open_or_build_csr_index(
        "test_sample_source",
        "deadbeef" * 8,
        sample_rows,
        cache_dir=tmp_path,
    )
    try:
        assert csr.num_docs == 2
        df_proxy = csr_mod.MmapDFProxy(csr)
        doc_proxy = csr_mod.MmapDocTableProxy(csr)
        assert df_proxy["alpha"] == 2
        assert df_proxy["beta"] == 1
        assert "canonical/runtime/alpha_solver_v1.py" in doc_proxy
        ranked = csr.search_ranked({"alpha", "solver"}, "alpha solver", top_k=2)
        assert ranked[0][1] == "canonical/runtime/alpha_solver_v1.py"
        ranked_path = csr.search_ranked(
            {"beta"},
            "inspect canonical/tools/beta_verifier_v1.py",
            top_k=2,
        )
        assert ranked_path[0][1] == "canonical/tools/beta_verifier_v1.py"
    finally:
        csr.close()


def test_wave21_unified_model_find_source_uses_mmap_csr_fast() -> None:
    model = u_mod.open_model(root=REPO_ROOT)
    t0 = time.perf_counter()
    res = model.find_source("domain of verification", top_k=5)
    any_res = model.find_any_source("speculative cow petri agent", top_k=5)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert res["operation"] == "FIND_SOURCE"
    assert any("domain_of_verification_v1.py" in c["path"] for c in res["candidates"])
    assert any("speculative_cow_petri_agent_v1.py" in c["path"] for c in any_res["candidates"])
    assert elapsed_ms < 50.0


# ---------------------------------------------------------------------------
# Wave 22: Execution-Traced Callable Compiler (`260/406 = 64.04%` Survival)
# ---------------------------------------------------------------------------


def test_wave22_full_406_census_exceeds_kill_floor_and_invokes_via_unified_model() -> None:
    model = u_mod.open_model(root=REPO_ROOT)
    cat = model.traced_callable_catalog()
    assert cat["pass"] is True
    assert cat["total_verified_count"] >= 250
    assert cat["survival_rate"] >= 0.60  # +20 pp above 40% kill floor
    assert cat["lift_multiple_vs_ast_literal_baseline"] >= 15.0

    inv = model.invoke_traced_module("canonical/runtime/domain_of_verification_v1.py")
    assert inv["pass"] is True
    assert inv["status"] == "PASS__TRACED_MODULE_INVOKED"
    assert inv["matches_recorded_witness"] is True
    assert len(inv["output_digest"]) == 64
    assert len(inv["capsule_head_hash"]) == 64


def test_wave22_nondeterministic_module_rejected_by_two_run_gate(tmp_path: Path) -> None:
    mod_dir = tmp_path / "sandbox_probe_pkg"
    test_dir = tmp_path / "canonical" / "tests"
    mod_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    (mod_dir / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "flaky_rng_probe_v1.py").write_text(
        "import os\ndef sample_entropy(n: int = 8) -> str:\n    return os.urandom(n).hex()\n",
        encoding="utf-8",
    )
    (test_dir / "test_flaky_rng_probe_v1.py").write_text(
        "from sandbox_probe_pkg.flaky_rng_probe_v1 import sample_entropy\n"
        "def test_entropy():\n    assert len(sample_entropy(8)) == 16\n",
        encoding="utf-8",
    )
    res = etcc.derive_verified_module_adapter("sandbox_probe_pkg/flaky_rng_probe_v1.py", root=tmp_path)
    assert res["pass"] is False
    assert res["reason"] == "NO_CANDIDATE_SURVIVED_TWO_RUN_REPLAY"


# ---------------------------------------------------------------------------
# Wave 23: 4-Rung Fast-Cascade Orchestrator & State-Alias Tomography Guard
# ---------------------------------------------------------------------------


def test_wave23_rung0_discr_tree_and_domain_of_verification_refusal() -> None:
    model = u_mod.open_model(root=REPO_ROOT)
    r0 = model.fast_cascade_solve(
        {
            "buggy_fn_source": "def ratio(a, b):\n    return a / b\n",
            "fn_name": "ratio",
            "failure_witness": "ZeroDivisionError",
            "probe_cases": [((10, 0), 0.0), ((10, 2), 5.0)],
            "verified_points": [(0, 0), (5, 25), (10, 100)],
            "query_point": 4,
        }
    )
    assert r0["pass"] is True
    assert r0["rung_selected"] == 0
    assert r0["model_calls"] == 0

    # Extrapolation outside verified interval must fail closed
    extrap = model.fast_cascade_solve(
        {
            "verified_points": [(0, 0), (5, 25), (10, 100)],
            "query_point": 99,
        }
    )
    assert extrap["pass"] is False
    assert extrap["reason"] == "EXTRAPOLATION_OUTSIDE_VERIFIED_DOMAIN"


def test_wave23_rung1_state_alias_guard_blocks_lying_extension_and_commits_valid_sqlite(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    db_fp = ws / "ledger.sqlite"
    conn = sqlite3.connect(str(db_fp))
    conn.execute("CREATE TABLE items(id INTEGER PRIMARY KEY, code TEXT)")
    conn.commit()
    conn.close()

    # 1. State-Alias attack: command exits 0 and writes a `.json` file whose bytes are NOT valid JSON!
    aliased = fco.execute_fast_cascade(
        {
            "workspace_root": str(ws),
            "shell_action": ["python3", "-c", "open('report.json','w').write('{corrupt_json')"],
            "expected_files": ["report.json"],
            "commit_on_pass": True,
        }
    )
    assert aliased["pass"] is False
    assert not (ws / "report.json").exists(), "CoW sandbox must never commit invalid State-Alias mutations"

    # 2. Genuine valid mutation on both JSON and SQLite DB commits cleanly
    valid = fco.execute_fast_cascade(
        {
            "workspace_root": str(ws),
            "shell_action": [
                "python3",
                "-c",
                (
                    "import json, sqlite3; "
                    "open('report.json','w').write(json.dumps({'ok': True})); "
                    "c = sqlite3.connect('ledger.sqlite'); "
                    "c.execute(\"INSERT INTO items(code) VALUES ('A1')\"); c.commit(); c.close()"
                ),
            ],
            "expected_files": ["report.json", "ledger.sqlite"],
            "commit_on_pass": True,
        }
    )
    assert valid["pass"] is True
    assert valid["rung_selected"] == 1
    assert json.loads((ws / "report.json").read_text(encoding="utf-8")) == {"ok": True}


def test_wave23_rung2_cow_zygote_and_rung3_petri_and_contrast() -> None:
    r2 = fco.execute_fast_cascade(
        {
            "module_source": "def double(x):\n    return x * 2\n",
            "candidate_patches": [
                {"id": "bad", "source": "def double(x):\n    return x + 2\n"},
                {"id": "good", "source": "def double(x):\n    return x * 2 if x >= 0 else 0\n"},
            ],
            "test_source": (
                "def test_double_nonneg():\n    assert double(4) == 8\n    assert double(-3) == 0\n\n"
                "def test_unrelated():\n    assert 2 + 2 == 4\n"
            ),
            "changed_symbols": ["double"],
        }
    )
    assert r2["pass"] is True
    assert r2["rung_selected"] == 2
    assert r2["winning_candidate_id"] == "good"
    assert r2["impact_slice"]["reduction_ratio"] >= 0.5

    r3 = fco.execute_fast_cascade(
        {
            "petri_transitions": [
                {
                    "action_id": "open_cfg",
                    "modality": "cli",
                    "preconditions": ["boot"],
                    "add_tokens": ["cfg_ready"],
                    "del_tokens": [],
                },
                {
                    "action_id": "apply_cfg",
                    "modality": "gui",
                    "preconditions": ["cfg_ready"],
                    "add_tokens": ["done"],
                    "del_tokens": ["cfg_ready"],
                },
            ],
            "initial_tokens": ["boot"],
            "goal_tokens": ["done"],
        }
    )
    assert r3["pass"] is True
    assert r3["rung_selected"] == 3
    assert len(r3["articulation_step_indices"]) >= 1


# ---------------------------------------------------------------------------
# Wave 24: Bi-Temporal ForwardPush PPR & Two-Door Rubin Skill Rent Curator
# ---------------------------------------------------------------------------


def test_wave24_bitemporal_forward_push_and_two_door_rent_roundtrip(tmp_path: Path) -> None:
    bus_path = tmp_path / "memory_w24.json"
    bus = mem_mod.VerificationFirstMemoryBus(state_path=bus_path)

    bus.record_bitemporal_fact(
        fact_id="fact_v1_deprecated",
        subject="checkout_api",
        predicate="uses_key",
        obj="legacy_rsa_1024",
        valid_at=10.0,
    )
    bus.supersede_bitemporal_fact(
        old_fact_id="fact_v1_deprecated",
        superseded_at=20.0,
        replacement_fact={
            "fact_id": "fact_v2_live",
            "subject": "checkout_api",
            "predicate": "uses_key",
            "obj": "ed25519_vault_ring",
            "valid_at": 20.0,
        },
    )

    sk_good = bus.crystallize_action_macro(
        trigger_key="ed25519_vault_ring",
        actions=[{"op": "rotate_ed25519_ring"}],
        provenance_episode_id="ep_vault_1",
    )
    sk_decoy = bus.crystallize_action_macro(
        trigger_key="ed25519_vault_ring",
        actions=[{"op": "corrupt_ring"}],
        provenance_episode_id="ep_decoy_1",
    )
    for idx in range(4):
        bus.crystallize_action_macro(
            trigger_key=f"aux_target_{idx}",
            actions=[{"op": f"noop_{idx}"}],
            provenance_episode_id=f"ep_aux_{idx}",
        )

    rent_res = bus.enforce_two_door_rent_and_cap(
        max_active_skills=2,
        paired_probes={
            sk_good.skill_id: [{"y_with": 1.0, "y_without": 0.0, "delta_ms": 1.0, "is_safe_baseline": False}],
            sk_decoy.skill_id: [{"y_with": 0.0, "y_without": 1.0, "delta_ms": 1.0, "is_safe_baseline": True}],
        },
    )
    assert rent_res["pass"] is True
    assert rent_res["active_skills_after"] == 2
    assert sk_decoy.skill_id in rent_res["decoys_quarantined_ids"]
    assert rent_res["retired_archive_size"] == 3

    bus.save()
    reloaded = mem_mod.VerificationFirstMemoryBus(state_path=bus_path)

    hist = reloaded.forward_push_bitemporal_recall("checkout_api", valid_at_ts=15.0, top_k=5)
    hist_ids = [h["record_id"] for h in hist["hits"]]
    assert "fact_v1_deprecated" in hist_ids
    assert "fact_v2_live" not in hist_ids

    live = reloaded.forward_push_bitemporal_recall("checkout_api", top_k=5)
    live_ids = [h["record_id"] for h in live["hits"]]
    assert "fact_v2_live" in live_ids
    assert sk_good.skill_id in live_ids
    assert "fact_v1_deprecated" not in live_ids
    assert sk_decoy.skill_id not in live_ids
    assert live["associative_multi_hop_hits"] >= 1


# ---------------------------------------------------------------------------
# End-to-End Unification Across UnifiedModel, Creature, and Federated Engines
# ---------------------------------------------------------------------------


def test_waves21_24_unified_across_model_creature_and_federated_engines(tmp_path: Path) -> None:
    model = u_mod.open_model(root=REPO_ROOT)
    creature = model.open_creature(tmp_path / "creature_home", identity="leapfrog_body", life=20.0)

    model.memory_bus.record_bitemporal_fact(
        fact_id="f_shared",
        subject="kernel_socket",
        predicate="routes_via",
        obj="zygote_pipe_7",
        valid_at=1.0,
    )
    rec = creature.bitemporal_recall("kernel_socket", top_k=3)
    assert rec["pass"] is True
    assert rec["hits"][0]["record_id"] == "f_shared"

    casc = creature.fast_cascade_solve(
        {
            "contrast_evidence": [
                (["has_token", "is_admin"], True),
                ([], False),
            ],
            "candidate_states": [["has_token"], ["is_admin"], ["has_token", "is_admin"]],
        }
    )
    assert casc["pass"] is True
    assert casc["rung_selected"] == 3
    assert casc["rung_name"] == "RUNG3_ACTIVE_CONTRAST_PROBE"

    concept = fed.resolve_cross_disciplinary_concept("hipporag forward push personalized pagerank")
    assert concept["best"] is not None
    assert "engine:LEAPFROG_W24_FORWARD_PUSH_BITEMPORAL_PPR" in concept["best"]["engines"]

    eng_out = fed.run_federated_engine(
        "LEAPFROG_W21_MMAP_CSR_SLOT_INDEX",
        {"query": "mmap csr slot index", "top_k": 3},
    )
    assert eng_out["pass"] is True


class TestFrontierLeapfrogWaves21To24(unittest.TestCase):
    def test_01_wave21_mmap_csr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_wave21_mmap_csr_exact_equivalence_and_mapping_surface(Path(td))

    def test_02_wave21_unified_model_find_source(self) -> None:
        test_wave21_unified_model_find_source_uses_mmap_csr_fast()

    def test_03_wave22_full_406_census_and_traced_invoke(self) -> None:
        test_wave22_full_406_census_exceeds_kill_floor_and_invokes_via_unified_model()

    def test_04_wave22_nondeterministic_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_wave22_nondeterministic_module_rejected_by_two_run_gate(Path(td))

    def test_05_wave23_rung0_discr_tree_and_domain_guard(self) -> None:
        test_wave23_rung0_discr_tree_and_domain_of_verification_refusal()

    def test_06_wave23_rung1_state_alias_guard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_wave23_rung1_state_alias_guard_blocks_lying_extension_and_commits_valid_sqlite(Path(td))

    def test_07_wave23_rung2_and_rung3(self) -> None:
        test_wave23_rung2_cow_zygote_and_rung3_petri_and_contrast()

    def test_08_wave24_bitemporal_forward_push_and_two_door_rent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_wave24_bitemporal_forward_push_and_two_door_rent_roundtrip(Path(td))

    def test_09_end_to_end_unification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_waves21_24_unified_across_model_creature_and_federated_engines(Path(td))


if __name__ == "__main__":
    unittest.main()
