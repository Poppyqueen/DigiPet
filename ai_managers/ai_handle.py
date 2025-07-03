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
import os
from dotenv import load_dotenv

load_dotenv()  # This loads variables from .env into os.environ

api_key = os.getenv("OPENAI_API_KEY")

# if not found stop the program
if api_key is None:
    print("API key not found. Please set the OPENAI_API_KEY environment variable.")
    exit(1)

class ai_bot:
    client=OpenAI(api_key=api_key)

    

    def __init__(self, data_filepath="captured_text.txt", act_model="gpt-4.1-mini", functions_builder=None, state_manager=None, signal=None, memory_manager=None):
        self._signal_callback=signal
        self.action_model = act_model
        self.memory_manager = memory_manager
        self.text_capture = TextCapture(filepath=data_filepath)  # Initialize text capture
        self.functions_builder = functions_builder
        self.state_manager = state_manager

    def _send_signal(self, signal_data):
        if self._signal_callback:
            print(f"House signaling: {signal_data}")
            self._signal_callback(signal_data)
        else:
            print(f"House attempted to signal, but no callback registered: {signal_data}")


        
    async def call_function(self, name, args):
        result = await self.functions_builder.call_function(name, args) # Call the function using the function builder
        return result # Return the result of the function call

    
    async def adventure_response(self, mem_structure, prompt, depth, max_depth):
            our_room= self.state_manager.get_current_room_name()

            # Here we will implement a function to get a "current state", this will be 
            # built with a module that accepts strings and saves them as a status 
            # this function here should return a string with this data.
            extra_context=self.functions_builder.construct_context()

            final_prompt = prompt + extra_context

            #print(f"📌 Final prompt for OpenAI API: {final_prompt}")

            messages_data = self.memory_manager.construct_data(mem_structure, final_prompt)
            tools = self.functions_builder.construct_tools() # Get the tools for the current room

            # Depth check for tools
            if depth >= (max_depth - 1):
                settings={
                    "model":self.action_model,
                    "input":messages_data
                }
            else:
                settings={
                    "model":self.action_model,
                    "input":messages_data,
                    "tools":tools,
                    "tool_choice":"auto"
                }


            try:
                response = self.client.responses.create( # This is a target process we can turn into a separate script in an ABC design pattern to integrate different AI providers
                    **settings
                )
                # Update notes for ABCs integration:
                
                # In theory, we would abstract away the responses structure, and maybe the function calling process, making sure each AI provider returns this response structure similar to the one we are processing now
                # It should be an openAI response structure, probably a lot of providers follow the same patters but this needs to be carefully managed by each individual provider we make for it
                # the settings parsed into it should also be managed to follow individual providers APIs documentation

                # The main task fo this function then would be to call functions and process messages as the process bellow is for the component on top of it

                # Maybe if we are going into the weeds and really changing this part of the project, we could simplify the structures it returns 
                # then we would need to update the process bellow for it to function and return the data exactly as it already does but with our simpler structures we create inside each individual provider
                time.sleep(1)
            except Exception as e:
                print(f"Error creating response: {e}")
                # Handle API errors or connection issues gracefully
                return False, f"Error communicating with model: {e}"
            



            # Initialize collectors and flags BEFORE processing the output
            function_flag = False # Use a more descriptive name
            final_text = ""
            functions_list = []

            all_text_content_parts = [] 

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

                                # We call the functions we find with this method and the arguments for each of them

                                function_result = await self.call_function(item.name, parsed_args)
                                function_array["result"] = function_result # Store successful result
                                #print(f"Function call '{item.name}' executed successfully.")


                                # Add the names of the functions in here you want to have muted for the GUI text. It will truncate the text result on the window


                                # muted_functions=["forward_ALIFE", "backward_ALIFE", "observe_ALIFE"]
                                
                                signal_message={"type": "function_called",  "function_name": f"{item.name}", "function_result": f"{function_result}"}
                                # if str(item.name) in muted_functions:
                                #     #print("📌📌📌📌📌 DEBUG FUNCTION MUTE 📌📌📌📌📌")
                                #     #print(str(item.name))
                                #     signal_message={"type": "function_called",  "function_name": f"{item.name}", "function_result": f"{function_result}", "muted": True}


                                self._send_signal(signal_message)

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
                                        all_text_content_parts.append(content_item.text)


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

                # This part returns this information to the main end of the bot which manages the main process of it (subsequent runs or memory management),
                # this is only tasked on returning information on the current response and actions from functions
                if functions_list:
                    print("Returning function call results.")
                    # Return True to indicate function calls were the primary result
                    return True, functions_list # Note this tuple return with a bool and the functions list
                # If no functions were called, check for text message
                elif all_text_content_parts:
                    print("Returning final text message.")
                    # Return False to indicate no function calls were the primary result
                    final_text = all_text_content_parts[-1]
                    return False, final_text # Note the bool and the final text return
                # If neither functions nor text were found in the output items
                else:
                    print("Response output processed, but found no function calls or text messages.")
                    return False, "No relevant output found in output items."
                
                # 

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

