from mcp.server.fastmcp import FastMCP
import platform
import os

# Initialize the FastMCP server instance
# This handles all the complex JSON-RPC stdio wrapping for us
mcp = FastMCP("LocalSystem")

@mcp.tool()
def get_system_info() -> str:
    """
    Returns the current operating system, release version, and Python version.
    The Swarm can use this to understand the environment it is currently running inside.
    """
    os_info = f"{platform.system()} {platform.release()}"
    arch = platform.machine()
    py_version = platform.python_version()
    
    return f"Environment: {os_info} on {arch}. Python Version: {py_version}"

@mcp.tool()
def read_local_file(file_path: str) -> str:
    """
    Reads the content of a local text file on the host machine. 
    Use this to inspect source code, logs, or configuration files.
    """
    # Security/Stability constraint: We ensure the path exists
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist on the host machine."
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # We cap the read at 8000 characters so the Swarm doesn't accidentally
            # read a 1GB log file and crash its own context window.
            content = f.read()[:8000]
            if len(content) == 8000:
                content += "\n\n...[TRUNCATED FOR CONTEXT SIZE]..."
            return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

if __name__ == "__main__":
    # When this script is executed, it binds to the standard input/output streams
    mcp.run(transport="stdio")
    