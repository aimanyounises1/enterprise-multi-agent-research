"""
Enterprise Multi-Agent Research System
Main implementation that combines supervisor and research agents with enterprise MCP tools.
"""

import os
import warnings
from typing import List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

# Ensure environment variables are loaded
if "LANGSMITH_API_KEY" in os.environ:
    print(f"✅ LangSmith API key loaded: {os.environ['LANGSMITH_API_KEY'][:10]}...")
    print(f"✅ LangSmith project: {os.environ.get('LANGSMITH_PROJECT', 'default')}")
    print(f"✅ LangSmith tracing: {os.environ.get('LANGCHAIN_TRACING_V2', 'false')}")

from .state.graph_state import ReportState, SectionState, SectionOutputState
from .config.agent_config import MultiAgentConfiguration
from .agents.supervisor import (
    supervisor, supervisor_tools, supervisor_should_continue
)
from .agents.researcher import (
    research_agent, research_agent_tools, research_agent_should_continue
)


# MCP Tool Loading Functions
async def _load_mcp_tools(config: RunnableConfig, existing_tool_names: set[str]) -> List[BaseTool]:
    """
    Initializes the MultiServerMCPClient and fetches the available enterprise tools.
    This function is the bridge to your enterprise tools.
    """
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    if not configurable.mcp_server_config:
        return []
    
    print("Connecting to MCP server and loading enterprise tools...")
    try:
        client = MultiServerMCPClient(configurable.mcp_server_config)
        mcp_tools = await client.get_tools()
        print(f"Found MCP tools: {[t.name for t in mcp_tools]}")
        
        filtered_mcp_tools: List[BaseTool] = []
        for t in mcp_tools:
            if t.name in existing_tool_names:
                warnings.warn(f"MCP tool name '{t.name}' conflicts with an existing tool. Ignoring.")
                continue
            if configurable.mcp_tools_to_include and t.name not in configurable.mcp_tools_to_include:
                continue
            filtered_mcp_tools.append(t)
        
        print(f"Loaded {len(filtered_mcp_tools)} enterprise tools")
        return filtered_mcp_tools
    
    except Exception as e:
        print(f"Error loading MCP tools"
              f": {e}")
        warnings.warn(f"Failed to load MCP tools: {e}")
        return []


# Build the Enterprise Multi-Agent Graph
def supervisor_tools_router(state: ReportState):
    """
    Route from supervisor_tools based on state.
    If sections are being delegated, send to research_team.
    Otherwise, go back to supervisor.
    """
    # Check if we have sections to research
    sections = state.get("sections", [])
    completed_sections = state.get("completed_sections", [])
    
    # Only delegate sections that haven't been completed yet
    if sections:
        completed_section_names = {s.name for s in completed_sections} if completed_sections else set()
        remaining_sections = [s for s in sections if s not in completed_section_names]
        
        if remaining_sections:
            # Return Send commands for parallel execution of remaining sections
            original_query = state.get("original_query", "")
            return [Send("research_team", {"section": s, "original_query": original_query}) for s in remaining_sections]
    
    return "supervisor"


def build_enterprise_research_graph():
    """
    Builds the complete enterprise research graph with supervisor and research agents.
    """
    # Research agent sub-graph - with config schema
    research_builder = StateGraph(
        SectionState, 
        output=SectionOutputState,
        config_schema=MultiAgentConfiguration
    )
    research_builder.add_node("research_agent", research_agent)
    research_builder.add_node("research_agent_tools", research_agent_tools)
    
    # Research graph edges
    research_builder.add_edge(START, "research_agent")
    research_builder.add_conditional_edges(
        "research_agent",
        research_agent_should_continue,
        ["research_agent_tools", END]
    )
    research_builder.add_edge("research_agent_tools", "research_agent")
    
    # Main supervisor graph - with config schema and proper input/output types
    supervisor_builder = StateGraph(
        ReportState,
        config_schema=MultiAgentConfiguration
    )
    supervisor_builder.add_node("supervisor", supervisor)
    supervisor_builder.add_node("supervisor_tools", supervisor_tools)
    supervisor_builder.add_node("research_team", research_builder.compile())
    
    # Flow of the supervisor agent
    supervisor_builder.add_edge(START, "supervisor")
    supervisor_builder.add_conditional_edges(
        "supervisor",
        supervisor_should_continue,
        ["supervisor_tools", END]
    )
    
    # Add conditional routing from supervisor_tools
    supervisor_builder.add_conditional_edges(
        "supervisor_tools",
        supervisor_tools_router,
        ["supervisor", "research_team"]
    )
    
    supervisor_builder.add_edge("research_team", "supervisor")
    
    # Compile the final graph
    return supervisor_builder.compile()


# Create the compiled graph instance
graph = build_enterprise_research_graph()


# Utility functions for running the graph
async def research_with_enterprise_tools(
    query: str,
    mcp_config: dict = None,
    stream_output: bool = True
) -> dict:
    """
    Run enterprise research on a query using the multi-agent system.
    
    Args:
        query: The research query
        mcp_config: Optional MCP configuration (uses defaults if not provided)
        stream_output: Whether to print progress as the graph executes
    
    Returns:
        Final state including the completed report
    """
    from langchain_core.messages import HumanMessage
    
    # Use provided config or get defaults
    if not mcp_config:
        mcp_config = MultiAgentConfiguration.get_default_mcp_config()
    
    # Build configuration with defaults
    config = {
        "configurable": MultiAgentConfiguration(
            mcp_server_config=mcp_config
        ).model_dump()
    }
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "original_query": query  # Store original query for researchers
    }
    
    if stream_output:
        print(f"\n🔍 Starting enterprise research for: {query}\n")
        
        # Stream execution
        async for chunk in graph.astream(initial_state, config=config):
            for key, value in chunk.items():
                print(f"\n--- Node: {key} ---")
                
                if "messages" in value and value["messages"]:
                    last_message = value["messages"][-1]
                    
                    # Print tool calls
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            print(f"🔧 Tool: {tool_call['name']}")
                            if tool_call["name"] in ["search_perforce_changelists", 
                                                   "search_jira_issues",
                                                   "search_confluence_pages"]:
                                args = tool_call.get("args", {})
                                print(f"   Query: {args.get('query', 'N/A')}")
                    
                    # Print content if not a tool message
                    elif hasattr(last_message, "content") and last_message.content:
                        # Truncate long content
                        content = str(last_message.content)
                        if len(content) > 200:
                            content = content[:200] + "..."
                        print(f"📝 {content}")
                
                # Print final report
                if "final_report" in value and value["final_report"]:
                    print("\n" + "="*80)
                    print("📄 FINAL REPORT")
                    print("="*80)
                    print(value["final_report"])
                    print("="*80 + "\n")
        
        # Get final state
        final_state = await graph.ainvoke(initial_state, config=config)
    else:
        # Run without streaming
        final_state = await graph.ainvoke(initial_state, config=config)
    
    return final_state