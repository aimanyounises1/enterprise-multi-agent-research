"""
Tool schemas for the Enterprise Multi-Agent Research System.
These Pydantic models define the structure for report generation.
"""

from typing import List
from pydantic import BaseModel, Field


class Section(BaseModel):
    """A section of the report being researched and written."""
    name: str = Field(description="Name for this section of the report.")
    description: str = Field(description="A detailed description of the research scope for this section.")
    content: str = Field(description="The fully written content of the section, based on research.")


class Sections(BaseModel):
    """A list of section titles that will form the main body of the report."""
    sections: List[str] = Field(description="The titles of the sections to be researched.")


class Introduction(BaseModel):
    """The introduction for the final report."""
    name: str = Field(description="The overall title for the report.")
    content: str = Field(description="The content of the introduction, giving an overview of the report.")


class Conclusion(BaseModel):
    """The conclusion for the final report."""
    name: str = Field(description="The title for the conclusion section (e.g., 'Conclusion', 'Summary').")
    content: str = Field(description="The content of the conclusion, summarizing the report's findings.")


class FinishResearch(BaseModel):
    """A tool to signify that research for a specific section is complete."""
    pass


class FinishReport(BaseModel):
    """A tool to signify that the entire report (intro, body, conclusion) is complete."""
    pass