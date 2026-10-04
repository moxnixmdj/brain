#!/usr/bin/env python3
"""Static compiler for the pinned public LiveBench/IFBench instruction grammar.

The compiler never executes upstream source.  It parses Python AST, binds active
registry entries to checker classes, recovers public build_description templates,
and proves which effective scorer parameters are rendered into visible prompt
text.  Hidden parameters remain explicit and fail closed.

This is a build/verification primitive.  It is intentionally source-text driven
so exact public upstream bytes can be content-addressed independently.
"""
from __future__ import annotations

import ast
import re
import string
from dataclasses import dataclass, asdict
from typing import Any

SCHEMA = "PROJECT_BRAIN_IFBENCH_PUBLIC_DESCRIPTION_GRAMMAR_COMPILER_V1"


class GrammarCompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckerGrammar:
    instruction_id: str
    class_name: str
    templates: tuple[str, ...]
    parameter_keys: tuple[str, ...]
    visible_parameter_keys: tuple[str, ...]
    hidden_parameter_keys: tuple[str, ...]
    placeholder_to_parameter_key: tuple[tuple[str, str], ...]
    visible_complete: bool


def _static_string(node: ast.AST | None, env: dict[str, str] | None = None) -> str | None:
    env = env or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left, env)
        right = _static_string(node.right, env)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                symbol = _expr_symbol(value.value)
                if symbol is None:
                    return None
                parts.append("{" + symbol.rsplit(".", 1)[-1].lstrip("_") + "}")
            else:
                return None
        return "".join(parts)
    return None


def _expr_symbol(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_symbol(node.value)
        return (base + "." if base else "") + node.attr
    if isinstance(node, ast.Call):
        # strip(), lower(), list(), int(), etc. do not change parameter identity
        if isinstance(node.func, ast.Attribute) and node.args == []:
            return _expr_symbol(node.func.value)
        if len(node.args) == 1 and isinstance(node.func, ast.Name) and node.func.id in {
            "str", "int", "float", "list", "tuple", "set"
        }:
            return _expr_symbol(node.args[0])
    if isinstance(node, ast.IfExp):
        a = _expr_symbol(node.body)
        b = _expr_symbol(node.orelse)
        return a if a == b else None
    return None


def _module_string_env(tree: ast.Module) -> dict[str, str]:
    env: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for stmt in tree.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name) or target.id in env:
                continue
            value = _static_string(stmt.value, env)
            if value is not None:
                env[target.id] = value
                changed = True
    return env


def _class_map(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _method(cls: ast.ClassDef, name: str) -> ast.FunctionDef | None:
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node if isinstance(node, ast.FunctionDef) else None
    return None


def _self_attr_symbol(node: ast.AST | None) -> str | None:
    symbol = _expr_symbol(node)
    if symbol and symbol.startswith("self."):
        return symbol
    return None


def _template_assignments(method: ast.FunctionDef) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in ast.walk(method):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        value = _static_string(value_node)
        if value is None:
            continue
        for target in targets:
            symbol = _self_attr_symbol(target)
            if symbol and symbol.rsplit(".", 1)[-1] in {
                "_description_pattern", "_description", "description_pattern", "description"
            }:
                out[symbol] = value
    return out


def _return_templates_and_format_map(
    method: ast.FunctionDef,
    assigned_templates: dict[str, str],
) -> tuple[set[str], dict[str, str]]:
    templates: set[str] = set(assigned_templates.values())
    placeholder_symbol: dict[str, str] = {}

    for node in ast.walk(method):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        direct = _static_string(value)
        if direct is not None:
            templates.add(direct)
            continue
        if isinstance(value, ast.Attribute):
            symbol = _expr_symbol(value)
            if symbol in assigned_templates:
                templates.add(assigned_templates[symbol])
            continue
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            if value.func.attr != "format":
                continue
            base_symbol = _expr_symbol(value.func.value)
            template = assigned_templates.get(base_symbol or "")
            if template is None:
                template = _static_string(value.func.value)
            if template is None:
                continue
            templates.add(template)
            fields = {
                field_name.split(".", 1)[0].split("[", 1)[0]
                for _, field_name, _, _ in string.Formatter().parse(template)
                if field_name
            }
            for kw in value.keywords:
                if kw.arg and kw.arg in fields:
                    symbol = _expr_symbol(kw.value)
                    if symbol:
                        placeholder_symbol[kw.arg] = symbol
    return templates, placeholder_symbol


def _literal_string_list(node: ast.AST | None) -> tuple[str, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[str] = []
    for elt in node.elts:
        if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
            return None
        values.append(elt.value)
    return tuple(values)


def _parameter_keys(cls: ast.ClassDef) -> tuple[str, ...]:
    method = _method(cls, "get_instruction_args_keys")
    if method is not None:
        for node in ast.walk(method):
            if isinstance(node, ast.Return):
                values = _literal_string_list(node.value)
                if values is not None:
                    return values
    getter = _method(cls, "get_instruction_args")
    if getter is not None:
        for node in ast.walk(getter):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                keys: list[str] = []
                for key in node.value.keys:
                    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                        break
                    keys.append(key.value)
                else:
                    return tuple(keys)
    return ()


def _getter_symbols(cls: ast.ClassDef) -> dict[str, str]:
    method = _method(cls, "get_instruction_args")
    if method is None:
        return {}
    for node in ast.walk(method):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        out: dict[str, str] = {}
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                return {}
            symbol = _expr_symbol(value)
            if symbol is None:
                return {}
            out[key.value] = symbol
        return out
    return {}


def _placeholders(templates: set[str]) -> set[str]:
    out: set[str] = set()
    for template in templates:
        for _, field_name, _, _ in string.Formatter().parse(template):
            if field_name:
                out.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return out


def _active_registry(registry_source: str) -> dict[str, str]:
    tree = ast.parse(registry_source)
    env = _module_string_env(tree)
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        if not any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in targets):
            continue
        value = stmt.value
        if not isinstance(value, ast.Dict):
            raise GrammarCompileError("INSTRUCTION_DICT_NOT_LITERAL_DICT")
        out: dict[str, str] = {}
        for key, val in zip(value.keys, value.values):
            instruction_id = _static_string(key, env)
            if instruction_id is None:
                raise GrammarCompileError("INSTRUCTION_ID_NOT_STATIC")
            if not isinstance(val, ast.Attribute):
                raise GrammarCompileError("INSTRUCTION_CLASS_NOT_ATTRIBUTE")
            out[instruction_id] = val.attr
        return out
    raise GrammarCompileError("INSTRUCTION_DICT_NOT_FOUND")


def _compile_checker(instruction_id: str, cls: ast.ClassDef) -> CheckerGrammar:
    build = _method(cls, "build_description")
    if build is None:
        raise GrammarCompileError("BUILD_DESCRIPTION_MISSING:" + cls.name)

    assigned = _template_assignments(build)
    templates, placeholder_symbol = _return_templates_and_format_map(build, assigned)
    placeholders = _placeholders(templates)
    keys = _parameter_keys(cls)
    getter = _getter_symbols(cls)

    # Direct placeholder names count only when they correspond to an effective
    # scorer parameter.  Alias recovery is stronger: if the expression rendered
    # into a placeholder is byte-identical to the expression returned under a
    # get_instruction_args key, the effective parameter is visibly recoverable.
    placeholder_to_key: dict[str, str] = {}
    for placeholder in sorted(placeholders):
        if placeholder in keys:
            placeholder_to_key[placeholder] = placeholder
            continue
        rendered_symbol = placeholder_symbol.get(placeholder)
        if rendered_symbol is None:
            continue
        candidates = sorted(k for k, symbol in getter.items() if symbol == rendered_symbol)
        if len(candidates) == 1:
            placeholder_to_key[placeholder] = candidates[0]

    visible = set(placeholder_to_key.values())
    # Some templates use the canonical key directly but format through an alias
    # expression that our deliberately small symbolic evaluator cannot reduce.
    visible.update(k for k in keys if k in placeholders)
    hidden = tuple(k for k in keys if k not in visible)

    return CheckerGrammar(
        instruction_id=instruction_id,
        class_name=cls.name,
        templates=tuple(sorted(templates)),
        parameter_keys=tuple(keys),
        visible_parameter_keys=tuple(k for k in keys if k in visible),
        hidden_parameter_keys=hidden,
        placeholder_to_parameter_key=tuple(sorted(placeholder_to_key.items())),
        visible_complete=(len(hidden) == 0),
    )


def compile_grammar(instructions_source: str, registry_source: str) -> dict[str, Any]:
    tree = ast.parse(instructions_source)
    classes = _class_map(tree)
    registry = _active_registry(registry_source)
    records: list[CheckerGrammar] = []
    for instruction_id, class_name in sorted(registry.items()):
        cls = classes.get(class_name)
        if cls is None:
            raise GrammarCompileError("ACTIVE_CLASS_MISSING:" + class_name)
        records.append(_compile_checker(instruction_id, cls))

    return {
        "schema": SCHEMA,
        "active_checker_count": len(records),
        "visible_complete_count": sum(1 for x in records if x.visible_complete),
        "hidden_parameter_checker_count": sum(1 for x in records if not x.visible_complete),
        "checkers": [asdict(x) for x in records],
    }


def combine_grammars(*manifests: dict[str, Any]) -> dict[str, Any]:
    checkers: list[dict[str, Any]] = []
    for manifest in manifests:
        if manifest.get("schema") != SCHEMA:
            raise GrammarCompileError("MANIFEST_SCHEMA_MISMATCH")
        checkers.extend(manifest.get("checkers") or [])
    ids = [str(x.get("instruction_id")) for x in checkers]
    if len(ids) != len(set(ids)):
        raise GrammarCompileError("DUPLICATE_INSTRUCTION_ID")
    return {
        "schema": SCHEMA,
        "active_checker_count": len(checkers),
        "visible_complete_count": sum(bool(x.get("visible_complete")) for x in checkers),
        "hidden_parameter_checker_count": sum(not bool(x.get("visible_complete")) for x in checkers),
        "checkers": sorted(checkers, key=lambda x: str(x.get("instruction_id"))),
    }


def _literal_regex(text: str) -> str:
    parts = re.split(r"(\s+)", text)
    return "".join(r"\s+" if part.isspace() else re.escape(part) for part in parts if part)


def template_regex(template: str) -> re.Pattern[str]:
    pieces: list[str] = []
    seen: set[str] = set()
    for literal, field_name, _format_spec, _conversion in string.Formatter().parse(template):
        pieces.append(_literal_regex(literal))
        if not field_name:
            continue
        field = field_name.split(".", 1)[0].split("[", 1)[0]
        if not re.fullmatch(r"[A-Za-z_]\w*", field):
            raise GrammarCompileError("UNSAFE_PLACEHOLDER:" + field)
        if field in seen:
            pieces.append(r"(?P=" + field + ")")
        else:
            pieces.append(r"(?P<" + field + r">.+?)")
            seen.add(field)
    return re.compile("".join(pieces), re.DOTALL)


def recover_visible_bindings(prompt: str, checker: dict[str, Any]) -> list[dict[str, Any]]:
    aliases = dict(checker.get("placeholder_to_parameter_key") or [])
    out: list[dict[str, Any]] = []
    for template in checker.get("templates") or []:
        rx = template_regex(str(template))
        for match in rx.finditer(str(prompt or "")):
            recovered: dict[str, str] = {}
            for placeholder, raw in match.groupdict().items():
                key = aliases.get(placeholder, placeholder)
                recovered[key] = raw
            out.append({
                "instruction_id": checker.get("instruction_id"),
                "class_name": checker.get("class_name"),
                "span": [match.start(), match.end()],
                "matched_text": match.group(0),
                "recovered_parameters": recovered,
                "visible_complete": bool(checker.get("visible_complete")),
                "hidden_parameter_keys": list(checker.get("hidden_parameter_keys") or []),
            })
    return out


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    if "instructions_source" not in args or "registry_source" not in args:
        raise GrammarCompileError("INSTRUCTIONS_AND_REGISTRY_SOURCE_REQUIRED")
    return compile_grammar(
        str(args["instructions_source"]),
        str(args["registry_source"]),
    )
