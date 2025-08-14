# --- Item Definitions for Harvest and Seeds ---
# These items will be created and added to the inventory upon harvest or used for planting.

# Existing Items
_lettuce_item = {
    "name": "lettuce",
    "descriptions": [
        "A refreshing lettuce"
    ],
    "static": False,
    "type": ["consumable"],
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
    "type": ["seed"],
    "plant_type": "lettuce" # This key links the seed to its plant type
}

_carrot_seed = {
    "name": "carrot seed",
    "descriptions": [
        "A tiny brownish seed, for a carrot!"
    ],
    "static": False,
    "stackable": True,
    "type": ["seed"],
    "plant_type": "carrot"
} 

_cactus_seed = {
    "name": "cactus seed",
    "descriptions": [
        "A round, hardy seed, for a resilient cactus."
    ],
    "static": False,
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
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
    "stackable": True,
    "type": ["seed"],
    "plant_type": "strawberry"
}


# --- NEW ITEM DEFINITIONS ---

# Rose (Ornamental Flower)
_rose_flower_item = {
    "name": "rose flower",
    "descriptions": [
        "A beautiful, fragrant rose, perfect for decoration.",
        "Its delicate petals and sweet scent can brighten any room."
    ],
    "stackable": True,
    "static": False,
    "type": ["misc"]
}

_rose_seed = {
    "name": "rose seed",
    "descriptions": [
        "A small, hard seed that promises a beautiful rose."
    ],
    "stackable": True,
    "static": False,
    "type": ["seed"],
    "plant_type": "rose"
}

# Sunflower (Ornamental and Edible Seeds)
_sunflower_head_item = {
    "name": "sunflower head",
    "descriptions": [
        "The large, iconic head of a sunflower, full of potential seeds.",
        "A majestic bloom, often turning to follow the sun."
    ],
    "stackable": True,
    "static": False,
    "type": ["misc"]

}


_sunflower_seed = {
    "name": "sunflower seed",
    "descriptions": [
        "A single, dark sunflower seed, ready to grow into a giant."
    ],
    "static": False,
    "stackable": True,
    "type": ["seed"],
    "plant_type": "sunflower"
}


# Mint (Herb)
_mint_leaves_item = {
    "name": "mint leaves",
    "descriptions": [
        "Fresh, fragrant mint leaves, perfect for tea or flavoring.",
        "Cool and refreshing, a common culinary herb."
    ],
    "static": False,
    "type": ["consumable"],
    "stackable": True,
    "stats_edit": {
        "fullness": 3,
        "hydration": 5,
        "energy": 1
    },
    "effects": [
        "A cool, tingling sensation spreads through your mouth.",
        "You feel a slight revitalization from the mint."
    ]
}

_mint_seed = {
    "name": "mint seed",
    "descriptions": [
        "Tiny, dark seeds from a mint plant."
    ],
    "static": False,
    "stackable": True,
    "type": ["seed"],
    "plant_type": "mint"
}

# Basil (Herb)
_basil_leaves_item = {
    "name": "basil leaves",
    "descriptions": [
        "Aromatic basil leaves, commonly used in cooking.",
        "Sweet and slightly peppery, a staple in many cuisines."
    ],
    "static": False,
    "type": ["consumable"],
    "stackable": True,
    "stats_edit": {
        "fullness": 2,
        "hydration": 3,
        "energy": 1
    },
    "effects": [
        "The fragrant aroma of basil fills your senses.",
        "A subtle, savory taste lingers on your tongue."
    ]
}

_basil_seed = {
    "name": "basil seed",
    "stackable": True,
    "descriptions": [
        "Small, black seeds from a basil plant."
    ],
    "static": False,
    "type": ["seed"],
    "plant_type": "basil"
}


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
            {"item": _lettuce_item, "base_harvest_yield": 7},
            {"item": _lettuce_seed, "base_harvest_yield": 2}
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
            {"item": _carrot_item, "base_harvest_yield": 10},
            {"item": _carrot_seed, "base_harvest_yield": 4}
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
            {"item": _cactus_fruit_item, "base_harvest_yield": 7},
            {"item": _cactus_seed, "base_harvest_yield": 3}

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
            {"item": _tomato_item, "base_harvest_yield": 6},
            {"item": _tomato_seed, "base_harvest_yield": 2}
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
            {"item": _potato_item, "base_harvest_yield": 8},
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
            {"item": _strawberry_item, "base_harvest_yield": 6},
            {"item": _strawberry_seed, "base_harvest_yield": 2}
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
        {"item": _rose_flower_item, "base_harvest_yield": 3},
        {"item": _rose_seed, "base_harvest_yield": 1}
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
        {"item": _sunflower_head_item, "base_harvest_yield": 1},
        {"item": _sunflower_seed, "base_harvest_yield": 3}
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
        {"item": _mint_leaves_item, "base_harvest_yield": 8},
        {"item": _mint_seed, "base_harvest_yield": 2}
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
        {"item": _basil_leaves_item, "base_harvest_yield": 7},
        {"item": _basil_seed, "base_harvest_yield": 2}
    ],
    "life_cycle": "annual"
}
}