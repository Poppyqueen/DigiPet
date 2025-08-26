from abc import ABC, abstractmethod


class ImagesAI(ABC):
    """
    Abstract base class for all image AI models.
    """

    def __init__(self, model):
        self.ai_model = model

    @abstractmethod
    def generate_image(self, prompt: str) -> bytes:
        """
        Generate an image based on the given prompt.

        Args:
            prompt (str): The text prompt to generate the image from.

        Returns:
            bytes: The generated image as a byte array.
        """
        pass