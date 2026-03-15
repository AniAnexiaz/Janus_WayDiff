"""
Intelligence layer for WayDiff.

Contains rule-based and LLM-based reporting modules.
"""

from .diff_security_report import generate_security_report
from .diff_llm_report import generate_llm_report

__all__ = [
    "generate_security_report",
    "generate_llm_report",
]
