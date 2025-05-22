import pygame # For font operations if directly used
from pygame_int import config
from pygame_int import state
from pygame_int import gui_core # To access _font, _line_height, _text_width_limit

# --- Text Wrapping Function ---
def wrap_text(text, max_width, prefix=""):
    """
    Wraps text based on maximum pixel width using the initialized font.
    Takes into account the prefix length for the first line if provided.
    Uses gui_core._font.
    """
    if gui_core._font is None:
        return [str(text)]  # Avoid crash, return text as single line

    lines = []
    if not text: return [""]

    words = text.split(' ')
    if not words: return [""]

    # Handle the first line with prefix differently
    first_line_max_width = max_width
    if prefix:
        try:
            prefix_width = gui_core._font.size(prefix)[0]
            first_line_max_width = max(1, max_width - prefix_width)
        except pygame.error as e:
            print(f"Pygame error calculating prefix width for '{prefix}': {e}")
            first_line_max_width = max_width # Fallback if size calculation fails


    current_line_words = []
    is_first_line = True
    current_max_width = first_line_max_width

    for word in words:
        # Handle long words that exceed max_width
        # Calculate width safely
        try:
             word_width = gui_core._font.size(word)[0]
        except pygame.error as e:
             print(f"Pygame error calculating word width for '{word}': {e}")
             word_width = current_max_width + 1 # Assume it's too wide if calculation fails


        if current_max_width > 0 and word_width > current_max_width:
            # Add the current line if not empty before adding the long word
            if current_line_words:
                lines.append(' '.join(current_line_words))
                current_line_words = []
                if is_first_line:
                    is_first_line = False
                    current_max_width = max_width  # Subsequent lines use full width
            lines.append(word)  # Add the long word on its own line
            continue

        # Check if adding the word exceeds the max width
        test_line = ' '.join(current_line_words + [word])
        # Calculate width safely
        try:
            test_line_width = gui_core._font.size(test_line)[0]
        except pygame.error as e:
            print(f"Pygame error calculating test line width for '{test_line}': {e}")
            test_line_width = current_max_width + 1 # Assume it's too wide


        if current_max_width <= 0 or test_line_width <= current_max_width:
            current_line_words.append(word)
        else:
            # Current line + word is too wide, add the current line and start a new one
            lines.append(' '.join(current_line_words))
            current_line_words = [word]
            if is_first_line:
                is_first_line = False
                current_max_width = max_width  # Subsequent lines use full width

    # Add the last line if it's not empty
    if current_line_words:
        lines.append(' '.join(current_line_words))

    return lines

# --- Chat History Height Calculation ---
def calculate_total_history_height(history_list_of_dicts):
    """Calculates the total pixel height by summing pre-calculated heights from chat history."""
    # Accesses state.chat_history
    return sum(msg['total_height'] for msg in history_list_of_dicts)


# --- Add Message to History ---

def add_message_to_history(text, msg_type):
    """Adds a message tuple (text, type) to history and auto-scrolls to bottom.
    
    msg_type can be 'user', 'bot', 'error', 'system', or 'system_instruction'.
    """

    # Prevent adding empty messages if they somehow get here
    if not text or not text.strip():
        return

    # Determine prefix and color
    # Initialize with default values before the if/elif chain
    display_prefix = ""
    text_color = config.LIGHT_GREY # Use a neutral default color

    if msg_type == 'user':
        display_prefix = "You: "
        text_color = state.game_theme_colors["user_message_color"]
    elif msg_type == 'bot':
        display_prefix = "Bot: "
        text_color = state.game_theme_colors["original_pet_color"] # 
    elif msg_type == 'error':
        display_prefix = "Error: "
        text_color = state.game_theme_colors["error_color"]
    elif msg_type == 'system':
        display_prefix = "System: "
        text_color = state.game_theme_colors["system_messages"]
    elif msg_type == 'system_instruction':
        display_prefix = "Instruction: "
        text_color = config.ORANGE
    else:
        # Handle unknown message types - set both prefix and color
        print(f"Warning: Unknown message type '{msg_type}' received. Using default style.") # Optional warning
        display_prefix = "Info: " # Or "Unknown: ", or keep it ""
        text_color = config.DARK_GREY # A distinct color for unknown types

    # Now display_prefix is guaranteed to have been assigned a value
    wrapped_lines_list = wrap_text(text.strip(), gui_core._text_width_limit, display_prefix) # Use your existing wrap_text

    rendered_surfaces = []
    message_total_height = 0

    # Ensure _font and _line_height are initialized before this point
    if gui_core._font is None or gui_core._line_height == 0:
         print("Error: Font not initialized when adding message.")
         # Add unrendered text as fallback? Or just return? Let's return.
         # If you need basic text display even without font, handle it here.
         # For now, just add the text data without rendering surfaces if font fails
         state.chat_history.append({
             'original_text': text.strip(),
             'type': msg_type,
             'wrapped_lines': [text.strip()], # Simple fallback
             'rendered_surfaces': [], # No surfaces
             'total_height': gui_core._line_height # Rough guess for height
         })
         # Limit history size even if font failed
         while len(state.chat_history) > config.MAX_MESSAGE_HISTORY:
              state.chat_history.pop(0)
         state.scroll_y = 0
         return


    for i, line in enumerate(wrapped_lines_list):
        # Only add prefix string to the first line.
        # Subsequent lines are just the wrapped content.
        rendered_line_text = display_prefix + line if i == 0 else line

        try:
            # Use the correct color determined above
            line_surface = gui_core._font.render(rendered_line_text, True, text_color)
            rendered_surfaces.append(line_surface)
            message_total_height += gui_core._line_height
        except pygame.error as e:
            print(f"Pygame error rendering message line '{rendered_line_text}': {e}")
            # Handle error: Add a placeholder surface or skip?
            # Add a placeholder surface or just log the error and move on?
            # For now, add None and still account for height
            rendered_surfaces.append(None) # Add None or a red error surface
            message_total_height += gui_core._line_height # Still account for the line space


    # Create the message dictionary
    message_dict = {
        'original_text': text.strip(),
        'type': msg_type,
        'wrapped_lines': wrapped_lines_list, # Can keep this for debugging or other uses, or remove if not needed
        'rendered_surfaces': rendered_surfaces,
        'total_height': message_total_height
    }

    state.chat_history.append(message_dict) # Append the dictionary

    # Limit history size and cleanup surfaces
    while len(state.chat_history) > config.MAX_MESSAGE_HISTORY:
        oldest_message = state.chat_history.pop(0)
        # Relying on Python's garbage collection for surfaces is fine.
        # No explicit 'del surface' loop needed here.

    state.scroll_y = 0 # Auto-scroll to bottom
    # print(f"Added message to history ({msg_type}): {text[:50]}...") # Debugging log
