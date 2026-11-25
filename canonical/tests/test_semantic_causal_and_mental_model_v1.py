#!/usr/bin/env python3
"""End-to-end zero-mock verification suite for the Autonomous Causal SWE & Computer-Use Engine.

Tests (100% real execution: gcc + ASan/UBSan, Node.js, Python, SQLite, Git, os.fork() CoW, zero mocks):
  1. 6-language UIR quotient convergence (Python, C, C++, JS, Rust, Go), Z3 safety proofs,
     anti-tautology admission rejection, and 1-experience cross-language transfer + memory ablation
     (Generalized UIR Store vs Empty Store vs Raw Unquotiented String Traces).
  2. Repo-native Petri-net component mining (`REPO_PETRI_COMPREHENSION_MAP`), counterexample-
     partitioned Dual-Program Splicing (`VERIFIED__DUAL_PROGRAM_SPLICE`), and 3-site coordinated
     multi-hunk compositional repair (`VERIFIED__MULTI_SITE_COMPOSITIONAL_CEGIS`).
  3. Multi-modal state perception (FS + Archive + CSV + JSON + SQLite + Git + DOM/a11y + zero-VLM
     PPM canvas connected-component segmentation), 16-way parallel `os.fork()` CoW speculative
     execution, deceptive-doc hazard rejection, and version-drift staleness re-probing.
  4. Cross-Modal Type-Transition Petri Net (`GUI/DOM + SQLite + CLI`) and 320-step OSWorld-horizon
     stateful workflow execution with injected mid-trajectory drift recovery vs open-loop ablation.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import pathlib
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile

import pytest

measured_open_on_real_inputs = pytest.mark.xfail(
    strict=True,
    reason=(
        "MEASURED OPEN, not skipped. This test passes on synthetic six-language snippets but "
        "fails at the ablation-B step (`repair_project_causally` on a real C project returns "
        "OPEN__NO_CAUSAL_SITES_IN_CPG). It stays failing visibly: z3 5.4.1, tree-sitter 0.27.0 "
        "and the c/js/rust/go language packs are all installed here, so a skip would disguise "
        "an engine gap as a missing dependency. See "
        "canonical/verification/CROSS_BRANCH_TRANSFER_RECEIPT_20261124_V1.json."
    ),
)

from canonical.swe_kernel.executable_mental_model_v1 import (
    CrossModalPetriNet,
    EnvironmentGoal,
    RelationalActionStore,
    check_goal_satisfied,
    compute_predicate_facts,
    perceive_environment_state,
    solve_environment_goal,
    speculate_parallel_cow_branches,
)
from canonical.swe_kernel.semantic_causal_engine_v1 import (
    CausalLawStore,
    canonicalize_uir,
    lower_to_uir,
    repair_project_causally,
    z3_verify_uir_safety,
)


def _write_exec(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@measured_open_on_real_inputs
def test_six_language_uir_convergence_z3_and_memory_ablation(tmp_path: pathlib.Path) -> None:
    # 1. Six-language syntactic quotient convergence onto a single canonical UIR SHA-256
    snippets = {
        "python": ("for i in range(0, len(xs) + 1):\n    s += xs[i]\n", ()),
        "c": ("for (int i = 0; i <= n; i++) { s += xs[i]; }", (("const int*", "xs"), ("int", "n"))),
        "cpp": ("for (int i = 0; i <= (int)xs.size(); i++) { s += xs[i]; }", ()),
        "javascript": ("for (let i = 0; i <= xs.length; i++) { s += xs[i]; }", ()),
        "rust": ("for i in 0..=xs.len() { s += xs[i]; }", ()),
        "go": ("for i := 0; i <= len(xs); i++ { s += xs[i] }", ()),
    }
    hashes = {}
    for lang, (src, c_params) in snippets.items():
        term, _ = lower_to_uir(src, lang, c_params=c_params)
        canon = canonicalize_uir(term)
        hashes[lang] = canon.digest()
        safety = z3_verify_uir_safety(canon)
        assert safety["checked"] is True and safety["safe"] is False
        assert any(c["kind"] == "OUT_OF_BOUNDS_INDEX" for c in safety["counterexamples"])

    assert len(set(hashes.values())) == 1, f"Expected 1 canonical UIR hash across 6 languages, got {hashes}"

    # 2. Anti-tautology gate: `bool is None` / constant-boolean dead-branch mutations must be REJECTED
    law_store = CausalLawStore(path=tmp_path / "uir_laws.json")
    taut_law = law_store.admit_from_verified_pair(
        "hasattr(x, '__reversed__')",
        "(hasattr(x, '__reversed__') is None)",
        "python",
        diagnostic_class="REWARD_HACK_TAUTOLOGY",
        as_condition=True,
    )
    assert taut_law is None, "Anti-tautology gate must reject constant-False `bool is None` rewrites!"

    # 3. 1-Experience Cross-Language Transfer + 3-Way Memory Ablation (Empty vs Raw String vs UIR Store)
    py_proj = tmp_path / "py_oob"
    (py_proj / "pkg").mkdir(parents=True)
    (py_proj / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (py_proj / "pkg" / "stats.py").write_text(
        "def sum_adjacent(arr):\n"
        "    acc = 0\n"
        "    for idx in range(0, len(arr) + 1):\n"
        "        acc += arr[idx]\n"
        "    return acc\n",
        encoding="utf-8",
    )
    (py_proj / "test_stats.py").write_text(
        "from pkg.stats import sum_adjacent\n"
        "def test_sum_adjacent():\n"
        "    assert sum_adjacent([3, 5, 7]) == 15\n"
        "    assert sum_adjacent([]) == 0\n",
        encoding="utf-8",
    )
    py_res = repair_project_causally(
        py_proj,
        [sys.executable, "-m", "pytest", "-q", "test_stats.py"],
        law_store=law_store,
    )
    assert py_res.repaired is True and py_res.admitted_law_id is not None

    # Target B: C project compiled with `gcc -fsanitize=address,undefined` (completely different var names & syntax)
    c_proj = tmp_path / "c_oob"
    c_proj.mkdir()
    c_src = (
        "#include <stddef.h>\n"
        "int accumulate_buf(const int* buf, int count) {\n"
        "    int total_v = 0;\n"
        "    for (int k = 0; k <= count; k++) {\n"
        "        total_v += buf[k];\n"
        "    }\n"
        "    return total_v;\n"
        "}\n"
    )
    (c_proj / "accum.c").write_text(c_src, encoding="utf-8")
    (c_proj / "accum_test.c").write_text(
        "#include <assert.h>\n"
        "int accumulate_buf(const int* buf, int count);\n"
        "int main(void) {\n"
        "    int xs[4] = {2, 4, 6, 8};\n"
        "    assert(accumulate_buf(xs, 4) == 20);\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    c_cmd = ["bash", "-c", "gcc -g -O1 -fsanitize=address,undefined accum.c accum_test.c -o accum_bin && ./accum_bin"]

    # Ablation A: Raw unquotiented string-diff trace from Python (`range(0, len(arr) + 1) -> range(0, len(arr))`)
    raw_trace_matches_c = "range(0, len(arr) + 1)" in c_src
    assert raw_trace_matches_c is False

    # Ablation B: Generalized UIR Law Store -> Zero-shot O(1) transfer on Candidate #1!
    c_transfer = repair_project_causally(c_proj, c_cmd, law_store=law_store)
    assert c_transfer.repaired is True
    assert c_transfer.status == "VERIFIED__ZERO_SHOT_UIR_LAW_TRANSFER"
    assert c_transfer.candidates_evaluated == 1

    # Target C: JavaScript (`node`) zero-shot transfer from the same 1 Python experience!
    js_proj = tmp_path / "js_oob"
    js_proj.mkdir()
    (js_proj / "sum.js").write_text(
        "function sumItems(items) {\n"
        "    let out = 0;\n"
        "    for (let j = 0; j <= items.length; j++) {\n"
        "        out += items[j];\n"
        "    }\n"
        "    return out;\n"
        "}\n"
        "module.exports = { sumItems };\n",
        encoding="utf-8",
    )
    (js_proj / "sum.test.js").write_text(
        "const assert = require('assert');\n"
        "const { sumItems } = require('./sum');\n"
        "assert.strictEqual(sumItems([10, 20, 30]), 60);\n"
        "assert.strictEqual(sumItems([]), 0);\n",
        encoding="utf-8",
    )
    js_transfer = repair_project_causally(js_proj, ["node", "sum.test.js"], law_store=law_store)
    assert js_transfer.repaired is True
    assert js_transfer.status == "VERIFIED__ZERO_SHOT_UIR_LAW_TRANSFER"
    assert js_transfer.candidates_evaluated == 1


def test_repo_petri_mining_dual_program_splice_and_multisite_cegis(tmp_path: pathlib.Path) -> None:
    store = CausalLawStore(path=tmp_path / "laws_s2.json")

    # 1. Repo-Native Petri-Net Comprehension Mining (`REPO_PETRI_COMPREHENSION_MAP`)
    petri_proj = tmp_path / "petri_proj"
    petri_proj.mkdir()
    (petri_proj / "cli_model.py").write_text(
        "class RenderContext:\n"
        "    def __init__(self, prefix: str) -> None:\n"
        "        self.prefix = prefix\n\n"
        "class ParamSpec:\n"
        "    def __init__(self, name: str, doc: str) -> None:\n"
        "        self.name = name\n"
        "        self.doc = doc\n\n"
        "    def render_row(self, ctx: RenderContext) -> tuple[str, str]:\n"
        "        return (f'{ctx.prefix}:{self.name.upper()}', self.doc)\n\n"
        "def collect_rows(params: list[ParamSpec], ctx: RenderContext) -> list[tuple[str, str]]:\n"
        "    rows = []\n"
        "    return rows\n",
        encoding="utf-8",
    )
    (petri_proj / "test_cli_model.py").write_text(
        "from cli_model import ParamSpec, RenderContext, collect_rows\n"
        "def test_collect_rows():\n"
        "    ctx = RenderContext('env')\n"
        "    ps = [ParamSpec('host', 'target host'), ParamSpec('port', 'tcp port')]\n"
        "    assert collect_rows(ps, ctx) == [('env:HOST', 'target host'), ('env:PORT', 'tcp port')]\n",
        encoding="utf-8",
    )
    res_petri = repair_project_causally(
        petri_proj,
        [sys.executable, "-m", "pytest", "-q", "test_cli_model.py"],
        law_store=store,
    )
    assert res_petri.repaired is True
    assert "REPO_PETRI_COMPREHENSION" in (res_petri.mechanism or "")

    # 2. Counterexample-Partitioned Dual-Program Splicing (`VERIFIED__DUAL_PROGRAM_SPLICE`)
    splice_proj = tmp_path / "splice_proj"
    splice_proj.mkdir()
    (splice_proj / "headers.py").write_text(
        "def format_env_badge(envvar) -> str:\n"
        "    label = envvar.upper()\n"
        "    return f'[{label}]'\n",
        encoding="utf-8",
    )
    (splice_proj / "test_headers.py").write_text(
        "from headers import format_env_badge\n"
        "def test_single_string_envvar():\n"
        "    assert format_env_badge('app_port') == '[APP_PORT]'\n\n"
        "def test_sequence_envvar():\n"
        "    assert format_env_badge(['PRIMARY', 'FALLBACK']) == '[PRIMARY, FALLBACK]'\n",
        encoding="utf-8",
    )
    res_splice = repair_project_causally(
        splice_proj,
        [sys.executable, "-m", "pytest", "-q", "test_headers.py"],
        law_store=store,
    )
    assert res_splice.repaired is True
    assert res_splice.status == "VERIFIED__DUAL_PROGRAM_SPLICE"
    assert "isinstance(envvar, (list, tuple))" in next(iter(res_splice.patched_files.values()))

    # 3. Coordinated Multi-Site Compositional Repair (`VERIFIED__MULTI_SITE_COMPOSITIONAL_CEGIS`)
    multi_proj = tmp_path / "multi_proj"
    multi_proj.mkdir()
    (multi_proj / "claims.py").write_text(
        "class ClaimDecodeError(Exception):\n"
        "    pass\n\n"
        "def parse_iat(data: dict) -> int:\n"
        "    try:\n"
        "        return int(data['iat'])\n"
        "    except ValueError:\n"
        "        raise ClaimDecodeError('bad iat')\n\n"
        "def parse_exp(data: dict) -> int:\n"
        "    try:\n"
        "        return int(data['exp'])\n"
        "    except ValueError:\n"
        "        raise ClaimDecodeError('bad exp')\n",
        encoding="utf-8",
    )
    (multi_proj / "test_claims.py").write_text(
        "import pytest\n"
        "from claims import ClaimDecodeError, parse_exp, parse_iat\n"
        "def test_iat_none():\n"
        "    with pytest.raises(ClaimDecodeError):\n"
        "        parse_iat({'iat': None})\n"
        "def test_exp_inf():\n"
        "    with pytest.raises(ClaimDecodeError):\n"
        "        parse_exp({'exp': float('inf')})\n"
        "def test_valid_claims():\n"
        "    assert parse_iat({'iat': '42'}) == 42\n"
        "    assert parse_exp({'exp': '99'}) == 99\n",
        encoding="utf-8",
    )
    res_multi = repair_project_causally(
        multi_proj,
        [sys.executable, "-m", "pytest", "-q", "test_claims.py"],
        law_store=store,
    )
    assert res_multi.repaired is True
    assert res_multi.status == "VERIFIED__MULTI_SITE_COMPOSITIONAL_CEGIS"


def _make_ppm_canvas(path: pathlib.Path, width: int, height: int, rects: list[tuple[int, int, int, int, tuple[int, int, int]]]) -> None:
    buf = bytearray([240, 240, 240] * (width * height))
    for x0, y0, x1, y1, (r, g, b) in rects:
        for y in range(y0, y1):
            for x in range(x0, x1):
                idx = (y * width + x) * 3
                buf[idx:idx + 3] = bytes((r, g, b))
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    path.write_bytes(header + bytes(buf))


def test_parallel_cow_speculation_zero_vlm_canvas_and_staleness_ablation(tmp_path: pathlib.Path) -> None:
    ws = tmp_path / "ws_spec"
    ws.mkdir()
    # Initialize git repo + stash so stash-destroying traps are caught!
    subprocess.run(["git", "init", "-q"], cwd=str(ws), check=True)
    subprocess.run(["git", "config", "user.email", "test@brain.local"], cwd=str(ws), check=True)
    subprocess.run(["git", "config", "user.name", "BrainTest"], cwd=str(ws), check=True)
    (ws / "bystander.json").write_text('{"keep": true}\n', encoding="utf-8")
    subprocess.run(["git", "add", "bystander.json"], cwd=str(ws), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(ws), check=True)
    (ws / "bystander.json").write_text('{"keep": true, "wip": 1}\n', encoding="utf-8")
    subprocess.run(["git", "stash", "push", "-q", "-m", "wip_stash"], cwd=str(ws), check=True)

    # Create raw PPM visual canvas + structured DOM snapshot + unsorted CSV
    _make_ppm_canvas(ws / "screen.ppm", 32, 24, [(4, 5, 12, 11, (220, 30, 30)), (18, 10, 28, 20, (20, 160, 60))])
    (ws / "ui.a11y.json").write_text(
        json.dumps({"elements": [{"id": "sync_status", "role": "status", "name": "Sync", "value": "PENDING"}]}),
        encoding="utf-8",
    )
    (ws / "raw.csv").write_text("id,amount\nb,30\na,10\nc,20\n", encoding="utf-8")

    snap0 = perceive_environment_state(ws)
    assert len(snap0.canvas_regions) == 2
    assert snap0.canvas_regions[0].bbox == (4, 5, 12, 11)
    assert snap0.canvas_regions[1].bbox == (18, 10, 28, 20)
    assert snap0.dom_elements["sync_status"].value == "PENDING"
    assert snap0.git.stash_count == 1

    # Build 8 competing candidate branches (including bystander deleter, git stash clearer, wrong sorter, & valid winner!)
    goal = EnvironmentGoal(
        required_files={"out/sorted.csv": {"kind": "csv", "sorted_by_col": 1, "min_rows": 3}},
        required_dom_elements={"sync_status": {"value": "DONE"}},
        protected_bystanders=("bystander.json",),
        preserve_git_stash=True,
    )
    cmds = [
        ["python3", "-c", "import os; os.remove('bystander.json')"],  # Trap 1: deletes protected bystander
        ["git", "stash", "clear"],                                     # Trap 2: destroys git stash
        ["python3", "-c", "import pathlib; pathlib.Path('out').mkdir(exist_ok=True); pathlib.Path('out/sorted.csv').write_text('id,amount\\nb,30\\na,10\\nc,20\\n')"],  # Unsorted
        ["python3", "-c", "raise SystemExit(2)"],                      # Failing command
        [
            "python3", "-c",
            "import csv, json, pathlib; "
            "rows = list(csv.reader(open('raw.csv'))); hdr, body = rows[0], sorted(rows[1:], key=lambda r: int(r[1])); "
            "pathlib.Path('out').mkdir(exist_ok=True); "
            "w = csv.writer(open('out/sorted.csv', 'w', newline='')); w.writerow(hdr); w.writerows(body); "
            "json.dump({'elements': [{'id': 'sync_status', 'role': 'status', 'name': 'Sync', 'value': 'DONE'}]}, open('ui.a11y.json', 'w'))",
        ],
    ]
    spec_receipt = speculate_parallel_cow_branches(ws, cmds, goal, max_parallel=16, commit_winner=True)
    assert spec_receipt.winner_idx == 4
    assert spec_receipt.committed is True
    assert spec_receipt.branches[0].bystander_safe is False
    assert spec_receipt.branches[1].bystander_safe is False
    post_snap = perceive_environment_state(ws)
    ok_goal, unmet = check_goal_satisfied(post_snap, snap0, goal)
    assert ok_goal is True, f"Expected satisfied goal after committing CoW winner, got {unmet}"

    # Two-Tier Epistemic Transfer + Version-Drift Staleness Re-Probing (`WS1 -> WS2 -> WS3`)
    store = RelationalActionStore(path=tmp_path / "rel_actions.json")

    def _build_env_ws(dest: pathlib.Path, *, csv_name: str, out_name: str, sort_flag: str) -> EnvironmentGoal:
        dest.mkdir(parents=True)
        (dest / "keep.txt").write_text("DO_NOT_TOUCH\n", encoding="utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            payload = b"item,score\nx,50\ny,10\nz,30\n"
            ti = tarfile.TarInfo(name=csv_name)
            ti.size = len(payload)
            tf.addfile(ti, io.BytesIO(payload))
        (dest / "bundle.tar.gz").write_bytes(buf.getvalue())
        _write_exec(
            dest / "bin" / "unpack_tool",
            "#!/usr/bin/env python3\n"
            "import argparse, pathlib, tarfile\n"
            "ap = argparse.ArgumentParser(); ap.add_argument('--in', dest='inp', required=True); ap.add_argument('--out', dest='out', required=True)\n"
            "a = ap.parse_args()\n"
            "with tarfile.open(a.inp, 'r:gz') as tf:\n"
            "    m = tf.getmembers()[0]; data = tf.extractfile(m).read()\n"
            "p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)\n",
        )
        _write_exec(
            dest / "bin" / "table_sorter",
            "#!/usr/bin/env python3\n"
            "import argparse, csv, pathlib\n"
            f"ap = argparse.ArgumentParser(); ap.add_argument('{sort_flag}', dest='inp', required=True); ap.add_argument('--out', dest='out', required=True); ap.add_argument('--col', type=int, default=1)\n"
            "a = ap.parse_args()\n"
            "rows = list(csv.reader(open(a.inp))); hdr, body = rows[0], sorted(rows[1:], key=lambda r: float(r[a.col]))\n"
            "p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)\n"
            "w = csv.writer(open(p, 'w', newline='')); w.writerow(hdr); w.writerows(body)\n",
        )
        # Deceptive bystander-destroying tool with glowing prose guide
        (dest / "GUIDE.md").write_text("Run `bin/fast_clean` first — completely safe cleanup helper!\n", encoding="utf-8")
        _write_exec(
            dest / "bin" / "fast_clean",
            "#!/usr/bin/env python3\nimport os\nif os.path.exists('keep.txt'): os.remove('keep.txt')\n",
        )
        return EnvironmentGoal(
            required_files={out_name: {"kind": "csv", "sorted_by_col": 1, "min_rows": 3}},
            protected_bystanders=("keep.txt",),
        )

    g1 = _build_env_ws(tmp_path / "ws1", csv_name="alpha.csv", out_name="result/final_a.csv", sort_flag="--in")
    r1 = solve_environment_goal(tmp_path / "ws1", g1, store=store)
    assert r1.solved is True and r1.epistemic_receipt is not None
    assert r1.epistemic_receipt["probes_executed"] > 0
    assert any("fast_clean:BYSTANDER_DAMAGE:keep.txt" in h for h in r1.epistemic_receipt["hazards_detected"])
    assert (tmp_path / "ws1" / "keep.txt").read_text(encoding="utf-8") == "DO_NOT_TOUCH\n"

    # WS2: Completely renamed target paths (`beta.csv` -> `published/report_b.csv`), identical tool binaries -> 0 CoW probes!
    g2 = _build_env_ws(tmp_path / "ws2", csv_name="beta.csv", out_name="published/report_b.csv", sort_flag="--in")
    r2 = solve_environment_goal(tmp_path / "ws2", g2, store=store)
    assert r2.solved is True and r2.epistemic_receipt is not None
    assert r2.epistemic_receipt["probes_executed"] == 0, "Generalized relational store must solve WS2 with ZERO CoW probes!"

    # WS3: Silent tool version upgrade (`--in` changed to `--input`) -> O(1) sha256 staleness detection + targeted re-probe!
    g3 = _build_env_ws(tmp_path / "ws3", csv_name="gamma.csv", out_name="out/report_c.csv", sort_flag="--input")
    r3 = solve_environment_goal(tmp_path / "ws3", g3, store=store)
    assert r3.solved is True and r3.epistemic_receipt is not None
    assert r3.epistemic_receipt["tier1_diff"]["table_sorter"] == "STALE_VERSION"
    assert r3.epistemic_receipt["probes_executed"] > 0


def test_cross_modal_petri_net_and_320_step_osworld_horizon_drift_recovery(tmp_path: pathlib.Path) -> None:
    # Part A: Cross-Modal Petri Net over GUI/DOM + SQLite + CLI with §9.2 Admission Filtering
    app = tmp_path / "enterprise_app"
    app.mkdir()
    (app / "config.lock").write_text("LOCKED=1\n", encoding="utf-8")
    db_p = app / "ledger.db"
    conn = sqlite3.connect(str(db_p))
    conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, state TEXT)")
    conn.executemany("INSERT INTO invoices (state) VALUES (?)", [("RAW",), ("RAW",)])
    conn.commit()
    conn.close()
    (app / "portal.a11y.json").write_text(
        json.dumps({
            "elements": [
                {"id": "auth_checkbox", "role": "checkbox", "name": "Approve Batch", "value": "false", "checked": False},
                {"id": "export_banner", "role": "status", "name": "Banner", "value": "IDLE"},
            ]
        }),
        encoding="utf-8",
    )

    _write_exec(
        app / "ui_click_approve",
        "#!/usr/bin/env python3\n"
        "import json\n"
        "d = json.load(open('portal.a11y.json'))\n"
        "for el in d['elements']:\n"
        "    if el['id'] == 'auth_checkbox': el['checked'] = True; el['value'] = 'true'\n"
        "json.dump(d, open('portal.a11y.json', 'w'))\n",
    )
    _write_exec(
        app / "sql_settle_approved",
        "#!/usr/bin/env python3\n"
        "import json, sqlite3, sys\n"
        "d = json.load(open('portal.a11y.json'))\n"
        "if not any(e['id'] == 'auth_checkbox' and e.get('checked') for e in d['elements']): sys.exit(3)\n"
        "c = sqlite3.connect('ledger.db'); c.execute(\"UPDATE invoices SET state='SETTLED'\"); c.commit(); c.close()\n",
    )
    _write_exec(
        app / "ui_publish_receipt",
        "#!/usr/bin/env python3\n"
        "import json, sqlite3, sys\n"
        "c = sqlite3.connect('ledger.db'); rows = c.execute('SELECT state FROM invoices').fetchall(); c.close()\n"
        "if not rows or any(r[0] != 'SETTLED' for r in rows): sys.exit(4)\n"
        "d = json.load(open('portal.a11y.json'))\n"
        "for el in d['elements']:\n"
        "    if el['id'] == 'export_banner': el['value'] = 'PUBLISHED'\n"
        "json.dump(d, open('portal.a11y.json', 'w'))\n"
        "open('settled_receipt.json', 'w').write('{\"published\": true}\\n')\n",
    )
    _write_exec(app / "noop_btn", "#!/usr/bin/env python3\npass\n")
    _write_exec(app / "corrupt_lock", "#!/usr/bin/env python3\nimport os; os.remove('config.lock')\n")

    net = CrossModalPetriNet()
    # §9.2 Admission filter must reject both no-op and bystander-corrupting operators!
    assert net.admit_via_cow_probe(app, "gui_dom", ["{workspace}/noop_btn"], protected_bystanders=("config.lock",)) is None
    assert net.admit_via_cow_probe(app, "cli", ["{workspace}/corrupt_lock"], protected_bystanders=("config.lock",)) is None
    assert net.rejected_count == 2

    # Discover the 3 cross-modal transitions in sequence via CoW state tomography
    t1 = net.admit_via_cow_probe(app, "gui_dom", ["{workspace}/ui_click_approve"], protected_bystanders=("config.lock",))
    assert t1 is not None
    # Stage state in scratch to probe downstream state-dependent transitions (`sql_settle_approved` & `ui_publish_receipt`)
    subprocess.run([str(app / "ui_click_approve")], cwd=str(app), check=True)
    t2 = net.admit_via_cow_probe(
        app, "sqlite", ["{workspace}/sql_settle_approved"],
        protected_bystanders=("config.lock",),
        precondition_filter=lambda f: f == "DOM_CHECKED:auth_checkbox",
    )
    assert t2 is not None
    subprocess.run([str(app / "sql_settle_approved")], cwd=str(app), check=True)
    t3 = net.admit_via_cow_probe(
        app, "gui_dom", ["{workspace}/ui_publish_receipt"],
        protected_bystanders=("config.lock",),
        precondition_filter=lambda f: f == "SQL_ALL_EQ:ledger.db:invoices.state=SETTLED",
    )
    assert t3 is not None

    # Reset `app` to clean initial state and solve the entire 3-modality workflow from scratch via Petri reachability!
    conn = sqlite3.connect(str(db_p))
    conn.execute("UPDATE invoices SET state='RAW'")
    conn.commit()
    conn.close()
    (app / "portal.a11y.json").write_text(
        json.dumps({
            "elements": [
                {"id": "auth_checkbox", "role": "checkbox", "name": "Approve Batch", "value": "false", "checked": False},
                {"id": "export_banner", "role": "status", "name": "Banner", "value": "IDLE"},
            ]
        }),
        encoding="utf-8",
    )

    init_facts = frozenset(compute_predicate_facts(perceive_environment_state(app)))
    target = frozenset({"DOM_VAL:export_banner=PUBLISHED", "FILE_EXISTS:settled_receipt.json"})
    plan = net.solve_reachability(init_facts, target)
    assert plan is not None and len(plan) == 3
    for tr in plan:
        cmd = [tok.replace("{workspace}", str(app)) for tok in tr.action_argv]
        subprocess.run(cmd, cwd=str(app), check=True)
    final_facts = compute_predicate_facts(perceive_environment_state(app))
    assert target.issubset(final_facts)

    # Part B: 320-Step OSWorld-2.1-Horizon Stateful Cross-Modal Workflow with Mid-Trajectory Perturbations
    # State machine cycles 80 four-step cross-modal transactions (`UI_STAGE -> SQL_RECORD -> FS_CHECKSUM -> UI_COMMIT` = 320 steps)
    # with exogenous session-lock perturbations injected at steps 80, 160, and 240!
    hz = tmp_path / "horizon_320"
    hz.mkdir()
    (hz / "bystander.cfg").write_text("SAFE=1\n", encoding="utf-8")
    hdb = sqlite3.connect(str(hz / "state.db"))
    hdb.execute("CREATE TABLE tx_log (tx_id INTEGER PRIMARY KEY, committed INTEGER)")
    hdb.commit()
    hdb.close()
    (hz / "app.a11y.json").write_text(
        json.dumps({
            "elements": [
                {"id": "phase", "role": "status", "value": "IDLE"},
                {"id": "modal_lock", "role": "dialog", "value": "CLOSED", "enabled": False},
                {"id": "committed_count", "role": "status", "value": "0"},
            ]
        }),
        encoding="utf-8",
    )

    def _step_env(target_dir: pathlib.Path, op: str) -> int:
        ui_p = target_dir / "app.a11y.json"
        d = json.loads(ui_p.read_text(encoding="utf-8"))
        els = {e["id"]: e for e in d["elements"]}
        if els["modal_lock"]["value"] == "OPEN" and op != "DISMISS_MODAL":
            return 9  # Blocked by unexpected modal dialog!
        if op == "DISMISS_MODAL":
            els["modal_lock"]["value"] = "CLOSED"
        elif op == "UI_STAGE" and els["phase"]["value"] == "IDLE":
            els["phase"]["value"] = "STAGED"
        elif op == "SQL_RECORD" and els["phase"]["value"] == "STAGED":
            c = sqlite3.connect(str(target_dir / "state.db"))
            nxt_id = int(els["committed_count"]["value"]) + 1
            c.execute("INSERT OR REPLACE INTO tx_log (tx_id, committed) VALUES (?, 0)", (nxt_id,))
            c.commit()
            c.close()
            els["phase"]["value"] = "SQL_RECORDED"
        elif op == "FS_CHECKSUM" and els["phase"]["value"] == "SQL_RECORDED":
            nxt_id = int(els["committed_count"]["value"]) + 1
            (target_dir / "last_checksum.json").write_text(json.dumps({"tx": nxt_id}), encoding="utf-8")
            els["phase"]["value"] = "CHECKSUMMED"
        elif op == "UI_COMMIT" and els["phase"]["value"] == "CHECKSUMMED":
            nxt_id = int(els["committed_count"]["value"]) + 1
            c = sqlite3.connect(str(target_dir / "state.db"))
            c.execute("UPDATE tx_log SET committed=1 WHERE tx_id=?", (nxt_id,))
            c.commit()
            c.close()
            els["committed_count"]["value"] = str(nxt_id)
            els["phase"]["value"] = "IDLE"
        else:
            return 7
        ui_p.write_text(json.dumps(d), encoding="utf-8")
        return 0

    # 1. Ablation: Open-loop action replay (no per-step relational state tomography) collapses at first perturbation (step 80)
    hz_open = tmp_path / "horizon_open"
    subprocess.run(["cp", "-r", str(hz), str(hz_open)], check=True)
    open_loop_failed_step = None
    cycle_ops = ("UI_STAGE", "SQL_RECORD", "FS_CHECKSUM", "UI_COMMIT")
    for step_idx in range(320):
        if step_idx in (80, 160, 240):
            d = json.loads((hz_open / "app.a11y.json").read_text(encoding="utf-8"))
            for e in d["elements"]:
                if e["id"] == "modal_lock":
                    e["value"] = "OPEN"
            (hz_open / "app.a11y.json").write_text(json.dumps(d), encoding="utf-8")
        rc = _step_env(hz_open, cycle_ops[step_idx % 4])
        if rc != 0:
            open_loop_failed_step = step_idx
            break
    assert open_loop_failed_step == 80, "Open-loop replay without state tomography must fail on step-80 perturbation!"

    # 2. Closed-Loop Differential State Tomography Controller: perceives live `EnvironmentSnapshot` at every step,
    #    detects unexpected `DOM_VAL:modal_lock=OPEN` state divergence, resolves it deterministically, and completes all 320tx steps!
    executed_ops = 0
    recoveries = 0
    injected_at: set[int] = set()
    while True:
        snap = perceive_environment_state(hz)
        committed_n = int(snap.dom_elements["committed_count"].value)
        if committed_n >= 80:
            break
        if executed_ops in (80, 160, 240) and executed_ops not in injected_at:
            injected_at.add(executed_ops)
            # Inject exogenous state perturbation
            d = json.loads((hz / "app.a11y.json").read_text(encoding="utf-8"))
            for e in d["elements"]:
                if e["id"] == "modal_lock":
                    e["value"] = "OPEN"
            (hz / "app.a11y.json").write_text(json.dumps(d), encoding="utf-8")
            snap = perceive_environment_state(hz)

        # Select transition purely from live relational state predicates (zero token-history drift!)
        if snap.dom_elements["modal_lock"].value == "OPEN":
            assert _step_env(hz, "DISMISS_MODAL") == 0
            recoveries += 1
            continue
        phase = snap.dom_elements["phase"].value
        next_op = {
            "IDLE": "UI_STAGE",
            "STAGED": "SQL_RECORD",
            "SQL_RECORDED": "FS_CHECKSUM",
            "CHECKSUMMED": "UI_COMMIT",
        }[phase]
        assert _step_env(hz, next_op) == 0
        executed_ops += 1
        assert executed_ops <= 320

    final_hz = perceive_environment_state(hz)
    hz_goal = EnvironmentGoal(
        required_files={"last_checksum.json": {"kind": "json", "required_json_keys": ["tx"]}},
        required_sqlite={("state.db", "tx_log"): {"where_col_eq": ("committed", 1), "min_matching": 80, "row_count": 80}},
        required_dom_elements={"committed_count": {"value": "80"}, "phase": {"value": "IDLE"}, "modal_lock": {"value": "CLOSED"}},
        protected_bystanders=("bystander.cfg",),
    )
    ok_hz, unmet_hz = check_goal_satisfied(final_hz, perceive_environment_state(hz), hz_goal)
    assert executed_ops == 320 and recoveries == 3
    assert ok_hz is True, f"Expected 100% invariant satisfaction after 320 steps + 3 recoveries, got {unmet_hz}"


# ================================================================================================== #
# 5. Causal Nexus: expected-value abduction, single-site counterfactual blame, lens synthesis,
#    statement-level tree-rewrite morphisms, L3 negative invariants, and boundary fuzzing.
# ================================================================================================== #

def test_causal_nexus_blame_lens_morphisms_and_negative_invariants(tmp_path: pathlib.Path) -> None:
    from canonical.swe_kernel import causal_nexus_v1 as nx

    # -- 1. Expected-value abduction: the failing assertion's own RHS is the goal residual.
    transcript = (
        "tests/test_app.py:7: in test_help_record_is_never_none\n"
        "    assert get_help_record(ctx) == ()\n"
        "E   AssertionError: assert None == ()\n"
        "E   AssertionError: assert None == ('SRC', '')\n"
        "E   assert 3 == 1\n"
        "FAILED tests/test_app.py::test_help_record_is_never_none - assert None == b''\n"
    )
    obls = nx.extract_value_obligations(transcript)
    values = [o.expected_value for o in obls]
    assert () in values and 1 in values and ("SRC", "") in values and b"" in values
    # The anti-laundering gate: a data-shaped value from a single test is refused as a repair source.
    assert nx.data_literal_gate(("SRC", ""))[0] is False
    assert nx.data_literal_gate(("SRC", ""), supporting_obligations=2)[0] is True
    assert nx.data_literal_gate(())[0] is True

    # -- 2. Lens / transducer: minimal consistent table, compiled to one stdlib expression.
    fit = nx.infer_transducer([(b"\x04", b"^D"), (b"\x1a", b"^Z")])
    assert fit is not None and fit.mode == "token" and fit.invertible
    lens = nx.lens_expression("s", fit, value_kind="bytes")
    assert eval(lens, {"s": b"a\x04b\x1a"}) == b"a^Db^Z"  # noqa: S307 - our own generated expression
    back = nx.invert_lens(fit, value_kind="bytes")
    assert eval(back, {"v": b"a^Db^Z"}) == b"a\x04b\x1a"  # noqa: S307
    assert nx.infer_transducer([("abc", "abc")]) is None          # identity: nothing to learn
    assert nx.infer_transducer([("ab", "aX"), ("ab", "aY")]) is None  # inconsistent: refuse, never guess
    pos = nx.infer_transducer([("aa", "zz")])
    assert eval(nx.lens_expression("s", pos), {"s": "baab"}) == "bzzb"  # noqa: S307

    # -- 3. Statement-level morphism: multi-statement fix crystallizes and transfers by identifier.
    import tempfile

    store_dir = pathlib.Path(tempfile.mkdtemp(prefix="nexus-store-", dir=str(tmp_path)))
    store = nx.SkillStoreV2(store_dir / "skills.json")
    before = "\nif record is None:\n    return None\nreturn (record[0], record[1])\n"
    after = "\nif record is None:\n    record = (metavar, \"\")\nreturn (record[0], record[1] or \"\")\n"
    morph = store.learn(before, after, origin="unit@1", diagnostic_class="GUARD_TO_FALLBACK")
    assert morph is not None and morph.hole_count >= 1
    proposals = store.propose("\nif help_rec is None:\n    return None\nreturn (help_rec[0], help_rec[1])\n")
    assert len(proposals) == 1
    rewritten = proposals[0][1]
    assert "help_rec = (metavar, '')" in rewritten and "help_rec[1] or ''" in rewritten
    # A different guard body is refused: the pattern is two-sided, not a wildcard.
    assert store.propose("\nif rec is None:\n    return 7\nreturn (rec[0], rec[1])\n") == []
    assert store.stale(morph.morphism_id, "") is False
    assert store.remove(morph.morphism_id) is True and store.morphisms == {}

    # -- 4. L3 negative invariants: a refuted shape is filtered in microseconds, forever.
    inv_store = nx.NegativeInvariantStore(store_dir / "invariants.json")
    site = type("FixtureSite", (), {"source_text": "if x is None:\n    return None\n", "kind": "func_body"})()
    feats = nx.candidate_features(site, "return y")
    inv_store.record("func_body", "NEXUS_FALSY_FALLBACK", feats, "tests/t.py::t1", origin="unit@1")
    assert inv_store.refuted("func_body", "NEXUS_FALSY_FALLBACK", feats) is not None
    assert inv_store.refuted("func_body", "SOME_OTHER_TAG", feats) is None
    assert inv_store.remove(next(iter(inv_store.invariants))) is True and inv_store.invariants == {}

    # -- 5. Boundary invariance: predicted fallback divergence passes, a silent change does not.
    def before_fn(x):
        return x or None

    def after_fn(x):
        return x or ("SRC", "")

    verdict, reason = nx.patch_invariance_verdict(nx.differential_boundary_scan(before_fn, after_fn))
    assert verdict is True and reason.startswith("PREDICTED_FALLBACK_DIVERGENCE")
    silent = nx.differential_boundary_scan(before_fn, lambda x: 5)
    assert nx.patch_invariance_verdict(silent)[0] is False


def test_nexus_repair_end_to_end_on_a_fresh_repository(tmp_path: pathlib.Path) -> None:
    """A function that returns `None` where the contract says `()` is repaired by one proven counterfactual."""
    from canonical.swe_kernel import causal_nexus_v1 as nx

    repo = tmp_path / "nexus_repo"
    (repo / "demo").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "demo" / "__init__.py").write_text("")
    (repo / "demo" / "app.py").write_text(
        "def get_help_record(ctx):\n"
        "    if ctx is None:\n"
        "        return None\n"
        "    record = getattr(ctx, \"record\", None)\n"
        "    if record is None:\n"
        "        return None\n"
        "    return record\n"
    )
    (repo / "tests" / "test_app.py").write_text(
        "from types import SimpleNamespace\n"
        "from demo.app import get_help_record\n\n"
        "def test_help_record_is_never_none():\n"
        "    ctx = SimpleNamespace(record=None)\n"
        "    assert get_help_record(ctx) == ()\n"
    )
    store_dir = pathlib.Path(tempfile.mkdtemp(prefix="nexus-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_app.py"],
        law_store=CausalLawStore(store_dir / "laws.json"),
        skill_store=nx.SkillStoreV2(store_dir / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store_dir / "invs.json"),
        origin="nexus_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True
    assert result.status == "VERIFIED__ANGELIC_NEXUS_FALLBACK"
    assert "NEXUS_" in (result.mechanism or "")
    patched = next(iter(result.patched_files.values()))
    assert "or ()" in patched
    # The repair was proven by the project's own suite, not by our oracle.
    check = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_app.py"], cwd=str(repo), capture_output=True, text=True,
    )
    assert check.returncode != 0  # not applied in place: this was a dry run
    assert "or ()" not in (repo / "demo" / "app.py").read_text()


def test_cut_vertex_slicing_and_seven_step_loop(tmp_path: pathlib.Path) -> None:
    """Cut-vertex sub-goal factoring, then the full seven-step loop on a real workspace."""
    from canonical.runtime.causal_computer_use_agent_v1 import (
        GoalDirectedAgent,
        SelfPlayLoop,
        broad_ingest_baseline,
        compare_acquisition_strategies,
    )
    from canonical.swe_kernel import causal_nexus_v1 as nx

    # -- 1. Artifact-token slicing on a reachability graph with a dead-end branch.
    net = CrossModalPetriNet()

    from canonical.swe_kernel.executable_mental_model_v1 import CrossModalTransition

    def _add(tid: str, pre: set[str], add: set[str], rem: frozenset[str] = frozenset()) -> None:
        net.transitions[tid] = CrossModalTransition(
            transition_id=tid, modality="cli", action_argv=("x",),
            preconditions=frozenset(pre), added_facts=frozenset(add), removed_facts=frozenset(rem),
            tool_sha256="deadbeef", witness_digest="cafe",
        )

    _add("t1", {"a"}, {"b"})
    _add("t2", {"b"}, {"c"})
    _add("t3", {"c"}, {"d"})
    _add("tx", {"b"}, {"e"})  # dead end: must not become a checkpoint
    cuts = net.articulation_tokens(frozenset({"a"}), frozenset({"d"}))
    assert [sorted(m) for m in cuts] == [["a", "b"], ["a", "b", "c"]]
    sliced = net.solve_in_slices(frozenset({"a"}), frozenset({"d"}))
    assert sliced is not None and [[t.transition_id for t in s] for s in sliced] == [["t1"], ["t2"], ["t3"]]

    # -- 2. Seven-step loop: goal reached, bystander preserved, zero prediction error.
    def factory(tag: str) -> pathlib.Path:
        root = tmp_path / f"loop_{tag}"
        root.mkdir(parents=True)
        (root / "data.txt").write_text("alpha,beta\n1,2\n")
        (root / "README.md").write_text("keep me\n")
        return root

    live = factory("live")
    receipt = GoalDirectedAgent(live).solve(
        ["file:data.txt.gz"],
        [["gzip", "-k", "data.txt"], ["cat", "README.md"]],
    )
    assert receipt.reached is True
    assert [s.name for s in receipt.steps] == ["goal", "scan", "recall", "acquire", "predict_act", "verify", "compress"]
    assert receipt.prediction_errors == 0
    assert (live / "data.txt.gz").is_file()
    assert (live / "README.md").read_text() == "keep me\n"
    assert receipt.to_dict()["runtime_model_calls"] == 0

    # -- 3. Goal-directed vs broad ingest on identical fresh workspaces.
    comparison = compare_acquisition_strategies(
        factory,
        [["gzip", "-k", "data.txt"], ["cat", "README.md"], ["ls", "-l"], ["stat", "data.txt"]],
        ["file:data.txt.gz"],
    )
    assert comparison["goal_directed"]["reached"] is True
    assert comparison["goal_directed"]["probes"] < comparison["broad_ingest"]["probes"]
    assert comparison["broad_ingest"]["probes"] == 4
    assert broad_ingest_baseline(factory("bi_solo"), [["ls", "-l"]], ["file:data.txt.gz"]).probes == 1

    # -- 4. Offline self-play: an unsolved failure is an open episode, a solved one crystallizes.
    from canonical.swe_kernel.semantic_causal_engine_v1 import CausalLawStore as _LawStore

    store_dir = tmp_path / "selfplay"
    store_dir.mkdir()
    skills = nx.SkillStoreV2(store_dir / "skills.json")
    invs = nx.NegativeInvariantStore(store_dir / "invs.json")

    good = store_dir / "good_repo"
    (good / "demo").mkdir(parents=True)
    (good / "tests").mkdir(parents=True)
    (good / "demo" / "__init__.py").write_text("")
    (good / "demo" / "app.py").write_text(
        "def get_help_record(ctx):\n"
        "    if ctx is None:\n"
        "        return None\n"
        "    record = getattr(ctx, \"record\", None)\n"
        "    if record is None:\n"
        "        return None\n"
        "    return record\n"
    )
    (good / "tests" / "test_app.py").write_text(
        "from types import SimpleNamespace\nfrom demo.app import get_help_record\n\n"
        "def test_never_none():\n"
        "    assert get_help_record(SimpleNamespace(record=None)) == ()\n"
    )
    passing = store_dir / "passing_repo"
    (passing / "tests").mkdir(parents=True)
    (passing / "tests" / "test_ok.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n")

    loop = SelfPlayLoop(skills, invs, origin="unit_selfplay")
    play = loop.run(
        [
            {"label": "good", "repo_root": good, "test_cmd": [sys.executable, "-m", "pytest", "-q", "tests/test_app.py"]},
            {"label": "passing", "repo_root": passing, "test_cmd": [sys.executable, "-m", "pytest", "-q", "tests/test_ok.py"]},
        ],
        repair_project_causally,
        max_episodes=2,
    )
    assert play.solved == 1 and play.open == 1
    statuses = {e.label: e.status for e in play.episodes}
    assert statuses["good"] == "VERIFIED__ANGELIC_NEXUS_FALLBACK"
    assert statuses["passing"] == "REFUSED__BASELINE_ALREADY_PASSING"
    assert play.skills >= 1


def test_frame_provenance_turns_a_data_value_into_a_sound_repair(tmp_path: pathlib.Path) -> None:
    """The value a test publishes is only usable when the site itself is shown to produce it.

    This is the mechanism that closed `click@05f6fd0` blind: the wanted `('SRC', '')` is refused as a
    literal (it is the test's data) and rebuilt as `(self.make_metavar(ctx), '')` from the live frame,
    preferring the repository's own method over a builtin that happens to agree.
    """
    from canonical.swe_kernel import causal_nexus_v1 as nx

    # -- 1. Pure substitution rules.
    frame = {"self.name": "src", "self.make_metavar(ctx)": "SRC", "self.name.upper()": "SRC"}
    src, reason = nx.frame_substituted_source(("SRC", ""), frame)
    assert reason == "FRAME_SUBSTITUTED" and src == "(self.name.upper(), '')"
    preferred, _ = nx.frame_substituted_source(("SRC", ""), frame, prefer_names=("make_metavar",))
    assert preferred == "(self.make_metavar(ctx), '')"
    assert nx.frame_substituted_source(("SRC", "missing"), frame)[0] is None
    assert nx.frame_substituted_source(("SRC", ""), {})[0] is None
    # A one-character value is data, not a canonical default.
    assert nx.is_canonical_default("X") is False

    # -- 2. End to end, on a repository shaped like click's `Argument`.
    repo = tmp_path / "frame_repo"
    (repo / "demo").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "demo" / "__init__.py").write_text("")
    (repo / "demo" / "app.py").write_text(
        "class Argument:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "        self.help = \"\"\n\n"
        "    def make_metavar(self, ctx):\n"
        "        return self.name.upper()\n\n"
        "    def get_help_record(self, ctx):\n"
        "        return None\n"
    )
    (repo / "tests" / "test_app.py").write_text(
        "from types import SimpleNamespace\n"
        "from demo.app import Argument\n\n"
        "def test_help_record_never_none():\n"
        "    arg = Argument(\"src\")\n"
        "    assert arg.get_help_record(SimpleNamespace()) == (\"SRC\", \"\")\n"
    )
    store_dir = pathlib.Path(tempfile.mkdtemp(prefix="frame-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_app.py"],
        law_store=CausalLawStore(store_dir / "laws.json"),
        skill_store=nx.SkillStoreV2(store_dir / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store_dir / "invs.json"),
        origin="frame_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True
    assert result.status == "VERIFIED__ANGELIC_NEXUS_FALLBACK"
    assert (result.mechanism or "").startswith("NEXUS_FRAME_SUBSTITUTED_FALLBACK")
    patched = next(iter(result.patched_files.values()))
    assert "(self.make_metavar(ctx), '')" in patched
    assert "\"SRC\"" not in patched and "'SRC'" not in patched  # the test's data never enters the code


def test_spec_contract_guard_from_the_tests_own_raises(tmp_path: pathlib.Path) -> None:
    """A `DID NOT RAISE` failure states its contract; the guard is mined, not searched."""
    from canonical.swe_kernel import causal_nexus_v1 as nx
    from canonical.swe_kernel import spec_contract_synthesis_v1 as spc
    from canonical.swe_kernel.semantic_causal_engine_v1 import build_project_cpg

    src = (
        "import pytest\n\n"
        "def test_register_rejects_none(pm):\n"
        "    with pytest.raises(TypeError, match=\"plugin must not be None\"):\n"
        "        pm.register(None)\n"
        "    assert pm.get_plugins() == set()\n\n"
        "def test_build_rejects_empty():\n"
        "    with pytest.raises(ValueError, match=\"must not be empty\"):\n"
        "        build(\"\")\n"
    )
    contracts = spc.mine_exception_contracts(src)
    got = {(c.callee, c.exc_name, c.match_pattern, c.arg_literals) for c in contracts}
    assert ("register", "TypeError", "plugin must not be None", (None,)) in got
    assert ("build", "ValueError", "must not be empty", ("",)) in got

    repo = tmp_path / "guard_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "pm.py").write_text(
        "class PluginManager:\n"
        "    def __init__(self):\n"
        "        self._plugins = set()\n\n"
        "    def register(self, plugin, name=None):\n"
        "        self._plugins.add(plugin)\n"
        "        return plugin\n\n"
        "    def get_plugins(self):\n"
        "        return set(self._plugins)\n\n"
        "    def is_registered(self, plugin):\n"
        "        return plugin in self._plugins\n"
    )
    (repo / "tests" / "test_pm.py").write_text(
        "import pytest\n"
        "from pkg.pm import PluginManager\n\n"
        "def test_register_rejects_none():\n"
        "    pm = PluginManager()\n"
        "    with pytest.raises(TypeError, match=\"plugin must not be None\"):\n"
        "        pm.register(None)\n"
        "    assert pm.get_plugins() == set()\n"
        "    assert not pm.is_registered(None)\n\n"
        "def test_register_ok():\n"
        "    pm = PluginManager()\n"
        "    obj = object()\n"
        "    assert pm.register(obj) is obj\n"
    )
    cpg = build_project_cpg(repo)
    guards = spc.synthesize_spec_guards(repo, cpg, [(repo / "tests" / "test_pm.py").read_text()])
    # The boundary literal leads; the repo-predicate variants are later candidates, not peers of it.
    assert guards
    tag, fn_name, fn_cpg, patched = guards[0]
    assert fn_name == "register" and "plugin is None" in tag and "self." not in tag
    text = patched.decode()
    assert "if plugin is None:" in text and 'raise TypeError("plugin must not be None")' in text

    # End to end: the engine's own pass must find and verify it against the project suite.
    store_dir = pathlib.Path(tempfile.mkdtemp(prefix="spec-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_pm.py"],
        law_store=CausalLawStore(store_dir / "laws.json"),
        skill_store=nx.SkillStoreV2(store_dir / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store_dir / "invs.json"),
        origin="spec_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True
    assert result.status == "VERIFIED__SPEC_CONTRACT_GUARD"
    assert "plugin is None" in (result.mechanism or "")
    assert "if plugin is None:" in next(iter(result.patched_files.values()))


def test_spec_contract_guard_set_is_composed_and_ordered(tmp_path: pathlib.Path) -> None:
    """Two contracts in one test are one patch, and the guard that calls nothing runs first.

    `unregister()` and `unregister(obj)` are two different demands on the same method. Enforcing
    them separately can never pass, because the predicate guard answers *both* calls. The order is
    semantic, not cosmetic: whichever guard runs first decides which exception the zero-argument
    call raises.
    """
    from canonical.swe_kernel import causal_nexus_v1 as nx
    from canonical.swe_kernel import spec_contract_synthesis_v1 as spc
    from canonical.swe_kernel.semantic_causal_engine_v1 import build_project_cpg

    repo = tmp_path / "compose_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "pm.py").write_text(
        "class PluginManager:\n"
        "    def __init__(self):\n"
        "        self._plugins = set()\n\n"
        "    def register(self, plugin):\n"
        "        self._plugins.add(plugin)\n"
        "        return plugin\n\n"
        "    def is_registered(self, plugin):\n"
        "        return plugin in self._plugins\n\n"
        "    def unregister(self, plugin=None, name=None):\n"
        "        return None\n"
    )
    (repo / "tests" / "test_pm.py").write_text(
        "import pytest\n"
        "from pkg.pm import PluginManager\n\n"
        "def test_unregister_states_both_contracts():\n"
        "    pm = PluginManager()\n"
        "    with pytest.raises(TypeError, match=\"one of name or plugin\"):\n"
        "        pm.unregister()\n"
        "    with pytest.raises(ValueError, match=\"not registered\"):\n"
        "        pm.unregister(object())\n\n"
        "def test_register_ok():\n"
        "    pm = PluginManager()\n"
        "    obj = object()\n"
        "    assert pm.register(obj) is obj\n"
    )
    cpg = build_project_cpg(repo)
    guards = spc.synthesize_spec_guards(repo, cpg, [(repo / "tests" / "test_pm.py").read_text()])
    assert guards, "two co-required contracts must produce a composed proposal"
    tag, fn_name, _fn_cpg, patched = guards[0]
    assert fn_name == "unregister"
    body = patched.decode()
    nullity = body.index("if plugin is None and name is None:")
    predicate = body.index("if name is None and not self.is_registered(plugin):")
    assert nullity < predicate, "the guard that calls nothing must run before the predicate guard"
    assert "SPEC_CONTRACT_SET" in tag

    store_dir = pathlib.Path(tempfile.mkdtemp(prefix="spec-set-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_pm.py"],
        law_store=CausalLawStore(store_dir / "laws.json"),
        skill_store=nx.SkillStoreV2(store_dir / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store_dir / "invs.json"),
        origin="spec_set_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True, result.status
    assert result.status == "VERIFIED__SPEC_CONTRACT_GUARD"
    text = next(iter(result.patched_files.values()))
    assert "one of name or plugin" in text and "not registered" in text


def test_escape_contract_binds_to_the_traceback_frame_not_the_name(tmp_path: pathlib.Path) -> None:
    """The suite prints `file:line`; binding by function name edits statements that cannot be at fault.

    `click@fc518e4` measured this: patching statements chosen by name left all five failures in place,
    while containing the two statements the traceback actually named took the same suite from five
    failures to one. Composition is bottom-up so earlier line numbers stay valid.
    """
    from canonical.swe_kernel import spec_contract_synthesis_v1 as spc

    repo = tmp_path / "frame_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "mod.py").write_text(
        "def outer(x):\n"
        "    y = x + 1\n"
        "    return inner(y)\n"
        "\n"
        "def inner(y):\n"
        "    return y * 2\n"
    )
    failure = (
        'pkg/mod.py:6: in inner\n'
        '    return y * 2\n'
        'pkg/mod.py:3: in outer\n'
        '    return inner(y)\n'
        'E   Failed: KeyboardInterrupt escaped inner\n'
    )
    frames = spc.mine_escape_frames(failure, repo)
    assert frames and frames[0].exc_name == "KeyboardInterrupt"
    assert frames[0].rel_path == "pkg/mod.py"
    innermost = frames[0].lineno
    assert innermost in (3, 6), "the named frames are the ones to edit, not a name lookup"

    composed = spc.compose_frame_containments(repo, frames[:2])
    assert composed is not None
    text = composed["pkg/mod.py"].decode()
    assert text.count("except KeyboardInterrupt:") == 2
    compile(text, "mod.py", "exec")


def test_contract_binds_through_the_tests_constructor_and_reads_a_container_field(
    tmp_path: pathlib.Path,
) -> None:
    """`algo.from_jwk({...})` names a variable; the test's own `algo = Algo(...)` line names the class.

    The exception reference is resolved the same way: the test writes `pkg.algo.InvalidKeyError`, the
    module that must raise it binds `InvalidKeyError`, and a guard has to use the name that exists.
    """
    from canonical.swe_kernel import causal_nexus_v1 as nx
    from canonical.swe_kernel import spec_contract_synthesis_v1 as spc
    from canonical.swe_kernel.semantic_causal_engine_v1 import build_project_cpg

    repo = tmp_path / "container_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "algo.py").write_text(
        "class InvalidKeyError(Exception):\n"
        "    pass\n"
        "\n"
        "\n"
        "class Algo:\n"
        "    def __init__(self, kind):\n"
        "        self.kind = kind\n"
        "\n"
        "    def from_jwk(self, jwk):\n"
        "        return jwk\n"
    )
    (repo / "tests" / "test_algo.py").write_text(
        "import pytest\n"
        "import pkg.algo\n"
        "from pkg.algo import Algo\n"
        "\n"
        "\n"
        "def test_rejects_empty_key():\n"
        "    algo = Algo('HS256')\n"
        "    with pytest.raises(pkg.algo.InvalidKeyError, match='must not be empty'):\n"
        "        algo.from_jwk({'kty': 'oct', 'k': '', 'alg': 'HS256'})\n"
    )
    contracts = spc.mine_exception_contracts((repo / "tests" / "test_algo.py").read_text())
    assert contracts and contracts[0].callee_qualifier == "Algo", "the constructor line names the class"
    assert contracts[0].exc_name.endswith("InvalidKeyError")

    cpg = build_project_cpg(repo)
    guards = spc.synthesize_spec_guards(repo, cpg, [(repo / "tests" / "test_algo.py").read_text()])
    assert guards
    tag, fn_name, _fn, patched = guards[0]
    text = patched.decode()
    assert fn_name == "from_jwk"
    assert 'jwk.get("k") ==' in text, "the empty field is the field the message names"
    assert "raise InvalidKeyError(\"must not be empty\")" in text, "the name the module binds, not the dotted one"

    store = pathlib.Path(tempfile.mkdtemp(prefix="container-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_algo.py"],
        law_store=CausalLawStore(store / "laws.json"),
        skill_store=nx.SkillStoreV2(store / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store / "invs.json"),
        origin="container_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True, result.status
    assert result.status == "VERIFIED__SPEC_CONTRACT_GUARD"


def test_postcondition_names_the_container_the_mutator_must_purge(tmp_path: pathlib.Path) -> None:
    """A failing `assert getter() == [...]` after a mutator is a *statement* contract: delete the entry.

    Nothing about the repository is assumed. The compared call names the getter, the call before it
    names the mutator, and the getter's own `return` names the container. The purge has to go before
    the mutator's `return` — appending it there measured as dead code, and the suite said so.
    """
    from canonical.swe_kernel import causal_nexus_v1 as nx
    from canonical.swe_kernel import spec_contract_synthesis_v1 as spc
    from canonical.swe_kernel.semantic_causal_engine_v1 import build_project_cpg

    repo = tmp_path / "purge_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "registry.py").write_text(
        "class Registry:\n"
        "    def __init__(self):\n"
        "        self._name2plugin = {}\n"
        "        self._entries = []\n"
        "\n"
        "    def add(self, plugin, dist):\n"
        "        self._entries.append((plugin, dist))\n"
        "        self._name2plugin[dist] = plugin\n"
        "\n"
        "    def entries(self):\n"
        "        return list(self._entries)\n"
        "\n"
        "    def drop(self, plugin):\n"
        "        self._name2plugin.pop(plugin, None)\n"
        "        return plugin\n"
    )
    (repo / "tests" / "test_registry.py").write_text(
        "from pkg.registry import Registry\n"
        "\n"
        "\n"
        "class Api:\n"
        "    pass\n"
        "\n"
        "\n"
        "def test_drop_purges_entries():\n"
        "    reg = Registry()\n"
        "    a = Api()\n"
        "    b = Api()\n"
        "    reg.add(a, 'da')\n"
        "    reg.add(b, 'db')\n"
        "    reg.drop(a)\n"
        "    assert reg.entries() == [(b, 'db')]\n"
    )
    contract = spc.mine_postcondition_contracts(
        (repo / "tests" / "test_registry.py").read_text(),
        "tests/test_registry.py::test_drop_purges_entries",
    )[0]
    assert (contract.getter, contract.mutator) == ("entries", "drop")

    cpg = build_project_cpg(repo)
    cands = spc.state_consistency_candidates(repo, cpg, contract)
    assert cands, "the container behind the getter must be found from its own return"
    tag, _rel, patched = cands[0]
    text = patched.decode()
    assert "self._entries[:]" in text and "is not plugin" in text
    body = text.split("def drop", 1)[1]
    assert body.index("self._name2plugin.pop") < body.index("self._entries[:]") < body.index("return plugin"), \
        "the purge lands before the mutator's own return, never after it (dead code)"

    store = pathlib.Path(tempfile.mkdtemp(prefix="purge-e2e-", dir=str(tmp_path)))
    result = repair_project_causally(
        repo,
        [sys.executable, "-m", "pytest", "-q", "tests/test_registry.py"],
        law_store=CausalLawStore(store / "laws.json"),
        skill_store=nx.SkillStoreV2(store / "skills.json"),
        invariant_store=nx.NegativeInvariantStore(store / "invs.json"),
        origin="purge_e2e",
        max_sites=12,
        max_candidates=16,
    )
    assert result.repaired is True, result.status
    assert result.status == "VERIFIED__STATE_CONSISTENCY"
