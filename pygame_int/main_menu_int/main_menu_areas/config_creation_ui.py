# main_menu_areas/config_creation_ui.py
import pygame
import sys


from ....pygame_int import gui_config
from ....pygame_int import config


from ....ai_managers import prompt_data

from ...main_digipet import gui

from ..main_menu_modules.button import Button
from ..main_menu_modules.checkbox import Checkbox
from ..main_menu_modules.dropdown_menu import DropdownMenu
from ..main_menu_modules.text_input_box import TextInputBox

from ..main_menu_modules.main_menu_utils import (calculate_total_content_height, draw_section_title)


from ....ai_managers.ai_utils.ai_loader import AIConfiguration, UnifiedLoader


text_inputs = {}
dropdowns = {}
active_element = None




AVAILABLE_AGENTS=AIConfiguration.get_providers_by_mode("agent")

AVAILABLE_SIMPLE_AI=AIConfiguration.get_providers_by_mode("simple_ai")

AVAILABLE_EMBEDDINGS=UnifiedLoader.get_available_providers("embeddings")


def run_config_creation_ui(screen, font, config_manager, state_configs):
    """
    A UI for creating a new configuration, with a dedicated scrollable viewport.
    (This function has been updated with the same event handling fixes for consistency)
    """
    print("Entering New DigiPet Configuration UI...")

    clock = pygame.time.Clock()
    running = True
    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    text_inputs.clear()
    dropdowns.clear()

    availiable_configs=state_configs
    available_states=[]
    for i in availiable_configs:
        available_states.append(i) 

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
    viewport_y = 1
    viewport_height = back_button.rect.top - viewport_y - 15
    viewport_rect = pygame.Rect(0, viewport_y, screen_width, viewport_height)
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height))

    # --- Build Scrollable Content ---
    elements = []
    current_y = 10 
    
    config_name_label_surface = font.render("New Config Name:", True, config.WHITE)
    config_name_label_rect = config_name_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    config_name_input = TextInputBox(config_name_label_rect.right + 10, current_y, 250, gui_config.CONFIG_INPUT_BOX_HEIGHT, font, 'config_name', text_inputs=text_inputs, active_element=active_element)
    elements.append((config_name_label_surface, config_name_label_rect)); elements.append(config_name_input)
    current_y += config_name_input.rect.h + gui_config.INPUT_BOX_SPACING # Use actual height of the text input 
    title_surface, title_rect = draw_section_title(font, "AI_DeepMemory", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    enable_deep_memory_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Deep Memory", font); elements.append(enable_deep_memory_checkbox); current_y += 30
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_ai_provider", "Provider:", current_y, screen_width, elements, options=AVAILABLE_SIMPLE_AI)
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_ai", "Model Name:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "deep_memory_embeddings_provider", "Embeddings Provider:", current_y, screen_width, elements, options=AVAILABLE_EMBEDDINGS) # No Groq Embeddings model
    title_surface, title_rect = draw_section_title(font, "AI", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    current_y = draw_labeled_dropdown_or_input(font, "general_ai_provider", "General AI Provider:", current_y, screen_width, elements, options=AVAILABLE_AGENTS)
    current_y = draw_labeled_dropdown_or_input(font, "memory_ai_provider", "Memory AI Provider:", current_y, screen_width, elements, options=AVAILABLE_SIMPLE_AI)
    current_y = draw_labeled_dropdown_or_input(font, "cook_provider", "Cook Provider:", current_y, screen_width, elements, options=AVAILABLE_SIMPLE_AI)
    current_y = draw_labeled_dropdown_or_input(font, "pets_folder", "Pet's Folder:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "general_model", "General Model:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "memory_model", "Memory Model:", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "cook_model", "Cook Model:", current_y, screen_width, elements, is_dropdown=False)

    title_surface, title_rect = draw_section_title(font, "Token Limits", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    current_y = draw_labeled_dropdown_or_input(font, "max_tokens", "Max Tokens:", current_y, screen_width, elements, is_dropdown=False, default_text="44000")


    title_surface, title_rect = draw_section_title(font, "Location", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    current_y = draw_labeled_dropdown_or_input(font, "lat", "Latitude (optional):", current_y, screen_width, elements, is_dropdown=False)
    current_y = draw_labeled_dropdown_or_input(font, "long", "Longitude (optional):", current_y, screen_width, elements, is_dropdown=False)

    title_surface, title_rect = draw_section_title(font, "Tools", current_y, screen_width)
    elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    enable_youtube_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable YouTube", font); elements.append(enable_youtube_checkbox); current_y += 30
    enable_discogs_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Discogs", font); elements.append(enable_discogs_checkbox); current_y += 30
    enable_musicbrainz_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable MusicBrainz", font); elements.append(enable_musicbrainz_checkbox); current_y += 30
    enable_bluesky_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Bluesky", font); elements.append(enable_bluesky_checkbox); current_y += 30
    enable_wikipedia_checkbox = Checkbox(gui_config.HORIZONTAL_PADDING, current_y, "Enable Wikipedia", font); elements.append(enable_wikipedia_checkbox); current_y += 30

    title_surface, title_rect = draw_section_title(font, "game_settings", current_y, screen_width); elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    game_states = available_states; current_y = draw_labeled_dropdown_or_input(font, "initial_state", "Initial State:", current_y, screen_width, elements, options=game_states)
    tts_providers = ["", "macos_say", "espeak_ng"]; current_y = draw_labeled_dropdown_or_input(font, "tts_provider", "TTS Provider:", current_y, screen_width, elements, options=tts_providers)
    current_y = draw_labeled_dropdown_or_input(font, "selected_voice", "Selected Voice:", current_y, screen_width, elements, is_dropdown=False)
    title_surface, title_rect = draw_section_title(font, "System Prompt", current_y, screen_width); elements.append((title_surface, title_rect)); current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    system_prompt_label_surface = font.render("Additional Prompt:", True, config.WHITE); system_prompt_label_rect = system_prompt_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    system_prompt_input = TextInputBox(gui_config.HORIZONTAL_PADDING, system_prompt_label_rect.bottom + 5, screen_width - 2*gui_config.HORIZONTAL_PADDING, gui_config.CONFIG_INPUT_BOX_HEIGHT * 2, font, 'sys_prompt', allow_newlines=True, text_inputs=text_inputs, active_element=active_element)
    elements.append((system_prompt_label_surface, system_prompt_label_rect)); elements.append(system_prompt_input); current_y += system_prompt_input.rect.h + gui_config.INPUT_BOX_SPACING # Use actual height
    total_content_height = current_y
    scroll_offset_y = 0
    scroll_speed = 30

    
    while running:
        dt = clock.tick(30)
        current_time_ms = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        gui.gui_core.update_gui_rects(0)
        gui.gui_popups.update_popups(current_time_ms)

        total_content_height = calculate_total_content_height(elements)

        if not text_inputs['max_tokens'].text and not text_inputs['max_tokens'].active:
            print("tokens empty")
            text_inputs['max_tokens'].text="44000"
            text_inputs['max_tokens']._render_text()
    
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

                        # 1. GATHER all current data AND component references
                        # This structure holds both the value and the UI component reference
                        form_data = {
                            "config_name": {
                                "value": text_inputs['config_name'].text,
                                "component": text_inputs['config_name'],
                                "type": "text"
                            },
                            "deep_memory_flag": {
                                "value": enable_deep_memory_checkbox.checked,
                                "component": enable_deep_memory_checkbox,
                                "type": "checkbox"
                            },
                            "deep_memory_ai_provider": {
                                "value": dropdowns['deep_memory_ai_provider'].selected_option,
                                "component": dropdowns['deep_memory_ai_provider'],
                                "type": "dropdown"
                            },
                            "deep_memory_ai": {
                                "value": text_inputs['deep_memory_ai'].text,
                                "component": text_inputs['deep_memory_ai'],
                                "type": "text"
                            },
                            "deep_memory_embeddings_provider": {
                                "value": dropdowns['deep_memory_embeddings_provider'].selected_option,
                                "component": dropdowns['deep_memory_embeddings_provider'],
                                "type": "dropdown"
                            },
                            "general_ai_provider": {
                                "value": dropdowns['general_ai_provider'].selected_option,
                                "component": dropdowns['general_ai_provider'],
                                "type": "dropdown"
                            },
                            "memory_ai_provider": {
                                "value": dropdowns['memory_ai_provider'].selected_option,
                                "component": dropdowns['memory_ai_provider'],
                                "type": "dropdown"
                            },
                            "cook_provider": {
                                "value": dropdowns['cook_provider'].selected_option,
                                "component": dropdowns['cook_provider'],
                                "type": "dropdown"
                            },
                            "pets_folder": {
                                "value": text_inputs['pets_folder'].text,
                                "component": text_inputs['pets_folder'],
                                "type": "text"
                            },
                            "general_model": {
                                "value": text_inputs['general_model'].text,
                                "component": text_inputs['general_model'],
                                "type": "text"
                            },
                            "memory_model": {
                                "value": text_inputs['memory_model'].text,
                                "component": text_inputs['memory_model'],
                                "type": "text"
                            },
                            "cook_model": {
                                "value": text_inputs['cook_model'].text,
                                "component": text_inputs['cook_model'],
                                "type": "text"
                            },
                            "initial_state": {
                                "value": dropdowns['initial_state'].selected_option,
                                "component": dropdowns['initial_state'],
                                "type": "dropdown"
                            },
                            "max_tokens": {
                                "value": text_inputs['max_tokens'].text,
                                "component": text_inputs['max_tokens'],
                                "type": "text"
                            },
                            "lat": {
                                "value": text_inputs['lat'].text,
                                "component": text_inputs['lat'],
                                "type": "text"
                            },
                            "long": {
                            "value": text_inputs['long'].text,
                            "component": text_inputs['long'],
                            "type": "text"
                        },
                        }

                        print("--- Form Data Collected ---")
                        for field, data in form_data.items():
                            print(f"{field}: {data['value']}")
                        print("--------------------------")

                        # Clear any existing validation errors first
                        for field, data in form_data.items():
                            data['component'].validation_error = False

                        validation_errors = []
                        failed_fields = []  # Track which fields failed validation

                        # 2. RUN explicit and robust validation logic
                        # -- Unconditional fields --
                        unconditional_fields = [
                            "config_name", "general_ai_provider", "memory_ai_provider",
                            "cook_provider", "pets_folder", "general_model", "memory_model",
                            "cook_model", "initial_state"
                        ]

                        # Validate each unconditional field
                        for field in unconditional_fields:
                            if field in form_data:
                                value = form_data[field]["value"]
                                
                                # Check if value is None, empty string, or just whitespace
                                if not value or (isinstance(value, str) and not value.strip()):
                                    error_msg = f"{field.replace('_', ' ').title()} cannot be empty."
                                    validation_errors.append(error_msg)
                                    failed_fields.append(field)
                                    # Mark the UI component as having a validation error
                                    form_data[field]["component"].validation_error = True
                            else:
                                validation_errors.append(f"Required field '{field}' is missing from form data.")

                        # -- Conditional fields --
                        # Only validate deep memory fields if the checkbox is checked
                        if form_data["deep_memory_flag"]["value"]:
                            # Deep Memory AI Provider validation
                            if not form_data["deep_memory_ai_provider"]["value"]:
                                error_msg = "Deep Memory AI Provider must be selected."
                                validation_errors.append(error_msg)
                                failed_fields.append("deep_memory_ai_provider")
                                form_data["deep_memory_ai_provider"]["component"].validation_error = True
                            
                            # Deep Memory AI Model validation
                            if not form_data["deep_memory_ai"]["value"] or not form_data["deep_memory_ai"]["value"].strip():
                                error_msg = "Deep Memory AI Model Name cannot be empty."
                                validation_errors.append(error_msg)
                                failed_fields.append("deep_memory_ai")
                                form_data["deep_memory_ai"]["component"].validation_error = True

                            # Deep Memory Embeddings Provider validation
                            if not form_data["deep_memory_embeddings_provider"]["value"]:
                                error_msg = "Deep Memory Embeddings Provider must be selected."
                                validation_errors.append(error_msg)
                                failed_fields.append("deep_memory_embeddings_provider")
                                form_data["deep_memory_embeddings_provider"]["component"].validation_error = True


                        # validate tokens as an int if it has any value, else, set a default, add a validation error
                        if form_data["max_tokens"]["value"]:
                            try:
                                form_data["max_tokens"]["value"] = int(form_data["max_tokens"]["value"])
                            except ValueError:
                                error_msg = "Max Tokens must be an integer."
                                validation_errors.append(error_msg)
                                failed_fields.append("max_tokens")
                                form_data["max_tokens"]["component"].validation_error = True
                        else:
                            form_data["max_tokens"]["value"] = 44000  # Set default value

                        if form_data["lat"]["value"] or form_data["long"]["value"]: # validate as a float
                            try:
                                form_data["lat"]["value"] = float(form_data["lat"]["value"])
                            except ValueError:
                                error_msg = "Latitude must be a float."
                                validation_errors.append(error_msg)
                                failed_fields.append("lat")
                                form_data["lat"]["component"].validation_error = True

                            try:
                                form_data["long"]["value"] = float(form_data["long"]["value"])
                            except ValueError:
                                error_msg = "Longitude must be a float."
                                validation_errors.append(error_msg)
                                failed_fields.append("long")
                                form_data["long"]["component"].validation_error = True

                        else: # set default to None if not provided
                            form_data["lat"]["value"] = None
                            form_data["long"]["value"] = None

                        # 3. PROCESS the result of the validation
                        if validation_errors:
                            # If there are errors, print them and show popup
                            print("--- Validation Failed ---")
                            print(f"Failed fields: {failed_fields}")
                            for error in validation_errors:
                                print(f"Error: {error}")

                                # print each message individualy 
                                gui.gui_popups.show_popup_message(error, (255, 0, 0), True)
                            
                            print(f"Marked {len(failed_fields)} UI components with validation errors")

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
                            config_manager.set_config("Tools", "enable_wikipedia", enable_wikipedia_checkbox.checked)
                            
                            config_manager.set_config("game_settings", "initial_state", dropdowns['initial_state'].selected_option)
                            config_manager.set_config("game_settings", "tts_provider", dropdowns['tts_provider'].selected_option)
                            config_manager.set_config("game_settings", "selected_voice", text_inputs['selected_voice'].text)

                            config_manager.set_config("AI", "max_memory_tokens", form_data["max_tokens"]["value"])

                            base_prompt = prompt_data.sys_prompt
                            user_prompt = text_inputs['sys_prompt'].text
                            final_prompt = base_prompt + " " + user_prompt if user_prompt else base_prompt
                            config_manager.set_config("AI", "sys_prompt", final_prompt)

                            config_manager.set_config("location", "latitude", text_inputs['lat'].text)
                            config_manager.set_config("location", "longitude", text_inputs['long'].text)

                            config_manager.save_config_to_archive(config_name)
                            gui.gui_popups.clear_all_popups()
                            running = False
                
                elif back_button.rect.collidepoint(mouse_pos):
                    if back_button.handle_event(event, mouse_pos) == "go_back":
                        gui.gui_popups.clear_all_popups()
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
                # Handle click events only if the click is within the viewport
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if viewport_rect.collidepoint(mouse_pos):
                        for element in elements:
                            if hasattr(element, 'handle_event'):
                                element.handle_event(event, adjusted_mouse_pos)


            if viewport_rect.collidepoint(mouse_pos):
                if event.type == pygame.MOUSEWHEEL:
                    if is_any_dropdown_open(mouse_pos, scroll_offset_y, viewport_rect):
                        # Let the dropdown handle its own scrolling - don't scroll the main viewport
                        pass  # The dropdown will handle the scroll in its own handle_event method
                    else:
                        scroll_offset_y -= event.y * scroll_speed
                        max_scroll = max(0, total_content_height - viewport_rect.height)
                        scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))
    


        # --- Drawing ---
        screen.fill(config.BLACK)
        
        # 1. Draw the scrollable content onto its surface
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

        


        # 2. Blit the scroll surface to the screen
        screen.blit(scroll_surface, viewport_rect.topleft)
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        # 3. Draw the static buttons and other non-scrolling UI on top
        create_button.draw(screen, mouse_pos, 0)
        back_button.draw(screen, mouse_pos, 0)


        gui.gui_popups.draw_popups(screen)
        pygame.display.flip()
    return None


def draw_labeled_dropdown_or_input(font, key, label_text, y, screen_width, elements, is_dropdown=True, options=None, default_text=""):
    """Helper function to draw a label and a dropdown or text input box."""
    label_surface = font.render(label_text, True, config.WHITE)
    label_rect = label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=y)
    elements.append((label_surface, label_rect))

    x = label_rect.right + gui_config.INPUT_LABEL_SPACING

    box_width= screen_width - x - gui_config.HORIZONTAL_PADDING

    if is_dropdown:
        element_ui = DropdownMenu(
            x, y, box_width, gui_config.CONFIG_INPUT_BOX_HEIGHT, font, key, options, dropdowns=dropdowns
        )
    else:
        element_ui = TextInputBox(
            x, y, box_width, gui_config.CONFIG_INPUT_BOX_HEIGHT, font, key, text_inputs=text_inputs, active_element=active_element, default_text=default_text
        )
    elements.append(element_ui)
    
    # Return the bottom of the element, which is its Y position plus its height, plus spacing
    # This ensures subsequent elements are positioned correctly below
    return element_ui.rect.bottom + gui_config.INPUT_BOX_SPACING


def is_any_dropdown_open(mouse_pos, scroll_offset_y, viewport_rect):
    """
    Check if any dropdown menu is currently open and the mouse is hovering over it,
    accounting for the scroll offset.
    """
    # First, quickly check if the mouse is even inside the viewport.
    # If not, it can't be hovering over a dropdown within the scrollable area.

    flag = False
    if not viewport_rect.collidepoint(mouse_pos):
        return flag

    # Convert the screen mouse coordinates to coordinates relative to the scrollable surface
    adjusted_mouse_x = mouse_pos[0] - viewport_rect.x
    adjusted_mouse_y = mouse_pos[1] - viewport_rect.y + scroll_offset_y
    adjusted_pos = (adjusted_mouse_x, adjusted_mouse_y)

    for dropdown in dropdowns.values():
        if dropdown.is_open:
            # Check collision with the main dropdown button
            if dropdown.rect.collidepoint(adjusted_pos):
                flag = True
            # Check collision with the expanded options list (if it exists)
            if dropdown.dropdown_rect and dropdown.dropdown_rect.collidepoint(adjusted_pos):
                flag = True

    return flag