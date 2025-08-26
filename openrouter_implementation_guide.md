# OpenRouter Implementation Guide

Codexa now supports both OpenRouter API approaches:

## 1. OpenAI Client Approach (Default)
Uses the `openai` Python package with OpenRouter's base URL:

```python
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="<OPENROUTER_API_KEY>",
)

completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "https://codexa.ai",
    "X-Title": "Codexa - AI Coding Assistant",
  },
  model="qwen/qwen3-coder:free",
  messages=[{"role": "user", "content": "What is the meaning of life?"}]
)
```

## 2. Raw HTTP Requests Approach
Uses the `requests` library directly:

```python
import requests
import json

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer <OPENROUTER_API_KEY>",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://codexa.ai",
    "X-Title": "Codexa - AI Coding Assistant",
  },
  data=json.dumps({
    "model": "qwen/qwen3-coder:free",
    "messages": [{"role": "user", "content": "What is the meaning of life?"}],
  })
)
```

## Configuration Options

### In ~/.codexarc:
```yaml
provider: openrouter
openrouter:
  use_oai_client: true  # Use OpenAI client (true) or HTTP requests (false)
```

### Explicit Provider Selection:
- `openrouter` - Uses config preference (defaults to OAI client)
- `openrouter-oai` - Forces OpenAI client approach
- `openrouter-http` - Forces HTTP requests approach

## Benefits of Each Approach

### OpenAI Client (Default):
- ✅ Type safety and auto-completion
- ✅ Built-in error handling
- ✅ Familiar OpenAI API interface
- ✅ Streaming support
- ✅ Better debugging tools

### HTTP Requests:
- ✅ Direct control over requests
- ✅ No additional dependencies
- ✅ Custom timeout/retry logic
- ✅ Easier to debug network issues
- ✅ More transparent error handling

## Current Implementation Status

Both approaches are fully implemented and tested:
- ✅ Headers properly set for OpenRouter rankings
- ✅ Error handling and timeouts
- ✅ Configuration support
- ✅ Enhanced provider factory integration
- ✅ Runtime switching capability

Choose the approach that best fits your development style and requirements!