from pygame_int import gui_config
from pygame_int import config
from pygame_int import state
import pygame

from pygame_int.main_digipet import gui

from pygame_int.main_menu_int.main_menu_modules.button import Button
from pygame_int.main_menu_int.main_menu_modules.checkbox import Checkbox
from pygame_int.main_menu_int.main_menu_modules.dropdown_menu import DropdownMenu
from pygame_int.main_menu_int.main_menu_modules.text_input_box import TextInputBox

from pygame_int.main_menu_int.main_menu_modules.main_menu_utils import (calculate_total_content_height, draw_section_title)

from pygame_int.main_menu_int.utils.crafter_signal import CrafterSignal

import sys
import threading
import queue
from enum import Enum

# imports for our threaded process
from data_constructors.base_state_construct import BaseCrafter


from ai_managers.ai_utils.ai_loader import AIConfiguration

from pygame_int.main_menu_int.main_menu_modules.pulsing_text import PulsingText




AVAILABLE_SIMPLE_AI=AIConfiguration.get_providers_by_mode("simple_ai")


dropdowns = {}

# =============================================================================
# NEW: Redesigned Processing States & Signals
# =============================================================================

class ProcessState(Enum):
    """
    Represents the major *phase* the UI is currently in.
    Determines the overall display style (e.g., show progress bar).
    """
    IDLE = "idle"
    FOUNDATION = "foundation"       # Generating the house structure
    POPULATION = "population"       # Generating items for rooms (shows progress)
    FINALIZATION = "finalization"   # Filtering, saving, and wrapping up
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLING = "cancelling"       # Waiting for thread to acknowledge shutdown


text_inputs = {}
active_element = None

# Thread management globals
shutdown_event = threading.Event()
process_state = ProcessState.IDLE
signal_queue = queue.Queue()
result_queue = queue.Queue()
processing_thread = None
base_state_crafter_instance = None # To hold the crafter for shutdown requests


def start_threaded_processing(crafter, user_prompt):
    global processing_thread, process_state
    if process_state != ProcessState.IDLE:
        return False

    while not signal_queue.empty(): signal_queue.get()
    while not result_queue.empty(): result_queue.get()

    processing_thread = threading.Thread(
        target=lambda: result_queue.put(crafter.generate_base_state(user_prompt)),
        daemon=True
    )
    processing_thread.start()
    # The first signal from the thread will set the correct initial state
    return True


def reset_processing_state():
    global process_state, processing_thread, base_state_crafter_instance
    process_state = ProcessState.IDLE
    processing_thread = None
    base_state_crafter_instance = None

# =============================================================================
# Example 3: Updated UI signal handling
# =============================================================================
def run_config_creation_twilight_zone(screen, font, init_states):
    global process_state, processing_thread, active_element, base_state_crafter_instance
    print("Entering Environment Creation UI...")

    state.panel_width = 0
    state.panel_visible = False
    clock = pygame.time.Clock()
    running = True
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    initial_states_manager = init_states
    reset_processing_state()
    text_inputs.clear()
    
    # --- UI State variables for processing display ---
    main_status_message = ""
    sub_status_message = ""
    current_progress = 0
    completion_data = None # Holds the final results
    completion_scroll_offset = 0 # FIXED: Initialize scroll offset for completion screen

    # --- Fixed UI Elements ---
    create_environment_button_x = (screen_width - gui_config.ENTER_BUTTON_WIDTH) // 2
    create_environment_button_y = screen_height - gui_config.INPUT_AREA_BOTTOM_PADDING - gui_config.ENTER_BUTTON_HEIGHT
    create_environment_button = Button(
        create_environment_button_x, create_environment_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
        "Create Config", font, lambda: "create_config"
    )
    back_button_x = gui_config.HORIZONTAL_PADDING
    back_button_y = screen_height - gui_config.ENTER_BUTTON_HEIGHT - gui_config.INPUT_AREA_BOTTOM_PADDING #
    back_button = Button(
        back_button_x, back_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
        "Back", font, lambda: "go_back"
    )

    # --- Viewport & Scrollable Content Setup ---
    viewport_y = 0
    viewport_height = back_button.rect.top - viewport_y - 15
    viewport_rect = pygame.Rect(0, viewport_y, screen_width, viewport_height)
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height))

    footer_height = screen_height - viewport_rect.bottom
    footer_rect = pygame.Rect(0, viewport_rect.bottom, screen_width, footer_height)

    menu_font = pygame.font.Font(None, 25)

    flavor_text_display = PulsingText(
        "", menu_font,
        (viewport_height / 2, viewport_height / 2 + 25),
        color=(100, 255, 100), ang_velocity=0.002
    )

    elements = []
    current_y = 10
    current_y = draw_labeled_dropdown_or_input(font, "ai_provider_name", "Provider:", current_y, screen_width, elements, options=AVAILABLE_SIMPLE_AI)
    current_y = draw_labeled_dropdown_or_input(font, "select_model", "Model Name:", current_y, screen_width, elements, is_dropdown=False)
    title_surface, title_rect = draw_section_title(font, "System Prompt", current_y, screen_width)
    elements.append((title_surface, title_rect))
    current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    system_prompt_label_surface = font.render("Home Idea:", True, config.WHITE)
    system_prompt_label_rect = system_prompt_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    system_prompt_input = TextInputBox(
        gui_config.HORIZONTAL_PADDING, system_prompt_label_rect.bottom + 5, screen_width - 2*gui_config.HORIZONTAL_PADDING,
        gui_config.CONFIG_INPUT_BOX_HEIGHT * 2, font, 'sys_prompt', allow_newlines=True, text_inputs=text_inputs, active_element=active_element
    )
    elements.append((system_prompt_label_surface, system_prompt_label_rect))
    elements.append(system_prompt_input)
    current_y = system_prompt_input.rect.h + gui_config.INPUT_BOX_SPACING

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

        # FIXED: `is_processing` now correctly excludes the COMPLETED state.
        is_processing = process_state not in [ProcessState.IDLE, ProcessState.COMPLETED, ProcessState.ERROR]

        if not is_processing:
            flavor_text_display.hide()
        else:
            flavor_text_display.show()

        # --- Redesigned Signal Handling ---
        while not signal_queue.empty():
            try:
                signal, data = signal_queue.get_nowait()
                if signal == CrafterSignal.FOUNDATION_START:
                    process_state = ProcessState.FOUNDATION
                    main_status_message = "Phase 1: Building Foundation"
                    sub_status_message = "Generating house and room structure..."
                    current_progress = 0
                elif signal == CrafterSignal.POPULATION_START:
                    process_state = ProcessState.POPULATION
                    main_status_message = "Phase 2: Populating Rooms"
                elif signal == CrafterSignal.POPULATION_PROGRESS:
                    sub_status_message = f"Furnishing '{data['room_name']}' ({data['current']}/{data['total']})"
                    current_progress = (data['current'] / data['total']) * 100
                elif signal in [CrafterSignal.FILTERING_START, CrafterSignal.SAVING_START, CrafterSignal.FINALIZING]:
                    process_state = ProcessState.FINALIZATION
                    main_status_message = "Phase 3: Finalizing"
                    if signal == CrafterSignal.FILTERING_START:
                        sub_status_message = "Filtering for unique items..."
                    elif signal == CrafterSignal.SAVING_START:
                        sub_status_message = "Saving configuration files..."
                    else:
                        sub_status_message = "Assembling the final data..."
                    current_progress = 100
                elif signal == CrafterSignal.FLAVOR_TEXT:
                    flavor_text_display.update_text(data)
                elif signal == CrafterSignal.OVERALL_COMPLETE:
                    process_state = ProcessState.COMPLETED
                    completion_data = result_queue.get()
                    print(f"Received result: {completion_data}")
                    gui.gui_popups.show_popup_message("Environment created successfully!", (0, 255, 0), True)
                elif signal == CrafterSignal.ERROR:
                    process_state = ProcessState.ERROR
                    error_message = f"Error: {data}"
                    gui.gui_popups.show_popup_message(error_message, (255, 0, 0), True)
                    reset_processing_state()
                elif signal == CrafterSignal.SHUTDOWN_COMPLETE:
                    if process_state == ProcessState.CANCELLING:
                        gui.gui_popups.clear_all_popups()
                        running = False
            except queue.Empty:
                break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if processing_thread and processing_thread.is_alive():
                    if base_state_crafter_instance: base_state_crafter_instance.request_shutdown()
                    processing_thread.join(timeout=1.0)
                pygame.quit()
                sys.exit()

            # --- Event Handling ---
            is_form_active = process_state in [ProcessState.IDLE, ProcessState.ERROR]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_form_active and create_environment_button.rect.collidepoint(mouse_pos):
                    if create_environment_button.handle_event(event, mouse_pos) == "create_config":
                        user_prompt = text_inputs['sys_prompt']
                        select_provider = dropdowns['ai_provider_name']
                        select_model = text_inputs['select_model']
                        select_data = [user_prompt.text, select_provider.selected_option, select_model.text]

                        if any(not item or not item.strip() for item in select_data):
                            gui.gui_popups.show_popup_message("All fields must be filled out.", (255, 0, 0), True)
                            continue


                        flavor_text_display.color = (100, 255, 100) # The original green color
                        base_state_crafter_instance = BaseCrafter(
                            select_model.text, select_provider.selected_option,
                            initial_states_manager, signal_queue=signal_queue
                        )
                        if start_threaded_processing(base_state_crafter_instance, user_prompt.text):
                            gui.gui_popups.show_popup_message("Starting environment creation...", (0, 255, 255), True)
                        else:
                            gui.gui_popups.show_popup_message("Processing already in progress.", (255, 255, 0), True)
                elif back_button.rect.collidepoint(mouse_pos):
                    if back_button.handle_event(event, mouse_pos) == "go_back":
                        if is_processing or process_state == ProcessState.CANCELLING:
                            process_state = ProcessState.CANCELLING
                            flavor_text_display.color = (255, 0, 0) # Change color to red
                            flavor_text_display.update_text("Cancelling the creation...")
                            main_status_message = "Cancelling..."
                            sub_status_message = "Waiting for process to stop safely."
                            if base_state_crafter_instance:
                                base_state_crafter_instance.request_shutdown()
                        else:
                            gui.gui_popups.clear_all_popups()
                            running = False

            # FIXED: Moved scroll handling to the main event loop and separated logic by state
            if event.type == pygame.MOUSEWHEEL and viewport_rect.collidepoint(mouse_pos):
                if is_any_dropdown_open(mouse_pos, scroll_offset_y, viewport_rect):
                    # Let the dropdown handle its own scrolling - don't scroll the main viewport
                    pass  # The dropdown will handle the scroll in its own handle_event method
                elif process_state == ProcessState.COMPLETED:
                    completion_scroll_offset -= event.y * scroll_speed
                    # Ensure total_content_height for completion screen is updated in the drawing phase
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    completion_scroll_offset = max(0, min(completion_scroll_offset, max_scroll))
                elif is_form_active:
                    scroll_offset_y -= event.y * scroll_speed
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))

            if is_form_active:
                adjusted_mouse_pos = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y + scroll_offset_y)
                if active_element:
                    active_element.handle_event(event, adjusted_mouse_pos)
                else:
                    for element in elements:
                        if hasattr(element, 'handle_event'):
                            element.handle_event(event, adjusted_mouse_pos)

        # --- Drawing ---
        screen.fill(config.BLACK)
        
        # Hide the create button if processing, otherwise show it.
        create_environment_button.hidden = is_processing or process_state == ProcessState.CANCELLING

        # FIXED: A single clear if/elif/else structure to manage what is drawn in the main viewport.
        if process_state == ProcessState.COMPLETED:
            # --- Draw Completion Screen ---
            # The draw function now returns the content height for scrolling calculations
            total_content_height = draw_completion_screen(screen, font, completion_data, completion_scroll_offset, viewport_rect)

        elif is_processing or process_state == ProcessState.CANCELLING:
            # --- Draw Processing Indicators ---
            main_text = font.render(main_status_message, True, (255, 255, 255))
            main_rect = main_text.get_rect(center=(screen_width / 2, viewport_height / 2 - 40))
            screen.blit(main_text, main_rect)
            
            sub_text = font.render(sub_status_message, True, (200, 200, 200))
            sub_rect = sub_text.get_rect(center=(screen_width / 2, viewport_height / 2))
            screen.blit(sub_text, sub_rect)

            if process_state == ProcessState.POPULATION:
                progress_bar_width = screen_width
                progress_bar_height = 20
                progress_bar_x = (screen_width - progress_bar_width) // 2
                progress_bar_y = main_rect.bottom + 80
                progress_bar_y = viewport_height - progress_bar_height
                pygame.draw.rect(screen, (50, 50, 50), (progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height))
                fill_width = (current_progress / 100) * progress_bar_width
                pygame.draw.rect(screen, (0, 200, 100), (progress_bar_x, progress_bar_y, fill_width, progress_bar_height))
                pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, (progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height), 1)
        else:
            # --- Draw Input Form (for IDLE or ERROR states) ---
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
            screen.blit(scroll_surface, viewport_rect.topleft)

        # --- Draw Common UI Elements ---
        flavor_text_display.draw(screen)
        gui.gui_popups.draw_popups(screen)
        create_environment_button.draw(screen, mouse_pos, 0)
        back_button.draw(screen, mouse_pos, 0)
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        pygame.display.flip()
        
    if processing_thread and processing_thread.is_alive():
        if base_state_crafter_instance: base_state_crafter_instance.request_shutdown()
        processing_thread.join(timeout=1.0)
    return None



def draw_labeled_dropdown_or_input(font, key, label_text, y, screen_width, elements, is_dropdown=True, options=None):
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
            x, y, box_width, gui_config.CONFIG_INPUT_BOX_HEIGHT, font, key, text_inputs=text_inputs, active_element=active_element
        )
    elements.append(element_ui)
    
    # Return the bottom of the element, which is its Y position plus its height, plus spacing
    # This ensures subsequent elements are positioned correctly below
    return element_ui.rect.bottom + gui_config.INPUT_BOX_SPACING



# Add this new function to draw the completion screen
def draw_completion_screen(screen, font, completion_data, scroll_offset, viewport_rect):
    """Draw the completion information screen."""
    if not completion_data:
        return 0
    
    # Create a surface for scrollable content
    scroll_surface = pygame.Surface((viewport_rect.width, viewport_rect.height * 2)) 
    scroll_surface.fill(config.BLACK)
    
    current_y = 20
    padding = gui_config.HORIZONTAL_PADDING
    line_spacing = 25
    section_spacing = 35
    
    # Title
    title_font = pygame.font.Font(None, 32)
    title_text = title_font.render("Environment Created Successfully!", True, (0, 255, 0))
    title_rect = title_text.get_rect(centerx=viewport_rect.width // 2, top=current_y)
    scroll_surface.blit(title_text, title_rect)
    current_y = title_rect.bottom + section_spacing
    
    # Generation Summary Section
    if 'generation_summary' in completion_data:
        summary = completion_data['generation_summary']
        
        section_title = font.render("Generation Summary:", True, (200, 200, 255))
        scroll_surface.blit(section_title, (padding, current_y))
        current_y += line_spacing + 5
        
        # House details
        details = [
            f"House Name: {summary.get('house_name', 'Unknown')}",
            f"Total Rooms: {summary.get('total_rooms', 0)}",
            f"Total Items Generated: {summary.get('total_items_generated', 0)}",
            f"Starting Room: {summary.get('initial_room', 'Unknown')}"
        ]
        
        for detail in details:
            detail_text = font.render(detail, True, config.WHITE)
            scroll_surface.blit(detail_text, (padding + 20, current_y))
            current_y += line_spacing
        
        current_y += section_spacing
    
    # Blit the scrollable surface to the screen with offset
    screen.blit(scroll_surface, viewport_rect.topleft, 
                pygame.Rect(0, scroll_offset, viewport_rect.width, viewport_rect.height))
    
    return current_y + 50  # Return total content height


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