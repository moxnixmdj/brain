"""Brain adapter for the pinned model-free ARC symbolic ensemble V15.

The detector source is vendored as a content-addressed Python source bundle.
No external model or inference API is invoked. Candidate transformations are
accepted by the donor harness only after exact reproduction of every training
demonstration.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_VENDOR_ZIP = Path(__file__).resolve().parents[1] / "vendor" / "arc_symbolic_ensemble_v1.zip"
if str(_VENDOR_ZIP) not in sys.path:
    sys.path.insert(0, str(_VENDOR_ZIP))

import numpy as np  # type: ignore
import harness as _harness  # type: ignore
import registry as _registry  # type: ignore

SCHEMA = "PROJECT_BRAIN_ARC_SYMBOLIC_ENSEMBLE_V15"
VENDOR_SHA256 = "95c01e84e5db7ee6e7323d8d7dc72f1e0c8462b59d7f846ab7c204a0585b34cc"
DONOR_COMMIT = "e151937e34c8b34f953833a0dab75797fc737ba4"


def _grid(value: Sequence[Sequence[int]], label: str) -> np.ndarray:
    a = np.asarray(value, dtype=int)
    if a.ndim != 2 or a.size == 0:
        raise ValueError(label + "_INVALID")
    if np.any(a < 0) or np.any(a > 9):
        raise ValueError(label + "_CELL_RANGE_INVALID")
    return a


def solve_task(task: Mapping[str, Any]) -> dict[str, Any]:
    try:
        raw_train = task["train"]
        raw_test = task["test"]
        if not isinstance(raw_train, Sequence) or not raw_train:
            raise ValueError("TRAIN_INVALID")
        if not isinstance(raw_test, Sequence) or not raw_test:
            raise ValueError("TEST_INVALID")

        train = [
            (
                _grid(pair["input"], f"TRAIN_{i}_INPUT"),
                _grid(pair["output"], f"TRAIN_{i}_OUTPUT"),
            )
            for i, pair in enumerate(raw_train)
        ]
        tests = [
            (_grid(pair["input"], f"TEST_{i}_INPUT"), None)
            for i, pair in enumerate(raw_test)
        ]

        predictions, fitting_detector_count = _harness.solve_task(
            {"train": train, "test": tests},
            _registry.ALL,
        )
        return {
            "schema": SCHEMA,
            "status": "CANDIDATES",
            "vendor_sha256": VENDOR_SHA256,
            "donor_commit": DONOR_COMMIT,
            "detector_count": len(_registry.ALL),
            "fitting_detector_count": fitting_detector_count,
            "predictions": [
                [candidate.astype(int).tolist() for candidate in candidates]
                for candidates in predictions
            ],
            "max_attempts_per_test": 2,
            "all_candidates_demo_verified": True,
            "external_model_used": False,
            "external_inference_service_used": False,
            "terminal_authority": False,
            "promotion_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "external_model_used": False,
            "external_inference_service_used": False,
            "terminal_authority": False,
            "promotion_authority": False,
        }
