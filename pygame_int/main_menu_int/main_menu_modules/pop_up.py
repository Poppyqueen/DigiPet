import pygame

from pygame_int import gui_config

from pygame_int.main_menu_int.main_menu_modules.button import Button

import sys

from pygame_int import config

class Popup:
    """A class to handle confirmation popups."""
    def __init__(self, screen, font, message):
        self.screen = screen
        self.font = font
        self.message = message
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        self.popup_width = 450


        # --- START OF DYNAMIC SIZING UPDATE ---

        # 1. Calculate the height required for the text message.
        lines = self.message.split('\n')
        text_height = len(lines) * self.font.get_height()

        # 2. Define vertical padding and space for buttons.
        top_padding = 40  # Increased padding for better spacing
        bottom_padding = 20
        button_height = 40
        space_above_buttons = 20

        # 3. Calculate the total dynamic height of the popup.
        self.popup_height = top_padding + text_height + space_above_buttons + button_height + bottom_padding
        
        # 4. Create the popup rectangle with the new dynamic height.
        self.popup_rect = pygame.Rect(
            (self.screen_width - self.popup_width) // 2,
            (self.screen_height - self.popup_height) // 2,
            self.popup_width,
            self.popup_height
        )

        # 5. Calculate the Y position for the buttons based on the new popup bottom.
        button_y_position = self.popup_rect.bottom - bottom_padding - button_height

        self.accept_button = Button(
            self.popup_rect.right - 170, button_y_position, 120, 40, "Accept", font, lambda: True
        )
        self.back_button = Button(
            self.popup_rect.x + 50, button_y_position, 120, 40, "Go Back", font, lambda: False
        )
        # --- END OF DYNAMIC SIZING UPDATE ---

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
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # --- FIX IS HERE ---
                    # First, check if the accept button was clicked.
                    # handle_event should return None if not clicked, or the lambda result if clicked.
                    accept_result = self.accept_button.handle_event(event, mouse_pos)
                    if accept_result is not None:
                        # Since the lambda is `lambda: True`, we know this will be True.
                        return True

                    # Separately, check if the back button was clicked.
                    back_result = self.back_button.handle_event(event, mouse_pos)
                    if back_result is not None:
                        # Since the lambda is `lambda: False`, we know this will be False.
                        print("User chose to go back.") # This will now print.
                        return False
                    # --- END OF FIX ---

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
