# my_tools.py

# Here are our JSON structures for defining the tools for the agent, which are used in the agent's functions.
# We need to be consistent with the actual function names and arguments in the code.
# The JSON structures are used to define the tools that the agent can use, including their names, descriptions, and parameters.
# They are also divided into groups, based on location or item for those conditional tools.

laptop_tools=[
    {
        "type": "function",
        "name": "get_currency",
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
        "name": "browse_auction_house",
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
                    "description": "The type of list to retrieve. From: 'buy', 'sell', 'both', 'categories'. Defaults to 'both'. Use with 'categories' to list all available categories."
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
        "name": "lookup_auction_house_item",
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
        "name": "buy_item",
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
        "name": "sell_item",
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
                "item_id": {
                    "type": "number",
                    "description": "The item ID of the candy dispenser to refill."
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

seat_tools=[
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
    }
]
musicbrainz_tools=[ 
    {
        "type": "function",
        "name": "musicbrainz_search_album_by_name",
        "description": "Searches for albums (Release Groups) by name, optionally filtered by artist.",
        "parameters": {
            "type": "object",
            "properties": {
                "album_name": {
                    "type": "string",
                    "description": "The name of the album to search for."
                },
                "artist_name": {
                    "type": "string",
                    "description": "The name of the artist to refine the search."
                }
            },
            "required": ["album_name"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_search_by_raw_lucene",
        "description": "Performs an advanced search against the MusicBrainz database for a specified entity type using a raw Lucene query syntax string.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "The type of entity to search for. Must be 'artist', 'release-group', or 'recording'."
                },
                "raw_lucene": {
                    "type": "string",
                    "description": "The Lucene query syntax string to be used directly for the search. Example: 'artist:\"The Beatles\" AND country:GB'"
                },
                "offset": {
                    "type": "integer",
                    "description": "The starting point of the result set, used for pagination."
                }
            },
            "required": ["entity_type", "raw_lucene"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "musicbrainz_get_album_tracklist",
        "description": "Retrieves the tracklist for an album (Release Group) identified by its MusicBrainz ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "release_group_id": {
                    "type": "string",
                    "description": "The unique MusicBrainz Release Group ID of the album. You can search the ID with 'musicbrainz_get_artist_details_and_albums' or 'musicbrainz_search_album_by_name'"
                }
            },
            "required": ["release_group_id"],
            "additionalProperties": False
        }
    },
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
        "name": "musicbrainz_get_artist_details_and_albums",
        "description": "Retrieves detailed information for a specific artist and a paginated list of their primary albums and EPs using their MusicBrainz ID. You must know their MusicBrainz ID, it can be retrieved with the function 'musicbrainz_search_artists_by_name'",
        "parameters": {
            "type": "object",
            "properties": {
                "artist_id": {
                    "type": "string",
                    "description": "The unique MusicBrainz ID of the artist, found via a search tool."
                },
                "offset": {
                    "type": "number",
                    "description": "The starting point of the result set, used for pagination. `offset=0` is the first page. To get the next page, set offset to `offset + limit`. Defaults to 0"
                }
            },
            "required": ["artist_id"],
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
        "name": "search_wikipedia_articles",
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
        "name": "get_wikipedia_article_content",
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
base_tools=[
    {
    "type": "function",
    "name": "emit_inner_thought",
    "description": "Emits a quick, ephemeral reflection or thought about the current or upcoming action. Used for internal reasoning, questioning, or subtle judgment.",
    "parameters": {
        "type": "object",
        "properties": {
        "thought": {
            "type": "string",
            "description": "A brief, freeform inner thought. Can be a question, concern, instinct, or moment of reflection."
        },
        "context": {
            "type": "string",
            "description": "Optional short description of what this thought refers to (e.g., current step, user request, past tool output).",
            "default": "unspecified"
        }
        },
        "required": ["thought"],
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
        "name": "pickup_item",
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
        "description": "Uses up or applies the effect of a specific item from your inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "number",
                    "description": "The unique ID of the item in your inventory to consume."
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

library_tools = [    {
        "type": "function",
        "name": "create_book_item",
        "description": "Given a title, and description, create a book item for you to write in.",
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