# --- Item Definitions for Harvest and Seeds ---
# These items will be created and added to the inventory upon harvest or used for planting.

# Existing Items (copied for context, not modified)
_lettuce_item = {
    "name": "lettuce",
    "descriptions": [
        "A refreshing lettuce"
    ],
    "static": False,
    "type": ["consumable"],
    "stats_edit": {
        "fullness": 10,
        "hydration": 10,
        "energy": 2
    },
    "effects": [
        "You feel the crunch of the lettuce, it is wattery",
        "A refreshing snack"
    ]
} 

_carrot_item = {
    "name": "carrot",
    "descriptions": [
        "A crunchy, sweet orange carrot."
    ],
    "static": False,
    "type": ["consumable"],
    "stats_edit": {
        "fullness": 15,
        "hydration": 5,
        "energy": 3
    },
    "effects": [
        "You bite into the sweet crunch of the carrot, feeling healthier."
    ]
}

_cactus_fruit_item = {
    "name": "cactus fruit",
    "descriptions": [
        "A surprisingly juicy fruit from a cactus, often prickly but hydrating."
    ],
    "static": False,
    "type": ["consumable"],
    "stats_edit": {
        "fullness": 5,
        "hydration": 20,
        "energy": 1
    },
    "effects": [
        "A burst of sweet water in your mouth, watch out for the tiny spines!"
    ]
}

_lettuce_seed = {
    "name": "lettuce seed",
    "descriptions": [
        "A seed, promises a refreshing lettuce."
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "lettuce" # This key links the seed to its plant type
}

_carrot_seed = {
    "name": "carrot seed",
    "descriptions": [
        "A tiny brownish seed, for a carrot!"
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "carrot"
} 

_cactus_seed = {
    "name": "cactus seed",
    "descriptions": [
        "A round, hardy seed, for a resilient cactus."
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "cactus"
}


# --- NEW ITEM DEFINITIONS ---

# Tomato
_tomato_item = {
    "name": "tomato",
    "descriptions": [
        "A ripe, red and juicy tomato, good for eating raw or cooking."
    ],
    "static": False,
    "type": ["consumable"],
    "stats_edit": {
        "fullness": 12,
        "hydration": 15,
        "energy": 2
    },
    "effects": [
        "The sweet tang of the tomato refreshes you.",
        "A juicy and versatile fruit."
    ]
}

_tomato_seed = {
    "name": "tomato seed",
    "descriptions": [
        "Small, flat seeds from a tomato, ready to grow."
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "tomato"
}

# Potato
_potato_item = {
    "name": "potato",
    "descriptions": [
        "A starchy, earthy potato, excellent for baking or boiling. It is still raw! It needs cooking or will be harmful to eat. Can be used to grow another potato while raw."
    ],
    "static": False,
    "type": ["consumable", "seed"],
    "stats_edit": {
        "fullness": 25,
        "hydration": -20,
        "energy": -20
    },
    "effects": [
        "The raw potato makes your stomach hurt",
        "You powered through all that raw potato, amazing.",
        "You feel tired after that whole situation."
    ]
}

# Strawberry
_strawberry_item = {
    "name": "strawberry",
    "descriptions": [
        "A small, sweet, and fragrant red berry."
    ],
    "static": False,
    "type": ["consumable"],
    "stats_edit": {
        "fullness": 8,
        "hydration": 12,
        "energy": 2
    },
    "effects": [
        "A delightful burst of sweet fruit, juicy and refreshing.",
        "You enjoy the delicate taste of the berry."
    ]
}

_strawberry_seed = {
    "name": "strawberry seed",
    "descriptions": [
        "Tiny seeds from a strawberry, promising more sweetness."
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "strawberry"
}


# --- Plant Definitions ---

# Dictionary of predefined plant types and their growth stages
# Each stage defines duration in *minutes* and optimal water level range.
plant_types = {
    "lettuce": { # Existing plant (copied for context, not modified)
        "stages": [
            {"name": "seedling", "duration_minutes": 10, "optimal_water_level_range": (0.8, 1.0)},
            {"name": "juvenile", "duration_minutes": 15, "optimal_water_level_range": (0.6, 0.9)},
            {"name": "mature", "duration_minutes": 35, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.5, 0.7)} # Duration 0 means it's ready
        ],
        "total_grow_minutes": 60, # Sum of duration_minutes for stages before harvestable
        "harvest_items": [ # A list of items this plant can yield upon harvest
            {"item": _lettuce_item, "base_harvest_yield": 7}, # Yield 5 lettuce items
            {"item": _lettuce_seed, "base_harvest_yield": 2}   # Yield 1 lettuce seed
        ],
        "life_cycle": "annual"
    },
    "carrot": { # Existing plant (copied for context, not modified)
        "stages": [
            {"name": "seedling", "duration_minutes": 15, "optimal_water_level_range": (0.7, 0.9)},
            {"name": "young", "duration_minutes": 30, "optimal_water_level_range": (0.6, 0.8)},
            {"name": "rooting", "duration_minutes": 30, "optimal_water_level_range": (0.4, 0.7)},
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.4, 0.7)}
        ],
        "total_grow_minutes": 75,
        "harvest_items": [
            {"item": _carrot_item, "base_harvest_yield": 10},
            {"item": _carrot_seed, "base_harvest_yield": 4}
        ],
        "life_cycle": "biennial" 
    },
    "cactus": { # Existing plant (copied for context, not modified)
        "stages": [
            {"name": "sprout", "duration_minutes": 30, "optimal_water_level_range": (0.1, 0.6)},
            {"name": "young", "duration_minutes": 60, "optimal_water_level_range": (0.05, 0.4)},
            {"name": "mature", "duration_minutes": 60, "optimal_water_level_range": (0.05, 0.25)},
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.1, 0.45)}
        ],
        "total_grow_minutes": 150,
        "harvest_items": [
            {"item": _cactus_fruit_item, "base_harvest_yield": 7},
            {"item": _cactus_seed, "base_harvest_yield": 3}
        ],
        "life_cycle": "perennial" 
    },

    # --- NEW PLANT DEFINITIONS ---

    "tomato": {
        "stages": [
            {"name": "sprout", "duration_minutes": 15, "optimal_water_level_range": (0.7, 0.9)},
            {"name": "young", "duration_minutes": 15, "optimal_water_level_range": (0.6, 0.85)},
            {"name": "mature", "duration_minutes": 20, "optimal_water_level_range": (0.5, 0.75)},
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.5, 0.75)}
        ],
        "total_grow_minutes": 50,
        "harvest_items": [
            {"item": _tomato_item, "base_harvest_yield": 6},
            {"item": _tomato_seed, "base_harvest_yield": 2}
        ],
        "life_cycle": "annual"
    },
    "potato": {
        "stages": [
            {"name": "sprout", "duration_minutes": 20, "optimal_water_level_range": (0.6, 0.8)},
            {"name": "young", "duration_minutes": 25, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "mature", "duration_minutes": 40, "optimal_water_level_range": (0.4, 0.6)}, # Develops underground tubers
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.4, 0.6)}
        ],
        "total_grow_minutes": 85,
        "harvest_items": [
            {"item": _potato_item, "base_harvest_yield": 8}, # Potatoes are plenty
        ],
        "life_cycle": "annual" # Though some varieties are biennial, annual is common for game simplicity.
    },
    "strawberry": {
        "stages": [
            {"name": "sprout", "duration_minutes": 15, "optimal_water_level_range": (0.7, 0.9)},
            {"name": "young", "duration_minutes": 30, "optimal_water_level_range": (0.6, 0.8)},
            {"name": "mature", "duration_minutes": 25, "optimal_water_level_range": (0.5, 0.7)},
            {"name": "harvestable", "duration_minutes": 0, "optimal_water_level_range": (0.5, 0.7)}
        ],
        "total_grow_minutes": 70,
        "harvest_items": [
            {"item": _strawberry_item, "base_harvest_yield": 5},
            {"item": _strawberry_seed, "base_harvest_yield": 2}
        ],
        "life_cycle": "perennial" # Can produce fruit year after year (or cycle after cycle in game terms)
    }
}