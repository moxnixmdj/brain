#!/usr/bin/env python3
"""Top-level Brain harness: namespace membrane + canonical effect broker."""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime.namespace_zero_ambient_launcher_v1 import spawn_confined
from canonical.runtime.namespace_effect_broker_session_v1 import (
    BrokerSessionError,
    serve_broker_session,
)

SCHEMA = "PROJECT_BRAIN_NAMESPACE_CONFINED_BRAIN_HARNESS_V1"


def run_confined_brain(
    policy: Mapping[str, object],
    *,
    repo_root: str | Path,
    grant_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    effect_handlers: Mapping[
        tuple[str, str],
        Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    ],
    timeout_s: float = 120.0,
    max_requests: int = 256,
) -> dict[str, Any]:
    if not (0.1 <= float(timeout_s) <= 3600.0):
        raise ValueError("TIMEOUT_INVALID")

    with spawn_confined(policy) as confined:
        confined.broker.settimeout(float(timeout_s))
        try:
            broker = serve_broker_session(
                confined.broker,
                repo_root=repo_root,
                grant_provider=grant_provider,
                effect_handlers=effect_handlers,
                max_requests=max_requests,
            )
        except (socket.timeout, TimeoutError):
            confined.kill()
            try:
                confined.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED_TIMEOUT",
                "child_returncode": confined.process.poll(),
                "effect_execution_possible_only_via_broker": True,
                "acceptance_credit_delta": 0,
                "execution_authority": False,
                "promotion_authority": False,
            }
        except Exception as exc:
            confined.kill()
            try:
                confined.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED_BROKER_SESSION",
                "child_returncode": confined.process.poll(),
                "reason": type(exc).__name__ + ":" + str(exc),
                "effect_execution_possible_only_via_broker": True,
                "acceptance_credit_delta": 0,
                "execution_authority": False,
                "promotion_authority": False,
            }

        try:
            rc = int(confined.process.wait(timeout=5))
        except subprocess.TimeoutExpired:
            confined.kill()
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED_CHILD_DID_NOT_EXIT_AFTER_BROKER_CLOSE",
                "child_returncode": None,
                "broker": broker,
                "effect_execution_possible_only_via_broker": True,
                "acceptance_credit_delta": 0,
                "execution_authority": False,
                "promotion_authority": False,
            }

        return {
            "schema": SCHEMA,
            "status": "CHILD_EXITED",
            "child_returncode": rc,
            "broker": broker,
            "effect_execution_possible_only_via_broker": True,
            "ambient_host_effect_channels": 0,
            "declared_parent_effect_channel_count": 1,
            "acceptance_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
