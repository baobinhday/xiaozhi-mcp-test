"""Math tool functions."""
import math
import random
import logging

logger = logging.getLogger('math_tools')


def calculator(python_expression: str) -> dict:
    """For mathematical calculation, always use this tool to calculate the result of a python expression. `math` and `random` are available."""
    result = eval(python_expression)
    logger.info(f"Calculating formula: {python_expression}, result: {result}")
    return {"success": True, "result": result}
