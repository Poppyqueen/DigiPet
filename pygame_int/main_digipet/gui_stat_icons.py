# gui_stat_icons.py

import pygame

from .. import config
from .. import state
from . import gui_core

# Global dictionary to store stat icon rectangles for collision detection
_stat_icon_rects = {}

def get_stat_icon_rects():
    """
    Returns the current stat icon rectangles for collision detection.
    
    Returns:
        dict: Dictionary with stat names as keys and pygame.Rect objects as values
              Format: {"fullness": rect, "hydration": rect, "energy": rect}
    """
    return _stat_icon_rects.copy()

def _get_stat_level(value):
    """Determines the icon level ('full', 'half', 'empty') for a given stat value (0-200)."""
    clamped_value = max(0.0, min(200.0, value)) 

    if clamped_value >= config.STAT_THRESHOLDS['full']:
        return 'full'
    elif clamped_value >= config.STAT_THRESHOLDS['half']:
        return 'half'
    else:
        return 'empty'

def update_stat_icon_rects():
    """
    Updates the stat icon rectangles based on current configuration.
    Should be called when screen layout changes or during initialization.
    """
    global _stat_icon_rects
    
    stats_to_draw_order = ["fullness", "hydration", "energy"]
    icon_start_x = config.STAT_ICON_START_X_SCREEN
    icon_start_y = config.STAT_ICON_START_Y_SCREEN
    icon_width, icon_height = config.STAT_ICON_SIZE
    icon_spacing = config.STAT_ICON_SPACING_Y
    
    _stat_icon_rects.clear()
    
    for i, stat_name in enumerate(stats_to_draw_order):
        icon_draw_y = icon_start_y + i * (icon_height + icon_spacing)
        rect = pygame.Rect(icon_start_x, icon_draw_y, icon_width, icon_height)
        _stat_icon_rects[stat_name] = rect

def draw_stat_icons(screen):
    """
    Draws all stat icons on the screen and updates their collision rectangles.
    If a stat is being hovered (state.hover_stat), displays its value text beside the icon.
    
    Args:
        screen (pygame.Surface): The main display surface to draw on
    """
    # Update rectangles first
    update_stat_icon_rects()
    
    stats_to_draw_order = ["fullness", "hydration", "energy"]
    
    for stat_name in stats_to_draw_order:
        stat_value = state.pet_stats.get(stat_name, 0)
        stat_level = _get_stat_level(stat_value)
        icon_surface = gui_core._stat_icons.get((stat_name, stat_level))
        
        if icon_surface and stat_name in _stat_icon_rects:
            rect = _stat_icon_rects[stat_name]
            screen.blit(icon_surface, (rect.x, rect.y))
            
            # Draw stat value text if this stat is being hovered
            if hasattr(state, 'hover_stat') and state.hover_stat == stat_name:
                if gui_core._font is not None:
                    try:
                        # Format the stat value (round to 1 decimal place)
                        value_text = f"{stat_value:.1f}"
                        
                        # Get text color from theme
                        text_color = getattr(state, 'game_theme_colors', {}).get('contrast_color', config.WHITE)
                        
                        # Render the text
                        text_surface = gui_core._font.render(value_text, True, text_color)
                        
                        # Position text to the right of the icon with some padding
                        text_x = rect.right + 10  # 10 pixels padding from icon
                        text_y = rect.centery - text_surface.get_height() // 2  # Center vertically with icon
                        
                        # Draw a semi-transparent background for better readability
                        text_bg_rect = pygame.Rect(text_x - 2, text_y - 2, 
                                                 text_surface.get_width() + 4, 
                                                 text_surface.get_height() + 4)
                        bg_color = getattr(state, 'game_theme_colors', {}).get('original_pet_color', config.BLACK)
                        # Create a surface with alpha for semi-transparency
                        bg_surface = pygame.Surface((text_bg_rect.width, text_bg_rect.height))
                        bg_surface.set_alpha(128)  # Semi-transparent
                        bg_surface.fill(bg_color)
                        screen.blit(bg_surface, (text_bg_rect.x, text_bg_rect.y))
                        
                        # Draw the text
                        screen.blit(text_surface, (text_x, text_y))
                        
                    except pygame.error as e:
                        print(f"Pygame error rendering stat hover text: {e}")
