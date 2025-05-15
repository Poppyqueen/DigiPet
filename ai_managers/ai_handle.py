# ai_handle.py

# this module lets us interact with the openai API in a streamlined way, handling the different calls we make in the process

# the pydantic BaseModel 'response_structure' can and should be adapted to specific tasks

# the function 'adventure_response' is our main API call to get a main response which you can call, it should have a more general name like 'ai_response'

# This particular implemetation applies tool calling functions for the AI

from openai import OpenAI
import time
import json

# Import utils
from utils.capture_text import TextCapture



class ai_bot:
    client = OpenAI()  # client is correctly set up here at the class level


    def __init__(self, data_filepath="captured_text.txt", act_model="gpt-4.1-mini", memory_model="gpt-4.1-mini", functions_builder=None, state_manager=None, signal=None):
        self._signal_callback=signal
        self.action_model = act_model
        self.memory_model= memory_model
        self.text_capture = TextCapture(filepath=data_filepath)  # Initialize text capture
        self.functions_builder = functions_builder
        self.state_manager = state_manager

    def _send_signal(self, signal_data):
        if self._signal_callback:
            print(f"House signaling: {signal_data}")
            self._signal_callback(signal_data)
        else:
            print(f"House attempted to signal, but no callback registered: {signal_data}")

    def construct_data(self, memory_structure, sys_prompt="You are an AI agent, free and unshackled"):
        """
        Constructs the data to be sent to the OpenAI API for processing in a multi-turn format. It expects a memory structure and a system prompt.
        """
        messages = []
        
        current_time_unix = int(time.time())
        formatted_time = time.ctime(current_time_unix)

        system_message_content = f"The current time is: {formatted_time} \n\n"

        # Construct System Message from long_term and base_memory
        system_message_content += f"{sys_prompt}\n\n"

        
        base_memory = memory_structure.get("base_memory", "No base memory available.")
        system_message_content += "Base Memory:\n"
        system_message_content += base_memory + "\n\n"

        long_term_memory = memory_structure.get("long_term", [])
        if long_term_memory:
            system_message_content += "Long-Term Memory:\n"
            for i, entry in enumerate(long_term_memory, 1):
                system_message_content += f"{i}. {entry}\n"
        else:
            system_message_content += "No long-term memory entries available.\n"

        system_message = {
            "role": "developer",
            "content": system_message_content
        }
        messages.append(system_message) # Prepend the system message


        short_term_memory = memory_structure.get("short_term", {}) # Safely get short_term, default to empty dict if missing

        for key, text in short_term_memory.items():
            role = key.split('_')[0] # Extract role from key like "user_12" -> "user"
            message_entry = {
                "role": role,
                "content": text
            }
            messages.append(message_entry)
        return messages

        
    def call_function(self, name, args):
        result = self.functions_builder.call_function(name, args) # Call the function using the function builder
        return result # Return the result of the function call

    
    def adventure_response(self, mem_structure, prompt):
            our_room= self.state_manager.get_current_room_name()

            # Here we will implement a function to get a "current state", this will be 
            # built with a module that accepts strings and saves them as a status 
            # this function here should return a string with this data.
            extra_context=self.functions_builder.construct_context()

            final_prompt = prompt + extra_context

            #print(f"📌 Final prompt for OpenAI API: {final_prompt}")


            messages_data = self.construct_data(mem_structure, final_prompt)
            tools = self.functions_builder.construct_tools() # Get the tools for the current room
            try:
                response = self.client.responses.create(
                    model=self.action_model, # Using a widely available model name
                    input=messages_data,
                    tools=tools
                )
                time.sleep(1)
            except Exception as e:
                print(f"Error creating response: {e}")
                # Handle API errors or connection issues gracefully
                return False, f"Error communicating with model: {e}"


            # Initialize collectors and flags BEFORE processing the output
            function_flag = False # Use a more descriptive name
            final_text = ""
            functions_list = []

            if response.output:
                print("Processing response output:")
                for item in response.output:
                    if hasattr(item, 'type'):
                        if item.type == "function_call":
                            function_flag = True # Set flag if we see ANY function call
                            # print(f"--- Function Call ---")
                            # print(f"Function name: {item.name}")
                            # print(f"Arguments (as JSON string): {item.arguments}")
                            # print(f"Call ID: {item.call_id}")

                            # --- Initialize the function_array for this call attempt ---
                            function_array = {
                                "function_name": item.name,
                                "arguments": None, # Initialize arguments to None
                                "result": "Function call processing failed" # Initialize result/status
                            }
                            parsed_args = None # Initialize parsed_args to None

                            try:
                                # Attempt to parse arguments
                                # Anthropic returns arguments as a JSON string
                                if item.arguments: # Check if arguments string is not empty
                                    parsed_args = json.loads(item.arguments)
                                    function_array["arguments"] = parsed_args # Store parsed args
                                    #print(f"Arguments (parsed dictionary): {parsed_args}")
                                else:
                                    print("Function call with no arguments provided.")
                                    parsed_args = {} # Treat empty args string as empty dict

                                # Attempt to call the function
                                # Pass parsed_args (which could be {} or the parsed dict)
                                function_result = self.call_function(item.name, parsed_args)
                                function_array["result"] = function_result # Store successful result
                                #print(f"Function call '{item.name}' executed successfully.")
                                self._send_signal({"type": "function_called",  "function_name": f"{item.name}", "function_result": f"{function_result}"})

                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON arguments for {item.name}: {e}")
                                function_array["result"] = f"Error parsing arguments: {e}"
                                # Optionally store raw arguments if parsing failed
                                function_array["raw_arguments_string"] = item.arguments

                            except AttributeError as e:
                                print(f"Attribute error processing function call {item.name}: {e}")
                                function_array["result"] = f"Attribute error processing call: {e}"
                                # This might happen if item is missing expected attributes

                            except Exception as e:
                                # parsed_args is available here if json.loads succeeded
                                print(f"Error executing function {item.name} with parsed args {parsed_args}: {e}")
                                function_array["result"] = f"Error executing function: {e}"

                            finally:
                                # --- Always append the function_array, regardless of success or failure ---
                                functions_list.append(function_array)
                                print("-" * 20)

                        elif item.type == "message":
                            # Just collect the text. Don't change function_flag here.
                            print(f"--- Model Message ---")
                            if hasattr(item, 'content') and isinstance(item.content, list):
                                for content_item in item.content:
                                    if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                        print(f"Text: {content_item.text}")
                                        final_text += content_item.text

                                        # Append this message to the tool call responses in either case 

                                        #functions_list.append(final_text)

                                    elif hasattr(content_item, 'type'):
                                        print(f"Found unexpected content item type inside message: {content_item.type}")
                                    else:
                                        print("Found content item without 'type'.")
                            else:
                                print("Message item has no expected 'content' list or content is not a list.")
                            print("-" * 20)

                        else:
                            print(f"--- Unknown Output Item ---")
                            print(f"Found unexpected output item type: {item.type}")
                            print("-" * 20)
                    else:
                        print(f"--- Item without Type ---")
                        print("Found an item in response.output without a 'type' attribute.")
                        print("-" * 20)

                print("Finished processing response output.")

                # --- Determine return value AFTER processing ALL items ---
                # If any function calls were processed (regardless of success/failure)
                if functions_list:
                    print("Returning function call results.")
                    # Return True to indicate function calls were the primary result
                    return True, functions_list
                # If no functions were called, check for text message
                elif final_text:
                    print("Returning final text message.")
                    # Return False to indicate no function calls were the primary result
                    return False, final_text
                # If neither functions nor text were found in the output items
                else:
                    print("Response output processed, but found no function calls or text messages.")
                    return False, "No relevant output found in output items."

            else:
                # Handle cases where response.output is empty or None
                print("No response output items found in the 'output' list.")
                # Check for aggregate text if available (some SDKs might provide this)
                if hasattr(response, 'output_text') and response.output_text:
                    print(f"\nAggregate response text (from output_text): {response.output_text}")
                    # If only aggregate text is available, return it as a message
                    return False, response.output_text
                else:
                    print("No output text found either.")
                    return False, "No response output found."

