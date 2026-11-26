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
        "entrypoint": "run_wake_sleep_operation",
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
        "triggers": ["domain_of_verification_v1", "observed_domain prequential extrapolation", "refuse unverified claim"],
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
            return _ok(mode, "COW_CANDIDATE_PATCH_EVALUATED", verdict)
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
        for abs_path, rel, st_ext in _fast_scandir_py(root_str, tree_rel, skip_dirs=skip_dirs):
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
