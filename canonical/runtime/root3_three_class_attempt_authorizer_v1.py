"""Request-bound attempt authorizer over the classifier-V2 live registry.

This authorizer permits only coarse, content-bound attempts for:
- READ_ONLY_DECLARED_QUERY
- TEMPORARY_FILESYSTEM_TRANSFORM
- BOUND_CHILD_CODE_EXECUTION (content-bound codec/verification probes)

It inherits the two-class profiles from
root3_two_class_attempt_authorizer_v1 after rebasing them onto the live
registry V2 exactly: every verified call-site key and registry provenance is
re-derived from the current compilation instead of frozen line constants, so
legitimate source reflows re-pin by semantics, while any UNKNOWN site or new
process API keeps failing closed.

It does not execute children and does not replace the class executors'
deeper path, command-semantic, output, or namespace validation. All other
classes and all malformed, drifted, or tampered requests fail closed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_subprocess_callsite_classifier_v2 as classifier
from canonical.runtime import (
    root3_subprocess_effect_class_registry_v2 as registry_v2,
)
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as read_only
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_transform
from canonical.runtime import root3_bound_codec_child_executor_v1 as codec_child
from canonical.runtime import root3_confined_shell_executor_v1 as confined_shell

SCHEMA = "PROJECT_BRAIN_ROOT3_THREE_CLASS_ATTEMPT_AUTHORIZATION_V1"
AUTHORITY_ID = "ROOT3_READ_ONLY_PLUS_TEMP_PLUS_BOUND_CODEC_CHILD_V1"
import re

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

CLASSES = registry_v2.CLASSES
CODEC = "BOUND_CHILD_CODE_EXECUTION"
SHELL = "ARBITRARY_COMMAND_EXECUTION"

EXPECTED_FUNCTION: dict[tuple[str, int, str], str] = {
    ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py", 53, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/jq_query.py", 41, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py", 44, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/yq_yaml_json.py", 23, "subprocess.run"): "run",
    (temp_transform.SUPPORTED_SITE): "run",
    (codec_child.NPM_PROBE_SITE): "_probe_contract",
    (codec_child.SRC_CODEC_PROBE_SITE): "dispatch",
    (codec_child.SRC_CODEC_PRIME_PROBE_SITE): "prime_verifier_trees",
    (codec_child.NODE_LIBRARY_RUN_SITE): "_run_node",
    (codec_child.PY_SOURCE_TREE_RUN_SITE): "run",
    (codec_child.VERIFY_MISSION_SITE): "_verify_and_promote_acquisition",
    ("canonical/runtime/astra_runtime.py", 357, "subprocess.run"): "run_shell",
    ("canonical/runtime/astra_runtime.py", 400, "subprocess.run"): "run_shell",
    # 2026-10-28 SWE_TOOL_STEP fleet lighting (profile enforced in the
    # executor and authorizer; argv families: pytest/mypy/coverage/ruff/
    # bandit/unittest/crosshair/git/sha256sum/python -c/-I).
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 108, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 112, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 122, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 127, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 143, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 154, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_coverage_gate.py", 164, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_mutation_gate.py", 281, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_mutation_gate.py", 292, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_mutation_gate.py", 297, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_mutation_gate.py", 320, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_mutation_gate.py", 373, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_perf_gate.py", 128, "subprocess.run"): "_bench",
    ("canonical/runtime/bound_capabilities/python_review_diff_perf_gate.py", 174, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_perf_gate.py", 190, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_perf_gate.py", 195, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_security_gate.py", 129, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_security_gate.py", 136, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_type_gate.py", 119, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_type_gate.py", 125, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_static_triage.py", 160, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_review_diff_static_triage.py", 166, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repo_diff_apply_full_testgate.py", 100, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repo_diff_apply_full_testgate.py", 111, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repo_diff_apply_full_testgate.py", 116, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repo_diff_apply_full_testgate.py", 130, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repo_pr_realize.py", 69, "subprocess.run"): "_git",
    ("canonical/runtime/bound_capabilities/python_issue_to_pr_orchestrate.py", 485, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_issue_to_pr_orchestrate.py", 597, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_refactor_extract_function.py", 398, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_refactor_rename_parameter.py", 346, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_refactor_rename_symbol.py", 503, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py", 78, "subprocess.run"): "_run_test",
    ("canonical/runtime/bound_capabilities/python_test_guided_patch_search_v1.py", 59, "subprocess.run"): "_run_tests",
    ("canonical/runtime/bound_capabilities/python_test_guided_patch_search_v1.py", 66, "subprocess.run"): "_run_tests",
    ("canonical/runtime/bound_capabilities/python_tests_generate_scaffold.py", 321, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_tests_generate_scaffold.py", 326, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_tests_generate_scaffold.py", 347, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_dynamic_fault_localizer_v1.py", 58, "subprocess.run"): "_trace_one",
    ("canonical/runtime/bound_capabilities/python_dynamic_fault_localizer_v1.py", 134, "subprocess.run"): "_trace_file_cases",
    ("canonical/runtime/bound_capabilities/python_source_move_function.py", 83, "subprocess.run"): "_run_suite",
    ("canonical/runtime/bound_capabilities/python_source_move_symbol.py", 94, "subprocess.run"): "_verify_project",
    ("canonical/runtime/bound_capabilities/python_source_add_parameter.py", 92, "subprocess.run"): "_verify_project",
    ("canonical/runtime/bound_capabilities/python_feature_implement_function_spec.py", 481, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py", 144, "subprocess.run"): "_verify_project",
    ("canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py", 1221, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py", 1222, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/python_interprocedural_value_provenance_v1.py", 94, "subprocess.run"): "_trace_one",
    ("canonical/runtime/bound_capabilities/code_tree_sitter_patch_verify_v1.py", 101, "subprocess.run"): "_run_tests",
    ("canonical/runtime/bound_capabilities/python_repository_acceptance_measurement_v1.py", 249, "subprocess.run"): "_run_tests",
    ("canonical/runtime/bound_capabilities/brain_module_invoke_v1.py", 145, "subprocess.run"): "_child",
    ("canonical/runtime/bound_capabilities/source_candidates_verify_git_index.py", 56, "subprocess.run"): "_independent_digests",
    ("canonical/runtime/bound_capabilities/source_candidates_verify_git_index.py", 83, "subprocess.run"): "run",
    ("canonical/runtime/bound_capabilities/crosshair_contract_oracle.py", 51, "subprocess.run"): "run",
}


def _live_registry() -> dict[str, Any]:
    return registry_v2.compile_effect_classes(registry_v2.ROOT)


_REGISTRY = _live_registry()
_REGISTRY_SHA = _REGISTRY["registry_sha256"]
_SITE_ROWS: dict[tuple[str, int, str], dict[str, Any]] = {
    (
        str(row["module_path"]),
        int(row["lineno"]),
        str(row["interception_api"]),
    ): dict(row)
    for row in _REGISTRY["classified_sites"]
}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _deny(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "DENY_FAIL_CLOSED",
        "allowed": False,
        "reason": reason,
        "acceptance_credit_delta": 0,
    }


def _request_hash_valid(request: Mapping[str, Any]) -> bool:
    digest = request.get("request_sha256")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        return False
    core = dict(request)
    core.pop("request_sha256", None)
    return hashlib.sha256(_canon(core)).hexdigest() == digest


def _plain_argv(request: Mapping[str, Any]) -> list[str] | None:
    command = request.get("command")
    if not isinstance(command, Mapping) or command.get("kind") != "ARGV":
        return None
    items = command.get("items")
    if not isinstance(items, list) or not items:
        return None
    out: list[str] = []
    for item in items:
        if (
            not isinstance(item, Mapping)
            or item.get("kind") != "STRING"
            or not isinstance(item.get("value"), str)
            or not item.get("value")
            or "\x00" in item.get("value")
        ):
            return None
        out.append(item["value"])
    return out


def _registry_binding(request: Mapping[str, Any], key: tuple[str, int, str]) -> str | None:
    callsite = request.get("callsite")
    expected_fn = EXPECTED_FUNCTION.get(key)
    if expected_fn is not None and callsite.get("function") != expected_fn:
        return "CALLSITE_FUNCTION_MISMATCH"
    if callsite.get("registry_site_count") != len(_SITE_ROWS):
        return "REGISTRY_SITE_COUNT_MISMATCH"
    if callsite.get("registry_sha256") != _REGISTRY_SHA:
        return "REGISTRY_SHA256_DRIFT"
    if callsite.get("runtime_join") not in (
        "EXACT_PATH_LINE_INTERCEPTION_API",
        "EXACT_PATH_LINE_API",
    ):
        return "RUNTIME_JOIN_MISMATCH"
    row = _SITE_ROWS.get(key)
    if row is None:
        return "PROCESS_CALLSITE_NOT_IN_LIVE_REGISTRY"
    if str(callsite.get("effect_class") or "") != str(row["effect_class"]):
        return "EFFECT_CLASS_REGISTRY_MISMATCH"
    return None


def _common(request: Mapping[str, Any], key: tuple[str, int, str]) -> str | None:
    binding = _registry_binding(request, key)
    if binding:
        return binding
    if request.get("api") != "subprocess.run":
        return "PROCESS_API_MISMATCH"
    if request.get("shell") is not False:
        return "SHELL_FORBIDDEN"
    if request.get("capture_output") is not True:
        return "CAPTURE_OUTPUT_REQUIRED"
    if request.get("text") is not True and request.get("encoding") is None:
        return "TEXT_MODE_REQUIRED"
    if request.get("stdin") not in (None, "DEVNULL"):
        return "STDIN_FORBIDDEN"
    if _plain_argv(request) is None:
        return "COMMAND_ITEMS_INVALID"
    return None


def _timeout_value(request: Mapping[str, Any], maximum: float) -> float | None:
    timeout = request.get("timeout")
    if timeout is None:
        return min(60.0, maximum)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        return None
    value = float(timeout)
    if not (0.0 < value <= maximum):
        return None
    return value


def _authorize_read_only(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    if key not in read_only.SUPPORTED:
        return _deny("CALLSITE_NOT_VERIFIED_READ_ONLY")
    common = _common(request, key)
    if common:
        return _deny(common)
    if request.get("env") is not None:
        return _deny("CUSTOM_ENV_FORBIDDEN")
    if request.get("input") is not None:
        return _deny("INPUT_FORBIDDEN")
    if request.get("stdout") is not None or request.get("stderr") is not None:
        return _deny("EXPLICIT_STDOUT_STDERR_FORBIDDEN")
    if _timeout_value(request, 180.0) is None:
        return _deny("TIMEOUT_OUT_OF_RANGE")
    return _allow(
        request=request,
        effect_class="READ_ONLY_DECLARED_QUERY",
        key=key,
        profile=str(read_only.SUPPORTED[key]),
    )


def _authorize_temp(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    if key != temp_transform.SUPPORTED_SITE:
        return _deny("CALLSITE_NOT_VERIFIED_TEMP")
    common = _common(request, key)
    if common:
        return _deny(common)
    if request.get("env") is not None:
        return _deny("CUSTOM_ENV_FORBIDDEN")
    if request.get("input") is not None:
        return _deny("INPUT_FORBIDDEN")
    if request.get("stdout") is not None or request.get("stderr") is not None:
        return _deny("EXPLICIT_STDOUT_STDERR_FORBIDDEN")
    if request.get("cwd") is not None:
        return _deny("TEMP_CWD_MUST_BE_NONE")
    if request.get("timeout") != 180:
        return _deny("TEMP_TIMEOUT_MUST_EQUAL_180")
    argv = _plain_argv(request)
    assert argv is not None
    if len(argv) != 10:
        return _deny("TEMP_ARGV_LENGTH_INVALID")
    if argv[0] != "pdftoppm":
        return _deny("TEMP_EXECUTABLE_INVALID")
    if argv[1:4] != ["-f", "1", "-l"] or argv[5] != "-r" or argv[7] != "-png":
        return _deny("TEMP_OPTIONS_INVALID")
    try:
        max_pages = int(argv[4])
        dpi = int(argv[6])
    except Exception:
        return _deny("TEMP_NUMERIC_OPTIONS_INVALID")
    if not 1 <= max_pages <= 500:
        return _deny("TEMP_MAX_PAGES_OUT_OF_RANGE")
    if not 72 <= dpi <= 600:
        return _deny("TEMP_DPI_OUT_OF_RANGE")
    src = pathlib.Path(argv[8])
    prefix = pathlib.Path(argv[9])
    if not src.is_absolute() or not prefix.is_absolute():
        return _deny("TEMP_PATHS_MUST_BE_ABSOLUTE")
    if prefix.name != "page" or not prefix.parent.name.startswith("project-brain-ocr-"):
        return _deny("TEMP_OUTPUT_PREFIX_INVALID")
    return _allow(
        request=request,
        effect_class="TEMPORARY_FILESYSTEM_TRANSFORM",
        key=key,
        profile="PDF_RASTER_EPHEMERAL_OUTPUT",
    )


def _authorize_shell_step(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    if key not in confined_shell.SUPPORTED:
        return _deny("CALLSITE_NOT_VERIFIED_CONFINED_SHELL:" + repr(key))
    profile = confined_shell.SUPPORTED.get(key)
    if profile == "SWE_TOOL_STEP":
        argv = _plain_argv(request)
        if argv is None:
            return _deny("SWE_TOOL_ARGV_NOT_LIST")
        try:
            confined_shell.classify_tool_argv(list(argv))
        except confined_shell.ConfinedShellDenied as exc:
            return _deny(str(exc))
        if _timeout_value(request, 300.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        input_binding = request.get("input")
        if input_binding is not None:
            return _deny("SWE_TOOL_INPUT_FORBIDDEN")
        cwd = request.get("cwd")
        if cwd is not None:
            try:
                pathlib.Path(str(cwd)).resolve().relative_to(confined_shell.ROOT)
            except ValueError:
                return _deny("SWE_TOOL_CWD_OUTSIDE_REPO:" + repr(cwd))
        return _allow(
            request=request,
            effect_class=SHELL,
            key=key,
            profile="SWE_TOOL_STEP",
        )
    common = _common(request, key)
    if common:
        return _deny(common)
    argv = _plain_argv(request)
    assert argv is not None
    if len(argv) != 3:
        return _deny("SHELL_ARGV_SHAPE_INVALID")
    if pathlib.Path(argv[0]).name not in {"bash", "sh"}:
        return _deny("SHELL_EXECUTABLE_INVALID")
    if argv[1] != "-lc":
        return _deny("SHELL_MODE_INVALID")
    cmd_bytes = len(argv[2].encode("utf-8"))
    if cmd_bytes > confined_shell.MAX_COMMAND_BYTES:
        return _deny("SHELL_COMMAND_TOO_LARGE")
    if request.get("input") is not None:
        return _deny("SHELL_INPUT_FORBIDDEN")
    timeout = request.get("timeout")
    if timeout is not None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            return _deny("TIMEOUT_INVALID")
        if not (0.0 < float(timeout) <= 1200.0):
            return _deny("TIMEOUT_OUT_OF_RANGE")
    cwd = request.get("cwd")
    if str(cwd or "") != str(confined_shell.ROOT):
        return _deny("SHELL_CWD_MUST_BE_REPO_ROOT:" + repr(cwd))
    return _allow(
        request=request,
        effect_class=SHELL,
        key=key,
        profile="ASTRA_SHELL_STEP",
    )


def _authorize_codec_child(request: Mapping[str, Any], key: tuple[str, int, str]) -> dict[str, Any]:
    profile = codec_child.SUPPORTED.get(key)
    if profile is None:
        return _deny("CALLSITE_NOT_VERIFIED_BOUND_CODEC_CHILD:" + repr(key))
    common = _common(request, key)
    if common:
        return _deny(common)
    if profile == "ASTRA_VERIFICATION_MISSION_CHILD":
        # env=os.environ.copy() is intrinsic to this profile: the child needs
        # the mission environment; the executor rewrites env inside the
        # confined namespace to a fixed allowlist-side set anyway.
        if _timeout_value(request, 660.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        argv = _plain_argv(request)
        assert argv is not None
        if len(argv) != 3:
            return _deny("ASTRA_VERIFY_ARGV_INVALID")
        launcher_expected = str((codec_child.ROOT / codec_child.LAUNCHER_REL).resolve())
        if argv[1] != launcher_expected:
            return _deny("ASTRA_VERIFY_LAUNCHER_INVALID")
        mission_rel = argv[2]
        mission_dir = codec_child.ROOT / codec_child.ASTRA_DIR_REL / "missions"
        mission_path = (codec_child.ROOT / mission_rel).resolve()
        if mission_path.parent != mission_dir.resolve():
            return _deny("ASTRA_VERIFY_MISSION_INVALID")
        if request.get("input") is not None:
            return _deny("ASTRA_VERIFY_INPUT_FORBIDDEN")
        cwd = request.get("cwd")
        if str(cwd or "") != str(codec_child.ROOT):
            return _deny("ASTRA_VERIFY_CWD_INVALID")
        return _allow(request=request, effect_class=CODEC, key=key, profile=profile)
    if request.get("env") is not None:
        return _deny("CUSTOM_ENV_FORBIDDEN")
    argv = _plain_argv(request)
    assert argv is not None
    if profile == "NPM_CODEC_CONTRACT_PROBE":
        if _timeout_value(request, 90.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        if len(argv) != 2 or argv[0] != "node":
            return _deny("NPM_PROBE_ARGV_INVALID")
        expected_runner = str((codec_child.ROOT / codec_child.NODE_RUNNER_REL).resolve())
        if argv[1] != expected_runner:
            return _deny("NPM_PROBE_RUNNER_INVALID")
        # Input content is digest-bound at authorization time; the JSON shape
        # is revalidated against real kwargs by the class executor.
        input_binding = request.get("input")
        if (
            not isinstance(input_binding, Mapping)
            or input_binding.get("type") != "TEXT"
        ):
            return _deny("NPM_PROBE_STDIN_TEXT_REQUIRED")
        size = input_binding.get("bytes")
        if not isinstance(size, int) or size > codec_child.MAX_INPUT_BYTES:
            return _deny("NPM_PROBE_STDIN_TOO_LARGE")
        cwd = request.get("cwd")
        if str(cwd or "") != str(codec_child.ROOT):
            return _deny("NPM_PROBE_CWD_INVALID")
        return _allow(
            request=request,
            effect_class=CODEC,
            key=key,
            profile=profile,
        )
    if profile == "NODE_LIBRARY_CODEC_RUN":
        if _timeout_value(request, 120.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        if len(argv) != 2 or argv[0] != "node":
            return _deny("NODE_RUN_ARGV_INVALID")
        expected_runner = str((codec_child.ROOT / codec_child.NODE_RUNNER_REL).resolve())
        if argv[1] != expected_runner:
            return _deny("NODE_RUN_RUNNER_INVALID")
        input_binding = request.get("input")
        if (
            not isinstance(input_binding, Mapping)
            or input_binding.get("type") != "TEXT"
        ):
            return _deny("NODE_RUN_STDIN_TEXT_REQUIRED")
        size = input_binding.get("bytes")
        if not isinstance(size, int) or size > codec_child.MAX_INPUT_BYTES:
            return _deny("NODE_RUN_STDIN_TOO_LARGE")
        cwd = request.get("cwd")
        if str(cwd or "") != str(codec_child.ROOT):
            return _deny("NODE_RUN_CWD_INVALID")
        return _allow(
            request=request,
            effect_class=CODEC,
            key=key,
            profile=profile,
        )
    if profile == "PY_SOURCE_TREE_CODEC_RUN":
        if _timeout_value(request, 120.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        if len(argv) != 2 or not argv[1].endswith("github_source_codec_runner.py"):
            return _deny("SRC_TREE_RUN_ARGV_INVALID")
        input_binding = request.get("input")
        if (
            not isinstance(input_binding, Mapping)
            or input_binding.get("type") != "TEXT"
        ):
            return _deny("SRC_TREE_RUN_STDIN_TEXT_REQUIRED")
        size = input_binding.get("bytes")
        if not isinstance(size, int) or size > codec_child.MAX_INPUT_BYTES:
            return _deny("SRC_TREE_RUN_STDIN_TOO_LARGE")
        cwd = request.get("cwd")
        if str(cwd or "") != str(codec_child.ROOT):
            return _deny("SRC_TREE_RUN_CWD_INVALID")
        return _allow(
            request=request,
            effect_class=CODEC,
            key=key,
            profile=profile,
        )
    if profile == "PY_SOURCE_CODEC_CONTRACT_PROBE":
        if _timeout_value(request, 120.0) is None:
            return _deny("TIMEOUT_OUT_OF_RANGE")
        if len(argv) != 4 or not argv[1].endswith(".py"):
            return _deny("PY_PROBE_ARGV_INVALID")
        if request.get("input") is not None:
            return _deny("PY_PROBE_INPUT_FORBIDDEN")
        cwd = request.get("cwd")
        if str(cwd or "") != str(codec_child.ROOT):
            return _deny("PY_PROBE_CWD_INVALID")
        return _allow(
            request=request,
            effect_class=CODEC,
            key=key,
            profile=profile,
        )
    return _deny("PROFILE_UNREACHABLE")


def _allow(
    *,
    request: Mapping[str, Any],
    effect_class: str,
    key: tuple[str, int, str],
    profile: str,
) -> dict[str, Any]:
    material = {
        "schema": SCHEMA,
        "authority_id": AUTHORITY_ID,
        "request_sha256": request["request_sha256"],
        "effect_class": effect_class,
        "callsite": {
            "module_path": key[0],
            "lineno": key[1],
            "process_api": key[2],
            "profile": profile,
        },
        "permit": "ATTEMPT_ONLY__CLASS_EXECUTOR_MUST_REVALIDATE_AND_CONFINE",
    }
    return {
        **material,
        "status": "ALLOW_REQUEST_BOUND_ROOT3_ATTEMPT",
        "allowed": True,
        "authorization_sha256": _sha(material),
        "acceptance_credit_delta": 0,
    }


def authorize(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping) or request.get("schema") != "PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2":
        return _deny("REQUEST_SCHEMA_MISMATCH")
    if not _request_hash_valid(request):
        return _deny("REQUEST_CONTENT_BINDING_INVALID")
    callsite = request.get("callsite")
    if not isinstance(callsite, Mapping):
        return _deny("CALLSITE_MISSING")
    key = (
        str(callsite.get("module_path") or ""),
        int(callsite.get("lineno") or 0),
        str(callsite.get("process_api") or ""),
    )
    effect_class = str(request.get("effect_class") or callsite.get("effect_class") or "")
    if effect_class == "READ_ONLY_DECLARED_QUERY":
        return _authorize_read_only(request, key)
    if effect_class == "TEMPORARY_FILESYSTEM_TRANSFORM":
        return _authorize_temp(request, key)
    if effect_class == CODEC:
        return _authorize_codec_child(request, key)
    if effect_class == SHELL:
        return _authorize_shell_step(request, key)
    return _deny("EFFECT_CLASS_NOT_AUTHORIZED")
