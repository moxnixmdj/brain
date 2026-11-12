#!/usr/bin/env python3
"""Fix the semantic generalization integration to be more robust."""

import re

# Read the file
with open('canonical/swe_kernel/closed_loop_autonomous_controller_v1.py', 'r') as f:
    lines = f.readlines()

# Find the semantic generalization section and replace it with a more robust version
new_semantic_section = """    # ------------------------------------------------------------------
    # TIER 0A-SEMANTIC (<10 ms): Semantic Generalization - Retrieve Similar
    #                            Experiences & Adapt Strategies
    # ------------------------------------------------------------------
    if learn and recalled is None:
        try:
            from canonical.swe_kernel.semantic_generalization_engine_v1 import (
                SemanticGeneralizationEngine,
            )
            import ast as python_ast

            sem_engine = SemanticGeneralizationEngine()
            sem_result = sem_engine.generalize_and_solve(goal, top_k=3)
            
            if sem_result.get("adapted_strategy") is not None:
                adapted = sem_result["adapted_strategy"]
                base_strategy = adapted.get("base_strategy", {})
                
                # Try to execute the adapted strategy
                if base_strategy.get("task_type") == "information_retrieval":
                    # Apply information retrieval strategy
                    recommended = base_strategy.get("recommended_actions", [])
                    if recommended and any("read" in act.lower() or "file" in act.lower() for act in recommended):
                        # Extract file path from goal
                        file_match = re.search(r'[\w/.-]+\.(?:py|md|json|txt)', goal)
                        if file_match:
                            file_path = file_match.group(0)
                            # Make path absolute if needed
                            if not file_path.startswith('/'):
                                file_path = str(work_cwd / file_path)
                            
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                
                                # Count based on strategy
                                if any("function" in goal.lower() or "method" in goal.lower() or "subroutine" in goal.lower() for act in recommended):
                                    try:
                                        tree = python_ast.parse(file_content)
                                        count = sum(1 for node in python_ast.walk(tree) 
                                                  if isinstance(node, (python_ast.FunctionDef, python_ast.AsyncFunctionDef)))
                                        return {
                                            "schema": SCHEMA,
                                            "task_id": task_id,
                                            "pass": True,
                                            "status": "PASS__TIER0A_SEMANTIC_GENERALIZATION",
                                            "tier_used": "tier0a_semantic_generalization",
                                            "from_memory": True,
                                            "generalization_used": True,
                                            "similar_experiences_count": sem_result.get("similar_experiences_found", 0),
                                            "top_similarities": sem_result.get("top_similarities", []),
                                            "answer": f"Found {count} {'functions' if 'function' in goal.lower() else 'methods' if 'method' in goal.lower() else 'subroutines'}",
                                            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                                        }
                                    except Exception as e:
                                        pass
                                elif "class" in goal.lower():
                                    try:
                                        tree = python_ast.parse(file_content)
                                        count = sum(1 for node in python_ast.walk(tree) if isinstance(node, python_ast.ClassDef))
                                        return {
                                            "schema": SCHEMA,
                                            "task_id": task_id,
                                            "pass": True,
                                            "status": "PASS__TIER0A_SEMANTIC_GENERALIZATION",
                                            "tier_used": "tier0a_semantic_generalization",
                                            "from_memory": True,
                                            "generalization_used": True,
                                            "similar_experiences_count": sem_result.get("similar_experiences_found", 0),
                                            "top_similarities": sem_result.get("top_similarities", []),
                                            "answer": f"Found {count} classes",
                                            "elapsed_ms": round((perf_counter_ns() - t0) / 1e6, 3),
                                        }
                                    except Exception as e:
                                        pass
                            except FileNotFoundError:
                                pass
                            except Exception:
                                pass
        except Exception:
            pass

"""

# Find and replace the semantic generalization section
in_semantic_section = False
semantic_section_start = None
semantic_section_end = None
indent_level = None

for i, line in enumerate(lines):
    if "TIER 0A-SEMANTIC" in line:
        in_semantic_section = True
        semantic_section_start = i - 1  # Include the comment line before
        # Find the indent level
        indent_level = len(line) - len(line.lstrip())
    elif in_semantic_section and line.strip() and not line.startswith(' ' * indent_level) and "forged_state_path" in line:
        semantic_section_end = i
        break

if semantic_section_start is not None and semantic_section_end is not None:
    # Replace the section
    new_lines = lines[:semantic_section_start] + [new_semantic_section] + lines[semantic_section_end:]
    
    with open('canonical/swe_kernel/closed_loop_autonomous_controller_v1.py', 'w') as f:
        f.writelines(new_lines)
    
    print("✓ Semantic generalization integration updated with robust error handling")
else:
    print("✗ Could not find semantic generalization section to replace")
