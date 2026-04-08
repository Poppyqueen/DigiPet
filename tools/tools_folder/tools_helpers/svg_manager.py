# TODO: this is related to a image book item thing, find it and put everything related to it in one place.

import os

import logging

from tools.tools_folder.tools_data.blsk_alt_text import alt_text


class SVGManager():
    def __init__(self):
        self.alt_text=alt_text

    def _prepare_image_data(self, images_metadata, image_name: str = None):
        """Helper method to prepare image data for posting."""
        try:
            # Get specific image from archive
            metadata = images_metadata
            target_image = None
            
            for img_data in metadata:
                if img_data["image_name"] == image_name:
                    target_image = img_data
                    break
            
            if not target_image:
                return None, f"Image '{image_name}' not found in archive."
            
            image_path = target_image["path"]
            if not os.path.exists(image_path):
                return None, f"Image file not found at '{image_path}'."
            
            alt = f"{target_image['image_name']}: {target_image['concept']}"
            
            # Handle SVG conversion
            if image_path.lower().endswith('.svg'):
                img_data = self._convert_svg_to_png(image_path)
                if img_data is None:
                    return None, "Failed to convert SVG to PNG."
            else:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
            
            return img_data, alt

        except Exception as e:
            logging.error(f"Error preparing image data: {e}")
            return None, f"Error preparing image: {e}"

    def _convert_svg_to_png(self, svg_path: str):
        """Convert SVG to PNG format."""
        try:
            from PIL import Image
            import cairosvg
            import io
            
            png_data = cairosvg.svg2png(url=svg_path)
            
            with Image.open(io.BytesIO(png_data)) as img:
                max_size = (1200, 1200)
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG', optimize=True)
                return img_bytes.getvalue()
            
        except ImportError:
            logging.error("cairosvg not available. Install with: pip install cairosvg")
            return None
        except Exception as e:
            logging.error(f"Failed to convert SVG to PNG: {e}")
            return None

