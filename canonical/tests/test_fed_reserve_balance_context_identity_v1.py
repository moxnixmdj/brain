from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import fed_reserve_balance_context_identity_v1 as identity

ROOT=Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass":True,
        "status":"PASS__FAKE_PROJECTION",
        "receipt":{
            "fragment_ids":sorted(
                str(row["fragment_id"]) for row in pack.get("fragments",[])
            ),
            "receipt_sha256":"a"*64,
        },
        "source_fragment_authority":True,
        "terminal_authority":False,
    }


def span(text,needle):
    start=text.index(needle)
    return start,start+len(needle)


def resolve(text,needle,**kwargs):
    start,end=span(text,needle)
    return identity.resolve_occurrence(
        text,start=start,end=end,repo_root=ROOT,
        projection_verifier=fake_projection,**kwargs
    )


class Tests(unittest.TestCase):
    def test_banks_hold_reserves_in_fed_accounts_resolves(self):
        text="Banks hold reserves—money—in accounts at the Federal Reserve."
        out=resolve(text,"reserves")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["concept_id"],identity.CONCEPT_ID)
        self.assertEqual(
            out["relation_signature"],
            "BANKS_HOLD_RESERVES_IN_FED_ACCOUNTS",
        )

    def test_bank_possessive_reserves_at_fed_resolves(self):
        out=resolve(
            "The bank's reserves at the Federal Reserve increased.",
            "reserves",
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["concept_id"],identity.CONCEPT_ID)

    def test_bank_reserves_in_account_at_fed_resolves(self):
        out=resolve(
            "The bank's reserves in its account at the Federal Reserve increased.",
            "reserves",
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["relation_signature"],
            "BANK_RESERVES_IN_ACCOUNT_AT_FED",
        )

    def test_reserve_balances_at_fed_resolves(self):
        out=resolve(
            "Reserve balances at the Federal Reserve increased.",
            "Reserve balances",
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["relation_signature"],
            "RESERVE_BALANCES_AT_FED",
        )

    def test_bare_singular_reserve_is_unresolved(self):
        text="Reserve increased."
        start,end=span(text,"Reserve")
        out=identity.resolve_occurrence(
            text,start=start,end=end,repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__TARGET_OCCURRENCE_OUTSIDE_BOUND_RESERVE_SURFACE",
        )

    def test_plural_reserves_without_fed_relation_is_unresolved(self):
        out=resolve("The bank's reserves increased.","reserves")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_UNIQUE_FED_RESERVE_BALANCE_RELATION_SIGNATURE",
        )

    def test_loan_loss_reserves_do_not_steal_fed_identity(self):
        out=resolve(
            "The loan loss reserves increased while the Federal Reserve met.",
            "reserves",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_UNIQUE_FED_RESERVE_BALANCE_RELATION_SIGNATURE",
        )

    def test_unrelated_reserves_near_fed_do_not_resolve(self):
        out=resolve(
            "Oil reserves increased near a Federal Reserve building.",
            "reserves",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_UNIQUE_FED_RESERVE_BALANCE_RELATION_SIGNATURE",
        )

    def test_negated_relation_is_unresolved(self):
        out=resolve(
            "The bank's reserves are not at the Federal Reserve.",
            "reserves",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
        )

    def test_second_reserves_occurrence_is_not_stolen(self):
        text=(
            "The bank's reserves at the Federal Reserve increased, "
            "while commodity reserves increased."
        )
        first=text.index("reserves")
        second=text.index("reserves",first+1)
        out=identity.resolve_occurrence(
            text,start=second,end=second+len("reserves"),repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_UNIQUE_FED_RESERVE_BALANCE_RELATION_SIGNATURE",
        )

    def test_source_authentication_failure_fails_closed(self):
        text="The bank's reserves at the Federal Reserve increased."
        start,end=span(text,"reserves")
        out=identity.resolve_occurrence(
            text,start=start,end=end,repo_root=ROOT,
            projection_verifier=lambda _pack:{"pass":False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "PINNED_FED_RESERVE_SOURCE_AUTHORITY_FAILED",
        )

    def test_missing_required_fragment_fails_closed(self):
        text="The bank's reserves at the Federal Reserve increased."
        start,end=span(text,"reserves")
        out=identity.resolve_occurrence(
            text,start=start,end=end,repo_root=ROOT,
            projection_verifier=lambda _pack:{
                "pass":True,
                "receipt":{
                    "fragment_ids":["BANKS_HOLD_RESERVES_IN_FED_ACCOUNTS"],
                    "receipt_sha256":"b"*64,
                },
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "FED_RESERVE_SOURCE_FRAGMENT_NOT_AUTHENTICATED",
        )

    def test_pack_blob_drift_fails_closed(self):
        source=ROOT/identity.PACK_PATH
        doc=json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"]+="-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/identity.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc,sort_keys=True),encoding="utf-8")
            text="The bank's reserves at the Federal Reserve increased."
            start,end=span(text,"reserves")
            out=identity.resolve_occurrence(
                text,start=start,end=end,repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PACK_GIT_BLOB_DRIFT",out["reason"])

    def test_no_global_policy_or_terminal_authority(self):
        out=resolve(
            "The bank's reserves at the Federal Reserve increased.",
            "reserves",
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["occurrence_identity_authority"])
        self.assertFalse(out["global_reserve_sense_authority"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
