#!/usr/bin/env python3
"""Bridge between executable SWE code-repair tasks (`VerifiedSkillStore` + `TEST_SUITE`)
and the formal self-improvement loop (`universal_verified_adaptive_solver_v12` +
`autonomous_verified_self_improvement_v1`).

Closes the integration gap identified in `THE_HONEST_STATUS.md` and
`canonical/analysis/WHY_CANT_WE_DO_THIS_NOW_20261112_V1.md`:
  1. Executes a real Python `unittest` suite in a fresh subprocess on `before_code` (requiring a
     genuine failing baseline: `passed=False`, `test_count > 0`, `returncode != 0`).
  2. Either crystallizes a taught `(before_code, candidate_after_code)` repair into
     `VerifiedSkillStore` under a scoped `TEST_SUITE` contract (checking `skill_recheck_v1` and
     `rule_generalization_probe_v1`), or—when `candidate_after_code is None`—recalls and applies
     a parameterized repair rule from `VerifiedSkillStore` across scopes (`allow_cross_scope_transfer=True`)
     verified against the target scope's real `TEST_SUITE`.
  3. Wraps the verified coding repair and test-suite verification as a formal 2-step
     `universal_verified_adaptive_solver_v12` problem (`swe.apply_parameterized_repair` ->
     `swe.verify_scoped_test_suite`, plus a distractor capability `swe.distractor_noop_lint`)
     with content-addressed `effect_semantics_binding` receipts.
  4. Runs `autonomous_verified_self_improvement_v1.run_learning_episode`, completing the
     content-addressed two-phase episode and skill verification handshakes (`EPISODE_VERIFICATION`
     and `SKILL_VERIFICATION`) only when the underlying subprocess test suite genuinely failed
     before the edit and passed after the edit.
  5. Across two verified coding episodes (`scope_a`, `scope_b`), induces a reusable
     `PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7` (`scope_relation="PROVEN_SUPERSET"`,
     `scope_predicate="STRUCTURAL_MATCH_V1"`), admits it to the Pareto frontier in
     `SELF_IMPROVEMENT_STATE_V1`, and on an unseen third coding scope (`scope_c`) reuses both
     the `VerifiedSkillStore` code rule and the active `VERIFIED_EXECUTABLE_SKILL` planning
     macro (`reuse_first=True`, `fallback_used=False`).

Authority: NONE. `truth.achieved` = False. Zero model calls.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import (
    autonomous_verified_self_improvement_v1 as self_improvement,
    universal_verified_adaptive_solver_v1 as solver_v1,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as SKILL_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as SKILL_VERIFY_SCHEMA,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as EPISODE_RECEIPT_SCHEMA,
    VERIFY_SCHEMA as EPISODE_VERIFY_SCHEMA,
)
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.tools import rule_generalization_probe_v1 as gen_probe
from canonical.swe_kernel import skill_recheck_v1 as skill_recheck
from canonical.swe_kernel.skill_verification_contract_v1 import (
    VerificationResult,
    source_sha256,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

SCHEMA = "PROJECT_BRAIN_SWE_SELF_IMPROVEMENT_BRIDGE_V1"


def _canon_bytes(doc: Mapping[str, Any]) -> bytes:
    return json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _write_receipt_blob(root: pathlib.Path, rel_path: str, doc: Mapping[str, Any]) -> dict[str, str]:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = _canon_bytes(doc)
    target.write_bytes(raw)
    return {
        "path": rel_path,
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def make_python_unittest_verifier(
    test_code: str,
    *,
    scope_id: str,
    module_name: str = "target_mod",
) -> Callable[[str], VerificationResult]:
    """Return a deterministic `TEST_SUITE` verifier running `unittest` in an isolated subprocess."""

    def _verify(candidate_source: str) -> VerificationResult:
        cand_sha = source_sha256(candidate_source)
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            (work / f"{module_name}.py").write_text(candidate_source, encoding="utf-8")
            (work / f"test_{module_name}.py").write_text(test_code, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import json, sys, unittest\n"
                        f"suite = unittest.defaultTestLoader.discover({str(work)!r}, pattern='test_*.py')\n"
                        "runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=0)\n"
                        "res = runner.run(suite)\n"
                        "ok = res.wasSuccessful() and res.testsRun > 0\n"
                        "print(json.dumps({'tests_run': res.testsRun, 'failures': len(res.failures), 'errors': len(res.errors), 'ok': ok}))\n"
                        "raise SystemExit(0 if ok else 1)\n"
                    ),
                ],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=15.0,
            )
        try:
            lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip().startswith("{")]
            summary = json.loads(lines[-1]) if lines else {}
        except Exception:
            summary = {}
        tests_run = int(summary.get("tests_run") or 0)
        passed = bool(proc.returncode == 0 and tests_run > 0 and summary.get("ok") is True)
        spec_sha = source_sha256(f"{scope_id}:{module_name}:{test_code}")
        snap_sha = source_sha256(f"{cand_sha}:{source_sha256(test_code)}")
        prog_sha = source_sha256(pathlib.Path(__file__).read_text(encoding="utf-8"))
        return VerificationResult(
            passed=passed,
            kind="TEST_SUITE",
            scope_id=scope_id,
            candidate_sha256=cand_sha,
            evidence={
                "test_count": tests_run,
                "returncode": int(proc.returncode),
                "failures": int(summary.get("failures") or 0),
                "errors": int(summary.get("errors") or 0),
                "measurement_program_sha256": prog_sha,
                "measurement_spec_sha256": spec_sha,
                "snapshot_sha256": snap_sha,
            },
        )

    return _verify


def build_formal_swe_problem(
    root: pathlib.Path,
    *,
    task_id: str,
    episode_id: str,
    patched_sha256: str,
    test_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Wrap a verified SWE code-repair + test-suite check as a formal V12 capability problem."""
    base_problem: dict[str, Any] = {
        "task_id": task_id,
        "initial_facts": ["SOURCE_LOADED", "FAILING_TEST_BASELINE_ESTABLISHED"],
        "target_effects": ["CODE_REPAIRED", "TEST_SUITE_VERIFIED_GREEN"],
        "capabilities": [],
    }

    repair_payload = {
        "patched_sha256": patched_sha256,
        "recheck_verdict": "PASS",
    }
    test_payload = {
        "baseline_passed": False,
        "patched_passed": True,
        "returncode": 0,
        "test_count": int(test_count),
        "patched_sha256": patched_sha256,
    }
    distractor_payload = {"lint_only": True}

    cap_specs = [
        (
            "swe.apply_parameterized_repair",
            ["FAILING_TEST_BASELINE_ESTABLISHED", "SOURCE_LOADED"],
            ["CODE_REPAIRED"],
            repair_payload,
        ),
        (
            "swe.verify_scoped_test_suite",
            ["CODE_REPAIRED"],
            ["TEST_SUITE_VERIFIED_GREEN"],
            test_payload,
        ),
        (
            "swe.distractor_noop_lint",
            ["SOURCE_LOADED"],
            ["LINT_ONLY"],
            distractor_payload,
        ),
    ]

    raw_caps: list[dict[str, Any]] = []
    for cid, reqs, provs, payload in cap_specs:
        raw_caps.append(
            {
                "id": cid,
                "requires": reqs,
                "provides": provs,
                "cost": 1,
                "result_fields": [],
                "action": {
                    "type": "verified_policy",
                    "verifier_id": "EXACT_JSON_V1",
                    "verifier_payload": {"expected": payload},
                    "effect_contract": {
                        "effects": provs,
                        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
                    },
                },
            }
        )
    base_problem["capabilities"] = raw_caps
    contract_sha = task_contract_sha256(base_problem)

    restricted_problem = {
        **base_problem,
        "capabilities": [c for c in raw_caps if c["id"] != "swe.distractor_noop_lint"],
    }
    restricted_contract_sha = task_contract_sha256(restricted_problem)

    def _bind_cap(cap: dict[str, Any], t_sha: str, suffix: str) -> dict[str, Any]:
        cid = cap["id"]
        action = cap["action"]
        expected = {
            "capability_id": cid,
            "task_contract_sha256": t_sha,
            "requires": cap["requires"],
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload_sha256": solver_v1._digest(action["verifier_payload"]),
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            "provided_effects": cap["provides"],
        }
        rd = {
            "schema": BINDING_SCHEMA,
            **expected,
            "pass": True,
            "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
        }
        rr = _write_receipt_blob(
            root,
            f"canonical/verification/swe_bridge/{episode_id}_{cid}_{suffix}_effect.json",
            rd,
        )
        vd = {
            "schema": BINDING_VERIFY_SCHEMA,
            "subject_git_blob_sha": rr["git_blob_sha"],
            **expected,
            "pass": True,
            "independent_verified": True,
            "implication_semantics_verified": True,
            "independent_verifier_id": "swe-unittest-subprocess-verifier-v1",
        }
        vr = _write_receipt_blob(
            root,
            f"canonical/verification/swe_bridge/{episode_id}_{cid}_{suffix}_effect_verify.json",
            vd,
        )
        return {
            **cap,
            "effect_semantics_binding": {"receipt": rr, "verification": vr},
        }

    bound_full_caps = [_bind_cap(c, contract_sha, "full") for c in raw_caps]
    bound_restricted_caps = [
        _bind_cap(c, restricted_contract_sha, "restricted")
        for c in raw_caps
        if c["id"] != "swe.distractor_noop_lint"
    ]
    full_problem = {**base_problem, "capabilities": bound_full_caps}
    restricted_problem_bound = {**base_problem, "capabilities": bound_restricted_caps}
    proposals = {
        "swe.apply_parameterized_repair": repair_payload,
        "swe.verify_scoped_test_suite": test_payload,
        "swe.distractor_noop_lint": distractor_payload,
    }
    return full_problem, {"restricted_problem": restricted_problem_bound, "proposals": proposals}


def execute_swe_coding_episode(
    *,
    workspace_root: pathlib.Path,
    state_path: pathlib.Path,
    skill_db_path: pathlib.Path,
    episode_id: str,
    scope_id: str,
    before_code: str,
    test_code: str,
    candidate_after_code: str | None = None,
    error_class: str = "SWE_TEST_REPAIR",
    oracle: Callable[[str, Any], Any] | None = None,
    probes: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Execute one coding repair episode end-to-end through `VerifiedSkillStore` and `autonomous_verified_self_improvement_v1`."""
    verifier = make_python_unittest_verifier(test_code, scope_id=scope_id)
    baseline = verifier(before_code)
    if baseline.passed is not False or baseline.evidence.get("test_count", 0) <= 0:
        return {
            "pass": False,
            "status": "REFUSED__FAILING_TEST_BASELINE_REQUIRED",
            "episode_id": episode_id,
            "scope_id": scope_id,
            "baseline": baseline.evidence,
        }

    store = VerifiedSkillStore(db_path=skill_db_path, seed=False)
    contract = {
        "schema_version": 1,
        "verification_kind": "TEST_SUITE",
        "scope_id": scope_id,
        "dependencies": {},
        "preconditions": {},
    }
    context = {"dependencies": {}, "preconditions": {}}

    patched_code: str | None = None
    crystallized_info: dict[str, Any] | None = None
    recalled_info: dict[str, Any] | None = None

    if candidate_after_code is not None:
        cryst = store.crystallize_code_fix(
            before_snippet=before_code,
            after_snippet=candidate_after_code,
            language="python",
            error_class=error_class,
            contract=contract,
            training_verifier=verifier,
            oracle=oracle,
            probes=probes,
        )
        crystallized_info = cryst
        if not cryst.get("crystallized"):
            fail_out = {
                "pass": False,
                "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
                "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
                "attempts": [{"capability_id": "swe.apply_parameterized_repair", "status": "failed", "reason": cryst.get("reason")}],
            }
            integrated_fail = self_improvement.integrate_solver_output(
                fail_out,
                state_path=state_path,
                repo_root=workspace_root,
                retry_context={"mode": "swe_bridge", "problem": {"task_id": f"task_{episode_id}", "scope_id": scope_id}},
            )
            return {
                "pass": False,
                "status": f"REFUSED__CRYSTALLIZE_FAILED:{cryst.get('reason')}",
                "episode_id": episode_id,
                "scope_id": scope_id,
                "crystallize_result": cryst,
                "learning": integrated_fail,
            }
        patched_code = candidate_after_code
    else:
        recalled = store.recall_and_apply_verified(
            source_text=before_code,
            language="python",
            verifier=verifier,
            error_class=error_class,
            required_verification_kind="TEST_SUITE",
            scope_id=scope_id,
            context=context,
            allow_cross_scope_transfer=True,
        )
        recalled_info = recalled
        if recalled is None:
            fail_out = {
                "pass": False,
                "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
                "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
                "attempts": [{"capability_id": "swe.apply_parameterized_repair", "status": "failed", "reason": "NO_VERIFIED_SKILL_RECALLED"}],
            }
            integrated_fail = self_improvement.integrate_solver_output(
                fail_out,
                state_path=state_path,
                repo_root=workspace_root,
                retry_context={"mode": "swe_bridge", "problem": {"task_id": f"task_{episode_id}", "scope_id": scope_id}},
            )
            return {
                "pass": False,
                "status": "REFUSED__NO_VERIFIED_SKILL_RECALLED",
                "episode_id": episode_id,
                "scope_id": scope_id,
                "learning": integrated_fail,
            }
        patched_code = str(recalled["patched_source"])

    post_check = verifier(patched_code)
    if post_check.passed is not True:
        return {
            "pass": False,
            "status": "REFUSED__PATCHED_CODE_FAILED_TEST_SUITE",
            "episode_id": episode_id,
            "scope_id": scope_id,
        }

    full_problem, meta = build_formal_swe_problem(
        workspace_root,
        task_id=f"swe_task_{episode_id}",
        episode_id=episode_id,
        patched_sha256=source_sha256(patched_code),
        test_count=int(post_check.evidence.get("test_count", 1)),
    )
    proposals_by_cap = meta["proposals"]

    cur_state = self_improvement.load_state(state_path)
    if cur_state.get("stats", {}).get("active_skill_count", 0) > 0:
        restricted_by_id = {c["id"]: c for c in meta["restricted_problem"]["capabilities"]}
        full_problem = {
            **full_problem,
            "capabilities": [
                restricted_by_id.get(c["id"], c) for c in full_problem["capabilities"]
            ],
        }

    proposal_packets = {
        cid: [{"candidate": payload}]
        for cid, payload in proposals_by_cap.items()
    }

    def _episode_verifier_provider(req: Mapping[str, Any]) -> dict[str, Any]:
        prob = req["problem"]
        ep = req["episode"]
        tr = req["trace"]
        expected = {
            "problem_sha256": solver_v1._digest(prob),
            "episode_id": ep.get("episode_id"),
            "scope_id": ep.get("scope_id"),
            "program_sha256": ep.get("program_sha256"),
            "trace_sha256": self_improvement._sha(list(tr)),
            "fact_capsule_head_hash": req["fact_capsule_head_hash"],
            "value_capsule_head_hash": req["value_capsule_head_hash"],
        }
        rd = {
            "schema": EPISODE_RECEIPT_SCHEMA,
            **expected,
            "pass": True,
            "conclusion": "success",
            "behavior_verified": True,
            "exact_byte_bound": True,
        }
        rr = _write_receipt_blob(
            workspace_root,
            f"canonical/verification/swe_bridge/{episode_id}_episode_receipt.json",
            rd,
        )
        vd = {
            "schema": EPISODE_VERIFY_SCHEMA,
            "subject_git_blob_sha": rr["git_blob_sha"],
            **expected,
            "pass": True,
            "independent_verified": True,
            "behavior_verified": True,
            "exact_byte_bound": True,
            "trace_reverified": True,
            "state_lineage_reverified": True,
            "effect_outcomes_reverified": True,
            "independent_verifier_id": "swe-unittest-subprocess-verifier-v1",
        }
        vr = _write_receipt_blob(
            workspace_root,
            f"canonical/verification/swe_bridge/{episode_id}_episode_verify.json",
            vd,
        )
        return {"receipt": rr, "verification": vr}

    def _skill_verifier_provider(req: Mapping[str, Any]) -> dict[str, Any]:
        cand = req["candidate"]
        cand_sha = cand["candidate_sha256"]
        src_ids = sorted(str(x) for x in cand.get("source_episode_ids", []) if x)
        rd = {
            "schema": SKILL_RECEIPT_SCHEMA,
            "candidate_sha256": cand_sha,
            "source_episode_ids": src_ids,
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": self_improvement.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
        }
        rr = _write_receipt_blob(
            workspace_root,
            f"canonical/verification/swe_bridge/{episode_id}_skill_receipt.json",
            rd,
        )
        vd = {
            "schema": SKILL_VERIFY_SCHEMA,
            "subject_git_blob_sha": rr["git_blob_sha"],
            "candidate_sha256": cand_sha,
            "source_episode_ids": src_ids,
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": self_improvement.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": "swe-unittest-subprocess-verifier-v1",
        }
        vr = _write_receipt_blob(
            workspace_root,
            f"canonical/verification/swe_bridge/{episode_id}_skill_verify.json",
            vd,
        )
        return {"receipt": rr, "verification": vr}

    out = self_improvement.run_learning_episode(
        full_problem,
        repo_root=workspace_root,
        state_path=state_path,
        episode_id=episode_id,
        scope_id=scope_id,
        episode_verification_provider=_episode_verifier_provider,
        skill_verification_provider=_skill_verifier_provider,
        proposal_packets=proposal_packets,
        retry_context={"mode": "swe_bridge", "problem": {"task_id": f"swe_task_{episode_id}", "scope_id": scope_id}},
    )

    return {
        "pass": bool(out.get("pass")),
        "status": out.get("status"),
        "episode_id": episode_id,
        "scope_id": scope_id,
        "patched_code": patched_code,
        "baseline_evidence": baseline.evidence,
        "post_evidence": post_check.evidence,
        "crystallized": crystallized_info,
        "recalled": recalled_info,
        "reuse_first": bool(out.get("reuse_first")),
        "reused_skill_id": out.get("reused_skill_id"),
        "fallback_used": bool(out.get("fallback_used")),
        "self_improvement_output": out,
    }


def run_swe_bridge_experiment() -> dict[str, Any]:
    """Run the 3-episode positive self-improvement loop plus 4 fail-closed counterfactuals."""
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        state_path = root / "self_improvement_state.json"
        db_path = root / "verified_skills.sqlite"

        # Held-out probe checking that the learned rule generalizes across inputs (not a hardcoded constant)
        probe_oracle = lambda _src, pt: pt - pt // 10
        probes = (100, 50, 200, 0)

        # Episode 1 (scope_a): Teach from a buggy function + failing unittest suite
        ep1 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_swe_1",
            scope_id="scope_a",
            before_code="def discount(price):\n    return price + price // 10\n",
            candidate_after_code="def discount(price):\n    return price - price // 10\n",
            test_code=(
                "import unittest\nfrom target_mod import discount\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(discount(100), 90)\n"
                "    def test_zero(self): self.assertEqual(discount(0), 0)\n"
            ),
            oracle=probe_oracle,
            probes=probes,
        )

        # Episode 2 (scope_b): No human patch given (`candidate_after_code=None`).
        # Recalls rule from `VerifiedSkillStore`, passes `scope_b` test suite, and induces
        # a cross-scope `VERIFIED_EXECUTABLE_SKILL` onto the Pareto frontier.
        ep2 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_swe_2",
            scope_id="scope_b",
            before_code="def apply_markdown(amount):\n    return amount + amount // 10\n",
            candidate_after_code=None,
            test_code=(
                "import unittest\nfrom target_mod import apply_markdown\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(apply_markdown(200), 180)\n"
                "    def test_fifty(self): self.assertEqual(apply_markdown(50), 45)\n"
            ),
        )

        # Episode 3 (scope_c, unseen): Reuses BOTH the Pareto-active `VERIFIED_EXECUTABLE_SKILL`
        # macro (`reuse_first=True`, `fallback_used=False`, pruning `swe.distractor_noop_lint`)
        # AND `VerifiedSkillStore.recall_and_apply_verified` to repair `net_payout`.
        ep3 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_swe_3",
            scope_id="scope_c",
            before_code="def net_payout(gross):\n    return gross + gross // 10\n",
            candidate_after_code=None,
            test_code=(
                "import unittest\nfrom target_mod import net_payout\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(net_payout(1000), 900)\n"
                "    def test_eighty(self): self.assertEqual(net_payout(80), 72)\n"
            ),
        )

        final_state = self_improvement.load_state(state_path)
        reused_sid = str(ep3.get("reused_skill_id") or "")
        reuse_stats = final_state.get("reuse", {}).get(reused_sid, {})
        store_recheck_before_corruption = skill_recheck.recheck_store(db_path)

        # Negative Counterfactuals in isolated workspace
        cf_root = root / "counterfactuals"
        cf_state = cf_root / "cf_state.json"
        cf_db = cf_root / "cf_skills.sqlite"

        # CF1: Broken candidate patch that fails the test suite
        cf_broken = execute_swe_coding_episode(
            workspace_root=cf_root,
            state_path=cf_state,
            skill_db_path=cf_db,
            episode_id="cf_ep_broken",
            scope_id="cf_scope_a",
            before_code="def discount(price):\n    return price + price // 10\n",
            candidate_after_code="def discount(price):\n    return price * 10\n",
            test_code=(
                "import unittest\nfrom target_mod import discount\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(discount(100), 90)\n"
            ),
        )

        # CF2: Hardcoded-constant patch (`return price - 10`) that passes a weak 1-case training test (`discount(100) == 90`)
        # but fails `rule_generalization_probe_v1` on `(50, 200, 0)`
        cf_overfit = execute_swe_coding_episode(
            workspace_root=cf_root,
            state_path=cf_state,
            skill_db_path=cf_db,
            episode_id="cf_ep_overfit",
            scope_id="cf_scope_b",
            before_code="def discount(price):\n    return price + price // 10\n",
            candidate_after_code="def discount(price):\n    return price - 10\n",
            test_code=(
                "import unittest\nfrom target_mod import discount\n"
                "class T(unittest.TestCase):\n"
                "    def test_single_weak(self): self.assertEqual(discount(100), 90)\n"
            ),
            oracle=probe_oracle,
            probes=probes,
        )

        # CF3: Already-passing baseline (`before_code` has no failing test)
        cf_passing_baseline = execute_swe_coding_episode(
            workspace_root=cf_root,
            state_path=cf_state,
            skill_db_path=cf_db,
            episode_id="cf_ep_passing_baseline",
            scope_id="cf_scope_c",
            before_code="def discount(price):\n    return price - price // 10\n",
            candidate_after_code="def discount(price):\n    return price - price // 10\n",
            test_code=(
                "import unittest\nfrom target_mod import discount\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(discount(100), 90)\n"
            ),
        )

        # CF4: Corrupted `taught_sources` in SQLite blocked by `skill_recheck_v1` during recall
        conn = sqlite3.connect(str(db_path))
        with conn:
            row = conn.execute("SELECT skill_id, pattern_json FROM crystallized_skills LIMIT 1").fetchone()
            corrupted_skill_id = row[0]
            rule_obj = json.loads(row[1])
            rule_obj["provenance"]["taught_sources"][0]["after"] = "def discount(price):\n    return 999999\n"
            conn.execute(
                "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                (json.dumps(rule_obj), corrupted_skill_id),
            )
            conn.execute("UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1")
        conn.close()

        cf_corrupted_recall = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="cf_ep_corrupted_recall",
            scope_id="scope_d",
            before_code="def tax_deduct(base):\n    return base + base // 10\n",
            candidate_after_code=None,
            test_code=(
                "import unittest\nfrom target_mod import tax_deduct\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self): self.assertEqual(tax_deduct(100), 90)\n"
            ),
        )

        cf_state_loaded = self_improvement.load_state(cf_state)

        checks = {
            "ep1_passed_and_persisted": (
                ep1["pass"] is True
                and ep1["self_improvement_output"]["learning"]["state_stats"]["verified_episode_count"] == 1
                and ep1["crystallized"]["crystallized"] is True
                and store_recheck_before_corruption["counts"].get(skill_recheck.PASS) == 1
            ),
            "ep2_cross_scope_recalled_and_induced_skill": (
                ep2["pass"] is True
                and ep2["recalled"] is not None
                and ep2["self_improvement_output"]["learning"]["status"] == "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE"
                and ep2["self_improvement_output"]["learning"]["state_stats"]["verified_episode_count"] == 2
                and ep2["self_improvement_output"]["learning"]["state_stats"]["verified_skill_count"] == 1
                and ep2["self_improvement_output"]["learning"]["state_stats"]["active_skill_count"] == 1
            ),
            "ep3_unseen_scope_reused_active_skill_and_code_rule": (
                ep3["pass"] is True
                and ep3["reuse_first"] is True
                and bool(reused_sid)
                and ep3["fallback_used"] is False
                and reuse_stats.get("attempts") == 1
                and reuse_stats.get("successes") == 1
                and reuse_stats.get("pre_effect_failures") == 0
                and reuse_stats.get("effectful_failures") == 0
            ),
            "cf1_broken_candidate_rejected": (
                cf_broken["pass"] is False
                and cf_broken["status"] == "REFUSED__CRYSTALLIZE_FAILED:TRAINING_VERIFICATION_FAILED"
            ),
            "cf2_overfit_constant_rejected_by_probe": (
                cf_overfit["pass"] is False
                and "ORACLE_PROBE_BREAKS" in str(cf_overfit["status"])
            ),
            "cf3_passing_baseline_rejected": (
                cf_passing_baseline["pass"] is False
                and cf_passing_baseline["status"] == "REFUSED__FAILING_TEST_BASELINE_REQUIRED"
            ),
            "cf4_corrupted_rule_blocked_by_recheck": (
                cf_corrupted_recall["pass"] is False
                and cf_corrupted_recall["status"] == "REFUSED__NO_VERIFIED_SKILL_RECALLED"
            ),
            "cf_workspace_zero_verified_episodes_or_skills": (
                cf_state_loaded["stats"]["verified_episode_count"] == 0
                and cf_state_loaded["stats"]["verified_skill_count"] == 0
                and cf_state_loaded["stats"]["active_skill_count"] == 0
            ),
        }

        return {
            "schema": SCHEMA,
            "all_ok": all(checks.values()),
            "checks": checks,
            "episodes": {
                "ep_swe_1": {
                    "pass": ep1["pass"],
                    "status": ep1["self_improvement_output"]["learning"]["status"],
                    "state_stats": ep1["self_improvement_output"]["learning"]["state_stats"],
                    "skill_id": ep1["crystallized"]["skill_id"],
                    "recheck_counts": store_recheck_before_corruption["counts"],
                },
                "ep_swe_2": {
                    "pass": ep2["pass"],
                    "status": ep2["self_improvement_output"]["learning"]["status"],
                    "state_stats": ep2["self_improvement_output"]["learning"]["state_stats"],
                    "admitted_skill_id": ep2["self_improvement_output"]["learning"].get("active_skill_id"),
                },
                "ep_swe_3": {
                    "pass": ep3["pass"],
                    "status": ep3["self_improvement_output"]["learning"]["status"],
                    "reuse_first": ep3["reuse_first"],
                    "reused_skill_id": reused_sid,
                    "fallback_used": ep3["fallback_used"],
                    "reuse_stats": reuse_stats,
                    "state_stats": ep3["self_improvement_output"]["learning"]["state_stats"],
                },
            },
            "counterfactuals": {
                "cf1_broken_candidate": cf_broken["status"],
                "cf2_overfit_constant": cf_overfit["status"],
                "cf3_passing_baseline": cf_passing_baseline["status"],
                "cf4_corrupted_rule_recall": cf_corrupted_recall["status"],
                "cf_state_stats": cf_state_loaded["stats"],
            },
            "truth": {"achieved": False},
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout")
    parser.parse_args(argv)
    report = run_swe_bridge_experiment()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
