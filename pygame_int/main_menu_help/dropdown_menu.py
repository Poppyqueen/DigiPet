import pygame

from pygame_int import gui_config


class DropdownMenu:
    """A class for handling dropdown menus."""
    def __init__(self, x, y, w, h, font, key, options, default_text='Select...', dropdowns=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.key = key
        self.default_text = default_text
        self.font = font
        self.options = options
        self.selected_option = None
        self.is_open = False
        self.options_rects = []
        dropdowns[self.key] = self
        self.validation_error = False
        
    # --- MODIFIED: Event handler now accepts an adjusted mouse position ---
    def handle_event(self, event, adjusted_pos):
        global active_element
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(adjusted_pos):
                self.validation_error=False
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
        border_color = (255, 0, 0) if self.validation_error else gui_config.INPUT_BOX_BORDER_COLOR
        pygame.draw.rect(target_surface, border_color, draw_rect, 2)

        display_text = self.selected_option if self.selected_option is not None else self.default_text
        text_surface = self.font.render(display_text, True, gui_config.BUTTON_TEXT_COLOR)
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