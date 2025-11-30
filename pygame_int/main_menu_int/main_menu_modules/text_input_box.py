import pygame

from ....pygame_int import gui_config


class TextInputBox:
    """A simple class for handling text input boxes with multi-line support and text wrapping."""
    def __init__(self, x, y, w, h, font, key, default_text='', allow_newlines=False, text_inputs=None, active_element=None): # Added allow_newlines
        self.rect = pygame.Rect(x, y, w, h)
        self.key = key
        self.color = gui_config.INPUT_BOX_BORDER_COLOR
        self.active_color = gui_config.ACTIVE_INPUT_BOX_BORDER_COLOR
        self.text = default_text
        self.font = font
        self.active = False

        self.active_element = active_element
        
        self.max_width = w  # The maximum width the text box can be
        self.min_height = h # The minimum height of the text box
        self.line_height = self.font.get_height() + 2 # Add a little padding between lines
        self.text_padding = 5 # Padding inside the text box for text
        self.allow_newlines = allow_newlines # Store the new parameter
        
        self.rendered_lines = [] # Stores (surface, text_string) for each rendered line
        self._render_text() # Initial rendering and height adjustment
        self.validation_error =False
        text_inputs[self.key] = self

    def _render_text(self):
        """Renders the text, handling newlines and wrapping within max_width."""
        self.rendered_lines = []
        # If newlines are not allowed, replace them with spaces for rendering purposes
        text_to_render = self.text if self.allow_newlines else self.text.replace('\n', ' ')
        lines_from_input = text_to_render.split('\n')
        
        for line_text in lines_from_input:
            words = line_text.split(' ')
            current_line_words = []
            current_line_width = 0
            
            for word in words:
                # Test if adding the next word (plus a space if not the first word) exceeds max_width
                test_line = " ".join(current_line_words + [word])
                test_width, _ = self.font.size(test_line)
                
                if test_width <= self.max_width - (2 * self.text_padding):
                    current_line_words.append(word)
                else:
                    # If current_line_words is not empty, render it
                    if current_line_words:
                        rendered_surface = self.font.render(" ".join(current_line_words), True, gui_config.INPUT_TEXT_COLOR)
                        self.rendered_lines.append(rendered_surface)
                    # Start a new line with the current word
                    current_line_words = [word]
            
            # Render any remaining words in current_line_words
            if current_line_words:
                rendered_surface = self.font.render(" ".join(current_line_words), True, gui_config.INPUT_TEXT_COLOR)
                self.rendered_lines.append(rendered_surface)
            elif not words and line_text == '': # Handle empty lines (e.g., just a newline character)
                empty_line_surface = self.font.render("", True, gui_config.INPUT_TEXT_COLOR)
                self.rendered_lines.append(empty_line_surface)
        
        # Calculate new height based on rendered lines
        new_height = max(self.min_height, len(self.rendered_lines) * self.line_height + (2 * self.text_padding))
        self.rect.h = new_height
        self.rect.w = self.max_width # Ensure width remains fixed

    def handle_event(self, event, adjusted_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # global active_element
            if self.rect.collidepoint(adjusted_pos):
                self.validation_error=False

                self.active = True
                self.active_element = self
            else:
                self.active = False
                if self.active_element == self:
                    self.active_element = None
            self.color = self.active_color if self.active else gui_config.INPUT_BOX_BORDER_COLOR
            
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN and self.allow_newlines: # Only add newline if allowed
                self.text += '\n'
            elif event.unicode and event.unicode.isprintable(): # Allow most printable characters
                self.text += event.unicode
            
            self._render_text() # Re-render text after modification

    def draw(self, target_surface, offset_y):
        draw_rect = self.rect.move(0, -offset_y)
        pygame.draw.rect(target_surface, gui_config.INPUT_BOX_BACKGROUND_COLOR, draw_rect)
        border_color= (255,0,0) if self.validation_error else self.color
        pygame.draw.rect(target_surface, border_color, draw_rect, 2)
        
        y_offset_for_text = draw_rect.y + self.text_padding
        for line_surface in self.rendered_lines:
            target_surface.blit(line_surface, (draw_rect.x + self.text_padding, y_offset_for_text))
            y_offset_for_text += self.line_height
