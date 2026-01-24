"""
Web scraper module for extracting section titles and content from websites.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import time
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a section extracted from a webpage."""
    url: str
    section_title: str
    section_level: str
    content: str
    category: Optional[str] = None


class WebScraper:
    """Scraper for extracting section titles and content from webpages."""
    
    HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    def __init__(self, timeout: int = 30, delay: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests to be respectful to servers
        """
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch the HTML content of a webpage.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string, or None if fetch failed
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = 'https://' + url
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def extract_sections(self, html: str, url: str) -> List[Section]:
        """
        Extract all sections (headings and their content) from HTML.
        
        Args:
            html: The HTML content
            url: The source URL (for reference)
            
        Returns:
            List of Section objects
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script, style, nav, footer, header elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
        
        sections = []
        
        # Find all heading elements
        headings = soup.find_all(self.HEADING_TAGS)
        
        for i, heading in enumerate(headings):
            title = heading.get_text(strip=True)
            if not title:
                continue
            
            level = heading.name  # h1, h2, etc.
            
            # Extract content between this heading and the next
            content_parts = []
            current = heading.next_sibling
            
            while current:
                # Stop if we hit another heading of same or higher level
                if hasattr(current, 'name') and current.name in self.HEADING_TAGS:
                    current_level = int(current.name[1])
                    this_level = int(level[1])
                    if current_level <= this_level:
                        break
                
                # Extract text from this element
                if hasattr(current, 'get_text'):
                    text = current.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                elif isinstance(current, str) and current.strip():
                    content_parts.append(current.strip())
                
                current = current.next_sibling
            
            content = ' '.join(content_parts)
            
            # Only include sections with some content or meaningful titles
            if title or content:
                sections.append(Section(
                    url=url,
                    section_title=title,
                    section_level=level,
                    content=content[:5000]  # Limit content length
                ))
        
        # If no headings found, try to extract main content
        if not sections:
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                text = main_content.get_text(strip=True)
                if text:
                    sections.append(Section(
                        url=url,
                        section_title="Main Content",
                        section_level="body",
                        content=text[:5000]
                    ))
        
        return sections
    
    def scrape_url(self, url: str) -> List[Section]:
        """
        Scrape a single URL and extract its sections.
        
        Args:
            url: The URL to scrape
            
        Returns:
            List of Section objects
        """
        logger.info(f"Scraping: {url}")
        
        html = self.fetch_page(url)
        if not html:
            return [Section(
                url=url,
                section_title="ERROR",
                section_level="error",
                content="Failed to fetch page"
            )]
        
        sections = self.extract_sections(html, url)
        
        if not sections:
            return [Section(
                url=url,
                section_title="NO_CONTENT",
                section_level="none",
                content="No sections found on page"
            )]
        
        return sections
    
    def scrape_urls(self, urls: List[str]) -> List[Section]:
        """
        Scrape multiple URLs and extract sections from each.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of all Section objects from all URLs
        """
        all_sections = []
        
        for i, url in enumerate(urls):
            sections = self.scrape_url(url)
            all_sections.extend(sections)
            
            # Respectful delay between requests
            if i < len(urls) - 1:
                time.sleep(self.delay)
        
        return all_sections
