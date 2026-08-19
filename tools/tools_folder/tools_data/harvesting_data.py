# --- Item Definitions for Harvest and Seeds ---
# These items will be created and added to the inventory upon harvest or used for planting.
from inventory_items.items_provider.item_store import ItemStore

# Existing Items. Now from the store.
cc=ItemStore("inventory_items/items_provider/items_data")

# --- Plant Definitions ---


# Our main game loop is now calling a tick in a set timer, each tick is called in a minute

# Dictionary of predefined plant types and their growth stages
# Each stage defines duration in *ticks* and optimal water level range.


# Plants have different stages, they need at least the stage 'harvestable'; If they are perennial, they need a 'mature' stage. Each stage needs a tick lenght. For the harvestable stage the lenght has to be 0

# Plants have a list of nested item structures and base harvest number for each item

# Perennials revert to mature stage after harvesting, while annuals get removed from the plot directly.


# These settings need careful thought

# --- Hardiness ---
# Generalized weather-tolerance envelope per plant, in the spirit of a
# hardiness zone but keyed to live weather data instead of a fixed
# geography. temp_survivable_range is in °C; outside it, weather-driven
# stress accumulates every tick regardless of the sensitivity flags below.
# The *_sensitive flags add extra stress from specific event types even
# when the plant is still inside its survivable temperature range (e.g. a
# cactus can be at a perfectly fine temperature and still hate a downpour).
# Any plant type missing this block falls back to DEFAULT_HARDINESS —
# permissive, so forgetting to tune a new plant never makes it fragile.
DEFAULT_HARDINESS = {
    "temp_optimal_range": (10.0, 28.0),
    "temp_survivable_range": (-5.0, 40.0),
    "frost_sensitive": False,
    "wind_sensitive": False,
    "rain_sensitive": False,
}

plant_types = {
    "lettuce": {
        "stages": [
            {"name": "seedling", "duration_ticks": 10, "optimal_water_level_range": (0.8, 1.0)},
            {"name": "early_leafing", "duration_ticks": 15, "optimal_water_level_range": (0.7, 0.95)},
            {"name": "heading_up", "duration_ticks": 10, "optimal_water_level_range": (0.6, 0.9)},
            {"name": "forming_head", "duration_ticks": 20, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.8)}
        ],
        "harvest_items": [
            {"item": cc.get_item("lettuce Head"), "base_harvest_yield": 7}, # Notice, it is calling our item store and getting these harvestables, 'lettuce head', make sure that they exist if adding new plant types, or create new items, they need to be 'consumable' type, no specific harvest type yet, not sure if it is needed. 
            {"item": cc.get_item("Lettuce Seed"), "base_harvest_yield": 2}
        ],
        "life_cycle": "annual",
        "water_depletion_rate_per_tick": 0.002,
        "hardiness": {
            "temp_optimal_range": (8.0, 22.0),
            "temp_survivable_range": (-2.0, 30.0),
            "frost_sensitive": True,
            "wind_sensitive": False,
            "rain_sensitive": False,
        }
    },
    "carrot": {
        "stages": [
            {"name": "seedling", "duration_ticks": 15, "optimal_water_level_range": (0.7, 1.0)},
            {"name": "foliage_developing", "duration_ticks": 20, "optimal_water_level_range": (0.6, 0.8)},
            {"name": "early_root_swelling", "duration_ticks": 20, "optimal_water_level_range": (0.5, 0.75)},
            {"name": "root_maturing", "duration_ticks": 20, "optimal_water_level_range": (0.4, 0.7)},
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.4, 0.7)}
        ],
        "harvest_items": [
            {"item": cc.get_item("Carrot"), "base_harvest_yield": 10},
            {"item": cc.get_item("Carrot Seed"), "base_harvest_yield": 4}
        ],
        "life_cycle": "biennial",
        "hardiness": {
            "temp_optimal_range": (10.0, 24.0),
            "temp_survivable_range": (-5.0, 32.0),
            "frost_sensitive": False,
            "wind_sensitive": False,
            "rain_sensitive": False,
        }
    },
    "cactus": { # PERENNIAL - ENSURING 'mature' stage
        "stages": [
            {"name": "sprout", "duration_ticks": 30, "optimal_water_level_range": (0.1, 0.6)},
            {"name": "pad_developing", "duration_ticks": 60, "optimal_water_level_range": (0.05, 0.4)},
            {"name": "mature", "duration_ticks": 60, "optimal_water_level_range": (0.05, 0.30)}, # Renamed from 'fully_established'
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.1, 0.45)}
        ],
        "harvest_items": [
            {"item": cc.get_item("Cactus Pad"), "base_harvest_yield": 7},
            {"item": cc.get_item("Cactus Seed"), "base_harvest_yield": 3}

        ],
        "life_cycle": "perennial",
        "water_depletion_rate_per_tick": 0.009,
        "hardiness": {
            "temp_optimal_range": (18.0, 38.0),
            "temp_survivable_range": (2.0, 46.0),
            "frost_sensitive": True,
            "wind_sensitive": False,
            "rain_sensitive": True,
        }

    },

    # --- NEW PLANT DEFINITIONS ---

    "tomato": {
        "stages": [
            {"name": "sprout", "duration_ticks": 15, "optimal_water_level_range": (0.7, 1.0)},
            {"name": "vining_out", "duration_ticks": 10, "optimal_water_level_range": (0.6, 0.85)},
            {"name": "flowering", "duration_ticks": 10, "optimal_water_level_range": (0.55, 0.8)},
            {"name": "fruit_setting", "duration_ticks": 15, "optimal_water_level_range": (0.5, 0.75)},
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.75)}
        ],
        "harvest_items": [
            {"item": cc.get_item("Ripe Tomato"), "base_harvest_yield": 6},
            {"item": cc.get_item("Tomato Seed"), "base_harvest_yield": 2}
        ],
        "life_cycle": "annual",
        "hardiness": {
            "temp_optimal_range": (16.0, 29.0),
            "temp_survivable_range": (5.0, 36.0),
            "frost_sensitive": True,
            "wind_sensitive": True,
            "rain_sensitive": False,
        }
    },
    "potato": {
        "stages": [
            {"name": "sprout", "duration_ticks": 20, "optimal_water_level_range": (0.6, 1.0)},
            {"name": "foliage_developing", "duration_ticks": 25, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "tuber_forming", "duration_ticks": 40, "optimal_water_level_range": (0.4, 0.6)},
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.4, 0.6)}
        ],
        "harvest_items": [
            {"item": cc.get_item("Potato"), "base_harvest_yield": 8},
        ],
        "life_cycle": "annual",
        "hardiness": {
            "temp_optimal_range": (12.0, 24.0),
            "temp_survivable_range": (-3.0, 30.0),
            "frost_sensitive": True,
            "wind_sensitive": False,
            "rain_sensitive": False,
        }
    },
    "strawberry": { # PERENNIAL - ENSURING 'mature' stage
        "stages": [
            {"name": "sprout", "duration_ticks": 15, "optimal_water_level_range": (0.7, 1.0)},
            {"name": "spreading_foliage", "duration_ticks": 20, "optimal_water_level_range": (0.6, 0.8)},
            {"name": "budding", "duration_ticks": 15, "optimal_water_level_range": (0.55, 0.75)},
            {"name": "mature", "duration_ticks": 10, "optimal_water_level_range": (0.5, 0.75)}, # Renamed from 'fruiting', now the plant is established
            {"name": "fruit_ripening", "duration_ticks": 10, "optimal_water_level_range": (0.5, 0.7)}, # New stage for actual fruit ripening
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.7)}
        ],
        "harvest_items": [
            {"item": cc.get_item("Strawberry"), "base_harvest_yield": 6},
            {"item": cc.get_item("Strawberry Seed"), "base_harvest_yield": 2}
        ],
        "life_cycle": "perennial",
        "hardiness": {
            "temp_optimal_range": (10.0, 24.0),
            "temp_survivable_range": (-4.0, 30.0),
            "frost_sensitive": True,
            "wind_sensitive": False,
            "rain_sensitive": True,
        }
    },

# Ornamental Plants
"rose": { # PERENNIAL - ENSURING 'mature' stage
    "stages": [
        {"name": "sprout", "duration_ticks": 20, "optimal_water_level_range": (0.7, 1.0)},
        {"name": "branching_out", "duration_ticks": 30, "optimal_water_level_range": (0.6, 0.8)},
        {"name": "vegetative_growth", "duration_ticks": 20, "optimal_water_level_range": (0.55, 0.75)},
        {"name": "mature", "duration_ticks": 10, "optimal_water_level_range": (0.5, 0.7)}, # Renamed from 'budding', now the established plant
        {"name": "flowering", "duration_ticks": 10, "optimal_water_level_range": (0.5, 0.7)}, # New stage for actual bloom
        {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.7)}
    ],
    "harvest_items": [
        {"item": cc.get_item("Rose Stem"), "base_harvest_yield": 3},
        {"item": cc.get_item("Cut Rose Head"), "base_harvest_yield": 1},
        {"item": cc.get_item("Rose Seed"), "base_harvest_yield": 1},
        {"item": cc.get_item("Edible Rose Petals"), "base_harvest_yield": 6}

    ],
    "life_cycle": "perennial",
    "hardiness": {
        "temp_optimal_range": (8.0, 26.0),
        "temp_survivable_range": (-8.0, 34.0),
        "frost_sensitive": False,
        "wind_sensitive": True,
        "rain_sensitive": False,
    }
},
"sunflower": {
    "stages": [
        {"name": "seedling", "duration_ticks": 15, "optimal_water_level_range": (0.7, 1.0)},
        {"name": "stem_elongating", "duration_ticks": 25, "optimal_water_level_range": (0.6, 0.9)},
        {"name": "bud_forming", "duration_ticks": 20, "optimal_water_level_range": (0.55, 0.8)},
        {"name": "flowering", "duration_ticks": 30, "optimal_water_level_range": (0.5, 0.7)},
        {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.7)}
    ],
    "harvest_items": [
        {"item": cc.get_item("Cut Sunflower Head"), "base_harvest_yield": 1},
        {"item": cc.get_item("Sunflower Seed"), "base_harvest_yield": 3}
    ],
    "life_cycle": "annual",
    "hardiness": {
        "temp_optimal_range": (15.0, 32.0),
        "temp_survivable_range": (2.0, 40.0),
        "frost_sensitive": True,
        "wind_sensitive": True,
        "rain_sensitive": False,
    }
},

# Herbs
"mint": { # PERENNIAL - ENSURING 'mature' stage
    "stages": [
        {"name": "sprout", "duration_ticks": 10, "optimal_water_level_range": (0.7, 1.0)},
        {"name": "spreading_foliage", "duration_ticks": 15, "optimal_water_level_range": (0.6, 0.9)},
        {"name": "mature", "duration_ticks": 20, "optimal_water_level_range": (0.5, 0.8)}, # Renamed from 'lush_growth'
        {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.8)}
    ],
    "harvest_items": [
        {"item": cc.get_item("Fresh Mint Sprig"), "base_harvest_yield": 8},
        {"item": cc.get_item("Mint Seed"), "base_harvest_yield": 2}
    ],
    "life_cycle": "perennial",
    "hardiness": {
        "temp_optimal_range": (10.0, 28.0),
        "temp_survivable_range": (-6.0, 34.0),
        "frost_sensitive": False,
        "wind_sensitive": False,
        "rain_sensitive": False,
    }
},
"basil": {
    "stages": [
        {"name": "sprout", "duration_ticks": 10, "optimal_water_level_range": (0.7, 1.0)},
        {"name": "leaf_expansion", "duration_ticks": 20, "optimal_water_level_range": (0.6, 0.8)},
        {"name": "bushy_growth", "duration_ticks": 25, "optimal_water_level_range": (0.5, 0.7)},
        {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.5, 0.7)}
    ],
    "harvest_items": [
        {"item": cc.get_item("Basil Leaf Bunch"), "base_harvest_yield": 7},
        {"item": cc.get_item("Basil Seed"), "base_harvest_yield": 2}
    ],
    "life_cycle": "annual",
    "hardiness": {
        "temp_optimal_range": (18.0, 30.0),
        "temp_survivable_range": (8.0, 38.0),
        "frost_sensitive": True,
        "wind_sensitive": False,
        "rain_sensitive": False,
    }
}
}

# ---------------------------------------------------------------------------
# --- Showcase additions: exercising the fuller range of the hardiness /
#     health system. Each of these leans hard into one or two corners of
#     the design on purpose, so they double as living examples.
#     NOTE: these reference items ("Blackberry", "Watermelon Slice", etc.)
#     that need matching entries in the item store before use — same
#     requirement as every other plant here.
# ---------------------------------------------------------------------------

showcase_plant_types = {

    # A genuinely thorny bramble perennial. Slow to establish (a real
    # blackberry cane takes a season before it fruits), forgiving on
    # temperature once mature, but it hates being waterlogged — brambles
    # rot at the root in soggy soil more readily than they die of cold.
    "blackberry": {
        "stages": [
            {"name": "cane_sprout",     "duration_ticks": 25, "optimal_water_level_range": (0.6, 0.9)},
            {"name": "bramble_spread",  "duration_ticks": 40, "optimal_water_level_range": (0.5, 0.8)},
            {"name": "mature",          "duration_ticks": 25, "optimal_water_level_range": (0.45, 0.75)},
            {"name": "flowering",       "duration_ticks": 15, "optimal_water_level_range": (0.45, 0.7)},
            {"name": "fruit_ripening",  "duration_ticks": 15, "optimal_water_level_range": (0.45, 0.7)},
            {"name": "harvestable",     "duration_ticks": 0,  "optimal_water_level_range": (0.45, 0.7)},
        ],
        "harvest_items": [
            {"item": cc.get_item("Blackberry"), "base_harvest_yield": 9},
            {"item": cc.get_item("Blackberry Cane Cutting"), "base_harvest_yield": 1},
        ],
        "life_cycle": "perennial",
        "water_depletion_rate_per_tick": 0.0035,
        "hardiness": {
            "temp_optimal_range": (12.0, 26.0),
            "temp_survivable_range": (-10.0, 33.0),  # quite cold-hardy once mature
            "frost_sensitive": False,
            "wind_sensitive": False,
            "rain_sensitive": True,                  # root rot risk, not a frost risk
        },
    },

    # Heat-loving, thirsty, tender diva. Narrow, hot optimal band and a
    # survivable floor that's uncomfortably close to it — this one is
    # meant to be genuinely hard to keep alive somewhere with real winters.
    "watermelon": {
        "stages": [
            {"name": "sprout",          "duration_ticks": 15, "optimal_water_level_range": (0.7, 1.0)},
            {"name": "vining_out",      "duration_ticks": 20, "optimal_water_level_range": (0.6, 0.9)},
            {"name": "flowering",       "duration_ticks": 15, "optimal_water_level_range": (0.55, 0.85)},
            {"name": "fruit_swelling",  "duration_ticks": 25, "optimal_water_level_range": (0.55, 0.85)},
            {"name": "harvestable",     "duration_ticks": 0,  "optimal_water_level_range": (0.5, 0.8)},
        ],
        "harvest_items": [
            {"item": cc.get_item("Watermelon"), "base_harvest_yield": 2},
            {"item": cc.get_item("Watermelon Seed"), "base_harvest_yield": 5},
        ],
        "life_cycle": "annual",
        "water_depletion_rate_per_tick": 0.0045,      # thirstier than most
        "hardiness": {
            "temp_optimal_range": (24.0, 34.0),
            "temp_survivable_range": (14.0, 40.0),    # dies fast if it gets cool at all
            "frost_sensitive": True,
            "wind_sensitive": False,
            "rain_sensitive": False,
        },
    },

    # Tall and top-heavy. Fine with a wide range of temperatures and even
    # some frost once mature, but the whole point of this one is
    # wind_sensitive — a storm can snap it even in perfectly nice weather
    # otherwise.
    "corn": {
        "stages": [
            {"name": "sprout",         "duration_ticks": 15, "optimal_water_level_range": (0.65, 0.95)},
            {"name": "stalk_growing",  "duration_ticks": 30, "optimal_water_level_range": (0.55, 0.85)},
            {"name": "tasseling",      "duration_ticks": 15, "optimal_water_level_range": (0.55, 0.8)},
            {"name": "ear_filling",    "duration_ticks": 20, "optimal_water_level_range": (0.5, 0.75)},
            {"name": "harvestable",    "duration_ticks": 0,  "optimal_water_level_range": (0.45, 0.7)},
        ],
        "harvest_items": [
            {"item": cc.get_item("Corn Cob"), "base_harvest_yield": 4},
            {"item": cc.get_item("Corn Seed"), "base_harvest_yield": 3},
        ],
        "life_cycle": "annual",
        "hardiness": {
            "temp_optimal_range": (16.0, 30.0),
            "temp_survivable_range": (2.0, 36.0),
            "frost_sensitive": False,
            "wind_sensitive": True,          # the whole point of this plant
            "rain_sensitive": False,
        },
    },

    # Extremely drought-tolerant succulent. Loves it hot and dry, has an
    # enormous survivable band, but heavy rain events hurt it more than
    # almost any temperature swing — the near-opposite risk profile of
    # the blackberry above.
    "aloe_vera": {
        "stages": [
            {"name": "pup",            "duration_ticks": 20, "optimal_water_level_range": (0.2, 0.5)},
            {"name": "rosette_forming","duration_ticks": 40, "optimal_water_level_range": (0.15, 0.4)},
            {"name": "mature",         "duration_ticks": 40, "optimal_water_level_range": (0.1, 0.35)},
            {"name": "harvestable",    "duration_ticks": 0,  "optimal_water_level_range": (0.1, 0.35)},
        ],
        "harvest_items": [
            {"item": cc.get_item("Aloe Leaf"), "base_harvest_yield": 5},
            {"item": cc.get_item("Aloe Pup"), "base_harvest_yield": 1},
        ],
        "life_cycle": "perennial",
        "water_depletion_rate_per_tick": 0.0012,     # barely needs watering at all
        "hardiness": {
            "temp_optimal_range": (20.0, 35.0),
            "temp_survivable_range": (5.0, 45.0),
            "frost_sensitive": True,       # the one thing that actually kills it
            "wind_sensitive": False,
            "rain_sensitive": True,        # rots fast if it stays wet
        },
    },

    # Cold-loving, almost the mirror image of watermelon: it actively
    # prefers cool weather and tolerates real frost without trouble, but
    # struggles once things get properly hot.
    "kale": {
        "stages": [
            {"name": "seedling",     "duration_ticks": 10, "optimal_water_level_range": (0.6, 0.9)},
            {"name": "leaf_growth",  "duration_ticks": 20, "optimal_water_level_range": (0.55, 0.85)},
            {"name": "harvestable",  "duration_ticks": 0,  "optimal_water_level_range": (0.5, 0.8)},
        ],
        "harvest_items": [
            {"item": cc.get_item("Kale Leaf Bunch"), "base_harvest_yield": 6},
            {"item": cc.get_item("Kale Seed"), "base_harvest_yield": 2},
        ],
        "life_cycle": "annual",
        "hardiness": {
            "temp_optimal_range": (2.0, 18.0),        # genuinely prefers the cold
            "temp_survivable_range": (-15.0, 26.0),   # frost doesn't bother it at all
            "frost_sensitive": False,
            "wind_sensitive": False,
            "rain_sensitive": False,
        },
    },
}

# Merge the showcase set into the main table. Kept as a separate dict above
# so the new examples are easy to spot, diff, or lift out later — but the
# rest of the engine (GardenSimulation, GardenManager) just reads from
# plant_types as one flat table, so nothing downstream needs to know these
# were added separately.
plant_types.update(showcase_plant_types)