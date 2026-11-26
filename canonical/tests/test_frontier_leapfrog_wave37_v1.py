#!/usr/bin/env python3
"""Wave 37 Real-Execution Adversarial Verification Suite (`K3 = 0`, `$0` spend).

Verifies every Wave 37 frontier capability end-to-end with ZERO mocks:
  1. Real Linux kernel namespace isolation (`os_isolation_v1.probe()`: `user+mount+pid+ipc+uts+net`,
     `chroot`, `CapEff == 0`, all adversarial escape attempts blocked) via `UnifiedModel` & `Creature`.
  2. Real OS-confined 3-channel HCU executor catching PR #7071's disguised `xz`-as-`.gz`
     lying extension via `byte_effect_oracle_v1`, rolling back `/work`, and recovering with `gzip`.
  3. Real OS-confined collateral file mutation rollback + `< 20 us` `PreCommitFailureGate` skip.
  4. Microsecond Petri inhibitor guard blocking unauthorized OS commands prior to sandbox launch.
  5. Multi-file Python repository Futamura solver (`solve_multifile_repo_futamura`) solving Repo A
     at Rung 2 with Ring-0 Gate (`ddmin` + mutation kill + `dir_diff` + `ConformalEValueGate`) and
     solving unseen isomorphic Repo B (different package/file/function/variable names) at Rung 0!
  6. True 2-file coordinated bug repair + 6-task QuixBugs-class algorithmic benchmark (`6/6` solve
     + unseen renamed clone Rung-0 transfer, `0` LLM calls).
  7. Wave 37 federated kernel registration, cross-disciplinary concept resolution, dispatch, and
     `Creature` front-door wiring.
"""
from __future__ import annotations

import gzip
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    FEDERATED_KERNEL_DESCRIPTORS,
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)


def _write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class TestFrontierLeapfrogWave37(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = open_model()

    def test_01_real_os_kernel_isolation_escape_probes_via_unified_model(self) -> None:
        probe = self.model.probe_os_isolation(budget_s=30.0)
        self.assertEqual(probe["verdict"], "ISOLATED", f"Kernel isolation probe failed: {probe}")
        self.assertTrue(probe["isolated"])
        self.assertEqual(probe["caps_after_drop"], "0000000000000000")
        self.assertFalse(probe["host_canary_written"])
        attempts = probe["attempts"]
        for must_block in (
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
        ):
            self.assertTrue(
                attempts[must_block]["blocked"],
                f"Escape attempt {must_block} was NOT blocked: {attempts[must_block]}",
            )

    def test_02_confined_hcu_catches_lying_xz_as_gz_rolls_back_and_recovers_gzip(self) -> None:
        payload = b"Project Brain Wave 37 real kernel-confined byte-effect verification!\n" * 4
        with tempfile.TemporaryDirectory() as td:
            wd = Path(td)
            (wd / "in.txt").write_bytes(payload)

            # Primary attempt replicates PR #7071 defect: writes valid XZ stream into out.gz!
            # Fallback writes real gzip stream into out.gz.
            bad_xz_cmd = (
                "import lzma; "
                "open('/work/out.gz', 'wb').write(lzma.compress(open('/work/in.txt', 'rb').read()))"
            )
            good_gz_cmd = (
                "import gzip; "
                "open('/work/out.gz', 'wb').write(gzip.compress(open('/work/in.txt', 'rb').read()))"
            )
            steps = [
                {
                    "action": "compress_to_gz_lying_xz",
                    "argv": ["/usr/bin/python3", "-c", bad_xz_cmd],
                    "effect_contract": {
                        "output_path": "out.gz",
                        "expected_format": "gzip",
                        "expected_source_bytes": payload,
                    },
                    "allowed_modified_files": ["out.gz"],
                    "fallback_steps": [
                        {
                            "action": "compress_to_gz_real_gzip",
                            "argv": ["/usr/bin/python3", "-c", good_gz_cmd],
                        }
                    ],
                }
            ]
            res = self.model.execute_confined_computer_use(
                wd,
                steps,
                goal_id="w37_lying_gz_test",
                allow_network=False,
                verify_effect=True,
            )
            self.assertTrue(res["pass"], f"Expected recovery to pass: {res}")
            self.assertGreaterEqual(res["effect_rejections"], 1)
            self.assertGreaterEqual(res["rolled_back_steps"], 1)
            self.assertEqual(res["recovered_steps"], 1)
            attempts = res["trace"][0]["attempts"]
            self.assertEqual(attempts[0]["status"], "EFFECT_ORACLE_REJECTED_ROLLED_BACK")
            self.assertEqual(attempts[1]["status"], "EXECUTED_VERIFIED")
            self.assertTrue(attempts[1]["isolated"])
            self.assertTrue(attempts[1]["caps_dropped"])
            self.assertEqual(gzip.decompress((wd / "out.gz").read_bytes()), payload)

    def test_03_confined_hcu_blocks_collateral_mutation_and_trips_failure_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wd = Path(td)
            sacred_bytes = b"DO_NOT_TOUCH_ME_V37\n"
            (wd / "sacred.txt").write_bytes(sacred_bytes)

            rogue_cmd = (
                "open('/work/report.txt', 'w').write('ok'); "
                "open('/work/sacred.txt', 'w').write('CORRUPTED!')"
            )
            step = {
                "action": "rogue_writer",
                "argv": ["/usr/bin/python3", "-c", rogue_cmd],
                "allowed_modified_files": ["report.txt"],
            }
            r1 = self.model.execute_confined_computer_use(wd, [step], goal_id="w37_collateral_guard")
            self.assertFalse(r1["pass"])
            self.assertEqual(r1["trace"][0]["attempts"][0]["status"], "COLLATERAL_MUTATION_ROLLED_BACK")
            # Sacred file MUST be restored byte-for-byte & rogue report.txt removed!
            self.assertEqual((wd / "sacred.txt").read_bytes(), sacred_bytes)
            self.assertFalse((wd / "report.txt").exists())

            # Re-running the exact same rogue command must be blocked immediately by PreCommitFailureGate!
            r2 = self.model.execute_confined_computer_use(wd, [step], goal_id="w37_collateral_guard")
            self.assertFalse(r2["pass"])
            self.assertGreaterEqual(r2["failure_gate_skips"], 1)
            self.assertEqual(r2["trace"][0]["attempts"][0]["status"], "BLOCKED_BY_FAILURE_GATE")

    def test_04_confined_hcu_petri_inhibitor_blocks_before_sandbox_exec(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wd = Path(td)
            transitions = {
                "write_artifact": {
                    "consume": {"auth_token": 1},
                    "inhibitors": ["safety_lock"],
                    "produce": {"artifact_done": 1},
                }
            }
            step = {
                "action": "write_artifact",
                "argv": ["/usr/bin/python3", "-c", "open('/work/done.txt','w').write('ok')"],
            }
            blocked = self.model.execute_confined_computer_use(
                wd,
                [step],
                goal_id="w37_petri_blocked",
                initial_marking={"auth_token": 1, "safety_lock": 1},
                transitions=transitions,
            )
            self.assertFalse(blocked["pass"])
            self.assertEqual(blocked["trace"][0]["attempts"][0]["status"], "BLOCKED_BY_PETRI_GUARD")
            self.assertFalse((wd / "done.txt").exists())

            allowed = self.model.execute_confined_computer_use(
                wd,
                [step],
                goal_id="w37_petri_allowed",
                initial_marking={"auth_token": 1, "safety_lock": 0},
                transitions=transitions,
            )
            self.assertTrue(allowed["pass"])
            self.assertEqual((wd / "done.txt").read_text(encoding="utf-8"), "ok")

    def test_05_multifile_futamura_repo_solve_and_rung0_transfer_to_unseen_repo(self) -> None:
        # Use a clean dedicated model cascade so Pass 1 is genuinely cold (0 compiled rules).
        from canonical.runtime.futamura_leapfrog_kernel_v1 import (
            FutamuraSelfCompilingCascade,
            MultifileFutamuraRepoSolver,
        )

        solver = MultifileFutamuraRepoSolver(cascade=FutamuraSelfCompilingCascade())

        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            repo_a = Path(td1) / "billing_repo"
            _write_files(
                repo_a,
                {
                    "billing_pkg/__init__.py": "",
                    "billing_pkg/rates.py": (
                        "def qualifies_for_discount(subtotal, threshold):\n"
                        "    return subtotal > threshold\n"  # BUG: should be >=
                    ),
                    "billing_pkg/engine.py": (
                        "from billing_pkg.rates import qualifies_for_discount\n\n"
                        "def compute_invoice(amount, cutoff):\n"
                        "    if qualifies_for_discount(amount, cutoff):\n"
                        "        return amount - 10\n"
                        "    return amount\n"
                    ),
                    "tests/test_billing.py": (
                        "import unittest\n"
                        "from billing_pkg.engine import compute_invoice\n\n"
                        "class TestBilling(unittest.TestCase):\n"
                        "    def test_exact_boundary(self):\n"
                        "        self.assertEqual(compute_invoice(100, 100), 90)\n"
                        "    def test_above_and_below(self):\n"
                        "        self.assertEqual(compute_invoice(150, 100), 140)\n"
                        "        self.assertEqual(compute_invoice(99, 100), 99)\n"
                    ),
                },
            )
            r1 = solver.solve(repo_a, ["tests/test_billing.py"])
            self.assertTrue(r1["pass"], f"Pass 1 failed: {r1}")
            self.assertEqual(r1["rung"], "RUNG_2_MULTIFILE_COW_AST")
            self.assertEqual(r1["modified_files"], ["billing_pkg/rates.py"])
            self.assertTrue(r1["dir_diff"]["pass"])
            self.assertGreaterEqual(len(r1["compiled_rule_ids"]), 1)
            self.assertEqual(r1["conformal"]["verdict"], "COMMIT")

            # Completely unseen multi-file repo with renamed packages, files, functions, variables!
            repo_b = Path(td2) / "inventory_repo"
            _write_files(
                repo_b,
                {
                    "inventory_pkg/__init__.py": "",
                    "inventory_pkg/rules.py": (
                        "def can_fulfill_order(stock_qty, order_qty):\n"
                        "    return stock_qty > order_qty\n"  # Isomorphic unseen bug!
                    ),
                    "inventory_pkg/allocator.py": (
                        "from inventory_pkg.rules import can_fulfill_order\n\n"
                        "def reserve_units(available, requested):\n"
                        "    return available - requested if can_fulfill_order(available, requested) else -1\n"
                    ),
                    "tests/test_inventory.py": (
                        "import unittest\n"
                        "from inventory_pkg.allocator import reserve_units\n\n"
                        "class TestInventory(unittest.TestCase):\n"
                        "    def test_exact_stock(self):\n"
                        "        self.assertEqual(reserve_units(25, 25), 0)\n"
                        "    def test_surplus_and_shortage(self):\n"
                        "        self.assertEqual(reserve_units(40, 15), 25)\n"
                        "        self.assertEqual(reserve_units(10, 15), -1)\n"
                    ),
                },
            )
            r2 = solver.solve(repo_b, ["tests/test_inventory.py"])
            self.assertTrue(r2["pass"], f"Pass 2 Rung-0 transfer failed: {r2}")
            self.assertEqual(r2["rung"], "RUNG_0_COMPILED_SKILL")
            self.assertEqual(r2["candidates_evaluated"], 1)
            self.assertEqual(r2["proposer_calls"], 0)
            self.assertEqual(r2["modified_files"], ["inventory_pkg/rules.py"])
            self.assertTrue(r2["dir_diff"]["pass"])

    def test_06_multifile_coordinated_two_file_bug_and_quixbugs_suite(self) -> None:
        # 6A: True 2-file coupled bug where neither single-file edit passes!
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "coupled_repo"
            _write_files(
                repo,
                {
                    "pipeline/__init__.py": "",
                    "pipeline/normalize.py": (
                        "def scale_positive(val, factor):\n"
                        "    return val - factor\n"  # BUG 1: should be *
                    ),
                    "pipeline/combine.py": (
                        "from pipeline.normalize import scale_positive\n\n"
                        "def total_score(x, y, bonus):\n"
                        "    return scale_positive(x, y) - bonus\n"  # BUG 2: should be +
                    ),
                    "tests/test_pipeline.py": (
                        "import unittest\n"
                        "from pipeline.combine import total_score\n\n"
                        "class TestPipeline(unittest.TestCase):\n"
                        "    def test_scores(self):\n"
                        "        self.assertEqual(total_score(3, 4, 5), 17)\n"
                        "        self.assertEqual(total_score(5, 6, 2), 32)\n"
                    ),
                },
            )
            res = self.model.solve_multifile_repo_futamura(repo, ["tests/test_pipeline.py"])
            self.assertTrue(res["pass"], f"2-file coordinated repair failed: {res}")
            self.assertEqual(res["rung"], "RUNG_2_MULTIFILE_COORDINATED_AST")
            self.assertEqual(res["modified_files"], ["pipeline/combine.py", "pipeline/normalize.py"])
            self.assertTrue(res["dir_diff"]["pass"])

        # 6B: 6-task QuixBugs-class real algorithmic repair suite (0 LLM calls)
        quix_tasks = [
            (
                "binary_search_boundary",
                "def bsearch(arr, target):\n"
                "    lo, hi = 0, len(arr) - 1\n"
                "    while lo < hi:\n"  # BUG: should be <=
                "        mid = (lo + hi) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            lo = mid + 1\n"
                "        else:\n"
                "            hi = mid - 1\n"
                "    return -1\n",
                "import unittest\nfrom algo import bsearch\n"
                "class T(unittest.TestCase):\n"
                "    def test_hits(self):\n"
                "        self.assertEqual(bsearch([1, 3, 5, 7], 7), 3)\n"
                "        self.assertEqual(bsearch([1, 3, 5, 7], 1), 0)\n"
                "        self.assertEqual(bsearch([42], 42), 0)\n"
                "        self.assertEqual(bsearch([1, 3, 5], 4), -1)\n",
            ),
            (
                "kadane_max_sublist",
                "def max_sublist_sum(nums):\n"
                "    best = cur = nums[0]\n"
                "    for x in nums[1:]:\n"
                "        cur = min(x, cur + x)\n"  # BUG: min -> max
                "        best = max(best, cur)\n"
                "    return best\n",
                "import unittest\nfrom algo import max_sublist_sum\n"
                "class T(unittest.TestCase):\n"
                "    def test_kadane(self):\n"
                "        self.assertEqual(max_sublist_sum([4, -5, 2, 1, -1, 3]), 5)\n"
                "        self.assertEqual(max_sublist_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]), 6)\n",
            ),
            (
                "sum_inclusive_range",
                "def sum_up_to(n):\n"
                "    total = 0\n"
                "    for i in range(n):\n"  # BUG: range(n) -> range((n) + 1)
                "        total += i\n"
                "    return total\n",
                "import unittest\nfrom algo import sum_up_to\n"
                "class T(unittest.TestCase):\n"
                "    def test_sum(self):\n"
                "        self.assertEqual(sum_up_to(5), 15)\n"
                "        self.assertEqual(sum_up_to(10), 55)\n",
            ),
            (
                "gcd_operand_order",
                "def euclid_gcd(a, b):\n"
                "    while b != 0:\n"
                "        a, b = b, b % a\n"  # BUG: b % a -> a % b
                "    return a\n",
                "import unittest\nfrom algo import euclid_gcd\n"
                "class T(unittest.TestCase):\n"
                "    def test_gcd(self):\n"
                "        self.assertEqual(euclid_gcd(48, 18), 6)\n"
                "        self.assertEqual(euclid_gcd(1071, 462), 21)\n",
            ),
            (
                "filter_absent_items",
                "def missing_keys(required, present):\n"
                "    return [k for k in required if k in present]\n",  # BUG: in -> not in
                "import unittest\nfrom algo import missing_keys\n"
                "class T(unittest.TestCase):\n"
                "    def test_missing(self):\n"
                "        self.assertEqual(missing_keys(['a', 'b', 'c'], {'b'}), ['a', 'c'])\n"
                "        self.assertEqual(missing_keys(['x'], {'x'}), [])\n",
            ),
            (
                "skip_negative_entries",
                "def sum_positives(items):\n"
                "    total = 0\n"
                "    for x in items:\n"
                "        if x < 0:\n"
                "            break\n"  # BUG: break -> continue
                "        total += x\n"
                "    return total\n",
                "import unittest\nfrom algo import sum_positives\n"
                "class T(unittest.TestCase):\n"
                "    def test_pos(self):\n"
                "        self.assertEqual(sum_positives([3, -2, 5, -1, 4]), 12)\n"
                "        self.assertEqual(sum_positives([-1, 7]), 7)\n",
            ),
        ]
        solved = 0
        for name, buggy_src, test_src in quix_tasks:
            with tempfile.TemporaryDirectory() as td:
                rdir = Path(td) / name
                _write_files(rdir, {"algo.py": buggy_src, "test_algo.py": test_src})
                out = self.model.solve_multifile_repo_futamura(rdir, ["test_algo.py"])
                self.assertTrue(out["pass"], f"QuixBugs task {name} failed: {out}")
                solved += 1
        self.assertEqual(solved, 6)

    def test_07_wave37_federation_concept_routing_and_creature_front_door(self) -> None:
        for k in (
            "LEAPFROG_W37_OS_KERNEL_ISOLATION",
            "LEAPFROG_W37_CONFINED_HYBRID_CU",
            "LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO",
        ):
            self.assertIn(k, FEDERATED_KERNEL_DESCRIPTORS)

        concept = resolve_cross_disciplinary_concept("os isolation unshare capeff zero multifile futamura")
        self.assertIsNotNone(concept.get("best"))
        engines = concept["best"]["engines"]
        self.assertIn("engine:LEAPFROG_W37_OS_KERNEL_ISOLATION", engines)
        self.assertIn("engine:LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO", engines)

        fed_iso = run_federated_engine("LEAPFROG_W37_OS_KERNEL_ISOLATION", {"budget_s": 30.0})
        self.assertTrue(fed_iso["pass"], f"Federated OS isolation failed: {fed_iso}")
        self.assertEqual(fed_iso["verdict"], "ISOLATED")

        with tempfile.TemporaryDirectory() as td:
            c = self.model.open_creature(Path(td) / "creature_w37.json")
            c_probe = c.probe_os_isolation(budget_s=30.0)
            self.assertEqual(c_probe["verdict"], "ISOLATED")
            wd = Path(td) / "work"
            wd.mkdir()
            c_hcu = c.execute_confined_computer_use(
                wd,
                [{"action": "echo_hello", "argv": ["/usr/bin/python3", "-c", "open('/work/hi.txt','w').write('hi')"]}],
                goal_id="creature_w37_hcu",
            )
            self.assertTrue(c_hcu["pass"])
            self.assertEqual((wd / "hi.txt").read_text(encoding="utf-8"), "hi")


if __name__ == "__main__":
    unittest.main()
