"""
Singleton MCP Client Manager
Manages a single instance of the MCP client to preserve session state across tool invocations.
"""

import asyncio
from typing import List, Optional, Dict, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
import logging

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Singleton manager for MCP client to preserve session state."""
    
    _instance: Optional['MCPClientManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: Optional[List[BaseTool]] = None
        self._config: Optional[Dict[str, Any]] = None
        self._tools_loaded = False
    
    @classmethod
    async def get_instance(cls) -> 'MCPClientManager':
        """Get the singleton instance of MCPClientManager."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    async def get_tools(self, mcp_config: Dict[str, Any], force_reload: bool = False) -> List[BaseTool]:
        """
        Get MCP tools, creating client if needed and caching tools.
        
        Args:
            mcp_config: MCP server configuration
            force_reload: Force reload of tools even if already loaded
            
        Returns:
            List of available MCP tools
        """
        # Check if we need to reload (config changed or forced)
        config_changed = self._config != mcp_config
        
        if self._tools_loaded and not force_reload and not config_changed:
            logger.info("Using cached MCP tools")
            return self._tools or []
        
        # Create or recreate client if needed
        if self._client is None or config_changed:
            logger.info("Creating new MCP client with updated configuration")
            # Use the original config without modifications for better compatibility
            self._client = MultiServerMCPClient(mcp_config)
            self._config = mcp_config
        
        # Load tools
        try:
            logger.info("Loading MCP tools from server...")
            self._tools = await self._client.get_tools()
            
            self._tools_loaded = True
            logger.info(f"Successfully loaded {len(self._tools)} MCP tools")
            
            # Log tool names for debugging
            tool_names = [t.name for t in self._tools]
            logger.debug(f"Available tools: {tool_names}")
            
            return self._tools
            
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            self._tools = []
            # Don't set tools_loaded to True on failure
            return []
    
    def reset(self):
        """Reset the client manager, forcing fresh connections on next use."""
        logger.info("Resetting MCP client manager")
        self._client = None
        self._tools = None
        self._config = None
        self._tools_loaded = False
    
    @classmethod
    def clear_instance(cls):
        """Clear the singleton instance (useful for testing)."""
        cls._instance = None