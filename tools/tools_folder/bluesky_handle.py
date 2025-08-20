import os
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv
from atproto import Client, models, AtUri
from datetime import datetime, timezone

from tools.tools_folder.tools_data.blsk_alt_text import alt_text

from tools.tools_folder.tools_helpers.svg_manager import SVGManager
# Configure logging (keep it outside the class)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class bluesky_bot:
    def __init__(self, state, signal, images_lab):
        self._signal_callback = signal
        self.images_lab = images_lab
        self.alt_text = alt_text
        self.state = state

        self.svg_manager=SVGManager()

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
            self.client = Client()
            self.client.login(self.HANDLE, self.PASSWORD)
            logging.info(f"Logged in as {self.HANDLE} (Bluesky Bot)")
            self.is_ready = True
        except Exception as e:
            logging.error(f"Login failed for {self.HANDLE}: {e}")
            self.is_ready = False


    def _send_signal(self, signal_data):
        """Helper method to send signals using the registered callback."""
        if self._signal_callback:
            try:
                self._signal_callback(signal_data)
            except Exception as e:
                logging.error(f"Error sending signal from {self.__class__.__name__}: {e}")

    def extract_did_from_uri(self, uri: str) -> str:
        """Extract DID from AT-Proto URI."""
        try:
            at_uri = AtUri.from_str(uri)
            return at_uri.hostname
        except Exception as e:
            logging.error(f"Failed to extract DID from URI {uri}: {e}")
            raise



    def update_description(self, description: str):
        """Update the profile description."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot update description.")
            return "Bluesky bot not ready."

        logging.info(f"Attempting to update profile description to: '{description}'")
        
        try:
            current_profile_record = self.client.app.bsky.actor.profile.get(self.client.me.did, 'self')
            current_profile = current_profile_record.value
            swap_record_cid = current_profile_record.cid

            self.client.com.atproto.repo.put_record(
                models.ComAtprotoRepoPutRecord.Data(
                    collection=models.ids.AppBskyActorProfile,
                    repo=self.client.me.did,
                    rkey='self',
                    swap_record=swap_record_cid,
                    record=models.AppBskyActorProfile.Record(
                        avatar=current_profile.avatar,
                        banner=current_profile.banner,
                        description=description,
                        display_name=current_profile.display_name,
                    ),
                )
            )

            logging.info("Profile description updated successfully.")
            return "Profile description updated successfully."
            
        except Exception as e:
            logging.error(f"Failed to update profile description: {e}")
            return f"An error occurred while updating profile description: {e}"

    def post_reply(self, uri: str, response_text: str):
        """Post a reply to a specific post."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot post response.")
            return "Bluesky bot not ready."

        logging.info(f"Attempting to post reply to {uri}...")
        
        try:
            parent_uri = AtUri.from_str(uri)

            params = {
                "repo": parent_uri.hostname,  # <-- Use the hostname from the URI for the repo DID
                "collection": "app.bsky.feed.post",
                "rkey": parent_uri.rkey,
            }

            # The SDK returns a model object directly
            parent_post_resp = self.client.com.atproto.repo.get_record(params=params)

            # --- FIX STARTS HERE ---
            
            # Access attributes directly from the response object
            record_data = parent_post_resp 
            print("Parent post record data:")
            print(record_data)
            print(type(record_data)) # This should now be an atproto model object, not str
            
            print("try to access .cid, maybe an issue here:")
            print(record_data.cid)
            print("accessed record_data.cid correctly")

            print("try to access .uri, maybe an issue here:")
            print(record_data.uri)
            print("accessed record_data.uri")

            parent_cid = record_data.cid # <-- Access .cid attribute
            if not parent_cid:
                logging.error("Parent CID not found in the record.")
                return "Error: Parent CID not found."

            parent_ref = models.ComAtprotoRepoStrongRef.Main(
                uri=str(record_data.uri),
                cid=str(parent_cid)
            )
            
            root_ref = parent_ref
            
            # Access the record content from the .value attribute
            parent_record = record_data.value 
            if parent_record and parent_record.reply and parent_record.reply.root:
                root_ref = parent_record.reply.root

            # --- FIX ENDS HERE ---

            reply_ref = models.AppBskyFeedPost.ReplyRef(
                parent=parent_ref,
                root=root_ref
            )

            record = models.AppBskyFeedPost.Record(
                text=response_text,
                created_at=self.client.get_current_time_iso(),
                reply=reply_ref,
                #facets=
            )

            resp = self.client.app.bsky.feed.post.create(
                repo=self.client.me.did,
                record=record,
            )

            logging.info("Reply posted successfully.")
            return "Reply posted successfully on Bluesky."
            
        except Exception as e:
        # It's helpful to log the full traceback for easier debugging
            logging.error(f"Failed to post reply: {e}", exc_info=True)
            return f"An error occurred while posting reply: {e}"
        

    def _create_hashtag_facets(self, text: str, hashtag_list: list):
        """Create facets for hashtags in the post text."""
        facets = []
        text_bytes = text.encode('utf-8')
        
        for hashtag in hashtag_list:
            hashtag_with_hash = f'#{hashtag}'
            start_pos = 0
            
            while True:
                char_pos = text.find(hashtag_with_hash, start_pos)
                if char_pos == -1:
                    break
                
                byte_start = len(text[:char_pos].encode('utf-8'))
                byte_end = byte_start + len(hashtag_with_hash.encode('utf-8'))
                
                facet = {
                    "index": {
                        "byteStart": byte_start,
                        "byteEnd": byte_end
                    },
                    "features": [{
                        "$type": "app.bsky.richtext.facet#tag",
                        "tag": hashtag
                    }]
                }
                
                facets.append(facet)
                start_pos = char_pos + len(hashtag_with_hash)
        
        return facets
        
    def _extract_thread_info(self, replies, our_handle, depth=0, max_depth=5):
        """Extract complete thread information including all replies."""

        print("Running _extract_thread_info")
        thread_info = {
            "has_mention": False,
            "all_replies": []
        }

        if depth > max_depth:
            return thread_info

        our_did = self.client.me.did

        for reply in replies:
            if not hasattr(reply, 'post'):
                continue

            reply_post = reply.post

            mentions_us = False
            if hasattr(reply_post.record, 'facets') and reply_post.record.facets:
                for facet in reply_post.record.facets:
                    if hasattr(facet, 'features'):
                        for feature in facet.features:
                            if (hasattr(feature, 'did') and
                                feature.did == our_did and
                                reply_post.author.did != our_did):
                                mentions_us = True
                                break
                    if mentions_us:
                        break
            
            # This is the new, critical line!
            if mentions_us:
                thread_info["has_mention"] = True

            # Fallback to text-based detection if facets don't work
            if not mentions_us:
                reply_text = reply_post.record.text.lower()
                full_handle = f"@{self.HANDLE.lower()}"
                mentions_us = (full_handle in reply_text and
                            reply_post.author.did != our_did)
                if mentions_us:
                    # Update the master flag here as well for the fallback
                    thread_info["has_mention"] = True


            response_info = {
                "uri": reply_post.uri,
                "author": reply_post.author.handle,
                "text": reply_post.record.text,
                "created_at": reply_post.record.created_at,
                "depth": depth,
                "mentions_us": mentions_us,
                "is_our_reply": reply_post.author.did == our_did
            }

            thread_info["all_replies"].append(response_info)

            # Check nested replies recursively
            if hasattr(reply, 'replies') and reply.replies:
                nested_info = self._extract_thread_info(
                    reply.replies, our_handle, depth + 1, max_depth
                )
                if nested_info["has_mention"]:
                    thread_info["has_mention"] = True
                thread_info["all_replies"].extend(nested_info["all_replies"])

        return thread_info

    def _format_posts_for_ai(self, posts_data):
        """Format posts data into structured string for AI consumption."""
        if not posts_data:
            return "NO POSTS NEED RESPONSES"
        
        formatted_output = []
        formatted_output.append("=== POSTS REQUIRING RESPONSES ===\n")
        
        for i, post_data in enumerate(posts_data, 1):
            original = post_data["original_post"]
            responses = post_data["responses_needing_reply"]
            
            formatted_output.append(f"POST #{i}")
            formatted_output.append(f"URI: {original['uri']}")
            formatted_output.append(f"ORIGINAL POST: {original['text']}")
            formatted_output.append(f"POSTED: {original['created_at']}")
            formatted_output.append(f"STATS: {original['stats']['likes']} likes, {original['stats']['replies']} replies")
            formatted_output.append("")
            
            formatted_output.append(f"COMPLETE THREAD HISTORY ({len(responses)}):")
            
            for j, response in enumerate(responses, 1):
                depth_indicator = "  " + "└─ " * response['depth']
                
                # Mark different types of responses
                author_marker = ""
                if response['is_our_reply']:
                    author_marker = " [OUR REPLY]"
                elif response['mentions_us']:
                    author_marker = " [MENTIONS US]"
                
                formatted_output.append(f"{depth_indicator}REPLY #{j}{author_marker}")
                formatted_output.append(f"{depth_indicator}FROM: @{response['author']}")
                if not response['is_our_reply']:  # Don't include URI for our own replies
                    formatted_output.append(f"{depth_indicator}URI: {response['uri']}")
                formatted_output.append(f"{depth_indicator}TEXT: {response['text']}")
                formatted_output.append(f"{depth_indicator}POSTED: {response['created_at']}")
                formatted_output.append("")
            
            formatted_output.append("=" * 50)
            formatted_output.append("")
        return "\n".join(formatted_output)
    

    
        ### ----- AI TOOLS ----- ###

    def get_account_summary(self, limit: int = 10):
        """Get the top posts info for the latest n posts in the account."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot get account summary.")
            return None

        try:
            # Get own profile first
            profile = self.client.get_profile(self.client.me.handle)
            
            # Get own posts
            posts = self.client.get_author_feed(
                actor=self.client.me.did,
                limit=limit
            )
            
            summary = {
                "profile": {
                    "handle": profile.handle,
                    "display_name": profile.display_name,
                    "description": profile.description,
                    "followers_count": profile.followers_count,
                    "follows_count": profile.follows_count,
                    "posts_count": profile.posts_count
                },
                "recent_posts": []
            }
            
            for post in posts.feed:
                if post.post.author.did == self.client.me.did:  # Only our own posts
                    post_data = {
                        "uri": post.post.uri,
                        "text": post.post.record.text,
                        "created_at": post.post.record.created_at,
                        "like_count": post.post.like_count or 0,
                        "reply_count": post.post.reply_count or 0,
                        "repost_count": post.post.repost_count or 0
                    }
                    summary["recent_posts"].append(post_data)
            
            return summary
            
        except Exception as e:
            logging.error(f"Failed to get account summary: {e}")
            return None

    def get_posts_needing_responses(self, pagination: int = 2):
        """Get ONLY posts that need responses, formatted as structured string for AI."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot get posts needing responses.")
            return "ERROR: Bot not ready"

        try:
            # Get our recent posts
            posts = self.client.get_author_feed(
                actor=self.client.me.did,
                limit=pagination
            )
            
            response_needed_posts = []
            our_handle = self.HANDLE.lower()
            
            for post in posts.feed:
                if post.post.author.did != self.client.me.did:
                    continue  # Skip posts that aren't ours
                
                # Skip posts with no replies
                if not post.post.reply_count or post.post.reply_count == 0:
                    continue
                
                valid_responses = []
                                
                try:
                    # Get thread to check replies
                    response = self.client.get_post_thread(post.post.uri)
                    thread_view = response.thread

                    if hasattr(thread_view, 'replies') and thread_view.replies:
                        thread_info = self._extract_thread_info(thread_view.replies, our_handle)

                        # --- NEW DEBUGGING BLOCK ---
                        print("\n--- RETURNED THREAD_INFO ANALYSIS ---")
                        print(f"Value of thread_info object: {thread_info}")
                        print(f"Is 'has_mention' True? -> {thread_info.get('has_mention')}")
                        print(f"Content of 'all_replies': {thread_info.get('all_replies')}")
                        print(f"Number of items in 'all_replies': {len(thread_info.get('all_replies', []))}")
                        print("--- END ANALYSIS ---\n")
                        # --- END NEW DEBUGGING BLOCK ---

                        # Only include posts where someone mentioned us in the thread
                        if thread_info["has_mention"]:
                            valid_responses = thread_info["all_replies"]

                except Exception as e:
                    logging.warning(f"Failed to get replies for post {post.post.uri}: {e}")
                    continue
                
                # Only include posts that have valid responses needing our attention
                if valid_responses:
                    post_data = {
                        "original_post": {
                            "uri": post.post.uri,
                            "text": post.post.record.text,
                            "created_at": post.post.record.created_at,
                            "stats": {
                                "likes": post.post.like_count or 0,
                                "replies": post.post.reply_count or 0
                            }
                        },
                        "responses_needing_reply": valid_responses
                    }
                    response_needed_posts.append(post_data)

                    print(f"Printing post_data inside get posts needing responses:")
                    print(post_data)
            
            # Convert to structured string for AI
            return self._format_posts_for_ai(response_needed_posts)
            
        except Exception as e:
            logging.error(f"Failed to get posts needing responses: {e}")
            return f"ERROR: {str(e)}"
        
    def respond_to_post(self, target_uri: str, response_text: str):
        """Clean function to respond to a specific post URI."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot respond to post.")
            return "ERROR: Bot not ready"
        
        if not target_uri or not response_text:
            logging.warning("Missing target URI or response text.")
            return "ERROR: Missing required parameters"
        
        # Use the existing post_reply method
        return self.post_reply(target_uri, response_text)

    def post_bluesky(self, message: str, image_post: bool = False, langs_list: list = ['en'], 
                    image_name: str = None, hashtags: str = None):
        """Post a message to Bluesky with optional image and hashtags."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot send post.")
            return "Bluesky bot not ready."
        
        # Process hashtags if provided
        processed_message = message
        hashtag_list = []
        
        if hashtags:
            hashtag_list = [tag.strip() for tag in hashtags.split('#') if tag.strip()]
            hashtag_text = ' ' + ' '.join([f'#{tag}' for tag in hashtag_list])
            processed_message = message + hashtag_text 
        
        logging.info(f"Attempting to send post: '{processed_message}' (Image: {image_post})")
        
        metadata=self.images_lab._int_get_arch()
        current_room_name=self.state.get_current_room_name()
        try:
            if image_post:
                img_data, alt = self.svg_manager._prepare_image_data(current_room_name,metadata,image_name)
                if img_data is None:
                    return alt  # Error message is returned in alt
                
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
                
                logging.info(f"Image post sent successfully: {image_name or 'room image'}")
                return "Message posted successfully on Bluesky with image."
            
            else:
                # Text-only post
                if hashtags:
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

    def get_notifications(self, limit: int = 20):
        """Get recent notifications that mention our account."""
        if not self.is_ready:
            logging.warning("Bluesky bot not ready, cannot get notifications.")
            return None

        try:
            notifications = self.client.app.bsky.notification.list_notifications(limit=limit)
            
            filtered_notifications = []
            for notif in notifications.notifications:
                # Filter for replies and mentions
                if notif.reason in ['reply', 'mention']:
                    notif_data = {
                        "type": notif.reason,
                        "uri": notif.uri,
                        "author": notif.author.handle,
                        "created_at": notif.indexed_at,
                        "read": notif.is_read
                    }
                    
                    # Get the post content if available
                    if hasattr(notif, 'record') and notif.record:
                        notif_data["text"] = getattr(notif.record, 'text', '')
                    
                    filtered_notifications.append(notif_data)
            
            return filtered_notifications
            
        except Exception as e:
            logging.error(f"Failed to get notifications: {e}")
            return None