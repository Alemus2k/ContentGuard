import nltk
import re
import string
from collections import Counter
from textblob import TextBlob
import os

class TextAnalyzer:
    def __init__(self):
        """Initialize the text analyzer with necessary NLTK data and inappropriate words list."""
        self.download_nltk_data()
        self.inappropriate_words = self.load_inappropriate_words()
        self.spam_patterns = self.load_spam_patterns()
        
    def download_nltk_data(self):
        """Download required NLTK data."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger')
    
    def load_inappropriate_words(self):
        """Load inappropriate words from file."""
        words_file = os.path.join('data', 'inappropriate_words.txt')
        try:
            with open(words_file, 'r', encoding='utf-8') as f:
                words = [line.strip().lower() for line in f if line.strip()]
            return set(words)
        except FileNotFoundError:
            # Return default set if file doesn't exist
            return {
                'hate', 'harassment', 'threat', 'violence', 'abuse', 'offensive',
                'discrimination', 'bullying', 'spam', 'scam', 'fraud', 'malicious',
                'inappropriate', 'explicit', 'nsfw', 'adult', 'sexual', 'pornographic',
                'racist', 'sexist', 'homophobic', 'xenophobic', 'toxic', 'harmful'
            }
    
    def load_spam_patterns(self):
        """Load common spam patterns."""
        return [
            r'\b(?:click here|act now|limited time|urgent|winner|congratulations)\b',
            r'\b(?:free money|make money fast|get rich quick|work from home)\b',
            r'\b(?:viagra|cialis|pharmacy|medication)\b',
            r'(?:\$\d+|\d+\$)',  # Money amounts
            r'(?:http[s]?://|www\.)',  # URLs
            r'\b(?:call now|buy now|order now|subscribe)\b'
        ]
    
    def analyze(self, text):
        """
        Analyze text content for inappropriate material.
        
        Args:
            text (str): Text content to analyze
            
        Returns:
            dict: Analysis results including appropriateness, confidence, and reasons
        """
        if not text or not text.strip():
            return {
                'is_inappropriate': False,
                'confidence_score': 0.0,
                'reasons': [],
                'details': {}
            }
        
        text = text.strip()
        reasons = []
        scores = []
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        
        # 1. Check for inappropriate words
        flagged_words = self.check_inappropriate_words(text_lower)
        if flagged_words:
            reasons.append(f"Contains inappropriate words: {', '.join(flagged_words[:3])}")
            scores.append(0.8)
        
        # 2. Sentiment analysis
        sentiment_result = self.analyze_sentiment(text)
        if sentiment_result['is_negative']:
            reasons.append(f"Negative sentiment detected (polarity: {sentiment_result['polarity']:.2f})")
            scores.append(abs(sentiment_result['polarity']) * 0.6)
        
        # 3. Spam detection
        spam_score = self.detect_spam(text_lower)
        if spam_score > 0.5:
            reasons.append(f"Potential spam content detected")
            scores.append(spam_score * 0.7)
        
        # 4. Excessive capitalization
        caps_ratio = self.check_excessive_caps(text)
        if caps_ratio > 0.6:
            reasons.append(f"Excessive capitalization ({caps_ratio:.1%})")
            scores.append(0.4)
        
        # 5. Repeated characters/words
        repetition_score = self.check_repetition(text_lower)
        if repetition_score > 0.5:
            reasons.append("Excessive repetition detected")
            scores.append(repetition_score * 0.5)
        
        # 6. Check for personal information patterns
        personal_info_score = self.check_personal_info(text)
        if personal_info_score > 0:
            reasons.append("Potential personal information sharing")
            scores.append(personal_info_score * 0.6)
        
        # Calculate overall confidence score
        if scores:
            confidence_score = min(max(scores), 1.0)
            is_inappropriate = confidence_score > 0.5
        else:
            confidence_score = 0.1  # Low confidence for appropriate content
            is_inappropriate = False
        
        return {
            'is_inappropriate': is_inappropriate,
            'confidence_score': confidence_score,
            'reasons': reasons,
            'details': {
                'flagged_words': flagged_words,
                'sentiment': sentiment_result,
                'spam_score': spam_score,
                'caps_ratio': caps_ratio,
                'repetition_score': repetition_score,
                'word_count': len(text.split()),
                'character_count': len(text)
            }
        }
    
    def check_inappropriate_words(self, text_lower):
        """Check for inappropriate words in text."""
        # Remove punctuation and split into words
        translator = str.maketrans('', '', string.punctuation)
        words = text_lower.translate(translator).split()
        
        flagged = []
        for word in words:
            if word in self.inappropriate_words:
                flagged.append(word)
        
        return flagged
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text."""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Consider very negative sentiment as potentially inappropriate
            is_negative = polarity < -0.3
            
            return {
                'polarity': polarity,
                'subjectivity': subjectivity,
                'is_negative': is_negative,
                'label': 'negative' if polarity < -0.1 else 'positive' if polarity > 0.1 else 'neutral'
            }
        except Exception as e:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'is_negative': False,
                'label': 'neutral',
                'error': str(e)
            }
    
    def detect_spam(self, text_lower):
        """Detect potential spam content."""
        spam_indicators = 0
        total_patterns = len(self.spam_patterns)
        
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                spam_indicators += 1
        
        # Additional spam indicators
        # Check for excessive punctuation
        punct_ratio = len([c for c in text_lower if c in '!?']) / max(len(text_lower), 1)
        if punct_ratio > 0.1:
            spam_indicators += 1
            total_patterns += 1
        
        # Check for excessive numbers
        number_ratio = len(re.findall(r'\d', text_lower)) / max(len(text_lower), 1)
        if number_ratio > 0.3:
            spam_indicators += 1
            total_patterns += 1
        
        return spam_indicators / max(total_patterns, 1)
    
    def check_excessive_caps(self, text):
        """Check for excessive capitalization."""
        if not text:
            return 0
        
        uppercase_letters = sum(1 for c in text if c.isupper())
        total_letters = sum(1 for c in text if c.isalpha())
        
        if total_letters == 0:
            return 0
        
        return uppercase_letters / total_letters
    
    def check_repetition(self, text_lower):
        """Check for excessive repetition of characters or words."""
        # Check for repeated characters
        char_pattern = re.findall(r'(.)\1{3,}', text_lower)  # 4 or more repeated chars
        char_repetition_score = len(char_pattern) * 0.1
        
        # Check for repeated words
        words = text_lower.split()
        if len(words) > 0:
            word_counts = Counter(words)
            max_word_count = max(word_counts.values()) if word_counts else 0
            word_repetition_score = min((max_word_count - 1) * 0.1, 0.5)
        else:
            word_repetition_score = 0
        
        return min(char_repetition_score + word_repetition_score, 1.0)
    
    def check_personal_info(self, text):
        """Check for patterns that might indicate personal information sharing."""
        patterns = [
            r'\b\d{3}-?\d{2}-?\d{4}\b',  # SSN pattern
            r'\b\d{3}-?\d{3}-?\d{4}\b',  # Phone number
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card pattern
        ]
        
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text):
                matches += 1
        
        return min(matches * 0.3, 1.0)
