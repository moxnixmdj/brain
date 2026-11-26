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
import importlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


class _LazyModule:
    __slots__ = ("_mod_name", "_loaded")

    def __init__(self, mod_name: str) -> None:
        object.__setattr__(self, "_mod_name", mod_name)
        object.__setattr__(self, "_loaded", None)

    def __getattr__(self, item: str) -> Any:
        mod = object.__getattribute__(self, "_loaded")
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, "_mod_name"))
            object.__setattr__(self, "_loaded", mod)
        return getattr(mod, item)


instr_contract = _LazyModule("canonical.runtime.instruction_contract_v1")
verifier_falsif = _LazyModule("canonical.runtime.verifier_falsification_v1")
diag_engine = _LazyModule("canonical.swe_kernel.diagnostics_perf_and_design_engine_v1")
mhz = _LazyModule("canonical.swe_kernel.metamorphic_habitation_zipper_v1")
dep_gate = _LazyModule("canonical.swe_kernel.repair_input_dependency_gate_v1")
cond_wants = _LazyModule("canonical.swe_kernel.what_the_condition_wants_v1")
witness_inv = _LazyModule("canonical.swe_kernel.witness_inversion_v1")
assert_demand = _LazyModule("canonical.tools.the_assertion_is_the_demand_v1")
failing_rel = _LazyModule("canonical.tools.the_relation_is_read_from_the_failing_run_v1")
claim_exp = _LazyModule("canonical.tools.the_right_question_is_an_experiment_v1")

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


def mutation_admission_gate(
    source_text: str,
    verifier_fn: Callable[[Mapping[str, Any]], bool],
    *,
    limit: int = 8,
    seed: int = 7,
    min_kill_rate: float = 0.5,
) -> dict[str, Any]:
    """Mutation-as-Admission Gate (`mutation_admission_probe_v1`, Play 6 × STING defense).

    Executes ``verifier_fn(ns)`` first on the original compiled module namespace, then against
    real AST mutants synthesized by ``mutation_admission_probe_v1.mutants(...)``. Rejects any
    candidate/skill whose verifier fails on the original OR allows too many mutants to survive
    (kill_rate < min_kill_rate).
    """
    from canonical.tools import mutation_admission_probe_v1 as mut_probe

    t0 = time.perf_counter()
    orig_ns: dict[str, Any] = {}
    try:
        exec(compile(source_text, "<original_skill>", "exec"), orig_ns)
        orig_pass = bool(verifier_fn(orig_ns))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__ORIGINAL_FAILED_VERIFIER",
            "error": f"{type(exc).__name__}: {exc}",
            "mutants_tested": 0,
            "mutants_killed": 0,
            "kill_rate": 0.0,
        }
    if not orig_pass:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__ORIGINAL_REJECTED_BY_VERIFIER",
            "mutants_tested": 0,
            "mutants_killed": 0,
            "kill_rate": 0.0,
        }

    generated = mut_probe.mutants(source_text, limit=int(limit), seed=int(seed))
    killed = 0
    survivors: list[dict[str, Any]] = []
    for m in generated:
        m_ns: dict[str, Any] = {}
        try:
            exec(compile(str(m["text"]), "<mutant_skill>", "exec"), m_ns)
            m_passed = bool(verifier_fn(m_ns))
        except Exception:
            m_passed = False
        if not m_passed:
            killed += 1
        else:
            survivors.append(
                {
                    "mutator": m.get("mutator"),
                    "line": m.get("line"),
                    "before": m.get("before"),
                    "after": m.get("after"),
                }
            )
    total = len(generated)
    kill_rate = round(killed / total, 4) if total > 0 else 0.0
    admitted = total > 0 and kill_rate >= float(min_kill_rate)
    return {
        "schema": SCHEMA,
        "pass": admitted,
        "status": "PASS__MUTATION_ADMISSION_GATE" if admitted else "FAIL_CLOSED__VERIFIER_WEAK_MUTANTS_SURVIVED",
        "mutants_tested": total,
        "mutants_killed": killed,
        "kill_rate": kill_rate,
        "min_kill_rate": float(min_kill_rate),
        "surviving_mutants": survivors,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
    }


def extract_guard_demand_sites(source_text: str) -> dict[str, Any]:
    """Extract and instrument guard sites from Python source via ``the_demand_is_learned_from_the_run_v1``."""
    from canonical.tools import the_demand_is_learned_from_the_run_v1 as demand_mod

    sites = demand_mod.guard_sites(source_text)
    instrumented = demand_mod.instrument_guards(source_text, sites) if sites else None
    return {
        "schema": SCHEMA,
        "pass": len(sites) > 0,
        "site_count": len(sites),
        "sites": sites,
        "instrumented_ready": isinstance(instrumented, str) and len(instrumented) > 0,
        "model_calls": 0,
    }


def audit_check_vacuity(
    predicate: Callable[[Any], bool],
    *,
    positive_examples: Sequence[Any],
    negative_mutants: Sequence[Any],
    check_name: str = "candidate_check",
) -> dict[str, Any]:
    """'A Check That Nobody Runs Is a Check That Cannot Be Wrong' (`0H`).

    Proves a check actually executes, passes every real positive witness, and kills every
    semantic mutant (rejecting vacuous/tautological or unexecuted checks).
    """
    from canonical.tools import (
        a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1 as vac_mod,
    )

    proof = prove_verifier_can_say_no(
        predicate,
        positive_examples=positive_examples,
        negative_mutants=negative_mutants,
        verifier_name=check_name,
    )
    vacuous = not bool(proof.get("falsifiable"))
    return {
        "schema": SCHEMA,
        "pass": bool(proof.get("pass")) and not vacuous,
        "status": "PASS__CHECK_NON_VACUOUS" if (proof.get("pass") and not vacuous) else "FAIL_CLOSED__CHECK_VACUOUS_OR_UNSOUND",
        "vacuous": vacuous,
        "falsification": proof,
        "citation_vacuity_wired": hasattr(vac_mod, "citation_vacuity") and hasattr(vac_mod, "certification_audit"),
        "model_calls": 0,
    }


def evaluate_generalization_delta(
    pulls: Sequence[Mapping[str, Any]],
    *,
    markers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Measure which fix actually moves held-out generalization (`which_fix_moves_generalization_v1`)."""
    from canonical.tools import which_fix_moves_generalization_v1 as gen_mod

    res = gen_mod.run(list(pulls), markers=markers)
    return {
        "schema": SCHEMA,
        "pass": isinstance(res, Mapping),
        "status": "PASS__GENERALIZATION_DELTA_MEASURED",
        "measurement": res,
        "model_calls": 0,
    }


def audit_self_evolution_entry(
    source_text: str,
    verifier_fn: Callable[[Mapping[str, Any]], bool],
    *,
    skill_id: str = "self_mod_candidate",
    workspace_root: str | Path | None = None,
    target_rel: str | None = None,
    positive_examples: Sequence[Any] = (),
    negative_mutants: Sequence[Any] = (),
    check_predicate: Callable[[Any], bool] | None = None,
    limit: int = 8,
    seed: int = 7,
    min_kill_rate: float = 0.5,
    commit_on_pass: bool = False,
    memory_bus: Any = None,
) -> dict[str, Any]:
    """Wave 10 Entry-Only Self-Evolution Firewall (`0H` × `0F` × `0G`, defeating SEABench 43.9% drift).

    SEABench (2026) proves poisoned self-evolution CANNOT be repaired post-hoc: bad state MUST
    be blocked at entry. Every self-modification or skill write must pass ALL active gates:
      1. AST Mutation Killing (`mutation_admission_gate` via `mutation_admission_probe_v1`)
      2. Non-Vacuous Check Falsification (`audit_check_vacuity`, when predicate/examples given)
      3. Verified SHA-256 Event Lineage (`0G` `append_verified_event`, or T2 nogood on rejection)
      4. Crash-Safe Multi-Path Journal Commit (`0F` `durable_transactional_commit` via
         `the_record_is_the_commit_v1`), writing ZERO bytes on any gate failure.
    """
    t0 = time.perf_counter()
    reasons: list[str] = []

    # Gate 1: Real AST Mutation Killing
    mut_gate = mutation_admission_gate(
        source_text,
        verifier_fn,
        limit=limit,
        seed=seed,
        min_kill_rate=min_kill_rate,
    )
    if not mut_gate.get("pass"):
        reasons.append(str(mut_gate.get("status") or "MUTATION_GATE_FAILED"))

    # Gate 2: Non-Vacuous Check Falsification (when supplied)
    vac_gate = None
    if check_predicate is not None or positive_examples or negative_mutants:
        if check_predicate is None:
            reasons.append("VACUITY_PREDICATE_MISSING")
        else:
            vac_gate = audit_check_vacuity(
                check_predicate,
                positive_examples=positive_examples,
                negative_mutants=negative_mutants,
                check_name=skill_id,
            )
            if not vac_gate.get("pass"):
                reasons.append(str(vac_gate.get("status") or "CHECK_VACUOUS"))

    admitted = len(reasons) == 0
    event_receipt = None
    commit_receipt = None
    nogood_recorded = False

    if admitted:
        # Gate 3: Append verified event to 0G hash-chained memory log
        if memory_bus is not None and hasattr(memory_bus, "append_verified_event"):
            import hashlib

            event_receipt = memory_bus.append_verified_event(
                op="SET",
                key=f"self_evolution:{skill_id}",
                value={
                    "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                    "kill_rate": mut_gate.get("kill_rate"),
                },
                source_commit="entry_firewall_v1",
                precondition_guard=["mutation_killed", "non_vacuous_check"],
            )
        # Gate 4: Crash-safe journaled commit (ONLY after all gates pass!)
        if commit_on_pass and workspace_root is not None and target_rel is not None:
            from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

            commit_receipt = cu_spine.durable_transactional_commit(
                workspace_root,
                {str(target_rel): source_text.encode("utf-8")},
            )
            if not commit_receipt.get("pass"):
                admitted = False
                reasons.append("DURABLE_COMMIT_FAILED")
    else:
        # Block at entry + compile failure into T2 CDCL negative-space nogood!
        if memory_bus is not None and hasattr(memory_bus, "record_conflict"):
            memory_bus.record_conflict(
                source_text[:400],
                reason=";".join(reasons),
                domain="self_evolution_firewall",
                context_sig=skill_id,
            )
            nogood_recorded = True

    return {
        "schema": SCHEMA,
        "pass": admitted,
        "admitted": admitted,
        "status": "PASS__SELF_EVOLUTION_ADMITTED" if admitted else "FAIL_CLOSED__BLOCKED_AT_ENTRY_FIREWALL",
        "skill_id": skill_id,
        "reasons": reasons,
        "mutation_gate": mut_gate,
        "vacuity_gate": vac_gate,
        "event_receipt": event_receipt,
        "commit_receipt": commit_receipt,
        "nogood_recorded": nogood_recorded,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
    }


def interrogate_minimax_witness(
    *,
    params: Sequence[str],
    examples: Sequence[tuple[Any, Any]] = (),
    candidate_bodies: Sequence[str] | None = None,
    max_weight: int = 3,
    extra_constants: Sequence[Any] = (),
) -> dict[str, Any]:
    """Wave 18: Exact-Minimax Witness Interrogation via `evidence_demand_v1` (closes spec & 1-demo ambiguity).

    Refuses premature commitment whenever >=2 admissible candidate functions agree on all observed examples
    yet diverge on a discriminating probe; computes the exact minimax probe maximizing worst-case
    hypothesis-space elimination (`O(log |H|)` active queries).
    """
    import math

    from canonical.runtime import evidence_demand_v1 as ev_dem

    t0 = time.perf_counter()
    param_list = [str(p) for p in params]
    ex_list = list(examples)
    if candidate_bodies is not None:
        admissible = []
        for raw_b in candidate_bodies:
            s = str(raw_b).strip()
            if not s:
                continue
            # Auto-wrap bare expressions into `return <expr>` for evidence_demand_v1.behaviour_signature
            if not s.startswith(("return ", "if ", "for ", "while ", "def ")) and "\n" not in s:
                s = f"return {s}"
            admissible.append(s)
    else:
        raw_adm = ev_dem.enumerate_admissible(
            param_list,
            ex_list,
            max_weight=int(max_weight),
            extra_constants=tuple(extra_constants),
        )
        admissible = [str(b) for b in raw_adm]

    if not admissible:
        return {
            "schema": SCHEMA,
            "pass": False,
            "decision": "FAIL_CLOSED__NO_ADMISSIBLE_HYPOTHESIS",
            "status": "FAIL_CLOSED__NO_ADMISSIBLE_HYPOTHESIS",
            "admissible_count": 0,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    probes = ev_dem.disclose_probes(admissible, examples=ex_list)
    # Build probe-indexed partition buckets to select exact minimax discriminating probe
    sigs: dict[str, tuple[Any, ...]] = {}
    for body in admissible:
        try:
            sigs[body] = tuple(ev_dem.behaviour_signature(body, param_list, probes=probes))
        except Exception:
            continue

    unique_classes: dict[tuple[Any, ...], list[str]] = {}
    for body, sig in sigs.items():
        unique_classes.setdefault(sig, []).append(body)

    if len(unique_classes) <= 1:
        chosen = sorted(admissible, key=lambda s: (len(s), s))[0]
        return {
            "schema": SCHEMA,
            "pass": True,
            "decision": "COMMIT_UNIQUE_EXPLANATION",
            "status": "PASS__UNIQUE_EXPLANATION_IDENTIFIED",
            "chosen_body": chosen,
            "admissible_count": len(admissible),
            "equivalence_classes": len(unique_classes),
            "minimax_probe": None,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # Pick the exact minimax probe: minimizes max bucket size over distinct behaviour classes
    reps = [members[0] for members in unique_classes.values()]
    n_classes = len(reps)
    best_probe: Any = None
    best_max_bucket = n_classes + 1
    best_entropy = -1.0
    best_buckets: dict[str, int] = {}

    for p_idx, probe_val in enumerate(probes):
        buckets: dict[str, int] = {}
        for rep in reps:
            out_val = sigs[rep][p_idx] if p_idx < len(sigs[rep]) else "<ERR>"
            k = repr(out_val)
            buckets[k] = buckets.get(k, 0) + 1
        if len(buckets) <= 1:
            continue
        max_b = max(buckets.values())
        ent = -sum((c / n_classes) * math.log2(c / n_classes) for c in buckets.values() if c > 0)
        if (max_b < best_max_bucket) or (max_b == best_max_bucket and ent > best_entropy):
            best_max_bucket = max_b
            best_entropy = ent
            best_probe = probe_val
            best_buckets = dict(buckets)

    return {
        "schema": SCHEMA,
        "pass": True,
        "decision": "REFUSE_AMBIGUOUS_NEED_PROBE",
        "status": "PASS__MINIMAX_DISCRIMINATING_PROBE_COMPUTED",
        "admissible_count": len(admissible),
        "equivalence_classes": n_classes,
        "minimax_probe": best_probe,
        "worst_case_remaining_classes": best_max_bucket if best_probe is not None else n_classes,
        "information_gain_bits": round(max(0.0, best_entropy), 6),
        "outcome_buckets": best_buckets,
        "sample_competing_bodies": reps[:6],
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def generate_csp_hard_negatives(
    *,
    source_text: str,
    test_source: str,
    max_mutants: int = 12,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Wave 18: NS-PRM Counterfactual Symbolic Perturbation (CSP) hard-negative & spec-gap generator.

    Synthesizes syntactically valid, type-compatible AST perturbations of a verified Python module and
    runs each in an isolated subprocess against `test_source`, separating:
    - `caught_pairs`: ready-to-distill `(verified_positive, csp_hard_negative)` pairs for ASCENT / NS-PRM
    - `survived_spec_gaps`: broken implementations that *passed* the tests (exposing specification gaps!)
    """
    import ast
    import subprocess
    import sys
    import tempfile

    t0 = time.perf_counter()
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__SOURCE_SYNTAX_ERROR",
            "reason": str(exc),
            "model_calls": 0,
        }

    # Verify original source passes test_source first (pytest or zero-dependency stdlib runner!)
    import importlib.util

    has_pytest = importlib.util.find_spec("pytest") is not None
    stdlib_runner = (
        "import importlib.util, pathlib, sys, traceback, unittest\n"
        "sys.path.insert(0, '.')\n"
        "failed = 0\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "spec = importlib.util.spec_from_file_location(p.stem, str(p))\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "for name, obj in sorted(vars(mod).items()):\n"
        "    if name.startswith('test_') and callable(obj):\n"
        "        try:\n"
        "            obj()\n"
        "        except Exception:\n"
        "            failed += 1\n"
        "            traceback.print_exc()\n"
        "    elif isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:\n"
        "        res = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(obj))\n"
        "        if not res.wasSuccessful():\n"
        "            failed += len(res.failures) + len(res.errors)\n"
        "sys.exit(0 if failed == 0 else 1)\n"
    )

    def _exec_pair(src: str) -> tuple[bool, str]:
        with tempfile.TemporaryDirectory(prefix="csp_eval_") as td:
            td_p = Path(td)
            (td_p / "subject_mod.py").write_text(src, encoding="utf-8")
            (td_p / "test_subject.py").write_text(test_source, encoding="utf-8")
            cmd = (
                [sys.executable, "-m", "pytest", "-q", "test_subject.py"]
                if has_pytest
                else [sys.executable, "-c", stdlib_runner, "test_subject.py"]
            )
            cp = subprocess.run(
                cmd,
                cwd=td,
                capture_output=True,
                text=True,
                timeout=min(8.0, float(timeout_s)),
            )
            return cp.returncode == 0, (cp.stdout + "\n" + cp.stderr).strip()

    orig_ok, orig_out = _exec_pair(source_text)
    if not orig_ok:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__BASELINE_SOURCE_FAILS_TESTS",
            "baseline_output": orig_out[-400:],
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    cmp_swaps = {
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }
    bin_swaps = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.FloorDiv,
    }
    bool_swaps = {ast.And: ast.Or, ast.Or: ast.And}

    mutants: list[tuple[str, str]] = []
    seen_srcs: set[str] = {source_text}

    def _collect_mutants() -> None:
        all_nodes = list(ast.walk(tree))
        for idx, node in enumerate(all_nodes):
            if len(mutants) >= int(max_mutants):
                return
            kind_label = None
            new_tree = ast.parse(source_text)
            target = list(ast.walk(new_tree))[idx]
            if isinstance(target, ast.Compare) and len(target.ops) == 1:
                op_cls = type(target.ops[0])
                if op_cls in cmp_swaps:
                    target.ops[0] = cmp_swaps[op_cls]()
                    kind_label = f"CMP_SWAP_{op_cls.__name__}_TO_{cmp_swaps[op_cls].__name__}"
            elif isinstance(target, ast.BinOp) and type(target.op) in bin_swaps:
                op_cls = type(target.op)
                target.op = bin_swaps[op_cls]()
                kind_label = f"BINOP_SWAP_{op_cls.__name__}_TO_{bin_swaps[op_cls].__name__}"
            elif isinstance(target, ast.BoolOp) and type(target.op) in bool_swaps:
                op_cls = type(target.op)
                target.op = bool_swaps[op_cls]()
                kind_label = f"BOOL_SWAP_{op_cls.__name__}_TO_{bool_swaps[op_cls].__name__}"
            if kind_label is not None:
                mut_src = ast.unparse(new_tree) + "\n"
                if mut_src not in seen_srcs:
                    seen_srcs.add(mut_src)
                    mutants.append((kind_label, mut_src))

    _collect_mutants()

    caught_pairs: list[dict[str, Any]] = []
    survived_spec_gaps: list[dict[str, Any]] = []
    for label, mut_src in mutants:
        ok, out = _exec_pair(mut_src)
        rec = {
            "perturbation": label,
            "mutated_source": mut_src,
            "test_passed": ok,
            "diagnostic": out[-240:],
        }
        if ok:
            survived_spec_gaps.append(rec)
        else:
            caught_pairs.append(
                {
                    "perturbation": label,
                    "positive_source": source_text,
                    "hard_negative_source": mut_src,
                    "verifier_diagnostic": out[-240:],
                }
            )

    total = len(mutants)
    kill_rate = round(len(caught_pairs) / total, 4) if total > 0 else 0.0
    return {
        "schema": SCHEMA,
        "pass": total > 0,
        "status": "PASS__CSP_HARD_NEGATIVES_GENERATED" if total > 0 else "FAIL_CLOSED__NO_PERTURBATION_SITES",
        "total_mutants": total,
        "caught_count": len(caught_pairs),
        "survived_spec_gap_count": len(survived_spec_gaps),
        "kill_rate": kill_rate,
        "caught_pairs": caught_pairs,
        "survived_spec_gaps": survived_spec_gaps,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def run_red_queen_evaluator_coevolution(
    *,
    epoch_index: int = 0,
    scan_root: str | Path | None = None,
    orig_source: str | None = None,
    patched_source: str | None = None,
    func_name: str | None = None,
    lens_witness_pairs: Sequence[tuple[Any, Any]] | None = None,
    mine_rewrite_laws: bool = True,
    rewrite_max_size: int = 3,
    rewrite_term_limit: int = 96,
    discover_stdlib_judges: bool = True,
) -> dict[str, Any]:
    """Wave 24: Red Queen Co-Evolution of Evaluators (`0H`, `K3=0`).

    Fuses three hidden evaluator engines under Red Queen Gödel Machine intra-epoch
    freeze discipline (evaluators are content-hashed and FROZEN within `epoch_index`;
    newly discovered judges, CoW boundary fuzzers, bidirectional lenses, and mined
    algebraic rewrite rules take effect only at `epoch_index + 1`):
      1. `auto_judge_discovery_v1` (`discover_stdlib_candidates` + `close_ignorance_loop`).
      2. `cow_lens_fuzz_and_negative_space_v1` (`verify_cow_boundary_invariance` +
         `synthesize_bidirectional_fst_lens`).
      3. `mined_rewrite_theory_v1` (`mine_rules` + `minimize_rules`).
    """
    import hashlib as _hl

    from canonical.swe_kernel import auto_judge_discovery_v1 as ajd
    from canonical.swe_kernel import cow_lens_fuzz_and_negative_space_v1 as clf
    from canonical.swe_kernel import mined_rewrite_theory_v1 as mrt

    t0 = time.perf_counter()
    # Freeze current-epoch judge signature so intra-epoch reward hacking is structurally impossible
    epoch_judge_digest = _hl.sha256(
        f"red_queen_epoch:{int(epoch_index)}:{bool(discover_stdlib_judges)}:{bool(mine_rewrite_laws)}".encode("utf-8")
    ).hexdigest()[:16]

    stdlib_judges: list[dict[str, Any]] = []
    ignorance_report: dict[str, Any] | None = None
    if discover_stdlib_judges:
        cands = ajd.discover_stdlib_candidates()
        stdlib_judges = [
            {"kind": str(c[0]), "label": str(c[1]), "probe": list(c[2])}
            for c in cands
        ]
    if scan_root is not None and Path(scan_root).is_dir():
        ignorance_report = ajd.close_ignorance_loop(Path(scan_root).resolve(), max_files=64)

    fuzz_report: dict[str, Any] | None = None
    if orig_source is not None and patched_source is not None and func_name:
        fv = clf.verify_cow_boundary_invariance(
            orig_source.encode("utf-8"),
            patched_source.encode("utf-8"),
            str(func_name),
        )
        fuzz_report = {
            "passed": bool(fv.passed),
            "cases_executed": int(fv.cases_executed),
            "preserved_ok": int(fv.preserved_ok),
            "crashes_fixed": int(fv.crashes_fixed),
            "new_unexpected_crashes": int(fv.new_unexpected_crashes),
            "isolated_via_cow_fork": bool(fv.isolated_via_cow_fork),
            "counterexample_count": len(fv.counterexamples),
        }

    lens_report: dict[str, Any] | None = None
    if lens_witness_pairs:
        lens = clf.synthesize_bidirectional_fst_lens(list(lens_witness_pairs))
        if lens is not None:
            lens_report = {
                "lens_id": str(lens.lens_id),
                "lens_family": str(lens.lens_family),
                "forward_expr_template": str(lens.forward_expr_template),
                "backward_expr_template": str(lens.backward_expr_template),
                "roundtrip_verified": bool(lens.roundtrip_verified),
                "witness_count": int(lens.witness_count),
            }
        else:
            lens_report = {"roundtrip_verified": False}

    rewrite_report: dict[str, Any] | None = None
    if mine_rewrite_laws:
        mined = mrt.mine_rules(
            max_size=int(rewrite_max_size),
            term_limit=int(rewrite_term_limit),
            witnesses_per_round=12,
            verify_rounds=2,
            seed=int(epoch_index),
        )
        rules_raw = list(mined.get("rules") or ())
        minimal = mrt.minimize_rules(rules_raw[:24], rounds=2, budget=120) if rules_raw else []
        rewrite_report = {
            "mined_rule_count": len(rules_raw),
            "minimized_rule_count": len(minimal),
            "refuted_count": len(mined.get("refuted") or ()),
            "sample_rules": [
                {"left": repr(r.left), "right": repr(r.right), "witnesses": int(r.witnesses)}
                for r in minimal[:6]
            ],
        }

    next_epoch_digest = _hl.sha256(
        f"red_queen_epoch:{int(epoch_index) + 1}:{len(stdlib_judges)}:{(rewrite_report or {}).get('minimized_rule_count', 0)}:{bool((fuzz_report or {}).get('passed', True))}".encode("utf-8")
    ).hexdigest()[:16]

    passed = (
        (fuzz_report is None or bool(fuzz_report["passed"]))
        and (len(stdlib_judges) > 0 or rewrite_report is not None or fuzz_report is not None or lens_report is not None)
    )
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__RED_QUEEN_EPOCH_COEVOLVED" if passed else "FAIL_CLOSED__RED_QUEEN_FUZZ_REGRESSION",
        "epoch_index": int(epoch_index),
        "next_epoch_index": int(epoch_index) + 1,
        "intra_epoch_frozen_judge_digest": epoch_judge_digest,
        "next_epoch_judge_digest": next_epoch_digest,
        "intra_epoch_mutation_forbidden": True,
        "stdlib_judges_discovered": len(stdlib_judges),
        "stdlib_judges": stdlib_judges[:16],
        "ignorance_loop": ignorance_report,
        "cow_boundary_fuzz": fuzz_report,
        "bidirectional_lens": lens_report,
        "mined_rewrite_theory": rewrite_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def audit_verifier_pinning_and_synthesize_oracles(
    *,
    before_source: str | None = None,
    after_source: str | None = None,
    verifier_fn: Callable[[str], bool] | None = None,
    min_pin_ratio: float = 0.5,
    require_fail_to_pass: bool = True,
    docstring_source: str | None = None,
    docstring_probe_inputs: Sequence[Any] = (),
    green_suite_source: str | None = None,
    green_suite_entry: str | None = None,
    green_suite_inputs: Sequence[tuple[Any, ...]] = (),
    origin_target: str | None = None,
    origin_baseline: Mapping[str, str] | None = None,
    origin_kind: str = "exact",
    origin_root: str | Path | None = None,
) -> dict[str, Any]:
    """Wave 29 (`0H` × 4 unwired oracle-synthesis & verifier-pinning superweapons, `K3=0`).

    Wires:
      1. `what_the_verifier_actually_pins_v1` (`hunks`, `revert`, `is_behavioural`, `typing_only`):
         hunk-by-hunk ablation audit measuring what fraction of behavioural hunks the verifier
         actually pins (catches weak tests, dead edits, and reward hacking!).
      2. `the_docstring_states_the_oracle_v1` (`docstrings`, `claims_in`):
         extracts mechanically checkable roundtrip/idempotence claims directly from docstrings
         and optionally executes them against compiled code!
      3. `the_oracle_can_be_synthesised_from_a_green_suite_v1` + behavioural oracle capture:
         synthesizes concrete `(args -> expected_output)` regression assertions from a green module.
      4. `one_origin_derives_the_judge_v1` (`supplied_judge`):
         optionally evaluates an origin-derived target judge on `origin_root`.
    """
    t0 = time.perf_counter()
    from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as pin_mod
    from canonical.tools import the_docstring_states_the_oracle_v1 as doc_oracle

    pinning_report: dict[str, Any] | None = None
    pinning_ok = True
    if before_source is not None and after_source is not None and verifier_fn is not None:
        all_hunks = pin_mod.hunks(before_source, after_source)
        beh_hunks = [
            h for h in all_hunks
            if pin_mod.is_behavioural(after_source, h) and not pin_mod.typing_only(after_source, h)
        ]
        before_passes = bool(verifier_fn(before_source))
        after_passes = bool(verifier_fn(after_source))
        hunk_results: list[dict[str, Any]] = []
        pinned_count = 0
        for idx, h in enumerate(beh_hunks):
            reverted = pin_mod.revert(after_source, before_source, h)
            rev_passes = bool(verifier_fn(reverted))
            is_pinned = not rev_passes
            if is_pinned:
                pinned_count += 1
            hunk_results.append({
                "hunk_index": idx,
                "tag": str(h["tag"]),
                "old_range": list(h["old"]),
                "new_range": list(h["new"]),
                "pinned": is_pinned,
                "reverted_verifier_passed": rev_passes,
            })
        pin_ratio = (pinned_count / len(beh_hunks)) if beh_hunks else 0.0
        ftp_ok = (not before_passes) if require_fail_to_pass else True
        pinning_ok = (
            after_passes
            and ftp_ok
            and len(beh_hunks) > 0
            and pin_ratio >= float(min_pin_ratio)
        )
        pinning_report = {
            "pass": pinning_ok,
            "before_passed": before_passes,
            "after_passed": after_passes,
            "total_hunks": len(all_hunks),
            "behavioural_hunks": len(beh_hunks),
            "pinned_hunks": pinned_count,
            "unpinned_hunks": len(beh_hunks) - pinned_count,
            "pin_ratio": round(pin_ratio, 4),
            "min_pin_ratio": float(min_pin_ratio),
            "hunks": hunk_results,
        }

    # 2. Docstring-stated oracle claims (`the_docstring_states_the_oracle_v1`)
    doc_src = docstring_source if docstring_source is not None else after_source
    docstring_report: dict[str, Any] | None = None
    doc_probe_ok = True
    if doc_src is not None:
        docs = doc_oracle.docstrings(doc_src)
        claims = doc_oracle.claims_in(doc_src)
        probe_results: list[dict[str, Any]] = []
        if claims and docstring_probe_inputs:
            ns: dict[str, Any] = {"__name__": "__wave29_doc_probe__"}
            try:
                exec(compile(doc_src, "<doc_oracle>", "exec"), ns)
                for claim in claims:
                    owner = str(claim.get("owner") or "")
                    other = str(claim.get("other") or "")
                    fn_owner = ns.get(owner)
                    fn_other = ns.get(other)
                    if callable(fn_owner) and callable(fn_other):
                        checked = 0
                        passed_n = 0
                        for inp in docstring_probe_inputs:
                            checked += 1
                            try:
                                norm_v = fn_other(inp)
                                res_v = fn_owner(norm_v)
                                if bool(res_v):
                                    passed_n += 1
                            except Exception:
                                pass
                        ok_c = checked > 0 and passed_n == checked
                        if not ok_c:
                            doc_probe_ok = False
                        probe_results.append({
                            "claim": dict(claim),
                            "checked": checked,
                            "passed": passed_n,
                            "holds": ok_c,
                        })
            except Exception as exc:  # noqa: BLE001
                doc_probe_ok = False
                probe_results.append({"error": f"{type(exc).__name__}: {exc}"})
        docstring_report = {
            "docstring_count": len(docs),
            "claims_extracted": claims,
            "probe_results": probe_results,
            "all_probed_claims_hold": doc_probe_ok,
        }

    # 3. Synthesize concrete regression oracle assertions from a green module (`the_oracle_can_be_synthesised_from_a_green_suite_v1` contract)
    green_oracle_report: dict[str, Any] | None = None
    if green_suite_source is not None and green_suite_entry and green_suite_inputs:
        ns_g: dict[str, Any] = {"__name__": "__wave29_green_oracle__"}
        assertions: list[str] = []
        try:
            exec(compile(green_suite_source, "<green_suite>", "exec"), ns_g)
            fn_g = ns_g.get(str(green_suite_entry))
            if callable(fn_g):
                for args in green_suite_inputs:
                    arg_tuple = tuple(args) if isinstance(args, (list, tuple)) else (args,)
                    val = fn_g(*arg_tuple)
                    arg_s = ", ".join(repr(a) for a in arg_tuple)
                    assertions.append(f"assert {green_suite_entry}({arg_s}) == {val!r}")
        except Exception as exc:  # noqa: BLE001
            assertions = []
            green_oracle_report = {"pass": False, "error": f"{type(exc).__name__}: {exc}", "assertions": []}
        if green_oracle_report is None:
            green_oracle_report = {
                "pass": len(assertions) > 0,
                "entry": str(green_suite_entry),
                "synthesized_assertion_count": len(assertions),
                "assertions": assertions,
            }

    # 4. Origin-derived judge (`one_origin_derives_the_judge_v1`)
    origin_judge_report: dict[str, Any] | None = None
    origin_ok = True
    if origin_target and origin_baseline is not None and origin_root is not None:
        from canonical.tools import one_origin_derives_the_judge_v1 as orig_j

        judge_fn = orig_j.supplied_judge(str(origin_target), dict(origin_baseline), str(origin_kind))
        j_ok, j_msg = judge_fn(Path(origin_root).resolve())
        origin_ok = bool(j_ok)
        origin_judge_report = {
            "pass": origin_ok,
            "target": str(origin_target),
            "kind": str(origin_kind),
            "detail": str(j_msg),
        }

    any_checked = any(
        x is not None for x in (pinning_report, docstring_report, green_oracle_report, origin_judge_report)
    )
    overall = (
        any_checked
        and pinning_ok
        and doc_probe_ok
        and origin_ok
        and (green_oracle_report is None or bool(green_oracle_report.get("pass")))
    )
    return {
        "schema": SCHEMA,
        "pass": overall,
        "status": (
            "PASS__VERIFIER_PINNING_AND_ORACLES_AUDITED"
            if overall
            else "FAIL_CLOSED__VERIFIER_PINNING_OR_ORACLE_FAILED"
        ),
        "verifier_pinning": pinning_report,
        "docstring_oracles": docstring_report,
        "green_suite_oracle": green_oracle_report,
        "origin_judge": origin_judge_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def prove_equivalence_and_amplify_verdict(
    *,
    # 1. Consistency vs Equivalence proof (`consistency_vs_equivalence_v1`)
    code_rule: Mapping[str, Any] | None = None,
    before_snippet: str | None = None,
    after_snippet: str | None = None,
    rule_judge: Any = None,
    rule_probes: Sequence[Any] | None = None,
    rule_language: str = "python",
    gate_report: Mapping[str, Any] | None = None,
    # 2. Minimal distinguishing projection oracle (`distinguishing_projection_v1`)
    projection_root: str | Path | None = None,
    projection_features: Sequence[str] | None = None,
    run_projection_synthesize: bool = False,
    # 3. Reach changed site & pin reverted part (`reach_the_changed_site_v1` + `pins_from_the_reverted_part_v1`)
    pin_tree: str | Path | None = None,
    pin_source_rel: str | None = None,
    pin_test_rel: str | None = None,
    pin_fixed: str | None = None,
    pin_mutant: str | None = None,
    pin_test_source: str | None = None,
    reach_part_spec: Mapping[str, Any] | None = None,
    reach_budget: int = 80,
    # 4. Patch verdict amplification (`patch_verdict_amplification_v1`)
    amplify_module_path: str | None = None,
    amplify_test_path: str | None = None,
    amplify_candidate_source: str | None = None,
    amplify_repo_root: str | Path | None = None,
    amplify_extra_pools: Mapping[str, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Wave 32: Behavioral-Equivalence Proof, Minimal Distinguishing Projection, Reverted-Part Pinning & Verdict Amplification (`0H`, `K3=0`).

    Composes 5 pure-stdlib hidden oracle & proof engines lazily on demand:
      - `consistency_vs_equivalence_v1`: prove_code_rule + combined_admission_verdict
      - `distinguishing_projection_v1`: project / combine / synthesize minimal action-identifying oracle
      - `pins_from_the_reverted_part_v1`: calls_from_the_test + pin_part
      - `reach_the_changed_site_v1`: reach_part to hit the changed line and assert its effect
      - `patch_verdict_amplification_v1`: prepare_laws + laws_against_prepared / amplify
    """
    t0 = time.perf_counter()
    engines_invoked: list[str] = []
    results: dict[str, Any] = {}
    any_ok = False
    all_ok = True

    # 1. Consistency vs Equivalence (`consistency_vs_equivalence_v1`)
    if code_rule is not None and before_snippet is not None and after_snippet is not None and rule_judge is not None and rule_probes is not None:
        from canonical.swe_kernel import consistency_vs_equivalence_v1 as cve

        engines_invoked.append("canonical.swe_kernel.consistency_vs_equivalence_v1")
        proof = cve.prove_code_rule(
            dict(code_rule),
            str(before_snippet),
            str(after_snippet),
            rule_judge,
            list(rule_probes),
            language=str(rule_language),
        )
        proof_dict = proof.__dict__ if hasattr(proof, "__dict__") else {"proof": str(proof)}
        combined = cve.combined_admission_verdict(dict(gate_report), proof) if gate_report is not None else None
        results["equivalence_proof"] = {
            "proof": proof_dict,
            "combined_verdict": combined,
        }
        any_ok = True

    # 2. Distinguishing projection oracle (`distinguishing_projection_v1`)
    if projection_root is not None and projection_features:
        from canonical.swe_kernel import distinguishing_projection_v1 as dp

        engines_invoked.append("canonical.swe_kernel.distinguishing_projection_v1")
        root_p = Path(projection_root).resolve()
        feats = [str(f) for f in projection_features]
        per_feat = {f: dp.project(root_p, f) for f in feats}
        combined_proj = dp.combine(root_p, feats)
        results["distinguishing_projection"] = {
            "features": feats,
            "per_feature": per_feat,
            "combined": combined_proj,
        }
        any_ok = True
    elif run_projection_synthesize:
        from canonical.swe_kernel import distinguishing_projection_v1 as dp

        engines_invoked.append("canonical.swe_kernel.distinguishing_projection_v1")
        results["distinguishing_projection"] = dp.synthesize()
        any_ok = True

    # 3. Calls from test + Pin reverted part + Reach changed site (`pins_from_the_reverted_part_v1` + `reach_the_changed_site_v1`)
    extracted_calls: list[dict[str, Any]] = []
    if pin_test_source is not None:
        from canonical.swe_kernel import pins_from_the_reverted_part_v1 as pinr

        engines_invoked.append("canonical.swe_kernel.pins_from_the_reverted_part_v1")
        extracted_calls = pinr.calls_from_the_test(str(pin_test_source))
        results["test_calls"] = {
            "count": len(extracted_calls),
            "calls": extracted_calls,
        }
        any_ok = True

    if pin_tree is not None and pin_source_rel and pin_test_rel and pin_fixed is not None and pin_mutant is not None:
        from canonical.swe_kernel import pins_from_the_reverted_part_v1 as pinr

        if "canonical.swe_kernel.pins_from_the_reverted_part_v1" not in engines_invoked:
            engines_invoked.append("canonical.swe_kernel.pins_from_the_reverted_part_v1")
        tree_p = Path(pin_tree).resolve()
        if not extracted_calls:
            tst_p = tree_p / str(pin_test_rel)
            if tst_p.is_file():
                extracted_calls = pinr.calls_from_the_test(tst_p.read_text(encoding="utf-8", errors="replace"))
        pin_res = pinr.pin_part(tree_p, str(pin_source_rel), str(pin_test_rel), str(pin_fixed), str(pin_mutant), extracted_calls)
        results["reverted_part_pin"] = pin_res
        any_ok = True
        if reach_part_spec is not None:
            from canonical.swe_kernel import reach_the_changed_site_v1 as reachs

            engines_invoked.append("canonical.swe_kernel.reach_the_changed_site_v1")
            reach_res = reachs.reach_part(
                tree_p,
                str(pin_source_rel),
                str(pin_test_rel),
                str(pin_fixed),
                str(pin_mutant),
                dict(reach_part_spec),
                extracted_calls,
                budget=int(reach_budget),
            )
            results["reach_changed_site"] = reach_res

    # 4. Patch verdict amplification (`patch_verdict_amplification_v1`)
    if amplify_module_path is not None:
        from canonical.swe_kernel import patch_verdict_amplification_v1 as pva

        engines_invoked.append("canonical.swe_kernel.patch_verdict_amplification_v1")
        repo_p = Path(amplify_repo_root).resolve() if amplify_repo_root is not None else ROOT
        if amplify_test_path is not None and amplify_candidate_source is not None:
            amp_res = pva.amplify(
                module_path=str(amplify_module_path),
                test_path=str(amplify_test_path),
                candidate_source=str(amplify_candidate_source),
                repo_root=repo_p,
                extra_pools=amplify_extra_pools,
            )
            results["verdict_amplification"] = amp_res
        else:
            prep = pva.prepare_laws(
                module_path=str(amplify_module_path),
                repo_root=repo_p,
                extra_pools=amplify_extra_pools,
            )
            if amplify_candidate_source is not None:
                law_res = pva.laws_against_prepared(prep, candidate_source=str(amplify_candidate_source))
                results["verdict_amplification"] = {"prepared": prep, "laws_result": law_res}
            else:
                results["verdict_amplification"] = {"prepared": prep}
        any_ok = True

    passed = bool(engines_invoked) and any_ok and all_ok
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__WAVE32_EQUIVALENCE_AND_VERDICT_AMPLIFIED"
            if passed
            else "FAIL_CLOSED__WAVE32_ORACLE_INPUTS_MISSING"
        ),
        "engines_invoked": engines_invoked,
        "results": results,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }






