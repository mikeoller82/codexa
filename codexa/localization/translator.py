"""
Advanced translation system with multiple providers and intelligent caching.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from rich.console import Console


class TranslationProvider(Enum):
    """Available translation providers."""
    GOOGLE_TRANSLATE = "google"
    AZURE_TRANSLATOR = "azure"
    AWS_TRANSLATE = "aws"
    DEEPL = "deepl"
    OPENAI = "openai"
    LOCAL_MODEL = "local"
    MOCK = "mock"  # For testing


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: TranslationProvider
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationCache:
    """Cache for translation results."""
    translations: Dict[str, TranslationResult] = field(default_factory=dict)
    max_size: int = 10000
    ttl_hours: int = 24
    
    def get_cache_key(self, text: str, source_lang: str, target_lang: str, provider: TranslationProvider) -> str:
        """Generate cache key for translation."""
        return f"{provider.value}:{source_lang}:{target_lang}:{hash(text)}"
    
    def get(self, text: str, source_lang: str, target_lang: str, provider: TranslationProvider) -> Optional[TranslationResult]:
        """Get cached translation."""
        key = self.get_cache_key(text, source_lang, target_lang, provider)
        
        if key in self.translations:
            result = self.translations[key]
            # Check if cache entry is still valid
            if datetime.now() - result.timestamp < timedelta(hours=self.ttl_hours):
                return result
            else:
                # Remove expired entry
                del self.translations[key]
        
        return None
    
    def put(self, result: TranslationResult):
        """Cache translation result."""
        key = self.get_cache_key(result.source_text, result.source_language, result.target_language, result.provider)
        
        # Remove oldest entries if cache is full
        if len(self.translations) >= self.max_size:
            # Remove 10% of oldest entries
            sorted_items = sorted(self.translations.items(), key=lambda x: x[1].timestamp)
            for old_key, _ in sorted_items[:self.max_size // 10]:
                del self.translations[old_key]
        
        self.translations[key] = result
    
    def clear(self):
        """Clear all cached translations."""
        self.translations.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.translations)


class BaseTranslationProvider:
    """Base class for translation providers."""
    
    def __init__(self, provider_type: TranslationProvider):
        self.provider_type = provider_type
        self.logger = logging.getLogger(f"codexa.translation.{provider_type.value}")
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """Translate text from source to target language."""
        raise NotImplementedError
    
    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text."""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if the provider is available."""
        raise NotImplementedError


class MockTranslationProvider(BaseTranslationProvider):
    """Mock translation provider for testing."""
    
    def __init__(self):
        super().__init__(TranslationProvider.MOCK)
        
        # Simple mock translations
        self.mock_translations = {
            "Hello": {
                "es": "Hola",
                "fr": "Bonjour", 
                "de": "Hallo",
                "ja": "こんにちは",
                "zh": "你好"
            },
            "Goodbye": {
                "es": "Adiós",
                "fr": "Au revoir",
                "de": "Auf Wiedersehen", 
                "ja": "さようなら",
                "zh": "再见"
            },
            "Thank you": {
                "es": "Gracias",
                "fr": "Merci",
                "de": "Danke",
                "ja": "ありがとう",
                "zh": "谢谢"
            }
        }
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """Mock translation."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        # Check for exact matches in mock data
        if text in self.mock_translations and target_language in self.mock_translations[text]:
            translated_text = self.mock_translations[text][target_language]
            confidence = 0.95
        else:
            # Fallback: append language code to indicate "translation"
            translated_text = f"{text} [{target_language}]"
            confidence = 0.3
        
        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_language=source_language or "en",
            target_language=target_language,
            provider=self.provider_type,
            confidence=confidence,
            metadata={"mock_provider": True}
        )
    
    async def detect_language(self, text: str) -> str:
        """Mock language detection."""
        # Simple heuristic based on character sets
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return "zh"
        elif any('\u3040' <= char <= '\u309f' for char in text) or any('\u30a0' <= char <= '\u30ff' for char in text):
            return "ja"
        elif any('\u0600' <= char <= '\u06ff' for char in text):
            return "ar"
        elif any('\u0400' <= char <= '\u04ff' for char in text):
            return "ru"
        else:
            return "en"  # Default to English
    
    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True


class OpenAITranslationProvider(BaseTranslationProvider):
    """OpenAI-based translation provider."""
    
    def __init__(self, api_key: str):
        super().__init__(TranslationProvider.OPENAI)
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"
        
        # Language code mapping
        self.language_names = {
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "zh": "Chinese",
            "pt": "Portuguese",
            "it": "Italian",
            "ru": "Russian",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "nl": "Dutch",
            "sv": "Swedish"
        }
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """Translate using OpenAI API."""
        target_lang_name = self.language_names.get(target_language, target_language)
        source_lang_name = self.language_names.get(source_language, "the source language") if source_language else "the source language"
        
        prompt = f"Translate the following text from {source_lang_name} to {target_lang_name}. Only return the translation, nothing else:\n\n{text}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional translator. Provide accurate, natural translations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": len(text) * 3  # Rough estimate for translation length
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result["choices"][0]["message"]["content"].strip()
                        
                        # Estimate confidence based on response quality
                        confidence = 0.9 if len(translated_text) > 0 else 0.1
                        
                        return TranslationResult(
                            source_text=text,
                            translated_text=translated_text,
                            source_language=source_language or "auto",
                            target_language=target_language,
                            provider=self.provider_type,
                            confidence=confidence,
                            metadata={
                                "model": self.model,
                                "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
        
        except Exception as e:
            self.logger.error(f"OpenAI translation failed: {e}")
            raise
    
    async def detect_language(self, text: str) -> str:
        """Detect language using OpenAI."""
        prompt = f"What language is this text written in? Respond with only the ISO 639-1 language code (e.g., 'en', 'es', 'fr'):\n\n{text}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 10
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        language_code = result["choices"][0]["message"]["content"].strip().lower()
                        return language_code
                    else:
                        return "en"  # Fallback to English
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return "en"
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        return bool(self.api_key)


class Translator:
    """Main translation coordinator with multiple providers and intelligent routing."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.translation")
        
        # Provider management
        self.providers: Dict[TranslationProvider, BaseTranslationProvider] = {}
        self.primary_provider: Optional[TranslationProvider] = None
        self.fallback_providers: List[TranslationProvider] = []
        
        # Caching
        self.cache = TranslationCache()
        
        # Performance tracking
        self.provider_performance: Dict[TranslationProvider, Dict[str, Any]] = {}
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available translation providers."""
        # Always add mock provider for testing
        mock_provider = MockTranslationProvider()
        self.add_provider(mock_provider)
        self.primary_provider = TranslationProvider.MOCK
        
        # Try to initialize OpenAI provider
        openai_key = self._get_openai_api_key()
        if openai_key:
            try:
                openai_provider = OpenAITranslationProvider(openai_key)
                if openai_provider.is_available():
                    self.add_provider(openai_provider)
                    self.primary_provider = TranslationProvider.OPENAI
                    self.fallback_providers = [TranslationProvider.MOCK]
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI provider: {e}")
    
    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or config."""
        import os
        return os.environ.get('OPENAI_API_KEY')
    
    def add_provider(self, provider: BaseTranslationProvider):
        """Add a translation provider."""
        self.providers[provider.provider_type] = provider
        
        # Initialize performance tracking
        self.provider_performance[provider.provider_type] = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'avg_response_time': 0.0,
            'last_used': None
        }
        
        self.logger.info(f"Added translation provider: {provider.provider_type.value}")
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[TranslationResult]:
        """Translate text using the best available provider."""
        if not text.strip():
            return None
        
        # Check cache first
        if use_cache:
            for provider_type in [self.primary_provider] + self.fallback_providers:
                if provider_type:
                    cached_result = self.cache.get(text, source_language or "auto", target_language, provider_type)
                    if cached_result:
                        self.logger.debug(f"Cache hit for translation: {text[:50]}...")
                        return cached_result
        
        # Try providers in order of preference
        providers_to_try = []
        if self.primary_provider and self.primary_provider in self.providers:
            providers_to_try.append(self.primary_provider)
        
        for fallback in self.fallback_providers:
            if fallback in self.providers and fallback not in providers_to_try:
                providers_to_try.append(fallback)
        
        for provider_type in providers_to_try:
            provider = self.providers[provider_type]
            
            try:
                self.logger.debug(f"Attempting translation with {provider_type.value}")
                start_time = datetime.now()
                
                # Update performance tracking
                self.provider_performance[provider_type]['requests'] += 1
                
                result = await provider.translate(text, target_language, source_language)
                
                # Update performance metrics
                response_time = (datetime.now() - start_time).total_seconds()
                perf = self.provider_performance[provider_type]
                perf['successes'] += 1
                perf['last_used'] = datetime.now()
                
                # Update average response time
                total_successes = perf['successes']
                perf['avg_response_time'] = ((perf['avg_response_time'] * (total_successes - 1)) + response_time) / total_successes
                
                # Cache the result
                if use_cache:
                    self.cache.put(result)
                
                self.logger.info(f"Translation successful with {provider_type.value}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Translation failed with {provider_type.value}: {e}")
                self.provider_performance[provider_type]['failures'] += 1
                continue
        
        self.logger.error("All translation providers failed")
        return None
    
    async def detect_language(self, text: str) -> str:
        """Detect the language of text using the best available provider."""
        if not text.strip():
            return "en"
        
        # Try providers in order
        providers_to_try = []
        if self.primary_provider and self.primary_provider in self.providers:
            providers_to_try.append(self.primary_provider)
        
        for fallback in self.fallback_providers:
            if fallback in self.providers and fallback not in providers_to_try:
                providers_to_try.append(fallback)
        
        for provider_type in providers_to_try:
            provider = self.providers[provider_type]
            
            try:
                language = await provider.detect_language(text)
                self.logger.debug(f"Language detected as {language} by {provider_type.value}")
                return language
                
            except Exception as e:
                self.logger.warning(f"Language detection failed with {provider_type.value}: {e}")
                continue
        
        # Fallback to English
        return "en"
    
    async def batch_translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Optional[TranslationResult]]:
        """Translate multiple texts efficiently."""
        results = []
        
        # Process in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Create tasks for concurrent translation
            tasks = [
                self.translate(text, target_language, source_language, use_cache)
                for text in batch
            ]
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch translation error: {result}")
                    results.append(None)
                else:
                    results.append(result)
            
            # Small delay between batches to be respectful to APIs
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        return results
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all translation providers."""
        status = {
            'primary_provider': self.primary_provider.value if self.primary_provider else None,
            'fallback_providers': [p.value for p in self.fallback_providers],
            'cache_size': self.cache.size(),
            'providers': {}
        }
        
        for provider_type, provider in self.providers.items():
            perf = self.provider_performance[provider_type]
            status['providers'][provider_type.value] = {
                'available': provider.is_available(),
                'requests': perf['requests'],
                'successes': perf['successes'],
                'failures': perf['failures'],
                'success_rate': perf['successes'] / max(1, perf['requests']),
                'avg_response_time': perf['avg_response_time'],
                'last_used': perf['last_used'].isoformat() if perf['last_used'] else None
            }
        
        return status
    
    def clear_cache(self):
        """Clear translation cache."""
        self.cache.clear()
        self.logger.info("Translation cache cleared")
    
    def set_primary_provider(self, provider_type: TranslationProvider):
        """Set the primary translation provider."""
        if provider_type not in self.providers:
            raise ValueError(f"Provider {provider_type.value} is not available")
        
        old_primary = self.primary_provider
        self.primary_provider = provider_type
        
        # Update fallback providers
        if old_primary and old_primary != provider_type and old_primary not in self.fallback_providers:
            self.fallback_providers.insert(0, old_primary)
        
        self.logger.info(f"Primary provider changed to: {provider_type.value}")
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive translation statistics."""
        total_requests = sum(perf['requests'] for perf in self.provider_performance.values())
        total_successes = sum(perf['successes'] for perf in self.provider_performance.values())
        total_failures = sum(perf['failures'] for perf in self.provider_performance.values())
        
        return {
            'total_requests': total_requests,
            'total_successes': total_successes,
            'total_failures': total_failures,
            'overall_success_rate': total_successes / max(1, total_requests),
            'cache_hit_rate': 0.0,  # Would need to track cache hits vs misses
            'providers_available': len([p for p in self.providers.values() if p.is_available()]),
            'cache_size': self.cache.size(),
            'provider_performance': {
                provider_type.value: perf
                for provider_type, perf in self.provider_performance.items()
            }
        }