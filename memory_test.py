

import os

from memory.memory_handle import memory_manager

# --- Setup ---
# Define unique filepaths for this test run to avoid conflicts
test_main_mem_file = "test_main_memory.json"
test_deep_mem_file = "test_deep_memory.json"

# Clean up previous test files if they exist
if os.path.exists(test_main_mem_file): os.remove(test_main_mem_file)
if os.path.exists(test_deep_mem_file): os.remove(test_deep_mem_file)

print(f"--- Initializing Memory Manager ---")
# Assumes ai_handle.py and pydantic_models.py exist and are functional
# If ai_handle.py needs setup (like API keys), ensure that's handled.
test_main_mem_file = os.path.join("sub_directory", test_main_mem_file)

try:
    memory_system = memory_manager(
        filepath=test_main_mem_file,
        deep_memory_filepath=test_deep_mem_file,
        sub_directory="test_memory/"
    )
except ImportError as e:
    print(f"FATAL: Could not import dependencies ({e}). Exiting example.")
    exit()
except Exception as e:
    print(f"FATAL: Could not initialize memory_manager ({e}). Exiting example.")
    exit()


# --- Basic Memory Operations ---
print("\n--- Populating Short-Term Memory ---")
memory_system.save_to_memory("User said hello.", "short_term", "user")
memory_system.save_to_memory("Assistant responded cordially.", "short_term", "assistant")
memory_system.save_to_memory("User asked about the weather in London.", "short_term", "user")
memory_system.save_to_memory("Assistant mentioned it's rainy.", "short_term", "assistant")

print("\n--- Populating Long-Term Memory ---")
memory_system.save_to_memory("Key fact: Project 'Phoenix' started last month.", "long_term")
memory_system.save_to_memory("Reminder: Follow up with Dr. Aris.", "long_term")

print("\n--- Setting Base Memory ---")
memory_system.save_to_memory("The AI's name is Oracle. It aims to be helpful.", "base_memory")

print("\n--- Memory Structure Before Checks (Formatted) ---")
print(memory_system.get_memory_structure(formatted=True))

# --- Deep Memory Operations (Requires functional AI) ---
# Note: These depend heavily on the AI's ability to extract NER correctly.
# Mocking the AI would be needed for reliable unit tests.
if memory_system.deep_memory:
    # Create deep memory based on the current state
    memory_system.create_deep_memory()

    # Search deep memory
    # The AI needs to identify searchable terms (like 'London', 'Project Phoenix', 'Dr. Aris')
    # from the current memory context when search_deep_memory is called.
    found_excerpts = memory_system.search_deep_memory()
    if found_excerpts:
        print("\n--- Excerpts Found in Deep Memory ---")
        for excerpt in found_excerpts:
            print(f"- {excerpt}")
    else:
        print("\n--- No Excerpts Found in Deep Memory (or search terms not identified) ---")
else:
    print("\n--- Deep Memory Operations Skipped (DeepMemory not initialized) ---")


# --- Memory Check and Summarization (Requires functional AI) ---
print("\n--- Running Memory Check (will summarize if thresholds met) ---")
# Add more entries to potentially trigger summarization
print("Adding more short-term entries...")
for i in range(memory_system.SHORT_TERM_THRESHOLD):
    memory_system.save_to_memory(f"Filler message {i+1}", "short_term", "user" if i % 2 == 0 else "assistant")

print("Adding more long-term entries...")
for i in range(memory_system.LONG_TERM_THRESHOLD):
    memory_system.save_to_memory(f"Filler long-term note {i+1}", "long_term")

# Run the check - this might call the AI multiple times if thresholds are hit
memory_system.check()

print("\n--- Memory Structure After Check (Formatted) ---")
print(memory_system.get_memory_structure(formatted=True))

# --- Optional: Final Deep Memory Update & Search after Check ---
if memory_system.deep_memory:
    print("\n--- Running Deep Memory Create/Update Again After Check ---")
    memory_system.create_deep_memory() # Update with summarized info potentially

    print("\n--- Running Deep Memory Search Again After Check ---")
    found_excerpts_after = memory_system.search_deep_memory()
    if found_excerpts_after:
        print("\n--- Excerpts Found in Deep Memory (After Check) ---")
        for excerpt in found_excerpts_after:
            print(f"- {excerpt}")
            continue
    else:
        print("\n--- No Excerpts Found in Deep Memory (After Check) ---")

print("\n--- Example Run Finished ---")

# Optional: Clean up test files
# print("\nCleaning up test files...")
# if os.path.exists(test_main_mem_file): os.remove(test_main_mem_file)
# if os.path.exists(test_deep_mem_file): os.remove(test_deep_mem_file)