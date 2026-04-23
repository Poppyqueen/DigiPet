from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager
    from inventory_items.services.return_objects import InventoryStateResult, InventoryItemEntry

import random
from utils.misc import front_weighted_pick

NOOK_TYPE = "cranny_host"

YIELD_POOL_CAP = 1.0


class CrannyController:
    def __init__(self, state_manager, signal_callback, items_crafter=None):
        self.state_manager: InventoryHouseManager = state_manager
        self._signal_callback = signal_callback
        self.items_crafter = items_crafter

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter_cranny_items(self, item_data: list[InventoryItemEntry]):
        return [item for item in item_data if NOOK_TYPE in item.item_data.get("type", "")]

    def _get_yield_state(self, item_data: dict) -> tuple[float, float, float, list, list]:
        """Return (search_chance, yield_pool, yield_cost, reward_options, narrative_lines)."""
        search_chance  = item_data.get("chance", 0.05)
        yield_pool     = item_data.get("yield_pool", 1.0)
        yield_cost     = item_data.get("yield_cost", 0.25)
        refresh_rate   = item_data.get("refresh_rate", 0.1)
        reward_options = item_data.get("reward_options", [])
        narrative_lines = item_data.get("narrative_search", ["You reach carefully inside."])
        return search_chance, yield_pool, yield_cost, reward_options, narrative_lines

    # ------------------------------------------------------------------
    # Agent-facing action
    # ------------------------------------------------------------------

    def reach_into_item_crevice(self, item_id: int) -> str:
        lookup = self.state_manager.find_item(
            item_id,
            required_type=NOOK_TYPE,
            required_location="room"
        )
        if lookup.error:
            return lookup.error

        item_data = lookup.item_data
        item_name = self.state_manager.format_item_for_display(item_data, False)

        search_chance, yield_pool, yield_cost, reward_options, narrative_lines = self._get_yield_state(item_data)

        self._signal_callback({"type": "show_message_popup", "message": "Looking for something hidden..."})

        search_action_desc = random.choice(narrative_lines)

        # Gate 1 — action check
        if random.random() >= search_chance:
            return f"{search_action_desc} However, you fail to reach, pull or find any of the remaining rewards this spot holds"

        # Gate 2 — resource check
        if yield_pool < yield_cost:
            return (
                f"{search_action_desc} You feel around carefully... "
                f"but this spot seems to have been picked clean for now."
            )

        # Resolve reward type
        found_item_types = None
        if reward_options:
            try:
                found_item_types = front_weighted_pick(items=reward_options, none_chance=.2)
            except Exception as e:
                print(f"DEBUG ERROR: front_weighted_pick crashed: {e}")

        item_descs_text = "\n".join(item_data.get("descriptions", []))

        items_to_create = self.items_crafter.craft_item(
            user_prompt=(
                f"Create an item found under: {item_name}. {item_descs_text}. "
                f"Inconsequential, evocative, and fits the source item's qualities."
            ),
            select_types=found_item_types
        )

        if not items_to_create:
            return f"{search_action_desc} You feel something, but it turns out to be a mirage."

        result = self.state_manager.create_item(
            target_location="inventory",
            target_location_id=None,
            item_creation_data=items_to_create
        )

        if not result.success:
            return f"{search_action_desc} You feel something, but it slips back into the shadows."

        # Drain pool on success
        new_pool = max(0.0, round(yield_pool - yield_cost, 6))
        self.state_manager.set_item_attribute(item_id, "yield_pool", new_pool)

        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/trumpet.png"})

        return f"{search_action_desc} You found:\n{result.message}"

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    def agent_perceive(self) -> str: # TODO: Decide if we want to wire this into the agent.
        inventory: InventoryStateResult = self.state_manager.get_inventory_state()
        all_items = inventory.inventory_items + inventory.room_items
        cranny_items = self._filter_cranny_items(all_items)

        if not cranny_items:
            return ""

        lines = ["You notice some nooks and crannies nearby:"]
        for item in cranny_items:
            item_data = item.item_data
            display = self.state_manager.format_item_for_display(item_data, True)
            yield_pool = item_data.get("yield_pool", 1.0)
            yield_cost = item_data.get("yield_cost", 0.25)

            if yield_pool < yield_cost:
                pool_hint = "Seems picked clean for now."
            elif yield_pool < yield_cost*2:
                pool_hint = "Feels a bit sparse."
            else:
                pool_hint = "Looks promising."

            lines.append(f"  {display} — {pool_hint}")

        return "\n".join(lines)

    def display_perceive(self) -> str:
        return ""  

    # ------------------------------------------------------------------
    # Tick — replenish yield_pool for all cranny_host items globally
    # ------------------------------------------------------------------

    def tick(self) -> str:
        all_nooks = self.state_manager.get_all_items_by_type(NOOK_TYPE)
        lines = []

        for item_entry in all_nooks:
            item_data = item_entry.item_data
            item_id   = item_entry.item_id

            yield_pool   = item_data.get("yield_pool", 1.0)
            refresh_rate = item_data.get("refresh_rate", 0.1)

            if yield_pool >= YIELD_POOL_CAP:
                continue

            new_pool = min(round(yield_pool + refresh_rate, 6), YIELD_POOL_CAP)
            self.state_manager.set_item_attribute(item_id, "yield_pool", new_pool)

            if yield_pool == 0.0 and new_pool > 0.0:
                item_name = item_data.get("name", "A hidden nook")
                lines.append(f"{item_name}: something may have crept back in...")

        return "\n".join(lines)