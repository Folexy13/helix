"""
Helper utilities for Helix.
"""

import re
from typing import Dict, List, Tuple


def clean_content(text: str) -> str:
    """
    Clean agent output by removing internal tags like <thinking>.
    
    Args:
        text: Original text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    # Remove <thinking>...</thinking> tags and content
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    # Also remove any stray opening/closing tags if they exist
    cleaned = re.sub(r'</?thinking>', '', cleaned)
    return cleaned.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    Generate a URL-safe slug from text.
    
    Args:
        text: Text to convert
        max_length: Maximum slug length
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Truncate
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]
    
    return slug


def parse_code_blocks(text: str) -> List[Tuple[str, str, str]]:
    """
    Parse code blocks from markdown text.
    
    Args:
        text: Markdown text with code blocks
        
    Returns:
        List of (language, code, full_match) tuples
    """
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    results = []
    for lang, code in matches:
        full_match = f"```{lang}\n{code}```"
        results.append((lang or "text", code.strip(), full_match))
    
    return results


def extract_file_paths(text: str) -> List[str]:
    """
    Extract file paths from text.
    
    Args:
        text: Text containing file paths
        
    Returns:
        List of file paths
    """
    # Match common file path patterns
    patterns = [
        r'`([^`]+\.[a-zA-Z]+)`',  # Backtick-wrapped paths
        r'File:\s*([^\s\n]+)',    # "File: path" format
        r'###\s*([^\s\n]+\.[a-zA-Z]+)',  # Markdown headers with paths
    ]
    
    paths = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        paths.extend(matches)
    
    return list(set(paths))


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in text.
    
    Uses a simple heuristic of ~4 characters per token.
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe filesystem use.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    return filename


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary to merge on top
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result
