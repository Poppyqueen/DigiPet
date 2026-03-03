# DigiPet Framework — Overview

DigiPet is a framework for building a living environment that an AI agent inhabits, perceives, and acts within. The agent is an entity with a body, a location, a home, possessions, and needs. It experiences the world through its current situation: what room it's in, what it's carrying, what's around it.

Your job as a designer or developer is to shape that world. You define the spaces, the objects that populate them, and the behaviors those objects unlock. The framework takes care of connecting everything to the agent.

---

## The Building Blocks

The live world the agent inhabits is made of three things: **Rooms**, **objects**, and **Affordances**. These are the framework's core triad — understanding how they relate is the foundation for everything else.

### Rooms

Rooms are the navigable spaces the agent moves between. The agent is always in exactly one room at a time, and rooms are where most of the framework's logic is grounded.

Each room has a visual appearance, ambient descriptions that shift with time of day, background music, and — most importantly — **room types**.

Room types are tags that directly shape what the agent can do and perceive. A room tagged `planting_garden` unlocks gardening actions. A room tagged `darkroom` could unlock photo development. A room tagged `outdoors_view` gives the agent passive weather awareness without it needing to ask. You define a room's character and capabilities by choosing its types.

### objects

objects are anything that can exist in the world — placed in a room, or carried in the agent's inventory. objects are defined as JSON blueprints with a name, descriptions, and one or more **type tags**.

Type tags are how the framework knows what an item *is* and what it *enables*. A `consumable` item has stat effects. A `seed` can be planted. A `book` has chapters. A `seat` can be sat on. The type tag connects the item to the behaviors the framework knows about.

objects can belong to multiple types at once — both `seed` and `consumable`, or both `furniture` and `dispenser`. The framework validates that every required field for each type is present.

objects can be **static** (they live in a room and can't be picked up — furniture, fixtures) or **portable** (they can be carried in the agent's inventory). This distinction matters for how affordances activate.

### Affordances

Affordances are what the agent can *do* and what it passively *perceives* — both determined dynamically by the triad in motion.

Every turn, the framework looks at what room the agent is in and what it's carrying, then assembles the exact set of actions and perceptions available right now. This is the **Affordance Construction System**. It doesn't give the agent everything at once — it gives the agent what makes sense given its situation.

Affordances come in two kinds:

- **Actions** — callable tools the agent can invoke: `dig_hole`, `read_chapter`, `take_a_seat`, `prepare_food`. These only appear when the context warrants them.
- **Perceptions** — information the agent passively receives without taking an action. If the agent is in a room with an active lamp simulation, it already knows the lamp's state when its turn begins. This is analogous to peripheral vision: awareness that comes from *being somewhere*, not from asking.

The link between objects, Rooms, and Affordances is the type tag system. An affordance block declares which item types or room types activate it, and whether an item needs to be in the agent's inventory, in the current room, or either. When the context matches, the affordance is live.

---

## Scenes — Designing the Whole

A **Scene** is what you author: the complete starting configuration of a world — its rooms, the objects placed inside them, and what the agent begins with in its inventory. A Scene is a home, a lighthouse, a research station, a cramped apartment above a shop.

Scenes only matter at the moment a new agent is initialized. The framework reads the Scene, builds the world from it, and then steps back. From that point on, the agent's world evolves on its own — objects are created and consumed, rooms are navigated, state accumulates. The Scene blueprint is never consulted again.

This means a Scene is a creative act, not a runtime concept. You design it once; the agent lives in it.

---

## How They Connect

```
Scene (your design — rooms + objects + starting inventory)
  ↓  [first launch only]
Live World
  │
  ├── Current Room (room types)
  └── Agent Inventory (item types)
          ↓
  Affordance Construction System
          ↓
  Active Actions + Active Perceptions  →  Agent turn
          ↓
  Agent acts → world state changes → new context → new affordances
```

It's a continuous loop. The agent acts, the world changes, the available affordances update, and the agent's next turn starts with a fresh accurate picture of its situation — automatically.

---

## What You Can Design

You can work at any level of this system:

**Just scenes and objects (no Python required)**
Design an environment entirely through JSON: define rooms with types and descriptions, create item blueprints, configure the initial state that populates a new agent's world. The framework wires up all the affordances that already exist for the types you use.

**New item types with new behaviors (Python)**
Define a new item type, write the tool class that implements its behavior, register it as an affordance block. Now any room or item using that type automatically activates your new behavior.

**New perception layers (Python)**
Add passive context that gets injected into the agent's situation automatically — environmental readings, system states, ambient awareness — without the agent needing to call anything.

**New simulation systems (Python)**
Build an independent system (a simulation, an external integration, a multi-session process) that the agent can interact with through objects in the world. The framework has established patterns for exactly this.

---

## Where to Go Next

- **[Designing Scenes](DESIGNING_SCENES.md)** — Define rooms, create item blueprints, configure initial states. Start here if you want to build a world without writing Python behavior.

- **[Extending Behaviors](EXTENDING_BEHAVIORS.md)** — Write tools, register affordances, implement new item types, build simulation systems. Start here if you want to add new capabilities to the agent.