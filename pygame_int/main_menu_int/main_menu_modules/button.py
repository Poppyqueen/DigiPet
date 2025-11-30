import pygame

from ....pygame_int import gui_config

class Button:
    def __init__(self, x, y, w, h, text, font, action=None, border_color=None, border_width=0, text_color=None, button_color=None, hover_color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.action = action
        self.color = button_color or gui_config.BUTTON_COLOR
        self.hover_color = hover_color or gui_config.BUTTON_HOVER_COLOR
        
        # We still store the color, but we don't pre-render the surface here.
        self.text_color = text_color or gui_config.BUTTON_TEXT_COLOR 
        
        self.is_hovered = False
        self.border_color = border_color
        self.border_width = border_width

        self.hidden = False
        
        # Store the initial position for centering, will be updated in draw
        self.initial_center = self.rect.center 

    def handle_event(self, event, adjusted_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(adjusted_pos) and event.button == 1 and not self.hidden:
            if self.action:
                return self.action()
        return None

    def draw(self, target_surface, mouse_pos, offset_y):

        if not self.hidden:
            draw_rect = self.rect.move(0, -offset_y)
            self.is_hovered = draw_rect.collidepoint(mouse_pos)
            
            current_color = self.hover_color if self.is_hovered else self.color
            pygame.draw.rect(target_surface, current_color, draw_rect, border_radius=15)
            
            if self.border_color and self.border_width > 0:
                pygame.draw.rect(target_surface, self.border_color, draw_rect, self.border_width, border_radius=15)
            
            # --- CRITICAL CHANGE: RENDER TEXT EVERY FRAME ---
            # 1. Render the text using the LATEST self.text_color
            text_surface = self.font.render(self.text, True, self.text_color)
            
            # 2. Get the rectangle and center it on the drawn rectangle
            text_rect_final = text_surface.get_rect(center=draw_rect.center)
            
            # 3. Blit the newly rendered surface
            target_surface.blit(text_surface, text_rect_final)