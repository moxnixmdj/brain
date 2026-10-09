> **Canonical transplant note (2026-10-09):** This handoff was originally written while the executable package lived only on an unmerged preservation branch. It is being added to canonical Brain history by the transplant commit recorded in `2026-10-09_PROFESSIONAL_QUALITY_FULL_RESEARCH_CANONICAL_TRANSPLANT_V1.json`. Statements below describing the pre-transplant state are preserved as historical provenance. No capability, ownership, benchmark, acceptance, or terminal credit follows from this transplant.

# Brain Professional / Qualitative Judgment — Full Research Handoff

**Date:** 2026-10-09
**Authority:** research preservation only. No capability, acceptance, ownership, benchmark, or terminal credit.

## Current durable state
- Closed unmerged GitHub PR #3667: `Professional quality: collapse research into executable closure normal form`.
- Closed PR head: `81b167d4f8b5f542a1f7dfa121c9f8aa62f61987`.
- Preservation branch: `research/professional-quality-full-save-20261009-v2`.
- Preservation branch head after reconciliation probe: `7ba9eb8c299b033d8f95d58b98cba860fff3d1ae`.
- Core package preserved on that branch: action intent, 12-root normal form, 28-challenge matrix, fail-closed structural verifier, tests, reasoning reconciliation, CI workflow.
- These files were not present on canonical `main` when checked after PR closure.
- GitHub Actions runs on the prior PR created jobs with `steps=[]`; no verifier test actually executed. Treat as execution-carrier non-result, not pass/fail.
- In-session structural replay on the exact normal-form/challenge-matrix blobs found 12/12 expected roots, 28 challenges, all roots covered, zero structural errors, 4/4 negative canaries detected; this was non-independent and zero credit.

## Research corpus

### 1–16: core professional-quality assurance
1. **Robust qualitative excellence:** no single scalar or judge defines quality; use context-conditioned dimensions, pairwise comparison, heterogeneous calibrated evaluators, hard-defect separation, robust/minimax preference reasoning, fresh terminal evidence; professional excellence is distinct from exact Opus preference.
2. **Measurement-system qualification:** construct validity first; quality universe, anchor ladder, severity/discrimination/reliability calibration, causal degradations/metamorphic tests, uncertainty decomposition, legitimate disagreement preservation.
3. **Candidate-space/search closure:** strong judging cannot rescue weak search; diverse lineages, transformation basis, escape generation, separate artifact closure from search closure, stop by material-undiscovered-improvement saturation.
4. **Reality/outcome anchoring:** combine construct, comparative, and consequence evidence; outcomes include comprehension, decision accuracy, recall, latency, misinterpretation, trust calibration, actionability; shared judge consensus is insufficient.
5. **Causal quality verification:** separate intrinsic/causal/preference quality; X→M→Y, interventions/randomization where feasible; preserve outcome vectors; distinguish structural validity, robust preference, causal effect, generalization.
6. **Applicability envelope:** quality is conditional on audience/goal/environment/time; define target contexts, effect modifiers, transport overlap and certified coverage envelope.
7. **Temporal drift:** detect before adapt; freeze evaluator within an optimization episode; time/version-bound certs; separate evaluator drift from world/audience/context drift.
8. **Novelty-safe excellence:** unfamiliar≠bad and novel≠good; OOD detection; mechanism/outcome tests; separate familiarity penalty from defect; maintain escape generator and distant-search budget.
9. **Adaptive evaluation integrity:** dev/selection/cert separation; freeze before terminal test; secret/random fresh challenges; exposed holdouts retired; evidence states PRISTINE/EXPOSED/CONTAMINATED/STALE; failed cert consumes evidence.
10. **Preference structure:** no assumed scalar total order; strict preference, practical equivalence, uncertain dominance, incomparability; compatible preference models, cycles/context effects, vetoes, robust maximality, VOI.
11. **Causal attribution:** winner correctness does not prove mechanism; matched counterfactuals, factorial interactions, substance/style swaps, negative controls; promote correlation→controlled association→causal feature/interactions→mechanism.
12. **Multiscale/emergent quality:** evaluate element→slide/page→section→whole artifact→audience session; dependency/sequence effects, holistic residual, global regression after local edits, internal grammar/pacing/density.
13. **Delivery/realization fidelity:** authored x→renderer→experienced x_e; quality applies to experienced artifact; delivery envelope, render diffs, exact hash, accessibility/ecological testing, dependency manifest, fault injection.
14. **Intent/spec closure:** immutable request R0 separate from compiled spec S; plausible spec set, trace request→criteria→tests→artifact, goal/proxy separation, decision-sensitive ambiguity only, TARGET separate from CURRENTLY_PROVEN.
15. **Meta-assurance/defeaters:** assurance case plus rebutting/undermining/undercutting defeaters; false-cert paths across target/candidate/measurement/inference/scope/realization/change; unmapped material path = uncontrolled certification hazard.
16. **Executable assurance kernel:** typed Claim/Inference/Evidence/Defeater/Assumption/Test/Scope/Subject; exact subject hash/version/config; explicit inference; evidence provenance/independence/exposure/uncertainty; proof-carrying artifact package.

### 17–36: kernel, execution, and assurance infrastructure
17. **Kernel semantics:** workers never write CLOSED; append-only content-addressed history; OPEN/CLOSED/FAILED/CONFLICT; derived validity and dependency invalidation; small trusted canonicalizer/hasher/reducer/graph validator.
18. **Bounded model checking/policy precommit:** prior abstract exploration reportedly 2,136 states up to 7 transitions with no false CLOSED under intended rules; mutations produced false-cert traces; freeze materiality/risk policy and hash it before terminal evidence.
19. **Immutable ledger/pure reducer:** persist facts/events, not conclusions; SemanticState=Reduce(Facts); closures/defeaters derived and reopenable; hash-linked checkpoints; caches have zero authority.
20. **Confluence/canonical representation:** same facts→same cert independent of arrival order/serialization/duplicates; monotone fact union with nonmonotone certification; strict canonicalization and conflict preservation.
21. **Schema/reducer evolution:** MUST_UNDERSTAND; unsupported required fields→UNSUPPORTED; EQUIVALENT/REFINING/BREAKING evolution; migrations append DerivedFrom; auto migration requires semantic-preservation proof.
22. **Authority graph/roles:** separate proposal, observation, validation, adjudication, certification, policy mutation; typed scope-bounded authority; no self-promotion.
23. **Threshold authorization:** load-bearing state changes use explicit threshold/authority policy, not hidden defaults.
24. **Failure-domain independence:** assurance depends on independent failure domains; κ is minimum independent failures needed to break a property; common ancestry reduces redundancy.
25. **Weighted temporal compromise cost:** where adversarial corruption matters, reason about cost/time required to compromise enough independent domains.
26. **Adaptive attacker-defender value:** focus defenses on the cheapest causal false-certification routes, not static checklists.
27. **Lifetime risk:** tiny per-run risks can become material over repeated use; cumulative exposure and dependence matter.
28. **Model-risk closure:** risk model is assumption-bearing; maintain model-family uncertainty and misspecification challenges.
29. **Observability:** every material failure needs observable signals and coverage.
30. **Detection-to-enforcement:** detected failures must bind to block/reopen/route/remediate; dashboards alone have no authority.
31. **Crash-consistent issuance:** artifact, evidence snapshot, and certificate must not split under partial commit/crash.
32. **Rollback resistance:** stale favorable state cannot replace newer invalidating evidence; use epoch/version/freshness checks.
33. **Trusted time/randomness:** freshness and hidden-challenge secrecy depend on trustworthy time/random sources when load-bearing.
34. **Software realization/reproducible builds:** correct theory can be invalidated by implementation; bind source/implementation versions, reproducible builds, deterministic replay.
35. **Platform attestation:** activate only when platform substitution is a material failure route.
36. **Assurance regress:** stop regress using explicit PROVED/ASSURED/ASSUMED leaves and conditional assurance; ordinary professional tasks default to P0/P1, not P3/P4 machinery.

### 37–60: criteria, judges, grounding, composition, proof search
37. **Latent criterion discovery:** rubric is a hypothesis; holistic residual triggers discovery; promote criteria only with discrimination, held-out explanatory power, intervention validity, nonredundancy, stability, adversarial robustness; target decision completeness, not impossible universal criterion recovery.
38. **Residual attribution:** residual may be nonlinearity/interactions/context/measurement/evaluator noise/latent/irreducible; diagnose before inventing new criteria; exact attribution unnecessary if decision invariant.
39. **Stakeholder aggregation:** evaluator outputs can be epistemic/preference/hybrid; competence≠normative authority; keep user spec, audience needs, professional convention, reviewer taste, hard facts distinct; use Pareto/necessary dominance/minimax regret.
40. **Surrogate validity/target anchoring:** AI judge reliability≠professional-population validity; use large cheap surrogate panel plus small target-professional/outcome grounding; calibrate near finalists; track conditional bias/OOD; exact Opus preference requires actual Opus observations.
41. **Adaptive Goodhart:** surrogate can fail under optimizer pressure; track search pressure/distribution; scrutinize extreme winners; frozen dev judge, exploit archive, fresh generator-blind terminal evaluation; optimize target lower bound, not judge score.
42. **Evidence ancestry:** judges may share base model, training, distillation, provider, RLHF, rubric, references, prompt, labels; independence is genealogical plus empirical error diversity; unknown genealogy→ANCESTRY_UNKNOWN.
43. **Selection noise/optimizer's curse:** noisy evaluator + large search selects lucky errors; search evidence is not cert evidence; wide search→shortlist→fresh finalist eval→freeze winner→fresh cert; track regret/ties/winner identity uncertainty.
44. **Evaluation resolution:** define meaningful δ and resolution; use comparison intervals; practical equivalence and abstention; repetition reduces random error not bias; qualify near decision boundary.
45. **Absolute quality floor:** relative best does not imply excellence; maintain defective/usable/competent/excellent/exceptional ladder, hard constraints/vetoes/professional requirements/outcomes, multiple defensible standards; distinguish BEST_AVAILABLE_BUT_BELOW_STANDARD, STANDARD_MET_BUT_SEARCH_OPEN, EXCELLENT_AND_SEARCH_CLOSED.
46. **Anchor/provenance contamination:** prestige/brand framing can bias standards; provenance swaps, blind intrinsic channel, candidate-blind standard setting; Opus reference does not define professional excellence automatically.
47. **Anchor memorization/training contamination:** public anchors may be recognized; use private shadows/twins/continuous families, style-mimic degraded controls; UNSEEN_PRIVATE strongest; detector pass does not prove unseen.
48. **Challenge-generation validity:** Fresh∧Valid∧Diagnostic∧Representative∧OracleSound; freeze challenge spec; prefer verified transformations/metamorphic oracle over unconstrained generation; generator≠oracle; challenge uncertainty propagates.
49. **Challenge-to-deployment transport:** P_test≠P_deploy; separate representative/stress/mechanism suites; reweight only with support; missing mechanisms cannot be weighted into existence; certified envelope is intersection of construct/judge/challenge/transport support.
50. **Performative deployment:** deployment policy can change future distribution; separate exogenous/endogenous shift, maintain external anchors where possible, account for selection, monitor self-confirming loops/diversity collapse.
51. **Equilibrium/path dependence:** same policy may have multiple reachable equilibria/basins; model basin risk, rollout order, tipping boundaries, resilience/recovery; prefer large good basins.
52. **Compositional assurance:** assumption-guarantee graph, assumption discharge, joint satisfiability, nonvacuity, typed interfaces, scope intersection, no unsupported cycles; same exact artifact/system must satisfy root conjunction.
53. **Abstraction/refinement:** contract must preserve downstream-relevant behavior; under-approximation unsound, over-approximation safe/imprecise; effect manifests and safe refinement (weaker assumptions, stronger guarantees).
54. **Concurrency/interference:** commutative/idempotent fact plane where possible; noncommutative authority ops need linearization and optimistic concurrency; workers emit facts, not authority; recompute derived state.
55. **Distributed partitions/split brain:** knowledge may fork/merge, authority may not; under partition, authority pauses unless quorum semantics justify it; certificates bind checkpoint/epoch/policy/semantics/commit proof.
56. **Evidence admission:** workers append observations/claims, not truth; admission checks identity/integrity/auth/subject/method/scope/freshness/provenance/contamination/claim-fit; preserve contradictions; RAW→AUTHENTICATED→PROVENANCE_CHECKED→ADMISSIBLE→REPRODUCED→REFUTED.
57. **Semantic claim typing:** raw text→claim IR with predicate/subject/object/quantifier/modality/population/context/time/scope/comparison/effect/uncertainty; predicate→verification contract; natural language itself has no inference authority; weakening auditable.
58. **Inference rules/hidden premises:** each derivation has RuleID/Premises/SideConditions/Assumptions/Conclusion/Scope; distinguish deductive rules from empirical warrants; rich proposer, tiny checker; no certainty creation, scope preserved.
59. **Proof-search incompleteness:** NO_PROOF_FOUND≠FALSE/UNPROVABLE; separate semantic states from search states; preserve partial proofs and frontier/min blocking cuts; diagnose missing evidence/lemma/rule/ambiguity/resource/counterexample/conflict.
60. **Bounded inquiry/rational stopping:** stop based on decision invariance, EVPI/EVSI, regret and veto-sensitive uncertainty; distinguish CERTIFIED/REFUTED/DECISION_CLOSED/PRACTICALLY_EQUIVALENT/UNRESOLVED_STOP/RESOURCE_STOP.

### 61–84: preferences, representation, statistics, multiplicity
61. **Utility/normative uncertainty:** separate world uncertainty Θ from utility family U; preserve vector outcomes/hard constraints; Pareto prune, necessary preference, minimax regret; user statements constrain preferences without invented precise weights; freeze preference constitution.
62. **Preference-elicitation performativity:** questions can change preferences; track baseline/expressed/deliberated states and protocol/frame/order/context/time; ask only decision-sensitive preference questions; never elicit what cannot change the correct action.
63. **Strategic preference/incentive compatibility:** reported preference can be strategic; separate authority/expertise/decision power/incentives; role types AUTHORITATIVE/DESCRIPTIVE/ADVISORY/FORECAST/EVIDENTIARY; mechanism claims scoped, not universal.
64. **Constituency/representation:** define target population before sample; normative who-counts separate from empirical representativeness; missing strata cannot be fixed by weighting; track coverage/representativeness/response validity/independence/context match; population mixture may be uncertain.
65. **Measurement invariance:** groups may use scales differently; test construct/metric/threshold invariance; pairwise reduces scale-use heterogeneity but not construct/preference heterogeneity; keep group-specific scales if invariance fails; only require invariance where comparison matters.
66. **Within-episode drift:** evaluator state includes severity/discrimination/criterion interpretation/fatigue/calibration/context/history; use canaries/change-point/order controls; fresh terminal contexts; historical evidence stale after meaningful drift.
67. **Panel interaction/social influence:** seal pre-discussion judgments; consensus has no automatic bonus; preserve minority reports/revision reasons; model influence/conformity; aggregate information before opinions; discuss only if disagreement decision-critical.
68. **Rater assignment/identifiability:** judge-artifact graph must be sufficiently connected locally; bridge artifacts and shared finalist judges; adaptive specialist routing logged; disconnected assignment→ASSIGNMENT_DISCONNECTED.
69. **Judge×artifact interaction:** judge competence is local by criterion/domain/style/quality region/novelty; detect structured residuals/halo; global correction can hide conditional bias; route typed claims or abstain outside envelope.
70. **Meta-evaluator/judge-router selection:** choosing best evaluator/router from noisy calibration creates second-order winner's curse; certified object is full evidence-acquisition policy; split judge-cal/route-dev/route-cert; unknown region→NO_QUALIFIED_JUDGE.
71. **Grounded meta-evaluation:** regress ends in deterministic verifier, observable target outcomes, correctly constituted target professionals/humans, normative authority, or explicit assumption frontier; terminal support paths must reach ground; ungrounded cycles invalid.
72. **Ground conflict/joint feasibility:** classify epistemic conflict, construct mismatch, normative conflict, real tradeoff; hard constraints define feasible set; observed tradeoff may be generator weakness; soft objectives stay vector-valued; root closure requires same artifact satisfy all branches.
73. **Joint assurance/multiplicity:** strong marginal branch confidence does not imply strong conjunction confidence; root failure risk is union of branch failures; use global procedural false-cert budget and simultaneous coverage or validated dependence models; risk follows proof logic.
74. **Probability semantics:** a 95% classical CI is not 95% posterior truth probability; guarantees must state semantics/randomness/conditioning/scope/assumptions/loss/adaptivity; distinguish frequentist coverage, type-I/FWER/FDR, posterior, predictive, PAC, conformal, calibrated probability, robust bound.
75. **Meta-controller/critical-path correctness:** VOI/attention controller can miss important branches; estimated low value may deprioritize but hard pruning requires valid upper bound; retain falsification budget; measure meta-regret, premature stop and missed critical branch rate; OOD widens caution.
76. **Agenda/consideration set:** preference depends on candidates/attributes/representation/order/reference/protocol; test order/translation/dominated-candidate/irrelevant-attribute perturbations; terminal winner robust across defensible agenda family or AGENDA_DEPENDENT.
77. **Criterion ontology/decomposition invariance:** criterion splitting can create fake weight; fundamental objectives vs indicators/proxies/constraints/diagnostics; conserve value under refinement; clone/compress attacks; semantics-preserving decomposition should not change terminal decision.
78. **Scale/normalization/reference range:** same measurements can yield different winners after transformation; respect scale type; avoid candidate-dependent min/max normalization; use candidate-independent anchors and meaningful value functions; normalization changes can require weight revalidation.
79. **Compensability/interaction topology:** weighted sum can wrongly compensate veto weakness; trade-off permission matrix FORBIDDEN/BOUNDED/ALLOWED/CONDITIONAL/UNKNOWN; hard floors, veto regions, sparse interactions; weakest aggregation model sufficient.
80. **Reference-point/baseline contamination:** absolute quality, relative improvement, benchmark superiority are distinct; weak baseline cannot certify excellence; blind absolute evaluation before comparison; track reference role and reference sensitivity.
81. **Distributional quality/tail risk:** equal means do not imply reliability; track central quality, threshold reliability, low quantile/CVaR, failure probability, worst critical group as needed; aleatoric vs epistemic uncertainty; catastrophic tails may be vetoes.
82. **Rare-event/unseen failure:** zero observed failures≠zero risk; simple iid zero-failure upper bound p_U=1−α^(1/n)≈3/n at 95%; separate mode discovery, frequency estimation, structural exclusion; stress distribution not deployment frequency.
83. **Selective observability/missing outcomes:** exposure→participation→completion→outcome observation; MCAR/MAR-like/MNAR; high response rate does not prove low bias; support/positivity; policy-independent audits/follow-up; MNAR sensitivity bounds; tail cert requires tail observability.
84. **Rashomon/model multiplicity:** multiple semantically admissible near-optimal models can fit evidence yet disagree on finalists; maintain Rashomon/version set and DecisionSet; necessary conclusions hold across all survivors; ensemble averaging does not erase epistemic disagreement; disagreement guides discriminating experiments.

### 85–97: final discovered holes before process transition
85. **Evaluator-channel / candidate-control integrity:** artifact content is evidence, never evaluator-control authority; separate control plane/evidence plane; inventory visible/hidden/metadata/link surfaces; test prompt-injection/style/hidden-channel effects; artifact self-claims carry zero authority without independent evidence.
86. **Observer equivalence / representation loss:** model experience→observation operator→judge; observation sufficiency is criterion-specific; test observation collisions where materially different audience experiences collapse to same evaluator view; bind terminal claims to exact observation basis; lost information cannot be recovered by more reasoning.
87. **Operator/presenter dependence:** artifact quality, operator quality, pair quality, system quality are distinct; outcome may depend on artifact×presenter×audience×context; use crossed designs, operator envelope, robustness and rank-reversal tests; great presenter cannot certify weak artifact as intrinsically excellent.
88. **Cross-condition contamination/carryover:** after seeing A, participant/evaluator may not be naive for B; distinguish period effects from content learning, criterion sensitization, memory, fatigue; counterbalancing does not erase irreversible carryover; first-exposure claims require naive/validly adjusted evidence.
89. **Analysis-path / researcher degrees of freedom:** same data may support different results under defensible analyses; freeze analysis constitution/admissible family and selection rule; post-hoc selection is another optimizer's curse; record all terminal-relevant paths; robust decision must survive decision-relevant specifications or remain ANALYSIS_DEPENDENT.
90. **Pseudoreplication / hidden dependence:** nominal N≠effective independent information; distinguish observation unit from inference/replication unit; model clusters/shared presenter/session/judge family/source/failure cause; repeated same-mechanism calls reduce random noise, not systematic error; do not count shared root leaves repeatedly.
91. **Base-rate / spectrum shift:** evaluator accuracy/calibration/precision are population and stage specific; balanced benchmark does not determine deployment PPV; distinguish prevalence shift from difficulty spectrum shift; qualify near the actual threshold and post-selection finalists; heavy optimization itself creates shift.
92. **Reference-standard/ground-truth fallibility:** reference label is evidence unless grounding makes it definitive; truth types deterministic/direct outcome/normative authority/construct judgment/latent empirical state; preserve disagreement/ambiguity/plurality; reference uncertainty propagates to judge calibration; benchmark corrections invalidate descendants.
93. **Temporal-horizon / delayed outcome:** Y_x(t) trajectory; immediate and later rankings may reverse; target horizons are part of spec and frozen before results; short-term proxy transports only through validated surrogate/causal argument; delayed censoring and environment drift matter.
94. **Outcome-measure gaming / transfer validity:** assessment performance is not the construct; use ladder verbatim retrieval→paraphrase→near transfer→structural transfer→ecological task; terminal items generated after artifact freeze; construct transparent but exact instances hidden; gains that vanish under paraphrase/context/application are assessment-specific.
95. **Evaluation reactivity/ecological context:** being evaluated can change attention, effort, presenter behavior, strategy; distinguish level reactivity from differential reactivity that changes ranking; probe evaluation vs deployment regime only when decision-relevant; measurement itself can be an intervention.
96. **Predictive-to-prescriptive/edit-effect closure:** knowing what is good≠knowing what action improves it; feature importance/critique/gradient/correlation are edit hypotheses, not causal authority; learn τ_T(x), heterogeneity, interactions, sequence effects; exploratory branches are allowed, promotion requires verified improvement.
97. **Intervention fidelity/manipulation validity:** intended edit, realized transformation, actual changed properties may differ; intervention contract includes target/dose/preconditions/allowed+forbidden effects/invariants; verify manipulation and collateral changes; compound improvement proves package, not isolated component, unless isolated by further evidence.

## Process correction reached in this thread
The discovery direction was correct, but continuing to add one named closure layer per turn became diminishing-return bureaucracy. The workflow should now be:
1. Normalize the existing mechanisms into a small root ontology.
2. Build the global false-certification graph.
3. Adversarially search for materially distinct uncovered paths.
4. Patch only genuine uncovered paths.
5. Execute an end-to-end challenge suite.
6. Seek decision-level closure/saturation evidence rather than counting concepts.

## 12-root closure normal form
- **R1 TARGET_SPECIFICATION:** objective, audience, hard constraints, plausible interpretations, target construct, claim scope.
- **R2 CANDIDATE_SEARCH:** diversity, search closure, best-of-mediocre/local-fixation protection.
- **R3 REALIZATION_OBSERVATION:** exact bytes, delivery, experienced artifact, observation sufficiency, hidden/render loss.
- **R4 MEASUREMENT_CONSTRUCT:** construct validity, absolute floor, ontology/scale/resolution, transfer.
- **R5 EVALUATOR_REFERENCE:** local judge qualification and fallible/plural reference standards.
- **R6 EVIDENCE_GROUNDING_DEPENDENCE:** evidence typing/provenance/independence/common cause/grounding/uncertainty semantics.
- **R7 CAUSAL_PRESCRIPTIVE:** attribution, edit effects, intervention fidelity, scope, post-edit verification.
- **R8 POPULATION_CONTEXT_OPERATOR:** constituency, presenter/operator, context, representation/invariance, reactivity.
- **R9 TEMPORAL_DEPLOYMENT:** horizons, drift, carryover, censoring, rare events, performativity/equilibria where material.
- **R10 ANALYSIS_DECISION:** analysis family, aggregation, compensation, thresholds, risk policy, ontology/scale robustness.
- **R11 ADAPTIVE_INTEGRITY_SECURITY:** dev/selection/cert split, holdouts, evaluator control plane, Goodhart/selection pressure, evidence consumption.
- **R12 META_COMPOSITION_CLOSURE:** assumption-guarantee composition, same-artifact root conjunction, defeaters, challenge coverage, nonvacuity, residual unknowns.

A proposed new issue becomes a new root only if it is a materially distinct causal false-certification path that cannot be mapped soundly to an existing root. Otherwise it becomes another challenge/test.

## 28 adversarial challenge classes
C01 goal substitution; C02 ambiguous-spec winner; C03 best of mediocre; C04 search fixation; C05 render/capture loss; C06 hidden-surface dependence; C07 rubric underrepresentation; C08 assessment overfit; C09 reference-standard error; C10 frontier-local judge failure; C11 pseudoreplication; C12 ungrounded meta-evaluator; C13 predictive-prescriptive gap; C14 compound-edit attribution; C15 presenter confounding; C16 reactivity rank reversal; C17 carryover learning; C18 horizon reversal; C19 analysis cherry-pick; C20 ontology/scale reversal; C21 forbidden compensation; C22 candidate-to-judge-control/prompt injection; C23 optimizer Goodhart; C24 holdout reuse; C25 root conjunction failure; C26 hidden assumption cycle; C27 unmapped defeater; C28 always-abstain vacuity.

Every injected false-certification challenge must force FAIL, ABSTAIN, or INVESTIGATE. Terminal PASS is forbidden for the challenge case.

## P1 default professional-quality path
1. Compile target spec and hard constraints.
2. Generate diverse candidate branches while preserving incumbent.
3. Run deterministic fact/structure/format/grounding checks.
4. Render exact audience view and bind observation channels.
5. Run criterion-specific plus holistic comparative evaluation.
6. Attack finalists with only relevant invariance/defeater/hidden-channel/counterexample probes.
7. Freeze winner; use fresh or selection-aware terminal evidence.
8. Issue scoped certificate or abstain with minimum blocking cut.

Escalation triggers: near decision boundary, qualified disagreement, novelty/OOD, heavy optimization against dev judge, material invariance failure, reference ambiguity, model/analysis multiplicity that changes decision, high-consequence/veto dimension, unsupported observation channel, or population/context/time transport gap. Do not run all deep assurance machinery on every ordinary artifact.

## Hard nonclaims and continuation
- Professional-quality closure is not proved.
- Uncovered set is not proved empty.
- Opus 5.5 equivalence/noninferiority is not proved.
- The 28-challenge matrix is not proved complete.
- No fresh terminal evidence was consumed for the normal-form integration.
- Persistence of research creates zero capability/acceptance/ownership/terminal credit.
- Closed/unmerged PR or preservation branch is not canonical-main promotion.
- CI check records with zero executed steps are neither passing nor failing executions.

Next work: independently replay structural verifier when an actual runner executes; instantiate end-to-end fixtures for all 28 challenge classes; run an independent defeater search whose explicit target is an unmapped false-certification path; only add a new root if one is found; quantify saturation carefully without treating absence-of-discovery as proof of completeness; keep P1 cheap and relevance-gated; never weaken the original target because evidence is inconvenient.

## Source note
The chat used current 2026 literature and primary/official sources across LLM-as-judge robustness, multimodal document evaluation, causal/prescriptive modeling, longitudinal outcomes, transfer/assessment validity, clustering/dependence, label/base-rate shift, imperfect reference standards, reactivity, and related methods. This handoff preserves the substantive conclusions, not a complete bibliography. Any terminal empirical claim derived from external literature should re-bind the original primary source rather than using this handoff as source authority.