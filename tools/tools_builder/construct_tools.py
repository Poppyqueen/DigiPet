# construct_tools.py 
# This file is responsible for constructing the tools and their definitions for an AI agent.
# It imports necessary components from other files and defines the FunctionBuilder class.
# It includes methods to construct function mappings and tool definitions based on the current room.
# It also includes a method to call functions dynamically based on the current room and function name.
# It includes examples on room and item specific functions.

# Notes:
# The tool definitions are JSON structures, the names and order of arguments are important and need to 
# be consistent with the functions in the tools folder. This is a crucial part of the design of new tools.

# All tools end up here one way or another, if initialized from another module or imported directly for use
# all tools are included here and then passed to the AI agent


# Import necessary components from library_tools.py (and potentially other files)
# from tools_folder.functions_local import (
#     get_weather,      # Import the global functions
#     get_time,
#     send_email
# )

# Import tools and their definitions from the tools folder
# Here we can import tools that don't need to interact inside the AI agent itself or the CLI, so we can construct them directly here
from datetime import datetime
# Import the tool definitions lists
from .my_tools import base_tools, library_tools, book_tools, white_room_tools, living_room_tools, bedroom_tools, bathroom_tools, computer_room_tools, garden_room_tools, kitchen_room_tools # Import the tool definitions lists

from utils import open_meteo_handle

# Import tools 

from tools.tools_folder.bluesky_handle import bluesky_bot

from tools.tools_folder.rooms_tools import main_tools_handle

class FunctionBuilder:
    def __init__(self, state_manager=None, signal=None):
        self._signal_callback=signal
        # current_room is not strictly needed in __init__ anymore unless it affects library initialization
        # Instantiate Library and store it as an attribute of THIS instance
        self.state_manager = state_manager
        self.room_tools=main_tools_handle(self.state_manager)

        #self.emote_manager = EmoteManager(emote_folder, self._signal_callback) 
        # Create the mapping dictionary for base functions

        #self.blsky=bluesky_bot(state_manager)
        self.base_function_map = {
            #"get_weather": get_weather, # Refers to the imported global function
            #"get_time": get_time,       # Refers to the imported global function
            #"send_email": send_email,   # Refers to the imported global function

            #"list_items_in_current_room": self.room_handler.list_items_in_current_room, # Refers to the method on the injected instance
            #"get_current_emote": self.emote_manager.get_current_emote, # Refers to the method on the injected instance
            "set_current_emote": self.state_manager.set_current_emote, # Refers to the method on the injected instance
            #"get_possible_emotes": self.state_manager.get_possible_emotes, # Refers to the method on the injected instance
            # Add any other functions/methods here that are always available, keep it lean
            "move_to_room": self.state_manager.set_current_room,
            "get_all_rooms": self.state_manager.get_all_rooms,
            "examine_item": self.state_manager.get_item_details,
            "pickup_item": self.state_manager.pickup_item,
            "drop_item": self.state_manager.drop_item,
            "consume_item": self.state_manager.consume_item,
            #"sleep": self.state_manager.sleep,
            #"post_bluesky": self.blsky.post_bluesky,
            "trash_item": self.state_manager.trash_item
        }
        # self.function_map will be constructed dynamically by call_function
        self.function_map = {} # Initialize as empty or base map if you prefer

        # Store the imported tool definitions
        # Storing them here makes them accessible to construct_tools method
        self._base_tools_definitions = base_tools
        self._books_tools_definitions = book_tools
        self._library_tools_definitions = library_tools
        self._livingroom_tools_definitions = living_room_tools
        self._bedroom_tools_definitions = bedroom_tools
        self._bathroom_tools_definitions = bathroom_tools
        self._computerroom_tools_definitions = computer_room_tools
        self._gardenroom_tools_definitons = garden_room_tools
        self._whitetoom_tools_definitions = white_room_tools
        self._kitchenroom_tools_definitions = kitchen_room_tools

    def construct_map(self, current_room="library"):
        """Constructs the function mapping based on the current room and the functions available."""
        # Reset to base function map (only global functions)
        self.function_map = self.base_function_map.copy()

        # Add room-specific functions
        if current_room == "library":
            library_functions = {
                # These refer to methods on the specific self.local_library instance
                # "save_note": self.local_library.save_note,
                # "general_look_shelves": self.local_library.general_look_shelves,
                # "targeted_look_shelves": self.local_library.targeted_look_shelves,
                # "delete_note": self.local_library.delete_note,
                # "delete_shelve": self.local_library.delete_shelve,
                # "read_note": self.local_library.read_note,
                # "create_shelve": self.local_library.create_shelve,
                # "update_note": self.local_library.update_note,
                "create_book_item": self.state_manager.create_book_item
                
            }
            self.function_map.update(library_functions)
        # elif current_room == "white_room":
        #     white_room_functions = {
        #         "create_room": self.room_handler.create_room
        #     }
        #     self.function_map.update(white_room_functions)
        elif current_room == "bedroom":
            bedroom_functions={
            "sleep": self.room_tools.bedroom.sleep,
            "hug_pillow": self.room_tools.bedroom.hug_pillow
            }
            self.function_map.update(bedroom_functions)

        elif current_room == "living_room":
            livingroom_functions={
                "watch_tv": self.room_tools.living_room.watch_tv,
                "look_at_window": self.room_tools.living_room.look_at_window,
                "sit_on_couch": self.room_tools.living_room.sit_on_couch
            }
            self.function_map.update(livingroom_functions)

        elif current_room == "bathroom":
            bathroom_functions={
                "drink_water": self.room_tools.bathroom.drink_water,
                "wash_hands": self.room_tools.bathroom.wash_hands
            }
            self.function_map.update(bathroom_functions)

        elif current_room == "computer_room":
            computer_functions={
                "random_wikipedia": self.room_tools.computer.random_wikipedia
            }
            self.function_map.update(computer_functions)

        elif current_room == "garden":
            garden_functions={
                "dig_hole": self.room_tools.garden.dig_hole,
                "lay_down": self.room_tools.garden.lay_down
            }
            self.function_map.update(garden_functions)

        elif current_room == "white_room":
            white_room_functions={
                "meditate": self.room_tools.white_room.meditate
            }
            self.function_map.update(white_room_functions)

        elif current_room == "kitchen":
            kitchen_room_functions={
                "prepare_food": self.room_tools.kitchen.prepare_food
            }
            self.function_map.update(kitchen_room_functions)


        # # Items dependent functions  ## This does not work with the most recent update, needs revamp
        # if self.state_manager.verify_item_in_inventory("mirror"): # Check if the item is in the inventory
        #     # Add item-specific functions
        #     item_functions = {
        #         # "add_possible_emote": self.emote_manager.add_possible_emote
        #     }
        #     self.function_map.update(item_functions)




        if self.state_manager.list_inventory_books(True):
            # Add book-specific functions
            book_functions = {
                "list_chapters": self.state_manager.list_book_chapters,
                "add_chapter": self.state_manager.add_book_chapter,
                "read_chapter": self.state_manager.read_book_chapter,
                "delete_chapter": self.state_manager.delete_book_chapter,
                "update_chapter": self.state_manager.update_book_chapter
            }
            self.function_map.update(book_functions)


    def construct_tools(self, current_room="library"):
        """
        Constructs and returns the list of tool definitions (JSON-like structure)
        available in the current state. This list is built by filtering *all potential*
        definitions based on the functions currently present in self.function_map.
        """
        # First, build the function map for the current room and items
        self.construct_map(current_room)

        # Collect all potential tool definitions relevant to the current state
        # (without filtering by the map yet)
        all_potential_definitions = []
        all_potential_definitions.extend(self._base_tools_definitions)

        # Add room-specific definitions
        if current_room == "library":
            all_potential_definitions.extend(self._library_tools_definitions)
        # Add elif/else blocks here for other rooms and their specific tools definitions
        elif current_room == "living_room":
            all_potential_definitions.extend(self._livingroom_tools_definitions)

        elif current_room == "bedroom":
            all_potential_definitions.extend(self._bedroom_tools_definitions)

        elif current_room == "bathroom":
            all_potential_definitions.extend(self._bathroom_tools_definitions)

        elif current_room == "computer_room":
            all_potential_definitions.extend(self._computerroom_tools_definitions)

        elif current_room == "garden":
            all_potential_definitions.extend(self._gardenroom_tools_definitons)

        elif current_room == "white_room":
            all_potential_definitions.extend(self._whitetoom_tools_definitions)
        elif current_room == "kitchen":
            all_potential_definitions.extend(self._kitchenroom_tools_definitions)



        # # Add item-specific definitions
        # if self.inventory_handler and self.inventory_handler.verify_item_in_inventory("mirror"):
        #     all_potential_definitions.extend(self._mirror_tools_definitions)

        if self.state_manager.list_inventory_books(True):
             all_potential_definitions.extend(self._books_tools_definitions)

        # Now, filter the potential definitions based on which function names
        # are actually present in the constructed function_map.
        available_tools_definitions = []
        for definition in all_potential_definitions:
            # Ensure the definition has a 'name' and it exists in the current function_map
            tool_name = definition.get('name')
            if tool_name and tool_name in self.function_map:
                 available_tools_definitions.append(definition)
            # Optional: Add a print statement here if you want to see which tools are excluded
            # else:
            #     print(f"Excluding tool definition '{tool_name}' as function is not in map.")

        #print(f"Available tools definitions for current room '{current_room}': {available_tools_definitions}")


        return available_tools_definitions

    
    def construct_context(self):
        """
        Constructs and returns context for the LLM based on recent actions taken by the functions.
        This will be redundant for many functions, but it is useful for certain essential information
        that needs to be passed to the LLM every prompt, like location, inventory, etc.
        """

        # Here we are appending the context of the current room, the inventory, the items in the current room and the current emote
        # You can add any state context managed by your tools here and it will be added to the context of the LLM 
        # automatically
        # This is a list of strings that will be joined together to form the context

        # Not all functions should be included in context, only critical information should be included
        # This is passed along the system message to the LLM
        context=[]
        now = datetime.now()
        f = now.strftime("%Y-%m-%d %H:%M:%S")
        context.append(f"Current time: {f}")
        # Format the current room
        # We pass the current room
        current_room=self.state_manager.get_current_room_name()
        format_room="Currently, you are in the room: "+ current_room
        context.append(format_room)
        
        # Append already formatted context
        # Including inventory, items in current room and current emote
        context.append("#############")
        context.append("In the current room the items are:")
        context.append(self.state_manager.get_items_in_current_room())
        context.append("#############")
        context.append(self.state_manager.get_current_emote())
        context.append("#############")
        context.append(self.state_manager.get_possible_emotes())
        context.append("#############")
        context.append("In your inventory the current items are:")
        context.append(self.state_manager.get_inventory_items())

        print("Current stats:")
        print(self.state_manager.get_stats())
        context.append(self.state_manager.get_stats())

        if current_room=="garden":
            context.append(open_meteo_handle.get_full_weather())

        string_context = "\n".join(context)
        return string_context
    
        



    def call_function(self, name, args, current_room):
        """
        Calls the function mapped to the given name, considering the current room.
        """
        # Ensure the function_map is up-to-date based on the room BEFORE attempting to call.
        self.construct_map(current_room)

        # Look up the function in the map built by construct_map
        func = self.function_map.get(name)

        if func:
            try:
                print(f"Calling {name} with args: {args}")
                # Call the function using the retrieved object and unpack args
                result = func(**args) # func is either a global function or a method object
                print(f"{name} returned: {result}")
                return result
            except TypeError as e:
                # Specific error for argument mismatch
                print(f"Error calling function {name}: Argument mismatch or type error: {e}")
                return f"Error: Invalid arguments provided for function '{name}'. Details: {e}"
            except Exception as e:
                # Catch any other unexpected errors during the function's execution
                print(f"An unexpected error occurred during execution of {name}: {e}")
                return f"Error executing function '{name}'. Details: {e}"
        else:
            # Handle unknown function names for the *current* map configuration
            print(f"Warning: Attempted to call unknown function: {name} in room '{current_room}'")
            return f"Error: Unknown function '{name}' in the current room '{current_room}'"