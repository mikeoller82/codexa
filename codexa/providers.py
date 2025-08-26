"""AI provider implementations for Codexa."""

import os
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import openai
import anthropic
from .config import Config


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def ask(self, prompt: str, history: Optional[List[Dict]] = None, context: Optional[str] = None) -> str:
        """Ask the AI provider a question."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (has API key, etc.)."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available models from the provider API."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.get_api_key("openai")
        self.model = config.get_model("openai")
        
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def ask(self, prompt: str, history: Optional[List[Dict]] = None, context: Optional[str] = None) -> str:
        """Ask OpenAI a question."""
        if not self.client:
            return "Error: OpenAI API key not configured."

        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt(context)}
            ]
            
            # Add conversation history
            if history:
                for msg in history[-10:]:  # Keep last 10 messages to avoid token limits
                    messages.append({"role": "user", "content": msg.get("user", "")})
                    messages.append({"role": "assistant", "content": msg.get("assistant", "")})
            
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            
            return response.choices[0].message.content or "No response from OpenAI."
            
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return bool(self.api_key and self.client)

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available models from OpenAI API."""
        if not self.client:
            return []
        
        try:
            response = self.client.models.list()
            models = []
            
            # Filter for GPT models only
            for model in response.data:
                if 'gpt' in model.id.lower():
                    models.append({
                        'id': model.id,
                        'name': model.id,
                        'description': f"OpenAI {model.id}"
                    })
            
            # Sort by name for consistent ordering
            models.sort(key=lambda x: x['name'])
            return models
            
        except Exception as e:
            print(f"Error fetching OpenAI models: {e}")
            return []

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for OpenAI."""
        base_prompt = """You are Codexa, an AI-powered coding assistant. You help developers by:
1. Creating structured project plans
2. Generating technical requirements
3. Breaking down work into manageable tasks
4. Writing clean, production-ready code
5. Explaining code and debugging issues

Always be proactive, suggest best practices, and structure your responses clearly."""
        
        if context:
            base_prompt += f"\n\nProject context:\n{context}"
            
        return base_prompt


class AnthropicProvider(AIProvider):
    """Anthropic (Claude) provider implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.get_api_key("anthropic")
        self.model = config.get_model("anthropic")
        
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def ask(self, prompt: str, history: Optional[List[Dict]] = None, context: Optional[str] = None) -> str:
        """Ask Anthropic a question."""
        if not self.client:
            return "Error: Anthropic API key not configured."

        try:
            # Build conversation history
            messages = []
            
            if history:
                for msg in history[-10:]:  # Keep last 10 messages
                    if msg.get("user"):
                        messages.append({"role": "user", "content": msg["user"]})
                    if msg.get("assistant"):
                        messages.append({"role": "assistant", "content": msg["assistant"]})
            
            messages.append({"role": "user", "content": prompt})

            system_prompt = self._get_system_prompt(context)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.3,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text or "No response from Anthropic."
            
        except Exception as e:
            return f"Error calling Anthropic: {str(e)}"

    def is_available(self) -> bool:
        """Check if Anthropic is available."""
        return bool(self.api_key and self.client)

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available models from Anthropic API."""
        if not self.client:
            return []
        
        # Anthropic doesn't have a models endpoint, so return known models
        known_models = [
            {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet', 'description': 'Most capable model'},
            {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku', 'description': 'Fast and efficient'},
            {'id': 'claude-3-opus-20240229', 'name': 'Claude 3 Opus', 'description': 'Most powerful legacy model'},
            {'id': 'claude-3-sonnet-20240229', 'name': 'Claude 3 Sonnet', 'description': 'Balanced performance'},
            {'id': 'claude-3-haiku-20240307', 'name': 'Claude 3 Haiku', 'description': 'Fast legacy model'}
        ]
        
        # Test which models are actually available by trying a simple request
        available_models = []
        for model in known_models:
            try:
                # Quick test with minimal tokens
                test_response = self.client.messages.create(
                    model=model['id'],
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}]
                )
                if test_response:
                    available_models.append(model)
            except Exception:
                # Model not available or access denied
                continue
        
        return available_models if available_models else known_models  # Fallback to known list

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for Anthropic."""
        base_prompt = """You are Codexa, an AI-powered coding assistant. You help developers by:
1. Creating structured project plans
2. Generating technical requirements  
3. Breaking down work into manageable tasks
4. Writing clean, production-ready code
5. Explaining code and debugging issues

Always be proactive, suggest best practices, and structure your responses clearly."""
        
        if context:
            base_prompt += f"\n\nProject context:\n{context}"
            
        return base_prompt


class OpenRouterProvider(AIProvider):
    """OpenRouter provider implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.get_api_key("openrouter")
        self.model = config.get_model("openrouter")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Set up headers exactly as OpenRouter requires
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://codexa.ai",  # Optional site URL for rankings
            "X-Title": "Codexa - AI Coding Assistant",  # Optional site title for rankings
        }

    def ask(self, prompt: str, history: Optional[List[Dict]] = None, context: Optional[str] = None) -> str:
        """Ask OpenRouter a question."""
        if not self.api_key:
            return "Error: OpenRouter API key not configured."

        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt(context)}
            ]
            
            # Add conversation history
            if history:
                for msg in history[-10:]:  # Keep last 10 messages to avoid token limits
                    if msg.get("user"):
                        messages.append({"role": "user", "content": msg["user"]})
                    if msg.get("assistant"):
                        messages.append({"role": "assistant", "content": msg["assistant"]})
            
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2048,
                "stream": False
            }

            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=60  # Increased timeout for OpenRouter
            )
            
            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', {}).get('message', str(error_data))
                except:
                    error_detail = response.text
                return f"OpenRouter API error ({response.status_code}): {error_detail}"
            
            data = response.json()
            
            # Handle OpenRouter error responses
            if 'error' in data:
                error_msg = data['error'].get('message', str(data['error']))
                return f"OpenRouter error: {error_msg}"
            
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'] or "No response from OpenRouter."
            else:
                return f"Unexpected response format from OpenRouter: {data}"
            
        except requests.exceptions.Timeout:
            return "OpenRouter request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return "Failed to connect to OpenRouter. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            return f"Network error calling OpenRouter: {str(e)}"
        except Exception as e:
            return f"Error calling OpenRouter: {str(e)}"

    def is_available(self) -> bool:
        """Check if OpenRouter is available."""
        return bool(self.api_key)

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available models from OpenRouter API."""
        if not self.api_key:
            return []
        
        try:
            models_url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://codexa.ai",
                "X-Title": "Codexa - AI Coding Assistant",
            }
            
            response = requests.get(models_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Error fetching OpenRouter models: {response.status_code}")
                return []
            
            data = response.json()
            models = []
            
            if 'data' in data:
                for model in data['data']:
                    models.append({
                        'id': model.get('id', ''),
                        'name': model.get('name', model.get('id', '')),
                        'description': model.get('description', '')[:100] + ('...' if len(model.get('description', '')) > 100 else ''),
                        'pricing': model.get('pricing', {}),
                        'context_length': model.get('context_length', 0)
                    })
            
            # Sort by name for consistent ordering
            models.sort(key=lambda x: x['name'])
            return models
            
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching OpenRouter models: {e}")
            return []
        except Exception as e:
            print(f"Error fetching OpenRouter models: {e}")
            return []

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for OpenRouter."""
        base_prompt = """You are Codexa, an AI-powered coding assistant. You help developers by:
1. Creating structured project plans
2. Generating technical requirements
3. Breaking down work into manageable tasks
4. Writing clean, production-ready code
5. Explaining code and debugging issues

Always be proactive, suggest best practices, and structure your responses clearly."""
        
        if context:
            base_prompt += f"\n\nProject context:\n{context}"
            
        return base_prompt


class OpenRouterOAIProvider(AIProvider):
    """OpenRouter provider using OpenAI Python client implementation."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.get_api_key("openrouter")
        self.model = config.get_model("openrouter")
        self.base_url = "https://openrouter.ai/api/v1"
        
        if self.api_key:
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        else:
            self.client = None

    def ask(self, prompt: str, history: Optional[List[Dict]] = None, context: Optional[str] = None) -> str:
        """Ask OpenRouter a question using OpenAI client."""
        if not self.client:
            return "Error: OpenRouter API key not configured."

        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt(context)}
            ]
            
            # Add conversation history
            if history:
                for msg in history[-10:]:  # Keep last 10 messages to avoid token limits
                    if msg.get("user"):
                        messages.append({"role": "user", "content": msg["user"]})
                    if msg.get("assistant"):
                        messages.append({"role": "assistant", "content": msg["assistant"]})
            
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                extra_headers={
                    "HTTP-Referer": "https://codexa.ai",  # Optional site URL for rankings
                    "X-Title": "Codexa - AI Coding Assistant",  # Optional site title for rankings
                },
                extra_body={}
            )
            
            return response.choices[0].message.content or "No response from OpenRouter."
            
        except Exception as e:
            return f"Error calling OpenRouter (OAI): {str(e)}"

    def is_available(self) -> bool:
        """Check if OpenRouter is available."""
        return bool(self.api_key and self.client)

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available models from OpenRouter API using OAI client."""
        if not self.api_key:
            return []
        
        try:
            # Use direct HTTP request since OpenAI client doesn't have models endpoint for OpenRouter
            models_url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://codexa.ai",
                "X-Title": "Codexa - AI Coding Assistant",
            }
            
            response = requests.get(models_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"Error fetching OpenRouter models: {response.status_code}")
                return []
            
            data = response.json()
            models = []
            
            if 'data' in data:
                for model in data['data']:
                    models.append({
                        'id': model.get('id', ''),
                        'name': model.get('name', model.get('id', '')),
                        'description': model.get('description', '')[:100] + ('...' if len(model.get('description', '')) > 100 else ''),
                        'pricing': model.get('pricing', {}),
                        'context_length': model.get('context_length', 0)
                    })
            
            # Sort by name for consistent ordering
            models.sort(key=lambda x: x['name'])
            return models
            
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching OpenRouter models: {e}")
            return []
        except Exception as e:
            print(f"Error fetching OpenRouter models: {e}")
            return []

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for OpenRouter."""
        base_prompt = """You are Codexa, an AI-powered coding assistant. You help developers by:
1. Creating structured project plans
2. Generating technical requirements
3. Breaking down work into manageable tasks
4. Writing clean, production-ready code
5. Explaining code and debugging issues

Always be proactive, suggest best practices, and structure your responses clearly."""
        
        if context:
            base_prompt += f"\n\nProject context:\n{context}"
            
        return base_prompt


class ProviderFactory:
    """Factory class for creating AI providers."""

    @staticmethod
    def create_provider(config: Config) -> Optional[AIProvider]:
        """Create an AI provider based on configuration."""
        provider_name = config.get_provider()
        
        if provider_name == "openai":
            provider = OpenAIProvider(config)
        elif provider_name == "anthropic":
            provider = AnthropicProvider(config)
        elif provider_name == "openrouter":
            # Choose OpenRouter implementation based on config preference
            use_oai_client = getattr(config, 'openrouter_use_oai_client', True)  # Default to OAI client
            if use_oai_client:
                provider = OpenRouterOAIProvider(config)
            else:
                provider = OpenRouterProvider(config)
        elif provider_name == "openrouter-http":
            # Explicit HTTP requests approach
            provider = OpenRouterProvider(config)
        elif provider_name == "openrouter-oai":
            # Explicit OpenAI client approach
            provider = OpenRouterOAIProvider(config)
        else:
            return None
        
        if provider.is_available():
            return provider
        
        # Try fallback providers in order of preference
        fallback_order = ["openrouter", "openai", "anthropic"]
        for fallback in fallback_order:
            if fallback != provider_name:
                if fallback == "openai" and config.get_api_key("openai"):
                    return OpenAIProvider(config)
                elif fallback == "anthropic" and config.get_api_key("anthropic"):
                    return AnthropicProvider(config)
                elif fallback == "openrouter" and config.get_api_key("openrouter"):
                    # Use default OpenRouter approach for fallback
                    return OpenRouterOAIProvider(config)
        
        return None