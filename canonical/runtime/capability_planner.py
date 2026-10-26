#!/usr/bin/env python3
"""Zero-dependency capability-graph planner for Project Brain.

This is deliberately small: it plans over externally declared capabilities
(preconditions/effects/cost/action contracts). It does not interpret arbitrary
natural language and it does not call a model. Unknown effects fail closed so
the acquisition layer can search for a missing capability instead of guessing.
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass


class PlanningFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code = code
        self.detail = detail
        msg = code if detail is None else f"{code}:{detail}"
        super().__init__(msg)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    requires: frozenset[str]
    provides: frozenset[str]
    cost: float
    action: dict
    result_fields: frozenset[str]
    # Typed composition channels: an optional declaration of what each result
    # field materially IS ("kind"+"format"), published on the channel with the
    # endpoint. Consumers may require a format; a producer that declares none
    # cannot satisfy a format predicate. Tuple of sorted (field, kind, format)
    # triples so the dataclass stays hashable.
    channel_schema: tuple = ()


def _channel_schema(value, cid):
    """Validate/normalize an optional channel_schema block.

    Shape: {"<result_field>": {"kind": <str>, "format": <str>}}. ``format`` is
    mandatory per field -- a schema without it says nothing a consumer could
    predicate on. Unknown shapes refuse loudly rather than degrade to
    "declares nothing".
    """
    if value is None:
        return ()
    if not isinstance(value, dict) or not value:
        raise PlanningFailure("CAPABILITY_CHANNEL_SCHEMA_INVALID", cid)
    out = []
    for field, spec in sorted(value.items(), key=lambda x: str(x[0])):
        field = str(field).strip()
        if not field or not isinstance(spec, dict):
            raise PlanningFailure("CAPABILITY_CHANNEL_SCHEMA_INVALID", cid)
        fmt = str(spec.get("format") or "").strip()
        kind = str(spec.get("kind") or "").strip()
        if not fmt:
            raise PlanningFailure("CAPABILITY_CHANNEL_SCHEMA_INVALID", cid)
        out.append((field, kind, fmt))
    return tuple(out)


def _channel_format(cap, field):
    """Declared format of ``field`` on a normalized capability, else None."""
    for f, _kind, fmt in getattr(cap, "channel_schema", ()):
        if f == field:
            return fmt
    return None


def _string_set(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise PlanningFailure("INVALID_STRING_SET", field)
    return frozenset(x.strip() for x in value)


def _normalize(problem):
    if not isinstance(problem, dict):
        raise PlanningFailure("INVALID_PROBLEM")
    initial = _string_set(problem.get("initial_facts", []), "initial_facts")
    targets = _string_set(problem.get("target_effects", []), "target_effects")
    if not targets:
        raise PlanningFailure("TARGET_EFFECTS_REQUIRED")
    raw_caps = problem.get("capabilities", [])
    if not isinstance(raw_caps, list) or not raw_caps:
        raise PlanningFailure("CAPABILITIES_REQUIRED")
    caps = []
    seen = set()
    for raw in raw_caps:
        if not isinstance(raw, dict):
            raise PlanningFailure("INVALID_CAPABILITY")
        cid = str(raw.get("id", "")).strip()
        if not cid or cid in seen:
            raise PlanningFailure("INVALID_OR_DUPLICATE_CAPABILITY_ID", cid)
        seen.add(cid)
        requires = _string_set(raw.get("requires", []), f"{cid}.requires")
        provides = _string_set(raw.get("provides", []), f"{cid}.provides")
        if not provides:
            raise PlanningFailure("CAPABILITY_PROVIDES_REQUIRED", cid)
        try:
            cost = float(raw.get("cost", 1.0))
        except Exception as exc:
            raise PlanningFailure("INVALID_CAPABILITY_COST", cid) from exc
        if cost < 0:
            raise PlanningFailure("NEGATIVE_CAPABILITY_COST", cid)
        action = raw.get("action")
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            raise PlanningFailure("EXECUTABLE_ACTION_REQUIRED", cid)
        result_fields = _string_set(raw.get("result_fields", []), f"{cid}.result_fields")
        channel_schema = _channel_schema(raw.get("channel_schema"), cid)
        caps.append(Capability(cid, requires, provides, cost, action, result_fields, channel_schema))
    return initial, targets, caps


def reachable_effects(initial, caps):
    facts = set(initial)
    changed = True
    while changed:
        changed = False
        for cap in caps:
            if cap.requires.issubset(facts) and not cap.provides.issubset(facts):
                facts.update(cap.provides)
                changed = True
    return frozenset(facts)


def plan_capabilities(problem):
    initial, targets, caps = _normalize(problem)
    if targets.issubset(initial):
        return {
            "status": "SOLVED",
            "plan": [],
            "total_cost": 0.0,
            "expanded_states": 0,
            "initial_facts": sorted(initial),
            "target_effects": sorted(targets),
        }

    reachable = reachable_effects(initial, caps)
    unreachable = sorted(targets - reachable)
    if unreachable:
        raise PlanningFailure("UNREACHABLE_TARGET_EFFECTS", ",".join(unreachable))

    cap_by_id = {c.capability_id: c for c in caps}
    counter = itertools.count()
    frontier = [(0.0, 0, next(counter), initial, tuple())]
    best = {initial: 0.0}
    expanded = 0
    max_expansions = max(1, min(int(problem.get("max_expansions", 5000)), 100000))

    while frontier:
        cost, depth, _, facts, path = heapq.heappop(frontier)
        if cost != best.get(facts):
            continue
        if targets.issubset(facts):
            return {
                "status": "SOLVED",
                "plan": list(path),
                "total_cost": cost,
                "expanded_states": expanded,
                "initial_facts": sorted(initial),
                "target_effects": sorted(targets),
            }
        expanded += 1
        if expanded > max_expansions:
            raise PlanningFailure("MAX_EXPANSIONS_EXCEEDED", str(max_expansions))

        for cap in caps:
            if not cap.requires.issubset(facts):
                continue
            if cap.provides.issubset(facts):
                continue
            new_facts = frozenset(set(facts) | set(cap.provides))
            new_cost = cost + cap.cost
            if new_cost >= best.get(new_facts, float("inf")):
                continue
            best[new_facts] = new_cost
            heapq.heappush(
                frontier,
                (new_cost, depth + 1, next(counter), new_facts, path + (cap.capability_id,))
            )

    raise PlanningFailure("NO_CAPABILITY_PLAN")


def _channel_candidates(store, effect):
    """The ordered channel list for ``effect`` from either store shape.

    Typed composition channels: a store maps an effect to every producer that
    published it, in plan order. Both the legacy single-entry shape (tuple,
    last-writer-wins overwrite) and the new list shape are readable; ``None``
    means no channel exists at all.
    """
    value = store.get(effect)
    if value is None:
        return None
    if isinstance(value, list):
        return list(value)
    return [value]


def _channel_where(where, consumer_id):
    """Validate an optional channel predicate; return (provider_set, format).

    Phase C knows two predicates: ``provider`` (a capability id or a list of
    them) and ``format`` (a declared channel format string, matched against the
    producer's channel_schema for the exact field being bound). An empty or
    unknown-keyed predicate is refused loudly -- never silently ignored.
    """
    if where is None:
        return None
    if not isinstance(where, dict) or not where or set(where) - {"provider", "format"}:
        raise PlanningFailure("CAPABILITY_CHANNEL_INVALID", str(consumer_id))
    provider_set = None
    if "provider" in where:
        provider = where["provider"]
        if isinstance(provider, str) and provider.strip():
            provider_set = {provider.strip()}
        elif (
            isinstance(provider, list)
            and provider
            and all(isinstance(x, str) and x.strip() for x in provider)
        ):
            provider_set = {x.strip() for x in provider}
        else:
            raise PlanningFailure("CAPABILITY_CHANNEL_INVALID", str(consumer_id))
    fmt = None
    if "format" in where:
        fmt = where["format"]
        if not (isinstance(fmt, str) and fmt.strip()):
            raise PlanningFailure("CAPABILITY_CHANNEL_INVALID", str(consumer_id))
        fmt = fmt.strip()
    return provider_set, fmt


def _select_channel(candidates, where, consumer_id, field=""):
    """Pick one (cycle, producer) from an ordered channel list.

    Laws: predicates filter first (provider id set, then declared channel
    format for the field being bound; a producer that declares no schema for
    the field cannot satisfy a format predicate). Zero survivors or no channel
    is the existing missing-provider refusal. More than one survivor UNDER any
    predicate fails closed CAPABILITY_CHANNEL_AMBIGUOUS. Without predicates the
    historical last-writer-wins law of the in-plan store is preserved exactly.
    """
    if not candidates:
        return None
    parsed = _channel_where(where, consumer_id)
    if parsed is None:
        return candidates[-1]
    provider_set, fmt = parsed
    chosen = candidates
    if provider_set is not None:
        chosen = [
            x for x in candidates
            if getattr(x[1], "capability_id", None) in provider_set
        ]
    if fmt is not None:
        chosen = [x for x in chosen if _channel_format(x[1], field) == fmt]
    if len(chosen) > 1:
        raise PlanningFailure(
            "CAPABILITY_CHANNEL_AMBIGUOUS",
            f"{consumer_id}:" + ",".join(sorted(
                str(getattr(x[1], "capability_id", "?")) for x in chosen
            )),
        )
    if not chosen:
        return None
    return chosen[0]


def _resolve_effect_bindings(value, consumer, providers):
    if isinstance(value, dict):
        if set(value.keys()) == {"$effect_result"}:
            spec = value["$effect_result"]
            if not isinstance(spec, dict):
                raise PlanningFailure("INVALID_EFFECT_RESULT_BINDING", consumer.capability_id)
            effect = str(spec.get("effect", "")).strip()
            field = str(spec.get("field", "")).strip()
            if not effect or not field:
                raise PlanningFailure("INVALID_EFFECT_RESULT_BINDING", consumer.capability_id)
            if effect not in consumer.requires:
                raise PlanningFailure(
                    "BINDING_EFFECT_NOT_REQUIRED",
                    f"{consumer.capability_id}:{effect}",
                )
            channel = _channel_candidates(providers, effect)
            provider = _select_channel(
                channel, spec.get("where"), consumer.capability_id, field
            )
            if provider is None:
                raise PlanningFailure(
                    "BINDING_PROVIDER_MISSING",
                    f"{consumer.capability_id}:{effect}",
                )
            cycle, producer = provider
            if field not in producer.result_fields:
                raise PlanningFailure(
                    "BINDING_RESULT_FIELD_UNDECLARED",
                    f"{producer.capability_id}:{field}",
                )
            return {"$result": {"cycle": cycle, "field": field}}
        return {
            key: _resolve_effect_bindings(item, consumer, providers)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_effect_bindings(item, consumer, providers) for item in value]
    return value


def _append_channel(store, effect, endpoint):
    """Publish one more endpoint on ``effect``'s channel, in plan order."""
    channel = store.setdefault(effect, [])
    if not isinstance(channel, list):
        channel = [channel]
        store[effect] = channel
    channel.append(endpoint)


def plan_actions(problem):
    result = plan_capabilities(problem)
    initial, _, caps = _normalize(problem)
    cap_by_id = {c.capability_id: c for c in caps}
    actions = []
    providers = {}
    composition_contract = []
    for cid in result["plan"]:
        cap = cap_by_id[cid]
        action = _resolve_effect_bindings(cap.action, cap, providers)
        action.setdefault("args", {})
        action["capability_id"] = cid
        cycle = len(actions)
        provider_bindings = {}
        requirement_bindings = {}
        for effect in sorted(cap.requires):
            provider = _select_channel(
                _channel_candidates(providers, effect), None, cid
            )
            if provider is not None:
                provider_cycle, producer = provider
                provider_bindings[effect] = {
                    "cycle": provider_cycle,
                    "capability_id": producer.capability_id,
                }
                requirement_bindings[effect] = {
                    "source": "capability",
                    "cycle": provider_cycle,
                    "capability_id": producer.capability_id,
                }
                continue
            if effect in initial:
                requirement_bindings[effect] = {"source": "initial_fact"}
                continue
            raise PlanningFailure(
                "COMPOSITION_REQUIREMENT_SOURCE_MISSING",
                f"{cid}:{effect}",
            )
        composition_contract.append({
            "cycle": cycle,
            "capability_id": cid,
            "requires": sorted(cap.requires),
            "provides": sorted(cap.provides),
            "result_fields": sorted(cap.result_fields),
            "provider_bindings": provider_bindings,
            "requirement_bindings": requirement_bindings,
        })
        actions.append(action)
        for effect in cap.provides:
            _append_channel(providers, effect, (cycle, cap))
    finish_summary = str(problem.get("finish_summary", "CAPABILITY_PLAN_COMPLETE")).strip()
    if not finish_summary:
        raise PlanningFailure("FINISH_SUMMARY_REQUIRED")
    actions.append({
        "type": "finish",
        "args": {"summary": finish_summary},
        "why": "All target effects have an executable minimum-cost capability plan."
    })
    return {
        "planning": result,
        "actions": actions,
        "composition_contract": composition_contract,
    }
