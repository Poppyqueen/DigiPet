# tools/tools_folder/tools_data/garden_settings.py

# General Garden Settings
GARDEN_SETTINGS = {
    # --- Rain & Water Management ---
    "RAIN_COOLDOWN_MINUTES": 30,
    "RAIN_WATER_APPLY_MULTIPLIER": 0.05, # How much rain (mm/h) affects water level per tick
    "DEFAULT_WATER_DEPLETION_RATE_PER_TICK": 0.002778, # Default rate for plants if not specified
    "DEFAULT_INITIAL_WATER_LEVEL": 0.5, # Water level for newly planted seeds
    "WATER_LOSS_ON_STAGE_CHANGE": 0.05, # Amount of water lost when a plant grows to a new stage
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
    },

    # --- Health / Stress / Death ---
    # stress_ticks is a float accumulator. Bad conditions add to it each
    # elapsed tick, good conditions bleed it back down. Crossing a threshold
    # moves health_state forward; dropping back below one recovers it —
    # except "dead", which is permanent.
    "STRESS_THRESHOLD": 15,   # healthy -> stressed
    "WILT_THRESHOLD": 40,     # stressed -> wilted
    "DEATH_THRESHOLD": 80,    # wilted -> dead (terminal)
    "STRESS_RECOVERY_RATE_PER_TICK": 1.5,   # stress_ticks bled off per good tick
    "BAD_WATER_STRESS_INCREMENT": 1.0,      # per tick spent under/overwatered
    "WEATHER_EXTREME_STRESS_INCREMENT": 1.5, # per tick spent outside hardiness

    # --- Weather Hardiness Thresholds ---
    # Generic cutoffs used together with each plant's "hardiness" block
    # (see harvesting_data.py) to decide if a plant is currently experiencing
    # extreme weather. A plant only "feels" these if its hardiness flags it
    # as sensitive to that condition.
    "FROST_TEMP_C": 0.0,             # at/below this, frost_sensitive plants take stress
    "STORM_WIND_KMH": 40.0,          # at/above this, wind_sensitive plants take stress
    "HEAVY_RAIN_MM_H": 4.0,          # at/above this, rain_sensitive plants take stress

    # --- Weather Extreme Severity Scaling ---
    # Being *just* outside a plant's survivable range shouldn't hit as hard
    # as being catastrophically outside it: -1°C past a plant's frost floor
    # is a bad tick, -40°C past it should be a death sentence, not the same
    # 1.5-point stress increment. Each *_SEVERITY_SCALE is "how many units
    # past the threshold equal one extra full severity step" — overshoot is
    # divided by this and added to a baseline severity of 1.0 (the "just
    # crossed the line" case), then capped at MAX_WEATHER_SEVERITY_MULTIPLIER
    # so one apocalyptic reading can't insta-kill in a single tick.
    "TEMP_SEVERITY_SCALE_C": 6.0,
    "WIND_SEVERITY_SCALE_KMH": 20.0,
    "RAIN_SEVERITY_SCALE_MM_H": 5.0,
    "MAX_WEATHER_SEVERITY_MULTIPLIER": 6.0,

    # --- Weather Exposure ---
    # Multiplier applied to both rain gain and weather-extreme stress.
    # 1.0 = fully outdoors_area. Anything else (indoor open_soil_zone rooms,
    # pots not sitting in an outdoors_area room) is dampened, not immune —
    # walls help, they're not a fortress.
    "OUTDOOR_EXPOSURE_MULTIPLIER": 1.0,
    "INDOOR_EXPOSURE_MULTIPLIER": 0.3,

    # --- Weather Harvest Quality (mirrors water_history/bonus mechanism) ---
    "RECORD_WEATHER_HISTORY_INTERVAL_TICKS": 10,
    "WEATHER_BONUS_LOG_BASE": 2,
    "WEATHER_BONUS_SENSITIVITY_FACTOR": 3,
    "WEATHER_BONUS_PER_LOG_STEP": 0.5, # smaller than water's — a nice bonus, not the main driver

    # --- Harvestable Decay (fruit falls, plant lives) ---
    # Once a plant has been sitting in 'harvestable' this many ticks, yield
    # starts falling off. It reaches 0 after DECAY_TICKS_TO_ZERO more ticks —
    # at which point the harvest is fully lost and the plant moves on with
    # its lifecycle (perennials reset to 'mature', annuals complete their
    # cycle) exactly as if it had been harvested for nothing.
    "HARVEST_DECAY_GRACE_TICKS": 20,
    "HARVEST_DECAY_TICKS_TO_ZERO": 40,

    # --- Health State Descriptions ---
    "HEALTH_STATE_MESSAGES": {
        "healthy": "It looks vibrant and healthy.",
        "stressed": "It looks stressed — check its water and shelter.",
        "wilted": "It's wilting badly. It needs help soon or it won't make it.",
        "dead": "It has died. Remove it to free up the plot.",
    }
}