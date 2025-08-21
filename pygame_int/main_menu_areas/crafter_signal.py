# pygame_int/main_menu_areas/crafter_signal.py
from enum import Enum, auto

class CrafterSignal(Enum):
    """
    Represents specific, granular events occurring within the BaseCrafter process.
    These are 'fire-and-forget' signals sent to the UI.
    """
    # --- Major Phase Markers ---
    FOUNDATION_START = auto()      # House structure generation begins
    FOUNDATION_COMPLETE = auto()   # House structure generation ends
    
    POPULATION_START = auto()      # Item generation for all rooms begins
    POPULATION_COMPLETE = auto()   # Item generation for all rooms ends
    
    FILTERING_START = auto()       # Unique item filtering begins
    FILTERING_COMPLETE = auto()    # Unique item filtering ends
    
    SAVING_START = auto()          # Saving config files begins
    SAVING_COMPLETE = auto()       # Saving config files ends

    FINALIZING = auto()            # Final data structure assembly
    OVERALL_COMPLETE = auto()      # The entire process succeeded

    # --- Progress & Detail Signals ---
    POPULATION_PROGRESS = auto()   # Update during item generation loop
                                   # Data: {'room_name': str, 'current': int, 'total': int}

    # --- Special UI-Specific Signals ---
    FLAVOR_TEXT = auto()           # A decorative, temporary message for the UI
                                   # Data: str (the message to display)

    # --- State & Error Signals ---
    ERROR = auto()                 # An error occurred
    SHUTDOWN_COMPLETE = auto()     # Process acknowledged shutdown and stopped