"""
AI-powered categorization module for normalizing section titles into common themes.
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import json

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# Common website section categories
DEFAULT_CATEGORIES = [
    "About/Company Overview",
    "Products/Services",
    "Features/Capabilities",
    "Pricing/Plans",
    "Testimonials/Reviews",
    "Contact Information",
    "FAQ/Help",
    "Blog/News/Articles",
    "Team/Leadership",
    "Careers/Jobs",
    "Legal/Terms/Privacy",
    "Case Studies/Portfolio",
    "Partners/Integrations",
    "Resources/Downloads",
    "Getting Started/How It Works",
    "Other"
]


class AICategorizer:
    """Uses AI to categorize section titles into common themes."""
    
    def __init__(self, api_key: Optional[str] = None, categories: Optional[List[str]] = None):
        """
        Initialize the categorizer.
        
        Args:
            api_key: OpenAI API key (falls back to env var)
            categories: Custom list of categories to use
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.categories = categories or DEFAULT_CATEGORIES
        self.client = None
        
        if self.api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)
    
    def is_available(self) -> bool:
        """Check if AI categorization is available."""
        return self.client is not None
    
    def categorize_batch(self, sections: List[Dict]) -> List[str]:
        """
        Categorize a batch of section titles.
        
        Args:
            sections: List of dicts with 'section_title' and 'content' keys
            
        Returns:
            List of category strings in the same order
        """
        if not self.is_available():
            logger.warning("OpenAI not available, using fallback categorization")
            return [self._fallback_categorize(s['section_title']) for s in sections]
        
        # Prepare the prompt
        sections_text = "\n".join([
            f"{i+1}. Title: \"{s['section_title']}\" | Content preview: \"{s['content'][:200]}...\""
            for i, s in enumerate(sections)
        ])
        
        categories_text = "\n".join([f"- {cat}" for cat in self.categories])
        
        prompt = f"""Categorize each of the following website sections into one of these categories:

{categories_text}

Sections to categorize:
{sections_text}

Respond with a JSON array of category strings in the same order as the input sections.
Only use categories from the list provided. If unsure, use "Other".
Example response: ["About/Company Overview", "Products/Services", "Contact Information"]"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that categorizes website content. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            
            categories = json.loads(result)
            
            # Validate and fill in missing categories
            while len(categories) < len(sections):
                categories.append("Other")
            
            return categories[:len(sections)]
            
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return [self._fallback_categorize(s['section_title']) for s in sections]
    
    def _fallback_categorize(self, title: str) -> str:
        """
        Simple keyword-based fallback categorization.
        
        Args:
            title: Section title to categorize
            
        Returns:
            Category string
        """
        title_lower = title.lower()
        
        keyword_map = {
            "About/Company Overview": ["about", "who we are", "our story", "mission", "vision", "company"],
            "Products/Services": ["product", "service", "solution", "offering"],
            "Features/Capabilities": ["feature", "capability", "benefit", "why choose"],
            "Pricing/Plans": ["price", "pricing", "plan", "cost", "subscription"],
            "Testimonials/Reviews": ["testimonial", "review", "customer", "client", "success"],
            "Contact Information": ["contact", "reach", "email", "phone", "location", "address"],
            "FAQ/Help": ["faq", "question", "help", "support", "how to"],
            "Blog/News/Articles": ["blog", "news", "article", "post", "update"],
            "Team/Leadership": ["team", "leadership", "founder", "people", "staff"],
            "Careers/Jobs": ["career", "job", "hiring", "work with us", "join"],
            "Legal/Terms/Privacy": ["legal", "terms", "privacy", "policy", "cookie"],
            "Case Studies/Portfolio": ["case study", "portfolio", "project", "work"],
            "Partners/Integrations": ["partner", "integration", "connect"],
            "Resources/Downloads": ["resource", "download", "guide", "whitepaper", "ebook"],
            "Getting Started/How It Works": ["getting started", "how it works", "start", "begin"],
        }
        
        for category, keywords in keyword_map.items():
            if any(kw in title_lower for kw in keywords):
                return category
        
        return "Other"
    
    def categorize_sections(self, sections: List) -> List:
        """
        Add categories to a list of Section objects.
        
        Args:
            sections: List of Section objects
            
        Returns:
            Same list with category field populated
        """
        if not sections:
            return sections
        
        # Process in batches of 20 to avoid token limits
        batch_size = 20
        
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            batch_dicts = [{'section_title': s.section_title, 'content': s.content} for s in batch]
            
            categories = self.categorize_batch(batch_dicts)
            
            for j, category in enumerate(categories):
                sections[i + j].category = category
        
        return sections
