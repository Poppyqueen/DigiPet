import pygame

from pygame_int import gui_config

class DropdownMenu:
    """A class for handling dropdown menus with scrolling support."""
    
    def __init__(self, x, y, w, h, font, key, options, default_text='Select...', dropdowns=None, max_visible_options=5):
        self.rect = pygame.Rect(x, y, w, h)
        self.key = key
        self.default_text = default_text
        self.font = font
        self.options = options
        self.selected_option = None
        self.is_open = False
        self.options_rects = []
        self.validation_error = False
        
        # Scrolling properties
        self.max_visible_options = max_visible_options
        self.scroll_offset = 0
        self.option_height = h  # Height of each option
        self.dropdown_rect = None  # Will be set when dropdown opens
        
        if dropdowns is not None:
            dropdowns[self.key] = self

    def _calculate_dropdown_bounds(self):
        """Calculate the bounds for the dropdown options area."""
        visible_options = min(len(self.options), self.max_visible_options)
        dropdown_height = visible_options * self.option_height
        
        self.dropdown_rect = pygame.Rect(
            self.rect.x, 
            self.rect.bottom, 
            self.rect.width, 
            dropdown_height
        )

    def _get_visible_options(self):
        """Get the currently visible options based on scroll offset."""
        start_idx = self.scroll_offset
        end_idx = min(start_idx + self.max_visible_options, len(self.options))
        return self.options[start_idx:end_idx], start_idx

    def handle_event(self, event, adjusted_pos):
        global active_element
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if clicking on the main dropdown button
            if self.rect.collidepoint(adjusted_pos):
                self.validation_error = False
                self.is_open = not self.is_open
                if self.is_open:
                    self._calculate_dropdown_bounds()
                    self.scroll_offset = 0  # Reset scroll when opening
                active_element = self if self.is_open else None
                
            # Check if clicking on dropdown options
            elif self.is_open and self.dropdown_rect and self.dropdown_rect.collidepoint(adjusted_pos):
                visible_options, start_idx = self._get_visible_options()
                
                for i, option_rect in enumerate(self.options_rects):
                    if option_rect.collidepoint(adjusted_pos):
                        actual_option_idx = start_idx + i
                        if actual_option_idx < len(self.options):
                            self.selected_option = self.options[actual_option_idx]
                            self.is_open = False
                            active_element = None
                            return self.selected_option
            else:
                # Clicked outside - close dropdown
                if self.is_open:
                    self.is_open = False
                    active_element = None
                    
        # Handle mouse wheel scrolling
        elif event.type == pygame.MOUSEWHEEL and self.is_open:
            # Check if mouse is over the dropdown area
            if self.dropdown_rect and self.dropdown_rect.collidepoint(adjusted_pos):
                # Scroll up (negative) or down (positive)
                scroll_direction = -event.y  # Invert for natural scrolling
                self.scroll_offset += scroll_direction
                
                # Clamp scroll offset
                max_scroll = max(0, len(self.options) - self.max_visible_options)
                self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
                
        return None

    def draw(self, target_surface, offset_y):
        # Draw main dropdown button
        draw_rect = self.rect.move(0, -offset_y)
        pygame.draw.rect(target_surface, gui_config.BUTTON_COLOR, draw_rect)
        border_color = (255, 0, 0) if self.validation_error else gui_config.INPUT_BOX_BORDER_COLOR
        pygame.draw.rect(target_surface, border_color, draw_rect, 2)
        
        # Draw text on button
        display_text = self.selected_option if self.selected_option is not None else self.default_text
        text_surface = self.font.render(display_text, True, gui_config.BUTTON_TEXT_COLOR)
        target_surface.blit(text_surface, (draw_rect.x + 5, draw_rect.y + 5))
        
        # Draw dropdown arrow indicator
        arrow_x = draw_rect.right - 20
        arrow_y = draw_rect.centery
        if self.is_open:
            # Up arrow
            pygame.draw.polygon(target_surface, gui_config.BUTTON_TEXT_COLOR, [
                (arrow_x, arrow_y + 3),
                (arrow_x + 6, arrow_y - 3),
                (arrow_x + 12, arrow_y + 3)
            ])
        else:
            # Down arrow
            pygame.draw.polygon(target_surface, gui_config.BUTTON_TEXT_COLOR, [
                (arrow_x, arrow_y - 3),
                (arrow_x + 6, arrow_y + 3),
                (arrow_x + 12, arrow_y - 3)
            ])

        if self.is_open:
            self._draw_dropdown_options(target_surface, offset_y)

    def _draw_dropdown_options(self, target_surface, offset_y):
        """Draw the dropdown options with scrolling support."""
        if not self.dropdown_rect:
            return
            
        visible_options, start_idx = self._get_visible_options()
        self.options_rects = []
        
        # Draw background for entire dropdown area
        dropdown_draw_rect = self.dropdown_rect.move(0, -offset_y)
        pygame.draw.rect(target_surface, gui_config.BUTTON_COLOR, dropdown_draw_rect)
        pygame.draw.rect(target_surface, gui_config.BUTTON_TEXT_COLOR, dropdown_draw_rect, 2)
        
        # Draw visible options
        for i, option in enumerate(visible_options):
            option_y = self.dropdown_rect.y + (i * self.option_height)
            option_rect = pygame.Rect(self.dropdown_rect.x, option_y, self.dropdown_rect.width, self.option_height)
            self.options_rects.append(option_rect)
            
            draw_option_rect = option_rect.move(0, -offset_y)
            
            # Highlight on hover (you'd need to pass mouse pos to implement this)
            pygame.draw.rect(target_surface, gui_config.BUTTON_HOVER_COLOR, draw_option_rect)
            pygame.draw.rect(target_surface, gui_config.BUTTON_TEXT_COLOR, draw_option_rect, 1)
            
            # Draw option text
            option_surface = self.font.render(option, True, gui_config.BUTTON_TEXT_COLOR)
            target_surface.blit(option_surface, (draw_option_rect.x + 5, draw_option_rect.y + 5))
        
        # Draw scrollbar if needed
        if len(self.options) > self.max_visible_options:
            self._draw_scrollbar(target_surface, offset_y)

    def _draw_scrollbar(self, target_surface, offset_y):
        """Draw a scrollbar on the right side of the dropdown."""
        if not self.dropdown_rect:
            return
            
        scrollbar_width = 8
        scrollbar_x = self.dropdown_rect.right - scrollbar_width - 2
        scrollbar_rect = pygame.Rect(scrollbar_x, self.dropdown_rect.y, scrollbar_width, self.dropdown_rect.height)
        scrollbar_draw_rect = scrollbar_rect.move(0, -offset_y)
        
        # Draw scrollbar background
        pygame.draw.rect(target_surface, (200, 200, 200), scrollbar_draw_rect)
        
        # Calculate thumb position and size
        total_options = len(self.options)
        visible_ratio = self.max_visible_options / total_options
        thumb_height = max(10, int(self.dropdown_rect.height * visible_ratio))
        
        scroll_ratio = self.scroll_offset / (total_options - self.max_visible_options) if total_options > self.max_visible_options else 0
        thumb_y = scrollbar_draw_rect.y + int((scrollbar_draw_rect.height - thumb_height) * scroll_ratio)
        
        thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
        pygame.draw.rect(target_surface, (100, 100, 100), thumb_rect)