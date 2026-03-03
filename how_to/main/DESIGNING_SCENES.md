# Designing Scenes

A Scene is the authored starting point for an agent's world — a collection of rooms, the objects placed inside them, and what the agent begins with in its inventory. This guide covers everything you need to design one, from scratch, without writing any Python.

Two example Scenes ship with the project: **DevRoom** and **PrimeHouse**. Both are worth reading before designing your own.

---

## How a Scene Is Structured

A Scene is defined across two JSON files:

- **The House file** — defines the rooms: their layout, appearance, types, and descriptions.
- **The Config file** — populates those rooms with objects, sets the starting inventory, and declares which room the agent begins in.

Both files are then registered together in a Config Map, which is how the framework discovers them.

---

## 1. The House File

**Location:** `inventory_items/base_state_manager/houses_data/`

A house file is a JSON array of room objects. Each room in the array becomes a navigable space in the Scene.

```json
[
    {
        "name": "Living Room",
        "image": "living_room",
        "music": "ambient_home",
        "room_types": ["living_room"],
        "descriptions": {
            "early_morning": ["The room is quiet, pale light just beginning to filter through the curtains."],
            "morning": ["Soft morning light fills the space."],
            "noon": ["The room is bright and warm."],
            "afternoon": ["A comfortable afternoon stillness."],
            "late_afternoon": ["Long shadows stretch across the floor."],
            "night": ["The room is dim, lit only by the glow of the street outside."],
            "late_night": ["Everything is still. The house is asleep."]
        },
        "items": []
    }
]
```

### Room Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | The room's display name. Free-form. |
| `image` | string | ✅ | Filename without extension. Place the image at `style/images/my_unique_rooms_images/<name>.jpg` |
| `room_types` | list of strings | ✅ | One or more type tags — see valid types below |
| `descriptions` | object | ✅ | All seven time-of-day keys required — see below |
| `music` | string or null | — | Filename without extension. Place at `style/sounds/music/rooms/<name>.mp3`. Omit or set `null` for silence. |
| `items` | list | ✅ | Initialize as an empty list `[]` — items are added via the Config file |

### Descriptions

The `descriptions` field takes all seven time-of-day keys. Each key maps to a list of strings — the runtime picks one at random for the current time. Write at least one string per key, and consider writing two or three for variety.

```json
"descriptions": {
    "early morning": ["One string", "Or multiple for variety"],
    "morning":       ["..."],
    "noon":          ["..."],
    "afternoon":     ["..."],
    "late afternoon":["..."],
    "night":         ["..."],
    "late night":    ["..."]
}
```

All seven keys are required. The key names exactly as shown.

### Room Types

Room types define what the agent can do and perceive while in that room. A room can have multiple types — their affordances combine.

| Room Type | What it enables |
|---|---|
| `living_room` | General living space affordances |
| `bedroom` | Bed and rest affordances |
| `bathroom` | Bathroom affordances |
| `kitchen` | Food preparation affordances |
| `library` | Reading and study affordances |
| `garden` | General garden awareness |
| `planting_garden` | Active planting, watering, and harvesting tools ⚠ |
| `outdoors_view` | Passive weather perception — agent receives weather info automatically |
| `white_room` | Minimal environment |
| `computer_room` | Computer and digital affordances |
| `ALIFE_research` | A-Life simulation lab affordances |
| `lantern_room` | Lighthouse lantern room affordances |
| `lighthouse_gallery` | Lighthouse gallery affordances |
| `accessible_light_viewing_room` | Lighthouse viewing affordances |

⚠ **`planting_garden` requires an extra field on the room:** `plot_number` (integer) — the number of planting plots available.

```json
{
    "name": "Back Garden",
    "image": "garden_back",
    "room_types": ["planting_garden", "outdoors_view"],
    "plot_number": 4,
    "descriptions": { ... },
    "items": []
}
```

A room can have multiple types. `["planting_garden", "outdoors_view"]` gives the agent both gardening tools and passive weather awareness.

> **Adding new room types** is covered in [Extending Behaviors](EXTENDING_BEHAVIORS.md). If none of the existing types fit what you're designing, you're not stuck — new types are straightforward to register.

---

## 2. The Config File

**Location:** `inventory_items/base_state_manager/houses_configs/`

The config file populates your rooms with objects and sets up the agent's starting conditions. It's a single JSON object.

```json
{
    "initial_room": "Living Room",
    "Living Room": ["sofa", "coffee_table", "lamp[x1]"],
    "Back Garden": ["garden_bed[x4]"],
    "inventory": ["notebook", "pen"]
}
```

### Config Fields

| Key | Type | Notes |
|---|---|---|
| `initial_room` | string | The room name the agent starts in. Must match a room `name` in your house file exactly. |
| `<Room Name>` | list or string | Objects to place in that room at initialization. |
| `inventory` | list or string | Objects the agent starts with in their inventory. Optional. |

### Specifying Objects

There are two ways to specify objects for a room or inventory slot:

**As a list of names** — each name is looked up in the Item Store by name:
```json
"Living Room": ["sofa", "lamp", "coffee_table"]
```

**As a file path** — loads all objects defined in that file:
```json
"Living Room": "inventory_items/items_provider/items_data/furniture/living_room_set.json"
```

**Stacking syntax** — append `[xN]` to a name to create a stack of N units. Only valid for stackable objects:
```json
"inventory": ["carrot_seeds[x5]", "apple[x3]", "notebook"]
```

Object names come from the Item Store — the files inside `inventory_items/items_provider/items_data/`. The name you use must match the `name` field in the object's blueprint exactly.

---

## 3. The Config Map

**Location:** `inventory_items/base_state_manager/configs/`

Config Maps are JSON files that tell the framework where to find your Scene's two files. You can add your Scene to an existing config map file, or create a new one — the framework recursively loads all JSON files in this directory and merges them.

```json
{
    "my_scene": {
        "b_house_path": "inventory_items/base_state_manager/houses_data/my_house.json",
        "items_config": "inventory_items/base_state_manager/houses_configs/my_house_config.json"
    }
}
```

The key (`"my_scene"`) becomes the Scene's identifier — the name used when initializing a new agent with this Scene.

Once registered, the Scene is immediately available. No code changes needed.

---

## Designing Objects

Objects are JSON blueprints stored in `inventory_items/items_provider/items_data/`. You can add new blueprints to existing files or create new files in any subdirectory — the Item Store walks the entire directory tree.

### Base Fields

Every object requires these fields:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name. Used to look up the object by name in configs. |
| `descriptions` | list of strings | One or more descriptions shown to the agent. |
| `static` | bool | `true` = cannot be picked up (furniture, fixtures). `false` = portable. |
| `type` | list of strings | One or more type tags — see valid types below. |
| `stackable` | bool | `true` for small interchangeable objects (seeds, coins). `false` for unique objects. |

### Optional Base Fields

| Field | Type | Notes |
|---|---|---|
| `quantity` | positive int | Defaults to `1`. Must be `1` for non-stackable objects. |
| `max_stack_size` | positive int | Maximum units per stack. Omit for unlimited. |

### Object Types and Their Required Fields

An object's type tags determine what the agent can do with it. Some types require additional fields beyond the base.

**Types with no extra required fields:**
`misc`, `furniture`, `seat`, `bed`, `pillow`, `art_book`, `toggle_item_power`

**`consumable`** — something the agent can eat, drink, or use for a stat effect:
```json
{
    "name": "Apple",
    "descriptions": ["A crisp, red apple."],
    "static": false,
    "type": ["consumable"],
    "stackable": true,
    "stats_edit": { "fullness": 10.0, "hydration": 2.0, "energy": 5.0 },
    "effects": ["You eat the apple. Refreshing."]
}
```
Required: `stats_edit` (object with `fullness`, `hydration`, `energy` as floats — negative values allowed) and `effects` (list of strings shown on use).

**`seed`** — something that can be planted in a `planting_garden` room:
```json
{
    "name": "Carrot Seeds",
    "descriptions": ["Small seeds for growing carrots."],
    "static": false,
    "type": ["seed"],
    "stackable": true,
    "plant_type": "carrot"
}
```
Required: `plant_type` — must be one of the valid plant types: `lettuce`, `carrot`, `cactus`, `tomato`, `potato`, `strawberry`, `rose`, `sunflower`, `mint`, `basil`.

**`book`** — something the agent can read:
```json
{
    "name": "Field Notes",
    "descriptions": ["A worn notebook filled with observations."],
    "static": false,
    "type": ["book"],
    "stackable": false,
    "chapters": [
        { "title": "Entry 1", "content": "Today I noticed...", "is_locked": false }
    ],
    "is_locked": false
}
```
Required: `chapters` (list of chapter objects, each with `title`, `content`, and `is_locked`) and `is_locked` (bool — a locked book cannot have chapters added or edited by the agent).

**`dispenser`** — a container that dispenses items:
```json
{
    "name": "Candy Machine",
    "descriptions": ["A colourful vending machine."],
    "static": true,
    "type": ["furniture", "dispenser"],
    "stackable": false,
    "dispenser_state": {
        "contents": { "lemon candy": 10, "mint candy": 8 }
    }
}
```
Required: `dispenser_state` object with a `contents` dict mapping item names to quantities.

**`candy_bag`** — a portable container with contents:

Required: `contents` — a dict mapping item names in the item store to quantities, e.g. `{"candy": 5}`.

**Togglable types** (`tv`, `bluesky_social`, `iPod`, `cellphone`, `maze`, `laptop`, `desktop_computer`) — objects with a power state the agent can toggle:
```json
{
    "name": "Television",
    "descriptions": ["A wide flatscreen television."],
    "static": true,
    "type": ["furniture", "tv"],
    "stackable": false,
    "power_toggle": false
}
```
Required: `power_toggle` (bool) — `true` means the object starts powered on, `false` means off. When off, the affordances associated with that object type are unavailable to the agent until it toggles power on.

### Multi-type Objects

An object can carry multiple types simultaneously and must satisfy the required fields for all of them:

```json
{
    "name": "Lettuce Seeds",
    "descriptions": ["Pale seeds for growing lettuce. Edible in a pinch."],
    "static": false,
    "type": ["seed", "consumable"],
    "stackable": true,
    "plant_type": "lettuce",
    "stats_edit": { "fullness": 0.3, "hydration": 0.2, "energy": 0.8 },
    "effects": ["You chew a seed. Not much to it."]
}
```

### Adding a New Object Type

If none of the existing types fit what you're designing, you can register a new one. Two cases:

**No extra fields needed** — add the type name string to the `item_types` list in `inventory_items/item_pydantic_models.py`. That's all. The validation and AI schema systems pick it up automatically.

**Extra fields needed** — add the type to `item_types`, then write a field contract mixin and register it in `TYPE_FIELD_CONTRACTS` in the same file:

```python
class MyTypeFields(BaseModel):
    model_config = ConfigDict(extra="allow")
    my_required_key: str = Field(description="What this key does.")

TYPE_FIELD_CONTRACTS["my_new_type"] = MyTypeFields
```

To wire the new type to agent behaviors, see [Extending Behaviors](EXTENDING_BEHAVIORS.md).

---

## Putting It Together — A Complete Example

A minimal two-room Scene from scratch:

**`houses_data/cozy_flat.json`**
```json
[
    {
        "name": "Main Room",
        "image": "cozy_room",
        "music": "lo_fi_afternoon",
        "room_types": ["living_room", "bedroom"],
        "descriptions": {
            "early_morning": ["The flat is quiet, the city just waking outside."],
            "morning": ["Morning light catches the dust in the air."],
            "noon": ["The room feels warm and unhurried."],
            "afternoon": ["A good afternoon for staying in."],
            "late_afternoon": ["The light turns golden through the window."],
            "night": ["The room glows softly from the lamp in the corner."],
            "late_night": ["Deep quiet. The city has settled."]
        },
        "items": []
    },
    {
        "name": "Kitchenette",
        "image": "small_kitchen",
        "music": null,
        "room_types": ["kitchen"],
        "descriptions": {
            "early_morning": ["Cold and still. The kettle waits."],
            "morning": ["The smell of coffee drifts through."],
            "noon": ["Bright and a little cramped."],
            "afternoon": ["Quiet between meals."],
            "late_afternoon": ["Time to think about dinner."],
            "night": ["The dishes are done. The kitchen rests."],
            "late_night": ["Only the hum of the refrigerator."]
        },
        "items": []
    }
]
```

**`houses_configs/cozy_flat_config.json`**
```json
{
    "initial_room": "Main Room",
    "Main Room": ["bed_single", "desk", "lamp", "bookshelf"],
    "Kitchenette": ["kettle", "mug[x2]", "apple[x3]"],
    "inventory": ["notebook", "pen"]
}
```

**`configs/my_scenes.json`**
```json
{
    "cozy_flat": {
        "b_house_path": "inventory_items/base_state_manager/houses_data/cozy_flat.json",
        "items_config": "inventory_items/base_state_manager/houses_configs/cozy_flat_config.json"
    }
}
```

The Scene `"cozy_flat"` is now registered and available for agent initialization.

---

## Managing Configs at Runtime

The framework exposes three utility methods for managing Scene configs programmatically:

- `list_available_configs()` — returns all registered Scene names
- `reload_configs()` — forces a full reload from disk (useful during development)
- `add_state_configuration(config_map, subdirectory="")` — programmatically registers a new Scene config and saves it to the configs directory