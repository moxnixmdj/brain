# RECURSIVE OBSOLESCENCE CONTROL LAW V3

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Supersedes:
- canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V2.md

## Purpose

Recursive obsolescence analysis (OBS) is the default outer control loop for every consequential Project Brain action.

V3 preserves V2 and closes a second critical failure class: a fresh route-discovery timestamp can still authorize an execution route whose volatile dependencies are unavailable now.

V2 closed the earlier failure class where a route can be locally well justified yet globally obsolete because the external candidate universe changed after the last search.

A previously selected route has **no durable authority** merely because it was once best known.

## Core invariant

**NO CONSEQUENTIAL DIAGNOSIS, CURRENT-BLOCKER CLAIM, RECOMMENDATION, ROUTE SELECTION, IMPLEMENTATION, OR EXPENSIVE CONTINUATION MAY RECEIVE CURRENT AUTHORITY UNTIL A CURRENT OBS PASS PROVES THAT THE SELECTED ROUTE SURVIVES A FRESH CHALLENGER FRONTIER.**

The burden of proof is on keeping the incumbent route, not on discovering a reason to switch.

## Operator decision boundary

OBS applies before the operator turns analysis into an authoritative Project Brain conclusion, not merely before code or infrastructure changes.

Before claiming the current blocker, recommending or selecting a route, starting consequential work, spending a scarce gate, or changing capability credit, the operator MUST:

- refresh the live canonical pointer, active goal hierarchy, frontier queue, scoreboard, and relevant task/evidence state;
- treat conversation memory, summaries, and prior assistant conclusions as retrieval hints only, never current authority;
- complete the seven OBS layers against the current canonical base;
- refresh the challenger frontier and selected-route preflight when required;
- withhold decision authority if any required OBS predicate is stale, missing, hollow, or contradicted.

Exploration and hypothesis generation may occur before OBS, but those outputs are provisional and MUST NOT be presented as the current blocker, selected route, or authorized next action.

The machine-readable operator contract is `canonical/governance/OPERATOR_OBS_DECISION_BOUNDARY_V1.json`.

## Seven recursive OBS layers

Every consequential action MUST evaluate all seven layers in order:

1. OBS the real goal.
2. OBS the required capability.
3. OBS the blocker.
4. OBS the proposed solution.
5. OBS the verification route.
6. OBS the inherited system after a win.
7. OBS the OBS/search process itself.

All V1 deletion-first, verification, inheritance, stop, and progress rules remain mandatory.

## Live challenger frontier

When an external tool, service, library, API, model, solver, database, runtime, provider, repository, package, or composition could plausibly satisfy the required capability, OBS-2 and OBS-4 MUST include a fresh challenger frontier.

A valid challenger frontier contains:

- the incumbent route, if one exists;
- the exact UTC time discovery was refreshed;
- a freshness lease of no more than 24 hours;
- inherited Brain routes checked;
- official/primary product, documentation, changelog, release, or specification evidence;
- code or package registry evidence;
- broad web/community/launch discovery evidence;
- multiple semantically different query families, including capability-vector searches rather than only provider-name searches;
- every material challenger found;
- evidence for each material challenger;
- a comparison over correctness, useful capability strength, wall-clock time, incremental cost, reliability, and verifiability;
- unresolved plausible dominators;
- the surviving selected route.

The route frontier is invalid if any plausible challenger could dominate the incumbent and has not yet been cheaply resolved.

## Discovery diversity rule

Searching one wording, one provider class, one directory, or one familiar ecosystem is insufficient.

The search MUST deliberately vary at least:

- capability wording;
- supplier/product wording;
- implementation form;
- recency/new-release wording.

Where relevant, discovery should span official sources, GitHub or equivalent code registries, package/model registries, broad web search, launch/changelog surfaces, and community/social discussion.

The purpose is not ritual coverage. It is to make terminology and ecosystem blind spots less able to hide a superior route.

### Discovery is not qualification

Broad web, community, social, launch, and discussion surfaces are discovery sensors, not truth authority.

A material challenger may be surfaced there, but promotion, rejection, or comparison claims that determine the route decision MUST be grounded in at least one qualification-grade source class:
- official/primary documentation, specification, changelog, pricing, or release evidence;
- code/package/model registry evidence for registry-verifiable properties;
- direct probe evidence;
- independent verifier evidence.

Community evidence alone can trigger investigation. It cannot by itself qualify or disqualify a consequential route.

## Freshness lease

For externally supplied capabilities, the challenger frontier lease MUST be <=24 hours.

Expiry invalidates the route decision before:

- expensive execution;
- a second or later repair/continuation on the same route;
- new infrastructure work;
- freezing or spending a scarce validation gate;
- declaring a provider/supplier route exhausted;
- promoting a route as fastest sufficient.

A new material external release, capability, price/limit change, access change, or discovered route invalidates the affected OBS layers immediately even if the lease has not expired.

Stable historical facts may be cached. The current route decision may not.

## Adversarial challenger rule

For any incumbent route consuming meaningful wall-clock time, one search role is adversarial:

> Find a route that makes the incumbent unnecessary.

A challenger is useful even when it loses. The system must record why it loses.

No route is protected by sunk cost, familiarity, existing code, prior debugging effort, or prior selection.

## Incumbent failure rule

After a material route failure, do not automatically repair the route.

Before continuation:

1. refresh the challenger frontier;
2. rerun only affected OBS layers;
3. test whether the failure is route-specific;
4. switch immediately if a faster sufficient challenger now exists.

## Infrastructure rule

Before building or repairing a carrier, provider bridge, scheduler, runtime, deployment path, account integration, queue, or orchestration layer, the live challenger frontier is mandatory.

Infrastructure work is forbidden if an existing challenger can delete the infrastructure requirement.

## Selected-route execution preflight

A fresh challenger frontier proves only that the route decision is current. It does **not** prove that the selected route can execute now.

Before consequential execution, repair continuation, infrastructure continuation, or scarce-gate spend, every normal action MUST attach a selected-route execution preflight.

The preflight MUST:

- bind to the exact selected route;
- be checked no more than 2 hours before trusted validation;
- enumerate **all** execution-critical dependencies of the selected route and assert the inventory complete;
- use controlled dependency kinds so carriers and entitlement/capacity surfaces cannot be renamed into a static-looking category;
- include at least one execution substrate dependency: carrier, local runtime, model API, or remote service;
- classify each dependency as STATIC or VOLATILE;
- mark every required dependency READY;
- carry current evidence for every required dependency;
- contain no unresolved or failed required dependency.

Examples of volatile dependencies include hosted compute carriers and runner pools; account quota, billing entitlement, free-credit balance, or account authorization; remote model/API endpoints; externally rate-limited or capacity-limited execution services; and network services whose availability determines whether the route starts or completes.

Historical success is not current availability.

Documentation, pricing pages, changelogs, model cards, and public provider status pages may establish capability or global health. They cannot by themselves prove that an account-scoped, quota-scoped, region-scoped, or capacity-scoped dependency is READY now.

For a required VOLATILE dependency, qualification MUST include at least one direct non-destructive probe of the exact dependency or one independent verifier observation of the exact dependency.

For ACCOUNT_SPECIFIC or REGION_SPECIFIC scope, direct or independent evidence is mandatory and the evidence scope MUST exactly match the dependency scope. Generic public status is insufficient.

A failed current probe immediately invalidates the selected route even when the route-frontier lease itself is fresh.

### Preflight probe economy

Preflight is not permission to waste scarce tests. Use the cheapest sufficient non-destructive check that proves route startability and required entitlement/capacity. Do not spend a held-out scientific or benchmark gate merely to prove a carrier can start.

If no cheap preflight can prove readiness, the route remains unresolved and execution does not begin.

## Search stop rule

Search is not infinite.

Stop and execute when:

- a correctness-sufficient route exists;
- the live challenger frontier is fresh;
- no unresolved plausible dominator remains;
- remaining candidates cannot reasonably beat the selected route enough to justify delay;
- further search is unlikely to change the execution decision.

A stale candidate set can never satisfy the stop rule.

## OBS receipt V4

Every consequential action MUST carry a generation- and exact-base-bound V4 receipt with the V3 fields plus a selected-route execution preflight inside `route_frontier` for normal executable work.

For actions where external route discovery is genuinely inapplicable, the receipt may set `discovery_required=false` only for governance, reconciliation, or evidence-preservation work and MUST state why.

Normal capability acquisition, real-task execution, support, repair, adaptation, infrastructure, and verification actions do not receive that exemption.

## Recursive invalidation

Invalidate affected OBS layers on:

- canonical base change;
- canonical generation change;
- material task/capability change;
- selected-route falsification;
- new adequate route discovery;
- route-frontier lease expiry;
- selected-route preflight expiry;
- required volatile dependency failure or entitlement/capacity change;
- material provider/tool/model/library release or access change;
- verification requirement change.

Refresh only affected layers when safely localizable. Otherwise reissue the full receipt.

## OBS-6 deletion reaction

Every verified capability gain triggers immediate downstream deletion analysis.

The first question after a win remains:

> What can now be deleted?

The same applies after a superior challenger is discovered: obsolete incumbent repairs, probes, infrastructure, and queued work must be stopped rather than ceremonially completed.

## Progress

OBS and discovery activity receive zero progress credit.

Progress remains VERIFIED REUSABLE CAPABILITY OUTPUT.

The live challenger frontier is successful when it reduces wall-clock to real output by preventing work on obsolete routes.

## Priority

1. correctness and real capability strength;
2. minimum wall-clock time to verified reusable output;
3. minimum incremental cost;
4. live discovery/reuse/deletion over construction;
5. independent verification strength;
6. minimum machinery, compute, context, and energy.

The best part is still no part. A stale route is merely a part that has not yet received the courtesy of deletion.
