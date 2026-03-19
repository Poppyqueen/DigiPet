# ai_handle.py (modified)

import time

# Import utils (assuming these remain the same)
from utils.capture_text import TextCapture


# New imports for abstraction
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient
from ai_managers.agents.agents_utils.llm_response_types import LLMResponse # Import the new structure


class ai_bot:

    def __init__(self, data_filepath="captured_text.txt", act_model="gpt-5-mini", 
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
    async def ai_response(self, mem_structure, depth, max_depth, developer_message=None): #TODO: Document the mem_structure parameter, it does not equal to the StructuredMemory object
            extra_context=""
            if developer_message:
                extra_context=developer_message

            current_context = await self.functions_builder.construct_context()
            extra_context = f"{extra_context}\n{current_context}"

            # this is logging
            extra_context_message=f"##########\n Current system state: \n{extra_context}"
            self.text_capture.dump_text(extra_context_message)
            extra_context_message=f"\n##########\n"
            ##

            if self.memory_manager.deep_memory_flag:
                print("Deep Memory Flag detected")
                deep_memory_context=self.memory_manager.deep_memory.quick_search_optimized(mem_structure, False, current_context) # Leave as false, set as false will use a quick method of memory using embeddings that is much more efficient than using the LLM from the setting on True

                extra_context=f"#####Deep past memories: \n{deep_memory_context}\n End of deep past memories.#####" + extra_context

            final_prompt = extra_context

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
                self.text_capture.dump_text("########\n")
                self.text_capture.dump_text("LLM RESPONSE:\n")
                self.text_capture.dump_text(str(llm_response))
                self.text_capture.dump_text("\n########")


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
                    function_array = {
                        "function_name": fc_details.name,
                        "arguments": fc_details.arguments, 
                        "result": "Function call processing failed",
                        "call_id": fc_details.call_id,
                        # ✅ CRITICAL: Ensure this is passed into the dictionary that gets saved to memory
                        "thought_signature": fc_details.thought_signature 
                    }

                    try:
                    
                        function_result = await self.call_function(fc_details.name, fc_details.arguments)
                        function_array["result"] = str(function_result)
                        function_array["call_id"] = fc_details.call_id

                        self.text_capture.dump_text("########\n")
                        self.text_capture.dump_text("FUNCTION RESPONSE:\n")
                        self.text_capture.dump_text(F"Function Name:\n{fc_details.name}")
                        self.text_capture.dump_text(F"Result:\n")
                        self.text_capture.dump_text(str(function_result))
                        self.text_capture.dump_text("\n########\n")

                        signal_message = {"type": "function_called", "function_name": f"{fc_details.name}", "function_result": f"{function_result}"}
                        self._send_signal(signal_message)
                    except Exception as e:
                        print(f"Error executing function {fc_details.name} with args {fc_details.arguments}: {e}")
                        function_array["result"] = f"Error executing function: {e}"
                    finally:
                        functions_list.append(function_array)
                        #print(f"This is our functions list returned from the last action: {functions_list}")
                
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