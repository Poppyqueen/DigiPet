# store_type_definitions.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the single source of truth for all store categories (aisles).
#
# HOW TO ADD A NEW CATEGORY
#   1. Add an entry to STORE_TYPE_DEFINITIONS below.
#   2. Add the same key string to the "store_types" list of whichever
#      store_endpoint item blueprint should carry it.
#   3. Add that same key string to the "store_entry_data.store_type" field
#      of every item blueprint you want sold in that category.
#   That's it — no store logic code needs to change.
#
# STRUCTURE PER ENTRY
#   "key"         Used everywhere as the canonical type identifier.
#                 Must be a valid Python identifier (snake_case).
#   display_name  Human-readable label shown in the store UI / agent output.
#   description   Agent-facing text describing what this aisle contains.
# ─────────────────────────────────────────────────────────────────────────────

STORE_TYPE_DEFINITIONS: dict[str, dict] = {
    "hearty_meals": {
        "display_name": "Hearty Meals",
        "description": "Filling, home-style cooked dishes and full meals.",
    },
    "drinks": {
        "display_name": "Drinks",
        "description": "Beverages of all kinds — hot, cold, and everything in between.",
    },
    "snacks": {
        "display_name": "Snacks",
        "description": "Light bites, crisps, crackers, and quick hunger fixes.",
    },
    "plant_based_foods": {
        "display_name": "Plant-Based Foods",
        "description": "Vegetables, legumes, tofu, and other plant-derived foods.",
    },
    "staples": {
        "display_name": "Pantry Staples",
        "description": "Rice, pasta, flour, oil — the building blocks of cooking.",
    },
    "condiments": {
        "display_name": "Condiments & Sauces",
        "description": "Sauces, spreads, dressings, and flavour enhancers.",
    },
    "seeds": {
        "display_name": "Seeds",
        "description": "Plantable seeds for the garden. Grow your own produce.",
    },
    "harvest": {
        "display_name": "Harvest",
        "description": "Fresh produce brought in from gardens. Sell-only — the store buys, never stocks.",
    },
    "furniture": {
        "display_name": "Furniture",
        "description": "Chairs, tables, shelving, and decorative pieces for the home.",
    },
    "electronics": {
        "display_name": "Electronics",
        "description": "Discounted gadgets, small appliances, and tech accessories.",
    },
    "books": {
        "display_name": "Books",
        "description": "Fiction, non-fiction, guides, and collector editions.",
    },
}

# Derived — consumed by store_types.py to build the Literal and by store logic
# for iteration. Do not edit this line.
STORE_TYPES: list[str] = list(STORE_TYPE_DEFINITIONS.keys())