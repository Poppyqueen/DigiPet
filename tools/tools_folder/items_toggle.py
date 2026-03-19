from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager, InventoryStateResult, InventoryItemEntry

class ItemToggleTool:
    def __init__(self, state_manager, signal):
        self.state_manager: InventoryHouseManager = state_manager
        self._send_signal = signal

    def _get_toggle_state(self, item_data: dict) -> tuple[bool, dict | str]:
        if "toggle_state" not in item_data:
            return False, f"'{item_data.get('name', 'That item')}' doesn't have a power switch."
        ts = item_data.get("toggle_state", {})
        if not isinstance(ts, dict) or "toggle_state" not in ts:
            return False, f"'{item_data.get('name', 'That item')}' has a malformed toggle_state block."
        return True, ts

    def _filter_toggle_items(self, item_data: list[InventoryItemEntry]):
        return [item for item in item_data if "toggleable" in item.item_data.get("type", "")]

    def _toggle_item(self, item_id: int, turn_on: bool) -> str:
        item_result = self.state_manager.find_item(item_id)
        if not item_result.success:
            return item_result.error

        item_data = item_result.item_data
        item_name = item_data.get("name", "Unknown")

        ok, ts = self._get_toggle_state(item_data)
        if not ok:
            return ts

        current_state = ts.get("toggle_state") == "on"
        if current_state == turn_on:
            return f"The {item_name} is already {'on' if turn_on else 'off'}."

        uses_left = ts.get("toggle_uses_left")
        if turn_on and uses_left is not None and uses_left <= 0:
            return f"The {item_name} has no uses left."

        self.state_manager.set_item_attribute(
            item_id, "toggle_state", "on" if turn_on else "off", path=["toggle_state"]
        )
        self._send_signal({
            "type": "show_message_popup",
            "message": f"{'Turned on' if turn_on else 'Turned off'} {item_name}"
        })

        sequence_key = "on_sequence" if turn_on else "off_sequence"
        description_key = "on_description" if turn_on else "off_description"

        sequence = ts.get(sequence_key, "")
        description = ts.get(description_key, "")

        return "\n".join(part for part in [sequence, description] if part) or f"The {item_name} changed state."

    def toggle_item_power_auto(self, item_id: int) -> str:
        """Toggle — determines on/off from current state and flips it."""
        item_result = self.state_manager.find_item(item_id)
        if not item_result.success:
            return item_result.error

        item_data = item_result.item_data
        ok, ts = self._get_toggle_state(item_data)
        if not ok:
            return ts

        current_on = ts.get("toggle_state") == "on"
        return self._toggle_item(item_id, not current_on)

    def get_access_toggles(self):
        inventory : InventoryStateResult = self.state_manager.get_inventory_state()

        check_all = inventory.inventory_items + inventory.room_items

        toggleable_items = self._filter_toggle_items(check_all)

        if not toggleable_items:
            return ""

        info_string = "You notice some of the items around you:\n"
        for item in toggleable_items:
            item_id = item.item_id
            item_data = item.item_data
            item_name = item_data.get("name", "Unknown")

            ok, ts = self._get_toggle_state(item_data)
            if not ok:
                continue

            info_string += f"  {item_name} ID: {item_id}\n"
            if ts.get("toggle_uses_left") is not None:
                total_potential = ts.get("toggle_uses_left", 0) * ts.get("ticks_lasting", 1)
                remaining_lifespan = total_potential - ts.get("ticks_elapsed", 0)
                info_string += f"  Remaining lifespan: {remaining_lifespan} ticks\n"
            
            if ts.get("toggle_state") == "on":
                info_string += f" {ts.get('on_description', '')}\n"
                info_string += "=" * 30 + "\n"
            else:
                info_string += f" {ts.get('off_description', '')}\n"
                info_string += "=" * 30 + "\n"
        
        return info_string


    def tick(self) -> str:
        """
        Called by the orchestrator on a schedule.
        Finds all toggleable items that are currently ON with finite uses,
        advances ticks_elapsed, and drains one use when a full ticks_lasting
        cycle completes (or every tick if ticks_lasting is absent).
        Destroys perishable items at zero uses.
        """
        all_toggleables = self.state_manager.get_all_items_by_type("toggleable")
        lines = []

        for item_entry in all_toggleables:
            item_data = item_entry.item_data
            item_id   = item_entry.item_id
            item_name = item_data.get("name", "Unknown")

            ts = item_data.get("toggle_state")
            if not isinstance(ts, dict):
                continue
            if ts.get("toggle_state") != "on":
                continue
            uses_left = ts.get("toggle_uses_left")
            if uses_left is None:
                continue

            # --- ticks_lasting gate ---
            ticks_lasting = ts.get("ticks_lasting")
            if ticks_lasting:
                ticks_elapsed = ts.get("ticks_elapsed", 0) + 1
                self.state_manager.set_item_attribute(
                    item_id, "ticks_elapsed", ticks_elapsed, path=["toggle_state"]
                )
                if ticks_elapsed % ticks_lasting != 0:
                    continue  # cycle not complete yet, don't drain

            # --- drain one use ---
            new_uses = uses_left - 1

            if new_uses <= 0 and ts.get("perishable", False):
                self.state_manager.remove_item(item_id)
                off_seq = ts.get("off_sequence", f"The {item_name} has been spent.")
                lines.append(f"{item_name}: {off_seq}")
                self._send_signal({"type": "show_message_popup", "message": f"{item_name} fully consumed!"})
            else:
                self.state_manager.set_item_attribute(
                    item_id, "toggle_uses_left", new_uses, path=["toggle_state"]
                )
                if new_uses <= 0:
                    self.state_manager.set_item_attribute(
                        item_id, "toggle_state", "off", path=["toggle_state"]
                    )
                    off_seq = ts.get("off_sequence", f"The {item_name} switches off.")
                    lines.append(f"{item_name}: {off_seq}")

        return "\n".join(lines)