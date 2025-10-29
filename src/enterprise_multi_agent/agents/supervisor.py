"""
Supervisor Agent for the Enterprise Multi-Agent Research System.
Manages the overall research workflow and delegates tasks.
"""

from typing import List, cast
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langchain_ollama import ChatOllama
from langgraph.graph import END

from ..state.graph_state import ReportState
from ..tools.tool_schemas import (
    Sections, Introduction, Conclusion, FinishReport
)
from ..config.agent_config import MultiAgentConfiguration


async def get_supervisor_tools(config: RunnableConfig) -> List[BaseTool]:
    """Get supervisor tools, including enterprise tools from MCP."""
    import logging
    from ..mcp_client_manager import MCPClientManager
    
    logger = logging.getLogger("Supervisor.Tools")
    
    # Core supervisor tools
    tools = [
        tool(Sections),
        tool(Introduction),
        tool(Conclusion),
        tool(FinishReport)
    ]
    
    # Load MCP tools using singleton manager
    existing_tool_names = {t.name for t in tools}
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    
    logger.info(f"[MCP DEBUG] Supervisor MCP server config exists: {configurable.mcp_server_config is not None}")
    
    if configurable.mcp_server_config:
        logger.info(f"[MCP DEBUG] Supervisor loading MCP tools with config: {configurable.mcp_server_config}")
        try:
            manager = await MCPClientManager.get_instance()
            mcp_tools = await manager.get_tools(configurable.mcp_server_config)
            
            logger.info(f"[MCP DEBUG] Supervisor loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
            
            # Filter MCP tools
            added_tools = 0
            for t in mcp_tools:
                if t.name in existing_tool_names:
                    logger.debug(f"[MCP DEBUG] Supervisor skipping duplicate tool: {t.name}")
                    continue
                if configurable.mcp_tools_to_include and t.name not in configurable.mcp_tools_to_include:
                    logger.debug(f"[MCP DEBUG] Supervisor skipping filtered tool: {t.name}")
                    continue
                tools.append(t)
                added_tools += 1
                logger.debug(f"[MCP DEBUG] Supervisor added tool: {t.name}")
            
            logger.info(f"[MCP DEBUG] Supervisor added {added_tools} MCP tools")
            
        except Exception as e:
            logger.error(f"[MCP DEBUG] Supervisor failed to load MCP tools: {e}")
    else:
        logger.warning("[MCP DEBUG] Supervisor no MCP server config found")
    
    logger.info(f"[MCP DEBUG] Supervisor total tools available: {len(tools)} - {[t.name for t in tools]}")
    return tools


async def supervisor(state: ReportState, config: RunnableConfig):
    """The supervisor agent decides the next action or plan."""
    import logging
    import re
    
    logger = logging.getLogger("Supervisor")
    
    messages = state["messages"]
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    
    # Store original query if not already stored
    original_query = state.get("original_query", "")
    if not original_query and messages:
        # Find the first human message as the original query
        for msg in messages:
            if hasattr(msg, "type") and msg.type == "human":
                original_query = msg.content
                state["original_query"] = original_query
                break
    
    # Extract identifiers from query for logging
    vit_pattern = r'(VIT|VFIT|CR|INC)-?\d+'
    mtv_pattern = r'MTV\d{3,}'
    cl_pattern = r'(?:CL|changelist)\s*[:#]?\s*(\d{6,8})'
    
    vit_matches = re.findall(vit_pattern, original_query, re.IGNORECASE)
    mtv_matches = re.findall(mtv_pattern, original_query, re.IGNORECASE)
    cl_matches = re.findall(cl_pattern, original_query, re.IGNORECASE)
    
    logger.info(f"[SUPERVISOR] Original Query: {original_query}")
    logger.info(f"[SUPERVISOR] Extracted Identifiers - VITs: {vit_matches}, MTVs: {mtv_matches}, CLs: {cl_matches}")
    
    # Initialize ChatOllama with supervisor settings
    # Remove format="json" to allow proper tool calling
    llm = ChatOllama(
        model=configurable.supervisor_model,
        temperature=configurable.supervisor_temperature
    )
    
    # Check if research is complete and we need to write introduction/conclusion
    sections = state.get("sections", [])
    completed_sections = state.get("completed_sections", [])
    
    logger.info(f"[SUPERVISOR] Status - Sections: {len(sections)}, Completed: {len(completed_sections)}")
    
    if sections and completed_sections and len(completed_sections) >= len(sections) and not state.get("final_report"):
        logger.info("[SUPERVISOR] All research sections complete, preparing to write introduction and conclusion")
        research_complete_message = {
            "role": "user",
            "content": (
                "All research sections are complete. Now, write the introduction and "
                "conclusion for the report based on the following content:\n\n" +
                "\n\n".join([s.content for s in completed_sections])
            )
        }
        messages = messages + [research_complete_message]
    
    # Get tools and bind to LLM
    supervisor_tool_list = await get_supervisor_tools(config)
    llm_with_tools = llm.bind_tools(
        supervisor_tool_list,
        tool_choice="auto"
    )
    
    # System prompt emphasizing enterprise sources
    system_prompt = (
        "You are an expert enterprise research supervisor. Your goal is to create "
        "comprehensive reports based on user queries. /no_think\n\n"
        "CRITICAL: You MUST use the available tools to accomplish this task. "
        "Do NOT respond with just text - you must call tools to proceed.\n\n"
        "Available tools:\n"
        "- Sections: Create a list of sections for research delegation\n"
        "- search_perforce_changelists: Search code changes and implementations\n"
        "- search_jira_issues: Find issue tracking and project information\n"
        "- search_confluence_pages: Locate documentation and knowledge\n"
        "- search_all_enterprise_sources: Cross-source search\n"
        "- Introduction: Write introduction after research is complete\n"
        "- Conclusion: Write conclusion after research is complete\n"
        "- FinishReport: Signal completion of the entire report\n\n"
        "WORKFLOW:\n"
        "1. For research queries, use the 'Sections' tool to create research sections\n"
        "2. When creating sections for specific items (like VIT-60872, MTV2005), "
        "   use specific names like 'VIT-60872 Details', 'Related Perforce Changes for VIT-60872'\n"
        "3. After research is delegated and completed, use Introduction and Conclusion tools\n"
        "4. Finally use FinishReport to signal completion\n\n"
        "REMEMBER: Always call tools - never respond with just text content."
    )
    
    logger.info(f"[SUPERVISOR] Invoking LLM with {len(supervisor_tool_list)} tools available")
    
    # Invoke LLM
    response = await llm_with_tools.ainvoke(
        [{"role": "system", "content": system_prompt}] + messages
    )
    
    # Log the supervisor's decision
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            logger.info(f"[SUPERVISOR] Decided to call: {tc['name']} with args: {tc.get('args', {})}")
    else:
        logger.info(f"[SUPERVISOR] Response without tool calls: {getattr(response, 'content', str(response))[:200]}...")
    
    return {"messages": [response], "original_query": original_query}


async def supervisor_tools(state: ReportState, config: RunnableConfig) -> dict:
    """Handles the tool calls made by the supervisor."""
    result = []
    sections_list = []
    intro_content = None
    conclusion_content = None
    
    # Get tools for processing
    supervisor_tool_list = await get_supervisor_tools(config)
    supervisor_tools_by_name = {t.name: t for t in supervisor_tool_list}
    
    # Process each tool call
    for tool_call in state["messages"][-1].tool_calls:
        tool_to_call = supervisor_tools_by_name[tool_call["name"]]
        observation = await tool_to_call.ainvoke(tool_call["args"], config)
        
        result.append({
            "role": "tool",
            "content": str(observation),
            "name": tool_call["name"],
            "tool_call_id": tool_call["id"]
        })
        
        # Handle specific tool types
        if tool_call["name"] == "Sections":
            sections_list = cast(Sections, observation).sections
        elif tool_call["name"] == "Introduction":
            observation = cast(Introduction, observation)
            intro_content = f"# {observation.name}\n\n{observation.content}"
        elif tool_call["name"] == "Conclusion":
            observation = cast(Conclusion, observation)
            conclusion_content = f"## {observation.name}\n\n{observation.content}"
    
    # Default update state
    state_update = {"messages": result}
    
    # Handle sections delegation
    if sections_list:
        # We'll use Send commands to trigger parallel execution
        print(f"Supervisor delegating research for sections: {sections_list}")
        state_update["sections"] = sections_list
        # The routing function will handle sending to research_team
    
    # Handle introduction
    if intro_content:
        state_update["final_report"] = intro_content
        result.append({
            "role": "user",
            "content": "Introduction written. Now write a conclusion."
        })
    
    # Handle conclusion and finalize report
    if conclusion_content:
        intro = state.get("final_report", "")
        body_sections = "\n\n".join([s.content for s in state["completed_sections"]])
        complete_report = f"{intro}\n\n{body_sections}\n\n{conclusion_content}"
        state_update["final_report"] = complete_report
        result.append({
            "role": "user",
            "content": "Report is complete."
        })
    
    return state_update


def supervisor_should_continue(state: ReportState) -> str:
    """Decision point for the supervisor loop."""
    last_message = state["messages"][-1]
    
    # Check if no tool calls or only FinishReport
    if not last_message.tool_calls:
        return END
    
    if (len(last_message.tool_calls) == 1 and 
        last_message.tool_calls[0]["name"] == "FinishReport"):
        return END
    
    return "supervisor_tools"