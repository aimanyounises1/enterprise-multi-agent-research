"""
Research Agent for the Enterprise Multi-Agent Research System.
Focuses on researching individual sections using enterprise tools.
"""

from typing import List, cast
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langchain_ollama import ChatOllama
from langgraph.graph import END

from ..state.graph_state import SectionState
from ..tools.tool_schemas import Section, FinishResearch
from ..config.agent_config import MultiAgentConfiguration


async def get_research_tools(config: RunnableConfig) -> List[BaseTool]:
    """Get research tools, including enterprise tools from MCP."""
    import logging
    from ..mcp_client_manager import MCPClientManager
    
    logger = logging.getLogger("Researcher.Tools")
    
    # Core research tools
    tools = [
        tool(Section),
        tool(FinishResearch)
    ]
    
    # Load MCP tools using singleton manager
    existing_tool_names = {t.name for t in tools}
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    
    logger.info(f"[MCP DEBUG] Configurable MCP server config exists: {configurable.mcp_server_config is not None}")
    
    if configurable.mcp_server_config:
        logger.info(f"[MCP DEBUG] Loading MCP tools with config: {configurable.mcp_server_config}")
        try:
            manager = await MCPClientManager.get_instance()
            mcp_tools = await manager.get_tools(configurable.mcp_server_config)
            
            logger.info(f"[MCP DEBUG] Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
            
            # Filter MCP tools
            added_tools = 0
            for t in mcp_tools:
                if t.name in existing_tool_names:
                    logger.debug(f"[MCP DEBUG] Skipping duplicate tool: {t.name}")
                    continue
                if configurable.mcp_tools_to_include and t.name not in configurable.mcp_tools_to_include:
                    logger.debug(f"[MCP DEBUG] Skipping filtered tool: {t.name}")
                    continue
                tools.append(t)
                added_tools += 1
                logger.debug(f"[MCP DEBUG] Added tool: {t.name}")
            
            logger.info(f"[MCP DEBUG] Added {added_tools} MCP tools to research agent")
            
        except Exception as e:
            logger.error(f"[MCP DEBUG] Failed to load MCP tools: {e}")
    else:
        logger.warning("[MCP DEBUG] No MCP server config found")
    
    logger.info(f"[MCP DEBUG] Total tools available: {len(tools)} - {[t.name for t in tools]}")
    return tools


async def research_agent(state: SectionState, config: RunnableConfig):
    """The research agent that focuses on a single section."""
    import logging
    import re
    
    logger = logging.getLogger("Researcher")
    
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    section_name = state["section"]
    
    # Initialize ChatOllama with researcher settings
    # Remove format="json" to allow proper tool calling
    llm = ChatOllama(
        model=configurable.researcher_model,
        temperature=configurable.researcher_temperature
    )
    
    # Get tools and bind to LLM
    research_tool_list = await get_research_tools(config)
    llm_with_tools = llm.bind_tools(
        research_tool_list,
        tool_choice="auto"
    )
    
    # Extract the original query for context
    original_query = state.get("original_query", "")
    
    # Extract identifiers from original query
    vit_pattern = r'(VIT|VFIT|CR|INC)-?\d+'
    mtv_pattern = r'MTV\d{3,}'
    cl_pattern = r'(?:CL|changelist)\s*[:#]?\s*(\d{6,8})'
    
    vit_matches = re.findall(vit_pattern, original_query, re.IGNORECASE)
    mtv_matches = re.findall(mtv_pattern, original_query, re.IGNORECASE)
    cl_matches = re.findall(cl_pattern, original_query, re.IGNORECASE)
    
    logger.info(f"[RESEARCHER] Section: {section_name}")
    logger.info(f"[RESEARCHER] Original Query: {original_query}")
    logger.info(f"[RESEARCHER] Extracted Identifiers - VITs: {vit_matches}, MTVs: {mtv_matches}, CLs: {cl_matches}")
    
    # System prompt emphasizing enterprise research
    system_prompt = f"""You are an expert enterprise researcher. Your sole focus is to research 
and write a detailed section for a report. The section you must write is: '{section_name}'. /no_think

CONTEXT: The user's original query was: "{original_query}"

EXTRACTED IDENTIFIERS FROM QUERY:
- VIT/JIRA Issues: {vit_matches if vit_matches else 'None found'}
- MTV Numbers: {mtv_matches if mtv_matches else 'None found'}  
- Changelist Numbers: {cl_matches if cl_matches else 'None found'}

Use the available enterprise search tools to gather comprehensive information:
- search_perforce_changelists: Find code implementations, changes, and technical details
  IMPORTANT: Use max_results between 50-200 for efficiency. Start small and expand if needed.
- get_perforce_changelist_details: Get detailed information about specific changelists
- search_jira_issues: Locate related tickets, issues, and project tracking information
  IMPORTANT: Use max_results between 10-50 for efficiency
- get_jira_issue_details: Get detailed information about specific JIRA issues
- search_confluence_pages: Find documentation, specifications, and knowledge articles
  IMPORTANT: Use max_results between 10-20 for efficiency
- search_all_enterprise_sources: Perform comprehensive cross-source searches
  IMPORTANT: Use max_results_per_source between 10-20 for efficiency

CRITICAL RESEARCH STRATEGY:

1. INITIAL SEARCH: Start by searching for the specific identifiers extracted above
   - Search for each MTV number (e.g., "MTV2005")
   - Search for each VIT number (e.g., "VIT-60872")
   - Search for each changelist number

2. DETAILED INVESTIGATION: For EVERY item found, get detailed information:
   - When you find a changelist, ALWAYS call get_perforce_changelist_details
   - When you find a JIRA issue, ALWAYS call get_jira_issue_details
   - This reveals related items, descriptions, and connections

3. CROSS-REFERENCE EXPANSION: Extract new identifiers from the results:
   - Look for MTV numbers mentioned in JIRA descriptions
   - Find VIT numbers referenced in Perforce changelists
   - Identify changelist numbers in JIRA tickets
   - Search for these newly discovered items

4. ITERATIVE DEEPENING: Continue expanding your search:
   - Each new item may reveal more connections
   - Search for at least 2-3 levels deep
   - Keep searching until you have a comprehensive view

5. COMPREHENSIVE COVERAGE: Ensure you've searched all sources:
   - If you found an MTV in Perforce, also search JIRA and Confluence
   - If you found a VIT in JIRA, also search Perforce for related code changes
   - Cross-check all findings across all three systems

EXAMPLE WORKFLOW:
- Original query mentions "MTV2005"
- Search Perforce for "MTV2005" → Find CL 27235273
- Get details of CL 27235273 → Discover it mentions VIT-12345
- Search JIRA for "VIT-12345" → Find full ticket details
- Get details of VIT-12345 → Discover it references MTV2005 and MTV2010
- Search for "MTV2010" across all sources → Find more related items
- Continue until you have the full picture

CRITICAL: After you gather information, you MUST call the 'Section' tool to complete your research.
- After 2-3 search iterations, write your section using the Section tool
- Include citations in the format: [Source: JIRA VIT-1234] or [Source: Perforce CL 12345678]
- Do NOT continue searching indefinitely - complete your section promptly"""
    
    # Initialize messages if empty
    messages = state.get("messages", [])
    if not messages:
        messages = [{
            "role": "user",
            "content": f"Please research and write the section: {section_name}"
        }]
    
    logger.info(f"[RESEARCHER] Starting research for section with {len(research_tool_list)} tools available")
    
    # Invoke LLM
    response = await llm_with_tools.ainvoke(
        [{"role": "system", "content": system_prompt}] + messages
    )
    
    # Log the agent's decision
    if response.tool_calls:
        for tc in response.tool_calls:
            logger.info(f"[RESEARCHER] Agent decided to call: {tc['name']} with args: {tc['args']}")
    else:
        logger.info(f"[RESEARCHER] Agent response without tool calls: {response.content[:200]}...")
    
    return {"messages": [response]}


async def research_agent_tools(state: SectionState, config: RunnableConfig):
    """Handles the tool calls made by the researcher."""
    import logging
    import re
    
    logger = logging.getLogger("Researcher.Tools")
    
    result = []
    completed_section = None
    
    # Get tools for processing
    research_tool_list = await get_research_tools(config)
    research_tools_by_name = {t.name: t for t in research_tool_list}
    
    # Process each tool call
    for tool_call in state["messages"][-1].tool_calls:
        tool_name = tool_call["name"]
        tool_to_call = research_tools_by_name[tool_name]
        
        # Log enterprise tool usage
        if tool_name in ["search_perforce_changelists", "search_jira_issues", 
                        "search_confluence_pages", "search_all_enterprise_sources",
                        "get_perforce_changelist_details", "get_jira_issue_details"]:
            logger.info(f"[TOOL CALL] {tool_name} with args: {tool_call['args']}")
        
        observation = await tool_to_call.ainvoke(tool_call["args"], config)
        
        # Analyze results for cross-referencing
        if tool_name == "search_perforce_changelists" and isinstance(observation, dict):
            if observation.get("status") == "success":
                total = observation.get("total_found", 0)
                logger.info(f"[PERFORCE RESULTS] Found {total} changelists for query '{tool_call['args'].get('query')}'")
                
                # Extract identifiers from results for cross-referencing
                for cl in observation.get("changelists", [])[:5]:  # Log first 5
                    cl_num = cl.get("number", "")
                    desc = cl.get("description", "")[:200]
                    logger.info(f"  - CL {cl_num}: {desc}")
                    
                    # Find VIT/MTV references in descriptions
                    vit_refs = re.findall(r'(VIT|VFIT|CR|INC)-?\d+', desc, re.IGNORECASE)
                    mtv_refs = re.findall(r'MTV\d{3,}', desc, re.IGNORECASE)
                    if vit_refs or mtv_refs:
                        logger.info(f"    → Found references: VITs={vit_refs}, MTVs={mtv_refs}")
        
        elif tool_name == "search_jira_issues" and isinstance(observation, dict):
            if observation.get("status") == "success":
                total = observation.get("total_found", 0)
                logger.info(f"[JIRA RESULTS] Found {total} issues for query '{tool_call['args'].get('query')}'")
                
                # Extract identifiers from results
                for issue in observation.get("issues", [])[:5]:
                    key = issue.get("key", "")
                    summary = issue.get("summary", "")[:100]
                    logger.info(f"  - {key}: {summary}")
                    
                    # Find MTV/CL references
                    desc = issue.get("description", "")
                    mtv_refs = re.findall(r'MTV\d{3,}', desc, re.IGNORECASE)
                    cl_refs = re.findall(r'(?:CL|changelist)\s*[:#]?\s*(\d{6,8})', desc, re.IGNORECASE)
                    if mtv_refs or cl_refs:
                        logger.info(f"    → Found references: MTVs={mtv_refs}, CLs={cl_refs}")
        
        elif tool_name == "get_perforce_changelist_details" and isinstance(observation, dict):
            if observation.get("status") == "success":
                details = observation.get("details", {})
                cl_num = details.get("number", "")
                desc = details.get("description", "")
                logger.info(f"[PERFORCE DETAILS] CL {cl_num} details retrieved")
                logger.info(f"  Description: {desc[:200]}...")
                
                # Find references for cross-referencing
                vit_refs = re.findall(r'(VIT|VFIT|CR|INC)-?\d+', desc, re.IGNORECASE)
                mtv_refs = re.findall(r'MTV\d{3,}', desc, re.IGNORECASE)
                if vit_refs or mtv_refs:
                    logger.info(f"  → Found new references to explore: VITs={vit_refs}, MTVs={mtv_refs}")
        
        elif tool_name == "get_jira_issue_details" and isinstance(observation, dict):
            if observation.get("status") == "success":
                details = observation.get("details", {})
                key = details.get("key", "")
                logger.info(f"[JIRA DETAILS] {key} details retrieved")
                
                # Check for cross-references
                desc = details.get("description", "")
                mtv_refs = re.findall(r'MTV\d{3,}', desc, re.IGNORECASE)
                cl_refs = re.findall(r'(?:CL|changelist)\s*[:#]?\s*(\d{6,8})', desc, re.IGNORECASE)
                if mtv_refs or cl_refs:
                    logger.info(f"  → Found new references to explore: MTVs={mtv_refs}, CLs={cl_refs}")
        
        result.append({
            "role": "tool",
            "content": str(observation),
            "name": tool_name,
            "tool_call_id": tool_call["id"]
        })
        
        # Check if section was completed
        if tool_name == "Section":
            completed_section = cast(Section, observation)
            logger.info(f"[SECTION COMPLETE] {completed_section.name} - {len(completed_section.content)} chars")
    
    # Update state
    state_update = {"messages": result}
    
    if completed_section:
        state_update["completed_sections"] = [completed_section]
    
    return state_update


def research_agent_should_continue(state: SectionState) -> str:
    """Decision point for the researcher loop."""
    last_message = state["messages"][-1]
    
    # Check if research is finished
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return END
    
    # Check for completion tools
    if any(tc["name"] in ["FinishResearch", "Section"] for tc in last_message.tool_calls):
        return END
    
    return "research_agent_tools"