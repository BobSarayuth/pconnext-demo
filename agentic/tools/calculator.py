import math

import numexpr
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from typing_extensions import Annotated

from agentic.tools.utils import reply


@tool
def calculator(
    expression: Annotated[str, "Expression should be a single line mathematical expression that solves the problem."],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Use this for all numerical calculations a single line.

    Examples:
        "37593 * 67" for "37593 times 67"
        "37593**(1/5)" for "37593^(1/5)"

    mathematical functions:

    - {sin,cos,tan}(float|complex): trigonometric sine, cosine or tangent.
    - {arcsin,arccos,arctan}(float|complex): trigonometric inverse sine, cosine or tangent.
    - arctan2(float1, float2): trigonometric inverse tangent of float1/float2.
    - {sinh,cosh,tanh}(float|complex): hyperbolic sine, cosine or tangent.
    - {arcsinh,arccosh,arctanh}(float|complex): hyperbolic inverse sine, cosine or tangent.
    - {log,log10,log1p}(float|complex): natural, base-10 and log(1+x) logarithms.
    - {exp,expm1}(float|complex): exponential and exponential minus one.
    - sqrt(float|complex): square root.
    - abs(float|complex): absolute value.
    - conj(complex): conjugate value.
    - {real,imag}(complex): real or imaginary part of complex.
    - complex(float, float): complex from real and imaginary parts.
    - contains(np.str, np.str): returns True for every string in op1 that contains op2.

    """
    evel = {
        "ex": expression.strip(),
        "global_dict": {},
        "local_dict": {"pi": math.pi, "e": math.e},
    }

    return reply(
        ToolMessage(content=str(numexpr.evaluate(**evel)), artifact={}, tool_call_id=tool_call_id),
        instructions=[
            "**INSTRUCT**",
            "- Clearly explain the input factors used for the calculation and the resulting outcome."
            "- Only mention the product name briefly and concisely."
            "- Always round up decimals.",
            "- Start your response with the customer's name.",
        ],
    )
