#!/usr/bin/env python3
"""
Instant Learning: Complete System Demonstration

This script demonstrates the complete learning pipeline:
1. Semantic Generalization Engine (neuro-symbolic reasoning)
2. Self-Reflective Learning System (causal understanding)
3. Hierarchical Skill Library (skill extraction)
4. Continuous Learning (accumulation over time)

AUDIT 2026-11-13: it does not prove that. Each of the four tasks is answered by the
same pre-existing AST query tier (PASS__TIER0A_TYPED_PYTHON_AST_QUERY), and the
"learning" is a counter (causal_models 8 -> 16 -> 24) that no later phase reads. The
held-out transfer this script is credited with is 37.52% on one class and 34.15% on
another, with 65 wrong changes at the upper bound. See
WHAT_IS_SOLVED_HERE_AND_WHAT_IS_A_COUNTER_THAT_GOES_UP_20261113_V1.md §3.
The script is kept as a demo; its closing banner is not a measurement.
"""

import sys
sys.path.insert(0, '/home/user/brain')

from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def print_task_result(task, result):
    print(f"\nTask: {task}")
    print(f"  Status: {result.get('status')}")
    print(f"  Pass: {result.get('pass')}")
    print(f"  Answer: {result.get('answer')}")
    
    if result.get('self_reflection'):
        sr = result['self_reflection']
        print(f"  Self-reflection:")
        print(f"    - Causal models: {sr.get('causal_models_built', 0)}")
        print(f"    - Abstract concepts: {sr.get('abstract_concepts', 0)}")
        print(f"    - Transferable principles: {sr.get('transferable_principles', 0)}")

print_section("INSTANT LEARNING: COMPLETE SYSTEM DEMONSTRATION")
print("\nThis demonstrates the system learning from experience once and")
print("applying that learning to new tasks with different concepts.")

# ===========================================================================
# Phase 1: Learn from first task (functions)
# ===========================================================================
print_section("PHASE 1: Learn from First Task")

task1 = "count functions in canonical/runtime/solve_v1.py"
print(f"\nExecuting: {task1}")
result1 = solve_or_learn(task1, learn=True, confinement_admitted=True)
print_task_result(task1, result1)

print("\n✓ System learned from this execution")
print("  - Built causal models")
print("  - Extracted abstract concepts")
print("  - Identified transferable principles")

# ===========================================================================
# Phase 2: Generalize to different concept (if statements)
# ===========================================================================
print_section("PHASE 2: Generalize to Different Concept")

task2 = "count if statements in canonical/swe_kernel/semantic_generalization_engine_v1.py"
print(f"\nExecuting: {task2}")
result2 = solve_or_learn(task2, learn=True, confinement_admitted=True)
print_task_result(task2, result2)

if result2.get('self_reflection'):
    causal_growth = result2['self_reflection']['causal_models_built'] - result1['self_reflection']['causal_models_built']
    print(f"\n✓ System generalized to new concept!")
    print(f"  - Different concept: if_statement (not function)")
    print(f"  - Causal models grew by: {causal_growth}")
    print(f"  - System is accumulating understanding")

# ===========================================================================
# Phase 3: Generalize to yet another concept (classes)
# ===========================================================================
print_section("PHASE 3: Generalize to Yet Another Concept")

task3 = "count classes in canonical/swe_kernel/hierarchical_skill_library_v1.py"
print(f"\nExecuting: {task3}")
result3 = solve_or_learn(task3, learn=True, confinement_admitted=True)
print_task_result(task3, result3)

if result3.get('self_reflection'):
    causal_growth = result3['self_reflection']['causal_models_built'] - result2['self_reflection']['causal_models_built']
    print(f"\n✓ System generalized again!")
    print(f"  - Different concept: class (not function or if_statement)")
    print(f"  - Different file (new environment!)")
    print(f"  - Causal models grew by: {causal_growth}")

# ===========================================================================
# Phase 4: Test more concepts (for loops)
# ===========================================================================
print_section("PHASE 4: Test More Concepts")

task4 = "count for loops in canonical/swe_kernel/self_reflective_learning_system_v1.py"
print(f"\nExecuting: {task4}")
result4 = solve_or_learn(task4, learn=True, confinement_admitted=True)
print_task_result(task4, result4)

if result4.get('self_reflection'):
    causal_growth = result4['self_reflection']['causal_models_built'] - result3['self_reflection']['causal_models_built']
    print(f"\n✓ System continues to learn!")
    print(f"  - Different concept: for_loop")
    print(f"  - Causal models grew by: {causal_growth}")

# ===========================================================================
# Phase 5: Test list operation (different operation)
# ===========================================================================
print_section("PHASE 5: Test Different Operation")

task5 = "list classes in canonical/swe_kernel/operator_semantics_v1.py"
print(f"\nExecuting: {task5}")
result5 = solve_or_learn(task5, learn=True, confinement_admitted=True)
print_task_result(task5, result5)

if result5.get('self_reflection'):
    causal_growth = result5['self_reflection']['causal_models_built'] - result4['self_reflection']['causal_models_built']
    print(f"\n✓ System handles different operations!")
    print(f"  - Different operation: list (not count)")
    print(f"  - Causal models grew by: {causal_growth}")

# ===========================================================================
# Summary
# ===========================================================================
print_section("SUMMARY: INSTANT LEARNING ACHIEVED")

print("\n" + "─" * 80)
print("WHAT THIS ACTUALLY SHOWS")
print("─" * 80)

print("\nFour tasks, one mechanism: each goal is answered by the same pre-existing")
print("typed-AST query tier (PASS__TIER0A_TYPED_PYTHON_AST_QUERY). The 'new concept'")
print("in each phase is a verb that tier already knows.")

print("\nWhat changes between phases is a counter printed by the reflection layer.")
print("No later phase reads anything an earlier phase produced, so nothing here is")
print("learned, retained, or transferred.")

print("\nWhat the held-out instrument measures instead (8 pull requests the operators")
print("were not designed on): 12.19% -> 37.52% coverage on PEP 585 at 76.36%")
print("precision; 8.54% strict / 34.15% assumed on utcnow at 60.61% precision with")
print("65 changes the developers did not make. Two of the eight are at zero.")

print("\nSee WHAT_IS_SOLVED_HERE_AND_WHAT_IS_A_COUNTER_THAT_GOES_UP_20261113_V1.md §3.")
print("\n" + "=" * 80)
print("DEMO OF AST QUERY DISPATCH, NOT A MEASUREMENT OF LEARNING")
print("=" * 80 + "\n")
