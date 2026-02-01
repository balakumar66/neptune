"""
Data cleaning and filtering module for Neptune.

Implements filtering logic to optimize scraped data for AI analysis.
Configuration is loaded from config/filters.yaml for easy customization.
"""

import re
import os
import pandas as pd
from typing import List, Set, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import yaml, fall back to defaults if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Using default filter configuration.")


def load_filter_config() -> Dict[str, Any]:
    """
    Load filter configuration from YAML file.
    Falls back to defaults if file not found or yaml not available.
    
    Returns:
        Configuration dictionary
    """
    defaults = {
        'min_word_count': 5,
        'excluded_categories': [
            "Legal/Terms/Privacy",
            "Contact Information",
            "Navigation/Menu",
            "Other"
        ],
        'excluded_section_titles': [
            "related products",
            "you may also like",
            "customers also bought",
            "similar products",
            "recently viewed",
            "recommended for you",
            "footer",
            "sitemap"
        ],
        'boilerplate_keywords': [
            "copyright",
            "all rights reserved",
            "privacy policy",
            "terms and conditions"
        ],
        'boilerplate_phrases': [
            r"Loading\.\.\.",
            r"Click here",
            r"Read more"
        ]
    }
    
    if not YAML_AVAILABLE:
        return defaults
    
    # Look for config file in multiple locations
    config_paths = [
        Path(__file__).parent.parent / 'config' / 'filters.yaml',
        Path(__file__).parent / 'config' / 'filters.yaml',
        Path('config/filters.yaml'),
        Path('filters.yaml'),
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded filter config from {config_path}")
                    # Merge with defaults for any missing keys
                    for key, value in defaults.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
    
    logger.info("Using default filter configuration")
    return defaults


# Load configuration
_config = load_filter_config()

# Export configuration values for use in module
EXCLUDED_CATEGORIES = set(_config.get('excluded_categories', []))
BOILERPLATE_KEYWORDS = _config.get('boilerplate_keywords', [])
EXCLUDED_SECTION_TITLES = _config.get('excluded_section_titles', [])
BOILERPLATE_PHRASES = _config.get('boilerplate_phrases', [])
MIN_WORD_COUNT = _config.get('min_word_count', 5)


def reload_config():
    """Reload configuration from file. Useful for testing or runtime updates."""
    global _config, EXCLUDED_CATEGORIES, BOILERPLATE_KEYWORDS, EXCLUDED_SECTION_TITLES, BOILERPLATE_PHRASES, MIN_WORD_COUNT
    _config = load_filter_config()
    EXCLUDED_CATEGORIES = set(_config.get('excluded_categories', []))
    BOILERPLATE_KEYWORDS = _config.get('boilerplate_keywords', [])
    EXCLUDED_SECTION_TITLES = _config.get('excluded_section_titles', [])
    BOILERPLATE_PHRASES = _config.get('boilerplate_phrases', [])
    MIN_WORD_COUNT = _config.get('min_word_count', 5)


def clean_text(text: str) -> str:
    """
    Clean text by removing HTML tags, extra whitespace, and newlines.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove HTML entities
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def strip_boilerplate_phrases(text: str) -> str:
    """
    Remove common boilerplate phrases from text.
    
    Args:
        text: Text to clean
        
    Returns:
        Text with boilerplate phrases removed
    """
    for phrase in BOILERPLATE_PHRASES:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    
    # Clean up any double spaces created
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def contains_boilerplate_keywords(title: str, content: str) -> bool:
    """
    Check if title or content contains boilerplate keywords.
    
    Args:
        title: Section title
        content: Section content
        
    Returns:
        True if boilerplate keywords found
    """
    combined_text = f"{title} {content}".lower()
    
    for keyword in BOILERPLATE_KEYWORDS:
        if keyword in combined_text:
            return True
    
    return False


def is_excluded_section_title(title: str) -> bool:
    """
    Check if section title matches excluded patterns (e.g., Related Products).
    
    Args:
        title: Section title to check
        
    Returns:
        True if title should be excluded
    """
    if not title:
        return False
    
    title_lower = title.lower().strip()
    
    for excluded in EXCLUDED_SECTION_TITLES:
        if excluded in title_lower:
            return True
    
    return False


def get_word_count(text: str) -> int:
    """
    Get word count of text.
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
    """
    if not text:
        return 0
    
    words = text.split()
    return len(words)


def is_full_page_dump(row: dict, all_rows_for_url: List[dict]) -> bool:
    """
    Check if an h1 row contains a full page dump that duplicates other sections.
    
    Args:
        row: The row to check
        all_rows_for_url: All rows for the same URL
        
    Returns:
        True if this appears to be a full page dump
    """
    if row.get('section_level') != 'h1':
        return False
    
    content = row.get('content', '')
    if not content:
        return False
    
    # Check if h1 content length is significantly larger than other sections
    h1_length = len(content)
    
    # Get content from h2/h3/h4/h5/h6 sections
    other_sections = [r for r in all_rows_for_url 
                      if r.get('section_level') in ['h2', 'h3', 'h4', 'h5', 'h6']]
    
    if not other_sections:
        return False
    
    # Calculate total length of specific sections
    specific_content_length = sum(len(r.get('content', '')) for r in other_sections)
    
    # If h1 content is more than 80% of the combined specific sections,
    # and there are at least 3 specific sections, it's likely a dump
    if len(other_sections) >= 3 and h1_length > specific_content_length * 0.8:
        # Additional check: see if h1 content contains text from multiple sections
        matches = 0
        for section in other_sections:
            section_content = section.get('content', '')
            if section_content and len(section_content) > 50:
                # Check if significant portion of section content is in h1
                if section_content[:100] in content:
                    matches += 1
        
        # If h1 contains content from more than half the sections, it's a dump
        if matches >= len(other_sections) / 2:
            return True
    
    return False


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all filtering rules to the DataFrame.
    
    Args:
        df: Input DataFrame with scraped data
        
    Returns:
        Filtered DataFrame
    """
    original_count = len(df)
    
    # Step 1: Clean text fields
    logger.info("Cleaning text fields...")
    df['content'] = df['content'].apply(clean_text)
    df['section_title'] = df['section_title'].apply(clean_text)
    
    # Strip boilerplate phrases from content
    df['content'] = df['content'].apply(strip_boilerplate_phrases)
    
    # Step 2: Filter by excluded categories
    if 'ai_category' in df.columns:
        logger.info("Filtering excluded categories...")
        before = len(df)
        df = df[~df['ai_category'].isin(EXCLUDED_CATEGORIES)]
        logger.info(f"  Removed {before - len(df)} rows by category filter")
    
    # Step 3: Filter by boilerplate keywords
    logger.info("Filtering boilerplate keywords...")
    before = len(df)
    mask = df.apply(
        lambda row: not contains_boilerplate_keywords(
            row.get('section_title', ''), 
            row.get('content', '')
        ), 
        axis=1
    )
    df = df[mask]
    logger.info(f"  Removed {before - len(df)} rows by keyword filter")
    
    # Step 3b: Filter by excluded section titles (Related Products, etc.)
    logger.info("Filtering excluded section titles...")
    before = len(df)
    mask = ~df['section_title'].apply(is_excluded_section_title)
    df = df[mask]
    logger.info(f"  Removed {before - len(df)} rows by section title filter")
    
    # Step 3c: Filter product link sections (title equals content, common in Related Products)
    logger.info("Filtering product link sections...")
    before = len(df)
    def is_product_link_section(row):
        title = str(row.get('section_title', '')).strip().lower()
        content = str(row.get('content', '')).strip().lower()
        # If content is just the title (or title + "good/better/best"), it's likely a product link
        if not title or not content:
            return False
        # Check if content is essentially just the title with maybe a rating word
        content_clean = content.replace('good', '').replace('better', '').replace('best', '').replace('new', '').strip()
        title_in_content = title in content and len(content) < len(title) * 2
        return title_in_content or content_clean == title
    
    mask = ~df.apply(is_product_link_section, axis=1)
    df = df[mask]
    logger.info(f"  Removed {before - len(df)} rows by product link filter")
    
    # Step 4: Filter by minimum word count
    logger.info("Filtering by minimum word count...")
    before = len(df)
    df['word_count'] = df['content'].apply(get_word_count)
    df = df[df['word_count'] >= MIN_WORD_COUNT]
    df = df.drop(columns=['word_count'])
    logger.info(f"  Removed {before - len(df)} rows by word count filter")
    
    # Step 5: Deduplicate content within same URL
    logger.info("Deduplicating content...")
    before = len(df)
    df = df.drop_duplicates(subset=['url', 'content'], keep='first')
    logger.info(f"  Removed {before - len(df)} duplicate rows")
    
    # Step 6: Remove full page dumps (h1 that contains all other content)
    logger.info("Removing full page dumps...")
    before = len(df)
    rows_to_remove = set()
    
    for url in df['url'].unique():
        url_rows = df[df['url'] == url].to_dict('records')
        for i, row in enumerate(url_rows):
            if is_full_page_dump(row, url_rows):
                # Find the index in the original dataframe
                mask = (df['url'] == row['url']) & \
                       (df['section_title'] == row['section_title']) & \
                       (df['section_level'] == row['section_level'])
                indices = df[mask].index.tolist()
                rows_to_remove.update(indices)
    
    df = df.drop(index=list(rows_to_remove))
    logger.info(f"  Removed {before - len(df)} full page dump rows")
    
    # Reset index
    df = df.reset_index(drop=True)
    
    logger.info(f"Filtering complete: {original_count} -> {len(df)} rows ({original_count - len(df)} removed)")
    
    return df


def get_filter_summary(original_count: int, filtered_count: int) -> dict:
    """
    Generate a summary of filtering results.
    
    Args:
        original_count: Number of rows before filtering
        filtered_count: Number of rows after filtering
        
    Returns:
        Summary dictionary
    """
    removed = original_count - filtered_count
    percentage = (removed / original_count * 100) if original_count > 0 else 0
    
    return {
        'original_rows': original_count,
        'filtered_rows': filtered_count,
        'removed_rows': removed,
        'removal_percentage': round(percentage, 1)
    }
