#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic program synthesis from single demonstration — zero model calls."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SynthesizedProgram:
    script: str
    parameters: tuple
    description: str
    model_calls: int
    network_calls: int


class ProgramSynthesizer:
    """Synthesize shell programs from successful execution traces."""

    def __init__(self):
        self.model_calls = 0
        self.network_calls = 0

    def synthesize(self, steps, terminal_outcome: int, param_names=None) -> SynthesizedProgram:
        if not steps:
            return SynthesizedProgram("", (), "empty_trace", 0, 0)
        if terminal_outcome != 0:
            return SynthesizedProgram("", (), "refused__non_successful_trace", 0, 0)

        param_candidates = {}
        param_counter = 0
        if param_names is None:
            param_names = []

        for step_index, (action, _) in enumerate(steps):
            parts = action.split()
            if not parts:
                continue
            args = parts[1:]
            for arg in args:
                if arg.startswith("-") or arg == "" or arg in self._SHELL_OPERATORS:
                    continue
                if arg not in param_candidates:
                    param_counter += 1
                    if param_counter - 1 < len(param_names):
                        pname = param_names[param_counter - 1]
                    else:
                        pname = "arg" + str(param_counter)
                    param_candidates[arg] = pname

        param_list = list(param_candidates.values())
        seen = set()
        unique_params = []
        for p in param_list:
            if p not in seen:
                seen.add(p)
                unique_params.append(p)
        param_list = unique_params

        script_lines = []
        script_lines.append("#!/bin/sh")
        script_lines.append("# Synthesized program — zero model calls, deterministic")
        script_lines.append("")

        for pname in param_list:
            default_val = None
            for lit, pn in param_candidates.items():
                if pn == pname:
                    default_val = lit
                    break
            if default_val is not None:
                script_lines.append(pname + "=" + repr(default_val))
            else:
                script_lines.append(pname + "=${1:-}")

        script_lines.append("")

        for step_index, (action, _) in enumerate(steps):
            parts = action.split()
            if not parts:
                continue
            cmd = parts[0]
            args = parts[1:]
            new_args = []
            for arg in args:
                if arg in param_candidates:
                    new_args.append("$" + param_candidates[arg])
                else:
                    new_args.append(arg)
            script_lines.append("# Step " + str(step_index) + ": " + cmd + " " + " ".join(new_args))
            script_lines.append(cmd + " " + " ".join(new_args))
            script_lines.append("")

        script = "\n".join(script_lines)
        loop_script = self._detect_loops(steps, param_candidates, script_lines)
        if loop_script:
            script = loop_script

        description = "synthesized_from_" + str(len(steps)) + "_step_trace"
        if param_list:
            description += "_params_" + ",".join(param_list)

        return SynthesizedProgram(script, tuple(param_list), description, 0, 0)

    _SHELL_OPERATORS = frozenset({">", ">>", "<", "|", "&", ";", "(", ")", "2>", "2>>"})

    def _extract_literals(self, action: str) -> dict:
        positions = {}
        parts = action.split()
        for i, part in enumerate(parts):
            if i == 0:
                continue
            if part.startswith("-"):
                continue
            if part in self._SHELL_OPERATORS:
                continue
            positions[i] = part
        return positions

    def _detect_loops(self, steps, param_candidates, script_lines):
        if len(steps) < 2:
            return None
        cmd_groups = {}
        for step_index, (action, _) in enumerate(steps):
            parts = action.split()
            if not parts:
                continue
            cmd = parts[0]
            args = parts[1:]
            if cmd not in cmd_groups:
                cmd_groups[cmd] = []
            cmd_groups[cmd].append((step_index, " ".join(args)))

        for cmd, executions in cmd_groups.items():
            if len(executions) < 2:
                continue
            arg_counts = [len(ex[1].split()) for ex in executions]
            if len(set(arg_counts)) != 1:
                continue
            varying_positions = set()
            for i in range(arg_counts[0]):
                values = set()
                for _, args_str in executions:
                    args = args_str.split()
                    values.add(args[i])
                if len(values) > 1:
                    varying_positions.add(i)
            if len(varying_positions) == 1:
                var_pos = varying_positions.pop()
                target_item = executions[0][1].split()[var_pos]
                loop_var = param_candidates.get(target_item, "item")
                items = " ".join(ex[1].split()[var_pos] for _, ex in executions)
                loop_lines = []
                loop_lines.append("#!/bin/sh")
                loop_lines.append("# Synthesized with loop — zero model calls")
                loop_lines.append("")
                loop_lines.append("for " + loop_var + " in " + items + "; do")
                for step_index, (action, _) in enumerate(steps):
                    parts = action.split()
                    if not parts or parts[0] != cmd:
                        continue
                    args = parts[1:]
                    new_args = []
                    for arg in args:
                        if arg == target_item:
                            new_args.append("$" + loop_var)
                        elif arg in param_candidates:
                            new_args.append("$" + param_candidates[arg])
                        else:
                            new_args.append(arg)
                    loop_lines.append("    " + cmd + " " + " ".join(new_args))
                loop_lines.append("done")
                return "\n".join(loop_lines)
        return None

    def verify_program(self, program, environment_root: pathlib.Path, test_cases) -> dict:
        import subprocess
        import tempfile
        import os

        passed = 0
        failed = 0
        results = []

        for args, expected_rc in test_cases:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                f.write(program.script)
                f.write("\n")
                script_path = f.name
            os.chmod(script_path, 0o755)
            try:
                result = subprocess.run(
                    [script_path] + list(args),
                    cwd=str(environment_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                actual_rc = result.returncode
                ok = actual_rc == expected_rc
                if ok:
                    passed += 1
                else:
                    failed += 1
                results.append({
                    "args": args,
                    "expected_rc": expected_rc,
                    "actual_rc": actual_rc,
                    "passed": ok,
                })
            except subprocess.TimeoutExpired:
                failed += 1
                results.append({
                    "args": args,
                    "expected_rc": expected_rc,
                    "actual_rc": 124,
                    "passed": False,
                    "error": "timeout",
                })
            finally:
                os.unlink(script_path)

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "all_passed": failed == 0,
            "results": results,
            "model_calls": 0,
            "network_calls": 0,
        }


def synthesize_program(steps, terminal_outcome: int, param_names=None) -> dict:
    synth = ProgramSynthesizer()
    program = synth.synthesize(steps, terminal_outcome, param_names)
    return {
        "script": program.script,
        "parameters": program.parameters,
        "description": program.description,
        "model_calls": program.model_calls,
        "network_calls": program.network_calls,
    }
