# Item System Contract Documentation

This document is auto-generated from the Pydantic contract registry. It defines the required keys and semantic behavior for all item types.

## 1. Base Item (Global Contract)
Every item, regardless of type, must include these fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | `str` | Human-readable item name, e.g. 'Bowl of Nuts'. |
| `descriptions` | `List[str]` | One or more description strings shown to the player. |
| `static` | `bool` | True if the item cannot be logically picked up or moved by a single human, like furniture, machinery, permanent fixtures or installed work equipment. |
| `type` | `Optional` | Empty, one or more type tags from valid literals. Empty list if none of the existing types fits. Used to define, control and determine specific behaviors and required keys for the item. Standard items with no interaction do not require a types. |
| `stackable` | `bool` | Stackability is primarily driven by item size and weight, then by uniqueness. Most items are stackable except for furniture, objects larger than a human, or items that are too heavy to lift. Some truly unique items are not stackable, a specific meal is not stackable, but a red apple is stackable. |
| `quantity` | `int` | How many units are in this stack. Always 1. |
| `max_stack_size` | `Optional` | Maximum units per stack. None means unlimited. |

## 2. Specialized Item Types
When an item includes one of these strings in its `type` list, it must satisfy the following additional field requirements.

### Type: `consumable`

| Field | Type | Description |
| :--- | :--- | :--- |
| `consume_uses_left` | `int` | Logical bites or portions for consumables, dishes, bags, jars, bowls, etc. A single piece of bread has 5 bites, a full meal has 15, a milk carton has 25, etc.Set to 1 for single-bite items like single pieces of candy, chocolates, or other single-bite items. |
| `stats_edit` | `ItemStatsEdit` | You should first think 'Is this a Potentially Hazardous Food?' (raw meats, spoiled foods, etc.). If it is, all the stat edits should be negative floats ranging from -10.0 to -0.5 depending on severity. If it is not, all the stat edits should be positive floats ranging from 0.5 to 10.0.  |
| `effects` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, having a bite or consuming a portion of this item, based on consume_uses_left. Each entry on the list is an individual singular bite and narration of the experience from different angles and dimensions. |

**Examine Tool Fields:** `consume_uses_left`

### Type: `seed`
> A seed item, most of them are also consumables, they have a direct tie to a plant through its plant type, it must be always set as any of the valid literals. This seed growth and behavior are directly tied to its plant type.

| Field | Type | Description |
| :--- | :--- | :--- |
| `plant_type` | `Literal` | The plant this type of seed grows. From valid literals. Always required for seed type. |

### Type: `book`
> A book item, it can be a notebook for personal use or a publication with content, it can be empty or contain chapters. Its locked quality is determined by its use case. It varies wildly in presentation, from size, to cover art, to the color and format of the pages inside.

| Field | Type | Description |
| :--- | :--- | :--- |
| `chapters` | `List[BookChapter]` | Ordered list of chapters in this book. Empty list means the book is empty. |
| `is_locked` | `bool` | True if the book cannot be written to or edited after creation. |

### Type: `dispenser`

| Field | Type | Description |
| :--- | :--- | :--- |
| `dispenser_state` | `DispenserState` | Always set dispenser_state.contents to empty dict. Runtime manages contents. |

### Type: `candy_bag`

| Field | Type | Description |
| :--- | :--- | :--- |
| `contents` | `List[CandyBagEntry]` | List of candy items and their quantities in the bag. |

### Type: `tv`

| Field | Type | Description |
| :--- | :--- | :--- |
| `tv_state` | `TVState` | Runtime state of the TV, managed by the TV tool. |

### Type: `iov_spirit_pan`
> Made of different metals and in varying conditions and ages, they are used to hold spirit fuel to host a small flame. Usually stackable.

| Field | Type | Description |
| :--- | :--- | :--- |
| `filled` | `bool` | Whether the spirit pan currently contains spirit. |

**Examine Tool Fields:** `filled`

### Type: `spirit_source`
> A large container for spirit fuel, they come in various sizes, materials and shapes, depending on era. From wooden barrels, metal tins, to plastic containers. Usually stackable.

| Field | Type | Description |
| :--- | :--- | :--- |
| `spirit_quantity` | `float` | Amount of spirit remaining. 1.0 is full, 0.0 is empty. |

### Type: `art_book`
> These are varieties of notebooks, from E-ink drawing tablets to physical sketchbooks. They are used for drawing, sketching, and other forms of art. Covers can be made of various materials, such as paper, leather, plastic, etc.

*No unique fields required (marker type).*

### Type: `fenestration_aperture`
> These are architectural designs, ornamental, functional, furniture and static fixtures of a room, ranging from windows, skylights, light wells, clerestories to sun tubes, portholes and any others designed as apertures of a room to peer through to the outside world.

| Field | Type | Description |
| :--- | :--- | :--- |
| `accessible` | `bool` | This true or false flag represents the accessibility, and reachability for the opening fixture. It asks if it is possible to stand no more than 1 feet besides it, if so, it should be set to true. Features like raised windows or skylights and other inaccessible apertures should be set as false. |
| `outdoors_type` | `List[Literal]` | A list of outdoors types that can be seen from this aperture. From valid literals. |

### Type: `bookmaking_implements`
> This type of item holds and provides the ability to create books, from DIY carry kits for simple books, simple areas for home-made binding in workbenches, DIY enthusiasts spaces, semi-profesional apparatuses, to large machinery, or any other.

*No unique fields required (marker type).*

### Type: `meditation_aid`
> These items are meditation aid, sensory decor, ambience decorations, meaningful, unique, or personal trinkets, furniture, and other sources of relaxation, inspiration for deep thought, meditation, or other forms of mindfulness practices. From small objects like incense, cushions, windchimes, emotionally charged trinkets, to larger items like yoga mats, particularly beautiful benches, fountains, and others.

| Field | Type | Description |
| :--- | :--- | :--- |
| `meditation_aid_ambience` | `List[str]` | **Present tense** evocative descriptions of what ambience effect this specific item brings, examples range from the description of humidifiers and their soft LED illumination, to personal objects like jewerly emitting powerful courage for whoever is near it, or the entrancing soft rythm of a water fountain. |

### Type: `sleepable_spot`
> These items range from beds, couches, hammocks and some chairs to tents, sleeping bags, some rugs, or any reasonable place where one could sleep on.

| Field | Type | Description |
| :--- | :--- | :--- |
| `narrative_sleeping` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, laying down and sleeping on this item. |

### Type: `cranny_host`
> A nook, cranny, crevice, or hidden hollow within a piece of furniture or room feature that may conceal small forgotten or lost objects. The yield_pool depletes as items are pulled from it and replenishes over time via the tick system.

| Field | Type | Description |
| :--- | :--- | :--- |
| `chance` | `float` | Base probability (0.0–1.0) that a search action finds anything at all. 0.05 is a tight crevice that rarely gives up its secrets; 0.3 is an obvious cubby. |
| `yield_pool` | `float` | Current resource level of this nook (0.0–1.0). Always initialise at 1.0. Managed by the tool at runtime — decreases on a successful pull, replenishes each tick by refresh_rate up to 1.0. |
| `yield_cost` | `float` | How much yield_pool is consumed by a single successful pull. 0.25 means the nook can be harvested ~4 times before running dry. A rare, singular hiding spot might use 1.0. |
| `refresh_rate` | `float` | How much yield_pool is restored each tick. 0.1 means a fully drained nook refills over ~10 ticks. Set very low (0.01–0.05) for spots that should stay sparse for a long time. |
| `reward_options` | `List[List[Literal]]` | A list of lists. Each nested list represents a collection of types for the possible rewarded item extracted from this cranny host. Use 'dust_bunnied_gleaning' if no logical item types fit. A front-weighted random pick selects one inner list, which is then passed to the crafter as the item type constraint. Example for a cranny behind a bookshelf: [['dust_bunnied_gleaning'], ['trinket'], ['consumable'], ['trinket', 'readable']]. |
| `narrative_search` | `List[str]` | A list of **second-person, present tense** narration lines describing the physical act of reaching into or searching this nook. Each line should feel distinct — different angles of the same gesture. One is chosen at random per search. |

**Examine Tool Fields:** `yield_pool, yield_cost, refresh_rate`

### Type: `dust_bunnied_gleaning`
> Inconsequential flotsam of all sorts, the rewards of reaching into the forgotten corners and crevices of a room, such as lost buttons, discontinued coins, antique kitchen utensils, former held-close trinkets, and other defunct minutiae.

*No unique fields required (marker type).*

### Type: `seatable`
> Items like chairs, seats, stools, benches, couches, hammocks, beds, some desks, a variety of rugs, or any reasonable place where one could sit on.

| Field | Type | Description |
| :--- | :--- | :--- |
| `narrative_sitting` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, sitting on this item. |

### Type: `comfort_object`
> These items usually are soft goods, tactile comfort objects or other emotionally charged objects; plushies, blankets, pillows, dolls, or any other item that can be hugged.

| Field | Type | Description |
| :--- | :--- | :--- |
| `narrative_hug` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, hugging this item. |

### Type: `water_point`
> This type is never combined with 'consumable' type; Water points are currently functional or active, environmental features, water fixtures, water bodies, aqueous outlets, all sorts of water sources and water points, like rivers, ponds, kitchen faucets, outdoors faucets and others, ranging in safety from tainted rivers, to fresh water ponds and saline shoars, sewage outlets and kitchen fauces and more, exclusive to fixtures and large features of the environment, NEVER individual carry water sources like water bottles or glasses of water.

| Field | Type | Description |
| :--- | :--- | :--- |
| `narrative_drinking` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, taking a sip directly out of this water source. |
| `narrative_wash_self` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, different ways to wash and rinse oneself with such water source. |
| `stats_edit` | `ItemStatsEdit` | You should first think 'Is this a Potentially Hazardous Water Source?' (badly tainted rivers, sewage outlets, a saline water body, etc.). If it is, all the stat edits should be negative floats ranging from -15.0 to -0.5 depending on severity. If it is instead a fresh drinkable water source, all the stat edits should be positive floats ranging from 0.1 to 0.5. They represent a sip. |

### Type: `culinary_equipment`
> These are culinary fixtures, furniture, appliances, workstations or vessels that transform food, from salad mixers, blenders, toasters, ovens to open fires and grills, cookeries or hearths, from appliances or work areas. It strictly excludes utensils and items that are not completely self-contained for their full functional use.

| Field | Type | Description |
| :--- | :--- | :--- |
| `narrative_prepare` | `List[str]` | A list of different, separate **second-person, present tense** evocative and grounded narration lines of the phenomenal experience of, the starting interaction, first actions and first contact with this specific item. Do not mention specific ingredients, processes or outcomes, only descriptions and narratives of encountering and preparing to use such item. |

### Type: `planter_pot`
> Ellipsis

| Field | Type | Description |
| :--- | :--- | :--- |
| `capacity` | `int` | How many plant slots this pot has. A small terracotta pot has 1, a rooftop planting bed might have 3 or 4. |
| `size_multiplier` | `float` | Harvest yield multiplier at harvest time. Above 1.0 increases yield, below 1.0 reduces it. |

**Examine Tool Fields:** `capacity`

### Type: `toggleable`
> This type modifies any item so its affordances are toggleable, these items are utilities one can change their state, ranging from incense sticks to electronic devices like computers, to windows or other systems.

| Field | Type | Description |
| :--- | :--- | :--- |
| `toggle_state` | `ToggleableStates` | The initial state of a toggable item, detailing its total uses capacity, and description on either state. |

### Type: `youtube_playlists_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a Youtube account, with the ability to search for videos, create and manage playlists.

*No unique fields required (marker type).*

### Type: `discogs_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a Discogs account, with the ability to search for records, create and manage collections, and view artist information.

*No unique fields required (marker type).*

### Type: `musicbrainz_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a MusicBrainz, with a stateless implementation, it is direct access to a large music database without any accounts tied to it. It provides the ability to search for artists, albums, tracks, and view detailed information about them.

*No unique fields required (marker type).*

### Type: `bluesky_social_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a Bluesky Social account, with the ability to view and post content, with the platform's AT Protocol.

*No unique fields required (marker type).*

### Type: `wikipedia_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to Wikipedia, with a stateless implementation, it is direct access to the Wikipedia database without any accounts tied to it. It provides the ability to search and retrieve Wikipedia articles.

*No unique fields required (marker type).*

### Type: `searxng_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a Searxng instance with direct access to a meta-search engine and the ability to query found results for full website content retrieval.

*No unique fields required (marker type).*

### Type: `colab_endpoint`
> These items, usually toggleable electronic devices, are gateways to different information sources, databases, APIs, or other digital repositories of information. They affort detailed interactions, control and manipulation on the information they provide access to, and they are meant to be used as tools for information retrieval, research, or entertainment. They can be mixed and matched with other types, from handhelds to interactive furniture. This specific endpoint provides access to a Colab notebook, with the ability to execute code cells, retrieve outputs, and manage the notebook's content. It is meant to be used as a powerful tool for running custom code, data analysis, or any other task that can be accomplished within a Colab environment.

*No unique fields required (marker type).*

### Type: `maze_interface`
> Maze device or toy, it can be a physical maze box with a small ball inside, or a virtual maze on a screen. The item provides an interactive maze experience, where the user can navigate through the maze by tilting the box or using controls for the virtual version. It can be used for entertainment, stress relief, or as a cognitive exercise.

| Field | Type | Description |
| :--- | :--- | :--- |
| `stackable` | `bool` | None |
| `maze_state` | `MazeState` | The state of the maze, including the seed for generation, size, current position, goal position, and steps taken. Managed by the maze tool. |

### Type: `drawing_area`
> Digital or physical sketchbooks, drawing notebooks or paginated archives that contain images and where someone can create new entries by adding new images to it. They can be physical or digital.

| Field | Type | Description |
| :--- | :--- | :--- |
| `images_lab_uid` | `str` | Stable archive UID. Always initialise as empty string — assigned automatically by the tool on first use. |

### Type: `store_entry`
> A store entry item represents a purchasable offering in an online or physical store. It contains details about the product, such as its name, description, price, and any other relevant information that a customer would need to know before making a purchase. This type is meant to be used in conjunction with the StoreEndpointFields type, which provides access to a store's inventory and purchasing system.

| Field | Type | Description |
| :--- | :--- | :--- |
| `store_entry_data` | `StoreEntryData` | Data specific to a store entry, including price, availability, and other relevant details. Managed by the store endpoint tool. |

### Type: `store_endpoint`
> This specific endpoint provides access to an online or physical store, with the ability to browse products, view details, and make purchases. It is meant to be used as a tool for shopping and managing online purchases, and it can be mixed with other types for enhanced functionality, such as toggleable for electronics or dispensers for vending machines.

| Field | Type | Description |
| :--- | :--- | :--- |
| `store_endpoint_data` | `StoreEndpointData` | Data specific to a store endpoint, including available categories and item listings. Managed by the store endpoint tool. |