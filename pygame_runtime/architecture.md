# DigiPet — Game Loop Architecture

## The problem with the old `game.py`

The original file mixed six different concerns in ~700 lines:

| Concern | Lines (approx.) |
|---|---|
| Pygame init + font/display setup | 40 |
| Config loading + main-menu UI | 30 |
| Chatbot construction | 30 |
| Signal handling (agent → pygame) | 120 |
| Event handling (pygame → game) | 280 |
| Thread workers | 60 |
| Game loop + autonomous logic | 140 |

Every time you needed to change *one thing*, you had to navigate all the rest.

---

## New file layout

```
game.py              ← entry point + main loop  (~130 lines)
initializer.py       ← one-time startup          (~170 lines)
signal_handler.py    ← agent signals → pygame    (~200 lines)
event_handler.py     ← pygame events → game      (~300 lines)
workers.py           ← background threads         (~110 lines)
```

---

## What each file owns

### `game.py`
**One job: run the loop.**

```
main()
 ├── signal_callback  = make_signal_handler(...)   # wiring
 ├── ctx              = initialize(...)             # startup
 └── while running:
      ├── clock / cursor / popup updates
      ├── for event: handle_custom_events()
      │              handle_input_events()
      ├── _trigger_autonomous_action()
      ├── _trigger_garden_tick()
      └── gui.draw_gui()
```

Two tiny helpers live here because they read `ctx` directly:
- `add_items(items_list, room_id)` — sends a care package to the room
- `clean_hover()` — resets hover state variables

---

### `initializer.py`
**One job: produce a ready-to-run `GameContext`.**

Called once before the loop.  Returns a `GameContext` dataclass with every
object the loop needs (screen, chatbot, clock, config, timers …).

Sub-steps in order:
1. `_init_pygame()` — display, mixer, fonts, GUI layout
2. `_load_config()` — ConfigManager + main-menu UI
3. `_apply_theme_and_settings()` — pet colour, pet sound, colour theme
4. `_build_chatbot()` — dynamic import of agent or user-controller
5. `_load_initial_game_state()` — stats, inventory, background image
6. `_splash()` — intro sound + splash popup
7. Timer setup — `last_activity_time`, `next_garden_tick_time`

---

### `signal_handler.py`
**One job: translate agent signals into Pygame events.**

The agent never imports pygame.  Instead it calls `signal_callback(dict)`,
which is the closure returned by `make_signal_handler()`.

Each signal type has its own private function (`_on_*`), all registered in
`_SIGNAL_HANDLERS` dict.  Adding a new signal type = add one function +
one dict entry.

```python
_SIGNAL_HANDLERS = {
    "change_background":  _on_change_background,
    "shake_circle":       _on_shake_circle,
    "TTS_AUDIO":          _on_tts_audio,
    "function_called":    _on_function_called,
    "emote_changed":      _on_emote_changed,
    "start_sleep":        _on_start_sleep,
    "end_sleep":          _on_end_sleep,
    "stat_changed":       _on_stat_changed,
    "room_inventory":     _on_room_inventory,
    "player_inventory":   _on_player_inventory,
    "show_icon_popup":    _on_show_icon_popup,
    "show_message_popup": _on_show_message_popup,
    "play_sound":         _on_play_sound,
}
```

The handler is a **closure** (`make_signal_handler`) so `chatbot` and
`music_player` can be swapped in after construction via single-element lists.

---

### `event_handler.py`
**One job: react to Pygame events.**

Two public functions called by the game loop:

| Function | Handles |
|---|---|
| `handle_custom_events(event, …)` | All `config.*_EVENT` types posted by the agent |
| `handle_input_events(event, …)` | Mouse, keyboard, inventory panel modal |

Both return `True` if the event was consumed (caller should `continue`).

Internal breakdown:
- `_handle_inventory_panel_events()` — modal close/scroll when panel is open
- `_handle_mouse_motion()` — hover state for packages + stat icons
- `_handle_mouse_button()` — all left-click targets (toggles, mute, panels, packages)
- `_handle_care_package_click()` — scroll arrows + package button clicks
- `_handle_keyboard()` — text input, hotkeys (i / c / m), Ctrl+5, Escape

---

### `workers.py`
**One job: run blocking calls off the main thread.**

| Function | Thread target | Posts event |
|---|---|---|
| `chatbot_worker()` | `asyncio.run(chatbot.process_input())` | `CHATBOT_RESPONSE_EVENT` |
| `start_chatbot_request()` | spawns above | — |
| `garden_tick_worker()` | garden + lighthouse + TV ticks | `UPDATE_LORE_DISPLAY_EVENT` |
| `start_garden_tick_request()` | spawns above | — |

All threads are **daemon threads** (die when the process exits).
Communication back to the main thread is **exclusively via `pygame.event.post()`**,
which is the only thread-safe Pygame call.

---

## Data flow diagram

```
User input
    │
    ▼
pygame event queue
    │
    ├─► handle_custom_events()   ← also fed by workers via event.post()
    │       │
    │       └─► state mutations + gui calls
    │
    └─► handle_input_events()
            │
            ├─► state mutations
            └─► start_chatbot_request()
                        │
                        └─► chatbot_worker (thread)
                                │
                                ├─► agent.process_input()
                                │       │
                                │       └─► signal_callback()
                                │               │
                                │               └─► pygame.event.post()
                                │
                                └─► pygame.event.post(CHATBOT_RESPONSE_EVENT)
```

---

## Adding features — where does it go?

| What you want to add | Where |
|---|---|
| New agent signal type | `signal_handler.py` — add `_on_*` + entry in `_SIGNAL_HANDLERS` |
| New button / UI element | `event_handler.py` — add to `_handle_mouse_button` or a new helper |
| New keyboard shortcut | `event_handler.py` — `_handle_keyboard()` |
| New background thread task | `workers.py` — new `*_worker` + `start_*_request` pair |
| New startup step | `initializer.py` — new `_*` function, call from `initialize()` |
| Config or constants | `pygame_int/config.py` (unchanged) |

---

## State conventions (unchanged)

All shared mutable state lives in `pygame_int/state.py`.
No file should import another game-layer file to read state —
everything reads from `state` directly.

The only deliberate exception is `music_player_ref` and `chatbot_ref`,
which are single-element lists passed around so late-initialised objects
can be referenced without a global reassignment.