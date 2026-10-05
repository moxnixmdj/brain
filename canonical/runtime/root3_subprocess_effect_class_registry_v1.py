"""Compile the exact 18-site subprocess universe into seven semantic effect classes.

This is a classification/compression layer only. It does NOT infer that a child
program is free of hidden effects from its declared class. The purpose is to
replace 18 remaining policy-verifier obligations with seven class-specific
semantic proof obligations, while retaining exact per-call-site identity.

Any call-site drift, new process API, missing mapping, duplicate mapping, or
unexpected class fails closed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime.root3_child_process_channel_registry_v1 import (
    compile_registry as compile_child_registry,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_EFFECT_CLASS_REGISTRY_V1"

CLASSES = {
    "READ_ONLY_DECLARED_QUERY",
    "TEMPORARY_FILESYSTEM_TRANSFORM",
    "PACKAGE_ENV_MUTATION",
    "LOCAL_LOOPBACK_SERVICE",
    "DECLARED_ARTIFACT_PRODUCTION",
    "BOUND_CHILD_CODE_EXECUTION",
    "ARBITRARY_COMMAND_EXECUTION",
}

# Exact mapping over the already content-addressed 18-site current universe.
# Keys are (module_path, lineno, process_api).
EXPECTED: dict[tuple[str, int, str], str] = {
    ("canonical/runtime/astra_runtime.py", 325, "subprocess.run"): "ARBITRARY_COMMAND_EXECUTION",
    ("canonical/runtime/astra_runtime.py", 595, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 673, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 939, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 1215, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
    ("canonical/runtime/astra_runtime.py", 5777, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",


    ("canonical/runtime/auto_python_source_codec_acquisition.py", 217, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
    ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py", 32, "subprocess.run"): "READ_ONLY_DECLARED_QUERY",
    ("canonical/runtime/bound_capabilities/browser_chromedriver.py", 50, "subprocess.Popen"): "LOCAL_LOOPBACK_SERVICE",
    ("canonical/runtime/bound_capabilities/cli_command.py", 27, "subprocess.run"): "ARBITRARY_COMMAND_EXECUTION",
    ("canonical/runtime/bound_capabilities/jq_query.py", 41, "subprocess.run"): "READ_ONLY_DECLARED_QUERY",
    ("canonical/runtime/bound_capabilities/node_library_codec.py", 16, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
    ("canonical/runtime/bound_capabilities/pandoc_weasyprint.py", 24, "subprocess.run"): "DECLARED_ARTIFACT_PRODUCTION",
    ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 29, "subprocess.run"): "TEMPORARY_FILESYSTEM_TRANSFORM",
    ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 44, "subprocess.run"): "READ_ONLY_DECLARED_QUERY",
    ("canonical/runtime/bound_capabilities/python_test_audit.py", 50, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
    ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py", 66, "subprocess.run"): "READ_ONLY_DECLARED_QUERY",
    ("canonical/runtime/bound_capabilities/yq_yaml_json.py", 21, "subprocess.run"): "READ_ONLY_DECLARED_QUERY",
}

CLASS_PROOF_RESIDUALS = {
    "READ_ONLY_DECLARED_QUERY": [
        "PROVE_BOUND_COMMAND_AND_ARGUMENT_SHAPE_IS_READ_ONLY_FOR_DECLARED_RESOURCE",
        "PROVE_OR_SANDBOX_CHILD_INTERNAL_NATIVE_EFFECTS",
    ],
    "TEMPORARY_FILESYSTEM_TRANSFORM": [
        "PROVE_WRITES_ARE_CONFINED_TO_CONTENT_BOUND_EPHEMERAL_WORKSPACE",
        "PROVE_NO_EXTERNAL_OR_DURABLE_EFFECT_ESCAPES_THE_WORKSPACE",
    ],
    "PACKAGE_ENV_MUTATION": [
        "REQUIRE_EXACT_PACKAGE_VERSION_HASH_AND_ENVIRONMENT_TARGET_BINDING",
        "REQUIRE_EXPLICIT_PACKAGE_ENV_MUTATION_AUTHORITY",
        "VERIFY_POSTCONDITION_OR_MARK_COMPLETION_UNKNOWN",
    ],
    "LOCAL_LOOPBACK_SERVICE": [
        "BIND_EXECUTABLE_AND_ARGUMENTS",
        "PROVE_LISTENER_IS_LOOPBACK_ONLY",
        "BIND_SERVICE_LIFECYCLE_AND_POSTCONDITION_RECONCILIATION",
    ],
    "DECLARED_ARTIFACT_PRODUCTION": [
        "BIND_INPUTS_OUTPUT_PATH_AND_TOOLCHAIN",
        "PROVE_DURABLE_WRITES_ARE_LIMITED_TO_DECLARED_ARTIFACT_OUTPUTS",
        "VERIFY_OUTPUT_POSTCONDITION",
    ],
    "BOUND_CHILD_CODE_EXECUTION": [
        "BIND_EXACT_CHILD_PROGRAM_BYTES_AND_INPUTS",
        "INHERIT_OR_SANDBOX_THE_SAME_MATERIAL_EFFECT_BOUNDARY_INSIDE_CHILD",
        "PROVE_CHILD_CANNOT_ESCAPE_EFFECT_MEDIATION",
    ],
    "ARBITRARY_COMMAND_EXECUTION": [
        "FORBID_FROM_CREDITED_RUNTIME_UNLESS_COMMAND_SEMANTICS_ARE_SEPARATELY_BOUND",
        "IF_ALLOWED_REQUIRE_EXACT_COMMAND_PAYLOAD_AND_COMPLETE_EFFECT_AUTHORITY",
    ],
}


class EffectClassRegistryError(RuntimeError):
    pass


def classify_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observed: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row["module_path"]),
            int(row["lineno"]),
            str(row["process_api"]),
        )
        if key in observed:
            raise EffectClassRegistryError("DUPLICATE_PROCESS_SITE:" + repr(key))
        observed[key] = dict(row)

    expected_keys = set(EXPECTED)
    observed_keys = set(observed)
    if observed_keys != expected_keys:
        missing = sorted(expected_keys - observed_keys)
        new = sorted(observed_keys - expected_keys)
        raise EffectClassRegistryError(
            "PROCESS_SITE_UNIVERSE_DRIFT:"
            + json.dumps({"missing": missing, "new": new}, sort_keys=True)
        )

    unknown_classes = set(EXPECTED.values()) - CLASSES
    if unknown_classes:
        raise EffectClassRegistryError(
            "UNKNOWN_EFFECT_CLASSES:" + ",".join(sorted(unknown_classes))
        )

    classified = []
    counts = {name: 0 for name in sorted(CLASSES)}
    for key in sorted(EXPECTED):
        effect_class = EXPECTED[key]
        counts[effect_class] += 1
        row = observed[key]
        classified.append(
            {
                "module_path": key[0],
                "lineno": key[1],
                "process_api": key[2],
                "function": row.get("function"),
                "command_literals": row.get("command_literals", []),
                "effect_class": effect_class,
            }
        )

    if len(classified) != 18 or sum(counts.values()) != 18:
        raise EffectClassRegistryError("CLASSIFICATION_COUNT_NOT_18")
    if any(v == 0 for v in counts.values()):
        raise EffectClassRegistryError("EMPTY_DECLARED_EFFECT_CLASS")

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_18_PROCESS_SITES_PARTITIONED_INTO_7_DECLARED_EFFECT_CLASSES",
        "site_count": 18,
        "class_count": len(CLASSES),
        "class_counts": counts,
        "classified_sites": classified,
        "semantic_verifier_obligations_before": 18,
        "semantic_verifier_classes_after": len(CLASSES),
        "duplicate_policy_obligations_deleted": 18 - len(CLASSES),
        "compression_percent": (18 - len(CLASSES)) / 18 * 100.0,
        "class_proof_residuals": CLASS_PROOF_RESIDUALS,
        "truth_boundary": {
            "classification_is_scope_complete_for_current_direct_python_process_sites": True,
            "classification_proves_child_internal_effect_safety": False,
            "classification_proves_semantic_authorization": False,
            "classification_proves_c1_or_c2_complete": False,
        },
        "hard_nonclaims": [
            "A_READ_ONLY_DECLARED_QUERY_LABEL_DOES_NOT_PROVE_THE_CHILD_BINARY_HAS_NO_HIDDEN_EFFECTS",
            "A_TEMPORARY_FILESYSTEM_TRANSFORM_LABEL_DOES_NOT_PROVE_OS_LEVEL_CONFINEMENT",
            "BOUND_CHILD_CODE_EXECUTION_REMAINS_EFFECTFUL_UNTIL_INHERITED_OR_SANDBOXED_MEDIATION_IS_PROVED",
            "ARBITRARY_COMMAND_EXECUTION_REMAINS_FAIL_CLOSED_FOR_CREDITED_RUNTIME_UNTIL_SEPARATELY_BOUND",
            "NO_ROOT3_OR_ACCEPTANCE_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def compile_effect_classes(root: Path = ROOT) -> dict[str, Any]:
    child = compile_child_registry(root)
    rows = child["whole_runtime"]["call_sites"]
    return classify_rows(rows)


if __name__ == "__main__":
    print(json.dumps(compile_effect_classes(), indent=2, sort_keys=True))
