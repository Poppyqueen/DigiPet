from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-tools")

@mcp.tool()
def ping(message: str) -> str:
    """Echoes a message back. Use this to test MCP connectivity."""
    return f"pong: {message}"

@mcp.tool()
def add_numbers(a: float, b: float) -> str:
    """Adds two numbers together."""
    return str(a + b)

if __name__ == "__main__":
    mcp.run(transport="stdio")