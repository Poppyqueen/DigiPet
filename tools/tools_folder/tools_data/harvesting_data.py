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
            {"item": cc.get_item("lettuce head"), "base_harvest_yield": 7},
            {"item": cc.get_item("Lettuce Seeds"), "base_harvest_yield": 2}
        ],
        "life_cycle": "annual",
        "water_depletion_rate_per_tick": 0.002
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
            {"item": cc.get_item("carrot"), "base_harvest_yield": 10},
            {"item": cc.get_item("Carrot Seeds"), "base_harvest_yield": 4}
        ],
        "life_cycle": "biennial" 
    },
    "cactus": { # PERENNIAL - ENSURING 'mature' stage
        "stages": [
            {"name": "sprout", "duration_ticks": 30, "optimal_water_level_range": (0.1, 0.6)},
            {"name": "pad_developing", "duration_ticks": 60, "optimal_water_level_range": (0.05, 0.4)},
            {"name": "mature", "duration_ticks": 60, "optimal_water_level_range": (0.05, 0.30)}, # Renamed from 'fully_established'
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.1, 0.45)}
        ],
        "harvest_items": [
            {"item": cc.get_item("cactus pad"), "base_harvest_yield": 7},
            {"item": cc.get_item("Cactus Seeds"), "base_harvest_yield": 3}

        ],
        "life_cycle": "perennial",
        "water_depletion_rate_per_tick": 0.009

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
            {"item": cc.get_item("ripe tomato"), "base_harvest_yield": 6},
            {"item": cc.get_item("Tomato Seeds"), "base_harvest_yield": 2}
        ],
        "life_cycle": "annual"
    },
    "potato": {
        "stages": [
            {"name": "sprout", "duration_ticks": 20, "optimal_water_level_range": (0.6, 1.0)},
            {"name": "foliage_developing", "duration_ticks": 25, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "tuber_forming", "duration_ticks": 40, "optimal_water_level_range": (0.4, 0.6)},
            {"name": "harvestable", "duration_ticks": 0, "optimal_water_level_range": (0.4, 0.6)}
        ],
        "harvest_items": [
            {"item": cc.get_item("potato (tuber)"), "base_harvest_yield": 8},
        ],
        "life_cycle": "annual"
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
            {"item": cc.get_item("strawberry"), "base_harvest_yield": 6},
            {"item": cc.get_item("Strawberry Seeds"), "base_harvest_yield": 2}
        ],
        "life_cycle": "perennial"
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
        {"item": cc.get_item("rose seed"), "base_harvest_yield": 1}

    ],
    "life_cycle": "perennial"
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
        {"item": cc.get_item("sunflower seed"), "base_harvest_yield": 3}
    ],
    "life_cycle": "annual"
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
        {"item": cc.get_item("mint seed"), "base_harvest_yield": 2}
    ],
    "life_cycle": "perennial"
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
        {"item": cc.get_item("basil seed"), "base_harvest_yield": 2}
    ],
    "life_cycle": "annual"
}
}