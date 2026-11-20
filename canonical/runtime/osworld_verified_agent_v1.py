"""Factory for the zero-model, ledger-gated OSWorld agent.

The V7 adapter and pinned state kernels are reused byte-for-byte. V7 already
executes product-native ``WEB_APP_OP`` operations through the external registry
and already accepts DONE only after a structured completion receipt. The only new
wiring is the verified ledger policy and the already admitted sensor bridge, so
directory assertions cannot carry policy-supplied field/value facts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.osworld_sensor_request_bridge_v1 import AdmittedSensorGuestOps
from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7
from canonical.runtime.osworld_v21_host_web_app_ops_v1 import OSWorldHostWebAppOps
from canonical.runtime.osworld_verified_policy_v1 import decide as verified_decide

DEFAULT_POLICY_ID = "BRAIN_OSWORLD_VERIFIED_POLICY_V1"


def build_verified_agent(
    *,
    policy_id: str = DEFAULT_POLICY_ID,
    store: str | Path | None = None,
    guest_controller: Any | None = None,
    web_app_controller: Any | None = None,
    browser_controller: Any | None = None,
) -> BrainOSWorldAgentV7:
    """Compose the ledger policy with admitted guest and product-native controllers."""
    controller = guest_controller
    if controller is None:
        controller = (AdmittedSensorGuestOps(store=store) if store is not None
                      else AdmittedSensorGuestOps())
    return BrainOSWorldAgentV7(
        policy_provider=verified_decide,
        policy_id=policy_id,
        browser_controller=browser_controller,
        guest_controller=controller,
        web_app_controller=(web_app_controller if web_app_controller is not None
                            else OSWorldHostWebAppOps()),
    )
