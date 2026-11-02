"""Shared fail-closed status for unadmitted automatic computer execution.

This is not an isolation check or an authorization token. No request flag,
process environment or caller can use it to grant execution authority. It
marks automatic routes that are deliberately unavailable until a reviewed,
admitted confinement and effect-verification path exists.
"""

FAILURE_CLASS = 'COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT'
STATUS = 'FAIL_CLOSED__' + FAILURE_CLASS


def is_unconfined_capability_id(capability_id):
    """Known IDs that can cause host execution; not a complete effect catalog."""
    return capability_id in {'shell.command.run', 'software.analysis.diagnose_and_architect.v1'}


REPAIR_CAPABILITY_ID = 'python.software.repair.apply.verified.v1'


def retained_repair_policy_error(config, learn):
    """Return an explicit conflict or malformed configuration, if any."""
    from collections.abc import Mapping
    if not isinstance(config, Mapping) or type(config.get('enabled')) is not bool:
        return 'RETAINED_LEARNING_CONFIG_INVALID'
    if learn is False and config['enabled']:
        return 'RETAINED_LEARNING_CONFLICTS_WITH_LEARN_FALSE'
    return None


def is_repair_verification_gap(result):
    """The specific repair admission refusal, including its exact bound wrapper."""
    if not hasattr(result, 'get') or result.get('pass') is not False:
        return False
    cid = result.get('compiled_capability_id') or result.get('capability_id')
    if cid == 'bound:' + REPAIR_CAPABILITY_ID:
        inner = result.get('result')
        return is_repair_verification_gap(inner)
    if cid != REPAIR_CAPABILITY_ID:
        return False
    import re
    token = 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:' + REPAIR_CAPABILITY_ID
    return bool(re.search(re.escape(token) + r'(?![A-Za-z0-9_.-])', str(result.get('reason') or '')))


def is_unconfined_repair_entry(capability_id, entry):
    """Recognize repair's test-running adapter; direct calls still bypass this guard."""
    if capability_id == REPAIR_CAPABILITY_ID:
        return True
    if not hasattr(entry, 'get'):
        return False
    if entry.get('adapter_module') == 'python_repair_apply_verified_v1':
        return True
    source = entry.get('source')
    path = str(source.get('adapter_path') or '') if hasattr(source, 'get') else ''
    if not path:
        return False
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    try:
        return (root / path).resolve() == (root / 'canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py').resolve()
    except (OSError, RuntimeError, ValueError):
        return True


def is_unconfined_cli_entry(entry):
    """Recognize the known generic local command adapter, not all unsafe code.

    Other adapters and direct calls may also execute programs; this is a narrow
    guard, not a complete security classifier or a grant of authority.
    """
    if not hasattr(entry, 'get'):
        return False
    if entry.get('adapter_module') == 'cli_command':
        return True
    source = entry.get('source')
    path = str(source.get('adapter_path') or '') if hasattr(source, 'get') else ''
    if not path:
        return False
    # The local dispatcher resolves adapter_path against this repository, so
    # apply the same resolution before comparing, including symlink aliases.
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    try:
        return (root / path).resolve() == (root / 'canonical/runtime/bound_capabilities/cli_command.py').resolve()
    except (OSError, RuntimeError, ValueError):
        # An unresolvable adapter path cannot be admitted as safe.
        return True


DIAGNOSE_CAPABILITY_ID = 'software.analysis.diagnose_and_architect.v1'
DIAGNOSE_ADAPTER_MODULE = 'software_analysis_diagnose_and_architect_v1'
DIAGNOSE_ADAPTER_PATH = 'canonical/runtime/bound_capabilities/software_analysis_diagnose_and_architect_v1.py'

# Operations whose implementation in
# `canonical/swe_kernel/diagnostics_perf_and_design_engine_v1.py` is pure AST or
# text analysis: no `exec`/`compile` of target code, no child process, no target
# import, and every function reachable from them (within that module) is the
# same. The value is the engine function the adapter dispatches to, so a change
# to the dispatch table fails the guard instead of silently re-pointing an
# admitted operation at an executing one.
#
# Measured 2026-11-02 by an AST call-graph walk of that engine: the operations
# below reach no `exec`, no `compile`, no `_run_cmd`/`pipeline_exec_v1`, no
# `shutil.which` and no other repository module. Every other diagnose operation
# (`profile_hotspot`, `benchmark_git_ref`, `fuzz_overflow`, `explain_behavior`,
# `explain_bug`, `diagnose_test_suite`, `find_root_cause`, `find_race_condition`,
# `measure_coverage`, `measure_mutation_score`, `find_flaky_tests`,
# `lint_javascript`, `run_js_tests`, `run_single_test`, `git_*`,
# `review_pull_request`, `show_definition`, `which_modules_import`,
# `import_cycles`, `class_hierarchy`) reaches `exec`, `pipeline_exec_v1.
# run_command` or a repository symbol-graph module that may do either, and stays
# refused. A missing or unrecognised operation is refused.
STATIC_DIAGNOSE_OPERATIONS = {
    'analyze_log_exception': 'analyze_log_exception',
    'audit_dependencies': 'audit_dependency_vulnerabilities',
    'design_adr': 'synthesize_architecture_artifact',
    'find_dead_code': 'find_dead_code_symbols',
    'migration_plan': 'synthesize_architecture_artifact',
    'package_split_design': 'synthesize_architecture_artifact',
    'plan_rename': 'plan_rename_files',
    'review_api_design': 'review_api_design',
    'security_audit': 'security_audit_package',
    'trace_data_flow': 'trace_intermodule_data_flow',
    'trace_value_provenance': 'trace_value_provenance_in_file',
    'validate_json_schema': 'validate_json_config_schema',
}


def _resolves_to_diagnose_adapter(entry):
    """True only when the entry names this adapter by module name or resolved path."""
    if not hasattr(entry, 'get'):
        return False
    if entry.get('adapter_module') == DIAGNOSE_ADAPTER_MODULE:
        return True
    source = entry.get('source')
    path = str(source.get('adapter_path') or '') if hasattr(source, 'get') else ''
    if not path:
        return False
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    try:
        return (root / path).resolve() == (root / DIAGNOSE_ADAPTER_PATH).resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def diagnose_operation_is_static(capability_id, entry, operation):
    """The one narrowing that is admitted: a static-analysis diagnose operation.

    It decides only that *this* call does not need an execution carrier, because
    the code it runs does not execute anything. It is not a confinement check and
    grants nothing to any other capability, adapter or operation.
    """
    if str(capability_id or '') != DIAGNOSE_CAPABILITY_ID and not _resolves_to_diagnose_adapter(entry):
        return False
    return str(operation or '').strip() in STATIC_DIAGNOSE_OPERATIONS


def refuses_execution(capability_id, entry, operation=None, *, repair=True):
    """The single decision every execution site must use.

    Fails closed: an unknown capability, a missing operation or an operation not
    in the audited static table is refused exactly as before.

    `repair=False` is for the one caller whose refusal of the repair row is
    conditional (the raw-goal fabric refuses it only for a multi-action or DAG
    plan, or outside the bound registry). Folding repair into the decision there
    made the refusal earlier than the path that records the missing-information
    gap, which is a regression in what the creature learns from a refusal.
    """
    if diagnose_operation_is_static(capability_id, entry, operation):
        return False
    return (
        is_unconfined_capability_id(capability_id)
        or is_unconfined_execution_entry(entry)
        or (repair and is_unconfined_repair_entry(capability_id, entry))
    )


def is_unconfined_execution_entry(entry):
    """Recognize two known execution-capable adapters; not a safety allowlist.

    The diagnosis adapter includes operations that run target tests or load
    target code. Refuse the whole adapter until its operation surface has been
    audited and a carrier admitted. Direct calls bypass this dispatcher guard.
    """
    if is_unconfined_cli_entry(entry):
        return True
    if not hasattr(entry, 'get'):
        return False
    if entry.get('adapter_module') == 'software_analysis_diagnose_and_architect_v1':
        return True
    source = entry.get('source')
    path = str(source.get('adapter_path') or '') if hasattr(source, 'get') else ''
    if not path:
        return False
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    try:
        return (root / path).resolve() == (root / 'canonical/runtime/bound_capabilities/software_analysis_diagnose_and_architect_v1.py').resolve()
    except (OSError, RuntimeError, ValueError):
        return True
