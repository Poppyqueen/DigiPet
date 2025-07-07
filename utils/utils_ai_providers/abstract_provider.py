from abc import ABC, abstractmethod
from pydantic import BaseModel

class SimpleAI(ABC):
    """
    ABC for structured and simple responses from various AI providers
    """

    def __init__(self, selected_model):
        self.ai_model=selected_model

    @abstractmethod
    def structured_output(self, system, user, structure: BaseModel) -> BaseModel:
        """
        Method to get a structured response from a given pydantic model                                                             
        Returns the requested structure as a pydantic object.                               
        """
        pass

    @abstractmethod
    def response_output(self, system: str, message: str) -> str:
        """
        Method to get a simple string response from a model.
        Must be implemented by subclasses.
        """
        pass