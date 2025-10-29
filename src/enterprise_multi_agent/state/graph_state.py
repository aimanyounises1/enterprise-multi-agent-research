"""
State definitions for the Enterprise Multi-Agent Research System.
These TypedDict classes define the state that flows through the LangGraph.
"""

import operator
from typing import List, TypedDict, Annotated
from langgraph.graph import MessagesState

from ..tools.tool_schemas import Section


class ReportState(MessagesState):
    """Main state for the supervisor agent."""
    sections: List[str]
    completed_sections: Annotated[List[Section], operator.add]
    final_report: str
    original_query: str  # Store the original user query


class SectionState(MessagesState):
    """State for individual research tasks."""
    section: str
    completed_sections: List[Section]
    original_query: str  # Pass original query to researchers


class SectionOutputState(TypedDict):
    """Output format for research results."""
    completed_sections: List[Section]