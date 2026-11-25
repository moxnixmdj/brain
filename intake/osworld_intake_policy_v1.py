#!/usr/bin/env python3
"""Compose the authorized-answer intake with the existing verified OSWorld policy.

This is a root-level candidate adapter: it changes no byte-pinned runtime kernel.
The base decision is made by the existing verified policy (unified policy gated by
the external task ledger); the intake only replaces an unearned DONE with one
authorized question, or admits an authorized answer as a fresh guest assertion.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import osworld_verified_policy_v1 as verified  # noqa: E402

from intake import authorized_answer_intake_v1 as intake  # noqa: E402

SCHEMA = "BRAIN_OSWORLD_AUTHORIZED_INTAKE_POLICY_V1"


def decide(state: Mapping[str, Any]) -> dict[str, Any]:
    """Run the verified policy first; apply the intake only to its decision."""
    return intake.decide(state, verified.decide)
