"""The ledger must be able to say NO before it is allowed to say yes.

These pin the properties that make the ledger a re-checkable record rather than a bibliography:
a confirming row without verbatim words is rejected, a silent row cannot smuggle a claim, an
unaudited version cannot be presented as audited, and an id the ledger has never seen is reported
as unpinned rather than quietly passing.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools.external_evidence_ledger_v1 import (  # noqa: E402
    PINNED,
    UNPINNED,
    VERSION_MISMATCH,
    load,
    validate,
    census,
    iter_citations,
)

LEDGER = load()


def _minimal() -> dict:
    return {
        "schema": "external_evidence_ledger_v1",
        "sources": [
            {
                "id": "2610.05303",
                "version": "v1",
                "title": "t",
                "submitted": "2026-10-04",
                "fetched": "2026-11-13",
                "support_level": "ABSTRACT_CONFIRMS",
                "claim_allowed": "c",
                "quote": "q",
            }
        ],
        "drift": [],
        "claims_with_no_primary_source": [],
    }


# ---------------------------------------------------------------------------------------------
# The shipped ledger
# ---------------------------------------------------------------------------------------------
def test_the_shipped_ledger_is_structurally_valid() -> None:
    assert validate(LEDGER) == []


def test_the_rows_that_decide_the_owners_question_are_recorded() -> None:
    """If one of these is dropped, the repository goes back to citing its own conclusion."""
    ids = {row["id"] for row in LEDGER["sources"]}
    for required in ("2611.14505", "2610.05303", "2607.21051", "2611.14326"):
        assert required in ids, required


def test_every_confirming_row_quotes_the_words_that_carry_it() -> None:
    for row in LEDGER["sources"]:
        if row["support_level"] == "ABSTRACT_CONFIRMS":
            assert row["quote"].strip(), row["id"]


def test_a_drift_record_names_documents_that_exist_if_it_names_any() -> None:
    for row in LEDGER["drift"]:
        for doc in row.get("documents_repeating_the_stale_numbers", []):
            assert (ROOT / doc).exists(), f"{row['id']}: {doc}"


# ---------------------------------------------------------------------------------------------
# Fails closed
# ---------------------------------------------------------------------------------------------
def test_a_confirming_row_with_no_quote_is_rejected() -> None:
    bad = _minimal()
    bad["sources"][0]["quote"] = "   "
    errors = validate(bad)
    assert any("verbatim quote" in e for e in errors), errors


def test_a_silent_row_that_states_a_claim_is_rejected() -> None:
    bad = _minimal()
    bad["sources"][0]["support_level"] = "ABSTRACT_SILENT"
    bad["sources"][0]["claim_allowed"] = "this paper proves the gain is permanent"
    errors = validate(bad)
    assert any("licenses nothing" in e for e in errors), errors


def test_a_silent_row_may_disclaim() -> None:
    ok = _minimal()
    ok["sources"][0]["support_level"] = "ABSTRACT_SILENT"
    ok["sources"][0]["claim_allowed"] = "nothing may be asserted; not verified here"
    ok["sources"][0]["quote"] = ""
    assert validate(ok) == []


def test_an_unaudited_version_may_only_be_silent() -> None:
    bad = _minimal()
    bad["sources"][0]["version"] = "unverified"
    errors = validate(bad)
    assert any("unaudited version" in e for e in errors), errors


def test_a_row_with_no_read_date_is_rejected() -> None:
    bad = _minimal()
    bad["sources"][0]["fetched"] = ""
    errors = validate(bad)
    assert any("cannot be re-checked" in e for e in errors), errors


def test_a_malformed_arxiv_id_is_rejected() -> None:
    bad = _minimal()
    bad["sources"][0]["id"] = "arXiv 2610"
    errors = validate(bad)
    assert any("not an arXiv id" in e for e in errors), errors


def test_a_drift_row_that_names_a_missing_document_is_rejected() -> None:
    bad = _minimal()
    bad["drift"] = [
        {
            "id": "2602.12670",
            "support_level": "VERSION_DRIFT",
            "what_broke": "numbers moved",
            "documents_repeating_the_stale_numbers": ["NO_SUCH_DOCUMENT_20991231.md"],
        }
    ]
    errors = validate(bad)
    assert any("does not exist" in e for e in errors), errors


def test_misattribution_is_recorded_as_its_own_drift_kind() -> None:
    ok = _minimal()
    ok["drift"] = [
        {"id": "2602.20867", "support_level": "MISATTRIBUTED", "what_broke": "number not carried"}
    ]
    assert validate(ok) == []


# ---------------------------------------------------------------------------------------------
# The census
# ---------------------------------------------------------------------------------------------
def test_an_id_the_ledger_has_never_seen_is_reported_unpinned(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("we rely on arXiv:9999.99999 for this\n", encoding="utf-8")
    found = list(iter_citations(tmp_path, LEDGER))
    assert [c.state for c in found] == [UNPINNED]
    assert census(tmp_path, LEDGER).unpinned == 1


def test_a_pinned_id_at_its_pinned_version_is_pinned(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("see arXiv:2610.05303v1\n", encoding="utf-8")
    assert [c.state for c in iter_citations(tmp_path, LEDGER)] == [PINNED]


def test_a_pinned_id_at_another_version_is_a_mismatch(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("see arXiv:2610.05303v7\n", encoding="utf-8")
    assert [c.state for c in iter_citations(tmp_path, LEDGER)] == [VERSION_MISMATCH]


def test_a_compact_audit_row_counts_as_pinned(tmp_path: Path) -> None:
    """A paper audited in audited_elsewhere is audited; the census must not double-count it."""
    (tmp_path / "note.md").write_text("see arXiv:2610.28601\n", encoding="utf-8")
    assert [c.state for c in iter_citations(tmp_path, LEDGER)] == [PINNED]


def test_the_census_reads_every_citation_on_a_line(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text(
        "arXiv:2610.05303 and arXiv:9999.99999 in one sentence\n", encoding="utf-8"
    )
    states = [c.state for c in iter_citations(tmp_path, LEDGER)]
    assert states == [PINNED, UNPINNED]


def test_python_sources_are_scanned_too(tmp_path: Path) -> None:
    (tmp_path / "probe.py").write_text('"""Authority: arXiv:9999.99999."""\n', encoding="utf-8")
    assert [c.state for c in iter_citations(tmp_path, LEDGER)] == [UNPINNED]


def test_the_ledger_is_not_mutated_by_being_read() -> None:
    before = copy.deepcopy(LEDGER)
    census(ROOT / "canonical" / "tools", LEDGER)
    assert LEDGER == before
