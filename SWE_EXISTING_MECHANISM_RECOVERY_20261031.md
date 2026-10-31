# Existing-mechanism SWE recovery — 2026-10-31

## Implemented rather than reinvented

This work reuses Brain's acceptance-clause extractor, lossless objective compiler, measurement schema, direct repair routing, existing provenance tracer, and normal GitHub pull-request merge mechanism. No new capability, external model, dependency, or protected-policy modification was added in this follow-up.

### Reject unsupported structured requests before expensive execution

`live_brain_route_admission_v1._bind_requested_contract_checks` now feeds the original request through the existing clause extractor and objective compiler using the actual measurement schema before dispatching repair. Undeclared prefix requirements, unsupported suffixes, unknown fields, and invalid field/type combinations cannot be erased by a supported property check.

This is feasibility checking, not acceptance: supported but false objectives still require real candidate execution and verification. The existing artifact/content/property checks remain mandatory. This follow-up scopes the preflight to requests carrying explicit `contract_checks`; it does not claim general natural-language semantic understanding or preflight coverage for every adapter.

Six added real-oracle regressions put a filesystem marker in the baseline test program. All refuse before that program runs, emit no report, and preserve the entire source/input directory. No successful test result is substituted or cached.

### Honest route provenance

The request-local compilation already selects the measured repair controller directly in the current registry. Its observed primary and selected capability are now reported with basis `PRIMARY_COMPILATION_REUSED_BEFORE_EXECUTION`. Genuine typed corrections retain their distinct `DECISIVE_TYPED_SELECTION_BEFORE_EXECUTION` basis and executed verdicts remain final. The test no longer expects a historical measurement-only route that was not taken.

### Correct two stale test assumptions without weakening acceptance

- Interprocedural provenance had deliberately become opt-in upstream for cost reasons. The positive provenance test now requests `provenance=True`; the existing tracer produces actual hypotheses and its strict positive-count assertion is unchanged. This was not a missing tracing algorithm.
- The fullstack declaration test previously assumed the current partial registry contained every producer. It now exercises explicitly declaration-only complete and incomplete catalogs, requiring the exact resolution result for each. Both must still deny workflow execution, delivery verification and output acceptance. No actual software-delivery capability is inferred from catalog completeness.

### Let model diagnostics finish honestly

The missing-input negative control now uses the registered Python symbol index instead of an absent audit capability. This preserves the missing-input assertion and allows the verifier to reach all categories. Its existing fresh execution checks still expose unsupported audit, SQLite creation and test-audit workflows; none is relabeled as passing or removed.

## Actual measurements

- Reproduced all four previously reported SWE failures before edits: **4 failed, 3.96 s**.
- First corrected three-module run: **66 passed, 23.07 s**.
- Structured public-contract module, including six new no-execution controls: **30 passed, 14.82 s**.
- Full selected 16-module SWE regression run: **299 passed, 101.67 s**, one existing tree-sitter deprecation warning. This includes real repair, candidate replay, source preservation, caller routing, destination handling, parallel indexing, property checks, namespace execution, cache invalidation, and both cross-file protocols. It is not a full repository-suite claim.
- Separate wider routing/acceptance run: **50 passed, 17 failed, 12.61 s**. Actual-source comparison with the pre-change runtime reproduced **50 passed, the same 17 failed, 11.81 s**. Production source was restored byte-for-byte after comparison; no import-loader or test-harness file substitution was used. Missing registrations and older routing/composition failures remain real backlog, not passing capability evidence. These runs do not establish an overall speedup.
- Model-verification diagnostic run completed **30/33**, including **5/5 negative controls**. Remaining failures are source-audit execution, SQLite creation, and test-audit execution. They were not fixed by changing the control, and no 33/33 claim is made.
- Local integrity guard against `origin/main`: **17 rules, zero violations, PASS**. The follow-up leaves the preceding three-declaration restoration within its existing limit.

The compiled artifact is regenerated from the final tree; its own digest block and PR record identify it. The current digest is deliberately not embedded in this root knowledge document, avoiding a self-referential compiler input.

## Concurrent upstream restoration

Main advanced from restoration rung 46 to rung 52 (`4ed8fce1`) while the initial verification ran. Its changes were registry-only and were integrated without dropping any upstream declaration. Two of our three navigation restorations are now also upstream, leaving just one additional declaration relative to that base. The actual public-contract test derives the primary route independently from the current registry and checks its reported identity/basis exactly; it still independently checks the repaired function on 401 inputs.

Post-integration measurements:

- Caller/destination/integration/public-contract smoke: **74 passed, 12.65 s**.
- Wider routing/acceptance: **55 passed, 12 failed, 14.09 s**; remaining failures are disclosed, not treated as green.
- Model diagnostics: **31/33**, including the independently checked source audit restored upstream and all **5/5 negative controls**. SQLite creation and test-audit execution remain failing.

The integrated 16-module run also passed all **299 cases in 97.38 seconds** on the rung-52 registry. No whole-suite or overall speedup claim follows from this.

Main then advanced to rung 54 (`7502e90b`), again changing only the registry. All three original navigation restorations are now upstream; this branch adds **zero registry declarations** relative to that base. Post-update smoke passed **74/74 in 11.70 s**. The full 299-case run above was not rerun after this final registry-only update. The regenerated artifact covers the current registry, not the earlier smaller catalog.

Before the landing attempt, registry-only restoration continued through rung 56 (`5eb63865`). The registry was proven semantically identical to upstream and its exact upstream serialization was retained, removing formatting churn and future artificial merge conflicts. All original branch work is preserved. Subsequent registry refreshes are identified by the PR head/base and regenerated artifact; the full 299-case results above remain measurements of their stated earlier registry versions.

The concurrent restoration batch completed at rung 66 (`b0df8bee`). Its registry changes are integrated before the final required-check run. The artifact is regenerated rather than carrying forward a smaller catalog's digest. Final post-batch measurements and the actual merge outcome are recorded on PR #6341; earlier numerical results here retain their explicitly stated measurement scope.

The final integration also retains upstream's complete-registry loader and native-verdict/git improvements. Its plan-first path for explicitly stated effect families coexists with this branch's staged-crossfile grammar, structured-contract preflight, within-request context reuse and independent report reinspection. Planning faults can fall back; an executed typed adapter's failure is final, not an invitation to try a different lexical answer.

## Corrected landing diagnosis

The live GitHub branch-rules endpoint `repos/moxnixmdj/brain/rules/branches/main` declares the signed `referee/repo-integrity-guard` as its required status check, with strict up-to-date enforcement and a pull-request requirement. The local missing-intent and scope diagnostics remain failures, but they are not listed as required status checks by that endpoint. Earlier statements that they necessarily prevent any normal GitHub merge were too strong.

This evidence does not authorize bypassing the referee. A fresh signed SUCCESS for the pushed head is required before attempting the normal, head-matched PR merge. No admin flag, forced push, check manipulation, ruleset change, or protected-file edit is used. At document creation the new commit has not yet landed; the GitHub PR state is authoritative for the subsequent merge outcome.

## Late reliability observation

A later 74-case smoke run on the rung-57 integrated registry produced **73 passed, 1 failed, 11.86 s**. The failure was the *initial positive request* in `test_reinspection_rejects_tampered_real_report[different_bounds]`, before tampering: it refused with `CONTRACT_CHECKS_UNBOUND`, selected the measurement-only primary, and did not execute. This resembles the previously documented intermittent false refusal; this work does **not** claim to have explained or eliminated it.

An additional 80-case pure-planning probe did not reproduce the refusal. A subsequent **64/64 actual positive public requests passed in 50.455 s** on fresh temporary sources, but that passing probe does not cancel the failed smoke observation or prove the flake fixed. No speculative routing change or outcome-tolerant assertion was introduced to make it disappear.

## Limits

Passing these selected tests does not establish the world's fastest or most capable general software engineer. The wider 17-case routing backlog, three model execution failures, declaration-only fullstack composition, bounded repair grammars, and broader real-repository transfer/production-engineering qualifications remain unresolved. These are producer-run sandbox measurements, not independent verification or terminal-capability credit.
