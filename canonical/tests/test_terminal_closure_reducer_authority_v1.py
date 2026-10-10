from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.terminal_closure_reducer import _evaluate_universal_cover_proof

SCOPE = "scope://opus55/observable-trace"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fixture(root: Path, *, admit: bool) -> dict:
    proof = {
        "proof_kind": "SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id": SCOPE,
        "conclusion": "success",
        "observable_trace_scope_complete": True,
        "all_useful_target_behaviors_in_scope": True,
        "every_admission_sound": True,
        "residual_complement_unsat": True,
        "selected_cover_complete": True,
        "u_empty": True,
        "abc_closed": True,
        "all_credited_routes_brain_owned": True,
        "donor_independence_closed": True,
        "clean_room_replay_pass": True,
    }
    proof_path = root / "proof.json"
    proof_path.write_text(json.dumps(proof, sort_keys=True) + "\n", encoding="utf-8")
    proof_binding = {"path": "proof.json", "git_blob_sha": _git_blob_sha(proof_path)}

    verifier = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": proof_binding,
    }
    verifier_path = root / "verifier.json"
    verifier_path.write_text(json.dumps(verifier, sort_keys=True) + "\n", encoding="utf-8")
    verifier_binding = {"path": "verifier.json", "git_blob_sha": _git_blob_sha(verifier_path)}

    authority_path = root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    authority = {
        "authoritative_sources": {
            "fixture": (
                {
                    **proof_binding,
                    "independent_verification": verifier_binding,
                }
                if admit
                else {"note": "PAIR_NOT_ADMITTED"}
            )
        }
    }
    authority_path.write_text(json.dumps(authority, sort_keys=True) + "\n", encoding="utf-8")
    authority_binding = {
        "path": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "git_blob_sha": _git_blob_sha(authority_path),
    }

    return {
        "universal_cover_proof": {
            "proof_kind": proof["proof_kind"],
            "scope_id": SCOPE,
            "conclusion": "success",
            "proof_artifact": proof_binding,
            "verifier_receipt_artifact": verifier_binding,
            "authority_pointer": authority_binding,
        }
    }


class TerminalClosureReducerAuthorityTests(unittest.TestCase):
    def test_admitted_exact_pair_passes_universal_route(self):
        with TemporaryDirectory() as td:
            out = _evaluate_universal_cover_proof(_fixture(Path(td), admit=True), Path(td))
        self.assertTrue(out["pass"], out)

    def test_content_addressed_unadmitted_pair_cannot_self_certify_terminal_route(self):
        with TemporaryDirectory() as td:
            out = _evaluate_universal_cover_proof(_fixture(Path(td), admit=False), Path(td))
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_AUTHORITY_PROOF_VERIFIER_ADMISSION_REQUIRED", out["failed_predicates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
