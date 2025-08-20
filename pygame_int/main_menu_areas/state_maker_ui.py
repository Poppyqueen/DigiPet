# main_menu_areas/config_creation_ui.py
from pygame_int import gui_config
from pygame_int import config
from pygame_int import state
import pygame

from pygame_int import gui

from pygame_int.main_menu_help.button import Button
from pygame_int.main_menu_help.checkbox import Checkbox
from pygame_int.main_menu_help.dropdown_menu import DropdownMenu
from pygame_int.main_menu_help.text_input_box import TextInputBox

from pygame_int.main_menu_help.main_menu_utils import (calculate_total_content_height, draw_section_title)

from pygame_int.main_menu_areas.crafter_signal import CrafterSignal

import sys
import threading
import queue
from enum import Enum

# imports for our threaded process
from data_constructors.base_state_construct import BaseCrafter


from utils.ai_loader import AIConfiguration




AVAILABLE_SIMPLE_AI=AIConfiguration.get_providers_by_mode("simple_ai")


dropdowns = {}

# Thread communication signals
class ProcessState(Enum):
    IDLE = "idle"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    ERROR = "error"

class ThreadSignal(Enum):
    START_PROCESSING = "start_processing"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_ERROR = "processing_error"
    CANCEL_PROCESSING = "cancel_processing"

text_inputs = {}
active_element = None

# Thread management globals
shutdown_event = threading.Event()
process_state = ProcessState.IDLE
signal_queue = queue.Queue()
result_queue = queue.Queue()
processing_thread = None


def start_enhanced_threaded_processing(base_state_crafter, user_prompt):
    """
    Start the enhanced processing in a separate thread.
    """
    global processing_thread, process_state
    
    if process_state != ProcessState.IDLE:
        return False  # Already processing
    
    # Clear any old results from queues
    while not signal_queue.empty():
        signal_queue.get()
    while not result_queue.empty():
        result_queue.get()
    
    # Start the enhanced worker thread
    processing_thread = threading.Thread(
        target=enhanced_worker_thread, # <<< TARGETS THE NEW WORKER
        args=(base_state_crafter, user_prompt, signal_queue, result_queue),
        daemon=True
    )
    processing_thread.start()
    process_state = ProcessState.PROCESSING # Set state to processing immediately
    
    return True


def reset_processing_state():
    """Reset the processing state back to idle."""
    global process_state, processing_thread
    process_state = ProcessState.IDLE
    processing_thread = None

# =============================================================================
# Example 2: Updated worker thread function to handle BaseCrafter signals
# =============================================================================

def enhanced_worker_thread(base_state_crafter, user_prompt, ui_signal_queue, result_queue):
    """
    Enhanced worker thread that handles signals from BaseCrafter
    """
    try:
        # Create a signal queue for BaseCrafter to use
        crafter_signal_queue = queue.Queue()
        
        # Pass the signal queue to BaseCrafter (if it supports it)
        if hasattr(base_state_crafter, 'signal_queue'):
            base_state_crafter.signal_queue = crafter_signal_queue
        
        # Start processing in a separate thread so we can monitor signals
        import threading
        
        processing_complete = threading.Event()
        processing_result = [None]
        processing_error = [None]
        
        def do_processing():
            try:
                result = base_state_crafter.generate_base_state(user_prompt)
                processing_result[0] = result
            except Exception as e:
                processing_error[0] = e
            finally:
                processing_complete.set()
        
        process_thread = threading.Thread(target=do_processing, daemon=True)
        process_thread.start()
        
        # Monitor for signals while processing
        while not processing_complete.is_set():
            try:
                # Check for signals from BaseCrafter
                signal, data = crafter_signal_queue.get(timeout=0.1)
                
                # Translate BaseCrafter signals to UI signals
                if signal == CrafterSignal.STARTED:
                    ui_signal_queue.put(("status_update", "Starting AI processing..."))
                elif signal == CrafterSignal.ANALYZING_PROMPT:
                    ui_signal_queue.put(("status_update", "Analyzing your prompt..."))
                elif signal == CrafterSignal.GENERATING_STATE:
                    ui_signal_queue.put(("status_update", "Generating environment state..."))
                elif signal == CrafterSignal.VALIDATING_RESULT:
                    ui_signal_queue.put(("status_update", "Validating results..."))
                elif signal == CrafterSignal.PROGRESS_UPDATE:
                    ui_signal_queue.put(("progress", data))  # data is percentage
                elif signal == CrafterSignal.ERROR:
                    ui_signal_queue.put(("error", data))
                    
            except queue.Empty:
                continue  # No signals, keep waiting
        
        # Processing finished, check results
        if processing_error[0]:
            raise processing_error[0]
        elif processing_result[0]:
            result_queue.put(processing_result[0])
            ui_signal_queue.put(("completed", "Environment created successfully!"))
        
    except Exception as e:
        result_queue.put(str(e))
        ui_signal_queue.put(("error", str(e)))

# =============================================================================
# Example 3: Updated UI signal handling
# =============================================================================

def check_enhanced_thread_signals():
    """
    Enhanced signal checking that handles different types of signals
    """
    global process_state
    
    result_data = None
    status_message = None
    progress_percentage = None
    
    # Process all available signals
    while not signal_queue.empty():
        try:
            signal_type, signal_data = signal_queue.get_nowait()
            
            if signal_type == "status_update":
                status_message = signal_data
                print(f"Status: {status_message}")
                
            elif signal_type == "progress":
                progress_percentage = signal_data
                print(f"Progress: {progress_percentage}%")
                
            elif signal_type == "completed":
                process_state = ProcessState.COMPLETED
                if not result_queue.empty():
                    result_data = result_queue.get()
                status_message = signal_data
                print("Processing completed!")
                
            elif signal_type == "error":
                process_state = ProcessState.ERROR
                status_message = f"Error: {signal_data}"
                print(f"Processing error: {signal_data}")
                
        except queue.Empty:
            break
    
    return {
        'result': result_data,
        'status': status_message, 
        'progress': progress_percentage
    }


def run_config_creation_twilight_zone(screen, font, init_states):
    """
    A UI for creating a new configuration, with a dedicated scrollable viewport.
    Now with the enhanced threading integration.
    """
    global process_state, processing_thread
    
    print("Entering New Configuration UI...")

    state.panel_width = 0
    state.panel_visible = False
    clock = pygame.time.Clock()
    running = True
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    initial_states_manager = init_states
    

    # Reset processing state when entering UI
    reset_processing_state()
    
    # +++ ADDED: Variables to hold status messages and progress from the thread
    current_status_message = ""
    current_progress = 0
    
    text_inputs.clear()

    # --- Fixed UI Elements ---
    create_environment_button_x = (screen_width - gui_config.ENTER_BUTTON_WIDTH) // 2
    create_environment_button_y = screen_height - gui_config.INPUT_AREA_BOTTOM_PADDING - gui_config.ENTER_BUTTON_HEIGHT
    create_environment_button = Button(
        create_environment_button_x, create_environment_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT,
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



    current_y = draw_labeled_dropdown_or_input(font, "ai_provider_name", "Provider:", current_y, screen_width, elements, options=AVAILABLE_SIMPLE_AI)

    current_y = draw_labeled_dropdown_or_input(font, "select_model", "Model Name:", current_y, screen_width, elements, is_dropdown=False)




    title_surface, title_rect = draw_section_title(font, "System Prompt", current_y, screen_width)
    elements.append((title_surface, title_rect))
    current_y = title_rect.bottom + gui_config.SECTION_TITLE_SPACING_BOTTOM
    
    system_prompt_label_surface = font.render("Home Idea:", True, config.WHITE)
    system_prompt_label_rect = system_prompt_label_surface.get_rect(left=gui_config.HORIZONTAL_PADDING, top=current_y)
    system_prompt_input = TextInputBox(
        gui_config.HORIZONTAL_PADDING, 
        system_prompt_label_rect.bottom + 5, 
        screen_width - 2*gui_config.HORIZONTAL_PADDING, 
        gui_config.CONFIG_INPUT_BOX_HEIGHT * 2, 
        font, 
        'sys_prompt', 
        allow_newlines=True, 
        text_inputs=text_inputs, 
        active_element=active_element
    )
    elements.append((system_prompt_label_surface, system_prompt_label_rect))
    elements.append(system_prompt_input)

    current_y += system_prompt_input.rect.h + gui_config.INPUT_BOX_SPACING




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

        # <<< CHANGED: Use the enhanced signal checker
        enhanced_results = check_enhanced_thread_signals()
        
        # +++ ADDED: Update status and progress from the returned dictionary
        if enhanced_results['status']:
            current_status_message = enhanced_results['status']
        if enhanced_results['progress'] is not None:
            current_progress = enhanced_results['progress']

        # <<< CHANGED: Simplified result/error handling. 
        # The 'check_enhanced_thread_signals' function now sets the process_state.
        # We just need to react to the state and the returned data.
        if process_state == ProcessState.COMPLETED:
            if enhanced_results['result'] is not None:
                # Process the result here
                print(f"Received result: {enhanced_results['result']}")
                gui.gui_popups.show_popup_message("Environment created successfully!", (0, 255, 0), True)
            reset_processing_state() # Reset to allow another run
            
        elif process_state == ProcessState.ERROR:
            # The error message is now in the status
            gui.gui_popups.show_popup_message(current_status_message, (255, 0, 0), True)
            reset_processing_state() # Reset to allow another run

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if processing_thread and processing_thread.is_alive():
                    processing_thread.join(timeout=1.0)
                pygame.quit()
                sys.exit()

            # --- Event Handling ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_environment_button.rect.collidepoint(mouse_pos):
                    if create_environment_button.handle_event(event, mouse_pos) == "create_config":
                        if process_state == ProcessState.IDLE:


                            user_prompt = text_inputs['sys_prompt']
                            select_provider = dropdowns['ai_provider_name']
                            select_model = text_inputs['select_model']


                            select_data = [
                                user_prompt.text,
                                select_provider.selected_option,
                                select_model.text
                            ]

                            validation_error = False
                            for item in select_data:
                                if not item or (isinstance(item, str) and not item.strip()):
                                    message = "All fields must be filled out."
                                    gui.gui_popups.show_popup_message(message, (255, 0, 0), True)
                                    validation_error = True

                            if validation_error:
                                continue

                            # Passed validation error!

                            base_state_crafter = BaseCrafter(select_model.text, select_provider.selected_option, initial_states_manager, signal_queue=signal_queue)  
                            # <<< CHANGED: Call the new enhanced processing starter
                            if start_enhanced_threaded_processing(base_state_crafter, user_prompt.text):
                                message = "Creating new environment with help from the AI..."
                                current_status_message = "Initializing..." # Initial status
                                current_progress = 0
                                gui.gui_popups.show_popup_message(message, (0, 255, 255), True)
                            else:
                                message = "Could not start processing. Please try again."
                                gui.gui_popups.show_popup_message(message, (255, 0, 0), True)
                        else:
                            message = "Please wait, processing is already in progress..."
                            gui.gui_popups.show_popup_message(message, (255, 255, 0), True)
                
                elif back_button.rect.collidepoint(mouse_pos):
                    if back_button.handle_event(event, mouse_pos) == "go_back":
                        if processing_thread and processing_thread.is_alive():
                            reset_processing_state()
                        gui.gui_popups.clear_all_popups()
                        running = False

            # --- Handle scrollable element events ---
            adjusted_mouse_pos = (
                mouse_pos[0] - viewport_rect.x,
                mouse_pos[1] - viewport_rect.y + scroll_offset_y
            )
            if active_element:
                active_element.handle_event(event, adjusted_mouse_pos)
            else:
                if event.type != pygame.MOUSEBUTTONDOWN:
                    for element in elements:
                        if hasattr(element, 'handle_event'):
                            element.handle_event(event, adjusted_mouse_pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if viewport_rect.collidepoint(mouse_pos):
                        for element in elements:
                            if hasattr(element, 'handle_event'):
                                element.handle_event(event, adjusted_mouse_pos)

            if viewport_rect.collidepoint(mouse_pos):
                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset_y -= event.y * scroll_speed
                    max_scroll = max(0, total_content_height - viewport_rect.height)
                    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll))

        if process_state == ProcessState.PROCESSING:
            create_environment_button.hidden = True
            #back_button.hidden = True
        elif process_state == ProcessState.IDLE:
            create_environment_button.hidden = False
            #back_button.hidden = False

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
                # Simplified drawing logic for example
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
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        create_environment_button.draw(screen, mouse_pos, 0)
        back_button.draw(screen, mouse_pos, 0)

        # <<< CHANGED: Draw the new, detailed processing indicator
        if process_state == ProcessState.PROCESSING:




            # Display 'Processing...'
            processing_message = font.render("Processing...", True, (255, 255, 255)) # Maybe we can make this blink, lets make a class for blinking text, maybe a "pulse" (softer and using alpha if possible to fade in and out? with an option for looping while active and an option for it to have and manage a timelife of its own?)
            processing_rect = processing_message.get_rect(center=(screen_width / 2, screen_height - gui_config.INPUT_AREA_BOTTOM_PADDING - gui_config.ENTER_BUTTON_HEIGHT))
            screen.blit(processing_message, processing_rect) 


            # Display the current status message from the thread
            status_text = font.render(current_status_message, True, (255, 255, 0))

            status_rect = status_text.get_rect(center=(screen_width / 2, screen_height / 2))


            screen.blit(status_text, status_rect) 

            
            # Draw a progress bar
            progress_bar_width = viewport_rect.width
            progress_bar_height = 20
            progress_bar_x = (screen_width - progress_bar_width) // 2
            progress_bar_y = viewport_height - progress_bar_height

            # Draw background
            pygame.draw.rect(screen, (50, 50, 50), (progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height))
            # Draw foreground
            fill_width = (current_progress / 100) * progress_bar_width
            pygame.draw.rect(screen, (0, 200, 100), (progress_bar_x, progress_bar_y, fill_width, progress_bar_height))
            # Draw border
            pygame.draw.rect(screen, config.WHITE, (progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height), 1)

        gui.gui_popups.draw_popups(screen)
        pygame.display.flip()
    
    if processing_thread and processing_thread.is_alive():
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