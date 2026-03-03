# Adding a New AI Provider

This guide walks through everything needed to integrate a new AI provider into the framework, using **OpenRouter** as the reference implementation throughout.

---

## Overview

The framework is built around a set of abstract interfaces. Adding a provider means implementing those interfaces and registering the new classes in the central loader. There are up to four components depending on what the provider supports:

| Component | Required | Purpose |
|---|---|---|
| Agent Client | Yes | Drives the agentic loop (tool calling, multi-turn) |
| Simple AI Provider | Optional | Single-turn text and structured output |
| Tokenizer | Yes | Token counting for memory budget management |
| Loader Registration | Yes | Makes all of the above discoverable |

---

## 1. Agent Client

**Location:** `ai_managers/agents/agent_clients/`

**Abstract interface:** `AbstractLLMClient`

The agent client is the core integration point. It receives a `StructuredMemory` object and a list of tool definitions, calls the provider API, and returns a normalized `LLMResponse`.

### Key responsibilities

- Convert `StructuredMemory` → provider message format
- Normalize tool definitions to the provider's expected shape
- Handle `tool_choice="none"` by omitting tools entirely (do not pass the value to the API)
- Return a normalized `LLMResponse` with `function_calls` and/or `text_content`

### Message format

`StructuredMemory` contains two fields:

```python
system_context: str          # Combined system prompt, base memory, long-term memory
conversation_history: list   # Ordered list of user / assistant / tool_output entries
```

Each `tool_output` entry in `conversation_history` must be reconstructed as a proper tool call round-trip in the provider's format. For Chat Completions-compatible providers this means injecting an assistant message with a `tool_calls` array followed by a `tool` role message with the result.

### Tool definition format

Tools arrive in the flat OpenAI Responses API format:

```python
{
    "type": "function",
    "name": "my_tool",
    "description": "...",
    "parameters": { ... }
}
```

Most providers (including OpenRouter, Groq, Ollama) expect the Chat Completions nested format instead:

```python
{
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "...",
        "parameters": { ... }
    }
}
```

Add `_transform_function_structure` and `_process_functions_list` methods to handle this normalization on the fly. See `openrouter_client.py` and `groq_client.py` for the reference implementation. The transform should be idempotent — if the tool already has a `"function"` key, pass it through unchanged.

### Handling tool_choice

The agentic loop passes `tool_choice="none"` at the final depth to force a text response. Many providers do not accept `"none"` as a value and will return a 404. The correct pattern is to simply omit tools entirely when `tool_choice="none"`:

```python
if tools and tool_choice != "none":
    settings["tools"] = self._process_functions_list(tools)
    settings["tool_choice"] = tool_choice
```

### LLMResponse

All clients must return:

```python
@dataclass
class LLMResponse:
    function_calls: Optional[List[FunctionCallDetails]] = None
    text_content: Optional[str] = None
```

```python
@dataclass
class FunctionCallDetails:
    name: str
    arguments: Dict[str, Any]   # Already parsed, not a JSON string
    call_id: Optional[str] = None
    thought_signature: Optional[str] = None  # Gemini only
```

---

## 2. Simple AI Provider

**Location:** `ai_managers/simple_ai/providers/`

**Abstract interface:** `SimpleAI`

Used by the memory manager for summarization tasks. Simpler than the agent client — single-turn only, no tool calling.

```python
class SimpleAI(ABC):
    def response_output(self, system: str, message: str) -> str: ...
    def structured_output(self, system: str, user: str, structure: BaseModel) -> BaseModel: ...
```

For Chat Completions-compatible providers, structured output is best handled via `instructor` with `Mode.JSON`, which works across the widest range of models. See `openrouter_provider.py` and `groq_provider.py`.

---

## 3. Tokenizer

**Location:** `ai_managers/tokens/token_providers/`

**Abstract interface:** `TokenizerProvider`

```python
class TokenizerProvider(ABC):
    def count_tokens(self, text: str) -> int: ...
```

The memory manager uses this to measure short-term and long-term memory sizes independently before deciding whether to summarize. This must be a local, synchronous operation — it is called frequently and cannot make API requests.

### Provider routing (meta-providers)

For routing providers like OpenRouter, model strings encode the underlying provider as a prefix (`"google/gemini-2.0-flash"`, `"openai/gpt-4o"`, `"meta-llama/llama-3.1-8b"`). The tokenizer should parse this prefix and delegate to the appropriate underlying tokenizer.

**Always strip the provider prefix** before passing the model name to the underlying tokenizer — the Gemini API, tiktoken, and HuggingFace tokenizers all expect just the model name, not the routing prefix.

```python
@staticmethod
def _strip_provider_prefix(model: str) -> str:
    return model.split("/", 1)[-1]
```

### Prefix mapping

Maintain a `PROVIDER_PREFIXES` dict mapping prefix → loader method. Raise `ValueError` (not a silent fallback) if the prefix is unmapped — a wrong token count causes incorrect memory management decisions, which is harder to debug than a startup crash:

```python
PROVIDER_PREFIXES = {
    "openai":     "_load_tiktoken",
    "google":     "_load_google",
    "meta-llama": "_load_opensource",
}
```

### Underlying tokenizers available

| Tokenizer class | Library | Use for |
|---|---|---|
| `OpenAITokenizer` | `tiktoken` | OpenAI models, `o200k_base` / `o200k_harmony` |
| `GeminiTokenizer` | `google-genai` | Gemini models (makes API call) |
| `OpenSourceTokenizer` | `tokenizers` (HuggingFace) | Open source models via HuggingFace ID |

For `OpenSourceTokenizer`, the model must be registered in `opensource_dict.py` mapping the provider model ID to its HuggingFace tokenizer ID.

---

## 4. Loader Registration

**Location:** `ai_managers/ai_utils/ai_loader.py`

All providers are registered in `UnifiedLoader.COMPONENT_DEFINITIONS`. Add entries under each relevant section.

### ai_providers entry

```python
"openrouter": {
    "simple_ai_module": "ai_managers.simple_ai.providers.openrouter_provider",
    "simple_ai_class": "OpenRouterProv",
    "agent_module": "ai_managers.agents.agent_clients.openrouter_client",
    "agent_class": "OpenRouterClient",
    "required_libraries": ["openai", "instructor"],
    "api_key_env": "OPENROUTER_API_KEY",
    "requires_api_key": True
}
```

### tokenizers entry

```python
"openrouter": {
    "module": "ai_managers.tokens.token_providers.openrouter_tokenizer",
    "class": "OpenRouterTokenizer",
    "required_libraries": ["openai"],
    "needs_model": True
}
```

`needs_model: True` means `TokenizerConfiguration` will pass the model string to the tokenizer constructor. Set to `False` for tokenizers that determine encoding from the model string internally (e.g. tiktoken with a default encoding).

### API key

Add the key name to `.env`:

```
OPENROUTER_API_KEY=sk-or-...
```

The loader reads it via `os.getenv(config["api_key_env"])` and passes it to the client constructor automatically.

---

## 5. Checklist

- [ ] `agent_clients/my_provider_client.py` — implements `AbstractLLMClient.generate_response()`
- [ ] `simple_ai/providers/my_provider_provider.py` — implements `SimpleAI`
- [ ] `tokens/token_providers/my_provider_tokenizer.py` — implements `TokenizerProvider.count_tokens()`
- [ ] Registered in `ai_loader.py` under `ai_providers` and `tokenizers`
- [ ] API key added to `.env`
- [ ] Tool definitions normalized from flat → nested format
- [ ] `tool_choice="none"` handled by omitting tools, not passing the string value
- [ ] Provider prefix stripped before passing model name to underlying tokenizer
- [ ] `ValueError` raised (not silent fallback) for unmapped tokenizer prefixes

---

## Reference files

```
ai_managers/agents/agent_clients/openrouter_client.py
ai_managers/agents/agent_clients/groq_client.py
ai_managers/simple_ai/providers/openrouter_provider.py
ai_managers/simple_ai/providers/groq_provider.py
ai_managers/tokens/token_providers/openrouter_tokenizer.py
ai_managers/tokens/token_providers/tokenizer_abc.py
ai_managers/ai_utils/ai_loader.py
```