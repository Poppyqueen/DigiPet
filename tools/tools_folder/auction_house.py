# auction_house.py - Case-Insensitive Version

# TODO: Write a JSON state like the lighthouse or the ALife tools, do not use the state manager
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager #just for typing
    from inventory_items.services.return_objects import ItemLookupResult

import random
from inventory_items.items_provider.item_store import ItemStore
from inventory_items.items_provider.items_scanner import FuzzyMatcher



class AuctionHouse: # TODO: Refactor this, make a store_entry type, make dictionary that returns individual item cost, any store_entry type enters the store with the hard coded price in its data blueprint, stop querying with paths, store entry dict needs cost for item, and available for purchase boolean
    # needs awareness affordance, return a sort of main menu, or interface which would be sensible to pass as context to the AI, not full details, just maybe available categories, currency, new items 
    # make a list of store categories, register them as literals in the pydantic models, these categories live inside store_entry, they need to be categories you would sensibly imagine seeing in a store, aisles names, not just item types. Unique to store_entry, only affects Auction House. Rename to online store. Maybe store types with different lists of categories? 
    # New items are good to have but not necessary (add a tick, and after a long time run an AI in the background that creates a few items, maybe every... from 2 to 10 hours? maybe more? based on ticks... need to refactor tick manager for that)
    def __init__(self, state_manager):
        self.item_store = ItemStore()
        self.state_manager : InventoryHouseManager = state_manager

        self.price_ranges = {
            "food_n_drinks/hearty_meals.json": { "minimum": 30, "maximum": 75, "available_for_purchase": True },
            "food_n_drinks/drinks_n_drinks.json": { "minimum": 10, "maximum": 25, "available_for_purchase": True },
            "food_n_drinks/snacks.json": { "minimum": 5, "maximum": 20, "available_for_purchase": True },
            "food_n_drinks/plant_based_foods.json": { "minimum": 35, "maximum": 60, "available_for_purchase": True },
            "food_n_drinks/staples.json": { "minimum": 25, "maximum": 50, "available_for_purchase": True },
            "food_n_drinks/condiments_n_sauces.json": { "minimum": 5, "maximum": 15, "available_for_purchase": True },
            "gardening/seeds.json": { "minimum": 40, "maximum": 100, "available_for_purchase": True },
            "gardening/harvest.json": { "minimum": 10, "maximum": 25, "available_for_purchase": False },
            "furniture/sellable_furniture.json": { "minimum": 150, "maximum": 300, "available_for_purchase": True },
            "gadgets/discount_electronics.json": { "minimum": 25, "maximum": 80, "available_for_purchase": True },
            "books/books_collection.json": { "minimum": 25, "maximum": 45, "available_for_purchase": True },
        }

        # Populate the catalogs
        self.item_to_source_map = {}
        self.currently_selling = {}
        self.item_valuations = {}
        self.accepted_for_selling = set()
        
        # NEW: Case-insensitive lookup maps
        self.lowercase_to_actual = {}  # Maps lowercase names to actual item names
        
        self._map_items()
        self.fuzzy_matcher = FuzzyMatcher(list(self.currently_selling.keys()))
    
    def _normalize_item_name(self, item_name):
        """
        Convert user input to the actual item name using case-insensitive matching.
        Returns the actual item name or None if not found.
        """
        return self.lowercase_to_actual.get(item_name.lower())
        
    def _add_item_to_inventory(self, item_name):
        item_data = self.item_store.get_item(item_name)
        return self.state_manager.create_item("inventory", None, item_data)

    def _calc_buy_price(self, mini, maxi, item):
        """Calculate price for items available for purchase"""
        base_price = random.randint(mini, maxi)
        stats_edit = item.get('stats_edit', {})
        positive_stats_sum = sum(max(0, value) for value in stats_edit.values())
        stats_multiplier = 1.0 + (positive_stats_sum / 500)
        rarity_multiplier = 0.8 if item.get('stackable', True) else 1.2
        final_price = base_price * stats_multiplier * rarity_multiplier
        return max(1, int(final_price))
    
    def _calc_sell_price(self, item_name):
        """Calculate price when selling items to auction house"""
        if item_name in self.item_valuations:
            base_value = self.item_valuations[item_name]
            return int(base_value * 0.8)

        source_path = self.item_to_source_map.get(item_name)
        if not source_path:
            item_data = self.item_store.get_item(item_name)
            if item_data and '__source_path__' in item_data:
                source_path = item_data['__source_path__']
                self.item_to_source_map[item_name] = source_path
        
        if source_path:
            config = self.price_ranges.get(source_path)
            if config:
                item_data = self.item_store.get_item(item_name)
                if item_data:
                    mini = config["minimum"]
                    maxi = config["maximum"]
                    base_price = self._calc_buy_price(mini, maxi, item_data)
                    return int(base_price * 0.8)
        
        return 1
    
    def _map_items(self):
        """Creates maps of items for both buying and selling based on price_ranges config."""
        for source_path, config in self.price_ranges.items():
            filters = {'__source_path__': source_path}
            items = self.item_store.find_items(filters)
            
            mini = config["minimum"]
            maxi = config["maximum"]
            available_for_purchase = config.get("available_for_purchase", True)

            for item in items:
                item['__source_path__'] = source_path
                name = item["name"]
                
                # Store mappings
                self.item_to_source_map[name] = source_path
                self.accepted_for_selling.add(name)
                
                # NEW: Add to case-insensitive lookup
                self.lowercase_to_actual[name.lower()] = name
                
                # Calculate and cache price
                calculated_value = self._calc_buy_price(mini, maxi, item)
                self.item_valuations[name] = calculated_value

                if available_for_purchase:
                    self.currently_selling[name] = {
                        "item": item,
                        "price": calculated_value
                    }

    def get_pretty_items_list(self, list_type: str = "both", pagination: int = 0, category: str = None) -> str:
        """
        Returns a paginated, human-readable list of items.
        
        Args:
            list_type (str): "buy", "sell", "both", or "categories"
            pagination (int): Page number (0-based)
            category (str): Filter by category
        """
        max_display = 20
        start_index = pagination * max_display
        end_index = start_index + max_display

        if list_type == "categories":
            categories = set()
            for source_path in self.price_ranges.keys():
                category_name = source_path.split('/')[-1].replace('.json', '')
                categories.add(category_name)
            
            sorted_categories = sorted(categories)
            response = "--- Available Categories ---\n"
            for cat in sorted_categories:
                response += f"- **{cat}**\n"
            response += "\nUse get_pretty_items_list('both', 0, 'category_name') to browse items in a specific category."
            return response

        if category:
            matching_source = None
            for source_path in self.price_ranges.keys():
                if source_path.endswith(f"{category}.json"):
                    matching_source = source_path
                    break
            
            if not matching_source:
                available_categories = [path.split('/')[-1].replace('.json', '') for path in self.price_ranges.keys()]
                return f"Category '{category}' not found. Available categories: {', '.join(sorted(available_categories))}"
            
            if list_type == "buy":
                item_names = [name for name, info in self.currently_selling.items() 
                            if info['item'].get('__source_path__') == matching_source]
                title = f"Items for Sale - {category.replace('_', ' ').title()}"
                empty_message = f"No items are currently available for purchase in category '{category}'."
            elif list_type == "sell":
                filters = {'__source_path__': matching_source}
                category_items = self.item_store.find_items(filters)
                item_names = [item['name'] for item in category_items if item['name'] in self.accepted_for_selling]
                title = f"Items Accepted for Selling - {category.replace('_', ' ').title()}"
                empty_message = f"No items are currently accepted for selling in category '{category}'."
            else:
                filters = {'__source_path__': matching_source}
                category_items = self.item_store.find_items(filters)
                all_category_items = set(item['name'] for item in category_items)
                buyable_items = set(name for name, info in self.currently_selling.items() 
                                if info['item'].get('__source_path__') == matching_source)
                sellable_items = all_category_items & self.accepted_for_selling
                item_names = sorted(buyable_items | sellable_items)
                title = f"All Auction House Items - {category.replace('_', ' ').title()}"
                empty_message = f"No items are available in category '{category}'."
            
            item_names = sorted(item_names)
        else:
            if list_type == "buy":
                item_names = sorted(self.currently_selling.keys())
                title = "Items for Sale"
                empty_message = "No items are currently available for purchase."
            elif list_type == "sell":
                item_names = sorted(self.accepted_for_selling)
                title = "Items Accepted for Selling"
                empty_message = "No items are currently accepted for selling."
            elif list_type == "both":
                all_items = set(self.currently_selling.keys()) | self.accepted_for_selling
                item_names = sorted(all_items)
                title = "All Auction House Items"
                empty_message = "The auction house has no items available."
            else:
                return f"Invalid list_type '{list_type}'. Use 'buy', 'sell', 'both', or 'categories'."

        total_items = len(item_names)
        total_pages = (total_items + max_display - 1) // max_display if total_items > 0 else 1
        
        if start_index >= total_items and total_items > 0:
            return "No more items to display on this page."
        
        items_to_display = item_names[start_index:end_index]
        
        if not items_to_display:
            return empty_message
            
        response = f"--- {title} (Page {pagination + 1} of {total_pages}) ---\n"
        
        for name in items_to_display:
            if list_type == "buy":
                if name in self.currently_selling:
                    price = self.currently_selling[name]['price']
                    response += f"- **{name}**: {price} currency (buy)\n"
                else:
                    response += f"- **{name}**: Not available for purchase\n"
            elif list_type == "sell":
                sell_price = self._calc_sell_price(name)
                buy_status = "buy available" if name in self.currently_selling else "sell-only"
                response += f"- **{name}**: {sell_price} currency (sell) - {buy_status}\n"
            else:
                buy_price = None
                sell_price = self._calc_sell_price(name)
                
                if name in self.currently_selling:
                    buy_price = self.currently_selling[name]['price']
                
                if buy_price is not None and name in self.accepted_for_selling:
                    response += f"- **{name}**: Buy {buy_price} | Sell {sell_price} currency\n"
                elif buy_price is not None:
                    response += f"- **{name}**: Buy {buy_price} currency (buy-only)\n"
                elif name in self.accepted_for_selling:
                    response += f"- **{name}**: Sell {sell_price} currency (sell-only)\n"
                else:
                    response += f"- **{name}**: Not available\n"
        
        remaining_items = total_items - end_index
        if remaining_items > 0:
            if category:
                response += f"\n--- {remaining_items} more items available. Use 'get_pretty_items_list(\"{list_type}\", {pagination + 1}, \"{category}\")' to see the next page. ---"
            else:
                response += f"\n--- {remaining_items} more items available. Use 'get_pretty_items_list(\"{list_type}\", {pagination + 1})' to see the next page. ---"
        else:
            response += "\n--- You've reached the end of the list. ---"
            
        return response
    
    def lookup_item(self, item_name: str) -> str:
        """
        Looks up an item by name (case-insensitive) and returns its buying price,
        selling price, and availability.
        """
        # NEW: Normalize the item name
        actual_name = self._normalize_item_name(item_name)
        
        if actual_name and actual_name in self.currently_selling:
            item_info = self.currently_selling[actual_name]
            buy_price = item_info.get("price")
            sell_price = self._calc_sell_price(actual_name)
            
            return (
                f"Item: {actual_name}\n"
                f"Status: Available for purchase.\n"
                f"Buy Price: {buy_price} currency.\n"
                f"Sell Price: {sell_price} currency."
            )
        elif actual_name and actual_name in self.accepted_for_selling:
            sell_price = self._calc_sell_price(actual_name)
            return (
                f"Item: {actual_name}\n"
                f"Status: Not available for purchase, but accepted for selling.\n"
                f"Buy Price: Not available.\n"
                f"Sell Price: {sell_price} currency."
            )
        else:
            suggestions = self.fuzzy_matcher.find_suggestions(item_name)
            if suggestions:
                suggestion_names = [s.item_name for s in suggestions]
                suggestion_text = ", ".join(suggestion_names)
                return (
                    f"Item: {item_name}\n"
                    f"Status: Not available for purchase or selling.\n"
                    f"Available items similar to your search: {suggestion_text}?"
                )
            else:
                return (
                    f"Item: {item_name}\n"
                    f"Status: Not available for purchase or selling.\n"
                    "No similar items found in the Auction House. What are you trying to find?"
                )
            
    def buy_item(self, item_name, quantity=1):
        """
        Buy items from the auction house with specified quantity (case-insensitive).
        Only items in currently_selling can be bought.
        """
        if quantity <= 0:
            return "Quantity must be greater than 0."
        
        # NEW: Normalize the item name
        actual_name = self._normalize_item_name(item_name)
        
        if not actual_name:
            return f"No item named '{item_name}' found in the auction house."
        
        current_currency = self.state_manager.pet_state_manager.get_currency() # TODO: Write a state like the lighthouse or the ALife tools, do not use the state manager

        entry = self.currently_selling.get(actual_name)
        if not entry:
            if actual_name in self.accepted_for_selling:
                return f"{actual_name} is not available for purchase (sell-only item)."
            else:
                return f"No item named {actual_name} is currently being sold."

        item_price = entry.get("price", None)
        if item_price is None:
            return f"Item {actual_name} is out of stock..."
        
        total_cost = item_price * quantity
        if current_currency < total_cost:
            return f"Not enough currency to buy {quantity}x {actual_name}. Required: {total_cost}, Available: {current_currency}"

        messages = []
        for i in range(quantity):
            item_lookup_result : ItemLookupResult = self._add_item_to_inventory(actual_name)
            message = item_lookup_result.message
            messages.append(message)
            if not item_lookup_result.success:
                return message
        
        self.state_manager.adjust_currency(-total_cost)

        if quantity == 1:
            return f"Successfully bought {actual_name} for {item_price}. {'\n'.join(messages)}"
        else:
            return f"Successfully bought {quantity}x {actual_name} for {total_cost} currency total ({item_price} each). {'\n'.join(messages)}"

    def sell_item(self, item_id, quantity=1):
        """
        Sell items from inventory to the auction house with specified quantity.
        Items must be in accepted_for_selling set.
        """
        if quantity <= 0:
            return "Quantity must be greater than 0."

        item_object : ItemLookupResult = self.state_manager.find_item(item_id=item_id, required_type=None, required_location="inventory")

        item_data = item_object.item_data

        item_name = item_data.get("name")
        if not item_name:
            return "Item details missing name."

        item_quantity = item_data.get("quantity", 1)
        
        if quantity > item_quantity:
            return f"Cannot sell {quantity}x {item_name}. Only {item_quantity} available in inventory."

        # Note: item_name from inventory should already be the actual name,
        # but we can still normalize it to be safe
        actual_name = self._normalize_item_name(item_name) or item_name
        
        if actual_name not in self.accepted_for_selling:
            return f"Item {actual_name} is not currently accepted in the auction house."

        sold_price_per_item = self._calc_sell_price(actual_name)
        
        if sold_price_per_item is not None:
            total_earned = sold_price_per_item * quantity
            self.state_manager.adjust_currency(total_earned)
            
            return_object = self.state_manager.remove_item(item_id, quantity=quantity)
            
            if quantity == 1:
                return f"Successfully sold {actual_name} for {sold_price_per_item} currency. You earned currency! {return_object.message}"
            else:
                return f"Successfully sold {quantity}x {actual_name} for {total_earned} currency total ({sold_price_per_item} each). You earned currency! {return_object.message}"
        else:
            return f"Failed to sell {actual_name}. Please try again later."
        
    def get_currency(self):
        """Get the current currency balance of the user."""
        currency_data = self.state_manager.get_currency()
        return f"Your current currency balance is: {currency_data.currency} total."