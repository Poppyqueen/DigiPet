# animation.py

from pygame_int import config # Needed for animation constants and event types
from pygame_int import state # Needed for accessing/modifying animation state variables and sleep state

import pygame
import math # Needed for sine/cosine calculations
from pygame_int.main_digipet import gui # Needed to add system messages to history (e.g., input locked)

# --- Helper functions to clear specific animation states and variables ---
def _clear_sad_state():
    state.sad_state = 0
    state.original_radius_before_sad = None
    state.target_sad_radius = None
    # Note: pet_radius reset happens in the main clear_lower_priority_animations or calculate_circle_offset base case
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_happy_state():
    state.happy_state = 0
    state.original_radius_before_happy = None
    state.target_happy_radius = None
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_angry_state():
    state.angry_state = 0
    state.original_radius_before_angry = None
    state.target_angry_radius = None
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_excited_state():
    state.excited_state = 0
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_thinking_state():
    state.is_thinking = False
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_curious_state():
    state.is_curious = False
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_confused_state(): # <-- NEW HELPER FUNCTION
    state.confused_state = 0
    state.confused_start_time = 0
    state.confused_phase_start_time = 0
    state.confused_corner_index = 0
    state.original_radius_before_confused = None
    # state.pet_radius = state.current_radius # Can add here for safety if needed

def _clear_shake_state():
    state.is_shaking = False
    # state.pet_radius = state.current_radius # Can add here for safety if needed
# --- Animation Priority Order (Highest to Lowest) ---
# Each tuple is (animation_name, lambda_check_if_active, function_to_clear_state)


ANIMATION_PRIORITY = [
    ('sad',       lambda: state.sad_state != 0,       _clear_sad_state),
    ('happy',     lambda: state.happy_state != 0,     _clear_happy_state),
    ('angry',     lambda: state.angry_state != 0,     _clear_angry_state),
    ('excited',   lambda: state.excited_state != 0,   _clear_excited_state),
    ('thinking',  lambda: state.is_thinking,          _clear_thinking_state),
    ('curious',   lambda: state.is_curious,           _clear_curious_state),
    ('confused',  lambda: state.confused_state != 0,  _clear_confused_state), # <-- UPDATED CONFUSED ENTRY
    ('shake',     lambda: state.is_shaking,           _clear_shake_state),
]
# Base movement is lower priority than 'shake' and is the default when none above are active.

# --- Helper function to check if any higher priority animation is active ---
# This function remains the same as provided before.
def is_higher_priority_animation_active(current_animation_name):
    """Checks if any animation with higher priority than the current one is active."""
    found_current = False
    # Only need name and the check function from the list
    for name, is_active_check, _ in ANIMATION_PRIORITY:
        if name == current_animation_name:
            found_current = True
            continue # Found current, check subsequent (lower priority) items are not higher

        # If we haven't found the current animation yet, this one is higher priority
        if not found_current and is_active_check():
            return True

    return False # No higher priority animation is currently active

# --- Helper function to clear lower priority animations ---
# This function needs a small adjustment to only call the single clear function
def clear_lower_priority_animations(current_animation_name):
    """Clears animation states and cleanup vars that have lower priority than the current one."""
    found_current = False
    # Get name, check (though not used here), and the clear function from the list
    for name, _, clear_state_func in ANIMATION_PRIORITY:
        if name == current_animation_name:
            found_current = True
            continue # Found current, now clear subsequent (lower priority) items

        # If we have found the current animation, clear this one (it's lower priority)
        if found_current:
            clear_state_func()
            # print(f"Cleared lower priority animation: {name}") # Optional debug print

    # Ensure the radius is reset to the current default if it was changed by a lower priority one just cleared
    # The individual clear functions handle pet_radius = state.current_radius, but a final defensive reset is fine.
    state.pet_radius = state.current_radius
# --- Function to start the circle shake animation ---
def start_circle_shake():
    """Starts the general circle shake animation if no other animation is active or asleep."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual shake command.") # Already printed in core loop
        gui.gui_text_utils.add_message_to_history("System: Cannot manually trigger shake while bot is resting.", 'system')
        return

    # Only general shake if no other specific animation is active
    if not is_higher_priority_animation_active('shake') and not state.is_shaking:
        state.is_shaking = True
        state.shake_start_time = pygame.time.get_ticks()
        print("Circle shake started (general).")
        # No lower priorities to clear explicitly for general shake
    else:
        pass # print("Shake signal received, but another animation is active or already shaking. Ignoring general shake.")


# --- Function to start the sad animation sequence ---
# --- Function to start the sad animation sequence ---
def start_sad_animation():
    """Starts the sad animation sequence (dropping, shaking down, rising)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual sad command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger sad while bot is resting.", 'system')
        return

    # Only start if not already in a sad sequence AND no higher priority is active (Sad is highest here)
    # The is_higher_priority_animation_active check is technically redundant here as sad is highest,
    # but leaving it for consistency and future re-ordering robustness.
    if state.sad_state == 0 and not is_higher_priority_animation_active('sad'):
        state.sad_state = 1 # Start dropping
        state.sad_phase_start_time = current_time_ms # Reset phase timer for phase 1
        clear_lower_priority_animations('sad') # Clear all other non-sad states

        # --- NEW SIZE LOGIC FOR SAD ---
        # Store the original radius BEFORE starting the animation
        state.original_radius_before_sad = state.pet_radius
        # Calculate and store the *target* radius for the sad animation
        state.target_sad_radius = state.original_radius_before_sad * (1 + config.SAD_SIZE_CHANGE_PERCENTAGE) # Note: SAD_SIZE_CHANGE_PERCENTAGE is likely negative
        # ----------------------------

        print("Sad animation started (dropping).")
    else:
        pass # print(f"Sad animation signal received, but already in sad state {state.sad_state}. Ignoring.")

# --- Function to start the happy animation sequence ---
def start_happy_animation():
    """Starts the happy animation sequence (dipping, shaking happily, bouncing up)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual happy command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger happy while bot is resting.", 'system')
        return

    # Only start if not already in a happy sequence AND no higher priority is active
    if state.happy_state == 0 and not is_higher_priority_animation_active('happy'):
        state.happy_state = 1 # Start dipping
        state.happy_phase_start_time = current_time_ms # Reset phase timer for phase 1
        clear_lower_priority_animations('happy') # Clear all other non-happy/non-sad states

        # --- NEW SIZE LOGIC FOR HAPPY ---
        # Store the original radius BEFORE starting the animation
        state.original_radius_before_happy = state.pet_radius
        # Calculate and store the *target* radius for the happy animation
        state.target_happy_radius = state.original_radius_before_happy * (1 + config.HAPPY_SIZE_CHANGE_PERCENTAGE) # <-- New state variable needed
        # -------------------------------

        print("Happy animation started (dipping).")
    else:
        pass # print(f"Happy animation signal received, but already in happy state {state.happy_state} or higher priority active. Ignoring.")

# --- Function to start the angry animation sequence ---
def start_angry_animation():
    """Starts the angry animation sequence (e.g., Tense down -> Vibrate intensely -> Settle up)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual angry command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger angry while bot is resting.", 'system')
        return

    # Only start if not already in an angry sequence AND no higher priority is active
    if state.angry_state == 0 and not is_higher_priority_animation_active('angry'):
        state.angry_state = 1 # Start tense down
        state.angry_phase_start_time = pygame.time.get_ticks()
        clear_lower_priority_animations('angry') # Clear states lower than angry

        # Store the original radius BEFORE starting the animation
        state.original_radius_before_angry = state.pet_radius
        # Calculate and store the *target* maximum radius for the grow phase
        state.target_angry_radius = state.original_radius_before_angry * (1 + config.ANGRY_SIZE_INCREASE_PERCENTAGE) # <-- New state variable needed

        print("Angry animation started (tense down).")
    else:
        pass # print(f"Angry animation signal received, but already in angry state {state.angry_state} or higher priority active. Ignoring.")

# --- Function to start the excited animation sequence ---
def start_excited_animation():
    """Starts the excited animation sequence (e.g., Quick bounce up -> Jiggle rapidly -> Settle)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual excited command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger excited while bot is resting.", 'system')
        return

    # Only start if not already in an excited sequence AND no higher priority is active
    if state.excited_state == 0 and not is_higher_priority_animation_active('excited'):
        state.excited_state = 1 # Start quick bounce up
        state.excited_phase_start_time = pygame.time.get_ticks()
        clear_lower_priority_animations('excited') # Clear states lower than excited
        print("Excited animation started (bounce up).")
    else:
        pass # print(f"Excited animation signal received, but already in excited state {state.excited_state} or higher priority active. Ignoring.")

# --- Function to start the thinking animation (U-shape) ---
def start_thinking_animation():
    """Starts the thinking animation (U-shape path movement)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual thinking command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger thinking while bot is resting.", 'system')
        return

    # Only start if not already thinking AND no higher priority is active
    if not state.is_thinking and not is_higher_priority_animation_active('thinking'):
        state.is_thinking = True
        # --- Initialize State for U-Shape Animation ---
        state.thinking_current_segment_index = 1 # Start with the first segment (P0 -> P1)
        state.thinking_segment_start_time = current_time_ms # Record start time for the first segment
        state.thinking_total_segments = config.THINKING_U_CYCLES * 10 # 10 segments per back-and-forth cycle

        # Define points for easy lookup based on segment index (using a tuple of tuples)
        # P0=(0,0), P1=(0,P1_Y), P2=(P2_X, P2_Y), P3=(P3_X, P3_Y)
        p0 = (0, 0)
        p1 = (0, config.THINKING_POINT_P1_Y)
        p2 = (config.THINKING_POINT_P2_X, config.THINKING_POINT_P2_Y)
        p3 = (config.THINKING_POINT_P3_X, config.THINKING_POINT_P3_Y)

        # List of (start_point, end_point) tuples for each segment
        # One full back-and-forth cycle (10 segments):
        # P0->P1 (Down), P1->P2 (DL), P2->P3 (R), P3->P1 (UL), P1->P0 (Up) - First U (L-R)
        # P0->P1 (Down), P1->P3 (DR), P3->P2 (L), P2->P1 (UR), P1->P0 (Up) - Second U (R-L)
        state.thinking_segments_path = [
            (p0, p1), (p1, p2), (p2, p3), (p3, p1), (p1, p0), # L-R U path
            (p0, p1), (p1, p3), (p3, p2), (p2, p1), (p1, p0)  # R-L U path
        ]
        # We will loop through this list based on the current segment index and total cycles.
        # Example: Segment 1 is state.thinking_segments_path[0], Segment 10 is state.thinking_segments_path[9]
        # Segment 11 would use state.thinking_segments_path[0] again, and so on.

        # --- End State Initialization ---

        clear_lower_priority_animations('thinking') # Clear states lower than thinking
        print("Thinking animation started (U-shape).")
    else:
        pass # print("Thinking animation signal received, but already thinking or higher priority active. Ignoring.")

# --- Function to start the curious animation ---
def start_curious_animation():
    """Starts the curious animation (horizontal sway and size pulse)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        gui.add_message_to_history("System: Cannot manually trigger curious while bot is resting.", 'system')
        return

    # Only start if not already curious AND no higher priority is active
    if not state.is_curious and not is_higher_priority_animation_active('curious'):
        state.is_curious = True
        state.curious_start_time = pygame.time.get_ticks()
        clear_lower_priority_animations('curious') # Clear states lower than curious

        # Store the original radius BEFORE starting the animation for size pulsing
        state.original_radius_before_curious = state.pet_radius

        print("Curious animation started (sway and size pulse).")
    else:
        pass # print("Curious animation signal received, but already curious or higher priority active. Ignoring.")
# --- Function to start the confused animation ---
def start_confused_animation():
    """Starts the confused animation (e.g., subtle wobble)."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        # print("Input locked - bot is asleep. Ignoring manual confused command.") # Already printed in core loop
        gui.add_message_to_history("System: Cannot manually trigger confused while bot is resting.", 'system')
        return

    # --- FIX: Use state.confused_state != 0 for the check ---
    # Only start if not already confused AND no higher priority is active
    if state.confused_state == 0 and not is_higher_priority_animation_active('confused'):
        # --- FIX: Initialize state.confused_state to 1 to start the first phase ---
        state.confused_state = 1
        state.confused_start_time = current_time_ms # Reset overall animation timer
        state.confused_phase_start_time = current_time_ms # Reset phase timer for phase 1
        state.confused_corner_index = 0 # Reset corner index (will be incremented for states 3, 5, 7)
        clear_lower_priority_animations('confused') # Clear states lower than confused

        # --- FIX: Store the original radius BEFORE starting the animation for size pulsing ---
        state.original_radius_before_confused = state.pet_radius

        print("Confused animation started.")
    else:
        pass # print(f"Confused animation signal received, but already in confused state {state.confused_state} or higher priority active. Ignoring.")

# --- Function to update animation state based on timers ---
# --- Function to update animation state based on timers ---
def update_animation_state(current_time_ms):
    """Updates the state variables for ongoing animations based on elapsed time.
       This function ONLY handles state transitions (e.g., phase 1 to phase 2).
       Returns True if any specific animation (non-base movement) is currently active, False otherwise."""

    # Priority Order (Highest to Lowest): Sad > Happy > Angry > Excited > Thinking > Curious > Confused > General Shake > Base

    # Handle animation state transitions in order of priority
    # Once a transition happens for a high-priority animation, lower ones are implicitly not checked for transition *this frame*.
    # However, lower priority animations might finish *on their own* if their timer runs out.
    # The clear_lower_priority_animations is handled when a *new* animation starts.
    # Here, we just check if existing animations should transition phases or end.

    # Flag to track if any specific animation is active *after* potential transitions
    is_any_specific_animation_active = False


    # --- Handle Sad Animation State (Highest Priority) ---
    if state.sad_state == 1: # Moving down
        is_any_specific_animation_active = True
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        if elapsed_phase_time >= config.SAD_DROP_DURATION_MS:
            state.sad_state = 2 # Transition to shaking down phase
            state.sad_phase_start_time = current_time_ms # Reset phase timer for phase 2 start
            state.shake_start_time = current_time_ms # Start shake timer for state 2's specific shake
            #print("Sad state: Dropping complete, starting shake down.")

    elif state.sad_state == 2: # Shaking down
        is_any_specific_animation_active = True
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
        if elapsed_shake_time >= config.SAD_SHAKE_DURATION_MS: # Check against state 2's shake duration
            state.sad_state = 3 # Transition to rising phase
            state.sad_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
            #print("Sad state: Shaking down complete, starting rise.")

    elif state.sad_state == 3: # Moving up
        is_any_specific_animation_active = True
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        if elapsed_phase_time >= config.SAD_RISE_DURATION_MS:
            state.sad_state = 0 # Transition back to idle state
            # --- CLEANUP SIZE STATE FOR SAD ---
            state.original_radius_before_sad = None # <-- Reset
            state.target_sad_radius = None # <-- Reset
            state.pet_radius = state.current_radius # Ensure radius is reset
            # ----------------------------------
            #print("Sad state: Rising complete, returning to idle.")


    # --- Handle Happy Animation State (Second Highest Priority) ---
    # Check if Sad is not active before processing Happy transitions
    if state.sad_state == 0:
        if state.happy_state == 1: # Dipping down
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.happy_phase_start_time
            if elapsed_phase_time >= config.HAPPY_DIP_DURATION_MS:
                state.happy_state = 2 # Transition to shaking happy phase
                state.happy_phase_start_time = current_time_ms # Reset phase timer for phase 2 start
                state.shake_start_time = current_time_ms # Start shake timer for state 2's specific shake
                #print("Happy state: Dipping complete, starting happy shake.")

        elif state.happy_state == 2: # Shaking happily
            is_any_specific_animation_active = True
            elapsed_shake_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
            if elapsed_shake_time >= config.HAPPY_SHAKE_DURATION_MS: # Check against state 2's shake duration
                state.happy_state = 3 # Transition to rising phase
                state.happy_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
                #print("Happy state: Shaking happy complete, starting bounce up.")

        elif state.happy_state == 3: # Bouncing up
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.happy_phase_start_time
            if elapsed_phase_time >= config.HAPPY_RISE_DURATION_MS:
                state.happy_state = 0 # Transition back to idle state
                # --- CLEANUP SIZE STATE FOR HAPPY ---
                state.original_radius_before_happy = None # <-- Reset
                state.target_happy_radius = None # <-- Reset
                state.pet_radius = state.current_radius # Ensure radius is reset
                # ------------------------------------
                #print("Happy state: Rising complete, returning to idle.")

    # --- Handle Angry Animation State (Third Highest Priority) ---
    # Check if Sad and Happy are not active before processing Angry transitions
    # This block already exists and handles size changes correctly.
    if state.sad_state == 0 and state.happy_state == 0:
        if state.angry_state == 1: # Tense down (Phase 1)
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.angry_phase_start_time
            if elapsed_phase_time >= config.ANGRY_TENSE_DURATION_MS:
                state.angry_state = 2 # Transition from Tense (1) to Vibrate (2)
                state.angry_phase_start_time = current_time_ms # Reset phase timer for phase 2 start (though phase 2 uses shake_start_time)
                state.shake_start_time = current_time_ms # Start shake timer specifically for state 2's vibration
                print("Angry state: Tense down complete, starting vibrate.") # <-- Add print back here

        elif state.angry_state == 2: # Vibrate intensely (Phase 2)
            is_any_specific_animation_active = True
            elapsed_vibrate_time = current_time_ms - state.shake_start_time # Use the shake timer specifically set when entering state 2
            if elapsed_vibrate_time >= config.ANGRY_VIBRATE_DURATION_MS:
                state.angry_state = 3 # Transition from Vibrate (2) to Settle (3)
                state.angry_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
                print("Angry state: Vibrate complete, starting settle.") # <-- Add print back here

        elif state.angry_state == 3: # Settle up (Phase 3)
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.angry_phase_start_time
            if elapsed_phase_time >= config.ANGRY_SETTLE_DURATION_MS:
                state.angry_state = 0 # Transition from Settle (3) back to Idle (0)
                # Clean up stored radius values when animation finishes
                state.original_radius_before_angry = None # <-- Reset
                state.target_angry_radius = None # <-- Reset
                state.pet_radius = state.current_radius # Ensure radius is reset
                #print("Angry state: Settle complete, returning to idle.")


    # --- Handle Excited Animation State (Fourth Highest Priority) ---
    # Check if Sad, Happy, Angry are not active before processing Excited transitions
    if state.sad_state == 0 and state.happy_state == 0 and state.angry_state == 0:
        if state.excited_state == 1: # Quick bounce up
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.excited_phase_start_time
            if elapsed_phase_time >= config.EXCITED_BOUNCE_DURATION_MS:
                state.excited_state = 2 # Transition to jiggle phase
                state.excited_phase_start_time = current_time_ms # Reset phase timer for phase 2 start
                state.shake_start_time = current_time_ms # Start shake timer for state 2's specific jiggle
                #print("Excited state: Bounce complete, starting jiggle.")

        elif state.excited_state == 2: # Jiggle rapidly
            is_any_specific_animation_active = True
            elapsed_jiggle_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
            if elapsed_jiggle_time >= config.EXCITED_JIGGLE_DURATION_MS:
                state.excited_state = 3 # Transition to settle phase
                state.excited_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
                #print("Excited state: Jiggle complete, starting settle.")

        elif state.excited_state == 3: # Settle
            is_any_specific_animation_active = True
            elapsed_phase_time = current_time_ms - state.excited_phase_start_time
            if elapsed_phase_time >= config.EXCITED_SETTLE_DURATION_MS:
                state.excited_state = 0 # Transition back to idle state
                state.pet_radius = state.current_radius # Ensure radius is reset if it was changed by Excited (currently not, but good practice)
                #print("Excited state: Settle complete, returning to idle.")


    # --- Handle Thinking Animation State (Fifth Highest Priority) ---
    # Check if higher priorities are not active before processing Thinking
    if state.sad_state == 0 and state.happy_state == 0 and state.angry_state == 0 and state.excited_state == 0 and state.is_thinking:
        is_any_specific_animation_active = True
        elapsed_segment_time = current_time_ms - state.thinking_segment_start_time

        # Check if the current segment is finished
        if elapsed_segment_time >= config.THINKING_SEGMENT_DURATION_MS:
            # Move to the next segment
            state.thinking_current_segment_index += 1
            state.thinking_segment_start_time = current_time_ms # Reset timer for the new segment

            # Check if all segments for all cycles are complete
            if state.thinking_current_segment_index > state.thinking_total_segments:
                # Animation finished
                state.is_thinking = False
                state.thinking_current_segment_index = 0 # Reset index
                state.thinking_segment_start_time = 0 # Reset timer
                state.thinking_total_segments = 0 # Reset total
                # Clean up segment path list
                state.thinking_segments_path = []
                state.pet_radius = state.current_radius # Ensure radius is reset
                print("Thinking animation ended.")
                # Note: No need to clear lower priority animations here, as they are only cleared
                # when a *new* higher or equal priority animation starts. Transitioning back to
                # base movement from Thinking is handled by the main loop based on
                # is_any_specific_animation_active being False.


    # --- Handle Curious Animation State (Sixth Highest Priority) ---
    # Check if higher priorities are not active before processing Curious end
    # (Implicit check due to elif structure after higher priorities)
    if state.sad_state == 0 and state.happy_state == 0 and state.angry_state == 0 and state.excited_state == 0 and not state.is_thinking and state.is_curious:
        is_any_specific_animation_active = True
        elapsed_time = current_time_ms - state.curious_start_time
        if elapsed_time >= config.CURIOUS_DURATION_MS:
            state.is_curious = False
            # Clean up stored radius values when animation finishes
            state.original_radius_before_curious = None # <-- Reset
            state.pet_radius = state.current_radius # Ensure radius is reset
            #print("Curious animation ended.")
    # The is_any_specific_animation_active flag is updated here if Confused is active.
    if state.confused_state > 0:
        is_any_specific_animation_active = True
        # Check if any *higher* priority animation is currently active.
        # If so, Confused should pause its transitions.
        # However, the overall update loop's priority handling means this block
        # is only reached if Sad, Happy, Angry, Excited, Thinking, Curious are NOT active.
        # So, the check `is_higher_priority_animation_active('confused')` here
        # is redundant *if* the block structure implies priority.
        # Let's rely on the block structure for simplicity.

        elapsed_phase_time = current_time_ms - state.confused_phase_start_time

        if elapsed_phase_time >= config.CONFUSED_PHASE_DURATION_MS:
            state.confused_state += 1
            state.confused_phase_start_time = current_time_ms # Reset phase timer

            if state.confused_state > 8: # Finished all 8 phases
                state.confused_state = 0 # Transition back to idle state
                # --- CLEANUP STATE FOR CONFUSED ---
                state.confused_start_time = 0 # Reset overall animation timer
                state.confused_phase_start_time = 0 # Reset phase timer
                state.confused_corner_index = 0 # Reset corner index
                state.original_radius_before_confused = None # Reset stored radius
                state.pet_radius = state.current_radius # Ensure radius is reset
                # ----------------------------------
                #print("Confused animation ended.")
            elif state.confused_state % 2 != 0: # Transitioning to an odd state (3, 5, 7) - implies starting a new corner move
                 state.confused_corner_index += 1 # Move to the next target corner for the *next* 'into corner' phase
                 # The index will be 1 after state 2, 2 after state 4, 3 after state 6.
                 # After state 8, we transition to state 0, the index is reset in the cleanup.
                 #print(f"Confused state: Transitioned to phase {state.confused_state}, targeting corner index {state.confused_corner_index}.")
            # else: # Transitioning to an even state (2, 4, 6, 8) - staying at the same corner index conceptually
                 #print(f"Confused state: Transitioned to phase {state.confused_state}.")


    # --- Handle General Shake (Eighth Highest Priority) ---
    # Check if all higher priorities are not active before processing General Shake end

    if state.sad_state == 0 and state.happy_state == 0 and state.angry_state == 0 and state.excited_state == 0 and not state.is_thinking and not state.is_curious and state.confused_state == 0 and state.is_shaking: # <-- Updated check for Confused
         is_any_specific_animation_active = True
         elapsed_shake_time = current_time_ms - state.shake_start_time
         if elapsed_shake_time >= config.SHAKE_DURATION_MS:
             state.is_shaking = False # General shake duration is over
             state.pet_radius = state.current_radius # Ensure radius is reset if it was changed by Shake (currently not, but good practice)
             #print("General shake ended.")


    # The return value should indicate if *any* specific animation (non-base movement) is running.
    # This determines if base movement should be applied in calculate_circle_offset.
    # The flag tracked above is more reliable than re-checking states *after* they might have just transitioned to 0/False
    return is_any_specific_animation_active

# --- Function to calculate the animation offset ---
# --- Function to calculate the animation offset ---
def calculate_circle_offset(current_time_ms):
    """Calculates the current pixel offset (x, y) and potentially size based on animation state.
       This function ONLY calculates the visual effect for the CURRENT state; it does NOT change state."""
    offset_x = 0
    offset_y = 0
    time_in_seconds = current_time_ms / 1000.0 # Total elapsed time for base movement

    # Priority Order (Highest to Lowest): Sad > Happy > Angry > Excited > Thinking > Curious > Confused > General Shake > Base

    # --- Calculate offsets based on Sad Animation State (Highest Priority) ---
    if state.sad_state == 1: # Moving down
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_DROP_DURATION_MS)
        offset_y = progress * config.SAD_DROP_AMOUNT

        # --- NEW SIZE LOGIC FOR SAD PHASE 1 (CONTRACT) ---
        # Interpolate pet_radius from the original size towards the target sad size based on phase progress
        if state.original_radius_before_sad is not None and state.target_sad_radius is not None:
             state.pet_radius = state.original_radius_before_sad + progress * (state.target_sad_radius - state.original_radius_before_sad)
        # -------------------------------------------------

    elif state.sad_state == 2: # Shaking down
        offset_y = config.SAD_DROP_AMOUNT # Maintain dropped position

        # Apply the specific SAD SHAKE parameters
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
        angle_x = elapsed_shake_time / 1000.0 * config.SAD_SHAKE_FREQUENCY_HZ * 2 * math.pi
        angle_y = elapsed_shake_time / 1000.0 * config.SAD_SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        shake_offset_x = config.SAD_SHAKE_INTENSITY * math.sin(angle_x)
        shake_offset_y = config.SAD_SHAKE_INTENSITY * math.sin(angle_y)

        offset_x += shake_offset_x
        offset_y += shake_offset_y # Add shake on top of drop

        # --- NEW SIZE LOGIC FOR SAD PHASE 2 (MAINTAIN CONTRACTED SIZE) ---
        # Set pet_radius directly to the target contracted size calculated when entering sad state 1
        if state.target_sad_radius is not None:
            state.pet_radius = state.target_sad_radius
        # ---------------------------------------------------------------

    elif state.sad_state == 3: # Moving up
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_RISE_DURATION_MS)
        offset_y = (1.0 - progress) * config.SAD_DROP_AMOUNT # Interpolate from dropped back to zero

        # --- NEW SIZE LOGIC FOR SAD PHASE 3 (EXPAND BACK TO ORIGINAL) ---
        # Interpolate pet_radius from target_sad_radius back to original_radius_before_sad
        if state.original_radius_before_sad is not None and state.target_sad_radius is not None:
             state.pet_radius = state.target_sad_radius + progress * (state.original_radius_before_sad - state.target_sad_radius)
        # --------------------------------------------------------------


# --- Calculate offsets based on Happy Animation State (Second Highest Priority, only if Sad is Idle) ---
    # These checks implicitly mean Sad is state 0 because of the priority order
    elif state.happy_state == 1: # Dipping down
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_DIP_DURATION_MS)
        offset_y = progress * config.HAPPY_DIP_AMOUNT

        # --- NEW SIZE LOGIC FOR HAPPY PHASE 1 (EXPAND) ---
        # Interpolate pet_radius from the original size towards the target happy size based on phase progress
        # The speed/rate of this size change is determined by config.HAPPY_DIP_DURATION_MS
        if state.original_radius_before_happy is not None and state.target_happy_radius is not None:
             state.pet_radius = state.original_radius_before_happy + progress * (state.target_happy_radius - state.original_radius_before_happy)
        # ----------------------------------------------


    elif state.happy_state == 2: # Shaking happily with Orbit
        # The base position for this state is the dipped position
        base_vertical_pos_offset = config.HAPPY_DIP_AMOUNT
        offset_x = 0 # Start with zero offset relative to base position
        offset_y = base_vertical_pos_offset

        elapsed_phase_time = current_time_ms - state.happy_phase_start_time # Time in current phase

        # --- Apply Configurable Orbit ---
        # Determine current orbit radius based on phase progress (fade in/out)
        phase_duration = config.HAPPY_SHAKE_DURATION_MS # Total duration of phase 2

        # Calculate progress for fade-in and fade-out using elapsed time in phase
        fade_in_progress = min(1.0, elapsed_phase_time / config.HAPPY_ORBIT_FADE_IN_DURATION_MS)
        # Calculate time remaining in phase, and progress within the fade-out window
        time_remaining_in_phase = max(0.0, phase_duration - elapsed_phase_time)
        fade_out_progress = min(1.0, max(0.0, (config.HAPPY_ORBIT_FADE_OUT_DURATION_MS - time_remaining_in_phase) / config.HAPPY_ORBIT_FADE_OUT_DURATION_MS))


        # Apply ease-out quadratic for smoother fade effect
        eased_fade_in_progress = -(fade_in_progress) * (fade_in_progress - 2)
        eased_fade_out_progress = -(fade_out_progress) * (fade_out_progress - 2)

        # Combine fade-in and fade-out factors
        # During fade-in, factor goes from 0 to 1. During fade-out, it goes from 1 to 0.
        # The effective factor peaks at 1 in the middle portion of the phase.
        current_orbit_factor = eased_fade_in_progress * (1.0 - eased_fade_out_progress)

        current_orbit_radius = config.HAPPY_ORBIT_RADIUS * current_orbit_factor

        # Calculate orbit angle based on elapsed time in the phase and frequency
        orbit_angle = elapsed_phase_time / 1000.0 * config.HAPPY_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.HAPPY_ORBIT_START_ANGLE

        orbit_offset_x = current_orbit_radius * math.cos(orbit_angle)
        orbit_offset_y = current_orbit_radius * math.sin(orbit_angle)


        # --- Apply HAPPY SHAKE parameters ---
        # Use shake_start_time for the jiggle's internal timer for consistent oscillation pattern
        elapsed_jiggle_timer_time = current_time_ms - state.shake_start_time
        jiggle_angle_x = elapsed_jiggle_timer_time / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi
        jiggle_angle_y = elapsed_jiggle_timer_time / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        shake_offset_x = config.HAPPY_SHAKE_INTENSITY * math.sin(jiggle_angle_x)
        shake_offset_y = config.HAPPY_SHAKE_INTENSITY * math.sin(jiggle_angle_y)


        # Combine base dip, shake, and orbit offsets
        # Orbit and Shake are added relative to the base dipped position (0, base_vertical_pos_offset)
        offset_x = orbit_offset_x + shake_offset_x
        offset_y = base_vertical_pos_offset + orbit_offset_y + shake_offset_y


        # --- NEW SIZE LOGIC FOR HAPPY PHASE 2 (MAINTAIN EXPANDED SIZE) ---
        # Set pet_radius directly to the target expanded size calculated when entering happy state 1
        # Size remains constant during this phase
        if state.target_happy_radius is not None:
            state.pet_radius = state.target_happy_radius
        # ----------------------------------------------------------------


    elif state.happy_state == 3: # Bouncing up
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_RISE_DURATION_MS)
        offset_y = (1.0 - progress) * config.HAPPY_DIP_AMOUNT # Interpolate from dipped back to zero

        # --- NEW SIZE LOGIC FOR HAPPY PHASE 3 (SHRINK BACK TO ORIGINAL) ---
        # Interpolate pet_radius from target_happy_radius back to original_radius_before_happy
        # The speed/rate of this size change is determined by config.HAPPY_RISE_DURATION_MS
        if state.original_radius_before_happy is not None and state.target_happy_radius is not None:
             state.pet_radius = state.target_happy_radius + progress * (state.original_radius_before_happy - state.target_happy_radius)
        # ----------------------------------------------------------------
    # --- Handle Angry Animation State (Third Highest Priority) ---
    # These checks implicitly mean Sad and Happy are state 0
    elif state.angry_state == 1: # Tense down and Grow (Phase 1)
        elapsed_phase_time = current_time_ms - state.angry_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.ANGRY_TENSE_DURATION_MS)
        offset_y = progress * config.ANGRY_TENSE_AMOUNT # Move down

        # Interpolate pet_radius from the original size towards the target angry size based on phase progress
        if state.original_radius_before_angry is not None and state.target_angry_radius is not None:
             state.pet_radius = state.original_radius_before_angry + progress * (state.target_angry_radius - state.original_radius_before_angry)


    elif state.angry_state == 2: # Vibrate intensely and Maintain Size (Phase 2)
        # The base position for this state is the tensed position (downward)
        offset_y = config.ANGRY_TENSE_AMOUNT # Maintain tensed position
        offset_x = 0 # No horizontal offset for the base position in this state

        # Set pet_radius directly to the target maximum size calculated earlier when entering angry state 1
        if state.target_angry_radius is not None:
            state.pet_radius = state.target_angry_radius

        # Apply the specific ANGRY VIBRATE parameters
        elapsed_vibrate_time = current_time_ms - state.shake_start_time # Use the shake timer specifically set when entering state 2
        angle_x = elapsed_vibrate_time / 1000.0 * config.ANGRY_VIBRATE_FREQUENCY_HZ * 2 * math.pi
        angle_y = elapsed_vibrate_time / 1000.0 * config.ANGRY_VIBRATE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        vibrate_offset_x = config.ANGRY_VIBRATE_INTENSITY * math.sin(angle_x)
        vibrate_offset_y = config.ANGRY_VIBRATE_INTENSITY * math.sin(angle_y)

        # Add the vibration offsets to the current total offset
        offset_x += vibrate_offset_x
        offset_y += vibrate_offset_y # Add vibration on top of tense position


    elif state.angry_state == 3: # Settle up and Shrink (Phase 3)
        elapsed_phase_time = current_time_ms - state.angry_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.ANGRY_SETTLE_DURATION_MS)
        offset_y = (1.0 - progress) * config.ANGRY_TENSE_AMOUNT # Interpolate from tensed back to zero

        # Interpolate pet_radius from target_angry_radius back to original_radius_before_angry
        if state.original_radius_before_angry is not None and state.target_angry_radius is not None:
             state.pet_radius = state.target_angry_radius + progress * (state.original_radius_before_angry - state.target_angry_radius)
        # If animation finishes (progress=1), pet_radius will be back to original. Cleanup happens in update_animation_state.


    # --- Calculate offsets based on Excited Animation State (Fourth Highest Priority) ---
    # These checks implicitly mean Sad, Happy, Angry are state 0
    elif state.excited_state == 1: # Quick bounce up
        elapsed_phase_time = current_time_ms - state.excited_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.EXCITED_BOUNCE_DURATION_MS)
        # Apply a parabolic easing function for the upward movement (ease-out quadratic)
        # This moves the offset from 0 towards -config.EXCITED_BOUNCE_AMOUNT parabolically
        # Ease-out quadratic: f(t) = -t * (t - 2)
        eased_progress = -(progress) * (progress - 2)
        offset_y = -config.EXCITED_BOUNCE_AMOUNT * eased_progress
        # Size remains default/base (unless you want to add size changes here)


    elif state.excited_state == 2: # Jiggle rapidly and Orbit
        # Calculate elapsed time in Phase 2
        elapsed_phase_time = current_time_ms - state.excited_phase_start_time

        # Base vertical position for the orbit center is the peak bounce height from phase 1
        base_vertical_pos_offset = -config.EXCITED_BOUNCE_AMOUNT

        # --- Calculate Orbit Offset ---
        # Orbit radius fades in smoothly over the first part of the phase
        fade_in_progress = min(1.0, elapsed_phase_time / config.EXCITED_ORBIT_FADE_IN_DURATION_MS)
        # Use ease-out quadratic for radius fade-in
        eased_fade_in_progress = -(fade_in_progress) * (fade_in_progress - 2)
        current_orbit_radius = config.EXCITED_ORBIT_RADIUS * eased_fade_in_progress

        # Calculate orbit angle based on elapsed time and frequency
        orbit_angle = elapsed_phase_time / 1000.0 * config.EXCITED_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.EXCITED_ORBIT_START_ANGLE

        # Calculate orbit offset relative to the base position (screen center for X, peak bounce for Y)
        orbit_offset_x = current_orbit_radius * math.cos(orbit_angle)
        orbit_offset_y = current_orbit_radius * math.sin(orbit_angle)

        # --- Calculate Jiggle Offset ---
        # Jiggle intensity fades in smoothly over the first part of the phase
        jiggle_fade_in_progress = min(1.0, elapsed_phase_time / config.EXCITED_JIGGLE_FADE_IN_DURATION_MS)
         # Use ease-out quadratic for jiggle fade-in
        eased_jiggle_fade_in_progress = -(jiggle_fade_in_progress) * (jiggle_fade_in_progress - 2)
        current_jiggle_intensity = config.EXCITED_JIGGLE_INTENSITY * eased_jiggle_fade_in_progress


        # Use shake_start_time for the jiggle's internal timer for consistent oscillation pattern
        elapsed_jiggle_timer_time = current_time_ms - state.shake_start_time
        jiggle_angle_x = elapsed_jiggle_timer_time / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi
        jiggle_angle_y = elapsed_jiggle_timer_time / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift for Y jiggle

        jiggle_offset_x = current_jiggle_intensity * math.sin(jiggle_angle_x)
        jiggle_offset_y = current_jiggle_intensity * math.sin(jiggle_angle_y)

        # Combine all offsets: Orbit relative to base + Base Bounce Vertical + Jiggle
        # The orbit is centered around (0, base_vertical_pos_offset) relative to the screen center.
        offset_x = orbit_offset_x + jiggle_offset_x
        offset_y = base_vertical_pos_offset + orbit_offset_y + jiggle_offset_y

        # Size remains default/base (unless you want to add size changes here)


    elif state.excited_state == 3: # Settle
        elapsed_phase_time = current_time_ms - state.excited_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.EXCITED_SETTLE_DURATION_MS)
        # Use ease-out quadratic for the settle movement back to origin
        eased_progress = -(progress) * (progress - 2)


        # Calculate the exact offset at the moment Phase 3 started (which is the end of Phase 2)
        # This part is correct for position interpolation, leaving it as is.
        time_at_end_of_phase_2 = state.excited_phase_start_time
        elapsed_time_in_phase_2_at_end = config.EXCITED_JIGGLE_DURATION_MS # Total duration of phase 2

        # Recalculate orbit radius at the end of phase 2 (should be near full radius)
        fade_in_progress_at_end_phase2 = min(1.0, elapsed_time_in_phase_2_at_end / config.EXCITED_ORBIT_FADE_IN_DURATION_MS)
        eased_fade_in_progress_at_end_phase2 = -(fade_in_progress_at_end_phase2) * (fade_in_progress_at_end_phase2 - 2)
        end_phase2_orbit_radius = config.EXCITED_ORBIT_RADIUS * eased_fade_in_progress_at_end_phase2

        # Recalculate orbit angle at the end of phase 2
        end_phase2_orbit_angle = elapsed_time_in_phase_2_at_end / 1000.0 * config.EXCITED_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.EXCITED_ORBIT_START_ANGLE
        end_phase2_orbit_offset_x = end_phase2_orbit_radius * math.cos(end_phase2_orbit_angle)
        end_phase2_orbit_offset_y = end_phase2_orbit_radius * math.sin(end_phase2_orbit_angle)


        # Recalculate jiggle intensity at the end of phase 2 (should be near full intensity)
        jiggle_fade_in_progress_at_end_phase2 = min(1.0, elapsed_time_in_phase_2_at_end / config.EXCITED_JIGGLE_FADE_IN_DURATION_MS)
        eased_jiggle_fade_in_progress_at_end_phase2 = -(jiggle_fade_in_progress_at_end_phase2) * (jiggle_fade_in_progress_at_end_phase2 - 2)
        end_phase2_jiggle_intensity = config.EXCITED_JIGGLE_INTENSITY * eased_jiggle_fade_in_progress_at_end_phase2

        # Recalculate jiggle offset at the end of phase 2 using shake_start_time
        # Note: The shake_start_time for phase 2 is set when entering phase 2.
        # The elapsed_time_in_phase_2_at_end is the *duration* of phase 2, not the time since shake_start_time.
        # To get the correct jiggle state *at the end of phase 2*, we need to know the absolute time pygame.time.get_ticks() was
        # at the moment phase 2 ended (which is the moment phase 3 started: state.excited_phase_start_time).
        # Or, more simply, calculate how much time has passed since shake_start_time IF Phase 2 ran for its full duration.
        # The original calculation: `elapsed_jiggle_timer_time = current_time_ms - state.shake_start_time` should be evaluated
        # using the `current_time_ms` *at the moment phase 2 ended*. This value *is* state.excited_phase_start_time for Phase 3.
        end_phase2_actual_time = state.excited_phase_start_time # This is the time Phase 3 started
        elapsed_jiggle_timer_time_at_end_phase2 = end_phase2_actual_time - (state.excited_phase_start_time - config.EXCITED_JIGGLE_DURATION_MS) if state.excited_phase_start_time is not None else 0 # Reconstruct shake start time
        # Alternatively, just use the duration if the animation completed its phase:
        # end_phase2_jiggle_timer_time = config.EXCITED_JIGGLE_DURATION_MS # The total time the shake timer ran if phase 2 completed


        # Let's stick to the simpler logic: The jiggle pattern should be evaluated based on the total time the jiggle timer ran
        # *if* the phase completed normally. The shake_start_time is set at the *beginning* of phase 2.
        # The total duration of phase 2 is config.EXCITED_JIGGLE_DURATION_MS.
        # So, the elapsed time on the jiggle timer at the end of phase 2 is just the duration of phase 2.
        end_phase2_jiggle_timer_time = config.EXCITED_JIGGLE_DURATION_MS
        end_phase2_jiggle_angle_x = end_phase2_jiggle_timer_time / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi
        end_phase2_jiggle_angle_y = end_phase2_jiggle_timer_time / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift for Y jiggle
        end_phase2_jiggle_offset_x = end_phase2_jiggle_intensity * math.sin(end_phase2_jiggle_angle_x)
        end_phase2_jiggle_offset_y = end_phase2_jiggle_intensity * math.sin(end_phase2_jiggle_angle_y)


        # Calculate the total offset at the end of phase 2
        end_phase2_total_offset_x = end_phase2_orbit_offset_x + end_phase2_jiggle_offset_x
        # Orbit was centered around -EXCITED_BOUNCE_AMOUNT vertically
        end_phase2_total_offset_y = -config.EXCITED_BOUNCE_AMOUNT + end_phase2_orbit_offset_y + end_phase2_jiggle_offset_y


        # Interpolate from the end_phase2_total_offset back to (0,0) using eased progress
        offset_x = end_phase2_total_offset_x * (1.0 - eased_progress)
        offset_y = end_phase2_total_offset_y * (1.0 - eased_progress)

        # Size remains default/base (unless you want to add size changes here)

    # --- Calculate offsets based on Thinking Animation State (Fifth Highest Priority) ---
    # These checks implicitly mean higher priorities are state 0/False
    elif state.is_thinking:
        # Ensure we have a valid segment index and path
        if state.thinking_current_segment_index > 0 and state.thinking_segments_path:
            # Calculate which segment in the base 10-segment path we are currently on
            # The index within the base path repeats every 10 segments
            base_path_index = (state.thinking_current_segment_index - 1) % 10 # 0-based index

            # Get the start and end points for the current segment
            start_point, end_point = state.thinking_segments_path[base_path_index]

            # Calculate progress along the current segment
            elapsed_segment_time = current_time_ms - state.thinking_segment_start_time
            # Use max(0, ...) to handle cases where segment_start_time might be slightly in the future due to timing
            # Use min(1.0, ...) to cap progress at 1.0 even if elapsed time exceeds duration (waiting for state transition)
            progress = min(1.0, max(0.0, elapsed_segment_time / config.THINKING_SEGMENT_DURATION_MS))

            # Interpolate linearly between the start and end points of the segment
            offset_x = start_point[0] + (end_point[0] - start_point[0]) * progress
            offset_y = start_point[1] + (end_point[1] - start_point[1]) * progress

        # If state.is_thinking is True but segment state is invalid, default to origin (shouldn't happen with correct logic)
        else:
            offset_x = 0
            offset_y = 0
            # Potentially log an error here if this branch is hit unexpectedly
            print("Warning: Thinking state active but segment state invalid.")

        # Size remains default/base
        # state.pet_radius = state.current_radius # This should be handled when animation ends

     # --- Calculate offsets and size based on Curious Animation State (Sixth Highest Priority) ---
    # These checks implicitly mean higher priorities are state 0/False
    elif state.is_curious:
        elapsed_time = current_time_ms - state.curious_start_time # Time since curious animation started
        time_in_seconds_curious = elapsed_time / 1000.0 # Elapsed time in seconds for curious animation

        # Calculate horizontal sway
        # Use elapsed time for the sine wave
        sway_angle_x = time_in_seconds_curious * config.CURIOUS_SWAY_FREQUENCY_HZ * 2 * math.pi
        offset_x = config.CURIOUS_SWAY_AMPLITUDE_X * math.sin(sway_angle_x)

        # Calculate subtle vertical sway (optional)
        if config.CURIOUS_SWAY_AMPLITUDE_Y > 0:
             sway_angle_y = time_in_seconds_curious * config.CURIOUS_SWAY_FREQUENCY_HZ * 2 * math.pi + config.CURIOUS_SWAY_PHASE_SHIFT_Y
             offset_y = config.CURIOUS_SWAY_AMPLITUDE_Y * math.sin(sway_angle_y)
        else:
             offset_y = 0 # No vertical sway if amplitude is 0

        # --- Calculate size pulse ---
        # Only apply size pulse if original radius was captured and percentage is non-zero
        if state.original_radius_before_curious is not None and config.CURIOUS_SIZE_CHANGE_PERCENTAGE != 0:
            # Use elapsed time for the size pulse sine wave
            size_angle = time_in_seconds_curious * config.CURIOUS_SIZE_PULSE_FREQUENCY_HZ * 2 * math.pi
            # Calculate the size offset from the original radius based on the sine wave
            size_offset = state.original_radius_before_curious * config.CURIOUS_SIZE_CHANGE_PERCENTAGE * math.sin(size_angle)
            # Set the pet_radius to the original radius plus the calculated offset
            state.pet_radius = state.original_radius_before_curious + size_offset
        # Else, size remains whatever it was when the animation started (e.g. state.current_radius if coming from base)


    elif state.confused_state > 0:
        elapsed_phase_time = current_time_ms - state.confused_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.CONFUSED_PHASE_DURATION_MS)

        # Define corner coordinates relative to center (0,0)
        corners = [
            (-config.CONFUSED_X_OFFSET_AMOUNT, -config.CONFUSED_Y_OFFSET_AMOUNT), # Top-Left (Index 0)
            (config.CONFUSED_X_OFFSET_AMOUNT, -config.CONFUSED_Y_OFFSET_AMOUNT),  # Top-Right (Index 1)
            (-config.CONFUSED_X_OFFSET_AMOUNT, config.CONFUSED_Y_OFFSET_AMOUNT),  # Bottom-Left (Index 2)
            (config.CONFUSED_X_OFFSET_AMOUNT, config.CONFUSED_Y_OFFSET_AMOUNT)   # Bottom-Right (Index 3)
        ]

        start_pos = (0, 0)
        end_pos = (0, 0)
        # Determine start and end positions based on the current phase
        # Phases 1, 3, 5, 7: Center -> Corner
        # Phases 2, 4, 6, 8: Corner -> Center

        if state.confused_state % 2 != 0: # Odd state (1, 3, 5, 7) - Center -> Corner
            start_pos = (0, 0)
            # Calculate corner index for this phase: (1-1)//2=0, (3-1)//2=1, (5-1)//2=2, (7-1)//2=3
            corner_index_for_this_phase = (state.confused_state - 1) // 2
            # Ensure index is within bounds (should be 0-3)
            if 0 <= corner_index_for_this_phase < len(corners):
                 end_pos = corners[corner_index_for_this_phase]
            else:
                 # Fallback to no movement if index is somehow invalid
                 print(f"Error: Invalid confused_corner_index calculated: {corner_index_for_this_phase} for state {state.confused_state}")
                 start_pos = (0,0)
                 end_pos = (0,0)


        else: # Even state (2, 4, 6, 8) - Corner -> Center
            # Calculate start corner index for this phase: (2-2)//2=0, (4-2)//2=1, (6-2)//2=2, (8-2)//2=3
            corner_index_for_this_phase = (state.confused_state - 2) // 2
            # Ensure index is within bounds (should be 0-3)
            if 0 <= corner_index_for_this_phase < len(corners):
                start_pos = corners[corner_index_for_this_phase]
            else:
                 # Fallback to no movement if index is somehow invalid
                 print(f"Error: Invalid confused_corner_index calculated: {corner_index_for_this_phase} for state {state.confused_state}")
                 start_pos = (0,0)

            end_pos = (0, 0)

        # Interpolate position
        offset_x = start_pos[0] + progress * (end_pos[0] - start_pos[0])
        offset_y = start_pos[1] + progress * (end_pos[1] - start_pos[1])

        # --- Size Pulsing Logic ---
        # The pulse depends on the total time since the confused animation started,
        # not just the current phase time, for a continuous effect.
        if state.original_radius_before_confused is not None and state.confused_start_time is not None:
            total_elapsed_confused_time = current_time_ms - state.confused_start_time
            # Calculate the angle for the sine wave based on total elapsed time and frequency
            pulse_angle = total_elapsed_confused_time / 1000.0 * config.CONFUSED_SIZE_PULSE_FREQUENCY_HZ * 2 * math.pi

            # Calculate the change in size from the original radius
            size_change_amplitude = state.original_radius_before_confused * config.CONFUSED_SIZE_PULSE_AMPLITUDE_PERCENTAGE

            # Apply the sine wave for the size change. Adds/subtracts from the original radius.
            state.pet_radius = state.original_radius_before_confused + size_change_amplitude * math.sin(pulse_angle)

            # Ensure radius doesn't become too small (e.g., negative or zero)
            state.pet_radius = max(1, state.pet_radius)
        else:
             # Fallback if state vars are not set correctly (shouldn't happen if animation starts correctly)
             state.pet_radius = state.current_radius # Use default radius

    # --- Calculate General Shake (Eighth Highest Priority, only if all above are Idle) ---
    # This check implicitly means all higher priorities are state 0/False
    elif state.is_shaking:
        elapsed_shake_time = current_time_ms - state.shake_start_time
        angle_x = elapsed_shake_time / 1000.0 * config.SHAKE_FREQUENCY_HZ * 2 * math.pi
        angle_y = elapsed_shake_time / 1000.0 * config.SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        offset_x = config.SHAKE_INTENSITY * math.sin(angle_x)
        offset_y = config.SHAKE_INTENSITY * math.sin(angle_y)
        # Optional: Size change? If so, need config/state vars for it.
        # Size remains default/base



    # --- Calculate Base Movement (Lowest Priority, only when all specific animations are Idle) ---
    # This check implicitly means all specific animations are state 0/False
    else:
         # Calculate base bobbing (vertical) offset using total time for continuous effect
         bob_angle = time_in_seconds * config.BASE_BOB_FREQUENCY * 2 * math.pi
         offset_y = config.BASE_BOB_AMPLITUDE * math.sin(bob_angle)

         # Calculate base swaying (horizontal) offset using total time for continuous effect
         sway_angle = time_in_seconds * config.BASE_SWAY_FREQUENCY * 2 * math.pi + config.BASE_PHASE_SHIFT
         offset_x = config.BASE_SWAY_AMPLITUDE * math.sin(sway_angle)

         # Ensure radius is back to default/base if it was changed by a previous animation
         # This is handled by cleanup in update_animation_state when an animation finishes,
         # but this ensures it's reset if we transition directly to base movement for any reason.
         state.pet_radius = state.current_radius

    return (offset_x, offset_y)


# Note: The 'neutral' state is implicitly the absence of any specific animation,
# resulting in the base movement calculated in the final 'elif' block of
# calculate_circle_offset.

# Add a placeholder function for 'neutral' if you want to be able to
# explicitly trigger a return to base movement, though stopping other
# animations is often handled by simply setting their state back to 0/False.

def start_neutral_animation():
    """Clears all specific animation states to return to neutral base movement."""
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        gui.add_message_to_history("System: Cannot manually trigger neutral while bot is resting.", 'system')
        return

    # Check if we are already in a neutral state (no specific animation active)
    # Call update_animation_state to process any final frame transitions before checking
    is_currently_any_specific_animation_active = update_animation_state(current_time_ms)

    if not is_currently_any_specific_animation_active:
        # Already neutral, do nothing
        pass # print("Already in neutral state.")
    else:
        # Clear all active specific animations using the refactored helper
        # Passing a name that isn't in the list (like 'Base') effectively clears *all* entries in the list
        clear_lower_priority_animations('Base_Placeholder_To_Clear_All')

        # Explicitly set radius back to default just in case
        state.pet_radius = state.current_radius

        print("Returned to neutral state.")
        gui.add_message_to_history("System: Returned to neutral state.", 'system')