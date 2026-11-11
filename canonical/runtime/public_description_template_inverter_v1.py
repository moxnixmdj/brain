#!/usr/bin/env python3
"""Static inverter for public instruction-checker description grammars.

The module converts *source code*, not benchmark rows, into a compact grammar:
for each Instruction subclass it recovers literal self._description_pattern
templates and the {fields} rendered into those templates.  It never imports or
executes the source being analyzed.

This is deliberately benchmark-agnostic.  Its immediate use is the frozen
LiveBench/IFBench public checker source, where it replaces hand-written
per-checker prompt recognizers with one source-derived compiler.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import re
import string
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_PUBLIC_DESCRIPTION_TEMPLATE_INVERTER_V1"


class DescriptionGrammarError(ValueError):
    pass


@dataclass(frozen=True)
class TemplateSpec:
    class_name: str
    template: str
    rendered_fields: tuple[str, ...]
    declared_parameters: tuple[str, ...]
    nonrendered_parameters: tuple[str, ...]


def _static_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left)
        right = _static_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        pieces: list[str] = []
        for item in node.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                pieces.append(item.value)
            elif isinstance(item, ast.FormattedValue) and isinstance(item.value, ast.Name):
                pieces.append("{" + item.value.id + "}")
            else:
                return None
        return "".join(pieces)
    return None


def _is_description_target(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and node.attr == "_description_pattern"
    )


def _declared_parameters(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    names: list[str] = []
    positional = list(fn.args.posonlyargs) + list(fn.args.args)
    for arg in positional + list(fn.args.kwonlyargs):
        if arg.arg != "self":
            names.append(arg.arg)
    return tuple(names)


def _fields(template: str) -> tuple[str, ...]:
    names: list[str] = []
    try:
        parsed = string.Formatter().parse(template)
        for _literal, field, _spec, _conversion in parsed:
            if field is None:
                continue
            # Public checker descriptions use simple named fields.  Reject
            # attribute/index access rather than silently mis-binding it.
            if not re.fullmatch(r"[A-Za-z_]\w*", field):
                raise DescriptionGrammarError("UNSUPPORTED_FORMAT_FIELD:" + field)
            if field not in names:
                names.append(field)
    except ValueError as exc:
        raise DescriptionGrammarError("INVALID_FORMAT_TEMPLATE") from exc
    return tuple(names)


def extract_templates(source: str) -> list[TemplateSpec]:
    """Extract literal description templates from Instruction subclasses."""
    try:
        tree = ast.parse(str(source))
    except SyntaxError as exc:
        raise DescriptionGrammarError("SOURCE_SYNTAX_ERROR") from exc

    out: list[TemplateSpec] = []
    seen: set[tuple[str, str]] = set()

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            isinstance(base, ast.Name) and base.id == "Instruction"
            or isinstance(base, ast.Attribute) and base.attr == "Instruction"
            for base in node.bases
        ):
            continue

        build = next(
            (
                item for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "build_description"
            ),
            None,
        )
        if build is None:
            continue

        declared = _declared_parameters(build)
        patterns: list[str] = []
        for child in ast.walk(build):
            value: ast.AST | None = None
            targets: Iterable[ast.AST] = ()
            if isinstance(child, ast.Assign):
                value = child.value
                targets = child.targets
            elif isinstance(child, ast.AnnAssign):
                value = child.value
                targets = (child.target,)
            if value is None or not any(_is_description_target(t) for t in targets):
                continue
            literal = _static_string(value)
            if literal is not None and literal:
                patterns.append(literal)

        for template in patterns:
            key = (node.name, template)
            if key in seen:
                continue
            seen.add(key)
            rendered = _fields(template)
            out.append(
                TemplateSpec(
                    class_name=node.name,
                    template=template,
                    rendered_fields=rendered,
                    declared_parameters=declared,
                    nonrendered_parameters=tuple(x for x in declared if x not in rendered),
                )
            )
    return out


def audit(source: str, *, expected_classes: Iterable[str] | None = None) -> dict[str, Any]:
    specs = extract_templates(source)
    by_class: dict[str, list[TemplateSpec]] = {}
    for spec in specs:
        by_class.setdefault(spec.class_name, []).append(spec)

    expected = sorted(set(expected_classes or ()))
    missing = [name for name in expected if name not in by_class]
    return {
        "schema": SCHEMA + "_AUDIT",
        "template_count": len(specs),
        "class_count_with_templates": len(by_class),
        "expected_class_count": len(expected),
        "missing_expected_classes": missing,
        "all_expected_classes_covered": bool(expected) and not missing,
        "classes": {
            name: {
                "template_count": len(items),
                "rendered_fields": sorted({f for x in items for f in x.rendered_fields}),
                "declared_parameters": sorted({f for x in items for f in x.declared_parameters}),
                "nonrendered_parameters": sorted({f for x in items for f in x.nonrendered_parameters}),
            }
            for name, items in sorted(by_class.items())
        },
    }


def _template_regex(template: str) -> re.Pattern[str]:
    pieces: list[str] = []
    seen: set[str] = set()
    for literal, field, _spec, _conversion in string.Formatter().parse(template):
        pieces.append(re.escape(literal))
        if field is None:
            continue
        if not re.fullmatch(r"[A-Za-z_]\w*", field):
            raise DescriptionGrammarError("UNSUPPORTED_FORMAT_FIELD:" + field)
        if field in seen:
            pieces.append(f"(?P={field})")
        else:
            # Description parameters are rendered into visible literal context.
            # Non-greedy capture prevents one field from swallowing later text.
            pieces.append(f"(?P<{field}>.+?)")
            seen.add(field)
    return re.compile("".join(pieces), flags=re.DOTALL)


def match_prompt(prompt: str, specs: Iterable[TemplateSpec]) -> list[dict[str, Any]]:
    """Find public description-template instances inside a visible prompt."""
    text = str(prompt or "")
    matches: list[dict[str, Any]] = []
    for spec in specs:
        regex = _template_regex(spec.template)
        for match in regex.finditer(text):
            matches.append(
                {
                    "class_name": spec.class_name,
                    "template": spec.template,
                    "parameters": {
                        key: value for key, value in match.groupdict().items()
                        if value is not None
                    },
                    "nonrendered_parameters": list(spec.nonrendered_parameters),
                    "span": [match.start(), match.end()],
                }
            )
    matches.sort(key=lambda x: (x["span"][0], x["span"][1], x["class_name"]))
    return matches



def _module_string_constants(tree: ast.Module) -> dict[str, str]:
    env: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            name = targets[0].id
            resolved = _static_eval_string(value, env)
            if resolved is not None and env.get(name) != resolved:
                env[name] = resolved
                changed = True
    return env


def _static_eval_string(node: ast.AST, env: dict[str, str]) -> str | None:
    literal = _static_string(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_eval_string(node.left, env)
        right = _static_eval_string(node.right, env)
        if left is not None and right is not None:
            return left + right
    return None


def extract_registry_bindings(registry_source: str) -> dict[str, tuple[str, ...]]:
    """Return Instruction subclass -> active public instruction IDs.

    Handles literal keys and module-level string-prefix concatenation used by
    the frozen legacy IFEval registry. Commented-out entries are absent from the
    AST and therefore cannot silently become active.
    """
    try:
        tree = ast.parse(str(registry_source))
    except SyntaxError as exc:
        raise DescriptionGrammarError("REGISTRY_SOURCE_SYNTAX_ERROR") from exc
    env = _module_string_constants(tree)
    pairs: list[tuple[str, str]] = []
    found = False
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if not any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in targets):
            continue
        found = True
        if not isinstance(node.value, ast.Dict):
            raise DescriptionGrammarError("INSTRUCTION_DICT_NOT_LITERAL_DICT")
        for key_node, value_node in zip(node.value.keys, node.value.values):
            if key_node is None:
                raise DescriptionGrammarError("REGISTRY_DICT_UNPACK_UNSUPPORTED")
            instruction_id = _static_eval_string(key_node, env)
            if instruction_id is None:
                raise DescriptionGrammarError("REGISTRY_ID_NOT_STATIC")
            if not (
                isinstance(value_node, ast.Attribute)
                and isinstance(value_node.value, ast.Name)
                and value_node.value.id == "instructions"
            ):
                raise DescriptionGrammarError("REGISTRY_VALUE_NOT_INSTRUCTION_CLASS")
            pairs.append((value_node.attr, instruction_id))
    if not found:
        raise DescriptionGrammarError("INSTRUCTION_DICT_NOT_FOUND")
    by_class: dict[str, list[str]] = {}
    for class_name, instruction_id in pairs:
        if instruction_id not in by_class.setdefault(class_name, []):
            by_class[class_name].append(instruction_id)
    return {name: tuple(ids) for name, ids in sorted(by_class.items())}


def recognize(
    prompt: str,
    instruction_source: str,
    registry_source: str,
) -> list[dict[str, Any]]:
    """Recognize public instruction IDs and visible rendered parameters.

    This composes the source-derived description grammar with the active public
    registry. Runtime input is still only visible prompt text plus precommitted
    public source bytes. No benchmark kwargs or case IDs are required.
    """
    bindings = extract_registry_bindings(registry_source)
    matches = match_prompt(str(prompt or ""), extract_templates(instruction_source))
    out: list[dict[str, Any]] = []
    for match in matches:
        class_name = match["class_name"]
        ids = bindings.get(class_name, ())
        for instruction_id in ids:
            out.append({
                **match,
                "instruction_id": instruction_id,
                "registry_binding_proved": True,
            })
    out.sort(key=lambda x: (x["span"][0], x["span"][1], x["instruction_id"]))
    return out


def audit_registered_coverage(
    instruction_source: str,
    registry_source: str,
) -> dict[str, Any]:
    bindings = extract_registry_bindings(registry_source)
    report = audit(instruction_source, expected_classes=bindings.keys())
    return {
        "schema": SCHEMA + "_REGISTERED_COVERAGE_AUDIT",
        "active_instruction_id_count": sum(len(ids) for ids in bindings.values()),
        "active_instruction_class_count": len(bindings),
        "all_active_classes_have_description_templates": report["all_expected_classes_covered"],
        "missing_active_classes": report["missing_expected_classes"],
        "bindings": {k: list(v) for k, v in bindings.items()},
        "source_execution": False,
    }

def manifest(source: str) -> dict[str, Any]:
    specs = extract_templates(source)
    return {
        "schema": SCHEMA + "_MANIFEST",
        "source_execution": False,
        "template_count": len(specs),
        "templates": [asdict(x) for x in specs],
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    source = str(args.get("source") or "")
    if not source:
        raise DescriptionGrammarError("SOURCE_REQUIRED")
    registry_source = str(args.get("registry_source") or "")
    if "prompt" in args and registry_source:
        return {
            "schema": SCHEMA + "_RECOGNITION",
            "matches": recognize(str(args.get("prompt") or ""), source, registry_source),
            "source_execution": False,
        }
    if registry_source:
        return audit_registered_coverage(source, registry_source)
    if "prompt" in args:
        return {
            "schema": SCHEMA + "_MATCH",
            "matches": match_prompt(str(args.get("prompt") or ""), extract_templates(source)),
            "source_execution": False,
        }
    return manifest(source)
