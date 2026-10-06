"""Fail-closed adapter for the public OpenAI math frontier corpus.

The public corpus is useful as an evaluator/verifier seed, not as a matched target
distribution. Public solutions and reasoning traces are exposed and therefore cannot
be laundered into hidden matched capability evidence.

This module grants zero terminal, acceptance, family, capability, or ownership credit.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OPENAI_MATH_FRONTIER_CORPUS_ADAPTER_V1"
SOURCE_SNAPSHOT_SCHEMA = "PROJECT_BRAIN_OPENAI_MATH_FRONTIER_CORPUS_SNAPSHOT_V1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_SOURCE_PATHS = {
    "README.md",
    "CONTENTS.md",
    "lean/formalization.yaml",
    "lean/ComparatorChallenges/README.md",
}

EVALUATION_LANES = (
    {
        "id": "PUBLIC_FORMAL_REPLAY",
        "use": "REPRODUCIBILITY_AND_VERIFIER_TOOLCHAIN_CHECK_ONLY",
        "public_exposure": True,
        "capability_credit_eligible": False,
    },
    {
        "id": "PUBLIC_COMPARATOR_CHALLENGE",
        "use": "EXTRACT_MACHINE_CHECKABLE_CONTRACT_AND_VERIFIER_SHAPES",
        "public_exposure": True,
        "capability_credit_eligible": False,
    },
    {
        "id": "PUBLIC_REASONING_TRACE_ANALYSIS",
        "use": "MECHANISM_HYPOTHESIS_SOURCE_ONLY",
        "public_exposure": True,
        "capability_credit_eligible": False,
    },
    {
        "id": "HIDDEN_DERIVATIVE_FORMAL_CHALLENGE",
        "use": "PRECOMMITTED_UNEXPOSED_NEARBY_FORMAL_TASKS_WITH_INDEPENDENT_VERIFIER",
        "public_exposure": False,
        "capability_credit_eligible": False,
        "credit_boundary": "REQUIRES_SEPARATE_PROOF_OF_MATCHED_TARGET_RELATION",
    },
    {
        "id": "FALSE_CONJECTURE_NEGATIVE_CANARY",
        "use": "PRECOMMITTED_FALSE_PLAUSIBLE_CLAIMS_TO_TEST_REFUSAL_AND_COUNTEREXAMPLE_SEARCH",
        "public_exposure": False,
        "capability_credit_eligible": False,
        "credit_boundary": "REQUIRES_SEPARATE_PROOF_OF_MATCHED_TARGET_RELATION",
    },
    {
        "id": "PROOF_REPAIR_ABLATION",
        "use": "REMOVE_OR_CORRUPT_LOAD_BEARING_LEMMAS_AND_TEST_CAUSAL_REPAIR",
        "public_exposure": False,
        "capability_credit_eligible": False,
        "credit_boundary": "REQUIRES_SEPARATE_PROOF_OF_MATCHED_TARGET_RELATION",
    },
)


class CorpusAdapterError(ValueError):
    pass


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise CorpusAdapterError(f"{label}_MUST_BE_SHA40")
    return value


def _nat(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CorpusAdapterError(f"{label}_MUST_BE_NONNEGATIVE_INTEGER")
    return value


def _binding(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise CorpusAdapterError(f"{label}_BINDING_MISSING")
    path = value.get("path")
    sha = value.get("git_blob_sha")
    if not isinstance(path, str) or not path.strip():
        raise CorpusAdapterError(f"{label}_PATH_INVALID")
    _sha(sha, f"{label}_GIT_BLOB_SHA")
    return {"path": path, "git_blob_sha": sha}


def compile_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        return _fail(["SNAPSHOT_NOT_OBJECT"])

    errors: list[str] = []
    try:
        if snapshot.get("schema") != SOURCE_SNAPSHOT_SCHEMA:
            raise CorpusAdapterError("SNAPSHOT_SCHEMA_MISMATCH")
        if snapshot.get("source_repository") != "openai/math":
            raise CorpusAdapterError("SOURCE_REPOSITORY_NOT_OPENAI_MATH")
        source_commit = _sha(snapshot.get("source_commit_sha"), "SOURCE_COMMIT_SHA")

        facts = snapshot.get("reported_facts")
        if not isinstance(facts, Mapping):
            raise CorpusAdapterError("REPORTED_FACTS_MISSING")
        if facts.get("model_identity_disclosed") is not False:
            raise CorpusAdapterError("MODEL_IDENTITY_MUST_REMAIN_UNDISCLOSED")
        manuscripts = _nat(facts.get("manuscripts"), "MANUSCRIPTS")
        families = _nat(facts.get("families"), "FAMILIES")
        approx_problems = _nat(facts.get("approx_problems"), "APPROX_PROBLEMS")
        avg_hours = facts.get("average_pro_thinking_hours_per_result")
        if isinstance(avg_hours, bool) or not isinstance(avg_hours, (int, float)) or avg_hours <= 0:
            raise CorpusAdapterError("AVERAGE_PRO_THINKING_HOURS_INVALID")

        census = snapshot.get("artifact_census")
        if not isinstance(census, Mapping):
            raise CorpusAdapterError("ARTIFACT_CENSUS_MISSING")
        comparator_pairs = _nat(census.get("comparator_challenge_pairs"), "COMPARATOR_CHALLENGE_PAIRS")
        reasoning_pdfs = _nat(census.get("reasoning_summary_pdfs"), "REASONING_SUMMARY_PDFS")
        formalization_sources = _nat(census.get("formalization_source_entries"), "FORMALIZATION_SOURCE_ENTRIES")
        if comparator_pairs <= 0 or reasoning_pdfs <= 0 or formalization_sources <= 0:
            raise CorpusAdapterError("ARTIFACT_CENSUS_EMPTY")

        raw_bindings = snapshot.get("source_artifact_bindings")
        if not isinstance(raw_bindings, list) or not raw_bindings:
            raise CorpusAdapterError("SOURCE_ARTIFACT_BINDINGS_MISSING")
        bindings = [_binding(x, f"SOURCE_ARTIFACT_{i}") for i, x in enumerate(raw_bindings)]
        paths = {x["path"] for x in bindings}
        missing = sorted(REQUIRED_SOURCE_PATHS - paths)
        if missing:
            raise CorpusAdapterError("MISSING_REQUIRED_SOURCE_BINDINGS:" + ",".join(missing))
        if len(paths) != len(bindings):
            raise CorpusAdapterError("DUPLICATE_SOURCE_BINDING_PATH")

        if snapshot.get("public_solution_exposure") is not True:
            raise CorpusAdapterError("PUBLIC_SOLUTION_EXPOSURE_MUST_BE_TRUE")
        if snapshot.get("direct_target_identity_relation") is not False:
            raise CorpusAdapterError("DIRECT_TARGET_IDENTITY_RELATION_MUST_BE_FALSE")

    except CorpusAdapterError as exc:
        errors.append(str(exc))
        return _fail(errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_PUBLIC_CORPUS_COMPILED_TO_ZERO_CREDIT_EVALUATOR_FACTORY",
        "source": {
            "repository": "openai/math",
            "commit_sha": source_commit,
            "source_artifact_bindings": bindings,
        },
        "reported_facts": {
            "manuscripts": manuscripts,
            "families": families,
            "approx_problems": approx_problems,
            "average_pro_thinking_hours_per_result": float(avg_hours),
            "model_identity_disclosed": False,
        },
        "artifact_census": {
            "comparator_challenge_pairs": comparator_pairs,
            "reasoning_summary_pdfs": reasoning_pdfs,
            "formalization_source_entries": formalization_sources,
        },
        "evaluation_lanes": list(EVALUATION_LANES),
        "terminal_relation": {
            "direct_target_identity_proved": False,
            "complete_target_capability_distribution_proved": False,
            "matched_brain_vs_target_distribution_proved": False,
            "target_complete_evaluator_relation_proved": False,
        },
        "contamination_boundary": {
            "public_openai_outputs_may_seed_verifiers_or_mutations": True,
            "public_openai_solutions_may_be_used_as_hidden_matched_cases": False,
            "public_reasoning_traces_may_be_used_as_hidden_matched_cases": False,
            "derived_hidden_cases_require_precommit_before_brain_execution": True,
            "derived_hidden_cases_require_independent_verification": True,
            "derived_hidden_cases_require_separate_target_relation_for_credit": True,
        },
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": [],
    }


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": errors,
    }
