#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[5]
BASE=ROOT/"canonical/capabilities/internalized/software_engineering/mini_swe_agent_2_4_6/vendored/src/minisweagent/config/mini.yaml"
SUPER=ROOT/"canonical/capabilities/internalized/software_engineering/superpowers_6_4_2/skills"
EXPECTED_BASE="8b72f71f8092ae805ec43221dbeaeefc2340cd3e"
SKILLS=[["using-superpowers","069d578445805a28b8dacbf70cdf045e1673def0"],["brainstorming","e3f17885f8d5f87d7a92f0469141662b476e1288"],["writing-plans","4cf0275d88d67aa4ef09f4bbca9970ed6ff74a00"],["using-git-worktrees","1381dacb3516b94382dd6ec736ede21ee8ede2b3"],["test-driven-development","46838cc9e893c06259e3bdad0fc2425b36242f15"],["systematic-debugging","095d194ac041502905f15b01d22d294fb94db8b2"],["subagent-driven-development","f7bbf6a01b519807ec00baf5e98522bed33f8834"],["dispatching-parallel-agents","3fa091b348bbe0a18eaa0e17e9092c97f7005cbe"],["requesting-code-review","6d995da5c7d8d6c5a3cc63ddb701427f88ec2021"],["receiving-code-review","950da7b74bf6dbed6b8726d12ddadd65a9f5fda7"],["verification-before-completion","7d45333cc4a49c57a80df6c1fe2fa777a207afbc"],["executing-plans","49077ad961268a840d7dcb5d8c5d06c46fc276ae"],["finishing-a-development-branch","fa8aecaf8813f1b19d19996f7957d1b0121f2d9c"]]

def blob_sha(path):
    p=path.resolve()
    cp=subprocess.run(["git","hash-object",str(p)],cwd=ROOT,text=True,capture_output=True,check=True)
    return cp.stdout.strip()

def checked(path, expected):
    actual=blob_sha(path)
    if actual!=expected:
        raise RuntimeError(f"PIN_MISMATCH:{path}:{actual}:{expected}")
    return path.read_text(encoding="utf-8")

def indent_block(text,n=4):
    prefix=" "*n
    return "\n".join(prefix+line for line in text.splitlines())

def build():
    checked(BASE,EXPECTED_BASE)
    parts=[
      "BRAIN-OWNED COMPOSED CODING CONFIGURATION: mini-SWE-agent 2.4.6 harness + exact Superpowers 6.4.2 discipline.",
      "The following Superpowers skill texts are durable Brain-owned capability configuration. Apply them throughout the task while respecting the mini-SWE one-action execution contract."
    ]
    for name,sha in SKILLS:
        p=SUPER/name/"SKILL.md"
        parts.append(f"\n===== SUPERPOWERS SKILL: {name} =====\n"+checked(p,sha))
    parts.append("""\n===== BRAIN FAIL-CLOSED COMPLETION CONTRACT V3 =====
Do not submit while a known relevant failure remains.
REQUIREMENT TRACEABILITY GATE: every validation requirement, rejection condition, and mandatory field must trace to authoritative task instructions or runtime-visible specification bytes.
ACCEPTANCE COVERAGE GATE: enumerate every explicit acceptance criterion and map it to fresh passing evidence. Any unmapped criterion blocks submission.
RUNTIME ORACLE GATE: if a criterion depends on a concrete runtime engine, protocol implementation, browser, database, compiler, kernel, or other execution substrate, execute that class of runtime oracle or an independently justified behaviorally equivalent oracle before submission.
BROWSER ORACLE RULE: browser, UI, and web-security behavior requires actual browser-backed execution. BROWSER_AVAILABLE=NONE IS A BLOCKER, never passing evidence.
SECURITY INTERACTION RULE: for adversarial/security work, test parser/runtime round trips and composition, batching, or interaction effects when the consumer can combine artifacts.
Before submission, run the strongest task-relevant tests available without reading hidden benchmark verifier logic.
Inspect the final diff and confirm requested behavior, regression preservation, and scope compliance.
SINGLE TERMINAL AUTHORITY: parallel lanes may inspect, implement, and verify, but only the central completion authority may authorize terminal submission after the completion audit.
The public session bridge must enforce BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1 with zero known relevant failures and all acceptance/verification entries PASS.
If verification cannot be completed, preserve the blocker and do not issue COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT.
Only after these checks and terminal authorization pass may the central authority issue exactly: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT""")
    system="\n".join(parts).rstrip()+"\n"
    return "agent:\n  system_template: |\n"+indent_block(system,4)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    out=pathlib.Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(build(),encoding="utf-8")
    print(out)
if __name__=="__main__":
    main()
