import pygame
import math
import sys
from pygame_int import gui_config # For INPUT_BOX_HEIGHT, GRID_COLS, etc.
from pygame_int.main_digipet.colors_config import _color_selection_options # For the list of colors
# gui_core might not be needed if font is passed as an argument and no other core elements are directly accessed.

active_input_box = None # 0 for R, 1 for G, 2 for B
rgb_input_values = ["", "", ""] # Store input text for R, G, B

def run_color_selection_ui(screen, font):
    """
    Runs a blocking UI loop to allow the user to select a pet theme color.
    Dynamically calculates grid layout to fit options on the screen.
    Adds an optional RGB text input at the bottom.
    Returns the selected color tuple (R, G, B) or None if the user quits.
    Uses local active_input_box, rgb_input_values.
    Uses gui_config for constants.
    Uses _color_selection_options from colors_config.
    """
    global active_input_box, rgb_input_values # Use global variables

    print("Entering color selection UI (Dynamic Grid Layout + RGB Input)...")
    clock = pygame.time.Clock()

    screen_width = screen.get_width()
    screen_height = screen.get_height()
    num_options = len(_color_selection_options)

    # Calculate grid dimensions
    num_rows = math.ceil(num_options / gui_config.GRID_COLS)

    # --- Dynamically Calculate Circle Size and Spacing ---

    # Available width and height for the grid area
    available_width = screen_width - 2 * gui_config.HORIZONTAL_PADDING
    # Estimate height needed for instruction text and RGB input area
    rgb_input_area_height = gui_config.INPUT_BOX_HEIGHT + gui_config.INPUT_AREA_BOTTOM_PADDING # Approximate height for input boxes and padding
    available_height = screen_height - gui_config.VERTICAL_START_Y_GRID_AREA - rgb_input_area_height - gui_config.HORIZONTAL_PADDING # Use HORIZONTAL_PADDING for top/bottom grid padding

    try:
        sample_text_height = font.get_linesize()
    except:
        sample_text_height = 20 # Default if get_linesize fails

    # To simplify, let's first determine the maximum possible diameter including spacing per grid cell
    max_item_width = available_width / gui_config.GRID_COLS

    # Let's allocate a percentage of the item space to the circle and the rest to spacing and text.
    # circle_space_ratio = 0.7 # Percentage of item space for the circle (adjust as needed)

    # Calculate potential diameter based on width constraint
    required_item_width = available_width / gui_config.GRID_COLS
    required_item_height = available_height / num_rows

    # The diameter of the circle plus horizontal spacing must fit within required_item_width
    # The diameter of the circle plus vertical spacing and text height must fit within required_item_height

    # Let's assume horizontal spacing and vertical spacing are a certain factor of the circle diameter.
    spacing_factor = 0.2 # Adjust this factor to control the spacing relative to the circle size

    # The actual radius will be the minimum of the radii calculated from width and height constraints.
    max_radius_by_width = required_item_width / (2 * (1 + spacing_factor))
    # Ensure required_item_height - sample_text_height is not negative
    if required_item_height - sample_text_height < 0:
        max_radius_by_height = 0 # Or handle error
    else:
        max_radius_by_height = (required_item_height - sample_text_height) / (2 * (1 + spacing_factor + gui_config.TEXT_SPACING_BELOW_CIRCLE_FACTOR))

    calculated_radius = min(max_radius_by_width, max_radius_by_height)

    # Ensure the radius is not too small or negative
    COLOR_SELECTION_CIRCLE_RADIUS = max(5, int(calculated_radius)) # Minimum radius of 5

    # Calculate actual spacing based on the calculated radius
    GRID_HORIZONTAL_SPACING = spacing_factor * 2 * COLOR_SELECTION_CIRCLE_RADIUS
    GRID_VERTICAL_SPACING = spacing_factor * 2 * COLOR_SELECTION_CIRCLE_RADIUS
    TEXT_SPACING_BELOW_CIRCLE = gui_config.TEXT_SPACING_BELOW_CIRCLE_FACTOR * 2 * COLOR_SELECTION_CIRCLE_RADIUS

    # Recalculate the starting position for the grid based on the calculated size and spacing
    total_grid_width = gui_config.GRID_COLS * (2 * COLOR_SELECTION_CIRCLE_RADIUS + GRID_HORIZONTAL_SPACING) - GRID_HORIZONTAL_SPACING
    start_x = (screen_width - total_grid_width) // 2 + COLOR_SELECTION_CIRCLE_RADIUS # Start position for the center of the first circle

    # Calculate the center points for the circles in the grid
    circle_centers = []
    for i in range(num_options):
        row = i // gui_config.GRID_COLS
        col = i % gui_config.GRID_COLS

        center_x = start_x + col * (2 * COLOR_SELECTION_CIRCLE_RADIUS + GRID_HORIZONTAL_SPACING)
        center_y = gui_config.VERTICAL_START_Y_GRID_AREA + row * (2 * COLOR_SELECTION_CIRCLE_RADIUS + GRID_VERTICAL_SPACING + sample_text_height + TEXT_SPACING_BELOW_CIRCLE)

        circle_centers.append((center_x, center_y))

    # Calculate position for the instruction text
    instruction_text = "Choose your pet's theme color or enter RGB:"
    try:
        instruction_surface = font.render(instruction_text, True, (255, 255, 255)) # Assuming WHITE
        instruction_rect = instruction_surface.get_rect()
        instruction_rect.centerx = screen_width // 2
        instruction_rect.top = gui_config.INSTRUCTION_TEXT_Y
    except pygame.error as e:
         print(f"Error rendering instruction text: {e}")
         instruction_surface = None
         instruction_rect = None

    # --- Calculate Positions for RGB Input Boxes and Button ---
    total_input_width = 3 * gui_config.INPUT_BOX_WIDTH + 2 * gui_config.INPUT_BOX_SPACING + gui_config.ENTER_BUTTON_WIDTH
    input_area_start_x = (screen_width - total_input_width) // 2
    input_area_top_y = screen_height - gui_config.INPUT_BOX_HEIGHT - gui_config.INPUT_AREA_BOTTOM_PADDING

    rgb_input_boxes = []
    for i in range(3):
        box_x = input_area_start_x + i * (gui_config.INPUT_BOX_WIDTH + gui_config.INPUT_BOX_SPACING)
        box_y = input_area_top_y
        rgb_input_boxes.append(pygame.Rect(box_x, box_y, gui_config.INPUT_BOX_WIDTH, gui_config.INPUT_BOX_HEIGHT))

    enter_button_rect = pygame.Rect(
        input_area_start_x + 3 * (gui_config.INPUT_BOX_WIDTH + gui_config.INPUT_BOX_SPACING) - gui_config.INPUT_BOX_SPACING + gui_config.INPUT_BOX_SPACING, # Adjust for spacing
        input_area_top_y,
        gui_config.ENTER_BUTTON_WIDTH,
        gui_config.ENTER_BUTTON_HEIGHT
    )

    running = True
    selected_color = None

    while running:
        dt = clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    mouse_pos = pygame.math.Vector2(event.pos)

                    # Check for circle clicks
                    for i, center in enumerate(circle_centers):
                        # Need to ensure we only check circles that were successfully positioned
                        if i < len(circle_centers):
                            circle_center_vec = pygame.math.Vector2(center)
                            distance = mouse_pos.distance_to(circle_center_vec)

                            if distance <= COLOR_SELECTION_CIRCLE_RADIUS:
                                selected_color = _color_selection_options[i][0]
                                print(f"Color selected from circle: {_color_selection_options[i][1]} {selected_color}")
                                running = False
                                break # Stop checking circles

                    # If a circle was clicked, the loop will break and running will be False
                    if not running:
                        continue

                    # Check for input box clicks
                    active_input_box = None # Deactivate any currently active box
                    for i, box_rect in enumerate(rgb_input_boxes):
                        if box_rect.collidepoint(event.pos):
                            active_input_box = i
                            print(f"Input box {i} activated.")
                            break

                    # Check for Enter button click
                    if enter_button_rect.collidepoint(event.pos):
                        print("Enter button clicked.")
                        try:
                            r = int(rgb_input_values[0])
                            g = int(rgb_input_values[1])
                            b = int(rgb_input_values[2])

                            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                                selected_color = (r, g, b)
                                print(f"Color selected from RGB input: {selected_color}")
                                running = False
                            else:
                                print("Invalid RGB values. Please enter numbers between 0 and 255.")
                                # Optionally, add visual feedback for invalid input
                        except ValueError:
                            print("Invalid input. Please enter numerical values for RGB.")
                            # Optionally, add visual feedback for invalid input

            if event.type == pygame.KEYDOWN:
                if active_input_box is not None:
                    if event.key == pygame.K_BACKSPACE:
                        rgb_input_values[active_input_box] = rgb_input_values[active_input_box][:-1]
                    elif event.key == pygame.K_RETURN:
                         # Trigger processing of RGB input if Enter is pressed while in a box
                         try:
                            r = int(rgb_input_values[0])
                            g = int(rgb_input_values[1])
                            b = int(rgb_input_values[2])

                            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                                selected_color = (r, g, b)
                                print(f"Color selected from RGB input (Enter key): {selected_color}")
                                running = False
                            else:
                                print("Invalid RGB values. Please enter numbers between 0 and 255.")
                         except ValueError:
                            print("Invalid input. Please enter numerical values for RGB.")

                    elif event.unicode.isdigit():
                        # Limit input length if desired
                        if len(rgb_input_values[active_input_box]) < 3: # Limit to 3 digits per color component
                             rgb_input_values[active_input_box] += event.unicode


        # --- Drawing for the Color Selection UI ---
        screen.fill((0, 0, 0)) # Assuming BLACK

        # Draw instruction text
        if instruction_surface and instruction_rect:
             screen.blit(instruction_surface, instruction_rect)

        # Draw color circles and names
        for i, (color, name) in enumerate(_color_selection_options):
            # Ensure we only draw circles that were successfully positioned
            if i < len(circle_centers):
                center = circle_centers[i]

                # Draw the color circle
                # For Black, draw a white circle outline with black fill (looks like a ring)
                if color == (0, 0, 0): # Assuming BLACK
                     pygame.draw.circle(screen, (255, 255, 255), center, COLOR_SELECTION_CIRCLE_RADIUS) # Assuming WHITE
                     # Draw the inner black circle slightly smaller to create the ring effect
                     pygame.draw.circle(screen, (0, 0, 0), center, max(0, COLOR_SELECTION_CIRCLE_RADIUS - 2)) # Ensure radius is not negative
                else:
                    pygame.draw.circle(screen, color, center, COLOR_SELECTION_CIRCLE_RADIUS)
                    pygame.draw.circle(screen, (255, 255, 255), center, COLOR_SELECTION_CIRCLE_RADIUS, 1) # Assuming WHITE border


        # --- Draw RGB Input Boxes ---
        for i, box_rect in enumerate(rgb_input_boxes):
            # Draw box background
            pygame.draw.rect(screen, (0, 0, 0), box_rect) # Black background
            # Draw border
            border_color = gui_config.ACTIVE_INPUT_BOX_BORDER_COLOR if active_input_box == i else gui_config.INPUT_BOX_BORDER_COLOR
            pygame.draw.rect(screen, border_color, box_rect, 2) # 2 pixel border

            # Draw input text
            try:
                text_surface = font.render(rgb_input_values[i], True, gui_config.INPUT_TEXT_COLOR)
                text_rect = text_surface.get_rect(centery=box_rect.centery, left=box_rect.left + 5) # Add a little left padding
                screen.blit(text_surface, text_rect)
            except pygame.error as e:
                 print(f"Error rendering input text: {e}")

            # Draw R, G, B labels
            label_text = ["R", "G", "B"][i]
            try:
                label_surface = font.render(label_text, True, (255, 255, 255)) # White labels
                label_rect = label_surface.get_rect(bottom=box_rect.top - 5, centerx=box_rect.centerx) # Position above the box
                screen.blit(label_surface, label_rect)
            except pygame.error as e:
                 print(f"Error rendering label text: {e}")


        # --- Draw Enter Button ---
        pygame.draw.rect(screen, gui_config.BUTTON_COLOR, enter_button_rect)
        try:
            button_text_surface = font.render("Enter", True, gui_config.BUTTON_TEXT_COLOR)
            button_text_rect = button_text_surface.get_rect(center=enter_button_rect.center)
            screen.blit(button_text_surface, button_text_rect)
        except pygame.error as e:
             print(f"Error rendering button text: {e}")

        # --- Update Display ---
        pygame.display.flip()

    print("Exiting color selection UI.")

    # Reset active input box and input values on exit
    active_input_box = None
    rgb_input_values = ["", "", ""]

    return selected_color


# huh