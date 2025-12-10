"""Math tool functions."""

import ast
import logging
import math
import random
from typing import Any, Dict


logger = logging.getLogger("math_tools")

# Allowed names for safe evaluation
_ALLOWED_NAMES = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "int": int,
    "float": float,
    # Math module functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
    # Random module functions
    "random": random.random,
    "randint": random.randint,
}


def calculator(python_expression: str) -> Dict[str, Any]:
    """Calculate the result of a mathematical Python expression.

    This tool evaluates mathematical expressions safely using a restricted
    set of allowed functions from math and random modules.

    Args:
        python_expression: A valid Python mathematical expression.
            Available functions: sin, cos, tan, sqrt, log, log10, exp,
            ceil, floor, abs, round, min, max, sum, pow, random, randint.
            Constants: pi, e

    Returns:
        Dict with 'success' status and 'result' or 'error' message.

    Examples:
        >>> calculator("2 + 2")
        {'success': True, 'result': 4}
        >>> calculator("sqrt(16) + pi")
        {'success': True, 'result': 7.141592653589793}
    """
    try:
        # Parse the expression to an AST
        tree = ast.parse(python_expression, mode="eval")

        # Compile with restricted globals
        code = compile(tree, "<expression>", "eval")

        # Evaluate with only allowed names
        result = eval(code, {"__builtins__": {}}, _ALLOWED_NAMES)

        logger.info(f"Calculating formula: {python_expression}, result: {result}")
        return {"success": True, "result": result}

    except SyntaxError as e:
        logger.error(f"Syntax error in expression: {e}")
        return {"success": False, "error": f"Invalid expression syntax: {e}"}

    except NameError as e:
        logger.error(f"Name error in expression: {e}")
        return {"success": False, "error": f"Unknown function or variable: {e}"}

    except Exception as e:
        logger.error(f"Error calculating expression: {e}")
        return {"success": False, "error": str(e)}
