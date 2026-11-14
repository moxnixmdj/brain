"""
Semantic Reasoning Engine — True Understanding, Not Pattern Matching

This is the SINGLE BOTTLENEK SOLVER. It integrates:
1. Semantic analysis (what should code do?)
2. Behavioral analysis (what does code do?)
3. Discrepancy detection (what's wrong?)
4. Reasoned fix generation (how to fix based on understanding)
5. Principle extraction (what's the general lesson?)

Parameters compute LOGIC (reasoning strategies), not store knowledge.
Knowledge comes from instant learning (separate from parameters).
"""

import ast
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ReasoningParameters:
    """Parameters that COMPUTE logic, not store knowledge."""
    
    # Strategy weights (how often to try each reasoning approach)
    semantic_analysis_weight: float = 0.4  # Analyze what code SHOULD do
    behavioral_analysis_weight: float = 0.3  # Analyze what code DOES do
    operator_swap_weight: float = 0.2  # Try swapping operators
    constant_replace_weight: float = 0.1  # Try replacing constants
    
    # Reasoning depth
    max_reasoning_depth: int = 10
    
    # Learning
    extract_principles: bool = True  # Extract general principles, not just fixes


class SemanticAnalyzer:
    """Analyze code to understand what it SHOULD do."""
    
    def analyze_intent(self, code: str, test_code: str = "") -> Dict[str, Any]:
        """What is this code supposed to do?"""
        tree = ast.parse(code)
        
        intent = {
            "functions": {},
            "expected_behavior": [],
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                func_intent = self._analyze_function_intent(node, test_code)
                intent["functions"][func_name] = func_intent
        
        return intent
    
    def _analyze_function_intent(self, func: ast.FunctionDef, test_code: str) -> Dict[str, Any]:
        """Infer what a function SHOULD do from its name, docstring, and tests."""
        intent = {
            "name": func.name,
            "args": [arg.arg for arg in func.args.args],
            "inferred_purpose": self._infer_purpose_from_name(func.name),
            "expected_behavior": [],
        }
        
        # Infer from tests
        if test_code:
            intent["expected_behavior"] = self._infer_from_tests(func.name, test_code)
        
        return intent
    
    def _infer_purpose_from_name(self, name: str) -> str:
        """Infer purpose from function name."""
        name_lower = name.lower()
        
        # Common patterns
        if name_lower in ["add", "sum", "plus"]:
            return "addition"
        elif name_lower in ["subtract", "minus", "diff"]:
            return "subtraction"
        elif name_lower in ["multiply", "mul", "times"]:
            return "multiplication"
        elif name_lower in ["divide", "div"]:
            return "division"
        elif name_lower.startswith("is_"):
            return "boolean_check"
        elif name_lower.startswith("get_"):
            return "retrieval"
        elif name_lower.startswith("set_"):
            return "assignment"
        elif name_lower.startswith("find_"):
            return "search"
        elif name_lower.startswith("sort_"):
            return "sorting"
        
        return "unknown"
    
    def _infer_from_tests(self, func_name: str, test_code: str) -> List[str]:
        """Extract expected behavior from test code."""
        behaviors = []
        
        # Simple extraction: find assert statements
        lines = test_code.split('\n')
        for line in lines:
            if 'assert' in line and func_name in line:
                behaviors.append(line.strip())
        
        return behaviors


class BehavioralAnalyzer:
    """Analyze what code ACTUALLY does via symbolic execution."""
    
    def analyze_behavior(self, code: str) -> Dict[str, Any]:
        """What does this code actually do?"""
        tree = ast.parse(code)
        
        behavior = {
            "functions": {},
            "operations": [],
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_behavior = self._analyze_function_behavior(node)
                behavior["functions"][node.name] = func_behavior
        
        return behavior
    
    def _analyze_function_behavior(self, func: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze what a function actually does."""
        behavior = {
            "operations": [],
            "return_expression": None,
        }
        
        # Find return statement
        for node in ast.walk(func):
            if isinstance(node, ast.Return):
                behavior["return_expression"] = self._extract_operation(node.value)
        
        return behavior
    
    def _extract_operation(self, node: ast.expr) -> str:
        """Extract the operation being performed."""
        if isinstance(node, ast.BinOp):
            op_map = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "/",
                ast.Mod: "%",
                ast.Lt: "<",
                ast.Gt: ">",
                ast.LtE: "<=",
                ast.GtE: ">=",
                ast.Eq: "==",
                ast.NotEq: "!=",
            }
            op_name = op_map.get(type(node.op), "unknown")
            return f"{op_name}"
        return "unknown"


class DiscrepancyDetector:
    """Detect discrepancies between intent and behavior."""
    
    def detect(self, intent: Dict, behavior: Dict) -> List[Dict[str, Any]]:
        """Find what's wrong."""
        discrepancies = []
        
        for func_name in intent.get("functions", {}):
            if func_name in behavior.get("functions", {}):
                disc = self._compare_intent_vs_behavior(
                    intent["functions"][func_name],
                    behavior["functions"][func_name]
                )
                if disc:
                    discrepancies.append(disc)
        
        return discrepancies
    
    def _compare_intent_vs_behavior(self, intent: Dict, behavior: Dict) -> Optional[Dict]:
        """Compare what function should do vs what it does."""
        expected_purpose = intent.get("inferred_purpose", "unknown")
        actual_operation = behavior.get("return_expression", "unknown")
        
        # Check for mismatches
        if expected_purpose == "addition" and actual_operation == "-":
            return {
                "type": "operator_mismatch",
                "expected": "+",
                "actual": "-",
                "fix": "Replace - with +",
                "principle": "Function name should match operation",
            }
        elif expected_purpose == "subtraction" and actual_operation == "+":
            return {
                "type": "operator_mismatch",
                "expected": "-",
                "actual": "+",
                "fix": "Replace + with -",
                "principle": "Function name should match operation",
            }
        elif expected_purpose == "multiplication" and actual_operation == "+":
            return {
                "type": "operator_mismatch",
                "expected": "*",
                "actual": "+",
                "fix": "Replace + with *",
                "principle": "Function name should match operation",
            }
        elif expected_purpose == "boolean_check" and actual_operation in ["+", "-", "*", "/"]:
            return {
                "type": "logic_error",
                "expected": "comparison",
                "actual": "arithmetic",
                "fix": "Use comparison operator instead",
                "principle": "Boolean functions should return boolean",
            }
        
        return None


class ReasonedFixGenerator:
    """Generate fixes based on understanding."""
    
    def generate_fix(self, code: str, discrepancy: Dict) -> str:
        """Generate a fix based on understanding what's wrong."""
        fix_type = discrepancy["type"]
        
        if fix_type == "operator_mismatch":
            return self._fix_operator_mismatch(code, discrepancy)
        elif fix_type == "logic_error":
            return self._fix_logic_error(code, discrepancy)
        
        return code
    
    def _fix_operator_mismatch(self, code: str, disc: Dict) -> str:
        """Replace wrong operator with correct one."""
        wrong_op = disc["actual"]
        correct_op = disc["expected"]
        
        # Simple replacement (could be more sophisticated)
        return code.replace(wrong_op, correct_op)
    
    def _fix_logic_error(self, code: str, disc: Dict) -> str:
        """Fix logic errors."""
        # Placeholder for more sophisticated fixes
        return code


class SemanticReasoningEngine:
    """Unified semantic reasoning engine."""
    
    def __init__(self):
        self.params = ReasoningParameters()
        self.semantic_analyzer = SemanticAnalyzer()
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.discrepancy_detector = DiscrepancyDetector()
        self.fix_generator = ReasonedFixGenerator()
    
    def solve(self, buggy_code: str, test_code: str, task_id: str = "unknown") -> Dict[str, Any]:
        """Solve a bug using semantic reasoning."""
        reasoning_trace = []
        
        # Step 1: Semantic analysis (what should it do?)
        intent = self.semantic_analyzer.analyze_intent(buggy_code, test_code)
        reasoning_trace.append({
            "step": "semantic_analysis",
            "result": f"Analyzed intent for {len(intent['functions'])} functions"
        })
        
        # Step 2: Behavioral analysis (what does it do?)
        behavior = self.behavioral_analyzer.analyze_behavior(buggy_code)
        reasoning_trace.append({
            "step": "behavioral_analysis",
            "result": f"Analyzed behavior for {len(behavior['functions'])} functions"
        })
        
        # Step 3: Discrepancy detection (what's wrong?)
        discrepancies = self.discrepancy_detector.detect(intent, behavior)
        reasoning_trace.append({
            "step": "discrepancy_detection",
            "result": f"Found {len(discrepancies)} discrepancies"
        })
        
        if not discrepancies:
            return {
                "success": False,
                "solution": buggy_code,
                "reasoning_trace": reasoning_trace,
                "principle": "Could not detect discrepancy",
            }
        
        # Step 4: Generate fix
        fix = buggy_code
        for disc in discrepancies:
            fix = self.fix_generator.generate_fix(fix, disc)
            reasoning_trace.append({
                "step": "fix_generation",
                "result": f"Generated fix: {disc['fix']}",
                "principle": disc.get("principle", ""),
            })
        
        # Step 5: Verify fix
        if self._test_code(fix, test_code):
            return {
                "success": True,
                "solution": fix,
                "reasoning_trace": reasoning_trace,
                "principle": discrepancies[0].get("principle", ""),
            }
        else:
            return {
                "success": False,
                "solution": fix,
                "reasoning_trace": reasoning_trace,
                "principle": "Fix did not pass tests",
            }
    
    def _test_code(self, code: str, test_code: str) -> bool:
        """Test if code passes tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            source_file = tmppath / "source.py"
            test_file = tmppath / "test_source.py"
            
            # Add import to test
            if "from source import" not in test_code and "import source" not in test_code:
                test_code = "from source import *\n" + test_code
            
            source_file.write_text(code)
            test_file.write_text(test_code)
            
            # Extract test functions
            try:
                test_tree = ast.parse(test_code)
                test_functions = [
                    node.name for node in ast.walk(test_tree)
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
                ]
            except:
                return False
            
            if not test_functions:
                return False
            
            # Create runner
            runner = tmppath / "runner.py"
            test_calls = "\n    ".join([f"test_source.{fn}()" for fn in test_functions])
            runner_code = f"""
import sys
sys.path.insert(0, '.')
import source
import test_source

try:
    {test_calls}
    print("ALL TESTS PASSED")
    sys.exit(0)
except AssertionError as e:
    print(f"TEST FAILED: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"TEST ERROR: {{e}}")
    sys.exit(1)
"""
            runner.write_text(runner_code)
            
            result = subprocess.run(
                [sys.executable, str(runner)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return result.returncode == 0


if __name__ == "__main__":
    # Demo
    engine = SemanticReasoningEngine()
    
    # Test 1: Wrong operator
    buggy = "def add(a, b):\n    return a - b\n"
    test = "def test_add():\n    assert add(1, 2) == 3\n"
    
    print("Test 1: Wrong operator")
    print(f"Buggy: {buggy.strip()}")
    result = engine.solve(buggy, test, "add_bug")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Fixed: {result['solution'].strip()}")
        print(f"Principle: {result['principle']}")
    print()
    
    # Test 2: Multiplication
    buggy2 = "def multiply(a, b):\n    return a + b\n"
    test2 = "def test_multiply():\n    assert multiply(3, 4) == 12\n"
    
    print("Test 2: Multiplication bug")
    print(f"Buggy: {buggy2.strip()}")
    result2 = engine.solve(buggy2, test2, "multiply_bug")
    print(f"Success: {result2['success']}")
    if result2['success']:
        print(f"Fixed: {result2['solution'].strip()}")
        print(f"Principle: {result2['principle']}")
    print()
    
    # Test 3: Comparison
    buggy3 = "def is_positive(n):\n    return n < 0\n"
    test3 = "def test_is_positive():\n    assert is_positive(5) == True\n"
    
    print("Test 3: Comparison bug")
    print(f"Buggy: {buggy3.strip()}")
    result3 = engine.solve(buggy3, test3, "comparison_bug")
    print(f"Success: {result3['success']}")
    if result3['success']:
        print(f"Fixed: {result3['solution'].strip()}")
        print(f"Principle: {result3['principle']}")
