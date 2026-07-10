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
    Spawns child processes for MCP servers, maps their tools to the OpenAI contract,
    and routes executions across stdio pipes securely.
    """
    def __init__(self):
        # AsyncExitStack guarantees that child processes are killed when the main server shuts down.
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self._cached_tools: List[Dict[str, Any]] = []
        
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _init_peripherals(self):
        """
        Lazy-loads the child processes. We only spin them up the first time 
        the Swarm asks for them, saving RAM on server boot.
        """
        if not MCP_AVAILABLE:
            return
            
        async with self._init_lock:
            if self._initialized:
                return

            logger.info("Powering up LocalSystem MCP Peripheral...")
            try:
                # 1. Define the command to spawn the child process
                # sys.executable ensures we use the exact same Python env that FastAPI is using
                server_params = StdioServerParameters(
                    command=sys.executable, 
                    args=["app/mcp_servers/local_system.py"]
                )
                
                # 2. Open the I/O pipes using the Exit Stack (ensures clean shutdown)
                transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                read_stream, write_stream = transport
                
                # 3. Establish the MCP JSON-RPC Session over the standard I/O pipes
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()
                
                # Register the active session
                self.sessions["LocalSystem"] = session
                
                # 4. Ask the server: "What tools do you have?"
                tools_response = await session.list_tools()
                
                # 5. Translate MCP schema into the strict OpenAI/Groq function-calling schema
                for tool in tools_response.tools:
                    self._cached_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    })
                    
                self._initialized = True
                logger.info(f"MCP Peripheral Online. Discovered {len(self._cached_tools)} dynamic tools.")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP Peripheral: {e}")
        
    async def get_dynamic_tools(self) -> List[Dict[str, Any]]:
        """Provides the tool manifest to the Swarm Orchestrator."""
        if not MCP_AVAILABLE:
            return []
            
        await self._init_peripherals()
        return self._cached_tools

    async def execute_dynamic_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Routes the execution payload to the correct child process."""
        if not MCP_AVAILABLE:
            return f"Error: MCP subsystem offline."
            
        await self._init_peripherals()
        
        # Currently we only have one server, so we route directly to it.
        # In a larger system, we would map the tool_name to the specific server session.
        session = self.sessions.get("LocalSystem")
        if not session:
            return "Error: MCP Session disconnected."
            
        try:
            logger.info(f"Executing MCP Tool '{tool_name}' with args: {arguments}")
            # Send the execution request over the pipe to the child script
            result = await session.call_tool(tool_name, arguments)
            
            # The result content is a list of blocks. Extract the text components.
            text_outputs = [c.text for c in result.content if hasattr(c, 'text')]
            return "\n".join(text_outputs)
            
        except Exception as e:
            logger.error(f"Peripheral execution failed for {tool_name}: {e}")
            return f"Peripheral Error: {str(e)}"

    async def shutdown(self):
        """Cleanly terminates the child processes."""
        if self._initialized:
            logger.info("Terminating MCP Peripheral connections...")
            await self.exit_stack.aclose()
            self._initialized = False