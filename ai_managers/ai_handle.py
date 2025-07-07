# ai_handle.py (modified)

import time

# Import utils (assuming these remain the same)
from utils.capture_text import TextCapture


# New imports for abstraction
from ai_managers.llm_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.llm_clients.llm_response_types import LLMResponse # Import the new structure



class ai_bot:

    def __init__(self, data_filepath="captured_text.txt", act_model="gpt-4.1-mini", 
                 functions_builder=None, state_manager=None, signal=None, 
                 memory_manager=None, llm_client: AbstractLLMClient = None): # Inject the abstract client
        self._signal_callback = signal
        self.action_model = act_model
        self.memory_manager = memory_manager
        self.text_capture = TextCapture(filepath=data_filepath)
        self.functions_builder = functions_builder
        self.state_manager = state_manager
        
        # New: Use the injected LLM client
        if llm_client is None:
            raise ValueError("An LLM client must be provided to ai_bot.")
        self.llm_client = llm_client

    def _send_signal(self, signal_data):
        if self._signal_callback:
            print(f"House signaling: {signal_data}")
            self._signal_callback(signal_data)
        else:
            print(f"House attempted to signal, but no callback registered: {signal_data}")

    async def call_function(self, name, args):
        result = await self.functions_builder.call_function(name, args)
        return result

    # Rename to ai_response
    async def ai_response(self, mem_structure, prompt, depth, max_depth):
            our_room = self.state_manager.get_current_room_name()
            extra_context = self.functions_builder.construct_context()
            final_prompt = prompt + extra_context
            messages_data = self.memory_manager.construct_data(mem_structure, final_prompt)
            tools = self.functions_builder.construct_tools()

            # Determine tool_choice based on depth
            tool_choice = "auto"
            if depth >= (max_depth - 1):
                tool_choice = "none" # Explicitly no tools at max depth

            try:
                # Call the abstracted LLM client to get our simplified LLMResponse
                llm_response: LLMResponse = await self.llm_client.generate_response(
                    messages=messages_data,
                    tools=tools,
                    model=self.action_model,
                    tool_choice=tool_choice # Pass tool_choice to the client
                )
                time.sleep(1) # Still keep the delay if desired
            except Exception as e:
                print(f"Error generating LLM response: {e}")
                return False, f"Error communicating with model: {e}"
            
            # --- Simplified processing based on LLMResponse ---
            function_flag = False
            functions_list = []
            final_text = ""

            if llm_response.has_function_calls:
                function_flag = True
                for fc_details in llm_response.function_calls:
                    # Reconstruct the function_array exactly as it was before
                    function_array = {
                        "function_name": fc_details.name,
                        "arguments": fc_details.arguments, # Arguments are already parsed dict
                        "result": "Function call processing failed",
                        "call_id": None
                    }

                    try:
                    
                        function_result = await self.call_function(fc_details.name, fc_details.arguments)
                        function_array["result"] = str(function_result)
                        function_array["call_id"] = fc_details.call_id
                        signal_message = {"type": "function_called", "function_name": f"{fc_details.name}", "function_result": f"{function_result}"}
                        self._send_signal(signal_message)
                    except Exception as e:
                        print(f"Error executing function {fc_details.name} with args {fc_details.arguments}: {e}")
                        function_array["result"] = f"Error executing function: {e}"
                    finally:
                        functions_list.append(function_array)
                        print(f"This is our functions list returned from the last action: {functions_list}")
                
                # IMPORTANT: Return exactly as before
                return True, functions_list
            
            elif llm_response.has_text_content:
                final_text = llm_response.text_content
                # IMPORTANT: Return exactly as before
                return False, final_text
            
            else:
                print("LLM response processed, but found no function calls or text messages.")
                # IMPORTANT: Return exactly as before
                return False, "No relevant output found in LLM response."