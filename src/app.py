#!/usr/bin/env python3
"""
Neptune - Web UI for Website Content Extractor

Streamlit-based web interface for scraping and categorizing website content.
"""

import streamlit as st
import pandas as pd
import re
import time
from urllib.parse import urlparse
from io import BytesIO
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import WebScraper, Section
from categorizer import AICategorizer
from cleaner import filter_dataframe, get_filter_summary


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    # Clean the URL
    url = url.strip()
    if not url:
        return False
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Parse and validate
    try:
        result = urlparse(url)
        # Must have scheme and netloc (domain)
        if not all([result.scheme, result.netloc]):
            return False
        # Domain must have at least one dot (e.g., example.com)
        if '.' not in result.netloc:
            return False
        # Check for valid characters in domain
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?'
            r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*'
            r'\.[a-zA-Z]{2,}$'
        )
        domain = result.netloc.split(':')[0]  # Remove port if present
        if not domain_pattern.match(domain):
            return False
        return True
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize URL by adding scheme if missing."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def sections_to_dataframe(sections: list) -> pd.DataFrame:
    """Convert Section objects to DataFrame."""
    data = []
    for section in sections:
        data.append({
            'url': section.url,
            'page_title': getattr(section, 'page_title', '') or '',
            'meta_description': getattr(section, 'meta_description', '') or '',
            'canonical_url': getattr(section, 'canonical_url', '') or '',
            'section_title': section.section_title,
            'section_level': section.section_level,
            'content': section.content,
            'ai_category': section.category or ''
        })
    return pd.DataFrame(data)


def main():
    st.set_page_config(
        page_title="Neptune - Website Content Extractor",
        page_icon="🌊",
        layout="wide"
    )
    
    st.title("🌊 Neptune")
    st.subheader("Website Content Extractor")
    st.markdown("Extract section titles and content from websites with AI-powered categorization.")
    
    st.divider()
    
    # URL Input Section
    st.markdown("### 📝 Enter URLs")
    st.markdown("Enter one URL per line. URLs will be validated before processing.")
    
    url_input = st.text_area(
        "URLs to scrape",
        height=200,
        placeholder="https://example.com\nhttps://another-site.com/page\nhttps://website.com/products",
        help="Enter one URL per line. The tool will extract all section headings and content from each page."
    )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        enable_ai = st.checkbox(
            "Enable AI Categorization",
            value=True,
            help="Use AI to categorize sections into common themes like 'Products', 'About', 'Contact', etc."
        )
    with col2:
        delay = st.slider(
            "Delay between requests (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Be respectful to servers by adding delay between requests"
        )
    
    # Additional options
    col3, col4 = st.columns(2)
    with col3:
        enable_filtering = st.checkbox(
            "Enable Data Cleaning & Filtering",
            value=True,
            help="Remove boilerplate, low-value content, and optimize for AI analysis"
        )
    
    # Parse and validate URLs
    urls_raw = [line.strip() for line in url_input.strip().split('\n') if line.strip()]
    
    valid_urls = []
    invalid_urls = []
    
    for url in urls_raw:
        if is_valid_url(url):
            valid_urls.append(normalize_url(url))
        else:
            invalid_urls.append(url)
    
    # Show validation status
    if urls_raw:
        st.markdown("### ✅ URL Validation")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Valid URLs", len(valid_urls))
        with col2:
            st.metric("Invalid URLs", len(invalid_urls))
        
        if invalid_urls:
            with st.expander(f"⚠️ {len(invalid_urls)} Invalid URLs (click to see)", expanded=False):
                for url in invalid_urls:
                    st.error(f"❌ `{url}`")
    
    # Submit button
    st.divider()
    submit_disabled = len(valid_urls) == 0
    
    if st.button("🚀 Start Extraction", type="primary", disabled=submit_disabled, use_container_width=True):
        if not valid_urls:
            st.error("Please enter at least one valid URL")
            return
        
        # Initialize components
        scraper = WebScraper(timeout=30, delay=delay)
        categorizer = AICategorizer() if enable_ai else None
        
        all_sections = []
        
        # Progress tracking
        st.markdown("### 📊 Progress")
        progress_bar = st.progress(0)
        status_text = st.empty()
        current_url_text = st.empty()
        
        # Scraping phase
        status_text.markdown("**Phase 1/2:** Extracting content from websites...")
        
        for i, url in enumerate(valid_urls):
            current_url_text.markdown(f"🔍 Scraping: `{url}`")
            progress = (i + 1) / len(valid_urls) * 0.7  # 70% for scraping
            progress_bar.progress(progress)
            
            try:
                sections = scraper.scrape_url(url)
                all_sections.extend(sections)
            except Exception as e:
                st.warning(f"Failed to scrape {url}: {str(e)}")
            
            # Delay between requests (except for last one)
            if i < len(valid_urls) - 1:
                time.sleep(delay)
        
        current_url_text.empty()
        
        # Categorization phase
        if enable_ai and all_sections:
            status_text.markdown("**Phase 2/2:** AI Categorization...")
            progress_bar.progress(0.8)
            
            if categorizer and categorizer.is_available():
                current_url_text.markdown("🤖 Using OpenAI for intelligent categorization...")
            else:
                current_url_text.markdown("🔤 Using keyword-based categorization (set OPENAI_API_KEY for AI)")
            
            all_sections = categorizer.categorize_sections(all_sections)
            current_url_text.empty()
        
        progress_bar.progress(0.9)
        
        # Convert to DataFrame
        df = sections_to_dataframe(all_sections)
        original_count = len(df)
        
        # Apply filtering if enabled
        if enable_filtering:
            status_text.markdown("**Phase 3/3:** Cleaning and filtering data...")
            current_url_text.markdown("🧹 Removing boilerplate and low-value content...")
            df = filter_dataframe(df)
            filter_summary = get_filter_summary(original_count, len(df))
            current_url_text.empty()
        
        progress_bar.progress(1.0)
        status_text.markdown("**✅ Complete!**")
        
        # Results
        st.divider()
        st.markdown("### 📋 Results")
        
        if len(df) > 0:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("URLs Processed", len(valid_urls))
            with col2:
                st.metric("Sections Extracted", original_count)
            with col3:
                if enable_filtering:
                    st.metric("After Filtering", len(df))
                else:
                    st.metric("Total Sections", len(df))
            with col4:
                if enable_ai:
                    unique_categories = df['ai_category'].nunique()
                    st.metric("Categories Found", unique_categories)
            
            # Category breakdown
            if enable_ai and 'ai_category' in df.columns:
                st.markdown("#### 📊 Sections by Category")
                category_counts = df['ai_category'].value_counts()
                st.bar_chart(category_counts)
            
            # Data preview
            st.markdown("#### 📄 Data Preview")
            st.dataframe(df, use_container_width=True, height=400)
            
            # Download buttons
            st.markdown("#### 💾 Download Results")
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name="neptune_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Excel download
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data,
                    file_name="neptune_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.warning("No content was extracted from the provided URLs.")
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <small>Neptune - Website Content Extractor | Built with Streamlit</small>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
