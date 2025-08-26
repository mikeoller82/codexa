"""
Comprehensive localization manager with multi-language support and cultural adaptation.
"""

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class Language(Enum):
    """Supported languages with ISO codes."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    RUSSIAN = "ru"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"
    DUTCH = "nl"
    SWEDISH = "sv"


class TextDirection(Enum):
    """Text direction for different languages."""
    LTR = "ltr"  # Left to Right
    RTL = "rtl"  # Right to Left


class CommunicationStyle(Enum):
    """Communication styles for different cultures."""
    DIRECT = "direct"           # Direct, explicit communication
    INDIRECT = "indirect"       # Indirect, implicit communication
    FORMAL = "formal"           # Formal, respectful tone
    CASUAL = "casual"           # Casual, friendly tone
    HIERARCHICAL = "hierarchical"  # Respect for authority/hierarchy
    EGALITARIAN = "egalitarian"    # Equal, peer-to-peer communication


@dataclass
class CulturalContext:
    """Cultural context information for localization."""
    language: Language
    country_code: str
    text_direction: TextDirection
    communication_style: CommunicationStyle
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    number_format: str = "{:,.2f}"
    currency_symbol: str = "$"
    greeting_style: str = "formal"
    politeness_level: int = 3  # 1-5 scale
    context_sensitivity: float = 0.5  # 0-1 scale


@dataclass
class LocaleConfig:
    """Configuration for a specific locale."""
    language: Language
    cultural_context: CulturalContext
    translation_files: List[Path] = field(default_factory=list)
    fallback_language: Language = Language.ENGLISH
    enabled: bool = True
    completion_percentage: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TranslationKey:
    """Key for translation lookup with metadata."""
    key: str
    context: str = ""
    description: str = ""
    category: str = "general"
    requires_plural: bool = False
    variables: List[str] = field(default_factory=list)
    max_length: Optional[int] = None
    urgency: str = "normal"  # low, normal, high, critical


class LocalizationManager:
    """Comprehensive localization manager with cultural adaptation."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.localization")
        
        # Core configuration
        self.current_language = Language.ENGLISH
        self.fallback_language = Language.ENGLISH
        
        # Locale configurations
        self.locales: Dict[Language, LocaleConfig] = {}
        
        # Translation storage
        self.translations: Dict[Language, Dict[str, str]] = {}
        self.translation_metadata: Dict[str, TranslationKey] = {}
        
        # Cultural adaptations
        self.cultural_contexts: Dict[Language, CulturalContext] = {}
        
        # Caching and performance
        self.translation_cache: Dict[str, str] = {}
        self.missing_translations: Set[str] = set()
        
        # Statistics
        self.translation_stats = {
            'translations_requested': 0,
            'cache_hits': 0,
            'missing_keys': 0,
            'fallback_used': 0
        }
        
        # Initialize default configurations
        self._initialize_default_locales()
        self._initialize_cultural_contexts()
    
    def _initialize_default_locales(self):
        """Initialize default locale configurations."""
        # English (default)
        self.locales[Language.ENGLISH] = LocaleConfig(
            language=Language.ENGLISH,
            cultural_context=CulturalContext(
                language=Language.ENGLISH,
                country_code="US",
                text_direction=TextDirection.LTR,
                communication_style=CommunicationStyle.DIRECT,
                greeting_style="casual"
            ),
            completion_percentage=100.0
        )
        
        # Spanish
        self.locales[Language.SPANISH] = LocaleConfig(
            language=Language.SPANISH,
            cultural_context=CulturalContext(
                language=Language.SPANISH,
                country_code="ES",
                text_direction=TextDirection.LTR,
                communication_style=CommunicationStyle.FORMAL,
                date_format="%d/%m/%Y",
                currency_symbol="€",
                greeting_style="formal",
                politeness_level=4
            )
        )
        
        # Japanese
        self.locales[Language.JAPANESE] = LocaleConfig(
            language=Language.JAPANESE,
            cultural_context=CulturalContext(
                language=Language.JAPANESE,
                country_code="JP",
                text_direction=TextDirection.LTR,
                communication_style=CommunicationStyle.HIERARCHICAL,
                date_format="%Y年%m月%d日",
                time_format="%H時%M分",
                currency_symbol="¥",
                greeting_style="formal",
                politeness_level=5,
                context_sensitivity=0.9
            )
        )
        
        # German
        self.locales[Language.GERMAN] = LocaleConfig(
            language=Language.GERMAN,
            cultural_context=CulturalContext(
                language=Language.GERMAN,
                country_code="DE",
                text_direction=TextDirection.LTR,
                communication_style=CommunicationStyle.DIRECT,
                date_format="%d.%m.%Y",
                time_format="%H:%M",
                number_format="{:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                currency_symbol="€",
                politeness_level=3
            )
        )
        
        # Arabic
        self.locales[Language.ARABIC] = LocaleConfig(
            language=Language.ARABIC,
            cultural_context=CulturalContext(
                language=Language.ARABIC,
                country_code="SA",
                text_direction=TextDirection.RTL,
                communication_style=CommunicationStyle.FORMAL,
                date_format="%d/%m/%Y",
                currency_symbol="ريال",
                greeting_style="formal",
                politeness_level=4,
                context_sensitivity=0.8
            )
        )
    
    def _initialize_cultural_contexts(self):
        """Initialize cultural context mappings."""
        for language, locale_config in self.locales.items():
            self.cultural_contexts[language] = locale_config.cultural_context
    
    def set_language(self, language: Language) -> bool:
        """Set the current language for localization."""
        if language not in self.locales:
            self.logger.warning(f"Language {language.value} not configured")
            return False
        
        if not self.locales[language].enabled:
            self.logger.warning(f"Language {language.value} is disabled")
            return False
        
        old_language = self.current_language
        self.current_language = language
        
        # Clear translation cache when language changes
        self.translation_cache.clear()
        
        self.logger.info(f"Language changed from {old_language.value} to {language.value}")
        self.console.print(f"[green]Language set to: {language.value}[/green]")
        
        return True
    
    def translate(
        self,
        key: str,
        language: Optional[Language] = None,
        variables: Optional[Dict[str, Any]] = None,
        fallback: Optional[str] = None,
        plural_count: Optional[int] = None
    ) -> str:
        """Translate a key to the specified or current language."""
        self.translation_stats['translations_requested'] += 1
        
        # Determine target language
        target_language = language or self.current_language
        
        # Create cache key
        cache_key = f"{target_language.value}:{key}:{str(variables)}:{plural_count}"
        
        # Check cache first
        if cache_key in self.translation_cache:
            self.translation_stats['cache_hits'] += 1
            return self.translation_cache[cache_key]
        
        # Get translation
        translation = self._get_translation(key, target_language, plural_count)
        
        if not translation:
            # Try fallback language
            if target_language != self.fallback_language:
                translation = self._get_translation(key, self.fallback_language, plural_count)
                if translation:
                    self.translation_stats['fallback_used'] += 1
        
        if not translation:
            # Use provided fallback or return key
            translation = fallback or key
            self.missing_translations.add(f"{target_language.value}:{key}")
            self.translation_stats['missing_keys'] += 1
            self.logger.debug(f"Missing translation: {target_language.value}:{key}")
        
        # Apply variables if provided
        if variables:
            try:
                translation = translation.format(**variables)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Variable substitution failed for {key}: {e}")
        
        # Apply cultural adaptations
        translation = self._apply_cultural_adaptations(translation, target_language)
        
        # Cache the result
        self.translation_cache[cache_key] = translation
        
        return translation
    
    def _get_translation(self, key: str, language: Language, plural_count: Optional[int] = None) -> Optional[str]:
        """Get translation from storage."""
        if language not in self.translations:
            return None
        
        lang_translations = self.translations[language]
        
        # Handle pluralization
        if plural_count is not None:
            plural_key = self._get_plural_key(key, plural_count, language)
            if plural_key in lang_translations:
                return lang_translations[plural_key]
        
        # Regular translation lookup
        return lang_translations.get(key)
    
    def _get_plural_key(self, base_key: str, count: int, language: Language) -> str:
        """Get the appropriate plural form key based on language rules."""
        # Simplified pluralization rules - in practice, this would be more sophisticated
        
        if language == Language.ENGLISH:
            if count == 1:
                return f"{base_key}.singular"
            else:
                return f"{base_key}.plural"
        
        elif language == Language.RUSSIAN:
            # Russian has complex plural forms
            if count % 10 == 1 and count % 100 != 11:
                return f"{base_key}.singular"
            elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
                return f"{base_key}.few"
            else:
                return f"{base_key}.many"
        
        elif language == Language.JAPANESE:
            # Japanese doesn't have plural forms
            return base_key
        
        else:
            # Default plural handling
            return f"{base_key}.plural" if count != 1 else f"{base_key}.singular"
    
    def _apply_cultural_adaptations(self, text: str, language: Language) -> str:
        """Apply cultural adaptations to translated text."""
        if language not in self.cultural_contexts:
            return text
        
        context = self.cultural_contexts[language]
        
        # Apply politeness adaptations
        if context.politeness_level >= 4:
            # Add honorifics or polite forms
            text = self._add_politeness_markers(text, language)
        
        # Apply communication style adaptations
        if context.communication_style == CommunicationStyle.INDIRECT:
            text = self._make_more_indirect(text, language)
        elif context.communication_style == CommunicationStyle.FORMAL:
            text = self._make_more_formal(text, language)
        
        return text
    
    def _add_politeness_markers(self, text: str, language: Language) -> str:
        """Add politeness markers appropriate for the language."""
        if language == Language.JAPANESE:
            # Add -masu endings, desu copula, etc.
            if text.endswith('.'):
                text = text[:-1] + 'です。'
        elif language == Language.GERMAN:
            # Use Sie instead of du
            text = text.replace('you', 'Sie')
        elif language == Language.SPANISH:
            # Use usted form
            text = text.replace('tú', 'usted')
        
        return text
    
    def _make_more_indirect(self, text: str, language: Language) -> str:
        """Make text more indirect for cultures that prefer indirect communication."""
        # Add softening phrases
        softening_phrases = {
            Language.JAPANESE: "もしよろしければ、",  # "If it's alright with you"
            Language.ENGLISH: "Perhaps you might consider ",
            Language.GERMAN: "Vielleicht könnten Sie ",
            Language.SPANISH: "Tal vez podría "
        }
        
        if language in softening_phrases:
            return softening_phrases[language] + text.lower()
        
        return text
    
    def _make_more_formal(self, text: str, language: Language) -> str:
        """Make text more formal."""
        # Replace casual words with formal equivalents
        formal_replacements = {
            Language.ENGLISH: {
                "hi": "hello",
                "bye": "goodbye",
                "ok": "very well",
                "yeah": "yes"
            },
            Language.SPANISH: {
                "hola": "buenos días",
                "vale": "muy bien"
            },
            Language.FRENCH: {
                "salut": "bonjour",
                "ok": "d'accord"
            }
        }
        
        if language in formal_replacements:
            for casual, formal in formal_replacements[language].items():
                text = text.replace(casual, formal)
        
        return text
    
    def load_translations(self, language: Language, translations_file: Path) -> bool:
        """Load translations from a JSON file."""
        try:
            with open(translations_file, 'r', encoding='utf-8') as f:
                translations_data = json.load(f)
            
            # Initialize language if not exists
            if language not in self.translations:
                self.translations[language] = {}
            
            # Load translations
            if 'translations' in translations_data:
                self.translations[language].update(translations_data['translations'])
            
            # Load metadata
            if 'metadata' in translations_data:
                for key, meta in translations_data['metadata'].items():
                    self.translation_metadata[key] = TranslationKey(
                        key=key,
                        context=meta.get('context', ''),
                        description=meta.get('description', ''),
                        category=meta.get('category', 'general'),
                        requires_plural=meta.get('requires_plural', False),
                        variables=meta.get('variables', []),
                        max_length=meta.get('max_length'),
                        urgency=meta.get('urgency', 'normal')
                    )
            
            # Update locale configuration
            if language in self.locales:
                self.locales[language].last_updated = datetime.now()
                translation_count = len(self.translations[language])
                total_keys = len(self.translation_metadata) or translation_count
                self.locales[language].completion_percentage = (translation_count / total_keys) * 100
            
            self.logger.info(f"Loaded {len(translations_data.get('translations', {}))} translations for {language.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load translations from {translations_file}: {e}")
            return False
    
    def export_translations(self, language: Language, output_file: Path) -> bool:
        """Export translations to a JSON file."""
        if language not in self.translations:
            self.logger.error(f"No translations available for {language.value}")
            return False
        
        try:
            export_data = {
                'language': language.value,
                'exported_at': datetime.now().isoformat(),
                'translations': self.translations[language],
                'metadata': {}
            }
            
            # Add metadata for keys that exist in this language
            for key in self.translations[language]:
                if key in self.translation_metadata:
                    meta = self.translation_metadata[key]
                    export_data['metadata'][key] = {
                        'context': meta.context,
                        'description': meta.description,
                        'category': meta.category,
                        'requires_plural': meta.requires_plural,
                        'variables': meta.variables,
                        'max_length': meta.max_length,
                        'urgency': meta.urgency
                    }
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Exported {len(export_data['translations'])} translations to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export translations: {e}")
            return False
    
    def add_translation(self, language: Language, key: str, translation: str, metadata: Optional[TranslationKey] = None):
        """Add a single translation."""
        if language not in self.translations:
            self.translations[language] = {}
        
        self.translations[language][key] = translation
        
        if metadata:
            self.translation_metadata[key] = metadata
        
        # Clear cache for this key
        cache_keys_to_remove = [k for k in self.translation_cache.keys() if k.startswith(f"{language.value}:{key}")]
        for cache_key in cache_keys_to_remove:
            del self.translation_cache[cache_key]
        
        self.logger.debug(f"Added translation: {language.value}:{key}")
    
    def get_missing_translations(self, language: Optional[Language] = None) -> List[str]:
        """Get list of missing translation keys."""
        if language:
            return [key for key in self.missing_translations if key.startswith(f"{language.value}:")]
        return list(self.missing_translations)
    
    def get_completion_status(self) -> Dict[str, Any]:
        """Get completion status for all languages."""
        status = {
            'current_language': self.current_language.value,
            'languages': {},
            'overall_stats': self.translation_stats.copy(),
            'cache_size': len(self.translation_cache),
            'missing_translations_count': len(self.missing_translations)
        }
        
        for language, locale_config in self.locales.items():
            translation_count = len(self.translations.get(language, {}))
            status['languages'][language.value] = {
                'enabled': locale_config.enabled,
                'completion_percentage': locale_config.completion_percentage,
                'translation_count': translation_count,
                'last_updated': locale_config.last_updated.isoformat(),
                'cultural_context': {
                    'communication_style': locale_config.cultural_context.communication_style.value,
                    'text_direction': locale_config.cultural_context.text_direction.value,
                    'politeness_level': locale_config.cultural_context.politeness_level
                }
            }
        
        return status
    
    def format_localized_message(
        self,
        template_key: str,
        variables: Optional[Dict[str, Any]] = None,
        language: Optional[Language] = None
    ) -> str:
        """Format a localized message with proper cultural adaptations."""
        target_language = language or self.current_language
        
        # Get cultural context
        context = self.cultural_contexts.get(target_language)
        if not context:
            context = self.cultural_contexts[Language.ENGLISH]
        
        # Translate the template
        template = self.translate(template_key, target_language, variables)
        
        # Apply cultural formatting
        if context.communication_style == CommunicationStyle.FORMAL:
            template = template.replace("Hi", "Hello").replace("Thanks", "Thank you")
        
        return template
    
    def get_culturally_appropriate_greeting(self, language: Optional[Language] = None) -> str:
        """Get culturally appropriate greeting."""
        target_language = language or self.current_language
        context = self.cultural_contexts.get(target_language)
        
        greetings = {
            Language.ENGLISH: "Hello" if context and context.greeting_style == "formal" else "Hi",
            Language.SPANISH: "Buenos días" if context and context.greeting_style == "formal" else "Hola",
            Language.FRENCH: "Bonjour",
            Language.GERMAN: "Guten Tag" if context and context.greeting_style == "formal" else "Hallo",
            Language.JAPANESE: "こんにちは",
            Language.CHINESE_SIMPLIFIED: "您好" if context and context.greeting_style == "formal" else "你好",
            Language.ARABIC: "السلام عليكم",
            Language.RUSSIAN: "Здравствуйте" if context and context.greeting_style == "formal" else "Привет"
        }
        
        return greetings.get(target_language, "Hello")
    
    def clear_cache(self):
        """Clear translation cache."""
        self.translation_cache.clear()
        self.logger.info("Translation cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get localization statistics."""
        stats = self.translation_stats.copy()
        
        # Add cache statistics
        stats.update({
            'cache_size': len(self.translation_cache),
            'cache_hit_rate': stats['cache_hits'] / max(1, stats['translations_requested']),
            'missing_translation_rate': stats['missing_keys'] / max(1, stats['translations_requested']),
            'fallback_usage_rate': stats['fallback_used'] / max(1, stats['translations_requested'])
        })
        
        # Add language statistics
        stats['languages'] = {}
        for language, translations in self.translations.items():
            stats['languages'][language.value] = len(translations)
        
        return stats