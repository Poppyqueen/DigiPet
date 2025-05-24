import colorsys
from pygame_int import config
from pygame_int import state

def set_color_theme():
    """
    Based on the initial pet color this function creates a color theme for the game.

    The theme includes:
        A dictionary of various colors:
            - Original pet color
            - Original color adjusted to target brightness (no alpha)
            - Overlay color with alpha (for drawing the filter)
            - New contrast color (desaturated with tint)
            - Inverted color (for system messages)
            - Black or white (for user messages)
            - Error color (red unless the pet color is red, if so, use green)
            - Dynamic package colors (hydration, fullness, misc, ingredient, combo, cheat)
            - NEW: Key Information/Interactive color
    """

    # --- Configuration ---
    # Define this value as your desired absolute brightness level (0.0 to 1.0)
    
    # ---- Draw filter overlay above the background image ----
    # Define the alpha value for the overlay (0-255, where 255 is opaque)
    alpha_value = 80
    
    # Convert RGB to HSV for brightness adjustment
    # Normalize RGB to 0-1 range for colorsys
    #print(f"--- Original Pet Color: {state.pet_color} ---")
    r, g, b = [x / 255.0 for x in state.pet_color]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    #print(f"Original RGB (normalized): ({r:.2f}, {g:.2f}, {b:.2f})")
    #print(f"Original HSV (normalized): H={h:.2f}, S={s:.2f}, V={v:.2f}")


    # Apply absolute brightness target for the overlay color
    # Set the brightness component directly to the target
    v_adjusted = config.TARGET_BRIGHTNESS 
    
    # Convert back to RGB and denormalize to 0-255 range for Pygame
    adjusted_r, adjusted_g, adjusted_b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v_adjusted)]
    
    state.pets_theme_color = (adjusted_r, adjusted_g, adjusted_b)
    overlay_color_with_alpha = (adjusted_r, adjusted_g, adjusted_b, alpha_value)

    # --- Generate Better Contrast Color & Determine Dynamic Color Targets ---
    # These decisions will influence contrast_color, user_message_color, system_messages,
    # error_color, AND the new package colors.
    if v < 0.60: # If the original color is dark (low brightness)
        #print(f"Original color is dark (V={v:.2f} < 0.6). Aiming for LIGHT contrast elements.")
        contrast_v = 0.85  # Push brightness very high (close to white)
        contrast_s = 0.15  # Reduce saturation significantly (almost grayscale tint)
        user_message_color = (0, 0, 0) # Black for user messages
        
        # When original is dark, contrast_color is light.
        # System messages should be dark.
        inverted_target_v = 0.25 # Target brightness for system messages (dark)
        inverted_target_s = 0.50 # Moderate saturation for system messages

        # Error color: If contrast_color is LIGHT, error_color should be DARK.
        error_target_v = 0.35 # Darker error color
        error_target_s = 0.90 # High saturation

        # Package colors: If contrast_color is LIGHT, package colors should be DARK.
        package_target_v = 0.40 # Medium-dark brightness for package colors
        package_target_s = 0.85 # High saturation for package colors
        combo_target_v = 0.05 # Very dark for combo (closer to black)

        # Key Information/Interactive color target: Should be dark to stand out on light contrast
        interactive_target_v = 0.30 # Relatively dark
        interactive_target_s = 0.95 # High saturation to pop
        
    else: # If the original color is light (high brightness)
        #print(f"Original color is light (V={v:.2f} >= 0.6). Aiming for DARK contrast elements.")
        contrast_v = 0.25  # Push brightness very low (close to black)
        contrast_s = 0.45  # Reduce saturation significantly (almost grayscale tint)
        user_message_color = (255, 255, 255) # White for user messages

        # When original is light, contrast_color is dark.
        # System messages should be light.
        inverted_target_v = 0.75 # Target brightness for system messages (light)
        inverted_target_s = 0.50 # Moderate saturation for system messages

        # Error color: If contrast_color is DARK, error_color should be LIGHT.
        error_target_v = 0.85 # Lighter error color
        error_target_s = 0.90 # High saturation

        # Package colors: If contrast_color is DARK, package colors should be LIGHT.
        package_target_v = 0.60 # Medium-light brightness for package colors
        package_target_s = 0.85 # High saturation for package colors
        combo_target_v = 0.15 # Still dark for combo, but slightly lighter than pure black to stand out from background

        # Key Information/Interactive color target: Should be light to stand out on dark contrast
        interactive_target_v = 0.75 # Relatively light
        interactive_target_s = 0.95 # High saturation to pop


    def invert_hsv_for_messages(h_in, inverted_target_s, inverted_target_v):
        """
        Calculates an 'inverted' HSV color where hue is inverted,
        and saturation/value are set based on desired contrast for messages.
        """
        # print(f"\n--- Inside invert_hsv_for_messages function ---")
        # print(f"  Input Hue: H={h_in:.2f}")
        # print(f"  Target Saturation: {inverted_target_s:.2f}")
        # print(f"  Target Value: {inverted_target_v:.2f}")

        inverted_h = (h_in + 0.5) % 1.0
        inverted_s = inverted_target_s
        inverted_v = inverted_target_v
        
        # print(f"  Final Inverted HSV for messages: H={inverted_h:.2f}, S={inverted_s:.2f}, V={inverted_v:.2f}")
        # print(f"--- End invert_hsv_for_messages function ---")
        
        return inverted_h, inverted_s, inverted_v
    
    # Calculate System Messages Color
    # hsv_tuple_normalized = (h, s, v) # This line is not used
    i_h, i_s, i_v = invert_hsv_for_messages(h, inverted_target_s, inverted_target_v)
    inverted_r_norm, inverted_g_norm, inverted_b_norm = colorsys.hsv_to_rgb(i_h, i_s, i_v)
    inverted_color = (int(inverted_r_norm * 255), int(inverted_g_norm * 255), int(inverted_b_norm * 255))
    #print(f"  Calculated System Message Color: {inverted_color}")
    
    # Calculate Contrast Color
    contrast_r, contrast_g, contrast_b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, contrast_s, contrast_v)]
    contrast_color = (contrast_r, contrast_g, contrast_b)
    #print(f"  Calculated Contrast Color: {contrast_color}")


    def is_red(h_norm, s_norm, v_norm):
        """
        Checks if a color (in normalized HSV) is predominantly red.
        Adjusted for 0.0-1.0 HSV range.
        """
        is_red_hue = (h_norm >= 350/360.0 or h_norm <= 10/360.0)
        is_saturated = s_norm > 0.15
        is_bright_enough = v_norm > 0.1

        return is_red_hue and is_saturated and is_bright_enough

    # --- Calculate Error Color ---
    #print("\n--- Calculating Error Color ---")
    if is_red(h, s, v):
        error_hue = 120 / 360.0 # Pure green hue
        #print(f"  Original pet is RED. Error hue set to GREEN (H={error_hue:.2f})")
    else:
        error_hue = 0 / 360.0 # Pure red hue
        #print(f"  Original pet is NOT RED. Error hue set to RED (H={error_hue:.2f})")

    error_r_norm, error_g_norm, error_b_norm = colorsys.hsv_to_rgb(error_hue, error_target_s, error_target_v)
    error_color = (int(error_r_norm * 255), int(error_g_norm * 255), int(error_b_norm * 255))
    #print(f"  Calculated Error Color: {error_color}")

    # --- Calculate Dynamic Package Colors ---
    #print("\n--- Calculating Dynamic Package Colors ---")
    dynamic_package_colors = {}
    
    # Define base hues for each package type
    package_hues = {
        "hydration": 220 / 360.0, # A standard blue
        "fullness": 0 / 360.0,    # Red
        "misc": 280 / 360.0,      # Purple (slightly more magenta than pure purple)
        "ingredient": 35 / 360.0, # Orange (closer to yellow-orange)
        "cheat": 120 / 360.0      # Green
    }

    # Generate colors for each package type
    for key, base_h in package_hues.items():
        # Use the dynamically determined target S and V
        r_norm, g_norm, b_norm = colorsys.hsv_to_rgb(base_h, package_target_s, package_target_v)
        dynamic_package_colors[key] = (int(r_norm * 255), int(g_norm * 255), int(b_norm * 255))
        #print(f"  {key.capitalize()} Color: {dynamic_package_colors[key]}")

    # Handle "combo" color (always dark, but with a slight variation based on theme)
    r_norm, g_norm, b_norm = colorsys.hsv_to_rgb(0, 0, combo_target_v) # Hue and Saturation don't matter for V=0.0-0.15
    dynamic_package_colors["combo"] = (int(r_norm * 255), int(g_norm * 255), int(b_norm * 255))
    #print(f"  Combo Color: {dynamic_package_colors['combo']}")


    # --- Calculate Key Information / Interactive Color ---
    # Shift pet's hue to get a distinctive related color
    # You can experiment with this shift amount (e.g., 0.2 to 0.4)
    interactive_h = (h + 0.3) % 1.0 # Shift hue by 0.3 (108 degrees) for distinctiveness

    # Calculate the interactive color based on the determined target brightness and saturation
    interactive_r_norm, interactive_g_norm, interactive_b_norm = colorsys.hsv_to_rgb(
        interactive_h, interactive_target_s, interactive_target_v
    )
    key_information_color = (
        int(interactive_r_norm * 255),
        int(interactive_g_norm * 255),
        int(interactive_b_norm * 255)
    )
    #print(f"  Calculated Key Information/Interactive Color: {key_information_color}")


    # Store the generated theme colors in a dictionary
    state.game_theme_colors = {
        "original_pet_color": state.pet_color,
        "adjusted_brightness_color": (adjusted_r, adjusted_g, adjusted_b),
        "overlay_color_with_alpha": overlay_color_with_alpha,
        "contrast_color": contrast_color,
        "system_messages": inverted_color,
        "user_message_color": user_message_color,
        "error_color": error_color,
        "package_colors": dynamic_package_colors,
        "key_information_color": key_information_color, # NEW: Key information/interactive color
    }
