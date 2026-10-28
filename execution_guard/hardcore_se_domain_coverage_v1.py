# PROJECT_BRAIN
"""hardcore_se_domain_coverage_v1.py — what a senior software engineer must be able to DO,
measured against the 158-entry bound registry, domain by domain.

The missing-verb probe asks about 43 acts and says what the front door does with each.  This
instrument asks a different question: for each hardcore-SE domain, which candidate acts are
PERFORMED by a capability that provides them, which are only *named* by keywords somewhere, and
which nothing in the machine mentions at all.  It is deliberately lexical against `provides` --
the registry's own claim vocabulary -- because anything cleverer would be an opinion.

Classification of one act:

  BOUND    some capability's `provides` names the act (or a token of it)  -> the machine claims it
  NAMED    no `provides` match, but a capability's keywords mention it    -> vocabulary only
  ABSENT   nothing in the registry mentions it                            -> a real hole

`BOUND` is a claim, not a proof: the missing-verb probe is what turns a claim into a measurement,
and the evidence audit (`capability_evidence_probe_v1.py --audit-pointers`) is what says whether
the claim points at anything a reader can check.  This instrument exists to find the holes the
43-act probe cannot reach, because a probe can only ask about acts somebody thought of.

Usage:
  python execution_guard/hardcore_se_domain_coverage_v1.py [--json PATH] [--only DOMAIN]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
EVIDENCE = ROOT / "canonical/astra_runtime/evidence/HARDCORE-SE-DOMAIN-COVERAGE-V1__RECEIPT.json"

# (domain, [(act, [tokens that would have to appear in some `provides`]) ...])
#
# The token lists are the vocabulary a capability would have to claim in order to be the thing
# that does the act.  They are deliberately narrow: `git.push` should not be satisfied by a
# capability that merely mentions the word "push" in prose.
DOMAINS: list[tuple[str, list[tuple[str, list[str]]]]] = [
    ("version control", [
        ("git.status", ["vcs.git.status"]),
        ("git.diff", ["vcs.git.diff"]),
        ("git.commit", ["vcs.git.commit"]),
        ("git.branch.create", ["vcs.git.branch_create"]),
        ("git.checkout", ["vcs.git.checkout"]),
        ("git.revert", ["vcs.git.revert"]),
        ("git.rebase", ["vcs.git.branch.rebase"]),
        ("git.bisect", ["vcs.git.history.bisect"]),
        ("git.blame", ["vcs.git.blame"]),
        ("git.stash", ["vcs.git.stash"]),
        ("git.merge", ["vcs.git.merge"]),
        ("git.cherry_pick", ["vcs.git.cherry"]),
        ("git.tag", ["vcs.git.tag"]),
        ("git.worktree", ["vcs.git.worktree"]),
        ("git.remote", ["vcs.git.remote"]),
        ("git.conflict.resolve", ["vcs.git.conflict", "merge.conflict"]),
        ("git.reflog.undo", ["vcs.git.reflog"]),
    ]),
    ("refactoring", [
        ("refactor.rename_symbol", ["python.refactor.rename_symbol"]),
        ("refactor.rename_parameter", ["python.refactor.rename_parameter"]),
        ("refactor.extract_function", ["python.refactor.extract_function"]),
        ("refactor.inline_function", ["python.refactor.inline_function"]),
        ("refactor.move_function", ["python.refactor.move_function"]),
        ("refactor.change_signature", ["python.refactor.change_signature"]),
        ("refactor.extract_variable", ["refactor.extract_variable"]),
        ("refactor.encapsulate_field", ["refactor.encapsulate"]),
        ("refactor.pull_up_method", ["refactor.pull_up"]),
        ("refactor.replace_conditional", ["refactor.replace_conditional"]),
        ("refactor.convert_to_method", ["refactor.convert"]),
        ("refactor.remove_dead_imports", ["refactor.unused_import"]),
        ("refactor.organise_imports", ["refactor.import"]),
        ("refactor.split_module", ["refactor.split"]),
    ]),
    ("static analysis", [
        ("static.lint", ["python.source.lint"]),
        ("static.type_check", ["python.source.types"]),
        ("static.complexity", ["python.source.complexity"]),
        ("static.dead_code", ["python.source.dead_code"]),
        ("static.duplication", ["python.source.duplication"]),
        ("static.symbol_index", ["python.source.symbol_index"]),
        ("static.symbol_resolve", ["python.source.symbols.resolve"]),
        ("static.impact_analysis", ["python.source.change_impact"]),
        ("static.audit_ast", ["python.source.audit"]),
        ("static.dataflow_taint", ["static.taint", "dataflow.taint"]),
        ("static.call_graph", ["static.call_graph"]),
        ("static.dependency_graph", ["static.dependency_graph"]),
        ("static.cross_language_index", ["code.symbols.multilanguage"]),
    ]),
    ("testing", [
        ("test.coverage", ["python.tests.coverage"]),
        ("test.slice", ["test.slice"]),
        ("test.scaffold", ["python.tests.generate.scaffold"]),
        ("test.flake_detect", ["python.quality.flaky_tests"]),
        ("test.mutation", ["test.mutation"]),
        ("test.property_based", ["evidence.hypothesis.property", "evidence.property_test"]),
        ("test.differential", ["test.differential"]),
        ("test.golden_snapshot", ["test.snapshot", "test.golden"]),
        ("test.data_generation", ["test.data", "test.fixture"]),
        ("test.contract_oracle", ["python.contract.verdict"]),
    ]),
    ("dynamic analysis", [
        ("dynamic.fuzz", ["python.dynamic.fuzz"]),
        ("dynamic.crash_repro", ["dynamic.crash"]),
        ("dynamic.memory_profile", ["dynamic.memory"]),
        ("dynamic.cpu_profile", ["dynamic.cpu_profile", "dynamic.profile"]),
        ("dynamic.debugger_breakpoint", ["dynamic.debug"]),
        ("dynamic.race_detect", ["dynamic.race", "concurrency.race"]),
        ("dynamic.deadlock_detect", ["dynamic.deadlock"]),
        ("dynamic.syscall_trace", ["dynamic.trace"]),
        ("dynamic.benchmark", ["dynamic.benchmark", "perf.benchmark"]),
    ]),
    ("performance engineering", [
        ("perf.regression_gate", ["python.review.diff_perf_gate"]),
        ("perf.complexity_metric", ["python.source.complexity"]),
        ("perf.big_o_inference", ["perf.big_o", "performance.complexity_class"]),
        ("perf.hotspot_ranking", ["perf.hotspot"]),
        ("perf.allocation_growth", ["perf.allocation"]),
        ("perf.query_plan", ["perf.query_plan"]),
    ]),
    ("security and supply chain", [
        ("security.sast", ["python.source.security.report"]),
        ("security.diff_gate", ["python.review.diff_security_gate"]),
        ("security.secret_scan", ["security.secret"]),
        ("security.vulnerability_audit", ["security.vulnerability", "security.cve", "security.osv"]),
        ("security.sbom", ["security.sbom"]),
        ("security.signature_verify", ["security.signature", "security.attestation"]),
        ("supplychain.license", ["python.dependencies.licenses"]),
        ("supplychain.provenance", ["pypi.provenance"]),
        ("supplychain.pin_lockfile", ["supplychain.lock", "python.project.lock"]),
    ]),
    ("dependencies and build", [
        ("build.package", ["python.project.wheel"]),
        ("build.dependency_add", ["python.project.dependency"]),
        ("build.install", ["python.project.install"]),
        ("build.upgrade_dependency", ["python.project.dependency.upgrade"]),
        ("build.remove_dependency", ["python.project.dependency.remove"]),
        ("build.version_bump", ["build.version", "python.project.version"]),
        ("build.reproducible", ["build.reproducible"]),
        ("build.monorepo", ["build.monorepo", "build.workspace"]),
        ("build.cache", ["build.cache"]),
        ("release.publish", ["release.publish"]),
    ]),
    ("data and persistence", [
        ("data.sqlite_create", ["sqlite.table.create"]),
        ("data.sqlite_verify", ["sqlite.table.verify"]),
        ("data.json_transform", ["json.file", "json.query"]),
        ("data.yaml_transform", ["yaml.to_json"]),
        ("data.binary_codec", ["structured.binary.encode"]),
        ("data.schema_migration", ["data.schema_migration", "database.migration"]),
        ("data.query_optimise", ["database.query"]),
        ("data.transaction", ["database.transaction"]),
        ("data.integrity_check", ["database.integrity"]),
    ]),
    ("services and concurrency", [
        ("service.http_client", ["http.json.fetch"]),
        ("service.shell", ["shell.command.result"]),
        ("service.retry_design", ["service.retry", "resilience.retry"]),
        ("service.timeout_policy", ["resilience.timeout"]),
        ("service.circuit_breaker", ["resilience.circuit"]),
        ("service.async_audit", ["python.source.concurrency.report"]),
        ("service.task_graph", ["concurrency.task_graph"]),
        ("service.server_local", ["service.http_server"]),
    ]),
    ("infrastructure and delivery", [
        ("infra.ci_config", ["infra.ci", "cicd.pipeline.config"]),
        ("infra.container", ["infra.container", "docker.image"]),
        ("infra.iac", ["infra.iac", "terraform"]),
        ("infra.deploy", ["infra.deploy"]),
        ("infra.secret_management", ["infra.secret"]),
        ("infra.environment_fit", ["environment_fit", "environment.satisfy"]),
    ]),
    ("observability", [
        ("obs.logging_instrument", ["obs.logging", "observability.logging"]),
        ("obs.metrics_instrument", ["obs.metrics"]),
        ("obs.tracing", ["obs.trace"]),
        ("obs.structured_log_analysis", ["obs.log_analysis"]),
        ("obs.slo", ["obs.slo"]),
    ]),
    ("documentation", [
        ("docs.docstrings", ["docs.docstring", "documentation.docstring"]),
        ("docs.readme", ["docs.readme"]),
        ("docs.api_reference", ["docs.api_reference"]),
        ("docs.changelog", ["python.repository.changelog"]),
    ]),
    ("review and delivery flow", [
        ("review.diff_gate", ["python.review.diff_coverage_gate"]),
        ("review.mutation_gate", ["python.review.diff_mutation_gate"]),
        ("review.type_gate", ["python.review.diff_type_gate"]),
        ("review.static_triage", ["python.review.diff_static_triage"]),
        ("review.pr_land", ["python.pr.land"]),
        ("review.pr_realize", ["python.repo.pr_realize"]),
        ("review.issue_to_pr", ["python.software.issue_to_pr"]),
        ("review.code_review_comment", ["review.comment"]),
    ]),
    ("multi-language", [
        ("lang.python_parse", ["python.source.symbol_index"]),
        ("lang.tree_sitter_parse", ["code.ast.tree_sitter"]),
        ("lang.tree_sitter_patch_verify", ["code.patch.tree_sitter"]),
        ("lang.javascript_refactor", ["javascript.refactor", "typescript.refactor"]),
        ("lang.go_analysis", ["go.analysis", "golang"]),
        ("lang.rust_analysis", ["rust.analysis"]),
        ("lang.c_cpp_compile", ["c.compile", "cpp.compile"]),
    ]),
]


def classify(act_tokens: list[str], provides: list[str], keywords: list[str]) -> tuple[str, str]:
    joined_provides = " ".join(provides)
    for token in act_tokens:
        if token in joined_provides:
            owner = next((p for p in provides if token in p), token)
            return "BOUND", owner
    joined_keywords = " ".join(keywords)
    for token in act_tokens:
        if token.split(".")[-1] in joined_keywords:
            return "NAMED", ""
    return "ABSENT", ""


def measure() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    caps = registry.get("capabilities", registry)
    provides: list[str] = []
    keywords: list[str] = []
    for entry in caps.values():
        provides.extend(str(p) for p in (entry.get("provides") or []))
        keywords.extend(str(k) for k in (entry.get("keywords") or []))
    rows: list[dict[str, Any]] = []
    for domain, acts in DOMAINS:
        for act, tokens in acts:
            state, owner = classify(tokens, provides, keywords)
            rows.append({"domain": domain, "act": act, "state": state, "owner": owner})
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = summary.setdefault(row["domain"], {"BOUND": 0, "NAMED": 0, "ABSENT": 0, "total": 0})
        bucket[row["state"]] += 1
        bucket["total"] += 1
    return {"capabilities_in_registry": len(caps),
            "provides_vocabulary": len(set(provides)),
            "rows": rows, "summary": summary}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None)
    parser.add_argument("--only", default=None)
    ns = parser.parse_args(argv)
    measured = measure()
    rows = measured["rows"]
    if ns.only:
        rows = [row for row in rows if row["domain"] == ns.only]
    width = max(len(row["act"]) for row in rows)
    for row in rows:
        print("%-11s %-*s %s" % (row["state"], width, row["act"], row["owner"]))
    print()
    bound = sum(1 for row in measured["rows"] if row["state"] == "BOUND")
    named = sum(1 for row in measured["rows"] if row["state"] == "NAMED")
    absent = sum(1 for row in measured["rows"] if row["state"] == "ABSENT")
    print("acts: %d | BOUND %d | NAMED %d | ABSENT %d" %
          (len(measured["rows"]), bound, named, absent))
    print()
    for domain, counts in measured["summary"].items():
        print("%-28s bound %2d / %2d  (named %d, absent %d)" %
              (domain, counts["BOUND"], counts["total"], counts["NAMED"], counts["ABSENT"]))
    if ns.json:
        Path(ns.json).write_text(json.dumps(measured, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
    receipts = ROOT / "canonical/astra_runtime/evidence"
    if receipts.is_dir() and not ns.only:
        payload = {"schema": "HARDCORE_SE_DOMAIN_COVERAGE_V1", "measured": measured,
                   "instrument": "execution_guard/hardcore_se_domain_coverage_v1.py"}
        EVIDENCE.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("\nreceipt: %s" % EVIDENCE.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
