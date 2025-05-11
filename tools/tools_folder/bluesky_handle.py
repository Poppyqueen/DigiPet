import os
import logging
# import threading # Removed threading import
from urllib.parse import urlparse
from dotenv import load_dotenv
from atproto import Client, models, AtUri

# Configure logging (keep it outside the class)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Removed threading.Thread inheritance
class bluesky_bot:

    alt_text = {
        "bedroom": (
            "Image of a bedroom: A sketch of a bedroom interior, framed by a rounded-corner green border. "
            "A bed with pillows and blankets is centered in the frame, with bedside tables on either side. "
            "Curtains hang in front of a window in the background, and a dresser stands against the wall to the right. "
            "A solid black circle is positioned in the center of the room, representing a character within the scene. "
            "The graphical design is a simple line drawing with a light gray fill on a white background, creating a sketch-like aesthetic."
        ),
        "garden": (
            "Image of a garden: A sketch of a garden or greenhouse space, framed by a rounded-corner green border. "
            "Lush plants and vines grow on trellises and in pots. Potted plants are visible in the foreground, and stone-like tiles cover the floor. "
            "A glass structure suggests a greenhouse or conservatory setting. A solid black circle is positioned in the center of the garden, "
            "representing a character within the scene. The graphical design is a simple line drawing with a light gray fill on a white background, "
            "giving the image a hand-drawn, illustrative style."
        ),
        "kitchen": (
            "Image of a kitchen: A sketch of a kitchen interior, framed by a rounded-corner green border. "
            "Cabinets and countertops are visible along the walls, with a sink, oven, and kettle clearly depicted. "
            "Dishes are on the counter and hanging from the cabinets. A solid black circle is positioned in the center of the kitchen, "
            "representing a character within the scene. The graphical design is a simple line drawing with a light gray fill on a white background, "
            "creating a clean and schematic visual."
        ),
        "library": (
            "Image of a library: A sketch depicting a library, framed by a rounded-corner green border. "
            "Shelves filled with books cover the frame. The books are stacked densely and reach to the top of the image. "
            "A solid black circle is positioned in the center of the library, representing a character within the scene. "
            "The graphical design is a simple line drawing with a light gray fill on a white background, emphasizing the linear texture of the bookshelves and books."
        ),
        "living_room": (
            "Image of a living room: A sketch of a living room interior, framed by a rounded-corner green border. "
            "A sofa and armchairs are arranged around a coffee table. A rug is on the floor, and a cabinet or shelving unit is visible in the background. "
            "A solid black circle is positioned in the center of the living room, representing a character within the scene. "
            "The graphical design is a simple line drawing with a light gray fill on a white background, providing a clear and uncluttered representation of the room."
        ),
        "study": (
            "Image of a study: A sketch of a study or home office, framed by a rounded-corner green border. "
            "A desk with stacked books is in the foreground. A window and shelving unit are visible in the background. "
            "A solid black circle is positioned in the center of the study, representing a character within the scene. "
            "The graphical design is a simple line drawing with a light gray fill on a white background, resulting in a minimalist and diagrammatic style."
        ),
        "computer_room": (
            "Image of a computer room: A sketch depicting a computer room, framed by a rounded-corner green border. Desks with computers and keyboards are arranged around office chairs. Bookshelves and storage units are visible in the background, filled with equipment and supplies. "
            "A solid black circle is positioned in the center of the room, representing a character within the scene. The graphical design is a simple line drawing with a light gray fill on a white background."
        ),
        "white_room":(
            "A white image, A solid black circle is positioned in the center of the room, representing a character within the scene."
        )
    }

    # Removed threading arguments and super().__init__()
    def __init__(self, state, signal):
        # super().__init__() # Removed call to parent class init
        self._signal_callback=signal

        self.state = state
        # Removed _stop_event
        # Removed _update_interval
        # Removed _lock

        # Load environment variables
        load_dotenv()
        self.HANDLE = os.getenv('HANDLE')
        self.PASSWORD = os.getenv('PASSWORD')

        if not self.HANDLE or not self.PASSWORD:
            logging.error("HANDLE or PASSWORD not set in environment variables.")
            self.is_ready = False
            return

        # Initialize client and login
        try:
            # Lock is no longer needed as there's no separate thread
            self.client = Client()
            self.client.login(self.HANDLE, self.PASSWORD)

            logging.info(f"Logged in as {self.HANDLE} (Bluesky Bot)")
            self.is_ready = True
        except Exception as e:
            logging.error(f"Login failed for {self.HANDLE}: {e}")
            self.is_ready = False

        # Removed thread start
        # Removed initial timed action call

    # --- Helper method to be added to each room class ---
    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            # print(f"{self.__class__.__name__} signaling: {signal_data}") # Optional: uncomment for debug
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                print(f"Error sending signal from {self.__class__.__name__}: {e}")
        else:
            # print(f"{self.__class__.__name__} attempted to signal, but no callback registered: {signal_data}") # Optional: uncomment for debug
            pass # Silently fail if no callback is registered, or log loudly
    # ------------------------------------------------------

    # Removed run method
    # Removed stop method
    # Removed _perform_timed_action method

    # --- Existing methods, lock removed ---

    def extract_did_from_uri(self, uri: str) -> str:
        """Extracts the DID from an at:// URI using urlparse."""
        # This method doesn't use self.client, no lock needed
        return urlparse(uri).netloc


    def post_response(self, uri: str, response_text: str):
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot post response.")
            return "Bluesky bot not ready."

        logging.info("Attempting to post response...")
        record_data = None
        try:
            # Lock is no longer needed
            parent_uri = AtUri.from_str(uri)
            parent_did = self.extract_did_from_uri(uri)

            params = {
                "repo": parent_did,
                "collection": "app.bsky.feed.post",
                "rkey": parent_uri.rkey,
            }

            # Use self.client directly
            parent_post_resp = self.client.com.atproto.repo.get_record(params=params)
            record_data = parent_post_resp.json()

            parent_cid = record_data.get("cid")
            if not parent_cid:
                logging.error("Parent CID not found in the record.")
                return "Error: Parent CID not found."

            parent_ref = models.create_strong_ref({
                'uri': str(parent_uri),
                'cid': parent_cid
            })
            root_ref = parent_ref # In a reply, root is usually the same as parent unless it's a deep thread

            reply_ref = models.AppBskyFeedPost.ReplyRef(
                parent=parent_ref,
                root=root_ref
            )

            record = models.AppBskyFeedPost.Record(
                text=response_text,
                created_at=self.client.get_current_time_iso(),
                reply=reply_ref,
            )

            # Use self.client directly
            resp = self.client.app.bsky.feed.post.create(
                repo=self.client.me.did,
                collection=models.ids.AppBskyFeedPost,
                record=record,
            )

            logging.info("Response posted successfully.")
            return "Response posted successfully on Bluesky."
        except Exception as e:
            logging.error(f"Failed to post response: {e}")
            return f"An error occurred while posting response: {e}"


    def post_bluesky(self, message: str, image_post: bool = False, langs_list: list = ['en']):
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot send post.")
            return "Bluesky bot not ready."

        logging.info(f"Attempting to send post: '{message}' (Image: {image_post})")
        try:
            if image_post:
                # The class now receives state in __init__, so it can access house info
                # if 'house' is managed within the state object passed in
                if not hasattr(self.state, 'get_current_room_name') or not callable(self.state.get_current_room_name):
                     logging.error("State object does not have 'get_current_room_name' method for image post.")
                     return "An error occurred: Application state not correctly configured."

                current_room = self.state.get_current_room_name()
                alt = self.alt_text.get(current_room, "Image description not available.")
                # Ensure file path uses forward slashes or os.path.join for cross-platform compatibility
                image_path = os.path.join('style', 'images', f'{current_room}_bordered.jpg')


                if not os.path.exists(image_path):
                    logging.error(f"Image file not found: {image_path}")
                    return f"An error occurred: Image file not found for room '{current_room}'."

                # Lock is no longer needed
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                self.client.send_image( # Use self.client directly
                    text=message,
                    image=img_data,
                    image_alt=alt
                )

                logging.info(f"Image post sent successfully from {current_room}.")
                logging.info(f"Used alt text: {alt}")
                return "Message posted successfully on Bluesky with image."
            else:
                 # Lock is no longer needed
                 self.client.send_post(message, langs=langs_list) # Use self.client directly
                 self._send_signal({"type": "show_icon_popup", "icon_path": "style/images/action_icons/computer_icon.png"})

                 logging.info("Text post sent successfully.")
                 return "Message posted successfully on Bluesky."
        except Exception as e:
            logging.error(f"Failed to send post: {e}")
            return f"An error occurred while sending post: {e}"

    def update_description(self, description):
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot update description.")
            return "Bluesky bot not ready."

        logging.info(f"Attempting to update profile description to: '{description}'")
        try:
            # Lock is no longer needed
            # Use self.client directly
            current_profile_record = self.client.app.bsky.actor.profile.get(self.client.me.did, 'self')
            current_profile = current_profile_record.value
            swap_record_cid = current_profile_record.cid

            new_description = description

            # Use self.client directly
            self.client.com.atproto.repo.put_record(
                models.ComAtprotoRepoPutRecord.Data(
                    collection=models.ids.AppBskyActorProfile,
                    repo=self.client.me.did,
                    rkey='self',
                    swap_record=swap_record_cid,
                    record=models.AppBskyActorProfile.Record(
                        avatar=current_profile.avatar,
                        banner=current_profile.banner,
                        description=new_description,
                        display_name=current_profile.display_name,
                    ),
                )
            )

            logging.info("Profile description updated successfully.")
            return "Profile description updated successfully."
        except Exception as e:
            logging.error(f"Failed to update profile description: {e}")
            return f"An error occurred while updating profile description: {e}"

# Example Usage (in your main application file):
# from your_module import bluesky_bot # Assuming the class is in 'your_module.py'
# from state_module import AppState # Assuming your state object is in 'state_module.py'

# def main_signal_callback(data):
#     print(f"Received signal from bluesky_bot: {data}")
#     # Handle signals like showing popups based on 'data'

# app_state = AppState(...) # Instantiate your application state object
#
# # Instantiate the bot class
# bot_instance = bluesky_bot(state=app_state, signal=main_signal_callback)
#
# if bot_instance.is_ready:
#     # You can now call methods directly
#     response = bot_instance.post_bluesky("Hello from the non-threaded bot!", image_post=False)
#     print(response)
#
#     # If you want to update the description periodically, you need a timer mechanism
#     # in your main application's event loop or a separate Timer class.
#     # For example (conceptually, depends on your app's structure):
#     # def periodic_description_update():
#     #     current_room = app_state.get_current_room_name()
#     #     # Get emote or other info from state if needed
#     #     new_desc = f"Currently in the {current_room}." #+ ...
#     #     bot_instance.update_description(new_desc)
#     #
#     # # Set up a timer to call periodic_description_update every 30 minutes
#     # timer = Timer(30 * 60, periodic_description_update)
#     # timer.start()
#
# else:
#     print("Bluesky bot failed to initialize.")

# ... rest of your main application logic ...

# Note: You don't need bot_instance.stop() or bot_instance.join() anymore.
# The bot instance will be garbage collected when it's no longer referenced.