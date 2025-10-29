#!/usr/bin/env python3
"""
Example usage of the Enterprise Multi-Agent Research System
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enterprise_multi_agent import research_with_enterprise_tools


async def example_simple_research():
    """Simple research example"""
    print("=" * 80)
    print("EXAMPLE 1: Simple Research Query")
    print("=" * 80)
    
    query = "Find information about VIT-60872"
    
    result = await research_with_enterprise_tools(
        query=query,
        stream_output=True
    )
    
    print("\n" + "=" * 80)
    print("FINAL REPORT:")
    print("=" * 80)
    print(result["final_report"])


async def example_complex_research():
    """Complex multi-source research example"""
    print("=" * 80)
    print("EXAMPLE 2: Complex Multi-Source Research")
    print("=" * 80)
    
    query = """
    Research VIT-60872 and MTV2005:
    1. Find all related Perforce changelists
    2. Identify linked JIRA issues
    3. Locate relevant Confluence documentation
    4. Analyze the relationships between these items
    """
    
    result = await research_with_enterprise_tools(
        query=query,
        stream_output=True
    )
    
    return result


async def example_secondary_expansion():
    """Slide-driven 360° secondary search example"""
    print("=" * 80)
    print("EXAMPLE 3: 360° Secondary Search Expansion")
    print("=" * 80)
    
    query = """
    Investigate customer/v1/updateAccount:
    - Identify related changelists and documentation tasks
    - Cross-reference any linked knowledge base items
    - Summarize relationships across code, tickets, and docs
    """
    
    result = await research_with_enterprise_tools(
        query=query,
        stream_output=True
    )
    
    print("\n" + "=" * 80)
    print("SECONDARY SEARCH SUMMARY:")
    print("=" * 80)
    print(result["final_report"])
    
    return result


async def example_custom_configuration():
    """Example with custom configuration"""
    print("=" * 80)
    print("EXAMPLE 4: Custom Configuration")
    print("=" * 80)
    
    # Custom MCP configuration
    custom_config = {
        "enterprise_server": {
            "command": "python",
            "args": ["src/mcp/enterprise_mcp_server.py"],
            "transport": "stdio",
            "env": {
                # Override with custom settings if needed
                "P4PORT": "custom-server:1666",
                # Add other custom environment variables
            }
        }
    }
    
    query = "Search for recent changes in the authentication module"
    
    result = await research_with_enterprise_tools(
        query=query,
        mcp_config=custom_config,
        stream_output=True
    )
    
    return result


async def main():
    """Run examples"""
    print("\n" + "🚀" * 40)
    print("ENTERPRISE MULTI-AGENT RESEARCH SYSTEM - EXAMPLES")
    print("🚀" * 40 + "\n")
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  WARNING: .env file not found!")
        print("Please copy .env.example to .env and fill in your credentials.")
        print("cp .env.example .env")
        return
    
    print("Choose an example to run:")
    print("1. Simple Research Query")
    print("2. Complex Multi-Source Research")
    print("3. 360° Secondary Search Expansion")
    print("4. Custom Configuration")
    print("5. Run All Examples")
    
    choice = input("\nEnter your choice (1-5): ")
    
    try:
        if choice == "1":
            await example_simple_research()
        elif choice == "2":
            await example_complex_research()
        elif choice == "3":
            await example_secondary_expansion()
        elif choice == "4":
            await example_custom_configuration()
        elif choice == "5":
            await example_simple_research()
            print("\n" + "=" * 80 + "\n")
            await example_complex_research()
            print("\n" + "=" * 80 + "\n")
            await example_secondary_expansion()
            print("\n" + "=" * 80 + "\n")
            await example_custom_configuration()
        else:
            print("Invalid choice. Please run the script again.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure:")
        print("1. Your .env file is properly configured")
        print("2. Ollama is running (ollama serve)")
        print("3. You have the required model (ollama pull qwen3:30b-a3b)")
        print("4. Your enterprise credentials are correct")


if __name__ == "__main__":
    asyncio.run(main())
