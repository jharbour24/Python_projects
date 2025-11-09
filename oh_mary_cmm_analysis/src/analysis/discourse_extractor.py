"""Discourse extraction and labeling for CMM analysis."""
import re
import json
from typing import Dict, List, Any, Tuple
from collections import Counter
import numpy as np


class DiscourseExtractor:
    """Extracts and labels discourse patterns from audience text."""

    def __init__(self, lexicon: Dict[str, List[str]]):
        """
        Initialize discourse extractor.

        Args:
            lexicon: Movement language lexicon from config
        """
        self.lexicon = lexicon

        # Compile regex patterns for efficiency
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns from lexicon."""
        patterns = {}

        for category, terms in self.lexicon.items():
            patterns[category] = [
                re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                for term in terms
            ]

        return patterns

    def extract_features(self, text: str) -> Dict[str, Any]:
        """
        Extract discourse features from text.

        Args:
            text: Input text

        Returns:
            Dictionary of extracted features
        """
        if not text or len(text) < 10:
            return self._empty_features()

        text_lower = text.lower()

        features = {
            # Lexicon-based features
            'collective_pronouns_count': self._count_matches(text, 'collective_pronouns'),
            'belonging_terms_count': self._count_matches(text, 'belonging_terms'),
            'necessity_terms_count': self._count_matches(text, 'necessity_terms'),
            'identity_terms_count': self._count_matches(text, 'identity_terms'),
            'evangelism_terms_count': self._count_matches(text, 'evangelism_terms'),
            'repeat_terms_count': self._count_matches(text, 'repeat_terms'),
            'gatekeeping_terms_count': self._count_matches(text, 'gatekeeping_terms'),
            'emotion_intensity_count': self._count_matches(text, 'emotion_intensity'),

            # Pronoun analysis
            'first_person_plural': self._count_pronouns(text, ['we', 'us', 'our', 'ours']),
            'first_person_singular': self._count_pronouns(text, ['i', 'me', 'my', 'mine']),

            # Exclamation and emphasis
            'exclamation_count': text.count('!'),
            'all_caps_words': len(re.findall(r'\b[A-Z]{2,}\b', text)),

            # Questions (engagement markers)
            'question_count': text.count('?'),

            # Emojis (proxy for emotion)
            'emoji_count': len(re.findall(r'[\U0001F300-\U0001F9FF]', text)),

            # Length features
            'text_length': len(text),
            'word_count': len(text.split()),

            # Specific patterns
            'multiple_viewing_mention': self._detect_multiple_viewings(text),
            'recommendation_language': self._detect_recommendations(text),
            'identity_alignment': self._detect_identity_alignment(text),
            'community_reference': self._detect_community_reference(text),

            # Text for further analysis
            'original_text': text
        }

        return features

    def _count_matches(self, text: str, category: str) -> int:
        """Count matches for a lexicon category."""
        if category not in self.patterns:
            return 0

        count = 0
        for pattern in self.patterns[category]:
            count += len(pattern.findall(text))

        return count

    def _count_pronouns(self, text: str, pronouns: List[str]) -> int:
        """Count specific pronouns in text."""
        text_lower = text.lower()
        count = 0
        for pronoun in pronouns:
            count += len(re.findall(r'\b' + pronoun + r'\b', text_lower))
        return count

    def _detect_multiple_viewings(self, text: str) -> bool:
        """Detect mentions of seeing the show multiple times."""
        patterns = [
            r'seen.*\b(twice|2x|three times|3x|again|multiple times)\b',
            r'\b(second|third|fourth)\s+time',
            r'going\s+back',
            r'saw.*again',
            r'rush.*again',
            r'lottery.*again'
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _detect_recommendations(self, text: str) -> bool:
        """Detect recommendation/evangelism language."""
        patterns = [
            r'you\s+(need|must|have to|should)\s+(see|watch|go)',
            r'everyone\s+(needs|must|should)',
            r'if you haven\'?t seen',
            r'please\s+go\s+see',
            r'dragged.*friend',
            r'brought.*friend',
            r'taking.*friend'
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _detect_identity_alignment(self, text: str) -> bool:
        """Detect identity-based language."""
        identity_markers = [
            'queer', 'gay', 'lgbtq', 'lgbt', 'trans',
            'theatre kid', 'theater kid', 'broadway gay',
            'felt seen', 'represented', 'representation',
            'as a [identity]', 'for us', 'our show'
        ]

        text_lower = text.lower()
        for marker in identity_markers:
            if marker in text_lower:
                return True

        return False

    def _detect_community_reference(self, text: str) -> bool:
        """Detect references to fan community."""
        community_patterns = [
            r'rush\s+line',
            r'lottery\s+(crew|fam|gang)',
            r'stan\s+twitter',
            r'discord',
            r'groupchat',
            r'meet\s?up',
            r'fellow\s+fans',
            r'community'
        ]

        for pattern in community_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _empty_features(self) -> Dict[str, Any]:
        """Return empty feature dict for invalid text."""
        return {
            'collective_pronouns_count': 0,
            'belonging_terms_count': 0,
            'necessity_terms_count': 0,
            'identity_terms_count': 0,
            'evangelism_terms_count': 0,
            'repeat_terms_count': 0,
            'gatekeeping_terms_count': 0,
            'emotion_intensity_count': 0,
            'first_person_plural': 0,
            'first_person_singular': 0,
            'exclamation_count': 0,
            'all_caps_words': 0,
            'question_count': 0,
            'emoji_count': 0,
            'text_length': 0,
            'word_count': 0,
            'multiple_viewing_mention': False,
            'recommendation_language': False,
            'identity_alignment': False,
            'community_reference': False,
            'original_text': ''
        }

    def label_discourse_type(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Label discourse type based on features.

        Args:
            features: Extracted features

        Returns:
            Dictionary with labels and scores
        """
        labels = {
            'movement_framing': False,
            'identity_resonance': False,
            'belonging_signal': False,
            'necessity_framing': False,
            'repeat_attendance': False,
            'evangelism': False,
            'insider_gatekeeping': False,
            'high_emotion': False,
            'collective_voice': False,
            'movement_score': 0.0  # Overall score 0-1
        }

        # Movement framing: collective pronouns + community language
        if features['collective_pronouns_count'] >= 2 or features['community_reference']:
            labels['movement_framing'] = True

        # Identity resonance: identity terms + alignment
        if features['identity_terms_count'] >= 1 or features['identity_alignment']:
            labels['identity_resonance'] = True

        # Belonging signal: belonging terms
        if features['belonging_terms_count'] >= 1:
            labels['belonging_signal'] = True

        # Necessity framing: necessity terms
        if features['necessity_terms_count'] >= 1:
            labels['necessity_framing'] = True

        # Repeat attendance: multiple viewing mentions
        if features['multiple_viewing_mention'] or features['repeat_terms_count'] >= 1:
            labels['repeat_attendance'] = True

        # Evangelism: recommendation language
        if features['recommendation_language'] or features['evangelism_terms_count'] >= 1:
            labels['evangelism'] = True

        # Insider gatekeeping: gatekeeping terms
        if features['gatekeeping_terms_count'] >= 1:
            labels['insider_gatekeeping'] = True

        # High emotion: intensity markers
        if (features['emotion_intensity_count'] >= 1 or
            features['exclamation_count'] >= 3 or
            features['all_caps_words'] >= 2):
            labels['high_emotion'] = True

        # Collective voice: plural > singular pronouns
        if features['first_person_plural'] > features['first_person_singular']:
            labels['collective_voice'] = True

        # Calculate overall movement score (0-1)
        movement_indicators = [
            labels['movement_framing'],
            labels['identity_resonance'],
            labels['belonging_signal'],
            labels['necessity_framing'],
            labels['repeat_attendance'],
            labels['evangelism'],
            labels['insider_gatekeeping'],
            labels['collective_voice']
        ]

        labels['movement_score'] = sum(movement_indicators) / len(movement_indicators)

        return labels

    def classify_audience_tone(self, features: Dict[str, Any], labels: Dict[str, Any]) -> str:
        """
        Classify overall audience tone.

        Args:
            features: Extracted features
            labels: Discourse labels

        Returns:
            Tone category: reverence, belonging, identity, casual
        """
        if labels['movement_score'] >= 0.6:
            if labels['identity_resonance'] and labels['belonging_signal']:
                return 'identity'
            elif labels['movement_framing'] and labels['collective_voice']:
                return 'belonging'
            elif labels['high_emotion'] and labels['necessity_framing']:
                return 'reverence'
            else:
                return 'belonging'
        else:
            return 'casual'
