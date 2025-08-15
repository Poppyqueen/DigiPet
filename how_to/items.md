# Items: How to Create and Use Items for the DigiPet

## What are items?

Let's divide the concept of items into two categories. There are item definitions/structures, and there are items in the game state. This guide will contain information on how to create these definitions for items (which we will think of as 'blueprints'), and how instantiating them in the project would work.

Item definitions/structures, or 'blueprints', are JSON definitions inside our `inventory_items/items_provider/items_data` directory. We have an `inventory_items/items_provider/item_store.py` that walks the files in this directory to populate a store of item definitions for usage across the DigiPet project.

All items have requirements for certain keys on their blueprints, depending on the types they are, while always including certain specific basic values.

## How to use an item?

`tools/tools_folder/tools_data/harvesting_data.py` displays the usage of the ItemStore. It involves initializing our store with the path to the directory where we keep our item blueprints, and then we can query the store to get item definitions with the item name. We receive the item blueprint which we can manipulate as we like inside the game, i.e., calling a create item method with this blueprint retrieved.

```python
from inventory_items.items_provider.item_store import ItemStore # import item store

cc = ItemStore("inventory_items/items_provider/items_data") # Initialize the store with our items path

carrot_blueprint = cc.get_item("carrot") # Query for an item definition for an item called "carrot". Here you can manipulate this blueprint with the inventory manager as you like to instantiate it into the game.
```

## How to create an item?

To create an item, go into the directory `inventory_items/items_provider/items_data/`

Here you can create new JSON files or add into the existing ones.

Some items have extra required keys, alongside the base ones.

**Base Keys (all items use):**

- `name` - string
- `descriptions` - list of strings
- `static` - bool
- `type` - list of valid item types *1
- `stackable` - bool, defaults to False if not given

Items with certain specific 'types' might require specific keys. Here are all the specific items that require extra keys and what they require:

**Types:**

**seed:**
- `plant_type` - a string relating this seed to its valid parent plant type *2

**consumable:**
- `effects` - string list, descriptions of effects or phenomenal narrative for consuming this item
- `stats_edit` - a dictionary with the keys `fullness`, `hydration` and `energy` as positive or negative floats to adjust stats with when consumed

**book:**
- `chapters` - a list of dictionaries for individual chapters, each dictionary item in this list contains the keys `title` and `content` where both are single strings

After creating the correct blueprint structure for your item, it will be accessible for the project using the ItemStore automatically.

**Notes:**

*1 Item 'type' key: This is a list of strings from a valid pool of item types. For example, an item can be both a seed and a consumable. You can see the valid item types inside `inventory_items/services/inventory_service.py`.

`ALLOWED_ITEM_TYPES = ["tool", "consumable", "misc", "key", "weapon", "armor", "furniture", "book", "seed", "chair"]`

Adding a new allowed item type without extra keys only requires you to add its type name into this list. 

If your new item type requires an extra key like consumables or books do you will have to add to the the validation method to consider this.

Different item types afford the agent with varied functions; these are mapped inside the tools manager. More about mapping new item types in the tools how_to md file.

When creating an item blueprint, changing the item type will change the tool affordances for the agent actions while holding them or some by being in a room that holds them. Those types that give the agent tools currently are `book`, `seed`, `chair` and `consumable`. `chair` is the only example of an environmental item that affords actions or tools to the agent. The rest need to be in inventory.

*2 Plant type: In `tools/tools_folder/tools_data/harvesting_data.py` you will find definitions of plant harvesting structures that determine their behavior for growing. Here we can find all the valid plant types that exist in the garden simulator. If you are creating a seed, this `plant_type` key maps the seed to its specific behavior. i.e., you can make a seed object called "magical seed" and if the plant type is set as 'lettuce' it will behave as a lettuce and grow a lettuce. Make sure to use existing plant types in this garden manager.