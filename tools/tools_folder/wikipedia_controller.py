from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inventory_items.inventory_manager import InventoryHouseManager # just for typing


from tools.tools_folder.tools_helpers.services.wiki_handle import Wikipedia_handle
# Moved now, updating later 
class WikipediaController:
    def __init__(self, state_manager, signal=None, memory_manager=None):
        self._signal_callback=signal
        self.wiki=Wikipedia_handle(memory_manager) # This is using the memory manager, we can pass it, but there is no need, let the wiki ignore memory constraints
        # Store the state_manager reference
        self.state_manager : InventoryHouseManager = state_manager

        self.last_accessed_wiki=""
        self.last_wiki_query=""
        #print("Computer room initialized.")


    def display_information(self):
        message=f"""The last query made into the wiki was:\n{self.last_wiki_query}\n
                    The last accessed article was: \n{self.last_accessed_wiki}\n 
                """
        return message
    
    def search_wikipedia_articles(self, query):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-2
        self.state_manager.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        query_result=self.wiki.search_wikipedia(query)
        self.last_wiki_query=query_result
        return query_result

    def get_wikipedia_article_content(self, title):
        "Delegated, returns a structured string with title and body for a random wikipedia article"
        edit=-5
        self.state_manager.adjust_stat("energy", edit)
        # --- Add signal call ---
        self._signal_callback({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})
        # ------------------------
        article=self.wiki.get_wikipedia_content_by_title(title)
        self.last_accessed_wiki=article
        return article
    