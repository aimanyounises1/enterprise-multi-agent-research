"""
MCP Tool Wrapper
Wraps MCP tools to automatically parse JSON string responses into dictionaries.
"""

import json
import logging
from typing import Any, Dict, Union, List
from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)


def create_json_parsing_tool(original_tool: BaseTool) -> BaseTool:
    """Create a new tool that wraps the original and parses JSON responses."""
    
    async def json_parsing_coroutine(**kwargs) -> Union[Dict[str, Any], str]:
        """Run the original tool and parse JSON responses."""
        try:
            # Call the original tool
            result = await original_tool.ainvoke(kwargs)
            
            # If result is a string, try to parse it as JSON
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                    logger.debug(f"[{original_tool.name}] Parsed JSON response successfully")
                    return parsed_result
                except json.JSONDecodeError as e:
                    logger.warning(f"[{original_tool.name}] Failed to parse JSON response: {e}")
                    # Return original string if not valid JSON
                    return result
            
            # Return as-is if not a string
            return result
            
        except Exception as e:
            logger.error(f"[{original_tool.name}] Tool execution failed: {e}")
            # Return error response in expected format
            return {
                "status": "error",
                "error": str(e),
                "tool": original_tool.name
            }
    
    def json_parsing_func(**kwargs) -> Union[Dict[str, Any], str]:
        """Synchronous version that delegates to async."""
        import asyncio
        return asyncio.run(json_parsing_coroutine(**kwargs))
    
    # Create a new tool with the wrapped functions
    wrapped_tool = StructuredTool(
        name=original_tool.name,
        description=original_tool.description,
        func=json_parsing_func,
        coroutine=json_parsing_coroutine,
        args_schema=original_tool.args_schema
    )
    
    return wrapped_tool


def wrap_mcp_tools(tools: List[BaseTool]) -> List[BaseTool]:
    """
    Wrap MCP tools to automatically parse JSON responses.
    
    Args:
        tools: List of MCP tools to wrap
        
    Returns:
        List of wrapped tools
    """
    wrapped_tools = []
    
    for tool in tools:
        # Only wrap tools that look like MCP tools
        if any(name in tool.name for name in ['perforce', 'jira', 'confluence', 'search_all']):
            logger.info(f"Wrapping MCP tool: {tool.name}")
            wrapped_tool = create_json_parsing_tool(tool)
            wrapped_tools.append(wrapped_tool)
        else:
            # Keep non-MCP tools as-is
            wrapped_tools.append(tool)
    
    return wrapped_tools