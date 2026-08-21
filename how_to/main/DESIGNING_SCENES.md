# Designing Scenes

A Scene is the authored starting point for an agent's world — a set of rooms, how they connect to one another, the objects placed inside them, and what the agent begins with in its inventory. This guide covers how to design one using the current **store + layout** system, without writing any Python.

Scenes currently shipping with the project (see `inventory_items/base_state_manager/configs/state_configs_map.json`):

- **Default Home**
- **Compact Home**
- **Walled Garden**
- **Lighthouse Keeper**

All are worth reading before designing your own.

---

## The Store Paradigm

Before you touch a single Scene, understand the shift from how this used to work: rooms and items are **no longer authored inline inside a Scene's files**. Both live in shared, reusable **stores** — a flat catalogue of definitions that any number of Scenes can draw from.

| | Store | Loaded by |
|---|---|---|
| Rooms | `inventory_items/rooms_provider/rooms_data/` | `RoomStore` |
| Items | `inventory_items/items_provider/items_data/` | `ItemStore` |

Both stores recursively scan their root directory for `.json` files — a file may contain a single object or a list of them. Subfolders (`furniture/contemporary/`, `compact_house/`, etc.) are **pure organization**, not a requirement the loader cares about. Every room definition needs a unique `name`; every item definition needs a unique `name`. Those names are how everything else in the system refers to them.

A Scene, then, is really just **a manifest that says which store entries to use and how to arrange them** — it doesn't define rooms or items itself. This is what makes rooms and items reusable across multiple houses: the same store room can be dressed up differently, aliased to a different display name, and dropped into completely different Scenes.

---

## How a Scene Is Structured

A Scene is defined across **two files**, registered together as one entry in a Config Map:

- **The Layout file** — the topology. Which rooms (from the store) this Scene uses, what to call them, how they connect to each other, and which room the agent starts in. Contains **no item data**.
- **The Items file** — populates the rooms named in the layout with objects (from the store), and optionally sets the agent's starting inventory. Contains **no topology data**.

```
inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_lo.json        ← layout
inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_items_lo.json  ← items
```

Both paths get registered together under a Scene name in the Config Map:

```json
// inventory_items/base_state_manager/configs/state_configs_map.json
{
    "Compact Home": {
        "layout_config": "inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_lo.json",
        "items_config": "inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_items_lo.json"
    }
}
```

The key (`"Compact Home"`) is the Scene's identifier — the name used when initializing a new agent. `InitialStateConst.create_state(select_state)` is what reads both files and assembles the full live state.

---

## 1. The Room Store

**Location:** `inventory_items/rooms_provider/rooms_data/` (any subfolder structure you like)

A room store file is a JSON array of room objects — reusable definitions, not tied to any one Scene.

```json
[
    {
        "name": "compact garden",
        "image": "collage_porch",
        "music": "stasis",
        "room_types": ["outdoors_area", "open_soil_zone"],
        "outdoors_type": ["earth-weather", "earth-astro-views", "xeno-canto"],
        "plot_number": 6
    }
]
```

### Room Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | The room's canonical store name. This is what layouts reference (directly, or through an alias — see below). |
| `image` | string | ✅ | **Must match an existing filename** (no extension) under `style/images/area_images/`. This is a `Literal` type validated at import time — you can't invent a name and add the asset later; add the asset first. |
| `music` | string or null | — | Same rule, against `style/sounds/music/rooms/`. Omit or `null` for silence. |
| `room_types` | list of strings | — | Zero or more type tags. See below — this list is much shorter than it used to be. |
| `outdoors_type` | list of strings | — | What kind of outdoors surrounds this room (used by fenestration items and outdoors-tagged behavior). See its own section below. Defaults to `[]`. |
| `movement_group` / `is_connectoid` / `connections` | — | — | **Do not set these in the store.** They're pathing data, assigned per-Scene by the layout file, not a property of the room definition itself. |

Notably absent from the current contract: `descriptions` (the old seven-time-of-day text blocks) and `items`. Neither exists on a room anymore — items are never embedded in a room definition; they're only ever attached at Scene-build time from the items file.

### Room Types

This is the biggest behavioral change from the old system, worth reading carefully: **most of the old room-type affordances are gone.** The full current registry (`inventory_items/items_validation/room_pydantic_models.py`) is:

| Room Type | What it does |
|---|---|
| `outdoors_area` | Marks the room as an accessible outdoors space. |
| `open_soil_zone` | Enables planting/watering/harvesting. **Requires an extra field:** `plot_number` (int) — number of planting plots. |
| `lantern_room` | Lighthouse lantern-room affordances. |
| `lighthouse_gallery` | Lighthouse gallery affordances. |
| `accessible_light_viewing_room` | Lighthouse viewing affordances. |
| `fresnel_lens_interior` | Lighthouse-specific interior. |

There is no more `kitchen`, `bedroom`, `bathroom`, `living_room`, `library`, `computer_room`, `white_room`, or `ALIFE_research` room type. **Room-level affordances for everyday activities have moved onto items.** A room is a kitchen because it contains an item typed `culinary_equipment`, not because the room itself is tagged `kitchen`. A room is a bedroom because it contains a `sleepable_spot` item. A room has drinking water because it contains a `water_point` item. This means when you're designing a new room, the room's `room_types` list is usually going to be empty (or just `outdoors_area` if it applies) — the interesting affordance work happens when you populate it with items, not when you tag the room. See `ITEM_SYSTEM_DOCS.md` for the full item-type catalogue that now carries this weight.

`room_types` absent from `ROOM_TYPE_FIELD_CONTRACTS` (i.e. everything except `open_soil_zone` right now) require no extra fields.

### `outdoors_type`

A separate axis from `room_types`, and easy to conflate with it, so here's the distinction:

- **`room_types: ["outdoors_area"]`** answers *"is this room itself an outdoor space?"* — it changes what the agent can directly do while standing in the room.
- **`outdoors_type: [...]`** answers *"what environment does this room expose a view/access to?"* — regardless of whether the room itself is indoors or outdoors. It's what a `fenestration_aperture` item (a window, skylight, porthole, etc.) placed in that room reads from at runtime to decide what the agent perceives through it. Valid values live in `tools/tools_folder/tools_helpers/outdoors_helpers/outdoors_type_definitions.py` (currently `earth-weather`, `ocean-views`, `xeno-canto`, `earth-astro-views`, `walled-window`, `lunar-dome-view`).

Every room carries this field, indoor or outdoor — you don't need to set it for a normal interior room with no windows worth describing. If you leave it as the default `[]`, the perception tools fall back to a hardcoded `walled-window` behavior on your behalf. You only need to set it explicitly when a room's outdoors access is meaningfully different from a plain walled room — e.g. the lunar dome rooms in `manifest_lunar_items.yaml`, or a garden that should expose real weather and astronomy data.

---

## 2. The Items File

**Location:** alongside its paired layout file, e.g. `inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_items_lo.json`

A flat JSON object: keys are room names **as they appear in the layout** (alias name if the room is aliased — see below), values are the objects to place there. An optional `"inventory"` key sets the agent's starting inventory.

```json
{
    "Garden": [
        "Lounge Outdoors Chair",
        "Lounge Outdoors Chair",
        "Freshwater Pond",
        "Terracotta pot"
    ],
    "Kitchen": [
        "Knife Set",
        "Countertop Convection Toaster Oven"
    ],
    "inventory": ["notebook", "pen"]
}
```

There is **no `initial_room` key here** — that lives in the layout file now, not the items file.

### Specifying Objects

Two ways to populate a room or the inventory, both still handled by `ItemStore`:

**A list of names** — each looked up directly in the Item Store:
```json
"Kitchen": ["Knife Set", "Kitchen Sink"]
```

**A file path string** — pulls in every item under that path in the store (file or directory prefix):
```json
"Kitchen": "inventory_items/items_provider/items_data/furniture/contemporary/items.json"
```

**Stacking syntax** — append `[xN]` to a name for N units of an item, if stackable it will create stacks for it, if not, will create the given individual entries:
```json
"inventory": ["carrot_seeds[x5]", "apple[x3]", "notebook"]
```

Names must match an item's `name` field in the store exactly (a case/whitespace-insensitive fallback match exists, but don't rely on it — keep names exact).

---

## 3. The Layout File

**Location:** paired with its items file, e.g. `inventory_items/base_state_manager/configs/houses_layouts/Compact_Home/default_lo.json`

This is where topology, naming, and the starting room live.

```json
{
  "aliases": {
    "compact garden": "Garden",
    "comfy kitchen": "Kitchen",
    "compact bedroom": "Bedroom",
    "compact living room": "Living Room"
  },
  "initial_room": "Living Room",
  "rooms": ["Living Room", "Kitchen", "Bedroom", "Garden"],
  "groups": {
    "default": ["Living Room", "Kitchen", "Bedroom", "Garden"]
  },
  "connections": []
}
```

### `rooms` — the roster

`"rooms"` is the **single explicit list of every room name in this Scene**, and it's the first thing to write when starting a new layout. `groups` and `connections` describe pathing *between* rooms already declared here — they don't declare rooms on their own. This is validated strictly at build time, in both directions:

- Any name used in `groups` or `connections` that isn't in `rooms` fails immediately — this catches typos (e.g. wiring up `"Rhea's Sky Walkway"` when the room is actually named `"Reah's Sky Walkway"`) before they silently create a disconnected phantom room instead of erroring.
- Any name in `rooms` that never shows up in `groups` or `connections` also fails immediately — this catches a room you declared but forgot to wire in, which would otherwise be built but permanently unreachable with no warning.

Every room in your Scene needs to appear in all the places it's relevant: once in `rooms`, and then wired into either a `groups` entry or a `connections` edge (or both aren't required — one is enough).

### Aliases

Rooms are authored once in the store under a generic name (`"compact garden"`) so they can be reused across multiple houses, then given a Scene-specific display name via `aliases`: `{ store_name: alias_name }`. Every other part of the layout and items file — `rooms`, `groups`, `connections`, `initial_room`, and the item-file's room keys — is written using the **alias name**, never the store name. At build time the engine resolves alias → store name, pulls the room from the `RoomStore`, then renames it to the alias so the rest of the engine only ever sees the alias. If a room isn't aliased, its store name is used as-is.

### `initial_room`

Must exactly match a name in the `rooms` roster. This room becomes room `id: 0` and is where the agent begins.

### Pathing: `groups` vs. `connections`

The layout supports two ways of describing how rooms connect, and you can mix them in the same Scene:

**`groups`** — the simple case. A named bucket of rooms that are all mutually reachable from one another — the "every room in my house is accessible at all times" model most Scenes want. A room can only belong to one group.

**`connections`** — for maze-like structures. A list of `[roomA, roomB]` edges between named nodes. Any node that shows up in `connections` but is **not** also listed in `groups` becomes a **connectoid** — a bridge/hallway/road node rather than a regular room:
- A connectoid can only reach the specific rooms listed in its edges — it has no group of its own.
- A regular room in a group can reach every connectoid that lists it as a connection, in addition to its group-mates.
- Connections are bidirectional regardless of edge order.

```json
"connections": [
    ["Living Room", "Garden Path"],
    ["Garden Path", "Garden"]
]
```
Here `"Garden Path"` (not in any group) becomes a connectoid — a gate the agent must pass through to get from the Living Room group to the Garden, rather than a direct group member.

Whether a room is a connectoid isn't a flag you set — it's derived from group membership: a room in a `groups` entry has full clique access to its group-mates, which is mutually exclusive with the narrower "only these specific neighbours" access a connectoid has. If it's not in any group, and it appears in `connections`, it's a connectoid.

**If you forget to declare a room properly, the build now fails loudly rather than silently misbehaving** — see the `rooms` roster validation above. There's no more silent catch-all fallback to worry about.

The runtime traversal rules themselves live in `inventory_items/services/connections_graph.py` if you want the exact reachability logic (`ConnectionsGraph.get_accessible_ids`, `is_accessible`, etc.) — it's built once per state from the fully-resolved room list produced by the layout.

---

## Designing Objects

Item definitions and their type contracts are large enough to warrant their own document, which is **auto-generated directly from the Pydantic contract registry** — so it never drifts out of date the way this doc can. See:

**[`ITEM_SYSTEM_DOCS.md`](./ITEM_SYSTEM_DOCS.md)**

It covers the base item contract (`name`, `descriptions`, `static`, `type`, `stackable`, `quantity`, `max_stack_size`) and every specialized type's required fields — from `consumable` and `seed` to `fenestration_aperture`, `sleepable_spot`, `culinary_equipment`, `toggleable`, the various information-endpoint types, and the lighthouse-specific set. New item files just get dropped anywhere under `inventory_items/items_provider/items_data/`; the store picks them up recursively.

### Adding a New Item or Room Type

Both items and rooms use the same contract-mixin pattern, defined in `inventory_items/items_validation/contract_mixin.py`. To add a new type:

1. Write a mixin class inheriting from `ContractMixin` (not `BaseModel`) in `item_pydantic_models.py` (items) or `room_pydantic_models.py` (rooms):
    ```python
    class MyTypeFields(ContractMixin):
        model_description: ClassVar[str] = "Plain-English description of what this type represents."
        my_required_key: str = Field(description="What this key does.")
    ```
2. Register it in `TYPE_FIELD_CONTRACTS` (items) or `ROOM_TYPE_FIELD_CONTRACTS` (rooms).

That's it — `validate_item_dict`/`validate_room_dict` and the AI generation schema (built by `ai_schema_builder.build_llm_schema`) both pick it up automatically.

`ContractMixin` enforces some rules strictly, at **class-definition time** (a bad mixin is an import error, not a runtime surprise):
- Don't set `model_config` yourself — it forces `extra="forbid"` for you.
- Every field needs a non-empty `Field(description=...)`.
- No field may be typed `Any` or `object`.
- No field may be `Optional` — mixin fields are always required; the schema builder wraps them in `Optional` automatically when constructing the LLM-facing generation schema, so you should never do that yourself.

Optionally set `model_description` (surfaces as semantic context to the AI generator) and `examine_fields` / override `render_examine_section` (controls what shows up when the agent examines an item of this type).

If none of the existing types fit, this is the whole process — no other registration is required. For wiring the new type into actual agent tools/behaviors (not just data validation), see [`EXTENDING_BEHAVIORS.md`](./EXTENDING_BEHAVIORS.md).

---

## Generating Items with AI

For bulk item creation, `data_constructors/dev_crafter/batch_process.py` drives an LLM through `client.structured_output(...)`, using a schema scoped to exactly the item (or room) types you're generating — built via `build_llm_schema_for_types` / `build_room_llm_schema_for_types`, so the model only sees fields relevant to the types you asked for.

You drive it with a YAML manifest — see `data_constructors/dev_crafter/manifest_lunar_items.yaml` for a full example. Each task in the manifest specifies:

```yaml
config:
  provider: "openrouter"
  model: "google/gemma-4-26b-a4b-it:free"
  export_dir: "inventory_items/items_provider/items_data/lunar_items"

tasks:
  - mode: "item"                       # or "room"
    types: ["fenestration_aperture", "toggleable"]
    context:
      - "Style/theme instructions..."
    prompts:
      - "A round viewport window mounted on a central horizontal axis..."
```

Each `prompt` in a task generates one item (or room), constrained to carry exactly the `types` listed — the script force-overwrites the model's `type` field to match what you asked for even if the LLM tried to omit or add types. Results save incrementally to `<export_dir>/session_<timestamp>/items.json` (or `rooms.json`) after every successful generation, so a failed run partway through doesn't lose earlier output.

**Generated output is a starting draft, not a final asset** — always manually review and curate what comes out before it goes into the store. Move approved items/rooms into their permanent home under `items_provider/items_data/` or `rooms_provider/rooms_data/`, editing as needed.

---

## Putting It Together — Designing a New Environment

1. **Draft the layout pair.** Create a new folder under `houses_layouts/`, and write a layout file (aliases, groups/connections, `initial_room`) and an items file (per-room object lists, optional `inventory`) — even before the rooms and items behind them exist. This gives you your target room names up front.
2. **Populate the Room Store.** Write the actual room definitions (`name`, `image`/`music` referencing assets that already exist on disk, `room_types` if any apply, `outdoors_type` if it matters) and save them under `rooms_provider/rooms_data/`. Alias them from your layout as needed.
3. **Generate item drafts with the AI tool.** Study `ITEM_SYSTEM_DOCS.md` for the types you need (or reuse what's already in the store), then write a manifest and run `batch_process.py`.
4. **Curate.** Manually review every generated item and room — fix descriptions, correct fields, discard what doesn't fit — before moving them into the store proper.
5. **Wire it all up.** Make sure every item name referenced in your items file exists in the Item Store, every room name in your layout resolves (via alias or directly) to something in the Room Store, and every room is explicitly placed in `groups` or `connections`.
6. **Register the Scene.** Add an entry to `state_configs_map.json` (or a new config map file merged into that directory) pointing `layout_config` and `items_config` at your two files.
7. **Verify.** `InitialStateConst.create_state("Your Scene Name")` — or `reload_configs()` first if the map file changed on disk during a live session — and confirm the state builds without missing-room or missing-item warnings.

---

## Managing Configs at Runtime

`InitialStateConst` exposes:

- `list_available_configs()` — all registered Scene names.
- `reload_configs()` — force a full reload of the config map from disk.
- `add_state_configuration(config_map, subdirectory="")` — programmatically register a new Scene config and persist it to disk.
- `remove_state_configuration(config_name)` — delete a registered Scene config.