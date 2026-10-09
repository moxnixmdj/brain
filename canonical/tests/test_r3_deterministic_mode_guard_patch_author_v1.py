from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_deterministic_mode_guard_patch_author_v1 as author
from canonical.runtime import r3_success_adapter_patch_author_wrapper_v1 as wrapper
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall
from canonical.runtime import r3_root1_adapter_gap_witness_v1 as gap_witness
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bound_source_fixture() -> str:
    return (
        "def adapt(request, *, repo_root):\n"
        "    replay = request.get('replay_context') or {}\n"
        + author.OLD_GUARD
        + "\n"
        + author.OLD_RETURN
        + "\n"
        "    return {'candidate_only': True}\n"
    )


def _fixture(root: Path) -> None:
    _write(root, firewall.MUTABLE_ADAPTER_PATHS[0], _bound_source_fixture())
    _write(root, firewall.MUTABLE_ADAPTER_PATHS[1], "raw adapter\n")
    for path in gap_witness.SUCCESS_ADAPTER_FRONTIER_PATHS:
        target = root / path
        if not target.exists():
            _write(root, path, "frontier auxiliary\n")
    for path in gap_witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS:
        _write(root, path, "IMMUTABLE_VERIFIER\n")


def _context(mode: str, *, deterministic: bool = True, checkpoint: bool = True) -> dict:
    proof = {
        "source_schema": "sha256:" + "1" * 64,
        "source_status": "sha256:" + "2" * 64,
        "selected_plan": ["sha256:" + "3" * 64],
        "selected_plan_count": 1,
        "verified_target_effect_count": 1,
        "controller_checkpoint_present": checkpoint,
        "execution_rows": [
            {
                "capability_id": "sha256:" + "4" * 64,
                "pass": True,
                "status": "sha256:" + "5" * 64,
                "composition_digest_present": True,
            }
        ],
        "execution_count": 1,
        "cognition_dependency_class": (
            "DETERMINISTIC_ONLY" if deterministic else "MODEL_ASSISTED"
        ),
        "model_dependency_count": 0 if deterministic else 1,
        "semantic_acceptance_complete": False,
        "raw_goal_digest_present": False,
        "raw_task_contract_digest_present": False,
        "raw_acceptance_obligation_count": None,
        "accepted_raw_obligation_id_count": 0,
        "compiled_capability_id": None,
        "raw_goal_acceptance_present": False,
    }
    out = {
        "schema": author_context.SCHEMA,
        "status": "PASS__REDACTED_ADAPTER_AUTHOR_CONTEXT_READY",
        "pass": True,
        "replay": {
            "mode": mode,
            "request_keys": ["task_id", "goal"],
            "request_shape": {
                "task_id": {"type": "string"},
                "goal": {"type": "string"},
            },
        },
        "proof": proof,
        "bindings": {
            "proof_capsule_sha256": "sha256:" + "6" * 64,
            "replay_capsule_sha256": "sha256:" + "7" * 64,
        },
        "redaction_policy": {
            "raw_request_values_exposed": False,
            "raw_goal_text_exposed": False,
            "checkpoint_path_exposed": False,
            "acceptance_payload_exposed": False,
            "model_valuations_exposed": False,
            "verifier_source_exposed": False,
            "only_fixed_protocol_keys_and_sanitized_symbols_exposed": True,
        },
        "candidate_generation_authority": True,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    out["context_sha256"] = author_context.context_sha256(out)
    return out


def _gap(root: Path, mode: str, *, deterministic: bool = True, checkpoint: bool = True):
    redacted = _context(mode, deterministic=deterministic, checkpoint=checkpoint)
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
        "status": "PASS__ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP_ESTABLISHED__NO_CURRENT_BOUND_ACQUISITION_ROUTE",
        "pass": True,
        "root1_positive_gap_established": True,
        "required_primitive": gap_witness.REQUIRED_PRIMITIVE,
        "witness_id": "r3-root1-adapter-gap:deterministic-mode",
        "witness": {
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
            "adapter_author_context_sha256": redacted["context_sha256"],
        },
        "gap_evidence": {
            "required_behavior": "Author one candidate adapter patch.",
        },
        "adapter_author_context": redacted,
        "adapter_frontier_sha256": adapter_sha,
        "verification_authority_sha256": authority_sha,
    }


class R3DeterministicModeGuardPatchAuthorV1Tests(unittest.TestCase):
    def test_specialized_mode_generates_firewall_valid_candidate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            out = wrapper.request_candidate(
                _gap(root, "specialized"),
                repo_root=root,
                author_provider=author.author,
                author_provider_id="R3_DETERMINISTIC_MODE_GUARD_PATCH_AUTHOR_V1",
            )
            source_after = (root / author.TARGET_PATH).read_text(encoding="utf-8")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["touched_paths"], [author.TARGET_PATH])
        self.assertIn('"specialized"', out["patch_text"])
        self.assertIn('"compiled_bound"', out["patch_text"])
        self.assertIn(author.OLD_GUARD, source_after)
        self.assertFalse(out["source_write_authority"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_generic_and_decision_are_supported_exact_modes(self):
        for mode in ("generic", "decision"):
            with self.subTest(mode=mode), TemporaryDirectory() as td:
                root = Path(td)
                _fixture(root)
                packet = wrapper.build_author_packet(_gap(root, mode), repo_root=root)
                raw = author.author(packet["author_packet"])
                self.assertIsInstance(raw, dict)
                self.assertEqual(raw["target_mode"], mode)
                verdict = wrapper.validate_author_output(packet, raw, repo_root=root)
                self.assertTrue(verdict["pass"], verdict)

    def test_compiled_bound_and_raw_bound_do_not_generate_candidate(self):
        for mode in ("compiled_bound", "raw_bound"):
            with self.subTest(mode=mode), TemporaryDirectory() as td:
                root = Path(td)
                _fixture(root)
                packet = wrapper.build_author_packet(_gap(root, mode), repo_root=root)
                self.assertIsNone(author.author(packet["author_packet"]))

    def test_model_assisted_context_is_not_admitted(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(
                _gap(root, "specialized", deterministic=False),
                repo_root=root,
            )
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_checkpoint_and_complete_execution_proof_are_required(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(
                _gap(root, "specialized", checkpoint=False),
                repo_root=root,
            )
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_source_guard_drift_returns_no_candidate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            path = root / author.TARGET_PATH
            source = path.read_text(encoding="utf-8")
            path.write_text(source.replace(author.OLD_GUARD, "    if False:"), encoding="utf-8")
            gap = _gap(root, "specialized")
            packet = wrapper.build_author_packet(gap, repo_root=root)
            self.assertIsNone(author.author(packet["author_packet"]))

    def test_author_never_touches_verifier_authority(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            packet = wrapper.build_author_packet(_gap(root, "specialized"), repo_root=root)
            raw = author.author(packet["author_packet"])
            self.assertIsInstance(raw, dict)
            self.assertNotIn("r3_independent_learning_verifier_v1.py", raw["patch_text"])
            self.assertNotIn("checkpoint_verifier", raw["patch_text"])
            self.assertFalse(raw["source_write_authority"])
            self.assertFalse(raw["verification_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
