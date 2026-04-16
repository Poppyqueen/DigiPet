# tools/tools_folder/tools_helpers/outdoors_helpers/sky_sim/demo_sky.py
# python -m tools.tools_folder.tools_helpers.outdoors_helpers.sky_sim.demo_sky
# !!!!

import pygame
import numpy as np
import random
import time

from . import NightSkySimulator, render_snapshot, SkyLogger
from .cloud_sim import _sky_to_xy
from .types import SkySnapshot, VisibilityState, TwilightPhase, EclipseType, EclipsePhase

from utils.open_meteo_handle import OpenMeteoLoc
import math
import os

def clear_screen():
    # For Windows (os.name is 'nt')
    if os.name == 'nt':
        _ = os.system('cls')
    # For macOS and Linux (os.name is 'posix')
    else:
        _ = os.system('clear')


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOCATIONS = {
    "Anacapa Island, USA": {
        "lat": 34.0167, 
        "lon": -119.45, 
        "bortle": 3
    },
    "Mexico City": {
        "lat": 19.4326,
        "lon": -99.1332,
        "bortle": 9  # Inner City
    },
    "Cape Spencer Light (Alaska)":{
        "lat": 58.19891, 
        "lon": -136.64018, 
        "bortle": 1      
    },
    "London, UK": {
        "lat": 51.5074, 
        "lon": -0.1278, 
        "bortle": 9  # Heavy light pollution
    },
    "Cairo, Egypt": {
        "lat": 30.0444, 
        "lon": 31.2357, 
        "bortle": 9  # Very bright urban center
    },
    "Amazon Rainforest, Brazil": {
        "lat": -3.4653, 
        "lon": -62.2159, 
        "bortle": 1  # True pristine wilderness
    },
    "Yeongyang-gun, South Korea": {
        "lat": 36.6667, 
        "lon": 129.1167, 
        "bortle": 2  # Firefly Eco Park (one of the darkest spots in Korea)
    },
    "Bordeaux, France": {
        "lat": 44.8378,
        "lon": -0.5792,
        "bortle": 8
    },
    "Mount Kilimanjaro, Tanzania": {
        "lat": -3.07583,
        "lon": 37.35333,
        "bortle": 1
    },
    "Tibetan Plateau (Ngari), China": {
        "lat": 32.5000,
        "lon": 80.1000,
        "bortle": 1  # High-altitude pristine dark sky
    },
    "Sydney, Australia": {
        "lat": -33.8688,
        "lon": 151.2093,
        "bortle": 7  # Suburban/urban transition (can reach 8-9 in CBD)
    },
    "Nauru (Central Pacific)": {
        "lat": -0.5228,
        "lon": 166.9315,
        "bortle": 2  # Exceptionally dark, influenced by minor local glow
    },
    "Paranal Observatory, Chile": {
        "lat": -24.6275, 
        "lon": -70.4045, 
        "bortle": 1,
},
    "Tokyo, Japan": {
        "lat": 35.6762, 
        "lon": 139.6503, 
        "bortle": 8,  # Bright city, but we're looking for planets!
    },
    "NamibRand Nature Reserve, Namibia": {
        "lat": -24.9610, 
        "lon": 15.9125, 
        "bortle": 1,
    },
    "North Pole": {
        "lat": 89.999, 
        "lon": 0.0000, 
        "bortle": 1  # Total darkness (during polar night), no local light pollution
    },
    "Asturias, Spain":
    {
        "lat": 43.250476,
        "lon": -5.983295,
        "bortle": 3

# 65.502707°N 24.531688°W
    },
    "Látrabjarg, Iceland":
    {
        "lat": 65.502707,
        "lon": -24.531688,
        "bortle": 1
    }
}

WIDTH, HEIGHT = 600, 600
FPS = 60

SIM_TICK_TIME = 0.25            # 15 seconds sim time
REAL_TIME_WAIT = 15 * 1000      # Every 15 real seconds

STAR_GOLD = (255, 215, 0)
HORIZON_CYAN = (0, 255, 255)
CLOUD_WHITE = (200, 200, 220)


UI_GREEN = (0, 255, 0)
UI_BLUE = (0, 200, 255)


# --- Enhanced Color Palette ---
ECLIPSE_GOLD = (255, 255, 180)
BLOOD_MOON = (138, 3, 3)      # Deep umbral red
PENUMBRA_GRAY = (100, 100, 110)
HUD_ALERT = (255, 100, 0)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sky_to_pixel(az, alt):
    """
    Maps Azimuth/Altitude to Pygame screen coordinates.
    
    Convention: North up, East left (standard sky-chart orientation —
    because you're looking UP, East/West are mirrored vs a map).
    
    Az 0° (N) → top center
    Az 90° (E) → left center
    Az 180° (S) → bottom center
    Az 270° (W) → right center
    """
    sx, sy = _sky_to_xy(az, alt)

    # _sky_to_xy gives:  x = r*cos(az),  y = r*sin(az)
    # with az measured East-of-North.
    # cos(0°)=1 → x=r, so North lands at screen-right. Wrong.
    #
    # Sky chart fix:
    #   • Rotate -90° so North goes to top:  x' = y,  y' = -x
    #   • Mirror East (negate new x):         x'' = -y
    #   This gives: screen_x = -sy,  screen_y = -sx
    screen_x = -sy
    screen_y = -sx

    px = int(WIDTH / 2 + screen_x * (WIDTH / 2.5))
    py = int(HEIGHT / 2 + screen_y * (HEIGHT / 2.5))   # note: + not -, because y' is already flipped
    return px, py

def draw_cardinal_labels(screen, font):
    """Draws N/E/S/W labels just outside the horizon circle."""
    center_x, center_y = WIDTH // 2, HEIGHT // 2
    radius = int(WIDTH / 2.5)
    offset = 18  # pixels outside the circle edge

    cardinals = {
        "N": (center_x,             center_y - radius - offset),
        "S": (center_x,             center_y + radius + offset),
        "E": (center_x - radius - offset, center_y),   # East is LEFT
        "W": (center_x + radius + offset, center_y),
    }

    label_color = (0, 200, 255)  # cyan, same as horizon ring
    for letter, (lx, ly) in cardinals.items():
        lbl = font.render(letter, True, label_color)
        rect = lbl.get_rect(center=(lx, ly))
        screen.blit(lbl, rect)

def create_cloud_surface(sim, grid_res=80):
    """Generates a semi-transparent cloud overlay correctly mapped to the sky dome projection."""
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    # Calculate float cell sizes and use ceil to prevent visual seams 
    # (WIDTH // grid_res leaves a blank margin if WIDTH doesn't divide perfectly)
    cell_w = WIDTH / grid_res
    cell_h = HEIGHT / grid_res
    
    C_HIGH = (0, 100, 255)   # Vibrant Blue
    C_MID  = (255, 215, 0)   # Golden Yellow
    C_LOW  = (200, 30, 30)   # Deep Red

    for i in range(grid_res):
        for j in range(grid_res):
            # 1. Find the center pixel coordinate of this grid cell
            px = i * cell_w + cell_w / 2
            py = j * cell_h + cell_h / 2
            
            # 2. Invert the sky_to_pixel() mapping logic
            # px = WIDTH / 2 + screen_x * (WIDTH / 2.5) -> Solve for screen_x
            screen_x = (px - WIDTH / 2) / (WIDTH / 2.5)
            screen_y = (py - HEIGHT / 2) / (HEIGHT / 2.5)
            
            # 3. Invert the 90° rotation and mirroring from sky_to_pixel()
            # screen_x = -sy  =>  sy = -screen_x
            # screen_y = -sx  =>  sx = -screen_y
            sx = -screen_y
            sy = -screen_x
            
            # 4. The sky dome is a circle of radius 1.0; only process inside it
            if (sx**2 + sy**2) <= 1.0:
                # Sample using the correctly projected Cartesian coordinates
                low = sim._clouds._low.opacity_at(sx, sy)
                mid = sim._clouds._mid.opacity_at(sx, sy)
                high = sim._clouds._high.opacity_at(sx, sy)
                
                total = low + mid + high
                if total > 0:
                    r = (C_HIGH[0]*high + C_MID[0]*mid + C_LOW[0]*low) / total
                    g = (C_HIGH[1]*high + C_MID[1]*mid + C_LOW[1]*low) / total
                    b = (C_HIGH[2]*high + C_MID[2]*mid + C_LOW[2]*low) / total
                    
                    # Compute combined opacity exactly like the simulation's classifier
                    opacity = 1.0 - (1.0 - low) * (1.0 - mid) * (1.0 - high)
                    
                    if opacity > 0.1:
                        alpha = int(opacity * 180)
                        # Draw cleanly on the surface
                        rect = pygame.Rect(int(i * cell_w), int(j * cell_h), 
                                           math.ceil(cell_w), math.ceil(cell_h))
                        pygame.draw.rect(surf, (int(r), int(g), int(b), alpha), rect)
                        
    return surf

def get_eclipse_color(base_color, eclipse_res):
    """Calculates the Moon's color based on its depth into Earth's shadow."""
    if eclipse_res.eclipse_type != EclipseType.LUNAR:
        return base_color
    
    # umbral_depth > 0 means we are in the dark part of the shadow
    # 0.0 to 1.0+ is the transition from 'bite taken out' to 'Blood Moon'
    if eclipse_res.umbral_depth <= 0:
        return base_color
    
    # Blend between white and deep red based on umbral depth
    lerp = min(1.0, eclipse_res.umbral_depth)
    r = base_color[0] + (BLOOD_MOON[0] - base_color[0]) * lerp
    g = base_color[1] + (BLOOD_MOON[1] - base_color[1]) * lerp
    b = base_color[2] + (BLOOD_MOON[2] - base_color[2]) * lerp
    return (int(r), int(g), int(b))

def render_eclipse_hud(screen, font, snap: SkySnapshot):
    """Draws a detailed technical readout when an eclipse is active."""
    e = snap.eclipse
    if e.eclipse_type == EclipseType.NONE or not e.visible_from_here:
        return
    
    hud_y = screen.get_height() - 80

    # Create a blinking alert effect
    alpha = int(155 + 100 * math.sin(pygame.time.get_ticks() * 0.005))
    alert_color = (*HUD_ALERT, alpha)
    
    header = f"*** {e.eclipse_type.value.upper()} ECLIPSE DETECTED ***"
    phase_str = f"Phase: {e.phase.value.title()} | Obscuration: {e.obscuration*100:.1f}%"
    note_str = f"Note: {e.note}"

    # Draw background plate for readability
    overlay = pygame.Surface((350, 80), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (WIDTH // 2 - 175, hud_y))

    render_h = font.render(header, True, HUD_ALERT)
    render_p = font.render(phase_str, True, (255, 255, 255))
    render_n = font.render(note_str, True, (200, 200, 200))

# Draw text relative to hud_y (offsetting by 5, 25, and 45 pixels)
    screen.blit(render_h, (WIDTH // 2 - render_h.get_width() // 2, hud_y + 5))
    screen.blit(render_p, (WIDTH // 2 - render_p.get_width() // 2, hud_y + 25))
    screen.blit(render_n, (WIDTH // 2 - render_n.get_width() // 2, hud_y + 45))

# def get_moon_phase_name(angle: float) -> str:
#     if angle < 1 or angle >= 359: return "New Moon"
#     if angle < 89: return "Waxing Crescent"
#     if angle < 91: return "First Quarter"
#     if angle < 179: return "Waxing Gibbous"
#     if angle < 181: return "Full Moon"
#     if angle < 269: return "Waning Gibbous"
#     if angle < 271: return "Last Quarter"
#     return "Waning Crescent"

def print_extensive_report(name, snap: SkySnapshot):
    print(f"\n{'-'*60}")
    print(f"📡 EXPEDITION LOG: {name}")
    print(f"⏰ Local Time: {snap.local_time}")
    print(f"📍 {snap.latitude}, {snap.longitude}")
    print(f"{'-'*60}")
    
    # Updated to handle Enums
    status_text = snap.condition.value.replace('_', ' ').upper()
    print(f"☁️  CONDITIONS: {status_text}")
    print(f"   Bortle: Class {snap.bortle_class.value} | Limit: {snap.limiting_magnitude:.2f} mag")
    
    print(f"✨ STELLAR POOL")
    print(f"   Visible: {snap.total_stars_visible}")
    print(f"   Blocked by Clouds: {len(snap.stars_clouded)}")
    print(f"   Below Horizon: {snap.stars_above_horizon} total above")
    
    print(f"\n{render_snapshot(snap, compact=True)}")
    print(f"{'-'*60}\n")

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
def run_pygame_expedition(name, info):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Sky Sim: {name}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier", 16, bold=True)

    print(f"Connecting to {name}...")
    weath = OpenMeteoLoc(info['lat'], info['lon'])
    elev = weath.get_elevation()
    
    sim = NightSkySimulator(
        lat=info['lat'], lon=info['lon'], 
        weather_provider=weath, 
        bortle_class=info['bortle'],
        noise_seed=random.randrange(1, 999999),
        elevation_m=elev
    )
    
    # Initialize snapshot and cloud texture
# 1. Initialize the logger
    logger = SkyLogger(name)
    
    # Initialize snapshot
    snap = sim.snapshot()
    cloud_tex = create_cloud_surface(sim)
    
    # 2. Log the initial state
    #print_extensive_report(name, snap) # Keep console print if you like
    logger.log_snapshot(name, snap)    # Write to file
    
    last_tick_time = pygame.time.get_ticks()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        now = pygame.time.get_ticks()
        if now - last_tick_time > REAL_TIME_WAIT:
            #clear_screen()
            sim.tick()
            snap = sim.snapshot() 
            cloud_tex = create_cloud_surface(sim)
            logger.log_snapshot(name, snap)
            #print_extensive_report(name, snap)
            last_tick_time = now

        # --- DYNAMIC BACKGROUND (Using New SunResult/TwilightPhase Enum) ---
        phase = snap.sun.twilight_phase

        # Base background selection
        if phase == TwilightPhase.DAY: bg_color = [135, 206, 235]
        elif phase == TwilightPhase.CIVIL_TWILIGHT: bg_color = [70, 100, 160]
        elif phase == TwilightPhase.NAUTICAL_TWILIGHT: bg_color = [30, 40, 80]
        else: bg_color = [11, 13, 23]

        # Solar Eclipse "False Night" effect
        if snap.eclipse.eclipse_type == EclipseType.SOLAR and snap.eclipse.obscuration > 0:
            # As obscuration reaches 1.0, sky color lerps toward Night (Space Black)
            obs = snap.eclipse.obscuration
            target = [11, 13, 23]
            bg_color[0] += (target[0] - bg_color[0]) * (obs ** 2) # Exponential darkening
            bg_color[1] += (target[1] - bg_color[1]) * (obs ** 2)
            bg_color[2] += (target[2] - bg_color[2]) * (obs ** 2)

        screen.fill(tuple(bg_color))

        # 1. Background Stars (Too dim/limit)
        for s in snap.stars_below_limit:
            pos = sky_to_pixel(s.azimuth, s.altitude)
            pygame.draw.circle(screen, (40, 42, 50), pos, 1)

        # 2. Clouded Stars (Red)
        for s in snap.stars_clouded:
            pos = sky_to_pixel(s.azimuth, s.altitude)
            pygame.draw.circle(screen, (150, 30, 30), pos, 2)

        # 3. Visible Stars (Gold)
        for s in snap.stars_visible:
            pos = sky_to_pixel(s.azimuth, s.altitude)
            # Size based on catalog magnitude
            size = max(1, int(6.5 - s.magnitude))
            pygame.draw.circle(screen, STAR_GOLD, pos, size)

        # 4. Planets
        # --- PLANETS (Pygame) ---
        for p in snap.planets:
            # Get screen coordinates
            pos = sky_to_pixel(p.azimuth, p.altitude)
            
            if p.visibility == VisibilityState.VISIBLE:
                # Calculate size: brighter planets get larger circles
                size = max(3, int(8.0 - p.magnitude))
                pygame.draw.circle(screen, (255, 255, 255), pos, size)
                
                # Render the name label
                lbl = font.render(p.name, True, (240, 240, 240))
                screen.blit(lbl, (pos[0] + 5, pos[1] + 5))
                
            elif p.visibility == VisibilityState.CLOUDED:
                # Draw a small "clouded out" indicator
                pygame.draw.circle(screen, (100, 20, 20), pos, 2)
                
            elif p.visibility == VisibilityState.BELOW_LIMIT:
                # Optional: Draw a very faint dot for planets that are up but too dim
                pygame.draw.circle(screen, (40, 40, 40), pos, 1)
        # 5. Sun
# --- 2. ENHANCED SUN RENDERING ---
        sun = snap.sun
        if sun.altitude > -2 and sun.visibility == VisibilityState.VISIBLE: 
            s_pos = sky_to_pixel(sun.azimuth, sun.altitude)
            e = snap.eclipse
            
            if e.eclipse_type == EclipseType.SOLAR:
                # Draw the Corona (Glow)
                corona_size = 22 + int(5 * math.sin(pygame.time.get_ticks() * 0.01))
                pygame.draw.circle(screen, (255, 255, 255, 100), s_pos, corona_size)
                
                # Draw the Sun base
                pygame.draw.circle(screen, (255, 220, 100), s_pos, 20)
                
                # Draw the Moon "Shadow" blocking the sun
                # We offset it based on separation_deg (scaled for pixels)
                # 0.5 degrees is roughly the diameter of the sun
                offset_px = (e.separation_deg / 0.5) * 20 
                # For simplicity, we assume the moon is moving horizontally across the sun
                m_shadow_pos = (s_pos[0] + offset_px, s_pos[1])
                pygame.draw.circle(screen, tuple(bg_color), m_shadow_pos, 20)
                
                # Total Eclipse "Diamond Ring" / Baily's Beads effect
                if e.phase == EclipsePhase.TOTAL:
                    pygame.draw.circle(screen, (255, 255, 255), s_pos, 21, 2)
            else:
                pygame.draw.circle(screen, (255, 220, 100), s_pos, 20)
                pygame.draw.circle(screen, (255, 255, 200), s_pos, 16)

        # 6. Moon
# --- 3. ENHANCED MOON RENDERING (Lunar Eclipse) ---
        m = snap.moon
        if m.above_horizon and m.visibility == VisibilityState.VISIBLE:
            m_pos = sky_to_pixel(m.azimuth, m.altitude)
            
            # Atmospheric reddening at low altitude OR Lunar Eclipse depth
            base_moon = (240, 240, 240) if m.altitude > 15 else (255, 180, 100)
            final_moon_color = get_eclipse_color(base_moon, snap.eclipse)
            
            pygame.draw.circle(screen, final_moon_color, m_pos, 12)
            
            # Label
            trend = "Waxing" if m.waxing else "Waining"
            if snap.eclipse.eclipse_type == EclipseType.LUNAR:
                trend = f"ECLIPSED {trend}"
            
            moon_lbl = font.render(f"{trend} ({int(m.illumination*100)}%)", True, final_moon_color)
            screen.blit(moon_lbl, (m_pos[0] + 15, m_pos[1] - 10))

        # 7. Cloud Overlay
        screen.blit(cloud_tex, (0, 0))
    
        # UI Overlays
        center, radius = (WIDTH // 2, HEIGHT // 2), int(WIDTH / 2.5)
        pygame.draw.circle(screen, HORIZON_CYAN, center, radius, 1)
        draw_cardinal_labels(screen, font)
        render_eclipse_hud(screen, font, snap)


        # Legend/Stats
        time_lbl  = font.render(f"TIME: {snap.local_time}", True, UI_GREEN)
        coord_lbl = font.render(f"LOC:  {snap.latitude:.2f}, {snap.longitude:.2f}", True, UI_BLUE)
        cloud_lbl = font.render(f"CLD:  {snap.cloud_coverage_simulated*100:.1f}%", True, (200, 200, 255))
        mag_lbl   = font.render(f"MAG:  {snap.limiting_magnitude:.2f} limit", True, STAR_GOLD)

        screen.blit(time_lbl, (15, 15))
        screen.blit(coord_lbl, (15, 35))
        screen.blit(cloud_lbl, (15, 55))
        screen.blit(mag_lbl, (15, 75))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

def select_location():
    loc_list = list(LOCATIONS.keys())
    page_size = 7
    current_page = 0
    total_pages = (len(loc_list) + page_size - 1) // page_size

    while True:
        clear_screen()
        print(f"\n--- AVAILABLE OBSERVATORIES (Page {current_page + 1}/{total_pages}) ---")
        
        # Calculate start and end indices for the current page
        start = current_page * page_size
        end = start + page_size
        page_items = loc_list[start:end]

        for i, name in enumerate(page_items, 1):
            print(f"[{i}] {name}")

        print("-" * 30)
        print("[N] Next Page  |  [P] Previous Page")
        print("[C] Add Custom Location")
        
        choice = input("\nSelect a number, navigate, or add custom: ").strip().upper()

        # 1. Handle Navigation
        if choice == 'N':
            if current_page < total_pages - 1:
                current_page += 1
            else:
                print(">> You are on the last page.")
            continue
        
        if choice == 'P':
            if current_page > 0:
                current_page -= 1
            else:
                print(">> You are on the first page.")
            continue

        # 2. Handle Custom Entry
        if choice == 'C':
            try:
                print("\n--- CONSTRUCT CUSTOM ENTRY ---")
                name = input("Location Name: ")
                lat = float(input("Latitude: "))
                lon = float(input("Longitude: "))
                bortle = int(input("Bortle Scale (1-9): "))
                
                custom_data = {"lat": lat, "lon": lon, "bortle": bortle}
                return name, custom_data
            except ValueError:
                print("Invalid input. Returning to menu.")
                continue

        # 3. Handle Numeric Selection
        try:
            idx = int(choice)
            if 1 <= idx <= len(page_items):
                selected_name = page_items[idx - 1]
                return selected_name, LOCATIONS[selected_name]
            else:
                print("Number out of range for this page.")
        except ValueError:
            print("Invalid input. Please choose a number, N, P, or C.")


if __name__ == "__main__":
    name, info = select_location()
    run_pygame_expedition(name, info)