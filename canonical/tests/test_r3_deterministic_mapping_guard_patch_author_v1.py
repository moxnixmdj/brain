from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_deterministic_mapping_guard_patch_author_v1 as author
from canonical.runtime import r3_success_adapter_patch_author_wrapper_v1 as wrapper
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall
from canonical.runtime import r3_root1_adapter_gap_witness_v1 as gap_witness


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _vulnerable_source() -> str:
    return """from __future__ import annotations

from typing import Any, Mapping
import re


def adapt(request: Mapping[str, Any]):
    if (
        request.get("kind") != "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE"
        or request.get("authority_requested") != "CANDIDATE_ONLY"
    ):
        return None

    observation = request.get("observation", {})
    if not observation.get("pass"):
        return None

    status = observation.get("status")
    output_sha256 = observation.get("output_sha256")
    if not isinstance(output_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", output_sha256):
        return None
    if not isinstance(status, str) or not status.startswith("PASS__"):
        return None
    return {
        "status": status,
        "output_sha256": output_sha256,
        "candidate_only": True,
    }
"""


def _fixture(root: Path, *, source: str | None = None) -> None:
    _write(
        root,
        firewall.MUTABLE_ADAPTER_PATHS[0],
        source if source is not None else _vulnerable_source(),
    )
    _write(root, firewall.MUTABLE_ADAPTER_PATHS[1], "raw adapter\n")
    for path in gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS:
        target = root / path
        if not target.exists():
            _write(root, path, "frontier auxiliary\n")
    for path in gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS:
        _write(root, path, "IMMUTABLE_VERIFIER\n")


def _gap(root: Path) -> dict:
    adapter_sha = gap_witness._frontier_sha256(
        gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS,
        repo_root=root,
    )
    authority_sha = gap_witness._frontier_sha256(
        gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS,
        repo_root=root,
    )
    return {
        "schema": gap_witness.SCHEMA,
        "status": (
            "PASS__ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP_ESTABLISHED__"
            "NO_CURRENT_BOUND_ACQUISITION_ROUTE"
        ),
        "pass": True,
        "root1_positive_gap_established": True,
        "required_primitive": gap_witness.REQUIRED_PRIMITIVE,
        "witness_id": "r3-root1-adapter-gap:mapping-guard",
        "witness": {
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
        },
        "gap_evidence": {
            "required_behavior": "Author one candidate success-adapter patch."
        },
        "adapter_frontier_sha256": adapter_sha,
        "verification_authority_sha256": authority_sha,
    }


class R3DeterministicMappingGuardPatchAuthorV1Tests(unittest.TestCase):
    def test_vulnerable_mapping_dereference_generates_firewall_valid_candidate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            out = wrapper.request_candidate(
                _gap(root),
                repo_root=root,
                author_provider=author.author,
                author_provider_id="R3_DETERMINISTIC_MAPPING_GUARD_PATCH_AUTHOR_V1",
            )
            source_after = (root / firewall.MUTABLE_ADAPTER_PATHS[0]).read_text(
                encoding="utf-8"
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["touched_paths"], [firewall.MUTABLE_ADAPTER_PATHS[0]])
        self.assertIn("if not isinstance(observation, Mapping):", out["patch_text"])
        self.assertIn("return None", out["patch_text"])
        self.assertEqual(source_after, _vulnerable_source())
        self.assertFalse(out["source_write_authority"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_rewrite_repairs_nonmapping_observation_fail_closed(self):
        rewritten = author._rewrite_source(_vulnerable_source())
        self.assertIsNotNone(rewritten)
        source, local_name = rewritten
        self.assertEqual(local_name, "observation")
        namespace: dict = {}
        exec(compile(source, "<mapping-guard-test>", "exec"), namespace, namespace)
        adapt = namespace["adapt"]
        valid = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "authority_requested": "CANDIDATE_ONLY",
            "observation": {
                "pass": True,
                "status": "PASS__OK",
                "output_sha256": "a" * 64,
            },
        }
        self.assertEqual(adapt(valid)["status"], "PASS__OK")
        malformed = dict(valid)
        malformed["observation"] = "not-a-mapping"
        self.assertIsNone(adapt(malformed))
        missing = dict(valid)
        missing.pop("observation")
        self.assertIsNone(adapt(missing))

    def test_already_guarded_source_returns_no_candidate(self):
        source = _vulnerable_source().replace(
            '    observation = request.get("observation", {})\n',
            '    observation = request.get("observation", {})\n'
            '    if not isinstance(observation, Mapping):\n'
            '        return None\n',
        )
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root, source=source)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_ambiguous_two_vulnerable_locals_returns_no_candidate(self):
        source = _vulnerable_source().replace(
            '    observation = request.get("observation", {})\n',
            '    observation = request.get("observation", {})\n'
            '    metadata = request.get("metadata", {})\n'
            '    if not metadata.get("ok"):\n'
            '        return None\n',
        )
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root, source=source)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_missing_mapping_symbol_returns_no_candidate(self):
        source = _vulnerable_source().replace(
            "from typing import Any, Mapping",
            "from typing import Any",
        )
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root, source=source)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_non_authoritative_packet_is_not_admitted(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(_gap(root), repo_root=root)
            forged = dict(packet["author_packet"])
            forged["source_write_authority"] = True
            self.assertIsNone(author.author(forged))


if __name__ == "__main__":
    unittest.main(verbosity=2)
