import pygame

from ....pygame_int import gui_config


class Checkbox:
    def __init__(self, x, y, text, font, initial_state=False):
        self.text = text
        self.font = font
        self.text_surface = font.render(text, True, gui_config.BUTTON_TEXT_COLOR)
        self.text_rect = self.text_surface.get_rect(topleft=(x + 25, y))
        self.rect = pygame.Rect(x, y, 20, 20)
        self.checked = initial_state
        self.is_hovered = False
        self.validation_error = False
    # --- MODIFIED: Event handler now accepts an adjusted mouse position ---
    def handle_event(self, event, adjusted_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(adjusted_pos):
                self.validation_error = None
                self.checked = not self.checked
        return None

    def draw(self, target_surface, mouse_pos, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        self.is_hovered = draw_rect.collidepoint(mouse_pos)
        pygame.draw.rect(target_surface, gui_config.INPUT_BOX_BACKGROUND_COLOR, draw_rect)
        #border_color = gui_config.ACTIVE_INPUT_BOX_BORDER_COLOR if self.is_hovered else gui_config.INPUT_BOX_BORDER_COLOR
        border_color = (255,0,0) if self.validation_error else gui_config.INPUT_BOX_BORDER_COLOR 
        pygame.draw.rect(target_surface, border_color, draw_rect, 2)
        if self.checked:
            pygame.draw.line(target_surface, gui_config.BUTTON_TEXT_COLOR, (draw_rect.left + 5, draw_rect.top + 5), (draw_rect.right - 5, draw_rect.bottom - 5), 2)
            pygame.draw.line(target_surface, gui_config.BUTTON_TEXT_COLOR, (draw_rect.left + 5, draw_rect.bottom - 5), (draw_rect.right - 5, draw_rect.top + 5), 2)
        
        text_rect_offset = self.text_rect.move(0, -offset_y)
        target_surface.blit(self.text_surface, text_rect_offset)
        return self.checked
