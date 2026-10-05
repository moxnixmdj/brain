# Opus 5.5 zero-incremental comparator free-credit route V1

Date: 2026-10-05
Status: CANDIDATE external-fact route, zero acceptance credit

## New fact

Current official Anthropic documentation states:

- Claude Opus 5.5 is active on the Claude API under model identifier `claude-opus-5-5`.
- New Claude API users receive a small amount of free credits to test the API.
- Egypt is a supported Claude location.

Primary sources:
- https://platform.claude.com/docs/en/models/opus-5-5/overview
- https://platform.claude.com/docs/en/about-claude/pricing
- https://support.claude.com/en/articles/8461763-where-can-i-access-claude

## Consequence for Project Brain

The exact Opus 5.5 comparator blocker must not be modeled as “all official exact routes necessarily require incremental spend.”

There is a conditional zero-incremental route:

`NEW_API_USER_FREE_CREDITS -> EXACT_MODEL_IDENTITY -> HARD_CREDIT_EXHAUSTION_STOP -> MINIMUM_DECISION_ONLY_COMPARATOR_WORK`

This route is admissible only if all of the following are verified before any use:
1. the account is actually eligible for the free-credit grant,
2. the exact model resolved is `claude-opus-5-5`,
3. no paid balance or post-credit billing can be consumed,
4. the available free-credit amount is sufficient for the selected minimum comparator certificate,
5. case generation remains pre-exposure and follows the frozen evaluation rules.

## Scheduling effect

Comparator acquisition is now two questions instead of one:
- eligibility for exact zero-incremental official access,
- sufficiency of the free-credit budget for the minimum certificate.

If eligibility fails, nothing else changes. If eligibility passes, the Brain should spend credits only on the smallest decision-changing matched certificate, never on a full benchmark by default.

## Nonclaims

This file does not claim the current user/account is eligible, does not claim any free-credit amount, does not claim the credits are sufficient, and creates no acceptance or capability credit.
