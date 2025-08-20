
from enum import Enum

class CrafterSignal(Enum):
    """Signals that BaseCrafter can send during processing"""
    STARTED = "started"
    ANALYZING_PROMPT = "analyzing_prompt" 
    GENERATING_STATE = "generating_state"
    VALIDATING_RESULT = "validating_result"
    PROGRESS_UPDATE = "progress_update"  # With percentage
    COMPLETED = "completed"
    
    ERROR = "error"