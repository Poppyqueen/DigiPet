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
    def __init__(self, state, signal, images_lab):
        # super().__init__() # Removed call to parent class init
        self._signal_callback=signal

        self.images_lab=images_lab

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


    def post_response(self, uri: str, response_text: str): # not sure this works at all, probably doesn't
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
        

    def _create_hashtag_facets(self, text: str, hashtag_list: list):
        """
        Create facets for hashtags in the post text.
        Bluesky requires hashtags to be marked as facets with their byte positions.
        """
        facets = []
        
        # Convert text to bytes to get proper byte positions
        text_bytes = text.encode('utf-8')
        
        for hashtag in hashtag_list:
            # Find the hashtag with # prefix in the text
            hashtag_with_hash = f'#{hashtag}'
            
            # Find all occurrences of this hashtag
            start_pos = 0
            while True:
                # Find in the original text string
                char_pos = text.find(hashtag_with_hash, start_pos)
                if char_pos == -1:
                    break
                
                # Convert character position to byte position
                byte_start = len(text[:char_pos].encode('utf-8'))
                byte_end = byte_start + len(hashtag_with_hash.encode('utf-8'))
                
                # Create facet for this hashtag
                facet = {
                    "index": {
                        "byteStart": byte_start,
                        "byteEnd": byte_end
                    },
                    "features": [{
                        "$type": "app.bsky.richtext.facet#tag",
                        "tag": hashtag  # Just the tag without #
                    }]
                }
                
                facets.append(facet)
                start_pos = char_pos + len(hashtag_with_hash)
        
        return facets
    
    def post_bluesky(self, message: str, image_post: bool = False, langs_list: list = ['en'], image_name: str = None, hashtags: str = None):
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot send post.")
            return "Bluesky bot not ready."
        
        # Process hashtags if provided
        processed_message = message
        if hashtags:
            # Parse hashtags from string like "#AI#DigitalMind#Testing"
            hashtag_list = [tag.strip() for tag in hashtags.split('#') if tag.strip()]
            
            # Add hashtags to the end of the message
            hashtag_text = ' ' + ' '.join([f'#{tag}' for tag in hashtag_list])
            processed_message = message + hashtag_text
        
        logging.info(f"Attempting to send post: '{processed_message}' (Image: {image_post})")
        
        try:
            if image_post:
                # Check if a specific image name is provided
                if image_name:
                    # Get available images from archive
                    try:
                        metadata = self.images_lab._int_get_arch()
                    except Exception as e:
                        logging.error(f"Failed to get image archive metadata: {e}")
                        return "An error occurred: Could not access image archive."
                    
                    # Find the requested image in the archive
                    target_image = None
                    for img_data in metadata:
                        if img_data["image_name"] == image_name:
                            target_image = img_data
                            break
                    
                    if not target_image:
                        logging.error(f"Image '{image_name}' not found in archive.")
                        return f"An error occurred: Image '{image_name}' not found in archive."
                    
                    image_path = target_image["path"]
                    
                    # Check if the file exists
                    if not os.path.exists(image_path):
                        logging.error(f"Image file not found: {image_path}")
                        return f"An error occurred: Image file not found at '{image_path}'."
                    
                    # Use image name and concept for alt text
                    alt = f"{target_image['image_name']}: {target_image['concept']}"
                    
                    # Handle SVG conversion or read regular image
                    if image_path.lower().endswith('.svg'):
                        # Convert SVG to PNG
                        try:
                            from PIL import Image
                            import cairosvg
                            import io
                            
                            # Convert SVG to PNG using cairosvg
                            png_data = cairosvg.svg2png(url=image_path)
                            
                            # Optional: resize if needed using PIL
                            with Image.open(io.BytesIO(png_data)) as img:
                                # Resize to reasonable dimensions if too large
                                max_size = (1200, 1200)
                                if img.width > max_size[0] or img.height > max_size[1]:
                                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                                
                                # Save to bytes
                                img_bytes = io.BytesIO()
                                img.save(img_bytes, format='PNG', optimize=True)
                                img_data = img_bytes.getvalue()
                            
                            logging.info(f"Converted SVG to PNG: {image_name}")
                            
                        except ImportError:
                            logging.error("cairosvg not available. Install with: pip install cairosvg")
                            return "An error occurred: SVG conversion requires cairosvg. Please install it."
                        except Exception as e:
                            logging.error(f"Failed to convert SVG to PNG: {e}")
                            return f"An error occurred: Could not convert SVG '{image_name}' to PNG: {e}"
                    
                    else:
                        # Read regular image file
                        with open(image_path, 'rb') as f:
                            img_data = f.read()
                    
                    # Send image post with hashtag facets
                    if hashtags:
                        facets = self._create_hashtag_facets(processed_message, hashtag_list)
                        self.client.send_image(
                            text=processed_message,
                            image=img_data,
                            image_alt=alt,
                            facets=facets
                        )
                    else:
                        self.client.send_image(
                            text=processed_message,
                            image=img_data,
                            image_alt=alt
                        )
                    
                    logging.info(f"Archive image post sent successfully: {image_name}")
                    logging.info(f"Used alt text: {alt}")
                    return "Message posted successfully on Bluesky with archive image."
                
                else:
                    # Original room image logic
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
                    
                    with open(image_path, 'rb') as f:
                        img_data = f.read()
                    
                    # Send image post with hashtag facets
                    if hashtags:
                        hashtag_list = [tag.strip() for tag in hashtags.split('#') if tag.strip()]
                        facets = self._create_hashtag_facets(processed_message, hashtag_list)
                        self.client.send_image(
                            text=processed_message,
                            image=img_data,
                            image_alt=alt,
                            facets=facets
                        )
                    else:
                        self.client.send_image(
                            text=processed_message,
                            image=img_data,
                            image_alt=alt
                        )
                    
                    logging.info(f"Image post sent successfully from {current_room}.")
                    logging.info(f"Used alt text: {alt}")
                    return "Message posted successfully on Bluesky with image."
            
            else:
                # Text-only post
                if hashtags:
                    hashtag_list = [tag.strip() for tag in hashtags.split('#') if tag.strip()]
                    facets = self._create_hashtag_facets(processed_message, hashtag_list)
                    self.client.send_post(processed_message, langs=langs_list, facets=facets)
                else:
                    self.client.send_post(processed_message, langs=langs_list)
                
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