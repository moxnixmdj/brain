#!/usr/bin/env python3
"""Behavioral unit & integration tests for the Zero-Knowledge-House CUA/SWE Kernel:
  1. `canonical.swe_kernel.epistemic_admission_and_self_play_v1`
  2. `canonical.swe_kernel.angelic_lens_cow_repair_v1`
  3. `canonical.swe_kernel.cross_modal_tomography_petri_v1`

Complies strictly with `REPO_INTEGRITY_POLICY_V1`: real execution only, zero mocks,
zero tautologies, `model_calls == 0`, `parameters_stored == 0`.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import angelic_lens_cow_repair_v1 as ALCR
from canonical.swe_kernel import cross_modal_tomography_petri_v1 as CMTP
from canonical.swe_kernel import epistemic_admission_and_self_play_v1 as EASP


def test_five_gate_epistemic_admission_and_version_drift_staleness(tmp_path: pathlib.Path) -> None:
    store = EASP.EpistemicStoreV1(tmp_path / "store.json")
    b_ir = EASP.anti_unify_ir(EASP.lift_python_to_ir("x <= limit"), EASP.lift_python_to_ir("idx <= n"))
    a_ir = EASP.anti_unify_ir(EASP.lift_python_to_ir("x < limit"), EASP.lift_python_to_ir("idx < n"))
    raw_trace = "Episode traceback: IndexError on boundary x <= limit across 14 stack frames..." * 6

    # Rejects unverified traces
    rejected = store.admit_l2_ir_skill(
        domain="swe_python",
        before_ir=b_ir,
        after_ir=a_ir,
        witness={"case": "x <= limit -> x < limit"},
        provenance={"test": "unit"},
        version_fingerprint="python3.11:api_v1",
        verified_on_oracle=False,
        goal_relevant=True,
        prediction_error_bearing=True,
        held_out_transfer_passed=True,
        innocent_controls_preserved=True,
        raw_episode_text=raw_trace,
    )
    assert rejected["admitted"] is False
    assert rejected["gates"]["verified"] is False

    # Rejects zero-prediction-error redundant storage
    no_surprise = store.admit_l2_ir_skill(
        domain="swe_python",
        before_ir=b_ir,
        after_ir=a_ir,
        witness={"case": "x <= limit -> x < limit"},
        provenance={"test": "unit"},
        version_fingerprint="python3.11:api_v1",
        verified_on_oracle=True,
        goal_relevant=True,
        prediction_error_bearing=False,
        held_out_transfer_passed=True,
        innocent_controls_preserved=True,
        raw_episode_text=raw_trace,
    )
    assert no_surprise["admitted"] is False
    assert no_surprise["gates"]["prediction_error_bearing"] is False

    # Admits genuinely general anti-unified rule passing all 5 §9.2 gates
    admitted = store.admit_l2_ir_skill(
        domain="swe_python",
        before_ir=b_ir,
        after_ir=a_ir,
        witness={"case": "x <= limit -> x < limit"},
        provenance={"test": "unit"},
        version_fingerprint="python3.11:api_v1",
        verified_on_oracle=True,
        goal_relevant=True,
        prediction_error_bearing=True,
        held_out_transfer_passed=True,
        innocent_controls_preserved=True,
        raw_episode_text=raw_trace,
    )
    assert admitted["admitted"] is True
    skill_id = admitted["skill_id"]
    assert store.summary()["active_l2_skills"] == 1
    assert store.summary()["parameters_stored"] == 0

    # Version drift (`api_v1 -> api_v2`) triggers automatic victim re-probing and quarantines stale rule
    reprobe = store.retrieve_l2_with_staleness_probe(
        domain="swe_python",
        current_version_fingerprint="python3.11:api_v2",
        reprobe_fn=lambda entry: False,
    )
    assert reprobe == []
    assert store.data["l2_skills"][skill_id]["status"] == "QUARANTINED__STALE_ON_VERSION_DRIFT"

    # Explicit O(1) edit & deletion without retraining (§2 Zero-Knowledge-House test)
    assert store.edit_entry(skill_id, {"notes": "reviewed"}) is True
    assert store.delete_entry(skill_id) is True
    assert skill_id not in store.data["l2_skills"]


def test_single_experience_cross_language_ir_transfer_python_to_c_and_js() -> None:
    before_ir = EASP.lift_python_to_ir("idx <= capacity")
    after_ir = EASP.lift_python_to_ir("idx < capacity")
    gen_b = EASP.anti_unify_ir(before_ir, EASP.lift_python_to_ir("pos <= length"))
    gen_a = EASP.anti_unify_ir(after_ir, EASP.lift_python_to_ir("pos < length"))

    c_fixed = EASP.transfer_ir_rule_to_snippet(
        gen_b, gen_a, "if (offset <= buf_len) { return buf[offset]; }", target_language="c"
    )
    js_fixed = EASP.transfer_ir_rule_to_snippet(
        gen_b, gen_a, "if (cursor <= items_count) { return items[cursor]; }", target_language="javascript"
    )
    assert c_fixed == "if (offset < buf_len) { return buf[offset]; }"
    assert js_fixed == "if (cursor < items_count) { return items[cursor]; }"


def test_bidirectional_lens_synthesis_and_roundtrip_inversion() -> None:
    # Synthesizes general ASCII control-character caret notation without hardcoded tables
    caret_lens = ALCR.synthesize_bidirectional_lens(
        [("line\x04\n", "line^D\n"), ("end\x1a\n", "end^Z\n")],
        preserved_samples=["normal text 123\n\t"],
    )
    assert caret_lens is not None
    assert caret_lens.roundtrip_verified is True
    assert caret_lens.forward_fn("interrupt\x03\n") == "interrupt^C\n"
    assert caret_lens.inverse_fn("interrupt^C\n") == "interrupt\x03\n"
    assert caret_lens.forward_fn("keep ^ literal?") == "keep ^ literal?"

    # Synthesizes delimiter structural swap (`YYYY-MM-DD <-> DD/MM/YYYY`)
    date_lens = ALCR.synthesize_bidirectional_lens(
        [("2026-11-25", "25/11/2026"), ("2025-04-09", "09/04/2025")],
        preserved_samples=["plain"],
    )
    assert date_lens is not None
    assert date_lens.forward_fn("2030-01-15") == "15/01/2030"
    assert date_lens.inverse_fn("15/01/2030") == "2030-01-15"


def test_cow_angelic_repair_with_repo_morphism_and_dual_splicing(tmp_path: pathlib.Path) -> None:
    # Multi-file repository where `codec.py` must discover helper `normalize_slug` from `helpers.py`
    # AND splice a separating guard for empty/whitespace headers!
    (tmp_path / "helpers.py").write_text(
        "def normalize_slug(raw: str) -> str:\n"
        "    return raw.strip().lower().replace(' ', '-')\n",
        encoding="utf-8",
    )
    (tmp_path / "router.py").write_text(
        "from helpers import normalize_slug\n\n"
        "def build_route(title: str) -> str:\n"
        "    if not title:\n"
        "        return '/index'\n"
        "    return title\n",
        encoding="utf-8",
    )

    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        import router  # type: ignore[import-not-found]

        def fail_1() -> tuple[bool, object, object]:
            got = router.build_route("Hello World")
            return (got == "hello-world"), got, "hello-world"

        def fail_2() -> tuple[bool, object, object]:
            got = router.build_route("  Admin Panel ")
            return (got == "admin-panel"), got, "admin-panel"

        def pass_1() -> bool:
            return router.build_route("") == "/index"

        def pass_2() -> bool:
            return router.build_route("/Ready/Path") == "/Ready/Path"

        store = EASP.EpistemicStoreV1(tmp_path / "splice_store.json")
        res = ALCR.repair_python_project_cow(
            project_root=tmp_path,
            suspect_files=["router.py"],
            failing_test_fns=[("f1", fail_1), ("f2", fail_2)],
            passing_test_fns=[("p1", pass_1), ("p2", pass_2)],
            store=store,
        )
        assert res["status"] == "VERIFIED"
        assert "normalize_slug" in res["replacement"]
        assert res["mechanism"] == "dual_program_splice"
        assert store.summary()["active_l3_negative_invariants"] >= 1
        assert res["model_calls"] == 0
    finally:
        sys.path.remove(str(tmp_path))


def test_c_tree_sitter_asan_causal_slice_and_ddmin_self_play(tmp_path: pathlib.Path) -> None:
    c_src = (
        "#include <stddef.h>\n"
        "#include <string.h>\n"
        "size_t safe_len(const char *ptr) {\n"
        "    return strlen(ptr);\n"
        "}\n"
        "int main(void) {\n"
        "    if (safe_len(\"abc\") != 3) return 1;\n"
        "    if (safe_len(NULL) != 0) return 2;\n"
        "    return 0;\n"
        "}\n"
    )
    (tmp_path / "prog.c").write_text(c_src, encoding="utf-8")
    bin_out = tmp_path / "prog_bin"
    cmd = [
        "bash",
        "-c",
        f"gcc -O1 -g -fsanitize=address,undefined prog.c -o {bin_out} && {bin_out}",
    ]
    c_res = ALCR.repair_c_causal_slice(
        work_dir=tmp_path,
        target_c_rel="prog.c",
        compile_and_test_cmd=cmd,
    )
    assert c_res["status"] == "VERIFIED"
    assert "NULL" in c_res["patched_source"]
    assert c_res["model_calls"] == 0

    # Verify Zeller ddmin shrinks a 16-element trace to the 2-element causal trigger
    shrunk, checks = EASP.ddmin_shrink_sequence(
        list(range(16)),
        lambda seq: (3 in seq and 11 in seq),
    )
    assert shrunk == [3, 11]
    assert checks <= 64


def test_multilayer_tomography_pure_canvas_dhash_and_320_step_petri_slicing(tmp_path: pathlib.Path) -> None:
    # 1. Pure-canvas widget perception survives translation across different screen coordinates!
    canvas_a = [[10 for _ in range(48)] for _ in range(32)]
    canvas_b = [[10 for _ in range(48)] for _ in range(32)]
    for dy in range(8):
        for dx in range(12):
            val = 60 + dx * 12 + dy * 4
            canvas_a[4 + dy][5 + dx] = val
            canvas_b[18 + dy][28 + dx] = val  # Shifted (+23, +14) on screen!

    wa = CMTP.extract_canvas_layout_graph(canvas_a)
    wb = CMTP.extract_canvas_layout_graph(canvas_b)
    assert len(wa) == 1 and len(wb) == 1
    assert wa[0].dhash_hex == wb[0].dhash_hex
    assert wa[0].centroid != wb[0].centroid

    # 2. SQLite + FS + DOM + A11y differential state tomography
    db_file = tmp_path / "app.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, paid INTEGER)")
    conn.execute("INSERT INTO invoices VALUES (1, 0)")
    conn.commit()
    conn.close()

    s_before = CMTP.capture_multilayer_state(
        a11y_tree=[{"role": "button", "label": "Pay", "enabled": True}],
        html_dom='<form><input type="hidden" name="csrf" value="tok99"><button id="pay">Pay</button></form>',
        canvas_2d=canvas_a,
        sqlite_paths=[db_file],
    )
    conn = sqlite3.connect(str(db_file))
    conn.execute("UPDATE invoices SET paid = 1 WHERE id = 1")
    conn.commit()
    conn.close()
    s_after = CMTP.capture_multilayer_state(
        a11y_tree=[{"role": "button", "label": "Pay", "enabled": False}],
        html_dom='<form><input type="hidden" name="csrf" value="tok99"><button id="pay" disabled>Pay</button></form>',
        canvas_2d=canvas_b,
        sqlite_paths=[db_file],
    )
    diff = CMTP.diff_multilayer_states(s_before, s_after)
    assert diff["is_noop"] is False
    assert any(f.startswith("sqlite:app.db:invoices:") for f in diff["added"])

    # 3. 320-step cross-modal workflow sliced at dominator cut-vertices with 16-way CoW rollouts
    net = CMTP.UnifiedCrossModalPetriNet()
    for step in range(320):
        net.add_transition(
            CMTP.PetriTransition(
                transition_id=f"op_{step:03d}",
                modality=("gui", "canvas", "dom", "sqlite", "cli")[step % 5],
                input_tokens=(f"s_{step}",),
                output_tokens=(f"s_{step + 1}",),
                deleted_tokens=(f"s_{step}",) if step > 0 else (),
            )
        )
    distractors = [(f"noop_btn_{i}", lambda st: None) for i in range(12)]
    wf = CMTP.execute_long_horizon_sliced_workflow(
        petri_net=net,
        env_state={},
        initial_tokens=["s_0"],
        goal_tokens=["s_320"],
        distractor_actions=distractors,
        target_chunk_size=32,
    )
    assert wf["status"] == "VERIFIED"
    assert wf["steps_executed"] == 320
    assert wf["checkpoints_verified"] == 10
    assert wf["max_sub_episode_length"] == 32


def test_supervised_self_play_batch_with_atomic_lease_and_ddmin(tmp_path: pathlib.Path) -> None:
    store = EASP.EpistemicStoreV1(tmp_path / "self_play_store.json")
    batch = EASP.run_supervised_self_play_batch(
        tasks=[
            {
                "task_id": "ddmin_lease_check",
                "goal": "Isolate minimal crash trigger under same_identity_supervisor lease",
                "failing_input": [10, 20, 30, -7, 40, 50, 60, 70],
                "is_failing_input": lambda seq: (-7 in seq),
            }
        ],
        solver_fn=lambda task, _st: {
            "status": "VERIFIED" if list(task["failing_input"]) == [-7] else "UNSOLVED",
            "witness": list(task["failing_input"]),
        },
        store=store,
    )
    assert batch["tasks_total"] == 1
    assert batch["solved_count"] == 1
    assert batch["results"][0]["lease_status"] == "CLAIMED"
    assert batch["results"][0]["shrunk_len"] == 1
    assert batch["results"][0]["witness"] == [-7]


def test_clone_family_except_widening_and_c_deref_guard_weakening(tmp_path: pathlib.Path) -> None:
    # 1. Python clone-family `ExceptHandler` tuple widening across sibling methods
    proj = tmp_path / "py_clone"
    proj.mkdir()
    (proj / "claims.py").write_text(
        "class Validator:\n"
        "    def check_a(self, x):\n"
        "        try:\n"
        "            return int(x)\n"
        "        except ValueError:\n"
        "            raise KeyError('bad_a')\n\n"
        "    def check_b(self, x):\n"
        "        try:\n"
        "            return int(x)\n"
        "        except ValueError:\n"
        "            raise KeyError('bad_b')\n",
        encoding="utf-8",
    )
    (proj / "test_claims.py").write_text(
        "import pytest\n"
        "from claims import Validator\n\n"
        "def test_none_a():\n"
        "    with pytest.raises(KeyError):\n"
        "        Validator().check_a(None)\n\n"
        "def test_inf_b():\n"
        "    with pytest.raises(KeyError):\n"
        "        Validator().check_b(float('inf'))\n\n"
        "def test_valid():\n"
        "    assert Validator().check_a('42') == 42\n",
        encoding="utf-8",
    )
    res_py = ALCR.repair_git_repo_from_pytest(repo_dir=proj, pytest_targets=["test_claims.py"], timeout_s=20.0)
    assert res_py["status"] == "VERIFIED"
    assert "except_clone_family_widen" in res_py["mechanism"]

    # 2. C conditional dereference precondition guard weakening under gcc ASan/UBSan
    c_dir = tmp_path / "c_deref"
    c_dir.mkdir()
    (c_dir / "list.c").write_text(
        "#include <stddef.h>\n"
        "typedef struct Node { struct Node *prev; struct Node *next; int val; } Node;\n"
        "typedef struct Root { Node *head; } Root;\n"
        "Node *detach(Root *r, Node *item) {\n"
        "    if ((r == NULL) || (r->head == NULL) || (item == NULL) || (item->prev == NULL)) {\n"
        "        return NULL;\n"
        "    }\n"
        "    if (item != r->head) {\n"
        "        item->prev->next = item->next;\n"
        "    } else {\n"
        "        r->head = item->next;\n"
        "    }\n"
        "    return item;\n"
        "}\n",
        encoding="utf-8",
    )
    (c_dir / "test_list.c").write_text(
        "#include <stdio.h>\n"
        "typedef struct Node { struct Node *prev; struct Node *next; int val; } Node;\n"
        "typedef struct Root { Node *head; } Root;\n"
        "Node *detach(Root *r, Node *item);\n"
        "int main(void) {\n"
        "    Node a = {NULL, NULL, 1};\n"
        "    Node b = {NULL, NULL, 2};\n"
        "    Root r = {&a};\n"
        "    if (detach(&r, &b) != NULL) { printf(\"test_detach:FAIL: middle\\n\"); return 1; }\n"
        "    if (detach(&r, &a) != &a) { printf(\"test_detach:FAIL: head\\n\"); return 1; }\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    bin_p = c_dir / "runner"
    res_c = ALCR.repair_c_causal_slice(
        work_dir=c_dir,
        target_c_rel="list.c",
        compile_and_test_cmd=["bash", "-c", f"gcc -O1 -g -fsanitize=address,undefined {c_dir}/list.c {c_dir}/test_list.c -o {bin_p} && {bin_p}"],
    )
    assert res_c["status"] == "VERIFIED"
    assert "c_conditional_deref_guard_weakening" in res_c["mechanism"]


def test_multi_statement_subtree_anti_unification_sibling_graft_and_replay(tmp_path: pathlib.Path) -> None:
    # 1. Dataflow Slice Closure: grafting `self.format_label(ctx)` from sibling statement into `if` branch
    before_sib = (
        "class Param:\n"
        "    def get_record(self, ctx):\n"
        "        if self.hidden:\n"
        "            return None\n"
        "        return (self.format_label(ctx), self.help_text)\n"
    )
    after_sib = (
        "class Param:\n"
        "    def get_record(self, ctx):\n"
        "        if self.hidden:\n"
        "            return (self.format_label(ctx), '')\n"
        "        return (self.format_label(ctx), self.help_text)\n"
    )
    sib_morph = EASP.lift_python_subtree_morphism(before_sib, after_sib)
    assert sib_morph is not None
    assert sib_morph.unbound_holes() == set()

    # 2. Multi-function clone Plotkin anti-unification + 1-attempt zero-search replay on unseen module
    store = EASP.EpistemicStoreV1(tmp_path / "subtree_store.json")
    proj1 = tmp_path / "repo_train"
    proj1.mkdir()
    (proj1 / "tokens.py").write_text(
        "class Decoder:\n"
        "    def parse_exp(self, d):\n"
        "        try:\n"
        "            return int(d['exp'])\n"
        "        except ValueError:\n"
        "            raise KeyError('bad exp')\n\n"
        "    def parse_nbf(self, d):\n"
        "        try:\n"
        "            return int(d['nbf'])\n"
        "        except ValueError:\n"
        "            raise KeyError('bad nbf')\n",
        encoding="utf-8",
    )
    (proj1 / "test_tokens.py").write_text(
        "import pytest\n"
        "from tokens import Decoder\n\n"
        "def test_bad_types():\n"
        "    with pytest.raises(KeyError):\n"
        "        Decoder().parse_exp(None)\n"
        "    with pytest.raises(KeyError):\n"
        "        Decoder().parse_nbf([])\n\n"
        "def test_ok():\n"
        "    assert Decoder().parse_exp({'exp': '9'}) == 9\n",
        encoding="utf-8",
    )
    train_res = ALCR.repair_git_repo_from_pytest(repo_dir=proj1, pytest_targets=["test_tokens.py"], store=store, timeout_s=20.0)
    assert train_res["status"] == "VERIFIED"
    assert train_res["learned_skill_id"] is not None
    sid = str(train_res["learned_skill_id"])

    # Held-out unseen repository with different class, method, and variable names -> 1-attempt L2 replay!
    proj2 = tmp_path / "repo_heldout"
    proj2.mkdir()
    (proj2 / "billing.py").write_text(
        "def parse_invoice_cents(row):\n"
        "    try:\n"
        "        return int(row['cents'])\n"
        "    except ValueError:\n"
        "        raise KeyError('invalid cents')\n",
        encoding="utf-8",
    )
    (proj2 / "test_billing.py").write_text(
        "import pytest\n"
        "from billing import parse_invoice_cents\n\n"
        "def test_dict_cents():\n"
        "    with pytest.raises(KeyError):\n"
        "        parse_invoice_cents({'cents': {'bad': 1}})\n\n"
        "def test_valid_cents():\n"
        "    assert parse_invoice_cents({'cents': '250'}) == 250\n",
        encoding="utf-8",
    )
    replay_res = ALCR.repair_git_repo_from_pytest(repo_dir=proj2, pytest_targets=["test_billing.py"], store=store, timeout_s=20.0)
    assert replay_res["status"] == "VERIFIED"
    assert str(replay_res["mechanism"]).startswith("l2_subtree_skill_replay(")
    assert replay_res["attempt"] == 1

    # Surgical O(1) deletion without retraining
    assert store.delete_entry(sid) is True
    assert store.summary()["active_l2_skills"] == 0


def test_cow_differential_boundary_fuzzing_refutes_overfit_patch(tmp_path: pathlib.Path) -> None:
    pkg = tmp_path / "fuzz_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    orig_src = "def unit_rate(total: int, count: int) -> int:\n    if count == 0:\n        return 0\n    return total // count\n"
    overfit_src = "def unit_rate(total: int, count: int) -> int:\n    return abs(total) // count\n"
    safe_src = "def unit_rate(total: int, count: int) -> int:\n    if count == 0:\n        return 0\n    return abs(total) // count\n"
    (pkg / "rates.py").write_text(orig_src, encoding="utf-8")
    ALCR._load_modules_from_sources(tmp_path, {"fuzz_pkg/rates.py": orig_src})

    refuted = ALCR.fuzz_verify_patch_cow(
        project_root=tmp_path,
        rel_path="fuzz_pkg/rates.py",
        orig_source=orig_src,
        patched_source=overfit_src,
        func_name="unit_rate",
        pass_envs=[{"total": 4, "count": 2}, {"total": 6, "count": 3}],
        max_boundary_cases=64,
    )
    assert refuted["fuzz_passed"] is False
    assert "ZeroDivisionError" in str(refuted.get("failure_reason", ""))

    accepted = ALCR.fuzz_verify_patch_cow(
        project_root=tmp_path,
        rel_path="fuzz_pkg/rates.py",
        orig_source=orig_src,
        patched_source=safe_src,
        func_name="unit_rate",
        pass_envs=[{"total": 4, "count": 2}, {"total": 6, "count": 3}],
        max_boundary_cases=64,
    )
    assert accepted["fuzz_passed"] is True
    assert accepted["boundary_cases_tested"] == 64


def test_idea1_zero_oracle_green_repo_metamorphic_repair(tmp_path: pathlib.Path) -> None:
    """Wall 1 (`80a7e8eb`): Repair a repository whose test suite is 100% GREEN (`pre_green=True`)
    by discovering escaping stdlib exceptions against a package domain exception lattice.
    """
    repo = tmp_path / "green_auth"
    repo.mkdir()
    (repo / "tokens.py").write_text(
        "class TokenError(Exception):\n"
        "    pass\n\n"
        "class InvalidClaimError(TokenError):\n"
        "    pass\n\n"
        "class Verifier:\n"
        "    def _validate_exp(self, payload: dict) -> int:\n"
        "        try:\n"
        "            val = int(payload['exp'])\n"
        "        except ValueError:\n"
        "            raise InvalidClaimError('exp must be an int')\n"
        "        if val < 0:\n"
        "            raise InvalidClaimError('expired')\n"
        "        return val\n",
        encoding="utf-8",
    )
    # 100% GREEN test suite: only tests valid int and bad string ('abc' -> ValueError -> InvalidClaimError),
    # completely missing None / float('inf') (`TypeError` / `OverflowError` escape!).
    (repo / "test_tokens.py").write_text(
        "import pytest\n"
        "from tokens import InvalidClaimError, Verifier\n\n"
        "def test_valid_and_bad_str():\n"
        "    v = Verifier()\n"
        "    assert v._validate_exp({'exp': '42'}) == 42\n"
        "    with pytest.raises(InvalidClaimError):\n"
        "        v._validate_exp({'exp': 'not-an-int'})\n",
        encoding="utf-8",
    )
    res = ALCR.repair_issue_only_green_repo_cow(
        repo_dir=repo,
        suspect_files=["tokens.py"],
        green_pytest_targets=["test_tokens.py"],
    )
    assert res["status"] == "VERIFIED"
    assert res["model_calls"] == 0
    assert res["parameters_stored"] == 0
    assert res["metamorphic_witnesses_synthesized"] >= 1
    ns: dict[str, object] = {}
    exec(res["patched_source"], ns)
    ver = ns["Verifier"]()  # type: ignore[operator]
    dom_err = ns["TokenError"]  # type: ignore[assignment]
    for bad in (None, [], float("inf")):
        try:
            ver._validate_exp({"exp": bad})  # type: ignore[attr-defined]
            raise AssertionError(f"Expected TokenError for {bad!r}")
        except BaseException as exc:
            assert isinstance(exc, dom_err)  # type: ignore[arg-type]


def test_idea2_type_habitation_and_raise_template_mining(tmp_path: pathlib.Path) -> None:
    """Wall 2: Repair non-ASCII domain guard using codebase-mined custom exception template."""
    repo = tmp_path / "lic_pkg"
    repo.mkdir()
    (repo / "licenses.py").write_text(
        "class InvalidLicenseError(ValueError):\n"
        "    pass\n\n"
        "def parse_license(raw: str) -> str:\n"
        "    cleaned = raw.strip()\n"
        "    if not cleaned:\n"
        "        raise InvalidLicenseError(f'Empty license: {raw!r}')\n"
        "    return cleaned.upper()\n",
        encoding="utf-8",
    )
    (repo / "test_licenses.py").write_text(
        "import pytest\n"
        "from licenses import InvalidLicenseError, parse_license\n\n"
        "def test_ascii_ok():\n"
        "    assert parse_license(' mit ') == 'MIT'\n\n"
        "def test_reject_non_ascii():\n"
        "    with pytest.raises(InvalidLicenseError, match='non-ASCII'):\n"
        "        parse_license('MIT-\\u00e9')\n",
        encoding="utf-8",
    )
    res = ALCR.repair_git_repo_from_pytest(
        repo_dir=repo,
        pytest_targets=["test_licenses.py"],
    )
    assert res["status"] == "VERIFIED"
    assert "isascii" in res["patched_source"]
    assert res["model_calls"] == 0


def test_idea3_coupled_two_file_relational_zipper(tmp_path: pathlib.Path) -> None:
    """Wall 3: Coupled 2-file producer/consumer repair where every 1-file edit fails."""
    pkg = tmp_path / "zipper_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "producer.py").write_text(
        "def normalize_slug(raw: str) -> str:\n"
        "    return raw.strip()\n",
        encoding="utf-8",
    )
    (pkg / "consumer.py").write_text(
        "from zipper_pkg.producer import normalize_slug\n\n"
        "def format_route(prefix: str, name: str) -> str:\n"
        "    clean_p = prefix\n"
        "    return f'/{clean_p}/{normalize_slug(name)}'\n",
        encoding="utf-8",
    )
    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        # Prove 1-file ceiling (`max_zipper_hops=1`) cannot solve coupled 2-file bug
        res_1hop = ALCR.repair_python_project_cow(
            project_root=tmp_path,
            suspect_files=["zipper_pkg/producer.py", "zipper_pkg/consumer.py"],
            failing_test_fns=[
                ("test_slug", lambda: ((v := __import__("zipper_pkg.producer", fromlist=["normalize_slug"]).normalize_slug("  Admin ")) == "admin", v, "admin")),
                ("test_route", lambda: ((v := __import__("zipper_pkg.consumer", fromlist=["format_route"]).format_route("/v1/", "  Admin ")) == "/v1/admin", v, "/v1/admin")),
            ],
            passing_test_fns=[
                ("test_clean", lambda: __import__("zipper_pkg.consumer", fromlist=["format_route"]).format_route("v1", "guest") == "/v1/guest"),
            ],
            max_zipper_hops=1,
        )
        assert res_1hop["status"] != "VERIFIED"

        res_2hop = ALCR.repair_python_project_cow(
            project_root=tmp_path,
            suspect_files=["zipper_pkg/producer.py", "zipper_pkg/consumer.py"],
            failing_test_fns=[
                ("test_slug", lambda: ((v := __import__("zipper_pkg.producer", fromlist=["normalize_slug"]).normalize_slug("  Admin ")) == "admin", v, "admin")),
                ("test_route", lambda: ((v := __import__("zipper_pkg.consumer", fromlist=["format_route"]).format_route("/v1/", "  Admin ")) == "/v1/admin", v, "/v1/admin")),
            ],
            passing_test_fns=[
                ("test_clean", lambda: __import__("zipper_pkg.consumer", fromlist=["format_route"]).format_route("v1", "guest") == "/v1/guest"),
            ],
            max_zipper_hops=2,
        )
        assert res_2hop["status"] == "VERIFIED"
        assert sorted(res_2hop["patched_files"].keys()) == ["zipper_pkg/consumer.py", "zipper_pkg/producer.py"]
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        for m in list(sys.modules):
            if m == "zipper_pkg" or m.startswith("zipper_pkg."):
                sys.modules.pop(m, None)


def test_idea4_transactional_worktree_rollout_and_negative_effect_guard(tmp_path: pathlib.Path) -> None:
    """Idea 4: Destructive candidate is rolled back and recorded in L3; safe delta commits atomically."""
    ws = tmp_path / "tx_ws"
    ws.mkdir()
    (ws / "prod.conf").write_text("tls=strict\n", encoding="utf-8")
    (ws / "state.txt").write_text("ready=0\n", encoding="utf-8")
    store = EASP.EpistemicStoreV1()
    out = CMTP.execute_transactional_worktree_rollout(
        workspace_dir=ws,
        candidate_commands=[
            ("rm_conf_branch", ["sh", "-c", "rm -f prod.conf && printf 'ready=1\n' > state.txt"]),
            ("safe_branch", ["sh", "-c", "printf 'ready=1\n' > state.txt"]),
        ],
        postcondition_fn=lambda d: (d / "state.txt").read_text(encoding="utf-8") == "ready=1\n",
        protected_rel_paths=["prod.conf"],
        store=store,
    )
    assert out["committed"] is True
    assert out["committed_branch"] == "safe_branch"
    assert out["real_workspace_protected_intact"] is True
    assert (ws / "prod.conf").read_text(encoding="utf-8") == "tls=strict\n"
    assert (ws / "state.txt").read_text(encoding="utf-8") == "ready=1\n"
    assert len(store.data["l3_negative_invariants"]) >= 1


def test_idea5_blackbox_binary_byte_jacobian_cow(tmp_path: pathlib.Path) -> None:
    """Idea 5: Probe a compiled black-box C binary to recover magic bytes, length crash, and payload taint."""
    import subprocess
    c_file = tmp_path / "proto.c"
    bin_file = tmp_path / "proto_bin"
    c_file.write_text(
        "#include <stdio.h>\n#include <stdint.h>\n#include <stdlib.h>\n"
        "int main(void) {\n"
        "  uint8_t b[8] = {0};\n"
        "  if (fread(b, 1, 8, stdin) < 6) return 1;\n"
        "  if (b[0] != 'P' || b[1] != 'K') return 1;\n"
        "  if (b[2] > 0x10) abort();\n"
        "  printf(\"TAG=%c\\n\", b[3]);\n"
        "  return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    subprocess.run(["gcc", "-O2", str(c_file), "-o", str(bin_file)], check=True)
    jac = ALCR.probe_binary_byte_jacobian_cow([str(bin_file)], b"PK\x02Z00")
    assert jac["baseline_rc"] == 0
    assert 0 in jac["control_sensitive_offsets"] and 1 in jac["control_sensitive_offsets"]
    assert 2 in jac["control_sensitive_offsets"]
    assert any(row["offset"] == 2 and row["crashed"] >= 1 for row in jac["jacobian"])
    assert 3 in jac["output_taint_offsets"]


def test_idea6_mutant_kill_self_play_and_o1_fingerprint_index(tmp_path: pathlib.Path) -> None:
    """Idea 6 + O(1) Index: Harvest verified skills from killed AST mutants and verify O(1) bucket lookup."""
    store = EASP.EpistemicStoreV1(tmp_path / "mut_store.json")
    clean_src = (
        "def classify(x: int, meta: dict | None = None) -> int:\n"
        "    if meta is None:\n"
        "        meta = {}\n"
        "    meta.setdefault('hits', 0)\n"
        "    if x >= 0:\n"
        "        return 1\n"
        "    return -1\n"
    )

    def _oracle(src: str) -> bool:
        ns: dict[str, object] = {}
        exec(src, ns)
        fn = ns["classify"]  # type: ignore[assignment]
        m = {"hits": 3}
        return fn(4, m) == 1 and m["hits"] == 3 and fn(0) == 1 and fn(-2) == -1  # type: ignore[operator]

    harv = EASP.harvest_repo_mutant_kill_skills(
        clean_source_text=clean_src,
        passing_oracle_fn=_oracle,
        store=store,
    )
    assert harv["mutants_killed"] >= 2
    assert harv["skills_admitted"] >= 2
    # Verify O(1) structural fingerprint lookup finds the harvested `>` -> `>=` skill on an unseen function!
    unseen_buggy = "def allow_zero(k: int) -> int:\n    if k > 0:\n        return 10\n    return -10\n"
    lookup = store.retrieve_l2_by_structural_fingerprint(source_text=unseen_buggy, domain="python")
    assert lookup["bucket_hits"] >= 1
    assert len(lookup["skills"]) >= 1


def test_unified_open_model_epistemic_front_door_repairs_workspace(tmp_path: pathlib.Path) -> None:
    """Verify `open_model().solve(..., mode='EPISTEMIC', cwd=...)` executes the full 7-stage
    epistemic loop (`model_calls == 0`, `parameters_stored == 0`) and repairs a buggy workspace.
    """
    from canonical.runtime import brain_unified_model_v1 as BUM

    (tmp_path / "bounds.py").write_text(
        "def clamp_nonneg(x: int) -> int:\n"
        "    if x > 0:\n"
        "        return x\n"
        "    return -1\n",
        encoding="utf-8",
    )
    (tmp_path / "test_bounds.py").write_text(
        "from bounds import clamp_nonneg\n"
        "def test_clamp():\n"
        "    assert clamp_nonneg(0) == 0\n"
        "    assert clamp_nonneg(7) == 7\n"
        "    assert clamp_nonneg(-4) == -1\n",
        encoding="utf-8",
    )
    model = BUM.open_model()
    out = model.solve("Repair boundary off-by-one defect in bounds.py", mode="EPISTEMIC", cwd=tmp_path)
    assert out["status"] == "VERIFIED"
    assert out["pass"] is True
    assert out["model_calls"] == 0
    assert out["parameters_stored"] == 0
    assert out["epistemic_result"]["mechanism"] == "guard_gt_to_gte"


def test_instance_slot_unwrapping_synthesizes_slots_getattr_without_literals(tmp_path: pathlib.Path) -> None:
    """Verify `__slots__` live object introspection (`getattr(x, slot, x)`) repairs wrapper
    unwrapping defects (such as `typing.ForwardRef`) with zero hardcoded type names.
    """
    import typing

    pkg = tmp_path / "slot_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "checker.py").write_text(
        "def is_classvar_annot(annot) -> bool:\n"
        "    annot = str(annot)\n"
        "    return annot.startswith(('ClassVar', 'typing.ClassVar'))\n",
        encoding="utf-8",
    )

    def _f0():
        import slot_pkg.checker as chk
        got = chk.is_classvar_annot(typing.ForwardRef("ClassVar[int]"))
        return (got is True, got, True)

    def _p0():
        import slot_pkg.checker as chk
        return chk.is_classvar_annot("ClassVar[str]") is True and chk.is_classvar_annot("int") is False

    import sys as _sys
    _sys.path.insert(0, str(tmp_path))
    try:
        res = ALCR.repair_python_project_cow(
            project_root=tmp_path,
            suspect_files=["slot_pkg/checker.py"],
            failing_test_fns=[("test_forward_ref", _f0)],
            passing_test_fns=[("test_plain", _p0)],
        )
    finally:
        _sys.path.remove(str(tmp_path))
    assert res["status"] == "VERIFIED"
    assert res["mechanism"] == "instance_slot_unwrap"
    assert "__forward_arg__" in res["patched_source"]





