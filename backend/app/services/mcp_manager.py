import logging
import json
import asyncio
import sys
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

# --- ARCHITECTURAL RESILIENCE ---
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not found. Swarm will run without dynamic peripheral tools. Run: pip install mcp")

class EnterpriseMCPManager:
    """
    The Peripheral Nervous System.
    Spawns MULTIPLE child processes for MCP servers, maps their tools to the OpenAI contract,
    and routes executions across stdio pipes securely.
    """
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self._cached_tools: List[Dict[str, Any]] = []
        
        # --- ARCHITECTURAL UPGRADE: The Tool Router ---
        # Maps tool_name -> server_name (e.g., "fetch_youtube_transcript" -> "YouTubeScraper")
        self._tool_to_server: Dict[str, str] = {}
        
        self._initialized = False
        self._init_lock = asyncio.Lock()

        # The Server Registry: Add new MCP scripts here to plug them into the Swarm
        self.server_registry = {
            "LocalSystem": "app/mcp_servers/local_system.py",
            "YouTubeScraper": "app/mcp_servers/youtube_scraper.py"
        }

    async def _init_peripherals(self):
        """Lazy-loads all child processes defined in the registry."""
        if not MCP_AVAILABLE:
            return
            
        async with self._init_lock:
            if self._initialized:
                return

            logger.info("Powering up Peripheral Nervous System...")
            
            # Boot every server in our registry simultaneously
            for server_name, script_path in self.server_registry.items():
                try:
                    logger.info(f"Booting MCP Server: {server_name}...")
                    server_params = StdioServerParameters(
                        command=sys.executable, 
                        args=[script_path]
                    )
                    
                    transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    read_stream, write_stream = transport
                    
                    session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
                    await session.initialize()
                    
                    self.sessions[server_name] = session
                    
                    # Ask the server: "What tools do you have?"
                    tools_response = await session.list_tools()
                    
                    # Map the tools and cache them
                    for tool in tools_response.tools:
                        self._tool_to_server[tool.name] = server_name
                        self._cached_tools.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        })
                except Exception as e:
                    logger.error(f"Failed to initialize MCP Server {server_name}: {e}")
                    
            self._initialized = True
            logger.info(f"MCP Peripheral Online. Discovered {len(self._cached_tools)} total dynamic tools.")
        
    async def get_dynamic_tools(self) -> List[Dict[str, Any]]:
        """Provides the tool manifest to the Swarm Orchestrator."""
        if not MCP_AVAILABLE:
            return []
        await self._init_peripherals()
        return self._cached_tools

    async def execute_dynamic_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Routes the execution payload to the exact child process that owns the tool."""
        if not MCP_AVAILABLE:
            return f"Error: MCP subsystem offline."
            
        await self._init_peripherals()
        
        # 1. Find which server owns this tool
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return f"Error: Tool '{tool_name}' is not registered to any active MCP server."
            
        # 2. Get that server's active communication pipe
        session = self.sessions.get(server_name)
        if not session:
            return f"Error: MCP Session for '{server_name}' disconnected."
            
        try:
            logger.info(f"Routing '{tool_name}' to Server '{server_name}'...")
            result = await session.call_tool(tool_name, arguments)
            text_outputs = [c.text for c in result.content if hasattr(c, 'text')]
            return "\n".join(text_outputs)
            
        except Exception as e:
            logger.error(f"Peripheral execution failed for {tool_name} on {server_name}: {e}")
            return f"Peripheral Error: {str(e)}"

    async def shutdown(self):
        if self._initialized:
            logger.info("Terminating MCP Peripheral connections...")
            await self.exit_stack.aclose()
            self._initialized = False

global_mcp_manager = EnterpriseMCPManager()
