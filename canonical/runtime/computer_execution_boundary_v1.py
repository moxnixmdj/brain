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
