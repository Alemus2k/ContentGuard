import re
from datetime import datetime
import hashlib

def get_confidence_color(confidence_score):
    """
    Get color code based on confidence score.
    
    Args:
        confidence_score (float): Confidence score between 0 and 1
        
    Returns:
        str: CSS color code
    """
    if confidence_score >= 0.8:
        return "#ff4444"  # Red for high confidence inappropriate
    elif confidence_score >= 0.6:
        return "#ff8800"  # Orange for medium-high confidence
    elif confidence_score >= 0.4:
        return "#ffbb00"  # Yellow for medium confidence
    elif confidence_score >= 0.2:
        return "#88cc00"  # Light green for low confidence
    else:
        return "#44cc44"  # Green for very low confidence (appropriate)

def format_timestamp(timestamp_str):
    """
    Format timestamp string for display.
    
    Args:
        timestamp_str (str): ISO format timestamp string
        
    Returns:
        str: Formatted timestamp
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp_str)

def sanitize_text(text, max_length=200):
    """
    Sanitize text for safe display.
    
    Args:
        text (str): Text to sanitize
        max_length (int): Maximum length to display
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', str(text))
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized

def generate_content_hash(content):
    """
    Generate hash for content to detect duplicates.
    
    Args:
        content (str): Content to hash
        
    Returns:
        str: SHA256 hash of content
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    elif isinstance(content, bytes):
        pass
    else:
        content = str(content).encode('utf-8')
    
    return hashlib.sha256(content).hexdigest()

def extract_keywords(text, min_word_length=3, max_words=10):
    """
    Extract keywords from text.
    
    Args:
        text (str): Text to extract keywords from
        min_word_length (int): Minimum word length to consider
        max_words (int): Maximum number of keywords to return
        
    Returns:
        list: List of keywords
    """
    if not text:
        return []
    
    # Convert to lowercase and remove punctuation
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Split into words
    words = clean_text.split()
    
    # Filter words
    keywords = []
    stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'of', 'for', 'in', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
    
    for word in words:
        if (len(word) >= min_word_length and 
            word not in stop_words and 
            word.isalpha() and 
            word not in keywords):
            keywords.append(word)
            
            if len(keywords) >= max_words:
                break
    
    return keywords

def calculate_text_similarity(text1, text2):
    """
    Calculate similarity between two texts using simple word overlap.
    
    Args:
        text1 (str): First text
        text2 (str): Second text
        
    Returns:
        float: Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Extract keywords from both texts
    keywords1 = set(extract_keywords(text1, max_words=50))
    keywords2 = set(extract_keywords(text2, max_words=50))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(keywords1.intersection(keywords2))
    union = len(keywords1.union(keywords2))
    
    return intersection / union if union > 0 else 0.0

def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_file_type(filename, allowed_types):
    """
    Validate if file type is allowed.
    
    Args:
        filename (str): Name of the file
        allowed_types (list): List of allowed file extensions
        
    Returns:
        bool: True if file type is allowed
    """
    if not filename or not allowed_types:
        return False
    
    file_extension = filename.lower().split('.')[-1]
    return file_extension in [ext.lower().strip('.') for ext in allowed_types]

def clean_html(text):
    """
    Remove HTML tags from text.
    
    Args:
        text (str): Text that may contain HTML
        
    Returns:
        str: Text with HTML tags removed
    """
    if not text:
        return ""
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', str(text))
    
    # Replace HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    
    for entity, replacement in html_entities.items():
        clean = clean.replace(entity, replacement)
    
    return clean.strip()
