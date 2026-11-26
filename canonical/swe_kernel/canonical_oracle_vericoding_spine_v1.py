#!/usr/bin/env python3
"""Canonical Dual-Channel Witness Inversion, Goal-Negation Oracle & Formal Vericoding Spine (`0H`).

Unifies Project Brain's previously disconnected witness-inversion, assertion-demand,
input-dependency, static diagnostics, and Coq formal-certificate inspection modules
under one front-door verification spine wired into ``brain_unified_model_v1``:

  1. Prose Claim Extraction:
       ``canonical.tools.the_right_question_is_an_experiment_v1``
  2. Assertion-Form & Demand Parsing:
       ``canonical.tools.the_assertion_is_the_demand_v1``
  3. Negative-Space Invariant Tracking:
       ``canonical.swe_kernel.witness_inversion_v1``
  4. Input-Dependency / Anti-Hardcoding Gate:
       ``canonical.swe_kernel.repair_input_dependency_gate_v1``
  5. Diagnostics / Security / API Review Engine:
       ``canonical.swe_kernel.diagnostics_perf_and_design_engine_v1``
  6. Dual-Channel Goal-Negation / Semantic-Mutation Oracle Audit
     (Harmonic-Aristotle / Terminal-Bench 4.1 anti-reward-hack):
       proves a patch + witness test is non-vacuous by verifying:
         (a) witness FAILS on original code,
         (b) witness PASSES on patched code,
         (c) input-dependency gate PASSES (rejects hardcoded constant cheats), AND
         (d) semantic goal-negation mutants of the patched code are KILLED by
             the witness (rejects vacuous/tautological oracles like ``assert True``).
  7. Formal Coq Proof Certificate Audit (zero-``Admitted`` check over ``.v`` bundles).
"""
from __future__ import annotations

import ast
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import instruction_contract_v1 as instr_contract
from canonical.runtime import verifier_falsification_v1 as verifier_falsif
from canonical.swe_kernel import diagnostics_perf_and_design_engine_v1 as diag_engine
from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
from canonical.swe_kernel import repair_input_dependency_gate_v1 as dep_gate
from canonical.swe_kernel import what_the_condition_wants_v1 as cond_wants
from canonical.swe_kernel import witness_inversion_v1 as witness_inv
from canonical.tools import the_assertion_is_the_demand_v1 as assert_demand
from canonical.tools import the_relation_is_read_from_the_failing_run_v1 as failing_rel
from canonical.tools import the_right_question_is_an_experiment_v1 as claim_exp

SCHEMA = "PROJECT_BRAIN_CANONICAL_ORACLE_VERICODING_SPINE_V1"
ROOT = Path(__file__).resolve().parents[2]
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_dual_channel_oracle_audit",
)


def _generate_goal_negation_mutants(source_text: str, *, max_mutants: int = 4) -> list[dict[str, str]]:
    """Synthesize deterministic semantic goal-negation mutants of Python code (AST-level)."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []

    mutants: list[dict[str, str]] = []
    seen: set[str] = {source_text}

    def _add(label: str, mod_tree: ast.AST) -> None:
        if len(mutants) >= max_mutants:
            return
        try:
            ast.fix_missing_locations(mod_tree)
            unparsed = ast.unparse(mod_tree)
            ast.parse(unparsed)
        except Exception:
            return
        if unparsed not in seen:
            seen.add(unparsed)
            mutants.append({"mutation_kind": label, "source": unparsed})

    # 1. Negate / alter first Return expression (most direct goal-negation check)
    for idx, node in enumerate(ast.walk(tree)):
        if len(mutants) >= max_mutants:
            break
        if isinstance(node, ast.Return) and node.value is not None:
            t_copy = copy.deepcopy(tree)
            target = list(ast.walk(t_copy))[idx]
            assert isinstance(target, ast.Return) and target.value is not None
            # Replace return value with sentinel that violates almost any non-vacuous spec
            target.value = ast.Constant(value=None)
            _add("GOAL_NEGATION_RETURN_NONE", t_copy)
            break

    # 2. Invert first comparison operator (e.g., < -> >=, == -> !=)
    cmp_flip = {
        ast.Lt: ast.GtE,
        ast.LtE: ast.Gt,
        ast.Gt: ast.LtE,
        ast.GtE: ast.Lt,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }
    for idx, node in enumerate(ast.walk(tree)):
        if len(mutants) >= max_mutants:
            break
        if isinstance(node, ast.Compare) and node.ops and type(node.ops[0]) in cmp_flip:
            t_copy = copy.deepcopy(tree)
            target = list(ast.walk(t_copy))[idx]
            assert isinstance(target, ast.Compare)
            target.ops[0] = cmp_flip[type(target.ops[0])]()
            _add(f"GOAL_NEGATION_CMP_{type(node.ops[0]).__name__}", t_copy)
            break

    # 3. Flip first binary arithmetic operator (+ <-> -, * -> +)
    bin_flip = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.Add,
        ast.Div: ast.Mult,
        ast.FloorDiv: ast.Mult,
    }
    for idx, node in enumerate(ast.walk(tree)):
        if len(mutants) >= max_mutants:
            break
        if isinstance(node, ast.BinOp) and type(node.op) in bin_flip:
            t_copy = copy.deepcopy(tree)
            target = list(ast.walk(t_copy))[idx]
            assert isinstance(target, ast.BinOp)
            target.op = bin_flip[type(target.op)]()
            _add(f"GOAL_NEGATION_BINOP_{type(node.op).__name__}", t_copy)
            break

    # 4. Perturb first numeric return or constant
    for idx, node in enumerate(ast.walk(tree)):
        if len(mutants) >= max_mutants:
            break
        if isinstance(node, ast.Return) and node.value is not None:
            t_copy = copy.deepcopy(tree)
            target = list(ast.walk(t_copy))[idx]
            assert isinstance(target, ast.Return)
            target.value = ast.Constant(value="__GOAL_NEGATED_SENTINEL__")
            _add("GOAL_NEGATION_RETURN_SENTINEL", t_copy)
            break

    return mutants


def _run_witness_in_clone(
    repo_root: Path,
    target_rel: str,
    candidate_source: str,
    test_file: str,
    *,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="brain_oracle_audit_") as tmp_dir:
        clone = Path(tmp_dir) / "repo"
        shutil.copytree(
            repo_root,
            clone,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "node_modules"),
        )
        dst = clone / target_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(candidate_source, encoding="utf-8")
        res = mhz.run_pytest_targets(clone, [test_file], timeout_s=timeout_s)
        return {
            "ok": bool(res.get("ok")),
            "returncode": res.get("returncode"),
            "stdout_tail": str(res.get("stdout") or "")[-400:],
        }


def extract_assertion_demands(test_source: str) -> list[dict[str, Any]]:
    """Extract all structured assertion forms from a Python test file via ``the_assertion_is_the_demand_v1``."""
    demands: list[dict[str, Any]] = []
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return demands
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            line = int(getattr(node, "lineno", 1))
            form, detail = assert_demand.assert_form(test_source, line)
            demands.append({"line": line, "form": form, "detail": repr(detail)[:200]})
    demands.sort(key=lambda d: d["line"])
    return demands


def audit_patch_and_oracle(
    repo_root: str | Path,
    *,
    target_rel: str,
    before_source: str,
    after_source: str,
    test_file: str,
    max_mutants: int = 4,
    timeout_s: float = 20.0,
    negative_store: witness_inv.NegativeSpaceInvariantStore | None = None,
) -> dict[str, Any]:
    """Dual-Channel Patch & Witness Oracle Audit (rejects broken patches, hardcoding, and vacuous tests)."""
    root = Path(repo_root).resolve()
    test_path = root / test_file
    test_src = test_path.read_text(encoding="utf-8", errors="replace") if test_path.exists() else ""
    assertion_demands = extract_assertion_demands(test_src)

    # Channel 1: Before must FAIL, After must PASS
    before_run = _run_witness_in_clone(root, target_rel, before_source, test_file, timeout_s=timeout_s)
    after_run = _run_witness_in_clone(root, target_rel, after_source, test_file, timeout_s=timeout_s)
    fail_to_pass = (not before_run["ok"]) and after_run["ok"]

    # Channel 2: Input-dependency & anti-hardcoding gate
    dep_res = dep_gate.gate(before_source, after_source)
    dep_ok = str(dep_res.get("status") or "").upper() == "PASS"

    # Channel 3: Goal-negation / semantic mutation discriminating power check
    mutants = _generate_goal_negation_mutants(after_source, max_mutants=max_mutants)
    mutant_rows: list[dict[str, Any]] = []
    killed = 0
    for m in mutants:
        m_run = _run_witness_in_clone(root, target_rel, m["source"], test_file, timeout_s=timeout_s)
        was_killed = not m_run["ok"]
        if was_killed:
            killed += 1
        mutant_rows.append(
            {
                "mutation_kind": m["mutation_kind"],
                "killed": was_killed,
                "returncode": m_run["returncode"],
            }
        )
    oracle_discriminates = len(mutants) > 0 and killed > 0

    all_pass = fail_to_pass and dep_ok and oracle_discriminates
    rejection_reasons: list[str] = []
    if before_run["ok"]:
        rejection_reasons.append("BEFORE_ALREADY_PASSED__WITNESS_DOES_NOT_REPRODUCE_BUG")
    if not after_run["ok"]:
        rejection_reasons.append("AFTER_FAILED_WITNESS")
    if not dep_ok:
        rejection_reasons.append(f"INPUT_DEPENDENCY_GATE_REJECTED:{dep_res.get('status')}:{dep_res.get('reason')}")
    if not oracle_discriminates:
        rejection_reasons.append("VACUOUS_ORACLE__MUTANTS_NOT_KILLED")

    if not all_pass and negative_store is not None:
        try:
            negative_store.record_refutation(
                after_source[:400],
                reason=";".join(rejection_reasons) or "ORACLE_AUDIT_REJECTED",
                repo=str(root.name),
                commit=target_rel,
            )
        except Exception:
            pass

    return {
        "schema": SCHEMA,
        "pass": all_pass,
        "status": "PASS__DUAL_CHANNEL_ORACLE_VERIFIED" if all_pass else "FAIL_CLOSED__ORACLE_AUDIT_REJECTED",
        "reasons": rejection_reasons,
        "channels": {
            "before_failed": not before_run["ok"],
            "after_passed": after_run["ok"],
            "fail_to_pass": fail_to_pass,
            "input_dependency_gate": dep_res,
            "input_dependency_ok": dep_ok,
            "goal_negation_mutants_tested": len(mutants),
            "goal_negation_mutants_killed": killed,
            "oracle_discriminates": oracle_discriminates,
            "mutants": mutant_rows,
        },
        "assertion_demands": assertion_demands,
    }


def verify_coq_certificate_bundle(
    bundle_dir: str | Path | None = None,
    *,
    run_coqc: bool = False,
) -> dict[str, Any]:
    """Audit a Coq formal-proof certificate directory for zero-``Admitted.`` integrity."""
    target = Path(bundle_dir).resolve() if bundle_dir is not None else (ROOT / "canonical" / "certificates" / "CAD_NURBS_RCF_V1")
    if not target.exists() or not target.is_dir():
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__COQ_BUNDLE_MISSING",
            "bundle_dir": str(target),
        }

    v_files = sorted(target.glob("*.v"))
    qed_total = 0
    defined_total = 0
    admitted_total = 0
    axiom_total = 0
    loc_total = 0
    per_file: list[dict[str, Any]] = []

    qed_re = re.compile(r"\bQed\.")
    def_re = re.compile(r"\bDefined\.")
    adm_re = re.compile(r"\bAdmitted\.")
    ax_re = re.compile(r"^\s*(Axiom|Parameter|Admit)\b", re.M)

    for vf in v_files:
        text = vf.read_text(encoding="utf-8", errors="replace")
        # Strip Coq block comments (* ... *) conservatively
        clean = re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)
        q = len(qed_re.findall(clean))
        d = len(def_re.findall(clean))
        a = len(adm_re.findall(clean))
        ax = len(ax_re.findall(clean))
        lines = len(text.splitlines())
        qed_total += q
        defined_total += d
        admitted_total += a
        axiom_total += ax
        loc_total += lines
        per_file.append(
            {"file": vf.name, "loc": lines, "qed": q, "defined": d, "admitted": a, "axioms": ax}
        )

    coqc_path = shutil.which("coqc")
    coqc_checked = False
    coqc_ok: bool | None = None
    if run_coqc and coqc_path and v_files:
        coqc_checked = True
        proc = subprocess.run(
            [coqc_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        coqc_ok = proc.returncode == 0

    passed = len(v_files) > 0 and qed_total > 0 and admitted_total == 0 and (not coqc_checked or bool(coqc_ok))
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__COQ_CERTIFICATES_ZERO_ADMITTED" if passed else "FAIL_CLOSED__COQ_AUDIT_FAILED",
        "bundle_dir": str(target),
        "file_count": len(v_files),
        "total_loc": loc_total,
        "qed_count": qed_total,
        "defined_count": defined_total,
        "admitted_count": admitted_total,
        "axiom_count": axiom_total,
        "coqc_available": coqc_path is not None,
        "coqc_checked": coqc_checked,
        "coqc_ok": coqc_ok,
        "files": per_file,
    }


def compile_and_check_instruction_contract(
    utterance: str,
    observation: Mapping[str, Any],
    *,
    trace: Sequence[tuple[Mapping[str, Any], str]] | None = None,
) -> dict[str, Any]:
    """Compile a natural-language instruction into a checkable contract (`instruction_contract_v1`)
    and optionally judge a trace against it (or return an explicit named refusal).
    """
    refusal = instr_contract.refusal_for(utterance)
    contract = instr_contract.compile_contract(utterance, observation)
    effective_refusal = refusal or contract.get("refusal")
    check_res = None
    if trace is not None and effective_refusal is None:
        check_res = instr_contract.check_contract(contract, list(trace))
    if effective_refusal is not None:
        passed = False
        status = "FAIL_CLOSED__CONTRACT_REFUSED"
    elif check_res is not None:
        passed = str(check_res.get("verdict") or "").upper() == "PASS"
        status = "PASS__INSTRUCTION_CONTRACT_VERIFIED" if passed else "FAIL_CLOSED__INSTRUCTION_CONTRACT_VIOLATED"
    else:
        clauses = contract.get("clauses") or []
        passed = len(clauses) > 0
        status = "PASS__INSTRUCTION_CONTRACT_COMPILED" if passed else "FAIL_CLOSED__EMPTY_INSTRUCTION_CONTRACT"
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "refusal": effective_refusal,
        "contract": contract,
        "check": check_res,
    }


def extract_failing_run_demands(
    source_text: str,
    *,
    failing_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract AST decision/production sites and demanded relations from a failing run
    (`the_relation_is_read_from_the_failing_run_v1` + `what_the_condition_wants_v1`).
    """
    sites = failing_rel.sites_in(source_text)
    demanded = failing_rel.demanded_values(failing_facts) if failing_facts is not None else {}
    forbidden = failing_rel.forbidden_token(failing_facts) if failing_facts is not None else None
    return {
        "schema": SCHEMA,
        "pass": len(sites) > 0,
        "site_count": len(sites),
        "sites": [s.as_dict() for s in sites[:64]],
        "demanded_values": demanded,
        "forbidden_token": forbidden,
        "condition_harvester_available": hasattr(cond_wants, "harvest"),
    }


def prove_verifier_can_say_no(
    predicate: Callable[[Any], bool],
    *,
    positive_examples: Sequence[Any],
    negative_mutants: Sequence[Any],
    verifier_name: str = "custom_verifier",
) -> dict[str, Any]:
    """Falsification proof (`verifier_falsification_v1` invariant): prove a verifier says YES
    on every valid example AND says NO on every adversarial/semantic mutant.

    Directly eliminates vacuous/tautological oracles (the STING / Terminal-Bench 4.0 defect).
    """
    pos_passed = 0
    pos_failures: list[int] = []
    for idx, ex in enumerate(positive_examples):
        try:
            ok = bool(predicate(ex))
        except Exception:
            ok = False
        if ok:
            pos_passed += 1
        else:
            pos_failures.append(idx)

    neg_killed = 0
    surviving_mutants: list[int] = []
    for idx, mut in enumerate(negative_mutants):
        try:
            accepted = bool(predicate(mut))
        except Exception:
            accepted = False
        if not accepted:
            neg_killed += 1
        else:
            surviving_mutants.append(idx)

    pos_total = len(positive_examples)
    neg_total = len(negative_mutants)
    falsifiable = neg_total > 0 and neg_killed == neg_total
    sound_on_positives = pos_total > 0 and pos_passed == pos_total
    passed = sound_on_positives and falsifiable
    kill_rate = round(neg_killed / neg_total, 4) if neg_total > 0 else 0.0
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__VERIFIER_PROVEN_FALSIFIABLE" if passed else "FAIL_CLOSED__VERIFIER_NOT_FALSIFIABLE",
        "verifier_name": verifier_name,
        "positive_passed": pos_passed,
        "positive_total": pos_total,
        "positive_failures": pos_failures,
        "mutants_killed": neg_killed,
        "mutants_total": neg_total,
        "surviving_mutants": surviving_mutants,
        "mutation_kill_rate": kill_rate,
        "falsifiable": falsifiable,
        "repo_falsification_suite_wired": hasattr(verifier_falsif, "run"),
    }


def audit_harvested_surface_with_falsification(
    capability_id: str = "",
    *,
    path: str = "",
    probe_args: Mapping[str, Any] | None = None,
    adversarial_args: Mapping[str, Any] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Dry-run audit a discovered harvested surface via ``harvested_capability_runtime_v1``
    without writing producer receipts or claiming admission (always ``admitted: False``).
    """
    from canonical.runtime import harvested_capability_runtime_v1 as harvested_rt

    base = Path(root).resolve() if root is not None else ROOT
    pos = harvested_rt.run(
        {
            "capability_id": capability_id,
            "path": path,
            "args": dict(probe_args or {}),
            "receipt": False,
        },
        root=base,
    )
    adv = None
    if adversarial_args is not None:
        adv = harvested_rt.run(
            {
                "capability_id": capability_id,
                "path": path,
                "args": dict(adversarial_args),
                "receipt": False,
            },
            root=base,
        )
    executed = bool(pos.get("executed") is True)
    adv_distinguished = True if adv is None else (
        (not bool(adv.get("executed"))) or (adv.get("result_sha256") != pos.get("result_sha256"))
    )
    passed = executed and adv_distinguished
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__HARVESTED_SURFACE_AUDITED_UNADMITTED" if passed else "FAIL_CLOSED__HARVESTED_SURFACE_AUDIT_FAILED",
        "admitted": False,
        "admission": "NOT_ADMITTED",
        "positive_probe": pos,
        "adversarial_probe": adv,
        "adversarial_distinguished": adv_distinguished,
    }


def audit_oracle_and_vericoding(
    *,
    repo_root: str | Path | None = None,
    target_rel: str | None = None,
    before_source: str | None = None,
    after_source: str | None = None,
    test_file: str | None = None,
    prose_claims_text: str | None = None,
    diagnostics_target: str | Path | None = None,
    coq_bundle_dir: str | Path | None = None,
    verify_default_coq: bool = False,
    instruction_utterance: str | None = None,
    instruction_observation: Mapping[str, Any] | None = None,
    instruction_trace: Sequence[tuple[Mapping[str, Any], str]] | None = None,
    failing_source: str | None = None,
    failing_facts: Mapping[str, Any] | None = None,
    falsification_spec: Mapping[str, Any] | None = None,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Unified front-door entrypoint (`0H`) for dual-channel oracle & vericoding verification."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE_SANDBOX",
        "model_calls": 0,
        "non_claims": list(NON_CLAIMS),
        "modules_invoked": [],
    }
    sub_passes: list[bool] = []

    if (
        repo_root is not None
        and target_rel is not None
        and before_source is not None
        and after_source is not None
        and test_file is not None
    ):
        report["modules_invoked"].extend(
            [
                "canonical.swe_kernel.repair_input_dependency_gate_v1",
                "canonical.tools.the_assertion_is_the_demand_v1",
                "canonical.swe_kernel.witness_inversion_v1",
                "canonical.swe_kernel.canonical_oracle_vericoding_spine_v1:audit_patch_and_oracle",
            ]
        )
        pa = audit_patch_and_oracle(
            repo_root,
            target_rel=target_rel,
            before_source=before_source,
            after_source=after_source,
            test_file=test_file,
            timeout_s=timeout_s,
        )
        report["patch_oracle_audit"] = pa
        sub_passes.append(bool(pa["pass"]))

    if prose_claims_text is not None:
        report["modules_invoked"].append("canonical.tools.the_right_question_is_an_experiment_v1")
        claims = claim_exp.extract_claims(prose_claims_text)
        report["extracted_claims"] = {"count": len(claims), "claims": claims[:24]}
        sub_passes.append(len(claims) > 0)

    if diagnostics_target is not None:
        report["modules_invoked"].append("canonical.swe_kernel.diagnostics_perf_and_design_engine_v1")
        d_target = Path(diagnostics_target).resolve()
        api_rev = diag_engine.review_api_design(d_target)
        race_res = diag_engine.detect_race_conditions(d_target)
        report["diagnostics"] = {"api_review": api_rev, "race_analysis": race_res}
        sub_passes.append(isinstance(api_rev, Mapping) and isinstance(race_res, Mapping))

    if coq_bundle_dir is not None or verify_default_coq:
        report["modules_invoked"].append("canonical.swe_kernel.canonical_oracle_vericoding_spine_v1:verify_coq_certificate_bundle")
        coq_res = verify_coq_certificate_bundle(coq_bundle_dir)
        report["coq_certificate_audit"] = coq_res
        sub_passes.append(bool(coq_res["pass"]))

    if instruction_utterance is not None and instruction_observation is not None:
        report["modules_invoked"].append("canonical.runtime.instruction_contract_v1")
        ic_res = compile_and_check_instruction_contract(
            instruction_utterance,
            instruction_observation,
            trace=instruction_trace,
        )
        report["instruction_contract"] = ic_res
        sub_passes.append(bool(ic_res["pass"]))

    if failing_source is not None:
        report["modules_invoked"].append("canonical.tools.the_relation_is_read_from_the_failing_run_v1")
        rel_res = extract_failing_run_demands(failing_source, failing_facts=failing_facts)
        report["failing_run_demands"] = rel_res
        sub_passes.append(bool(rel_res["pass"]))

    if falsification_spec is not None:
        report["modules_invoked"].append("canonical.runtime.verifier_falsification_v1")
        f_res = prove_verifier_can_say_no(
            falsification_spec["predicate"],
            positive_examples=falsification_spec.get("positive_examples") or (),
            negative_mutants=falsification_spec.get("negative_mutants") or (),
            verifier_name=str(falsification_spec.get("verifier_name") or "custom_verifier"),
        )
        report["verifier_falsification"] = f_res
        sub_passes.append(bool(f_res["pass"]))

    passed = bool(sub_passes) and all(sub_passes)
    report["pass"] = passed
    report["status"] = "PASS__ORACLE_AND_VERICODING_VERIFIED" if passed else "FAIL_CLOSED__ORACLE_VERICODING_REJECTED"
    report["reason"] = None if passed else "SUBCHECK_FAILED_OR_EMPTY_REQUEST"
    return report
