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
    if "prompt" in args:
        return {
            "schema": SCHEMA + "_MATCH",
            "matches": match_prompt(str(args.get("prompt") or ""), extract_templates(source)),
            "source_execution": False,
        }
    return manifest(source)
