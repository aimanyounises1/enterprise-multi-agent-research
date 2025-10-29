#!/usr/bin/env python3
"""
Clean Enterprise MCP Server
Focused on three core enterprise sources: Perforce, JIRA, Confluence
"""

from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastMCP server
mcp = FastMCP("Clean Enterprise Tools")

# ============================================================================
# PERFORCE TOOLS
# ============================================================================

@mcp.tool()
async def search_perforce_changelists(
    query: str,
    max_results: int = 5000  # Increased from 50 to search more comprehensively
) -> Dict[str, Any]:
    """
    Search Perforce changelists by keyword, MTV number, or changelist number.
    
    Args:
        query: Search query (keywords, MTV numbers, or CL numbers)
        max_results: Maximum number of changelists to return (default: 5000)
        
    Returns:
        Dictionary containing found changelists and metadata
    """
    import logging
    logger = logging.getLogger("MCP.Perforce")
    
    try:
        from tools.perforce_tool import PerforceSearchTool
        
        tool = PerforceSearchTool()
        
        logger.info(f"[MCP] Searching Perforce for '{query}' with max_results={max_results}")
        
        # Detect search type and perform appropriate search
        if query.upper().startswith('MTV') or query.isdigit():
            # MTV or changelist number search
            search_terms = [query]
            logger.info(f"[MCP] Detected MTV/CL search pattern: {search_terms}")
            results = tool.search_changelists(search_terms, max_results, search_mode="comprehensive")
            changelists = []
            for term, matches in results.items():
                changelists.extend(matches)
        else:
            # Keyword search
            search_terms = [query]
            logger.info(f"[MCP] Performing keyword search: {search_terms}")
            results = tool.search_changelists(search_terms, max_results, search_mode="comprehensive")
            changelists = []
            for term, matches in results.items():
                changelists.extend(matches)
        
        logger.info(f"[MCP] Perforce search found {len(changelists)} results for '{query}'")
        
        return {
            "status": "success",
            "query": query,
            "total_found": len(changelists),
            "changelists": changelists,
            "search_params": {
                "max_results": max_results,
                "search_mode": "comprehensive"
            }
        }
        
    except Exception as e:
        logger.error(f"[MCP] Perforce search error for '{query}': {str(e)}")
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "changelists": []
        }

@mcp.tool()
async def get_perforce_changelist_details(
    changelist_number: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Perforce changelist.
    
    Args:
        changelist_number: The changelist number
        
    Returns:
        Dictionary containing detailed changelist information
    """
    try:
        from tools.perforce_tool import PerforceSearchTool
        
        tool = PerforceSearchTool()
        details = tool.get_changelist_details(changelist_number)
        
        return {
            "status": "success",
            "changelist": changelist_number,
            "details": details
        }
        
    except Exception as e:
        return {
            "status": "error",
            "changelist": changelist_number,
            "error": str(e),
            "details": {}
        }

@mcp.tool()
async def get_perforce_file_content(
    file_path: str,
    changelist_number: str = None
) -> Dict[str, Any]:
    """
    Get the content of a file from Perforce.
    
    Args:
        file_path: Depot path to the file
        changelist_number: Optional changelist number for specific revision
        
    Returns:
        Dictionary containing file content
    """
    try:
        from tools.perforce_tool import PerforceSearchTool
        
        tool = PerforceSearchTool()
        content = tool.get_file_content(file_path, changelist_number)
        
        return {
            "status": "success",
            "file_path": file_path,
            "changelist": changelist_number,
            "content": content,
            "content_length": len(content) if content else 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "file_path": file_path,
            "changelist": changelist_number,
            "error": str(e),
            "content": None
        }

# ============================================================================
# JIRA TOOLS
# ============================================================================

@mcp.tool()
async def search_jira_issues(
    query: str,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search JIRA issues with enhanced capabilities.
    
    Args:
        query: Search query (issue keys, JQL, or text)
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing found issues and metadata
    """
    try:
        from tools.jira_tool import JiraSearchTool
        
        tool = JiraSearchTool()
        results = tool.search_issues(query, max_results)
        
        return {
            "status": "success",
            "query": query,
            "total_found": len(results),
            "issues": results
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "query": query,
            "error": str(e),
            "issues": []
        }

@mcp.tool()
async def get_jira_issue_details(
    issue_key: str,
    include_attachments: bool = False
) -> Dict[str, Any]:
    """
    Get detailed information about a specific JIRA issue.
    
    Args:
        issue_key: JIRA issue key (e.g., VIT-1234)
        include_attachments: Whether to include attachment information
        
    Returns:
        Dictionary containing detailed issue information
    """
    try:
        from tools.jira_tool import JiraSearchTool
        
        tool = JiraSearchTool()
        details = tool.get_issue_details(issue_key, include_attachments)
        
        return {
            "status": "success",
            "issue_key": issue_key,
            "details": details
        }
        
    except Exception as e:
        return {
            "status": "error",
            "issue_key": issue_key,
            "error": str(e),
            "details": {}
        }

# ============================================================================
# CONFLUENCE TOOLS
# ============================================================================

@mcp.tool()
async def search_confluence_pages(
    query: str,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search Confluence pages and content.
    
    Args:
        query: Search query for page content
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing found pages and content
    """
    try:
        from tools.confluence_tool import ConfluenceSearchTool
        
        tool = ConfluenceSearchTool()
        results = tool.search_pages(query, max_results)
        
        return {
            "status": "success",
            "query": query,
            "total_found": len(results) if isinstance(results, list) else 1,
            "pages": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query, 
            "error": str(e),
            "pages": []
        }

@mcp.tool()
async def get_confluence_page_content(
    page_id: str
) -> Dict[str, Any]:
    """
    Get the full content of a specific Confluence page.
    
    Args:
        page_id: Confluence page ID
        
    Returns:
        Dictionary containing page content and metadata
    """
    try:
        from tools.confluence_tool import ConfluenceSearchTool
        
        tool = ConfluenceSearchTool()
        content = tool.get_page_content(page_id)
        
        return {
            "status": "success",
            "page_id": page_id,
            "content": content
        }
        
    except Exception as e:
        return {
            "status": "error",
            "page_id": page_id,
            "error": str(e),
            "content": {}
        }

# ============================================================================
# CROSS-SOURCE SEARCH
# ============================================================================

@mcp.tool()
async def search_all_enterprise_sources(
    query: str,
    max_results_per_source: int = 10
) -> Dict[str, Any]:
    """
    Search across all enterprise sources (Perforce, JIRA, Confluence) simultaneously.
    
    Args:
        query: Search query to use across all sources
        max_results_per_source: Maximum results per source
        
    Returns:
        Dictionary containing results from all sources
    """
    results = {
        "status": "success",
        "query": query,
        "sources": {}
    }
    
    # Search Perforce
    try:
        perforce_results = await search_perforce_changelists(query, max_results_per_source)
        results["sources"]["perforce"] = perforce_results
    except Exception as e:
        results["sources"]["perforce"] = {"status": "error", "error": str(e)}
    
    # Search JIRA
    try:
        jira_results = await search_jira_issues(query, max_results_per_source)
        results["sources"]["jira"] = jira_results
    except Exception as e:
        results["sources"]["jira"] = {"status": "error", "error": str(e)}
    
    # Search Confluence
    try:
        confluence_results = await search_confluence_pages(query, max_results_per_source)
        results["sources"]["confluence"] = confluence_results
    except Exception as e:
        results["sources"]["confluence"] = {"status": "error", "error": str(e)}
    
    return results

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")
