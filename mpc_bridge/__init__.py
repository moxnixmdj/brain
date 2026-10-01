"""Import shim so Harbor can load the brain-side branch-command bridge agent.

Harbor resolves ``--agent`` with ``importlib.import_module(module.path)``, so the
module must live on a dotted path. The implementation lives with the task
evidence; this shim re-exports the agent class from there.
"""
import importlib.util
from pathlib import Path

_IMPL = (Path(__file__).resolve().parent.parent
         / "canonical" / "astra_runtime" / "evidence"
         / "TB4_MP_CHECKPOINT_FRESH_EXECUTION" / "session_bridge"
         / "harbor_branch_bridge.py")

_spec = importlib.util.spec_from_file_location("mpc_bridge_impl", _IMPL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

HarborBranchBridgeAgent = _mod.HarborBranchBridgeAgent
