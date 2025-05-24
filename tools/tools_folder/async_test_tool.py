# Test for async functions
import asyncio
import datetime

# --- NEW: Simple Async Example Tool ---
async def simulate_data_fetch(query: str, delay: int = 2) -> str:
    """
    Simulates fetching data from an external source asynchronously.
    The delay parameter determines how many seconds the fetch takes.
    """
    print(f"Simulating data fetch for query: '{query}' (waiting {delay} seconds)...")
    await asyncio.sleep(delay) # Simulate network latency or heavy computation
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = f"Data for '{query}' fetched successfully at {timestamp}. Simulated delay: {delay}s."
    print(f"Simulated data fetch completed for query: '{query}'")
    return result
