"""Zero-model OSWorld policy: existing deterministic stack gated by a verified ledger.

This is the runtime composition. The base stack proposes actions; the ledger
withholds DONE until explicit state requirements have fresh guest PASS receipts,
and emits the missing pinned assertions instead. Directory assertions are the
already admitted sensor request, never a policy-supplied field/value.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.osworld_verified_task_ledger_v1 import decide as _ledger_decide
from canonical.runtime.osworld_v21_unified_policy_v17 import decide as _base_decide

SCHEMA = "BRAIN_OSWORLD_VERIFIED_POLICY_V1"


def decide(state: Mapping[str, Any]) -> Mapping[str, Any]:
    return _ledger_decide(state, _base_decide)
