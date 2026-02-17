# command_translator.py
# Lightweight command translation using existing LLM client infrastructure
# used only for the user interface api

import json
from typing import List, Dict, Any

from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse
from ai_managers.ai_utils.ai_loader import AIConfiguration
from utils.pydantic_models import StructuredMemory, UserMessage

# TODO: refactor this, use the ai_handle that chatbot_api uses

class CommandTranslator:
    """
    Uses a small, fast LLM to translate natural language user commands 
    into structured function calls.
    
    Leverages existing AbstractLLMClient infrastructure but bypasses 
    memory/recursion complexity - single-shot translation only.
    """
    
    TRANSLATION_SYSTEM_PROMPT = """You are a command interpreter for a text adventure game.

Your ONLY job: Convert natural language into function calls from the available tools.

Rules:
- ONLY call functions that exist in the available tools list
- Use the current game context to resolve ambiguity (e.g., "eat apple" requires apple in inventory)
- Call multiple functions in the same turn when the user implies multiple actions
- Be interpretive on the user's intent, but do not make up functions or arguments
- You are a traditional text adventure game interpreter in steroids, the user should feel like you are reading their mind
- Even if certain actions seem impossible to you on the current context, call functions based on the user intent, the system will handle the error response
- If the user asks for something that requires no functions, just return an empty list []
Examples:
"go to the kitchen" → set_current_room(room_id="kitchen")
"pick up apple and eat it" → move_item_to_player(item_name="apple") + consume_item(item_name="apple")
"what's here?" → list_items_in_room() + (any examine or inspect functions for items in the room)

Current context and available tools will be provided with each request."""

    NARRATIVE_SYSTEM_PROMPT = """You are the narrator of a text adventure game (Zork-style).

Generate natural, immersive responses based on:
- The user's original command
- Which functions were executed (if any)
- The results of those functions
- The current game state

Guidelines:
- Be concise (1-3 sentences)
- Use second person ("You walk into...")
- Reference actual function results
- If functions failed, explain naturally
- Match classic text adventure tone

Examples:
Command: "go to kitchen" | Executed: set_current_room(success)
→ "You walk into the kitchen. The aroma of spices hangs in the air."

Command: "eat apple" | Executed: consume_item(+30 fullness)
→ "You bite into the crisp apple. Delicious! You feel satisfied."

Command: "fly to moon" | Executed: none
→ "You can't do that here."
"""

    def __init__(self, config_manager, functions_builder, text_capture):
        
        self.functions_builder = functions_builder
        self.text_capture = text_capture
        act_model = config_manager.get_config('AI','general_model')
        config_selected_provider = config_manager.get_config('AI','general_ai_provider')
        
        self.llm_client: AbstractLLMClient = AIConfiguration(
            provider=config_selected_provider,
            model=act_model,
            mode="agent"
        ).get_client()
        
        self.model_name = act_model

        print(f"CommandTranslator initialized with {act_model}")

    async def translate_to_functions(self, user_input: str, current_context: dict) -> List[Dict[str, Any]]:
        """
        Translate natural language → function calls using the LLM's native tool calling.
        
        This uses the SAME mechanism as the agent (AbstractLLMClient with tools),
        but in a single-shot fashion without memory or recursion.
        
        Args:
            user_input: Raw user text (e.g., "go to kitchen and grab apple")
            current_context: Current game state (room, items, stats)
            
        Returns:
            List of function call dicts: [{"name": "func", "args": {...}}, ...]
        """
        
        # Build context message
        context_str = f"""CURRENT GAME STATE:
- Context: {current_context.get('context', [])}
- Available Rooms: {current_context.get('available_rooms', [])}
USER COMMAND: {user_input}"""

        # Construct a minimal StructuredMemory (no history needed)
        structured_memory = StructuredMemory(
            system_context=self.TRANSLATION_SYSTEM_PROMPT,
            conversation_history=[
                UserMessage(type="user", content=context_str)
            ]
        )

        # Get available tools from the existing functions_builder
        tools = self.functions_builder.construct_tools()
        #print(f"Available tools: {tools}")

        try:
            # Use the SAME AbstractLLMClient.generate_response as the agent
            llm_response: LLMResponse = await self.llm_client.generate_response(
                messages=structured_memory,
                tools=tools,
                model=self.model_name,
                tool_choice="auto"  # Let LLM decide whether to call functions
            )

            # Extract function calls if present
            if llm_response.has_function_calls:
                function_calls = [
                    {
                        "name": fc.name,
                        "args": fc.arguments,
                        "call_id": fc.call_id
                    }
                    for fc in llm_response.function_calls
                ]
                
                self.text_capture.dump_text(f"Translation: '{user_input}' → {len(function_calls)} function(s)")
                return function_calls
            else:
                # No function calls = query or invalid command
                self.text_capture.dump_text(f"Translation: '{user_input}' → no functions")
                return []
                
        except Exception as e:
            print(f"Error translating command: {e}")
            self.text_capture.dump_text(f"Translation error: {e}")
            return []

    async def generate_response(self, user_input: str, execution_results: List[Dict], current_context: dict) -> str:
        """
        Generate natural language narrative response based on what happened.
        
        Args:
            user_input: Original user command
            execution_results: List of {function, args, result} dicts
            current_context: Current game state after execution
            
        Returns:
            Natural language response string
        """
        
        # Build execution summary
        if execution_results:
            results_summary = "\n".join([
                f"- {r['function']}({r['args']}) → {r['result']}"
                for r in execution_results
            ])
        else:
            results_summary = "No functions were executed (query or invalid command)"
        
        # Build context message

#         context_str = f"""USER'S COMMAND:
# {user_input}

# WHAT HAPPENED:
# {results_summary}

# CURRENT STATE:
# - Context: {current_context.get('context', [])}
# - Room Items: {', '.join(current_context.get('room_items', [])) or 'none'}
# - Available Rooms: {current_context.get('available_rooms', [])}
# - Tools info: {current_context.get('tools_info', [])['title']}
# - Tools state: {current_context.get('tools_info', [])['body']}

# Generate a narrative response (1-3 sentences):"""

        context_str = f"""USER'S COMMAND:
{user_input}

WHAT HAPPENED:
{results_summary}

CURRENT STATE:
- Context: {current_context.get('context', [])}
- Available Rooms: {current_context.get('available_rooms', [])}

Generate a narrative response (1-3 sentences):"""
# Context should contain all the previous information alonside a bit more,
# adding Available rooms manually, should think if we want to add that to the context crafter itself.
# this context grabber is shared with the agent, or bot

        # Construct minimal StructuredMemory
        structured_memory = StructuredMemory(
            system_context=self.NARRATIVE_SYSTEM_PROMPT,
            conversation_history=[
                UserMessage(type="user", content=context_str)
            ]
        )

        try:
            # Use AbstractLLMClient but with NO tools (just text generation)
            llm_response: LLMResponse = await self.llm_client.generate_response(
                messages=structured_memory,
                tools=None,  # No function calling for narrative generation
                model=self.model_name,
                tool_choice="none"
            )

            if llm_response.has_text_content:
                narrative = llm_response.text_content.strip()
                
                # Clean up common LLM wrapping artifacts
                if narrative.startswith('"') and narrative.endswith('"'):
                    narrative = narrative[1:-1]
                
                return narrative
            else:
                return "Something happened."
                
        except Exception as e:
            print(f"Error generating narrative: {e}")
            return "You did something, but the details are fuzzy."