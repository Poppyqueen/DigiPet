import pygame
import numpy as np
import random
import time

from sky_sim import NightSkySimulator, render_snapshot
from sky_sim.cloud_sim import _sky_to_xy
from sky_sim.types import SkySnapshot, VisibilityState, TwilightPhase

from utils.open_meteo_handle import OpenMeteoLoc

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
    """Generates a semi-transparent cloud overlay from simulation noise."""
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cell_size = WIDTH // grid_res
    x_range = np.linspace(-1.1, 1.1, grid_res)
    y_range = np.linspace(-1.1, 1.1, grid_res)
    
    C_HIGH = (230, 240, 255) 
    C_MID  = (210, 210, 210) 
    C_LOW  = (120, 120, 130) 

    for i, x in enumerate(x_range):
        for j, y in enumerate(y_range):
            if np.sqrt(x**2 + y**2) <= 1.0:
                low = sim._clouds._low.opacity_at(x, y)
                mid = sim._clouds._mid.opacity_at(x, y)
                high = sim._clouds._high.opacity_at(x, y)
                
                total = low + mid + high
                if total > 0:
                    r = (C_HIGH[0]*high + C_MID[0]*mid + C_LOW[0]*low) / total
                    g = (C_HIGH[1]*high + C_MID[1]*mid + C_LOW[1]*low) / total
                    b = (C_HIGH[2]*high + C_MID[2]*mid + C_LOW[2]*low) / total
                    
                    opacity = 1.0 - (1.0 - low) * (1.0 - mid) * (1.0 - high)
                    if opacity > 0.1:
                        alpha = int(opacity * 180)
                        pygame.draw.rect(surf, (int(r), int(g), int(b), alpha), 
                                        (i * cell_size, (grid_res - j - 1) * cell_size, cell_size, cell_size))
    return surf

def get_moon_phase_name(angle: float) -> str:
    if angle < 1 or angle >= 359: return "New Moon"
    if angle < 89: return "Waxing Crescent"
    if angle < 91: return "First Quarter"
    if angle < 179: return "Waxing Gibbous"
    if angle < 181: return "Full Moon"
    if angle < 269: return "Waning Gibbous"
    if angle < 271: return "Last Quarter"
    return "Waning Crescent"

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
    snap = sim.snapshot()
    cloud_tex = create_cloud_surface(sim)
    print_extensive_report(name, snap)
    
    last_tick_time = pygame.time.get_ticks()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        now = pygame.time.get_ticks()
        if now - last_tick_time > REAL_TIME_WAIT:
            sim.tick(minutes=SIM_TICK_TIME)
            snap = sim.snapshot() 
            cloud_tex = create_cloud_surface(sim)
            print_extensive_report(name, snap)
            last_tick_time = now

        # --- DYNAMIC BACKGROUND (Using New SunResult/TwilightPhase Enum) ---
        phase = snap.sun.twilight_phase
        if phase == TwilightPhase.DAY:
            bg_color = (135, 206, 235)  # Sky blue
        elif phase == TwilightPhase.CIVIL_TWILIGHT:
            bg_color = (70, 100, 160)   # Light twilight
        elif phase == TwilightPhase.NAUTICAL_TWILIGHT:
            bg_color = (30, 40, 80)     # Darker blue
        elif phase == TwilightPhase.ASTRO_TWILIGHT:
            bg_color = (15, 20, 40)     # Very dark blue
        else: # TwilightPhase.NIGHT
            bg_color = (11, 13, 23)     # Space black

        screen.fill(bg_color)

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
        sun = snap.sun
        if sun.altitude > -2: 
            s_pos = sky_to_pixel(sun.azimuth, sun.altitude)
            pygame.draw.circle(screen, (255, 220, 100), s_pos, 20)
            pygame.draw.circle(screen, (255, 255, 200), s_pos, 16)

        # 6. Moon
        m = snap.moon
        if m.above_horizon:
            m_pos = sky_to_pixel(m.azimuth, m.altitude)
            # Atmospheric reddening at low altitude
            moon_color = (240, 240, 240) if m.altitude > 15 else (255, 180, 100)
            pygame.draw.circle(screen, moon_color, m_pos, 12)
            
            phase_name = get_moon_phase_name(m.phase_angle)
            moon_lbl = font.render(f"{phase_name} ({int(m.illumination*100)}%)", True, moon_color)
            screen.blit(moon_lbl, (m_pos[0] + 15, m_pos[1] - 10))

        # 7. Cloud Overlay
        screen.blit(cloud_tex, (0, 0))
    
        # UI Overlays
        center, radius = (WIDTH // 2, HEIGHT // 2), int(WIDTH / 2.5)
        pygame.draw.circle(screen, HORIZON_CYAN, center, radius, 1)
        draw_cardinal_labels(screen, font)


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
    print("--- AVAILABLE OBSERVATORIES ---")
    loc_list = list(LOCATIONS.keys())
    for i, name in enumerate(loc_list, 1):
        print(f"[{i}] {name}")
    try:
        choice = int(input("\nSelect a location number: "))
        return loc_list[choice-1], LOCATIONS[loc_list[choice-1]]
    except (ValueError, IndexError):
        print("Invalid choice, defaulting to first location.")
        return loc_list[0], LOCATIONS[loc_list[0]]


if __name__ == "__main__":
    name, info = select_location()
    run_pygame_expedition(name, info)