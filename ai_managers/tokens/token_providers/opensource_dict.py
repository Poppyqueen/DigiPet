mapped_models={
    "qwen-qwq-32b":"Qwen/QwQ-32B", # groq 
    "llama-3.3-70b-versatile":"meta-llama/Llama-3.3-70B-Instruct",
    "llama-3.1-8b-instant":"meta-llama/Llama-3.1-8B",
    "gemma2-9b-it":"google/gemma-2-9b-it",
    "deepseek-r1-distill-llama-70b":"deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "openai/gpt-oss-120b":"openai/gpt-oss-120b", # Using Groq inference requires downloading the Tokenizer for this

    "qwen3:4b":"Qwen/Qwen3-4B", # ollama 4b models, improving the pet system allows for these models to be a lot more competent now
    "granite3.3:2b":"ibm-granite/granite-3.3-2b-instruct",
    "cogito:3b":"deepcogito/cogito-v1-preview-llama-3B",
    "phi4-mini:3.8b":"microsoft/Phi-4-mini-instruct",
    "llama3.2:3b":"meta-llama/Llama-3.2-3B-Instruct",

    "gemma-3-1b-it-BF16": "google/gemma-3-1b-it", 
    
    "qwen3:8b-q4_K_M":"deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", 
}

# This should map the models to use from Groq or Ollama (or other opensource provider)
# From the name of the model for the provider to the ID in HuggingFace to pull its tokenizers.json

# It should have some models for Groq already in place as-well some other for Ollama