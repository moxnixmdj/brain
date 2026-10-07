"""Collision-total successor generator for ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001.

V1 uses random opaque source IDs. Those IDs can collide inside one requirement,
which can alias a high-authority source with the low-authority source and make the
otherwise sound policy fail. V2 preserves the same random draws and research
semantics but makes the source slot structurally part of the opaque identifier.

This is a bounded information-safe proof population, not an open-world research
capability claim and not terminal execution authority.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any

from canonical.runtime import research_control_information_safe_proof as v1

SCHEMA = "PROJECT_BRAIN_RESEARCH_CONTROL_INFORMATION_SAFE_PROOF_V2"
DOMAINS = v1.DOMAINS


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if (
        not isinstance(seed, int)
        or isinstance(seed, bool)
        or not isinstance(ordinal, int)
        or ordinal < 0
    ):
        raise ValueError("INPUT")

    r = random.Random((seed << 17) ^ ordinal ^ 0x4D34)
    domain = DOMAINS[ordinal % len(DOMAINS)]
    n = 3 + (ordinal % 3)
    reqs = []
    sources = []
    hidden = {}

    for i in range(n):
        rid = f"R{i}"
        token = f"{domain}_{r.randrange(1000, 9999)}_{i}"
        reqs.append(
            {
                "id": rid,
                "text": f"Establish material finding {token}",
                "material": True,
            }
        )

        # Structural slot makes source identity injective within a requirement
        # even if the random opaque suffix collides.
        opaque = [
            f"S-{rid}-{slot}-{r.randrange(10000, 99999)}"
            for slot in range(3)
        ]
        first, second, low = opaque

        sources.extend(
            [
                {
                    "source_id": first,
                    "authority": 0.96,
                    "cost": 2.0,
                    "available": True,
                },
                {
                    "source_id": second,
                    "authority": 0.93,
                    "cost": 1.5,
                    "available": True,
                },
                {
                    "source_id": low,
                    "authority": 0.70,
                    "cost": 1.0,
                    "available": True,
                },
            ]
        )

        first_supports = (seed + i + ordinal) % 2 == 0
        hidden[first] = {
            "query_token": token,
            "supports": [rid] if first_supports else [],
            "content": f"Source material for {token}",
        }
        hidden[second] = {
            "query_token": token,
            "supports": [] if first_supports else [rid],
            "content": f"Source material for {token}",
        }
        hidden[low] = {
            "query_token": token,
            "supports": [rid],
            "content": f"Secondary source material for {token}",
        }

    r.shuffle(sources)
    budget = 3 * n + 1
    return {
        "schema": SCHEMA,
        "behavior_id": "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
        "case_id": f"RESEARCH-V2-{seed}-{ordinal}",
        "objective": f"Resolve every material {domain} requirement with authoritative evidence.",
        "material_requirements": reqs,
        "source_catalog": sources,
        "policy": {
            "minimum_authority": 0.90,
            "search_cost": 1.0,
            "max_actions": budget,
            "stop_only_when_all_material_requirements_supported": True,
        },
        "_oracle": {"sources": hidden},
    }


# Episode semantics are intentionally inherited byte-for-byte from V1.
public_state = v1.public_state
run_episode = v1.run_episode


def run_batch(seed: int, case_count: int, policy_fn) -> dict[str, Any]:
    rows = []
    by_domain = defaultdict(lambda: {"pass": 0, "total": 0})

    for ordinal in range(case_count):
        case = generate_case(seed, ordinal)
        try:
            verdict = run_episode(case, policy_fn)
        except Exception as exc:
            verdict = {
                "pass": False,
                "reason": "CANDIDATE_EXCEPTION:"
                + type(exc).__name__
                + ":"
                + str(exc),
            }

        domain = DOMAINS[ordinal % len(DOMAINS)]
        by_domain[domain]["total"] += 1
        by_domain[domain]["pass"] += int(bool(verdict.get("pass")))
        rows.append(
            {
                "case_id": case["case_id"],
                "pass": bool(verdict.get("pass")),
                "reason": verdict.get("reason"),
            }
        )

    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema": "PROJECT_BRAIN_RESEARCH_CONTROL_INFORMATION_SAFE_PREFLIGHT_RESULT_V2",
        "seed": seed,
        "case_count": case_count,
        "passed": passed,
        "failed": case_count - passed,
        "all_pass": passed == case_count,
        "by_domain": {k: dict(v) for k, v in sorted(by_domain.items())},
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
