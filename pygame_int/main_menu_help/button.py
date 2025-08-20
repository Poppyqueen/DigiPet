import pygame

from pygame_int import gui_config

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

        self.hidden = False

    def handle_event(self, event, adjusted_pos):
        # The collision check is now simple and correct.
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(adjusted_pos) and event.button == 1 and not self.hidden:
            if self.action:
                return self.action()
        return None

    # --- REVERTED TO SIMPLER, CORRECT VERSION ---
    def draw(self, target_surface, mouse_pos, offset_y):

        if not self.hidden:
            draw_rect = self.rect.move(0, -offset_y)
            # The mouse_pos passed to this function will now be pre-validated by the caller.
            # This makes the logic here simple and effective.
            self.is_hovered = draw_rect.collidepoint(mouse_pos)
            
            current_color = self.hover_color if self.is_hovered else self.color
            pygame.draw.rect(target_surface, current_color, draw_rect, border_radius=15)
            
            if self.border_color and self.border_width > 0:
                pygame.draw.rect(target_surface, self.border_color, draw_rect, self.border_width, border_radius=15)
            
            text_rect_final = self.text_surface.get_rect(center=draw_rect.center)
            target_surface.blit(self.text_surface, text_rect_final)
