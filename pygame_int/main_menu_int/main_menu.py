import pygame
import sys
from pygame_int import gui_config, state
from pygame_int import config



from pygame_int.main_menu_int.main_menu_modules.button import Button

from pygame_int.main_menu_int.main_menu_modules.pop_up import Popup

from pygame_int.main_menu_int.main_menu_areas.config_creation_ui import run_config_creation_ui
from pygame_int.main_menu_int.main_menu_areas.state_maker_ui import run_config_creation_twilight_zone

from inventory_items.base_state_manager.base_state_config import InitialStateConst


initial_states_manager=InitialStateConst()

def extract_color(config_manager, config_name):

    default_color = [255, 255, 255]
    color=config_manager.examine_config(config_name,'AI','pet_color')
    if not color:
        color=default_color
        print(f"No color found for config '{config_name}', It probably hasn't been configured yet. Using default color: {color}")
    return color
    

def run_config_main_menu_ui(screen, font, config_manager):
    print("Entering Main Config Menu...")
    clock = pygame.time.Clock()
    running = True


    # state.panel_width=0
    # state.panel_visible=False


    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    title_text = "Configuration Menu"
    title_surface = font.render(title_text, True, config.WHITE)
    title_rect = title_surface.get_rect(centerx=screen_width // 2, top=20)
    
    new_button_x = screen_width - gui_config.HORIZONTAL_PADDING - gui_config.ENTER_BUTTON_WIDTH
    new_button_y = title_rect.bottom + 15
    make_new_button = Button(new_button_x, new_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT, "Make DigiPet", font, lambda: "create_new")




    packages_button_x =  - gui_config.HORIZONTAL_PADDING + gui_config.ENTER_BUTTON_WIDTH
    packages_button_y = title_rect.bottom + 15
    packages_button = Button(packages_button_x, packages_button_y, gui_config.ENTER_BUTTON_WIDTH, gui_config.ENTER_BUTTON_HEIGHT, "Make Home", font, lambda: "create_new_package")

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
                # Prioritize static buttons. If a click happens on them, consume the event.
                if make_new_button.rect.collidepoint(mouse_pos):
                    result = make_new_button.handle_event(event, mouse_pos)
                    if result == "create_new":
                        result = run_config_creation_ui(screen, font, config_manager, initial_states_manager.states_configs)
                        print("Ran config creation UI")
                        if result == "config_created":
                            print("Config created")
                            # Can we return an load the agent here instead of rebuilding the list?
                            return True
                        else:
                            print("Config not created")
                        # Rebuild the list in case new configs were added

                        scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
                        scroll_offset_y = 0
                    continue  #

                if packages_button.rect.collidepoint(mouse_pos):
                    result = packages_button.handle_event(event, mouse_pos)
                    if result == "create_new_package":
                        run_config_creation_twilight_zone(screen, font, initial_states_manager) # To create base states 
                        # Rebuild the list in case new configs were added
                        scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
                        scroll_offset_y = 0
                    continue  #                        
                
                # Only check scrollable content if the click is within the viewport
                elif viewport_rect.collidepoint(mouse_pos):
                    adjusted_mouse_pos = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y + scroll_offset_y)

                    # Check delete buttons first
                    for button in delete_buttons:
                        result = button.handle_event(event, adjusted_mouse_pos)
                        if isinstance(result, tuple) and result[0] == "delete":
                            config_to_delete = result[1]
                            message = f"Attempting to delete '{config_to_delete}'. \nThis will delete all data associated with the relevant pet. \n\nThis action is irreversible. \n\nAre you sure you want to proceed?"

                            popup = Popup(screen, font, message)
                            if popup.run():
                                config_manager.delete_pet_archive(config_to_delete)
                                scrollable_buttons, delete_buttons, total_content_height = _build_scrollable_config_list(config_manager, font, viewport_rect.width)
                                scroll_offset_y = 0
                            else: # user cancelled
                                print("Deletion cancelled by user.") 
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
        

        # --- FIX IS HERE ---
        # 1. Determine if the mouse is physically inside the viewport rectangle.
        is_mouse_in_viewport = viewport_rect.collidepoint(mouse_pos)
        
        # 2. Calculate the mouse position relative to the scrollable surface.
        mouse_pos_in_viewport = (mouse_pos[0] - viewport_rect.x, mouse_pos[1] - viewport_rect.y)

        # 3. Create a "safe" position for hover checks. If the mouse is outside the viewport,
        #    use an impossible coordinate so nothing can be hovered.
        hover_check_pos = mouse_pos_in_viewport if is_mouse_in_viewport else (-1, -1)
        # --- END OF FIX ---

        scroll_surface.fill(config.BLACK)

        # 4. Pass the SAFE hover_check_pos to the draw methods.
        for button in scrollable_buttons:
            button.draw(scroll_surface, hover_check_pos, scroll_offset_y)
        # Draw delete buttons on top
        for button in delete_buttons:
            button.draw(scroll_surface, hover_check_pos, scroll_offset_y)

        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)
        screen.blit(scroll_surface, viewport_rect.topleft)
        pygame.draw.rect(screen, gui_config.INPUT_BOX_BORDER_COLOR, viewport_rect, 1)

        # Static elements are drawn last and use the original mouse_pos
        screen.blit(title_surface, title_rect)
        make_new_button.draw(screen, mouse_pos, 0)
        packages_button.draw(screen,mouse_pos, 0)

        pygame.display.flip()
        
    return None
