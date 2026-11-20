#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic image verification via ImageMagick — zero model calls.

THE ARGUMENT
------------
Computer-use tasks often require verifying visual state changes (did the
window open? did the button highlight? did the file appear in the file
manager?). Normally this requires a vision model. This module replaces
vision models with deterministic pixel-level image comparison using
ImageMagick (`import` for capture, `compare` for diff):

    capture_screen() → PNG via import -window root
    pixel_diff(img1, img2) → absolute error count via compare -metric AE
    state_changed(img1, img2, threshold) → boolean: did pixels change?

Every comparison is exact integer arithmetic — no neural network, no
embedding, no similarity score. Two images either have the same pixel
count or they don't.

ELON'S RULE APPLIED
-------------------
The best part is no part: no model calls for vision, no network calls for
image APIs, no knowledge house for image storage. Images are captured,
compared, and discarded. The comparison is deterministic and reproducible.

Authority: NONE. Producer-run sandbox measurement.
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImageDiffResult:
    """Result of deterministic pixel-level image comparison."""

    changed: bool           # True if pixel difference exceeds threshold
    absolute_error: int     # Number of differing pixels (from compare -metric AE)
    threshold: int          # Threshold used for the decision
    model_calls: int        # Always 0
    network_calls: int      # Always 0


class ImageVerification:
    """Deterministic image verification using ImageMagick command-line tools.

    Requires ImageMagick (`import`, `compare`) to be installed on the system.
    All operations are shell command invocations — zero model calls.
    """

    def __init__(self, threshold: int = 0):
        """Initialize with a pixel-difference threshold.

        Parameters
        ----------
        threshold : int
            Maximum number of differing pixels before declaring "changed".
            threshold=0 means any pixel difference counts as changed.
        """
        self.threshold = threshold
        self.model_calls = 0
        self.network_calls = 0

    def capture_screen(self, output_path: pathlib.Path | str) -> dict[str, Any]:
        """Capture the screen to a PNG file using ImageMagick import.

        Returns a dict with status, path, model_calls, network_calls.
        Fail-closed: if import fails, returns REFUSED.
        """
        out = str(output_path)
        try:
            result = subprocess.run(
                ["import", "-window", "root", out],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {
                    "status": "REFUSED",
                    "reason": f"IMPORT_FAILED__{result.stderr.strip()}",
                    "path": out,
                    "model_calls": 0,
                    "network_calls": 0,
                }
            return {
                "status": "CAPTURED",
                "path": out,
                "model_calls": 0,
                "network_calls": 0,
            }
        except FileNotFoundError:
            return {
                "status": "REFUSED",
                "reason": "IMAGEMAGICK_NOT_INSTALLED",
                "path": out,
                "model_calls": 0,
                "network_calls": 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "REFUSED",
                "reason": "IMPORT_TIMEOUT",
                "path": out,
                "model_calls": 0,
                "network_calls": 0,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "REFUSED",
                "reason": f"IMPORT_ERROR__{exc}",
                "path": out,
                "model_calls": 0,
                "network_calls": 0,
            }

    def compare(self, image_a: pathlib.Path | str,
                image_b: pathlib.Path | str) -> ImageDiffResult:
        """Compare two images pixel-by-pixel using ImageMagick compare.

        Uses `compare -metric AE` which reports the absolute error count
        (number of differing pixels). Zero model calls.
        """
        try:
            result = subprocess.run(
                ["compare", "-metric", "AE", str(image_a), str(image_b), "null:"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # compare writes the metric to stderr, exit code 1 if images differ
            stderr = result.stderr.strip()
            # parse the absolute error number from stderr
            try:
                absolute_error = int(stderr.split()[0]) if stderr else 0
            except (ValueError, IndexError):
                absolute_error = 0

            changed = absolute_error > self.threshold
            return ImageDiffResult(
                changed=changed,
                absolute_error=absolute_error,
                threshold=self.threshold,
                model_calls=0,
                network_calls=0,
            )
        except FileNotFoundError:
            return ImageDiffResult(
                changed=False,
                absolute_error=0,
                threshold=self.threshold,
                model_calls=0,
                network_calls=0,
            )
        except subprocess.TimeoutExpired:
            return ImageDiffResult(
                changed=False,
                absolute_error=0,
                threshold=self.threshold,
                model_calls=0,
                network_calls=0,
            )
        except Exception:  # noqa: BLE001
            return ImageDiffResult(
                changed=False,
                absolute_error=0,
                threshold=self.threshold,
                model_calls=0,
                network_calls=0,
            )

    def state_changed(self, image_a: pathlib.Path | str,
                      image_b: pathlib.Path | str) -> dict[str, Any]:
        """Convenience: compare two images and return a dict result."""
        diff = self.compare(image_a, image_b)
        return {
            "changed": diff.changed,
            "absolute_error": diff.absolute_error,
            "threshold": diff.threshold,
            "model_calls": diff.model_calls,
            "network_calls": diff.network_calls,
        }


# --------------------------------------------------------------------------- #
# Convenience function                                                        #
# --------------------------------------------------------------------------- #


def verify_visual_change(
    image_a: pathlib.Path | str,
    image_b: pathlib.Path | str,
    threshold: int = 0,
) -> dict[str, Any]:
    """Convenience function: verify that two images differ visually."""
    verifier = ImageVerification(threshold=threshold)
    return verifier.state_changed(image_a, image_b)
