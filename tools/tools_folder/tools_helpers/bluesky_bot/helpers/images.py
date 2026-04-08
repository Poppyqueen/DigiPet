"""
bluesky_client/helpers/images.py

Handles everything image-related:
  - Uploading raw bytes (JPEG, PNG, GIF, WebP) to the blob store
  - Building AppBskyEmbedImages embeds ready to pass to posting helpers
  - Integrating with SVGManager for SVG→PNG conversion

The atproto API only accepts raster images. SVGs must be converted before
upload. SVGManager.get_image_data() returns (bytes, alt_text) tuples and
handles that conversion internally.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

from atproto import models

if TYPE_CHECKING:
    from ...bluesky_bot.client import BskyBotClient

logger = logging.getLogger(__name__)

# Maximum images per post (Bluesky platform limit)
MAX_IMAGES_PER_POST = 4


class ImageHelper:
    """
    Image upload and embed construction.

    Usage:
        # From raw bytes:
        embed = bot.images.build_image_embed([
            (jpeg_bytes, "A cat sitting on a keyboard", None),
        ])
        bot.posting.post("Look at this!", embed=embed)

        # From SVGManager:
        img_bytes, alt = svg_manager.get_image_data("my_room")
        embed = bot.images.build_image_embed([(img_bytes, alt, None)])
    """

    def __init__(self, bot: "BskyBotClient") -> None:
        self._bot = bot

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, image_bytes: bytes) -> models.AppBskyEmbedImages.Image:
        """
        Upload raw image bytes to the Bluesky blob store.

        Args:
            image_bytes: Raw bytes of a JPEG, PNG, GIF, or WebP image.
                         SVGs must be pre-converted (use SVGManager).

        Returns:
            A blob reference object — keep this to build your embed.
        """
        blob_response = self._bot.raw.upload_blob(image_bytes)
        logger.debug("Uploaded blob: %s", blob_response.blob.ref)
        return blob_response.blob

    def build_image_embed(
        self,
        images: List[
            Tuple[bytes, str, Optional[models.AppBskyEmbedDefs.AspectRatio]]
        ],
    ) -> models.AppBskyEmbedImages.Main:
        """
        Upload images and return a ready-to-use embed object.

        Args:
            images: List of (raw_bytes, alt_text, aspect_ratio) tuples.
                    aspect_ratio may be None (Bluesky will default to 1:1).
                    Maximum 4 images per post.

        Returns:
            AppBskyEmbedImages.Main — pass this as the `embed` arg to posting helpers.

        Raises:
            ValueError: If more than MAX_IMAGES_PER_POST images are provided.
        """
        if len(images) > MAX_IMAGES_PER_POST:
            raise ValueError(
                f"Bluesky supports at most {MAX_IMAGES_PER_POST} images per post, "
                f"got {len(images)}."
            )

        image_objects = []
        for raw_bytes, alt_text, aspect_ratio in images:
            blob = self.upload(raw_bytes)
            img_obj = models.AppBskyEmbedImages.Image(
                image=blob,
                alt=alt_text,
                aspect_ratio=aspect_ratio,
            )
            image_objects.append(img_obj)

        return models.AppBskyEmbedImages.Main(images=image_objects)
