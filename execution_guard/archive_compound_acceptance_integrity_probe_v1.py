"""Probe whether compound archive acceptance checks member bytes independently.

Uses fabricated success trace records and four disposable corrupted archives.
The real archive verification adapter is run as an independent comparison.
This probes the acceptance function directly, not a live-front-door exploit.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from canonical.runtime.bound_capabilities import archive_tarfile, archive_verify_gnu_tar  # noqa: E402
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract  # noqa: E402
from canonical.runtime.raw_goal_archive_compound_acceptance_v1 import verify  # noqa: E402

GOAL = "Create a tar.gz archive from a manifest and verify the archive against that manifest."
BAD_PAYLOADS = (b"changed\n", b"", b"bad\n", b"original!\n")


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-archive-integrity-") as temporary:
        root = Path(temporary)
        (root / "canonical").mkdir()
        manifest = root / "canonical/manifest.json"
        manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/source.txt"]}]}))
        (root / "canonical/source.txt").write_text("original\n")
        contract = compile_contract(GOAL, source_id="user", routing_target_effects=["archive.verified"])
        create_args = {"capability_id": "archive.tar_gz.create_from_manifest",
                       "manifest_path": "canonical/manifest.json", "output_path": "out.tar.gz"}
        verify_args = {"capability_id": "archive.verify.tar_gz.gnu",
                       "manifest_path": "canonical/manifest.json", "archive_path": "out.tar.gz"}
        created = archive_tarfile.run(create_args, root)
        verified = archive_verify_gnu_tar.run(verify_args, root)
        for index, payload in enumerate(BAD_PAYLOADS):
            with tarfile.open(root / "out.tar.gz", "w:gz") as archive:
                archive.add(manifest, arcname="canonical/manifest.json")
                info = tarfile.TarInfo("canonical/source.txt")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            raw = (root / "out.tar.gz").read_bytes()
            # Forge all archive digests and retain the authentic source hashes,
            # member list and paths. A digest-only check must not mask a bad
            # archived payload.
            digest = hashlib.sha256(raw).hexdigest()
            trace = [
                {"plan": {"args": create_args}, "result": {
                    **created, "output_sha256": digest, "output_bytes": len(raw)}},
                {"plan": {"args": verify_args}, "result": {
                    **verified, "archive_sha256": digest}},
                {"result": {"type": "finish"}},
            ]
            acceptance = verify(goal=GOAL, execution=trace, raw_contract=contract, root=root)
            try:
                archive_verify_gnu_tar.run(
                    {"manifest_path": "canonical/manifest.json", "archive_path": "out.tar.gz"}, root)
                comparison = "ACCEPTED"
            except RuntimeError as exc:
                comparison = str(exc).split(":", 1)[0]
            rows.append({"case": index + 1, "corrupt_member_bytes": True,
                         "compound_semantic_acceptance": acceptance.get("semantic_acceptance_complete") is True,
                         "acceptance_reason": acceptance.get("reason"),
                         "actual_archive_verifier": comparison})
    unsafe = sum(row["compound_semantic_acceptance"] and
                 row["actual_archive_verifier"] == "ARCHIVE_HASH_MISMATCH" for row in rows)
    return {"schema": "BRAIN_COMPOUND_ARCHIVE_INTEGRITY_PROBE_V1",
            "status": "FAIL__CORRUPT_ARCHIVE_ACCEPTED" if unsafe else "NO_UNSAFE_ACCEPTANCE_OBSERVED",
            "case_count": len(rows), "unsafe_acceptances": unsafe, "rows": rows,
            "scope": "direct compound verifier with fabricated trace; live-front-door exploit not demonstrated",
            "terminal_authority": False}


def main() -> int:
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["unsafe_acceptances"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
