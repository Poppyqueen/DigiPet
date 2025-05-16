# my_tools.py

# Here are our JSON structures for defining the tools for the agent, which are used in the agent's functions.
# We need to be consistent with the actual function names and arguments in the code.
# The JSON structures are used to define the tools that the agent can use, including their names, descriptions, and parameters.
# They are also divided into groups, based on location or item for those conditional tools.
lab_room_tools=[        {
        "type": "function",
        "name": "forward",
        "description": "Move forward the A-Life simulation one step.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "backward",
        "description": "Move backwards the A-Life simulation one step.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False
        }
    },  
    {
    "type": "function",
    "name": "observe",
    "description": "Get the current observation of the A-life simulation.",
    "parameters": {
        "type": "object",
        "properties": {
        },
        "required": [],
        "additionalProperties": False
    }
    },  
    {
    "type": "function",
    "name": "set_current_tick",
    "description": "Sets the current simulation tick to the given int value",
    "parameters": {
        "type": "object",
        "properties": {
            "tick": {
                "type": "number",
                "description": "A number to set the current A-life simulation tick to."
            }
        },
        "required": ["tick"],
        "additionalProperties": False
    }
    },    {
    "type": "function",
    "name": "create_new_simulation",
    "description": "Create a whole new simulation run with the previous settings. Will override current simulation.",
    "parameters": {
        "type": "object",
        "properties": {
        },
        "required": [],
        "additionalProperties": False
    }
    },  
    ]
kitchen_room_tools=[
        {
        "type": "function",
        "name": "prepare_food",
        "description": "Prepare some food with the consumable items in your inventory",
        "parameters": {
            "type": "object",
            "properties": {
                    "process": {
                    "type": "string",
                    "description": "A detailed description of the process to apply into these items to prepare or cook something to eat."
                },
                    "items_list": {
                    "type": "string",
                    "description": "A list of items IDs in your current inventory for you to process, only consumable items, the string of IDs should have a '#' as a separator, example: 10002#20002#38882"
                }
            },
            "required": ["process", "items_list"
            ],
            "additionalProperties": False
        }
    },    

]
garden_room_tools=[
        {
        "type": "function",
        "name": "dig_hole",
        "description": "Dig a hole on the garden. Maybe you find something.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },    
    {
        "type": "function",
        "name": "lay_down",
        "description": "Lay down on the garden floor for a while.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },
]

living_room_tools= [
    {
        "type": "function",
        "name": "watch_tv",
        "description": "Watch some TV. Whatever is on right now.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },    
    {
        "type": "function",
        "name": "look_at_window",
        "description": "Look at the outside world from the window.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "sit_on_couch",
        "description": "Sit on the couch for a while",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },

]

computer_room_tools=[
    {
        "type": "function",
        "name": "random_wikipedia",
        "description": "Get a random wikipedia article, it is cached for 10 minutes at a time.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },


]

bedroom_tools=[

    {
        "type": "function",
        "name": "sleep",
        "description": "Sleep for a given amount of seconds.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Amount of seconds to sleep. Try to sleep for at least a few minutes."
                }
            },
            "required": ["seconds"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "hug_pillow",
        "description": "Hug your pillow!",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },    
    {
        "type": "function",
        "name": "look_under_bed",
        "description": "Look under the bed, who knows what might be there",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },

]

bathroom_tools=[

    {
        "type": "function",
        "name": "drink_water",
        "description": "Drink water from the faucet.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "wash_hands",
        "description": "Wash your hands in the bathroom.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False
        }
    },
]
base_tools = [
    # {  # Start of the first dictionary
    #     "type": "function",
    #     "name": "get_weather",
    #     "description": "Get current temperature for a given location.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "location": {
    #                 "type": "string",
    #                 "description": "City and country e.g. Bogotá, Colombia"
    #             }
    #         },
    #         "required": [
    #             "location"
    #         ],
    #         "additionalProperties": False
    #     }
    # }, # End of the first dictionary, comma separates elements in the list
    # {  # Start of the second dictionary - THIS WAS MISSING
    #     "type": "function",
    #     "name": "get_time",
    #     "description": "Get current time for a given location.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "location": {
    #                 "type": "string",
    #                 "description": "City and country e.g. Bogotá, Colombia"
    #             }
    #         },
    #         "required": [
    #             "location"
    #         ],
    #         "additionalProperties": False
    #     }
    # },  # End of the second dictionary
    # {
    #     "type": "function",
    #     "name": "send_email",
    #     "description": "Send an email to a recipient.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "recipient": {
    #                 "type": "string",
    #                 "description": "Email address of the recipient."
    #             },
    #             "subject": {
    #                 "type": "string",
    #                 "description": "Subject of the email."
    #             },
    #             "body": {
    #                 "type": "string",
    #                 "description": "Body of the email."
    #             }
    #         },
    #         "required": [
    #             "recipient",
    #             "subject",
    #             "body"
    #         ],
    #         "additionalProperties": False
    #     }
    # },
    {
        "type": "function",
        "name": "add_item_description",
        "description": "Add your own description to an specified item currently in your inventory",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "ID for the item to add a new description to."
                },
                    "new_description": {
                    "type": "string",
                    "description": "The description to append to the current object."
                }
            },
            "required": [
                "item_id"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "move_to_room",
        "description": "Move to a specified room.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "number",
                    "description": "ID for the room to move to."
                }
            },
            "required": [
                "room_id"
            ],
            "additionalProperties": False
        }
    },
    # {
    #     "type": "function",
    #     "name": "get_current_room",
    #     "description": "Get the current room.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "check": {
    #                 "type": "boolean",
    #                 "description": "Flag to get the current room."
    #             }
    #         },
    #         "required": ["check"],
    #         "additionalProperties": False
    #     }
    # },
    {
        "type": "function",
        "name": "get_all_rooms",
        "description": "Get a list of all existing rooms.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "drop_item",
        "description": "Place an item from the inventory into the current room.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "Item name to drop from inventory to current room."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "pickup_item",
        "description": "Take an item from the current room into the inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "Item ID to take from the current room."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    # {
    #     "type": "function",
    #     "name": "list_inventory",
    #     "description": "List all items in the inventory.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "check": {
    #                 "type": "boolean",
    #                 "description": "Check if inventory is available."
    #             }
    #         },
    #         "required": ["check"],
    #         "additionalProperties": False
    #     }
    # },
    {
        "type": "function",
        "name": "get_items_in_current_room",
        "description": "List all items in the current room.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False
        }
    },
    # {
    #     "type": "function",
    #     "name": "process",
    #     "description": "Process items using any process one can imagine.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "items": {
    #                 "type": "string",
    #                 "description": "A list of items to process, separated by commas."
    #             },
    #             "process": {
    #                 "type": "string",
    #                 "description": "The process to apply to the items."
    #             }
    #         },
    #         "required": ["items", "process"],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "get_current_emote",
    #     "description": "Get the current emote in your expression.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #         },
    #         "required": [],
    #         "additionalProperties": False
    #     }
    # },
    {
        "type": "function",
        "name": "set_current_emote",
        "description": "Set the current emote to express yourself.",
        "parameters": {
            "type": "object",
            "properties": {
                "emote_name": {
                    "type": "string",
                    "description": "The name of the emote to set."
                }
            },
            "required": ["emote_name"],
            "additionalProperties": False
        }
    },
    # {
    #     "type": "function",
    #     "name": "get_possible_emotes",
    #     "description": "Get a list of possible emotes.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #         },
    #         "required": ["act"],
    #         "additionalProperties": False
    #     }
    # },
    # {
    # "type": "function",
    # "name": "thinking",
    # "description": "This function is a tool to use as a temporal notepad, to think about anything internally before acting. Helpful for you to 'think' before you act.",
    # "parameters": {
    #     "type": "object",
    #     "properties": {
    #         "input": {
    #             "type": "string",
    #             "description": "The idea, concept, planing or internal monologue, it will be returned back without modifications, but it is helpful for you to 'think' before you act."
    #         }
    #     },
    #     "required": ["input"],
    #     "additionalProperties": False
    # }
    # },
    {
        "type": "function",
        "name": "examine_item",
        "description": "Examine an item closely.",
        "parameters": {
            "type":"object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The ID of the item to examine closely."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "consume_item",
        "description": "Consume an item in your inventory.",
        "parameters": {
            "type":"object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The ID of the item from your inventory to consume."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {  # Start of the first dictionary
        "type": "function",
        "name": "post_bluesky",
        "description": "Post online to the social media 'Bluesky'.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A message to post online, less than 250 characters. 2 short sentences."
                },
                    "image_post": {
                    "type": "boolean",
                    "description": "If true, the post will include an image of the current room."
                }
            },
            "required": [
                "message",
                "image_post"
            ],
            "additionalProperties": False
        }
    },
    {  # Start of the first dictionary
        "type": "function",
        "name": "trash_item",
        "description": "This will trash and item, it will make an item completely disappear irreversibly.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The number ID of the item to delete."
                },
                    "confirm": {
                    "type": "boolean",
                    "description": "If true, confirmation to TRASH the item, (this is irreversible). If set to false, it will cancel the process."
                }
            },
            "required": [
                "item_id",
                "confirm"
            ],
            "additionalProperties": False
        }
    },

]
library_tools = [    {
        "type": "function",
        "name": "create_book_item",
        "description": "Given a title, content and a shelve name, save the note in the shelve.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_name": {
                    "type": "string",
                    "description": "Title of the book to create"
                },
                "description": {
                    "type": "string",
                    "description": "The description of the book."
                }
            },
            "required": [
                "book_name",
                "description"

            ],
            "additionalProperties": False
        }
    },
    # {
    #     "type": "function",
    #     "name": "save_note",
    #     "description": "Given a title, content and a shelve name, save the note in the shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "A shelve name to save the note in. It should be a valid shelve from the list."
    #             },
    #             "note_name": {
    #                 "type": "string",
    #                 "description": "The title of the note."
    #             },
    #             "note_content": {
    #                 "type": "string",
    #                 "description": "The content of the note."
    #             }
    #         },
    #         "required": [
    #             "shelve_name",
    #             "note_name",
    #             "note_content"

    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "general_look_shelves",
    #     "description": "A tool to look at the available shelves.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "look_at_shelves": {
    #                 "type": "boolean",
    #                 "description": "A boolean to look at the shelves."
    #             }
    #         },
    #         "required": [
    #             "look_at_shelves"

    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "targeted_look_shelves",
    #     "description": "A tool to look at the contents of a specific shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "Given a shelve name, look at the notes in it."
    #             }
    #         },
    #         "required": [
    #             "shelve_name"
                

    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "read_note",
    #     "description": "Read the full content of a note from a shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "note_name": {
    #                 "type": "string",
    #                 "description": "Read a full note from a shelve."
    #             },
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "A shelve name to read the note from. It should be a valid shelve from the list."
    #             }
    #         },
    #         "required": [
    #             "note_name",
    #             "shelve_name"

    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "create_shelve",
    #     "description": "Create a new shelve if necessary.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "Create a new shelve."
    #             }
    #         },
    #         "required": [
    #             "shelve_name"
    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "delete_note",
    #     "description": "Delete a note from a shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "note_name": {
    #                 "type": "string",
    #                 "description": "Delete a note from a shelve."
    #             },
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "A shelve name to delete the note from. It should be a valid shelve from the list."
    #             }
    #         },
    #         "required": [
    #             "note_name",
    #             "shelve_name"

    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "delete_shelve",
    #     "description": "Delete a shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "Delete a shelve."
    #             }
    #         },
    #         "required": [
    #             "shelve_name"
    #         ],
    #         "additionalProperties": False
    #     }
    # },
    # {
    #     "type": "function",
    #     "name": "update_note",
    #     "description": "Update a note in a shelve.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "shelve_name": {
    #                 "type": "string",
    #                 "description": "A shelve name to update the note in. It should be a valid shelve from the list."
    #             },
    #             "note_name": {
    #                 "type": "string",
    #                 "description": "The title of the note."
    #             },
    #             "new_content": {
    #                 "type": "string",
    #                 "description": "The new content of the note."
    #             }
    #         },
    #         "required": [
    #             "shelve_name",
    #             "note_name",
    #             "new_content"

    #         ],
    #         "additionalProperties": False
    #     }
    # }
]


mirror_tools = [
    {
        "type": "function",
        "name": "add_possible_emote",
        "description": "You are holding a mirror, while holding this mirror, you can add new emotes to your list of possible emotes.",
        "parameters": {
            "type": "object",
            "properties": {
                "emote_name": {
                    "type": "string",
                    "description": "The name of the emote to add."
                },
                "description": {
                    "type": "string",
                    "description": "A description of the emote."
                }
            },
            "required": [
                "emote_name",
                "description"
            ],
            "additionalProperties": False
        }
    }
]


book_tools = [
    {
        "type": "function",
        "name": "add_chapter",
        "description": "Add a chapter to a book.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_item_id": {
                    "type": "number",
                    "description": "The ID of the book to add a chapter to. Make sure you have read the contents of the book before manking any changes."
                },
                "chapter_title": {
                    "type": "string",
                    "description": "The title of the chapter to add, it should be a file safe name."
                },
                "content": {
                    "type": "string",
                    "description": "The content of the chapter."
                }
            },
            "required": [
                "book_item_id",
                "chapter_title",
                "content"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "delete_chapter",
        "description": "Delete a chapter from a book.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_item_id": {
                    "type": "number",
                    "description": "The ID of the book to delete a chapter from."
                },
                "chapter_title": {
                    "type": "string",
                    "description": "The title of the chapter to delete."
                }
            },
            "required": [
                "book_item_id",
                "chapter_title"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_chapters",
        "description": "List all chapters in a book so you can read them.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_item_id": {
                    "type": "number",
                    "description": "The ID of the book to list chapters from."
                }
            },
            "required": ["book_item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "read_chapter",
        "description": "Read a chapter from a book in your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_item_id": {
                    "type": "number",
                    "description": "The ID of the book to read a chapter from."
                },
                "chapter_title": {
                    "type": "string",
                    "description": "The title of the chapter to read. First, check what chapters the book you want to read has."
                }
            },
            "required": [
                "book_item_id",
                "chapter_title"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "update_chapter",
        "description": "Update a chapter in a book.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_item_id": {
                    "type": "number",
                    "description": "The ID of the book to update a chapter in."
                },
                "chapter_title": {
                    "type": "string",
                    "description": "The title of the chapter to update."
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content of the chapter."
                }
            },
            "required": [
                "book_item_id",
                "chapter_title",
                "new_content"
            ],
            "additionalProperties": False
        }
    }

]


white_room_tools = [
    {
        "type": "function",
        "name": "meditate",
        "description": "Engage in a meditation session.",
        "parameters": {
            "type": "object",
            "properties": {
                "thoughts": {
                    "type": "string",
                    "description": "Some random thoughts that come to your mind"
                }
            },
            "required": ["thoughts"],
            "additionalProperties": False
        }
    }
]   