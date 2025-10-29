"""
Enterprise Multi-Agent Research System
A sophisticated LangGraph-based multi-agent system for enterprise research.
"""

__version__ = "1.0.0"

from .enterprise_multi_agent import (
    graph,
    research_with_enterprise_tools,
    build_enterprise_research_graph
)

__all__ = [
    "graph",
    "research_with_enterprise_tools", 
    "build_enterprise_research_graph"
]
