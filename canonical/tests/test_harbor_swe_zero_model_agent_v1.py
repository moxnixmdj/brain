"""End-to-end tests for Project Brain Zero-Model Harbor SWE Agent V1.

Verifies:
1. Static AST zero-model invariant (no `astra_runtime`, no LLM SDK imports, `PRODUCER_MODEL_CALLS == 0`);
2. Full Harbor transport (`HarborEnvironmentTransport`), command policy enforcement,
   SHA-256 compressed kernel bundle transfer, independent pytest verification cycle,
   `git diff --check` cycle, and `coding_control_kernel_v1.validate_finish` terminal gate;
3. Single-experience cross-container L2 `TreeRewriteMorphism` transfer across two isolated
   git workspaces sharing only the inspectable JSON external skill store.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import pathlib
import subprocess
import sys

from canonical.runtime import harbor_swe_zero_model_agent_v1 as hz
from canonical.runtime.coding_control_kernel_v1 import configuration_fingerprint
from canonical.runtime.harbor_command_policy import validate_environment_command

_FORBIDDEN_IMPORTS = {
    "astra_runtime",
    "openai",
    "anthropic",
    "google",
    "litellm",
    "ollama",
    "vllm",
    "transformers",
    "torch",
    "cohere",
    "mistralai",
    "groq",
}


def _init_git_repo(ws: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=ws, check=True)
    subprocess.run(["git", "add", "."], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=ws, check=True)


def test_harbor_swe_zero_model_agent_has_zero_model_imports() -> None:
    src_path = pathlib.Path(hz.__file__)
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(part in _FORBIDDEN_IMPORTS for part in alias.name.split(".")):
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if any(part in _FORBIDDEN_IMPORTS for part in node.module.split(".")):
                found.append(node.module)
    assert found == [], f"Forbidden model imports detected: {found}"
    assert hz.PRODUCER_MODEL_CALLS == 0
    assert hz.HarborSweZeroModelAgent.name() == "project-brain-swe-zero-model"
    # Verify command policy blocks external acquisition
    for bad in ("curl https://example.com/a", "pip install requests", "git clone https://github.com/x/y.git"):
        try:
            validate_environment_command(bad)
            raise AssertionError(f"Expected ValueError for {bad}")
        except ValueError:
            pass


def test_harbor_swe_zero_model_end_to_end_and_cross_container_l2_transfer(tmp_path: pathlib.Path) -> None:
    """Episode 1 (Container A, cold store) solves a multi-hunk/regex or guard bug and
    crystallizes an L2 TreeRewriteMorphism into the external JSON store;
    Episode 2 (Container B, unseen repo with renamed symbols & preserved comments) solves
    in 1 shot via L2_TREE_REWRITE_MORPHISM_1SHOT over HarborEnvironmentTransport with 0 model calls!
    """
    shared_store = tmp_path / "shared_harbor_l2_store.json"
    extra_pp = ":".join(p for p in sys.path if p)

    # --- Container A (Cold Store): STUN / guard bug in `billing.py` ---
    ws_a = tmp_path / "container_a"
    ws_a.mkdir()
    (ws_a / "billing.py").write_text(
        "# Container A billing helper\n"
        "def compute_fee(amount: float, waived: bool = False) -> float:\n"
        "    if amount > 100:\n"
        "        return 10.0\n"
        "    return 0.0\n",
        encoding="utf-8",
    )
    (ws_a / "test_billing.py").write_text(
        "from billing import compute_fee\n"
        "def test_normal_fee():\n"
        "    assert compute_fee(200.0, waived=False) == 10.0\n"
        "def test_small_fee():\n"
        "    assert compute_fee(50.0, waived=False) == 0.0\n"
        "def test_waived_fee():\n"
        "    assert compute_fee(200.0, waived=True) == 0.0\n",
        encoding="utf-8",
    )
    _init_git_repo(ws_a)

    env_a = hz.LocalSubprocessHarborEnvironment(
        ws_a, extra_env={"PYTHONPATH": f"{ws_a}:{extra_pp}"}
    )
    res_a = asyncio.run(
        hz.run_zero_model_swe_harbor_goal(
            "Fix failing tests in test_billing.py",
            env_a,
            timeout_s=45,
            external_store_path=shared_store,
            remote_kernel_root=str(tmp_path / "remote_k_a"),
        )
    )
    assert res_a["status"] == "FINISHED", res_a
    assert res_a["environment_kind"] == "LOCAL_SUBPROCESS_NON_DOCKER"
    assert res_a["model_dependency_count"] == 0
    assert res_a["external_model_runtime_calls"] == 0
    assert res_a["model_has_terminal_authority"] is False
    assert res_a["brain_configuration_sha256"] == configuration_fingerprint()
    assert res_a["terminal_gate"]["pass"] is True
    assert res_a["terminal_gate"]["status"] == "TERMINAL_AUTHORIZED"
    assert res_a["solver_result"]["repaired"] is True
    assert shared_store.is_file()
    store_data = json.loads(shared_store.read_text(encoding="utf-8"))
    assert len(store_data.get("tree_morphisms") or {}) >= 1

    # --- Container B (Warm L2 Store, Brand-New Repo with Renamed Function & Variables!) ---
    ws_b = tmp_path / "container_b"
    ws_b.mkdir()
    (ws_b / "shipping.py").write_text(
        "# Container B shipping rule (comment must survive surgical splicing)\n"
        "def calc_surcharge(weight: float, exempt: bool = False) -> float:\n"
        "    if weight > 100:\n"
        "        return 10.0\n"
        "    return 0.0\n",
        encoding="utf-8",
    )
    (ws_b / "test_shipping.py").write_text(
        "from shipping import calc_surcharge\n"
        "def test_heavy():\n"
        "    assert calc_surcharge(250.0, exempt=False) == 10.0\n"
        "def test_light():\n"
        "    assert calc_surcharge(40.0, exempt=False) == 0.0\n"
        "def test_exempt():\n"
        "    assert calc_surcharge(250.0, exempt=True) == 0.0\n",
        encoding="utf-8",
    )
    _init_git_repo(ws_b)

    env_b = hz.LocalSubprocessHarborEnvironment(
        ws_b, extra_env={"PYTHONPATH": f"{ws_b}:{extra_pp}"}
    )
    res_b = asyncio.run(
        hz.run_zero_model_swe_harbor_goal(
            "Fix failing tests in test_shipping.py",
            env_b,
            timeout_s=45,
            external_store_path=shared_store,
            remote_kernel_root=str(tmp_path / "remote_k_b"),
        )
    )
    assert res_b["status"] == "FINISHED", res_b
    assert res_b["model_dependency_count"] == 0
    assert res_b["terminal_gate"]["pass"] is True
    assert res_b["solver_result"]["repaired"] is True
    patched_b = (ws_b / "shipping.py").read_text(encoding="utf-8")
    assert "# Container B shipping rule (comment must survive surgical splicing)" in patched_b


def test_harbor_swe_zero_model_agent_publishes_atomic_model_patch_handoff(tmp_path: pathlib.Path):
    """Engine K-4: HarborSweZeroModelAgent emits verified `model.patch` for PatchReplayAgent."""
    ws = tmp_path / "repo_app"
    ws.mkdir()
    (ws / "calc.py").write_text(
        "def fee(x, skip=False):\n"
        "    if x > 10:\n"
        "        return 5\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (ws / "test_calc.py").write_text(
        "from calc import fee\n"
        "def test_fee():\n"
        "    assert fee(20, skip=False) == 5\n"
        "    assert fee(20, skip=True) == 0\n"
        "    assert fee(5, skip=False) == 0\n",
        encoding="utf-8",
    )
    _init_git_repo(ws)

    logs_dir = tmp_path / "agent_logs"
    extra_pp = os.environ.get("PYTHONPATH", "")
    env = hz.LocalSubprocessHarborEnvironment(
        tmp_path, extra_env={"PYTHONPATH": f"{ws}:{extra_pp}"}
    )
    agent = hz.HarborSweZeroModelAgent(
        logs_dir=logs_dir,
        model_name="zero-model",
        repo_root=str(ws),
        suite="pro-v2",
        timeout_s=45,
    )

    class _Ctx:
        cost_usd = 9.99

    ctx = _Ctx()
    asyncio.run(agent.run("Fix failing tests in test_calc.py", env, ctx))
    assert ctx.cost_usd == 0.0
    trace_file = logs_dir / "project_brain_swe_zero_model_trace.json"
    patch_file = logs_dir / "model.patch"
    assert trace_file.is_file()
    assert patch_file.is_file()
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["status"] == "FINISHED"
    assert trace["model_dependency_count"] == 0
    assert trace["patch_handoff"]["status"] == "CANDIDATE_BYTES_STORED__NOT_VERIFIED"
    assert "diff --git " in patch_file.read_text(encoding="utf-8")


def test_harbor_zero_model_agent_terminal_bench_sqlite_mode(tmp_path: pathlib.Path):
    """Unified HarborSweZeroModelAgent routes non-pytest Terminal-Bench goals to UniversalComputerAgent."""
    import sqlite3

    ws = tmp_path / "tb_ws"
    ws.mkdir()
    db_p = ws / "tickets.db"
    con = sqlite3.connect(db_p)
    con.execute("CREATE TABLE tickets (id INT, status TEXT, title TEXT)")
    con.executemany(
        "INSERT INTO tickets VALUES (?, ?, ?)",
        [(1, "open", "fix ipv6"), (2, "closed", "old bug"), (3, "open", "escape braces")],
    )
    con.commit()
    con.close()

    logs_dir = tmp_path / "tb_logs"
    store_p = tmp_path / "tb_store.json"
    extra_pp = os.environ.get("PYTHONPATH", "")
    env = hz.LocalSubprocessHarborEnvironment(
        tmp_path, extra_env={"PYTHONPATH": extra_pp}
    )
    agent = hz.HarborSweZeroModelAgent(
        logs_dir=logs_dir,
        model_name="zero-model",
        repo_root=str(ws),
        suite="terminal-bench-4",
        external_store_path=store_p,
        timeout_s=45,
    )

    class _Ctx:
        cost_usd = 5.0

    ctx = _Ctx()
    asyncio.run(
        agent.run(
            "Export status=open rows from tickets.db into open_tickets.json with 2 records.",
            env,
            ctx,
        )
    )
    assert ctx.cost_usd == 0.0
    trace = json.loads((logs_dir / "project_brain_swe_zero_model_trace.json").read_text(encoding="utf-8"))
    assert trace["status"] == "FINISHED", trace
    assert trace["model_dependency_count"] == 0
    assert trace["solver_result"]["mode"] == "TERMINAL_BENCH_ZERO_MODEL"
    out_json = ws / "open_tickets.json"
    assert out_json.is_file()
    rows = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(rows) == 2 and all(r["status"] == "open" for r in rows)


def test_harbor_zero_model_agent_issue_only_green_suite_mode(tmp_path: pathlib.Path):
    """HarborSweZeroModelAgent detects green-suite Python repo with issue prose only, runs Engine M-1, emits atomic model.patch."""
    ws = tmp_path / "m1_harbor_ws"
    (ws / "src" / "demo").mkdir(parents=True)
    (ws / "tests").mkdir()
    (ws / "pyproject.toml").write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")
    (ws / "src" / "demo" / "__init__.py").write_text("", encoding="utf-8")
    (ws / "src" / "demo" / "utils.py").write_text("def dup(x):\n    return x.copy()\n", encoding="utf-8")
    (ws / "src" / "demo" / "items.py").write_text(
        "def normalize_items(items):\n    items.append('done')\n    return items\n",
        encoding="utf-8",
    )
    (ws / "tests" / "test_items.py").write_text(
        "from demo.items import normalize_items\n\n"
        "def test_adds_done():\n    assert normalize_items([1]) == [1, 'done']\n",
        encoding="utf-8",
    )
    _init_git_repo(ws)

    logs_dir = tmp_path / "m1_logs"
    extra_pp = os.environ.get("PYTHONPATH", "")
    env = hz.LocalSubprocessHarborEnvironment(ws, extra_env={"PYTHONPATH": extra_pp})
    agent = hz.HarborSweZeroModelAgent(
        logs_dir=logs_dir,
        model_name="zero-model",
        repo_root=str(ws),
        suite="swebench-pro",
        timeout_s=45,
    )

    class _Ctx:
        cost_usd = 3.0

    ctx = _Ctx()
    asyncio.run(
        agent.run(
            "Bug: normalize_items mutates the caller's list in-place instead of working on a copy.",
            env,
            ctx,
        )
    )
    assert ctx.cost_usd == 0.0
    trace = json.loads((logs_dir / "project_brain_swe_zero_model_trace.json").read_text(encoding="utf-8"))
    assert trace["status"] == "FINISHED", trace
    assert trace["model_dependency_count"] == 0
    assert trace["solver_result"]["mode"] == "ISSUE_ONLY_METAMORPHIC_SWE"
    patch_file = logs_dir / "model.patch"
    assert patch_file.is_file()
    patch_txt = patch_file.read_text(encoding="utf-8")
    assert "items = items.copy()" in patch_txt
    assert not (ws / "_brain_metamorphic_oracle_test.py").exists()


def test_iter_o_harbor_polyglot_c_asan_swe_zero_model_patch(tmp_path: pathlib.Path) -> None:
    """Engine O-2 + Harbor: End-to-end polyglot C ASan/UBSan repair emitting atomic `model.patch` (0 model calls)."""
    import shutil
    import pytest

    if not (shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")):
        pytest.skip("No C compiler available")

    ws = tmp_path / "c_repo"
    (ws / "tests").mkdir(parents=True)
    (ws / "calc.c").write_text(
        "#include <math.h>\n#include <stddef.h>\n"
        "typedef struct { double v; } Box;\n"
        "double set_box(Box *b, double x)\n{\n"
        "    b->v = x;\n"
        "    return b->v;\n}\n",
        encoding="utf-8",
    )
    (ws / "tests" / "test_calc.c").write_text(
        "#include <assert.h>\n#include <math.h>\n#include <stddef.h>\n"
        "typedef struct { double v; } Box;\n"
        "double set_box(Box *b, double x);\n"
        "int main(void) {\n"
        "    Box box = {0.0};\n"
        "    assert(set_box(&box, 7.0) == 7.0);\n"
        "    assert(isnan(set_box(NULL, 7.0)));\n"
        "    return 0;\n}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "add", "."], cwd=ws, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"],
        cwd=ws,
        check=True,
    )

    logs_dir = tmp_path / "c_logs"
    env = hz.LocalSubprocessHarborEnvironment(ws)
    agent = hz.HarborSweZeroModelAgent(
        logs_dir=logs_dir,
        model_name="zero-model",
        repo_root=str(ws),
        suite="swebench-pro",
        timeout_s=45,
    )

    class _Ctx:
        cost_usd = 2.0

    ctx = _Ctx()
    asyncio.run(agent.run("Fix the NULL pointer crash failing tests/test_calc.c in calc.c", env, ctx))
    assert ctx.cost_usd == 0.0
    trace = json.loads((logs_dir / "project_brain_swe_zero_model_trace.json").read_text(encoding="utf-8"))
    assert trace["status"] == "FINISHED", trace
    assert trace["model_dependency_count"] == 0
    assert trace["solver_result"]["mode"] == "C_ASAN_UBSAN_SWE"
    patch_file = logs_dir / "model.patch"
    assert patch_file.is_file()
    assert "if (b == NULL)" in patch_file.read_text(encoding="utf-8")


def test_iter_p_harbor_js_and_issue_only_c_zero_model_patches(tmp_path: pathlib.Path) -> None:
    """Engine P-1 + P-2 + Harbor: End-to-end JS_V8_CAUSAL_SWE & zero-test ISSUE_ONLY_C_ASAN_SWE (0 model calls)."""
    import shutil
    import pytest

    if not shutil.which("node") or not (shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")):
        pytest.skip("Requires both node and gcc/cc")

    class _Ctx:
        cost_usd = 4.0

    # 1. JS_V8_CAUSAL_SWE end-to-end through HarborSweZeroModelAgent
    ws_js = tmp_path / "js_repo"
    (ws_js / "lib").mkdir(parents=True)
    (ws_js / "test").mkdir()
    (ws_js / "lib" / "read.js").write_text(
        "'use strict'\nfunction readTitle(doc) {\n  return doc.title\n}\nmodule.exports = { readTitle }\n",
        encoding="utf-8",
    )
    (ws_js / "test" / "read.test.js").write_text(
        "'use strict'\nconst assert = require('assert')\nconst { readTitle } = require('../lib/read.js')\n"
        "assert.strictEqual(readTitle({ title: 'hi' }), 'hi')\n"
        "assert.strictEqual(readTitle(null), undefined)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=ws_js, check=True)
    subprocess.run(["git", "add", "."], cwd=ws_js, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"], cwd=ws_js, check=True)

    logs_js = tmp_path / "logs_js"
    ctx_js = _Ctx()
    asyncio.run(
        hz.HarborSweZeroModelAgent(logs_dir=logs_js, model_name="zero-model", repo_root=str(ws_js), timeout_s=45).run(
            "Fix the TypeError failing test/read.test.js in lib/read.js",
            hz.LocalSubprocessHarborEnvironment(ws_js),
            ctx_js,
        )
    )
    assert ctx_js.cost_usd == 0.0
    tr_js = json.loads((logs_js / "project_brain_swe_zero_model_trace.json").read_text("utf-8"))
    assert tr_js["status"] == "FINISHED", tr_js
    assert tr_js["solver_result"]["mode"] == "JS_V8_CAUSAL_SWE"
    assert tr_js["model_dependency_count"] == 0
    assert (logs_js / "model.patch").is_file()

    # 2. ISSUE_ONLY_C_ASAN_SWE (ZERO human tests!) end-to-end through HarborSweZeroModelAgent
    ws_c = tmp_path / "c_issue_only"
    ws_c.mkdir()
    (ws_c / "box.h").write_text(
        "typedef struct { double val; } Box;\n"
        "Box *box_create(void);\n"
        "double box_set_number(Box *object, double number);\n",
        encoding="utf-8",
    )
    (ws_c / "box.c").write_text(
        "#include <math.h>\n#include <stdlib.h>\n#include \"box.h\"\n"
        "Box *box_create(void) { return (Box *)calloc(1, sizeof(Box)); }\n"
        "double box_set_number(Box *object, double number)\n{\n"
        "    object->val = number;\n"
        "    return object->val;\n}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=ws_c, check=True)
    subprocess.run(["git", "add", "."], cwd=ws_c, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"], cwd=ws_c, check=True)

    logs_c = tmp_path / "logs_c"
    ctx_c = _Ctx()
    asyncio.run(
        hz.HarborSweZeroModelAgent(logs_dir=logs_c, model_name="zero-model", repo_root=str(ws_c), timeout_s=45).run(
            "Prevent NULL pointer dereference in box_set_number when object is NULL.",
            hz.LocalSubprocessHarborEnvironment(ws_c),
            ctx_c,
        )
    )
    assert ctx_c.cost_usd == 0.0
    tr_c = json.loads((logs_c / "project_brain_swe_zero_model_trace.json").read_text("utf-8"))
    assert tr_c["status"] == "FINISHED", tr_c
    assert tr_c["solver_result"]["mode"] == "ISSUE_ONLY_C_ASAN_SWE"
    assert tr_c["model_dependency_count"] == 0
    assert (logs_c / "model.patch").is_file()
    assert "if (object == NULL)" in (logs_c / "model.patch").read_text("utf-8")
    assert not (ws_c / "_brain_c_asan_oracle.c").exists()


def test_iter_q_relational_cow_terminal_pipelines_and_harbor(tmp_path: pathlib.Path) -> None:
    """Engine Q-1: Live-schema Relational Dataflow CoW Terminal-Bench pipelines (JSON/CSV/TAR/LOG/SQLite + Harbor)."""
    import csv
    import sqlite3
    import tarfile
    from canonical.swe_kernel import universal_computer_agent_v1 as uca

    ag = uca.UniversalComputerAgent(law_store_path=tmp_path / "tb_laws.json")

    # 1. JSON -> filtered & sorted CSV with protected sibling file intact
    t1 = tmp_path / "t1"
    t1.mkdir()
    (t1 / "records.json").write_text(
        json.dumps([{"name": "carol", "active": True}, {"name": "bob", "active": False}, {"name": "alice", "active": True}]),
        encoding="utf-8",
    )
    (t1 / "keep.txt").write_text("PROTECTED", encoding="utf-8")
    r1 = ag.solve_terminal_goal(uca.RealTerminalEnv(t1), "Read records.json and export active records sorted by name to active.csv")
    assert r1["solved"] is True, r1
    assert [r["name"] for r in csv.DictReader((t1 / "active.csv").open())] == ["alice", "carol"]
    assert (t1 / "keep.txt").read_text("utf-8") == "PROTECTED"

    # 2. tar.gz extract + line-count manifest.json
    t2 = tmp_path / "t2"
    t2.mkdir()
    src_d = tmp_path / "src_tar"
    src_d.mkdir()
    (src_d / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
    with tarfile.open(t2 / "pack.tar.gz", "w:gz") as tf:
        tf.add(src_d / "a.txt", arcname="a.txt")
    r2 = ag.solve_terminal_goal(uca.RealTerminalEnv(t2), "Extract pack.tar.gz into extracted/ and write file line counts to manifest.json")
    assert r2["solved"] is True, r2
    assert json.loads((t2 / "manifest.json").read_text("utf-8")) == {"a.txt": 2}
    assert (t2 / "extracted" / "a.txt").is_file()

    # 3. Log ERROR aggregation -> JSON
    t3 = tmp_path / "t3"
    t3.mkdir()
    (t3 / "srv.log").write_text("INFO ok\nERROR timeout\nERROR auth\nERROR timeout\n", encoding="utf-8")
    r3 = ag.solve_terminal_goal(uca.RealTerminalEnv(t3), "Count ERROR entries in srv.log by error code and write summary to errs.json")
    assert r3["solved"] is True, r3
    assert json.loads((t3 / "errs.json").read_text("utf-8")) == {"auth": 1, "timeout": 2}

    # 4. SQLite numeric filter + descending sort -> CSV
    t4 = tmp_path / "t4"
    t4.mkdir()
    con = sqlite3.connect(str(t4 / "m.db"))
    con.execute("CREATE TABLE t (id TEXT, score INT)")
    con.executemany("INSERT INTO t VALUES (?, ?)", [("a", 30), ("b", 95), ("c", 85)])
    con.commit()
    con.close()
    r4 = ag.solve_terminal_goal(uca.RealTerminalEnv(t4), "Export rows with score >= 80 from m.db sorted by score descending to top.csv")
    assert r4["solved"] is True, r4
    assert [r["id"] for r in csv.DictReader((t4 / "top.csv").open())] == ["b", "c"]

    # 5. End-to-end HarborSweZeroModelAgent Terminal-Bench CSV group-by sum -> JSON
    t5 = tmp_path / "t5"
    t5.mkdir()
    (t5 / "sales.csv").write_text("dept,amount\neng,120\nops,80\neng,30\n", encoding="utf-8")
    logs5 = tmp_path / "logs5"

    class _Ctx:
        cost_usd = 2.5

    ctx5 = _Ctx()
    asyncio.run(
        hz.HarborSweZeroModelAgent(logs_dir=logs5, model_name="zero-model", repo_root=str(t5), timeout_s=30).run(
            "Sum amount by dept from sales.csv and write totals to totals.json",
            hz.LocalSubprocessHarborEnvironment(t5),
            ctx5,
        )
    )
    assert ctx5.cost_usd == 0.0
    tr5 = json.loads((logs5 / "project_brain_swe_zero_model_trace.json").read_text("utf-8"))
    assert tr5["status"] == "FINISHED", tr5
    assert tr5["solver_result"]["mode"] == "TERMINAL_BENCH_ZERO_MODEL"
    assert tr5["model_dependency_count"] == 0
    assert json.loads((t5 / "totals.json").read_text("utf-8")) == {"eng": 150, "ops": 80}


def test_iter_r_osworld_v21_zero_model_pure_canvas_and_1shot_recall(tmp_path: pathlib.Path) -> None:
    """Engine R-1: BrainOSWorldAgentV8 + ZeroModelOSWorldPolicy pure-canvas tomography, 1-shot L2 recall & O(1) unlearning."""
    import re
    from canonical.runtime.osworld_v21_brain_agent_adapter_v8 import BrainOSWorldAgentV8
    from canonical.runtime import osworld_v21_zero_model_policy_v1 as ozm

    def _screen(active: bool) -> bytes:
        bg = (240, 240, 240)
        grid = [[bg for _ in range(120)] for _ in range(80)]
        for y in range(20, 36):
            for x in range(10, 31):
                grid[y][x] = (30, 80, 210)
        col = (20, 190, 60) if active else (220, 40, 40)
        for y in range(20, 36):
            for x in range(70, 96):
                grid[y][x] = col
        return ozm.encode_rgb_to_png(grid)

    def _is_green(rgb) -> bool:
        return sum(1 for r in rgb for (rv, gv, bv) in r if gv > 150 and rv < 80 and bv < 100) >= 100

    def _run_ep(policy, goal: str) -> tuple[bool, list[tuple[int, int]]]:
        ag = BrainOSWorldAgentV8(policy_provider=policy, policy_id="brain-zero-model-osw-v1")
        active = False
        clicks: list[tuple[int, int]] = []
        for _ in range(6):
            _, actions = ag.predict(goal, {"screenshot": _screen(active)})
            if actions == ["DONE"]:
                return True, clicks
            for a in actions:
                mx, my = re.search(r"x\s*=\s*(\d+)", a), re.search(r"y\s*=\s*(\d+)", a)
                if mx and my:
                    x, y = int(mx.group(1)), int(my.group(1))
                    clicks.append((x, y))
                    if 70 <= x <= 95 and 20 <= y <= 35:
                        active = True
        return False, clicks

    store_p = tmp_path / "osw_laws.json"
    goal = "Activate the green indicator on the pure-canvas screen."

    # Episode 1: Cold pure-canvas tomography (0 a11y, 0 OCR, 0 model calls)
    p1 = ozm.ZeroModelOSWorldPolicy(law_store_path=store_p, visual_goal_verifier=_is_green)
    done1, clicks1 = _run_ep(p1, goal)
    assert done1 is True and len(clicks1) == 2 and p1.visual_transitions_learned == 1

    # Episode 2: Fresh agent + fresh policy loading persisted store -> 1-shot replay!
    p2 = ozm.ZeroModelOSWorldPolicy(law_store_path=store_p, visual_goal_verifier=_is_green)
    done2, clicks2 = _run_ep(p2, goal)
    assert done2 is True and len(clicks2) == 1 and p2.memory_recall_hits == 1

    # Episode 3: O(1) deletion / unlearning without retraining
    laws = p2.store.active_laws(domain="osworld_gui")
    assert len(laws) == 1
    assert p2.store.remove(laws[0].law_id) is True
    assert p2.store.active_laws(domain="osworld_gui") == []


def test_engine_s1_c_buffer_underflow_and_type_confusion_guards(tmp_path: pathlib.Path) -> None:
    """Engine S-1: CWE-125 stack-buffer-underflow (`buf[strlen(buf)-1]`) and CWE-843 type-confusion (`!IsString(x)`)."""
    from canonical.swe_kernel import c_asan_cegis_repair_v1 as ccr
    from canonical.swe_kernel import universal_computer_agent_v1 as uca

    if not ccr._find_c_compiler():
        pytest.skip("No C compiler available")

    # 1. CWE-125 stack-buffer-underflow (mirrors benhoyt/inih@8e06f6b)
    ws_oob = tmp_path / "c_oob"
    ws_oob.mkdir()
    (ws_oob / "buf.c").write_text(
        "#include <string.h>\n"
        "int trim_nl(char *buf) {\n"
        "    if (buf[strlen(buf) - 1] == '\\n') {\n"
        "        buf[strlen(buf) - 1] = '\\0';\n"
        "        return 1;\n"
        "    }\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    (ws_oob / "test_oob.c").write_text(
        "#include <assert.h>\n"
        "int trim_nl(char *buf);\n"
        "int main(void) {\n"
        "    char empty[4] = \"\";\n"
        "    char line[8] = \"hi\\n\";\n"
        "    assert(trim_nl(empty) == 0);\n"
        "    assert(trim_nl(line) == 1 && line[2] == '\\0');\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    store = uca.ExternalCausalLawStore(tmp_path / "c_s1_laws.json")
    r_oob = ccr.repair_c_repo_asan_cegis(
        ws_oob, ["buf.c", "test_oob.c"], editable_files=["buf.c"], timeout_s=20, skill_store=store
    )
    assert r_oob["repaired"] is True
    assert r_oob["model_calls"] == 0
    assert "C_OOB_" in str(r_oob["rule"])

    # 2. CWE-843 type confusion (mirrors DaveGamble/cJSON@fb16e5c)
    ws_tc = tmp_path / "c_tc"
    ws_tc.mkdir()
    (ws_tc / "node.c").write_text(
        "#include <stddef.h>\n"
        "#include <string.h>\n"
        "typedef struct { int kind; const char *valuestring; } Node;\n"
        "static int Node_IsString(const Node *n) { return n != NULL && n->kind == 1; }\n"
        "static int Node_IsNumber(const Node *n) { return n != NULL && n->kind == 2; }\n"
        "static int use_str(const char *s) { return (int)strlen(s); }\n"
        "int handle(const Node *from) {\n"
        "    (void)Node_IsString;\n"
        "    (void)Node_IsNumber;\n"
        "    if (from == NULL)\n"
        "    {\n"
        "        return 4;\n"
        "    }\n"
        "    return use_str(from->valuestring);\n"
        "}\n",
        encoding="utf-8",
    )
    (ws_tc / "test_tc.c").write_text(
        "#include <assert.h>\n"
        "#include <stddef.h>\n"
        "typedef struct { int kind; const char *valuestring; } Node;\n"
        "int handle(const Node *from);\n"
        "int main(void) {\n"
        "    Node num = {2, NULL};\n"
        "    Node s = {1, \"abc\"};\n"
        "    assert(handle(&num) == 4);\n"
        "    assert(handle(&s) == 3);\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    r_tc = ccr.repair_c_repo_asan_cegis(
        ws_tc, ["node.c", "test_tc.c"], editable_files=["node.c"], timeout_s=20, skill_store=store
    )
    assert r_tc["repaired"] is True
    assert r_tc["model_calls"] == 0
    assert "Node_IsString" in str(r_tc["patched_source"])


def test_engine_s2_js_regex_alias_decouple_and_length_polymorphism(tmp_path: pathlib.Path) -> None:
    """Engine S-2: JS regex flag algebra, def-use array copy+decouple, and short-circuit length-polymorphism."""
    from canonical.swe_kernel import js_causal_cegis_repair_v1 as jsc

    if not jsc._find_node():
        pytest.skip("Node.js not available")

    # 1. Regex case-insensitive flag + 2. Def-use defensive array copy + decouple + 3. Length-polymorphism short-circuit
    ws = tmp_path / "js_s2"
    (ws / "lib").mkdir(parents=True)
    (ws / "test").mkdir(parents=True)

    # Case A: regex `/%2E/g` -> `/%2E/gi`
    (ws / "lib" / "parse.js").write_text(
        "'use strict';\n"
        "module.exports = function decodeDots(s) {\n"
        "    return s.replace(/%2E/g, '.');\n"
        "};\n",
        encoding="utf-8",
    )
    (ws / "test" / "parse.js").write_text(
        "const assert = require('assert');\n"
        "const decodeDots = require('../lib/parse');\n"
        "assert.strictEqual(decodeDots('a%2Eb%2ec'), 'a.b.c');\n",
        encoding="utf-8",
    )
    r_rx = jsc.repair_js_repo_causal_cegis(ws, "test/parse.js", timeout_s=15)
    assert r_rx["repaired"] is True and r_rx["model_calls"] == 0
    assert "/%2E/gi" in str(r_rx["patched_source"])

    # Case B: def-use defensive array copy + alias decoupling (mirrors ljharb/qs@54f7f3b)
    (ws / "lib" / "stringify.js").write_text(
        "'use strict';\n"
        "function childOrder(flt) { return flt.join(','); }\n"
        "module.exports = function fmt(options) {\n"
        "    var filter;\n"
        "    var objKeys;\n"
        "    if (Array.isArray(options.filter)) {\n"
        "        filter = options.filter;\n"
        "        objKeys = filter;\n"
        "    }\n"
        "    objKeys.sort();\n"
        "    return objKeys.join(',') + '|' + childOrder(options.filter);\n"
        "};\n",
        encoding="utf-8",
    )
    (ws / "test" / "stringify.js").write_text(
        "const assert = require('assert');\n"
        "const fmt = require('../lib/stringify');\n"
        "const orig = ['b', 'a'];\n"
        "const out = fmt({ filter: orig });\n"
        "assert.deepStrictEqual(orig, ['b', 'a']);\n"
        "assert.strictEqual(out, 'a,b|a,b');\n",
        encoding="utf-8",
    )
    r_al = jsc.repair_js_repo_causal_cegis(ws, "test/stringify.js", timeout_s=15)
    assert r_al["repaired"] is True and r_al["model_calls"] == 0
    assert "options.filter.slice()" in str(r_al["patched_source"])

    # Case C: length-polymorphism guard preserving throwing contract on null/undefined (mirrors ljharb/qs@bd3d9b5)
    (ws / "lib" / "utils.js").write_text(
        "'use strict';\n"
        "module.exports = function enc(str) {\n"
        "    if (str.length === 0) {\n"
        "        return str;\n"
        "    }\n"
        "    return 'ENC:' + String(str);\n"
        "};\n",
        encoding="utf-8",
    )
    (ws / "test" / "utils.js").write_text(
        "const assert = require('assert');\n"
        "const enc = require('../lib/utils');\n"
        "assert.strictEqual(enc(''), '');\n"
        "assert.throws(() => enc(null), TypeError);\n"
        "assert.throws(() => enc(undefined), TypeError);\n"
        "assert.strictEqual(enc({ length: 0, toString() { return 'x'; } }), 'ENC:x');\n",
        encoding="utf-8",
    )
    r_lp = jsc.repair_js_repo_causal_cegis(ws, "test/utils.js", timeout_s=15)
    assert r_lp["repaired"] is True and r_lp["model_calls"] == 0
    assert "str.length === 0 &&" in str(r_lp["patched_source"])


def test_engine_s3a_osworld_multistep_click_type_hotkey_and_l2_replay(tmp_path: pathlib.Path) -> None:
    """Engine S-3a: Multi-step OSWorld 2.1 CLICK->TYPE->HOTKEY->DONE with AT-SPI XML & 1-shot L2 replay."""
    import re
    from canonical.runtime.osworld_v21_brain_agent_adapter_v8 import BrainOSWorldAgentV8
    from canonical.runtime.osworld_v21_zero_model_policy_v1 import ZeroModelOSWorldPolicy, encode_rgb_to_png

    def _screen(tag: str) -> bytes:
        bg = {"init": (235, 235, 235), "focus": (220, 235, 255), "typed": (220, 250, 225), "saved": (180, 240, 180)}[tag]
        return encode_rgb_to_png([[bg for _ in range(32)] for _ in range(20)])

    a11y_tpl = (
        '<desktop-frame>'
        '<entry name="Filename" screencoord="(100, 200)" size="(300, 40)">{val}</entry>'
        '<label name="Status" screencoord="(100, 400)" size="(200, 30)">{st}</label>'
        '</desktop-frame>'
    )

    def _run_ep(pol: ZeroModelOSWorldPolicy, inst: str) -> tuple[bool, list[str]]:
        pol.reset_episode()
        ag = BrainOSWorldAgentV8(policy_provider=pol, policy_id="zero_model_s3a")
        ui = {"focused": False, "text": "", "saved": False}
        acts: list[str] = []
        for _ in range(8):
            tag = "saved" if ui["saved"] else ("typed" if ui["text"] else ("focus" if ui["focused"] else "init"))
            _, out = ag.predict(inst, {"screenshot": _screen(tag), "accessibility_tree": a11y_tpl.format(val=ui["text"], st="SAVED" if ui["saved"] else "DRAFT")})
            a = out[0]
            acts.append(a)
            if a == "DONE":
                return True, acts
            if "pyautogui.click" in a:
                mx, my = re.search(r"x\s*=\s*(\d+)", a), re.search(r"y\s*=\s*(\d+)", a)
                if mx and my and 100 <= int(mx.group(1)) <= 400 and 200 <= int(my.group(1)) <= 240:
                    ui["focused"] = True
            elif "pyautogui.write" in a or "pyautogui.typewrite" in a:
                mt = re.search(r"['\"]([^'\"]+)['\"]", a)
                if mt and ui["focused"]:
                    ui["text"] = mt.group(1)
            elif "pyautogui.hotkey" in a and "ctrl" in a and "'s'" in a and ui["text"] == "report.csv":
                ui["saved"] = True
        return False, acts

    pol = ZeroModelOSWorldPolicy(
        law_store_path=tmp_path / "osw_s3a.json",
        a11y_goal_verifier=lambda nodes: any(nd.get("name") == "Status" and nd.get("text") == "SAVED" for nd in nodes),
    )
    inst = 'Click Filename, enter "report.csv", and press Ctrl+S to save.'
    ok1, a1 = _run_ep(pol, inst)
    assert ok1 and a1[-1] == "DONE"
    assert pol.visual_transitions_learned >= 3
    ok2, a2 = _run_ep(pol, inst)
    assert ok2 and a2 == a1
    assert pol.memory_recall_hits >= 3


def test_engine_s3b_terminal_bench_script_config_repair_and_two_table_join(tmp_path: pathlib.Path) -> None:
    """Engine S-3b: TB-7 CRLF/chmod shell repair, TB-8 malformed JSON config repair, TB-9 2-table hash-join."""
    import csv
    from canonical.swe_kernel import universal_computer_agent_v1 as uca

    ag = uca.UniversalComputerAgent(law_store_path=tmp_path / "tb_s3b.json")

    # TB-7: Broken shell script
    ws7 = tmp_path / "tb7"
    ws7.mkdir()
    (ws7 / "keep.txt").write_text("SAFE\n", encoding="utf-8")
    (ws7 / "run.sh").write_bytes(b"#!/usr/bin/env bash\r\nset -e\r\necho OK99 > out/res.txt\r\n")
    (ws7 / "run.sh").chmod(0o644)
    r7 = ag.solve_terminal_goal(uca.RealTerminalEnv(ws7), "Fix and run run.sh to create out/res.txt.")
    assert r7["solved"] is True
    assert (ws7 / "out/res.txt").read_text(encoding="utf-8").strip() == "OK99"
    assert (ws7 / "keep.txt").read_text(encoding="utf-8") == "SAFE\n"

    # TB-8: Malformed JSON config + verifier
    ws8 = tmp_path / "tb8"
    ws8.mkdir()
    (ws8 / "cfg.json").write_text("// comment\n{\n  'port': 9000,\n  'ok': True,\n}\n", encoding="utf-8")
    (ws8 / "check.py").write_text(
        "import json, pathlib\n"
        "d = json.loads(pathlib.Path('cfg.json').read_text())\n"
        "assert d['port'] == 9000 and d['ok'] is True\n"
        "pathlib.Path('passed.txt').write_text('YES\\n')\n",
        encoding="utf-8",
    )
    r8 = ag.solve_terminal_goal(uca.RealTerminalEnv(ws8), "Repair cfg.json and run check.py to produce passed.txt.")
    assert r8["solved"] is True
    assert json.loads((ws8 / "cfg.json").read_text(encoding="utf-8")) == {"ok": True, "port": 9000}
    assert (ws8 / "passed.txt").read_text(encoding="utf-8").strip() == "YES"

    # TB-9: Two-table JSON + CSV hash-join + filter + grouped sum
    ws9 = tmp_path / "tb9"
    ws9.mkdir()
    (ws9 / "users.json").write_text(
        json.dumps([
            {"user_id": 1, "tier": "pro", "active": True},
            {"user_id": 2, "tier": "pro", "active": False},
            {"user_id": 3, "tier": "team", "active": True},
        ]),
        encoding="utf-8",
    )
    with (ws9 / "orders.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "user_id", "amount"])
        w.writerow([1, 1, 40])
        w.writerow([2, 1, 60])
        w.writerow([3, 2, 500])
        w.writerow([4, 3, 250])
    r9 = ag.solve_terminal_goal(
        uca.RealTerminalEnv(ws9),
        "Join users.json and orders.csv on user_id, keep active users, and sum amount by tier into report.json.",
    )
    assert r9["solved"] is True
    assert json.loads((ws9 / "report.json").read_text(encoding="utf-8")) == {"pro": 100, "team": 250}








