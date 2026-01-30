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
class PageMeta:
    """Represents metadata extracted from a webpage."""
    page_title: str
    meta_description: str
    canonical_url: str


@dataclass
class Section:
    """Represents a section extracted from a webpage."""
    url: str
    section_title: str
    section_level: str
    content: str
    category: Optional[str] = None
    page_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None


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
    
    def extract_page_meta(self, soup: BeautifulSoup, url: str) -> PageMeta:
        """
        Extract page metadata (title, description, canonical URL).
        
        Args:
            soup: BeautifulSoup object of the page
            url: The page URL (fallback for canonical)
            
        Returns:
            PageMeta object with extracted metadata
        """
        # Extract page title
        page_title = ""
        title_tag = soup.find('title')
        if title_tag:
            page_title = title_tag.get_text(strip=True)
        
        # Extract meta description
        meta_description = ""
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_desc_tag:
            meta_description = meta_desc_tag.get('content', '')
        
        # Try og:description as fallback
        if not meta_description:
            og_desc_tag = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc_tag:
                meta_description = og_desc_tag.get('content', '')
        
        # Extract canonical URL
        canonical_url = url
        canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
        if canonical_tag:
            canonical_url = canonical_tag.get('href', url)
        
        return PageMeta(
            page_title=page_title,
            meta_description=meta_description,
            canonical_url=canonical_url
        )

    def _get_section_content(self, heading, soup, all_headings) -> str:
        """
        Extract all content belonging to a heading section, including nested elements.
        
        This method finds the parent container of the heading and extracts all text
        content until the next heading of equal or higher level.
        
        Args:
            heading: The heading element
            soup: The BeautifulSoup object
            all_headings: List of all heading elements in document order
            
        Returns:
            Extracted text content
        """
        content_parts = []
        heading_level = int(heading.name[1])
        
        # Find the index of this heading in the list
        try:
            heading_idx = all_headings.index(heading)
        except ValueError:
            heading_idx = -1
        
        # Find the next heading of same or higher level (lower number)
        next_boundary = None
        if heading_idx >= 0:
            for h in all_headings[heading_idx + 1:]:
                h_level = int(h.name[1])
                if h_level <= heading_level:
                    next_boundary = h
                    break
        
        # Strategy 1: Look for content in the heading's parent container
        parent = heading.parent
        if parent:
            # Traverse siblings after the heading within the same parent
            for sibling in heading.find_next_siblings():
                # Stop if we hit the next boundary heading
                if next_boundary and (sibling == next_boundary or next_boundary in sibling.descendants if hasattr(sibling, 'descendants') else False):
                    break
                # Stop if we hit another heading of same/higher level
                if sibling.name in self.HEADING_TAGS:
                    sib_level = int(sibling.name[1])
                    if sib_level <= heading_level:
                        break
                
                text = sibling.get_text(separator=' ', strip=True)
                if text:
                    content_parts.append(text)
        
        # Strategy 2: If no content found via siblings, use next_elements iterator
        if not content_parts:
            for element in heading.next_elements:
                # Stop conditions
                if element == next_boundary:
                    break
                if hasattr(element, 'name') and element.name in self.HEADING_TAGS:
                    elem_level = int(element.name[1])
                    if elem_level <= heading_level:
                        break
                
                # Skip the heading itself and non-text elements
                if element == heading:
                    continue
                if hasattr(element, 'name') and element.name in ['script', 'style']:
                    continue
                
                # Get text from NavigableString or leaf elements
                if isinstance(element, str):
                    text = element.strip()
                    if text and text not in content_parts:
                        content_parts.append(text)
                elif hasattr(element, 'name') and not element.find_all():
                    # Leaf element with no children
                    text = element.get_text(strip=True)
                    if text and text not in content_parts:
                        content_parts.append(text)
        
        # Join and clean up
        content = ' '.join(content_parts)
        # Remove excessive whitespace
        content = ' '.join(content.split())
        
        return content
    
    def _find_section_container(self, heading) -> Optional[any]:
        """
        Find the logical container for a section by looking at common patterns.
        
        Args:
            heading: The heading element
            
        Returns:
            Container element or None
        """
        # Look for common section container patterns
        container_classes = ['section', 'content', 'block', 'card', 'panel', 'box', 'module']
        container_tags = ['section', 'article', 'div']
        
        parent = heading.parent
        for _ in range(5):  # Look up to 5 levels
            if parent is None:
                break
            
            # Check if this parent looks like a section container
            if parent.name in container_tags:
                parent_classes = parent.get('class', [])
                if isinstance(parent_classes, list):
                    for cls in parent_classes:
                        if any(c in cls.lower() for c in container_classes):
                            return parent
            
            parent = parent.parent
        
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
        
        # Extract page metadata first (before removing elements)
        page_meta = self.extract_page_meta(soup, url)
        
        # Remove script, style, nav, footer, header elements
        for element in soup.find_all(['script', 'style', 'noscript']):
            element.decompose()
        
        sections = []
        
        # Find all heading elements in document order
        headings = soup.find_all(self.HEADING_TAGS)
        
        for heading in headings:
            title = heading.get_text(strip=True)
            if not title:
                continue
            
            level = heading.name  # h1, h2, etc.
            
            # Extract content using improved method
            content = self._get_section_content(heading, soup, headings)
            
            # If still no content, try the container approach
            if not content:
                container = self._find_section_container(heading)
                if container:
                    # Get all text from container, excluding the heading itself
                    container_text = container.get_text(separator=' ', strip=True)
                    # Remove the heading text from the beginning
                    if container_text.startswith(title):
                        content = container_text[len(title):].strip()
                    else:
                        content = container_text
            
            # Only include sections with some content or meaningful titles
            if title or content:
                sections.append(Section(
                    url=url,
                    section_title=title,
                    section_level=level,
                    content=content[:5000],  # Limit content length
                    page_title=page_meta.page_title,
                    meta_description=page_meta.meta_description,
                    canonical_url=page_meta.canonical_url
                ))
        
        # If no headings found, try to extract main content
        if not sections:
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
                if text:
                    sections.append(Section(
                        url=url,
                        section_title="Main Content",
                        section_level="body",
                        content=text[:5000],
                        page_title=page_meta.page_title,
                        meta_description=page_meta.meta_description,
                        canonical_url=page_meta.canonical_url
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
