import pygame
import sys
from pygame_int import gui_config
from pygame_int.colors_config import _color_selection_options
from pygame_int import config
import json
from ai_managers import data

# Global state variables for the UI
active_element = None
text_inputs = {}
dropdowns = {}

def extract_color(config_manager, config_name):
    # the configuration file for each individual bot should be in...
    pet_config = config_manager.get_config_info(config_name)
    pet_folder=pet_config["AI"]["pets_folder"]
    file_path = f"bots/{pet_folder}/inventory/house_inventory_state_id.json"
    
    default_color = [255, 255, 255]
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            # Check for both the key and its configured status
            if data.get('is_color_configured') and 'pet_theme_color' in data:
                color = data['pet_theme_color']
                #print(f"The pet theme color is: {color}")
                return color
            else:
                return default_color

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"No color found configured, probably file does not exist yet. Using default.")
        return default_color
    
class TextInputBox:
    """A simple class for handling text input boxes with multi-line support and text wrapping."""
    def __init__(self, x, y, w, h, font, key, default_text='', allow_newlines=False): # Added allow_newlines
        self.rect = pygame.Rect(x, y, w, h)
        self.key = key
        self.color = gui_config.INPUT_BOX_BORDER_COLOR
        self.active_color = gui_config.ACTIVE_INPUT_BOX_BORDER_COLOR
        self.text = default_text
        self.font = font
        self.active = False
        
        self.max_width = w  # The maximum width the text box can be
        self.min_height = h # The minimum height of the text box
        self.line_height = self.font.get_height() + 2 # Add a little padding between lines
        self.text_padding = 5 # Padding inside the text box for text
        self.allow_newlines = allow_newlines # Store the new parameter
        
        self.rendered_lines = [] # Stores (surface, text_string) for each rendered line
        self._render_text() # Initial rendering and height adjustment
        
        text_inputs[self.key] = self

    def _render_text(self):
        """Renders the text, handling newlines and wrapping within max_width."""
        self.rendered_lines = []
        # If newlines are not allowed, replace them with spaces for rendering purposes
        text_to_render = self.text if self.allow_newlines else self.text.replace('\n', ' ')
        lines_from_input = text_to_render.split('\n')
        
        for line_text in lines_from_input:
            words = line_text.split(' ')
            current_line_words = []
            current_line_width = 0
            
            for word in words:
                # Test if adding the next word (plus a space if not the first word) exceeds max_width
                test_line = " ".join(current_line_words + [word])
                test_width, _ = self.font.size(test_line)
                
                if test_width <= self.max_width - (2 * self.text_padding):
                    current_line_words.append(word)
                else:
                    # If current_line_words is not empty, render it
                    if current_line_words:
                        rendered_surface = self.font.render(" ".join(current_line_words), True, gui_config.INPUT_TEXT_COLOR)
                        self.rendered_lines.append(rendered_surface)
                    # Start a new line with the current word
                    current_line_words = [word]
            
            # Render any remaining words in current_line_words
            if current_line_words:
                rendered_surface = self.font.render(" ".join(current_line_words), True, gui_config.INPUT_TEXT_COLOR)
                self.rendered_lines.append(rendered_surface)
            elif not words and line_text == '': # Handle empty lines (e.g., just a newline character)
                empty_line_surface = self.font.render("", True, gui_config.INPUT_TEXT_COLOR)
                self.rendered_lines.append(empty_line_surface)
        
        # Calculate new height based on rendered lines
        new_height = max(self.min_height, len(self.rendered_lines) * self.line_height + (2 * self.text_padding))
        self.rect.h = new_height
        self.rect.w = self.max_width # Ensure width remains fixed

    def handle_event(self, event, adjusted_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            global active_element
            if self.rect.collidepoint(adjusted_pos):
                self.active = True
                active_element = self
            else:
                self.active = False
                if active_element == self:
                    active_element = None
            self.color = self.active_color if self.active else gui_config.INPUT_BOX_BORDER_COLOR
            
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN and self.allow_newlines: # Only add newline if allowed
                self.text += '\n'
            elif event.unicode and event.unicode.isprintable(): # Allow most printable characters
                self.text += event.unicode
            
            self._render_text() # Re-render text after modification

    def draw(self, target_surface, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        pygame.draw.rect(target_surface, gui_config.INPUT_BOX_BACKGROUND_COLOR, draw_rect)
        pygame.draw.rect(target_surface, self.color, draw_rect, 2)
        
        y_offset_for_text = draw_rect.y + self.text_padding
        for line_surface in self.rendered_lines:
            target_surface.blit(line_surface, (draw_rect.x + self.text_padding, y_offset_for_text))
            y_offset_for_text += self.line_height

class DropdownMenu:
    """A class for handling dropdown menus."""
    def __init__(self, x, y, w, h, font, key, options, default_text='Select...'):
        self.rect = pygame.Rect(x, y, w, h)
        self.key = key
        self.font = font
        self.options = options
        self.selected_option = default_text
        self.is_open = False
        self.options_rects = []
        dropdowns[self.key] = self
        
    # --- MODIFIED: Event handler now accepts an adjusted mouse position ---
    def handle_event(self, event, adjusted_pos):
        global active_element
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(adjusted_pos):
                self.is_open = not self.is_open
                active_element = self if self.is_open else None
            elif self.is_open:
                for i, option_rect in enumerate(self.options_rects):
                    if option_rect.collidepoint(adjusted_pos):
                        self.selected_option = self.options[i]
                        self.is_open = False
                        active_element = None
                        return self.selected_option
                # If clicked outside the dropdown list, close it
                self.is_open = False
                active_element = None
        return None
    
    def draw(self, target_surface, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        pygame.draw.rect(target_surface, gui_config.BUTTON_COLOR, draw_rect)
        pygame.draw.rect(target_surface, gui_config.BUTTON_TEXT_COLOR, draw_rect, 2)
        text_surface = self.font.render(self.selected_option, True, gui_config.BUTTON_TEXT_COLOR)
        target_surface.blit(text_surface, (draw_rect.x + 5, draw_rect.y + 5))
        
        if self.is_open:
            option_y = self.rect.bottom
            self.options_rects = []
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.rect.x, option_y, self.rect.width, self.rect.height)
                self.options_rects.append(option_rect)
                
                draw_option_rect = option_rect.move(0, -offset_y)
                pygame.draw.rect(target_surface, gui_config.BUTTON_HOVER_COLOR, draw_option_rect)
                pygame.draw.rect(target_surface, gui_config.BUTTON_TEXT_COLOR, draw_option_rect, 1)
                option_surface = self.font.render(option, True, gui_config.BUTTON_TEXT_COLOR)
                target_surface.blit(option_surface, (draw_option_rect.x + 5, draw_option_rect.y + 5))
                option_y += self.rect.height

class Button:
    def __init__(self, x, y, w, h, text, font, action=None, border_color=None, border_width=0, text_color=None, button_color=None, hover_color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.action = action
        self.color = button_color or gui_config.BUTTON_COLOR
        self.hover_color = hover_color or gui_config.BUTTON_HOVER_COLOR
        self.text_color = text_color or gui_config.BUTTON_TEXT_COLOR
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        self.is_hovered = False
        self.border_color = border_color
        self.border_width = border_width

    # --- MODIFIED: Event handler now accepts a single adjusted mouse position ---
    def handle_event(self, event, adjusted_pos):
        # The collision check is now simple and correct.
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(adjusted_pos):
            if self.action:
                return self.action()
        return None

    def draw(self, target_surface, mouse_pos, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        self.is_hovered = draw_rect.collidepoint(mouse_pos)
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(target_surface, current_color, draw_rect, border_radius=15)
        
        if self.border_color and self.border_width > 0:
            pygame.draw.rect(target_surface, self.border_color, draw_rect, self.border_width, border_radius=15)
        
        text_rect_final = self.text_surface.get_rect(center=draw_rect.center)
        target_surface.blit(self.text_surface, text_rect_final)

class Checkbox:
    def __init__(self, x, y, text, font, initial_state=False):
        self.text = text
        self.font = font
        self.text_surface = font.render(text, True, gui_config.BUTTON_TEXT_COLOR)
        self.text_rect = self.text_surface.get_rect(topleft=(x + 25, y))
        self.rect = pygame.Rect(x, y, 20, 20)
        self.checked = initial_state
        self.is_hovered = False

    # --- MODIFIED: Event handler now accepts an adjusted mouse position ---
    def handle_event(self, event, adjusted_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(adjusted_pos):
                self.checked = not self.checked
        return None

    def draw(self, target_surface, mouse_pos, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        self.is_hovered = draw_rect.collidepoint(mouse_pos)
        pygame.draw.rect(target_surface, gui_config.INPUT_BOX_BACKGROUND_COLOR, draw_rect)
        border_color = gui_config.ACTIVE_INPUT_BOX_BORDER_COLOR if self.is_hovered else gui_config.INPUT_BOX_BORDER_COLOR
        pygame.draw.rect(target_surface, border_color, draw_rect, 2)
        if self.checked:
            pygame.draw.line(target_surface, gui_config.BUTTON_TEXT_COLOR, (draw_rect.left + 5, draw_rect.top + 5), (draw_rect.right - 5, draw_rect.bottom - 5), 2)
            pygame.draw.line(target_surface, gui_config.BUTTON_TEXT_COLOR, (draw_rect.left + 5, draw_rect.bottom - 5), (draw_rect.right - 5, draw_rect.top + 5), 2)
        
        text_rect_offset = self.text_rect.move(0, -offset_y)
        target_surface.blit(self.text_surface, text_rect_offset)
        return self.checked

class Popup:
    """A class to handle confirmation popups."""
    def __init__(self, screen, font, message):
        self.screen = screen
        self.font = font
        self.message = message
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        self.popup_width = 450
        self.popup_height = 150
        self.popup_rect = pygame.Rect(
            (self.screen_width - self.popup_width) // 2,
            (self.screen_height - self.popup_height) // 2,
            self.popup_width,
            self.popup_height
        )

        self.accept_button = Button(
            self.popup_rect.x + 50, self.popup_rect.bottom - 60, 120, 40, "Accept", font, lambda: True
        )
        self.back_button = Button(
            self.popup_rect.right - 170, self.popup_rect.bottom - 60, 120, 40, "Go Back", font, lambda: False
        )

    def run(self):
        """Displays the popup and waits for user input. Returns True for accept, False for go back."""
        # Create a semi-transparent surface to dim the background
        dim_surface = pygame.Surface(self.screen.get_size())
        dim_surface.set_alpha(180)
        dim_surface.fill(config.BLACK)

        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Pass the original mouse_pos, as these buttons are not in a scrolled view
                    if self.accept_button.handle_event(event, mouse_pos):
                        return True
                    if self.back_button.handle_event(event, mouse_pos):
                        return False

            self.screen.blit(dim_surface, (0, 0))
            
            # Draw popup box
            pygame.draw.rect(self.screen, gui_config.INPUT_BOX_BACKGROUND_COLOR, self.popup_rect, border_radius=15)
            pygame.draw.rect(self.screen, config.WHITE, self.popup_rect, 2, border_radius=15)

            # Draw message
            lines = self.message.split('\n')
            y_offset = self.popup_rect.top + 20
            for line in lines:
                text_surface = self.font.render(line, True, config.WHITE)
                text_rect = text_surface.get_rect(centerx=self.popup_rect.centerx, top=y_offset)
                self.screen.blit(text_surface, text_rect)
                y_offset += self.font.get_height()

            # Draw buttons (offset is 0 as they are drawn directly on the screen)
            self.accept_button.draw(self.screen, mouse_pos, 0)
            self.back_button.draw(self.screen, mouse_pos, 0)

            pygame.display.flip()

def run_config_main_menu_ui(screen, font, config_manager):
    print("Entering Main Config Menu...")
    clock = pygame.time.Clock()
    running = True

    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    title_text = "Configuration Menu"
    title_surface = font.render(title_text, True, config.WHITE)
    title_rect = title_surface.get_rect(centerx=screen_width // 2, top=20)
    
    new_button_x = screen_width - gui_config.HORIZONTAL_PADDING - gui_config.ENTER_BUTTON_WIDTH
    new_button_y = title_rect.bottom + 15
    make_new_button = Button(new_button_x, new_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT, "Make New", font, lambda: "create_new")

    viewport_y = make_new_button.rect.bottom + 20
    viewport_height = screen_height - viewport_y - 20
    viewport_rect = pygame.Rect(
        gui_config.HORIZONTAL_PADDING, 
        viewport_y, 
        screen_width - 2 * gui_config.HORIZONTAL_PADDING, 
        viewport_height
    )
    
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height))

    def _build_scrollable_config_list(config_manager, font, content_width):
        buttons = []
        delete_buttons = []
        available_configs = config_manager.get_available_configs()
        if not available_configs:
            return [], [], 0

        num_columns = 2
        button_size = 150
        row_spacing = 20
        column_spacing = 20
        start_y = 10

        total_grid_width = (num_columns * button_size) + ((num_columns - 1) * column_spacing)
        start_x = (content_width - total_grid_width) / 2
        if start_x < 0: start_x = 0

        for i, config_name in enumerate(available_configs):
            row = i // num_columns
            col = i % num_columns
            
            btn_x = start_x + col * (button_size + column_spacing)
            btn_y = start_y + row * (button_size + row_spacing)

            # --- Lambda creators to capture the correct config_name ---
            def create_load_action(name):
                return lambda: (config_manager.load_config_from_archive(name), "loaded")
            def create_delete_action(name):
                return lambda: ("delete", name)

            # Create main button
            load_action = create_load_action(config_name)
            border_color = extract_color(config_manager, config_name)
            button = Button(btn_x, btn_y, button_size, button_size, config_name, font, load_action, border_color=border_color, border_width=4)
            buttons.append(button)
            
            # Create delete button
            delete_btn_size = 25
            delete_btn_x = btn_x + button_size - delete_btn_size
            delete_btn_y = btn_y
            delete_action = create_delete_action(config_name)
            delete_button = Button(delete_btn_x, delete_btn_y, delete_btn_size, delete_btn_size, "X", font, delete_action, text_color=config.WHITE, button_color=(200, 0, 0), hover_color=(255, 50, 50))
            delete_buttons.append(delete_button)

        content_height = buttons[-1].rect.bottom + row_spacing if buttons else start_y
        
        return buttons, delete_buttons, content_height

    scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
    
    scroll_offset_y = 0
    scroll_speed = 30
    
    while running:
        dt = clock.tick(30)
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Handle fixed button (no scrolling adjustment needed)
                if make_new_button.rect.collidepoint(mouse_pos):
                     result = make_new_button.handle_event(event, mouse_pos)
                     if result == "create_new":
                        run_config_creation_ui(screen, font, config_manager)
                        scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
                        scroll_offset_y = 0
                        continue
                
                # 2. Handle scrollable elements if click is inside the viewport
                elif viewport_rect.collidepoint(mouse_pos):
                    adjusted_mouse_pos = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y + scroll_offset_y)

                    # Check delete buttons first
                    for button in delete_buttons:
                        result = button.handle_event(event, adjusted_mouse_pos)
                        if isinstance(result, tuple) and result[0] == "delete":
                            config_to_delete = result[1]
                            message = f"Attempting to delete '{config_to_delete}'.\nThis action is irreversible. Confirm?"
                            popup = Popup(screen, font, message)
                            if popup.run():
                                config_manager.delete_config_from_archive(config_to_delete)
                                scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
                                scroll_offset_y = 0
                            # Break to avoid processing other clicks in the same frame
                            break 
                    else: # If the loop didn't break, check main config buttons
                        for button in scrollable_buttons:
                            result = button.handle_event(event, adjusted_mouse_pos) 
                            if isinstance(result, tuple) and result[1] == "loaded":
                                print("Exiting main menu after loading config.")
                                return True

            # Handle scrolling if the mouse is inside the viewport
            if viewport_rect.collidepoint(mouse_pos):
                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset_y -= event.y * scroll_speed
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))

        screen.fill(config.BLACK)
        screen.blit(title_surface, title_rect)
        make_new_button.draw(screen, mouse_pos, 0)
        
        scroll_surface.fill(config.BLACK)
        mouse_pos_in_viewport = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y)

        for button in scrollable_buttons:
            button.draw(scroll_surface, mouse_pos_in_viewport, scroll_offset_y)
        # Draw delete buttons on top
        for button in delete_buttons:
            button.draw(scroll_surface, mouse_pos_in_viewport, scroll_offset_y)

        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)
        screen.blit(scroll_surface, viewport_rect.topleft)

        pygame.display.flip()
        
    return None

# The rest of your code (run_config_creation_ui, helpers) is assumed to be correct
# but would need the same handle_event modifications if they also have scrollable elements.
# I will apply the same fixes to run_config_creation_ui for consistency.

def run_config_creation_ui(screen, font, config_manager):
    """
    A UI for creating a new configuration, with a dedicated scrollable viewport.
    (This function has been updated with the same event handling fixes for consistency)
    """
    print("Entering New Configuration UI...")
    clock = pygame.time.Clock()
    running = True
    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    text_inputs.clear()
    dropdowns.clear()

    # --- Fixed UI Elements ---
    create_button_x = (screen_width - gui_config.ENTER_BUTTON_WIDTH) // 2
    create_button_y = screen_height - gui_config.INPUT_AREA_BOTTOM_PADDING - gui_config.ENTER_BUTTON_HEIGHT
    create_button = Button(
        create_button_x, create_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
        "Create Config", font, lambda: "create_config"
    )
    
    back_button_x = gui_config.HORIZONTAL_PADDING
    back_button_y = screen_height - gui_config.INPUT_AREA_BOTTOM_PADDING - gui_config.ENTER_BUTTON_HEIGHT
    back_button = Button(
        back_button_x, back_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
        "Back", font, lambda: "go_back"
    )

    # --- Define the Viewport ---
    viewport_y = 10
    viewport_height = back_button.rect.top - viewport_y - 15
    viewport_rect = pygame.Rect(0, viewport_y, screen_width, viewport_height)
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height))

    # --- Build Scrollable Content ---
    elements = []
    current_y = 10 
    
    config_name_label_surface = font.render("New Config Name:", True, config.WHITE)
    config_name_label_rect = config_name_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    config_name_input = TextInputBox(config_name_label_rect.right + 10, current_y, 250, gui_config.INPUT_BOX_HEIGHT, font, 'config_name')
    elements.append((config_name_label_surface, config_name_label_rect)); elements.append(config_name_input)
    current_y += config_name_input.rect.h + gui_config.INPUT_BOX_SPACING # Use actual height of the text input 
    title_surface, title_rect = draw_section_title(font, "AI_DeepMemory", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    ai_providers = ["gemini", "openai", "groq", "ollama"]
    enable_deep_memory_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Deep Memory", font); elements.append(enable_deep_memory_checkbox); current_y += 30
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_ai_provider", "Provider:", current_y, screen_width, elements, options=ai_providers)
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_ai", "Model Name:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_embeddings_provider", "Embeddings Provider:", current_y, screen_width, elements, options=["gemini", "openai", "ollama"]) # No Groq Embeddings model
    title_surface, title_rect = draw_section_title(font, "AI", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    current_y = draw_labeled_dropdown_or_input(font, "general_ai_provider", "General AI Provider:", current_y, screen_width, elements, options=ai_providers)
    current_y = draw_labeled_dropdown_or_input(font, "memory_ai_provider", "Memory AI Provider:", current_y, screen_width, elements, options=ai_providers)
    current_y = draw_labeled_dropdown_or_input(font, "cook_provider", "Cook Provider:", current_y, screen_width, elements, options=ai_providers)
    current_y = draw_labeled_dropdown_or_input(font, "pets_folder", "Pet's Folder:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "general_model", "General Model:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "memory_model", "Memory Model:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "cook_model", "Cook Model:", current_y, screen_width, elements, is_dropdown=False)
    title_surface, title_rect = draw_section_title(font, "Tools", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    enable_youtube_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable YouTube", font); elements.append(enable_youtube_checkbox); current_y += 30
    enable_discogs_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Discogs", font); elements.append(enable_discogs_checkbox); current_y += 30
    enable_musicbrainz_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable MusicBrainz", font); elements.append(enable_musicbrainz_checkbox); current_y += 30
    enable_bluesky_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Bluesky", font); elements.append(enable_bluesky_checkbox); current_y += 30
    title_surface, title_rect = draw_section_title(font, "game_settings", current_y, screen_width); elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    game_states = ["base_state", "dev_room"]; current_y = draw_labeled_dropdown_or_input(font, "initial_state", "Initial State:", current_y, screen_width, elements, options=game_states)
    tts_providers = ["", "macos_say", "espeak_ng"]; current_y = draw_labeled_dropdown_or_input(font, "tts_provider", "TTS Provider:", current_y, screen_width, elements, options=tts_providers)
    current_y = draw_labeled_dropdown_or_input(font, "selected_voice", "Selected Voice:", current_y, screen_width, elements, is_dropdown=False)
    title_surface, title_rect = draw_section_title(font, "System Prompt", current_y, screen_width); elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    system_prompt_label_surface = font.render("Additional Prompt:", True, config.WHITE); system_prompt_label_rect = system_prompt_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    system_prompt_input = TextInputBox(gui_config.HORIZONTAL_PADDING, system_prompt_label_rect.bottom + 5, screen_width - 2*gui_config.HORIZONTAL_PADDING, gui_config.INPUT_BOX_HEIGHT * 2, font, 'sys_prompt', allow_newlines=True)
    elements.append((system_prompt_label_surface, system_prompt_label_rect)); elements.append(system_prompt_input); current_y += system_prompt_input.rect.h + gui_config.INPUT_BOX_SPACING # Use actual height
    total_content_height = current_y

    scroll_offset_y = 0
    scroll_speed = 30

    while running:
        dt = clock.tick(30)
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --- Event Handling ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Handle fixed buttons
                if create_button.rect.collidepoint(mouse_pos):
                    if create_button.handle_event(event, mouse_pos) == "create_config":
                        # (Config saving logic is unchanged)
                        if not text_inputs['config_name'].text:
                            print("Error: Configuration name cannot be empty.")
                        else:
                            config_name = text_inputs['config_name'].text
                            
                            config_manager.set_config("AI_DeepMemory", "deep_memory_flag", enable_deep_memory_checkbox.checked)
                            config_manager.set_config("AI_DeepMemory", "deep_memory_ai_provider", dropdowns['deep_memory_ai_provider'].selected_option)
                            config_manager.set_config("AI_DeepMemory", "deep_memory_ai", text_inputs['deep_memory_ai'].text)
                            config_manager.set_config("AI_DeepMemory", "deep_memory_embeddings_provider", dropdowns['deep_memory_embeddings_provider'].selected_option)
                            
                            config_manager.set_config("AI", "general_ai_provider", dropdowns['general_ai_provider'].selected_option)
                            config_manager.set_config("AI", "memory_ai_provider", dropdowns['memory_ai_provider'].selected_option)
                            config_manager.set_config("AI", "cook_provider", dropdowns['cook_provider'].selected_option)
                            
                            config_manager.set_config("AI", "pets_folder", text_inputs['pets_folder'].text)
                            config_manager.set_config("AI", "general_model", text_inputs['general_model'].text)
                            config_manager.set_config("AI", "memory_model", text_inputs['memory_model'].text)
                            config_manager.set_config("AI", "cook_model", text_inputs['cook_model'].text)
                            
                            config_manager.set_config("Tools", "enable_youtube", enable_youtube_checkbox.checked)
                            config_manager.set_config("Tools", "enable_discogs", enable_discogs_checkbox.checked)
                            config_manager.set_config("Tools", "enable_musicbrainz", enable_musicbrainz_checkbox.checked)
                            config_manager.set_config("Tools", "enable_bluesky", enable_bluesky_checkbox.checked)
                            
                            config_manager.set_config("game_settings", "initial_state", dropdowns['initial_state'].selected_option)
                            config_manager.set_config("game_settings", "tts_provider", dropdowns['tts_provider'].selected_option)
                            config_manager.set_config("game_settings", "selected_voice", text_inputs['selected_voice'].text)
                            
                            base_prompt = data.sys_prompt
                            user_prompt = text_inputs['sys_prompt'].text
                            final_prompt = base_prompt + " " + user_prompt if user_prompt else base_prompt
                            config_manager.set_config("AI", "sys_prompt", final_prompt)
                            
                            config_manager.save_config_to_archive(config_name)
                            running = False
                
                elif back_button.rect.collidepoint(mouse_pos):
                    if back_button.handle_event(event, mouse_pos) == "go_back":
                        running = False
            
            # --- MODIFIED: Handle scrollable element events ---
            # Pass events to the active element or all scrollable elements
            adjusted_mouse_pos = (
                mouse_pos[0] - viewport_rect.x,
                mouse_pos[1] - viewport_rect.y + scroll_offset_y
            )
            if active_element:
                active_element.handle_event(event, adjusted_mouse_pos)
            else:
                # Handle non-click events (like KEYDOWN) for all elements
                if event.type != pygame.MOUSEBUTTONDOWN:
                    for element in elements:
                        if hasattr(element, 'handle_event'):
                            element.handle_event(event, adjusted_mouse_pos)
                # Handle click events
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for element in elements:
                        if hasattr(element, 'handle_event'):
                            element.handle_event(event, adjusted_mouse_pos)


            if viewport_rect.collidepoint(mouse_pos):
                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset_y -= event.y * scroll_speed
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))
        
        # --- Drawing ---
        screen.fill(config.BLACK)
        scroll_surface.fill(config.BLACK)
        
        mouse_pos_in_viewport = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y)
        
        active_dropdown = None
        for element in elements:
            if isinstance(element, tuple):
                text_surface, text_rect = element
                draw_rect = text_rect.move(0, -scroll_offset_y)
                scroll_surface.blit(text_surface, draw_rect)
            elif isinstance(element, TextInputBox):
                 element.draw(scroll_surface, scroll_offset_y)
            elif isinstance(element, Checkbox):
                 element.draw(scroll_surface, mouse_pos_in_viewport, scroll_offset_y)
            elif isinstance(element, DropdownMenu):
                if element.is_open:
                    active_dropdown = element
                else:
                    element.draw(scroll_surface, scroll_offset_y)
        
        if active_dropdown:
            active_dropdown.draw(scroll_surface, scroll_offset_y)

        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)
        screen.blit(scroll_surface, viewport_rect.topleft)

        create_button.draw(screen, mouse_pos, 0)
        back_button.draw(screen, mouse_pos, 0)

        pygame.display.flip()
        
    return None

def draw_section_title(font, title, y, screen_width):
    """Helper function to draw a section title and return the surface and rect."""
    text_surface = font.render(f"[{title}]", True, gui_config.SECTION_TITLE_COLOR)
    text_rect = text_surface.get_rect(centerx=screen_width // 2, top=y + gui_config.SECTION_TITLE_SPACING_TOP)
    return text_surface, text_rect

def draw_labeled_dropdown_or_input(font, key, label_text, y, screen_width, elements, is_dropdown=True, options=None):
    """Helper function to draw a label and a dropdown or text input box."""
    label_surface = font.render(label_text, True, config.WHITE)
    label_rect = label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=y)
    elements.append((label_surface, label_rect))

    if is_dropdown:
        element_ui = DropdownMenu(
            label_rect.right + gui_config.INPUT_LABEL_SPACING, y, 250, gui_config.INPUT_BOX_HEIGHT, font, key, options
        )
    else:
        element_ui = TextInputBox(
            label_rect.right + gui_config.INPUT_LABEL_SPACING, y, 250, gui_config.INPUT_BOX_HEIGHT, font, key
        )
    elements.append(element_ui)
    
    # Return the bottom of the element, which is its Y position plus its height, plus spacing
    # This ensures subsequent elements are positioned correctly below
    return element_ui.rect.bottom + gui_config.INPUT_BOX_SPACING
