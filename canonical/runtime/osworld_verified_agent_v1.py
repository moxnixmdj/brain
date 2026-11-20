"""Factory for the zero-model, ledger-gated OSWorld agent.

The adapter and pinned state kernels are reused byte-for-byte. The only new
wiring is the verified ledger policy and the already admitted sensor bridge, so
directory assertions cannot carry policy-supplied field/value facts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.osworld_sensor_request_bridge_v1 import AdmittedSensorGuestOps
from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent
from canonical.runtime.osworld_verified_policy_v1 import decide as verified_decide

DEFAULT_POLICY_ID = "BRAIN_OSWORLD_VERIFIED_POLICY_V1"


def build_verified_agent(
    *,
    policy_id: str = DEFAULT_POLICY_ID,
    store: str | Path | None = None,
    guest_controller: Any | None = None,
) -> BrainOSWorldAgent:
    """Compose the ledger policy with the admitted guest controller."""
    controller = guest_controller
    if controller is None:
        controller = (AdmittedSensorGuestOps(store=store) if store is not None
                      else AdmittedSensorGuestOps())
    return BrainOSWorldAgent(
        policy_provider=verified_decide,
        policy_id=policy_id,
        guest_controller=controller,
    )
