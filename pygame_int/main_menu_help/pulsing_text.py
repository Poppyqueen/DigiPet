import math
import pygame
class PulsingText:
    """A helper to draw text that fades in and out indefinitely and can be updated."""
    def __init__(self, text, font, position, color=(255, 255, 0), ang_velocity=0.004):
        self.font = font
        self.position = position
        self.color = color
        self.visible = False  # Start hidden by default
        self.text = text
        self.start_time_ms = pygame.time.get_ticks()
        self.ang_velocity= ang_velocity

        self._render_text()

    def _render_text(self):
        """Internal helper to render the text surface and update its rectangle."""
        self.surface = self.font.render(self.text, True, self.color)
        self.rect = self.surface.get_rect(center=self.position)

    def update_text(self, new_text):
        """Updates the text content and re-renders the surface."""
        if self.text != new_text:
            self.text = new_text
            self._render_text()

    def draw(self, screen):
        """Draw the text with its current alpha, which pulses using a sine wave, if visible."""
        if not self.visible or not self.text:
            return
            
        elapsed_time = pygame.time.get_ticks() - self.start_time_ms
        
        # Use a sine wave to create a smooth pulse from 0 to 255 and back
        alpha = (math.sin(elapsed_time * self.ang_velocity) + 1) / 2 * 255
        self.surface.set_alpha(int(alpha))
        
        screen.blit(self.surface, self.rect)

    def show(self):
        """Makes the text visible."""
        self.visible = True

    def hide(self):
        """Hides the text."""
        self.visible = False