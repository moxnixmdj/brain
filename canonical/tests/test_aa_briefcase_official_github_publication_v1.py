import json
import unittest

from canonical.runtime.aa_briefcase_official_github_publication_v1 import (
    OfficialPublicationError,
    git_blob_sha1,
    verify_official_github_publication,
)


def target():
    return {
        "target": {
            "benchmark": "AA-Briefcase v1.1",
            "model": "Claude Opus 5.5 (Max, Default Fallback)",
            "current_owner_elo": 1807,
            "observed_date": "2026-10-08",
        },
        "epoch_rule": {"current_epoch_minimum_opus55_target_elo": 1807},
    }


def statement():
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": "brain-aa-briefcase-candidate",
                "digest": {"sha256": "a" * 64},
            }
        ],
        "predicateType": "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v2",
        "predicate": {
            "benchmark": "AA-Briefcase v1.1",
            "target_model": "Claude Opus 5.5 (Max, Default Fallback)",
            "target_observed_date": "2026-10-08",
            "grading_protocol_manifest_git_blob_sha": "5c77f294e09d4933e3a3175c46af225b414f4702",
            "task_count": 91,
            "complete_current_scored_private_scope_used": True,
            "all_load_bearing_grading_relations_included": True,
            "brain_weakly_dominates_current_opus55": True,
            "official_owner_elo_claimed": False,
            "historical_1822_epoch_rewritten": False,
        },
    }


def publication(s=None):
    s = s or statement()
    content = json.dumps(s, sort_keys=True, indent=2) + "\n"
    return {
        "retrieval_method": "GITHUB_CONNECTOR_FETCH_FILE_AT_EXACT_COMMIT",
        "owner_identity_anchor_git_blob_sha": "672877a30053a33e3589fde5214e2c61f9ea5e74",
        "repository_full_name": "ArtificialAnalysis/Stirrup",
        "owner_login": "ArtificialAnalysis",
        "owner_type": "Organization",
        "visibility": "public",
        "commit_sha": "1" * 40,
        "git_blob_sha": git_blob_sha1(content.encode("utf-8")),
        "path": "attestations/aa-briefcase-brain.json",
        "file_content_utf8": content,
    }


class T(unittest.TestCase):
    def test_official_publication_passes_without_signature(self):
        out = verify_official_github_publication(target(), publication())
        self.assertEqual(out["status"], "PASS_OFFICIAL_GITHUB_PUBLICATION")
        self.assertFalse(out["signature_required"])
        self.assertFalse(out["numeric_elo_reconstruction_required"])

    def test_wrong_org_rejected(self):
        p = publication()
        p["repository_full_name"] = "NotArtificialAnalysis/Stirrup"
        with self.assertRaisesRegex(OfficialPublicationError, "REPOSITORY_OWNER_NAMESPACE_MISMATCH"):
            verify_official_github_publication(target(), p)

    def test_wrong_owner_type_rejected(self):
        p = publication()
        p["owner_type"] = "User"
        with self.assertRaisesRegex(OfficialPublicationError, "OWNER_TYPE_MISMATCH"):
            verify_official_github_publication(target(), p)

    def test_private_repo_rejected(self):
        p = publication()
        p["visibility"] = "private"
        with self.assertRaisesRegex(OfficialPublicationError, "PUBLICATION_NOT_PUBLIC"):
            verify_official_github_publication(target(), p)

    def test_blob_mismatch_rejected(self):
        p = publication()
        p["file_content_utf8"] += " "
        with self.assertRaisesRegex(OfficialPublicationError, "GIT_BLOB_SHA_MISMATCH"):
            verify_official_github_publication(target(), p)

    def test_wrong_anchor_rejected(self):
        p = publication()
        p["owner_identity_anchor_git_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(OfficialPublicationError, "OWNER_IDENTITY_ANCHOR_DRIFT"):
            verify_official_github_publication(target(), p)

    def test_stale_epoch_rejected(self):
        s = statement()
        s["predicate"]["target_observed_date"] = "2026-10-07"
        with self.assertRaisesRegex(OfficialPublicationError, "PREDICATE_EPOCH_MISMATCH"):
            verify_official_github_publication(target(), publication(s))

    def test_incomplete_scope_rejected(self):
        s = statement()
        s["predicate"]["complete_current_scored_private_scope_used"] = False
        with self.assertRaisesRegex(OfficialPublicationError, "PRIVATE_SCOPE_NOT_COMPLETE"):
            verify_official_github_publication(target(), publication(s))

    def test_negative_noninferiority_rejected(self):
        s = statement()
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(OfficialPublicationError, "NONINFERIORITY_NOT_ATTESTED"):
            verify_official_github_publication(target(), publication(s))

    def test_invalid_commit_sha_rejected(self):
        p = publication()
        p["commit_sha"] = "x" * 40
        with self.assertRaisesRegex(OfficialPublicationError, "COMMIT_SHA_INVALID"):
            verify_official_github_publication(target(), p)
