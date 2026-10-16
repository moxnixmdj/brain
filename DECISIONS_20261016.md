# Decisions — 2026-10-16 (owner delegated: optimal, fastest, honest)

Rules applied: no guard weakened; no unverified dependency added; no evolving capability deleted;
fastest path that keeps provenance.

1. **Apt-pin rule and already-installed tools → NO, rule stays.** The pin verifies the archive hash
   against the apt snapshot. The installed copies (jq, openpyxl, python-docx, xlsxwriter, sqlite3) have no
   matching snapshot records (BOUND_APT_METADATA_NOT_FOUND), so there is no reference to verify
   against. Accepting them would violate UNKNOWN_PROVENANCE_FAILS_CLOSED. The ~8 capabilities stay
   blocked-with-reason until the snapshot can be refreshed (apt index is unreachable here).

2. **Install tesseract and pandoc → NO.** apt is unreachable from this sandbox, and the adapters require the
   pinned apt path. A PyPI pandoc wheel would not satisfy that pin and would add an unverified dependency.
   I found no route to a tesseract binary through the allowed hosts. OCR and chart-reading stay blocked-with-reason.

3. **Archive the 178 unreferenced modules → NO, leave in place.** They are not imported, so they cost no runtime
   speed. Moving them breaks receipt links, and the repo forbids removing records. Their presence is harmless.
   The list stays as a review aid in AUDIT_PY_UNREFERENCED_CANDIDATES_20261016.txt.

4. **Four open-research failures → FIXED as stale test doubles, not a capability defect.**
   - claim_relation: the test replaced the real BM25 ranker with a stub that lacked `top_candidate_admission`.
     Now uses the real ranker.
   - generic_bm25: a hand-built relevance receipt lacked the admission block. Now built with the real `rank`.
   - ror_identity_composition: asserted an older frontier (authority ran on every candidate). Current design
     binds authority only to the relevance-selected candidate (optional metadata, per its own claim scope).
     Test now runs real modules, uses an objective the real gate admits, and asserts the current contract.
   - Not changed: relevance admission rule (no weakening).

Known environment failures (not caused by this work): `test_open_research_source_frontend.py` (3 tests)
and `test_capability_dag_live_wiring_v1` (pre-existing). Source-frontend tests hit live search backends
that this sandbox blocks.
