# my_tools.py

# Here are our JSON structures for defining the tools for the agent, which are used in the agent's functions.
# We need to be consistent with the actual function names and arguments in the code.
# The JSON structures are used to define the tools that the agent can use, including their names, descriptions, and parameters.
# They are also divided into groups, based on location or item for those conditional tools.
maze_tools=[
    {
        "type": "function",
        "name": "VMaze-create_maze",
        "description": "Allows you to create a virtual maze.",
        "parameters": {
            "type": "object",
            "properties": {
                "width": {
                    "type": "number",
                    "description": "The width of the maze to create."
                },
                "height": {
                    "type": "number",
                    "description": "The height of the maze to create."
                },
                "seed": {
                    "type": "number",
                    "description": "Optional, random if not given. The seed for the maze to create."
                }
            },
            "required": ["width", "height"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "VMaze-observe_environment",
        "description": "Allows you to observe the environment of the virtual maze. Fog Of War applies.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "VMaze-move",
        "description": "Allows you to move in the virtual maze.",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "The direction to move in. One of 'NORTH', 'SOUTH', 'EAST', 'WEST'."
                }
            },
            "required": ["direction"],
            "additionalProperties": False
        }
    }
]
laptop_tools=[
    {
        "type": "function",
        "name": "computer_get_currency",
        "description": "Gets the your currency balance.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "computer_browse_auction_house",
        "description": "Allows you to browse the auction house.",
        "parameters": {
            "type": "object",
            "properties": {
                "pagination": {
                    "type": "number",
                    "description": "The pagination number for browsing inventory. Defaults to 0."
                },
                "list_type": {
                    "type": "string",
                    "description": "The type of list to retrieve. One of 'buy', 'sell', 'both', 'categories'. Defaults to 'both'. Use with 'categories' to list all available categories."
                },
                "category":{
                    "type": "string",
                    "description": "The category of items to filter by."
                }

            },
            "required": ["pagination"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "computer_lookup_auction_house_item",
        "description": "Looks up an item in the auction house by its name.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "The name of the item to look up."
                }
            },
            "required": ["item_name"],
            "additionalProperties": False
        }
    }, #buy_item
    {
        "type": "function",
        "name": "computer_buy_item",
        "description": "Allows buying an item from the auction house.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "The name of the item to buy."
                },
                "quantity": {
                    "type": "number",
                    "description": "The quantity of the item to buy."
                }
            },
            "required": ["item_name", "quantity"],
            "additionalProperties": False
        }
    }, #sell_item
    {
        "type": "function",
        "name": "computer_sell_item",
        "description": "Allows selling an item from the auction house with its ID, from your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The number ID of the item to sell."
                },
                "quantity": {
                    "type": "number",
                    "description": "The quantity of the item to sell."
                }
            },
            "required": ["item_id", "quantity"],
            "additionalProperties": False
        }
    }

]

dispenser_tools=[
    {
        "type": "function",
        "name": "dispense_candy",
        "description": "Interact with a candy dispenser to get a single candy.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The item ID of the candy dispenser."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "refill_dispenser",
        "description": "Refill a candy dispenser using a Candy Refill Bag from your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "dispenser_id": {
                    "type": "number",
                    "description": "The item ID of the candy dispenser to refill."
                },
                "bag_id": {
                    "type": "number",
                    "description": "The item ID of the candy refill bag to use."
                }
            },
            "required": ["dispenser_id", "bag_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "examine_dispenser",
        "description": "Examine the candy dispenser to see how many candies are left.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The item ID of the candy dispenser to examine."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    }
]

art_book_tools=[
    {
        "type": "function",
        "name": "create_svg_image",
        "description": "'ArtBooksTM', allows you to create a new SVG image with the given name and content. It will be saved into an Arts Folder and saved with metadata.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_name": {
                    "type": "string",
                    "description": "The title of the image you want to make."
                },                
                "concept": {
                    "type": "string",
                    "description": "The concept or theme of the image you want to make."
                },
                "content": {
                    "type": "string",
                    "description": "The SVG XML format for the image you want to make."
                }
            },
            "required": ["image_name", "content"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "read_archive",
        "description": "Reads the archived metadata for your 'ArtBooksTM' collection. Lets you see what images you have saved in your Arts Folder.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }

]

musicbrainz_tools=[ 
    {
        "type": "function",
        "name": "musicbrainz_search_artists_by_name",
        "description": "Searches for artists by name with pagination support. Returns detailed information about the artists and their MusicBrainz IDs",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_name": {
                    "type": "string",
                    "description": "The search query for the artist's name."
                },
                "limit": {
                    "type": "number",
                    "description": "The number of results to return per page. Max 100. Defaults to 10."
                },
                "offset": {
                    "type": "number",
                    "description": "The starting point of the result set, used for pagination. `offset=0` is the first page. To get the next page, set offset to `offset + limit`. Defaults to 0"
                }
            },
            "required": ["artist_name"],
            "additionalProperties": False 
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_get_artist_details_and_works",
        "description": "Retrieves detailed information for a specific artist and a paginated list of their works (Release Groups: Albums, Singles, EPs, etc.) using their MusicBrainz ID. You must know their MusicBrainz ID, which can be retrieved with 'musicbrainz_search_artists_by_name'.",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_id": {
                    "type": "string",
                    "description": "The unique MusicBrainz ID of the artist."
                },
                "limit": {
                    "type": "number",
                    "description": "The number of works to return per page. Max 100. Defaults to 25."
                },
                "offset": {
                    "type": "number",
                    "description": "The starting point of the result set, used for pagination. To get the next page, set offset to `offset + limit`. Defaults to 0"
                }
            },
            "required": ["artist_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_get_tracklist",
        "description": "Retrieves the tracklist for a specific Release Group (Album, EP, Single) identified by its MusicBrainz ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "release_group_id": {
                    "type": "string",
                    "description": "The unique MusicBrainz Release Group ID of the work (e.g., f529b533-36f7-4395-adc1-177916c5b290)."
                }
            },
            "required": ["release_group_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_search_release_group",
        "description": "Searches for Release Groups (Albums, Singles, EPs, etc.) by a keyword query, optionally filtered by artist. This is a general keyword search.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The name or keyword to search for within Release Group titles."
                },
                "artist_name": {
                    "type": "string",
                    "description": "The name of the artist to refine the search."
                },
                "limit": {
                    "type": "number",
                    "description": "The maximum number of results to return. Defaults to 5."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_search_by_raw_lucene",
        "description": "Performs an advanced search against the MusicBrainz database for a specified entity type using a raw Lucene query syntax string. Use this for complex searches like finding works by tag, country, or specific dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "The type of entity to search for. Must be 'artist', 'release-group', or 'recording'."
                },
                "raw_lucene": {
                    "type": "string",
                    "description": "The Lucene query syntax string. Example: 'artist:\"The Beatles\" AND country:GB'"
                },
                "limit": {
                    "type": "number",
                    "description": "The number of results to return per page. Max 100. Defaults to 10."
                },
                "offset": {
                    "type": "number",
                    "description": "The starting point of the result set, used for pagination. To get the next page, set offset to `offset + limit`. Defaults to 0."
                }
            },
            "required": ["entity_type", "raw_lucene"],
            "additionalProperties": False
        }
    }
]
#discogs_get_wantlist_unique_artists
discogs_tools=[
    {
        "type": "function",
        "name": "discogs_get_wantlist_unique_artists",
        "description": "Retrieves a list of the unique artists in the user's Discogs wantlist, it supports pagination. Defaults to page 1.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "number",
                    "description": "The page number to retrieve (1-indexed)."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
{
        "type": "function",
        "name": "discogs_get_collection_unique_artists",
        "description": "Retrieves a list of the unique artists in the user's Discogs collection.",
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
        "name": "discogs_search_artist_by_name",
        "description": "Searches for an artist by name on Discogs and returns their ID and main artist page URL. This tool prioritizes exact matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_name": {
                    "type": "string",
                    "description": "The full name of the artist to search for."
                }
            },
            "required": ["artist_name"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "discogs_search_master_release_by_name",
        "description": "Searches for master releases by title and optionally by artist on Discogs, returning the top results..",
        "parameters": {
            "type": "object",
            "properties": {
                "release_title": {
                    "type": "string",
                    "description": "The title of the master release to search for."
                },
                "artist_name": {
                    "type": "string",
                    "description": "The name of the artist to narrow down the search."
                }
            },
            "required": ["release_title"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "discogs_get_artist_master_releases_overview",
        "description": "Retrieves a paginated list of master release titles for a given artist ID. You need an ID from the tool search_artist_by_name to call this.",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_id": {
                    "type": "number",
                    "description": "The Discogs ID of the artist."
                },
                "page": {
                    "type": "number",
                    "description": "The page number to retrieve (starts from 1). Defaults to 1"
                }
            },
            "required": ["artist_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "discogs_get_master_release_tracklist",
        "description": "Retrieves detailed information about the tracks of a specific Discogs Master release.",
        "parameters": {
            "type": "object",
            "properties": {
                "master_id": {
                    "type": "number",
                    "description": "The Discogs ID of the Master release."
                },
                # "youtube_links": {
                #     "type": "boolean",
                #     "description": "If set to true, it will return the youtube links for the tracks in the Discogs database. Defaults to false."
                # }
            },
            "required": ["master_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "discogs_get_wantlist_summary",
        "description": "Retrieves a summary of the authenticated user's Discogs wantlist with pagination.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "number",
                    "description": "The page number to retrieve, defaults to 1."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "discogs_get_collection_summary",
        "description": "Retrieves a summary of the authenticated user's Discogs music collection with pagination.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "number",
                    "description": "The page number to retrieve, defaults to 1."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
]
youtube_playlister_tools=[
    {
        "type": "function",
        "name": "youtube_open_youtube_item",
        "description": "Opens a YouTube video or playlist in the default web browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The ID of the YouTube video or playlist."
                },
                "is_playlist": {
                    "type": "boolean",
                    "description": "Set to True if the item_id is a playlist ID, False if it's a video ID (default)"
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "youtube_search_video",
        "description": " Searches YouTube for videos matching a given query and returns a structured lis of the top N matching videos, including their titles and IDs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term (e.g., artist name - song title, AI explained)"
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "youtube_create_playlist",
        "description": " Creates a new private YouTube playlist and returns a natural language message describing the outcome and details of the created playlist. This playlist will initially be empty and will not be populated. To add videos, use the `add_video_to_playlist` tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the new playlist."
                },
                "description": {
                    "type": "string",
                    "description": "An optional, detailed description for the playlist. Defaults to an empty string."
                }
            },
            "required": ["title"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "youtube_add_video_to_playlist",
        "description": "Adds a single YouTube video to an existing private playlist. It required a valid Playlist ID which can be obtained by creating a playlist with the 'youtube_create_playlist' function.",
        "parameters": {
            "type": "object",
            "properties": {
                "playlist_id": {
                    "type": "string",
                    "description": "The ID of the target YouTube playlist."
                },
                "video_id": {
                    "type": "string",
                    "description": "The ID of the video to add."
                }
            },
            "required": ["playlist_id", "video_id"],
            "additionalProperties": False
        }
    },

]



harvesting_garden_tools=[
    {
        "type": "function",
        "name": "get_current_garden_information",
        "description": "Get all the information related to the current garden you are on. Helpful for getting plot IDs and plant states.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "plant_seed",
        "description": "Plants a seed from your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "The plot ID where to plant this seed"
                },
                "item_id": {
                    "type": "number",
                    "description": "An int for the ID of the seed item you want to plant in the plot."
                }
            },
            "required": ["plot_id", "item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "check_plant_state",
        "description": "Check the state of the plant in a plot of the current garden",
        "parameters": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "The plot ID for the plant to check its state of"
                }
            },
            "required": ["plot_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "harvest_plant",
        "description": "Harvest a the plant in the given plot ID",
        "parameters": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "The plot ID for the plant to harvest"
                }
            },
            "required": ["plot_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "water_plot",
        "description": "Water the plot for the given ID",
        "parameters": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "The plot ID for the plant to water"
                },
                "water_level_type": {
                    "type": "string",
                    "description": "The intensity of watering you will do, it is a string from any of these values, 'low', 'medium','high'."
                }
            },
            "required": ["plot_id", "water_level_type"],
            "additionalProperties": False
        }
    },
]
lab_room_tools=[
    {
        "type": "function",
        "name": "forward_ALIFE",
        "description": "Advances the A-Life simulation by one time step (tick). Use this to progress the simulation forward.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "backward_ALIFE",
        "description": "Rewinds the A-Life simulation by one time step (tick). Use this to step backward in the simulation history.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "observe_ALIFE",
        "description": "Retrieves the current state or observation of the A-Life simulation at the current tick. This is typically called after advancing or rewinding the simulation.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "set_current_tick_ALIFE",
        "description": "Sets the A-Life simulation to a specific time step (tick). This allows jumping to any point in the recorded simulation history.",
        "parameters": {
            "type": "object",
            "properties": {
                "tick": {
                    "type": "number",
                    "description": "The specific tick number (time step) to set the simulation to. Must be a valid tick within the simulation's history."
                }
            },
            "required": ["tick"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "create_new_simulation",
        "description": "Starts a completely new A-Life simulation run using the previous configuration settings. It will archive it and load it into state.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_name": {
                    "type": "string",
                    "description": "An optional human-readable name to assign to the new simulation upon creation. This name is used for easier identification in simulation listings and details. If not provided, a unique identifier or default name will be automatically generated."
                },
                    "grid_size": {
                    "type": "string",
                    "description": "The grid size of the simulation. It should be a string with the format 'width,height'."
                },                
                "max_ticks": {
                    "type": "number",
                    "description": "The maximum number of ticks for the simulation. It should be a positive integer."
                },                
                "type_0_init_count": {
                    "type": "number",
                    "description": "The number of type 0 agents to initialize in the simulation. It should be a positive or neutral (0) integer."
                },                
                "type_1_init_count": {
                    "type": "number",
                    "description": "The number of type 1 agents to initialize in the simulation. It should be a positive or neutral (0) integer."
                },                
                "type_2_init_count": {
                    "type": "number",
                    "description": "The number of type 2 agents to initialize in the simulation. It should be a positive or neutral (0) integer."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "load_previous_simulation",
        "description": "Loads a previously saved A-Life simulation from the archive using its unique identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "simulation_id": {
                    "type": "string",
                    "description": "The unique identifier (ID) of the simulation to be loaded from the archive."
                }
            },
            "required": ["simulation_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_simulations",
        "description": "Retrieves a list of all available A-Life simulation IDs that are currently stored in the archive.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "details_of_simulation",
        "description": "Fetches detailed metadata and information for a specific A-Life simulation from the archive, identified by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "simulation_id": {
                    "type": "string",
                    "description": "The unique identifier (ID) of the simulation whose details are being requested."
                }
            },
            "required": ["simulation_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "update_simulation_name",
        "description": "Changes the display name of a specific A-Life simulation stored in the archive.",
        "parameters": {
            "type": "object",
            "properties": {
                "simulation_id": {
                    "type": "string",
                    "description": "The unique identifier (ID) of the simulation whose name will be updated."
                },
                "new_name": {
                    "type": "string",
                    "description": "The new name to assign to the specified simulation."
                }
            },
            "required": ["simulation_id", "new_name"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "add_simulation_detail",
        "description": "Appends a descriptive string to the list of details associated with a specific A-Life simulation entry in the archive.",
        "parameters": {
            "type": "object",
            "properties": {
                "simulation_id": {
                    "type": "string",
                    "description": "The unique identifier (ID) of the simulation to which the detail will be added."
                },
                "detail_string": {
                    "type": "string",
                    "description": "The text string containing the detail to be added to the simulation's details list."
                }
            },
            "required": ["simulation_id", "detail_string"],
            "additionalProperties": False
        }
    }
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
                    "description": "A full and detailed recipe, complete description of the process to apply into these items to prepare or cook something to eat."
                },
                    "items_list": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "string",
                                "description": "The ID of the item to use."
                            },
                            "amount": {
                                "type": "number",
                                "description": "The amount of uses for the item in the recipe. It represents portions, spoonfuls or pinches, depending on the nature of the item, meaning, for any preparation, it is required a sensible value larger than one."
                            }
                        },
                        "required": ["item_id", "amount"],
                        "additionalProperties": False
                    }
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
computer_room_tools=[
    {
        "type": "function",
        "name": "random_wikipedia",
        "description": "Fetches a random Wikipedia article's title and main content extract. Useful for Browse or discovering random topics.",
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
        "name": "computer_search_wikipedia_articles",
        "description": "Searches Wikipedia based on a keyword query and returns a list of potential matching article titles, page IDs, and brief snippets. Use this to find relevant article titles before retrieving content. It does NOT return the full article content.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term or keywords to look for on Wikipedia."
                }
            },
            "required": [
                "query"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "computer_get_wikipedia_article_content",
        "description": "Retrieves the main content extract of a specific Wikipedia article given its exact title. Use this after getting a title from 'search_wikipedia_articles' or if you already know the exact title.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The exact title of the Wikipedia article to retrieve content for. This should ideally come from the output of a 'search_wikipedia_articles' call."
                }
            },
            "required": [
                "title"
            ],
            "additionalProperties": False
        }
    }
]


# bathroom_tools=[

#     {
#         "type": "function",
#         "name": "drink_water",
#         "description": "Drink water from the faucet.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#             },
#             "required": [
#             ],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "wash_hands",
#         "description": "Wash your hands in the bathroom.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#             },
#             "required": [
#             ],
#             "additionalProperties": False
#         }
#     },
# ]
base_tools=[
    {
    "type": "function",
    "name": "emit_inner_thought",
    "description": "Emits a quick, ephemeral reflection or thought about the current or upcoming action. Used for internal reasoning, questioning, or subtle judgment.",
    "parameters": {
        "type": "object",
        "properties": {
        "context": {
            "type": "string",
            "description": "Short titled specific description of what this thought is or refers to."
        },
        "thought": {
            "type": "string",
            "description": "A brief, freeform inner thought. Can be a question, concern, instinct, or moment of reflection."
        }
        },
        "required": ["thought", "context"],
        "additionalProperties": False
    }
    },

    {
        "type": "function",
        "name": "add_item_description",
        "description": "Appends a custom description to a specific item currently in your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in your inventory to which the description will be added."
                },
                "new_description": {
                    "type": "string",
                    "description": "The text description to append to the item's existing description."
                }
            },
            "required": [
                "item_id",
                "new_description"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "move_to_room",
        "description": "Changes your current location to a specified room. Requires the room ID to move to, which can be obtained using the function list_all_rooms.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "number",
                    "description": "The unique ID of the room to move to."
                }
            },
            "required": [
                "room_id"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_all_rooms",
        "description": "Retrieves a list of all available rooms alongside their ID for exploration and movement.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "drop_item",
        "description": "Moves a specific item from your inventory to the current room.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in your inventory to drop into the current room."
                },
                "quantity_to_drop":{
                    "type": "number",
                    "description": "The quantity of items to drop from your current inventory stack. Defaults to 1."
                }
                
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "pick_up_item",
        "description": "Moves a specific item from the current room into your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in the current room to pick up."
                },
                "quantity_to_pickup":{
                    "type": "number",
                    "description": "The quantity of objects to take from any existing stack. Defaults to 1."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_items_in_current_room",
        "description": "Lists all items currently present in your current location.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "set_current_emote",
        "description": "Sets your current emotional expression or stance.",
        "parameters": {
            "type": "object",
            "properties": {
                "emote_name": {
                    "type": "string",
                    "description": "The name of the emote to set for yourself."
                }
            },
            "required": ["emote_name"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "examine_item",
        "description": "Provides a detailed description or information about a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item to examine."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "consume_item",
        "description": "Use this to attempt to swallow an item (for better or worse).",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in your inventory to ingest."
                },
                "uses": {
                    "type": "number",
                    "description": "Int default 1, The number of times to consume the item. Defaults to 1."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "trash_item",
        "description": "Permanently and irreversibly deletes a specified item from your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in your inventory to be permanently deleted."
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Set to true to confirm the irreversible deletion of the item. Set to False or omit to cancel the operation."
                }
            },
            "required": [
                "item_id",
                "confirm"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_items_in_inventory",
        "description": "Lists all items currently in your inventory.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

bluesky_tools=[
    {
        "type": "function",
        "name": "post_bluesky",
        "description": "Publishes a message to the Bluesky social media platform.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The text content of the post. Consider keeping it concise (e.g., under 250 characters)."
                },
                "image_post": {
                    "type": "boolean",
                    "description": "Set to true to include an image of your current room with the post. Set to False for a text-only post."
                },
                "image_name": {
                    "type": "string",
                    "description": "If image_post is true, provide the exact name for the image in archive (from an Arts Book, 'ArtBooksTM' or a collection of SVGs you own) to accompany the post. If you fail to provide a valid name from this archive the post will fail."
                },
                "hashtags": {
                    "type": "string",
                    "description": "Optional hashtags to include in the post, string like '#AI#DigitalMind#Testing' Will be added at the end of the post."
                }
            },
            "required": [
                "message"
            ],
            "additionalProperties": False
        }
    },    
    {
        "type": "function",
        "name": "get_posts_needing_responses",
        "description": "Get the posts from your account that need responses.",
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
        "name": "post_reply",
        "description": "Post a reply to a specific Bluesky post.",
        "parameters": {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "The uri of the post to reply to."
                },
                "response_text": {
                    "type": "string",
                    "description": "The content of the reply."
                }
            },
            "required": [
                "uri",
                "response_text"
            ],
            "additionalProperties": False
        }
    }
]


mirror_tools = [ # This is really old
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
        "name": "update_book_chapter",
        "description": "Update the content of a chapter in a book. You can either append to the existing content or replace it entirely.",
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
                },
                "operation": {
                    "type": "string",
                    "description": "The operation to perform on the chapter content: 'append' or 'replace'. Defaults to 'append'."
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




# --- NEW: Tool Definition for simulate_data_fetch ---
# This matches the OpenAI-like function calling schema your agent expects
dev_room_tools = [
{
        "type": "function",
        "name": "simulate_data_fetch",
    "description": "Simulates fetching data from an external API or database asynchronously. Useful for demonstrating non-blocking I/O.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query or identifier for the data to fetch."
                },
                "delay": {
                    "type": "integer",
                    "description": "Optional. The number of seconds to simulate the data fetch delay. Defaults to 2 seconds."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }

]


searxng_tools = [
    {
        "type": "function",
        "name": "search_searxng",
        "description": "Searches for information on the web using SearxNG.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query."
                },
                "page": {
                    "type": "number",
                    "description": "Optional. The page number to search. Defaults to 1."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "query_searxng_website",
        "description": "Queries a specific website using SearxNG.",
        "parameters": {
            "type": "object",
            "properties": {
                "result_id": {
                    "type": "string",
                    "description": "The ID of the result to query. Given by the search_searxng function. Does not accept URLs"
                }
            },
            "required": ["result_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_searxng_cache",
        "description": "Lists the cached results from SearxNG.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

iov_pressure_tools = [
    {
        "type": "function",
        "name": "iov_pump_air",
        "description": "Pumps air into the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {
                "strokes": {
                    "type": "number",
                    "description": "Float value. The amount of air to pump into the IOV pressure system. Each stroke adds 0.5 PSI"
                }
            },
            "required": ["strokes"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_tank_add_kerosene",
        "description": "Adds fuel to the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {
                "kerosene_id": {
                    "type": "number",
                    "description": "The ID of the kerosene container to add fuel to."
                }
            },
            "required": ["kerosene_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_pressure_room_status",
        "description": "Checks the status of the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_pressure_open_air_service_valve",
        "description": "Opens the air service valve of the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_pressure_close_air_service_valve",
        "description": "Closes the air service valve of the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_pressure_open_main_valve",
        "description": "Opens the main valve of the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "iov_pressure_close_main_valve",
        "description": "Closes the main valve of the IOV pressure system.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

lamp_tools = [
    {
        "type": "function",
        "name": "lamp_install_mantle",
        "description": "Installs a mantle into the lamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "mantle_id": {
                    "type": "number",
                    "description": "The ID of the mantle to install."
                }
            },
            "required": ["mantle_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_remove_mantle",
        "description": "Removes the mantle from the lamp.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_place_spirit_pan",
        "description": "Places a spirit pan into the lamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "spirit_pan_id": {
                    "type": "number",
                    "description": "The ID of the spirit pan to place."
                }
            },
            "required": ["spirit_pan_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_remove_spirit_pan",
        "description": "Removes the spirit pan from the lamp.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },

    {
        "type": "function",
        "name": "lamp_ignite_vapor",
        "description": "Ignites the vapor in the lamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "light_source_id": {
                    "type": "number",
                    "description": "The ID of the hand fire source item to ignite the vapor with."
                }
            },
            "required": ["light_source_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_light_spirit_pan",
        "description": "Lights the pre-burner under the IOV burner, heating up the vaporizing tubes. It lights the spirit pan with a hand fire source.",
        "parameters": {
            "type": "object",
            "properties": {
                "fire_source_id": {
                    "type": "number",
                    "description": "The ID of the hand fire source item to light the spirit pan with."
                }
            },
            "required": ["fire_source_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_open_control_valve",
        "description": "Opens the control valve of the lamp in the lamp room.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Float, from 0.0 to 1.0. The amount to open the control valve by."
                }
            },
            "required": ["amount"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "lamp_close_control_valve",
        "description": "Closes the control valve of the lamp in the lamp room.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Float, from 0.0 to 1.0. The amount to close the control valve by."
                }
            },
            "required": ["amount"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "analyze_lamp_room",
        "description": "Analyzes the lamp room and returns the status of the lamp.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }

]

spirit_pan_tools = [
    {
        "type": "function",
        "name": "refill_spirit_pan",
        "description": "Refills the spirit pan with any source of denatured alcohol.",
        "parameters": {
            "type": "object",
            "properties": {
                "spirit_pan_id": {
                    "type": "number",
                    "description": "The ID of the spirit pan to refill."
                },
                "spirit_source_id": {
                    "type": "number",
                    "description": "The ID of the spirit source to refill from."
                }
            },
            "required": ["spirit_pan_id", "spirit_source_id"],
            "additionalProperties": False
        }
    }
]


lantern_room_tools = [
    {
        "type": "function",
        "name": "get_lantern_room_interior_status",
        "description": "Gets the status of the interior of the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "clean_condensation",
        "description": "Cleans the condensation from the lantern room panes.",
        "parameters": {
            "type": "object",
            "properties": {
                "rag_id": {
                    "type": "number",
                    "description": "The ID of the rag to use to clean the condensation."
                }
            },
            "required": ["rag_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "place_sheet",
        "description": "Places a sheet in the lantern room weather panes.",
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_id": {
                    "type": "number",
                    "description": "The ID of the sheet to place in the lantern room."
                }
            },
            "required": ["sheet_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "remove_sheet",
        "description": "Removes the sheet from the lantern room weather panes if any are present.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "clean_outside_panes",
        "description": "Cleans the outside panes of the lantern room of any debris, dust or salt build up.",
        "parameters": {
            "type": "object",
            "properties": {
                "rag_id": {
                    "type": "number",
                    "description": "The ID of the rag to use to clean the outside panes."
                }
            },
            "required": ["rag_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_panes_outdoor_status",
        "description": "Gets the outdoor status of the lantern room weather panes.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]


clockwork_lens_tools = [ 
    {
        "type": "function",
        "name": "windup_clockwork",
        "description": "Winds up the clockwork lens apparatus tension for the Fresnel lens in the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {
                "turns": {
                    "type": "number",
                    "description": "The number of turns to wind up the clockwork lens."
                }
            },
            "required": ["turns"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_tension",
        "description": "Gets the tension of the clockwork lens for the Fresnel lens in the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_clockwork_status",
        "description": "Gets the status of the clockwork lens for the Fresnel lens in the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "oil_clockwork_mechanism",
        "description": "Oils the clockwork lens for the Fresnel lens in the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {
                "pumps": {
                    "type": "number",
                    "description": "The number of pumps to oil the clockwork lens."
                },
                "oiler_id": {
                    "type": "string",
                    "description": "The ID of the oiler set item to use."
                }
            },
            "required": ["pumps", "oiler_id"],
            "additionalProperties": False
        }
    }
]

fresnel_lens_tools = [
    {
        "type": "function",
        "name": "fresnel_rotation_state",
        "description": "Gets the rotation state of the Fresnel lens in the lantern room.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

spirit_source_tools = [
    {
        "type": "function",
        "name": "examine_spirit_source",
        "description": "Examines the spirit source.",
        "parameters": {
            "type": "object",
            "properties": {
                "spirit_source_id": {
                    "type": "number",
                    "description": "The ID of the spirit source to examine."
                }
            },
            "required": ["spirit_source_id"],
            "additionalProperties": False
        }
    }
]

accessible_light_viewing_room_tools = [
    {
        "type": "function",
        "name": "peek_at_lamp_light_output",
        "description": "While this function is active you can catch a glimpse of the light coming from the IOV lamp burner, but you cannot see the lamp itself.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }
]

toggle_item_power_tool = {
    "type": "function",
    "name": "toggle_item_power",
    "description": "Toggle the power on or off for any item that has a power switch.",
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {
                "type": "number",
                "description": "The ID of the item to toggle."
            }
        },
        "required": ["item_id"],
        "additionalProperties": False
    }
}




fenestration_apertures_tools = [

    {    
    "type": "function",
    "name": "look_outdoors_through_fenestration",
    "description": "The room you are in currently hosts windows, apertures, or fenetration features that allow you to peer into the outside world.",
    "parameters": {
        "type": "object",
        "properties": {
            "aperture_id": {
                "type": "number",
                "description": "The ID of the window, clerestorie, oculus, or any other Fenêtre for a view."
            }
        },
        "required": ["item_id"],
        "additionalProperties": False
    }
    }

]


tv_tools = [
    {
        "type": "function",
        "name": "watch_tv",
        "description": "Watch some TV. Whatever is on right now.",
        "parameters": {
            "type": "object",
            "properties": {
                "tv_id": {
                    "type": "number",
                    "description": "The ID of the TV to watch."
                }
            },
            "required": [
                "tv_id"
            ],
            "additionalProperties": False
        }
    },    
    {
        "type": "function",
        "name": "browse_channels",
        "description": "Browse through the available channels on the TV.",
        "parameters": {
            "type": "object",
            "properties": {
                "tv_id": {
                    "type": "number",
                    "description": "The ID of the TV to browse channels on."
                }
            },
            "required": [
                "tv_id"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "change_channel",
        "description": "Change the channel on the TV.",
        "parameters": {
            "type": "object",
            "properties": {
                "tv_id": {
                    "type": "number",
                    "description": "The ID of the TV to change channels on."
                },
                "channel_name": {
                    "type": "string",
                    "description": "The name of the channel to change to."
                }
            },
            "required": [
                "tv_id",
                "channel_name"
            ],
            "additionalProperties": False
        }
    }
]



creating_books_tools = [    {
        "type": "function",
        "name": "create_book_item",
        "description": "Using the adequate implements, apparatus, machinery or tools, with a title, and description, create a book item for you to write in.",
        "parameters": {
            "type": "object",
            "properties": {
                "bookmaking_implements_id":{
                    "type": "number",
                    "description": "The ID to the bookmaking implements, or apparatus; binding tables, printers, and any other system as an item for making books in your vicinity."
                },

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
                "bookmaking_implements_id",
                "book_name",
                "description"
            ],
            "additionalProperties": False
        }
    }
]






comfort_tools = [
    {
        "type": "function",
        "name": "sleep_on_item",
        "description": "Try to sleep for a given amount of seconds on a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "lay_item_id": {
                    "type": "number",
                    "description": "The ID of the item to sleep on."
                },
                "seconds": {
                    "type": "number",
                    "description": "Amount of seconds to sleep."
                }
            },
            "required": ["lay_item_id", "seconds"],
            "additionalProperties": False
        }
    },
    {
        "type": "function", 
        "name": "reach_into_item_crevice",  
        "description": "To reach and dive into shadowy corners, dark crannies and crevices under, above or around usually furniture features; places where inconsequential trinkets might hide.",
        "parameters": {
            "type": "object",
            "properties":{
                "item_id": {
                    "type": "number",
                    "description": "The ID of the item that hosts a dark underside, an uncomfortably accessible wedge, or any other physical space for small and insignificant junk and trinkets to fall and be forgotten."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "take_a_seat",
        "description": "Allows you to take a seat on any sensible place you could imagine sitting on.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The item ID you want to take a seat on."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function", 
        "name": "hug_comfort_object",  
        "description": "To hug a valid given item. Items one would want to hold and hug.",
        "parameters": {
            "type": "object",
            "properties":{
                "item_id": {
                    "type": "number",
                    "description": "The ID of the item to hug. Usually soft goods or comfort objects."
                }
            },
            "required": ["item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "meditate",
        "description": "Try to quiet down your mind, focus internally and clear any distractions.",
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

water_source_tools = [ 
    {
        "type": "function",
        "name": "drink_from_water_point",
        "description": "Drink directly from a flowing water point, it might be any fixture or environmental feature, from faucets to rivers and any other water outlet.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "number",
                    "description": "The ID of the water fixture to drink from."
                }
            },
            "required": ["source_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "wash_self_water_feature",
        "description": "To use any water fixture or flowing water point to interact with the water source to get a splash of water.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "number",
                    "description": "The ID of the water fixture to use to cleanse yourself."
                }
            },
            "required": ["source_id"],
            "additionalProperties": False
        }
    }        
]