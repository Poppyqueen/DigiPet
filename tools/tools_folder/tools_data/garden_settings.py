# tools/tools_folder/tools_data/garden_settings.py

# General Garden Settings
GARDEN_SETTINGS = {
    # --- Rain & Water Management ---
    "RAIN_COOLDOWN_MINUTES": 30,
    "RAIN_WATER_APPLY_MULTIPLIER": 0.05, # How much rain (mm/h) affects water level per tick
    "DEFAULT_WATER_DEPLETION_RATE_PER_TICK": 0.002778, # Default rate for plants if not specified
    "DEFAULT_INITIAL_WATER_LEVEL": 0.5, # Water level for newly planted seeds
    "WATER_LOSS_ON_STAGE_CHANGE": 0.1, # Amount of water lost when a plant grows to a new stage
    "WATERING_AMOUNTS": {
        "low": 0.1,    # Adds 10% to water level
        "medium": 0.25,  # Adds 25% to water level
        "high": 0.5    # Adds 50% to water level
    },

    # --- Growth & Harvest Calculation ---
    "RECORD_WATER_HISTORY_INTERVAL_TICKS": 10, # How often to record water state for quality calculation
    "PENALTY_LOG_BASE": 2,
    "PENALTY_SENSITIVITY_FACTOR": 5, # Higher value makes penalty less severe
    "BONUS_LOG_BASE": 2,
    "BONUS_SENSITIVITY_FACTOR": 3, # Higher value makes bonus less severe
    "BONUS_PER_LOG_STEP": 1.0, # How much yield is added per log step of bonus

    # --- Life Cycle Quality Descriptions ---
    "LIFE_CYCLE_QUALITY_MESSAGES": {
        "poor": "You should be more careful.",
        "bad": "This isn't looking good.",
        "average": "There's room for improvement.",
        "good": "Well done!",
        "excellent": "Outstanding work!",
    }
}