"""
initializer.py
--------------
Everything that needs to happen *once* before the game loop starts.

Responsibilities
----------------
- pygame.init() and display/font setup
- Config loading (ConfigManager)
- Running the main-menu UI
- Building the chatbot (agent or user-controller)
- Loading initial stats, inventory, and room image into state
- Scheduling timers

Nothing in here touches the game loop.  It returns a clean
``GameContext`` dataclass that ``game.py`` passes into the loop.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Optional

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import gui
from pygame_int.juke_box import jukebox
from pygame_int.main_menu_int.main_menu import run_config_main_menu_ui

from utils.config_manager import ConfigManager
from inventory_items.base_state_manager.base_state_config import InitialStateConst
from ai_managers.agents.abstract_agent import BaseChatbot

from pygame_runtime.tick_registry import TickRegistry

from pygame_int.main_digipet.pet_dna import PetDNA

# ---------------------------------------------------------------------------
# Data container returned to game.py
# ---------------------------------------------------------------------------

@dataclass
class GameContext:
    """All objects the game loop needs, produced by ``initialize()``."""

    screen:              pygame.Surface
    font:                pygame.font.Font
    clock:               pygame.time.Clock
    config_manager:      ConfigManager
    chatbot:             Optional[BaseChatbot]
    chatbot_available:   bool
    music_player_ref:    list          # [None] — filled in after splash
    bots_archive_dir:    str
    idle_time_mins:      float
    #garden_tick_interval_ms: float
    game_mode:           str
    tick_registry:       TickRegistry

def _init_jukebox_silent(chatbot: BaseChatbot) -> Optional[jukebox]:
    # Name is now a misnomer — rename to _init_jukebox if you like.
    # Splash is done by the time this runs, so start music immediately.
    if not pygame.mixer.get_init():
        return None
    try:
        room_data = chatbot.state_manager.get_current_room_data()
        player    = jukebox(f"style/sounds/music/rooms/{room_data.music}.mp3")
        player.play_new_song(f"style/sounds/music/rooms/{room_data.music}.mp3")
        print("[init] Jukebox ready and playing.")
        return player
    except Exception as exc:
        print(f"[init] Jukebox init failed: {exc}")
        return None
# ---------------------------------------------------------------------------
# Sub-steps (called in order by initialize())
# ---------------------------------------------------------------------------

def _init_pygame() -> tuple[pygame.Surface, pygame.font.Font]:
    """Set up display, mixer, and fonts. Returns (screen, font)."""
    pygame.init()

    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
    pygame.display.set_caption("Digital Pet")

    try:
        pygame.mixer.init()
        print("[init] Pygame Mixer ready.")
    except pygame.error as exc:
        print(f"[init] Warning: Mixer unavailable — {exc}")

    try:
        font = pygame.font.Font("style/fonts/Inter/static/Inter_18pt-Bold.ttf", 13) # FONT: Add any font you like to the style/fonts folder and load it here.
    except pygame.error:
        font = pygame.font.SysFont(None, 20)

    line_height = font.get_linesize()
    # NOTE: init_gui_elements and update_gui_rects in gui_core.py are nearly
    # identical (~200 lines duplicated).  The fix is to have init_gui_elements
    # set _font and _line_height, then immediately call update_gui_rects().
    # That refactor lives in gui_core.py — tracked in ARCHITECTURE.md.
    gui.gui_core.init_gui_elements(font, line_height, 200)

    return screen, font


def _load_config(bots_archive_dir: str, screen: pygame.Surface, font: pygame.font.Font) -> ConfigManager:
    """Run the main-menu UI and return the populated ConfigManager."""
    config_manager = ConfigManager(bots_archive_dir)
    run_config_main_menu_ui(screen, font, config_manager)
    return config_manager


def _apply_theme_and_settings(config_manager: ConfigManager) -> None:
    """Push color theme, pet sound, and idle timing into state."""
    state.pet_color = config_manager.get_config("AI", "pet_color") or config.GREEN
    state.pet_sound = config_manager.get_config("AI", "pet_sound") or "mellow_friend.mp3"
    gui.gui_core.gui_construct_colors.set_color_theme()

    seed = config_manager.get_config("AI", "pet_dna")
    
    # Check if seed exists at all
    if not seed:
        # --- DEV SECTION: UNCOMMENT TO ALLOW RANDOM GENERATION ---
        # state.pet_dna = PetDNA.generate_random()
        # return
        # ---------------------------------------------------------
        raise RuntimeError("FATAL: 'pet_dna' is missing from the configuration file.")

    try:
        # Attempt to parse the 7-part DNA string
        state.pet_dna = PetDNA.from_seed(seed)
    except ValueError as e:
        # Re-raise as a fatal RuntimeError so the app stops immediately 
        # with the specific validation error details from PetDNA.
        raise RuntimeError(f"FATAL: Configuration corruption detected. {e}") from e

 

def _build_chatbot(game_mode, bots_archive_dir, config_manager, signal_callback) -> tuple:
    providers_map = {
        "ai_player":   "ai_managers.agents.agent_api.AgentChatbot",
        "user_player": "ai_managers.agents.user_interface_api.UserController",
    }
    if game_mode not in providers_map:
        raise ValueError(f"Invalid game_mode: {game_mode!r}.")
    module_path, class_name = providers_map[game_mode].rsplit(".", 1)
    module       = importlib.import_module(module_path)
    provider_cls = getattr(module, class_name)
    try:
        chatbot = provider_cls.create(
            signal_callback  = signal_callback,
            config_manager   = config_manager,
            bots_archive_dir = bots_archive_dir,
        )
        print(f"[init] {type(chatbot).__name__} ready (mode={game_mode}).")
        return chatbot, True
    except Exception as exc:
        print(f"[FATAL] Chatbot init failed: {type(exc).__name__}: {exc}")
        raise RuntimeError(f"Failed to initialize chatbot for {game_mode}") from exc


def _load_initial_game_state(chatbot: BaseChatbot) -> None:
    """Populate state with saved stats, inventory, and room image."""
    # Pet size based on steps
    steps = chatbot.state_manager.get_steps() if hasattr(chatbot.state_manager, "get_steps") else 0
    size  = _calculate_sized_by_steps(steps, config.CIRCLE_RADIUS, 100)
    state.current_radius = size

    # Background image
    room_data = chatbot.state_manager.get_current_room_data()
    gui.gui_core.load_and_set_background(room_data.image)

    # Stats
    stats_response = chatbot.state_manager.get_stats()
    stats_data     = stats_response.stats
    all_keys_ok    = all(k in stats_data for k in state.pet_stats)
    all_nums_ok    = all(isinstance(v, (int, float)) for v in stats_data.values())
    if all_keys_ok and all_nums_ok:
        for name, value in stats_data.items():
            state.pet_stats[name.lower()] = max(0.0, min(200.0, value))
    print(f"[init] Stats loaded: {state.pet_stats}")

    # Inventory
    inv = chatbot.state_manager.get_inventory_state()
    state.room_inventory_list = [
        gui.gui_inventory.prepare_inventory_item_data(item)
        for item in inv.room_display_strings
    ]
    state.player_inventory_list = [
        gui.gui_inventory.prepare_inventory_item_data(item)
        for item in inv.inventory_display_strings
    ]

# Register new tick workers here.
# reg contains all the initialized tool services from tools/tools_builder/tool_registry.py

def _build_tick_registry(chatbot,) -> TickRegistry:
    registry = TickRegistry()
    fb = chatbot.functions_builder
    reg = fb.registry


    idle_ms = config.IDLE_TIMEOUT_MINUTES * 60 * 1000  # base unit, individual ticks fire 

    registry.register("garden",      reg.garden_manager.tick,        interval_ms=idle_ms * 0.6) # each 60% of idle timeout
    registry.register("lighthouse",  reg.lighthouse.lighthouse_tick, interval_ms=idle_ms * 0.6) # each 60% of idle timeout
    registry.register("tv",          reg.tv_controller.tv_tick,      interval_ms=idle_ms * 1.5) # each 150% of idle timeout
    registry.register("item_toggle", reg.item_toggle.tick,           interval_ms=idle_ms * 2.2) # 2.2, each 220% of idle timeout

    interval_ms = idle_ms * 0.75
    registry.register("outdoors_perception", reg.outdoors_perception.tick, interval_ms=interval_ms)

    registry.register("cranny_controller", reg.cranny_controller.tick, interval_ms=idle_ms * 2.2)
    
    return registry

# Replace the existing _splash() function entirely:

def _splash(screen: pygame.Surface, font: pygame.font.Font) -> None:
    """
    True blocking intro screen. Runs its own tight event loop so the
    game world (chatbot, ticks, signals) doesn't exist yet.
    Exits on timer expiry OR any key/mouse press.
    """
    try:
        image = pygame.image.load("style/images/house_splash_v2.png").convert_alpha()
        image = pygame.transform.scale(image, (200, 200))
    except pygame.error as exc:
        print(f"[init] Splash image load failed: {exc}")
        image = None

    if pygame.mixer.get_init():
        try:
            sound = pygame.mixer.Sound("style/sounds/intro.mp3")
            sound.set_volume(0.5)
            sound.play()
        except pygame.error as exc:
            print(f"[init] Could not play intro sound: {exc}")

    DURATION_MS = 5000
    FADE_IN_MS  = 1000
    FADE_OUT_MS = 3000
    start_ms    = pygame.time.get_ticks()
    clock       = pygame.time.Clock()

    while True:
        now     = pygame.time.get_ticks()
        elapsed = now - start_ms

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            # if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            #     return   # Skip splash on any input

        if elapsed >= DURATION_MS:
            return

        # Alpha calculation: fade in → hold → fade out
        if elapsed < FADE_IN_MS:
            alpha = int(255 * elapsed / FADE_IN_MS)
        elif elapsed > DURATION_MS - FADE_OUT_MS:
            alpha = int(255 * (DURATION_MS - elapsed) / FADE_OUT_MS)
        else:
            alpha = 255

        screen.fill((0, 0, 0))
        if image:
            image.set_alpha(alpha)
            rect = image.get_rect(center=screen.get_rect().center)
            screen.blit(image, rect)

        pygame.display.flip()
        clock.tick(60)


def _calculate_sized_by_steps(
    current_steps: int, start_size: int, end_size: int
) -> int:
    step_limit = config.STEP_SIZE_LIMIT
    if step_limit == 0:
        return start_size
    scale  = min(current_steps, step_limit) / step_limit
    result = start_size + (end_size - start_size) * scale
    return int(max(start_size, min(result, end_size)))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def initialize(game_mode: str, signal_callback) -> GameContext:
    InitialStateConst()
    bots_archive_dir = f"data_archive/{game_mode}/"
    screen, font     = _init_pygame()
    config_manager   = _load_config(bots_archive_dir, screen, font)
    _apply_theme_and_settings(config_manager)



    idle_time_mins = (
        config_manager.get_config("game_settings", "idle_time_minutes")
        or config.IDLE_TIMEOUT_MINUTES
    )
    chatbot, chatbot_available = _build_chatbot(
        game_mode, bots_archive_dir, config_manager, signal_callback
    )
    _load_initial_game_state(chatbot)
    tick_registry       = _build_tick_registry(chatbot)
    state.current_emote = chatbot.state_manager.get_emotes_data().current_emote
    state.last_activity_time = pygame.time.get_ticks()


        # ✅ Splash runs HERE — before chatbot, ticks, or signals exist
    _splash(screen, font)

    return GameContext(
        screen            = screen,
        font              = font,
        clock             = pygame.time.Clock(),
        config_manager    = config_manager,
        chatbot           = chatbot,
        chatbot_available = chatbot_available,
        music_player_ref  = [_init_jukebox_silent(chatbot)],
        bots_archive_dir  = bots_archive_dir,
        idle_time_mins    = idle_time_mins,
        game_mode         = game_mode,
        tick_registry     = tick_registry,
    )