import pygame
import numpy as np
import random
import time
from sky_sim import NightSkySimulator, render_snapshot
from sky_sim.cloud_sim import _sky_to_xy
from utils.open_meteo_handle import OpenMeteoLoc

from utils.loc_datetime import CoordinateDateTime



# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOCATIONS = {
    "Anacapa Island, USA": {
        "lat": 34.0167, 
        "lon": -119.45, 
        "bortle": 2
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
    "Amazon Rainforest, Braczil": {
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
    }
}

WIDTH, HEIGHT = 600, 600 # Slightly larger for better visibility
FPS = 60


# SIM_TICK_TIME = 5.0  
# REAL_TIME_WAIT = 5 * 60 * 1000 

SIM_TICK_TIME = 0.25            # 1 minute passes
REAL_TIME_WAIT = 15 * 1000      # Every 60 seconds

SPACE_BLACK = (11, 13, 23)
STAR_GOLD = (255, 215, 0)
HORIZON_CYAN = (0, 255, 255)
CLOUD_WHITE = (200, 200, 220)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sky_to_pixel(az, alt):
    sx, sy = _sky_to_xy(az, alt)
    px = int(WIDTH / 2 + sx * (WIDTH / 2.5))
    py = int(HEIGHT / 2 - sy * (HEIGHT / 2.5))
    return px, py

def create_cloud_surface(sim, grid_res=80):
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cell_size = WIDTH // grid_res
    x_range = np.linspace(-1.1, 1.1, grid_res)
    y_range = np.linspace(-1.1, 1.1, grid_res)
    for i, x in enumerate(x_range):
        for j, y in enumerate(y_range):
            if np.sqrt(x**2 + y**2) <= 1.0:
                low = sim._clouds._low.opacity_at(x, y)
                mid = sim._clouds._mid.opacity_at(x, y)
                high = sim._clouds._high.opacity_at(x, y)
                opacity = 1.0 - (1.0 - low) * (1.0 - mid) * (1.0 - high)
                if opacity > 0.1:
                    alpha = int(opacity * 180)
                    pygame.draw.rect(surf, (*CLOUD_WHITE, alpha), (i * cell_size, (grid_res - j - 1) * cell_size, cell_size, cell_size))
    return surf

def print_extensive_report(name, snap, sim):
    """Restores the detailed terminal logging from the original demo."""
    print(f"\n{'-'*60}")
    print(f"📡 EXPEDITION LOG: {name}")
    print(f"⏰ Local Time: {snap.local_time}")
    print(f"📍 Coordinates: {sim.lat}, {sim.lon}")
    print(f"{'-'*60}")
    
    # Cloud Data
    print(f"☁️  WEATHER & ATMOSPHERE")
    print(f"   Sky Condition: {'Clear' if snap.cloud_coverage_simulated < 0.2 else 'Partly Cloudy' if snap.cloud_coverage_simulated < 0.7 else 'Overcast'}")
    print(f"   Total Cloud Coverage: {snap.cloud_coverage_simulated*100:.1f}%")
    print(f"   Bortle Scale: Class {sim.bortle_class}")
    
    # Astronomical Data
    print(f"✨ STELLAR POOL")
    print(f"   Visible Stars: {len(snap.stars_visible)}")
    print(f"   Obscured Stars: {len(snap.stars_obscured)}")
    print(f"   Moon Status: {'Visible' if snap.moon.above_horizon else 'Below Horizon'}")
    if snap.moon.above_horizon:
        print(f"   Moon Position: Az {snap.moon.azimuth:.1f}°, Alt {snap.moon.altitude:.1f}°")
    
    # DEETS
    print(f"\n{render_snapshot(snap)}")
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

    print(f"Initializing connection to {name}...")
    time_manager = CoordinateDateTime(info['lat'], info['lon'])
    weath = OpenMeteoLoc(info['lat'], info['lon'])
    sim = NightSkySimulator(
        lat=info['lat'], lon=info['lon'], 
        weather_provider=weath, 
        bortle_class=info['bortle'],
        noise_seed=random.randrange(1, 999999)
    )
    
    # First Update
    current_snap = sim.snapshot()
    cloud_tex = create_cloud_surface(sim)
    print_extensive_report(name, current_snap, sim)
    
    last_tick_time = pygame.time.get_ticks()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        now = pygame.time.get_ticks()
        if now - last_tick_time > REAL_TIME_WAIT:
            sim.tick(minutes=SIM_TICK_TIME)
            current_snap = sim.snapshot()
            cloud_tex = create_cloud_surface(sim)
            print_extensive_report(name, current_snap, sim) # Log back to terminal
            last_tick_time = now

        # --- DRAWING (Corrected Layers) ---
        screen.fill(SPACE_BLACK)
        all_stars = current_snap.stars_visible + current_snap.stars_obscured

        # Layer 4: Gray Pool
        for s in all_stars:
            if not s.visible and not s.obscured_by_cloud:
                pos = sky_to_pixel(s.azimuth, s.altitude)
                pygame.draw.circle(screen, (50, 50, 60), pos, 1)

        # Layer 3: Red Stars
        for s in all_stars:
            if s.obscured_by_cloud: # Something here weirds me out, not sure if it is a display issue, or a simulation one, but i think my worry is tied to OBSCURED BY CLOUD, what i don't understand is the difference between these and the gray pool, i assumed these obsured ones are the ones that are possibly visible in the location, however they have a cloud on top, however, as the clouds moves away from them, these are not highlighted as visible, probably because they are not actually visible with the naked eye on that location, they are on the horizon, and covered by clouds, but aren't visible in the sky, that's what's confusing that stars that at one point are "covered by clouds", when they move away, they are discovered as not observable. it is not that we want to change the who is visible calculation, but maybe define correctly what they mean. weirdest part is that not all covered stars are red, not sure what's going on
                pos = sky_to_pixel(s.azimuth, s.altitude)
                pygame.draw.circle(screen, (180, 40, 40), pos, 2) # these should be "these are possibly visible but right now covered", not "these exist and are covered right now"

        # Layer 2: Yellow Stars
        for s in all_stars:
            if s.visible: # these are the visible stars that passed all our checks
                pos = sky_to_pixel(s.azimuth, s.altitude)
                size = max(2, int(6.5 - s.magnitude) * 2)
                pygame.draw.circle(screen, STAR_GOLD, pos, size)
# --- NEW LAYER: PLANETS ---
        for p in current_snap.planets:
            # Type Check: PlanetResult uses altitude (float)
            if p.altitude > 0: 
                pos = sky_to_pixel(p.azimuth, p.altitude)
                
                # Type Check: p.visible is a bool in PlanetResult
                if p.visible:
                    # Draw a solid circle for visible planets
                    size = max(3, int(7.0 - p.magnitude))
                    pygame.draw.circle(screen, (240, 240, 255), pos, size)
                    
                    planet_lbl = font.render(p.name, True, (200, 200, 200))
                    screen.blit(planet_lbl, (pos[0] + 5, pos[1] + 5))
                
                # Type Check: p.obscured_by_cloud is a bool in PlanetResult
                elif p.obscured_by_cloud:
                    pygame.draw.circle(screen, (80, 20, 20), pos, 2)

        # --- NEW LAYER: THE MOON ---
        m = current_snap.moon
        # Type Check: MoonResult uses above_horizon (bool)
        if m.above_horizon:
            m_pos = sky_to_pixel(m.azimuth, m.altitude)
            
            # Simple color logic based on m.altitude (float)
            if m.altitude < 15:
                moon_color = (255, 180, 50) 
            elif m.altitude < 30:
                moon_color = (255, 255, 200)
            else:
                moon_color = (240, 240, 240)
            
            # Draw the Moon disk
            pygame.draw.circle(screen, moon_color, m_pos, 10)

            # Label using m.phase_name (str) and m.illumination (float)
            moon_text = f"{m.phase_name} ({int(m.illumination*100)}%)"
            moon_lbl = font.render(moon_text, True, moon_color)
            screen.blit(moon_lbl, (m_pos[0] + 12, m_pos[1] - 10))

        # Layer 1: Clouds (Drawn last, naturally obscuring everything beneath)
        screen.blit(cloud_tex, (0, 0))

        # Overlays
        center, radius = (WIDTH // 2, HEIGHT // 2), int(WIDTH / 2.5)
        pygame.draw.circle(screen, HORIZON_CYAN, center, radius, 1)

        # UI

        formatted_time = time_manager.strftime("%Y-%m-%d | %I:%M %p")

        time_lbl = font.render(f"OBSERVATORY TIME: {formatted_time}", True, (0, 255, 0))
        coord_lbl = font.render(f"LOC: {info['lat']}, {info['lon']}", True, (0, 200, 255))
        cloud_lbl = font.render(f"CLOUDS: {current_snap.cloud_coverage_simulated*100:.1f}%", True, (0, 255, 0))

        screen.blit(time_lbl, (15, 15))
        screen.blit(coord_lbl, (15, 35))
        screen.blit(cloud_lbl, (15, 55))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

def select_location():
    print("--- AVAILABLE OBSERVATORIES ---")
    loc_list = list(LOCATIONS.keys())
    for i, name in enumerate(loc_list, 1):
        print(f"[{i}] {name}")
    choice = int(input("\nSelect a location number: "))
    return loc_list[choice-1], LOCATIONS[loc_list[choice-1]]

if __name__ == "__main__":
    name, info = select_location()
    run_pygame_expedition(name, info)