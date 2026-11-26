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


def compile_extended_source_index_rows(root: Path, covered: set[str]) -> list[dict[str, Any]]:
    """Deterministically index non-`canonical/runtime` Python modules across the repo.

    Preserves `source_index` as the exact partition of `canonical/runtime/` while
    exposing `canonical/swe_kernel/`, `canonical/tools/`, `canonical/capabilities/`,
    `canonical/research/`, and `canonical/integrations/` to cross-repository discovery.
    """
    astra_tmp = root / "canonical" / "astra_runtime" / "tmp"
    importers: dict[str, set[str]] = {}
    all_py: list[Path] = []
    for sub in ("canonical", "tests"):
        base = root / sub
        if base.is_dir():
            for p in sorted(base.rglob("*.py")):
                if any(part in _NON_SOURCE_DIRS for part in p.parts) or p.is_relative_to(astra_tmp):
                    continue
                all_py.append(p)
    for p in all_py:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for mod in _IMPORT_RE.findall(txt):
            importers.setdefault(mod.split(".")[-1], set()).add(p.relative_to(root).as_posix())

    rows: list[dict[str, Any]] = []
    for tree_rel in _EXTENDED_SOURCE_TREES:
        tree_dir = root / tree_rel
        if not tree_dir.is_dir():
            continue
        for path in sorted(tree_dir.rglob("*.py")):
            if any(part in _NON_SOURCE_DIRS for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if rel in covered:
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            text = raw.decode("utf-8", errors="replace")
            stem = path.stem
            is_entry = "__main__" in text
            n_imp = len(importers.get(stem, set()) - {rel})
            classification = (
                "ENTRY_POINT" if is_entry else ("INTERNAL_HELPER" if n_imp else "ORPHAN")
            )
            symbols: list[str] = []
            summary_line = ""
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
                classification = "UNPARSEABLE"

            haystack = " ".join([tree_rel.replace("/", " "), stem.replace("_", " "), summary_line, " ".join(symbols[:24])])
            rows.append(
                {
                    "id": "ext_source:" + rel,
                    "kind": "EXTENDED_SOURCE_ADDRESSABLE_MODULE",
                    "tree": tree_rel,
                    "path": rel,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "classification": classification,
                    "capability": False,
                    "executable_entry_point": is_entry,
                    "imported_by_count": n_imp,
                    "symbol_count": len(symbols),
                    "symbols": sorted(symbols)[:24],
                    "summary": summary_line,
                    "terms": _term_counts(haystack),
                }
            )
    return rows
