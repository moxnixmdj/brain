"""Serial, alternating timing of archive reinspections on one disposable fixture.

The names-only baseline is deliberately unsafe: it models the former compound
check for cost comparison and must never be used as an acceptance verifier.
The existing GNU-tar adapter and the shared byte reinspector do stronger work.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import archive_tarfile, archive_verify_gnu_tar  # noqa: E402
from canonical.runtime.raw_goal_archive_acceptance_v1 import inspect_archive_manifest  # noqa: E402


def measure(samples: int = 8) -> dict:
    with tempfile.TemporaryDirectory(prefix="brain-archive-cost-") as temporary:
        root = Path(temporary)
        folder = root / "canonical"
        folder.mkdir()
        paths = []
        for i in range(8):
            rel = f"canonical/input-{i}.bin"
            (root / rel).write_bytes(os.urandom(256 * 1024))
            paths.append(rel)
        manifest = "canonical/manifest.json"
        (root / manifest).write_text(json.dumps({"records": [{"verification_paths": paths}]}))
        archive = "bundle.tar.gz"
        archive_tarfile.run({"manifest_path": manifest, "output_path": archive}, root)
        args = {"manifest_path": manifest, "archive_path": archive}

        def names_only():
            with tarfile.open(root / archive, "r:gz") as handle:
                members = sorted(handle.getnames())
            assert members and all((root / name).is_file() for name in members)

        def byte_reinspection():
            return inspect_archive_manifest(root, manifest, archive)

        def gnu_adapter():
            return archive_verify_gnu_tar.run(args, root)

        arms = (("former_names_only_unsafe", names_only),
                ("shared_byte_reinspection", byte_reinspection),
                ("existing_gnu_verifier", gnu_adapter))
        times = {name: [] for name, _ in arms}
        for _, fn in arms:
            fn()  # warm the same fixture, outside the samples
        for i in range(samples):
            # Rotate order to reduce simple first/last-arm bias.
            for name, fn in arms[i % len(arms):] + arms[:i % len(arms)]:
                started = time.perf_counter_ns()
                fn()
                times[name].append((time.perf_counter_ns() - started) / 1_000_000)
        return {
            "schema": "BRAIN_ARCHIVE_REINSPECTION_COST_PROBE_V1",
            "samples_per_arm": samples,
            "source_file_count": len(paths),
            "source_bytes": len(paths) * 256 * 1024,
            "archive_bytes": (root / archive).stat().st_size,
            "timings_ms": {name: {"median": round(statistics.median(values), 3),
                                  "min": round(min(values), 3), "max": round(max(values), 3)}
                           for name, values in times.items()},
            "scope": "one warmed disposable local fixture; not a fleet or workload-wide rate",
            "terminal_authority": False,
        }


def main() -> int:
    print(json.dumps(measure(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
