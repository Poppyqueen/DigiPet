import os


# ai_loader.py
from typing import Type, TypeVar, Union, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod
import os
import importlib
from dotenv import load_dotenv

from ai_managers.simple_ai.abstract_provider import SimpleAI
from ai_managers.agents.agent_clients.abstract_llm_client import AbstractLLMClient

# Load environment variables
load_dotenv()

ComponentType = Literal["ai_providers", "tokenizers", "embeddings"]

class UnifiedLoader:
    """
    Unified loader for all AI components with shared logic.
    """
    
    COMPONENT_DEFINITIONS = {
        "ai_providers": {
            "gemini": {
                "simple_ai_module": "ai_managers.simple_ai.providers.gemini_provider",
                "simple_ai_class": "GeminiProv",
                "agent_module": "ai_managers.agents.agent_clients.gemini_client",
                "agent_class": "GeminiClient",
                "required_libraries": ["google.genai"],
                "api_key_env": "GEMINI_API_KEY",
                "requires_api_key": True
            },
            "openai": {
                "simple_ai_module": "ai_managers.simple_ai.providers.openai_provider",
                "simple_ai_class": "OpenAIProv",
                "agent_module": "ai_managers.agents.agent_clients.openai_client",
                "agent_class": "OpenAIClient",
                "required_libraries": ["openai"],
                "api_key_env": "OPENAI_API_KEY",
                "requires_api_key": True
            },
            "groq": {
                "simple_ai_module": "ai_managers.simple_ai.providers.groq_provider",
                "simple_ai_class": "GroqProv",
                "agent_module": "ai_managers.agents.agent_clients.groq_client",
                "agent_class": "GroqClient",
                "required_libraries": ["groq", "instructor"],
                "api_key_env": "GROQ_API_KEY",
                "requires_api_key": True
            },
            "ollama": {
                "simple_ai_module": "ai_managers.simple_ai.providers.ollama_provider",
                "simple_ai_class": "OllamaProv",
                "agent_module": "ai_managers.agents.agent_clients.ollama_client",
                "agent_class": "OllamaClient",
                "required_libraries": ["ollama"],
                "api_key_env": None,
                "requires_api_key": False
            },
            "openrouter": {
                "simple_ai_module": "ai_managers.simple_ai.providers.openrouter_provider",
                "simple_ai_class": "OpenRouterProv",
                "agent_module": "ai_managers.agents.agent_clients.openrouter_client",
                "agent_class": "OpenRouterClient",
                "required_libraries": ["openai", "instructor"],
                "api_key_env": "OPENROUTER_API_KEY",
                "requires_api_key": True
            },
            "llama_cpp": {
                "simple_ai_module": "ai_managers.simple_ai.providers.llama_cpp_provider",
                "simple_ai_class": "LlamaCppProv",
                "agent_module": "ai_managers.agents.agent_clients.llama_cpp_client",
                "agent_class": "LlamaCppClient",
                "required_libraries": ["openai"],
                "api_key_env": None,
                "requires_api_key": False
            },
            "claude":{
                "simple_ai_module":"ai_managers.simple_ai.providers.claude_provider",
                "simple_ai_class":"AnthropicProv",
                "agent_module":"ai_managers.agents.agent_clients.anthropic_client",
                "agent_class":"AnthropicClient",
                "required_libraries":["anthropic"],
                "api_key_env": "ANTHROPIC_API_KEY",
                "requires_api_key":True
            }
        },
        
        "tokenizers": {
            "gemini": {
                "module": "ai_managers.tokens.token_providers.gemini_tokenizer",
                "class": "GeminiTokenizer",
                "required_libraries": ["google.genai"],
                "needs_model": True
            },
            "openai": {
                "module": "ai_managers.tokens.token_providers.openai_tokenizer",
                "class": "OpenAITokenizer",
                "required_libraries": ["tiktoken"],
                "needs_model": False
            },
            "groq": {
                "module": "ai_managers.tokens.token_providers.opensource_tokenizer",
                "class": "OpenSourceTokenizer",
                "required_libraries": ["tokenizers"],
                "needs_model": True
            },
            "ollama": {
                "module": "ai_managers.tokens.token_providers.opensource_tokenizer",
                "class": "OpenSourceTokenizer",
                "required_libraries": ["tokenizers"],
                "needs_model": True
            },
            "openrouter": {
                "module": "ai_managers.tokens.token_providers.openrouter_tokenizer",
                "class": "OpenRouterTokenizer",
                "required_libraries": ["tiktoken", "google.genai", "tokenizers"],
                "needs_model": True
            },
            "llama_cpp": {
                "module": "ai_managers.tokens.token_providers.opensource_tokenizer",
                "class": "OpenSourceTokenizer",
                "required_libraries": ["tokenizers"],
                "needs_model": True
            },
            "claude":{
                "module": "ai_managers.tokens.token_providers.claude_tokenizer",
                "class": "AnthropicTokenizer",
                "required_libraries": ["anthropic"],
                "needs_model": True                
            }
        },
        "embeddings": {
            "gemini": {
                "module": "ai_managers.embeddings.providers.google_embeddings",
                "class": "GoogleEmbeddingProvider",
                "required_libraries": ["google.genai"]
            },
            "openai": {
                "module": "ai_managers.embeddings.providers.openai_embeddings",
                "class": "OpenAIEmbeddingProvider",
                "required_libraries": ["openai"]
            },
            "ollama": {
                "module": "ai_managers.embeddings.providers.ollama_embeddings",
                "class": "OllamaEmbeddingProvider",
                "required_libraries": ["ollama"]
            }
        },

        "images": {
            "gemini": {
                "module": "ai_managers.images_ai.providers.gemini",
                "class": "GeminiImages",
                "required_libraries": ["google.genai"],
                "needs_model": True
            }
        }
    }
    
    # Cache for loaded components
    _loaded_components: Dict[ComponentType, Dict[str, Dict[str, Any]]] = {}
    
    @staticmethod
    def _check_library_availability(libraries: list[str]) -> bool:
        """Check if all required libraries are available."""
        return all(
            importlib.util.find_spec(lib) is not None 
            for lib in libraries
        )
    
    @staticmethod
    def _import_class(module_path: str, class_name: str) -> Optional[Type]:
        """Dynamically import a class from a module."""
        try:
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            print(f"Warning: Could not import {class_name} from {module_path}: {e}")
            return None
    
    @classmethod
    def load_components(cls, component_type: ComponentType) -> Dict[str, Dict[str, Any]]:
        """Load available components of a specific type."""
        if component_type in cls._loaded_components:
            return cls._loaded_components[component_type]
        
        available_components = {}
        definitions = cls.COMPONENT_DEFINITIONS[component_type]
        
        for provider_name, config in definitions.items():
            if not cls._check_library_availability(config["required_libraries"]):
                print(f"Skipping {component_type} {provider_name}: Required libraries {config['required_libraries']} not available")
                continue
            
            loaded_config = cls._load_component_config(component_type, provider_name, config)
            if loaded_config:
                available_components[provider_name] = loaded_config
                print(f"✓ Loaded {component_type} {provider_name}")
            else:
                print(f"✗ Failed to load {component_type} {provider_name}")
        
        cls._loaded_components[component_type] = available_components
        return available_components
    
    @classmethod
    def _load_component_config(cls, component_type: ComponentType, provider_name: str, config: Dict) -> Optional[Dict]:
        """Load configuration for a specific component type."""
        if component_type == "ai_providers":
            simple_ai_class = cls._import_class(config["simple_ai_module"], config["simple_ai_class"])
            agent_class = cls._import_class(config["agent_module"], config["agent_class"])
            
            if simple_ai_class is not None or agent_class is not None:
                return {
                    "simple_ai": simple_ai_class,
                    "agent": agent_class,
                    "api_key_env": config["api_key_env"],
                    "requires_api_key": config["requires_api_key"]
                }
        
        elif component_type in ["tokenizers", "embeddings"]:
            component_class = cls._import_class(config["module"], config["class"])
            if component_class is not None:
                result = {"class": component_class}
                if component_type == "tokenizers":
                    result["needs_model"] = config["needs_model"]
                return result
            
        elif component_type == "images":
            component_class = cls._import_class(config["module"], config["class"])
            if component_class is not None:
                return {
                    "class": component_class,
                    "needs_model": config["needs_model"]
                }
        
        return None
    
    @classmethod
    def get_available_providers(cls, component_type: ComponentType) -> list[str]:
        """Get list of available providers for a component type."""
        components = cls.load_components(component_type)
        return list(components.keys())
    
    @classmethod
    def refresh_components(cls, component_type: ComponentType = None):
        """Refresh component cache."""
        if component_type:
            cls._loaded_components.pop(component_type, None)
            print(f"{component_type} cache refreshed")
        else:
            cls._loaded_components.clear()
            print("All component caches refreshed")


class BaseConfiguration:
    """Base class for all configuration types with shared functionality."""
    
    def __init__(self, component_type: ComponentType, provider: str):
        self.component_type = component_type
        self.provider = provider.lower()
        self._components = None
        self._load_components()
        self._validate_provider()
    
    def _load_components(self):
        """Load components if not already loaded."""
        self._components = UnifiedLoader.load_components(self.component_type)
    
    def _validate_provider(self):
        """Validate that the provider is available."""
        if not self._components:
            raise ValueError(f"No {self.component_type} available. Please install the required libraries.")
        
        if self.provider not in self._components:
            available = ', '.join(self._components.keys())
            raise ValueError(f"Provider '{self.provider}' not available for {self.component_type}. Available: {available}")
    
    @classmethod
    def get_available_providers(cls, component_type: ComponentType) -> list[str]:
        """Get available providers for a component type."""
        return UnifiedLoader.get_available_providers(component_type)


class AIConfiguration(BaseConfiguration):
    """Configuration for AI providers (SimpleAI and Agent systems)."""
    
    def __init__(self, provider: str, model: str, mode: Literal["simple_ai", "agent"] = "simple_ai"):
        self.model = model
        self.mode = mode.lower()
        super().__init__("ai_providers", provider)
        self._validate_mode()
    
    def _validate_mode(self):
        """Validate the AI mode."""
        if self.mode not in ["simple_ai", "agent"]:
            raise ValueError(f"Unknown mode '{self.mode}'. Available: 'simple_ai', 'agent'")
        
        if self._components[self.provider][self.mode] is None:
            raise ValueError(f"Mode '{self.mode}' not available for provider '{self.provider}'")
    
    def _get_api_key(self) -> Optional[str]:
        """Get the API key for the current provider if required."""
        config = self._components[self.provider]
        
        if not config["requires_api_key"]:
            return None
        
        api_key = os.getenv(config["api_key_env"])
        if config["requires_api_key"] and not api_key:
            raise ValueError(f"API key not found. Please set {config['api_key_env']} environment variable.")
        
        return api_key
    
    def get_client(self) -> Union[SimpleAI, AbstractLLMClient]:
        """Get an initialized client based on the configuration."""
        config = self._components[self.provider]
        client_class = config[self.mode]
        api_key = self._get_api_key()
        
        print(f"Initializing {self.mode} client for {self.provider} with model {self.model}")
        
        if self.mode == "simple_ai":
            return client_class(selected_model=self.model)
        elif self.mode == "agent":
            return client_class(api_key)
    
    @classmethod
    def get_providers_by_mode(cls, mode: str) -> list[str]:
        """Get providers that support a specific mode."""
        components = UnifiedLoader.load_components("ai_providers")
        return [
            provider for provider, config in components.items()
            if config[mode] is not None
        ]
    
    def __repr__(self) -> str:
        return f"AIConfiguration(provider='{self.provider}', model='{self.model}', mode='{self.mode}')"


class TokenizerConfiguration(BaseConfiguration):
    """Configuration for tokenizer systems."""
    
    def __init__(self, provider: str, model: str = None):
        self.model = model
        super().__init__("tokenizers", provider)
    
    def get_tokenizer(self) -> Any:
        """Get an initialized tokenizer."""
        config = self._components[self.provider]
        tokenizer_class = config["class"]
        
        print(f"Initializing tokenizer for {self.provider}")
        
        if config["needs_model"]:
            if self.model is None:
                raise ValueError(f"Tokenizer '{self.provider}' requires a model parameter")
            return tokenizer_class(self.model)
        else:
            return tokenizer_class()
    
    def __repr__(self) -> str:
        return f"TokenizerConfiguration(provider='{self.provider}', model='{self.model}')"


class EmbeddingsConfiguration(BaseConfiguration):
    """Configuration for embeddings systems."""
    
    def __init__(self, provider: str):
        super().__init__("embeddings", provider)
    
    def get_embeddings(self):
        """Get an initialized embeddings provider."""
        embeddings_class = self._components[self.provider]["class"]
        try:
            return embeddings_class()
        except TypeError:
            return embeddings_class
    
    def __repr__(self) -> str:
        return f"EmbeddingsConfiguration(provider='{self.provider}')"

class ImagesConfiguration(BaseConfiguration):
    """Configuration for image generation systems."""

    def __init__(self, provider: str, model: str = None):
        self.model = model
        super().__init__("images", provider)

    def get_image_generator(self) -> Any:
        """Get an initialized image generator."""
        config = self._components[self.provider]
        image_class = config["class"]

        print(f"Initializing image generator for {self.provider}")

        if config["needs_model"]:
            if self.model is None:
                raise ValueError(f"Image generator '{self.provider}' requires a model parameter")
            return image_class(self.model)
        else:
            return image_class()

    def __repr__(self) -> str:
        return f"ImagesConfiguration(provider='{self.provider}', model='{self.model}')"


# Convenience functions for backward compatibility
def get_available_ai_providers() -> list[str]:
    """Get available AI providers."""
    return UnifiedLoader.get_available_providers("ai_providers")

def get_available_tokenizers() -> list[str]:
    """Get available tokenizer providers."""
    return UnifiedLoader.get_available_providers("tokenizers")

def get_available_embeddings() -> list[str]:
    """Get available embeddings providers."""
    return UnifiedLoader.get_available_providers("embeddings")

def get_available_image_providers() -> list[str]:
    """Get available image providers."""
    return UnifiedLoader.get_available_providers("images")

def refresh_all_providers():
    """Refresh all provider caches."""
    UnifiedLoader.refresh_components()

