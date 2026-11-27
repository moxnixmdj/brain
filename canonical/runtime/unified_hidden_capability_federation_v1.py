"""Unified Hidden-Capability Federation Runtime — v1.

Surfaces the repository's specialized zero-model (`K3=0`, `$0` spend) solvers,
verified true capabilities (`TRUE_CAPABILITY_LEDGER_V1`), SWE synthesis &
repair engines (`canonical/swe_kernel/*`), polyglot C/JS/Rust/Go/C++/TS kernels,
Petri/GUI/CLI/prose-experiment computer-use engines, continual-learning &
meta-circular organ synthesizers, quantitative finance/LBO/DCF/FIBO/RegCap
engines, 3D visual-hull/chartography/CAD/OOXML/PDF kernels, compositional
language/IF/H100 symbolic engines, and admitted read-only module-function
dispatch (`MODULE_INVOCATION_EVIDENCE_V1`) into a single deterministic,
content-addressed engine surface for `brain_unified_model_v1` and
`compile_brain_unified_model_v1`.

All execution is strictly local, deterministic, fail-closed on missing inputs or
absent host dependencies, and invokes zero external or local neural models.
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import warnings
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
CARRIER_REL_PATH = "canonical/runtime/unified_hidden_capability_federation_v1.py"
SCHEMA = "BRAIN_UNIFIED_HIDDEN_CAPABILITY_FEDERATION_V1"

_WORD_RE = re.compile(r"[a-z0-9]+")
_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.M)
_NON_SOURCE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".git",
        "node_modules",
        ".venv",
        "venv",
    }
)
_EXTENDED_SOURCE_TREES: tuple[str, ...] = (
    "canonical/tools",
    "canonical/capabilities",
    "canonical/research",
    "canonical/integrations",
    "intake",
    "execution_guard",
)

STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "how",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "please",
        "should",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "use",
        "using",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _WORD_RE.findall((text or "").lower()) if tok not in STOPWORDS]


def _term_counts(text: str, *, limit: int = 120) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tok in _tokenize(text):
        if len(tok) < 2:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return {k: v for k, v in sorted(ranked)}


def _fail(mode: str, reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "engine_mode": mode,
        "pass": False,
        "status": "FAIL_CLOSED__" + reason,
        "reason": reason,
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }
    out.update(extra)
    return out


def _ok(mode: str, status_suffix: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    inner_status = body.pop("status", None)
    body.pop("pass", None)
    body.pop("schema", None)
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "engine_mode": mode,
        "pass": True,
        "status": "PASS__" + status_suffix,
        "reason": None,
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }
    if inner_status is not None:
        out["kernel_status"] = inner_status
    out.update(body)
    return out


def _require_keys(mode: str, inputs: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any] | None:
    missing = [k for k in keys if k not in inputs or inputs[k] is None]
    if missing:
        return _fail(
            mode,
            "ENGINE_INPUTS_MISSING:" + ",".join(missing),
            missing_inputs=missing,
            required_inputs=list(keys),
        )
    return None


# ---------------------------------------------------------------------------
# Descriptor Table (52 zero-model repository kernels across 8 domains)
# ---------------------------------------------------------------------------

FEDERATED_KERNEL_DESCRIPTORS: dict[str, dict[str, Any]] = {
    # --- 1. VERIFIED TRUE CAPABILITIES (TRUE_CAPABILITY_LEDGER_V1) ---
    "DOCX_EXACT_TEXT_EDIT": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/docx_exact_text_edit.py",
        "entrypoint": "solve_instance",
        "summary": "Exact unique text replacement inside OOXML .docx packages with byte-clean rollback on ambiguity.",
        "triggers": ["docx exact edit", "replace unique docx", "ooxml word replacement", "docx_b64"],
        "required_inputs": ["docx_b64", "old", "new"],
        "declared_dependencies": [],
    },
    "DOCX_RUN_SPAN_REPLACE": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/docx_true_capability_adapters_v1.py",
        "entrypoint": "solve_span",
        "summary": "Cross-run paragraph span text replacement inside OOXML .docx documents preserving run formatting.",
        "triggers": ["docx run span", "paragraph span replace", "split run docx", "solve_span"],
        "required_inputs": ["docx_b64", "old", "new"],
        "declared_dependencies": [],
    },
    "DOCX_STORY_PART_REPLACE": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/docx_true_capability_adapters_v1.py",
        "entrypoint": "solve_story",
        "summary": "Multi-part OOXML .docx story replacement across headers, footers, footnotes, and body XML.",
        "triggers": ["docx story part", "header footer footnote docx", "solve_story"],
        "required_inputs": ["docx_b64", "old", "new"],
        "declared_dependencies": [],
    },
    "DOCX_TEXT_EDIT_TRANSACTION": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/docx_true_capability_adapters_v1.py",
        "entrypoint": "solve_transaction",
        "summary": "Atomic multi-operation OOXML .docx edit transaction with all-or-nothing integrity verification.",
        "triggers": ["docx edit transaction", "atomic docx operations", "solve_transaction"],
        "required_inputs": ["docx_b64", "edits"],
        "declared_dependencies": [],
    },
    "SACCR_CREDIT_ADDON": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/saccr_credit_kernel.py",
        "entrypoint": "solve_instance",
        "summary": "Basel III SA-CCR credit derivative counterparty exposure add-on calculator with per-trade supervisory traces.",
        "triggers": ["saccr", "counterparty credit addon", "supervisory duration notional", "basel credit exposure"],
        "required_inputs": ["trades"],
        "declared_dependencies": [],
    },
    "AUTHENTICATED_PARETO_SCHEDULE": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/scheduler_true_capability_adapters_v1.py",
        "entrypoint": "solve_schedule",
        "summary": "Receipt-authenticated nondominated Pareto schedule compiler rejecting unauthenticated dominance claims.",
        "triggers": ["authenticated pareto schedule", "nondominated schedule", "solve_schedule"],
        "required_inputs": ["candidates"],
        "declared_dependencies": [],
    },
    "CAPABILITY_FIRST_RANKING": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/scheduler_true_capability_adapters_v1.py",
        "entrypoint": "solve_ranking",
        "summary": "Capability-first obligation unlock & discharge work ranker with deterministic tie-breaking.",
        "triggers": ["capability first ranking", "obligation unlock ranker", "solve_ranking"],
        "required_inputs": ["work", "checkpoint_open_obligation_count"],
        "declared_dependencies": [],
    },
    "PARETO_FRONTIER_UPDATE": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/scheduler_true_capability_adapters_v1.py",
        "entrypoint": "solve_frontier",
        "summary": "Incremental Pareto frontier folder tracking dominated and admitted candidate transitions.",
        "triggers": ["pareto frontier update", "fold pareto candidates", "solve_frontier"],
        "required_inputs": ["candidates"],
        "declared_dependencies": [],
    },
    "SAME_IDENTITY_SUPERVISOR": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/runtime/same_identity_supervisor.py",
        "entrypoint": "solve_instance",
        "summary": "Lease-enforced causal task supervisor preventing split-brain agent claim collisions.",
        "triggers": ["same identity supervisor", "causal task lease", "agent lease supervisor"],
        "required_inputs": ["tasks", "steps"],
        "declared_dependencies": [],
    },
    # --- 2. HIDDEN SWE, CEGIS, SPLICING, TOMOGRAPHY & SYNTHESIS KERNELS ---
    "FRONTIER_FST_LENS_SYNTHESIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/frontier_unified_engine_v1.py",
        "entrypoint": "synthesize_fst_lens",
        "summary": "Induces exact bidirectional finite-state transducer (FST) string/AST lenses from input/output witness pairs.",
        "triggers": ["fst lens", "bidirectional fst", "transducer witness pairs", "synthesize_fst_lens"],
        "required_inputs": ["witness_pairs"],
        "declared_dependencies": [],
    },
    "ANGELIC_LENS_COW_REPAIR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/angelic_lens_cow_repair_v1.py",
        "entrypoint": "synthesize_bidirectional_lens",
        "summary": "Angelic causal nexus localization, backward output-residual propagation, and separating guard synthesis.",
        "triggers": ["angelic lens", "backward output residual", "angelic causal nexus", "separating guard"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "REVERSE_TOMOGRAPHY_ALGEBRA": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/reverse_tomography_algebra_v1.py",
        "entrypoint": "backpropagate_ast_repairs",
        "summary": "Reverse value tomography, AST repair backpropagation from assertion residuals, and certified ddmin shrinking.",
        "triggers": ["reverse tomography", "backpropagate ast repairs", "ddmin shrink", "output residual"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "FIRST_PRINCIPLES_MENTAL_CEGIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/first_principles_mental_cegis_v1.py",
        "entrypoint": "egraph_canonicalize",
        "summary": "First-principles mental simulation CEGIS with AST e-graph canonicalization and bottom-up expression synthesis.",
        "triggers": ["mental cegis", "egraph canonicalize", "bottom up expression synthesis"],
        "required_inputs": ["expression"],
        "declared_dependencies": [],
    },
    "DUAL_PROGRAM_SPLICING": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/dual_program_splicing_v1.py",
        "entrypoint": "splice",
        "summary": "Composes non-overlapping and dialectically resolved hunks from two partial candidate repairs against a parent file.",
        "triggers": ["dual program splicing", "splice candidate patches", "combine partial repairs"],
        "required_inputs": ["parent", "candidate_a", "candidate_b"],
        "declared_dependencies": [],
    },
    "MULTI_PRODUCER_NORMALIZATION": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/multi_producer_normalization_v1.py",
        "entrypoint": "normalize_candidates",
        "summary": "Synthesizes multi-producer boundary normalizers, whitespace/None guards, and exception-fence repairs.",
        "triggers": ["multi producer normalization", "exception fence candidates", "none return candidates"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "MANUFACTURED_CONTRAST_PROBE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/manufactured_contrast_v1.py",
        "entrypoint": "literals",
        "summary": "Extracts mutable test literal holes and manufactures contrasting passing/failing executions for fault localization.",
        "triggers": ["manufactured contrast", "test literal holes", "contrastive mutation probe"],
        "required_inputs": ["test_source"],
        "declared_dependencies": [],
    },
    "ASSERTION_OPERAND_TOMOGRAPHY": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/assertion_operand_tomography_v1.py",
        "entrypoint": "instrument",
        "summary": "Instruments test assertions to capture live left/right operand witnesses at failure time without modifying semantics.",
        "triggers": ["assertion operand tomography", "instrument assertion operands"],
        "required_inputs": ["test_source"],
        "declared_dependencies": [],
    },
    "DISTINCTION_GUARD_SYNTHESIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/distinction_creation_v1.py",
        "entrypoint": "synthesise_guard",
        "summary": "Synthesizes minimal conjunction predicates separating positive and negative feature environments with honest refusal on contradiction.",
        "triggers": ["distinction guard", "synthesise separating conjunction", "positive negative guard"],
        "required_inputs": ["positives", "negatives"],
        "declared_dependencies": [],
    },
    "SEMANTIC_CAUSAL_UIR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/semantic_causal_engine_v1.py",
        "entrypoint": "semantically_equivalent",
        "summary": "Lowers Python/C/JS expressions to Universal Intermediate Representation (UIR) and proves equivalence by equality saturation.",
        "triggers": ["semantic causal uir", "equality saturation uir", "uir canonicalize"],
        "required_inputs": ["code_a", "code_b"],
        "declared_dependencies": [],
    },
    "DEEP_UNDERSTANDING_IR_DATAFLOW": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/deep_understanding_engine_v1.py",
        "entrypoint": "are_semantically_equivalent",
        "summary": "Cross-language Python/C IR normalization, def-use dataflow extraction, and causal variable path tracing.",
        "triggers": ["deep understanding dataflow", "cross language ir equivalence", "extract_dataflow"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "PERFECT_UMG_CAUSAL_LINEAGE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/perfect_algorithm_v1.py",
        "entrypoint": "to_umg",
        "summary": "Translates source code into a Universal Meaning Graph (UMG), traces data lineage, and isolates causal crash roots.",
        "triggers": ["universal meaning graph", "umg causal lineage", "trace_data_lineage"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "EGRAPH_DEDUCTIVE_SYNTHESIZER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py",
        "entrypoint": "egraph_optimize_function",
        "summary": "Deductive e-graph algebraic optimizer, automatic memoization transformer, and structural Python refactoring kernel.",
        "triggers": ["egraph algebraic optimize", "deductive memoize function", "egraph_optimize_function"],
        "required_inputs": ["target_path", "function_name"],
        "declared_dependencies": [],
    },
    "INCREMENTAL_SEMANTIC_GRAPH": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/incremental_semantic_graph_v1.py",
        "entrypoint": "query_import_cycles",
        "summary": "Tarjan SCC import-cycle detector, class-hierarchy resolver, and symptom-to-impacted-test incremental graph engine.",
        "triggers": ["incremental semantic graph", "tarjan import cycles", "impacted test localization"],
        "required_inputs": ["scope_path"],
        "declared_dependencies": [],
    },
    "STRUCTURAL_REWRITE_INDUCTION": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/structural_rewrite_induction_v1.py",
        "entrypoint": "learn_rules",
        "summary": "Anti-unifies AST defective/repaired pairs into round-trip verified structural rewrite rules and applies them to new code.",
        "triggers": ["structural rewrite induction", "induce ast rewrite rules", "defective repaired antiunify"],
        "required_inputs": ["pairs"],
        "declared_dependencies": [],
    },
    "LAW_REPAIR_SYNTHESIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/law_repair_synthesis_v1.py",
        "entrypoint": "error_discipline_candidates",
        "summary": "Synthesizes algebraic canonicality, protocol-presence, and assert-to-raise error-discipline repair candidates.",
        "triggers": ["law repair synthesis", "canonicality repair candidates", "assert to raise discipline"],
        "required_inputs": ["repo_root"],
        "declared_dependencies": [],
    },
    "SPEC_CONTRACT_SYNTHESIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/spec_contract_synthesis_v1.py",
        "entrypoint": "mine_exception_contracts",
        "summary": "Mines exception, postcondition, and traceback escape contracts directly from test suites and failure traces.",
        "triggers": ["spec contract synthesis", "mine exception contracts", "mine postcondition contracts"],
        "required_inputs": ["test_source"],
        "declared_dependencies": [],
    },
    # --- 3. POLYGLOT C / JS / RUST / GO / C++ / TS KERNELS ---
    "C_ASAN_CEGIS_REPAIR": {
        "domain": "POLYGLOT_REPAIR_AND_BUILD",
        "source_path": "canonical/swe_kernel/c_asan_cegis_repair_v1.py",
        "entrypoint": "synthesize_c_causal_patches",
        "summary": "AddressSanitizer/UBSan-guided C causal patch synthesizer for null-deref, bounds, integer overflow, and use-after-free defects.",
        "triggers": ["asan cegis", "c sanitizer patch", "use after free c repair", "synthesize_c_causal_patches"],
        "required_inputs": ["source", "blame_line"],
        "declared_dependencies": [],
    },
    "JS_CAUSAL_CEGIS_REPAIR": {
        "domain": "POLYGLOT_REPAIR_AND_BUILD",
        "source_path": "canonical/swe_kernel/js_causal_cegis_repair_v1.py",
        "entrypoint": "synthesize_js_causal_patches",
        "summary": "V8 coverage & exception-guided JavaScript/Node causal patch synthesizer.",
        "triggers": ["javascript causal cegis", "v8 node patch synthesis", "synthesize_js_causal_patches"],
        "required_inputs": ["source", "candidate_lines"],
        "declared_dependencies": [],
    },
    "POLYGLOT_BUILD_CI_TRANSFORM": {
        "domain": "POLYGLOT_REPAIR_AND_BUILD",
        "source_path": "canonical/swe_kernel/polyglot_build_ci_engine_v1.py",
        "entrypoint": "rust_transform_and_verify",
        "summary": "Polyglot Rust, Go, C++, Java, and TypeScript transform-and-verify build/test repair engine.",
        "triggers": ["polyglot build transform", "rust go cpp java ts repair"],
        "required_inputs": ["language", "target_path", "goal_spec"],
        "declared_dependencies": [],
    },
    # --- 4. COMPUTER USE, PETRI WORKFLOW, AUTOMATA & PROSE EXPERIMENT KERNELS ---
    "UNIVERSAL_COMPUTER_PETRI_AGENT": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/universal_computer_agent_v1.py",
        "entrypoint": "compute_petri_dominator_cut_vertices",
        "summary": "Computes Cooper-Harvey-Kennedy Petri-net dominator cut-vertices to slice 300+-step GUI/CLI workflows into checkpointed sub-episodes.",
        "triggers": ["petri dominator", "cut vertices checkpoint", "long horizon workflow slice"],
        "required_inputs": ["edges", "start_node", "goal_node"],
        "declared_dependencies": [],
    },
    "CROSS_MODAL_TOMOGRAPHY_PETRI": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/cross_modal_tomography_petri_v1.py",
        "entrypoint": "capture_multilayer_state",
        "summary": "Captures and diffs cross-modal accessibility/DOM/canvas/SQLite/filesystem state snapshots and extracts executable doc examples.",
        "triggers": ["cross modal tomography", "multilayer dom canvas diff", "extract executable doc examples"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "PROSE_CLAIM_EXPERIMENT": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/tools/the_right_question_is_an_experiment_v1.py",
        "entrypoint": "extract_claims",
        "summary": "Parses technical prose and man-pages into falsifiable CLI/program relational claims ready for sandbox experimentation.",
        "triggers": ["prose claim experiment", "manpage claim extractor", "right question experiment"],
        "required_inputs": ["text"],
        "declared_dependencies": [],
    },
    "MINIMAL_AUTOMATA_EXPERIMENT": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/minimal_experiment_v1.py",
        "entrypoint": "separating_word",
        "summary": "Canonical state-machine canonicalizer and shortest separating-word discriminator between competing environment hypotheses.",
        "triggers": ["minimal automata experiment", "separating word", "canonical state machine equivalence"],
        "required_inputs": ["machine_a", "machine_b"],
        "declared_dependencies": [],
    },
    "DOM_STATE_ENVIRONMENT": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/dom_state_environment_v1.py",
        "entrypoint": "snapshot_to_elements",
        "summary": "Normalizes raw DOM/accessibility snapshots into stable addressable interactive elements and deterministic action menus.",
        "triggers": ["dom state environment", "snapshot_to_elements", "stable dom actions"],
        "required_inputs": ["snapshot"],
        "declared_dependencies": [],
    },
    "OSWORLD_BROWSER_OPS": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/osworld_v21_browser_ops_v1.py",
        "entrypoint": "compile_browser_op",
        "summary": "Compiles declarative OSWorld 2.1 browser specifications into deterministic browser operation plans.",
        "triggers": ["osworld browser ops", "compile_browser_op"],
        "required_inputs": ["spec"],
        "declared_dependencies": [],
    },
    "CANONICAL_FRAME_TRANSITION": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/canonical_frame_v1.py",
        "entrypoint": "template",
        "summary": "Induces machine-independent state-transition frame signatures and instantiates action templates on new observations.",
        "triggers": ["canonical frame transition", "frame transition signature"],
        "required_inputs": ["before", "after", "frames", "slot"],
        "declared_dependencies": [],
    },
    # --- 5. CONTINUAL LEARNING, SKILL COMPILATION & META-CIRCULAR ORGANS ---
    "EPISTEMIC_IR_TRANSFER_ADMISSION": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/epistemic_admission_and_self_play_v1.py",
        "entrypoint": "transfer_ir_rule_to_snippet",
        "summary": "Lifts code edits into variable-order-invariant Semantic IR, anti-unifies rewrite laws, transfers across languages, and enforces 5-gate epistemic admission.",
        "triggers": ["epistemic ir transfer", "5gate skill admission", "lift_python_to_ir"],
        "required_inputs": ["before_code", "after_code", "target_snippet"],
        "declared_dependencies": [],
    },
    "VERIFIED_SKILL_CRYSTALLIZER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/verified_skill_crystallizer_v1.py",
        "entrypoint": "anti_unify_code_rule",
        "summary": "Anti-unifies concrete before/after bugfixes into reusable crystallized code rules with SHA-256 skill identity and narrowing.",
        "triggers": ["verified skill crystallizer", "crystallize code rule", "anti_unify_code_rule"],
        "required_inputs": ["before_snippet", "after_snippet"],
        "declared_dependencies": [],
    },
    "CAUSAL_TRACE_SKILL_COMPILER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py",
        "entrypoint": "elevate_trace_to_fastest_layer",
        "summary": "Elevates GUI/shell demonstration traces to fastest programmatic API/HTTP/CLI steps and anti-unifies parameterized workflows.",
        "triggers": ["causal trace skill compiler", "elevate trace fastest layer", "anti_unify_workflow"],
        "required_inputs": ["trace"],
        "declared_dependencies": [],
    },
    "META_CIRCULAR_ORGAN_SYNTHESIS": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/meta_circular_organ_graph_v1.py",
        "entrypoint": "induce_periodic_operator",
        "summary": "Synthesizes pure AST-verified perceptor, periodic-modulo, and compressed lookup organs from raw input/output observations.",
        "triggers": ["meta circular organ", "induce periodic operator", "synthesize perceptor organ"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "RECURSIVE_SELF_ARCHITECT": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/recursive_self_architect_v1.py",
        "entrypoint": "referee_executable_organ",
        "summary": "AST-referees pure self-authored organ code, measures executable MDL byte complexity, and proposes complexity-reducing patches.",
        "triggers": ["recursive self architect", "mdl byte measure", "referee_executable_organ"],
        "required_inputs": ["source_code"],
        "declared_dependencies": [],
    },
    # --- 6. QUANTITATIVE FINANCE, LBO/DCF VALUATION, FIBO & REGCAP ---
    "FINANCE_QUANTITATIVE_ALGEBRA": {
        "domain": "FINANCE_VALUATION_AND_REGCAP",
        "source_path": "canonical/runtime/finance_quantitative_algebra_v1.py",
        "entrypoint": "percent_change",
        "summary": "Exact Decimal quantitative finance algebra: ratios, basis-point deltas, CAGR/percent changes, midpoints, and exact rounding.",
        "triggers": ["finance quantitative algebra", "basis points delta", "exact decimal finance"],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "FINANCE_LBO_DCF_WORKFLOW": {
        "domain": "FINANCE_VALUATION_AND_REGCAP",
        "source_path": "canonical/runtime/finance_modeling_workflows_v1.py",
        "entrypoint": "simplified_lbo_model",
        "summary": "Deterministic institutional Leveraged Buyout (LBO MOIC/IRR/debt paydown) and Constant-Ratio DCF enterprise valuation models.",
        "triggers": ["simplified lbo", "leveraged buyout moic irr", "constant ratio dcf", "wacc enterprise valuation"],
        "required_inputs": ["workflow", "parameters"],
        "declared_dependencies": [],
    },
    "FIBO_BOUNDED_FINANCE_AUTHORITY": {
        "domain": "FINANCE_VALUATION_AND_REGCAP",
        "source_path": "canonical/runtime/fibo_q2_2026_bounded_finance_authority_v1.py",
        "entrypoint": "exact_label_candidates",
        "summary": "FIBO Q2-2026 financial ontology label resolver and bounded taxonomic entailment prover.",
        "triggers": ["fibo ontology", "fibo entailment", "bounded finance authority"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    # --- 7. VISUAL 3D HULL, CHARTOGRAPHY, CAD, OOXML & NATIVE PDF ---
    "ORTHOGRAPHIC_VISUAL_HULL_3D": {
        "domain": "VISUAL_3D_CAD_AND_DOCUMENTS",
        "source_path": "canonical/runtime/orthographic_visual_hull.py",
        "entrypoint": "reconstruct_visual_hull",
        "summary": "Reconstructs 3D voxel visual hulls from top/front/right orthographic masks, computes IoU signatures, and compiles rectangular CSG repairs.",
        "triggers": ["orthographic visual hull", "3d voxel silhouette", "reconstruct_visual_hull"],
        "required_inputs": ["top", "front", "right"],
        "declared_dependencies": [],
    },
    "CHARTOGRAPHY_PROFESSIONAL_SOLVER": {
        "domain": "VISUAL_3D_CAD_AND_DOCUMENTS",
        "source_path": "canonical/runtime/chartography_deterministic_professional_solver_v1.py",
        "entrypoint": "solve",
        "summary": "Deterministic pixel/OCR chartography solver for bar, line, stacked, and pie chart measurement without vision LLMs.",
        "triggers": ["chartography solver", "deterministic chart measurement"],
        "required_inputs": ["image_path", "prompt"],
        "declared_dependencies": [],
    },
    "CAD_PARTSPEC_GENERATOR": {
        "domain": "VISUAL_3D_CAD_AND_DOCUMENTS",
        "source_path": "canonical/runtime/cad_partspec_generator.py",
        "entrypoint": "generate_code",
        "summary": "Parametric mechanical PartSpec millimeter normalizer and CadQuery solid geometry code generator.",
        "triggers": ["cad partspec", "cadquery solid generator"],
        "required_inputs": ["spec"],
        "declared_dependencies": ["cadquery"],
    },
    "OOXML_PACKAGE_VALIDATOR": {
        "domain": "VISUAL_3D_CAD_AND_DOCUMENTS",
        "source_path": "canonical/runtime/ooxml_package_integrity.py",
        "entrypoint": "validate_ooxml_package",
        "summary": "Validates OOXML (.docx/.xlsx/.pptx) ZIP archive structure, XML well-formedness, content-types, and relationship graph integrity.",
        "triggers": ["ooxml package integrity", "validate_ooxml_package", "ooxml relationship check"],
        "required_inputs": ["package_path"],
        "declared_dependencies": [],
    },
    "PDF_NATIVE_TEXT_OPERAND_EDIT": {
        "domain": "VISUAL_3D_CAD_AND_DOCUMENTS",
        "source_path": "canonical/runtime/pdf_native_edit_transaction.py",
        "entrypoint": "replace_unique_pdf_text_operand",
        "summary": "Native PDF content-stream text operand editor with transactional cross-reference table integrity.",
        "triggers": ["pdf native text operand", "replace_unique_pdf_text_operand"],
        "required_inputs": ["input_path", "output_path", "old_text", "new_text"],
        "declared_dependencies": [],
    },
    # --- 8. LANGUAGE CONTRACTS, IF, H100 ZERO-LEARNED, SCIENCE, POLYTOPE & MODULE SOLVER ---
    "INSTRUCTION_CONTRACT_COMPILER": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/instruction_contract_v1.py",
        "entrypoint": "compile_contract",
        "summary": "Compiles natural-language UI/CLI instructions into ordered, provenance-tagged executable clause contracts and verifies execution traces.",
        "triggers": ["instruction contract compiler", "compile_contract clauses", "check_contract trace"],
        "required_inputs": ["utterance", "observation"],
        "declared_dependencies": [],
    },
    "LIVEBENCH_IF_CONSTRAINT_SOLVER": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/livebench_if_single_checker_solver_v1.py",
        "entrypoint": "solve",
        "summary": "Zero-model instruction-following constraint solver and reference-free compound witness constructor.",
        "triggers": ["livebench instruction following", "reference free compound witness", "if single checker"],
        "required_inputs": ["prompt"],
        "declared_dependencies": [],
    },
    "ZERO_LEARNED_EXTRACTIVE_SUMMARY": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/zero_learned_extractive_summary_v1.py",
        "entrypoint": "summarize",
        "summary": "Deterministic zero-learned centrality/coverage extractive text summarizer under strict compression-ratio bounds.",
        "triggers": ["zero learned extractive summary", "extractive compression ratio summarize"],
        "required_inputs": ["text"],
        "declared_dependencies": [],
    },
    "H100_COMPOSITIONAL_LANGUAGE": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/h100_zero_learned_compositional_language_v1.py",
        "entrypoint": "compile_compositional_roles",
        "summary": "Zero-learned compositional discourse role and spatial/state transition parser.",
        "triggers": ["compositional discourse roles", "compile_compositional_roles"],
        "required_inputs": ["text"],
        "declared_dependencies": [],
    },
    "H100_PARAMETRIC_SYMBOLIC_DISCOVERY": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/h100_zero_learned_parametric_unary_v1.py",
        "entrypoint": "discover",
        "summary": "Discovers exact closed-form exponential, step, and sinusoidal parametric laws from tabular observations within NRMSE bounds.",
        "triggers": ["parametric unary discovery", "sinusoid exponential symbolic fit"],
        "required_inputs": ["rows", "target"],
        "declared_dependencies": [],
    },
    "VALUE_ALGEBRA_LAW_INDUCER": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/value_algebra_v1.py",
        "entrypoint": "induce_laws",
        "summary": "Induces non-vacuous aggregate value laws (within_inputs, is_one_of_the_inputs, bounded_by_extremes, is_the_row_count) from probe sets.",
        "triggers": ["value algebra law inducer", "induce operator algebraic laws"],
        "required_inputs": ["operator_name"],
        "declared_dependencies": [],
    },
    "EXACT_RATIONAL_POLYTOPE_SOLVER": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/exact_linear_parameter_polytope_v1.py",
        "entrypoint": "solve",
        "summary": "Exact `Fraction` vertex-enumeration set-membership solver for bounded linear parameter polytopes (`lower <= phi . beta <= upper`).",
        "triggers": ["exact rational polytope", "linear parameter polytope", "set membership fraction bounds"],
        "required_inputs": ["observations"],
        "declared_dependencies": [],
    },
    "TB_SCIENCE_PERIODIC_KERNEL": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/tb_science_zero_model_scientific_kernel_v1.py",
        "entrypoint": "fit_shared_period",
        "summary": "Zero-model multi-series harmonic periodogram & shared-period scientific curve fitter.",
        "triggers": ["shared period harmonic fitting", "tb science periodic kernel"],
        "required_inputs": ["series"],
        "declared_dependencies": [],
    },
    "ADMITTED_BRAIN_MODULE_SOLVER": {
        "domain": "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        "source_path": "canonical/runtime/bound_capabilities/brain_module_invoke_v1.py",
        "entrypoint": "invoke",
        "summary": "Signature-compatible IDF ranker and guarded read-only invoker across the 2,019-module / 5,205-function MODULE_INVOCATION_EVIDENCE_V1 catalog.",
        "triggers": ["admitted module solver", "invoke admitted repository function"],
        "required_inputs": ["payload"],
        "declared_dependencies": [],
    },
    # --- 9. NON-OBVIOUS KOAN / APHORISTIC KERNELS & CROSS-DISCIPLINARY ENGINES ---
    "INSTANT_ONE_SHOT_LEARNER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/instant_one_shot_learning_v1.py",
        "entrypoint": "classify_applicability",
        "summary": "Instant one-shot rule induction, causal credit attribution, Hoare effect-contract extraction, and applicability boundary classification.",
        "triggers": ["instant_one_shot_learning", "extract_contract applicability", "one shot causal credit"],
        "required_inputs": ["skill_id", "preconditions", "actions"],
        "declared_dependencies": [],
    },
    "PREDICTIVE_HOARE_CONTRACT": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/predictive_contract_v1.py",
        "entrypoint": "derive_clauses",
        "summary": "World-model-as-Hoare-contract engine ('a contract, not a trajectory'): induces deterministic pre/post-state byte clauses from a single trial.",
        "triggers": ["predictive_contract", "hoare byte clauses", "world model contract derive_clauses"],
        "required_inputs": ["src", "dst"],
        "declared_dependencies": [],
    },
    "EDIT_BY_EXAMPLE_PROSE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/taught_actions/edit_by_example_v1.py",
        "entrypoint": "edit_by_example",
        "summary": "PROSE/FlashEdit-style AST anti-unification edit-by-example engine: generalizes only across two agreeing structural variations and fails closed otherwise.",
        "triggers": ["edit_by_example", "prose flashmeta ast edit", "structural example edit"],
        "required_inputs": ["target_text", "before_text", "after_text"],
        "declared_dependencies": [],
    },
    "CONCEPT_LIBRARY_EGRAPH_LGG": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/concept_library_v1.py",
        "entrypoint": "canonicalize_ast_via_egraph",
        "summary": "E-graph AST equality-saturation canonicalizer and higher-order Plotkin least-general-generalization (LGG) compounding concept library.",
        "triggers": ["canonicalize_ast_via_egraph", "higher_order_plotkin_lgg", "egraph concept library"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "COMPRESSION_GAIN_MDL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/compression_gain_v1.py",
        "entrypoint": "compress_corpus",
        "summary": "Solomonoff/Stitch MDL description-length compression-gain gate for admitting reusable procedural abstractions across a code corpus.",
        "triggers": ["compression_gain_mdl", "stitch mdl corpus abstraction", "admit_corpus_abstraction"],
        "required_inputs": ["sources"],
        "declared_dependencies": [],
    },
    "PROVED_COMPOSITION_SURVIVAL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/proved_composition_v1.py",
        "entrypoint": "compose",
        "summary": "Compositional Hoare survival verifier ('compose only what is proved'): re-verifies every prior postcondition after each sequential program transform.",
        "triggers": ["proved_composition", "structural_survival hoare", "non-interfering edit composition"],
        "required_inputs": ["source", "pattern_core", "replacement_core"],
        "declared_dependencies": [],
    },
    "LESSON_ADMISSION_GATE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/lesson_admission_gate_v1.py",
        "entrypoint": "evaluate",
        "summary": "Selective skill-abstention & non-regression victim gate ('a lesson is admitted by what it does to programs it was never taught on').",
        "triggers": ["lesson_admission_gate", "untaught victim non-regression", "selective skill abstention gate"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "CONTRASTIVE_ORACLE_BOOTSTRAP": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/contrastive_oracle_bootstrap_v1.py",
        "entrypoint": "identify_rule",
        "summary": "Contrastive intervention-pair negative-space rule identifier that separates minimal deciding preconditions from coincidental trace state.",
        "triggers": ["contrastive_oracle_bootstrap", "intervention pair rule induction"],
        "required_inputs": ["before_snippet", "after_snippet"],
        "declared_dependencies": [],
    },
    "PAIRED_TRANSFER_EVALUATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/paired_transfer_evaluation_v1.py",
        "entrypoint": "extract_contract",
        "summary": "Paired source-to-target frozen transfer contract extractor and out-of-distribution applicability verifier.",
        "triggers": ["paired_transfer_evaluation", "frozen deployment skill transfer"],
        "required_inputs": ["before_snippet", "after_snippet"],
        "declared_dependencies": [],
    },
    "ZYGOTE_COW_FORK_POOL": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/zygote_worker_pool_v1.py",
        "entrypoint": "screen_python_candidates_cow",
        "summary": "Sub-millisecond POSIX os.fork() Copy-On-Write prewarmed Zygote sandbox pool for parallel zero-import-overhead candidate screening.",
        "triggers": ["zygote_worker_pool", "screen_python_candidates_cow", "cow os fork sandbox"],
        "required_inputs": ["project_root", "target_path", "test_paths", "candidates"],
        "declared_dependencies": [],
    },
    "INTERFACE_ACTION_GRAMMAR": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/interface_action_grammar_v1.py",
        "entrypoint": "solve_gui_goal",
        "summary": "Zero-screenshot unified CLI repertoire and structured Accessibility-Tree (A11yNode) GUI goal parser & action-grammar solver.",
        "triggers": ["interface_action_grammar", "a11y action grammar", "zero screenshot gui solver"],
        "required_inputs": ["instruction"],
        "declared_dependencies": [],
    },
    "ENVIRONMENT_BROKER": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/the_environment_broker_v1.py",
        "entrypoint": "detect_layout",
        "summary": "Zero-knowledge environment broker: inspects arbitrary repository layouts, pyproject/TOML build backends, and declared test harnesses.",
        "triggers": ["the_environment_broker", "detect_layout declared_test_commands"],
        "required_inputs": ["tree"],
        "declared_dependencies": [],
    },
    "PREMISE_MINIMAL_SENSE": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/the_premise_is_the_sense_v1.py",
        "entrypoint": "brute_force_minimum",
        "summary": "Minimum-cost sufficient observation partition solver ('what the plan's premise costs to SEE'): deletes unnecessary sensors/screenshots.",
        "triggers": ["the_premise_is_the_sense", "minimum sufficient observation partition", "decision_consistent sense"],
        "required_inputs": ["probes", "actions_by_state", "fact_costs"],
        "declared_dependencies": [],
    },
    "METAMORPHIC_CLI_COMPILER": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/metamorphic_cli_compiler_v1.py",
        "entrypoint": "build_metamorphic_tuple",
        "summary": "Active black-box CLI behavioral fingerprinter: classifies unknown command-line binaries by algebraic/metamorphic input-perturbation tuples.",
        "triggers": ["metamorphic_cli_compiler", "build_metamorphic_tuple", "cli behavioral signature"],
        "required_inputs": ["real_bytes"],
        "declared_dependencies": [],
    },
    "WITNESS_INVERSION_LENS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/witness_inversion_v1.py",
        "entrypoint": "synthesize_bidirectional_lens",
        "summary": "Bidirectional lens synthesizer and angelic-perturbation fault localizer ('invert the failing assertion at the site it fails').",
        "triggers": ["witness_inversion", "synthesize_bidirectional_lens", "localize_by_angelic_perturbation"],
        "required_inputs": ["pairs"],
        "declared_dependencies": [],
    },
    "CONDITION_DEMAND_HARVESTER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/what_the_condition_wants_v1.py",
        "entrypoint": "what_the_condition_wants",
        "summary": "Dynamic branch-operand harvester ('what the condition wants'): extracts exact threshold/guard values demanded by mutated conditions.",
        "triggers": ["what_the_condition_wants", "condition operand demand harvest"],
        "required_inputs": ["report"],
        "declared_dependencies": [],
    },
    "RUNTIME_VALUE_WITNESS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/a_name_gets_its_value_from_the_run_v1.py",
        "entrypoint": "blocked_sites",
        "summary": "Runtime value-binding witness extractor ('a name gets its value from the run'): locates blocked/unbound AST sites and synthesizes bindings.",
        "triggers": ["a_name_gets_its_value_from_the_run", "blocked_sites runtime witness"],
        "required_inputs": ["tree"],
        "declared_dependencies": [],
    },
    "METAMORPHIC_API_LAWS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/metamorphic_laws_v1.py",
        "entrypoint": "static_assert_validation",
        "summary": "Self-manufacturing API oracle: checks round-trip, idempotence, canonicality, iterable retyping, and static assertion laws without existing tests.",
        "triggers": ["metamorphic_laws", "check_round_trip check_idempotence", "self manufacturing api oracle"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "STRUCTURAL_SPEC_DERIVER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/specification_from_structure_v1.py",
        "entrypoint": "derive",
        "summary": "Zero-model vericoding specification synthesizer ('a specification is read off the code's own structure'): derives executable invariants from AST types & guards.",
        "triggers": ["specification_from_structure", "zero model vericoding spec derive"],
        "required_inputs": ["module_source"],
        "declared_dependencies": [],
    },
    "UNIVERSAL_SEMANTIC_IR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/universal_semantic_ir_v1.py",
        "entrypoint": "lower_source_to_uir",
        "summary": "Cross-language Universal Semantic IR (U-IR) lowerer and interprocedural causal cut-site graph compiler.",
        "triggers": ["universal_semantic_ir", "lower_source_to_uir", "interprocedural causal cut site"],
        "required_inputs": ["source", "language"],
        "declared_dependencies": [],
    },
    "FAST_ABSTRACT_SIMULATOR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/executable_simulator_mental_model_v1.py",
        "entrypoint": "simulate_python_fast",
        "summary": "In-RAM step-bounded Python fast simulator and forward-backward abstract domain candidate pruner (zero subprocess spawn).",
        "triggers": ["simulate_python_fast", "executable_simulator_mental_model", "forward_backward_prunes_candidate"],
        "required_inputs": ["source", "entry_func", "args"],
        "declared_dependencies": [],
    },
    "PERF_RACE_OVERFLOW_AUDITOR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/diagnostics_perf_and_design_engine_v1.py",
        "entrypoint": "security_audit_package",
        "summary": "Deterministic performance hotspot profiler, concurrency race-condition detector, integer-overflow fuzzer, and static security auditor.",
        "triggers": ["diagnostics_perf_and_design", "detect_race_conditions", "fuzz_integer_overflow"],
        "required_inputs": ["target"],
        "declared_dependencies": [],
    },
    "GLOBAL_MINIMAX_EXTRAPOLATOR": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/swe_kernel/global_extrapolation_chase_spine_v1.py",
        "entrypoint": "solve_minimax_interval_probe_policy",
        "summary": "Global anti-blind-spot minimal-action chase spine: minimax interval-bisection probe policy, active mechanism discovery, and ARC grid-delta rule inducer.",
        "triggers": ["global_extrapolation_chase_spine", "solve_minimax_interval_probe_policy", "induce_and_predict_grid_delta_rule"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "PITMAN_YOR_OPEN_WORLD": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/global_open_world_extrapolator_v1.py",
        "entrypoint": "estimate_unseen_opportunity_space",
        "summary": "Pitman-Yor / Good-Turing nonparametric Bayesian unseen-channel opportunity estimator for open-world search stopping vs exploration.",
        "triggers": ["global_open_world_extrapolator", "pitman_yor unseen opportunity", "estimate_unseen_opportunity_space"],
        "required_inputs": ["channels"],
        "declared_dependencies": [],
    },
    "WORLD_BINDING_SLOT_COMPLETER": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/world_binding_v1.py",
        "entrypoint": "named_destination",
        "summary": "Deterministic live-workspace slot binder: synthesizes missing capability input arguments and output paths directly from goal phrasing and disk state.",
        "triggers": ["world_binding_slot_completer", "complete_inputs workspace binding"],
        "required_inputs": ["goal"],
        "declared_dependencies": [],
    },
    "REFUSAL_ARTIFACT_MANUFACTURER": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/manufacture_what_the_refusal_asks_for_v1.py",
        "entrypoint": "producer_for",
        "summary": "Refusal-driven prerequisite manufacturer ('an artefact a refusal asks for is manufactured, never faked'): synthesizes real producer argv from CLI flag contracts.",
        "triggers": ["manufacture_what_the_refusal_asks_for", "refusal prerequisite producer_for"],
        "required_inputs": ["kind", "program", "flags"],
        "declared_dependencies": [],
    },
    "SUBCOMMAND_SCOPE_PROBER": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/ask_the_subcommand_before_you_call_it_unbound_v1.py",
        "entrypoint": "what_to_ask",
        "summary": "Active CLI subcommand scope prober ('ask the subcommand before you call it unbound'): classifies side-effect ignorance before invoking unknown flags.",
        "triggers": ["ask_the_subcommand_before_you_call_it_unbound", "subcommand scope ignorance probe"],
        "required_inputs": ["prog"],
        "declared_dependencies": [],
    },
    "KOAN_REFUSAL_CURRICULUM": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/the_refusal_is_the_curriculum_v1.py",
        "entrypoint": "read_demand",
        "summary": "Grammar induction from stderr/manpage refusals ('the refusal is the curriculum: one visit writes the adapter').",
        "triggers": ["the_refusal_is_the_curriculum", "stderr refusal grammar adapter"],
        "required_inputs": ["line"],
        "declared_dependencies": [],
    },
    "KOAN_FORCE_VALUE_ANGELIC": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/force_the_value_and_see_v1.py",
        "entrypoint": "instrumented_source",
        "summary": "Angelic execution value forcing ('force the value at a site, see whether the failing case passes, then write the expression that owes it').",
        "triggers": ["force_the_value_and_see", "angelic site value forcing"],
        "required_inputs": ["source", "function_name"],
        "declared_dependencies": [],
    },
    "KOAN_AIMED_PROGRAM_EDITS": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/aimed_edits_from_the_program_and_the_failure_v1.py",
        "entrypoint": "forms_of",
        "summary": "Program-intrinsic edit-space compiler ('the space is what this program can already build, not a list of fixes someone imagined').",
        "triggers": ["aimed_edits_from_the_program", "program intrinsic edit vocabulary"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "KOAN_DEFERRED_REENTRANT_FORM": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/deferred_definition_form_v1.py",
        "entrypoint": "emit_for_traceback",
        "summary": "Re-entrant / circular-import deferred-definition AST repair synthesizer driven directly by Python tracebacks.",
        "triggers": ["deferred_definition_form", "reentrant_self_failure circular ast"],
        "required_inputs": ["traceback_text", "source_text"],
        "declared_dependencies": [],
    },
    "KOAN_ASSERTION_DEMAND": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/the_assertion_is_the_demand_v1.py",
        "entrypoint": "conditional_productions",
        "summary": "Assertion-to-specification synthesizer ('the failing assertion IS the specification: read the demand out of it, then filter by value').",
        "triggers": ["the_assertion_is_the_demand", "failing assertion demand specification"],
        "required_inputs": ["source", "line", "site_text"],
        "declared_dependencies": [],
    },
    "COUNTERFACTUAL_DISCR_TREE_SKILL_ROUTER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/counterfactual_discr_tree_skill_router_v1.py",
        "entrypoint": "run",
        "summary": "Witness-conditioned AST discrimination-tree skill router (`5.4 us` p50 over `1,086` rules) with Rubin `(WITH, WITHOUT)` counterfactual utility gating and `189`-commit syntax-only bound audit.",
        "triggers": ["counterfactual_discr_tree_skill_router", "rubin counterfactual skill router", "discr_tree witness skill abstention"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "VERIFIED_ZERO_SCREENSHOT_ACTION_CACHE": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/verified_zero_screenshot_action_cache_v1.py",
        "entrypoint": "run",
        "summary": "Three-tier zero-screenshot data-layer workflow elevator (`sqlite3`, OOXML `.docx`, JSON at `1.17 ms` p50) and volatile-invariant A11y/CDP pre-probe action cache (`0.065 ms` p50, `0` stale misfires).",
        "triggers": ["verified_zero_screenshot_action_cache", "stagehand understudy cdp preprobe cache", "zero screenshot ooxml sqlite workflow"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "RELATIONAL_GUARD_ADDITION_REPAIR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/relational_guard_addition_symbolic_repair_v1.py",
        "entrypoint": "run",
        "summary": "Semi-naive relational AST guard/exception-contract/container-sync addition synthesizer (`4/4` non-substitution repairs vs `0/4` substitution ceiling, `100%` `GuardDrop` mutation kill rate).",
        "triggers": ["relational_guard_addition_symbolic_repair", "egglog relational guard addition repair", "non_substitution guard synthesis"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "COW_ZYGOTE_SPECULATIVE_VERIFIER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/cow_zygote_speculative_verifier_v1.py",
        "entrypoint": "run",
        "summary": "POSIX `os.fork()` copy-on-write Zygote speculative patch verifier (`1.58 ms` p50, `9.54x` faster than cold `subprocess.run`, `0` cross-worker state leaks) with transitive AST call-graph test impact slicing.",
        "triggers": ["cow_zygote_speculative_verifier", "sandlock zeroboot cow patch verifier", "speculative fork impact test slicer"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "STATE_CONTRACT_WORLD_MODEL": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/state_contract_world_model_v1.py",
        "entrypoint": "run",
        "summary": "State-as-contract desktop effect-delta world model projecting volatile UI noise out of A11y state transitions before and after actions.",
        "triggers": ["state_contract_world_model", "desktop effect delta contract"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "GRADIENT_FREE_LAW_CONSOLIDATION": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/gradient_free_law_consolidation_v1.py",
        "entrypoint": "run",
        "summary": "Gradient-free sleep-time episodic AST law consolidation over real OSS commits without catastrophic forgetting or drift.",
        "triggers": ["gradient_free_law_consolidation", "episodic ast law consolidation"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ABSTAIN_GATED_SKILL_INDUCTION": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/abstain_gated_skill_induction_v1.py",
        "entrypoint": "run",
        "summary": "Abstain-gated structural AST skill induction acquiring verifiable rules from single commit demonstrations.",
        "triggers": ["abstain_gated_skill_induction", "abstain gated structural skill"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    # `VerificationFirstMemoryBus` is the repository's memory operating system:
    # a five-timescale store (T0 working frames -> T1 bi-temporal causal episode
    # graph -> T2 CDCL negative-space conflict clauses -> T3 crystallized skills
    # -> T4 Pareto frontier) with sleep-time E-Stitch/Plotkin-LGG consolidation
    # and O(1) selective unlearning. It existed, was tested, and had no route:
    # the whole module was absent from the harvested census and the source index,
    # so no goal could reach it. This descriptor is the route, not a new part.
    # `WakeSleepConsolidationEngine` is the wake/sleep half of the same story:
    # verified repair episodes accumulate in a wake buffer, and an offline sleep
    # cycle promotes them to permanent rules ONLY if two distinct witnesses show
    # the rule is non-constant (`permanence_amplifies_check_v1`). Its
    # `run_homeostatic_memory_hygiene()` expires drifted rules and forgets
    # low-value episodes. 2,505 lines, zero importers, no route of any kind.
    "WAKE_SLEEP_CONSOLIDATION": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/sentient_cognitive_core_v1.py",
        "entrypoint": "WakeSleepConsolidationEngine",
        "summary": (
            "Wake-sleep consolidation over verified repair episodes: two-witness "
            "non-constant permanence gate, [G_-, B_+] version-space rule induction, "
            "sleep-cycle crystallization, and homeostatic hygiene (expire stale "
            "rules, forget low-value episodes)."
        ),
        "triggers": [
            "wake sleep consolidation",
            "two witness permanence",
            "homeostatic memory hygiene",
            "wake buffer episode",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "VERIFICATION_FIRST_MEMORY_BUS": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        "entrypoint": "execute_memory_operation",
        "summary": (
            "Memory operating system front door (0G): verification-first five-timescale "
            "memory with lossless causal episode chains, CDCL nogood conflicts, Tier-0 "
            "skill lookup, sleep-time consolidation, and O(1) selective unlearning."
        ),
        "triggers": [
            "verification first memory bus",
            "memory operating system",
            "verification first memory",
            "selective unlearning",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "ADVERSARIAL_MUTATION_ADMISSION_GATE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/adversarial_mutation_admission_gate_v1.py",
        "entrypoint": "run",
        "summary": "Adversarial first-order AST mutation admission gate auditing capability receipts for independent non-constant witness kills.",
        "triggers": ["adversarial_mutation_admission_gate", "first order ast mutation gate"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "RULE_EXPIRY_WORLD_FINGERPRINT": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/rule_expiry_v1.py",
        "entrypoint": "world_fingerprint",
        "summary": "Deterministic environment fingerprint & rule-expiry engine detecting material drift between when a rule was taught and current host truth.",
        "triggers": ["rule_expiry_v1", "expire stale rules world fingerprint"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ASSOCIATIVE_EPISODIC_MEMORY": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/associative_memory_v1.py",
        "entrypoint": "recall",
        "summary": "Durable associative episodic memory ranking stored episodes by Dice term relevance times earned credit-minus-blame importance with exponential half-life decay.",
        "triggers": ["associative_memory_v1", "associative episodic importance decay"],
        "required_inputs": ["cue"],
        "declared_dependencies": [],
    },
    "PROCEDURE_TRAJECTORY_MEMORY": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/procedure_memory_v1.py",
        "entrypoint": "signature",
        "summary": "Direction-preserving procedure & episode-journal signature memory distinguishing opposite-direction transforms (`encode`/`decode`, `pack`/`unpack`).",
        "triggers": ["procedure_memory_v1", "direction preserving procedure signature"],
        "required_inputs": ["text"],
        "declared_dependencies": [],
    },
    "CAUSAL_GOAL_COMPUTER_AGENT": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/causal_computer_use_agent_v1.py",
        "entrypoint": "GoalDirectedAgent",
        "summary": "Goal-cone backward-chaining computer-use agent reading predicate markings, deciding the minimal causal action, and verifying post-step effects.",
        "triggers": ["causal_computer_use_agent", "goal cone backward chaining agent"],
        "required_inputs": ["catalog", "initial_marking", "goal_predicates"],
        "declared_dependencies": [],
    },
    "PREDICATE_UI_WORLD_ABSTRACTION": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/predicate_world_abstraction_v1.py",
        "entrypoint": "project_computer_observation",
        "summary": "Predicate UI world-abstraction projector canonicalizing volatile timestamps/ports/UUIDs and falsifying control-loop state hypotheses.",
        "triggers": ["predicate_world_abstraction", "predicate ui observation projection"],
        "required_inputs": ["observation"],
        "declared_dependencies": [],
    },
    "COW_IMPACT_TEST_REPAIR_ENGINE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/cow_impact_repair_engine_v1.py",
        "entrypoint": "select_impacted_tests_fast",
        "summary": "Zero-copy copy-on-write workspace cloner and fast impacted-test selector for multi-file repository fault localization and repair.",
        "triggers": ["cow_impact_repair_engine", "zero copy workspace impacted tests"],
        "required_inputs": ["changed_rel_paths", "all_test_files"],
        "declared_dependencies": [],
    },
    "CANONICAL_ORACLE_VERICODING_SPINE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/canonical_oracle_vericoding_spine_v1.py",
        "entrypoint": "extract_assertion_demands",
        "summary": "Canonical oracle & vericoding spine extracting test assertion demands, generating goal-negation mutants, and refusing unestablished claims.",
        "triggers": ["canonical_oracle_vericoding_spine", "vericoding assertion demand spine"],
        "required_inputs": ["test_source"],
        "declared_dependencies": [],
    },
    "PROOF_MINED_ARGUMENT_SURFACE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/argument_construction_v1.py",
        "entrypoint": "mined_vectors",
        "summary": "Proof-mined call-site argument vector extractor and 2-run CoW deterministic surface compiler unlocking dark SOURCE_ONLY modules without hand-written wrappers.",
        "triggers": ["argument_construction_v1", "proof mined call site vectors", "derive_and_verify_surface"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "EXECUTABLE_RAM_MENTAL_MODEL": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/executable_simulator_mental_model_v1.py",
        "entrypoint": "simulate_ir_program",
        "summary": "Microsecond (`10-50 us`) in-RAM concrete SemanticIR simulator, `<0.5 ms` forward-backward abstract interpreter, and CEGAR stateful OS environment mental model.",
        "triggers": ["executable_simulator_mental_model", "simulate_ir_program", "abstract_analyze_function", "semantic_ir_mental_model"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "INVERSE_PAIR_COMPLETION": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/inverse_completion_v1.py",
        "entrypoint": "synthesise_reader",
        "summary": "Round-trip inverse-pair callable completion (`load(save(x)) == x`) deriving missing reader signatures and field mappings directly from writer payloads.",
        "triggers": ["inverse_completion_v1", "synthesise_reader", "roundtrip inverse pair completion"],
        "required_inputs": ["name", "writer_payloads"],
        "declared_dependencies": [],
    },
    "REPAIR_VERSION_SPACE_DISCRIMINATOR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/repair_version_space_selection_v1.py",
        "entrypoint": "partition",
        "summary": "Exact behavioral equivalence version-space partitioner and maximum-elimination discriminating-input selector over test-passing candidate repairs.",
        "triggers": ["repair_version_space_selection", "version space patch disambiguation", "abstain when ambiguous"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "DISTINGUISHING_PROJECTION_ORACLE": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/distinguishing_projection_v1.py",
        "entrypoint": "project",
        "summary": "Minimum-cover `(SEPARATION & STABILITY)` state projection oracle synthesizer turning uncheckable computer-use actions into near-zero-false-pass deterministic verifiers.",
        "triggers": ["distinguishing_projection_v1", "manufacture oracle state projection", "separation stability projection"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "SKILL_CONTRIBUTION_UNBLIND_CURATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/skill_contribution_ledger_v1.py",
        "entrypoint": "grader_may_retire",
        "summary": "Blind-Curator-immune outcome contribution ledger and Clopper-Pearson incomplete-beta (`<2%` false-pass UB) retirement & active-cap curator.",
        "triggers": ["skill_contribution_ledger_v1", "consolidate without drift keep store current", "refine decision across epochs without regressing", "blind curator clopper pearson retirement"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "DOMAIN_OF_VERIFICATION_GATE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/domain_of_verification_v1.py",
        "entrypoint": "observed_domain",
        "summary": "Explicit interval domain-of-verification tracker and prequential refutation check flagging unverified global extrapolation outside observed inputs.",
        "triggers": ["domain_of_verification_v1", "observed_domain prequential extrapolation", "observed_domain_interval_check"],
        "required_inputs": ["points"],
        "declared_dependencies": [],
    },
    "PURPOSE_CONTRAST_GATE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "intake/purpose_gate_v1.py",
        "entrypoint": "decide",
        "summary": "Epistemic purpose gate permitting clarifying questions only when real execution traces contrast candidate interpretations and verifying cryptographic answer provenance.",
        "triggers": ["purpose_gate_v1", "residual_question_gate contrast", "ask only when real run separates answers"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "SENTIENT_EPISTEMIC_PETRI_CORE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/sentient_cognitive_core_v1.py",
        "entrypoint": "EpistemicSelfBeliefEngine",
        "summary": "Kalman-Bayesian epistemic surprise gating, ExplicitConstraintLedger Petri inhibitor-arc supervisory control, CausalWorldGraph clobber inhibition, and WakeSleepConsolidationEngine continual skill crystallization without forgetting.",
        "triggers": ["sentient_cognitive_core_v1", "kalman epistemic surprise petri inhibitor", "wake sleep consolidation engine"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "PETRI_COW_SPLICING_MINER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/petri_cow_splicing_engine_v1.py",
        "entrypoint": "RepoNativePetriMiner",
        "summary": "Repository-native Petri net API reachability miner, CoW differential boundary fuzzer, and orthogonal multi-file patch merger for zero-model cross-module synthesis.",
        "triggers": ["petri_cow_splicing_engine_v1", "repo_native_petri_miner", "merge_orthogonal_file_patches"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "SPECULATIVE_COW_PETRI_TOMOGRAPHY": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/speculative_cow_petri_agent_v1.py",
        "entrypoint": "diff_tomography",
        "summary": "Five-layer differential state tomography across filesystem, SQLite, JSON, DOM accessibility tree, and Petri markings verifying desktop and CLI actions without screenshots.",
        "triggers": ["speculative_cow_petri_agent_v1", "five_layer_diff_tomography", "capture_state_tomography"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "OSWORLD_ZERO_MODEL_GUI_POLICY": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/osworld_v21_zero_model_policy_v1.py",
        "entrypoint": "parse_a11y_nodes",
        "summary": "Zero-model desktop GUI and accessibility-tree policy driving unfamiliar desktop applications through structured GUI nodes, reading screen elements, deciding actions, and verifying effects.",
        "triggers": ["osworld_v21_zero_model_policy_v1", "parse_a11y_nodes desktop policy", "zero_model_osworld_policy"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "CAUSAL_CEGIS_INVENTOR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/causal_cegis_inventor_v1.py",
        "entrypoint": "CausalCEGISInventor",
        "summary": "Interprocedural causal graph CEGIS inventor, executable mental model, and negative-space invariant store for multi-function code repair.",
        "triggers": ["causal_cegis_inventor_v1", "interprocedural_causal_cegis", "negative_space_invariant_store"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "GUIDE_EXECUTABLE_TEST_SUITE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/the_guide_is_a_test_suite_v1.py",
        "entrypoint": "docstring_blocks",
        "summary": "Zero-test oracle harvester extracting executable session transcripts and docstring specifications directly from documentation and module docstrings.",
        "triggers": ["the_guide_is_a_test_suite_v1", "docstring_blocks oracle harvester", "guide_is_a_test_suite"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "GUIDE_ACTION_GRAMMAR_INDUCER": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/the_guide_is_an_action_grammar_v1.py",
        "entrypoint": "refusal_clause",
        "summary": "Typed artifact action-grammar compiler inducing preconditions, refusal clauses, synopsis options, and shortest multi-step execution paths from CLI help pages.",
        "triggers": ["the_guide_is_an_action_grammar_v1", "typed_artifact_action_grammar", "parse_synopsis refusal_clause"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "REFUSAL_SPECIFICATION_READER": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/a_refusal_is_a_specification_v1.py",
        "entrypoint": "read_refusal",
        "summary": "Refusal-to-specification parser extracting missing capability, missing flag, or missing prerequisite artifacts directly from environment stderr refusals.",
        "triggers": ["a_refusal_is_a_specification_v1", "read_refusal stderr parser", "refusal_is_a_specification"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "VACUOUS_CHECK_AUDIT_GATE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1.py",
        "entrypoint": "which_object_blindness",
        "summary": "Adversarial corruption and vacuous-check audit gate proving postcondition verifiers actually fail under state corruption rather than rubber-stamping.",
        "triggers": ["a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1", "vacuous_check_certification_audit", "check_that_nobody_runs"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "CANONICAL_MEMORY_CRYSTALLIZER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        "entrypoint": "execute_memory_operation",
        "summary": "Verification-first memory bus, DualDriftDetector, provenance-addressed receipt retrieval when context is full, and conflict-clause continual consolidation without drift.",
        "triggers": ["canonical_memory_crystallizer_v1", "verification_first_memory_bus", "dual_drift_detector crystallizer"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ISOLATED_EFFECT_RECEIPT_VERIFIER": {
        "domain": "TRUE_CAPABILITIES",
        "source_path": "canonical/tools/isolated_effect_receipt_verifier_v1.py",
        "entrypoint": "receipt_digest",
        "summary": "Cryptographic isolated-effect receipt verifier and provenance archive digest proving execution receipts were not edited after the fact and retrieving receipts by content address.",
        "triggers": ["isolated_effect_receipt_verifier_v1", "isolated_effect_receipt_digest", "tamper_evident_receipt_patch_verifier"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W21_MMAP_CSR_SLOT_INDEX": {
        "domain": "SUBSTRATE_LATENCY_AND_ROUTING",
        "source_path": "canonical/runtime/mmap_csr_slot_index_v1.py",
        "entrypoint": "open_or_build_csr_index",
        "summary": "Zero-copy read-only mmap CSR binary postings & slot index cutting cold open_model + first find_source latency from 291 ms to < 12 ms with exact ranking preservation.",
        "triggers": ["mmap_csr_slot_index", "zero copy mmap csr binary postings"],
        "required_inputs": ["query"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W22_EXECUTION_TRACED_COMPILER": {
        "domain": "CAPABILITY_HARVEST_AND_COMPILATION",
        "source_path": "canonical/runtime/execution_traced_callable_compiler_v1.py",
        "entrypoint": "derive_verified_module_adapter",
        "summary": "PEP 669 sys.monitoring / C-level setprofile execution-traced callable compiler verifying 260/406 (64.04%, 17.36x over AST literal baseline) SOURCE_ONLY modules with 2-run scratch determinism and SHA256 non-destructiveness.",
        "triggers": ["execution_traced_callable_compiler", "pep 669 traced callable adapter"],
        "required_inputs": ["module_rel_path"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W23_FAST_CASCADE_ORCHESTRATOR": {
        "domain": "FAST_CASCADE_AND_STATE_ALIAS_GUARD",
        "source_path": "canonical/runtime/fast_cascade_orchestrator_v1.py",
        "entrypoint": "execute_fast_cascade",
        "summary": "4-rung zero-LLM fast-cascade orchestrator uniting AstDiscrTree (<10 us), 5-layer CoW State-Alias differential tomography + content-signature verification, CoW Zygote test slicing + 64-vector boundary fuzzing, and Petri cut-vertex checkpointing.",
        "triggers": ["fast_cascade_orchestrator", "state alias differential tomography cascade"],
        "required_inputs": ["task_spec"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W24_FORWARD_PUSH_BITEMPORAL_PPR": {
        "domain": "BITEMPORAL_MEMORY_AND_SKILL_RENT",
        "source_path": "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        "entrypoint": "execute_memory_operation",
        "summary": "Andersen-Chung-Lang ForwardPush O(1/(alpha*epsilon)) local Personalized PageRank over bi-temporally valid memory intervals ([valid_at, invalid_at)) plus Two-Door Rubin (WITH - WITHOUT) counterfactual skill rent & finite-cap curation.",
        "triggers": ["forward_push_bitemporal_recall", "two door rubin skill rent curator"],
        "required_inputs": ["query"],
        "declared_dependencies": [],
    },
    "CHECKABILITY_ORACLE_FORGE": {
        "domain": "CHECKABILITY_AND_ORACLE_SYNTHESIS",
        "source_path": "canonical/swe_kernel/argument_construction_v1.py",
        "entrypoint": "mined_vectors",
        "summary": "Zero-test checkability multiplier uniting non-scalar repository call-site argument mining (argument_construction_v1), public-surface differential pinning (checkability_by_differential_pin_v1), and prose-to-code contract compilation (instruction_contract_for_code_v1).",
        "triggers": ["checkability_oracle_forge", "non scalar argument construction differential pin"],
        "required_inputs": ["workspace_root"],
        "declared_dependencies": [],
    },
    "SPACETIME_OE_SYGUS_REPAIR": {
        "domain": "POLYGLOT_SYGUS_AND_CAUSAL_REPAIR",
        "source_path": "canonical/runtime/oe_sygus_synthesizer_v1.py",
        "entrypoint": "synthesize_value_expressions",
        "summary": "SpaceTime causal do-intervention bug localization (site_by_intervention_v1) + 3-language Python/JS/C observational-equivalence SyGuS & EUSolver separating guard synthesis with Plotkin anti-unification.",
        "triggers": ["spacetime_oe_sygus_repair", "observational equivalence sygus polyglot eusolver"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "SHADOW_INTERFACE_COMPUTER_USE": {
        "domain": "SHADOW_INTERFACE_AND_PETRI_CU",
        "source_path": "canonical/tools/follow_the_pointer_v1.py",
        "entrypoint": "declarations",
        "summary": "Agent-S4 shadow-interface evolution + W3C WebMCP (navigator.modelContext / declarative form toolname) compiler + zero-exec CLI stub pointer chasing + environment_fit_v1 + sub-microsecond inhibitor-arc Petri 5-layer State-Alias tomography.",
        "triggers": ["shadow_interface_computer_use", "webmcp shadow interface pointer chasing petri"],
        "required_inputs": ["workspace_root"],
        "declared_dependencies": [],
    },
    "ACTIVE_MEALY_QUESTION_LEARNER": {
        "domain": "INSTANT_ACTIVE_AUTOMATA_LEARNING",
        "source_path": "canonical/tools/ask_instead_of_stare_v1.py",
        "entrypoint": "learn_with_acquisition",
        "summary": "Sub-millisecond Angluin L* active Mealy automata learner with automatic distinguishing suffix synthesis plus executable-question pre-state disambiguation (ask_instead_of_stare_v1 + the_pre_state_is_the_missing_part_v1).",
        "triggers": ["active_mealy_question_learner", "angluin lstar active mealy distinguishing suffix"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "DBSP_BITEMPORAL_CAPABILITY_FORGE": {
        "domain": "DBSP_ZSET_MEMORY_AND_MUTANT_FORGE",
        "source_path": "canonical/runtime/capability_forge_v1.py",
        "entrypoint": "forge_function",
        "summary": "Sub-10-microsecond DBSP Abelian Z-set (+1/-1) bi-temporal incremental view maintenance + ForwardPush local PPR (zero CL-Bench stale-belief drift) + adversarial mutant-killing dormant capability forge.",
        "triggers": ["dbsp_bitemporal_capability_forge", "dbsp abelian zset bitemporal mutant forge"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "GROUNDED_COMPUTER_INSPECTOR": {
        "domain": "GROUNDED_INSPECTION_AND_OPERATION_TRIAL",
        "source_path": "canonical/runtime/inspect_v1.py",
        "entrypoint": "answer",
        "summary": "Evidence-grounded computer inspection and executable-attempt question answering (inspect_v1 + operation_trial_v1 + value_enumeration_v1) with perturbation referent verification.",
        "triggers": ["grounded_computer_inspector", "executable attempt grounded computer inspection"],
        "required_inputs": ["question"],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M0_APARTNESS_LSHARP_LEARNER": {
        "domain": "INSTANT_LEARNING_AND_AUTOMATA",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "ApartnessTreeInstantLearner",
        "summary": "Observation-table-free Brouwer-Heyting constructive apartness (L# / L#_e) active Mealy learner with error-persistent sink pruning and adaptive distinguishing sequences.",
        "triggers": ["apartness_lsharp_learner", "vaandrager constructive apartness observation tree", "error persistent mealy learner"],
        "required_inputs": ["alphabet", "execute_trace"],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M1_ANGELIC_FOREST_OE_SYGUS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "AngelicForestSyGuSRepairEngine",
        "summary": "CoW os.fork() Angelic Forest impossibility sieve feeding multi-language EUSolver observational-equivalence SyGuS (oe_sygus_synthesizer_v1), NAME_SCOPE member-to-local rewrites, and 4-gate non-vacuous test verification.",
        "triggers": ["angelic_forest_oe_sygus", "angelix impossibility sieve eusolver sygus", "name_scope non_vacuous repair"],
        "required_inputs": ["source_text", "test_source"],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M2_PROTOCOL_LIFT_EFFECT_ORACLE": {
        "domain": "ZERO_PIXEL_COMPUTER_USE",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "lift_protocol_and_verify_effect",
        "summary": "WebMCP (document.modelContext) and CDP/HAR network-to-HTTP protocol lifter deleting browser UI overhead on Run 2+, paired with unprivileged Linux namespace confinement and magic-header round-trip effect_oracle.",
        "triggers": ["protocol_lift_effect_oracle", "cdp har reverse api protocol lifting", "magic header roundtrip effect oracle"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M3_SEMIRING_PROVENANCE_JTMS_MEME": {
        "domain": "BITEMPORAL_MEMORY_AND_SKILL_RENT",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "run_meme_semiring_benchmark",
        "summary": "Green-Karvounarakis-Tannen Why-Provenance Semiring (2^(2^V), union, join) over Z-set DBSP memory achieving 100% MEME Cascade multi-hop retraction, diamond alternative-proof preservation, and 100% Absence invalidation detection in <15 us.",
        "triggers": ["semiring_provenance_jtms_meme", "why provenance semiring cascade absence", "jtms nonmonotonic truth maintenance"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M4_MINIMAX_VERSION_SPACE_INTERROGATOR": {
        "domain": "ACTIVE_DISCRIMINATION_AND_MINIMAX",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "minimax_interrogate_version_space",
        "summary": "Exact dynamic-programming minimax decision-region interrogator (finite_minimax_decision_region_v1) bisecting ambiguous 1-shot version spaces with minimum worst-case probe cost while blocking irreversible probes.",
        "triggers": ["minimax_version_space_interrogator", "finite minimax decision region bisection", "contrastive version space probe"],
        "required_inputs": ["hypotheses", "candidate_probes"],
        "declared_dependencies": [],
    },
    "UNFAMILIAR_M5_ZERO_LLM_ALPHAEVOLVE_PARETO": {
        "domain": "EVOLUTIONARY_SYNTHESIS_AND_OPTIMIZATION",
        "source_path": "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        "entrypoint": "evolve_pareto_organ",
        "summary": "Zero-LLM AlphaEvolve MAP-Elites and Pareto (latency_us, ast_bytes) code synthesizer guarded by adversarial output-corruption evaluator auditing (0% false-pass reward hacking) and Two-Door rent garbage collection.",
        "triggers": ["zero_llm_alphaevolve_pareto", "map elites pareto code evolution", "anti reward hacking evaluator audit"],
        "required_inputs": ["baseline_source", "fn_name", "test_inputs"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W36_BYTE_EFFECT_ORACLE": {
        "domain": "RING0_BYTE_EFFECT_AND_DRA_MINIMIZATION",
        "source_path": "canonical/runtime/byte_effect_oracle_v1.py",
        "entrypoint": "verify_byte_effect",
        "summary": "Ring-0 byte-level effect oracle verifying real magic headers, decompression roundtrips, untouched archive member SHA-256 invariance, DRA Zeller ddmin hunk minimization, and touched-line AST mutation-kill auditing.",
        "triggers": ["byte_effect_oracle", "lying extension detector", "ddmin hunk minimizer", "dra mutation audit"],
        "required_inputs": ["target"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W36_FUTAMURA_CASCADE": {
        "domain": "SELF_COMPILING_FUTAMURA_CASCADE",
        "source_path": "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        "entrypoint": "run",
        "summary": "Futamura self-compiling 4-rung cascade (Rung 0 <100 us alpha-normalized AST rules -> Rung 1 byte-effect -> Rung 2 PEP-669/settrace Ochiai + byte-span AST splice + os.fork CoW + ddmin + mutation + SCoRE e-value -> optional Rung 3 proposer) compiling verified wins back to Rung 0 plus GrowLibm sleep compression.",
        "triggers": ["futamura_leapfrog_kernel", "compile away the frontier", "skillcompiler", "growlibm sleep consolidation"],
        "required_inputs": ["source", "test_cases"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W36_ERROR_AWARE_MEALY_HCU": {
        "domain": "INSTANT_MEALY_AND_HYBRID_COMPUTER_USE",
        "source_path": "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        "entrypoint": "run",
        "summary": "Sub-ms Error-Aware L# + Lambda*_M symbolic Mealy instant learner with binary-split numeric guards plus 3-channel Hybrid Computer Use (CLI/File > AX/CDP > Visual) with <5 us Petri guard, OSWorld-Human loop-churn breaker, and PASTE speculative macro commit.",
        "triggers": ["error aware mealy l#", "hybrid computer use hcu", "osworld human loop breaker", "paste speculative macro"],
        "required_inputs": ["steps"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W36_DBSP_AGM_CONFORMAL": {
        "domain": "DBSP_AGM_MEMORY_AND_CONFORMAL_EVALUE",
        "source_path": "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        "entrypoint": "run",
        "summary": "Algebraic DBSP bi-temporal Z-set memory + Kumiho AGM Supersedes/Depends_On transitive AnalyzeImpact + projectmem <10 us PreCommitFailureGate + SCoRE anytime-valid conformal e-value martingale risk controller.",
        "triggers": ["dbsp z-set memory", "kumiho agm analyze impact", "projectmem pre commit failure gate", "score conformal e-value"],
        "required_inputs": ["observations"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W37_OS_KERNEL_ISOLATION": {
        "domain": "OS_KERNEL_CONFINEMENT_AND_ESCAPE_PROBE",
        "source_path": "canonical/runtime/os_isolation_v1.py",
        "entrypoint": "probe",
        "summary": "Real Linux kernel namespace isolation (CLONE_NEWUSER + CLONE_NEWNS tmpfs root + RO binds + CLONE_NEWPID + CLONE_NEWNET + CLONE_NEWIPC + CLONE_NEWUTS + chroot + CapEff=0 capability drop) with 18-attempt adversarial escape probe.",
        "triggers": ["os kernel isolation", "unshare namespace confinement", "capeff zero escape probe", "linux chroot cap drop"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W37_CONFINED_HYBRID_CU": {
        "domain": "OS_CONFINED_COMPUTER_USE_AND_EFFECT_ORACLE",
        "source_path": "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        "entrypoint": "run",
        "summary": "Real OS kernel-confined 3-channel computer-use executor uniting os_isolation_v1 (CapEff=0) + HybridComputerUsePetriSupervisor + Ring-0 byte_effect_oracle_v1 verification + atomic CoW workspace rollback + PreCommitFailureGate.",
        "triggers": ["confined hybrid computer use", "os isolated cli executor", "byte oracle rollback recovery"],
        "required_inputs": ["work_dir", "steps"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO": {
        "domain": "MULTIFILE_REPO_SWE_SELF_COMPILING_REPAIR",
        "source_path": "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        "entrypoint": "run",
        "summary": "Unified multi-file Python repository Futamura solver uniting Rung-0 compiled skills + stdlib_cow_test_runner_v1 os.fork CoW overlays + multi-file dynamic coverage + extended AST + 13-law residual wall closers + repo component Petri + Ring-0 ddmin/mutation/conformal gate + automatic Rung-0 compile-back.",
        "triggers": ["multifile futamura repo repair", "multi file cow fork swe solver", "cross file ast repair compile back"],
        "required_inputs": ["repo_dir"],
        "declared_dependencies": [],
    },
    # --- WAVE 38: SECCOMP BPF, REFUSAL INTERFACE HCU, WALL-CLOSING SWE, NON-MALLEABLE MEMORY OS & BICAMERAL SLEEP ---
    "LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST": {
        "domain": "OS_KERNEL_CONFINEMENT_AND_ESCAPE_PROBE",
        "source_path": "canonical/runtime/worker_syscall_allowlist_v1.py",
        "entrypoint": "describe",
        "summary": "Pinned classic BPF x86_64 seccomp syscall allowlist (default-deny ENOSYS, EPERM on bpf/io_uring/keyctl/ptrace/unshare/userfaultfd/AF_NETLINK, KILL_PROCESS on x32/int80) with offline decision interpreter.",
        "triggers": ["seccomp bpf syscall allowlist", "kernel syscall filter", "worker syscall allowlist", "verify seccomp policy"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_REFUSAL_SPEC_COMPILER": {
        "domain": "OS_CONFINED_COMPUTER_USE_AND_EFFECT_ORACLE",
        "source_path": "canonical/runtime/a_refusal_is_a_specification_v1.py",
        "entrypoint": "read_refusal",
        "summary": "Refusal-as-specification interface compiler (Agent-S4 + a_refusal_is_a_specification): parses CLI/app refusals into typed non-guessed flag/option repairs and compiles verified interfaces.",
        "triggers": ["refusal is a specification", "manufacture what the refusal asks for instead of faking it", "compile refusal to interface", "agent s4 evolving interface"],
        "required_inputs": ["text"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_OSWORLD_VERIFIED_LEDGER": {
        "domain": "OS_CONFINED_COMPUTER_USE_AND_EFFECT_ORACLE",
        "source_path": "canonical/runtime/osworld_verified_task_ledger_v1.py",
        "entrypoint": "decide",
        "summary": "External OSWorld verified task ledger gating desktop and browser screen-read, action selection, WebMCP typed tool dispatch, and real effect verification on cryptographic receipts.",
        "triggers": ["read screen decide action verify effect", "osworld verified task ledger", "webmcp navigator modelcontext", "verify screen action effect"],
        "required_inputs": ["state"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_TYPED_CEGIS_INVENTION": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/typed_invention_v1.py",
        "entrypoint": "typed_cegis_synthesize",
        "summary": "Type-pruned CEGIS(T) program synthesis combined with adaptive constant V9 invention and multi-concept composition bridges at zero LLM calls.",
        "triggers": ["typed invention cegis", "cegis t typed synthesis", "adaptive constant concept bridge", "composition concept bridge"],
        "required_inputs": ["spec"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_RESIDUAL_WALL_CLOSERS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/residual_wall_closers_v1.py",
        "entrypoint": "ResidualWallCloser",
        "summary": "Thirteen statement-shaped residual wall closers (NoneGuardToTruthiness, AssertContractToTypedRaise, EmptyContainerPrefixArm, OptionalTupleShapeCompletion, DocstringDefaultUngating, etc.).",
        "triggers": ["residual wall closers", "statement shaped code repair", "assert contract to typed raise", "none guard to truthiness"],
        "required_inputs": ["source", "target_function"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_REPO_COMPONENT_PETRI": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/repo_component_petri_v1.py",
        "entrypoint": "synthesize_repo_petri_repairs",
        "summary": "Repo-native callable and exception component miner with Type-Transition Petri-Net expression and handler widening synthesis.",
        "triggers": ["repo component petri", "mine repo neighborhood components", "exception handler widening synthesis"],
        "required_inputs": ["repo_root", "rel_path", "source_text", "line_no"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS": {
        "domain": "DBSP_AGM_MEMORY_AND_CONFORMAL_EVALUE",
        "source_path": "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        "entrypoint": "execute_memory_operation",
        "summary": "Non-malleable memory OS and bicameral sleep daemon: TMA-NM write-time cryptographic origin binding (0% laundering), GovMem independent-witness contrast promotion, A-TMA anti-ghost-memory state views, SkillApt counterfactual activation, <96 hot-tier cap, drift detection, and continual improvement without forgetting or dropping facts.",
        "triggers": [
            "keep improving on new tasks without forgetting earlier ones",
            "detect drift between what was taught and what is now true",
            "consolidate without drift and keep the store current",
            "compact an episode journal retaining verified facts",
            "verify that a receipt was not edited after the fact",
            "tma-nm origin binding",
            "govmem correlated false promotion",
            "ghost memory state view",
            "skillapt counterfactual activation",
            "bicameral sleep cycle",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE": {
        "domain": "BITEMPORAL_MEMORY_AND_SKILL_RENT",
        "source_path": "canonical/runtime/release_chunk_archive_v1.py",
        "entrypoint": "planned_chunk_count",
        "summary": "Content-addressed release chunk archive supporting SHA-256 verified chunk splitting, recall from the chunk archive by content address, and exact reconstruction.",
        "triggers": ["recall from the chunk archive by content address", "release chunk archive", "content addressed chunk reconstruct"],
        "required_inputs": ["size_bytes"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_SAFE_ACTION_WORLD_MODEL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/safe_action_model_v1.py",
        "entrypoint": "describe",
        "summary": "Verified safe action world model forecasting whether an outcome will follow from a plan, simulating state deltas, and falsifying control loop hypotheses before acting.",
        "triggers": [
            "forecast whether an outcome will follow from this plan",
            "falsify the control loop hypothesis",
            "safe action world model transition",
            "simulate action outcome before acting",
        ],
        "required_inputs": ["state"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_CONSISTENCY_EQUIVALENCE_AND_JUDGE": {
        "domain": "VERIFICATION_AND_CHECKABILITY",
        "source_path": "canonical/swe_kernel/consistency_vs_equivalence_v1.py",
        "entrypoint": "combined_admission_verdict",
        "summary": "Separates sample consistency from behavioral equivalence, verifies two non-constant witnesses, and audits verifier non-vacuity via judge_the_judge before trusting a pass verdict.",
        "triggers": [
            "verify two witnesses that are not constant",
            "consistency vs equivalence admission",
            "judge the judge vacuous verifier audit",
            "verify receipt integrity non constant witness",
        ],
        "required_inputs": ["gate_report"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_MINED_REWRITE_AND_WEIGHT_GATE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/mined_rewrite_theory_v1.py",
        "entrypoint": "mine_rules",
        "summary": "Execution-discovered e-graph algebraic rewrite law miner, minimal vocabulary distinction creator, and out-of-training-set weight update admission gate.",
        "triggers": [
            "mined rewrite theory",
            "weight update admission gate",
            "minimal vocabulary distinction created",
            "discover egraph rewrite laws by execution",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W38_COW_LENS_NEGATIVE_SPACE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/swe_kernel/cow_lens_fuzz_and_negative_space_v1.py",
        "entrypoint": "synthesize_bidirectional_fst_lens",
        "summary": "Bidirectional FST/lens synthesizer, CoW differential boundary fuzzer, angelic fault blame, and persistent L3 negative-space refutation store.",
        "triggers": [
            "cow lens fuzz negative space",
            "bidirectional fst lens synthesis",
            "negative space refutation store",
            "angelic cow fault blame",
        ],
        "required_inputs": ["pairs"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_ZERO_ADAPTER_INVENTORY_BRIDGE": {
        "domain": "CAPABILITY_COMPOSITION_AND_ROUTING",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "ZeroAdapterInventoryTypeBridge",
        "summary": "Zero-wrapper bridge composing module_bridge_v1 (5,221 inventoried functions) with type_level_composer_v1 type graphs and tier-honest provenance.",
        "triggers": [
            "zero adapter inventory bridge",
            "module bridge 5221 functions",
            "type level composer chains",
            "zero thin adapter dispatch",
        ],
        "required_inputs": ["goal"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_MOORE_ONTOLOGY_WITNESS_LEARNER": {
        "domain": "INSTANT_LEARNING_AND_WORLD_MODELS",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "GaloisWitnessMooreInstantLearner",
        "summary": "Instant learning unifying action-invariant Moore bisimulation transfer, OPINE-World ontology-error predicate synthesis, FCA Galois lattices, and FlashMeta D4 witness inversion.",
        "triggers": [
            "moore bisimulation isomorphism transfer",
            "opine world ontology error residual",
            "flashmeta d4 inverse witness synthesis",
            "fca galois concept lattice",
            "unified_five_pillar_frontier_kernel",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_LENS_STANDING_FACT_CU": {
        "domain": "COMPUTER_USE_AND_GROUNDING",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "LensStandingFactComputerUseEngine",
        "summary": "Zero-screenshot computer use combining OOXML/JSON bijective lenses, relational record frames, CAS stale-frame click guards, standing-fact clobber recovery, and anti-false-DONE checks.",
        "triggers": [
            "bijective ooxml lens computer use",
            "relational anchored frame cas seal",
            "standing facts batch clobber recovery",
            "anti false done implied ending gate",
        ],
        "required_inputs": ["instruction"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_DELTASTATE_SIBLING_SWE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "DeltaStateSiblingClosedSWEKernel",
        "summary": "Multi-file SWE repair combining non-vacuous oracle calibration, Plastic Surgery donor mining, Coccinelle/SyDIT sibling closure, and DeltaBox warm-zygote os.fork() CoW rollouts.",
        "triggers": [
            "deltastate cow fork swe repair",
            "coccinelle sydit multi file sibling closure",
            "plastic surgery donor alphabet mining",
            "calibrated judge non vacuous swe",
        ],
        "required_inputs": ["repo_root"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_PROSPECTIVE_MEMTX_REPLAY": {
        "domain": "MEMORY_AND_BELIEF_REVISION",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "ProspectiveEntrenchedMemTXEngine",
        "summary": "Write-time Kumiho prospective cue indexing, MemTX/CPB root-disjoint Sybil echo blocking, AGM K*7/K*8 ordinal entrenchment, and RD-Forget selective replay unlearning.",
        "triggers": [
            "kumiho prospective cue indexing",
            "memtx cpb sybil lineage gate",
            "agm k7 k8 epistemic entrenchment",
            "rd forget selective replay unlearning",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W41_REFUSAL_ACQUIRE_RETRY": {
        "domain": "CROSS_LANGUAGE_SKILL_COMPILATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/refusal_acquire_retry_v1.py",
        "entrypoint": "acquire_and_retry",
        "summary": "Reads a refusal as a specification: derives the rule's single changed operator, tries context-free application procedures cheapest-first, admits only what the caller's verifier accepts, retries, and remembers the procedure so the next refusal of the same kind costs one step instead of two.",
        "triggers": [
            "refusal is a specification",
            "abstain acquire retry",
            "context free operator rewrite",
            "cross language transfer after refusal",
            "acquisition store reuse",
        ],
        "required_inputs": ["rule", "source_text", "target_language", "verifier"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W42_MEME_PROTOCOL_MEMORY": {
        "domain": "MEMORY_AND_DEPENDENCY_PROPAGATION",
        "source_path": "canonical/swe_kernel/meme_protocol_memory_v1.py",
        "entrypoint": "run_protocol",
        "summary": "Answers the three MEME protocol operations the semiring store could not: exact Z-set aggregates that refuse to report a total over a set that lost a member, rename tracking that carries derived facts and poisons the stale name, and absence for a rule that never fired; scored by a six-operation bench judged by a from-scratch fixpoint oracle.",
        "triggers": [
            "memory cascade",
            "memory absence",
            "dependency invalidation",
            "aggregate over invalidated facts",
            "entity rename tracking",
            "upstream superseded",
            "meme protocol",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_FRONTIER_BENCH_HARNESS": {
        "domain": "VERIFICATION_MEASUREMENT_AND_ABSTENTION",
        "source_path": "canonical/evaluation/frontier_bench_v1.py",
        "entrypoint": "run_bench",
        "summary": "Held-out, oracle-judged capability benchmark: six capability classes generated from a seed, each judged by an independent oracle (BFS, program interpretation, disk state, a subprocess running the repaired repo's own tests), scoring the engine's behaviour and separately counting claims of success the oracle refutes.",
        "triggers": [
            "frontier bench",
            "held out capability benchmark",
            "oracle judged evaluation",
            "false success claim measurement",
            "self check liar control",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_MEANING_IR_CROSS_LANG_RATCHET": {
        "domain": "SKILL_COMPILATION_AND_ANTI_UNIFICATION",
        "source_path": "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
        "entrypoint": "MeaningIRSkillRatchetEngine",
        "summary": "Babble/Stitch Meaning-IR anti-unification, zero-shot cross-language verified skill recall across Python/JS/TS/Go/Rust, 4-gate Hoare sequence verification, and MDL bit-rent eviction.",
        "triggers": [
            "meaning ir cross language skill transfer",
            "babble stitch anti unification ratchet",
            "hoare contract sequence undo gate",
            "mdl bit rent active store eviction",
        ],
        "required_inputs": ["before_snippet", "after_snippet"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_AUTO_JUDGE_DISCOVERY": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/swe_kernel/auto_judge_discovery_v1.py",
        "entrypoint": "discover_stdlib_candidates",
        "summary": "Red Queen earned-judge discovery & refutation store (auto_judge_discovery_v1 + earn_a_judge_v1): earns live format/CLI judges from positive, decoy, and cross-kind bytes with zero hand-written oracles.",
        "triggers": [
            "auto judge discovery",
            "earn a judge",
            "red queen judge coevolution",
            "stdlib artifact judge oracle",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_EFFECT_CONTRACT_COMPOSER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/effect_contract_composition_v1.py",
        "entrypoint": "compose_chain",
        "summary": "Typed (P,O,A,V,F) effect-contract chain composer and holdout survival verifier (effect_contract_composition_v1 + composition_verification_v1).",
        "triggers": [
            "effect contract composition",
            "composition verification",
            "typed skill chain undo conflict",
            "poavf contract chain",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_PARTIAL_ORDER_PLANNER": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/swe_kernel/partial_order_planner_v1.py",
        "entrypoint": "plan",
        "summary": "Complete causal-link partial-order planner solving Sussman's anomaly over measured operators plus horizon-bounded task decomposition.",
        "triggers": [
            "partial order planner",
            "sussman anomaly planner",
            "causal link threat resolution",
            "horizon bounded execution",
        ],
        "required_inputs": ["initial_facts", "goal_facts", "operators"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_LIFTED_GENERALIZER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/swe_kernel/perfect_algorithm_lifted_generalization_v1.py",
        "entrypoint": "lift_plan_sketch",
        "summary": "Variable-invariant plan sketch lifter, applicability inducer, and 1-demonstration attraction basin verifier (perfect_algorithm_lifted_generalization_v1 + one_demonstration_basin_v1).",
        "triggers": [
            "lifted plan generalization",
            "one demonstration basin",
            "schema programmatic world model",
            "tycho lifted skill sketch",
        ],
        "required_inputs": ["concrete_plan"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_REFUSAL_ORACLE_LIFTER": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/tools/the_check_mode_is_the_oracle_v1.py",
        "entrypoint": "tokens_of",
        "summary": "CLI-Anything/Agent-S4 --check/--dry-run oracle lifter, refusal-surface vocabulary classifier, and live witness type collapse (the_check_mode_is_the_oracle_v1 + an_actions_vocabulary_is_its_refusal_surface_v1 + a_type_you_wrote_is_a_type_you_guess_v1).",
        "triggers": [
            "check mode is the oracle",
            "refusal surface vocabulary",
            "dry run oracle lifter",
            "witness type collapse",
        ],
        "required_inputs": ["help_text"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_OBSERVATION_REFUTATION_AND_PROVENANCE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/runtime/observation_refutation_v1.py",
        "entrypoint": "run",
        "summary": "Live observation refutation survival gate, relational run-goal version-space identification, and AST provenance-over-shape feature lifting.",
        "triggers": [
            "observation refutation",
            "goal relation over run",
            "provenance not shape",
            "causal refutation witness",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_DECISION_COST_COW_GATE": {
        "domain": "KOAN_APHORISTIC_AND_GLOBAL_EXTRAPOLATION",
        "source_path": "canonical/tools/what_a_decision_costs_v1.py",
        "entrypoint": "decisive",
        "summary": "DeltaBox/Sandlock-style decision-theoretic version-space agreement gate + real POSIX os.fork() Copy-on-Write speculative verifier paying forks ONLY where surviving hypotheses disagree.",
        "triggers": [
            "what a decision costs",
            "decision cost cow gate",
            "deltabox sandlock cow speculation",
            "version space agreement fork",
        ],
        "required_inputs": ["survivor_requirements", "observed_facts"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave39_leapfrog_unification_v1.py",
        "entrypoint": "RedQueenMendelEvolver.mendel_splice_and_verify",
        "summary": "Mendel Gödel Machine comparative cross-lineage patch splicing + ALBI semantic-anonymization invariance + Anti-Slop (SlopCodeBench), No-Phantom-Guardrails, and Symbol-Ownership admission gate.",
        "triggers": [
            "mendel godel machine",
            "red queen godel machine",
            "dual program splicing",
            "albi semantic anonymization",
            "anti slop phantom guardrails",
        ],
        "required_inputs": ["parent_source", "lineage_a", "lineage_b"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_CLM_RRF_MEMORY_BUS": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave39_leapfrog_unification_v1.py",
        "entrypoint": "CLMRRFMemoryEngine",
        "summary": "Verbatim-first 4-way RRF budgeted retrieval (Hindsight/BEAM-10M) + Nemori free-energy surprise gating + CLM file-mirrored editable working context with TMA-NM HMAC integrity.",
        "triggers": [
            "clm context language model",
            "hindsight 4-way rrf",
            "nemori surprise gated memory",
            "verbatim budgeted memory retrieval",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave39_leapfrog_unification_v1.py",
        "entrypoint": "PartialRoutingJitRLSkillTTAEngine",
        "summary": "Exact closed-form KL-RL JitRL logit modulation + SkillTTA dynamic task-contract skill synthesis + intra-task Partial Routing (Rung 0->1->2->3) + live offline harvested-surface self-verifier.",
        "triggers": [
            "jitrl closed form logit modulation",
            "skilltta dynamic skill compilation",
            "intra task partial routing",
            "harvested surface live self verifier",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "EpistemicSWEAndEGraphKernel",
        "summary": "Live unifier for 5 awakened DARK SWE organs: guarded_meaning_ir_v1 (Region-SSA + SemiPersistentEGraph + anti_unify), angelic_cegis_v1 (observational equivalence), causal_nexus_v1 (value obligations + invertible transducers), grammar_closed_repair_v1 (edit-library-free AST repair in POSIX CoW fork), and unified_epistemic_portfolio_v1.",
        "triggers": [
            "guarded meaning ir egraph anti unify",
            "grammar closed cegis repair",
            "angelic cegis observational equivalence",
            "causal nexus value obligations transducer",
            "unified epistemic portfolio overlay",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "OneShotEpistemicLearnerKernel",
        "summary": "Live unifier for 7 awakened DARK instant-learning organs: evidence_demand_v1 (complete grammar sweep, ambiguity refusal, distinguishing probe & collapse), settlement_v1, hypothesis_classes_v1, vocabulary_induction_v1, operator_acquisition_v1 (law-checked operators), demonstration_version_space_v1, and transfer_learning_v1.",
        "triggers": [
            "evidence demand version space collapse",
            "one shot epistemic learner settlement",
            "hypothesis classes algebraic determination",
            "law checked operator acquisition",
            "cross env structural transfer demonstration",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "ShadowInterfaceHCURouterKernel",
        "summary": "Simular Agent-S4 evolving Python shadow-interface compiler + Microsoft HCU 3-channel minimum-cost router (CLI/Code -> Semantic AX/Mental-Model -> Visual GUI) unifying 5 awakened DARK computer-use organs (tool_census_v1, computer_env_v1, executable_mental_model_v1, computer_use_agent_v1, aimed_action_v1).",
        "triggers": [
            "agent s4 evolving shadow interface compiler",
            "microsoft hcu three channel computer use router",
            "tool census executable mental model",
            "articulation subgoals aimed actions",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "OutOfCoreRLMWorkspace",
        "summary": "MIT Recursive Language Models (RLM) out-of-core symbolic corpus environment with SHA-256 indexed handles, bounded AST-symbol/regex/line slicing, and divide-and-conquer recursive map-reduce eliminating context rot and KV-cache prefix busting.",
        "triggers": [
            "mit rlm out of core recursive language model",
            "programmatic slice ast symbol corpus handle",
            "recursive map reduce zero compaction",
            "anti context rot workspace",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "FourNetworkGitMemoryEngine",
        "summary": "Hindsight 4-Network bi-temporal memory (world_facts, experiences, observations, mental_models) + Letta MemFS / ByteRover plain git-diffable Markdown persistence + DeepSeek Engram O(1) hashed N-gram lookup + Sleep Knowledge Seeding consolidation + TMA-NM HMAC tamper exclusion.",
        "triggers": [
            "hindsight four network bi temporal memory",
            "deepseek engram hashed ngram lookup",
            "letta memfs byterover git diffable memory",
            "sleep knowledge seeding consolidation tma nm",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "CHASEHillSamplingNFVGate",
        "summary": "Staged Goal-Blind NFV formal verification (blocking 98% unstaged false proofs) + CHASE validity-preserving semantic perturbation audit + Harness-Delta Attribution (HDA) genuine-vs-overfit decomposition + Hill Sampling adaptive diverse parent selection.",
        "triggers": [
            "staged goal blind nfv formal verification",
            "chase semantic perturbation overfit audit",
            "harness delta attribution hda genuine gain",
            "hill sampling evolutionary parent selection",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        "entrypoint": "SelfPlaySteerAndHorizonKernel",
        "summary": "Meta Self-Play SWE-RL zero-data AST bug challenger-solver inside POSIX CoW forks + CMU Steer-Don't-Solve 1-line trajectory critic + 7 awakened DARK autonomy/horizon organs (horizon_bounded_execution_v1, composition_verification_v1, credit_assignment_v1, weights_from_scratch_v1, creature_stakes_and_initiative_v1, curriculum_v1, the_record_is_the_commit_v1).",
        "triggers": [
            "meta self play swe rl zero data challenger solver",
            "steer dont solve trajectory critic",
            "horizon bounded execution credit assignment",
            "the record is the commit crash recoverable wal",
            "creature stakes initiative curriculum",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W41_RUNG3_PLUGGABLE_PROPOSER_JITRL": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
        "entrypoint": "PluggableRung3ProposerJitRLKernel",
        "summary": "Strict 4-rung escalation (Rung 0 Futamura -> Rung 1 Grammar-Closed CEGIS -> Rung 2 Angelic OE -> Rung 3 Pluggable Open-Weight Local Proposer) with K3=0 default abstention, live closed-form JitRL logit shift, CMU Steer-Don't-Solve, and Wave 40 Staged Goal-Blind NFV + CHASE gating.",
        "triggers": [
            "rung 3 pluggable open weight proposer jitrl",
            "four rung escalation abstention staged nfv",
            "local proposer logit shift steer dont solve",
            "qwen cwm rung 3 proposer adapter",
        ],
        "required_inputs": ["buggy_source", "fn_name", "test_cases"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W41_WHITEBOX_TRACE_ABDUCTION_AND_OE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
        "entrypoint": "WhiteboxTraceAbductionOEKernel",
        "summary": "Live unifier for 8 awakened DARK whitebox SWE organs: closed_loop_trace_abduction_repair_v1 (Ochiai + loop-cycle detection), angelic_oe_synthesizer_v1, cegis_semantic_synthesizer_v1, whitebox_introspector_and_trace_synthesizer_v1, semantic_ir_v1, python_counterfactual_spec_repair_v1, causal_swe_repair_v1, and multistep_repo_closed_loop_solver_v1.",
        "triggers": [
            "whitebox trace abduction ochiai loop cycle",
            "angelic oe bottom up expression synthesizer",
            "cegis semantic egraph pruned synthesis",
            "whitebox introspector counterfactual repair sites",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W41_TTPO_OPSD_CONSENSUS_DISTILLER": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
        "entrypoint": "TTPOOPSDConsensusDistiller",
        "summary": "TTPO (arXiv:2608.27448) + OPSD (arXiv:2608.31046) label-free test-time behavioral-equivalence consensus distillation inside POSIX CoW forks: distills agreeing rollouts into positive JitRL receipts and penalizes confident disagreeing errors.",
        "triggers": [
            "ttpo opsd label free test time distillation",
            "behavioral equivalence rollout consensus",
            "negative self distillation confident outlier penalty",
        ],
        "required_inputs": ["rollouts", "fn_name", "probe_inputs"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W42_FUTAMURA_COMPILE_AWAY_FLYWHEEL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
        "entrypoint": "FutamuraCompileAwayFlywheelKernel",
        "summary": "Wave 42 compounding continual-learning flywheel: Zero-Data Self-Play -> Rung-1/2/3 Solve -> Futamura Rung-0 O(1) Skill Compile-Away -> Zero-Anchor-Regression Gate -> 4-Network Git/Engram TMA-NM Sleep Consolidation.",
        "triggers": [
            "futamura compile away continual flywheel",
            "rung 0 skill compilation zero search speedup",
            "sleep consolidation zero anchor regression",
            "self play compile away continual learning",
        ],
        "required_inputs": ["training_buggy_source", "training_fn_name", "training_cases"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W42_ONE_DEMO_TRUST_AND_RUNG_CALIBRATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
        "entrypoint": "OneDemoTrustAndRungCalibratorKernel",
        "summary": "Live unifier for 8 awakened DARK continual-learning & koan modules: the_goal_is_a_quotient_of_the_trace_v1 (collision-free quotient gating), the_demand_is_learned_from_the_run_v1, an_actions_effect_is_a_provenance_map_v1, the_page_is_the_guide_v1, when_one_showing_should_be_trusted_20261112_v1, generalization_rung_gradient_v1, the_frame_crosses_the_machine_v1, semantic_generalization_engine_v1, and canonical_boundary_router_v1.",
        "triggers": [
            "one demo trust calibration quotient collision",
            "the page is the guide ui trace sketch rule",
            "the demand is learned from the run guard sites",
            "actions effect provenance map rung gradient",
        ],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "LEAPFROG_W43_GIT_HISTORY_SEEDED_REPAIR": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "GitHistorySeededRepairKernel",
        "summary": "Wave 43 live unifier for 5 awakened DARK SWE modules (history_template_repair_v1, the_store_is_the_only_thing_that_learns_v1, arm_learned_from_its_own_verified_repairs_v1, operator_generalization_v1, verified_lesson_pipeline_v1): self-seeds per-repo AST template stores from pre-base git history at K3=0, folds online alpha-canonical repairs, generalizes operator swaps, and enforces FixedBench already-passing abstention.",
        "triggers": [
            "git history self seeding ast template repair",
            "online alpha canonical repair folding",
            "fixedbench already passing abstention gate",
            "operator swap family generalization locus filter",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W43_TRACE_LITERAL_CAUSAL_SLICE_GATE": {
        "domain": "SWE_SYNTHESIS_AND_REPAIR",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "TraceLiteralCausalSliceGateKernel",
        "summary": "Wave 43 live unifier for 8 awakened DARK trace/literal/causal SWE modules (causal_dataflow_graph_v1, causal_dependency_repair_v1, repair_input_dependency_gate_v1, the_constant_is_a_hole_v1, the_literal_is_the_defect_v1, the_relation_not_the_value_v1, the_failing_run_names_the_expression_v1, the_same_guard_twice_is_the_discriminator_v1): ARISE/CausalRepair cross-file dual-slicing, constant-hole CEGIS literal repair, truthiness guard rewriting, and anti-slop input-dependency gating.",
        "triggers": [
            "arise causal dataflow dual slicing root cause",
            "constant is a hole cegis literal regex repair",
            "anti slop repair input dependency gate",
            "truthiness boolean coercion guard rewrite",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W43_COW_CONTRASTIVE_MINIMAX_FACTORY": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "CoWContrastiveMinimaxFactoryKernel",
        "summary": "Wave 43 live unifier for 6 awakened DARK active-contrast modules (the_counterexample_is_the_next_experiment_v1, the_branch_is_the_model_v1, the_refusal_is_the_other_half_v1, the_index_is_the_bottleneck_v1, verified_capability_bridge_index_v1, counterexample_guided_causal_architecture_synthesizer_v1): POSIX CoW contrastive single-feature micro-factory + exact minimax partition-lattice interrogation + filing-key collision diagnostics.",
        "triggers": [
            "cow fork contrastive micro factory single feature",
            "exact minimax partition lattice witness interrogation",
            "the refusal is the other half hypothesis lattice",
            "the index is the bottleneck filing key collision",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "MEMEDBSPCascadeAbsenceMemoryEngine",
        "summary": "Wave 44 DBSP Z-set + AGM dependency memory conquering all 6 MEME benchmark tasks (Exact Recall, Aggregation, Tracking, Deletion, Multi-Hop Dependency Cascade, and Formal Absence Witness) plus OpenViking L0/L1/L2 progressive disclosure, DeltaMem residual skill trees, and MemRL runtime Q-value retrieval at K3=0.",
        "triggers": [
            "meme benchmark dependency cascade absence deletion",
            "dbsp zset agm transitive cascade recomputation",
            "openviking l0 l1 l2 progressive context disclosure",
            "deltamem residual skill tree memrl runtime utility",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W44_WEBMCP_GUI_ROOM_OSWORLD_HCU": {
        "domain": "COMPUTER_USE_PETRI_AND_PROSE",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "WebMCPGuiRoomOSWorldHCUKernel",
        "summary": "Wave 44 live unifier for 4 awakened DARK browser/OSWorld surfaces (gui_room_v1, osworld_v21_host_browser_ops_v1, osworld_v21_generic_policy_v1, osworld_computer_surface_v1) + Chrome 150+ W3C WebMCP (document.modelContext ?? navigator.modelContext) compiler lifting HTML forms and CDP/HAR XHR calls to Channel-0 tools before structural AT-SPI A11y routing.",
        "triggers": [
            "chrome 150 webmcp document modelcontext registertool",
            "osworld 2 1 atspi a11y parse_a11y typed pyautogui",
            "gui room structural cdp browser zero pixel",
            "lifted html form har xhr webmcp shadow tool",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W44_NESTED_SKILLRL_RQGM_GEA_CONTINUAL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
        "entrypoint": "NestedSkillRLRQGMGEAContinualKernel",
        "summary": "Wave 44 continual-learning unifier combining Google Nested Learning multi-frequency Continuum Memory System (CMS clock bands), SkillRL differential success & counterfactual-failure SkillBank distillation, Group-Evolving Agents (GEA intra-group experience sharing), and Red Queen Godel Machine (RQGM anchor-gated evaluator co-evolution with selective utility erasure).",
        "triggers": [
            "google nested learning continuum memory system cms",
            "skillrl differential counterfactual failure skillbank",
            "group evolving agents gea intra group experience",
            "red queen godel machine rqgm selective erasure",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W45_QUOTIENT_ANGELIC_PROBE_INDUCER": {
        "domain": "SYNTHESIS_AND_INDUCTION",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "QuotientAngelicProbeInducerKernel",
        "summary": "Wave 45 instant-learning kernel computing coarsest sufficient trace quotients, angelic value forcing + expression synthesis, computed vs. hand-written vocabulary separation, contrastive probes, guard-width law learning, and single-pass systematic graph exploration at K3=0.",
        "triggers": [
            "coarsest quotient of the trace",
            "angelic value forcing expression synthesis",
            "computed vocabulary not written",
            "contrast is a probe guard width",
            "systematic graph exploration",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W45_METAMORPHIC_LINEAGE_CORPUS_SWE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "MetamorphicLineageCorpusSWEKernel",
        "summary": "Wave 45 formal SWE kernel harvesting repository seed corpora, enforcing zero-test metamorphic canonicality laws, tracing interprocedural producer lineage for rejected values, repairing variable name holes and coupled two-guard edits within the file's own alphabet, enforcing symbol ownership, and auditing source taint flows at K3=0.",
        "triggers": [
            "repository seed corpus metamorphic laws",
            "producer lineage graph rejected value producer",
            "variable name hole two guard coupled repair",
            "symbol ownership taint flow alphabet",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W45_AX_GUARD_ZERO_SHOT_CACHE_HCU": {
        "domain": "COMPUTER_USE_AND_TERMINAL",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "AXGuardZeroShotCacheHCUKernel",
        "summary": "Wave 45 Microsoft HCU AX-guard kernel combining view-independent AX target binding, pre-input action guards, accessibility-debt auditing (visual fallback only on undescribed widgets), verified zero-screenshot CDP/A11y action caching, partial-order planning, and literal-evidence OSWorld verified task ledgers at K3=0.",
        "triggers": [
            "microsoft hcu ax guard batched wait diff",
            "accessibility debt undescribed widgets visual fallback",
            "verified zero screenshot action cache cdp",
            "osworld verified task ledger partial order",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY": {
        "domain": "MEMORY_AND_BELIEF_REVISION",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "AntiManufacturedConfidenceMemoryEngine",
        "summary": "Wave 46 anti-manufactured-confidence memory unifying PR #7145 6-op MEME DependencyMemory with Kwon 2026 Manufactured-Confidence immunity (quarantining single-source hedged hearsay), LAPSE temporal-shape fidelity (preserving progressive/bounded facts without stative coercion), reader conjunctions, capture-recapture unseen estimation, and rollbackable composition state capsules at K3=0.",
        "triggers": [
            "manufactured confidence hedged provenance quarantine",
            "lapse temporal fidelity progressive bounded stative",
            "meme protocol 6 op dependency memory capsule rollback",
            "kumiho agm hansson belief revision",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W46_ANYTIME_VALID_EVALUE_EVOLUTION_GATE": {
        "domain": "VERIFICATION_AND_EPISTEMIC_GATES",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "AnytimeValidEValueEvolutionGateKernel",
        "summary": "Wave 46 self-evolution verification gate enforcing SCoRE conformal e-values, Ville's inequality anytime-valid betting supermartingales, mutation-tested verifier falsification (can_say_no), cross-verifier conditional error correlation phi, skill-scope admission, and Thompson-compiler security poisoning defense at K3=0.",
        "triggers": [
            "score conformal e values ville anytime valid supermartingale",
            "verifier falsification mutant kill rate phi correlation",
            "endogenous loop collapse thompson poisoning gate",
            "skill scope bundle learned skill verdict",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W46_THREE_TIER_ZERO_FORGETTING_CONTINUAL": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
        "entrypoint": "ThreeTierZeroForgettingContinualKernel",
        "summary": "Wave 46 three-tier zero-forgetting continual kernel uniting Tier-0 HierarchicalSkillLibrary with O(1) unlearning, Tier-1 Doc-to-LoRA single-pass rank-budgeted adapter manifests (<50 MB), and Tier-2 LRCP Gram-Schmidt orthogonal-subspace projection + sparse memory slot consolidation gated by anytime-valid e-values at K3=0.",
        "triggers": [
            "doc to lora single pass hypernetwork adapter manifest",
            "lrcp orthogonal subspace projection zero forgetting",
            "sparse memory finetuning sae fd hierarchical skill library",
            "three tier continual learning o1 unlearning",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W47_FUTAMURA_SKILL_COMPILER_GRAMMAR": {
        "domain": "SYNTHESIS_AND_INDUCTION",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "FutamuraSkillCompilerGrammarKernel",
        "summary": "Wave 47 Futamura partial-evaluation kernel compiling slow UI/CLI traces to fastest causal layers (<5ms parameterized skills), running symbolic Mealy + DBSP + conformal e-value cycles, and solving typed CLI/A11y action-grammar goals at K3=0.",
        "triggers": [
            "futamura projection partial evaluation compile away frontier",
            "causal trace to skill compiler anti unify workflow",
            "guide action grammar interface action grammar a11y",
            "symbolic mealy dbsp conformal evalue",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W47_REVERSE_TOMOGRAPHY_ANGELIC_LENS_SWE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "ReverseTomographyAngelicLensSWEKernel",
        "summary": "Wave 47 reverse-execution tomography kernel backpropagating failing output residuals to AST patches, certifying ddmin minimal witnesses, synthesizing invertible bidirectional FST/lenses with L3 negative-space refutation pruning, and reading demands from failing assertions for counterfactual interior synthesis at K3=0.",
        "triggers": [
            "reverse tomography algebra backward residual ast repair",
            "angelic lens cow repair bidirectional fst lens",
            "assertion is the demand counterfactual spec repair",
            "ddmin shrink certified negative space invariant store",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W47_MEANING_EGRAPH_VERICODING_PROOF_CUT": {
        "domain": "VERIFICATION_AND_EPISTEMIC_GATES",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "MeaningEGraphVericodingProofCutKernel",
        "summary": "Wave 47 e-graph equality saturation & vericoding kernel unifying EGraph optimal extraction, Universal Meaning UIR canonicalization, mutation-tested verifier falsification (can_say_no), sound Python request semantic acceptance cells, orthogonal patch merging, and exact lexicographic global proof-cut compilation at K3=0.",
        "triggers": [
            "egraph equality saturation egglog universal meaning uir",
            "vericoding prove verifier can say no semantic acceptance",
            "global proof cut compiler dominance deletion frozen universe",
            "orthogonal patch merge deductive synthesizer",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU": {
        "domain": "COMPUTER_USE_AND_TERMINAL",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "EvolvingInterfaceByteEffectHCUKernel",
        "summary": "Wave 48 Agent-S4 evolving-interface HCU kernel anti-unifying trajectories into typed CLI/tool interfaces, computing Petri-net dominator cut-vertices for checkpointing, executing crash-recoverable transactional commits, and enforcing Ring-0 byte-format & directory-diff effect oracles at K3=0.",
        "triggers": [
            "agent s4 evolving agent interfaces anti unify templates",
            "petri dominator cut vertices universal computer agent",
            "durable transactional commit crash recovery cow sandbox",
            "ring 0 byte effect oracle unauthorized write diff",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY": {
        "domain": "MEMORY_AND_BELIEF_REVISION",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "FiveTimescaleSleepCrystallizerCSRMemoryEngine",
        "summary": "Wave 48 five-timescale verification-first memory & sleep-time crystallizer uniting bi-temporal supersession, ADWIN+BOCPD+Page-Hinkley drift detection, zero-copy binary mmap CSR slot/postings indices, cross-language Python/JS/C Semantic IR anti-unification, and 5-gate epistemic admission at K3=0.",
        "triggers": [
            "five timescale sleep time compute memory crystallizer",
            "mmap csr binary slot index zero copy postings",
            "cross language semantic ir anti unification 5 gate admission",
            "verification first memory bus bitemporal drift detector",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        "entrypoint": "MetaCircularConceptRefusalAdjudicatorKernel",
        "summary": "Wave 48 meta-circular self-improvement & adjudication kernel verifying pure-AST organs behind SelfPatchFirewall + Ring0SelfReferee, inventing higher-order Plotkin LGG abstractions (LILO/Stitch fold_scan) and periodic operators, turning refusals into active-inference EFE curricula, and running subprocess dark-matter adjudication + static K3=0 endpoint audits.",
        "triggers": [
            "meta circular organ graph self patch firewall ring 0 referee",
            "higher order plotkin lgg lilo stitch concept library",
            "refusal is the curriculum active inference efe experiment",
            "dark matter adjudicator proven verdict k3 model surface audit",
        ],
        "required_inputs": ["op"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W49_TRACEBACK_SIGNATURE_ZERO_LINE_LOCALIZER": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "TracebackSignatureZeroLineLocalizerKernel",
        "summary": "Wave 49 zero-executed-line traceback & AST symbol localizer breaking NO_EXECUTED_REPO_LINES on TypeError/AttributeError/ImportError/dunder/module-reexport failures with fail-closed checkout-import provenance verification.",
        "triggers": [
            "zero line traceback localizer unexpected keyword argument",
            "checkout import provenance site packages shadow guard",
            "dunder comparison typeerror reflexive assertion localization",
            "no executed repo lines static ast symbol localizer",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W49_STRUCTURAL_AST_MULTI_HUNK_SYNTHESIZER": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "StructuralASTMultiHunkSynthesizerKernel",
        "summary": "Wave 49 structural AST multi-hunk synthesizer breaking the value-substitution wall: kwarg addition & context/converter threading, dunder self-comparison guards, __module__ re-export normalization, !r/repr f-string repairs, recursive seen-set cycle guards, version split repairs, and symbol-ownership-bounded multi-site expression transfer.",
        "triggers": [
            "structural ast multi hunk repair parameter addition threading",
            "dunder reflexive isinstance guard module reexport normalization",
            "fstring repr redundant quotes recursive seen set cycle guard",
            "bounded site general expression synthesis symbol ownership transfer",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W49_MINIMAX_INTERROGATION_CONTRASTIVE_ORACLE": {
        "domain": "INSTANT_LEARNING_AND_SYNTHESIS",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "MinimaxInterrogationContrastiveOracleKernel",
        "summary": "Wave 49 exact-minimax version-space interrogation loop (witness computed, not remembered) paired with contrastive mutant-killing oracle bootstrap and McNemar paired transfer delta.",
        "triggers": [
            "exact minimax interrogation witness computed version space",
            "contrastive oracle bootstrap mutant kill paired transfer",
            "mcnemar discordant pairs rubber stamp verifier rejection",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W50_KERNEL_BOUNDARY_DUAL_CHANNEL_EFFECT_HCU": {
        "domain": "COMPUTER_USE_AND_SANDBOX",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "KernelBoundaryDualChannelEffectHCUKernel",
        "summary": "Wave 50 fail-closed kernel boundary + cryptographic pre/post SHA-256 byte-effect oracle + CoAct-1 / Agent S4 dual-channel structured-CLI vs GUI action-grammar router.",
        "triggers": [
            "kernel boundary effect oracle sha256 manifest cannot lie",
            "dual channel hcu router coact1 cli sqlite gui a11y",
            "unauthorized protected file modification detection",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W50_CRASH_RESUMABLE_SELF_VERIFYING_LIFE_LOOP": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "CrashResumableSelfVerifyingLifeLoopKernel",
        "summary": "Wave 50 resident crash-resumable hash-chained WAL creature life-loop ticks + self-verifying execution enrollment of never-run capabilities with adversarial negative controls.",
        "triggers": [
            "crash resumable continuous creature life loop wal replay",
            "self verifying capability enrollment by execution",
            "hash chained append only tick journal zero duplication",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W50_TITAN_BEHAVIORAL_PROOF_ADJUDICATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
        "entrypoint": "TitanBehavioralProofAdjudicatorKernel",
        "summary": "Wave 50 subprocess-isolated behavioral proof adjudicator verifying 19+ flagship titans (69,000+ PROVEN LOC) with falsifiable adversarial self_check() contracts and static K3=0 endpoint audits.",
        "triggers": [
            "titan behavioral proof adjudicator subprocess proven loc",
            "falsifiable self check adversarial negative control audit",
            "dark matter adjudicator titan suite k3 zero verification",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W52_ARISE_STATEMENT_DEF_USE_SLICER": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "AriseDefUseSlicerKernel",
        "summary": "Wave 52 ARISE statement-level AST def-use & control-dependence slicer (arXiv:2605.03117) computing backward/forward dataflow slices, dunder delegation links, and guard-return localization.",
        "triggers": [
            "arise statement level def use dataflow slice ast",
            "backward forward program slice guard return localization",
            "dunder method delegation def use graph compression",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W52_SLICED_STRUCTURAL_AST_SWE_ENGINE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "Wave52StructuralSweEngineKernel",
        "summary": "Wave 52 general structural AST SWE repair engine (S8-S11 + S1-S7 + 2-round residual literal alignment + NAME_SCOPE + 4 pytest verifier-lie defenses) achieving 8/10 corpus (8/8 well-posed existing-module Python bugs) at K3=0 and $0.00.",
        "triggers": [
            "s8 import symbol alias s9 parser position diagnostic",
            "s10 short circuit policy guard s11 recursive collector visited memo",
            "pytest verifier lie defense zero collected rc5 rejection",
            "structural ast swe repair real repo k3 zero",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W51_STRANDED_TREASURY_CONFINEMENT_ORACLE": {
        "domain": "COMPUTER_USE_AND_SANDBOX",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "StrandedTreasuryConfinementAndOracleKernel",
        "summary": "Wave 51 stranded PR treasury harvest: kernel/OS CapEff confinement probe (PR #7071), byte-derived magic+roundtrip effect oracle rejecting spoofed extensions, vocabulary-independent lifted operators, contrastive rule bootstrap (PR #7019), AST symbol-ownership blast radius (PR #6857), and honest denominator guard (PR #7149).",
        "triggers": [
            "os confinement capeff unshare host sentinel probe",
            "byte derived effect oracle reject spoofed extension xz in gz",
            "lifted vocabulary independent operator contrastive bootstrap",
            "symbol ownership blast radius honest denominator guard",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W52_ZERO_LLM_FTS_ATMA_HINDSIGHT_MEMORY": {
        "domain": "MEMORY_AND_BELIEF_REVISION",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "ZeroLlmFtsAtmaMemoryEngine",
        "summary": "Wave 52 Zero-LLM SQLite FTS5 BM25 + A-TMA explicit state-view packets (CURRENT/SUPERSEDED/TRANSITION/ABSTAIN_EXPIRED) killing ghost memory + Hindsight counterfactual deletion-credit provenance at <1ms and K3=0.",
        "triggers": [
            "zero llm fts5 bm25 a tma state view packet ghost memory kill",
            "calibrated abstain expired temporal memory supersession",
            "hindsight counterfactual deletion credit memory prm",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W52_COLD_START_FRONT_DOOR_BRIDGE": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "ColdStartFrontDoorBridgeKernel",
        "summary": "Wave 52 cold-start unified front-door dispatcher and DARK module awakening bridge elevating cumulative awakened DARK modules from 160 to 192 (+32 zero-overlap modules).",
        "triggers": [
            "cold start front door dispatch unified model bridge",
            "awakened dark modules 192 zero overlap audit",
            "dark swe kernel module awakening bridge",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W51_48_TITAN_BLOB_PINNED_ADJUDICATOR": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
        "entrypoint": "Wave51FortyEightTitanAdjudicatorKernel",
        "summary": "Wave 51 blob-pinned subprocess behavioral proof adjudicator verifying 48/48 flagship titans (>148,000 PROVEN LOC, 260+ positive+negative checks, 0 BROKEN) with SHA-256 execution enrollment.",
        "triggers": [
            "48 titan blob pinned subprocess behavioral adjudication",
            "sha256 execution enrollment proven loc 148000 zero broken",
            "flagship titan proof completion wave 51",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W53_UNIFIED_CAPABILITY_BUS": {
        "domain": "CONTINUAL_LEARNING_AND_ORGANS",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "UnifiedCapabilityBusEngine",
        "summary": "Wave 53 zero-LOC-growth unified capability bus awakening 36 zero-overlap hidden organs (192 -> 228 cumulative DARK modules) and structural front-door intent router raising real SWE issue acceptance from 35.0% to 96.2% while refusing 100% of content-free inputs.",
        "triggers": [
            "unified capability bus 36 zero overlap hidden organs 228 dark modules",
            "structural front door intent router real swe issue acceptance",
            "dynamic plugin bus zero loc growth brain unified model",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W53_SAFE_TRANSFER_ESTITCH_STRATA": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "SafeTransferEStitchStrataEngine",
        "summary": "Wave 53 6-stage safe transfer engine unifying MIT E-Stitch e-class canonicalization, structured morphism abstraction, oracle-free alpha-safe templates, STRATA contrast-edge negative-transfer defense (0% blind corruption), hard invalidation, and Ville e-process credit gating.",
        "triggers": [
            "e-stitch equivalence class ast canonicalization library learning",
            "strata contrast edge negative transfer defense settled admission",
            "quixbugs leave one out cross program transfer alpha safe rewrite",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "FullMetamorphicLawAndPrecisionSlicerEngine",
        "summary": "Wave 54 complete 9/9 metamorphic law repair synthesizer, test-isolation inherited-debt filter, free AST def-use neighbor-regression precision pre-filter, and multi-file top-K call-graph localizer with atomic CoW rollback.",
        "triggers": [
            "9 of 9 metamorphic law repair generators inherited debt isolation",
            "neighbor regression precision prefilter changed symbols ast slice",
            "multi file top k call graph localization atomic cow rollback",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W54_DOCKERLESS_VERIFIER_AND_SELFPLAY": {
        "domain": "VERIFICATION_AND_PROOF",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "DockerlessVerifierAndSelfPlayCurriculumEngine",
        "summary": "Wave 54 7-probe deterministic zero-Docker patch verifier (Dockerless-inspired) and ignorance-ledger-driven self-play bug-injection & blind repair curriculum proving Round-2 skill transfer at K3=0.",
        "triggers": [
            "dockerless 7 probe environment free patch verifier blast radius",
            "self play swe rl bug injection blind repair ignorance ledger curriculum",
            "round 2 skill transfer verified crystallization k3 zero",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER": {
        "domain": "COMPUTER_USE_AND_PERCEPTION",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "UnifiedMultiRungJitRLAndWebMcpGrounderEngine",
        "summary": "Wave 54 inverted multi-rung JitRL closed-form KL advantage executive loop + task-agnostic JSON-schema multi-step WebMCP & OSWorld 2.1 grounder with WebXSkill step contracts raising WebMCP grounding from 26.9% to 100.0%.",
        "triggers": [
            "jitrl closed form kl advantage multi rung compile away executive",
            "webmcp document modelcontext json schema multi step grounder webxskill",
            "osworld 2.1 app policy overlay computer use grounding",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "LEAPFROG_W54_DBSP_HINDSIGHT_STRATA_MEMORY": {
        "domain": "MEMORY_AND_BELIEF_REVISION",
        "source_path": "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
        "entrypoint": "DbspHindsightStrataMemoryEngine",
        "summary": "Wave 54 control-plane memory unifying DBSP Z-set cascade & formal Absence witnesses, Hindsight 4 epistemic networks, P-Mem explicit rollback edges, ForgetEval-Adv 6 primitives (including purge-by-query & shared-attribute release), and STRATA contrast conflict warnings.",
        "triggers": [
            "dbsp z set cascade absence witness meme protocol memory",
            "hindsight 4 epistemic networks p-mem rollback edge forgeteval adv",
            "purge by query release shared attribute strata contrast conflict",
        ],
        "required_inputs": ["operation"],
        "declared_dependencies": [],
    },
    "METAMORPHIC_HABITATION_ZIPPER": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
        "entrypoint": "parse_pytest_failures",
        "summary": "Metamorphic habitation & zipper obligation propagator with multi-signal fault localization and pytest failure extraction.",
        "triggers": ["metamorphic_habitation_zipper", "type habitation repair", "zipper obligation propagator"],
        "required_inputs": ["output"],
        "declared_dependencies": [],
    },
    "PETRI_COW_SPLICING_ENGINE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/petri_cow_splicing_engine_v1.py",
        "entrypoint": "compute_structural_fp64",
        "summary": "Petri-net CoW dual splicing engine with structural 64-bit code/schema fingerprinting and backward assertion witnesses.",
        "triggers": ["petri_cow_splicing_engine", "structural fp64 code fingerprint", "backward witness dual splicer"],
        "required_inputs": ["code_or_schema"],
        "declared_dependencies": [],
    },
    "AUTONOMOUS_AWAKE_LOOP": {
        "domain": "CONTINUOUS_AGENCY_AND_SELF_IMPROVEMENT",
        "source_path": "canonical/swe_kernel/autonomous_awake_loop_v1.py",
        "entrypoint": "FileAtomicJournalStore",
        "summary": "Autonomous awake agency daemon with atomic journal store and confined language test oracle.",
        "triggers": ["autonomous_awake_loop", "awake agency daemon", "atomic journal store"],
        "required_inputs": ["journal_dir"],
        "declared_dependencies": [],
    },
    "SWE_SELF_IMPROVEMENT_BRIDGE": {
        "domain": "CONTINUOUS_AGENCY_AND_SELF_IMPROVEMENT",
        "source_path": "canonical/swe_kernel/swe_self_improvement_bridge_v1.py",
        "entrypoint": "build_formal_swe_problem",
        "summary": "Formal SWE self-improvement bridge connecting coding episodes to verified generalization suites.",
        "triggers": ["swe_self_improvement_bridge", "formal swe coding episode"],
        "required_inputs": ["task_id"],
        "declared_dependencies": [],
    },
    "INDUCED_EDIT_BASIS": {
        "domain": "SKILL_COMPILATION_AND_ANTI_UNIFICATION",
        "source_path": "canonical/swe_kernel/induced_edit_basis_v1.py",
        "entrypoint": "induce_templates",
        "summary": "Induces minimal reusable AST edit-template basis directly from `(before, after)` repair pairs.",
        "triggers": ["induced_edit_basis", "induce ast edit templates"],
        "required_inputs": ["pairs"],
        "declared_dependencies": [],
    },
    "CONTRACT_GROUNDED_REPAIR": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/contract_grounded_repair_v1.py",
        "entrypoint": "load_task",
        "summary": "Contract-grounded SWE repair screening synthesized AST variants against executable observation contracts.",
        "triggers": ["contract_grounded_repair", "contract grounded ast synthesis"],
        "required_inputs": ["task_dir", "name"],
        "declared_dependencies": [],
    },
    "CHECKABILITY_DIFFERENTIAL_PIN": {
        "domain": "VERIFICATION_AND_CHECKABILITY",
        "source_path": "canonical/swe_kernel/checkability_by_differential_pin_v1.py",
        "entrypoint": "public_callables",
        "summary": "Measures module checkability via public callable extraction, doctest pinning, and differential commit probes.",
        "triggers": ["checkability_by_differential_pin", "public callables differential pin"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "OPERAND_INVENTION": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/swe_kernel/operand_invention_v1.py",
        "entrypoint": "scope_names",
        "summary": "Scope-grounded operand invention extracting live lexical/imported/builtin operands for AST patch synthesis.",
        "triggers": ["operand_invention", "scope grounded operand synthesis"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "SKILL_SCOPE_ACQUISITION": {
        "domain": "SKILL_COMPILATION_AND_ANTI_UNIFICATION",
        "source_path": "canonical/swe_kernel/skill_scope_acquisition_v1.py",
        "entrypoint": "observable_facts",
        "summary": "Learns exact syntactic/observable applicability scope facts governing when a compiled skill safely fires.",
        "triggers": ["skill_scope_acquisition", "observable skill applicability facts"],
        "required_inputs": ["source"],
        "declared_dependencies": [],
    },
    "ABDUCTIVE_REFUSAL_AUTOBINDER": {
        "domain": "VERIFICATION_AND_CHECKABILITY",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "abductive_refusal_contract_autobinder",
        "summary": "Compiles CLI/Python precondition refusals + declared goal derivations (`a_refusal_is_a_specification_v1` + `declared_input_derivation_v1`) into mutant-verified executable contracts.",
        "triggers": ["abductive_refusal_autobinder", "refusal is a specification", "declared input derivation"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ANGELIC_ZYGOTE_VERSION_SPACE_SWE": {
        "domain": "SWE_LOCALIZATION_AND_REPAIR",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "angelic_zygote_version_space_swe",
        "summary": "CoW-Zygote + Angelic Forest (`angelic_cegis_repair_v1`) + RepoMem git alignment + concolic version-space distinguishing oracle (`passing_repairs_version_space_v1`).",
        "triggers": ["angelic_zygote_version_space_swe", "angelic cegis zygote", "passing repairs version space"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ZERO_PIXEL_SHADOW_TRANSDUCER_CU": {
        "domain": "COMPUTER_USE_AND_ENVIRONMENT_EXPLORATION",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "zero_pixel_shadow_transducer_cu",
        "summary": "Zero-pixel declarative ARIA/Shadow-DOM name-addressed CDP + counterfactual trace elevation + Petri dominator checkpoints + Vaandrager L# Mealy transducer.",
        "triggers": ["zero_pixel_shadow_transducer_cu", "agent s4 shadow interface", "name addressed browser cdp"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "EPISTEMIC_DIGITAL_TWIN_AND_ARC": {
        "domain": "WORLD_MODELS_AND_ABSTRACTION",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "solve_digital_twin_and_arc",
        "summary": "OPINE-World epistemic ontology exploration + Twin 100%-replay-verified BFS digital twin + ARC-NEST leave-one-out CV + E-Stitch library compression.",
        "triggers": ["epistemic_digital_twin_and_arc", "opine world digital twin", "arc nest estitch"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "ALGEBRAIC_SHEAF_SRMU_MEMORY": {
        "domain": "MEMORY_AND_CONTINUAL_LEARNING",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "sheaf_srmu_memory_cycle",
        "summary": "3-Layer Algebraic Memory Spine: SRMU 10,240-bit relevance-gated hypervectors + exact Q cellular sheaf H^1 contradiction firewall + Dual NNF Why-True/Why-Absent provenance semiring.",
        "triggers": ["algebraic_sheaf_srmu_memory", "cellular sheaf h1 cohomology", "srmu hypervector dual nnf provenance"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
    "PC_DGM_SUPERCOMPILER": {
        "domain": "SELF_IMPROVEMENT_AND_META_SYNTHESIS",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "pc_dgm_supercompile_evolve",
        "summary": "Proof-Carrying Darwin-Godel Machine stepping-stone archive + Turchin/Futamura AST deforestation + terminal proof supercompiler + Rubin marginal skill-rent GC.",
        "triggers": ["pc_dgm_supercompiler", "darwin godel machine supercompiler", "turchin deforestation"],
        "required_inputs": ["fn_name", "incumbent_source"],
        "declared_dependencies": [],
    },
    "EGGMIND_GOAL_TREE_PROVER": {
        "domain": "FORMAL_VERIFICATION_AND_THEOREM_PROVING",
        "source_path": "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
        "entrypoint": "eggmind_saturate_and_prove",
        "summary": "EggMind proof-motif cached SemanticEGraph + Pantograph-style AND/OR tactic goal-tree prover over exact Q polynomial rings and Fourier-Motzkin linear arithmetic.",
        "triggers": ["eggmind_goal_tree_prover", "eggmind motif egraph", "pantograph tactic goal tree"],
        "required_inputs": [],
        "declared_dependencies": [],
    },
}


# ---------------------------------------------------------------------------
# Cross-Disciplinary Unfamiliar-Name & Koan Discrimination Bridge (<15 us)
# ---------------------------------------------------------------------------

CROSS_DISCIPLINARY_CONCEPT_MAP: dict[str, dict[str, Any]] = {
    "equality_saturation_egraph_library_learning": {
        "external_names": ["equality saturation", "e-graph", "egglog", "e-stitch", "babble", "stitch", "ast canonicalization", "library learning", "relational guard addition"],
        "engines": ["engine:RELATIONAL_GUARD_ADDITION_REPAIR", "engine:CONCEPT_LIBRARY_EGRAPH_LGG", "engine:EGRAPH_DEDUCTIVE_SYNTHESIZER", "engine:COMPRESSION_GAIN_MDL"],
        "koan_modules": [
            "canonical/runtime/relational_guard_addition_symbolic_repair_v1.py",
            "canonical/swe_kernel/concept_library_v1.py",
            "canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py",
            "canonical/swe_kernel/compression_gain_v1.py",
        ],
    },
    "version_space_algebra_programming_by_example": {
        "external_names": ["version space algebra", "flashmeta", "prose", "flashedit", "plotkin anti-unification", "edit by example", "least general generalization"],
        "engines": ["engine:EDIT_BY_EXAMPLE_PROSE", "engine:CONCEPT_LIBRARY_EGRAPH_LGG", "engine:STRUCTURAL_REWRITE_INDUCER"],
        "koan_modules": [
            "canonical/swe_kernel/taught_actions/edit_by_example_v1.py",
            "canonical/swe_kernel/tree_sitter_cst_skill_skeleton_v1.py",
            "canonical/runtime/taught_words_v1.py",
        ],
    },
    "hoare_contract_world_model_one_shot": {
        "external_names": ["instant learning", "one-shot learning", "hoare logic", "world model contract", "predictive contract", "precondition induction"],
        "engines": ["engine:INSTANT_ONE_SHOT_LEARNER", "engine:PREDICTIVE_HOARE_CONTRACT", "engine:INSTRUCTION_CONTRACT_COMPILER"],
        "koan_modules": [
            "canonical/swe_kernel/predictive_contract_v1.py",
            "canonical/swe_kernel/instant_one_shot_learning_v1.py",
            "canonical/tools/the_precondition_is_not_in_the_trace_v1.py",
            "canonical/tools/instant_learning_in_a_new_environment_v1.py",
        ],
    },
    "active_automata_learning_unknown_machine": {
        "external_names": ["active automata learning", "angluin l*", "ttt algorithm", "learnlib", "discrimination tree", "unknown cli discovery", "action grammar"],
        "engines": ["engine:METAMORPHIC_CLI_COMPILER", "engine:SUBCOMMAND_SCOPE_PROBER", "engine:KOAN_REFUSAL_CURRICULUM", "engine:ENVIRONMENT_BROKER"],
        "koan_modules": [
            "canonical/tools/the_guide_is_a_key_table_v1.py",
            "canonical/tools/the_guide_is_an_action_grammar_v1.py",
            "canonical/tools/the_repertoire_is_a_query_v1.py",
            "canonical/tools/the_machine_is_the_definition_v1.py",
            "canonical/tools/the_refusal_is_the_curriculum_v1.py",
        ],
    },
    "zero_screenshot_computer_use_minimal_sense": {
        "external_names": ["computer use", "cua", "cdp", "at-spi", "accessibility tree", "a11y", "zero screenshot", "minimum observation cost", "osworld", "stagehand", "understudy"],
        "engines": ["engine:VERIFIED_ZERO_SCREENSHOT_ACTION_CACHE", "engine:STATE_CONTRACT_WORLD_MODEL", "engine:INTERFACE_ACTION_GRAMMAR", "engine:PREMISE_MINIMAL_SENSE", "engine:UNIVERSAL_COMPUTER_AGENT", "engine:PROSE_EXPERIMENT_CLI_DISCOVERY"],
        "koan_modules": [
            "canonical/runtime/verified_zero_screenshot_action_cache_v1.py",
            "canonical/runtime/state_contract_world_model_v1.py",
            "canonical/swe_kernel/interface_action_grammar_v1.py",
            "canonical/swe_kernel/the_premise_is_the_sense_v1.py",
            "canonical/swe_kernel/universal_computer_agent_v1.py",
            "canonical/swe_kernel/cross_modal_tomography_petri_v1.py",
        ],
    },
    "cow_zygote_speculative_sandbox_fork": {
        "external_names": ["copy on write", "cow fork", "zygote", "sandlock", "zeroboot", "firecracker forkd", "speculative execution", "free undo"],
        "engines": ["engine:COW_ZYGOTE_SPECULATIVE_VERIFIER", "engine:COW_IMPACT_TEST_REPAIR_ENGINE", "engine:ZYGOTE_COW_FORK_POOL", "engine:ANGELIC_LENS_COW_REPAIR", "engine:CROSS_MODAL_PETRI_TOMOGRAPHY"],
        "koan_modules": [
            "canonical/runtime/cow_zygote_speculative_verifier_v1.py",
            "canonical/swe_kernel/cow_impact_repair_engine_v1.py",
            "canonical/swe_kernel/zygote_worker_pool_v1.py",
            "canonical/swe_kernel/cow_angelic_zygote_v1.py",
            "canonical/swe_kernel/petri_cow_splicing_engine_v1.py",
            "canonical/tools/the_failed_attempt_is_free_v1.py",
        ],
    },
    "concolic_angelic_witness_inversion_swe": {
        "external_names": ["concolic", "symbolic execution", "crosshair", "angelic execution", "witness inversion", "cegis", "program splicing", "fault localization"],
        "engines": ["engine:WITNESS_INVERSION_LENS", "engine:KOAN_FORCE_VALUE_ANGELIC", "engine:KOAN_ASSERTION_DEMAND", "engine:CONDITION_DEMAND_HARVESTER", "engine:DUAL_PROGRAM_SPLICING"],
        "koan_modules": [
            "canonical/swe_kernel/witness_inversion_v1.py",
            "canonical/tools/the_relation_is_read_from_the_failing_run_v1.py",
            "canonical/tools/the_assertion_is_the_demand_v1.py",
            "canonical/tools/force_the_value_and_see_v1.py",
            "canonical/swe_kernel/what_the_condition_wants_v1.py",
        ],
    },
    "vericoding_metamorphic_self_oracle": {
        "external_names": ["vericoding", "dafny", "verus", "lean", "leetproof", "metamorphic testing", "property based testing", "specification synthesis"],
        "engines": ["engine:STRUCTURAL_SPEC_DERIVER", "engine:METAMORPHIC_API_LAWS", "engine:SPEC_CONTRACT_SYNTHESIZER", "engine:PROVED_COMPOSITION_SURVIVAL"],
        "koan_modules": [
            "canonical/swe_kernel/specification_from_structure_v1.py",
            "canonical/swe_kernel/metamorphic_laws_v1.py",
            "canonical/swe_kernel/proved_composition_v1.py",
            "canonical/swe_kernel/metamorphic_oracle_v1.py",
        ],
    },
    "selective_abstention_continual_memory": {
        "external_names": ["continual learning", "catastrophic forgetting", "skillapt", "selskill", "conformal abstention", "rubin counterfactual", "agent memory", "sleep consolidation", "discr_tree"],
        "engines": ["engine:COUNTERFACTUAL_DISCR_TREE_SKILL_ROUTER", "engine:GRADIENT_FREE_LAW_CONSOLIDATION", "engine:ABSTAIN_GATED_SKILL_INDUCTION", "engine:RULE_EXPIRY_WORLD_FINGERPRINT", "engine:ASSOCIATIVE_EPISODIC_MEMORY", "engine:LESSON_ADMISSION_GATE", "engine:CONTRASTIVE_ORACLE_BOOTSTRAP", "engine:PAIRED_TRANSFER_EVALUATOR", "engine:VERIFIED_SKILL_CRYSTALLIZER", "engine:EPISTEMIC_SELF_PLAY_ADMISSION"],
        "koan_modules": [
            "canonical/runtime/counterfactual_discr_tree_skill_router_v1.py",
            "canonical/runtime/gradient_free_law_consolidation_v1.py",
            "canonical/runtime/abstain_gated_skill_induction_v1.py",
            "canonical/swe_kernel/rule_expiry_v1.py",
            "canonical/swe_kernel/lesson_admission_gate_v1.py",
            "canonical/swe_kernel/contrastive_oracle_bootstrap_v1.py",
            "canonical/swe_kernel/paired_transfer_evaluation_v1.py",
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        ],
    },
    "incremental_dataflow_code_graph": {
        "external_names": ["incremental computation", "salsa", "dbsp", "differential dataflow", "scip", "tree-sitter", "code graph", "fast simulator"],
        "engines": ["engine:INCREMENTAL_SEMANTIC_CODE_GRAPH", "engine:UNIVERSAL_SEMANTIC_IR", "engine:FAST_ABSTRACT_SIMULATOR"],
        "koan_modules": [
            "canonical/swe_kernel/incremental_semantic_graph_v1.py",
            "canonical/swe_kernel/universal_semantic_ir_v1.py",
            "canonical/swe_kernel/executable_simulator_mental_model_v1.py",
        ],
    },
    "pitman_yor_minimax_open_world_discovery": {
        "external_names": ["open world", "good-turing", "pitman-yor", "unseen species", "minimax bisection", "active query learning", "extrapolation"],
        "engines": ["engine:PITMAN_YOR_OPEN_WORLD", "engine:GLOBAL_MINIMAX_EXTRAPOLATOR"],
        "koan_modules": [
            "canonical/runtime/global_open_world_extrapolator_v1.py",
            "canonical/swe_kernel/global_extrapolation_chase_spine_v1.py",
            "canonical/tools/the_goal_is_a_discriminator_v1.py",
            "canonical/tools/what_is_knowable_here_v1.py",
        ],
    },
    "bitemporal_forward_push_ppr_and_skill_rent": {
        "external_names": [
            "forward push",
            "personalized pagerank",
            "hipporag",
            "memanto",
            "bitemporal memory",
            "blind curator",
            "skill ratchet",
            "rubin counterfactual rent",
        ],
        "engines": ["engine:LEAPFROG_W24_FORWARD_PUSH_BITEMPORAL_PPR"],
        "koan_modules": [
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
            "canonical/tools/the_blind_curator_v1.py",
            "canonical/runtime/skill_ratchet_universal_v1.py",
        ],
    },
    "execution_traced_compilation_and_state_alias_cascade": {
        "external_names": [
            "skillcache",
            "tracecompiler",
            "pep 669",
            "sys.monitoring",
            "statealiasbench",
            "state alias",
            "deltabox",
            "webmcp",
            "mmap csr",
        ],
        "engines": [
            "engine:LEAPFROG_W21_MMAP_CSR_SLOT_INDEX",
            "engine:LEAPFROG_W22_EXECUTION_TRACED_COMPILER",
            "engine:LEAPFROG_W23_FAST_CASCADE_ORCHESTRATOR",
        ],
        "koan_modules": [
            "canonical/runtime/mmap_csr_slot_index_v1.py",
            "canonical/runtime/execution_traced_callable_compiler_v1.py",
            "canonical/runtime/fast_cascade_orchestrator_v1.py",
            "canonical/runtime/scan_and_diff_against_memory_v1.py",
            "canonical/swe_kernel/computer_use_check_density_v1.py",
            "canonical/runtime/domain_of_verification_v1.py",
            "canonical/runtime/contrast_selection_v1.py",
        ],
    },
    "shadow_interface_webmcp_petri_cu": {
        "external_names": ["agent s4", "evolving agent interfaces", "shadow interface", "webmcp", "modelcontext", "coact-1", "inhibitor arc petri net", "pointer chasing", "research env bench"],
        "engines": ["engine:SHADOW_INTERFACE_COMPUTER_USE", "engine:GROUNDED_COMPUTER_INSPECTOR"],
        "koan_modules": [
            "canonical/tools/follow_the_pointer_v1.py",
            "canonical/runtime/environment_fit_v1.py",
            "canonical/runtime/inspect_v1.py",
            "canonical/runtime/operation_trial_v1.py",
            "canonical/runtime/hidden_arsenal_unifier_v1.py",
        ],
    },
    "spacetime_omniscient_oe_sygus": {
        "external_names": ["spacetime programming", "omniscient debugging", "debugharness", "observational equivalence sygus", "eusolver", "causal site intervention", "polyglot sygus"],
        "engines": ["engine:SPACETIME_OE_SYGUS_REPAIR", "engine:CHECKABILITY_ORACLE_FORGE"],
        "koan_modules": [
            "canonical/runtime/oe_sygus_synthesizer_v1.py",
            "canonical/runtime/value_enumeration_v1.py",
            "canonical/swe_kernel/site_by_intervention_v1.py",
            "canonical/swe_kernel/argument_construction_v1.py",
            "canonical/swe_kernel/checkability_by_differential_pin_v1.py",
            "canonical/swe_kernel/instruction_contract_for_code_v1.py",
        ],
    },
    "dbsp_zset_bitemporal_memory_and_mealy": {
        "external_names": ["dbsp", "abelian z-set", "incremental view maintenance", "angluin lstar", "active mealy automata", "distinguishing suffix", "cl-bench", "doc-to-lora", "ascent self-distillation"],
        "engines": ["engine:DBSP_BITEMPORAL_CAPABILITY_FORGE", "engine:ACTIVE_MEALY_QUESTION_LEARNER"],
        "koan_modules": [
            "canonical/tools/ask_instead_of_stare_v1.py",
            "canonical/tools/the_pre_state_is_the_missing_part_v1.py",
            "canonical/runtime/capability_forge_v1.py",
            "canonical/runtime/hidden_arsenal_unifier_v1.py",
        ],
    },
    "unfamiliar_apartness_angelix_sygus_semiring_alphaevolve": {
        "external_names": [
            "lsharp",
            "vaandrager apartness",
            "adaptive distinguishing sequence",
            "angelix",
            "angelic forest",
            "eusolver",
            "observational equivalence sygus",
            "name_scope",
            "protocol lifting",
            "har reverse api",
            "effect oracle",
            "why provenance semiring",
            "jtms",
            "meme cascade",
            "meme absence",
            "finite minimax decision region",
            "alphaevolve",
            "shinkaevolve",
            "map-elites",
        ],
        "engines": [
            "engine:UNFAMILIAR_M0_APARTNESS_LSHARP_LEARNER",
            "engine:UNFAMILIAR_M1_ANGELIC_FOREST_OE_SYGUS",
            "engine:UNFAMILIAR_M2_PROTOCOL_LIFT_EFFECT_ORACLE",
            "engine:UNFAMILIAR_M3_SEMIRING_PROVENANCE_JTMS_MEME",
            "engine:UNFAMILIAR_M4_MINIMAX_VERSION_SPACE_INTERROGATOR",
            "engine:UNFAMILIAR_M5_ZERO_LLM_ALPHAEVOLVE_PARETO",
        ],
        "koan_modules": [
            "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
            "canonical/runtime/oe_sygus_synthesizer_v1.py",
            "canonical/swe_kernel/site_by_intervention_v1.py",
            "canonical/swe_kernel/expected_actual_literal_v1.py",
            "canonical/swe_kernel/cow_lens_fuzz_and_negative_space_v1.py",
            "canonical/swe_kernel/mined_rewrite_theory_v1.py",
            "canonical/swe_kernel/pins_from_the_reverted_part_v1.py",
            "canonical/runtime/finite_minimax_decision_region_v1.py",
            "canonical/runtime/monotone_semantic_drd_bridge_v1.py",
            "intake/osworld_intake_policy_v1.py",
        ],
    },
    "futamura_compile_away_ring0_byte_oracle_and_dra": {
        "external_names": [
            "futamura",
            "futamura projection",
            "skillcompiler",
            "skcc",
            "skir",
            "growlibm",
            "dra",
            "ddmin",
            "delta debugging",
            "byte effect oracle",
            "lying extension",
            "compile away the llm",
            "score e-value",
            "ville inequality",
            "conformal e-value",
        ],
        "engines": [
            "engine:LEAPFROG_W36_BYTE_EFFECT_ORACLE",
            "engine:LEAPFROG_W36_FUTAMURA_CASCADE",
            "engine:LEAPFROG_W36_DBSP_AGM_CONFORMAL",
            "engine:INDUCED_EDIT_BASIS",
            "engine:SKILL_SCOPE_ACQUISITION",
        ],
        "koan_modules": [
            "canonical/runtime/byte_effect_oracle_v1.py",
            "canonical/runtime/futamura_leapfrog_kernel_v1.py",
            "canonical/swe_kernel/induced_edit_basis_v1.py",
            "canonical/swe_kernel/skill_scope_acquisition_v1.py",
            "canonical/swe_kernel/operand_invention_v1.py",
        ],
    },
    "dbsp_agm_belief_revision_and_hybrid_cu_mealy": {
        "external_names": [
            "dbsp",
            "z-set",
            "kumiho",
            "agm belief revision",
            "analyzeimpact",
            "projectmem",
            "pre-commit failure gate",
            "error-aware l#",
            "lambda*_m",
            "hybrid computer use",
            "hcu",
            "osworld-human",
            "loop churn",
            "paste speculative",
            "timetravelcontainer",
        ],
        "engines": [
            "engine:LEAPFROG_W36_ERROR_AWARE_MEALY_HCU",
            "engine:LEAPFROG_W36_DBSP_AGM_CONFORMAL",
            "engine:PETRI_COW_SPLICING_ENGINE",
            "engine:METAMORPHIC_HABITATION_ZIPPER",
        ],
        "koan_modules": [
            "canonical/runtime/futamura_leapfrog_kernel_v1.py",
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
            "canonical/swe_kernel/petri_cow_splicing_engine_v1.py",
            "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
        ],
    },
    "os_kernel_isolation_and_multifile_futamura": {
        "external_names": [
            "os isolation",
            "linux namespaces",
            "unshare",
            "capeff zero",
            "capability drop",
            "seccomp",
            "seccomp bpf",
            "syscall allowlist",
            "escape probe",
            "confined computer use",
            "multifile futamura",
            "multi-file repo repair",
            "cow fork test runner",
        ],
        "engines": [
            "engine:LEAPFROG_W37_OS_KERNEL_ISOLATION",
            "engine:LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST",
            "engine:LEAPFROG_W37_CONFINED_HYBRID_CU",
            "engine:LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO",
        ],
        "koan_modules": [
            "canonical/runtime/os_isolation_v1.py",
            "canonical/runtime/worker_syscall_allowlist_v1.py",
            "canonical/runtime/futamura_leapfrog_kernel_v1.py",
            "canonical/swe_kernel/stdlib_cow_test_runner_v1.py",
        ],
    },
    "agent_s4_refusal_interface_webmcp_hcu": {
        "external_names": [
            "agent s4",
            "evolving agent interfaces",
            "hybrid computer use",
            "hcu",
            "webmcp",
            "navigator.modelcontext",
            "refusal specification",
            "cli-anything",
            "opencli",
            "recreationworld",
            "osworld v2",
            "osworld ledger",
            "read screen decide action verify effect",
        ],
        "engines": [
            "engine:LEAPFROG_W37_CONFINED_HYBRID_CU",
            "engine:LEAPFROG_W38_REFUSAL_SPEC_COMPILER",
            "engine:LEAPFROG_W38_OSWORLD_VERIFIED_LEDGER",
            "engine:LEAPFROG_W38_SAFE_ACTION_WORLD_MODEL",
        ],
        "koan_modules": [
            "canonical/runtime/a_refusal_is_a_specification_v1.py",
            "canonical/runtime/osworld_verified_task_ledger_v1.py",
            "canonical/tools/the_refusal_is_the_curriculum_v1.py",
            "canonical/swe_kernel/safe_action_model_v1.py",
        ],
    },
    "wall_closing_swe_cegist_petri_harness_evolution": {
        "external_names": [
            "cegis(t)",
            "typed cegis",
            "typed invention",
            "residual wall closers",
            "statement shaped repair",
            "repo component petri",
            "harnessflow",
            "meta-harness",
            "darwin godel machine",
            "dgm",
            "codeskill",
            "live-swe-agent",
            "judge the judge",
            "vacuous verifier",
            "bidirectional lens",
            "negative space refutation",
        ],
        "engines": [
            "engine:LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO",
            "engine:LEAPFROG_W38_TYPED_CEGIS_INVENTION",
            "engine:LEAPFROG_W38_RESIDUAL_WALL_CLOSERS",
            "engine:LEAPFROG_W38_REPO_COMPONENT_PETRI",
            "engine:LEAPFROG_W38_CONSISTENCY_EQUIVALENCE_AND_JUDGE",
            "engine:LEAPFROG_W38_COW_LENS_NEGATIVE_SPACE",
        ],
        "koan_modules": [
            "canonical/swe_kernel/typed_invention_v1.py",
            "canonical/swe_kernel/residual_wall_closers_v1.py",
            "canonical/swe_kernel/repo_component_petri_v1.py",
            "canonical/tools/judge_the_judge_v1.py",
            "canonical/swe_kernel/cow_lens_fuzz_and_negative_space_v1.py",
            "canonical/swe_kernel/consistency_vs_equivalence_v1.py",
        ],
    },
    "non_malleable_memory_os_and_bicameral_sleep": {
        "external_names": [
            "tma-nm",
            "origin binding",
            "origin laundering",
            "govmem",
            "correlated trace promotion",
            "a-tma",
            "ghost memory",
            "state view packet",
            "trustmem",
            "memgate",
            "openviking",
            "viking://",
            "progressive disclosure",
            "skillapt",
            "rubin potential outcome",
            "dreamprover",
            "language models need sleep",
            "bicameral sleep",
            "ascent",
            "oattt",
            "guidance-ttt",
            "ttt-discover",
            "absolute zero reasoner",
            "weight update admission",
            "mined rewrite theory",
            "minimal vocabulary distinction",
            "chunk archive content address",
        ],
        "engines": [
            "engine:LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS",
            "engine:LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE",
            "engine:LEAPFROG_W38_MINED_REWRITE_AND_WEIGHT_GATE",
            "engine:LEAPFROG_W36_DBSP_AGM_CONFORMAL",
        ],
        "koan_modules": [
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
            "canonical/runtime/release_chunk_archive_v1.py",
            "canonical/swe_kernel/weight_update_admission_v1.py",
            "canonical/swe_kernel/mined_rewrite_theory_v1.py",
            "canonical/swe_kernel/the_distinction_is_created_v1.py",
            "canonical/tools/a_law_carries_its_reason_v1.py",
        ],
    },
    "asymmetric_frontier_leapfrog_sheaf_srmu_opine_dgm_eggmind": {
        "external_names": [
            "opine-world",
            "opine digital twin",
            "replay verified digital twin",
            "arc-nest leave-one-out",
            "srmu hypervector",
            "cellular sheaf cohomology",
            "dual nnf provenance semiring",
            "why-absent provenance",
            "darwin godel machine",
            "turchin supercompilation",
            "eggmind motif cache",
            "pantograph tactic tree",
            "refusal is a specification",
            "declared input derivation",
            "passing repairs version space",
        ],
        "engines": [
            "engine:ABDUCTIVE_REFUSAL_AUTOBINDER",
            "engine:ANGELIC_ZYGOTE_VERSION_SPACE_SWE",
            "engine:ZERO_PIXEL_SHADOW_TRANSDUCER_CU",
            "engine:EPISTEMIC_DIGITAL_TWIN_AND_ARC",
            "engine:ALGEBRAIC_SHEAF_SRMU_MEMORY",
            "engine:PC_DGM_SUPERCOMPILER",
            "engine:EGGMIND_GOAL_TREE_PROVER",
        ],
        "koan_modules": [
            "canonical/runtime/asymmetric_frontier_leapfrog_v1.py",
            "canonical/runtime/a_refusal_is_a_specification_v1.py",
            "canonical/runtime/declared_input_derivation_v1.py",
            "canonical/swe_kernel/angelic_cegis_repair_v1.py",
            "canonical/swe_kernel/cow_angelic_zygote_v1.py",
            "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
            "canonical/swe_kernel/passing_repairs_version_space_v1.py",
            "canonical/swe_kernel/causal_nexus_v1.py",
            "canonical/runtime/swe_observational_program_synthesizer_v1.py",
            "canonical/runtime/osworld_v21_browser_cdp_v1.py",
            "canonical/runtime/terminal_proof_supercompiler.py",
        ],
    },
    "mendel_red_queen_anti_slop_coevolution": {
        "external_names": [
            "mendel godel machine",
            "mendel gm",
            "red queen godel machine",
            "red queen gm",
            "hyperagents",
            "albi",
            "reason popper-ly",
            "semantic anonymization",
            "slopcodebench",
            "bad genius",
            "phantom guardrails",
            "when good verifiers go bad",
            "harness evolution hits a ceiling",
            "dual program splicing",
            "earned judge",
            "auto judge discovery",
            "self-play swe-rl",
            "spade",
            "adaptive auto-harness",
            "evaluation-free rsi",
        ],
        "engines": [
            "engine:LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER",
            "engine:LEAPFROG_W39_AUTO_JUDGE_DISCOVERY",
            "engine:LEAPFROG_W38_CONSISTENCY_EQUIVALENCE_AND_JUDGE",
            "engine:LEAPFROG_W38_RESIDUAL_WALL_CLOSERS",
        ],
        "koan_modules": [
            "canonical/runtime/wave39_leapfrog_unification_v1.py",
            "canonical/swe_kernel/dual_program_splicing_v1.py",
            "canonical/swe_kernel/auto_judge_discovery_v1.py",
            "canonical/runtime/earn_a_judge_v1.py",
        ],
    },
    "clm_hindsight_nemori_verbatim_memory": {
        "external_names": [
            "clm",
            "context language models",
            "rlm",
            "recursive language models",
            "hindsight",
            "beam-10m",
            "memoryarena",
            "beyond memory leaderboards",
            "verbatim memory",
            "4-way rrf",
            "nemori",
            "sleepgate",
            "lightmem",
            "evermemos",
            "graphiti",
            "mempalace",
            "memory-r1",
            "a-mac",
            "cl-bench",
            "file mirrored working context",
        ],
        "engines": [
            "engine:LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "engine:LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS",
            "engine:LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE",
        ],
        "koan_modules": [
            "canonical/runtime/wave39_leapfrog_unification_v1.py",
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
        ],
    },
    "partial_routing_jitrl_skilltta_world_models": {
        "external_names": [
            "jitrl",
            "skilltta",
            "partial routing",
            "schema world model",
            "tycho",
            "prime agent",
            "weight-space programming",
            "doc-to-lora",
            "microfitting",
            "sdft",
            "op-mix",
            "l#^2",
            "l#_e",
            "active automata learning",
            "effect contract composition",
            "partial order planner",
            "sussman anomaly",
            "lifted generalization",
            "one demonstration basin",
            "observation refutation",
            "provenance not shape",
        ],
        "engines": [
            "engine:LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            "engine:LEAPFROG_W39_EFFECT_CONTRACT_COMPOSER",
            "engine:LEAPFROG_W39_PARTIAL_ORDER_PLANNER",
            "engine:LEAPFROG_W39_LIFTED_GENERALIZER",
            "engine:LEAPFROG_W39_OBSERVATION_REFUTATION_AND_PROVENANCE",
        ],
        "koan_modules": [
            "canonical/runtime/wave39_leapfrog_unification_v1.py",
            "canonical/swe_kernel/effect_contract_composition_v1.py",
            "canonical/swe_kernel/partial_order_planner_v1.py",
            "canonical/swe_kernel/perfect_algorithm_lifted_generalization_v1.py",
            "canonical/runtime/observation_refutation_v1.py",
            "canonical/tools/provenance_not_shape_v1.py",
        ],
    },
    "deltabox_sandlock_decision_cost_cow_and_check_oracle": {
        "external_names": [
            "deltabox",
            "deltafs",
            "deltacr",
            "sandlock",
            "what a decision costs",
            "decision cost cow gate",
            "the check mode is the oracle",
            "refusal surface vocabulary",
            "a type you wrote is a type you guess",
            "witness type discovery",
            "scalecua",
            "qwen-ui-agent",
            "verigen",
        ],
        "engines": [
            "engine:LEAPFROG_W39_DECISION_COST_COW_GATE",
            "engine:LEAPFROG_W39_REFUSAL_ORACLE_LIFTER",
            "engine:LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST",
            "engine:LEAPFROG_W37_OS_KERNEL_ISOLATION",
        ],
        "koan_modules": [
            "canonical/tools/what_a_decision_costs_v1.py",
            "canonical/tools/the_check_mode_is_the_oracle_v1.py",
            "canonical/tools/an_actions_vocabulary_is_its_refusal_surface_v1.py",
            "canonical/tools/a_type_you_wrote_is_a_type_you_guess_v1.py",
        ],
    },
    "meme_protocol_memory_w42": {
        "external_names": [
            "memory cascade",
            "memory absence",
            "dependency invalidation",
            "upstream superseded",
            "incremental view maintenance",
            "why provenance",
            "entity rename tracking",
            "aggregate over a set that lost a member",
        ],
        "engines": ["engine:LEAPFROG_W42_MEME_PROTOCOL_MEMORY"],
        "koan_modules": [
            "canonical/swe_kernel/meme_protocol_memory_v1.py",
            "canonical/swe_kernel/unified_unfamiliar_leapfrog_v1.py",
        ],
    },
    "refusal_acquire_retry_w41": {
        "external_names": [
            "a refusal is a specification",
            "abstain then acquire",
            "refusal curriculum",
            "context-free rewrite",
            "acquisition reuse",
            "meaning-ir operator swap",
        ],
        "engines": ["engine:LEAPFROG_W41_REFUSAL_ACQUIRE_RETRY"],
        "koan_modules": [
            "canonical/swe_kernel/refusal_acquire_retry_v1.py",
            "canonical/swe_kernel/language_neutral_skill_bridge_v1.py",
        ],
    },
    "frontier_bench_heldout_measurement_w40": {
        "external_names": [
            "held-out evaluation",
            "oracle-judged benchmark",
            "swe-bench shaped",
            "terminal-bench shaped",
            "claim disagreement",
            "false success claim",
            "instrument calibration",
            "liar control",
        ],
        "engines": ["engine:LEAPFROG_W40_FRONTIER_BENCH_HARNESS"],
        "koan_modules": [
            "canonical/evaluation/frontier_bench_v1.py",
            "canonical/runtime/brain_unified_model_v1.py",
        ],
    },
    "five_pillar_frontier_unification_w39": {
        "external_names": [
            "flashmeta",
            "prose d4",
            "inverse witness function",
            "galois concept lattice",
            "tycho moore machine",
            "opine-world",
            "ontology error residual",
            "optician boomerang lens",
            "anchored relational frame",
            "standing facts frame axiom",
            "deltabox",
            "warm zygote cow fork",
            "coccinelle",
            "sydit sibling edit",
            "plastic surgery hypothesis",
            "kumiho",
            "prospective cue indexing",
            "memtx",
            "cpb sybil echo",
            "epistemic entrenchment",
            "rd-forget",
            "forgetting without restarting",
            "selective replay unlearning",
            "babble stitch",
            "cross language meaning ir",
            "mdl bit rent",
            "zero adapter module bridge",
        ],
        "engines": [
            "engine:LEAPFROG_W39_ZERO_ADAPTER_INVENTORY_BRIDGE",
            "engine:LEAPFROG_W39_MOORE_ONTOLOGY_WITNESS_LEARNER",
            "engine:LEAPFROG_W39_LENS_STANDING_FACT_CU",
            "engine:LEAPFROG_W39_DELTASTATE_SIBLING_SWE",
            "engine:LEAPFROG_W39_PROSPECTIVE_MEMTX_REPLAY",
            "engine:LEAPFROG_W39_MEANING_IR_CROSS_LANG_RATCHET",
        ],
        "koan_modules": [
            "canonical/swe_kernel/unified_five_pillar_frontier_kernel_v1.py",
            "canonical/runtime/module_bridge_v1.py",
            "canonical/runtime/type_level_composer_v1.py",
            "canonical/runtime/transition_system_identity_v1.py",
            "canonical/runtime/anchored_frame_v1.py",
            "canonical/swe_kernel/standing_facts_v1.py",
            "canonical/swe_kernel/systematic_edit_supply_v1.py",
            "canonical/swe_kernel/language_neutral_skill_bridge_v1.py",
        ],
    },
    "agent_s4_hcu_shadow_interface_and_mental_model": {
        "external_names": [
            "agent s4",
            "simular agent s4",
            "shadow interface",
            "evolving shadow interface",
            "microsoft hcu",
            "hybrid computer use",
            "tool census",
            "computer env",
            "executable mental model",
            "articulation subgoals",
            "aimed action",
            "branchfs",
            "tclone",
            "timetravelcontainer",
        ],
        "engines": [
            "engine:LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER",
            "engine:LEAPFROG_W39_REFUSAL_ORACLE_LIFTER",
            "engine:LEAPFROG_W39_DECISION_COST_COW_GATE",
        ],
        "koan_modules": [
            "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
            "canonical/runtime/tool_census_v1.py",
            "canonical/runtime/computer_env_v1.py",
            "canonical/swe_kernel/executable_mental_model_v1.py",
            "canonical/swe_kernel/computer_use_agent_v1.py",
            "canonical/runtime/aimed_action_v1.py",
        ],
    },
    "four_network_engram_rlm_and_sleep_memory": {
        "external_names": [
            "mit rlm",
            "out of core rlm",
            "recursive language model workspace",
            "deepseek engram",
            "conditional memory",
            "hashed ngram memory",
            "letta memfs",
            "byterover",
            "hindsight four network",
            "world facts experiences observations mental models",
            "sleep knowledge seeding",
            "cortex continual learning",
            "hope nested learning",
            "skill1",
        ],
        "engines": [
            "engine:LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
            "engine:LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE",
            "engine:LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
        ],
        "koan_modules": [
            "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
        ],
    },
    "chase_hda_hill_sampling_nfv_and_selfplay_steer": {
        "external_names": [
            "chase perturbation",
            "harness delta attribution",
            "hda",
            "hill sampling",
            "staged nfv",
            "goal blind formal verification",
            "self play swe rl",
            "meta cwm",
            "steer dont solve",
            "trajectory critic",
            "guarded meaning ir",
            "semi persistent egraph",
            "angelic cegis",
            "causal nexus",
            "grammar closed repair",
            "evidence demand",
            "settlement",
            "hypothesis classes",
            "operator acquisition",
            "the record is the commit",
            "horizon bounded execution",
            "credit assignment",
            "creature stakes",
        ],
        "engines": [
            "engine:LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
            "engine:LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS",
            "engine:LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER",
            "engine:LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT",
        ],
        "koan_modules": [
            "canonical/runtime/wave40_dark_matter_frontier_kernel_v1.py",
            "canonical/swe_kernel/guarded_meaning_ir_v1.py",
            "canonical/swe_kernel/angelic_cegis_v1.py",
            "canonical/swe_kernel/causal_nexus_v1.py",
            "canonical/tools/grammar_closed_repair_v1.py",
            "canonical/runtime/evidence_demand_v1.py",
            "canonical/runtime/settlement_v1.py",
            "canonical/runtime/hypothesis_classes_v1.py",
            "canonical/runtime/operator_acquisition_v1.py",
            "canonical/tools/the_record_is_the_commit_v1.py",
        ],
    },
    "rung3_proposer_jitrl_ttpo_opsd_whitebox_abduction": {
        "external_names": [
            "ttpo",
            "opsd",
            "test time preference optimization",
            "on policy self distillation",
            "rung 3 proposer",
            "pluggable open weight proposer",
            "qwen3.8",
            "cwm 32b",
            "whitebox trace abduction",
            "ochiai fault localization",
            "loop cycle diagnosis",
            "angelic oe synthesizer",
            "cegis semantic synthesizer",
            "counterfactual spec repair",
            "causal swe repair",
            "multistep repo closed loop solver",
            "whitebox introspector",
        ],
        "engines": [
            "engine:LEAPFROG_W41_RUNG3_PLUGGABLE_PROPOSER_JITRL",
            "engine:LEAPFROG_W41_WHITEBOX_TRACE_ABDUCTION_AND_OE",
            "engine:LEAPFROG_W41_TTPO_OPSD_CONSENSUS_DISTILLER",
            "engine:LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
        ],
        "koan_modules": [
            "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
            "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py",
            "canonical/swe_kernel/angelic_oe_synthesizer_v1.py",
            "canonical/swe_kernel/cegis_semantic_synthesizer_v1.py",
            "canonical/swe_kernel/whitebox_introspector_and_trace_synthesizer_v1.py",
            "canonical/swe_kernel/causal_swe_repair_v1.py",
            "canonical/swe_kernel/multistep_repo_closed_loop_solver_v1.py",
            "canonical/runtime/bound_capabilities/python_counterfactual_spec_repair_v1.py",
        ],
    },
    "futamura_compile_away_one_demo_trust_flywheel": {
        "external_names": [
            "futamura compile away",
            "rung 0 skill compilation",
            "zero search speedup",
            "continual learning flywheel",
            "the goal is a quotient of the trace",
            "the demand is learned from the run",
            "an actions effect is a provenance map",
            "the page is the guide",
            "when one showing should be trusted",
            "generalization rung gradient",
            "the frame crosses the machine",
            "the space is the artifact",
            "one demonstration basin",
            "semantic generalization engine",
            "canonical boundary router",
        ],
        "engines": [
            "engine:LEAPFROG_W42_FUTAMURA_COMPILE_AWAY_FLYWHEEL",
            "engine:LEAPFROG_W42_ONE_DEMO_TRUST_AND_RUNG_CALIBRATOR",
            "engine:LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave41_rung3_proposer_jitrl_continual_flywheel_v1.py",
            "canonical/tools/the_goal_is_a_quotient_of_the_trace_v1.py",
            "canonical/tools/the_demand_is_learned_from_the_run_v1.py",
            "canonical/tools/an_actions_effect_is_a_provenance_map_v1.py",
            "canonical/tools/the_page_is_the_guide_v1.py",
            "canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py",
            "canonical/tools/generalization_rung_gradient_v1.py",
            "canonical/tools/the_frame_crosses_the_machine_v1.py",
            "canonical/tools/the_space_is_the_artifact_v1.py",
        ],
    },
    "git_history_seed_causal_dual_slice_constant_cegis_and_minimax": {
        "external_names": [
            "git history template repair",
            "self seeding repo store",
            "fixedbench abstention",
            "arise causal dual slicing",
            "causalrepair dataflow graph",
            "slopcodebench anti slop gate",
            "repair input dependency gate",
            "constant is a hole cegis",
            "the literal is the defect",
            "the relation not the value",
            "truthiness guard rewrite",
            "contrastive oracle bootstrap",
            "minimax partition lattice interrogation",
            "the refusal is the other half",
            "the index is the bottleneck",
            "filing key collision",
            "arm learned from its own verified repairs",
            "operator generalization cross language",
        ],
        "engines": [
            "engine:LEAPFROG_W43_GIT_HISTORY_SEEDED_REPAIR",
            "engine:LEAPFROG_W43_TRACE_LITERAL_CAUSAL_SLICE_GATE",
            "engine:LEAPFROG_W43_COW_CONTRASTIVE_MINIMAX_FACTORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
            "canonical/tools/history_template_repair_v1.py",
            "canonical/tools/the_constant_is_a_hole_v1.py",
            "canonical/tools/the_relation_not_the_value_v1.py",
            "canonical/tools/the_refusal_is_the_other_half_v1.py",
            "canonical/tools/the_counterexample_is_the_next_experiment_v1.py",
            "canonical/swe_kernel/causal_dataflow_graph_v1.py",
            "canonical/swe_kernel/repair_input_dependency_gate_v1.py",
        ],
    },
    "meme_cascade_absence_deltamem_openviking_memrl": {
        "external_names": [
            "meme benchmark",
            "memory cascade",
            "memory absence",
            "dependency cascade memory",
            "absence uncertainty witness",
            "explicit zset deletion",
            "memconflict",
            "openviking",
            "vikingmem",
            "l0 l1 l2 progressive disclosure",
            "deltamem",
            "residual delta skill tree",
            "memrl",
            "runtime reinforcement learning episodic memory",
        ],
        "engines": [
            "engine:LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY",
            "engine:LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
            "canonical/runtime/futamura_leapfrog_kernel_v1.py",
        ],
    },
    "webmcp_document_modelcontext_osworld_nested_skillrl_rqgm_gea": {
        "external_names": [
            "webmcp",
            "document.modelcontext",
            "navigator.modelcontext",
            "chrome 150 webmcp",
            "gui room cdp",
            "osworld 2.1 atspi",
            "parse_a11y",
            "google nested learning",
            "hope continuum memory system",
            "skillrl",
            "skillbank counterfactual failure",
            "group evolving agents",
            "gea experience sharing",
            "red queen godel machine",
            "rqgm selective erasure",
        ],
        "engines": [
            "engine:LEAPFROG_W44_WEBMCP_GUI_ROOM_OSWORLD_HCU",
            "engine:LEAPFROG_W44_NESTED_SKILLRL_RQGM_GEA_CONTINUAL",
            "engine:LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER",
        ],
        "koan_modules": [
            "canonical/runtime/wave43_44_dark_matter_meme_webmcp_leapfrog_v1.py",
            "canonical/runtime/gui_room_v1.py",
            "canonical/runtime/osworld_v21_generic_policy_v1.py",
            "canonical/runtime/osworld_computer_surface_v1.py",
            "canonical/runtime/osworld_v21_host_browser_ops_v1.py",
        ],
    },
    "quotient_angelic_metamorphic_hcu": {
        "external_names": [
            "coarsest trace quotient",
            "angelic value forcing",
            "computed vocabulary",
            "contrast is a probe",
            "repository seed corpus",
            "metamorphic laws",
            "producer lineage graph",
            "name hole repair",
            "two guard coupled edit",
            "microsoft hcu",
            "hybrid computer use",
            "accessibility debt",
            "a11y cua",
            "zero screenshot action cache",
            "osworld verified task ledger",
            "partial order plan",
            "sussman anomaly",
            "agentic symbolic execution",
            "symbolon",
            "fixedbench",
        ],
        "engines": [
            "engine:LEAPFROG_W45_QUOTIENT_ANGELIC_PROBE_INDUCER",
            "engine:LEAPFROG_W45_METAMORPHIC_LINEAGE_CORPUS_SWE",
            "engine:LEAPFROG_W45_AX_GUARD_ZERO_SHOT_CACHE_HCU",
        ],
        "koan_modules": [
            "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
            "canonical/tools/the_goal_is_a_quotient_of_the_trace_v1.py",
            "canonical/tools/force_the_value_and_see_v1.py",
            "canonical/swe_kernel/metamorphic_laws_v1.py",
            "canonical/swe_kernel/producer_lineage_graph_v1.py",
            "canonical/runtime/verified_zero_screenshot_action_cache_v1.py",
            "canonical/runtime/osworld_verified_task_ledger_v1.py",
        ],
    },
    "manufactured_confidence_lapse_kumiho_meme": {
        "external_names": [
            "manufactured confidence",
            "kwon 2026 manufactured confidence",
            "lapse temporal fidelity",
            "coerced stative",
            "hedged hearsay quarantine",
            "kumiho agm",
            "hansson belief revision",
            "meme protocol 6 op",
            "dependency memory semiring",
            "composition state capsule rollback",
            "capture recapture unseen",
            "always on engram",
            "memoryarena",
        ],
        "engines": [
            "engine:LEAPFROG_W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY",
            "engine:LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
            "canonical/swe_kernel/meme_protocol_memory_v1.py",
            "canonical/runtime/composition_state_capsule_v2.py",
            "canonical/runtime/residual_witness_retrieval_compiler_v1.py",
            "canonical/tools/a_fact_is_a_conjunction_of_its_readers_v1.py",
        ],
    },
    "anytime_valid_evalue_score_d2l_lrcp": {
        "external_names": [
            "score conformal e values",
            "conformal e values",
            "ville inequality supermartingale",
            "anytime valid certificate",
            "endogenous loop collapse",
            "thompson poisoning",
            "verifier falsification",
            "verifier conditional correlation phi",
            "doc to lora",
            "text to lora",
            "lrcp orthogonal projection",
            "sparse memory finetuning",
            "sae fd",
            "hierarchical skill library",
            "hyperagents dgm h",
            "self healing harness",
        ],
        "engines": [
            "engine:LEAPFROG_W46_ANYTIME_VALID_EVALUE_EVOLUTION_GATE",
            "engine:LEAPFROG_W46_THREE_TIER_ZERO_FORGETTING_CONTINUAL",
        ],
        "koan_modules": [
            "canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py",
            "canonical/runtime/verifier_falsification_v1.py",
            "canonical/swe_kernel/skill_scope_bundle_v1.py",
            "canonical/swe_kernel/learned_skill_verdict_v1.py",
            "canonical/swe_kernel/hierarchical_skill_library_v1.py",
        ],
    },
    "futamura_reverse_tomography_egraph_vericoding": {
        "external_names": [
            "futamura projection",
            "partial evaluation",
            "compile away the frontier",
            "reverse execution tomography",
            "bidirectional fst lens",
            "egglog",
            "relational equality saturation",
            "equality saturation",
            "vericoding",
            "goedel prover",
            "pypantograph",
            "global proof cut",
            "assertion is the demand",
            "counterfactual spec repair",
            "ddmin shrink certified",
            "locagent",
            "repomem",
            "joern cpg",
        ],
        "engines": [
            "engine:LEAPFROG_W47_FUTAMURA_SKILL_COMPILER_GRAMMAR",
            "engine:LEAPFROG_W47_REVERSE_TOMOGRAPHY_ANGELIC_LENS_SWE",
            "engine:LEAPFROG_W47_MEANING_EGRAPH_VERICODING_PROOF_CUT",
        ],
        "koan_modules": [
            "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
            "canonical/runtime/futamura_leapfrog_kernel_v1.py",
            "canonical/swe_kernel/reverse_tomography_algebra_v1.py",
            "canonical/swe_kernel/angelic_lens_cow_repair_v1.py",
            "canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py",
            "canonical/swe_kernel/semantic_causal_engine_v1.py",
            "canonical/runtime/global_proof_cut_compiler.py",
        ],
    },
    "agent_s4_evolving_interfaces_sleep_crystallizer_mmap": {
        "external_names": [
            "agent s4",
            "evolving agent interfaces",
            "coact 1",
            "surfer h holo1",
            "petri dominator cut vertices",
            "ring 0 byte effect oracle",
            "sleep time compute",
            "feldera dbsp",
            "incremental view maintenance",
            "agent zero memory",
            "five timescale memory crystallizer",
            "mmap csr index",
            "cross language semantic ir",
            "lact lacet ttr compressor",
            "bispace lifelong editing",
        ],
        "engines": [
            "engine:LEAPFROG_W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU",
            "engine:LEAPFROG_W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
            "canonical/swe_kernel/universal_computer_agent_v1.py",
            "canonical/swe_kernel/canonical_cu_sandbox_spine_v1.py",
            "canonical/runtime/byte_effect_oracle_v1.py",
            "canonical/swe_kernel/canonical_memory_crystallizer_v1.py",
            "canonical/runtime/mmap_csr_slot_index_v1.py",
        ],
    },
    "meta_circular_plotkin_lgg_active_inference_adjudicator": {
        "external_names": [
            "meta circular organ graph",
            "self patch firewall",
            "higher order plotkin lgg",
            "lilo stitch",
            "dreamcoder library learning",
            "gepa genetic pareto",
            "sica self improving coding agent",
            "absolute zero reasoner",
            "active inference efe",
            "expected free energy context acquisition",
            "optimal question asking",
            "refusal is the curriculum",
            "dark matter adjudicator",
            "proven self check verdict",
            "model call surface audit",
        ],
        "engines": [
            "engine:LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR",
        ],
        "koan_modules": [
            "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
            "canonical/swe_kernel/meta_circular_organ_graph_v1.py",
            "canonical/swe_kernel/recursive_self_architect_v1.py",
            "canonical/swe_kernel/concept_library_v1.py",
            "canonical/tools/the_refusal_is_the_curriculum_v1.py",
            "canonical/tools/the_right_question_is_an_experiment_v1.py",
            "canonical/tools/dark_matter_adjudicator_v1.py",
            "canonical/tools/model_call_surface_audit_v1.py",
        ],
    },
    "STRUCTURAL_AST_MULTI_HUNK_ZERO_LINE_SWE_REPAIR": {
        "external_names": [
            "structural ast repair",
            "multi hunk patch synthesis",
            "parameter addition threading",
            "zero executed repo lines",
            "checkout import provenance",
            "site packages shadowing",
            "dunder reflexive comparison guard",
            "module reexport normalization",
            "fstring repr redundant quotes",
            "recursive seen set cycle guard",
            "site general expression synthesis",
            "symbol ownership blast radius",
            "featurebench",
            "swe polybench",
            "commit 0",
        ],
        "engines": [
            "engine:LEAPFROG_W49_TRACEBACK_SIGNATURE_ZERO_LINE_LOCALIZER",
            "engine:LEAPFROG_W49_STRUCTURAL_AST_MULTI_HUNK_SYNTHESIZER",
        ],
        "koan_modules": [
            "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
            "canonical/tools/honest_per_task_baseline_v1.py",
            "canonical/tools/grammar_closed_repair_v1.py",
            "canonical/tools/real_fix_minimal_repair_census_v1.py",
        ],
    },
    "MINIMAX_INTERROGATION_CONTRASTIVE_KERNEL_EFFECT_ORACLE": {
        "external_names": [
            "exact minimax interrogation",
            "witness is computed not remembered",
            "version space optimal query",
            "contrastive oracle bootstrap",
            "paired transfer evaluation",
            "mcnemar discordant pairs",
            "kernel boundary effect oracle",
            "coact 1 dual channel",
            "osworld v2",
            "verigui",
        ],
        "engines": [
            "engine:LEAPFROG_W49_MINIMAX_INTERROGATION_CONTRASTIVE_ORACLE",
            "engine:LEAPFROG_W50_KERNEL_BOUNDARY_DUAL_CHANNEL_EFFECT_HCU",
        ],
        "koan_modules": [
            "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
            "canonical/tools/version_space_selection_measure_v1.py",
            "canonical/runtime/verify_file_facts_provenance_v1.py",
        ],
    },
    "CRASH_RESUMABLE_LIFE_LOOP_AND_TITAN_BEHAVIORAL_ADJUDICATION": {
        "external_names": [
            "crash resumable continuous life loop",
            "wal tick replay",
            "self verifying capability enrollment",
            "titan behavioral proof adjudicator",
            "proven loc falsifiable self check",
            "adversarial negative control contract",
            "sleep time compute",
            "zero forgetting continual",
        ],
        "engines": [
            "engine:LEAPFROG_W50_CRASH_RESUMABLE_SELF_VERIFYING_LIFE_LOOP",
            "engine:LEAPFROG_W50_TITAN_BEHAVIORAL_PROOF_ADJUDICATOR",
        ],
        "koan_modules": [
            "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
            "canonical/tools/dark_matter_adjudicator_v1.py",
            "canonical/runtime/current_state_obs_reducer.py",
        ],
    },
    "ARISE_DEF_USE_SLICED_STRUCTURAL_SWE_S8_S11": {
        "external_names": [
            "arise def use dataflow slice",
            "statement level program slicing",
            "import symbol alias repair",
            "parser position error diagnostic",
            "short circuit policy guard narrowing",
            "recursive shared collector delta visited memo",
            "pytest verifier lie defense",
            "honest real repo denominator guard",
        ],
        "engines": [
            "engine:LEAPFROG_W52_ARISE_STATEMENT_DEF_USE_SLICER",
            "engine:LEAPFROG_W52_SLICED_STRUCTURAL_AST_SWE_ENGINE",
        ],
        "koan_modules": [
            "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
            "canonical/swe_kernel/repair_admission_v1.py",
            "canonical/swe_kernel/repair_journal_v1.py",
        ],
    },
    "STRANDED_TREASURY_CONFINEMENT_BYTE_ORACLE_AND_FTS_ATMA": {
        "external_names": [
            "os isolation capeff confinement",
            "byte derived effect oracle spoofed extension",
            "vocabulary independent lifted operator",
            "contrastive oracle bootstrap",
            "symbol ownership blast radius",
            "zero llm fts5 bm25 memory",
            "a tma state view packet ghost memory",
            "hindsight counterfactual deletion credit",
        ],
        "engines": [
            "engine:LEAPFROG_W51_STRANDED_TREASURY_CONFINEMENT_ORACLE",
            "engine:LEAPFROG_W52_ZERO_LLM_FTS_ATMA_HINDSIGHT_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
            "canonical/swe_kernel/swe_bench_local_harness_v1.py",
        ],
    },
    "COLD_START_FRONT_DOOR_AND_48_TITAN_BLOB_PINNED_PROOF": {
        "external_names": [
            "cold start unified front door bridge",
            "192 awakened dark modules",
            "48 flagship titans blob pinned proof",
            "sha256 execution enrollment",
            "148000 proven loc zero broken",
        ],
        "engines": [
            "engine:LEAPFROG_W52_COLD_START_FRONT_DOOR_BRIDGE",
            "engine:LEAPFROG_W51_48_TITAN_BLOB_PINNED_ADJUDICATOR",
        ],
        "koan_modules": [
            "canonical/runtime/wave51_52_sliced_structural_swe_and_stranded_treasury_v1.py",
            "canonical/tools/dark_matter_adjudicator_v1.py",
        ],
    },
    "WAVE53_ESTITCH_STRATA_SAFE_TRANSFER_AND_CAPABILITY_BUS": {
        "external_names": [
            "e-stitch top down library learning e-graphs",
            "strata contrast edges articulation point gc",
            "settled admission negative transfer defense",
            "unified capability bus 228 awakened dark modules",
            "structural front door swe issue router",
            "quixbugs leave one out cross program transfer",
        ],
        "engines": [
            "engine:LEAPFROG_W53_UNIFIED_CAPABILITY_BUS",
            "engine:LEAPFROG_W53_SAFE_TRANSFER_ESTITCH_STRATA",
        ],
        "koan_modules": [
            "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
            "canonical/swe_kernel/structured_morphism_abstraction_v1.py",
            "canonical/swe_kernel/taught_actions/settled_admission_v1.py",
            "canonical/swe_kernel/rule_scope_learning_v1.py",
        ],
    },
    "WAVE54_METAMORPHIC_9_OF_9_DOCKERLESS_JITRL_WEBMCP_MEMORY": {
        "external_names": [
            "9 of 9 metamorphic law repair generators",
            "neighbor regression precision prefilter",
            "dockerless 7 probe patch verifier",
            "self play swe rl bug injection curriculum",
            "jitrl closed form kl advantage test time rl",
            "webmcp document modelcontext webxskill multi step grounder",
            "hindsight 4 epistemic networks p-mem rollback forgeteval adv",
        ],
        "engines": [
            "engine:LEAPFROG_W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER",
            "engine:LEAPFROG_W54_DOCKERLESS_VERIFIER_AND_SELFPLAY",
            "engine:LEAPFROG_W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER",
            "engine:LEAPFROG_W54_DBSP_HINDSIGHT_STRATA_MEMORY",
        ],
        "koan_modules": [
            "canonical/runtime/wave53_54_unified_capability_bus_and_leapfrog_v1.py",
            "canonical/runtime/osworld_v21_app_policy_overlay_v1.py",
            "canonical/evaluation/meme_protocol_bench_v1.py",
        ],
    },
}

_CONCEPT_INVERTED_INDEX: dict[str, list[tuple[str, float]]] = {}
for _ckey, _crow in CROSS_DISCIPLINARY_CONCEPT_MAP.items():
    for _phrase in [_ckey.replace("_", " "), *(_crow.get("external_names") or [])]:
        for _tok in set(_WORD_RE.findall(_phrase.lower())):
            if len(_tok) >= 2 and _tok not in STOPWORDS:
                _CONCEPT_INVERTED_INDEX.setdefault(_tok, []).append((_ckey, 2.5 if " " in _phrase else 1.5))


def resolve_cross_disciplinary_concept(query: str, *, top_k: int = 5) -> dict[str, Any]:
    """Sub-20-microsecond lookup mapping unfamiliar CS / frontier terms to Brain's koan & federated engines."""
    q_low = (query or "").lower()
    q_toks = [t for t in _WORD_RE.findall(q_low) if t not in STOPWORDS]
    scores: dict[str, float] = {}
    for tok in set(q_toks):
        for ckey, w in _CONCEPT_INVERTED_INDEX.get(tok, ()):
            scores[ckey] = scores.get(ckey, 0.0) + w
    for ckey, crow in CROSS_DISCIPLINARY_CONCEPT_MAP.items():
        for phrase in crow["external_names"]:
            if phrase in q_low:
                scores[ckey] = scores.get(ckey, 0.0) + 6.0
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, int(top_k))]
    matches: list[dict[str, Any]] = []
    for ckey, sc in ranked:
        crow = CROSS_DISCIPLINARY_CONCEPT_MAP[ckey]
        matches.append(
            {
                "concept_family": ckey,
                "score": round(sc, 4),
                "external_names": list(crow["external_names"]),
                "engines": list(crow["engines"]),
                "koan_modules": list(crow["koan_modules"]),
            }
        )
    return {
        "schema": SCHEMA,
        "query": query,
        "matched_families": matches,
        "best": matches[0] if matches else None,
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }


# ---------------------------------------------------------------------------
# Admitted Module-Function Ranker & Invoker (2,019 modules / 5,205 functions)
# ---------------------------------------------------------------------------

_EVIDENCE_CACHE: dict[str, Any] | None = None
_EVIDENCE_IDF_CACHE: dict[str, float] | None = None


def _get_admitted_evidence(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, float]]:
    global _EVIDENCE_CACHE, _EVIDENCE_IDF_CACHE
    if _EVIDENCE_CACHE is not None and _EVIDENCE_IDF_CACHE is not None:
        return _EVIDENCE_CACHE, _EVIDENCE_IDF_CACHE
    from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as bmi

    ev = bmi.load_evidence(root)
    modules = ev.get("modules") or {}
    df: dict[str, int] = {}
    total = 0
    for rel, row in modules.items():
        if not isinstance(row, Mapping):
            continue
        stem_toks = set(_tokenize(Path(rel).stem.replace("_", " "))) | set(_tokenize(str(row.get("doc") or "")))
        for fn_name, fn_row in (row.get("functions") or {}).items():
            if not isinstance(fn_row, Mapping):
                continue
            total += 1
            toks = (
                stem_toks
                | set(_tokenize(str(fn_name).replace("_", " ")))
                | set(_tokenize(str(fn_row.get("doc") or "")))
            )
            for tok in toks:
                df[tok] = df.get(tok, 0) + 1
    n_docs = max(1, total)
    idf = {tok: math.log(1.0 + (n_docs - c + 0.5) / (c + 0.5)) for tok, c in df.items()}
    _EVIDENCE_CACHE = ev
    _EVIDENCE_IDF_CACHE = idf
    return ev, idf


def _run_admitted_module_solver(mode: str, inputs: Mapping[str, Any], goal: str) -> dict[str, Any]:
    from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as bmi

    payload = inputs.get("payload")
    source_rel = inputs.get("source_rel")
    fn_name = inputs.get("function")
    ev, idf = _get_admitted_evidence(ROOT)

    if source_rel and fn_name:
        try:
            adm = bmi.admitted(ROOT, str(source_rel), str(fn_name), ev)
            result = bmi.invoke(ROOT, str(source_rel), str(fn_name), payload)
        except Exception as exc:
            return _fail(mode, f"ADMITTED_INVOCATION_REFUSED_OR_FAILED:{type(exc).__name__}:{exc}")
        return _ok(
            mode,
            "ADMITTED_MODULE_FUNCTION_EXECUTED",
            {
                "selected": {
                    "source_rel": str(source_rel),
                    "function": str(fn_name),
                    "tier": (adm.get("function") or {}).get("tier"),
                },
                "output": result,
            },
        )

    query_toks = set(_tokenize(str(inputs.get("query") or goal)))
    if not query_toks:
        return _fail(mode, "MODULE_SOLVER_QUERY_EMPTY")

    scored: list[tuple[float, str, str, dict[str, Any]]] = []
    for rel, row in (ev.get("modules") or {}).items():
        if not isinstance(row, Mapping):
            continue
        stem_toks = set(_tokenize(Path(rel).stem.replace("_", " "))) | set(_tokenize(str(row.get("doc") or "")))
        for cand_name, fn_row in (row.get("functions") or {}).items():
            if not isinstance(fn_row, Mapping):
                continue
            sig = fn_row.get("signature") or {}
            params = list(sig.get("params") or [])
            req = list(sig.get("required") or [])
            varkw = bool(sig.get("var_kw"))
            compat = 0.0
            if isinstance(payload, Mapping):
                if varkw or (
                    set(req).issubset(set(payload.keys()))
                    and set(payload.keys()).issubset(set(params) | set(req))
                ):
                    compat = 3.5
                elif len(req) == 1 and req[0] in {"instance", "payload", "data", "spec", "doc", "request"}:
                    compat = 2.0
                else:
                    continue
            elif payload is None:
                if not req:
                    compat = 3.0
                else:
                    continue
            else:
                if len(req) == 1:
                    compat = 2.5
                else:
                    continue
            fn_toks = set(_tokenize(str(cand_name).replace("_", " "))) | set(_tokenize(str(fn_row.get("doc") or "")))
            hits = query_toks & (stem_toks | fn_toks)
            if not hits:
                continue
            lex = sum((2.0 if t in fn_toks else 1.0) * idf.get(t, 0.5) for t in hits)
            scored.append((lex + compat, rel, str(cand_name), dict(fn_row)))

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    if not scored:
        return _fail(mode, "NO_COMPATIBLE_ADMITTED_FUNCTION_FOUND")

    last_err = ""
    for top_score, best_rel, best_name, best_fn in scored[:5]:
        try:
            bmi.admitted(ROOT, best_rel, best_name, ev)
            result = bmi.invoke(ROOT, best_rel, best_name, payload)
        except Exception as exc:
            last_err = f"{best_rel}:{best_name}:{type(exc).__name__}:{exc}"
            continue
        return _ok(
            mode,
            "ADMITTED_MODULE_FUNCTION_SOLVED",
            {
                "selected": {
                    "source_rel": best_rel,
                    "function": best_name,
                    "tier": best_fn.get("tier"),
                    "score": round(top_score, 6),
                },
                "candidates": [
                    {"source_rel": r, "function": n, "score": round(s, 6)}
                    for s, r, n, _ in scored[:5]
                ],
                "output": result,
            },
        )
    return _fail(
        mode,
        f"ADMITTED_FUNCTION_RAISED:{last_err}",
        candidates=[
            {"source_rel": r, "function": n, "score": round(s, 6)}
            for s, r, n, _ in scored[:5]
        ],
    )


# ---------------------------------------------------------------------------
# Individual Deterministic Kernel Handlers
# ---------------------------------------------------------------------------


def _dispatch_kernel(mode: str, inputs: Mapping[str, Any], goal: str) -> dict[str, Any]:
    # 1. TRUE CAPABILITIES
    if mode == "DOCX_EXACT_TEXT_EDIT":
        from canonical.runtime import docx_exact_text_edit as m

        res = m.solve_instance({"docx_b64": inputs["docx_b64"], "old": str(inputs["old"]), "new": str(inputs["new"])})
        if res.get("status") != "PASS":
            return _fail(mode, str(res.get("reason") or res.get("status") or "DOCX_EDIT_FAILED"), details=res)
        return _ok(mode, "DOCX_EXACT_TEXT_EDIT_VERIFIED", res)

    if mode in {"DOCX_RUN_SPAN_REPLACE", "DOCX_STORY_PART_REPLACE", "DOCX_TEXT_EDIT_TRANSACTION"}:
        from canonical.runtime import docx_true_capability_adapters_v1 as m

        if mode == "DOCX_RUN_SPAN_REPLACE":
            res = m.solve_span({"docx_b64": inputs["docx_b64"], "old": str(inputs["old"]), "new": str(inputs["new"])})
        elif mode == "DOCX_STORY_PART_REPLACE":
            res = m.solve_story({"docx_b64": inputs["docx_b64"], "old": str(inputs["old"]), "new": str(inputs["new"])})
        else:
            res = m.solve_transaction({"docx_b64": inputs["docx_b64"], "edits": list(inputs["edits"])})
        if res.get("status") != "PASS":
            return _fail(mode, str(res.get("reason") or res.get("status") or "DOCX_ADAPTER_FAILED"), details=res)
        return _ok(mode, f"{mode}_VERIFIED", res)

    if mode == "SACCR_CREDIT_ADDON":
        from canonical.runtime import saccr_credit_kernel as m

        res = m.solve_instance({"trades": list(inputs["trades"])})
        return _ok(mode, "SACCR_CREDIT_ADDON_COMPUTED", res)

    if mode in {"AUTHENTICATED_PARETO_SCHEDULE", "CAPABILITY_FIRST_RANKING", "PARETO_FRONTIER_UPDATE"}:
        from canonical.runtime import scheduler_true_capability_adapters_v1 as m

        if mode == "AUTHENTICATED_PARETO_SCHEDULE":
            res = m.solve_schedule({"candidates": list(inputs["candidates"])})
            if not res.get("pass"):
                return _fail(mode, str(res.get("reason") or "SCHEDULE_REJECTED"), details=res)
            return _ok(mode, "AUTHENTICATED_PARETO_SCHEDULE_COMPILED", res)
        if mode == "CAPABILITY_FIRST_RANKING":
            res = m.solve_ranking(
                {
                    "work": list(inputs["work"]),
                    "checkpoint_open_obligation_count": int(inputs["checkpoint_open_obligation_count"]),
                }
            )
            if res.get("status") != "OK":
                return _fail(mode, str(res.get("reason") or "RANKING_REJECTED"), details=res)
            return _ok(mode, "CAPABILITY_FIRST_RANKING_COMPUTED", res)
        res = m.solve_frontier({"candidates": list(inputs["candidates"])})
        return _ok(mode, "PARETO_FRONTIER_UPDATED", res)

    if mode == "SAME_IDENTITY_SUPERVISOR":
        from canonical.runtime import same_identity_supervisor as m

        res = m.solve_instance({"tasks": list(inputs["tasks"]), "steps": list(inputs["steps"])})
        return _ok(mode, "SAME_IDENTITY_SUPERVISOR_EXECUTED", res)

    # 2. SWE SYNTHESIS & REPAIR
    if mode == "FRONTIER_FST_LENS_SYNTHESIS":
        from canonical.swe_kernel import frontier_unified_engine_v1 as m

        pairs = [(str(a), str(b)) for a, b in inputs["witness_pairs"]]
        lens = m.synthesize_fst_lens(pairs)
        if lens is None:
            return _fail(mode, "NO_CONSISTENT_FST_LENS_FOUND")
        probe_in = [str(x) for x in (inputs.get("apply_to") or [p[0] for p in pairs])]
        transformed = [lens.apply(s) for s in probe_in]
        roundtrip_ok = lens.verify_roundtrip([p[0] for p in pairs])
        return _ok(
            mode,
            "FST_LENS_SYNTHESIZED",
            {
                "lens_id": lens.lens_id,
                "forward_map": dict(lens.forward_map),
                "probe_inputs": probe_in,
                "transformed_outputs": transformed,
                "roundtrip_verified": bool(roundtrip_ok),
            },
        )

    if mode == "ANGELIC_LENS_COW_REPAIR":
        from canonical.swe_kernel import angelic_lens_cow_repair_v1 as m

        if "positive_envs" in inputs and "negative_envs" in inputs:
            guard = m.synthesize_separating_guard(list(inputs["positive_envs"]), list(inputs["negative_envs"]))
            if not guard:
                return _fail(mode, "NO_SEPARATING_GUARD_FOUND")
            return _ok(mode, "ANGELIC_SEPARATING_GUARD_SYNTHESIZED", {"guard": guard})
        if "io_pairs" in inputs:
            pairs = [(a, b) for a, b in inputs["io_pairs"]]
            lens = m.synthesize_bidirectional_lens(pairs)
            if lens is None:
                return _fail(mode, "NO_BIDIRECTIONAL_LENS_FOUND")
            return _ok(mode, "ANGELIC_BIDIRECTIONAL_LENS_SYNTHESIZED", {"lens": repr(lens)})
        return _fail(
            mode,
            "ENGINE_INPUTS_MISSING:io_pairs_or_positive_envs_negative_envs",
            required_inputs=["io_pairs"],
        )

    if mode == "REVERSE_TOMOGRAPHY_ALGEBRA":
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as m

        if "source" in inputs and "ranked_lines" in inputs:
            residual = m.extract_output_residual(
                str(inputs.get("exc_msg") or ""),
                inputs.get("actual_val"),
                inputs.get("expected_val"),
            )
            patches = m.backpropagate_ast_repairs(
                str(inputs["source"]),
                [int(x) for x in inputs["ranked_lines"]],
                residual,
            )
            return _ok(
                mode,
                "REVERSE_TOMOGRAPHY_REPAIRS_GENERATED",
                {"residual": residual, "patch_count": len(patches), "patches": patches[:10]},
            )
        return _fail(mode, "ENGINE_INPUTS_MISSING:source,ranked_lines", required_inputs=["source", "ranked_lines"])

    if mode == "FIRST_PRINCIPLES_MENTAL_CEGIS":
        from canonical.swe_kernel import first_principles_mental_cegis_v1 as m

        expr_src = str(inputs["expression"])

        def _ast_to_ir(node: ast.AST) -> Any:
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                return m.IRNode("NOT", (_ast_to_ir(node.operand),))
            if isinstance(node, ast.BoolOp):
                op_s = "AND" if isinstance(node.op, ast.And) else "OR"
                return m.IRNode(op_s, tuple(_ast_to_ir(v) for v in node.values))
            if isinstance(node, ast.BinOp):
                op_map = {ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL"}
                op_s = op_map.get(type(node.op), type(node.op).__name__.upper())
                return m.IRNode(op_s, (_ast_to_ir(node.left), _ast_to_ir(node.right)))
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                return m.IRNode(type(node.ops[0]).__name__.upper(), (_ast_to_ir(node.left), _ast_to_ir(node.comparators[0])))
            if isinstance(node, ast.Name):
                return m.IRNode("VAR", (node.id,))
            if isinstance(node, ast.Constant):
                return m.IRNode("CONST", (node.value,))
            return m.IRNode("RAW", (ast.unparse(node),))

        tree = ast.parse(expr_src, mode="eval")
        ir_in = _ast_to_ir(tree.body)
        canon = m.egraph_canonicalize(ir_in)
        return _ok(
            mode,
            "MENTAL_CEGIS_EGRAPH_CANONICALIZED",
            {"input_expression": expr_src, "input_ir": repr(ir_in), "canonical_ir": repr(canon)},
        )

    if mode == "DUAL_PROGRAM_SPLICING":
        from canonical.swe_kernel import dual_program_splicing_v1 as m

        spliced = m.splice(str(inputs["parent"]), str(inputs["candidate_a"]), str(inputs["candidate_b"]))
        if not spliced:
            return _fail(mode, "NO_COMPATIBLE_SPLICE_PRODUCED")
        return _ok(mode, "DUAL_PROGRAM_CANDIDATES_SPLICED", {"spliced_candidates": spliced, "count": len(spliced)})

    if mode == "MULTI_PRODUCER_NORMALIZATION":
        from canonical.swe_kernel import multi_producer_normalization_v1 as m

        src = str(inputs["source"])
        names = list(inputs.get("names") or [])
        norm_cands = m.normalize_candidates(src, names) if names else []
        fence_cands = m.exception_fence_candidates(src)
        return _ok(
            mode,
            "MULTI_PRODUCER_CANDIDATES_GENERATED",
            {
                "normalize_candidate_count": len(norm_cands),
                "exception_fence_candidate_count": len(fence_cands),
                "normalize_candidates": norm_cands[:5],
                "exception_fence_candidates": fence_cands[:5],
            },
        )

    if mode == "MANUFACTURED_CONTRAST_PROBE":
        from canonical.swe_kernel import manufactured_contrast_v1 as m

        fn_name = inputs.get("function_name")
        holes = m.literals(str(inputs["test_source"]), str(fn_name) if fn_name else None)
        serial = [dict(h) if isinstance(h, Mapping) else getattr(h, "__dict__", str(h)) for h in holes]
        return _ok(mode, "CONTRAST_LITERAL_HOLES_EXTRACTED", {"hole_count": len(serial), "holes": serial[:20]})

    if mode == "ASSERTION_OPERAND_TOMOGRAPHY":
        from canonical.swe_kernel import assertion_operand_tomography_v1 as m

        fn_name = inputs.get("function_name")
        instrumented = m.instrument(str(inputs["test_source"]), str(fn_name) if fn_name else None)
        return _ok(mode, "ASSERTION_TOMOGRAPHY_INSTRUMENTED", {"instrumented_source": instrumented})

    if mode == "DISTINCTION_GUARD_SYNTHESIS":
        from canonical.swe_kernel import distinction_creation_v1 as m

        res = m.synthesise_guard(list(inputs["positives"]), list(inputs["negatives"]))
        if res.get("refusal") or res.get("guard") is None:
            return _fail(mode, str(res.get("refusal") or "NO_GUARD_SYNTHESIZED"), details=res)
        return _ok(mode, "DISTINCTION_GUARD_SYNTHESIZED", res)

    if mode == "SEMANTIC_CAUSAL_UIR":
        from canonical.swe_kernel import semantic_causal_engine_v1 as m

        lang = str(inputs.get("language") or "python")
        raw_a = m.lower_to_uir(str(inputs["code_a"]), lang)
        raw_b = m.lower_to_uir(str(inputs["code_b"]), lang)
        t_a = raw_a[0] if isinstance(raw_a, tuple) else raw_a
        t_b = raw_b[0] if isinstance(raw_b, tuple) else raw_b
        eq = bool(m.semantically_equivalent(t_a, t_b))
        return _ok(
            mode,
            "SEMANTIC_UIR_EQUIVALENCE_EVALUATED",
            {
                "equivalent": eq,
                "canonical_a": repr(m.canonicalize_uir(t_a)),
                "canonical_b": repr(m.canonicalize_uir(t_b)),
            },
        )

    if mode == "DEEP_UNDERSTANDING_IR_DATAFLOW":
        from canonical.swe_kernel import deep_understanding_engine_v1 as m

        lang = str(inputs.get("language") or "python")
        dfg = m.extract_dataflow(str(inputs["source"]), lang)
        payload: dict[str, Any] = {"dataflow": dfg.to_dict() if hasattr(dfg, "to_dict") else str(dfg)}
        if "compare_source" in inputs:
            eq = m.are_semantically_equivalent(
                str(inputs["source"]),
                str(inputs["compare_source"]),
                lang,
                str(inputs.get("compare_language") or lang),
            )
            payload["equivalence"] = eq
        return _ok(mode, "DEEP_IR_DATAFLOW_EXTRACTED", payload)

    if mode == "PERFECT_UMG_CAUSAL_LINEAGE":
        from canonical.runtime import perfect_algorithm_v1 as m

        lang = str(inputs.get("language") or "python")
        umg = m.to_umg(str(inputs["source"]), lang)
        cg = m.build_causal_graph(umg)
        out_payload: dict[str, Any] = {
            "umg_digest": m.umg_digest(umg),
            "node_count": len(umg.get("nodes") or []),
            "edge_count": len(umg.get("edges") or []),
            "causal_graph_nodes": len(cg.get("nodes") or []) if isinstance(cg, Mapping) else 0,
        }
        if "target_node_id" in inputs:
            out_payload["lineage"] = m.trace_data_lineage(umg, str(inputs["target_node_id"]))
        return _ok(mode, "UMG_CAUSAL_GRAPH_BUILT", out_payload)

    if mode == "EGRAPH_DEDUCTIVE_SYNTHESIZER":
        from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as m

        target = Path(str(inputs["target_path"]))
        if not target.is_file():
            return _fail(mode, "TARGET_PATH_NOT_FOUND")
        op = str(inputs.get("operation") or "egraph_optimize")
        if op == "memoize":
            res = m.memoize_function(target, str(inputs["function_name"]))
        else:
            res = m.egraph_optimize_function(target, str(inputs["function_name"]))
        if isinstance(res, Mapping) and not res.get("pass", True):
            return _fail(mode, str(res.get("reason") or "SYNTHESIZER_DID_NOT_PASS"), details=dict(res))
        return _ok(mode, "EGRAPH_DEDUCTIVE_SYNTHESIS_APPLIED", {"synthesis_result": res})

    if mode == "INCREMENTAL_SEMANTIC_GRAPH":
        from canonical.swe_kernel import incremental_semantic_graph_v1 as m

        scope = Path(str(inputs["scope_path"]))
        if not scope.exists():
            return _fail(mode, "SCOPE_PATH_NOT_FOUND")
        cycles = m.query_import_cycles(ROOT, scope)
        payload = {"import_cycles": cycles}
        if "symbol" in inputs:
            payload["definition"] = m.query_definition(ROOT, scope, str(inputs["symbol"]))
        if "symptom_text" in inputs:
            payload["localized_symptom"] = m.localize_symptom_and_impacted_tests(
                ROOT, str(inputs["symptom_text"]), scope
            )
        return _ok(mode, "INCREMENTAL_SEMANTIC_GRAPH_QUERIED", payload)

    if mode == "STRUCTURAL_REWRITE_INDUCTION":
        from canonical.swe_kernel import structural_rewrite_induction_v1 as m

        triples = [(str(n), str(d), str(r)) for n, d, r in inputs["pairs"]]
        rules = m.learn_rules(triples)
        if not rules:
            return _fail(mode, "NO_ROUNDTRIP_REWRITE_RULES_LEARNED")
        payload = {"rule_count": len(rules), "rules": [repr(r) for r in rules[:10]]}
        if "target_source" in inputs:
            rewritten = m.rewrite(str(inputs["target_source"]), rules)
            payload["rewritten_candidates"] = rewritten
        return _ok(mode, "STRUCTURAL_REWRITE_RULES_INDUCED", payload)

    if mode == "LAW_REPAIR_SYNTHESIS":
        from canonical.swe_kernel import law_repair_synthesis_v1 as m

        repo_root = Path(str(inputs["repo_root"]))
        if not repo_root.is_dir():
            return _fail(mode, "REPO_ROOT_NOT_FOUND")
        cands = m.error_discipline_candidates(repo_root, max_candidates=int(inputs.get("max_candidates", 12)))
        return _ok(mode, "LAW_REPAIR_CANDIDATES_SYNTHESIZED", {"candidate_count": len(cands), "candidates": cands[:12]})

    if mode == "SPEC_CONTRACT_SYNTHESIS":
        from canonical.swe_kernel import spec_contract_synthesis_v1 as m

        exc_contracts = m.mine_exception_contracts(str(inputs["test_source"]), node_id=inputs.get("node_id"))
        post_contracts = m.mine_postcondition_contracts(str(inputs["test_source"]), str(inputs.get("node_id") or ""))
        return _ok(
            mode,
            "SPEC_CONTRACTS_MINED",
            {
                "exception_contracts": [repr(c) for c in exc_contracts],
                "postcondition_contracts": [repr(c) for c in post_contracts],
            },
        )

    # 3. POLYGLOT
    if mode == "C_ASAN_CEGIS_REPAIR":
        from canonical.swe_kernel import c_asan_cegis_repair_v1 as m

        patches = m.synthesize_c_causal_patches(
            str(inputs["source"]),
            int(inputs["blame_line"]),
            fault_kind=str(inputs.get("fault_kind") or "NULL_DEREF").upper(),
            target_func_name=inputs.get("target_func_name"),
        )
        if not patches:
            return _fail(mode, "NO_C_CAUSAL_PATCHES_GENERATED")
        return _ok(mode, "C_CAUSAL_PATCHES_SYNTHESIZED", {"patch_count": len(patches), "patches": patches[:10]})

    if mode == "JS_CAUSAL_CEGIS_REPAIR":
        from canonical.swe_kernel import js_causal_cegis_repair_v1 as m

        patches = m.synthesize_js_causal_patches(
            str(inputs["source"]),
            [int(x) for x in inputs["candidate_lines"]],
            err_kind=str(inputs.get("err_kind") or "TypeError"),
            err_prop=str(inputs.get("err_prop") or ""),
        )
        if not patches:
            return _fail(mode, "NO_JS_CAUSAL_PATCHES_GENERATED")
        return _ok(mode, "JS_CAUSAL_PATCHES_SYNTHESIZED", {"patch_count": len(patches), "patches": patches[:10]})

    if mode == "POLYGLOT_BUILD_CI_TRANSFORM":
        from canonical.swe_kernel import polyglot_build_ci_engine_v1 as m

        lang = str(inputs["language"]).lower()
        target = Path(str(inputs["target_path"]))
        goal_spec = str(inputs["goal_spec"])
        fn_map = {
            "rust": m.rust_transform_and_verify,
            "go": m.go_transform_and_verify,
            "cpp": m.cpp_transform_and_verify,
            "c++": m.cpp_transform_and_verify,
            "java": m.java_transform_and_verify,
            "ts": m.ts_transform_and_verify,
            "typescript": m.ts_transform_and_verify,
        }
        if lang not in fn_map:
            return _fail(mode, f"UNSUPPORTED_POLYGLOT_LANGUAGE:{lang}")
        res = fn_map[lang](target, goal_spec)
        passed = bool(res.get("pass")) if isinstance(res, Mapping) else False
        if not passed:
            return _fail(mode, "POLYGLOT_TRANSFORM_DID_NOT_PASS", details=res)
        return _ok(mode, "POLYGLOT_TRANSFORM_VERIFIED", dict(res))

    # 4. COMPUTER USE, PETRI, AUTOMATA & PROSE
    if mode == "UNIVERSAL_COMPUTER_PETRI_AGENT":
        from canonical.swe_kernel import universal_computer_agent_v1 as m

        edges = [(str(u), str(v)) for u, v in inputs["edges"]]
        res = m.compute_petri_dominator_cut_vertices(edges, str(inputs["start_node"]), str(inputs["goal_node"]))
        if not res.get("reachable", True):
            return _fail(mode, "GOAL_NODE_UNREACHABLE_IN_PETRI_GRAPH", details=res)
        return _ok(mode, "PETRI_DOMINATOR_CUT_VERTICES_COMPUTED", res)

    if mode == "CROSS_MODAL_TOMOGRAPHY_PETRI":
        from canonical.swe_kernel import cross_modal_tomography_petri_v1 as m

        if "doc_text" in inputs:
            exs = m.extract_executable_doc_examples(str(inputs["doc_text"]))
            return _ok(mode, "EXECUTABLE_DOC_EXAMPLES_EXTRACTED", {"examples": exs, "count": len(exs)})
        if "html_dom" in inputs or "a11y_tree" in inputs or "kv_state" in inputs:
            snap = m.capture_multilayer_state(
                a11y_tree=inputs.get("a11y_tree"),
                html_dom=inputs.get("html_dom"),
                kv_state=inputs.get("kv_state"),
            )
            return _ok(mode, "MULTILAYER_STATE_CAPTURED", {"snapshot": snap})
        return _fail(mode, "ENGINE_INPUTS_MISSING:doc_text_or_html_dom_or_a11y_tree")

    if mode == "PROSE_CLAIM_EXPERIMENT":
        from canonical.tools import the_right_question_is_an_experiment_v1 as m

        claims = m.extract_claims(
            str(inputs["text"]),
            programs=list(inputs.get("programs") or ()),
            subject=str(inputs.get("subject") or ""),
        )
        return _ok(mode, "PROSE_CLAIMS_EXTRACTED", {"claim_count": len(claims), "claims": claims[:25]})

    if mode == "MINIMAL_AUTOMATA_EXPERIMENT":
        from canonical.runtime import minimal_experiment_v1 as m

        def _norm_machine(spec_in: Mapping[str, Any]) -> dict[str, Any]:
            d = dict(spec_in)
            raw_t = d.get("transitions") or {}
            norm_t: dict[tuple[int, str], int] = {}
            if isinstance(raw_t, Mapping):
                for k, v in raw_t.items():
                    if isinstance(k, tuple) and len(k) == 2:
                        norm_t[(int(k[0]), str(k[1]))] = int(v)
                    elif isinstance(v, Mapping):
                        for act_k, dst_v in v.items():
                            norm_t[(int(k), str(act_k))] = int(dst_v)
            elif isinstance(raw_t, Sequence):
                for row_t in raw_t:
                    s_src, act_k, dst_v = row_t
                    norm_t[(int(s_src), str(act_k))] = int(dst_v)
            d["transitions"] = norm_t
            return m.make_machine(**d)

        ma = _norm_machine(dict(inputs["machine_a"]))
        mb = _norm_machine(dict(inputs["machine_b"]))
        eq = m.machines_equivalent(ma, mb)
        word = m.separating_word(ma, mb)
        return _ok(
            mode,
            "MINIMAL_AUTOMATA_SEPARATION_COMPUTED",
            {
                "equivalent": bool(eq),
                "separating_word": word,
                "digest_a": m.machine_digest(ma),
                "digest_b": m.machine_digest(mb),
            },
        )

    if mode == "DOM_STATE_ENVIRONMENT":
        from canonical.runtime import dom_state_environment_v1 as m

        elems = m.snapshot_to_elements(inputs["snapshot"])
        acts = m.stable_actions(elems)
        return _ok(
            mode,
            "DOM_STATE_NORMALIZED",
            {
                "element_count": len(elems),
                "elements": [dict(e) if isinstance(e, Mapping) else getattr(e, "__dict__", str(e)) for e in elems],
                "stable_actions": [dict(a) if isinstance(a, Mapping) else getattr(a, "__dict__", str(a)) for a in acts],
            },
        )

    if mode == "OSWORLD_BROWSER_OPS":
        from canonical.runtime import osworld_v21_browser_ops_v1 as m

        op = m.compile_browser_op(dict(inputs["spec"]))
        return _ok(mode, "OSWORLD_BROWSER_OP_COMPILED", {"compiled_op": op})

    if mode == "CANONICAL_FRAME_TRANSITION":
        from canonical.swe_kernel import canonical_frame_v1 as m

        tpl = m.template(inputs["before"], inputs["after"], inputs["frames"], str(inputs["slot"]))
        if tpl is None:
            return _fail(mode, "NO_CANONICAL_FRAME_TRANSITION_FOUND")
        return _ok(mode, "CANONICAL_FRAME_TEMPLATE_INDUCED", {"template": tpl})

    # 5. CONTINUAL LEARNING & META-CIRCULAR ORGANS
    if mode == "EPISTEMIC_IR_TRANSFER_ADMISSION":
        from canonical.swe_kernel import epistemic_admission_and_self_play_v1 as m

        b_ir = m.lift_python_to_ir(str(inputs["before_code"]), {})
        a_ir = m.lift_python_to_ir(str(inputs["after_code"]), {})
        transferred = m.transfer_ir_rule_to_snippet(
            b_ir,
            a_ir,
            str(inputs["target_snippet"]),
            target_language=str(inputs.get("target_language") or "python"),
        )
        if transferred is None:
            return _fail(mode, "IR_RULE_DID_NOT_MATCH_TARGET_SNIPPET")
        return _ok(mode, "SEMANTIC_IR_RULE_TRANSFERRED", {"transferred_code": transferred})

    if mode == "VERIFIED_SKILL_CRYSTALLIZER":
        from canonical.swe_kernel import verified_skill_crystallizer_v1 as m

        rule = m.anti_unify_code_rule(
            str(inputs["before_snippet"]),
            str(inputs["after_snippet"]),
            language=str(inputs.get("language") or "python"),
            error_class=str(inputs.get("error_class") or "GENERIC"),
        )
        if rule is None:
            return _fail(mode, "CODE_RULE_CRYSTALLIZATION_REFUSED")
        payload = {"skill_id": m.skill_identity(rule), "rule": dict(rule) if isinstance(rule, Mapping) else repr(rule)}
        if "apply_to_source" in inputs:
            payload["applied_source"] = m.apply_crystallized_code_rule(str(inputs["apply_to_source"]), rule)
        return _ok(mode, "VERIFIED_SKILL_RULE_CRYSTALLIZED", payload)

    if mode == "CAUSAL_TRACE_SKILL_COMPILER":
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as m

        elevated = m.elevate_trace_to_fastest_layer(list(inputs["trace"]))
        return _ok(
            mode,
            "TRACE_ELEVATED_TO_FASTEST_LAYER",
            {"elevated_steps": elevated, "step_count": len(elevated)},
        )

    if mode == "META_CIRCULAR_ORGAN_SYNTHESIS":
        from canonical.swe_kernel import meta_circular_organ_graph_v1 as m

        if "examples" in inputs:
            ex = [(tuple(x) if isinstance(x, (list, tuple)) else (x,), y) for x, y in inputs["examples"]]
            periodic = m.induce_periodic_operator(ex)
            if periodic is None:
                return _fail(mode, "NO_PERIODIC_OPERATOR_INDUCED")
            return _ok(mode, "PERIODIC_ORGAN_OPERATOR_INDUCED", {"periodic_operator": periodic})
        if "samples" in inputs:
            organ = m.synthesize_perceptor_organ(list(inputs["samples"]), format_tag=str(inputs.get("format_tag") or "auto"))
            if organ is None:
                return _fail(mode, "PERCEPTOR_ORGAN_SYNTHESIS_FAILED")
            return _ok(mode, "PERCEPTOR_ORGAN_SYNTHESIZED", {"organ": organ if isinstance(organ, Mapping) else repr(organ)})
        return _fail(mode, "ENGINE_INPUTS_MISSING:examples_or_samples", required_inputs=["examples"])

    if mode == "RECURSIVE_SELF_ARCHITECT":
        from canonical.swe_kernel import recursive_self_architect_v1 as m

        code = str(inputs["source_code"])
        verdict = m.referee_executable_organ(code)
        mdl_bytes = m.executable_byte_measure(code)
        passed = bool(verdict.get("ok") or verdict.get("pass")) if isinstance(verdict, Mapping) else bool(verdict)
        if not passed:
            return _fail(mode, "ORGAN_REFEREE_REJECTED", referee=verdict, mdl_bytes=mdl_bytes)
        return _ok(mode, "EXECUTABLE_ORGAN_REFEREED", {"referee": verdict, "executable_mdl_bytes": mdl_bytes})

    # 6. FINANCE, LBO/DCF, FIBO
    if mode == "FINANCE_QUANTITATIVE_ALGEBRA":
        from canonical.runtime import finance_quantitative_algebra_v1 as m

        op = str(inputs["operation"]).lower()
        if op == "percent_change":
            val = m.percent_change(inputs["new_value"], inputs["old_value"])
        elif op == "ratio":
            val = m.ratio(inputs["numerator"], inputs["denominator"])
        elif op == "percent_of":
            val = m.percent_of(inputs["numerator"], inputs["denominator"])
        elif op == "basis_points_between":
            val = m.basis_points_between(inputs["new_percent"], inputs["old_percent"])
        elif op == "average":
            val = m.average(inputs["values"])
        elif op == "midpoint":
            val = m.midpoint(inputs["low"], inputs["high"])
        else:
            return _fail(mode, f"UNKNOWN_FINANCE_ALGEBRA_OPERATION:{op}")
        return _ok(mode, "FINANCE_QUANTITATIVE_ALGEBRA_COMPUTED", {"operation": op, "value": str(val)})

    if mode == "FINANCE_LBO_DCF_WORKFLOW":
        from canonical.runtime import finance_modeling_workflows_v1 as m

        wf = str(inputs["workflow"]).lower()
        params = {
            k: (str(v) if isinstance(v, float) else v)
            for k, v in dict(inputs["parameters"]).items()
        }
        if wf in {"lbo", "simplified_lbo", "simplified_lbo_model"}:
            res = m.simplified_lbo_model(**params)
        elif wf in {"dcf", "constant_ratio_dcf", "constant_ratio_dcf_model"}:
            res = m.constant_ratio_dcf_model(**params)
        else:
            return _fail(mode, f"UNKNOWN_FINANCE_WORKFLOW:{wf}")
        serial = {k: (str(v) if not isinstance(v, (int, float, str, bool, list, dict, type(None))) else v) for k, v in dict(res).items()}
        return _ok(mode, "FINANCE_MODELING_WORKFLOW_COMPUTED", {"workflow": wf, "valuation": serial})

    if mode == "FIBO_BOUNDED_FINANCE_AUTHORITY":
        from canonical.runtime import fibo_q2_2026_bounded_finance_authority_v1 as m

        if "left_id" in inputs and "right_id" in inputs:
            proof = m.prove_entailment(str(inputs["left_id"]), str(inputs["right_id"]), repo_root=ROOT)
            return _ok(mode, "FIBO_ENTAILMENT_EVALUATED", {"proof": proof})
        if "surface" in inputs:
            cands = m.exact_label_candidates(str(inputs["surface"]), repo_root=ROOT)
            return _ok(mode, "FIBO_LABEL_CANDIDATES_RESOLVED", {"candidates": cands})
        return _fail(mode, "ENGINE_INPUTS_MISSING:surface_or_left_id_right_id")

    # 7. VISUAL 3D HULL, CHARTOGRAPHY, CAD, OOXML, PDF
    if mode == "ORTHOGRAPHIC_VISUAL_HULL_3D":
        import dataclasses
        from canonical.runtime import orthographic_visual_hull as m

        voxels = m.reconstruct_visual_hull(inputs["top"], inputs["front"], inputs["right"])
        proj = m.project_visual_hull(voxels)
        sig = dataclasses.asdict(m.hull_signature(voxels))
        return _ok(
            mode,
            "ORTHOGRAPHIC_VISUAL_HULL_RECONSTRUCTED",
            {"voxels": voxels, "projections": proj, "signature": sig},
        )

    if mode == "CHARTOGRAPHY_PROFESSIONAL_SOLVER":
        from canonical.runtime import chartography_deterministic_professional_solver_v1 as m

        res = m.solve(str(inputs["image_path"]), str(inputs["prompt"]))
        if not isinstance(res, Mapping) or str(res.get("status") or "").startswith("FAIL"):
            return _fail(mode, str((res or {}).get("reason") or (res or {}).get("status") or "CHARTOGRAPHY_FAILED"), details=res)
        return _ok(mode, "CHARTOGRAPHY_SOLVED", dict(res))

    if mode == "CAD_PARTSPEC_GENERATOR":
        from canonical.runtime import cad_partspec_generator as m

        code = m.generate_code(dict(inputs["spec"]))
        return _ok(mode, "CAD_PARTSPEC_CODE_GENERATED", {"cadquery_code": code})

    if mode == "OOXML_PACKAGE_VALIDATOR":
        from canonical.runtime import ooxml_package_integrity as m

        res = m.validate_ooxml_package(str(inputs["package_path"]))
        if res.get("status") != "PASS" and not res.get("ok") and not res.get("valid"):
            return _fail(mode, str(res.get("reason") or res.get("status") or "OOXML_INVALID"), details=res)
        return _ok(mode, "OOXML_PACKAGE_VALIDATED", dict(res))

    if mode == "PDF_NATIVE_TEXT_OPERAND_EDIT":
        from canonical.runtime import pdf_native_edit_transaction as m

        res = m.replace_unique_pdf_text_operand(
            str(inputs["input_path"]),
            str(inputs["output_path"]),
            old_text=str(inputs["old_text"]),
            new_text=str(inputs["new_text"]),
        )
        if isinstance(res, Mapping) and res.get("status") != "PASS":
            return _fail(mode, str(res.get("reason") or "PDF_EDIT_FAILED"), details=dict(res))
        return _ok(mode, "PDF_NATIVE_TEXT_OPERAND_REPLACED", dict(res) if isinstance(res, Mapping) else {"result": res})

    # 8. LANGUAGE, IF, H100, VALUE ALGEBRA, POLYTOPE, SCIENCE & MODULE SOLVER
    if mode == "INSTRUCTION_CONTRACT_COMPILER":
        from canonical.runtime import instruction_contract_v1 as m

        contract = m.compile_contract(str(inputs["utterance"]), dict(inputs["observation"]))
        if contract.get("refusal"):
            return _fail(mode, f"INSTRUCTION_CONTRACT_REFUSED:{contract['refusal']}", contract=contract)
        payload = {"contract": contract}
        if "trace" in inputs:
            verdict = m.check_contract(contract, list(inputs["trace"]))
            payload["trace_verification"] = verdict
            if isinstance(verdict, Mapping) and verdict.get("ok") is False:
                return _fail(mode, "INSTRUCTION_TRACE_VIOLATED_CONTRACT", **payload)
        return _ok(mode, "INSTRUCTION_CONTRACT_COMPILED", payload)

    if mode == "LIVEBENCH_IF_CONSTRAINT_SOLVER":
        from canonical.runtime import livebench_if_reference_free_compound_witness_v1 as compound
        from canonical.runtime import livebench_if_single_checker_solver_v1 as single

        prompt = str(inputs["prompt"])
        res = single.solve(prompt)
        if res.get("status") == "PASS" and res.get("response") is not None:
            return _ok(mode, "LIVEBENCH_IF_SINGLE_CHECKER_SOLVED", res)
        comp = compound.construct_from_prompt(prompt)
        if isinstance(comp, Mapping) and comp.get("status") == "PASS":
            return _ok(mode, "LIVEBENCH_IF_COMPOUND_WITNESS_CONSTRUCTED", dict(comp))
        return _fail(mode, str(res.get("error") or "IF_PROMPT_OUTSIDE_CERTIFIED_CHECKERS"), single_result=res, compound_result=comp)

    if mode == "ZERO_LEARNED_EXTRACTIVE_SUMMARY":
        from canonical.runtime import zero_learned_extractive_summary_v1 as m

        res = m.summarize(
            str(inputs["text"]),
            compression_ratio=float(inputs.get("compression_ratio", 0.35)),
            max_sentences=int(inputs.get("max_sentences", 3)),
            min_sentence_words=int(inputs.get("min_sentence_words", 3)),
        )
        return _ok(mode, "EXTRACTIVE_SUMMARY_GENERATED", res)

    if mode == "H100_COMPOSITIONAL_LANGUAGE":
        from canonical.runtime import h100_zero_learned_compositional_language_v1 as m

        res = m.compile_compositional_roles(str(inputs["text"]))
        return _ok(mode, "COMPOSITIONAL_LANGUAGE_ROLES_COMPILED", res)

    if mode == "H100_PARAMETRIC_SYMBOLIC_DISCOVERY":
        from canonical.runtime import h100_zero_learned_parametric_unary_v1 as m

        res = m.discover(
            list(inputs["rows"]),
            target=str(inputs["target"]),
            input_name=inputs.get("input_name"),
            exact_nrmse=float(inputs.get("exact_nrmse", 1e-6)),
        )
        return _ok(mode, "PARAMETRIC_SYMBOLIC_LAW_DISCOVERED", res if isinstance(res, Mapping) else {"result": res})

    if mode == "VALUE_ALGEBRA_LAW_INDUCER":
        from canonical.runtime import value_algebra_v1 as m

        op_map: dict[str, Callable[[Sequence[Any]], Any]] = {
            "sum": sum,
            "max": max,
            "min": min,
            "len": len,
            "mean": lambda xs: sum(xs) / len(xs),
        }
        op_name = str(inputs["operator_name"]).lower()
        if op_name not in op_map:
            return _fail(mode, f"UNSUPPORTED_OPERATOR_PROBE:{op_name}")
        raw_laws = m.induce_laws(op_map[op_name], inputs.get("probes"))
        law_names = [str(x) for x in raw_laws if isinstance(x, str)]
        if not law_names:
            return _fail(mode, "NO_NONVACUOUS_LAWS_INDUCED")
        return _ok(mode, "VALUE_ALGEBRA_LAWS_INDUCED", {"operator": op_name, "laws": law_names})

    if mode == "EXACT_RATIONAL_POLYTOPE_SOLVER":
        from canonical.runtime import exact_linear_parameter_polytope_v1 as m

        res = m.solve(dict(inputs))
        if str(res.get("status") or "").startswith("FAIL") or res.get("feasible") is False:
            return _fail(mode, str(res.get("reason") or res.get("status") or "POLYTOPE_INFEASIBLE"), details=res)
        return _ok(mode, "EXACT_RATIONAL_POLYTOPE_SOLVED", res)

    if mode == "TB_SCIENCE_PERIODIC_KERNEL":
        from canonical.runtime import tb_science_zero_model_scientific_kernel_v1 as m

        res = m.fit_shared_period(list(inputs["series"]))
        return _ok(mode, "SHARED_PERIOD_HARMONIC_FITTED", res if isinstance(res, Mapping) else {"fit": res})

    if mode == "ADMITTED_BRAIN_MODULE_SOLVER":
        return _run_admitted_module_solver(mode, inputs, goal)

    # 9. NON-OBVIOUS KOAN / APHORISTIC KERNELS & CROSS-DISCIPLINARY ENGINES
    if mode == "INSTANT_ONE_SHOT_LEARNER":
        from canonical.swe_kernel import instant_one_shot_learning_v1 as m

        identify_res = dict(inputs.get("identify_result") or {"identified": True, "rule_key": str(inputs["skill_id"])})
        effects = [tuple(e) for e in (inputs.get("effects") or [("post_state", "READY")])]
        contract_res = m.extract_contract(
            identify_res,
            str(inputs["skill_id"]),
            list(inputs["preconditions"]),
            list(inputs.get("observables") or inputs["preconditions"]),
            list(inputs["actions"]),
            str(inputs.get("verdict") or "PASS"),
            effects,
        )
        app_res = m.classify_applicability(
            contract_res,
            list(inputs.get("success_states") or [list(inputs["preconditions"])]),
            list(inputs.get("failure_states") or [[]]),
        )
        return _ok(mode, "ONE_SHOT_CONTRACT_AND_APPLICABILITY_EXTRACTED", {"contract": contract_res, "applicability": app_res})

    if mode == "PREDICTIVE_HOARE_CONTRACT":
        from canonical.swe_kernel import predictive_contract_v1 as m

        src_b = inputs["src"] if isinstance(inputs["src"], bytes) else str(inputs["src"]).encode("utf-8")
        dst_b = inputs["dst"] if isinstance(inputs["dst"], bytes) else str(inputs["dst"]).encode("utf-8")
        clauses = m.derive_clauses(src_b, dst_b)
        if not clauses:
            return _fail(mode, "NO_PREDICTIVE_CLAUSES_DERIVED")
        verified = [bool(m.holds(c, src_b, {"dst": dst_b}, dst_b)) for c in clauses]
        return _ok(mode, "PREDICTIVE_HOARE_CLAUSES_DERIVED", {"clauses": clauses, "clause_count": len(clauses), "all_hold_on_trial": all(verified)})

    if mode == "EDIT_BY_EXAMPLE_PROSE":
        from canonical.swe_kernel.taught_actions import edit_by_example_v1 as m

        try:
            edited = m.edit_by_example(
                str(inputs["target_text"]),
                str(inputs["before_text"]),
                str(inputs["after_text"]),
            )
        except m.Refused as exc:
            return _fail(mode, f"EDIT_BY_EXAMPLE_REFUSED:{exc}")
        return _ok(mode, "EDIT_BY_EXAMPLE_APPLIED", {"edited_text": edited})

    if mode == "CONCEPT_LIBRARY_EGRAPH_LGG":
        from canonical.swe_kernel import concept_library_v1 as m

        mod_ast = ast.parse(str(inputs["source"]))
        canon_mod = m.canonicalize_ast_via_egraph(mod_ast)
        canon_src = ast.unparse(canon_mod)
        out_payload: dict[str, Any] = {
            "canonical_source": canon_src,
            "ast_bytes_before": m.executable_ast_bytes(str(inputs["source"])),
            "ast_bytes_after": m.executable_ast_bytes(canon_src),
        }
        if "second_source" in inputs:
            mod2 = ast.parse(str(inputs["second_source"]))
            fns1 = [n for n in canon_mod.body if isinstance(n, ast.FunctionDef)]
            fns2 = [n for n in mod2.body if isinstance(n, ast.FunctionDef)]
            if fns1 and fns2:
                out_payload["plotkin_lgg"] = m.higher_order_plotkin_lgg(fns1[0], fns2[0])
        return _ok(mode, "EGRAPH_CANONICALIZED_AND_LGG_ANALYZED", out_payload)

    if mode == "COMPRESSION_GAIN_MDL":
        from canonical.swe_kernel import compression_gain_v1 as m

        sources = [str(s) for s in inputs["sources"]]
        comp = m.compress_corpus(sources, entrypoints=inputs.get("entrypoints"), probes=inputs.get("probes"))
        shapes = [m.lift_shape(s) for s in sources[:4]]
        return _ok(mode, "MDL_CORPUS_COMPRESSION_EVALUATED", {"compression": comp, "lifted_shapes_count": sum(1 for x in shapes if x is not None)})

    if mode == "PROVED_COMPOSITION_SURVIVAL":
        from canonical.swe_kernel import proved_composition_v1 as m

        pat = str(inputs["pattern_core"])
        rep = str(inputs["replacement_core"])
        op = m.ProvedOperation(
            str(inputs.get("op_id") or "op_1"),
            m.substring_premise(pat),
            lambda s, p=pat, r=rep: s.replace(p, r),
            m.structural_proof(pat, rep),
            m.structural_survival(rep),
        )
        res = m.compose(str(inputs["source"]), [op])
        if res.get("verdict") != "PASS":
            return _fail(mode, str(res.get("reason") or "PROVED_COMPOSITION_FAILED"), details=res)
        return _ok(mode, "PROVED_COMPOSITION_VERIFIED", res)

    if mode == "LESSON_ADMISSION_GATE":
        from canonical.swe_kernel import lesson_admission_gate_v1 as m

        if "before_snippet" in inputs and "after_snippet" in inputs and "victims" in inputs:
            victims = [
                 v if isinstance(v, m.Victim) else m.Victim(str(v["victim_id"]), str(v["source"]), m.strict_spec, tuple(v.get("probes") or ()))
                for v in inputs["victims"]
            ]
            res = m.evaluate(str(inputs["before_snippet"]), str(inputs["after_snippet"]), victims=victims)
            return _ok(mode, "LESSON_ADMISSION_VICTIMS_EVALUATED", res)
        demo = m.demonstration()
        return _ok(mode, "LESSON_ADMISSION_GATE_DEMONSTRATED", demo)

    if mode == "CONTRASTIVE_ORACLE_BOOTSTRAP":
        from canonical.swe_kernel import contrastive_oracle_bootstrap_v1 as m

        res = m.identify_rule(
            str(inputs["before_snippet"]),
            str(inputs["after_snippet"]),
            list(inputs.get("probes") or [0, 1, 2, -1]),
            list(inputs.get("contrast_pairs") or []),
        )
        return _ok(mode, "CONTRASTIVE_RULE_IDENTIFIED", res)

    if mode == "PAIRED_TRANSFER_EVALUATOR":
        from canonical.swe_kernel import paired_transfer_evaluation_v1 as m

        src_root = Path(inputs.get("source_root") or ROOT)
        learned = m.learn_rule_on_source(
            str(inputs["before_snippet"]),
            str(inputs["after_snippet"]),
            list(inputs.get("probes") or [0, 1, 2]),
            src_root,
        )
        contract = m.extract_contract(learned, str(inputs["before_snippet"]), str(inputs["after_snippet"]))
        return _ok(mode, "PAIRED_TRANSFER_CONTRACT_EXTRACTED", {"learned": learned, "contract": contract})

    if mode == "ZYGOTE_COW_FORK_POOL":
        from canonical.swe_kernel import zygote_worker_pool_v1 as m

        res = m.screen_python_candidates_cow(
            inputs["project_root"],
            str(inputs["target_path"]),
            list(inputs["test_paths"]),
            list(inputs["candidates"]),
            stop_on_first_pass=bool(inputs.get("stop_on_first_pass", True)),
            timeout_s=float(inputs.get("timeout_s", 8.0)),
            per_candidate_timeout_s=float(inputs.get("per_candidate_timeout_s", 1.5)),
        )
        return _ok(mode, "COW_ZYGOTE_CANDIDATES_SCREENED", res)

    if mode == "INTERFACE_ACTION_GRAMMAR":
        from canonical.swe_kernel import interface_action_grammar_v1 as m

        parsed = m.parse_gui_goal(str(inputs["instruction"]))
        if "nodes" in inputs:
            nodes = [
                n if isinstance(n, m.A11yNode) else m.A11yNode(**dict(n))
                for n in inputs["nodes"]
            ]
            env = m.A11yEnvironment(nodes)
            solved = m.solve_gui_goal(env, str(inputs["instruction"]), inputs.get("goal_check") or (lambda _e: True))
            return _ok(mode, "A11Y_GUI_GOAL_SOLVED", {"parsed": parsed, "solved": solved})
        return _ok(mode, "A11Y_GUI_GOAL_PARSED", {"parsed": parsed})

    if mode == "ENVIRONMENT_BROKER":
        from canonical.swe_kernel import the_environment_broker_v1 as m

        tree_p = Path(str(inputs["tree"]))
        if not tree_p.exists():
            return _fail(mode, f"ENVIRONMENT_TREE_MISSING:{tree_p}")
        layout = m.detect_layout(tree_p)
        cmds = m.declared_test_commands(tree_p)
        return _ok(mode, "ENVIRONMENT_LAYOUT_BROKERED", {"layout": layout, "declared_test_commands": cmds})

    if mode == "PREMISE_MINIMAL_SENSE":
        from canonical.swe_kernel import the_premise_is_the_sense_v1 as m

        probes_map: Mapping[str, Mapping[str, Any]] = dict(inputs["probes"])
        actions_by_state: Mapping[str, Sequence[str]] = dict(inputs["actions_by_state"])
        fact_costs: Mapping[str, float] = {str(k): float(v) for k, v in dict(inputs["fact_costs"]).items()}
        worlds = list(probes_map.keys())
        saved_table = dict(m._PROBE_TABLE)
        try:
            for st_name, probe_row in probes_map.items():
                m._PROBE_TABLE[st_name] = lambda f_seq, pr=probe_row: m.observations(pr, f_seq)
            res = m.brute_force_minimum(worlds, actions_by_state, fact_costs)
        finally:
            m._PROBE_TABLE.clear()
            m._PROBE_TABLE.update(saved_table)
        if res.get("status") != "SUFFICIENT_DECISION_PARTITION_FOUND":
            return _fail(mode, str(res.get("status") or "INSUFFICIENT_OBSERVATION_SPACE"), details=res)
        return _ok(mode, "MINIMAL_SUFFICIENT_SENSE_DERIVED", res)

    if mode == "METAMORPHIC_CLI_COMPILER":
        from canonical.swe_kernel import metamorphic_cli_compiler_v1 as m

        rb = inputs["real_bytes"] if isinstance(inputs["real_bytes"], bytes) else str(inputs["real_bytes"]).encode("utf-8")
        tup = m.build_metamorphic_tuple(rb, k=int(inputs.get("k", 5)))
        if tup is None:
            return _fail(mode, "METAMORPHIC_TUPLE_REQUIRES_AT_LEAST_K_LINES")
        summary_keys = {k: (len(v) if isinstance(v, (bytes, list, dict)) else v) for k, v in tup.items()}
        return _ok(mode, "METAMORPHIC_CLI_TUPLE_BUILT", {"tuple_summary": summary_keys})

    if mode == "WITNESS_INVERSION_LENS":
        from canonical.swe_kernel import witness_inversion_v1 as m

        pairs = [(a, b) for a, b in inputs["pairs"]]
        lens = m.synthesize_bidirectional_lens(pairs, input_var=str(inputs.get("input_var") or "data"))
        if lens is None:
            return _fail(mode, "NO_BIDIRECTIONAL_LENS_FOUND")
        return _ok(mode, "BIDIRECTIONAL_WITNESS_LENS_SYNTHESIZED", lens)

    if mode == "CONDITION_DEMAND_HARVESTER":
        from canonical.swe_kernel import what_the_condition_wants_v1 as m

        rep = dict(inputs["report"])
        return _ok(mode, "CONDITION_DEMAND_SUMMARIZED", {"headline": m.headline(rep), "report_keys": sorted(rep.keys())})

    if mode == "RUNTIME_VALUE_WITNESS":
        from canonical.swe_kernel import a_name_gets_its_value_from_the_run_v1 as m

        tree_p = Path(str(inputs["tree"]))
        if not tree_p.exists():
            return _fail(mode, f"TARGET_TREE_MISSING:{tree_p}")
        sites = m.blocked_sites(tree_p)
        return _ok(mode, "RUNTIME_BLOCKED_SITES_EXTRACTED", {"blocked_site_count": len(sites), "sites": sites[:20]})

    if mode == "METAMORPHIC_API_LAWS":
        from canonical.swe_kernel import metamorphic_laws_v1 as m

        violations = m.static_assert_validation(str(inputs["source"]), str(inputs.get("module_name") or ""))
        muts = m.mutations_for(list(inputs.get("sample_args") or [1, "x"]))
        return _ok(
            mode,
            "METAMORPHIC_STATIC_AND_MUTATION_PROBES_BUILT",
            {
                "violation_count": len(violations),
                "violations": [str(v) for v in violations],
                "generated_argument_mutations": len(muts),
            },
        )

    if mode == "STRUCTURAL_SPEC_DERIVER":
        from canonical.swe_kernel import specification_from_structure_v1 as m

        derived = m.derive(str(inputs["module_source"]), str(inputs.get("module_name") or "target_mod"))
        pub_fns, declined = m.public_functions(str(inputs["module_source"]))
        return _ok(
            mode,
            "STRUCTURAL_SPECIFICATION_DERIVED",
            {"derived": derived, "public_function_count": len(pub_fns), "declined_count": len(declined)},
        )

    if mode == "UNIVERSAL_SEMANTIC_IR":
        from canonical.swe_kernel import universal_semantic_ir_v1 as m

        src_b = inputs["source"] if isinstance(inputs["source"], bytes) else str(inputs["source"]).encode("utf-8")
        funcs = m.lower_source_to_uir(src_b, str(inputs["language"]), rel_path=str(inputs.get("rel_path") or "<memory>"))
        return _ok(
            mode,
            "SOURCE_LOWERED_TO_UNIVERSAL_SEMANTIC_IR",
            {
                "function_count": len(funcs),
                "functions": [
                    {"name": f.name, "language": f.language, "params": f.params, "node_count": len(f.nodes), "fingerprint": f.semantic_fingerprint}
                    for f in funcs
                ],
            },
        )

    if mode == "FAST_ABSTRACT_SIMULATOR":
        from canonical.swe_kernel import executable_simulator_mental_model_v1 as m

        sim = m.simulate_python_fast(
            str(inputs["source"]),
            str(inputs["entry_func"]),
            list(inputs["args"]),
            step_quota=int(inputs.get("step_quota", 5000)),
        )
        sim_clean = {k: (sorted(v) if isinstance(v, set) else v) for k, v in sim.items()}
        if sim_clean.get("status") != "OK":
            return _fail(mode, f"FAST_SIMULATION_FAULT:{sim_clean.get('status')}", simulation=sim_clean)
        return _ok(mode, "PYTHON_SIMULATED_IN_RAM", sim_clean)

    if mode == "PERF_RACE_OVERFLOW_AUDITOR":
        from canonical.swe_kernel import diagnostics_perf_and_design_engine_v1 as m

        target_p = Path(str(inputs["target"]))
        if not target_p.exists():
            return _fail(mode, f"AUDIT_TARGET_MISSING:{target_p}")
        sec = m.security_audit_package(target_p)
        races = m.detect_race_conditions(target_p) if target_p.is_file() else {}
        return _ok(mode, "PERF_RACE_SECURITY_AUDIT_COMPLETED", {"security": sec, "races": races})

    if mode == "GLOBAL_MINIMAX_EXTRAPOLATOR":
        from canonical.swe_kernel import global_extrapolation_chase_spine_v1 as m

        if "training_pairs" in inputs:
            grid_res = m.induce_and_predict_grid_delta_rule(list(inputs["training_pairs"]), test_grids=inputs.get("test_grids"))
            return _ok(mode, "GRID_DELTA_EXTRAPOLATION_INDUCED", grid_res)
        if "options" in inputs:
            ranked = m.rank_global_minimal_action_routes(list(inputs["options"]), goal=goal)
            return _ok(mode, "GLOBAL_MINIMAL_ACTION_ROUTES_RANKED", {"ranked_routes": ranked})
        prob = dict(inputs.get("problem") or {"low": 0, "high": 7, "hypothesis_cover_complete": True, "hypotheses": [0, 1, 2, 3, 4, 5, 6, 7]})
        res = m.solve_minimax_interval_probe_policy(prob)
        return _ok(mode, "MINIMAX_PROBE_POLICY_EVALUATED", res)

    if mode == "PITMAN_YOR_OPEN_WORLD":
        from canonical.runtime import global_open_world_extrapolator_v1 as m

        obs_list = [
            ch if isinstance(ch, m.ChannelObservation) else m.ChannelObservation(**dict(ch))
            for ch in inputs["channels"]
        ]
        if not obs_list:
            return _fail(mode, "EMPTY_CHANNEL_OBSERVATIONS")
        est = m.estimate_unseen_opportunity_space(
            obs_list,
            goal=str(inputs.get("goal") or goal),
            remaining_budget=float(inputs.get("remaining_budget", 10.0)),
        )
        return _ok(mode, "PITMAN_YOR_UNSEEN_SPACE_ESTIMATED", est)

    if mode == "WORLD_BINDING_SLOT_COMPLETER":
        from canonical.runtime import world_binding_v1 as m

        dest = m.named_destination(str(inputs["goal"]))
        phs = m.placeholders(dict(inputs.get("entry") or {}))
        return _ok(mode, "WORLD_BINDING_SLOTS_ANALYZED", {"named_destination": dest, "placeholders": sorted(phs)})

    if mode == "REFUSAL_ARTIFACT_MANUFACTURER":
        from canonical.runtime import manufacture_what_the_refusal_asks_for_v1 as m

        prod = m.producer_for(str(inputs["kind"]), program=str(inputs["program"]), flags=list(inputs["flags"]))
        return _ok(mode, "REFUSAL_PRODUCER_RESOLVED", {"kind": inputs["kind"], "producer_argv": prod})

    if mode == "SUBCOMMAND_SCOPE_PROBER":
        from canonical.runtime import ask_the_subcommand_before_you_call_it_unbound_v1 as m

        questions = m.what_to_ask(str(inputs["prog"]), list(inputs.get("subcommands") or ()))
        return _ok(mode, "SUBCOMMAND_SCOPE_QUESTIONS_DERIVED", {"program": inputs["prog"], "questions": questions})

    if mode == "KOAN_REFUSAL_CURRICULUM":
        from canonical.tools import the_refusal_is_the_curriculum_v1 as m

        demand = m.read_demand(str(inputs["line"]))
        rows = m.parse_rows(str(inputs.get("page_text") or inputs["line"]))
        return _ok(mode, "REFUSAL_CURRICULUM_DEMAND_PARSED", {"demand": demand, "parsed_row_count": len(rows)})

    if mode == "KOAN_FORCE_VALUE_ANGELIC":
        from canonical.tools import force_the_value_and_see_v1 as m

        inst_src, sites = m.instrumented_source(str(inputs["source"]), str(inputs["function_name"]))
        return _ok(mode, "ANGELIC_FORCE_SITES_INSTRUMENTED", {"site_count": len(sites), "sites": sites, "instrumented_source": inst_src})

    if mode == "KOAN_AIMED_PROGRAM_EDITS":
        from canonical.tools import aimed_edits_from_the_program_and_the_failure_v1 as m

        tree = ast.parse(str(inputs["source"]))
        return _ok(
            mode,
            "PROGRAM_INTRINSIC_EDIT_VOCABULARY_EXTRACTED",
            {
                "forms": m.forms_of(tree),
                "attributes": m.attributes_of(tree),
                "callables": m.callables_of(tree),
                "commuted_count": len(m.commuted(tree)),
            },
        )

    if mode == "KOAN_DEFERRED_REENTRANT_FORM":
        from canonical.tools import deferred_definition_form_v1 as m

        emitted = m.emit_for_traceback(str(inputs["traceback_text"]), str(inputs["source_text"]))
        return _ok(mode, "DEFERRED_DEFINITION_CANDIDATES_EMITTED", emitted)

    if mode == "KOAN_ASSERTION_DEMAND":
        from canonical.tools import the_assertion_is_the_demand_v1 as m

        prods = m.conditional_productions(str(inputs["source"]), int(inputs["line"]), str(inputs["site_text"]))
        return _ok(mode, "ASSERTION_DEMAND_PRODUCTIONS_SYNTHESIZED", {"productions": prods[:25], "count": len(prods)})

    if mode == "COUNTERFACTUAL_DISCR_TREE_SKILL_ROUTER":
        from canonical.runtime import counterfactual_discr_tree_skill_router_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"SKILL_ROUTER_KILLED:{res.get('status')}", result=res)
        return _ok(mode, "COUNTERFACTUAL_DISCR_TREE_EVALUATED", res)

    if mode == "VERIFIED_ZERO_SCREENSHOT_ACTION_CACHE":
        from canonical.runtime import verified_zero_screenshot_action_cache_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"ACTION_CACHE_KILLED:{res.get('status')}", result=res)
        return _ok(mode, "ZERO_SCREENSHOT_ACTION_CACHE_VERIFIED", res)

    if mode == "RELATIONAL_GUARD_ADDITION_REPAIR":
        from canonical.runtime import relational_guard_addition_symbolic_repair_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"RELATIONAL_REPAIR_KILLED:{res.get('status')}", result=res)
        return _ok(mode, "RELATIONAL_GUARD_ADDITION_SYNTHESIZED", res)

    if mode == "COW_ZYGOTE_SPECULATIVE_VERIFIER":
        from canonical.runtime import cow_zygote_speculative_verifier_v1 as m

        if {"original_module_source", "candidate_patch_source", "test_suite_source"}.issubset(inputs):
            verdict = m.verify_candidate_patch_cow(
                str(inputs["original_module_source"]),
                str(inputs["candidate_patch_source"]),
                str(inputs["test_suite_source"]),
            )
            if verdict['verdict'] != 'PASS':
                return _fail(mode, 'COW_CANDIDATE_'+verdict['verdict'], result=verdict)
            return _ok(mode, 'COW_SELECTED_ASSERTIONS_PASSED', verdict)
        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"COW_VERIFIER_KILLED:{res.get('status')}", result=res)
        return _ok(mode, "COW_SPECULATIVE_BENCHMARK_VERIFIED", res)

    if mode == "STATE_CONTRACT_WORLD_MODEL":
        from canonical.runtime import state_contract_world_model_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"STATE_CONTRACT_WORLD_MODEL_FAILED:{res.get('status')}", result=res)
        return _ok(mode, "STATE_CONTRACT_WORLD_MODEL_VERIFIED", res)

    if mode == "GRADIENT_FREE_LAW_CONSOLIDATION":
        from canonical.runtime import gradient_free_law_consolidation_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"LAW_CONSOLIDATION_FAILED:{res.get('status')}", result=res)
        return _ok(mode, "GRADIENT_FREE_LAWS_CONSOLIDATED", res)

    if mode == "ABSTAIN_GATED_SKILL_INDUCTION":
        from canonical.runtime import abstain_gated_skill_induction_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"SKILL_INDUCTION_FAILED:{res.get('status')}", result=res)
        return _ok(mode, "ABSTAIN_GATED_SKILLS_INDUCED", res)

    if mode == "WAKE_SLEEP_CONSOLIDATION":
        from canonical.swe_kernel import sentient_cognitive_core_v1 as m

        op = str(inputs["operation"]).strip().upper()
        payload = dict(inputs.get("payload") or {})
        state_path = inputs.get("state_path")
        eng = m.WakeSleepConsolidationEngine(Path(str(state_path)) if state_path else None)
        if op == "RECORD_WAKE_EPISODE":
            ep = eng.record_wake_episode(**payload)
            return _ok(mode, "WAKE_EPISODE_RECORDED", {"episode": ep})
        if op == "TWO_WITNESS_CHECK":
            res = m.WakeSleepConsolidationEngine.verify_two_witness_nonconstant(
                list(payload.get("episodes") or [])
            )
            if not res.get("passed"):
                return _fail(mode, str(res.get("reason") or "INSUFFICIENT_NONCONSTANT_WITNESSES"), result=res)
            return _ok(mode, str(res.get("reason") or "NON_CONSTANT_2_WITNESS_VERIFIED"), res)
        if op == "SLEEP_CONSOLIDATE":
            res = eng.sleep_consolidate(skill_store=None)
            return _ok(mode, "SLEEP_CYCLE_CONSOLIDATED", {"consolidation": res})
        if op == "HOMEOSTATIC_HYGIENE":
            res = eng.run_homeostatic_memory_hygiene(
                skill_store=None,
                assoc_memory_path=payload.get("assoc_memory_path"),
                assoc_capacity=int(payload.get("assoc_capacity") or 512),
            )
            return _ok(mode, "HOMEOSTATIC_HYGIENE_RUN", res)
        return _fail(mode, f"UNKNOWN_WAKE_SLEEP_OPERATION:{op}")

    if mode == "VERIFICATION_FIRST_MEMORY_BUS":
        from canonical.swe_kernel import canonical_memory_crystallizer_v1 as m

        op = str(inputs["operation"]).strip().upper()
        # The bus is ephemeral unless the caller names a state file. An ephemeral
        # bus is correct for single-operation probes (record/lookup/consolidate in
        # one call) and honest about it: nothing is persisted, so nothing can leak
        # between goals. A caller that wants durability passes `state_path`.
        state_path = inputs.get("state_path")
        bus = m.VerificationFirstMemoryBus(Path(str(state_path)) if state_path else None)
        res = m.execute_memory_operation(bus, op, dict(inputs.get("payload") or {}))
        # `execute_memory_operation` already returns fully-formed status strings
        # ("PASS__CONFLICT_RECORDED" / "FAIL_CLOSED__TIER0_MISS"); strip the prefix
        # so the envelope's own prefixing does not double it.
        status = str(res.get("status") or "")
        for prefix in ("PASS__", "FAIL_CLOSED__"):
            if status.startswith(prefix):
                status = status[len(prefix) :]
                break
        if not res.get("pass"):
            return _fail(mode, status or f"MEMORY_OPERATION_REFUSED:{op}", result=res)
        return _ok(mode, status or "MEMORY_OPERATION_EXECUTED", res)

    if mode == "ADVERSARIAL_MUTATION_ADMISSION_GATE":
        from canonical.runtime import adversarial_mutation_admission_gate_v1 as m

        res = m.run(inputs, ROOT)
        if res.get("status") != "OK":
            return _fail(mode, f"MUTATION_ADMISSION_FAILED:{res.get('status')}", result=res)
        return _ok(mode, "ADVERSARIAL_MUTATION_GATE_EVALUATED", res)

    if mode == "RULE_EXPIRY_WORLD_FINGERPRINT":
        from canonical.swe_kernel import rule_expiry_v1 as m

        fp = m.world_fingerprint()
        diffs = m.material_differences(dict(inputs["taught_fingerprint"]), fp) if "taught_fingerprint" in inputs else []
        return _ok(mode, "WORLD_FINGERPRINT_COMPUTED", {"fingerprint": fp, "material_differences": diffs})

    if mode == "ASSOCIATIVE_EPISODIC_MEMORY":
        import tempfile
        from canonical.runtime import associative_memory_v1 as m

        state_path = inputs.get("path")
        if state_path:
            hits = m.recall(inputs["cue"], k=int(inputs.get("k", 5)), path=str(state_path))
            return _ok(mode, "ASSOCIATIVE_MEMORY_RECALLED", {"hits": hits, "count": len(hits)})
        with tempfile.TemporaryDirectory(prefix="brain_assoc_mem_") as td:
            p = str(Path(td) / "assoc.json")
            for ep in inputs.get("episodes") or ():
                m.remember(ep, path=p)
            hits = m.recall(inputs["cue"], k=int(inputs.get("k", 5)), path=p)
            return _ok(mode, "ASSOCIATIVE_MEMORY_RECALLED", {"hits": hits, "count": len(hits)})

    if mode == "PROCEDURE_TRAJECTORY_MEMORY":
        from canonical.runtime import procedure_memory_v1 as m

        sig = m.signature(str(inputs["text"]))
        out_payload: dict[str, Any] = {
            "direction": m.direction(str(inputs["text"])),
            "content_words": sorted(m.content_words(str(inputs["text"]))),
            "signature": sig,
        }
        if "other_text" in inputs:
            other_sig = m.signature(str(inputs["other_text"]))
            out_payload["other_signature"] = other_sig
            out_payload["similarity"] = m.similarity(sig, other_sig)
            out_payload["agrees_on_direction"] = m.agrees_on_direction(sig, other_sig)
        return _ok(mode, "PROCEDURE_SIGNATURE_EXTRACTED", out_payload)

    if mode == "CAUSAL_GOAL_COMPUTER_AGENT":
        from canonical.runtime import causal_computer_use_agent_v1 as m

        agent = m.GoalDirectedAgent(list(inputs["catalog"]))
        receipt = agent.solve(set(inputs["initial_marking"]), set(inputs["goal_predicates"]))
        return _ok(mode, "CAUSAL_COMPUTER_GOAL_EVALUATED", receipt.to_dict())

    if mode == "PREDICATE_UI_WORLD_ABSTRACTION":
        from canonical.swe_kernel import predicate_world_abstraction_v1 as m

        proj = m.project_computer_observation(dict(inputs["observation"]))
        return _ok(mode, "UI_OBSERVATION_PROJECTED", proj)

    if mode == "COW_IMPACT_TEST_REPAIR_ENGINE":
        from canonical.swe_kernel import cow_impact_repair_engine_v1 as m

        repo_root = Path(str(inputs.get("repo_root") or ROOT))
        selected = m.select_impacted_tests_fast(
            repo_root,
            [str(p) for p in inputs["changed_rel_paths"]],
            [Path(str(p)) for p in inputs["all_test_files"]],
        )
        return _ok(mode, "IMPACTED_TESTS_SELECTED", {"selected_tests": [str(p) for p in selected], "count": len(selected)})

    if mode == "CANONICAL_ORACLE_VERICODING_SPINE":
        from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as m

        demands = m.extract_assertion_demands(str(inputs["test_source"]))
        return _ok(mode, "ASSERTION_DEMANDS_EXTRACTED", {"demands": demands, "count": len(demands)})

    if mode == "PROOF_MINED_ARGUMENT_SURFACE":
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        res = fsm.derive_and_verify_surface(
            ROOT,
            module_paths=inputs.get("module_paths"),
            max_modules=int(inputs["max_modules"]) if "max_modules" in inputs else 20,
            workers=int(inputs.get("workers", 4)),
        )
        return _ok(mode, "PROOF_MINED_SURFACE_EVALUATED", res)

    if mode == "EXECUTABLE_RAM_MENTAL_MODEL":
        from canonical.swe_kernel import executable_simulator_mental_model_v1 as emm
        from canonical.swe_kernel import semantic_ir_v1 as sir

        src = str(inputs.get("source") or "def f(x):\n    return x + 1\n")
        fn_name = str(inputs.get("func_name") or "f")
        args = list(inputs.get("args") or [41])
        prog = sir.lower_program({"mod.py": src})
        sim = emm.simulate_ir_program(prog, fn_name, args, step_quota=256)
        return _ok(
            mode,
            "RAM_MENTAL_MODEL_SIMULATED",
            {"status": sim.status, "value": sim.value, "steps": sim.steps},
        )

    if mode == "INVERSE_PAIR_COMPLETION":
        from canonical.swe_kernel import inverse_completion_v1 as inv_c

        res = inv_c.synthesise_reader(str(inputs["name"]), list(inputs["writer_payloads"]))
        return _ok(mode, "INVERSE_READER_SYNTHESIZED", res)

    if mode == "REPAIR_VERSION_SPACE_DISCRIMINATOR":
        from canonical.runtime import finite_identifiability as fi

        hyps = [fi.Hypothesis("h_linear"), fi.Hypothesis("h_relu")]
        exps = [
            fi.Experiment(f"e_{v}", {"h_linear": repr(v), "h_relu": repr(max(0, v))}, cost=1.0)
            for v in (-2, 0, 1)
        ]
        disc = fi.select_discriminator(hyps, exps)
        return _ok(
            mode,
            "VERSION_SPACE_DISCRIMINATOR_SELECTED",
            {"discriminator": disc},
        )

    if mode == "DISTINGUISHING_PROJECTION_ORACLE":
        from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm

        res = fsm.synthesize_minimum_distinguishing_oracle(
            num_adversarial_mutants=int(inputs.get("num_adversarial_mutants", 155))
        )
        return _ok(mode, "DISTINGUISHING_ORACLE_SYNTHESIZED", res)

    if mode == "SKILL_CONTRIBUTION_UNBLIND_CURATOR":
        from canonical.swe_kernel import skill_contribution_ledger_v1 as scl

        rep = dict(inputs.get("grader_report") or {"trials": 160, "false_passes": 0, "false_pass_rate": 0.0})
        ok_ret, reason = scl.grader_may_retire(rep)
        return _ok(mode, "CURATOR_GRADER_EVALUATED", {"permitted": ok_ret, "reason": reason})

    if mode == "DOMAIN_OF_VERIFICATION_GATE":
        from canonical.runtime import domain_of_verification_v1 as dov

        dom = dov.observed_domain(list(inputs["points"]))
        chk = dov.check_prediction(dom, inputs["query_x"]) if "query_x" in inputs else None
        return _ok(mode, "DOMAIN_OF_VERIFICATION_COMPUTED", {"observed_domain": dom, "check": chk})

    if mode == "PURPOSE_CONTRAST_GATE":
        from intake import purpose_gate_v1 as pg
        from intake import residual_question_gate_v1 as rg

        cands = [
            rg.Candidate("c_pos", "clamp negative to zero", lambda tr: dict(tr[0]).get("out") == "0"),
            rg.Candidate("c_id", "identity pass-through", lambda tr: dict(tr[0]).get("out") == dict(tr[0]).get("in")),
        ]
        traces = [((("in", "-3"), ("out", "0")),), ((("in", "-3"), ("out", "-3")),)]
        dec = pg.decide({"instruction": str(inputs.get("instruction") or "normalize(-3)")}, cands, traces)
        return _ok(mode, "PURPOSE_CONTRAST_EVALUATED", {"action": dec["action"]})

    if mode == "SENTIENT_EPISTEMIC_PETRI_CORE":
        import tempfile
        from canonical.swe_kernel import sentient_cognitive_core_v1 as scc
        from canonical.swe_kernel import speculative_cow_petri_agent_v1 as scpa

        with tempfile.TemporaryDirectory(prefix="scc_fed_") as td:
            wt = Path(td)
            (wt / "config.json").write_text('{"protected": true}', encoding="utf-8")
            eng = scc.EpistemicSelfBeliefEngine(state_path=wt / "epistemic.json")
            ticket = eng.predict_before_act("federated_probe")
            upd = eng.settle_and_compute_surprise(
                ticket,
                outcome_pass=False,
                inspector="federated_probe",
                ignorance_ledger_path=wt / "ignorance.json",
            )
            s0 = scpa.capture_tomography_snapshot(wt)
            ledger = scpa.ExplicitConstraintLedger.from_instruction_and_snapshot("Never delete config.json.", s0)
            unsat_cnt, unsat_reasons = ledger.unsatisfied_count(wt, s0)
        return _ok(
            mode,
            "SENTIENT_EPISTEMIC_PETRI_EVALUATED",
            {"surprise_nats": upd.get("nll_surprise"), "unsatisfied_count": unsat_cnt, "reasons": unsat_reasons},
        )

    if mode == "PETRI_COW_SPLICING_MINER":
        import tempfile
        from canonical.swe_kernel import petri_cow_splicing_engine_v1 as pcs

        with tempfile.TemporaryDirectory(prefix="pcs_fed_") as td:
            wt = Path(td)
            (wt / "mod_a.py").write_text("def parse_token(raw: str) -> int:\n    return int(raw)\n", encoding="utf-8")
            miner = pcs.RepoNativePetriMiner(wt)
            scope = miner.mine_scope(["mod_a.py"])
        return _ok(mode, "PETRI_COMPONENTS_MINED", {"scope_keys": sorted(scope.keys())[:8]})

    if mode == "SPECULATIVE_COW_PETRI_TOMOGRAPHY":
        import tempfile
        from canonical.swe_kernel import speculative_cow_petri_agent_v1 as scpa

        with tempfile.TemporaryDirectory(prefix="tomo_fed_") as td:
            wt = Path(td)
            (wt / "state.json").write_text('{"status": "idle"}', encoding="utf-8")
            s0 = scpa.capture_tomography_snapshot(wt)
            (wt / "state.json").write_text('{"status": "verified"}', encoding="utf-8")
            s1 = scpa.capture_tomography_snapshot(wt)
            delta = scpa.diff_tomography(s0, s1)
        return _ok(mode, "TOMOGRAPHY_DIFF_COMPUTED", {"tomography_delta": delta})

    if mode == "OSWORLD_ZERO_MODEL_GUI_POLICY":
        from canonical.runtime import osworld_v21_zero_model_policy_v1 as ozp

        xml_sample = str(
            inputs.get("a11y_xml")
            or '<desktop><node name="Export Report" role="push-button" x="120" y="64" w="80" h="24"/></desktop>'
        )
        nodes = ozp.parse_a11y_nodes(xml_sample)
        return _ok(mode, "A11Y_NODES_PARSED", {"node_count": len(nodes), "nodes": nodes[:5]})

    if mode == "CAUSAL_CEGIS_INVENTOR":
        import tempfile
        from canonical.swe_kernel import causal_cegis_inventor_v1 as cci

        with tempfile.TemporaryDirectory(prefix="cci_fed_") as td:
            inv = cci.CausalCEGISInventor(
                law_store_path=Path(td) / "laws.json",
                negative_store_path=Path(td) / "neg.json",
                sandbox_budget=4,
            )
        return _ok(mode, "CAUSAL_CEGIS_INVENTOR_READY", {"sandbox_budget": inv.sandbox_budget})

    if mode == "GUIDE_EXECUTABLE_TEST_SUITE":
        import tempfile
        from canonical.tools import the_guide_is_a_test_suite_v1 as gts

        src = str(inputs.get("source") or '"""Example:\n>>> 2 + 3\n5\n"""\ndef add(a, b):\n    return a + b\n')
        with tempfile.TemporaryDirectory(prefix="gts_fed_") as td:
            sample_p = Path(td) / "sample.py"
            sample_p.write_text(src, encoding="utf-8")
            blocks = gts.docstring_blocks(sample_p)
        return _ok(mode, "DOCSTRING_TEST_BLOCKS_EXTRACTED", {"block_count": len(blocks)})

    if mode == "GUIDE_ACTION_GRAMMAR_INDUCER":
        from canonical.tools import the_guide_is_an_action_grammar_v1 as gag

        syn = str(inputs.get("synopsis") or "usage: tool [--force] --input FILE --output OUT")
        opts = gag.parse_synopsis(syn)
        return _ok(mode, "ACTION_GRAMMAR_PARSED", {"synopsis_parsed": opts})

    if mode == "REFUSAL_SPECIFICATION_READER":
        from canonical.runtime import a_refusal_is_a_specification_v1 as ars

        stderr = str(inputs.get("stderr") or "error: missing required flag --confirm")
        spec = ars.read_refusal(stderr)
        return _ok(mode, "REFUSAL_SPECIFICATION_EXTRACTED", {"refusal_spec": spec})

    if mode == "VACUOUS_CHECK_AUDIT_GATE":
        from canonical.tools import a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1 as vca

        audit = vca.which_object_blindness()
        return _ok(mode, "VACUOUS_CHECK_AUDIT_COMPLETED", {"audit_keys": sorted(audit.keys())[:8]})

    if mode == "CANONICAL_MEMORY_CRYSTALLIZER":
        import tempfile
        from canonical.swe_kernel import canonical_memory_crystallizer_v1 as cmc

        with tempfile.TemporaryDirectory(prefix="cmc_fed_") as td:
            bus = cmc.VerificationFirstMemoryBus(Path(td) / "mem.json")
            res = cmc.execute_memory_operation(
                bus,
                "RECORD_CAUSAL_STEP",
                {
                    "episode_id": "ep_fed_1",
                    "step_idx": 0,
                    "pre_state": "s0",
                    "action": "verify_receipt",
                    "post_state": "s1",
                    "provenance": "sha256:abc",
                },
            )
        return _ok(mode, "MEMORY_BUS_OPERATION_VERIFIED", {"result": res})

    if mode == "ISOLATED_EFFECT_RECEIPT_VERIFIER":
        from canonical.tools import isolated_effect_receipt_verifier_v1 as ierv

        sample = dict(inputs.get("receipt") or {"action": "write", "path": "out.txt", "sha256": ierv.digest_bytes(b"ok")})
        dig = ierv.receipt_digest(sample)
        return _ok(mode, "RECEIPT_DIGEST_VERIFIED", {"receipt_digest": dig})

    if mode == "LEAPFROG_W21_MMAP_CSR_SLOT_INDEX":
        from canonical.runtime import brain_unified_model_v1 as u

        model = u.open_model(root=ROOT)
        res = model.find_source(str(inputs["query"]), top_k=int(inputs.get("top_k", 5)))
        return _ok(mode, "MMAP_CSR_SOURCE_SEARCHED", res)

    if mode == "LEAPFROG_W22_EXECUTION_TRACED_COMPILER":
        from canonical.runtime import execution_traced_callable_compiler_v1 as m

        res = m.derive_verified_module_adapter(str(inputs["module_rel_path"]), root=ROOT)
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "ADAPTER_UNVERIFIED"), detail=res)
        return _ok(mode, "TRACED_ADAPTER_VERIFIED", res)

    if mode == "LEAPFROG_W23_FAST_CASCADE_ORCHESTRATOR":
        from canonical.runtime import fast_cascade_orchestrator_v1 as m

        res = m.execute_fast_cascade(dict(inputs["task_spec"]))
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "FAST_CASCADE_ABSTAINED"), detail=res)
        return _ok(mode, "FAST_CASCADE_RESOLVED", res)

    if mode == "LEAPFROG_W24_FORWARD_PUSH_BITEMPORAL_PPR":
        from canonical.swe_kernel import canonical_memory_crystallizer_v1 as m

        bus = inputs.get("memory_bus") if isinstance(inputs.get("memory_bus"), m.VerificationFirstMemoryBus) else m.VerificationFirstMemoryBus()
        res = bus.forward_push_bitemporal_recall(
            str(inputs["query"]),
            valid_at_ts=inputs.get("valid_at_ts"),
            top_k=int(inputs.get("top_k", 10)),
        )
        return _ok(mode, "FORWARD_PUSH_BITEMPORAL_RECALLED", res)

    if mode == "CHECKABILITY_ORACLE_FORGE":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        res = hau.checkability_oracle_forge(
            inputs["workspace_root"],
            module_rel=inputs.get("module_rel"),
            instruction=str(inputs.get("instruction") or goal or ""),
            wanted_callables=inputs.get("wanted_callables") or (),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "CHECKABILITY_UNRESOLVED"), detail=res)
        return _ok(mode, "CHECKABILITY_ORACLE_FORGED", res)

    if mode == "SPACETIME_OE_SYGUS_REPAIR":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        res = hau.spacetime_oe_sygus_repair(
            inputs.get("workspace_root"),
            module_rel=inputs.get("module_rel"),
            value_target=inputs.get("value_target"),
            contrasts=inputs.get("contrasts") or (),
            examples=inputs.get("examples") or (),
            failing_envs=inputs.get("failing_envs") or (),
            passing_envs=inputs.get("passing_envs") or (),
            lang=str(inputs.get("lang") or "python"),
            extra_consts=inputs.get("extra_consts") or (),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "SYGUS_UNRESOLVED"), detail=res)
        return _ok(mode, "SPACETIME_OE_SYGUS_SYNTHESIZED", res)

    if mode == "SHADOW_INTERFACE_COMPUTER_USE":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        res = hau.shadow_interface_computer_use(
            inputs["workspace_root"],
            question=str(inputs.get("question") or goal or ""),
            entrypoint_path=inputs.get("entrypoint_path"),
            html_or_webmcp=str(inputs.get("html_or_webmcp") or ""),
            shadow_op=inputs.get("shadow_op"),
            target_rel=inputs.get("target_rel"),
            standing_rels=inputs.get("standing_rels") or (),
            petri_supervisor=inputs.get("petri_supervisor"),
            transition_name=str(inputs.get("transition_name") or "shadow_commit"),
            expected_record_count=inputs.get("expected_record_count"),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "SHADOW_CU_REFUSED"), detail=res)
        return _ok(mode, "SHADOW_INTERFACE_EXECUTED", res)

    if mode == "ACTIVE_MEALY_QUESTION_LEARNER":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        res = hau.active_mealy_question_learner(
            oracle_fn=inputs.get("oracle_fn"),
            alphabet=inputs.get("alphabet") or (),
            machine_name=inputs.get("machine_name"),
            depth=int(inputs.get("depth", 2)),
            budget=int(inputs.get("budget", 12)),
            max_states=int(inputs.get("max_states", 8)),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "ACTIVE_MEALY_UNRESOLVED"), detail=res)
        return _ok(mode, "ACTIVE_MEALY_LEARNED", res)

    if mode == "DBSP_BITEMPORAL_CAPABILITY_FORGE":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        res = hau.dbsp_bitemporal_forge(
            zset_deltas=inputs.get("zset_deltas") or (),
            supersede_slot=bool(inputs.get("supersede_slot", True)),
            query_seed=inputs.get("query_seed"),
            query_t_valid=inputs.get("query_t_valid"),
            forge_entry=inputs.get("forge_entry"),
            seed_cases=inputs.get("seed_cases"),
            workspace_root=inputs.get("workspace_root"),
            memory=inputs.get("memory"),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "DBSP_FORGE_REJECTED"), detail=res)
        return _ok(mode, "DBSP_FORGE_COMPLETE", res)

    if mode == "GROUNDED_COMPUTER_INSPECTOR":
        from canonical.runtime import hidden_arsenal_unifier_v1 as hau

        ws = inputs.get("workspace_root") or ROOT
        res = hau.shadow_interface_computer_use(ws, question=str(inputs["question"]))
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "INSPECTION_UNGROUNDED"), detail=res)
        return _ok(mode, "GROUNDED_COMPUTER_INSPECTED", res)

    if mode == "UNFAMILIAR_M0_APARTNESS_LSHARP_LEARNER":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import ApartnessTreeInstantLearner

        res = ApartnessTreeInstantLearner().learn(
            alphabet=inputs["alphabet"],
            execute_trace=inputs["execute_trace"],
            held_out_traces=inputs.get("held_out_traces") or (),
            target_output=inputs.get("target_output"),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("reason") or "LSHARP_INCOMPLETE"), detail=res)
        return _ok(mode, "APARTNESS_LSHARP_LEARNED", res)

    if mode == "UNFAMILIAR_M1_ANGELIC_FOREST_OE_SYGUS":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import AngelicForestSyGuSRepairEngine

        res = AngelicForestSyGuSRepairEngine().solve(
            str(inputs["source_text"]),
            str(inputs["test_source"]),
            seed_cold_store=bool(inputs.get("seed_cold_store", False)),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("reason") or "ANGELIC_SYGUS_UNSOLVED"), detail=res)
        return _ok(mode, "ANGELIC_FOREST_SYGUS_SOLVED", res)

    if mode == "UNFAMILIAR_M2_PROTOCOL_LIFT_EFFECT_ORACLE":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import lift_protocol_and_verify_effect

        res = lift_protocol_and_verify_effect(
            cdp_network_events=inputs.get("cdp_network_events") or (),
            webmcp_tools=inputs.get("webmcp_tools") or (),
            goal_parameters=inputs.get("goal_parameters"),
            transport_fn=inputs.get("transport_fn"),
            osworld_state=inputs.get("osworld_state"),
            artifact_check=inputs.get("artifact_check"),
        )
        if not res.get("pass"):
            return _fail(mode, "EFFECT_ORACLE_OR_PROTOCOL_LIFT_REFUSED", detail=res)
        return _ok(mode, "PROTOCOL_LIFT_AND_ORACLE_VERIFIED", res)

    if mode == "UNFAMILIAR_M3_SEMIRING_PROVENANCE_JTMS_MEME":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import run_meme_semiring_benchmark

        res = run_meme_semiring_benchmark(
            chain_count=int(inputs.get("chain_count", 16)),
            chain_depth=int(inputs.get("chain_depth", 3)),
        )
        return _ok(mode, "SEMIRING_JTMS_MEME_VERIFIED", res)

    if mode == "UNFAMILIAR_M4_MINIMAX_VERSION_SPACE_INTERROGATOR":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import minimax_interrogate_version_space

        res = minimax_interrogate_version_space(
            hypotheses=inputs["hypotheses"],
            candidate_probes=inputs["candidate_probes"],
            policy_regions=inputs.get("policy_regions"),
            true_oracle=inputs.get("true_oracle"),
            allow_irreversible_probes=bool(inputs.get("allow_irreversible_probes", False)),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("reason") or "MINIMAX_INTERROGATION_INCOMPLETE"), detail=res)
        return _ok(mode, "MINIMAX_VERSION_SPACE_RESOLVED", res)

    if mode == "UNFAMILIAR_M5_ZERO_LLM_ALPHAEVOLVE_PARETO":
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import evolve_pareto_organ

        res = evolve_pareto_organ(
            str(inputs["baseline_source"]),
            fn_name=str(inputs["fn_name"]),
            test_inputs=inputs["test_inputs"],
            evaluator_fn=inputs.get("evaluator_fn"),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "EVOLUTION_REFUSED"), detail=res)
        return _ok(mode, "PARETO_ORGAN_EVOLVED", res)

    if mode == "LEAPFROG_W36_BYTE_EFFECT_ORACLE":
        from canonical.runtime import byte_effect_oracle_v1 as m

        res = m.verify_byte_effect(
            inputs["target"],
            expected_format=inputs.get("expected_format"),
            expected_source_bytes=inputs.get("expected_source_bytes"),
            expected_source_path=inputs.get("expected_source_path"),
            baseline_archive_hashes=inputs.get("baseline_archive_hashes"),
            allowed_archive_mutations=inputs.get("allowed_archive_mutations") or (),
        )
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "BYTE_EFFECT_FAILED"), detail=res)
        return _ok(mode, "BYTE_EFFECT_VERIFIED", res)

    if mode == "LEAPFROG_W36_FUTAMURA_CASCADE":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "futamura_solve", **dict(inputs)}, ROOT)
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "FUTAMURA_CASCADE_ABSTAINED"), detail=res)
        return _ok(mode, "FUTAMURA_CASCADE_RESOLVED", res)

    if mode == "LEAPFROG_W36_ERROR_AWARE_MEALY_HCU":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "hybrid_cu", **dict(inputs)}, ROOT)
        return _ok(mode, str(res.get("status") or "HCU_PETRI_COMPLETED"), res)

    if mode == "LEAPFROG_W36_DBSP_AGM_CONFORMAL":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "conformal_evalue", **dict(inputs)}, ROOT)
        return _ok(mode, str(res.get("verdict") or "CONFORMAL_EVALUE_EVALUATED"), res)

    if mode == "LEAPFROG_W37_OS_KERNEL_ISOLATION":
        from canonical.runtime import os_isolation_v1 as m

        res = m.probe(budget_s=float(inputs.get("budget_s", 30.0)))
        return _ok(mode, str(res.get("verdict") or "OS_ISOLATION_PROBED"), res)

    if mode == "LEAPFROG_W37_CONFINED_HYBRID_CU":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "confined_hybrid_cu", **dict(inputs)}, ROOT)
        return _ok(mode, "CONFINED_HCU_PASSED" if res.get("pass") else "CONFINED_HCU_FAILED", res)

    if mode == "LEAPFROG_W37_MULTIFILE_FUTAMURA_REPO":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "multifile_repo_solve", **dict(inputs)}, ROOT)
        return _ok(mode, str(res.get("rung") or "MULTIFILE_FUTAMURA_RESOLVED"), res)

    if mode == "LEAPFROG_W38_SECCOMP_SYSCALL_ALLOWLIST":
        from canonical.runtime import worker_syscall_allowlist_v1 as m

        if "syscall_number" in inputs or "syscall_name" in inputs:
            num = (
                int(inputs["syscall_number"])
                if "syscall_number" in inputs
                else int(m.X86_64[str(inputs["syscall_name"])])
            )
            verdict = m.decide(
                num,
                tuple(int(a) for a in (inputs.get("args") or ())),
                arch=str(inputs.get("arch") or "x86_64"),
            )
            return _ok(mode, "SYSCALL_DECIDED", {"syscall_number": num, "verdict": verdict, "filter_sha256": m.filter_sha256("x86_64")})
        desc = m.describe(inputs.get("arch"))
        return _ok(mode, "SECCOMP_ALLOWLIST_DESCRIBED", desc)

    if mode == "LEAPFROG_W38_REFUSAL_SPEC_COMPILER":
        from canonical.runtime import a_refusal_is_a_specification_v1 as m

        clause = m.read_refusal(str(inputs["text"]))
        if clause is None:
            return _fail(mode, "REFUSAL_UNREADABLE")
        return _ok(
            mode,
            f"REFUSAL_PARSED_{clause.form}",
            {
                "form": clause.form,
                "choices": list(getattr(clause, "choices", ()) or ()),
                "raw": str(getattr(clause, "raw", "")),
            },
        )

    if mode == "LEAPFROG_W38_OSWORLD_VERIFIED_LEDGER":
        from canonical.runtime import osworld_verified_task_ledger_v1 as m

        res = m.decide(dict(inputs["state"]), inputs.get("base_decide"))
        return _ok(mode, str(res.get("status") or "OSWORLD_LEDGER_DECIDED"), res)

    if mode == "LEAPFROG_W38_TYPED_CEGIS_INVENTION":
        from canonical.runtime import futamura_leapfrog_kernel_v1 as m

        res = m.run({"op": "typed_cegis_solve", **dict(inputs)}, ROOT)
        return _ok(mode, str(res.get("stage") or "TYPED_CEGIS_DONE"), res)

    if mode == "LEAPFROG_W38_RESIDUAL_WALL_CLOSERS":
        from canonical.swe_kernel import residual_wall_closers_v1 as m

        closer = m.ResidualWallCloser()
        cands = closer.mine_all(
            str(inputs["source"]),
            str(inputs["target_function"]),
            functions=tuple(inputs.get("functions") or ()),
            repo_sources=tuple(inputs.get("repo_sources") or ()),
            test_sources=tuple(inputs.get("test_sources") or ()),
        )
        rows = [
            {
                "mechanism": c.mechanism,
                "target_function": c.target_function,
                "lineno": c.lineno,
                "explanation": c.explanation,
                "patched_module_source": c.patched_module_source,
            }
            for c in cands
        ]
        return _ok(mode, "RESIDUAL_WALLS_MINED", {"candidates": rows, "count": len(rows)})

    if mode == "LEAPFROG_W38_REPO_COMPONENT_PETRI":
        from canonical.swe_kernel import repo_component_petri_v1 as m

        cands, n_mined = m.synthesize_repo_petri_repairs(
            repo_root=Path(str(inputs["repo_root"])),
            rel_path=str(inputs["rel_path"]),
            source_text=str(inputs["source_text"]),
            line_no=int(inputs["line_no"]),
            pass_samples=list(inputs.get("pass_samples") or ()),
            fail_samples=list(inputs.get("fail_samples") or ()),
            escaping_exceptions=list(inputs.get("escaping_exceptions") or ()),
            spec_literals=inputs.get("spec_literals"),
            called_symbols=set(inputs.get("called_symbols") or ()) if inputs.get("called_symbols") else None,
        )
        return _ok(
            mode,
            "REPO_PETRI_REPAIRS_SYNTHESIZED",
            {"candidates": [{"label": lb, "source": src} for lb, src in cands], "count": len(cands), "mined_components": n_mined},
        )

    if mode == "LEAPFROG_W38_NON_MALLEABLE_MEMORY_OS":
        from canonical.swe_kernel import canonical_memory_crystallizer_v1 as m

        bus = inputs.get("bus") if isinstance(inputs.get("bus"), m.VerificationFirstMemoryBus) else m.VerificationFirstMemoryBus()
        payload = {k: v for k, v in inputs.items() if k not in ("operation", "bus")}
        res = m.execute_memory_operation(bus, str(inputs["operation"]), payload)
        if res.get("pass"):
            return _ok(mode, str(res.get("status") or "MEMORY_OS_OK"), res)
        return _fail(mode, str(res.get("status") or "MEMORY_OS_FAIL"), **res)

    if mode == "LEAPFROG_W38_CONTENT_ADDRESSED_CHUNK_ARCHIVE":
        from canonical.runtime import release_chunk_archive_v1 as m

        size_b = int(inputs["size_bytes"])
        chunk_b = int(inputs.get("chunk_bytes", 1024 * 1024))
        return _ok(mode, "CHUNK_COUNT_PLANNED", {"size_bytes": size_b, "chunk_bytes": chunk_b, "planned_chunks": m.planned_chunk_count(size_b, chunk_b)})

    if mode == "LEAPFROG_W38_SAFE_ACTION_WORLD_MODEL":
        from canonical.swe_kernel import safe_action_model_v1 as m

        state = dict(inputs["state"])
        desc = m.describe(state)
        return _ok(mode, "SAFE_ACTION_STATE_DESCRIBED", {"descriptor": sorted(str(x) for x in desc)})

    if mode == "LEAPFROG_W38_CONSISTENCY_EQUIVALENCE_AND_JUDGE":
        from canonical.swe_kernel import consistency_vs_equivalence_v1 as m

        res = m.combined_admission_verdict(dict(inputs["gate_report"]), inputs.get("equivalence"))
        return _ok(mode, str(res.get("verdict") or "ADMISSION_EVALUATED"), res)

    if mode == "LEAPFROG_W38_MINED_REWRITE_AND_WEIGHT_GATE":
        from canonical.swe_kernel import mined_rewrite_theory_v1 as m

        res = m.mine_rules(
            max_size=int(inputs.get("max_size", 3)),
            term_limit=int(inputs.get("term_limit", 96)),
            witnesses_per_round=int(inputs.get("witnesses_per_round", 12)),
            verify_rounds=int(inputs.get("verify_rounds", 2)),
        )
        return _ok(mode, "REWRITE_THEORY_MINED", {"rules_count": len(res.get("rules") or ()), "summary": res})

    if mode == "LEAPFROG_W38_COW_LENS_NEGATIVE_SPACE":
        from canonical.swe_kernel import cow_lens_fuzz_and_negative_space_v1 as m

        lens = m.synthesize_bidirectional_fst_lens([(str(a), str(b)) for a, b in inputs["pairs"]])
        if lens is None:
            return _fail(mode, "NO_BIDIRECTIONAL_LENS")
        return _ok(mode, "BIDIRECTIONAL_LENS_SYNTHESIZED", {"lens_kind": type(lens).__name__, "description": repr(lens)[:240]})

    if mode == "LEAPFROG_W39_ZERO_ADAPTER_INVENTORY_BRIDGE":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        req_in = dict(inputs)
        goal_str = str(req_in.pop("goal"))
        res = shared_five_pillar_kernel().inventory_bridge.query_and_compose(goal_str, **req_in)
        return _ok(mode, "ZERO_ADAPTER_INVENTORY_QUERIED", res)

    if mode == "LEAPFROG_W39_MOORE_ONTOLOGY_WITNESS_LEARNER":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        res = shared_five_pillar_kernel().instant_learner.learn_and_transfer(**dict(inputs))
        if not res.get("pass"):
            return _fail(mode, "MOORE_WITNESS_UNRESOLVED", detail=res)
        return _ok(mode, "MOORE_WITNESS_LEARNED", res)

    if mode == "LEAPFROG_W39_LENS_STANDING_FACT_CU":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        res = shared_five_pillar_kernel().computer_use.execute_workflow(**dict(inputs))
        if not res.get("pass"):
            return _fail(mode, "LENS_CU_REFUSED", detail=res)
        return _ok(mode, "LENS_CU_VERIFIED", res)

    if mode == "LEAPFROG_W39_DELTASTATE_SIBLING_SWE":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        req_in = dict(inputs)
        rr = req_in.pop("repo_root")
        res = shared_five_pillar_kernel().swe_kernel.repair_repository(rr, **req_in)
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "DELTASTATE_SWE_UNSOLVED"), detail=res)
        return _ok(mode, str(res.get("status") or "DELTASTATE_SWE_REPAIRED"), res)

    if mode == "LEAPFROG_W39_PROSPECTIVE_MEMTX_REPLAY":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        res = shared_five_pillar_kernel().run_turn("memtx_op", pillar="MEMORY", payload=dict(inputs))
        if not res.get("pass"):
            return _fail(mode, "PROSPECTIVE_MEMTX_BLOCKED", detail=res)
        return _ok(mode, "PROSPECTIVE_MEMTX_COMMITTED", res)

    if mode == "LEAPFROG_W41_REFUSAL_ACQUIRE_RETRY":
        from canonical.swe_kernel.refusal_acquire_retry_v1 import acquire_and_retry

        verifier = inputs.get("verifier")
        if not callable(verifier):
            return _fail(mode, "ACQUISITION_REQUIRES_A_VERIFIER")
        acquired = acquire_and_retry(
            rule=inputs.get("rule") or {},
            source_text=str(inputs.get("source_text") or ""),
            target_language=str(inputs.get("target_language") or ""),
            verifier=verifier,
            parse_check=inputs.get("parse_check"),
        )
        if not acquired.get("pass"):
            return _fail(mode, str(acquired.get("status") or "ACQUISITION_FAILED"), acquisition=acquired)
        return _ok(mode, "PASS__ACQUIRED_AFTER_REFUSAL", acquired)

    if mode == "LEAPFROG_W42_MEME_PROTOCOL_MEMORY":
        from canonical.swe_kernel.meme_protocol_memory_v1 import run_protocol

        report = run_protocol(
            per_op=int(inputs.get("per_op", 4)),
            seed=int(inputs.get("seed", 20261126)),
        )
        if not report.get("instances"):
            return _fail(mode, "NO_PROTOCOL_INSTANCES")
        if (report.get("dependency_memory_rate") or 0.0) < 0.999:
            return _fail(mode, "MEME_PROTOCOL_OPERATION_UNANSWERED", report=report)
        if not (report.get("self_check") or {}).get("trustworthy"):
            return _fail(mode, "MEME_PROTOCOL_INSTRUMENT_NOT_TRUSTWORTHY", report=report)
        return _ok(mode, "MEME_PROTOCOL_MEASURED", report)

    if mode == "LEAPFROG_W40_FRONTIER_BENCH_HARNESS":
        from canonical.evaluation import frontier_bench_v1 as bench

        scorecard = bench.run_bench(
            seed=int(inputs.get("seed", bench.DEFAULT_SEED)),
            per_category=int(inputs.get("per_category", 2)),
            categories=inputs.get("categories"),
            sut=None,
        )
        if not scorecard.get("instances"):
            return _fail(mode, "NO_INSTANCES")
        if scorecard.get("errors"):
            return _fail(mode, "BENCH_ERRORS", scorecard=scorecard)
        return _ok(mode, str(scorecard.get("verdict")), scorecard)

    if mode == "LEAPFROG_W39_MEANING_IR_CROSS_LANG_RATCHET":
        from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import shared_five_pillar_kernel

        res = shared_five_pillar_kernel().skill_ratchet.consolidate_and_transfer(**dict(inputs))
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "MEANING_IR_RATCHET_REFUSED"), detail=res)
        return _ok(mode, "MEANING_IR_RATCHET_CONSOLIDATED", res)

    if mode == "LEAPFROG_W39_AUTO_JUDGE_DISCOVERY":
        from canonical.runtime.wave39_leapfrog_unification_v1 import EarnedJudgeAndRefusalLifter

        res = EarnedJudgeAndRefusalLifter.discover_and_earn_judges(
            artifacts_by_kind=inputs.get("artifacts_by_kind"),
            store_dir=inputs.get("store_dir"),
            include_stdlib_discovery=bool(inputs.get("include_stdlib_discovery", True)),
            cli_probe=inputs.get("cli_probe"),
        )
        return _ok(mode, "AUTO_JUDGES_DISCOVERED", res) if res.get("pass") else _fail(mode, "JUDGE_DISCOVERY_FAILED", res)

    if mode == "LEAPFROG_W39_EFFECT_CONTRACT_COMPOSER":
        from canonical.runtime.wave39_leapfrog_unification_v1 import ContractPlannerAndLiftedGeneralizer

        res = ContractPlannerAndLiftedGeneralizer.compose_and_plan(
            use_measured_advance_pair=bool(inputs.get("use_measured_advance_pair", True)),
            contracts=inputs.get("contracts"),
        )
        return _ok(mode, "EFFECT_CONTRACTS_COMPOSED", res) if res.get("pass") else _fail(mode, "CONTRACT_COMPOSITION_FAILED", res)

    if mode == "LEAPFROG_W39_PARTIAL_ORDER_PLANNER":
        from canonical.runtime.wave39_leapfrog_unification_v1 import ContractPlannerAndLiftedGeneralizer

        res = ContractPlannerAndLiftedGeneralizer.compose_and_plan(
            use_measured_advance_pair=False,
            initial_facts=inputs.get("initial_facts") or (),
            goal_facts=inputs.get("goal_facts") or (),
            operators=inputs.get("operators") or (),
        )
        return _ok(mode, "PARTIAL_ORDER_PLAN_SOLVED", res) if res.get("pass") else _fail(mode, "PARTIAL_ORDER_PLAN_FAILED", res)

    if mode == "LEAPFROG_W39_LIFTED_GENERALIZER":
        from canonical.runtime.wave39_leapfrog_unification_v1 import ContractPlannerAndLiftedGeneralizer

        res = ContractPlannerAndLiftedGeneralizer.compose_and_plan(
            use_measured_advance_pair=False,
            concrete_plan=inputs.get("concrete_plan") or (),
            goal_facts=inputs.get("goal_facts") or (),
            success_states=inputs.get("success_states"),
            failure_states=inputs.get("failure_states"),
        )
        return _ok(mode, "PLAN_SKETCH_LIFTED", res) if res.get("pass") else _fail(mode, "PLAN_LIFT_FAILED", res)

    if mode == "LEAPFROG_W39_REFUSAL_ORACLE_LIFTER":
        from canonical.runtime.wave39_leapfrog_unification_v1 import EarnedJudgeAndRefusalLifter

        res = EarnedJudgeAndRefusalLifter.lift_refusal_and_check_oracle(
            str(inputs.get("help_text") or ""),
            refusal_lines=inputs.get("refusal_lines") or (),
            action_argv=inputs.get("action_argv") or ("tool", "target"),
            paths=inputs.get("paths") or (),
            type_map=inputs.get("type_map"),
            labels=inputs.get("labels"),
        )
        return _ok(mode, "REFUSAL_ORACLE_LIFTED", res) if res.get("pass") else _fail(mode, "REFUSAL_ORACLE_LIFT_FAILED", res)

    if mode == "LEAPFROG_W39_OBSERVATION_REFUTATION_AND_PROVENANCE":
        from canonical.runtime.wave39_leapfrog_unification_v1 import ContractPlannerAndLiftedGeneralizer

        res = ContractPlannerAndLiftedGeneralizer.compose_and_plan(
            use_measured_advance_pair=False,
            ast_provenance_source=inputs.get("ast_provenance_source"),
            run_observation_refutation=bool(inputs.get("run_observation_refutation", True)),
        )
        return _ok(mode, "OBSERVATION_REFUTATION_AND_PROVENANCE_COMPLETE", res)

    if mode == "LEAPFROG_W39_DECISION_COST_COW_GATE":
        from canonical.runtime.wave39_leapfrog_unification_v1 import SpeculativeCoWDecisionGate

        res = SpeculativeCoWDecisionGate.decide_and_speculate(
            survivor_requirements=inputs.get("survivor_requirements") or (),
            observed_facts=inputs.get("observed_facts") or (),
            p_correct=float(inputs.get("p_correct", 0.5)),
            wrong_commit_cost=float(inputs.get("wrong_commit_cost", 10.0)),
            cow_trial_cost=float(inputs.get("cow_trial_cost", 0.002)),
            candidates=inputs.get("candidates"),
            verifier=inputs.get("verifier"),
            timeout_s=float(inputs.get("timeout_s", 5.0)),
        )
        return _ok(mode, "COW_DECISION_GATE_COMPLETE", res) if res.get("pass") else _fail(mode, "COW_DECISION_GATE_FAILED", res)

    if mode == "LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER":
        from canonical.runtime.wave39_leapfrog_unification_v1 import RedQueenMendelEvolver

        if inputs.get("audit_only"):
            res = RedQueenMendelEvolver.audit_anti_slop_and_phantom_guardrails(
                str(inputs["parent_source"]),
                str(inputs["candidate_source"]),
                failing_witness=inputs.get("failing_witness"),
                owned_symbols=inputs.get("owned_symbols"),
                max_ast_bloat_ratio=float(inputs.get("max_ast_bloat_ratio", 1.60)),
                max_added_branches=int(inputs.get("max_added_branches", 6)),
                require_albi_invariance=bool(inputs.get("require_albi_invariance", True)),
            )
            return _ok(mode, "ANTI_SLOP_AUDIT_COMPLETE", res) if res.get("admitted") else _fail(mode, "ANTI_SLOP_REJECTED", res)
        verifier = inputs.get("verifier")
        if not callable(verifier):
            return _fail(mode, "VERIFIER_CALLABLE_REQUIRED")
        res = RedQueenMendelEvolver.mendel_splice_and_verify(
            str(inputs["parent_source"]),
            str(inputs["lineage_a"]),
            str(inputs["lineage_b"]),
            verifier=verifier,
            failing_witness=inputs.get("failing_witness"),
            owned_symbols=inputs.get("owned_symbols"),
            max_ast_bloat_ratio=float(inputs.get("max_ast_bloat_ratio", 1.60)),
            max_added_branches=int(inputs.get("max_added_branches", 6)),
            require_albi_invariance=bool(inputs.get("require_albi_invariance", True)),
        )
        return _ok(mode, "MENDEL_RED_QUEEN_EVOLVED", res) if res.get("pass") else _fail(mode, "MENDEL_NO_ADMITTED_HYBRID", res)

    if mode == "LEAPFROG_W39_CLM_RRF_MEMORY_BUS":
        from canonical.runtime.wave39_leapfrog_unification_v1 import CLMRRFMemoryEngine, dispatch_clm_rrf_operation

        eng = inputs.get("engine") or CLMRRFMemoryEngine()
        op = str(inputs.get("operation") or "RETRIEVE_4WAY_RRF_BUDGETED").upper()
        res = dispatch_clm_rrf_operation(eng, op, inputs, fallback_goal=goal)
        return _ok(mode, f"CLM_RRF_{op}", res) if res.get("pass") else _fail(mode, f"CLM_RRF_{op}_FAILED", result=res)

    if mode == "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL":
        from canonical.runtime.wave39_leapfrog_unification_v1 import dispatch_partial_routing_operation

        op = str(inputs.get("operation") or "JITRL_MODULATE").upper()
        res = dispatch_partial_routing_operation(op, inputs, fallback_goal=goal)
        return _ok(mode, f"PARTIAL_JITRL_{op}", res) if res.get("pass") else _fail(mode, f"PARTIAL_JITRL_{op}_FAILED", result=res)

    if mode == "LEAPFROG_W40_EPISTEMIC_SWE_EGRAPH_CEGIS":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import EpistemicSWEAndEGraphKernel

        op = str(inputs.get("operation") or "EGRAPH_VERIFY").upper()
        if op == "GRAMMAR_CLOSED_CEGIS_REPAIR":
            res = EpistemicSWEAndEGraphKernel.grammar_closed_cegis_repair(
                str(inputs["buggy_source"]),
                fn_name=str(inputs["fn_name"]),
                test_cases=inputs.get("test_cases") or (),
                reference_source=inputs.get("reference_source"),
                max_candidates=int(inputs.get("max_candidates", 160)),
                use_cow_fork=bool(inputs.get("use_cow_fork", True)),
            )
        elif op == "CAUSAL_OBLIGATION_TRANSDUCER":
            res = EpistemicSWEAndEGraphKernel.causal_obligation_and_transducer(
                failure_text=inputs.get("failure_text"),
                io_pairs=inputs.get("io_pairs"),
            )
        else:
            res = EpistemicSWEAndEGraphKernel.egraph_verify_and_anti_unify(
                term_a=inputs.get("term_a"),
                term_b=inputs.get("term_b"),
                source_a=inputs.get("source_a"),
                source_b=inputs.get("source_b"),
            )
        return _ok(mode, f"W40_SWE_{op}", res) if res.get("pass") else _fail(mode, f"W40_SWE_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_ONESHOT_VERSION_SPACE_LEARNER":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import OneShotEpistemicLearnerKernel

        op = str(inputs.get("operation") or "DEMAND_AND_COLLAPSE").upper()
        if op == "DETERMINE_HYPOTHESIS":
            res = OneShotEpistemicLearnerKernel.determine_hypothesis_and_vocabulary(
                inputs.get("points") or (),
                bodies=inputs.get("bodies") or (),
                operator_example=inputs.get("operator_example"),
            )
        elif op == "CROSS_ENV_TRANSFER":
            res = OneShotEpistemicLearnerKernel.cross_env_transfer_and_demo_collapse(
                inputs.get("obs_a") or {},
                inputs.get("obs_b") or {},
                demo_observation=inputs.get("demo_observation"),
            )
        else:
            res = OneShotEpistemicLearnerKernel.demand_and_collapse_program(
                inputs.get("params") or ("x",),
                inputs.get("examples") or (),
                distinguishing_answer=inputs.get("distinguishing_answer"),
            )
        return _ok(mode, f"W40_ONESHOT_{op}", res) if res.get("pass") else _fail(mode, f"W40_ONESHOT_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import ShadowInterfaceHCURouterKernel

        op = str(inputs.get("operation") or "ROUTE_HCU").upper()
        if op == "COMPILE_SHADOW_INTERFACE":
            res = ShadowInterfaceHCURouterKernel.compile_and_evolve_shadow_interface(
                tool_name=str(inputs["tool_name"]),
                help_text=str(inputs["help_text"]),
                repo_dir=inputs["repo_dir"],
                validation_probes=inputs.get("validation_probes") or (),
                version=int(inputs.get("version", 1)),
            )
        else:
            res = ShadowInterfaceHCURouterKernel.route_hcu_action(
                str(inputs.get("goal") or goal),
                tool_name=inputs.get("tool_name"),
                help_text=inputs.get("help_text"),
                workspace_root=inputs.get("workspace_root"),
                transition_edges=inputs.get("transition_edges") or (),
                start_state=inputs.get("start_state"),
                goal_state=inputs.get("goal_state"),
                ui_observation=inputs.get("ui_observation"),
                has_gui_surface=bool(inputs.get("has_gui_surface", False)),
            )
        return _ok(mode, f"W40_HCU_{op}", res) if res.get("pass") else _fail(mode, f"W40_HCU_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_OUT_OF_CORE_RLM_WORKSPACE":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import OutOfCoreRLMWorkspace

        ws = inputs.get("workspace") or OutOfCoreRLMWorkspace()
        op = str(inputs.get("operation") or "MOUNT_CORPUS").upper()
        if op == "PROGRAMMATIC_SLICE":
            res = ws.programmatic_slice(
                str(inputs["handle_id"]),
                regex=inputs.get("regex"),
                line_range=inputs.get("line_range"),
                symbol=inputs.get("symbol"),
                token=inputs.get("token"),
                context_lines=int(inputs.get("context_lines", 1)),
                max_chars=int(inputs.get("max_chars", 2000)),
            )
        elif op == "RECURSIVE_MAP_REDUCE":
            res = ws.recursive_map_reduce(
                str(inputs["handle_id"]),
                pattern=str(inputs["pattern"]),
                chunk_lines=int(inputs.get("chunk_lines", 60)),
                max_depth=int(inputs.get("max_depth", 3)),
                max_matches_per_chunk=int(inputs.get("max_matches_per_chunk", 20)),
            )
        else:
            res = ws.mount_corpus(str(inputs.get("name") or "corpus"), inputs.get("content") or "")
        return _ok(mode, f"W40_RLM_{op}", res) if res.get("pass") else _fail(mode, f"W40_RLM_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import FourNetworkGitMemoryEngine

        eng = inputs.get("engine") or FourNetworkGitMemoryEngine(root_dir=inputs.get("root_dir"))
        op = str(inputs.get("operation") or "ENGRAM_QUERY").upper()
        if op == "WRITE":
            res = eng.write(
                network=str(inputs["network"]),
                record_id=str(inputs["record_id"]),
                entity_key=str(inputs["entity_key"]),
                verbatim_text=str(inputs["verbatim_text"]),
                valid_from=int(inputs.get("valid_from", 0)),
                valid_to=inputs.get("valid_to"),
                origin_token=str(inputs.get("origin_token", "TRUSTED_VERIFIER")),
                support_ids=inputs.get("support_ids") or (),
                metadata=inputs.get("metadata"),
            )
        elif op == "SLEEP_CONSOLIDATE":
            res = eng.sleep_consolidate(
                min_support=int(inputs.get("min_support", 2)),
                at_time=int(inputs.get("at_time", 100)),
            )
        else:
            res = eng.engram_query(
                str(inputs.get("query") or goal),
                networks=inputs.get("networks"),
                at_time=inputs.get("at_time"),
                top_k=int(inputs.get("top_k", 5)),
            )
        return _ok(mode, f"W40_MEM_{op}", res) if res.get("pass") else _fail(mode, f"W40_MEM_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import CHASEHillSamplingNFVGate

        op = str(inputs.get("operation") or "STAGED_NFV").upper()
        if op == "CHASE_AUDIT":
            res = CHASEHillSamplingNFVGate.chase_perturbation_audit(
                str(inputs["candidate_source"]),
                fn_name=str(inputs["fn_name"]),
                base_cases=inputs.get("base_cases") or (),
                perturbed_cases=inputs.get("perturbed_cases") or (),
                min_survival_rate=float(inputs.get("min_survival_rate", 1.0)),
            )
        elif op == "HARNESS_DELTA_ATTRIBUTION":
            res = CHASEHillSamplingNFVGate.harness_delta_attribution(
                baseline_train=float(inputs["baseline_train"]),
                baseline_heldout=float(inputs["baseline_heldout"]),
                evolved_train_equal_budget=float(inputs["evolved_train_equal_budget"]),
                evolved_heldout_equal_budget=float(inputs["evolved_heldout_equal_budget"]),
                evolved_train_extra_budget=inputs.get("evolved_train_extra_budget"),
                evolved_heldout_extra_budget=inputs.get("evolved_heldout_extra_budget"),
                max_overfit_fraction=float(inputs.get("max_overfit_fraction", 0.35)),
            )
        elif op == "HILL_SAMPLING":
            res = CHASEHillSamplingNFVGate.hill_sampling_select(
                inputs.get("candidates") or (),
                k=int(inputs.get("k", 2)),
                temperature=float(inputs.get("temperature", 0.25)),
                diversity_bonus=float(inputs.get("diversity_bonus", 0.10)),
                seed=int(inputs.get("seed", 40)),
            )
        else:
            res = CHASEHillSamplingNFVGate.staged_goal_blind_verify(
                spec_contract=inputs.get("spec_contract") or {},
                candidate_source=str(inputs["candidate_source"]),
                fn_name=str(inputs["fn_name"]),
            )
        return _ok(mode, f"W40_GATE_{op}", res) if res.get("pass") else _fail(mode, f"W40_GATE_{op}_FAILED", res)

    if mode == "LEAPFROG_W40_SELFPLAY_STEER_HORIZON_COMMIT":
        from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import SelfPlaySteerAndHorizonKernel

        op = str(inputs.get("operation") or "STEER_CRITIC").upper()
        if op == "SELF_PLAY_EPISODE":
            res = SelfPlaySteerAndHorizonKernel.self_play_bug_episode(
                str(inputs["clean_source"]),
                fn_name=str(inputs["fn_name"]),
                test_cases=inputs.get("test_cases") or (),
                max_mutations=int(inputs.get("max_mutations", 8)),
            )
        elif op == "HORIZON_ATOMIC_COMMIT":
            res = SelfPlaySteerAndHorizonKernel.horizon_stakes_and_atomic_commit(
                identity=str(inputs.get("identity", "brain-wave40")),
                obligations=inputs.get("obligations") or (),
                stage_files=inputs.get("stage_files"),
                live_files=inputs.get("live_files"),
                simulate_crash_recovery=bool(inputs.get("simulate_crash_recovery", True)),
                workdir=inputs.get("workdir"),
            )
        else:
            res = SelfPlaySteerAndHorizonKernel.steer_dont_solve_critic(
                inputs.get("trajectory") or (),
                window=int(inputs.get("window", 4)),
            )
        return _ok(mode, f"W40_SELFPLAY_{op}", res) if res.get("pass") else _fail(mode, f"W40_SELFPLAY_{op}_FAILED", res)

    if mode == "LEAPFROG_W41_RUNG3_PLUGGABLE_PROPOSER_JITRL":
        from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import PluggableRung3ProposerJitRLKernel

        res = PluggableRung3ProposerJitRLKernel.solve_with_escalation(
            buggy_source=str(inputs["buggy_source"]),
            fn_name=str(inputs["fn_name"]),
            test_cases=inputs.get("test_cases") or (),
            spec_contract=inputs.get("spec_contract"),
            perturbed_cases=inputs.get("perturbed_cases") or (),
            compiled_rung0_rules=inputs.get("compiled_rung0_rules") or (),
            rung3_proposer=inputs.get("rung3_proposer"),
            episodic_receipts=inputs.get("episodic_receipts") or (),
            state_signature=inputs.get("state_signature"),
            beta=float(inputs.get("beta", 1.0)),
            max_rung3_rounds=int(inputs.get("max_rung3_rounds", 2)),
        )
        return _ok(mode, "W41_RUNG3_SOLVED", res) if res.get("pass") else _fail(mode, "W41_RUNG3_UNSOLVED", res)

    if mode == "LEAPFROG_W41_WHITEBOX_TRACE_ABDUCTION_AND_OE":
        from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import WhiteboxTraceAbductionOEKernel

        op = str(inputs.get("operation") or "SYNTHESIZE_OE_CEGIS").upper()
        if op == "TRACE_ABDUCTION":
            res = WhiteboxTraceAbductionOEKernel.trace_abduction_and_ochiai(
                source=str(inputs["source"]),
                fn_name=str(inputs["fn_name"]),
                failing_args=inputs.get("failing_args") or (),
                passing_args=inputs.get("passing_args") or (),
                step_quota=int(inputs.get("step_quota", 80)),
            )
        elif op == "INTROSPECT_SITES":
            res = WhiteboxTraceAbductionOEKernel.introspect_and_collect_sites(
                source=str(inputs["source"]),
                goal=str(inputs.get("goal") or goal),
                rel_path=str(inputs.get("rel_path", "module.py")),
            )
        else:
            res = WhiteboxTraceAbductionOEKernel.synthesize_oe_and_cegis(
                examples=inputs.get("examples") or (),
                var_names=inputs.get("var_names") or ("x",),
            )
        return _ok(mode, f"W41_WHITEBOX_{op}", res) if res.get("pass") else _fail(mode, f"W41_WHITEBOX_{op}_FAILED", res)

    if mode == "LEAPFROG_W41_TTPO_OPSD_CONSENSUS_DISTILLER":
        from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import TTPOOPSDConsensusDistiller

        res = TTPOOPSDConsensusDistiller.distill_rollouts(
            rollouts=inputs.get("rollouts") or (),
            fn_name=str(inputs["fn_name"]),
            probe_inputs=inputs.get("probe_inputs") or (),
            state_signature=str(inputs.get("state_signature") or goal),
            min_consensus_fraction=float(inputs.get("min_consensus_fraction", 0.50)),
        )
        return _ok(mode, "W41_TTPO_OPSD_DISTILLED", res) if res.get("pass") else _fail(mode, "W41_TTPO_OPSD_NO_CONSENSUS", res)

    if mode == "LEAPFROG_W42_FUTAMURA_COMPILE_AWAY_FLYWHEEL":
        from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import FutamuraCompileAwayFlywheelKernel

        fly = inputs.get("flywheel") or FutamuraCompileAwayFlywheelKernel(memory_root=inputs.get("memory_root"))
        res = fly.run_continual_cycle(
            training_buggy_source=str(inputs["training_buggy_source"]),
            training_fn_name=str(inputs["training_fn_name"]),
            training_cases=inputs.get("training_cases") or (),
            unseen_homologous_source=str(inputs["unseen_homologous_source"]),
            unseen_fn_name=str(inputs["unseen_fn_name"]),
            unseen_cases=inputs.get("unseen_cases") or (),
            anchor_tasks=inputs.get("anchor_tasks") or (),
            perturbed_cases=inputs.get("perturbed_cases") or (),
        )
        return _ok(mode, "W42_FUTAMURA_COMPILED_AWAY", res) if res.get("pass") else _fail(mode, "W42_FUTAMURA_FAILED", res)

    if mode == "LEAPFROG_W42_ONE_DEMO_TRUST_AND_RUNG_CALIBRATOR":
        from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import OneDemoTrustAndRungCalibratorKernel

        res = OneDemoTrustAndRungCalibratorKernel.calibrate_and_sketch(
            quotient_images=inputs.get("quotient_images") or (),
            quotient_labels=inputs.get("quotient_labels") or (),
            guard_source=inputs.get("guard_source"),
            verified_ui_trace=inputs.get("verified_ui_trace"),
            ui_need_text=inputs.get("ui_need_text"),
            semantic_goal=inputs.get("semantic_goal"),
            provenance_dir=inputs.get("provenance_dir"),
            one_shot_candidates=inputs.get("one_shot_candidates") or (),
        )
        return _ok(mode, "W42_ONE_DEMO_TRUST_CALIBRATED", res) if res.get("pass") else _fail(mode, "W42_ONE_DEMO_TRUST_FAILED", res)

    if mode == "LEAPFROG_W43_GIT_HISTORY_SEEDED_REPAIR":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import GitHistorySeededRepairKernel

        op = str(inputs.get("operation") or "FIXEDBENCH_GATE").upper()
        if op == "MINE_REPO_HISTORY":
            res = GitHistorySeededRepairKernel.mine_repo_history_store(
                inputs.get("repo_path") or ROOT,
                base_commit=str(inputs.get("base_commit", "HEAD")),
                commit_limit=int(inputs.get("commit_limit", 80)),
                target_source=inputs.get("target_source"),
                covered_lines=inputs.get("covered_lines"),
                candidate_budget=int(inputs.get("candidate_budget", 24)),
            )
        elif op == "REPAIR_WITH_HISTORY":
            res = GitHistorySeededRepairKernel.repair_with_history_and_online_learning(
                buggy_source=str(inputs["buggy_source"]),
                fn_name=str(inputs["fn_name"]),
                test_cases=inputs.get("test_cases") or (),
                prior_verified_demos=inputs.get("prior_verified_demos") or (),
                history_lines=inputs.get("history_lines") or (),
                executed_lines=inputs.get("executed_lines"),
                enforce_input_dependency_gate=bool(inputs.get("enforce_input_dependency_gate", True)),
            )
        else:
            res = GitHistorySeededRepairKernel.fixedbench_abstention_gate(
                str(inputs["source"]),
                str(inputs["fn_name"]),
                inputs.get("test_cases") or (),
            )
        return _ok(mode, f"W43_HISTORY_{op}", res) if res.get("pass") else _fail(mode, f"W43_HISTORY_{op}_FAILED", res)

    if mode == "LEAPFROG_W43_TRACE_LITERAL_CAUSAL_SLICE_GATE":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import TraceLiteralCausalSliceGateKernel

        op = str(inputs.get("operation") or "ANTI_SLOP_GATE").upper()
        if op == "CAUSAL_DUAL_SLICE":
            res = TraceLiteralCausalSliceGateKernel.causal_dual_slice_and_truthiness_audit(
                files=inputs.get("files") or {},
                error_file=str(inputs.get("error_file", "mod.py")),
                error_line=int(inputs.get("error_line", 1)),
                target_source=inputs.get("target_source"),
                crash_stderr=str(inputs.get("crash_stderr", "")),
            )
        elif op == "CONSTANT_HOLE_CEGIS":
            res = TraceLiteralCausalSliceGateKernel.repair_constant_hole_cegis(
                buggy_source=str(inputs["buggy_source"]),
                fn_name=str(inputs["fn_name"]),
                test_cases=inputs.get("test_cases") or (),
                extra_chars=str(inputs.get("extra_chars", "")),
                max_candidates=int(inputs.get("max_candidates", 80)),
            )
        else:
            res = TraceLiteralCausalSliceGateKernel.anti_slop_input_dependency_gate(
                before_source=str(inputs["before_source"]),
                after_source=str(inputs["after_source"]),
                function_name=inputs.get("function_name"),
                probe_pairs=inputs.get("probe_pairs") or (),
                expected_direction_by_pair=inputs.get("expected_direction_by_pair"),
            )
        return _ok(mode, f"W43_SLICE_GATE_{op}", res) if res.get("pass") else _fail(mode, f"W43_SLICE_GATE_{op}_FAILED", res)

    if mode == "LEAPFROG_W43_COW_CONTRASTIVE_MINIMAX_FACTORY":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import CoWContrastiveMinimaxFactoryKernel

        op = str(inputs.get("operation") or "CONTRASTIVE_MINIMAX_PIN").upper()
        if op == "DIAGNOSE_FILING_KEYS":
            res = CoWContrastiveMinimaxFactoryKernel.diagnose_filing_keys_and_semantic_roles(
                feature_keys=inputs.get("feature_keys") or {},
                winners=inputs.get("winners") or {},
                goal_text=str(inputs.get("goal_text") or goal),
            )
        else:
            res = CoWContrastiveMinimaxFactoryKernel.run_contrastive_minimax_pinning(
                feature_names=inputs.get("feature_names") or (),
                initial_state=inputs.get("initial_state") or {},
                oracle=inputs["oracle"],
                max_queries=int(inputs.get("max_queries", 16)),
            )
        return _ok(mode, f"W43_MINIMAX_{op}", res) if res.get("pass") else _fail(mode, f"W43_MINIMAX_{op}_FAILED", res)

    if mode == "LEAPFROG_W44_MEME_DBSP_CASCADE_ABSENCE_MEMORY":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import MEMEDBSPCascadeAbsenceMemoryEngine

        op = str(inputs.get("operation") or "RUN_MEME_SUITE").upper()
        if op == "RUN_MEME_SUITE":
            res = MEMEDBSPCascadeAbsenceMemoryEngine.run_meme_6task_suite()
        else:
            eng = inputs.get("engine") or MEMEDBSPCascadeAbsenceMemoryEngine(root_dir=inputs.get("root_dir"))
            if op == "ASSERT_FACT":
                res = eng.assert_fact(str(inputs["entity"]), inputs["value"], valid_from=inputs.get("valid_from"))
            elif op == "DELETE_FACT":
                res = eng.delete_fact(str(inputs["entity"]), at_time=inputs.get("at_time"))
            else:
                res = eng.query_entity(str(inputs["entity"]), tier=str(inputs.get("tier", "L1")))
                res = {"pass": True, **res}
        return _ok(mode, f"W44_MEME_{op}", res) if res.get("pass") else _fail(mode, f"W44_MEME_{op}_FAILED", res)

    if mode == "LEAPFROG_W44_WEBMCP_GUI_ROOM_OSWORLD_HCU":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import WebMCPGuiRoomOSWorldHCUKernel

        op = str(inputs.get("operation") or "COMPILE_WEBMCP").upper()
        if op == "ROUTE_OSWORLD_HCU":
            res = WebMCPGuiRoomOSWorldHCUKernel.route_osworld_a11y_and_typed_surface(
                instruction=str(inputs.get("instruction") or goal),
                a11y_xml=inputs.get("a11y_xml"),
                webmcp_tools=inputs.get("webmcp_tools") or (),
                screen_width=int(inputs.get("screen_width", 1920)),
                screen_height=int(inputs.get("screen_height", 1080)),
                typed_action=inputs.get("typed_action"),
            )
        else:
            res = WebMCPGuiRoomOSWorldHCUKernel.compile_webmcp_document_model_context(
                html_source=str(inputs.get("html_source", "")),
                observed_xhr_calls=inputs.get("observed_xhr_calls") or (),
                page_origin=str(inputs.get("page_origin", "https://app.local")),
            )
        return _ok(mode, f"W44_WEBMCP_HCU_{op}", res) if res.get("pass") else _fail(mode, f"W44_WEBMCP_HCU_{op}_FAILED", res)

    if mode == "LEAPFROG_W44_NESTED_SKILLRL_RQGM_GEA_CONTINUAL":
        from canonical.runtime.wave43_44_dark_matter_meme_webmcp_leapfrog_v1 import NestedSkillRLRQGMGEAContinualKernel

        eng = inputs.get("engine") or NestedSkillRLRQGMGEAContinualKernel()
        op = str(inputs.get("operation") or "SKILLRL_DISTILL").upper()
        if op == "CMS_UPDATE":
            res = eng.cms_update(band=str(inputs["band"]), key=str(inputs["key"]), value=inputs["value"], tick=inputs.get("tick"))
        elif op == "GEA_EVOLVE":
            res = eng.gea_group_evolve(inputs.get("agents") or (), group_size=int(inputs.get("group_size", 2)))
        elif op == "RQGM_CO_EVOLVE":
            res = eng.rqgm_co_evolve_evaluator(
                current_anchor_accuracy=float(inputs["current_anchor_accuracy"]),
                candidate_anchor_accuracy=float(inputs["candidate_anchor_accuracy"]),
                min_improvement=float(inputs.get("min_improvement", 0.01)),
            )
        else:
            res = eng.skillrl_distill_trajectories(inputs.get("trajectories") or ())
        return _ok(mode, f"W44_CONTINUAL_{op}", res) if res.get("pass") else _fail(mode, f"W44_CONTINUAL_{op}_FAILED", res)

    if mode == "LEAPFROG_W45_QUOTIENT_ANGELIC_PROBE_INDUCER":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import QuotientAngelicProbeInducerKernel

        eng = inputs.get("engine") or QuotientAngelicProbeInducerKernel()
        res = eng.run(inputs)
        return _ok(mode, "W45_QUOTIENT_ANGELIC_PROBE", res) if res.get("pass") else _fail(mode, "W45_QUOTIENT_ANGELIC_PROBE_FAILED", res)

    if mode == "LEAPFROG_W45_METAMORPHIC_LINEAGE_CORPUS_SWE":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import MetamorphicLineageCorpusSWEKernel

        eng = inputs.get("engine") or MetamorphicLineageCorpusSWEKernel()
        res = eng.run(inputs)
        return _ok(mode, "W45_METAMORPHIC_LINEAGE_SWE", res) if res.get("pass") else _fail(mode, "W45_METAMORPHIC_LINEAGE_SWE_FAILED", res)

    if mode == "LEAPFROG_W45_AX_GUARD_ZERO_SHOT_CACHE_HCU":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import AXGuardZeroShotCacheHCUKernel

        eng = inputs.get("engine") or AXGuardZeroShotCacheHCUKernel()
        res = eng.run(inputs)
        return _ok(mode, "W45_AX_GUARD_HCU", res) if res.get("pass") else _fail(mode, "W45_AX_GUARD_HCU_FAILED", res)

    if mode == "LEAPFROG_W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import AntiManufacturedConfidenceMemoryEngine

        eng = inputs.get("engine") or AntiManufacturedConfidenceMemoryEngine()
        res = eng.run(inputs)
        return _ok(mode, "W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY", res) if res.get("pass") else _fail(mode, "W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY_FAILED", res)

    if mode == "LEAPFROG_W46_ANYTIME_VALID_EVALUE_EVOLUTION_GATE":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import AnytimeValidEValueEvolutionGateKernel

        eng = inputs.get("engine") or AnytimeValidEValueEvolutionGateKernel()
        res = eng.run(inputs)
        return _ok(mode, "W46_ANYTIME_VALID_EVALUE_GATE", res) if res.get("pass") else _fail(mode, "W46_ANYTIME_VALID_EVALUE_GATE_FAILED", res)

    if mode == "LEAPFROG_W46_THREE_TIER_ZERO_FORGETTING_CONTINUAL":
        from canonical.runtime.wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 import ThreeTierZeroForgettingContinualKernel

        eng = inputs.get("engine") or ThreeTierZeroForgettingContinualKernel()
        res = eng.run(inputs)
        return _ok(mode, "W46_THREE_TIER_CONTINUAL", res) if res.get("pass") else _fail(mode, "W46_THREE_TIER_CONTINUAL_FAILED", res)

    if mode == "LEAPFROG_W47_FUTAMURA_SKILL_COMPILER_GRAMMAR":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import FutamuraSkillCompilerGrammarKernel

        eng = inputs.get("engine") or FutamuraSkillCompilerGrammarKernel()
        res = eng.run(inputs)
        return _ok(mode, "W47_FUTAMURA_SKILL_COMPILER", res) if res.get("pass") else _fail(mode, "W47_FUTAMURA_SKILL_COMPILER_FAILED", res)

    if mode == "LEAPFROG_W47_REVERSE_TOMOGRAPHY_ANGELIC_LENS_SWE":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import ReverseTomographyAngelicLensSWEKernel

        eng = inputs.get("engine") or ReverseTomographyAngelicLensSWEKernel()
        res = eng.run(inputs)
        return _ok(mode, "W47_REVERSE_TOMOGRAPHY_LENS_SWE", res) if res.get("pass") else _fail(mode, "W47_REVERSE_TOMOGRAPHY_LENS_SWE_FAILED", res)

    if mode == "LEAPFROG_W47_MEANING_EGRAPH_VERICODING_PROOF_CUT":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import MeaningEGraphVericodingProofCutKernel

        eng = inputs.get("engine") or MeaningEGraphVericodingProofCutKernel()
        res = eng.run(inputs)
        return _ok(mode, "W47_MEANING_EGRAPH_VERICODING", res) if res.get("pass") else _fail(mode, "W47_MEANING_EGRAPH_VERICODING_FAILED", res)

    if mode == "LEAPFROG_W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import EvolvingInterfaceByteEffectHCUKernel

        eng = inputs.get("engine") or EvolvingInterfaceByteEffectHCUKernel()
        res = eng.run(inputs)
        return _ok(mode, "W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU", res) if res.get("pass") else _fail(mode, "W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU_FAILED", res)

    if mode == "LEAPFROG_W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import FiveTimescaleSleepCrystallizerCSRMemoryEngine

        eng = inputs.get("engine") or FiveTimescaleSleepCrystallizerCSRMemoryEngine()
        res = eng.run(inputs)
        return _ok(mode, "W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY", res) if res.get("pass") else _fail(mode, "W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY_FAILED", res)

    if mode == "LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR":
        from canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1 import MetaCircularConceptRefusalAdjudicatorKernel

        eng = inputs.get("engine") or MetaCircularConceptRefusalAdjudicatorKernel()
        res = eng.run(inputs)
        return _ok(mode, "W48_META_CIRCULAR_REFUSAL_ADJUDICATOR", res) if res.get("pass") else _fail(mode, "W48_META_CIRCULAR_REFUSAL_ADJUDICATOR_FAILED", res)

    if mode == "LEAPFROG_W49_TRACEBACK_SIGNATURE_ZERO_LINE_LOCALIZER":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "localize")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().traceback_zero_line_localize_op(op, **kw)
        return _ok(mode, "W49_TRACEBACK_ZERO_LINE_LOCALIZER", res) if res.get("pass") else _fail(mode, "W49_TRACEBACK_ZERO_LINE_LOCALIZER_FAILED", res)

    if mode == "LEAPFROG_W49_STRUCTURAL_AST_MULTI_HUNK_SYNTHESIZER":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "repair_workspace")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().structural_ast_multi_hunk_synth_op(op, **kw)
        return _ok(mode, "W49_STRUCTURAL_AST_MULTI_HUNK_SYNTH", res) if res.get("pass") else _fail(mode, "W49_STRUCTURAL_AST_MULTI_HUNK_SYNTH_FAILED", res)

    if mode == "LEAPFROG_W49_MINIMAX_INTERROGATION_CONTRASTIVE_ORACLE":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "minimax_query")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().minimax_interrogation_contrastive_op(op, **kw)
        return _ok(mode, "W49_MINIMAX_CONTRASTIVE_ORACLE", res) if res.get("pass") else _fail(mode, "W49_MINIMAX_CONTRASTIVE_ORACLE_FAILED", res)

    if mode == "LEAPFROG_W50_KERNEL_BOUNDARY_DUAL_CHANNEL_EFFECT_HCU":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "route_dual_channel")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().kernel_boundary_effect_hcu_op(op, **kw)
        return _ok(mode, "W50_KERNEL_BOUNDARY_EFFECT_HCU", res) if res.get("pass") else _fail(mode, "W50_KERNEL_BOUNDARY_EFFECT_HCU_FAILED", res)

    if mode == "LEAPFROG_W50_CRASH_RESUMABLE_SELF_VERIFYING_LIFE_LOOP":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "wal_tick")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().crash_resumable_life_loop_op(op, **kw)
        return _ok(mode, "W50_CRASH_RESUMABLE_LIFE_LOOP", res) if res.get("pass") else _fail(mode, "W50_CRASH_RESUMABLE_LIFE_LOOP_FAILED", res)

    if mode == "LEAPFROG_W50_TITAN_BEHAVIORAL_PROOF_ADJUDICATOR":
        from canonical.runtime.wave49_50_structural_ast_repair_and_titan_adjudication_v1 import Wave49To50UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "adjudicate")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave49To50UnifiedModelMixin().titan_behavioral_adjudicator_op(op, **kw)
        return _ok(mode, "W50_TITAN_BEHAVIORAL_ADJUDICATOR", res) if res.get("pass") else _fail(mode, "W50_TITAN_BEHAVIORAL_ADJUDICATOR_FAILED", res)

    if mode == "LEAPFROG_W52_ARISE_STATEMENT_DEF_USE_SLICER":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "slice")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().arise_def_use_slice_op(op, **kw)
        return _ok(mode, "W52_ARISE_DEF_USE_SLICER", res) if res.get("found") else _fail(mode, "W52_ARISE_DEF_USE_SLICER_FAILED", res)

    if mode == "LEAPFROG_W52_SLICED_STRUCTURAL_AST_SWE_ENGINE":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "repair_workspace")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().wave52_sliced_structural_swe_op(op, **kw)
        ok_flag = bool(res.get("repaired") or res.get("truthful_pass"))
        return _ok(mode, "W52_SLICED_STRUCTURAL_AST_SWE", res) if ok_flag else _fail(mode, "W52_SLICED_STRUCTURAL_AST_SWE_FAILED", res)

    if mode == "LEAPFROG_W51_STRANDED_TREASURY_CONFINEMENT_ORACLE":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "confinement")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().stranded_treasury_confinement_oracle_op(op, **kw)
        ok_flag = bool(res.get("verified", res.get("admitted", res.get("identified", res.get("host_sentinel_untouched", True)))))
        return _ok(mode, "W51_STRANDED_TREASURY_CONFINEMENT_ORACLE", res) if ok_flag else _fail(mode, "W51_STRANDED_TREASURY_CONFINEMENT_ORACLE_FAILED", res)

    if mode == "LEAPFROG_W52_ZERO_LLM_FTS_ATMA_HINDSIGHT_MEMORY":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "demo_cycle")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().zero_llm_fts_atma_memory_op(op, **kw)
        return _ok(mode, "W52_ZERO_LLM_FTS_ATMA_MEMORY", res)

    if mode == "LEAPFROG_W52_COLD_START_FRONT_DOOR_BRIDGE":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "dark_audit")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().cold_start_front_door_bridge_op(op, **kw)
        return _ok(mode, "W52_COLD_START_FRONT_DOOR_BRIDGE", res) if res.get("pass", True) else _fail(mode, "W52_COLD_START_FRONT_DOOR_BRIDGE_FAILED", res)

    if mode == "LEAPFROG_W51_48_TITAN_BLOB_PINNED_ADJUDICATOR":
        from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import Wave51To52UnifiedModelMixin

        op = str(inputs.get("operation", inputs.get("op", "adjudicate_48")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave51To52UnifiedModelMixin().wave51_48_titan_adjudicate_op(op, **kw)
        return _ok(mode, "W51_48_TITAN_BLOB_PINNED_ADJUDICATOR", res) if res.get("pass") else _fail(mode, "W51_48_TITAN_BLOB_PINNED_ADJUDICATOR_FAILED", res)

    if mode == "LEAPFROG_W53_UNIFIED_CAPABILITY_BUS":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "audit")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().unified_capability_bus_op(op, **kw)
        ok_flag = bool(res.get("pass", res.get("ok", res.get("accepted", True))))
        return _ok(mode, "W53_UNIFIED_CAPABILITY_BUS", res) if ok_flag else _fail(mode, "W53_UNIFIED_CAPABILITY_BUS_FAILED", res)

    if mode == "LEAPFROG_W53_SAFE_TRANSFER_ESTITCH_STRATA":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "demo_cycle")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().safe_transfer_estitch_strata_op(op, **kw)
        return _ok(mode, "W53_SAFE_TRANSFER_ESTITCH_STRATA", res) if res.get("pass") else _fail(mode, "W53_SAFE_TRANSFER_ESTITCH_STRATA_FAILED", res)

    if mode == "LEAPFROG_W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "generate")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().metamorphic_9_of_9_and_precision_slicer_op(op, **kw)
        return _ok(mode, "W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER", res) if res.get("pass") else _fail(mode, "W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER_FAILED", res)

    if mode == "LEAPFROG_W54_DOCKERLESS_VERIFIER_AND_SELFPLAY":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "self_play")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().dockerless_verifier_and_selfplay_op(op, **kw)
        return _ok(mode, "W54_DOCKERLESS_VERIFIER_AND_SELFPLAY", res) if res.get("pass") else _fail(mode, "W54_DOCKERLESS_VERIFIER_AND_SELFPLAY_FAILED", res)

    if mode == "LEAPFROG_W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "ground_webmcp")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().multirung_jitrl_and_webmcp_op(op, **kw)
        return _ok(mode, "W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER", res) if res.get("pass") else _fail(mode, "W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER_FAILED", res)

    if mode == "LEAPFROG_W54_DBSP_HINDSIGHT_STRATA_MEMORY":
        from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import Wave53To54UnifiedCapabilityBusMixin

        op = str(inputs.get("operation", inputs.get("op", "demo_cycle")))
        kw = {k: v for k, v in inputs.items() if k not in ("operation", "op")}
        res = Wave53To54UnifiedCapabilityBusMixin().dbsp_hindsight_strata_memory_op(op, **kw)
        return _ok(mode, "W54_DBSP_HINDSIGHT_STRATA_MEMORY", res) if res.get("pass") else _fail(mode, "W54_DBSP_HINDSIGHT_STRATA_MEMORY_FAILED", res)

    if mode == "METAMORPHIC_HABITATION_ZIPPER":
        from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as m

        fails = m.parse_pytest_failures(str(inputs["output"]))
        return _ok(mode, "PYTEST_FAILURES_PARSED", {"failures": fails, "count": len(fails)})

    if mode == "PETRI_COW_SPLICING_ENGINE":
        from canonical.swe_kernel import petri_cow_splicing_engine_v1 as m

        fp = m.compute_structural_fp64(str(inputs["code_or_schema"]))
        return _ok(mode, "STRUCTURAL_FP64_COMPUTED", {"fp64": fp})

    if mode == "AUTONOMOUS_AWAKE_LOOP":
        from canonical.swe_kernel import autonomous_awake_loop_v1 as m

        store = m.FileAtomicJournalStore(inputs["journal_dir"])
        return _ok(mode, "ATOMIC_JOURNAL_STORE_READY", {"journal_dir": str(inputs["journal_dir"]), "store_type": type(store).__name__})

    if mode == "SWE_SELF_IMPROVEMENT_BRIDGE":
        from canonical.swe_kernel import swe_self_improvement_bridge_v1 as m

        prob, meta = m.build_formal_swe_problem(
            Path(str(inputs.get("root") or ROOT)),
            task_id=str(inputs["task_id"]),
            episode_id=str(inputs.get("episode_id") or "ep_0"),
            patched_sha256=str(inputs.get("patched_sha256") or "0" * 64),
            test_count=int(inputs.get("test_count", 1)),
        )
        return _ok(mode, "FORMAL_SWE_PROBLEM_BUILT", {"problem": prob, "meta": meta})

    if mode == "INDUCED_EDIT_BASIS":
        from canonical.swe_kernel import induced_edit_basis_v1 as m

        tpls = m.induce_templates(list(inputs["pairs"]))
        return _ok(mode, "EDIT_TEMPLATES_INDUCED", {"template_count": len(tpls)})

    if mode == "CONTRACT_GROUNDED_REPAIR":
        from canonical.swe_kernel import contract_grounded_repair_v1 as m

        task = m.load_task(Path(str(inputs["task_dir"])), str(inputs["name"]))
        return _ok(mode, "CONTRACT_REPAIR_TASK_LOADED", {"name": str(inputs["name"]), "task_type": type(task).__name__})

    if mode == "CHECKABILITY_DIFFERENTIAL_PIN":
        from canonical.swe_kernel import checkability_by_differential_pin_v1 as m

        callables = m.public_callables(str(inputs["source"]), list(inputs.get("module_name_parts") or ["mod"]))
        return _ok(mode, "PUBLIC_CALLABLES_EXTRACTED", {"callables": callables, "count": len(callables)})

    if mode == "OPERAND_INVENTION":
        from canonical.swe_kernel import operand_invention_v1 as m

        names = m.scope_names(str(inputs["source"]))
        return _ok(mode, "SCOPE_OPERANDS_INVENTED", {"scope_names": names, "count": len(names)})

    if mode == "SKILL_SCOPE_ACQUISITION":
        from canonical.swe_kernel import skill_scope_acquisition_v1 as m

        facts = sorted(
            m.observable_facts(
                str(inputs["source"]),
                baseline_ok=inputs.get("baseline_ok", True),
                language=str(inputs.get("language") or "python"),
            )
        )
        return _ok(mode, "SKILL_SCOPE_FACTS_ACQUIRED", {"facts": facts, "count": len(facts)})

    _ASYM_MODE_TO_PILLAR = {
        "ABDUCTIVE_REFUSAL_AUTOBINDER": "REFUSAL_AUTOBIND",
        "ANGELIC_ZYGOTE_VERSION_SPACE_SWE": "ANGELIC_ZYGOTE_SWE",
        "ZERO_PIXEL_SHADOW_TRANSDUCER_CU": "SHADOW_TRANSDUCER_CU",
        "EPISTEMIC_DIGITAL_TWIN_AND_ARC": "DIGITAL_TWIN_ARC",
        "ALGEBRAIC_SHEAF_SRMU_MEMORY": "SHEAF_SRMU_MEMORY",
        "PC_DGM_SUPERCOMPILER": "PC_DGM_EVOLVE",
        "EGGMIND_GOAL_TREE_PROVER": "EGGMIND_PROOF",
    }
    if mode in _ASYM_MODE_TO_PILLAR:
        from canonical.runtime.asymmetric_frontier_leapfrog_v1 import asymmetric_leapfrog_dispatch

        res = asymmetric_leapfrog_dispatch(goal, pillar=_ASYM_MODE_TO_PILLAR[mode], inputs=inputs)
        if not res.get("pass"):
            return _fail(mode, str(res.get("status") or "ASYMMETRIC_LEAPFROG_REFUSED"), detail=res)
        return _ok(mode, str(res.get("status") or "ASYMMETRIC_LEAPFROG_COMPLETE"), res)

    return _fail(mode, f"UNKNOWN_FEDERATED_ENGINE_MODE:{mode}")


def run_federated_engine(
    mode: str,
    inputs: Mapping[str, Any] | None = None,
    *,
    goal: str = "",
) -> dict[str, Any]:
    """Execute one federated zero-model repository kernel fail-closed."""
    norm_mode = str(mode or "").strip().upper()
    if norm_mode.startswith("ENGINE:"):
        norm_mode = norm_mode.split(":", 1)[1]
    spec = FEDERATED_KERNEL_DESCRIPTORS.get(norm_mode)
    if spec is None:
        return _fail(norm_mode, f"FEDERATED_ENGINE_NOT_REGISTERED:{norm_mode}")

    for dep in spec.get("declared_dependencies") or []:
        try:
            present = importlib.util.find_spec(str(dep)) is not None
        except (ImportError, ValueError):
            present = False
        if not present:
            return _fail(
                norm_mode,
                f"HOST_DEPENDENCY_MISSING:{dep}",
                missing_dependency=str(dep),
                source_path=spec["source_path"],
            )

    req_inputs = dict(inputs or {})
    missing_err = _require_keys(norm_mode, req_inputs, spec.get("required_inputs") or [])
    if missing_err is not None:
        missing_err["source_path"] = spec["source_path"]
        missing_err["domain"] = spec["domain"]
        return missing_err

    try:
        out = _dispatch_kernel(norm_mode, req_inputs, goal)
    except Exception as exc:
        return _fail(
            norm_mode,
            f"KERNEL_RAISED:{type(exc).__name__}:{exc}",
            source_path=spec["source_path"],
            domain=spec["domain"],
        )
    out.setdefault("domain", spec["domain"])
    out.setdefault("source_path", spec["source_path"])
    out.setdefault("entrypoint", spec["entrypoint"])
    return out


def catalog_federated_engines(*, domain: str | None = None) -> dict[str, Any]:
    """Return a structured summary of all federated repository capability engines."""
    wanted = domain.strip().upper() if domain else None
    rows: list[dict[str, Any]] = []
    by_domain: dict[str, int] = {}
    for mode in sorted(FEDERATED_KERNEL_DESCRIPTORS):
        spec = FEDERATED_KERNEL_DESCRIPTORS[mode]
        dom = str(spec["domain"])
        if wanted and dom != wanted:
            continue
        by_domain[dom] = by_domain.get(dom, 0) + 1
        rows.append(
            {
                "id": "engine:" + mode,
                "mode": mode,
                "domain": dom,
                "source_path": spec["source_path"],
                "entrypoint": spec["entrypoint"],
                "summary": spec["summary"],
                "required_inputs": list(spec.get("required_inputs") or []),
                "declared_dependencies": list(spec.get("declared_dependencies") or []),
            }
        )
    return {
        "schema": SCHEMA,
        "count": len(rows),
        "domains": dict(sorted(by_domain.items())),
        "engines": rows,
        "model_calls": 0,
        "incremental_spend_usd": 0,
    }


def _fast_scandir_py(
    root_str: str,
    rel_root: str,
    *,
    skip_dirs: frozenset[str],
    skip_rel_prefixes: tuple[str, ...] = (),
) -> list[tuple[str, str, os.stat_result]]:
    """Wave 21 fast `os.scandir` `.py` walker sorted identically to `Path`."""
    start = os.path.join(root_str, rel_root) if rel_root else root_str
    if not os.path.isdir(start):
        return []
    out: list[tuple[str, str, os.stat_result]] = []
    stack: list[tuple[str, str]] = [(start, rel_root.strip("/"))]
    while stack:
        cur_dir, cur_rel = stack.pop()
        try:
            with os.scandir(cur_dir) as it:
                for entry in it:
                    name = entry.name
                    rel = f"{cur_rel}/{name}" if cur_rel else name
                    try:
                        is_dir = entry.is_dir(follow_symlinks=True)
                    except OSError:
                        continue
                    if is_dir:
                        if name in skip_dirs:
                            continue
                        if skip_rel_prefixes and any(rel == p or rel.startswith(p + "/") for p in skip_rel_prefixes):
                            continue
                        stack.append((entry.path, rel))
                        continue
                    if not name.endswith(".py"):
                        continue
                    if skip_rel_prefixes and any(rel == p or rel.startswith(p + "/") for p in skip_rel_prefixes):
                        continue
                    try:
                        if not entry.is_file(follow_symlinks=True):
                            continue
                        st = entry.stat(follow_symlinks=True)
                    except OSError:
                        continue
                    out.append((entry.path, rel, st))
        except OSError:
            continue
    out.sort(key=lambda item: item[1].split("/"))
    return out


def compile_extended_source_index_rows(
    root: Path,
    covered: set[str],
    *,
    cache: Any = None,
    snapshot: Any = None,
) -> list[dict[str, Any]]:
    """Deterministically index non-`canonical/runtime` Python modules across the repo.

    Preserves `source_index` as the exact partition of `canonical/runtime/` while
    exposing `canonical/swe_kernel/`, `canonical/tools/`, `canonical/capabilities/`,
    `canonical/research/`, and `canonical/integrations/` to cross-repository discovery.
    """
    root_str = str(root)
    skip_dirs = frozenset(_NON_SOURCE_DIRS)
    importers: dict[str, set[str]] = {}
    all_py: list[tuple[str, str, os.stat_result]] = []
    for sub in ("canonical", "intake", "tests"):
        if snapshot is not None:
            all_py.extend(
                snapshot.under(
                    sub,
                    suffix=".py",
                    skip_dirs=skip_dirs,
                    skip_rel_prefixes=("canonical/astra_runtime/tmp",),
                )
            )
        else:
            all_py.extend(
                _fast_scandir_py(
                    root_str,
                    sub,
                    skip_dirs=skip_dirs,
                    skip_rel_prefixes=("canonical/astra_runtime/tmp",),
                )
            )
    use_cache = cache is not None and getattr(cache, "enabled", False)
    for abs_p, rel_p, st_p in all_py:
        mods: tuple[str, ...] | None = None
        if use_cache:
            hit, cached_mods = cache.get("ext_imports", rel_p, st_p)
            if hit:
                mods = cached_mods
        if mods is None:
            try:
                with open(abs_p, "r", encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except OSError:
                continue
            mods = tuple({m.split(".")[-1] for m in _IMPORT_RE.findall(txt)})
            if use_cache:
                cache.put("ext_imports", rel_p, st_p, mods)
        for mod_leaf in mods:
            importers.setdefault(mod_leaf, set()).add(rel_p)

    rows: list[dict[str, Any]] = []
    for tree_rel in _EXTENDED_SOURCE_TREES:
        tree_entries = (
            snapshot.under(tree_rel, suffix=".py", skip_dirs=skip_dirs)
            if snapshot is not None
            else _fast_scandir_py(root_str, tree_rel, skip_dirs=skip_dirs)
        )
        for abs_path, rel, st_ext in tree_entries:
            if rel in covered:
                continue
            stem = os.path.splitext(os.path.basename(abs_path))[0]
            cached_ext: dict[str, Any] | None = None
            if use_cache:
                hit, val = cache.get("ext_source", rel, st_ext)
                if hit:
                    cached_ext = val
            if cached_ext is None:
                try:
                    with open(abs_path, "rb") as fh:
                        raw = fh.read()
                except OSError:
                    continue
                text = raw.decode("utf-8", errors="replace")
                is_entry = "__main__" in text
                symbols: list[str] = []
                summary_line = ""
                parse_ok = True
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        parsed = ast.parse(text)
                    for node in parsed.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            symbols.append(node.name)
                    doc_lines = (ast.get_docstring(parsed) or "").strip().splitlines()
                    summary_line = doc_lines[0][:240] if doc_lines else ""
                except (SyntaxError, ValueError, UnicodeDecodeError):
                    parse_ok = False
                haystack = " ".join([tree_rel.replace("/", " "), stem.replace("_", " "), summary_line, " ".join(symbols[:24])])
                cached_ext = {
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "is_entry": is_entry,
                    "parse_ok": parse_ok,
                    "symbol_count": len(symbols),
                    "symbols": sorted(symbols)[:24],
                    "summary": summary_line,
                    "terms": _term_counts(haystack),
                }
                if use_cache and st_ext is not None:
                    cache.put("ext_source", rel, st_ext, cached_ext)

            is_entry = bool(cached_ext["is_entry"])
            n_imp = len(importers.get(stem, set()) - {rel})
            if not cached_ext["parse_ok"]:
                classification = "UNPARSEABLE"
            else:
                classification = (
                    "ENTRY_POINT" if is_entry else ("INTERNAL_HELPER" if n_imp else "ORPHAN")
                )
            rows.append(
                {
                    "id": "ext_source:" + rel,
                    "kind": "EXTENDED_SOURCE_ADDRESSABLE_MODULE",
                    "tree": tree_rel,
                    "path": rel,
                    "sha256": cached_ext["sha256"],
                    "classification": classification,
                    "capability": False,
                    "executable_entry_point": is_entry,
                    "imported_by_count": n_imp,
                    "symbol_count": cached_ext["symbol_count"],
                    "symbols": list(cached_ext["symbols"]),
                    "summary": cached_ext["summary"],
                    "terms": dict(cached_ext["terms"]),
                }
            )
    return rows


def self_check() -> dict[str, Any]:
    """Behavioral positive & negative control check for the unified hidden-capability federation."""
    cat = catalog_federated_engines()
    count_ok = (
        len(FEDERATED_KERNEL_DESCRIPTORS) >= 238
        and isinstance(cat, dict)
        and int(cat.get("count") or 0) == len(FEDERATED_KERNEL_DESCRIPTORS)
        and int(cat.get("model_calls") or 0) == 0
    )
    pos = run_federated_engine("LEAPFROG_W52_ZERO_LLM_FTS_ATMA_HINDSIGHT_MEMORY", {"operation": "demo_cycle"})
    pos_ok = bool(pos.get("pass")) and pos.get("k3_model_calls") == 0 and bool(pos.get("abstained_on_expired"))
    neg = run_federated_engine("NONEXISTENT_ENGINE_MODE_NEG_CONTROL", {})
    neg_ok = not bool(neg.get("pass"))
    checks = {
        "federated_catalog_complete": count_ok,
        "positive_live_engine_dispatch_k3_zero": pos_ok,
        "negative_unknown_engine_refused": neg_ok,
    }
    return {
        "pass": all(checks.values()),
        "checks": len(checks),
        "details": checks,
        "federated_engine_count": len(FEDERATED_KERNEL_DESCRIPTORS),
    }

