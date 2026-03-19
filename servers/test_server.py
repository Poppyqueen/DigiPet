from mcp.server.fastmcp import FastMCP

# We give it a name and version so the inspector can find it
mcp = FastMCP("Enhanced-Test-Server")

# --- TOOLS ---
@mcp.tool()
def ping(message: str) -> str:
    """Echoes a message back. Use this to test MCP connectivity."""
    return f"pong: {message}"

@mcp.tool()
def add_numbers(a: float, b: float) -> str:
    """Adds two numbers together."""
    return str(a + b)

# --- PROMPTS ---

@mcp.prompt()
def daily_reminder() -> str:
    """A simple prompt template with no arguments."""
    return "This is your daily reminder to stay hydrated and take breaks!"

@mcp.prompt()
def say_hello(your_name: str) -> str:
    """A prompt template to set up the agent as a code reviewer."""
    return f"Hello, {your_name}! Isn't everything amazing?"

# --- RESOURCES ---
@mcp.resource("config://settings")
def get_config() -> str:
    """A static configuration resource."""
    return '{"debug": true, "timeout": 30, "api_version": "v1"}'

@mcp.resource("memo://daily-note")
def daily_note() -> str:
    """A dynamic resource example."""
    return "Remember to check the MCP logs for discovery errors!"

if __name__ == "__main__":
    mcp.run(transport="stdio")