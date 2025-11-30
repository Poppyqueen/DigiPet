# auction_house.py 

# This is another AI facing tool, it gives the ability to buy and sell items in a 
# digital fake marketplace, where it will be able to order stuff from

# we will load an items store and use it with the names to make a map of items being sold at any current time

import random

from ...inventory_items.items_provider.item_store import ItemStore
from ...inventory_items.items_provider.items_scanner import FuzzyMatcher

class AuctionHouse:
    def __init__(self, state_manager):
        self.item_store = ItemStore()
        self.state_manager = state_manager

        self.price_ranges = {
            "food_n_drinks/hearty_meals.json": { "minimum": 45, "maximum": 70, "available_for_purchase": True },
            "food_n_drinks/drinks_n_drinks.json": { "minimum": 10, "maximum": 25, "available_for_purchase": True },
            "food_n_drinks/snacks.json": { "minimum": 5, "maximum": 20, "available_for_purchase": True },
            "food_n_drinks/plant_based_foods.json": { "minimum": 35, "maximum": 60, "available_for_purchase": True },
            "food_n_drinks/staples.json": { "minimum": 25, "maximum": 50, "available_for_purchase": True },
            "food_n_drinks/condiments_n_sauces.json": { "minimum": 5, "maximum": 15, "available_for_purchase": True },
            "gardening/seeds.json": { "minimum": 40, "maximum": 100, "available_for_purchase": True },
            "gardening/harvest.json": { "minimum": 5, "maximum": 15, "available_for_purchase": False },
            "furniture/sellable_furniture.json": { "minimum": 150, "maximum": 300, "available_for_purchase": True },
            "gadgets/discount_electronics.json": { "minimum": 25, "maximum": 80, "available_for_purchase": True }
        }

        # Populate the catalogs
        self.item_to_source_map = {}
        self.currently_selling = {}  # Items available for purchase
        self.accepted_for_selling = set()  # Items accepted for selling
        
        self._map_items()

        self.fuzzy_matcher = FuzzyMatcher(list(self.currently_selling.keys()))
        
    def _add_item_to_inventory(self, item_name):
        item_data = self.item_store.get_item(item_name)
        return self.state_manager.create_item("inventory", None, item_data)

    def _calc_buy_price(self, mini, maxi, item):
        """Calculate price for items available for purchase"""
        # Get base price from range
        base_price = random.randint(mini, maxi)
        
        # Calculate positive stats bonus
        stats_edit = item.get('stats_edit', {})

        positive_stats_sum = sum(max(0, value) for value in stats_edit.values())
        
        # Stats multiplier (every 10 positive stats adds 10% to price)
        stats_multiplier = 1.0 + (positive_stats_sum / 100)

        # Rarity modifier based on stackable (stackable = more common = cheaper)
        rarity_multiplier = 0.8 if item.get('stackable', True) else 1.2
        
        # Calculate final price
        final_price = base_price * stats_multiplier * rarity_multiplier
        
        # Ensure minimum price of 1
        return max(1, int(final_price))
    
    def _calc_sell_price(self, item_name):
        """Calculate price when selling items to auction house"""
        # If it's a buyable item, use 80% of buy price
        if item_name in self.currently_selling:
            buy_price = self.currently_selling[item_name]["price"]
            return int(buy_price * 0.8)
        
        # For sell-only items, use our item-to-source mapping
        source_path = self.item_to_source_map.get(item_name)
        if not source_path:
            # Fallback: try to get item from store to see if we can find source
            item_data = self.item_store.get_item(item_name)
            if item_data and '__source_path__' in item_data:
                source_path = item_data['__source_path__']
                # Cache it for next time
                self.item_to_source_map[item_name] = source_path
        
        if source_path:
            config = self.price_ranges.get(source_path)
            if config:
                # Get item data for stats calculation
                item_data = self.item_store.get_item(item_name)
                if item_data:
                    mini = config["minimum"]
                    maxi = config["maximum"]
                    base_price = self._calc_buy_price(mini, maxi, item_data)
                    return int(base_price * 0.8)  # Apply same 80% sell rate
        
        # Final fallback if no config found
        return 1
    def _map_items(self):
        """Creates maps of items for both buying and selling based on price_ranges config."""
        for source_path, config in self.price_ranges.items():
            filters = {
                '__source_path__': source_path
            }
            items = self.item_store.find_items(filters)
            
            mini = config["minimum"]
            maxi = config["maximum"]
            available_for_purchase = config.get("available_for_purchase", True)

            for item in items:
                # --- FIX STARTS HERE ---
                # Manually add the source path to the item dictionary itself
                # so it can be used for category filtering later.
                item['__source_path__'] = source_path
                # --- FIX ENDS HERE ---

                name = item["name"]
                
                # Map item name to source path for sell price calculation
                self.item_to_source_map[name] = source_path
                
                # All items are accepted for selling
                self.accepted_for_selling.add(name)
                
                # Only items marked as available_for_purchase go into currently_selling
                if available_for_purchase:
                    price = self._calc_buy_price(mini, maxi, item)
                    self.currently_selling[name] = {
                        "item": item,
                        "price": price
                    }

    #### ------ AI Facing Functions ------ #####


    def get_pretty_items_list(self, list_type: str = "both", pagination: int = 0, category: str = None) -> str:
        """
        Returns a paginated, human-readable list of items.
        
        Args:
            list_type (str): "buy" for purchasable items only, "sell" for sellable items only, 
                        "both" for all items with buy/sell info, "categories" to list available categories
            pagination (int): Page number (0-based)
            category (str): Filter by category (e.g., "hearty_meals", "drinks_n_drinks", "seeds", etc.)
                        Use the filename without .json extension
        """
        max_display = 20
        start_index = pagination * max_display
        end_index = start_index + max_display

        # Handle categories listing
        if list_type == "categories":
            categories = set()
            for source_path in self.price_ranges.keys():
                # Extract category from path like "food_n_drinks/hearty_meals.json"
                category_name = source_path.split('/')[-1].replace('.json', '')
                categories.add(category_name)
            
            sorted_categories = sorted(categories)
            response = "--- Available Categories ---\n"
            for cat in sorted_categories:
                response += f"- **{cat}**\n"
            response += "\nUse get_pretty_items_list('both', 0, 'category_name') to browse items in a specific category."
            return response

        # Get items based on category filter
        if category:
            # Find the matching source path for the category
            matching_source = None
            for source_path in self.price_ranges.keys():
                if source_path.endswith(f"{category}.json"):
                    matching_source = source_path
                    break
            
            if not matching_source:
                available_categories = [path.split('/')[-1].replace('.json', '') for path in self.price_ranges.keys()]
                return f"Category '{category}' not found. Available categories: {', '.join(sorted(available_categories))}"
            
            # Filter items by category
            if list_type == "buy":
                item_names = [name for name, info in self.currently_selling.items() 
                            if info['item'].get('__source_path__') == matching_source]
                title = f"Items for Sale - {category.replace('_', ' ').title()}"
                empty_message = f"No items are currently available for purchase in category '{category}'."
            elif list_type == "sell":
                # Get all items from this category that are accepted for selling
                filters = {
                    '__source_path__': matching_source
                }
                category_items = self.item_store.find_items(filters)
                item_names = [item['name'] for item in category_items if item['name'] in self.accepted_for_selling]
                title = f"Items Accepted for Selling - {category.replace('_', ' ').title()}"
                empty_message = f"No items are currently accepted for selling in category '{category}'."
            else:  # both
                # Get all items from this category
                filters = {
                    '__source_path__': matching_source
                }
                category_items = self.item_store.find_items(filters)
                all_category_items = set(item['name'] for item in category_items)
                # Filter by what's actually in our auction house
                buyable_items = set(name for name, info in self.currently_selling.items() 
                                if info['item'].get('__source_path__') == matching_source)
                sellable_items = all_category_items & self.accepted_for_selling
                item_names = sorted(buyable_items | sellable_items)
                title = f"All Auction House Items - {category.replace('_', ' ').title()}"
                empty_message = f"No items are available in category '{category}'."
            
            item_names = sorted(item_names)
        else:
            # Original logic for all items
            if list_type == "buy":
                item_names = sorted(self.currently_selling.keys())
                title = "Items for Sale"
                empty_message = "No items are currently available for purchase."
            elif list_type == "sell":
                item_names = sorted(self.accepted_for_selling)
                title = "Items Accepted for Selling"
                empty_message = "No items are currently accepted for selling."
            elif list_type == "both":
                # Get all unique items from both lists
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
            else:  # both
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
        Looks up an item by name and returns its buying price, selling price,
        and availability.
        """
        # Check if the item is available for purchase
        if item_name in self.currently_selling:
            item_info = self.currently_selling[item_name]
            buy_price = item_info.get("price")
            sell_price = self._calc_sell_price(item_name)
            
            return (
                f"Item: {item_name}\n"
                f"Status: Available for purchase.\n"
                f"Buy Price: {buy_price} currency.\n"
                f"Sell Price: {sell_price} currency."
            )
        elif item_name in self.accepted_for_selling:
            # Item can be sold but not bought
            sell_price = self._calc_sell_price(item_name)
            return (
                f"Item: {item_name}\n"
                f"Status: Not available for purchase, but accepted for selling.\n"
                f"Buy Price: Not available.\n"
                f"Sell Price: {sell_price} currency."
            )
        else:
            # Use fuzzy matching to suggest similar items
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
        Buy items from the auction house with specified quantity.
        Only items in currently_selling can be bought.
        """
        if quantity <= 0:
            return "Quantity must be greater than 0."
        
        current_currency = self.state_manager.pet_state_manager.get_currency()

        # Check if the item is currently being sold (buyable)
        entry = self.currently_selling.get(item_name)
        if not entry:
            # Check if it's a sell-only item to give better error message
            if item_name in self.accepted_for_selling:
                return f"{item_name} is not available for purchase (sell-only item)."
            else:
                return f"No item named {item_name} is currently being sold."

        item_price = entry.get("price", None)
        if item_price is None:
            return f"Item {item_name} is out of stock..."
        
        total_cost = item_price * quantity
        if current_currency < total_cost:
            return f"Not enough currency to buy {quantity}x {item_name}. Required: {total_cost}, Available: {current_currency}"

        # Perform purchase
        messages = []
        for i in range(quantity):
            message = self._add_item_to_inventory(item_name)
            messages.append(message)
        
        self.state_manager.pet_state_manager.adjust_currency(-total_cost)

        if quantity == 1:
            return f"Successfully bought {item_name} for {item_price}. {messages}"
        else:
            return f"Successfully bought {quantity}x {item_name} for {total_cost} currency total ({item_price} each). {message}"

    def sell_item(self, item_id, quantity=1):
        """
        Sell items from inventory to the auction house with specified quantity.
        Items must be in accepted_for_selling set.
        """
        if quantity <= 0:
            return "Quantity must be greater than 0."
            
        item_info = self.state_manager.inventory_service.get_item_details(item_id, True)

        if not item_info:
            return f"Item with id {item_id} not found."

        item_status = item_info.get("status")
        if item_status != "found":
            return f"Cannot sell item: status is '{item_status}'."

        location_name = item_info.get("location")
        if location_name != "inventory":
            return f"Cannot sell item: it is located in '{location_name}', not in inventory."

        item_data = item_info.get("details")
        if not isinstance(item_data, dict):
            return "Invalid item details."

        item_name = item_data.get("name")
        if not item_name:
            return "Item details missing name."

        item_quantity = item_data.get("quantity", 1)
        
        if quantity > item_quantity:
            return f"Cannot sell {quantity}x {item_name}. Only {item_quantity} available in inventory."

        # Check if item is accepted for selling (expanded acceptance)
        if item_name not in self.accepted_for_selling:
            return f"Item {item_name} is not currently accepted in the auction house."

        # Calculate sell price and perform sale
        sold_price_per_item = self._calc_sell_price(item_name)
        
        if sold_price_per_item is not None:
            total_earned = sold_price_per_item * quantity
            self.state_manager.pet_state_manager.adjust_currency(total_earned)
            
            message = self.state_manager.remove_item(item_id, quantity=quantity)
            
            if quantity == 1:
                return f"Successfully sold {item_name} for {sold_price_per_item} currency. You earned currency! {message}"
            else:
                return f"Successfully sold {quantity}x {item_name} for {total_earned} currency total ({sold_price_per_item} each). You earned currency! {message}"
        else:
            return f"Failed to sell {item_name}. Please try again later."
        

    def get_currency(self):
        """
        Get the current currency balance of the user.
        """
        currency = self.state_manager.pet_state_manager.get_currency()
        return f"Your current currency balance is: {currency} total."