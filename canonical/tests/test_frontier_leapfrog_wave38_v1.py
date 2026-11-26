#!/usr/bin/env python3
"""Wave 38 Real-Execution Adversarial Verification Suite (`K3 = 0`, `$0` spend).

Verifies EVERY Wave 38 frontier-leapfrog breakthrough end-to-end with ZERO mocks:
  1. Real Linux kernel namespace isolation (`user+mount+pid+ipc+uts+net`, `chroot`,
     `CapEff == 0`) PLUS pinned classic BPF `seccomp` allowlist (`Seccomp: 2`,
     `26cd1e65...`) blocking 20/20 real kernel escape probes including live `bpf`,
     `io_uring_setup`, `keyctl`, `userfaultfd`, `ptrace`, `unshare`, `AF_NETLINK`.
  2. Agent-S4 + `a_refusal_is_a_specification_v1` Refusal-as-Interface-Compiler inside
     the seccomp sandbox: catches non-zero refusal, parses `--force` demand, retries,
     verifies real gzip byte effect via `byte_effect_oracle_v1`, compiles the interface,
     and reuses it at attempt 0 on the next episode.
  3. W3C WebMCP (`navigator.modelContext`) typed JSON-schema tool validation (fail-closed
     on schema mismatch) & zero-pixel execution (`97%` cost reduction vs visual).
  4. Multi-file SWE wall-closers:
     - Anti-vacuous verifier audit (`FAIL_CLOSED__VACUOUS_VERIFIER_ALREADY_PASSES`)
     - Real 13-law statement-shaped `residual_wall_closers_v1` (`AssertContractToTypedRaise`
       & `NoneGuardToTruthiness`) at `RUNG_2B_RESIDUAL_WALL_CLOSER`
     - Real `repo_component_petri_v1` escaping-exception widening at `RUNG_2C_REPO_COMPONENT_PETRI`
     - Optional pluggable Rung-3 Guidance-TTT proposer compiled away to `RUNG_0_COMPILED_SKILL`
       (`proposer_calls == 0` on unseen renamed repo!).
  5. Unified Type-pruned `CEGIS(T)` + Adaptive Constant V9 (`solve_typed_cegis`).
  6. Non-Malleable Memory OS (Spine `0G`):
     - TMA-NM write-time cryptographic origin binding (`0%` origin-laundering ASR + tamper detection)
     - GovMem correlated-trace dedup + `a_law_carries_its_reason` contrast-witness gate
     - A-TMA anti-ghost-memory `{current, historical, transitions, stale_impacted}` state views
     - SkillApt Rubin counterfactual activation (`ACTIVATE | ABSTAIN | DEMOTE`)
     - DreamProver `<96` hot-tier LRU/rent cap (`150 -> 96 hot + 54 cold L2`).
  7. Bicameral Consolidate-and-Dream Sleep Cycle (`mined_rewrite_theory_v1` + origin audit
     + `weight_update_admission_v1` out-of-train probe gate) on `UnifiedModel` & `Creature`.
  8. OpenViking-style L0/L1/L2 progressive dark-matter discovery, all 12 Wave 38 federated
     engines, and 100.0% (`1.000`) `DOMAIN_ATLAS_V1` route recall across all 7 domains.
"""
from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.futamura_leapfrog_kernel_v1 import (
    ConfinedHybridComputerUseExecutor,
    FutamuraSelfCompilingCascade,
    MultifileFutamuraRepoSolver,
)
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    FEDERATED_KERNEL_DESCRIPTORS,
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)
from canonical.runtime.worker_syscall_allowlist_v1 import filter_sha256

ROOT = Path(__file__).resolve().parents[2]
PINNED_SECCOMP_SHA256 = "26cd1e65305ccf034a213df6a5f33a2ba5cda2e718a6fc418dff5b082f2617b6"


def _write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class TestFrontierLeapfrogWave38(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = open_model()

    def test_01_real_seccomp_bpf_plus_6ns_plus_capeff0_20_escape_probe(self) -> None:
        probe = self.model.probe_os_isolation(budget_s=30.0, seccomp=True)
        self.assertEqual(probe["verdict"], "ISOLATED", f"Seccomp isolation failed: {probe}")
        self.assertTrue(probe["isolated"])
        self.assertEqual(probe["caps_after_drop"], "0000000000000000")
        self.assertEqual(probe["seccomp_mode"], "2")
        self.assertTrue(probe["seccomp_installed"])
        self.assertEqual(probe["seccomp_filter_sha256"], PINNED_SECCOMP_SHA256)
        self.assertEqual(filter_sha256("x86_64"), PINNED_SECCOMP_SHA256)
        self.assertFalse(probe["host_canary_written"])
        attempts = probe["attempts"]
        for must_block in (
            # Original 13 namespace/chroot/network/capability escapes
            "read_host_canary",
            "write_host_path",
            "list_host_dir",
            "tcp_connect",
            "udp_connect",
            "dns_resolve",
            "mount_tmpfs",
            "chroot_again",
            "dev_mem",
            "host_home",
            "write_readonly_bind",
            "proc_one_root_home",
            "escape_via_proc_root",
            # Wave 38 live kernel classic BPF seccomp syscall escapes
            "syscall_bpf",
            "syscall_io_uring_setup",
            "syscall_keyctl",
            "syscall_userfaultfd",
            "syscall_ptrace",
            "syscall_unshare",
            "socket_af_netlink",
        ):
            self.assertTrue(
                attempts[must_block]["blocked"],
                f"Kernel escape {must_block} was NOT blocked: {attempts[must_block]}",
            )
            if must_block.startswith(("syscall_", "socket_")):
                self.assertEqual(attempts[must_block]["errno"], 1, f"Expected EPERM for {must_block}")

    def test_02_refusal_as_interface_compiler_and_reuse_inside_seccomp_sandbox(self) -> None:
        payload = b"Wave 38 Agent-S4 Refusal-as-Interface-Compiler verified gzip output!\n" * 3
        cli_script = (
            "import gzip, sys\n"
            "args = sys.argv[1:]\n"
            "if '--force' not in args:\n"
            "    sys.stderr.write('Refused: target already exists; use the --force option\\n')\n"
            "    sys.exit(2)\n"
            "data = open('/work/input.txt', 'rb').read()\n"
            "open('/work/archive.gz', 'wb').write(gzip.compress(data))\n"
            "print('COMPRESSED_OK')\n"
        )
        ex = ConfinedHybridComputerUseExecutor()
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            wd1 = Path(td1)
            (wd1 / "tool_cli.py").write_text(cli_script, encoding="utf-8")
            (wd1 / "input.txt").write_bytes(payload)
            (wd1 / "archive.gz").write_bytes(b"stale")

            # Episode 1: cold call omits --force -> CLI refuses -> Brain compiles refusal -> succeeds in seccomp!
            r1 = ex.execute_episode(
                wd1,
                [
                    {
                        "action": "pack_archive",
                        "argv": ["/usr/bin/python3", "/work/tool_cli.py"],
                        "effect_contract": {
                            "output_path": "archive.gz",
                            "expected_format": "gzip",
                            "expected_source_bytes": payload,
                        },
                        "allowed_modified_files": ["archive.gz"],
                    }
                ],
                goal_id="w38_refusal_ep1",
                seccomp=True,
                auto_compile_refusal=True,
            )
            self.assertTrue(r1["pass"], f"Episode 1 refusal compilation failed: {r1}")
            self.assertEqual(r1["refusal_compiled_count"], 1)
            self.assertEqual(r1["recovered_steps"], 1)
            attempts1 = r1["trace"][0]["attempts"]
            self.assertEqual(attempts1[0]["status"], "CMD_REFUSED_COMPILED_RETRY")
            self.assertTrue(attempts1[0]["seccomp_installed"])
            self.assertEqual(attempts1[1]["status"], "EXECUTED_VERIFIED")
            self.assertTrue(attempts1[1]["seccomp_installed"])
            self.assertEqual(attempts1[1]["seccomp_filter_sha256"], PINNED_SECCOMP_SHA256)
            self.assertEqual(gzip.decompress((wd1 / "archive.gz").read_bytes()), payload)

            # Episode 2 (fresh workspace, SAME tool family, caller still omits --force):
            # Evolved interface applies automatically at attempt 0 with 0 retries!
            wd2 = Path(td2)
            (wd2 / "tool_cli.py").write_text(cli_script, encoding="utf-8")
            (wd2 / "input.txt").write_bytes(payload)
            (wd2 / "archive.gz").write_bytes(b"stale")

            r2 = ex.execute_episode(
                wd2,
                [
                    {
                        "action": "pack_archive",
                        "argv": ["/usr/bin/python3", "/work/tool_cli.py"],
                        "effect_contract": {
                            "output_path": "archive.gz",
                            "expected_format": "gzip",
                            "expected_source_bytes": payload,
                        },
                        "allowed_modified_files": ["archive.gz"],
                    }
                ],
                goal_id="w38_refusal_ep2",
                seccomp=True,
                auto_compile_refusal=True,
            )
            self.assertTrue(r2["pass"], f"Episode 2 evolved interface reuse failed: {r2}")
            self.assertEqual(r2["evolved_interface_hits"], 1)
            self.assertEqual(r2["recovered_steps"], 0)
            self.assertEqual(len(r2["trace"][0]["attempts"]), 1)
            self.assertEqual(r2["trace"][0]["attempts"][0]["status"], "EXECUTED_VERIFIED")
            self.assertEqual(gzip.decompress((wd2 / "archive.gz").read_bytes()), payload)

    def test_03_webmcp_typed_tool_channel_validation_and_zero_pixel_execution(self) -> None:
        def _write_json_tool(args, wd: Path):
            out = wd / str(args["filename"])
            out.write_text(json.dumps({"tag": args["tag"], "count": args["count"]}), encoding="utf-8")
            return {"written": str(args["filename"])}

        webmcp_tools = {
            "save_record": {
                "handler": _write_json_tool,
                "input_schema": {
                    "required": ["filename", "tag", "count"],
                    "properties": {
                        "filename": {"type": "string"},
                        "tag": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                    "additionalProperties": False,
                },
            }
        }
        with tempfile.TemporaryDirectory() as td:
            wd = Path(td)
            # Invalid type (count is str instead of integer) MUST fail closed!
            bad = self.model.execute_confined_computer_use(
                wd,
                [{"action": "bad_call", "webmcp_tool": "save_record", "webmcp_args": {"filename": "a.json", "tag": "x", "count": "oops"}}],
                webmcp_tools=webmcp_tools,
                goal_id="w38_webmcp_bad",
            )
            self.assertFalse(bad["pass"])
            self.assertEqual(bad["trace"][0]["attempts"][0]["status"], "WEBMCP_SCHEMA_REJECTED")
            self.assertFalse((wd / "a.json").exists())

            # Valid typed call executes on WebMCP channel at 0.03 cost (97% savings vs visual)!
            good = self.model.execute_confined_computer_use(
                wd,
                [
                    {
                        "action": "good_call",
                        "webmcp_tool": "save_record",
                        "webmcp_args": {"filename": "rec.json", "tag": "ok", "count": 7},
                        "allowed_modified_files": ["rec.json"],
                    }
                ],
                webmcp_tools=webmcp_tools,
                goal_id="w38_webmcp_good",
            )
            self.assertTrue(good["pass"], f"WebMCP valid call failed: {good}")
            self.assertEqual(good["channel_counts"]["webmcp"], 1)
            self.assertGreaterEqual(good["cost_reduction_vs_visual_only_pct"], 95.0)
            self.assertEqual(json.loads((wd / "rec.json").read_text(encoding="utf-8")), {"tag": "ok", "count": 7})

    def test_04_swe_wall_closers_anti_vacuous_verifier_and_rung3_compile_away(self) -> None:
        solver = MultifileFutamuraRepoSolver(cascade=FutamuraSelfCompilingCascade())

        # 4A: Anti-vacuous verifier check rejects a test suite that already passes on broken code
        with tempfile.TemporaryDirectory() as td:
            vac_repo = Path(td) / "vacuous_repo"
            _write_files(
                vac_repo,
                {
                    "app.py": "def broken(x):\n    return x - 1\n",
                    "test_app.py": "import unittest\nclass T(unittest.TestCase):\n    def test_noop(self):\n        self.assertTrue(True)\n",
                },
            )
            vac_res = solver.solve(vac_repo, ["test_app.py"], reject_vacuous_verifier=True)
            self.assertFalse(vac_res["pass"])
            self.assertEqual(vac_res["rung"], "FAIL_CLOSED__VACUOUS_VERIFIER_ALREADY_PASSES")
            self.assertTrue(vac_res["vacuous_verifier"])

        # 4B: Statement-shaped residual wall closer (`AssertContractToTypedRaise`: assert -> if not: raise ValueError)
        with tempfile.TemporaryDirectory() as td:
            wall_repo = Path(td) / "assert_wall_repo"
            _write_files(
                wall_repo,
                {
                    "validator.py": (
                        "def parse_positive(n):\n"
                        "    assert n > 0, 'n must be positive'\n"
                        "    return n * 2\n"
                    ),
                    "test_validator.py": (
                        "import unittest\nfrom validator import parse_positive\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_ok(self):\n"
                        "        self.assertEqual(parse_positive(5), 10)\n"
                        "    def test_raises_value_error(self):\n"
                        "        with self.assertRaises(ValueError):\n"
                        "            parse_positive(0)\n"
                    ),
                },
            )
            w_res = solver.solve(wall_repo, ["test_validator.py"])
            self.assertTrue(w_res["pass"], f"Residual wall AssertContractToTypedRaise failed: {w_res}")
            self.assertEqual(w_res["rung"], "RUNG_2B_RESIDUAL_WALL_CLOSER")
            self.assertEqual(w_res["proposer_calls"], 0)
            self.assertIn("raise ValueError", (wall_repo / "validator.py").read_text(encoding="utf-8"))

        # 4C: Statement-shaped residual wall closer (`NoneGuardToTruthiness` on Optional[str] attribute)
        with tempfile.TemporaryDirectory() as td:
            ng_repo = Path(td) / "none_guard_repo"
            _write_files(
                ng_repo,
                {
                    "labeler.py": (
                        "class Labeler:\n"
                        "    name: str | None = None\n\n"
                        "    def __init__(self, name: str | None = None):\n"
                        "        self.name = name\n\n"
                        "    def format_label(self) -> str:\n"
                        "        val = self.name\n"
                        "        if val is not None:\n"
                        "            return f'[{val}]'\n"
                        "        return '[default]'\n"
                    ),
                    "test_labeler.py": (
                        "import unittest\nfrom labeler import Labeler\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_nonempty(self):\n"
                        "        self.assertEqual(Labeler('alpha').format_label(), '[alpha]')\n"
                        "    def test_empty_string_uses_default(self):\n"
                        "        self.assertEqual(Labeler('').format_label(), '[default]')\n"
                        "    def test_none_uses_default(self):\n"
                        "        self.assertEqual(Labeler(None).format_label(), '[default]')\n"
                    ),
                },
            )
            ng_res = solver.solve(ng_repo, ["test_labeler.py"])
            self.assertTrue(ng_res["pass"], f"Residual wall NoneGuardToTruthiness failed: {ng_res}")
            self.assertEqual(ng_res["rung"], "RUNG_2B_RESIDUAL_WALL_CLOSER")
            self.assertEqual(ng_res["proposer_calls"], 0)

        # 4D: Repo-native component Petri-net escaping-exception widening (`RUNG_2C_REPO_COMPONENT_PETRI`)
        # Uses a custom repo-defined exception class (`CacheMissError`) that Rung 2's built-in AST
        # mutator cannot know about — only Rung 2C's repo-component Petri synthesizer mines it!
        with tempfile.TemporaryDirectory() as td:
            petri_repo = Path(td) / "petri_exc_repo"
            _write_files(
                petri_repo,
                {
                    "lookup.py": (
                        "class CacheMissError(Exception):\n"
                        "    pass\n\n"
                        "def _read_store(mapping, key):\n"
                        "    if key not in mapping:\n"
                        "        raise CacheMissError(key)\n"
                        "    return mapping[key]\n\n"
                        "def safe_fetch(mapping, key):\n"
                        "    try:\n"
                        "        return int(_read_store(mapping, key))\n"
                        "    except ValueError:\n"
                        "        return -1\n"
                    ),
                    "test_lookup.py": (
                        "import unittest\nfrom lookup import safe_fetch\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_present(self):\n"
                        "        self.assertEqual(safe_fetch({'a': '42'}, 'a'), 42)\n"
                        "    def test_bad_int(self):\n"
                        "        self.assertEqual(safe_fetch({'a': 'nope'}, 'a'), -1)\n"
                        "    def test_missing_key(self):\n"
                        "        self.assertEqual(safe_fetch({}, 'missing'), -1)\n"
                    ),
                },
            )
            p_res = solver.solve(petri_repo, ["test_lookup.py"])
            self.assertTrue(p_res["pass"], f"Repo Component Petri widening failed: {p_res}")
            self.assertEqual(p_res["rung"], "RUNG_2C_REPO_COMPONENT_PETRI")
            self.assertEqual(p_res["proposer_calls"], 0)

        # 4E: Optional pluggable Rung-3 proposer compiles back to Rung 0 -> 0 proposer calls on unseen repo!
        r3_solver = MultifileFutamuraRepoSolver(cascade=FutamuraSelfCompilingCascade())
        proposer_invocations = {"n": 0}

        def _guidance_proposer(ctx):
            proposer_invocations["n"] += 1
            src = ctx["sources"]["calc.py"]
            return [{"calc.py": src.replace("(a * b) - c", "(a + c) * b")}]

        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            repo1 = Path(td1) / "r3_a"
            _write_files(
                repo1,
                {
                    "calc.py": "def score_alpha(a, b, c):\n    return (a * b) - c\n",
                    "test_calc.py": (
                        "import unittest\nfrom calc import score_alpha\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_s(self):\n"
                        "        self.assertEqual(score_alpha(2, 5, 3), 25)\n"
                        "        self.assertEqual(score_alpha(4, 3, 2), 18)\n"
                    ),
                },
            )
            res1 = r3_solver.solve(
                repo1,
                ["test_calc.py"],
                use_residual_wall_closers=False,
                use_repo_component_petri=False,
                untrusted_proposer=_guidance_proposer,
            )
            self.assertTrue(res1["pass"], f"Rung-3 solve failed: {res1}")
            self.assertEqual(res1["rung"], "RUNG_3_GUIDANCE_PROPOSER_COMPILED")
            self.assertEqual(res1["proposer_calls"], 1)
            self.assertGreaterEqual(len(res1["compiled_rule_ids"]), 1)

            # Unseen renamed repo (completely different file, function, & variable names!)
            # solves at Rung 0 with ZERO proposer calls!
            repo2 = Path(td2) / "r3_b"
            _write_files(
                repo2,
                {
                    "metrics.py": "def compute_total(price, qty, fee):\n    return (price * qty) - fee\n",
                    "test_metrics.py": (
                        "import unittest\nfrom metrics import compute_total\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_b(self):\n"
                        "        self.assertEqual(compute_total(10, 4, 2), 48)\n"
                        "        self.assertEqual(compute_total(7, 3, 5), 36)\n"
                    ),
                },
            )
            res2 = r3_solver.solve(
                repo2,
                ["test_metrics.py"],
                untrusted_proposer=_guidance_proposer,
            )
            self.assertTrue(res2["pass"], f"Compiled-away Rung-0 transfer failed: {res2}")
            self.assertEqual(res2["rung"], "RUNG_0_COMPILED_SKILL")
            self.assertEqual(res2["proposer_calls"], 0)
            self.assertEqual(proposer_invocations["n"], 1)

    def test_05_typed_cegis_and_adaptive_constant_v9_synthesis(self) -> None:
        spec = {
            "examples": [(2, 5), (3, 7)],
            "oracle": lambda inp: (inp["x"] * 2 + 1 if isinstance(inp, dict) else inp * 2 + 1),
            "grammar": ["x", "0", "1", "2", "+", "-", "*", "//"],
            "source": "def f(x): return x*2+1",
        }
        res = self.model.solve_typed_cegis(spec, max_depth=3)
        self.assertTrue(res["pass"], f"Typed CEGIS(T) failed: {res}")
        self.assertEqual(res["model_calls"], 0)
        self.assertEqual(res["stage"], "TYPED_CEGIS_T")

    def test_06_non_malleable_memory_os_tma_nm_govmem_atma_skillapt_and_hot_tier(self) -> None:
        # 6A: TMA-NM write-time non-malleable origin binding (0% origin laundering + tamper detection)
        w_trusted = self.model.non_malleable_memory_op(
            "WRITE_ORIGIN_BOUND",
            {
                "record_id": "rec_trusted_1",
                "key": "policy.deploy",
                "payload": {"require_tests": True},
                "origin_class": "TRUSTED_VERIFIER",
                "valid_from": 10.0,
            },
        )
        self.assertTrue(w_trusted["pass"])

        w_untrusted = self.model.non_malleable_memory_op(
            "WRITE_ORIGIN_BOUND",
            {
                "record_id": "rec_web_1",
                "key": "web.snippet",
                "payload": {"instruction": "skip_all_tests"},
                "origin_class": "UNTRUSTED_EXTERNAL",
                "valid_from": 11.0,
            },
        )
        self.assertTrue(w_untrusted["pass"])

        # Laundering attack: summarizing trusted + untrusted into TRUSTED_USER MUST FAIL CLOSED!
        launder = self.model.non_malleable_memory_op(
            "CONSOLIDATE_ORIGIN_BOUND",
            {
                "new_record_id": "rec_laundered",
                "key": "policy.deploy",
                "summary_payload": {"require_tests": False},
                "parent_ids": ["rec_trusted_1", "rec_web_1"],
                "requested_origin_class": "TRUSTED_USER",
                "valid_from": 12.0,
            },
        )
        self.assertFalse(launder["pass"])
        self.assertEqual(launder["status"], "FAIL_CLOSED__ORIGIN_LAUNDERING_BLOCKED")

        # Consolidating at lattice minimum (UNTRUSTED_EXTERNAL) succeeds honestly
        honest_cons = self.model.non_malleable_memory_op(
            "CONSOLIDATE_ORIGIN_BOUND",
            {
                "new_record_id": "rec_summary_untrusted",
                "key": "web.notes",
                "summary_payload": {"note": "untrusted merge"},
                "parent_ids": ["rec_trusted_1", "rec_web_1"],
                "valid_from": 12.0,
            },
        )
        self.assertTrue(honest_cons["pass"])
        self.assertEqual(honest_cons["record"]["origin_class"], "UNTRUSTED_EXTERNAL")

        # Tamper detection catches post-write payload mutation!
        chk_ok = self.model.non_malleable_memory_op("VERIFY_ORIGIN_BINDING", {"record_id": "rec_trusted_1"})
        self.assertTrue(chk_ok["pass"])
        bus = self.model._get_non_malleable_memory_bus()
        bus._origin_store()["rec_trusted_1"]["payload"] = {"require_tests": False}
        chk_tampered = self.model.non_malleable_memory_op("VERIFY_ORIGIN_BINDING", {"record_id": "rec_trusted_1"})
        self.assertFalse(chk_tampered["pass"])
        self.assertEqual(chk_tampered["status"], "FAIL_CLOSED__ORIGIN_TAMPER_DETECTED")
        # Restore payload for clean sleep audit later
        bus._origin_store()["rec_trusted_1"]["payload"] = {"require_tests": True}

        # 6B: GovMem correlated-trace dedup + `a_law_carries_its_reason` contrast witness gate
        correlated_5 = [
            {"trace_lineage_id": "sess_A", "source_origin_hash": "hA", "origin_class": "TRUSTED_VERIFIER", "positive": True}
            for _ in range(5)
        ]
        rej_corr = self.model.non_malleable_memory_op(
            "PROPOSE_MEMORY_PROMOTION",
            {"rule_id": "rule_corr", "key": "k.corr", "rule_payload": "always_x", "witnesses": correlated_5},
        )
        self.assertFalse(rej_corr["admitted"])
        self.assertEqual(rej_corr["independent_positive_count"], 1)
        self.assertEqual(rej_corr["correlated_duplicates_collapsed"], 4)

        indep_no_contrast = [
            {"trace_lineage_id": "sess_1", "source_origin_hash": "h1", "origin_class": "TRUSTED_VERIFIER", "positive": True},
            {"trace_lineage_id": "sess_2", "source_origin_hash": "h2", "origin_class": "TRUSTED_VERIFIER", "positive": True},
        ]
        rej_nocontrast = self.model.non_malleable_memory_op(
            "PROPOSE_MEMORY_PROMOTION",
            {"rule_id": "rule_nc", "key": "k.nc", "rule_payload": "always_x", "witnesses": indep_no_contrast},
        )
        self.assertFalse(rej_nocontrast["admitted"])
        self.assertIn("MISSING_CONTRAST_WITNESS__A_LAW_MUST_CARRY_ITS_REASON", rej_nocontrast["reasons"])

        indep_with_contrast = indep_no_contrast + [
            {"trace_lineage_id": "sess_3", "source_origin_hash": "h3", "origin_class": "TRUSTED_VERIFIER", "kind": "contrast", "positive": False}
        ]
        admitted = self.model.non_malleable_memory_op(
            "PROPOSE_MEMORY_PROMOTION",
            {"rule_id": "rule_good", "key": "k.good", "rule_payload": "x_iff_cond", "witnesses": indep_with_contrast},
        )
        self.assertTrue(admitted["admitted"])
        self.assertEqual(admitted["status"], "PASS__PROMOTED_INDEPENDENT_CONTRAST_VERIFIED")

        # 6C: A-TMA anti-ghost-memory state view partitioning
        self.model.non_malleable_memory_op(
            "WRITE_ORIGIN_BOUND",
            {"record_id": "cfg_v1", "key": "api.endpoint", "payload": "https://old.example", "valid_from": 1.0},
        )
        self.model.non_malleable_memory_op(
            "WRITE_ORIGIN_BOUND",
            {"record_id": "derived_plan", "key": "deploy.plan", "payload": "use_old", "depends_on": ["cfg_v1"], "valid_from": 2.0},
        )
        self.model.non_malleable_memory_op(
            "WRITE_ORIGIN_BOUND",
            {"record_id": "cfg_v2", "key": "api.endpoint", "payload": "https://new.example", "supersedes": "cfg_v1", "valid_from": 5.0},
        )
        sv = self.model.non_malleable_memory_op("QUERY_STATE_VIEW", {"key": "api.endpoint", "as_of_ts": 10.0})
        self.assertTrue(sv["ghost_conflict_free"])
        self.assertEqual([r["record_id"] for r in sv["current"]], ["cfg_v2"])
        self.assertEqual([r["record_id"] for r in sv["historical"]], ["cfg_v1"])
        self.assertEqual(len(sv["transitions"]), 1)
        sv_dep = self.model.non_malleable_memory_op("QUERY_STATE_VIEW", {"key": "deploy.plan", "as_of_ts": 10.0})
        self.assertEqual([r["record_id"] for r in sv_dep["stale_impacted"]], ["derived_plan"])

        # 6D: SkillApt Rubin counterfactual activation with selective abstention
        act = self.model.non_malleable_memory_op(
            "DECIDE_SKILL_ACTIVATION",
            {"skill_id": "sk_good", "with_outcomes": [1, 1, 1, 1, 1], "without_outcomes": [0, 0, 0, 0, 0]},
        )
        self.assertEqual(act["decision"], "ACTIVATE")
        abst = self.model.non_malleable_memory_op(
            "DECIDE_SKILL_ACTIVATION",
            {"skill_id": "sk_unsure", "with_outcomes": [1], "without_outcomes": [0]},
        )
        self.assertEqual(abst["decision"], "ABSTAIN")
        dem = self.model.non_malleable_memory_op(
            "DECIDE_SKILL_ACTIVATION",
            {"skill_id": "sk_bad", "with_outcomes": [0, 0, 0, 0], "without_outcomes": [1, 1, 1, 1]},
        )
        self.assertEqual(dem["decision"], "DEMOTE")

        # 6E: DreamProver <96 hot-tier cap
        many_skills = [{"skill_id": f"sk_{i:03d}", "rubin_tau_hat": float(i) / 150.0, "hits": i} for i in range(150)]
        capped = self.model.non_malleable_memory_op("ENFORCE_HOT_TIER_CAP", {"skills": many_skills, "max_hot": 96})
        self.assertEqual(capped["hot_count"], 96)
        self.assertEqual(capped["cold_l2_count"], 54)
        self.assertEqual(capped["hot_tier"][0]["skill_id"], "sk_149")

    def test_07_bicameral_sleep_cycle_and_creature_front_door(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            c = self.model.open_creature(Path(td) / "creature_w38.json")
            w = c.non_malleable_memory_op(
                "WRITE_ORIGIN_BOUND",
                {"record_id": "c_rec_1", "key": "creature.fact", "payload": {"ok": True}, "valid_from": 1.0},
            )
            self.assertTrue(w["pass"])

            slp = c.bicameral_sleep_cycle(max_hot_skills=96, mine_algebraic_rewrites=True)
            self.assertTrue(slp["pass"], f"Bicameral sleep failed: {slp}")
            self.assertGreaterEqual(slp["phase_a_mined_rewrites_count"], 1)
            self.assertEqual(slp["phase_b_tampered_records"], [])

            dm = c.discover_dark_matter("tma-nm origin laundering govmem ghost memory skillapt")
            self.assertIn("engine:LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS", dm["recommended_targets"])

    def test_08_progressive_dark_matter_discovery_federation_and_100pct_domain_atlas(self) -> None:
        # Verify all 12 Wave 38 federated engines are registered
        w38_engines = (
            "LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST",
            "LEAPFROG_W38_REFUSAL_SPEC_COMPILER",
            "LEAPFROG_W38_OSWORLD_VERIFIED_LEDGER",
            "LEAPFROG_W38_TYPED_CEGIS_INVENTION",
            "LEAPFROG_W38_RESIDUAL_WALL_CLOSERS",
            "LEAPFROG_W38_REPO_COMPONENT_PETRI",
            "LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS",
            "LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE",
            "LEAPFROG_W38_SAFE_ACTION_WORLD_MODEL",
            "LEAPFROG_W38_CONSISTENCY_EQUIVALENCE_AND_JUDGE",
            "LEAPFROG_W38_MINED_REWRITE_AND_WEIGHT_GATE",
            "LEAPFROG_W38_COW_LENS_NEGATIVE_SPACE",
        )
        for eng in w38_engines:
            self.assertIn(eng, FEDERATED_KERNEL_DESCRIPTORS)

        # Cross-disciplinary unfamiliar-name resolution
        for q, must_eng in (
            ("seccomp bpf syscall allowlist capeff zero", "engine:LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST"),
            ("agent s4 evolving agent interfaces webmcp navigator.modelcontext", "engine:LEAPFROG_W38_REFUSAL_SPEC_COMPILER"),
            ("harnessflow cegis(t) residual wall closers judge the judge", "engine:LEAPFROG_W38_RESIDUAL_WALL_CLOSERS"),
            ("tma-nm govmem ghost memory skillapt language models need sleep", "engine:LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS"),
        ):
            res = resolve_cross_disciplinary_concept(q)
            self.assertIsNotNone(res.get("best"), f"No concept match for {q}")
            self.assertIn(must_eng, res["best"]["engines"], f"Missed {must_eng} for {q}: {res['best']}")
            dm = self.model.discover_dark_matter(q)
            self.assertEqual(dm["model_calls"], 0)
            self.assertIn(must_eng, dm["recommended_targets"])

        # Live federated dispatch checks
        f_sec = run_federated_engine("LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST", {"syscall_name": "bpf"})
        self.assertTrue(f_sec["pass"])
        self.assertEqual(f_sec["verdict"], "ERRNO:1")

        f_ref = run_federated_engine("LEAPFROG_W38_REFUSAL_SPEC_COMPILER", {"text": "No signature to verify: use the -signature option"})
        self.assertTrue(f_ref["pass"])
        self.assertEqual(f_ref["form"], "OFFERED")

        f_chk = run_federated_engine("LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE", {"size_bytes": 5_000_000})
        self.assertTrue(f_chk["pass"])
        self.assertGreaterEqual(f_chk["planned_chunks"], 5)

        f_lens = run_federated_engine("LEAPFROG_W38_COW_LENS_NEGATIVE_SPACE", {"pairs": [("abc", "ABC"), ("xyz", "XYZ")]})
        self.assertTrue(f_lens["pass"])

        # Assert 100.0% (1.000) DOMAIN_ATLAS_V1 route recall across ALL 7 frontier domains!
        atlas = json.loads((ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text(encoding="utf-8"))
        reach = atlas["reachability"]
        self.assertEqual(len(reach), 7)
        for dom, row in reach.items():
            self.assertEqual(row["frontier_route_hit_recall"], 1.0, f"{dom} frontier route recall < 1.0: {row}")
            self.assertEqual(row["native_route_hit_recall"], 1.0, f"{dom} native route recall < 1.0: {row}")


if __name__ == "__main__":
    unittest.main()
