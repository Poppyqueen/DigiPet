import pygame
import os
import sys
from pygame_int import gui_config
from pygame_int import config
from pygame_int.main_menu_int.main_menu_modules.button import Button
from pygame_int import state


def pop_colors():

    font_color=state.game_theme_colors["user_message_color"]
    button_color=state.game_theme_colors["contrast_color"]
    button_hover_color=state.game_theme_colors["adjusted_brightness_color"]
    button_pressed_color=state.game_theme_colors["original_pet_color"]
    return {"font_color": font_color,
            "button_color": button_color,
            "button_hover_color": button_hover_color,
            "button_pressed_color": button_pressed_color}
# Global mixer initialization check
def init_mixer_if_needed():
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Failed to initialize mixer: {e}")

def play_preview_sound(folder_path, filename):
    """Stops current sound and plays the new selection."""
    init_mixer_if_needed()
    if pygame.mixer.get_init():
        try:
            pygame.mixer.stop() # Stop any currently playing sound
            full_path = os.path.join(folder_path, filename)
            sound = pygame.mixer.Sound(full_path)
            sound.set_volume(0.11)
            sound.play()
            print(f"Previewing sound: {filename}")
        except pygame.error as e:
            print(f"Could not play sound {filename}: {e}")

def run_sound_selection_ui(screen, font, sound_folder_path):
    """
    Runs a blocking UI loop to allow the user to select a .mp3 file from a folder.
    Returns the filename (string) or None if cancelled.
    """
    print(f"Entering Sound Selection UI. Scanning: {sound_folder_path}...")
    colors=pop_colors()
    clock = pygame.time.Clock()
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # --- Load Files ---
    try:
        sound_files = [f for f in os.listdir(sound_folder_path) if f.endswith('.mp3')]
        sound_files.sort()
    except FileNotFoundError:
        print(f"Error: Sound folder not found at {sound_folder_path}")
        return None

    # --- UI Layout Setup ---
    
    # 1. Navigation Buttons (Fixed at bottom)
    input_area_bottom_padding = gui_config.INPUT_AREA_BOTTOM_PADDING
    
    # Confirm Button (center)
    confirm_button_x = screen_width // 2 - gui_config.ENTER_BUTTON_WIDTH // 2
    confirm_button_y = screen_height - gui_config.ENTER_BUTTON_HEIGHT - input_area_bottom_padding
    confirm_button = Button(
        confirm_button_x, confirm_button_y, 
        gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
        "Confirm", font, lambda: "confirm_selection"
    )

    # 2. Scrollable Area Calculation
    # Top area for Title
    title_y = gui_config.VERTICAL_START_Y_GRID_AREA
    try:
        title_height = font.get_linesize() * 2
    except:
        title_height = 40

    viewport_top = title_y + title_height + 20
    viewport_bottom = confirm_button.rect.top - 20
    viewport_height = viewport_bottom - viewport_top
    viewport_rect = pygame.Rect(0, viewport_top, screen_width, viewport_height)

    # --- Create Sound Item Buttons (Virtual Coordinates) ---
    sound_buttons = []
    current_y = 10 # Start slightly down inside the scroll view
    button_height = 50
    button_spacing = 10
    item_width = screen_width - (gui_config.HORIZONTAL_PADDING * 2)

    for filename in sound_files:
        # We use the Button class. The Y position is relative to the top of the SCROLL SURFACE (0,0)
        btn = Button(
            gui_config.HORIZONTAL_PADDING, 
            current_y, 
            item_width, 
            button_height,
            filename.replace(".mp3", "").replace("_", " ").title(), 
            font, 
            lambda f=filename: f"select_{f}", # Return unique ID
            text_color=colors["font_color"],
            button_color=colors["button_color"],
            hover_color=colors["button_hover_color"],
            
        )
        # Store the filename directly on the button object for easy access later
        btn.payload = filename 
        sound_buttons.append(btn)
        current_y += button_height + button_spacing

    total_content_height = current_y
    scroll_surface = pygame.Surface((screen_width, max(total_content_height, viewport_height)))
    
    scroll_offset_y = 0
    scroll_speed = 30
    
    selected_sound_file = None
    running = True

    while running:
        dt = clock.tick(30)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()

            # --- Scroll Handling ---
            if event.type == pygame.MOUSEWHEEL and viewport_rect.collidepoint(mouse_pos):
                scroll_offset_y -= event.y * scroll_speed
                max_scroll = max(0, total_content_height - viewport_height)
                scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    
                    # 1. Check Fixed Buttons
                    # Note: Fixed buttons don't need coordinate adjustment
                    if selected_sound_file and confirm_button.rect.collidepoint(mouse_pos):
                         if confirm_button.handle_event(event, mouse_pos) == "confirm_selection":
                             running = False
                             # Returns the currently selected variable

                    # 2. Check Scrollable Sound Buttons
                    if viewport_rect.collidepoint(mouse_pos):
                        # Calculate mouse position relative to the scroll surface
                        adjusted_mouse_pos = (
                            mouse_pos[0] - viewport_rect.x, 
                            mouse_pos[1] - viewport_rect.y + scroll_offset_y
                        )
                        
                        for btn in sound_buttons:
                            # Check collision using the adjusted coordinates
                            if btn.rect.collidepoint(adjusted_mouse_pos):
                                selected_sound_file = btn.payload
                                play_preview_sound(sound_folder_path, selected_sound_file)
                                break

        # --- Drawing ---
        screen.fill((0, 0, 0)) # Black background

        # 1. Draw Title
        title_text = "Select an Autonomous Action Sound:"
        title_surf = font.render(title_text, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(screen_width // 2, title_y))
        screen.blit(title_surf, title_rect)

        # 2. Draw Scrollable Content
        scroll_surface.fill((0, 0, 0)) # Clear scroll surface
        
        # Adjusted mouse for hover calculation
        adjusted_mouse_pos_for_draw = (
            mouse_pos[0] - viewport_rect.x, 
            mouse_pos[1] - viewport_rect.y + scroll_offset_y
        )

        for btn in sound_buttons:
            # Highlight if selected
            is_selected = (btn.payload == selected_sound_file)
            
            
            # --- THIS IS THE SECTION TO UPDATE ---
            if is_selected:
                # Use the pressed color here so the selected item looks "active"
                btn.color = colors["button_pressed_color"] 
                # Optional: Ensure text remains visible against the pressed color
                btn.text_color = colors["font_color"] 
            # -------------------------------------
            # FIX: Added '0' as the third argument.
            # Since 'btn' is drawn onto 'scroll_surface' at its exact coordinates, offset is 0.
            btn.draw(scroll_surface, adjusted_mouse_pos_for_draw, 0)
            
            # Restore colors
            btn.color = colors["button_color"]
            btn.text_color = colors["font_color"]

        # Blit the visible portion of scroll surface to screen
        screen.blit(scroll_surface, viewport_rect.topleft, 
                    pygame.Rect(0, scroll_offset_y, viewport_rect.width, viewport_rect.height))
        
        # Draw Border around viewport
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        # 3. Draw Fixed Buttons
        # FIX: Added '0' as the third argument. Fixed buttons are on the main screen, no offset needed.
        
        if selected_sound_file:
            confirm_button.draw(screen, mouse_pos, 0)

        pygame.display.flip()

    print(f"Exiting sound selection. Selected: {selected_sound_file}")
    
    if pygame.mixer.get_init():
        pygame.mixer.stop()

    return selected_sound_file