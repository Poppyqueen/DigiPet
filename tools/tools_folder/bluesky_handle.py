import os
import logging
import threading
from urllib.parse import urlparse
from dotenv import load_dotenv
from atproto import Client, models, AtUri

# Configure logging (keep it outside the class)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class bluesky_bot(threading.Thread):


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

    def __init__(self, state):
        super().__init__()
        self.name = "BlueskyBotThread"

        
        self.state = state
        self._stop_event = threading.Event()
        self._update_interval = 30 * 60 # 30 minutes * 60 seconds/minute

        # !!! ADD A LOCK !!!
        self._lock = threading.Lock()

        # Load environment variables
        load_dotenv()
        self.HANDLE = os.getenv('HANDLE')
        self.PASSWORD = os.getenv('PASSWORD')

        if not self.HANDLE or not self.PASSWORD:
            logging.error("HANDLE or PASSWORD not set in environment variables.")
            self.is_ready = False
            return

        # Initialize client and login
        # Login also needs to be protected if it involves setting client state
        try:
            # Acquire lock before using self.client for login
            with self._lock:
                 self.client = Client()
                 self.client.login(self.HANDLE, self.PASSWORD)

            logging.info(f"Logged in as {self.HANDLE} (Bluesky Bot Thread)")
            self.is_ready = True
        except Exception as e:
            logging.error(f"Login failed for {self.HANDLE}: {e}")
            self.is_ready = False

        if self.is_ready:
             logging.info("Starting Bluesky Bot Thread...")
             self.start()

        # !!! PROPOSED CHANGE HERE !!!
        # Call the timed action immediately in the main thread
        if self.is_ready: # Only call if initialization was successful
            logging.info("Performing initial timed action from __init__...")
            try:
                self._perform_timed_action()
                logging.info("Initial timed action completed.")
            except Exception as e:
                logging.error(f"Error performing initial timed action from __init__: {e}")

    def run(self):
        if not self.is_ready:
            logging.warning("Bluesky Bot Thread not ready. Exiting run method.")
            return

        logging.info(f"Bluesky Bot Thread started. Will perform timed actions every {self._update_interval} seconds.")

        while not self._stop_event.is_set():
            try:
                # The action performed needs to acquire the lock internally
                self._perform_timed_action()

            except Exception as e:
                logging.error(f"Error during timed Bluesky action: {e}")

            self._stop_event.wait(self._update_interval)

        logging.info("Bluesky Bot Thread received stop signal. Shutting down.")


    def stop(self):
        logging.info("Signaling Bluesky Bot Thread to stop...")
        self._stop_event.set()

    def _perform_timed_action(self):
        # logging.info("Performing timed Bluesky action: Updating profile description...")
        # try:
        #     if not hasattr(self, 'house') or self.house is None:
        #          logging.error("House handle not available for timed action.")
        #          return
        #     lines=[]

        #     current_room = self.house.get_current_room(True)
        #     current_emote = self.emoter.get_current_emote(True)
        #     new_description = f"Currently located in the {current_room}."
        #     lines.append(new_description)
        #     lines.append(current_emote)
        #     lines.append("– Updated every 30 minutes –")
        #     final_description="\n".join(lines)
        #     logging.info(f"Generated new description: '{new_description}'")

        #     # update_description will acquire the lock internally

        #     self.update_description(final_description) # Call the method
        #     logging.info("Profile description updated successfully by timed action.")

        # except Exception as e:
        #     logging.error(f"Failed to perform timed action: {e}")
        print("dummy") # We peovavly want to update the description with some other data, anyhow, we need to change the implementation of "house handle" and "emoter" for "state" which now manages both


    # --- Existing methods, modified to use the lock ---

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
            # Acquire lock before using self.client for API calls
            with self._lock:
                parent_uri = AtUri.from_str(uri)
                parent_did = self.extract_did_from_uri(uri)

                params = {
                    "repo": parent_did,
                    "collection": "app.bsky.feed.post",
                    "rkey": parent_uri.rkey,
                }

                # This API call uses self.client
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
                root_ref = parent_ref

                reply_ref = models.AppBskyFeedPost.ReplyRef(
                    parent=parent_ref,
                    root=root_ref
                )

                record = models.AppBskyFeedPost.Record(
                    text=response_text,
                    created_at=self.client.get_current_time_iso(), # Also uses self.client
                    reply=reply_ref,
                )

                # This API call uses self.client
                resp = self.client.app.bsky.feed.post.create(
                    repo=self.client.me.did, # Also uses self.client
                    collection=models.ids.AppBskyFeedPost,
                    record=record,
                )
            # Lock is released here

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
                if not hasattr(self, 'house') or self.house is None:
                     logging.error("House handle not available for image post.")
                     return "An error occurred: House handle not available."

                current_room = self.state.get_current_room_name()
                alt = self.alt_text.get(current_room, "Image description not available.")
                image_path = f'style/images/{current_room}_bordered.jpg'

                if not os.path.exists(image_path):
                    logging.error(f"Image file not found: {image_path}")
                    return f"An error occurred: Image file not found for room '{current_room}'."

                # Acquire lock before using self.client for API calls (send_image)
                with self._lock:
                    with open(image_path, 'rb') as f:
                        img_data = f.read()
                    self.client.send_image( # This API call uses self.client
                        text=message,
                        image=img_data,
                        image_alt=alt
                    )
                # Lock is released here

                logging.info(f"Image post sent successfully from {current_room}.")
                logging.info(f"Used alt text: {alt}")
                return "Message posted successfully on Bluesky with image."
            else:
                 # Acquire lock before using self.client for API calls (send_post)
                 with self._lock:
                     self.client.send_post(message, langs=langs_list) # This API call uses self.client
                 # Lock is released here

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
            # Acquire lock before using self.client for API calls
            with self._lock:
                # This API call uses self.client
                current_profile_record = self.client.app.bsky.actor.profile.get(self.client.me.did, 'self') # Uses self.client
                current_profile = current_profile_record.value
                swap_record_cid = current_profile_record.cid

                new_description = description

                # This API call uses self.client
                self.client.com.atproto.repo.put_record( # Uses self.client
                    models.ComAtprotoRepoPutRecord.Data(
                        collection=models.ids.AppBskyActorProfile,
                        repo=self.client.me.did, # Uses self.client
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
            # Lock is released here

            logging.info("Profile description updated successfully.")
            return "Profile description updated successfully."
        except Exception as e:
            logging.error(f"Failed to update profile description: {e}")
            return f"An error occurred while updating profile description: {e}"

# Example of shutdown in your main application:
# bot_instance = bluesky_bot(...)
# ... main program logic ...
# # Before exiting:
# bot_instance.stop() # Signal the thread to stop
# bot_instance.join() # Wait for the thread to complete its current cycle and exit run()