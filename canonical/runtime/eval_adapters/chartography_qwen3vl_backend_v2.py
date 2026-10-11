"""Artifact-identity lock for the verified Chartography Qwen backend V1.

V2 does not change the request/response or inference semantics. It verifies the
exact local Qwen model and projector bytes before delegating to V1.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from canonical.runtime.eval_adapters import chartography_qwen3vl_backend_v1 as v1

MODEL_SHA256 = "66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a"
PROJECTOR_SHA256 = "30ba2c7dd3127a4561b6cba9d13d0f711c91bdb38742e2f56d73c8cb596bd06d"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_artifacts() -> tuple[Path, Path]:
    model = v1.local_file("PROJECT_BRAIN_QWEN_MODEL")
    projector = v1.local_file("PROJECT_BRAIN_QWEN_MMPROJ")
    if _sha256_file(model) != MODEL_SHA256:
        v1.fail("QWEN_MODEL_SHA256_MISMATCH")
    if _sha256_file(projector) != PROJECTOR_SHA256:
        v1.fail("QWEN_MMPROJ_SHA256_MISMATCH")
    return model, projector


def main() -> int:
    verify_artifacts()
    return v1.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import sys
        sys.stderr.write(type(exc).__name__ + ":" + str(exc) + "\n")
        raise SystemExit(1)
