# animation.py

from pygame_int import config # Needed for animation constants and event types
from pygame_int import state # Needed for accessing/modifying animation state variables and sleep state

import pygame
import math # Needed for sine/cosine calculations
from pygame_int import gui # Needed to add system messages to history (e.g., input locked)

# --- Function to start the circle shake animation ---
def start_circle_shake():
    """Starts the general circle shake animation if not already in a sad/happy state or asleep."""
    # Access state variables directly using state. prefix

    # Only allow manual shake if not asleep
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        print("Input locked - bot is asleep. Ignoring manual shake command.")
        gui.add_message_to_history("System: Cannot manually trigger shake while bot is resting.", 'system')
        return

    # Only general shake if not already in a sad or happy sequence
    if state.sad_state == 0 and state.happy_state == 0:
        state.is_shaking = True
        state.shake_start_time = pygame.time.get_ticks()
        #print("Circle shake started (general).")
    else:
        pass # print("Shake signal received, but sad or happy animation is active. Ignoring general shake.")


# --- Function to start the sad animation sequence ---
def start_sad_animation():
    """Starts the sad animation sequence (dropping, shaking down, rising)."""
    # Access state variables directly using state. prefix

    # Only allow manual sad if not asleep
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        print("Input locked - bot is asleep. Ignoring manual sad command.")
        gui.add_message_to_history("System: Cannot manually trigger sad while bot is resting.", 'system')
        return

    # Only start if not already in a sad sequence AND not in a happy sequence
    # (Sad takes priority over Happy)
    if state.sad_state == 0 and state.happy_state == 0:
        state.sad_state = 1 # Start dropping
        state.sad_phase_start_time = pygame.time.get_ticks()
        state.is_shaking = False # Stop general shake if happening
        state.happy_state = 0 # Ensure happy is stopped if it somehow was active (shouldn't happen with the check, but good practice)
        #print("Sad animation started (dropping).")
    else:
        pass # print(f"Sad animation signal received, but already in sad state {state.sad_state} or happy state {state.happy_state}. Ignoring.")

# --- Function to start the happy animation sequence ---
def start_happy_animation():
    """Starts the happy animation sequence (dipping, shaking happily, bouncing up)."""
    # Access state variables directly using state. prefix

    # Only allow manual happy if not asleep
    current_time_ms = pygame.time.get_ticks()
    if current_time_ms < state.autonomous_action_paused_until_ms:
        print("Input locked - bot is asleep. Ignoring manual happy command.")
        gui.add_message_to_history("System: Cannot manually trigger happy while bot is resting.", 'system')
        return

    # Only start if not already in a sad sequence AND not in a happy sequence
    # (Sad takes priority over Happy)
    if state.sad_state == 0 and state.happy_state == 0:
        state.happy_state = 1 # Start dipping
        state.happy_phase_start_time = pygame.time.get_ticks()
        state.is_shaking = False # Stop general shake if happening
        #print("Happy animation started (dipping).")
    else:
        pass # print(f"Happy animation signal received, but already in sad state {state.sad_state} or happy state {state.happy_state}. Ignoring.")


# --- Function to update animation state based on timers ---
def update_animation_state(current_time_ms):
    """Updates the state variables for ongoing animations (sad, happy, general shake).
       Returns True if any specific animation (non-base movement) is active, False otherwise."""
    # Access state variables directly using state. prefix

    animation_active = False # Flag to indicate if any specific animation is currently running

    # --- Handle Sad Animation State (Highest Priority) ---
    if state.sad_state == 1: # Moving down
        animation_active = True
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_DROP_DURATION_MS)
        if progress >= 1.0:
            state.sad_state = 2 # Transition to shaking down phase
            state.sad_phase_start_time = current_time_ms # Reset phase timer for phase 2 start
            state.shake_start_time = current_time_ms # Start shake timer for state 2's specific shake
            #print("Sad state: Dropping complete, starting shake down.")

    elif state.sad_state == 2: # Shaking down
        animation_active = True
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
        if elapsed_shake_time >= config.SAD_SHAKE_DURATION_MS: # Check against state 2's shake duration
            state.sad_state = 3 # Transition to rising phase
            state.sad_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
            #print("Sad state: Shaking down complete, starting rise.")

    elif state.sad_state == 3: # Moving up
        animation_active = True
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_RISE_DURATION_MS)
        if progress >= 1.0:
            state.sad_state = 0 # Transition back to idle state
            #print("Sad state: Rising complete, returning to idle.")

    # --- Handle Happy Animation State (Second Highest Priority, only if Sad is Idle) ---
    # Check happy state ONLY if sad_state is 0
    elif state.sad_state == 0 and state.happy_state == 1: # Dipping down
        animation_active = True
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_DIP_DURATION_MS) # Use HAPPY_DIP_DURATION_MS
        if progress >= 1.0:
            state.happy_state = 2 # Transition to shaking happy phase
            state.happy_phase_start_time = current_time_ms # Reset phase timer for phase 2 start
            state.shake_start_time = current_time_ms # Start shake timer for state 2's specific shake
            #print("Happy state: Dipping complete, starting happy shake.")

    elif state.sad_state == 0 and state.happy_state == 2: # Shaking happily
        animation_active = True
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use the shake timer specific to phase 2
        if elapsed_shake_time >= config.HAPPY_SHAKE_DURATION_MS: # Check against state 2's shake duration
            state.happy_state = 3 # Transition to rising phase
            state.happy_phase_start_time = current_time_ms # Reset phase timer for phase 3 start
            #print("Happy state: Shaking happy complete, starting bounce up.")

    elif state.sad_state == 0 and state.happy_state == 3: # Bouncing up
        animation_active = True
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_RISE_DURATION_MS) # Use HAPPY_RISE_DURATION_MS
        if progress >= 1.0:
            state.happy_state = 0 # Transition back to idle state
            #print("Happy state: Rising complete, returning to idle.")

    # --- Handle General Shake (Third Highest Priority, only if Sad and Happy are Idle) ---
    # Only update general shake state if sad_state is 0 AND happy_state is 0
    elif state.sad_state == 0 and state.happy_state == 0 and state.is_shaking:
        animation_active = True
        elapsed_shake_time = current_time_ms - state.shake_start_time
        if elapsed_shake_time >= config.SHAKE_DURATION_MS: # Check against general shake duration
            state.is_shaking = False # General shake duration is over
            #print("General shake ended.")

    # The return value should indicate if *any* specific animation (sad, happy, general shake) is running.
    # If none are running, base movement implicitly takes over (handled in calculate_circle_offset).
    # So, return True if sad_state or happy_state is non-zero, or if is_shaking is True.
    return state.sad_state != 0 or state.happy_state != 0 or state.is_shaking


# --- Function to calculate the animation offset ---
def calculate_circle_offset(current_time_ms):
    """Calculates the current pixel offset (x, y) for the circle based on animation state."""
    # Read state variables using state. prefix. No global needed as we don't assign here.
    offset_x = 0
    offset_y = 0
    time_in_seconds = current_time_ms / 1000.0

    # --- Calculate offsets based on Sad Animation State (Highest Priority) ---
    if state.sad_state == 1: # Moving down
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_DROP_DURATION_MS)
        offset_y = progress * config.SAD_DROP_AMOUNT

    elif state.sad_state == 2: # Shaking down
        offset_y = config.SAD_DROP_AMOUNT # Maintain dropped position

        # Apply the specific SAD SHAKE parameters
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use shake timer from state update
        # Use the elapsed time *within this state* for the shake animation
        angle_x = elapsed_shake_time / 1000.0 * config.SAD_SHAKE_FREQUENCY_HZ * 2 * math.pi
        angle_y = elapsed_shake_time / 1000.0 * config.SAD_SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        shake_offset_x = config.SAD_SHAKE_INTENSITY * math.sin(angle_x)
        shake_offset_y = config.SAD_SHAKE_INTENSITY * math.sin(angle_y)

        offset_x += shake_offset_x
        offset_y += shake_offset_y # Add shake on top of drop

    elif state.sad_state == 3: # Moving up
        elapsed_phase_time = current_time_ms - state.sad_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.SAD_RISE_DURATION_MS)
        offset_y = (1.0 - progress) * config.SAD_DROP_AMOUNT # Interpolate from dropped back to zero

    # --- Calculate offsets based on Happy Animation State (Second Highest Priority, only if Sad is Idle) ---
    # Apply happy animation offsets ONLY if sad_state is 0
    elif state.sad_state == 0 and state.happy_state == 1: # Dipping down
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_DIP_DURATION_MS)
        offset_y = progress * config.HAPPY_DIP_AMOUNT # Use HAPPY_DIP_AMOUNT

    elif state.sad_state == 0 and state.happy_state == 2: # Shaking happily
        offset_y = config.HAPPY_DIP_AMOUNT # Maintain dipped position

        # Apply the specific HAPPY SHAKE parameters
        elapsed_shake_time = current_time_ms - state.shake_start_time # Use shake timer from state update
        # Use the elapsed time *within this state* for the shake animation
        angle_x = elapsed_shake_time / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi # Use HAPPY_SHAKE_FREQUENCY_HZ
        angle_y = elapsed_shake_time / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift, use HAPPY freq

        shake_offset_x = config.HAPPY_SHAKE_INTENSITY * math.sin(angle_x) # Use HAPPY_SHAKE_INTENSITY
        shake_offset_y = config.HAPPY_SHAKE_INTENSITY * math.sin(angle_y) # Use HAPPY_SHAKE_INTENSITY

        offset_x += shake_offset_x
        offset_y += shake_offset_y # Add shake on top of dip

    elif state.sad_state == 0 and state.happy_state == 3: # Bouncing up
        elapsed_phase_time = current_time_ms - state.happy_phase_start_time
        progress = min(1.0, elapsed_phase_time / config.HAPPY_RISE_DURATION_MS)
        offset_y = (1.0 - progress) * config.HAPPY_DIP_AMOUNT # Interpolate from dipped back to zero

    # --- Calculate offsets based on General Shake (Third Highest Priority, only if Sad and Happy are Idle) ---
    # Apply general shake if active AND not in a sad or happy animation phase
    elif state.sad_state == 0 and state.happy_state == 0 and state.is_shaking:
        elapsed_shake_time = current_time_ms - state.shake_start_time
        # Use the elapsed time *within this state* for the shake animation
        angle_x = elapsed_shake_time / 1000.0 * config.SHAKE_FREQUENCY_HZ * 2 * math.pi
        angle_y = elapsed_shake_time / 1000.0 * config.SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2 # Phase shift

        offset_x = config.SHAKE_INTENSITY * math.sin(angle_x)
        offset_y = config.SHAKE_INTENSITY * math.sin(angle_y)

    # --- Calculate Base Movement (Lowest Priority, only when Sad, Happy, and General Shake are Idle) ---
    # Apply base movement if not in any other animation state
    elif state.sad_state == 0 and state.happy_state == 0 and not state.is_shaking:
         # Calculate base bobbing (vertical) offset using total time for continuous effect
         bob_angle = time_in_seconds * config.BASE_BOB_FREQUENCY * 2 * math.pi
         offset_y = config.BASE_BOB_AMPLITUDE * math.sin(bob_angle)

         # Calculate base swaying (horizontal) offset using total time for continuous effect
         sway_angle = time_in_seconds * config.BASE_SWAY_FREQUENCY * 2 * math.pi + config.BASE_PHASE_SHIFT
         offset_x = config.BASE_SWAY_AMPLITUDE * math.sin(sway_angle)

    return (offset_x, offset_y)