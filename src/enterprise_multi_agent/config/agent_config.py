"""
Configuration classes for the Enterprise Multi-Agent Research System.
Handles MCP server configuration and agent settings.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded environment variables from {env_path}")


class MultiAgentConfiguration(BaseModel):
    """Configuration for the multi-agent research system."""
    
    mcp_server_config: Optional[Dict] = Field(
        default=None,
        description="Configuration for MCP server connection"
    )
    
    def __init__(self, **data):
        """Initialize configuration with default MCP config if none provided."""
        if 'mcp_server_config' not in data or not data['mcp_server_config']:
            data['mcp_server_config'] = self.get_default_mcp_config()
            print(f"✅ Applied default MCP configuration in __init__")
        super().__init__(**data)
    
    mcp_tools_to_include: Optional[List[str]] = Field(
        default=None,
        description="Specific MCP tools to include (None means all)"
    )
    
    mcp_prompt: Optional[str] = Field(
        default="",
        description="Additional prompt for MCP tool usage"
    )
    
    # Ollama model configurations
    supervisor_model: str = Field(
        default="qwen3:30b-a3b",
        description="Model to use for supervisor agent"
    )
    
    researcher_model: str = Field(
        default="qwen3:30b-a3b", 
        description="Model to use for research agents"
    )
    
    # Temperature settings
    supervisor_temperature: float = Field(
        default=0.1,
        description="Temperature for supervisor agent"
    )
    
    researcher_temperature: float = Field(
        default=0.2,
        description="Temperature for research agents"
    )
    
    @classmethod
    def from_runnable_config(cls, config: RunnableConfig):
        """Create configuration from LangChain RunnableConfig."""
        configurable = config.get("configurable", {})
        
        # Ensure MCP server config is available when none is provided
        if not configurable.get("mcp_server_config"):
            configurable["mcp_server_config"] = cls.get_default_mcp_config()
            print(f"✅ Using default MCP configuration for enterprise tools")
        
        return cls(**configurable)
    
    @classmethod
    def get_default_mcp_config(cls) -> Dict:
        """Get default MCP server configuration using environment variables."""
        # Load parent .env file if it exists
        parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", ".env")
        if os.path.exists(parent_env):
            from dotenv import load_dotenv
            load_dotenv(parent_env)
        
        # Get the path to the enterprise_mcp_server.py
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        server_path = os.path.join(script_dir, "enterprise_mcp_server.py")
        
        return {
            "enterprise_server": {
                "command": "python",
                "args": [server_path],
                "transport": "stdio",
                "env": {
                    # Perforce credentials
                    "P4PORT": os.environ.get("P4PORT", ""),
                    "P4USER": os.environ.get("P4USER", ""),
                    "P4CLIENT": os.environ.get("P4CLIENT", ""),
                    "P4PASSWD": os.environ.get("P4PASSWD", ""),
                    
                    # JIRA credentials
                    "JIRA_SERVER": os.environ.get("JIRA_SERVER", ""),
                    "JIRA_USERNAME": os.environ.get("JIRA_USERNAME", ""),
                    "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN", ""),
                    
                    # Confluence credentials
                    "CONFLUENCE_URL": os.environ.get("CONFLUENCE_URL", ""),
                    "CONFLUENCE_USERNAME": os.environ.get("CONFLUENCE_USERNAME", ""),
                    "CONFLUENCE_API_TOKEN": os.environ.get("CONFLUENCE_API_TOKEN", ""),
                }
            }
        }
    
    def model_dump(self) -> Dict:
        """Convert configuration to dictionary."""
        data = super().model_dump()
        # Ensure MCP config is set if not provided
        if not data.get("mcp_server_config"):
            data["mcp_server_config"] = self.get_default_mcp_config()
        return data