#!/usr/bin/env python3
"""A fresh-process, zero-model interpreter for declarative relation grammars.

Iteration 6 carried relation *texts* but still hard-coded one producer-side term family
(`holder_shape`). This module is the minimal boundary that lets a different grammar travel:
the external store contains a declarative grammar descriptor, not Python predicates, not a
model, and not world facts; this interpreter is Brain-owned generic machinery. It reads the
descriptor and a raw executor log, recomputes `content:first_relocation_source`, recomputes
every named term and the typed goal verdict from THAT machine's own states/commands, and
refuses unknown or mutated descriptors.

The CLI deliberately imports only the Python standard library. It can be run with
`python3 -I -B <this file> --store ... --raw-log ...` from a fresh process and a different
working directory. That is transport verification, NOT independent identity verification.
No independent verifier exists in this producer sandbox and none is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_RECOMPUTED_RELATION_GRAMMAR_V1"
STORE_SCHEMA = "BRAIN_DECLARATIVE_GRAMMAR_RELATION_STORE_V1"
GRAMMAR_SCHEMA = "BRAIN_DECLARATIVE_RELATION_GRAMMAR_V1"
RAW_LOG_SCHEMA = "BRAIN_EXECUTED_RAW_LOG_V1"
POINTER_TEXTS = frozenset({"content:first_relocation_source"})
OLD_GRAMMAR_FAMILY = "computed_deictic_holder_shape_v1"

TERM_KINDS = frozenset({
    "pointer_count_initial_ge",
    "pointer_count_final_eq",
    "pointer_count_series_monotone",
    "pointer_count_max_le",
    "pointer_count_increases_eq",
    "pointer_count_all_ge",
    "pointer_count_any_ge",
    "state_cardinality_series_monotone",
    "state_cardinality_final_eq",
    "state_cardinality_initial_eq",
})
GOAL_KINDS = frozenset({"pointer_count_final_eq_and_max_le"})
FORBIDDEN_CODE_KEYS = frozenset({
    "lambda", "exec", "eval", "code", "callable", "imports", "module",
    "function", "source_code", "globals", "locals", "__class__",
})
FORBIDDEN_CODE_TOKENS = ("lambda ", "import ", "exec(", "eval(", "__import__", "subprocess")
FORBIDDEN_IMPORT_PREFIXES = (
    "urllib", "requests", "httpx", "socket", "http", "openai", "anthropic",
    "transformers", "torch", "tensorflow", "boto3", "canonical", "intake",
    "the_content_is_not_a_literal_v1", "the_holder_is_not_the_identity_v1",
)
TERM_NAME_RE = re.compile(r"^[A-Za-z0-9_=<>!+-]+$")
PREFIX_RE = re.compile(r"^[a-z][a-z0-9_]*$")
LITERAL_RE_TEMPLATE = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"


class GrammarRefusal(ValueError):
    """A deterministic, typed refusal; never an exception that guesses."""


def canonical_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def bytes_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def literal_scan(text: str, literal: str) -> bool:
    return re.search(LITERAL_RE_TEMPLATE.format(re.escape(literal)), text) is not None


def _field(record: Any, name: str) -> Any:
    if isinstance(record, Mapping):
        if name not in record:
            raise GrammarRefusal("MALFORMED_RECORD_MISSING_FIELD:" + name)
        return record[name]
    if not hasattr(record, name):
        raise GrammarRefusal("MALFORMED_RECORD_MISSING_FIELD:" + name)
    return getattr(record, name)


def record_trace(record: Any) -> Sequence[Sequence[Sequence[str]]]:
    return _field(record, "trace")


def record_frames(record: Any) -> Sequence[Sequence[str]]:
    return _field(record, "frames")


def relocation_source(command: Sequence[str]) -> str | None:
    """Return the source operand of a real mv/cp command from an executor call log."""
    frame = tuple(str(part) for part in command)
    if not frame or pathlib.PurePosixPath(frame[0]).name not in {"mv", "cp"}:
        return None
    positional = [part for part in frame[1:] if not part.startswith("-")]
    return positional[0] if len(positional) >= 2 else None


def content_pointer(record: Any) -> str | None:
    """Compute the deictic pointer from initial states, pre-command states and call log."""
    trace = record_trace(record)
    frames = record_frames(record)
    if not trace:
        raise GrammarRefusal("MALFORMED_RECORD_EMPTY_TRACE")
    initial = {str(ident): str(value) for ident, value in trace[0]}
    for index, command in enumerate(frames):
        source = relocation_source(command)
        if source is None:
            continue
        if source in initial:
            return initial[source]
        if index >= len(trace):
            raise GrammarRefusal("MALFORMED_RECORD_FRAME_WITHOUT_PREVIOUS_STATE")
        before = {str(ident): str(value) for ident, value in trace[index]}
        if source in before:
            return before[source]
    return None


def pointer_counts(record: Any) -> list[int]:
    content = content_pointer(record)
    if content is None:
        raise GrammarRefusal("CONTENT_POINTER_NOT_RECOMPUTED")
    return [sum(1 for _ident, value in state if str(value) == content)
            for state in record_trace(record)]


def state_cardinalities(record: Any) -> list[int]:
    return [len(state) for state in record_trace(record)]


def _series_monotone(series: Sequence[int]) -> bool:
    return all(series[index + 1] >= series[index] for index in range(len(series) - 1))


def _int_param(term: Mapping[str, Any], name: str = "value") -> int:
    value = term.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise GrammarRefusal("TERM_PARAMETER_NOT_INT:" + name)
    return value


def evaluate_term(term: Mapping[str, Any], record: Any) -> bool:
    """Evaluate one finite declarative term primitive on one raw executed record."""
    kind = str(term.get("kind") or "")
    counts = pointer_counts(record)
    if kind == "pointer_count_initial_ge":
        return bool(counts) and counts[0] >= _int_param(term)
    if kind == "pointer_count_final_eq":
        return bool(counts) and counts[-1] == _int_param(term)
    if kind == "pointer_count_series_monotone":
        return _series_monotone(counts)
    if kind == "pointer_count_max_le":
        return max(counts or [0]) <= _int_param(term)
    if kind == "pointer_count_increases_eq":
        increases = sum(1 for i in range(len(counts) - 1) if counts[i + 1] > counts[i])
        return increases == _int_param(term)
    if kind == "pointer_count_all_ge":
        return bool(counts) and all(value >= _int_param(term) for value in counts)
    if kind == "pointer_count_any_ge":
        return any(value >= _int_param(term) for value in counts)
    if kind == "state_cardinality_series_monotone":
        return _series_monotone(state_cardinalities(record))
    if kind == "state_cardinality_final_eq":
        return state_cardinalities(record)[-1] == _int_param(term)
    if kind == "state_cardinality_initial_eq":
        return state_cardinalities(record)[0] == _int_param(term)
    raise GrammarRefusal("UNKNOWN_GRAMMAR_PRIMITIVE:" + kind)


def goal_verdict(grammar: Mapping[str, Any], record: Any) -> bool:
    """Recompute the typed goal verdict from the raw record; never read a stored label."""
    goal = grammar.get("goal")
    if not isinstance(goal, Mapping):
        raise GrammarRefusal("GOAL_DESCRIPTOR_MISSING")
    kind = str(goal.get("kind") or "")
    if kind not in GOAL_KINDS:
        raise GrammarRefusal("UNKNOWN_GOAL_PRIMITIVE:" + kind)
    counts = pointer_counts(record)
    final_eq = goal.get("final_eq")
    max_le = goal.get("max_le")
    if isinstance(final_eq, bool) or not isinstance(final_eq, int):
        raise GrammarRefusal("GOAL_PARAMETER_NOT_INT:final_eq")
    if isinstance(max_le, bool) or not isinstance(max_le, int):
        raise GrammarRefusal("GOAL_PARAMETER_NOT_INT:max_le")
    return bool(counts) and counts[-1] == final_eq and max(counts) <= max_le


def term_text(grammar: Mapping[str, Any], term: Mapping[str, Any]) -> str:
    return f"{grammar['term_prefix']}:{term['name']}[{grammar['pointer']['text']}]"


def term_texts(grammar: Mapping[str, Any]) -> list[str]:
    return [term_text(grammar, term) for term in grammar["terms"]]


def term_predicates(grammar: Mapping[str, Any]) -> dict[str, Callable[[Any], bool]]:
    out: dict[str, Callable[[Any], bool]] = {}
    for term in grammar["terms"]:
        text = term_text(grammar, term)
        out[text] = lambda record, entry=term: evaluate_term(entry, record)
    return out


def _contains_forbidden_key(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if str(key) in FORBIDDEN_CODE_KEYS:
                return True
            if _contains_forbidden_key(value):
                return True
    elif isinstance(obj, list):
        return any(_contains_forbidden_key(item) for item in obj)
    elif isinstance(obj, str):
        lowered = obj.lower()
        return any(token in lowered for token in FORBIDDEN_CODE_TOKENS)
    return False


def _grammar_errors(grammar: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(grammar, Mapping):
        return ["GRAMMAR_DESCRIPTOR_MISSING"]
    if grammar.get("schema") != GRAMMAR_SCHEMA:
        errors.append("GRAMMAR_SCHEMA_MISMATCH")
    family = str(grammar.get("family") or "")
    if not family or family == OLD_GRAMMAR_FAMILY:
        errors.append("GRAMMAR_FAMILY_UNCHANGED")
    prefix = str(grammar.get("term_prefix") or "")
    if not PREFIX_RE.match(prefix):
        errors.append("GRAMMAR_PREFIX_INVALID")
    pointer = grammar.get("pointer")
    if not isinstance(pointer, Mapping) or pointer.get("text") not in POINTER_TEXTS:
        errors.append("GRAMMAR_POINTER_NOT_ALLOWLISTED")
    elif pointer.get("source") != "executor_call_log_and_machine_readings":
        errors.append("GRAMMAR_POINTER_SOURCE_INVALID")
    terms = grammar.get("terms")
    if not isinstance(terms, list) or not terms or len(terms) > 32:
        errors.append("GRAMMAR_TERMS_INVALID")
    else:
        seen: set[str] = set()
        for index, term in enumerate(terms):
            if not isinstance(term, Mapping):
                errors.append(f"GRAMMAR_TERM_NOT_OBJECT:{index}")
                continue
            allowed = {"name", "kind", "value"}
            extra = sorted(set(map(str, term.keys())) - allowed)
            if extra:
                errors.append("GRAMMAR_TERM_UNEXPECTED_KEYS:" + ",".join(extra))
            name = str(term.get("name") or "")
            if not TERM_NAME_RE.match(name):
                errors.append(f"GRAMMAR_TERM_NAME_INVALID:{index}")
            elif name in seen:
                errors.append("GRAMMAR_TERM_NAME_DUPLICATE:" + name)
            else:
                seen.add(name)
            kind = str(term.get("kind") or "")
            if kind not in TERM_KINDS:
                errors.append("UNKNOWN_GRAMMAR_PRIMITIVE:" + kind)
            value = term.get("value")
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"GRAMMAR_TERM_VALUE_INVALID:{index}")
    goal = grammar.get("goal")
    if not isinstance(goal, Mapping):
        errors.append("GOAL_DESCRIPTOR_MISSING")
    else:
        allowed = {"kind", "final_eq", "max_le"}
        extra = sorted(set(map(str, goal.keys())) - allowed)
        if extra:
            errors.append("GOAL_DESCRIPTOR_UNEXPECTED_KEYS:" + ",".join(extra))
        if str(goal.get("kind") or "") not in GOAL_KINDS:
            errors.append("UNKNOWN_GOAL_PRIMITIVE:" + str(goal.get("kind") or ""))
        for key in ("final_eq", "max_le"):
            value = goal.get(key)
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append("GOAL_PARAMETER_NOT_INT:" + key)
    if _contains_forbidden_key(grammar):
        errors.append("EXECUTABLE_CODE_MARKER_IN_GRAMMAR")
    return sorted(set(errors))


def _machine_literals(raw_log: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    identities: set[str] = set()
    contents: set[str] = set()
    for machine in raw_log.get("machines", []):
        for record in machine.get("records", []):
            for state in record.get("trace", []):
                for ident, value in state:
                    identities.add(str(ident))
                    contents.add(str(value))
    return sorted(identities), sorted(contents)


def _store_validation_errors(store: Any, raw_log: Mapping[str, Any] | None,
                             raw_log_bytes: bytes | None,
                             *, check_raw_log_hash: bool) -> list[str]:
    if not isinstance(store, Mapping):
        return ["STORE_OBJECT_INVALID"]
    if store.get("schema") != STORE_SCHEMA:
        return ["STORE_SCHEMA_MISMATCH"]
    grammar = store.get("grammar")
    grammar_errors = _grammar_errors(grammar)
    if grammar_errors:
        return grammar_errors
    evidence = store.get("evidence")
    if not isinstance(evidence, Mapping):
        return ["STORE_EVIDENCE_MISSING"]
    if evidence.get("grammar_sha256") != canonical_hash(grammar):
        return ["GRAMMAR_DESCRIPTOR_HASH_MISMATCH"]
    if check_raw_log_hash:
        if raw_log_bytes is None:
            return ["RAW_LOG_BYTES_MISSING"]
        if evidence.get("raw_log_sha256") != bytes_sha256(raw_log_bytes):
            return ["RAW_LOG_HASH_MISMATCH"]
    relation = store.get("relation")
    if not isinstance(relation, Mapping) or relation.get("operator") != "and":
        return ["RELATION_DESCRIPTOR_INVALID"]
    texts = relation.get("texts")
    if not isinstance(texts, list) or not texts or any(not isinstance(text, str) for text in texts):
        return ["RELATION_TEXTS_INVALID"]
    allowed_texts = set(term_texts(grammar))
    missing = sorted(set(texts) - allowed_texts)
    if missing:
        return ["RELATION_TEXTS_NOT_IN_GRAMMAR:" + ",".join(missing)]
    if store.get("term_family") != grammar.get("family"):
        return ["TERM_FAMILY_MISMATCH"]
    pointer = store.get("content_pointer")
    if not isinstance(pointer, Mapping) or pointer.get("text") != grammar["pointer"]["text"]:
        return ["CONTENT_POINTER_MISMATCH"]
    if any("holder_shape:" in text for text in texts):
        return ["OLD_HOLDER_GRAMMAR_IN_RELATION"]
    if store.get("identity_literals") != [] or store.get("content_literals") != []:
        return ["STORE_LITERAL_LISTS_NOT_EMPTY"]
    if evidence.get("independent_verification_completed") is not False:
        return ["INDEPENDENT_VERIFICATION_MUST_NOT_BE_CLAIMED"]
    cost = store.get("cost")
    if not isinstance(cost, Mapping) or any(cost.get(key) != 0 for key in
            ("model_calls", "parameters_stored", "network_calls_at_run_time")):
        return ["NONZERO_MODEL_PARAMETER_OR_NETWORK_COST"]
    if raw_log is not None:
        identities, contents = _machine_literals(raw_log)
        store_text = json.dumps(store, sort_keys=True, ensure_ascii=False)
        leaks = [literal for literal in identities + contents if literal_scan(store_text, literal)]
        if leaks:
            return ["MACHINE_LITERAL_IN_STORE:" + ",".join(sorted(set(leaks)))]
    return []


def predict_from_store(store_or_path: Any, records: Sequence[Any]) -> dict[str, Any]:
    """Replay a validated store on raw records; recompute all terms and the typed goal."""
    if isinstance(store_or_path, (str, pathlib.Path)):
        path = pathlib.Path(store_or_path)
        if not path.exists():
            return {"status": "REFUSED__NO_RELATION", "abstentions": len(records)}
        try:
            store = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"status": "REFUSED__MALFORMED_STORE", "abstentions": len(records)}
    else:
        store = store_or_path
    errors = _store_validation_errors(store, None, None, check_raw_log_hash=False)
    if errors:
        if errors == ["GRAMMAR_DESCRIPTOR_HASH_MISMATCH"]:
            return {"status": "REFUSED__GRAMMAR_DESCRIPTOR_HASH_MISMATCH",
                    "abstentions": len(records), "errors": errors}
        if any(error.startswith("UNKNOWN_GRAMMAR_PRIMITIVE") for error in errors):
            return {"status": "REFUSED__UNKNOWN_GRAMMAR_PRIMITIVE",
                    "abstentions": len(records), "errors": errors}
        if errors == ["STORE_SCHEMA_MISMATCH"]:
            return {"status": "REFUSED__STORE_SCHEMA_MISMATCH",
                    "abstentions": len(records), "errors": errors}
        return {"status": "REFUSED__STORE_VALIDATION_FAILED",
                "abstentions": len(records), "errors": errors}
    grammar = store["grammar"]
    predicates = term_predicates(grammar)
    wanted = list(store["relation"]["texts"])
    pointer_values: list[str] = []
    for index, record in enumerate(records):
        pointer = content_pointer(record)
        if pointer is None:
            return {"status": "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED",
                    "runs": len(records), "abstentions": len(records),
                    "pointer_failures": len(records), "first_failure_index": index}
        pointer_values.append(pointer)
        for predicate in predicates.values():
            predicate(record)
    predictions: list[bool] = []
    verdicts: list[bool] = []
    for record in records:
        predictions.append(all(predicates[text](record) for text in wanted))
        verdicts.append(goal_verdict(grammar, record))
    false_accepts = sum(1 for predicted, verdict in zip(predictions, verdicts)
                        if predicted and not verdict)
    false_rejects = sum(1 for predicted, verdict in zip(predictions, verdicts)
                        if not predicted and verdict)
    return {
        "status": "PREDICTED", "runs": len(records), "abstentions": 0,
        "false_accepts": false_accepts, "false_rejects": false_rejects,
        "texts": wanted, "terms_recomputed_from_this_machine": len(predicates),
        "term_evaluations": len(records) * len(predicates),
        "pointer_contents_recomputed_from_this_machine": sorted(set(pointer_values)),
        "predictions": predictions, "goal_verdicts": verdicts,
    }


def verify_store_and_raw_log(store: Any, raw_log: Any, *, raw_log_bytes: bytes) -> dict[str, Any]:
    """Fresh-process verification: hash, descriptor, raw log, all terms, all machines."""
    if not isinstance(raw_log, Mapping) or raw_log.get("schema") != RAW_LOG_SCHEMA:
        return {"status": "REFUSED__RAW_LOG_SCHEMA_MISMATCH",
                "errors": ["RAW_LOG_SCHEMA_MISMATCH"], "abstentions": 0}
    errors = _store_validation_errors(store, raw_log, raw_log_bytes, check_raw_log_hash=True)
    if errors:
        if errors == ["GRAMMAR_DESCRIPTOR_HASH_MISMATCH"]:
            status = "REFUSED__GRAMMAR_DESCRIPTOR_HASH_MISMATCH"
        elif errors == ["RAW_LOG_HASH_MISMATCH"]:
            status = "REFUSED__RAW_LOG_HASH_MISMATCH"
        elif errors == ["STORE_SCHEMA_MISMATCH"]:
            status = "REFUSED__STORE_SCHEMA_MISMATCH"
        elif any(error.startswith("UNKNOWN_GRAMMAR_PRIMITIVE") for error in errors):
            status = "REFUSED__UNKNOWN_GRAMMAR_PRIMITIVE"
        else:
            status = "REFUSED__STORE_VALIDATION_FAILED"
        return {"status": status, "errors": errors, "abstentions": 0}
    grammar = store["grammar"]
    predicates = term_predicates(grammar)
    wanted = list(store["relation"]["texts"])
    machines = raw_log.get("machines")
    if not isinstance(machines, list) or not machines:
        return {"status": "REFUSED__RAW_LOG_MACHINES_MISSING", "errors": ["RAW_LOG_MACHINES_MISSING"]}
    reports: list[dict[str, Any]] = []
    normal_machines = 0
    pointerless_controls = 0
    total_false_accepts = 0
    total_false_rejects = 0
    for machine in machines:
        if not isinstance(machine, Mapping):
            return {"status": "REFUSED__RAW_LOG_MACHINE_INVALID", "errors": ["RAW_LOG_MACHINE_INVALID"]}
        name = str(machine.get("name") or "UNNAMED")
        control = str(machine.get("control") or "")
        records = machine.get("records")
        if not isinstance(records, list) or not records:
            return {"status": "REFUSED__RAW_LOG_RECORDS_MISSING",
                    "errors": ["RAW_LOG_RECORDS_MISSING:" + name]}
        if any("expected" in record if isinstance(record, Mapping) else False for record in records):
            return {"status": "REFUSED__RAW_LOG_HAS_STORED_VERDICTS",
                    "errors": ["RAW_LOG_HAS_STORED_VERDICTS:" + name]}
        pointers = [content_pointer(record) for record in records]
        if control == "POINTERLESS":
            if any(pointer is not None for pointer in pointers):
                return {"status": "REFUSED__POINTERLESS_CONTROL_HAS_POINTER",
                        "errors": ["POINTERLESS_CONTROL_HAS_POINTER:" + name]}
            pointerless_controls += 1
            reports.append({
                "name": name, "control": control,
                "status": "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED",
                "runs": len(records), "abstentions": len(records),
                "pointer_failures": len(records),
                "pointer_contents_recomputed_from_this_machine": [],
                "terms_recomputed_from_this_machine": 0,
            })
            continue
        if any(pointer is None for pointer in pointers):
            return {"status": "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED",
                    "errors": ["CONTENT_POINTER_NOT_RECOMPUTED:" + name],
                    "abstentions": sum(pointer is None for pointer in pointers)}
        normal_machines += 1
        predictions: list[bool] = []
        verdicts: list[bool] = []
        term_evaluations = 0
        for record in records:
            for predicate in predicates.values():
                predicate(record)
                term_evaluations += 1
            predictions.append(all(predicates[text](record) for text in wanted))
            verdicts.append(goal_verdict(grammar, record))
        false_accepts = sum(1 for predicted, verdict in zip(predictions, verdicts)
                            if predicted and not verdict)
        false_rejects = sum(1 for predicted, verdict in zip(predictions, verdicts)
                            if not predicted and verdict)
        total_false_accepts += false_accepts
        total_false_rejects += false_rejects
        reports.append({
            "name": name, "status": "PREDICTED", "runs": len(records), "abstentions": 0,
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "pointer_contents_recomputed_from_this_machine": sorted({p for p in pointers if p is not None}),
            "terms_recomputed_from_this_machine": len(predicates),
            "term_evaluations": term_evaluations,
        })
    if not normal_machines:
        return {"status": "REFUSED__NO_NORMAL_MACHINE", "errors": ["NO_NORMAL_MACHINE"],
                "machines": reports}
    if not pointerless_controls:
        return {"status": "REFUSED__NO_POINTERLESS_CONTROL", "errors": ["NO_POINTERLESS_CONTROL"],
                "machines": reports}
    if total_false_accepts or total_false_rejects:
        return {"status": "REFUSED__PREDICTION_MISMATCH",
                "errors": ["PREDICTION_MISMATCH"],
                "false_accepts": total_false_accepts,
                "false_rejects": total_false_rejects, "machines": reports}
    return {
        "status": "PASS", "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_FRESH_PROCESS",
        "independent_verification_completed": False,
        "grammar_family": grammar["family"], "grammar_sha256": canonical_hash(grammar),
        "raw_log_sha256": bytes_sha256(raw_log_bytes),
        "terms_recomputed_per_machine": len(predicates),
        "normal_machines": normal_machines,
        "pointerless_controls": pointerless_controls,
        "false_accepts": 0, "false_rejects": 0,
        "machines": reports,
    }


def _load_json(path: pathlib.Path) -> tuple[Any | None, bytes | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, None, "NO_FILE"
    try:
        return json.loads(raw.decode("utf-8")), raw, None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw, "MALFORMED_JSON"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=pathlib.Path, required=True)
    parser.add_argument("--raw-log", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    store, _store_bytes, store_error = _load_json(options.store)
    if store_error == "NO_FILE":
        print(json.dumps({"status": "REFUSED__NO_STORE", "errors": ["NO_STORE"]}, indent=1))
        return 2
    if store_error == "MALFORMED_JSON":
        print(json.dumps({"status": "REFUSED__MALFORMED_JSON", "errors": ["MALFORMED_STORE"]}, indent=1))
        return 2
    raw_log, raw_log_bytes, raw_log_error = _load_json(options.raw_log)
    if raw_log_error == "NO_FILE":
        print(json.dumps({"status": "REFUSED__NO_RAW_LOG", "errors": ["NO_RAW_LOG"]}, indent=1))
        return 2
    if raw_log_error == "MALFORMED_JSON":
        print(json.dumps({"status": "REFUSED__MALFORMED_RAW_LOG", "errors": ["MALFORMED_RAW_LOG"]}, indent=1))
        return 2
    assert raw_log_bytes is not None
    result = verify_store_and_raw_log(store, raw_log, raw_log_bytes=raw_log_bytes)
    result["python_pid"] = os.getpid()
    result["python_isolated_mode"] = bool(sys.flags.isolated)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
