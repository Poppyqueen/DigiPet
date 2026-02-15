# Items: How to Create and Use Items for the DigiPet

## What are items?

Let's divide the concept of items into two categories. There are item definitions/structures,
and there are items in the game state. This guide contains information on how to create
definitions for items (which we think of as 'blueprints'), and how instantiating them
in the project works.

Item definitions/structures, or 'blueprints', are JSON definitions inside
`inventory_items/items_provider/items_data/`. We have an
`inventory_items/items_provider/item_store.py` that walks the files in this directory
to populate a store of item definitions for usage across the DigiPet project.

All items require certain keys on their blueprints depending on their types, while always
including the base keys described below.

---

## How to instantiate an item?

`tools/tools_folder/tools_data/harvesting_data.py` shows the usage of `ItemStore`. It
involves initialising the store with the path to the items directory, then querying by
name to get a blueprint you can pass to `create_item`.

```python
from inventory_items.items_provider.item_store import ItemStore

cc = ItemStore("inventory_items/items_provider/items_data")

carrot_blueprint = cc.get_item("carrot")
# Pass the blueprint to the inventory manager to instantiate it in the game:
# state_manager.create_item("room", room_id, carrot_blueprint)
# state_manager.create_item("inventory", None, carrot_blueprint)
```

---

## How to create an item?

Go into `inventory_items/items_provider/items_data/` and either create a new JSON file
or add to an existing one.

### Base Keys (required on every item)

| Key | Type | Notes |
|-----|------|-------|
| `name` | string | Human-readable item name |
| `descriptions` | list of strings | One or more description strings shown to the player |
| `static` | bool | `true` if the item cannot be picked up or moved (e.g. furniture) |
| `type` | list of strings | At least one valid type tag — see valid types below |
| `stackable` | bool | Defaults to `false`. Set `true` for small non-unique items (seeds, coins). Unique or large items must be `false` |

### Optional Base Keys

| Key | Type | Notes |
|-----|------|-------|
| `quantity` | positive int | Defaults to `1`. Must be `1` for non-stackable items |
| `max_stack_size` | positive int or omitted | Maximum units per stack. Omit for unlimited |

---

### Type-Specific Required Keys

Items with certain type tags require additional keys. Every required key is enforced by
the validation system — items missing required keys will be rejected at creation and on
load.

**`consumable`**
- `stats_edit` — dict with keys `fullness`, `hydration`, `energy` as floats (positive or negative)
- `effects` — list of strings: narrative descriptions shown to the player on consumption

**`seed`**
- `plant_type` — string mapping the seed to a valid plant type *2

**`book`**
- `chapters` — list of chapter dicts, each with keys `title` (string) and `content` (string)
- `is_locked` — bool, defaults to `false`. Locked books cannot have chapters added or edited

**`dispenser`**
- `dispenser_state` — dict tracking the internal state of the dispenser mechanism

**`candy_bag`**
- `contents` — dict mapping contained item names to their quantities, e.g. `{"candy": 5}`

**Toggable types** (`tv`, `bluesky_social`, `iPod`, `cellphone`, `maze`, `laptop`, `desktop_computer`)
- `power_toggle` — bool. `true` = item starts On, `false` = item starts Off. Controls whether
  tools associated with this item are available to the agent. Toggling power is handled by
  the agent via a dedicated tool.

---

### Multi-type items

A single item can belong to multiple types simultaneously, and must satisfy the required
keys for all of them. For example, lettuce seeds are both `seed` and `consumable`:

```json
{
    "name": "Lettuce Seeds",
    "descriptions": ["Small pale seeds for growing lettuce."],
    "static": false,
    "type": ["seed", "consumable"],
    "stackable": true,
    "plant_type": "lettuce",
    "stats_edit": { "fullness": 0.3, "hydration": 0.2, "energy": 0.8 },
    "effects": ["A faint refreshing boost."]
}
```

---

## Adding a new item type

### Type with no required extra fields

Add the type name string to the `item_types` list in `inventory_items/item_pydantic_models.py`. That's it —
the item will pass validation with only the base keys.

### Type with required extra fields

1. Add the type name to `item_types` in `inventory_items/item_pydantic_models.py`.
2. Write a field contract mixin in the same file:
    ```python
    class MyNewTypeFields(BaseModel):
        model_config = ConfigDict(extra="allow")
        my_required_key: str = Field(description="What this key does.")
        my_optional_key: Optional[int] = Field(default=None, description="...")
    ```
3. Register it in `TYPE_FIELD_CONTRACTS`:
    ```python
    TYPE_FIELD_CONTRACTS["my_new_type"] = MyNewTypeFields
    ```

That's all. The runtime validator (`validate_item_dict`) and the AI generation schema
(`ItemDefinitionListContainer`) both update automatically — no other files need changing.

---

## Notes

*1 **Valid item types**: The full list lives in `inventory_items/item_pydantic_models.py` in the `item_types`
list. Types that introduce required fields also have a registered mixin in
`TYPE_FIELD_CONTRACTS` in the same file. See the interactive items workflow guide for
how new types connect to agent tool affordances.

Different item types afford the agent varied functions mapped inside the tools manager.
Types that currently give the agent tools are `book`, `seed`, `seat`, and `consumable`.
`seat` is the only example of an environmental item that affords actions to the agent
without being in inventory — the rest require the item to be carried.

*2 **Plant types**: Valid plant types are defined in
`tools/tools_folder/tools_data/harvesting_data.py`, which contains the harvesting
structures that govern plant growth behaviour. The `plant_type` key on a seed maps it
to one of these definitions. You can name the seed item anything — a seed called
"magical seed" with `plant_type: "lettuce"` will grow exactly like a lettuce. To add
a new plant type, extend the harvesting data structures there and add the new name to
`valid_plants` in `inventory_items/item_pydantic_models.py`.