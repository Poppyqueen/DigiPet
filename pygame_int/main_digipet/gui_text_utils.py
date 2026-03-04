# gui_text_utils.py
#
# What changed from the original
# --------------------------------
# All gui_core._font / _line_height / _text_width_limit accesses replaced
# with public getters:
#   gui_core._font              → gui_core.get_font()
#   gui_core._line_height       → gui_core.get_line_height()
#   gui_core._text_width_limit  → gui_core.get_text_width_limit()
#
# No logic changes.

import pygame
from pygame_int import config
from pygame_int import state
from pygame_int.main_digipet import gui_core


# ---------------------------------------------------------------------------
# Text wrapping
# ---------------------------------------------------------------------------

def wrap_text(text, max_width, prefix=""):
    """
    Wrap text to fit within max_width pixels using the shared font.
    The prefix (e.g. "You: ") is measured separately so the first line
    gets a tighter width budget; subsequent lines use the full max_width.
    """
    font = gui_core.get_font()
    if font is None:
        return [str(text)]

    if not text:
        return [""]

    words = text.split(' ')
    if not words:
        return [""]

    # First line has less room because the prefix is drawn before it.
    first_line_max_width = max_width
    if prefix:
        try:
            prefix_width = font.size(prefix)[0]
            first_line_max_width = max(1, max_width - prefix_width)
        except pygame.error as e:
            print(f"[gui_text_utils] Pygame error measuring prefix '{prefix}': {e}")

    lines             = []
    current_words     = []
    is_first_line     = True
    current_max_width = first_line_max_width

    for word in words:
        try:
            word_width = font.size(word)[0]
        except pygame.error as e:
            print(f"[gui_text_utils] Pygame error measuring word '{word}': {e}")
            word_width = current_max_width + 1  # treat as too wide

        # Word alone is wider than the available space — force it onto its own line.
        if current_max_width > 0 and word_width > current_max_width:
            if current_words:
                lines.append(' '.join(current_words))
                current_words = []
                if is_first_line:
                    is_first_line     = False
                    current_max_width = max_width
            lines.append(word)
            continue

        test_line = ' '.join(current_words + [word])
        try:
            test_width = font.size(test_line)[0]
        except pygame.error as e:
            print(f"[gui_text_utils] Pygame error measuring line '{test_line}': {e}")
            test_width = current_max_width + 1

        if current_max_width <= 0 or test_width <= current_max_width:
            current_words.append(word)
        else:
            lines.append(' '.join(current_words))
            current_words = [word]
            if is_first_line:
                is_first_line     = False
                current_max_width = max_width

    if current_words:
        lines.append(' '.join(current_words))

    return lines


# ---------------------------------------------------------------------------
# Chat history height
# ---------------------------------------------------------------------------

def calculate_total_history_height(history_list_of_dicts):
    """Return total pixel height of all messages by summing pre-calculated heights."""
    return sum(msg['total_height'] for msg in history_list_of_dicts)


# ---------------------------------------------------------------------------
# Add message to chat history
# ---------------------------------------------------------------------------

def add_message_to_history(text, msg_type):
    """
    Pre-render a message and append it to state.chat_history.

    msg_type can be: 'user', 'bot', 'error', 'system', 'system_instruction'.
    Auto-scrolls to the bottom after appending.
    """
    if not text or not text.strip():
        return

    # --- Determine prefix and colour ---
    if msg_type == 'user':
        display_prefix = "You: "
        text_color = state.game_theme_colors["user_message_color"]
    elif msg_type == 'bot':
        display_prefix = "Bot: "
        text_color = state.game_theme_colors["original_pet_color"]
    elif msg_type == 'error':
        display_prefix = "Error: "
        text_color = state.game_theme_colors["error_color"]
    elif msg_type == 'system':
        display_prefix = "System: "
        text_color = state.game_theme_colors["system_messages"]
    elif msg_type == 'system_instruction':
        display_prefix = "State: "
        text_color = config.GREY
    else:
        print(f"[gui_text_utils] Unknown message type '{msg_type}'. Using default style.")
        display_prefix = "Info: "
        text_color = config.DARK_GREY

    font        = gui_core.get_font()
    line_height = gui_core.get_line_height()

    # --- Fallback if font not ready ---
    if font is None or line_height == 0:
        print("[gui_text_utils] Font not initialised — storing message without rendering.")
        state.chat_history.append({
            'original_text':    text.strip(),
            'type':             msg_type,
            'wrapped_lines':    [text.strip()],
            'rendered_surfaces': [],
            'total_height':     line_height,
        })
        while len(state.chat_history) > config.MAX_MESSAGE_HISTORY:
            state.chat_history.pop(0)
        state.scroll_y = 0
        return

    # --- Wrap and render ---
    wrapped_lines      = wrap_text(text.strip(), gui_core.get_text_width_limit(), display_prefix)
    rendered_surfaces  = []
    message_total_height = 0

    for i, line in enumerate(wrapped_lines):
        rendered_text = display_prefix + line if i == 0 else line
        try:
            surface = font.render(rendered_text, True, text_color)
            rendered_surfaces.append(surface)
        except pygame.error as e:
            print(f"[gui_text_utils] Pygame error rendering '{rendered_text}': {e}")
            rendered_surfaces.append(None)
        message_total_height += line_height

    message_total_height += config.MESSAGE_PADDING

    state.chat_history.append({
        'original_text':     text.strip(),
        'type':              msg_type,
        'wrapped_lines':     wrapped_lines,
        'rendered_surfaces': rendered_surfaces,
        'total_height':      message_total_height,
    })

    while len(state.chat_history) > config.MAX_MESSAGE_HISTORY:
        state.chat_history.pop(0)

    state.scroll_y = 0  # Auto-scroll to bottom