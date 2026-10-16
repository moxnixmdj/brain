# First-principles audit — 2026-10-16 (measurements, not opinions)

## Scope understood
Make every capability Brain owns (all 67 registry entries, not the 66 headline) real, reachable, and
verified from one entry point (`live_brain_route_admission_v1.solve`), with the codebase cut down to what
that creature needs and the hot path made fast. Nothing that is still evolving is deleted.

## Measured state
| Quantity | Value | How measured |
|---|---|---|
| Registry entries | 67 | `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` |
| Adapters that load with the runtime's own loader rule | 63 | `/tmp/audit_caps2.py` (path rule copied from `live_brain_route_admission_v1._run_bound_capability`) |
| Adapter files missing | 4 (`knowledge.*`, declared `runtime_native_action`, no adapter file) | same |
| Reachable from one sentence | 66 of 67 (1 zero-input) | `/tmp/e2e_after_widen.json` reachability block |
| Distinct capabilities exercised by the repo end-to-end measurement | 27 | same file, `routes_taken` |
| Families not measured here | 9 (browser, chart compound grammar, network HTTP/knowledge, markdown→PDF, PDF OCR, etc.) | `families_not_measured_here` |
| Runtime Python files | 2112 | git ls-files |
| Files in the live static+adapter import closure of `solve` | **81 (3.8%)** | `/tmp/closure2.py` |
| Test files | ~2007 | git ls-files |
| JSON under canonical/ | 8446 (mostly receipts, reconciliation, and plans) | git ls-files |
| Solve latency | 5–10 ms routing; 0.3–2 s for Python repair/fault-localise (test execution) | e2e `mean_ms` |

## What this means
1. **Over-engineering is real and concentrated in receipts and dead code, not in the creature.** 96% of runtime
   modules are outside the live closure. Some are evolving research and may be needed; they must be classified,
   not deleted. The governance layer alone produces ~8,400 JSON records; the policy forbids deleting ledgers.
2. **The "66 capabilities" headline hides ~40 that are wired but never exercised end-to-end.** The fix is a
   per-capability live probe (one sentence → artifact → independent stdlib oracle), not more plans.
3. **Four knowledge.* capabilities have no adapter file.** They are declared `runtime_native_action`; I have not
   verified that the runtime dispatches them. Unverified until probed.
4. **The remaining blockers are environmental, not design:** system binaries (pandoc, weasyprint, tesseract,
   chromedriver) not installed; network egress blocked for HTTP/knowledge. Only PyPI and npm registries are
   reachable from this sandbox, so binaries via apt are not available.
5. **Speed:** the front door is already ~5 ms. The slow items are inherent test-execution loops; the next win is
   caching their subprocess setup, not rewriting the router.

## Proposed plan (fastest path that keeps evolving capability)
- P1 (no deletion): per-capability live probe over all 67 entries; table of {reachable, runs, oracle-pass,
  environment-blocked-with-reason}. This replaces the 27-of-67 unknown with a measurement.
- P2 (no deletion): classify the 2112 runtime modules as LIVE (in closure), BOUND_ADAPTER, GOVERNANCE_TOOL,
  EVOLVING_RESEARCH (named in an open obligation or recent receipt), or DEAD_CANDIDATE. Quarantine
  DEAD_CANDIDATE to an archive folder only after the owner confirms the classification rule.
- P3: verify or remove the 4 `knowledge.*` entries (one probe each).
- P4: speed — subprocess and import caching for repair/fault loops; target: each capability under 500 ms where its
  work allows it.
- P5: PR gates. The load-bearing gate needs an intent tied to an open obligation; the paraphrase work does not
  discharge any. Keep the PR as a draft unless the owner decides how it is credited.

## Decisions needed from the owner
- Quarantine vs delete for DEAD_CANDIDATE modules (recommend quarantine; no deletion of any ledger or receipt).
- Whether environment-blocked families (browser, OCR, markdown→PDF, network knowledge) count as "real" only once
  their binaries run, or whether they are acceptable as blocked-with-reason.

## P1 result — live probe of all 67 registry entries (2026-10-16)
Probe: `/tmp/probe_all.py` (one sentence per entry from `execution_guard/live_solver_end_to_end_measurement_v1.signature_goal`,
input fixtures written with valid content by type, run through `solve`). Raw: `/tmp/probe_all_67.json`.

Outcome counts: 7 PASS (6 via front-local adapter, 1 via controller), 1 terminal kstar with no status (not run), 1 route rejected
(R3 weak evidence), 3 fail-closed tool non-success, 55 controller failures (classified below).

Classes of the 55 controller failures:
- **Environment, real, not fixable here:** tesseract binary missing (8: chart.raster.*, chart.read.*, image.extract.ocr,
  pdf OCR, professional observer); chromedriver missing (1); pandoc missing (1). Apt index unavailable (sandbox egress).
- **Present on this machine, blocked by the apt-pin gate (decision needed):** `jq` at /usr/bin/jq; openpyxl, python-docx,
  xlsxwriter, sqlite3 importable. Blocked by `BOUND_APT_METADATA_NOT_FOUND`
  (`canonical/runtime/astra_runtime.py` ~line 1043): the adapter requires a pinned apt package hash in the apt snapshot
  before installing via sudo. Count: 8 (json.query.jq, xlsx x2, docx x2, sqlite verify, qrencode, zbar). This is a supply-chain
  provenance rule. Bypassing it would be wrong; the owner must decide whether "already installed, version and hash checked"
  counts as satisfying it.
- **Generic-probe input shape, not a capability defect (needs domain fixture):** repair/fault loops `BASELINE_ALREADY_PASSES` /
  `NO_FAILING_TEST` (≈9; covered by repo e2e families); DOCX/SACCR/decision/evidence schema inputs (≈8).
- **Adapter bug candidates, to probe with domain fixtures:** `'list' object has no attribute 'get'` in archive.verify.tar_gz.gnu,
  decision.synthesis.verify, knowledge.consistency.assess, knowledge.status.assert, knowledge.support.materialize,
  source.objective_relevance.rank.bm25, source.evidence.extract (7; may be my JSON-list fixture); `dictionary update
  sequence` in source.authority.identity.ror; `Stream has ended` in pdf.extract.text.pypdf; `SQLITE_STATUS_VALUE_UNRESOLVED`.
- **knowledge.* (4):** `runtime_native_action`, no adapter file; they do execute (errors come from inside the runtime).

## Honest conclusion
The probe does not yet prove 67 capabilities are real. It proves 7 end-to-end from a generic sentence, and classifies the rest.
Making the rest real needs (a) owner decision on the apt-pin rule, (b) an environment with tesseract/pandoc, and (c) a
domain fixture per capability, which the e2e families already provide for 27.

## Correction (2026-10-16, after checking the e2e coverage)
- The `'list' object has no attribute 'get'` failures are NOT adapter bugs. `archive.verify.tar_gz.gnu` and
  `source.objective_relevance.rank.bm25` pass 1.0 in the repo's own end-to-end families (ARCHIVE_VERIFY_GNU,
  SOURCE_RANKING_BM25). The probe's generic JSON fixture (a list) was the problem.
- Still unverified (no e2e family, no domain fixture yet): decision.synthesis.verify.stdlib,
  source.evidence.extract.objective_grounded.stdlib, source.authority.identity.ror, knowledge.* (4, network-blocked).
- decision.synthesis.typed.stdlib passes in the e2e family DECISION_SYNTHESIS.
