from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.authenticated_source_phrase_atom_bridge_v1 import (
    AUTHORITY_SCHEMA as LEXICON_AUTHORITY_SCHEMA,
    LEXICON_SCHEMA,
)
from canonical.runtime.repository_bound_semantic_mapping_pack_v1 import (
    PACK_SCHEMA,
    VERIFY_SCHEMA,
    load_verified_pack,
    make_concept_definition_verifier,
    make_lexicon_authority_verifier,
    pack_sha256,
)
from canonical.runtime.source_aligned_definitional_entailment_v1 import (
    CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
)


SCOPE = "finance:regulatory-capital:2026"


def pack():
    return {
        "schema": PACK_SCHEMA,
        "pack_id": "finance-loss-absorption-v1",
        "scope_id": SCOPE,
        "phrase_lexicon": {
            "schema": LEXICON_SCHEMA,
            "lexicon_id": "finance-loss-absorption-phrases-v1",
            "scope_id": SCOPE,
            "bounded_finite_lexicon": True,
            "entries": [
                {
                    "entry_id": "loss",
                    "surfaces": ["absorbs losses"],
                    "atom_id": "function.loss_absorption",
                },
                {
                    "entry_id": "resolution",
                    "surfaces": ["in resolution"],
                    "atom_id": "regime.resolution",
                },
            ],
        },
        "concept_definitions": [
            {
                "scope_id": SCOPE,
                "concept_id": "TLAC",
                "definition_kind": "EXACT_CONJUNCTION",
                "definition_atoms": [
                    "function.loss_absorption",
                    "regime.resolution",
                ],
            }
        ],
        "source_refs": [
            {
                "authority": "FSB",
                "document": "TLAC Principles and Term Sheet",
                "section": "standard overview",
                "url": "https://www.fsb.org/2015/11/total-loss-absorbing-capacity-tlac-principles-and-term-sheet-2/",
            }
        ],
    }


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write_verified_pack(root: Path, value, *, mutate=None):
    psha = pack_sha256(value)
    verify = {
        "schema": VERIFY_SCHEMA,
        "pass": True,
        "independent_verified": True,
        "pack_id": value["pack_id"],
        "scope_id": value["scope_id"],
        "pack_sha256": psha,
        "phrase_lexicon_semantics_authenticated": True,
        "concept_definitions_authenticated": True,
        "source_authority_reviewed": True,
        "verification_authority_mutated": False,
    }
    if mutate:
        mutate(verify)
    path = root / "canonical" / "verification" / "semantic-pack.json"
    path.parent.mkdir(parents=True)
    raw = (json.dumps(verify, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return {
        "path": "canonical/verification/semantic-pack.json",
        "git_blob_sha": git_blob_sha(raw),
    }


class Tests(unittest.TestCase):
    def test_valid_content_addressed_pack_authenticates(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(root, value)
            out = load_verified_pack(value, ref, repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["pack_sha256"], pack_sha256(value))
        self.assertTrue(out["phrase_lexicon_semantics_authenticated"])
        self.assertTrue(out["concept_definitions_authenticated"])
        self.assertFalse(out["terminal_authority"])

    def test_wrong_verification_blob_fails_closed(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(root, value)
            ref["git_blob_sha"] = "0" * 40
            out = load_verified_pack(value, ref, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_BLOB_DRIFT", out["reason"])

    def test_verification_for_different_pack_cannot_be_reused(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(
                root,
                value,
                mutate=lambda v: v.__setitem__("pack_sha256", "0" * 64),
            )
            out = load_verified_pack(value, ref, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("PACK_VERIFICATION_BINDING_INVALID", out["reason"])

    def test_verification_path_traversal_fails_closed(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = {
                "path": "../semantic-pack.json",
                "git_blob_sha": "0" * 40,
            }
            out = load_verified_pack(value, ref, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_PATH_INVALID", out["reason"])

    def test_verified_pack_mints_lexicon_authority_verifier(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(root, value)
            verified = load_verified_pack(value, ref, repo_root=root)
            verifier = make_lexicon_authority_verifier(verified)
            out = verifier({"candidate": True})
        self.assertTrue(out["pass"])
        self.assertEqual(out["schema"], LEXICON_AUTHORITY_SCHEMA)
        self.assertEqual(out["scope_id"], SCOPE)
        self.assertTrue(out["surface_to_atom_semantics_authenticated"])
        self.assertEqual(len(out["receipt_sha256"]), 64)

    def test_verified_pack_mints_concept_definition_verifier(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(root, value)
            verified = load_verified_pack(value, ref, repo_root=root)
            verifier = make_concept_definition_verifier(verified, "TLAC")
            out = verifier({"candidate": True})
        self.assertTrue(out["pass"])
        self.assertEqual(out["schema"], CONCEPT_DEFINITION_AUTHORITY_SCHEMA)
        self.assertEqual(out["concept_id"], "TLAC")
        self.assertTrue(out["definition_semantics_authenticated"])
        self.assertEqual(len(out["definition_sha256"]), 64)

    def test_unknown_concept_cannot_mint_definition_verifier(self):
        value = pack()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref = write_verified_pack(root, value)
            verified = load_verified_pack(value, ref, repo_root=root)
            with self.assertRaises(ValueError):
                make_concept_definition_verifier(verified, "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
